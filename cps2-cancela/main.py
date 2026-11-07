# SmartPark 2.0 · CPS2 Cancela · Projeto CSCF 2026.2 (PUCPR)
# Módulo acoplado à cancela que já existe; serve entrada e saída.
# Um HC-SR04 vê o carro parado, a "câmera" lê a placa e o ESP32 decide:
# abre o servo ou nega com o buzzer. Usa as vagas do CPS1 para saber se lotou
# e para achar evasão (mais carros nas vagas do que entraram pela cancela).
# Um fim de curso confirma se a cancela fechou; se não fechou, alarme.
#
# Reaproveitado do SmartPark 2026.1 (Old/main.py): medir_distancia(),
# conectar_wifi() e o buzzer em PWM. O resto é novo.

import json
import random
import time

import network
from machine import PWM, Pin, time_pulse_us
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

CLIENT_ID = "smartpark-cps2-%04x" % (random.getrandbits(16) ^ (time.ticks_us() & 0xFFFF))

T_SENSOR = PREFIXO + "/cps2/sensor"
T_ESTADO = PREFIXO + "/cps2/estado"
T_ALARME = PREFIXO + "/cps2/alarme"
T_COMANDO = PREFIXO + "/cps2/comando"
T_STATUS = PREFIXO + "/cps2/status"
T_PAGAMENTO = PREFIXO + "/pagamento"
T_CPS1_SENSOR = PREFIXO + "/cps1/sensor"

CARRO_CM = 30            # carro parado na cancela abaixo disso
TEMPO_ABERTA_MS = 5000   # a cancela fecha sozinha depois disso
TEMPO_TRAVADA_MS = 3000  # mandou fechar e o fim de curso não confirmou: alarme
TARIFA = 5.00            # débito automático da placa cadastrada
PING_MS = 10000          # sinal de vida (keepalive = 30 s)
RECONECTAR_MS = 5000     # sem rede: nova tentativa a cada 5 s, sem parar a cancela

# Placas de teste (fictícias). Na operação real, o cadastro fica num servidor.
CADASTRO = {
    "ABC1D23": {"tipo": "comum", "saldo": 50.0},
    "BRA2E19": {"tipo": "idoso", "saldo": 50.0},
    "PUC0R26": {"tipo": "pcd", "saldo": 50.0},
}

# ===== PINOS =====
trig = Pin(5, Pin.OUT)
echo = Pin(18, Pin.IN)
# Câmera simulada: cada botão é a câmera lendo uma placa cadastrada.
botoes = [
    (Pin(13, Pin.IN, Pin.PULL_UP), "ABC1D23"),
    (Pin(14, Pin.IN, Pin.PULL_UP), "BRA2E19"),
    (Pin(27, Pin.IN, Pin.PULL_UP), "PUC0R26"),
]
chave_sentido = Pin(26, Pin.IN, Pin.PULL_UP)    # esquerda (GND) = entrada, direita = saída
fim_de_curso = Pin(25, Pin.IN, Pin.PULL_UP)     # esquerda (GND) = fechada, direita = aberta
servo = PWM(Pin(4), freq=50, duty_u16=1638)      # 1638 ≈ 0,5 ms = 0° (fechada)
buzzer = PWM(Pin(23), freq=1000, duty_u16=0)     # duty 0 = silêncio (padrão do Old/main.py)

SERVO_FECHADA = 1638
SERVO_ABERTA = 4915      # ≈ 1,5 ms = 90°

# ===== ESTADO =====
dentro = {}              # placa -> {"tipo", "avulso", "pago"}
vagas_cps1 = None        # última mensagem do CPS1 (None = ainda não chegou)
modo = "normal"          # ou "emergencia"
cancela = "fechada"
aberta_em = 0
mandou_fechar_em = time.ticks_ms()   # começa fechada: o fim de curso precisa confirmar
travada = False
evasao = 0
buzzer_ate = 0
restaurado = False       # já relemos o próprio estado retido depois de reiniciar?
ultimo_ack = None
mudou_por_rede = False
lidas = []               # placas lidas pela câmera, preenchido pela interrupção dos botões

