# Equipe 3: Enzo Bossmann, Diego Feltrin e Gabriel Henrique
# Projeto: SmartPark 2.0 - CPS1 Vagas
# Disciplina: Conectividade em Sistemas Ciberfisicos - PUCPR 2026.2
# Placa: ESP32 + 4x HC-SR04 + 8 LEDs | Comunicacao: MQTT
#
# Logica: cada vaga tem um sensor de distancia. Carro perto do sensor = vaga
# OCUPADA (LED vermelho), senao LIVRE (LED verde). O ESP32 publica as vagas
# no broker e a cancela (CPS2) e o totem (CPS3) usam esse dado.
#
# Do SmartPark do semestre passado (Old/main.py) vieram medir_distancia(),
# atualizar_led() e conectar_wifi(). O resto e novo.
#
# Publica:  cps1/sensor (vagas), cps1/estado (LEDs), cps1/status (online/offline)
# Assina:   cps1/comando (dashboard) e cps2/estado (emergencia)

import json
import random
import time

import network
from machine import Pin, time_pulse_us
from umqtt.simple import MQTTClient

# Configuracoes
WIFI_SSID = "Wokwi-GUEST"
WIFI_SENHA = ""
BROKER = "broker.hivemq.com"
PREFIXO = "cscf/equipe03"
try:
    from sim_config import BROKER, PREFIXO  # so existe no teste local (pasta sim/)
except ImportError:
    pass

# No Wokwi todo ESP32 tem o mesmo MAC, entao o id precisa de um numero aleatorio.
# Se dois clientes usam o mesmo id, o broker derruba um deles.
CLIENT_ID = "smartpark-cps1-%04x" % (random.getrandbits(16) ^ (time.ticks_us() & 0xFFFF))

T_SENSOR = PREFIXO + "/cps1/sensor"
T_ESTADO = PREFIXO + "/cps1/estado"
T_COMANDO = PREFIXO + "/cps1/comando"
T_STATUS = PREFIXO + "/cps1/status"
T_CPS2_ESTADO = PREFIXO + "/cps2/estado"

# Ocupa abaixo de 50 cm e so libera acima de 60 cm, assim o LED nao fica piscando na borda
LIMIAR_OCUPADA_CM = 50
LIMIAR_LIVRE_CM = 60
PING_MS = 10000          # avisa o broker que esta vivo (keepalive de 30 s)
REPUBLICAR_MS = 15000    # republica as vagas mesmo se nada mudou
RECONECTAR_MS = 5000     # sem rede, tenta de novo a cada 5 s

# Pinos
# (id, tipo, TRIG, ECHO, LED verde, LED vermelho)
VAGAS = [
    ("V1", "comum", 5, 34, 2, 22),
    ("V2", "comum", 18, 35, 4, 23),
    ("V3", "idoso", 19, 32, 16, 25),
    ("V4", "pcd", 21, 33, 17, 26),
]

vagas = []
for vid, tipo, trig, echo, verde, vermelho in VAGAS:
    vagas.append({
        "id": vid,
        "tipo": tipo,
        "trig": Pin(trig, Pin.OUT),
        "echo": Pin(echo, Pin.IN),
        "verde": Pin(verde, Pin.OUT),
        "vermelho": Pin(vermelho, Pin.OUT),
        "ocupada": False,
        "cm": 400,
    })

interditadas = []    # vagas que o operador tirou de uso pelo dashboard
emergencia = False   # vem do CPS2
ultimo_ack = None
mudou_por_rede = False


# Funcoes

def medir_distancia(trig, echo):
    """Dispara um pulso ultrassonico e retorna a distancia em cm.
    Retorna 999 se nao houver eco."""
    trig.off()
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()
    duracao = time_pulse_us(echo, 1, 30000)
    if duracao < 0:
        return 999
    # velocidade do som = 0.0343 cm/us; divide por 2 (ida e volta)
    return duracao * 0.0343 / 2


def atualizar_led(ocupada, verde, vermelho):
    """Acende vermelho se a vaga esta ocupada, senao acende verde."""
    if ocupada:
        verde.off()
        vermelho.on()
    else:
        verde.on()
        vermelho.off()


def ler_vagas():
    # le os 4 sensores e devolve True se alguma vaga mudou
    mudou = False
    for v in vagas:
        cm = medir_distancia(v["trig"], v["echo"])
        v["cm"] = int(cm)
        if not v["ocupada"] and cm < LIMIAR_OCUPADA_CM:
            v["ocupada"] = True
            mudou = True
        elif v["ocupada"] and cm > LIMIAR_LIVRE_CM:
            v["ocupada"] = False
            mudou = True
    return mudou


def piscando(v):
    return emergencia or v["id"] in interditadas


