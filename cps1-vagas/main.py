# SmartPark 2.0 · CPS1 Vagas · Projeto CSCF 2026.2 (PUCPR)
# Mede cada vaga com um HC-SR04 e acende o LED verde (livre) ou vermelho (ocupada).
# Publica as vagas no broker; o CPS2 (cancela) e o CPS3 (totem) usam esse dado.
#
# Reaproveitado do SmartPark 2026.1 (Old/main.py): medir_distancia(),
# atualizar_led() e conectar_wifi(). O resto é novo: 4 vagas com tipo,
# assinatura de comandos, Last Will, retain e reconexão.

import json
import random
import time

import network
from machine import Pin, time_pulse_us
from umqtt.simple import MQTTClient

# ===== CONFIGURAÇÃO =====
WIFI_SSID = "Wokwi-GUEST"
WIFI_SENHA = ""
BROKER = "broker.hivemq.com"
PREFIXO = "cscf/smartpark"   # troque "smartpark" pelo id da equipe
try:
    from sim_config import BROKER, PREFIXO  # só no teste local (sim/); não existe no Wokwi
except ImportError:
    pass

# Todo ESP32 do Wokwi tem o mesmo MAC, então o id leva um número aleatório.
# Dois clientes com o mesmo id derrubam um ao outro no broker.
CLIENT_ID = "smartpark-cps1-%04x" % (random.getrandbits(16) ^ (time.ticks_us() & 0xFFFF))

T_SENSOR = PREFIXO + "/cps1/sensor"
T_ESTADO = PREFIXO + "/cps1/estado"
T_COMANDO = PREFIXO + "/cps1/comando"
T_STATUS = PREFIXO + "/cps1/status"
T_CPS2_ESTADO = PREFIXO + "/cps2/estado"

LIMIAR_OCUPADA_CM = 50   # abaixo disso tem carro
LIMIAR_LIVRE_CM = 60     # acima disso a vaga liberou (histerese evita piscar na borda)
PING_MS = 10000          # sinal de vida para o broker (keepalive = 30 s)
REPUBLICAR_MS = 15000    # republica as vagas mesmo sem mudança
RECONECTAR_MS = 5000     # sem rede: nova tentativa a cada 5 s, sem parar os sensores

# ===== PINOS =====
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

# ===== ESTADO =====
interditadas = []      # vagas que o operador tirou de uso
emergencia = False     # vem do CPS2
ultimo_ack = None


# ===== SENSOR E LEDS (reaproveitado de Old/main.py) =====
def medir_distancia(trig, echo):
    """Dispara um pulso ultrassônico e retorna a distância em cm (999 sem eco)."""
    trig.off()
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()
    duracao = time_pulse_us(echo, 1, 30000)
    if duracao < 0:
        return 999
    # velocidade do som = 0,0343 cm/us; divide por 2 (ida e volta)
    return duracao * 0.0343 / 2


def atualizar_led(ocupada, verde, vermelho):
    """Vermelho se a vaga está ocupada, senão verde."""
    verde.value(0 if ocupada else 1)
    vermelho.value(1 if ocupada else 0)


def ler_vagas():
    """Lê os 4 sensores. Retorna True se alguma vaga mudou."""
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


