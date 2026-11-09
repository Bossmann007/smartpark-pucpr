# Equipe 3: Enzo Bossmann, Diego Feltrin e Gabriel Henrique
# Projeto: SmartPark 2.0 - CPS3 Totem contador
# Disciplina: Conectividade em Sistemas Ciberfisicos - PUCPR 2026.2
# Placa: ESP32 + display TM1637 + 3 LEDs + fita NeoPixel (4) + PIR + botao | Comunicacao: MQTT
#
# Logica: totem na entrada do estacionamento. Mostra quantas vagas estao
# livres no display, LED verde/vermelho e um LED da fita para cada vaga.
# Tudo vem do CPS1 pela rede. Se o CPS1 cair (Last Will) mostra "----".
# Se o CPS2 avisar vaga PcD irregular, so o LED daquela vaga pisca.
# Sensores proprios: PIR (chegou alguem = brilho alto) e botao de ajuda.
#
# Do SmartPark do semestre passado (Old/main.py) veio conectar_wifi() e a
# ideia do totem de vagas (Old/imgs/puc-totem-vagas.jpg), agora vaga a vaga.
#
# Publica:  cps3/sensor (presenca, ajuda), cps3/estado, cps3/status
# Assina:   cps1/sensor, cps1/status, cps2/alarme, cps2/estado, cps3/comando

import json
import random
import time

import network
from machine import Pin
from neopixel import NeoPixel
from tm1637 import TM1637
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

# id com numero aleatorio porque no Wokwi todo ESP32 tem o mesmo MAC
CLIENT_ID = "smartpark-cps3-%04x" % (random.getrandbits(16) ^ (time.ticks_us() & 0xFFFF))

T_SENSOR = PREFIXO + "/cps3/sensor"
T_ESTADO = PREFIXO + "/cps3/estado"
T_COMANDO = PREFIXO + "/cps3/comando"
T_STATUS = PREFIXO + "/cps3/status"
T_CPS1_SENSOR = PREFIXO + "/cps1/sensor"
T_CPS1_STATUS = PREFIXO + "/cps1/status"
T_CPS2_ALARME = PREFIXO + "/cps2/alarme"
T_CPS2_ESTADO = PREFIXO + "/cps2/estado"

ATENDIDO_MS = 10000      # LED azul fica aceso esse tempo depois do atendimento
PING_MS = 10000          # avisa o broker que esta vivo (keepalive de 30 s)
RECONECTAR_MS = 5000     # sem rede, tenta de novo a cada 5 s

# Cores da fita (R, G, B). O totem guarda o nome da cor e so converte na hora de acender.
CORES = {
    "verde": (0, 180, 0),       # vaga comum livre
    "amarelo": (200, 140, 0),   # vaga de idoso livre
    "azul": (0, 60, 220),       # vaga PcD livre
    "vermelho": (200, 0, 0),    # ocupada
    "laranja": (220, 70, 0),    # interditada ou CPS1 fora do ar
    "branco": (160, 160, 160),  # emergencia
    "apagado": (0, 0, 0),
}
COR_LIVRE = {"comum": "verde", "idoso": "amarelo", "pcd": "azul"}

# Pinos
botao_ajuda = Pin(13, Pin.IN, Pin.PULL_UP)
pir = Pin(27, Pin.IN)
display = TM1637(clk=22, dio=21)
led_verde = Pin(4, Pin.OUT)
led_vermelho = Pin(16, Pin.OUT)
led_azul = Pin(17, Pin.OUT)
fita = NeoPixel(Pin(5), 4)

# Estado
vagas = None             # ultima mensagem do CPS1
cps1_online = False
alarmes = {}             # tipo do alarme -> ativo
irregular = ""           # vaga PcD ocupada sem credencial (vem do CPS2)
emergencia = False
presenca = False
ajuda = "nenhuma"        # nenhuma -> aguardando -> atendida -> nenhuma
atendida_em = 0
brilho_forcado = None    # comando do dashboard: "alto", "baixo" ou None (automatico)
apertou_ajuda = False    # a interrupcao do botao marca aqui
ultimo_ack = None


