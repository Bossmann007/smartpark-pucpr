# Equipe 3: Enzo Bossmann, Diego Feltrin e Gabriel Henrique
# Projeto: SmartPark 2.0 - CPS2 Cancela
# Disciplina: Conectividade em Sistemas Ciberfisicos - PUCPR 2026.2
# Placa: ESP32 + HC-SR04 + 3 botoes + 2 chaves + servo + buzzer | Comunicacao: MQTT
#
# Logica: modulo que vai junto da cancela que ja existe (entrada e saida).
# O HC-SR04 ve o carro parado, a "camera" le a placa (botoes ou dashboard)
# e o ESP32 abre o servo ou nega com o buzzer. As vagas do CPS1 dizem se
# lotou e mostram evasao (mais carro nas vagas do que entrou pela cancela)
# e vaga PcD irregular (vaga PcD ocupada sem nenhum carro PcD dentro).
# O fim de curso confirma se a cancela fechou mesmo.
#
# Do SmartPark do semestre passado (Old/main.py) vieram medir_distancia(),
# conectar_wifi() e o buzzer em PWM. O resto e novo.
#
# Publica:  cps2/sensor (eventos), cps2/estado, cps2/alarme, cps2/status
# Assina:   cps1/sensor, cps1/status, cps3/sensor (ajuda), cps2/comando,
#           pagamento e o proprio cps2/estado (so para lembrar quem estava dentro)

import json
import random
import time

import network
from machine import PWM, Pin, time_pulse_us
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
CLIENT_ID = "smartpark-cps2-%04x" % (random.getrandbits(16) ^ (time.ticks_us() & 0xFFFF))

T_SENSOR = PREFIXO + "/cps2/sensor"
T_ESTADO = PREFIXO + "/cps2/estado"
T_ALARME = PREFIXO + "/cps2/alarme"
T_COMANDO = PREFIXO + "/cps2/comando"
T_STATUS = PREFIXO + "/cps2/status"
T_PAGAMENTO = PREFIXO + "/pagamento"
T_CPS1_SENSOR = PREFIXO + "/cps1/sensor"
T_CPS1_STATUS = PREFIXO + "/cps1/status"
T_CPS3_SENSOR = PREFIXO + "/cps3/sensor"

CARRO_CM = 30            # abaixo disso tem carro parado na cancela
TEMPO_ABERTA_MS = 5000   # depois disso a cancela fecha sozinha
TEMPO_TRAVADA_MS = 3000  # mandou fechar e o fim de curso nao confirmou = travada
TARIFA = 5.00            # debito automatico da placa cadastrada
PING_MS = 10000          # avisa o broker que esta vivo (keepalive de 30 s)
RECONECTAR_MS = 5000     # sem rede, tenta de novo a cada 5 s

# Placas de teste (ficticias). De verdade o cadastro ficaria num servidor.
CADASTRO = {
    "ABC1D23": {"tipo": "comum", "saldo": 50.0},
    "BRA2E19": {"tipo": "idoso", "saldo": 50.0},
    "PUC0R26": {"tipo": "pcd", "saldo": 50.0},
}

# Pinos
trig = Pin(5, Pin.OUT)
echo = Pin(18, Pin.IN)

# Camera simulada: cada botao e a camera lendo uma placa cadastrada
botoes = [
    (Pin(13, Pin.IN, Pin.PULL_UP), "ABC1D23"),
    (Pin(14, Pin.IN, Pin.PULL_UP), "BRA2E19"),
    (Pin(27, Pin.IN, Pin.PULL_UP), "PUC0R26"),
]
chave_sentido = Pin(26, Pin.IN, Pin.PULL_UP)   # esquerda = entrada, direita = saida
fim_de_curso = Pin(25, Pin.IN, Pin.PULL_UP)    # esquerda = fechada, direita = aberta

# Servo: 1638 = 0 graus (fechada), 4915 = 90 graus (aberta)
SERVO_FECHADA = 1638
SERVO_ABERTA = 4915
servo = PWM(Pin(4), freq=50, duty_u16=SERVO_FECHADA)

# Buzzer igual ao Old/main.py: duty 0 = silencio, so liga para apitar
buzzer = PWM(Pin(23), freq=1000, duty_u16=0)

