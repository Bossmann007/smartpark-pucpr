# Grupo 1: Enzo Bossmann, Gabriel Henrique, Diego Feltrin, Daniel Luiz, Luis Henrique
# Problema: Monitoramento de vagas de estacionamento (Sistema Ciberfisico)
# Disciplina: Fundamentos de Sistemas Ciberfisicos — PUCPR
# Placa: ESP32 + 2x HC-SR04 + 4 LEDs + buzzer | Comunicacao: MQTT
#
# Logica: cada vaga tem um sensor de distancia. Se um carro fica
# perto do sensor (distancia abaixo do limiar), a vaga esta OCUPADA
# (LED vermelho). Se nao, esta LIVRE (LED verde). Se as duas vagas
# ficam ocupadas, o buzzer apita (estacionamento lotado).

from machine import Pin, PWM, time_pulse_us
from utime import sleep, sleep_us
from network import WLAN, STA_IF
from ujson import dumps

print("Hello, ESP32 — SmartPark!")

# umqtt pode nao existir no simulador; se faltar, roda em modo offline
try:
    from umqtt.simple import MQTTClient
    MQTT_DISPONIVEL = True
except ImportError:
    MQTT_DISPONIVEL = False
    print("Sem biblioteca umqtt — rodando em modo offline")


# ===== CONFIGURACOES =====
# No simulador Wokwi a unica rede e a "Wokwi-GUEST" (senha vazia).
# Para a placa real, troque pelos dados da rede do estacionamento.
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASS = ""

MQTT_BROKER = "broker.hivemq.com"   # broker publico para teste
MQTT_PORT   = 1883
CLIENT_ID   = "esp32-smartpark"

# Topicos MQTT — os mesmos que o dashboard Processing (PegadaCampus) assina.
# Convencao do payload: "0" = vaga LIVRE, "1" = vaga OCUPADA.
TOPICO_VAGA1  = "smartpark/puc/vaga1"
TOPICO_VAGA2  = "smartpark/puc/vaga2"
TOPICO_STATUS = "smartpark/puc/status"

# Distancia em cm abaixo da qual a vaga e considerada ocupada
LIMIAR_CM = 20

# ===== PINOS =====
# Sensores HC-SR04 (TRIG = saida que dispara, ECHO = entrada que mede)
TRIG1 = Pin(5,  Pin.OUT)
ECHO1 = Pin(18, Pin.IN)
TRIG2 = Pin(19, Pin.OUT)
ECHO2 = Pin(21, Pin.IN)

# LEDs — verde = vaga livre, vermelho = vaga ocupada
LED_V1 = Pin(2,  Pin.OUT)   # verde vaga 1
LED_R1 = Pin(4,  Pin.OUT)   # vermelho vaga 1
LED_V2 = Pin(22, Pin.OUT)   # verde vaga 2
LED_R2 = Pin(23, Pin.OUT)   # vermelho vaga 2

# Buzzer passivo no pino 25 via PWM. O som so existe quando o duty e
# maior que zero; com duty(0) o buzzer fica em silencio total. Esse e
# o padrao que o Wokwi reconhece para ligar/desligar o buzzer.
buzzer = PWM(Pin(25))
buzzer.freq(1000)
buzzer.duty(0)   # comeca em silencio

# Estado inicial: as duas vagas comecam LIVRES (verde ligado).
# Isso evita LEDs em estado indefinido enquanto a placa liga.
LED_V1.on()
LED_R1.off()
LED_V2.on()
LED_R2.off()
print("LEDs inicializados — vagas livres")


# ===== FUNCOES =====

def medir_distancia(trig, echo):
    """Dispara um pulso ultrassonico e retorna a distancia em cm.
    Retorna 999 se nao houver eco (timeout)."""
    trig.off()
    sleep_us(2)
    trig.on()
    sleep_us(10)
    trig.off()
    duracao = time_pulse_us(echo, 1, 30000)
    if duracao < 0:
        return 999.0
    # velocidade do som = 0.0343 cm/us; divide por 2 (ida e volta)
    return (duracao * 0.0343) / 2.0


def atualizar_led(ocupada, verde, vermelho):
    """Acende vermelho se a vaga esta ocupada, senao acende verde."""
    if ocupada:
        verde.off()
        vermelho.on()
    else:
        verde.on()
        vermelho.off()


def apitar():
    """Toca o buzzer por exatamente 1 segundo e depois silencia.
    Usado so no momento em que o estacionamento fica lotado."""
    buzzer.duty(512)   # liga o som
    sleep(1)           # toca por 1 segundo
    buzzer.duty(0)     # desliga o som


def conectar_wifi():
    """Tenta conectar no WiFi por ate 10 segundos. Retorna True se conectou."""
    wlan = WLAN(STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    for tentativa in range(20):
        if wlan.isconnected():
            print(f"WiFi conectado — IP {wlan.ifconfig()[0]}")
            return True
        sleep(0.5)
    print("WiFi nao conectou — modo offline")
    return False


def conectar_mqtt():
    """Tenta criar e conectar o cliente MQTT. Retorna o cliente ou None."""
    if not MQTT_DISPONIVEL:
        return None
    try:
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, MQTT_PORT)
        client.connect()
        print("MQTT conectado")
        return client
    except Exception as erro:
        print(f"Erro ao conectar MQTT: {erro}")
        return None


# ===== PROGRAMA PRINCIPAL =====

def main():
    wifi_ok = conectar_wifi()
    client = None
    if wifi_ok:
        client = conectar_mqtt()

    # Guarda o estado anterior de cada vaga para so publicar quando mudar
    ant1 = None
    ant2 = None
    lotado_ant = False   # estado anterior de "lotado" (para apitar so na mudanca)

    while True:
        # Le os dois sensores e decide se cada vaga esta ocupada
        d1 = medir_distancia(TRIG1, ECHO1)
        d2 = medir_distancia(TRIG2, ECHO2)
        ocup1 = d1 < LIMIAR_CM
        ocup2 = d2 < LIMIAR_CM

        # Atualiza os LEDs das duas vagas
        atualizar_led(ocup1, LED_V1, LED_R1)
        atualizar_led(ocup2, LED_V2, LED_R2)

        # Buzzer: apita 1 segundo SO no momento em que as duas vagas enchem
        lotado = ocup1 and ocup2
        if lotado and not lotado_ant:
            apitar()
        lotado_ant = lotado

        # So publica/imprime quando o estado de alguma vaga muda
        if ocup1 != ant1 or ocup2 != ant2:
            v1 = "1" if ocup1 else "0"   # 1 = ocupada, 0 = livre
            v2 = "1" if ocup2 else "0"
            status = dumps({"v1": int(ocup1), "v2": int(ocup2)})
            print(f"Vagas -> v1={v1}  v2={v2}  status={status}")
            if client:
                try:
                    client.publish(TOPICO_VAGA1, v1.encode())
                    client.publish(TOPICO_VAGA2, v2.encode())
                    client.publish(TOPICO_STATUS, status.encode())
                except Exception as erro:
                    print(f"Erro ao publicar: {erro}")
                    client = None   # desiste do MQTT e segue offline

        ant1 = ocup1
        ant2 = ocup2
        sleep(1)


main()