def ao_receber(topico, msg):
    # o check_msg() chama essa funcao toda vez que chega mensagem de um topico assinado
    global vagas, cps1_online, emergencia, ajuda, atendida_em, brilho_forcado, ultimo_ack, irregular
    topico = topico.decode()
    if topico == T_CPS1_STATUS:
        cps1_online = msg == b"online"
        return
    if not msg:
        return   # mensagem vazia = alguem apagou o retido do topico
    try:
        dados = json.loads(msg)
    except ValueError:
        print("JSON invalido em", topico)
        return
    if not isinstance(dados, dict):
        return

    if topico == T_CPS1_SENSOR:
        vagas = dados
    elif topico == T_CPS2_ALARME:
        alarmes[dados.get("tipo")] = dados.get("ativo", False)
        if dados.get("tipo") == "vaga_irregular":
            irregular = dados.get("vaga", "")
        print("Alarme:", dados)
    elif topico == T_CPS2_ESTADO:
        emergencia = dados.get("modo") == "emergencia"
        # o estado e retido, entao corrige o alarme mesmo se o aviso de fim se perdeu
        alarmes["cancela_travada"] = dados.get("travada", False)
        alarmes["evasao"] = dados.get("evasao", 0) > 0
        irregular = dados.get("vaga_irregular", "")
        alarmes["vaga_irregular"] = irregular != ""
    elif topico == T_COMANDO:
        if "ping" in dados:
            ultimo_ack = dados["ping"]
        if dados.get("ajuda") == "atendido" and ajuda == "aguardando":
            ajuda = "atendida"
            atendida_em = time.ticks_ms()
        if dados.get("brilho") in ("alto", "baixo"):
            brilho_forcado = dados["brilho"]
        elif dados.get("brilho") == "auto":
            brilho_forcado = None


def calcular_saida():
    # decide o numero, o LED e as cores da fita com o que chegou pela rede.
    pisca_vaga = None   # posicao da vaga PcD irregular na fita (so ela pisca)
    if not cps1_online or vagas is None:
        # sem CPS1 o numero nao e confiavel
        numero = None
        led = "vermelho"
        cores = ["laranja"] * 4
        fita_pisca = True
    else:
        numero = vagas.get("livres", 0)
        # verde so se ainda cabe carro comum (e o que a cancela usa para negar)
        led = "verde" if vagas.get("livres_comuns", 0) > 0 else "vermelho"
        fita_pisca = False
        cores = []
        for i, v in enumerate(vagas.get("vagas", [])):
            if v.get("id") == irregular:
                pisca_vaga = i
            if v.get("interditada"):
                cores.append("laranja")
            elif v.get("ocupada"):
                cores.append("vermelho")
            else:
                cores.append(COR_LIVRE.get(v.get("tipo"), "verde"))
    if emergencia:
        cores = ["branco"] * 4
        fita_pisca = True
    if True in alarmes.values():
        led = "vermelho_piscando"
    return numero, led, cores, fita_pisca, pisca_vaga