# Estado
dentro = {}            # placa -> {"tipo", "avulso", "pago"}
vagas_cps1 = None      # ultima mensagem do CPS1 (None = nao chegou ou CPS1 caiu)
modo = "normal"        # ou "emergencia"
cancela = "fechada"
aberta_em = 0
mandou_fechar_em = time.ticks_ms()   # None enquanto esta aberta
travada = False
evasao = 0
irregular = ""         # vaga PcD ocupada sem carro PcD dentro ("" = nenhuma)
buzzer_ate = 0
carro_presente = False
restaurado = False     # ja releu o proprio estado retido depois de reiniciar?
ultimo_ack = None
mudou_por_rede = False
lidas = []             # placas lidas pelos botoes (preenchido pela interrupcao)
pendentes = []         # comandos que chegaram pela rede, tratados no loop


# Interrupcao no botao: nao perde clique rapido mesmo com o loop ocupado com a rede
def botao_apertado(pino):
    for botao, placa in botoes:
        if botao is pino:
            lidas.append(placa)


for botao, placa in botoes:
    botao.irq(trigger=Pin.IRQ_FALLING, handler=botao_apertado)


# Funcoes

def medir_distancia(trig, echo):
    """Igual ao Old/main.py: distancia em cm, 999 se nao houver eco."""
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
    # liga o buzzer e o loop desliga depois de ms (com sleep a cancela travava)
    global buzzer_ate
    buzzer.duty_u16(32768)
    buzzer_ate = time.ticks_add(time.ticks_ms(), ms)


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


def ocupadas_cps1():
    return len([v for v in vagas_cps1.get("vagas", []) if v.get("ocupada")])


def tem_vaga(tipo):
    """Comum precisa de vaga comum. Idoso e PcD usam a vaga do tipo ou uma comum."""
    if vagas_cps1 is None:
        return True   # sem dado do CPS1 nao barra ninguem
    livres = vagas_cps1.get("livres_tipo", {})
    # quem passou pela cancela e ainda nao estacionou tambem conta
    a_caminho = max(0, len(dentro) - ocupadas_cps1())
    comuns = livres.get("comum", 0) - a_caminho
    if tipo == "comum":
        return comuns > 0
    return livres.get(tipo, 0) > 0 or comuns > 0


def evento(cliente, dados):
    print("Evento:", dados)
    if cliente:   # sem rede a cancela ja decidiu, so o aviso nao sai
        # QoS 1 porque evento nao se repete: o broker confirma que recebeu
        cliente.publish(T_SENSOR, json.dumps(dados).encode(), qos=1)


def placa_lida(cliente, placa, sentido):
    """A camera leu uma placa com um carro parado na cancela."""
    global mudou_por_rede
    cadastro = CADASTRO.get(placa)
    avulso = cadastro is None
    tipo = "comum" if avulso else cadastro["tipo"]
    base = {"placa": placa, "sentido": sentido, "tipo": tipo, "cadastrada": not avulso}
    mudou_por_rede = True

    if modo == "emergencia":
        # a cancela ja esta aberta, mas anota quem entra e sai para a evasao nao errar depois
        if sentido == "entrada" and placa not in dentro:
            dentro[placa] = {"tipo": tipo, "avulso": avulso, "pago": False}
        elif sentido == "saida":
            dentro.pop(placa, None)
        evento(cliente, dict(base, evento="livre", motivo="emergencia"))
        return

    if sentido == "entrada":
        if placa in dentro:
            motivo = "ja_dentro"
        elif not tem_vaga(tipo):
            motivo = "lotado"
        else:
            dentro[placa] = {"tipo": tipo, "avulso": avulso, "pago": False}
            abrir_cancela()
            evento(cliente, dict(base, evento="entrada", avulso=avulso))
            return
    else:
        carro = dentro.get(placa)
        if carro is None:
            motivo = "nao_registrado"
        elif carro["avulso"] and not carro["pago"]:
            motivo = "pagamento_pendente"
        else:
            if not carro["avulso"]:
                # debito automatico, como o Sem Parar
                cadastro["saldo"] -= TARIFA
                base["saldo"] = cadastro["saldo"]
                base["valor"] = TARIFA
            del dentro[placa]
            abrir_cancela()
            evento(cliente, dict(base, evento="saida"))
            return

    apitar(600)
    evento(cliente, dict(base, evento="negado", motivo=motivo))