# Interrupção na descida (apertou): não perde clique curto mesmo com o loop ocupado com a rede.
for _botao, _placa in botoes:
    _botao.irq(trigger=Pin.IRQ_FALLING, handler=lambda p, placa=_placa: lidas.append(placa))


# ===== SENSOR, SERVO E BUZZER =====
def medir_distancia(trig, echo):
    """Reaproveitado de Old/main.py: distância em cm (999 sem eco)."""
    trig.off()
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()
    duracao = time_pulse_us(echo, 1, 30000)
    if duracao < 0:
        return 999
    return duracao * 0.0343 / 2


def apitar(ms):
    """Liga o buzzer sem travar o loop; desliga em atualizar_buzzer()."""
    global buzzer_ate
    buzzer.duty_u16(32768)
    buzzer_ate = time.ticks_add(time.ticks_ms(), ms)


def atualizar_buzzer():
    if buzzer.duty_u16() and time.ticks_diff(time.ticks_ms(), buzzer_ate) > 0:
        buzzer.duty_u16(0)


def abrir_cancela():
    global cancela, aberta_em, mandou_fechar_em
    servo.duty_u16(SERVO_ABERTA)
    cancela = "aberta"
    aberta_em = time.ticks_ms()
    mandou_fechar_em = None


def fechar_cancela():
    global cancela, mandou_fechar_em
    servo.duty_u16(SERVO_FECHADA)
    cancela = "fechada"
    mandou_fechar_em = time.ticks_ms()


# ===== REGRAS =====
def tem_vaga(tipo):
    """Comum precisa de vaga comum; idoso e PcD usam a sua ou uma comum."""
    if vagas_cps1 is None:
        return True   # sem dado do CPS1 não bloqueia a entrada (falha segura para o fluxo)
    livres = vagas_cps1.get("livres_tipo", {})
    ocupadas = sum(1 for v in vagas_cps1.get("vagas", []) if v.get("ocupada"))
    a_caminho = max(0, len(dentro) - ocupadas)   # entrou e ainda não estacionou
    comuns = livres.get("comum", 0) - a_caminho
    if tipo == "comum":
        return comuns > 0
    return livres.get(tipo, 0) > 0 or comuns > 0


def evento(cliente, dados):
    print("Evento:", dados)
    if cliente:   # sem rede a decisão já foi tomada; só o aviso não sai
        cliente.publish(T_SENSOR, json.dumps(dados).encode(), qos=1)


def placa_lida(cliente, placa, sentido):
    """A câmera leu uma placa com um carro parado na cancela."""
    global mudou_por_rede
    cadastro = CADASTRO.get(placa)
    tipo = cadastro["tipo"] if cadastro else "comum"
    base = {"placa": placa, "sentido": sentido, "tipo": tipo, "cadastrada": cadastro is not None}

    if modo == "emergencia":
        evento(cliente, dict(base, evento="livre", motivo="emergencia"))
        return

    if sentido == "entrada":
        if placa in dentro:
            motivo = "ja_dentro"
        elif not tem_vaga(tipo):
            motivo = "lotado"
        else:
            dentro[placa] = {"tipo": tipo, "avulso": cadastro is None, "pago": False}
            abrir_cancela()
            evento(cliente, dict(base, evento="entrada", avulso=cadastro is None))
            mudou_por_rede = True
            return
    else:
        carro = dentro.get(placa)
        if carro is None:
            motivo = "nao_registrado"
        elif carro["avulso"] and not carro["pago"]:
            motivo = "pagamento_pendente"
        else:
            if not carro["avulso"]:
                cadastro["saldo"] -= TARIFA   # débito automático, como o Sem Parar
                base["saldo"] = cadastro["saldo"]
                base["valor"] = TARIFA
            del dentro[placa]
            abrir_cancela()
            evento(cliente, dict(base, evento="saida"))
            mudou_por_rede = True
            return

    apitar(600)
    evento(cliente, dict(base, evento="negado", motivo=motivo))


