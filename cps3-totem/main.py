# SmartPark 2.0 · CPS3 Totem contador · Projeto CSCF 2026.2 (PUCPR)
# Na entrada do estacionamento: mostra quantas vagas estão livres num display
# de 7 segmentos, um LED verde/vermelho e uma fita NeoPixel com um LED por vaga.
# Tudo vem do CPS1 pela rede. Se o CPS1 cai (Last Will), mostra "----".
# Sensores próprios: PIR (alguém chegou: brilho alto) e botão de ajuda (interfone).
#
# Reaproveitado do SmartPark 2026.1 (Old/main.py): conectar_wifi() e a ideia
# do "totem de vagas" (Old/imgs/puc-totem-vagas.jpg), agora medido vaga a vaga.

import json
import random
import time

import network
from machine import Pin
from neopixel import NeoPixel
from tm1637 import TM1637
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
PING_MS = 10000          # sinal de vida (keepalive = 30 s)

# Cores da fita (R, G, B)
VERDE = (0, 180, 0)
AMARELO = (200, 140, 0)
AZUL = (0, 60, 220)
VERMELHO = (200, 0, 0)
LARANJA = (220, 70, 0)
BRANCO = (160, 160, 160)
APAGADO = (0, 0, 0)
COR_LIVRE = {"comum": VERDE, "idoso": AMARELO, "pcd": AZUL}
NOME_COR = {VERDE: "verde", AMARELO: "amarelo", AZUL: "azul", VERMELHO: "vermelho",
            LARANJA: "laranja", BRANCO: "branco", APAGADO: "apagado"}

# ===== PINOS =====
botao_ajuda = Pin(13, Pin.IN, Pin.PULL_UP)
pir = Pin(27, Pin.IN)
display = TM1637(clk=22, dio=21)
led_verde = Pin(4, Pin.OUT)
led_vermelho = Pin(16, Pin.OUT)
led_azul = Pin(17, Pin.OUT)
fita = NeoPixel(Pin(5), 4)

# ===== ESTADO =====
vagas = None             # última mensagem do CPS1
cps1_online = False
alarmes = {}             # tipo -> ativo
emergencia = False
presenca = False
ajuda = "nenhuma"        # nenhuma -> aguardando -> atendida -> nenhuma
atendida_em = 0
brilho_forcado = None    # comando do dashboard: "alto" ou "baixo"
apertou_ajuda = False    # preenchido pela interrupção do botão
ultimo_ack = None
mudou_por_rede = False


def ao_receber(topico, msg):
    global vagas, cps1_online, emergencia, ajuda, atendida_em, brilho_forcado
    global ultimo_ack, mudou_por_rede
    topico = topico.decode()
    texto = msg.decode() if msg else ""
    if topico == T_CPS1_STATUS:
        cps1_online = texto == "online"
        mudou_por_rede = True
        return
    try:
        dados = json.loads(texto) if texto else None
    except ValueError:
        print("JSON inválido em", topico)
        return
    if not isinstance(dados, dict):
        return
    if topico == T_CPS1_SENSOR:
        vagas = dados
    elif topico == T_CPS2_ALARME:
        alarmes[dados.get("tipo")] = dados.get("ativo", False)
        print("Alarme:", dados)
    elif topico == T_CPS2_ESTADO:
        emergencia = dados.get("modo") == "emergencia"
        # o estado é retido: corrige o alarme mesmo se a mensagem de fim do alarme se perdeu
        alarmes["cancela_travada"] = dados.get("travada", False)
        alarmes["evasao"] = dados.get("evasao", 0) > 0
    elif topico == T_COMANDO:
        if "ping" in dados:
            ultimo_ack = dados["ping"]
        if dados.get("ajuda") == "atendido" and ajuda == "aguardando":
            ajuda = "atendida"
            atendida_em = time.ticks_ms()
        if dados.get("brilho") in ("alto", "baixo", "auto"):
            brilho_forcado = None if dados["brilho"] == "auto" else dados["brilho"]
    mudou_por_rede = True


def calcular_saida():
    """Decide o que o totem mostra a partir do que chegou pela rede.
    Retorna as cores firmes; quem pisca é decidido em aplicar()."""
    alarme = any(alarmes.values())
    confiavel = cps1_online and vagas is not None
    fita_pisca = False

    if not confiavel:
        numero = None
        led = "vermelho"
        cores = [LARANJA] * 4
        fita_pisca = True
    else:
        numero = vagas.get("livres", 0)
        # verde só se ainda cabe carro comum (é o que a cancela usa para negar)
        led = "verde" if vagas.get("livres_comuns", 0) > 0 else "vermelho"
        cores = []
        for v in vagas.get("vagas", []):
            if v.get("interditada"):
                cores.append(LARANJA)
            elif v.get("ocupada"):
                cores.append(VERMELHO)
            else:
                cores.append(COR_LIVRE.get(v.get("tipo"), VERDE))
    if emergencia:
        cores = [BRANCO] * 4
        fita_pisca = True
    if alarme:
        led = "vermelho_piscando"
    return numero, led, cores, fita_pisca