def acender_leds():
    """Interditada ou emergência: LEDs piscam. Normal: verde ou vermelho."""
    pisca = (time.ticks_ms() // 500) % 2 == 0
    for v in vagas:
        if emergencia or v["id"] in interditadas:
            v["verde"].value(0)
            v["vermelho"].value(1 if pisca else 0)
        else:
            atualizar_led(v["ocupada"], v["verde"], v["vermelho"])


# ===== MENSAGENS =====
def resumo_vagas():
    livres_tipo = {"comum": 0, "idoso": 0, "pcd": 0}
    lista = []
    for v in vagas:
        interditada = v["id"] in interditadas
        lista.append({"id": v["id"], "tipo": v["tipo"], "ocupada": v["ocupada"],
                      "interditada": interditada, "cm": v["cm"]})
        if not v["ocupada"] and not interditada:
            livres_tipo[v["tipo"]] += 1
    livres = livres_tipo["comum"] + livres_tipo["idoso"] + livres_tipo["pcd"]
    return {"vagas": lista, "livres": livres, "livres_comuns": livres_tipo["comum"],
            "livres_tipo": livres_tipo, "total": len(vagas)}


def estado_atual():
    cores = []
    for v in vagas:
        if emergencia or v["id"] in interditadas:
            cores.append("piscando")
        else:
            cores.append("vermelho" if v["ocupada"] else "verde")
    return {"leds": cores, "interditadas": interditadas,
            "emergencia": emergencia, "ack": ultimo_ack}


def publicar(cliente):
    cliente.publish(T_SENSOR, json.dumps(resumo_vagas()).encode(), retain=True)
    cliente.publish(T_ESTADO, json.dumps(estado_atual()).encode(), retain=True)


def ao_receber(topico, msg):
    """Callback do MQTT: roda dentro do check_msg()."""
    global emergencia, ultimo_ack, mudou_por_rede
    topico = topico.decode()
    try:
        dados = json.loads(msg)
    except ValueError:
        print("JSON inválido em", topico)
        return
    if not isinstance(dados, dict):
        return
    if topico == T_COMANDO:
        if "ping" in dados:
            ultimo_ack = dados["ping"]
        if "manutencao" in dados:
            vid = dados["manutencao"]
            if dados.get("ativo", True):
                if vid not in interditadas:
                    interditadas.append(vid)
            elif vid in interditadas:
                interditadas.remove(vid)
            print("Vagas interditadas:", interditadas)
        mudou_por_rede = True
    elif topico == T_CPS2_ESTADO:
        novo = dados.get("modo") == "emergencia"
        if novo != emergencia:
            emergencia = novo
            print("Emergência:", emergencia)
            mudou_por_rede = True


# ===== CONEXÃO (conectar_wifi reaproveitado de Old/main.py) =====
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_SENHA)
        for _ in range(100):
            if wlan.isconnected():
                break
            time.sleep_ms(100)
    if not wlan.isconnected():
        raise OSError("Wi-Fi não conectou")
    print("Wi-Fi conectado, IP", wlan.ifconfig()[0])


def conectar_mqtt():
    cliente = MQTTClient(CLIENT_ID, BROKER, keepalive=30)
    # Last Will: se este ESP32 cair sem avisar, o broker publica "offline" por ele.
    cliente.set_last_will(T_STATUS, "offline", retain=True, qos=1)
    cliente.set_callback(ao_receber)
    cliente.connect()
    cliente.publish(T_STATUS, "online", retain=True, qos=1)
    cliente.subscribe(T_COMANDO, qos=1)
    cliente.subscribe(T_CPS2_ESTADO, qos=1)
    print("MQTT conectado como", CLIENT_ID)
    return cliente


def tentar_conectar():
    """Uma tentativa só. Sem rede, o ESP32 segue com as regras locais e tenta de novo depois."""
    try:
        conectar_wifi()
        return conectar_mqtt()
    except Exception as erro:   # OSError (rede) ou MQTTException (broker recusou)
        print("Falha de conexão:", erro, "- seguindo offline")
        return None


# ===== PROGRAMA PRINCIPAL =====
print("SmartPark 2.0 · CPS1 Vagas")
cliente = tentar_conectar()
proxima_tentativa = time.ticks_add(time.ticks_ms(), RECONECTAR_MS)
mudou_por_rede = False
ultimo_ping = time.ticks_ms()
ultima_publicacao = time.ticks_add(time.ticks_ms(), -REPUBLICAR_MS - 1)   # publica na 1ª volta

while True:
    # Parte local: sensores e LEDs funcionam com ou sem rede.
    mudou = ler_vagas()
    acender_leds()
    agora = time.ticks_ms()
    if mudou:
        r = resumo_vagas()
        print("Vagas livres:", r["livres"], r["livres_tipo"])

    # Parte de rede: se caiu, tenta de novo a cada RECONECTAR_MS sem travar a parte local.
    if cliente is None:
        if time.ticks_diff(agora, proxima_tentativa) >= 0:
            cliente = tentar_conectar()
            proxima_tentativa = time.ticks_add(time.ticks_ms(), RECONECTAR_MS)
            ultima_publicacao = time.ticks_add(time.ticks_ms(), -REPUBLICAR_MS - 1)
    else:
        try:
            for _ in range(5):
                cliente.check_msg()
            if mudou or mudou_por_rede or time.ticks_diff(agora, ultima_publicacao) > REPUBLICAR_MS:
                publicar(cliente)
                ultima_publicacao = agora
                mudou_por_rede = False
            if time.ticks_diff(agora, ultimo_ping) > PING_MS:
                cliente.ping()
                cliente.publish(T_STATUS, "online", retain=True)   # reafirma: um Last Will atrasado não fica valendo
                ultimo_ping = agora
        except OSError as erro:
            print("Conexão perdida:", erro, "- seguindo offline")
            cliente = None
            proxima_tentativa = agora
        except Exception as erro:
            print("Erro ignorado:", erro)
    time.sleep_ms(200)