def conferir_alarmes(cliente):
    """Cancela travada e evasão. Publica só quando o alarme começa ou termina."""
    global travada, evasao
    aberta_fisica = fim_de_curso.value() == 1
    agora_travada = (cancela == "fechada" and modo == "normal" and aberta_fisica
                     and mandou_fechar_em is not None
                     and time.ticks_diff(time.ticks_ms(), mandou_fechar_em) > TEMPO_TRAVADA_MS)
    if agora_travada != travada:
        travada = agora_travada
        if travada:
            apitar(1500)
        if cliente:
            cliente.publish(T_ALARME, json.dumps({"tipo": "cancela_travada", "ativo": travada}).encode(), qos=1)
        print("Cancela travada:", travada)

    nova = 0
    if vagas_cps1 is not None:
        ocupadas = sum(1 for v in vagas_cps1.get("vagas", []) if v.get("ocupada"))
        nova = max(0, ocupadas - len(dentro))
    if nova != evasao:
        evasao = nova
        if cliente:
            cliente.publish(T_ALARME, json.dumps(
                {"tipo": "evasao", "ativo": evasao > 0, "diferenca": evasao}).encode(), qos=1)
        print("Evasão:", evasao)


def estado_atual():
    placas = [{"placa": p, "tipo": c["tipo"], "avulso": c["avulso"], "pago": c["pago"]}
              for p, c in dentro.items()]
    return {"cancela": cancela, "fim_curso": "aberta" if fim_de_curso.value() else "fechada",
            "modo": modo, "carro": carro_presente,
            "sentido": "saida" if chave_sentido.value() else "entrada",
            "dentro": len(dentro), "placas": placas, "travada": travada,
            "evasao": evasao, "ack": ultimo_ack}


def ao_receber(topico, msg):
    global vagas_cps1, ultimo_ack, mudou_por_rede, restaurado
    topico = topico.decode()
    try:
        dados = json.loads(msg) if msg else None
    except ValueError:
        print("JSON inválido em", topico)
        return
    if not isinstance(dados, dict):
        return
    if topico == T_CPS1_SENSOR:
        vagas_cps1 = dados
    elif topico == T_ESTADO:
        # Só na primeira vez: depois de reiniciar, relê quem estava dentro.
        if not restaurado:
            restaurado = True
            for c in dados.get("placas", []):
                dentro[c["placa"]] = {"tipo": c.get("tipo", "comum"), "avulso": c.get("avulso", False),
                                      "pago": c.get("pago", False)}
            print("Estado restaurado:", len(dentro), "carros dentro")
    elif topico == T_PAGAMENTO:
        pendentes.append(("pagamento", dados))
    elif topico == T_COMANDO:
        if "ping" in dados:
            ultimo_ack = dados["ping"]
            mudou_por_rede = True
        pendentes.append(("comando", dados))


def tratar_pendentes(cliente):
    """Comandos chegam no callback e são executados aqui, fora dele."""
    global modo, mudou_por_rede
    while pendentes:
        tipo, dados = pendentes.pop(0)
        if tipo == "pagamento":
            placa = dados.get("placa")
            carro = dentro.get(placa)
            if carro and carro["avulso"]:
                carro["pago"] = True
                evento(cliente, {"evento": "pagamento", "placa": placa,
                                 "valor": dados.get("valor"), "ok": True})
            else:
                evento(cliente, {"evento": "pagamento", "placa": placa, "ok": False,
                                 "motivo": "sem_entrada_avulsa"})
            mudou_por_rede = True
            continue
        if isinstance(dados.get("placa"), str):
            sentido = dados.get("sentido") or ("saida" if chave_sentido.value() else "entrada")
            if carro_presente:
                placa_lida(cliente, dados["placa"].upper(), sentido)
            else:
                evento(cliente, {"evento": "negado", "placa": dados["placa"],
                                 "motivo": "sem_carro_na_cancela"})
        if dados.get("cancela") == "abrir":
            abrir_cancela()
            evento(cliente, {"evento": "abertura_manual"})
            mudou_por_rede = True
        if dados.get("modo") in ("normal", "emergencia") and dados["modo"] != modo:
            modo = dados["modo"]
            if modo == "emergencia":
                abrir_cancela()
            else:
                fechar_cancela()
            evento(cliente, {"evento": "modo", "modo": modo})
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
    cliente.set_last_will(T_STATUS, "offline", retain=True, qos=1)
    cliente.set_callback(ao_receber)
    cliente.connect()
    cliente.publish(T_STATUS, "online", retain=True, qos=1)
    cliente.subscribe(T_ESTADO, qos=1)        # para restaurar quem estava dentro
    cliente.subscribe(T_CPS1_SENSOR, qos=1)
    cliente.subscribe(T_COMANDO, qos=1)
    cliente.subscribe(T_PAGAMENTO, qos=1)
    print("MQTT conectado como", CLIENT_ID)
    return cliente