def aplicar(led, cores, fita_pisca, brilho_alto):
    pisca = (time.ticks_ms() // 400) % 2 == 0
    led_verde.value(1 if led == "verde" else 0)
    led_vermelho.value(1 if led == "vermelho" or (led == "vermelho_piscando" and pisca) else 0)
    led_azul.value(1 if ajuda == "atendida" or (ajuda == "aguardando" and pisca) else 0)
    escala = 1.0 if brilho_alto else 0.25
    for i in range(4):
        r, g, b = cores[i] if i < len(cores) and (pisca or not fita_pisca) else APAGADO
        fita[i] = (int(r * escala), int(g * escala), int(b * escala))
    fita.write()


def mostrar_numero(numero, brilho_alto):
    display.brilho = 7 if brilho_alto else 2
    if numero is None:
        display.tracos()
    else:
        display.numero(numero)


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
    cliente.set_last_will(T_STATUS, "offline", retain=True, qos=1)
    cliente.set_callback(ao_receber)
    cliente.connect()
    cliente.publish(T_STATUS, "online", retain=True, qos=1)
    for t in (T_COMANDO, T_CPS1_SENSOR, T_CPS1_STATUS, T_CPS2_ALARME, T_CPS2_ESTADO):
        cliente.subscribe(t, qos=1)
    print("MQTT conectado como", CLIENT_ID)
    return cliente


def conectar():
    while True:
        try:
            conectar_wifi()
            return conectar_mqtt()
        except Exception as erro:   # OSError (rede) ou MQTTException (broker recusou)
            print("Falha de conexão:", erro, "- tentando de novo em 2 s")
            time.sleep(2)


def ao_apertar_ajuda(pino):
    global apertou_ajuda
    apertou_ajuda = True


botao_ajuda.irq(trigger=Pin.IRQ_FALLING, handler=ao_apertar_ajuda)


# ===== PROGRAMA PRINCIPAL =====
print("SmartPark 2.0 · CPS3 Totem")
display.tracos()
cliente = conectar()
mostrado = "inicio"
publicado = None
ultimo_ping = time.ticks_ms()

while True:
    try:
        for _ in range(5):
            cliente.check_msg()

        # Sensores próprios
        agora_presenca = pir.value() == 1
        if agora_presenca != presenca:
            presenca = agora_presenca
            cliente.publish(T_SENSOR, json.dumps({"presenca": presenca}).encode())
        if apertou_ajuda:
            apertou_ajuda = False
            if ajuda != "aguardando":
                ajuda = "aguardando"
                cliente.publish(T_SENSOR, json.dumps({"ajuda": True}).encode(), qos=1)
                print("Pedido de ajuda enviado")
        if ajuda == "atendida" and time.ticks_diff(time.ticks_ms(), atendida_em) > ATENDIDO_MS:
            ajuda = "nenhuma"

        # Atuadores
        brilho_alto = brilho_forcado == "alto" or (brilho_forcado is None and presenca)
        numero, led, cores, fita_pisca = calcular_saida()
        aplicar(led, cores, fita_pisca, brilho_alto)
        chave = (numero, brilho_alto)
        if chave != mostrado:       # o display só é reescrito quando muda
            mostrar_numero(numero, brilho_alto)
            mostrado = chave

        # Realimentação: publica o que o totem está mostrando (sem as piscadas)
        estado = {"display": "----" if numero is None else numero, "led": led,
                  "fita": [NOME_COR.get(c, "?") for c in cores], "fita_pisca": fita_pisca,
                  "ajuda": ajuda, "brilho": "alto" if brilho_alto else "baixo",
                  "presenca": presenca, "ack": ultimo_ack}
        texto = json.dumps(estado)
        if texto != publicado:
            cliente.publish(T_ESTADO, texto.encode(), retain=True)   # QoS 0: não trava o loop
            publicado = texto
        mudou_por_rede = False

        if time.ticks_diff(time.ticks_ms(), ultimo_ping) > PING_MS:
            cliente.ping()
            cliente.publish(T_STATUS, "online", retain=True)   # reafirma: um Last Will atrasado não fica valendo
            ultimo_ping = time.ticks_ms()
        time.sleep_ms(100)
    except OSError as erro:
        print("Conexão perdida:", erro)
        cliente = conectar()
        publicado = None
    except Exception as erro:
        print("Erro ignorado:", erro)