def leitura(cliente, placa, sentido):
    if carro_presente:
        placa_lida(cliente, placa, sentido)
    else:
        evento(cliente, {"evento": "negado", "placa": placa, "motivo": "sem_carro_na_cancela"})


def sentido_da_chave():
    return "saida" if chave_sentido.value() else "entrada"


def conferir_alarmes(cliente):
    # cancela travada, evasao e vaga PcD irregular; so publica quando o alarme liga ou desliga
    global travada, evasao, irregular
    agora_travada = (cancela == "fechada" and modo == "normal"
                     and fim_de_curso.value() == 1 and mandou_fechar_em is not None
                     and time.ticks_diff(time.ticks_ms(), mandou_fechar_em) > TEMPO_TRAVADA_MS)
    if agora_travada != travada:
        travada = agora_travada
        print("Cancela travada:", travada)
        if travada:
            apitar(1500)
        if cliente:
            alarme = {"tipo": "cancela_travada", "ativo": travada}
            cliente.publish(T_ALARME, json.dumps(alarme).encode(), qos=1)

    # evasao = mais vagas ocupadas do que carros que entraram pela cancela
    nova = 0
    if vagas_cps1 is not None:
        nova = max(0, ocupadas_cps1() - len(dentro))
    if nova != evasao:
        evasao = nova
        print("Evasao:", evasao)
        if cliente:
            alarme = {"tipo": "evasao", "ativo": evasao > 0, "diferenca": evasao}
            cliente.publish(T_ALARME, json.dumps(alarme).encode(), qos=1)

    # vaga PcD irregular = mais vagas PcD ocupadas do que carros PcD que entraram.
    # O CPS2 nao sabe qual carro esta em qual vaga, so compara as contas.
    nova = ""
    if vagas_cps1 is not None:
        pcd = [v["id"] for v in vagas_cps1.get("vagas", []) if v.get("tipo") == "pcd" and v.get("ocupada") and not v.get("interditada")]
        pcd_dentro = len([c for c in dentro.values() if c["tipo"] == "pcd"])
        if len(pcd) > pcd_dentro:
            nova = pcd[-1]
    if nova != irregular:
        irregular = nova
        print("Vaga PcD irregular:", irregular or "nenhuma")
        if cliente:
            alarme = {"tipo": "vaga_irregular", "ativo": irregular != "", "vaga": irregular}
            cliente.publish(T_ALARME, json.dumps(alarme).encode(), qos=1)


def estado_cancela():
    placas = []
    for p, c in dentro.items():
        placas.append({"placa": p, "tipo": c["tipo"], "avulso": c["avulso"], "pago": c["pago"]})
    return {"cancela": cancela,
            "fim_curso": "aberta" if fim_de_curso.value() else "fechada",
            "modo": modo, "carro": carro_presente, "sentido": sentido_da_chave(),
            "dentro": len(dentro), "placas": placas, "travada": travada,
            "evasao": evasao, "vaga_irregular": irregular, "vagas_ok": vagas_cps1 is not None, "ack": ultimo_ack}


def ao_receber(topico, msg):
    # o check_msg() chama essa funcao quando chega mensagem. Aqui so anota o que
    # chegou; quem abre cancela e publica e o loop (tratar_pendentes).
    global vagas_cps1, ultimo_ack, mudou_por_rede, restaurado, modo
    topico = topico.decode()
    if topico == T_CPS1_STATUS:
        # CPS1 caiu (Last Will): as vagas guardadas ficaram velhas, esquece elas
        if msg == b"offline":
            vagas_cps1 = None
            mudou_por_rede = True
            print("CPS1 offline, sem dado de vagas")
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
        vagas_cps1 = dados
    elif topico == T_ESTADO:
        # so uma vez, depois de reiniciar: rele quem estava dentro e o modo
        if not restaurado:
            restaurado = True
            for c in dados.get("placas", []):
                if isinstance(c, dict) and isinstance(c.get("placa"), str):
                    dentro[c["placa"]] = {"tipo": c.get("tipo", "comum"),
                                          "avulso": c.get("avulso", False),
                                          "pago": c.get("pago", False)}
            if dados.get("modo") == "emergencia":
                modo = "emergencia"
            print("Estado restaurado:", len(dentro), "carros dentro, modo", modo)
    elif topico == T_PAGAMENTO:
        pendentes.append(("pagamento", dados))
    elif topico == T_CPS3_SENSOR:
        if dados.get("ajuda"):
            pendentes.append(("ajuda", dados))
    elif topico == T_COMANDO:
        if "ping" in dados:
            ultimo_ack = dados["ping"]
            mudou_por_rede = True
        pendentes.append(("comando", dados))