def tentar_conectar():
    """Uma tentativa só. Sem rede, a cancela segue com as regras locais e tenta de novo depois."""
    try:
        conectar_wifi()
        return conectar_mqtt()
    except Exception as erro:   # OSError (rede) ou MQTTException (broker recusou)
        print("Falha de conexão:", erro, "- seguindo offline")
        return None


# ===== PROGRAMA PRINCIPAL =====
print("SmartPark 2.0 · CPS2 Cancela")
pendentes = []
carro_presente = False
cliente = tentar_conectar()
proxima_tentativa = time.ticks_add(time.ticks_ms(), RECONECTAR_MS)
# Espera o estado retido chegar antes de publicar, para não apagar quem estava dentro.
inicio = time.ticks_ms()
while cliente and not restaurado and time.ticks_diff(time.ticks_ms(), inicio) < 3000:
    try:
        cliente.check_msg()
    except OSError:
        cliente = None
    time.sleep_ms(50)
restaurado = True
publicado = None
ultimo_ping = time.ticks_ms()

while True:
    try:
        # Parte local: decide e atua com ou sem rede (sem rede, usa as últimas vagas recebidas).
        carro_presente = medir_distancia(trig, echo) < CARRO_CM
        # Câmera simulada pelos botões (a interrupção guardou as placas em `lidas`).
        while lidas:
            placa = lidas.pop(0)
            if placa in lidas:
                continue   # mesmo botão duas vezes no mesmo instante: lê uma vez só
            sentido = "saida" if chave_sentido.value() else "entrada"
            if carro_presente:
                placa_lida(cliente, placa, sentido)
            else:
                evento(cliente, {"evento": "negado", "placa": placa,
                                 "motivo": "sem_carro_na_cancela"})

        # Fecha sozinha depois do tempo (a não ser em emergência).
        if (cancela == "aberta" and modo == "normal"
                and time.ticks_diff(time.ticks_ms(), aberta_em) > TEMPO_ABERTA_MS):
            fechar_cancela()
        conferir_alarmes(cliente)
        atualizar_buzzer()

        # Parte de rede: se caiu, tenta de novo a cada RECONECTAR_MS sem travar a cancela.
        if cliente is None:
            if time.ticks_diff(time.ticks_ms(), proxima_tentativa) >= 0:
                cliente = tentar_conectar()
                proxima_tentativa = time.ticks_add(time.ticks_ms(), RECONECTAR_MS)
                publicado = None
        else:
            for _ in range(5):
                cliente.check_msg()
            tratar_pendentes(cliente)
            texto = json.dumps(estado_atual())
            if texto != publicado or mudou_por_rede:
                cliente.publish(T_ESTADO, texto.encode(), retain=True)   # QoS 0: não trava o loop esperando confirmação
                publicado = texto
                mudou_por_rede = False
            if time.ticks_diff(time.ticks_ms(), ultimo_ping) > PING_MS:
                cliente.ping()
                cliente.publish(T_STATUS, "online", retain=True)   # reafirma: um Last Will atrasado não fica valendo
                ultimo_ping = time.ticks_ms()
    except OSError as erro:
        print("Conexão perdida:", erro, "- seguindo offline")
        cliente = None
        proxima_tentativa = time.ticks_ms()
    except Exception as erro:
        print("Erro ignorado:", erro)
    time.sleep_ms(100)