def acender_leds():
    # vaga interditada ou emergencia: vermelho piscando
    pisca = (time.ticks_ms() // 500) % 2 == 0
    for v in vagas:
        if piscando(v):
            v["verde"].off()
            v["vermelho"].value(pisca)
        else:
            atualizar_led(v["ocupada"], v["verde"], v["vermelho"])


def resumo_vagas():
    livres_tipo = {"comum": 0, "idoso": 0, "pcd": 0}
    lista = []
    for v in vagas:
        interditada = v["id"] in interditadas
        lista.append({"id": v["id"], "tipo": v["tipo"], "ocupada": v["ocupada"],
                      "interditada": interditada, "cm": v["cm"]})
        if not v["ocupada"] and not interditada:
            livres_tipo[v["tipo"]] += 1
    return {"vagas": lista, "livres": sum(livres_tipo.values()),
            "livres_comuns": livres_tipo["comum"], "livres_tipo": livres_tipo,
            "total": len(vagas)}


def estado_leds():
    cores = []
    for v in vagas:
        if piscando(v):
            cores.append("piscando")
        elif v["ocupada"]:
            cores.append("vermelho")
        else:
            cores.append("verde")
    return {"leds": cores, "interditadas": interditadas,
            "emergencia": emergencia, "ack": ultimo_ack}


def publicar(cliente):
    # retain=True: o broker guarda a ultima mensagem e quem conectar depois
    # (totem, dashboard) ja recebe as vagas na hora, sem esperar a proxima.
    # QoS 0: manda e nao espera confirmacao. Se uma se perder, em 15 s vai outra.
    cliente.publish(T_SENSOR, json.dumps(resumo_vagas()).encode(), retain=True)
    cliente.publish(T_ESTADO, json.dumps(estado_leds()).encode(), retain=True)


def ao_receber(topico, msg):
    # o check_msg() chama essa funcao toda vez que chega mensagem de um topico assinado
    global emergencia, ultimo_ack, mudou_por_rede
    topico = topico.decode()
    if not msg:
        return   # mensagem vazia = alguem apagou o retido do topico
    try:
        dados = json.loads(msg)
    except ValueError:
        print("JSON invalido em", topico)
        return
    if not isinstance(dados, dict):
        return

    if topico == T_COMANDO:
        if "ping" in dados:
            ultimo_ack = dados["ping"]
        vid = dados.get("manutencao")
        if vid:
            if dados.get("ativo", True) and vid not in interditadas:
                interditadas.append(vid)
            elif not dados.get("ativo", True) and vid in interditadas:
                interditadas.remove(vid)
            print("Interditadas:", interditadas)
        mudou_por_rede = True
    elif topico == T_CPS2_ESTADO:
        nova = dados.get("modo") == "emergencia"
        if nova != emergencia:
            emergencia = nova
            print("Emergencia:", emergencia)
            mudou_por_rede = True


def conectar_wifi():
    # espera ate 10 s pelo WiFi; se nao vier da erro e o loop tenta de novo depois
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_SENHA)
        for _ in range(100):
            if wlan.isconnected():
                break
            time.sleep_ms(100)
    if not wlan.isconnected():
        raise OSError("WiFi nao conectou")
    print("WiFi conectado, IP", wlan.ifconfig()[0])


def conectar_mqtt():
    cliente = MQTTClient(CLIENT_ID, BROKER, keepalive=30)
    # Last Will: se o ESP32 cair sem avisar, o broker publica "offline" no lugar dele
    cliente.set_last_will(T_STATUS, "offline", retain=True, qos=1)
    cliente.set_callback(ao_receber)
    cliente.connect()
    cliente.publish(T_STATUS, "online", retain=True, qos=1)
    # qos=1: o broker entrega com confirmacao (pelo menos uma vez)
    cliente.subscribe(T_COMANDO, qos=1)
    cliente.subscribe(T_CPS2_ESTADO, qos=1)
    print("MQTT conectado como", CLIENT_ID)
    return cliente


def tentar_conectar():
    # tenta uma vez so, para nao travar os sensores esperando a rede
    try:
        conectar_wifi()
        return conectar_mqtt()
    except Exception as erro:
        print("Falha ao conectar:", erro)
        return None


# Programa principal
print("SmartPark 2.0 - CPS1 Vagas")
cliente = tentar_conectar()
ultima_tentativa = time.ticks_ms()
ultimo_ping = time.ticks_ms()
ultima_publicacao = None   # None = publica na proxima volta

while True:
    # Sensores e LEDs funcionam com ou sem rede
    mudou = ler_vagas()
    acender_leds()
    if mudou:
        r = resumo_vagas()
        print("Vagas livres:", r["livres"], r["livres_tipo"])

    if cliente is None:
        if time.ticks_diff(time.ticks_ms(), ultima_tentativa) > RECONECTAR_MS:
            cliente = tentar_conectar()
            ultima_tentativa = time.ticks_ms()
            ultima_publicacao = None
    else:
        try:
            for _ in range(5):
                cliente.check_msg()
            agora = time.ticks_ms()
            if (mudou or mudou_por_rede or ultima_publicacao is None
                    or time.ticks_diff(agora, ultima_publicacao) > REPUBLICAR_MS):
                publicar(cliente)
                ultima_publicacao = agora
                mudou_por_rede = False
            if time.ticks_diff(agora, ultimo_ping) > PING_MS:
                cliente.ping()
                # repete o "online" para um Last Will atrasado nao ficar valendo
                cliente.publish(T_STATUS, "online", retain=True)
                ultimo_ping = agora
        except OSError as erro:
            print("Conexao perdida:", erro)
            cliente = None
            ultima_tentativa = time.ticks_ms() - RECONECTAR_MS   # tenta de novo ja
        except Exception as erro:
            print("Erro:", erro)
    time.sleep_ms(200)