def acender(led, cores, fita_pisca, pisca_vaga, brilho_alto):
    pisca = (time.ticks_ms() // 400) % 2 == 0
    led_verde.value(led == "verde")
    led_vermelho.value(led == "vermelho" or (led == "vermelho_piscando" and pisca))
    led_azul.value(ajuda == "atendida" or (ajuda == "aguardando" and pisca))
    escala = 1.0 if brilho_alto else 0.25
    for i in range(4):
        nome = "apagado"
        apaga = fita_pisca or i == pisca_vaga
        if i < len(cores) and (pisca or not apaga):
            nome = cores[i]
        r, g, b = CORES[nome]
        fita[i] = (int(r * escala), int(g * escala), int(b * escala))
    fita.write()


def mostrar_numero(numero, brilho_alto):
    display.brilho = 7 if brilho_alto else 2
    if numero is None:
        display.tracos()
    else:
        display.numero(numero)


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
    cliente.set_last_will(T_STATUS, "offline", retain=True, qos=1)
    cliente.set_callback(ao_receber)
    cliente.connect()
    cliente.publish(T_STATUS, "online", retain=True, qos=1)
    for t in (T_COMANDO, T_CPS1_SENSOR, T_CPS1_STATUS, T_CPS2_ALARME, T_CPS2_ESTADO):
        cliente.subscribe(t, qos=1)
    print("MQTT conectado como", CLIENT_ID)
    return cliente


def tentar_conectar():
    # tenta uma vez so, para o totem nao parar esperando a rede
    try:
        conectar_wifi()
        return conectar_mqtt()
    except Exception as erro:
        print("Falha ao conectar:", erro)
        return None


def ajuda_apertada(pino):
    global apertou_ajuda
    apertou_ajuda = True


botao_ajuda.irq(trigger=Pin.IRQ_FALLING, handler=ajuda_apertada)


# Programa principal
print("SmartPark 2.0 - CPS3 Totem")
display.tracos()
cliente = tentar_conectar()
ultima_tentativa = time.ticks_ms()
ultimo_ping = time.ticks_ms()
mostrado = None
publicado = None
avisar = []   # avisos dos sensores esperando a rede voltar

while True:
    try:
        # Sensores proprios (funcionam com ou sem rede)
        if (pir.value() == 1) != presenca:
            presenca = not presenca
            avisar.append(({"presenca": presenca}, 0))
        if apertou_ajuda:
            apertou_ajuda = False
            if ajuda != "aguardando":
                ajuda = "aguardando"
                avisar.append(({"ajuda": True}, 1))
                print("Pedido de ajuda")
        if ajuda == "atendida" and time.ticks_diff(time.ticks_ms(), atendida_em) > ATENDIDO_MS:
            ajuda = "nenhuma"

        # Sem conexao propria o numero tambem nao e confiavel
        if cliente is None:
            cps1_online = False

        brilho_alto = brilho_forcado == "alto" or (brilho_forcado is None and presenca)
        numero, led, cores, fita_pisca, pisca_vaga = calcular_saida()
        acender(led, cores, fita_pisca, pisca_vaga, brilho_alto)
        if (numero, brilho_alto) != mostrado:   # so reescreve o display quando muda
            mostrar_numero(numero, brilho_alto)
            mostrado = (numero, brilho_alto)

        # Parte de rede
        if cliente is None:
            if time.ticks_diff(time.ticks_ms(), ultima_tentativa) > RECONECTAR_MS:
                cliente = tentar_conectar()   # os retidos trazem vagas e status de volta
                ultima_tentativa = time.ticks_ms()
                publicado = None
        else:
            for _ in range(5):
                cliente.check_msg()
            while avisar:
                dados, qos = avisar[0]
                cliente.publish(T_SENSOR, json.dumps(dados).encode(), qos=qos)
                avisar.pop(0)
            # publica o que o totem esta mostrando
            estado = {"display": "----" if numero is None else numero, "led": led,
                      "fita": cores, "fita_pisca": fita_pisca, "pisca_vaga": pisca_vaga,
                      "ajuda": ajuda, "brilho": "alto" if brilho_alto else "baixo",
                      "brilho_forcado": brilho_forcado or "auto",
                      "presenca": presenca, "ack": ultimo_ack}
            texto = json.dumps(estado)
            if texto != publicado:
                cliente.publish(T_ESTADO, texto.encode(), retain=True)
                publicado = texto
            if time.ticks_diff(time.ticks_ms(), ultimo_ping) > PING_MS:
                cliente.ping()
                cliente.publish(T_STATUS, "online", retain=True)
                ultimo_ping = time.ticks_ms()
    except OSError as erro:
        print("Conexao perdida:", erro)
        cliente = None
        ultima_tentativa = time.ticks_ms() - RECONECTAR_MS
    except Exception as erro:
        print("Erro:", erro)
    time.sleep_ms(100)