def tratar_pendentes(cliente):
    global modo, mudou_por_rede
    while pendentes:
        tipo, dados = pendentes.pop(0)

        if tipo == "ajuda":
            # pedido de ajuda no totem (CPS3): bip aqui, onde fica o operador
            apitar(250)
            evento(cliente, {"evento": "ajuda_totem"})

        elif tipo == "pagamento":
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

        else:
            placa = dados.get("placa")
            if isinstance(placa, str):
                # camera simulada pelo dashboard; sem sentido usa a chave
                leitura(cliente, placa.upper(), dados.get("sentido") or sentido_da_chave())
            if dados.get("cancela") == "abrir":
                abrir_cancela()
                evento(cliente, {"evento": "abertura_manual"})
                mudou_por_rede = True
            novo = dados.get("modo")
            if novo in ("normal", "emergencia") and novo != modo:
                modo = novo
                if modo == "emergencia":
                    abrir_cancela()
                else:
                    fechar_cancela()
                evento(cliente, {"evento": "modo", "modo": modo})
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
    cliente.set_last_will(T_STATUS, "offline", retain=True, qos=1)
    cliente.set_callback(ao_receber)
    cliente.connect()
    cliente.publish(T_STATUS, "online", retain=True, qos=1)
    for t in (T_ESTADO, T_CPS1_SENSOR, T_CPS1_STATUS, T_CPS3_SENSOR, T_COMANDO, T_PAGAMENTO):
        cliente.subscribe(t, qos=1)
    print("MQTT conectado como", CLIENT_ID)
    return cliente


def tentar_conectar():
    # tenta uma vez so, para a cancela nao parar esperando a rede
    try:
        conectar_wifi()
        return conectar_mqtt()
    except Exception as erro:
        print("Falha ao conectar:", erro)
        return None


# Programa principal
print("SmartPark 2.0 - CPS2 Cancela")
cliente = tentar_conectar()

# Espera ate 3 s o estado retido chegar, senao a primeira publicacao apagaria quem estava dentro
inicio = time.ticks_ms()
while cliente and not restaurado and time.ticks_diff(time.ticks_ms(), inicio) < 3000:
    try:
        cliente.check_msg()
    except Exception as erro:   # retido malformado nao pode travar o boot
        print("Erro ao restaurar:", erro)
        cliente = None
    time.sleep_ms(50)
restaurado = True
if modo == "emergencia":   # reiniciou em emergencia: a cancela continua aberta
    abrir_cancela()

ultima_tentativa = time.ticks_ms()
ultimo_ping = time.ticks_ms()
publicado = None

while True:
    try:
        # Parte local: decide com ou sem rede (sem rede usa as ultimas vagas recebidas)
        carro_presente = medir_distancia(trig, echo) < CARRO_CM
        while lidas:
            placa = lidas.pop(0)
            if placa not in lidas:   # mesmo botao duas vezes seguidas conta uma vez
                leitura(cliente, placa, sentido_da_chave())

        if (cancela == "aberta" and modo == "normal"
                and time.ticks_diff(time.ticks_ms(), aberta_em) > TEMPO_ABERTA_MS):
            fechar_cancela()
        conferir_alarmes(cliente)
        if buzzer.duty_u16() and time.ticks_diff(time.ticks_ms(), buzzer_ate) > 0:
            buzzer.duty_u16(0)

        # Parte de rede
        if cliente is None:
            if time.ticks_diff(time.ticks_ms(), ultima_tentativa) > RECONECTAR_MS:
                cliente = tentar_conectar()
                ultima_tentativa = time.ticks_ms()
                publicado = None
        else:
            for _ in range(5):
                cliente.check_msg()
            tratar_pendentes(cliente)
            texto = json.dumps(estado_cancela())
            if texto != publicado or mudou_por_rede:
                # QoS 0 para o loop nao ficar esperando confirmacao
                cliente.publish(T_ESTADO, texto.encode(), retain=True)
                publicado = texto
                mudou_por_rede = False
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
