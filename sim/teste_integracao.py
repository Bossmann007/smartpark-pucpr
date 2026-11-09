# /// script
# requires-python = ">=3.10"
# dependencies = ["paho-mqtt>=2"]
# ///
"""Teste de integração: roda os 3 main.py reais no MicroPython do Mac, com
hardware falso (sim/lib), contra o broker de verdade, e confere cada
integração do docs/topicos.md pelas mensagens MQTT.

Uso (na raiz do repo):  uv run sim/teste_integracao.py
Precisa: micropython (brew install micropython) e umqtt.simple
(micropython -m mip install umqtt.simple).

Grava o log de todas as mensagens em sim/run/<id>/mqtt-log.jsonl
(a apresentação reaproveita esse log).
"""
import json
import os
import signal
import socket
import subprocess
import sys
import time
import uuid

import paho.mqtt.client as mqtt

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BROKER = os.environ.get("BROKER", "broker.hivemq.com")
ID = "t" + uuid.uuid4().hex[:6]
PREFIXO = f"teste/smartpark-{ID}"
RUN = os.path.join(RAIZ, "sim", "run", ID)
MPLIB = os.path.expanduser("~/.micropython/lib")
PASTAS = {"cps1": "cps1-vagas", "cps2": "cps2-cancela", "cps3": "cps3-totem"}

ultimo = {}       # tópico (sem prefixo) -> último payload (str)
historico = []    # (t, tópico, payload)
procs = {}
falhas = []
t0 = time.time()
log = None


def ao_receber(c, u, m):
    t = m.topic[len(PREFIXO) + 1:]
    p = m.payload.decode(errors="replace")
    ultimo[t] = p
    historico.append((time.time(), t, p))
    log.write(json.dumps({"t": round(time.time() - t0, 3), "topico": t, "payload": p,
                          "retain": bool(m.retain)}, ensure_ascii=False) + "\n")
    log.flush()


def j(topico):
    try:
        return json.loads(ultimo.get(topico, ""))
    except ValueError:
        return None


def entrada(cps, **mudancas):
    """Muda o hardware falso de um CPS: dist={pino: cm}, pins={pino: nivel}."""
    arq = os.path.join(RUN, cps, "in.json")
    with open(arq) as f:
        dados = json.load(f)
    for chave, valores in mudancas.items():
        dados.setdefault(chave, {}).update({str(k): v for k, v in valores.items()})
    with open(arq + ".tmp", "w") as f:
        json.dump(dados, f)
    os.replace(arq + ".tmp", arq)


def saida(cps):
    try:
        with open(os.path.join(RUN, cps, "out.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def apertar(cps, pino):
    entrada(cps, pins={pino: 0})
    time.sleep(0.6)
    entrada(cps, pins={pino: 1})


def esperar(nome, cond, timeout=15):
    fim = time.time() + timeout
    while time.time() < fim:
        try:
            if cond():
                print(f"OK     {nome}")
                return True
        except (TypeError, KeyError, AttributeError):
            pass
        time.sleep(0.2)
    print(f"FALHA  {nome}")
    falhas.append(nome)
    return False


def evento_desde(t_inicio, cond):
    for t, top, p in historico:
        if t >= t_inicio and top == "cps2/sensor":
            try:
                if cond(json.loads(p)):
                    return True
            except ValueError:
                pass
    return False


def alarme_desde(t_inicio, tipo, ativo):
    for t, top, p in historico:
        if t >= t_inicio and top == "cps2/alarme":
            d = json.loads(p)
            if d.get("tipo") == tipo and d.get("ativo") == ativo:
                return True
    return False


def iniciar(cps):
    pasta = os.path.join(RUN, cps)
    env = dict(os.environ, MICROPYPATH=f"{pasta}:{os.path.join(RAIZ, 'sim', 'lib')}:{MPLIB}")
    arq_log = open(os.path.join(pasta, "console.log"), "a")
    procs[cps] = subprocess.Popen(["micropython", os.path.join(PASTAS[cps], "main.py")],
                                  cwd=RAIZ, env=env, stdout=arq_log, stderr=subprocess.STDOUT)


def matar(cps):
    procs[cps].send_signal(signal.SIGKILL)
    procs[cps].wait()


def main():
    global log
    sys.stdout.reconfigure(line_buffering=True)
    for cps in PASTAS:
        pasta = os.path.join(RUN, cps)
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, "sim_config.py"), "w") as f:
            # IPv4: o MicroPython do Mac recebe IPv6 primeiro e falha (errno 47); no ESP32 não acontece
            ipv4 = socket.getaddrinfo(BROKER, 1883, socket.AF_INET)[0][4][0]
            f.write(f"DIR = {pasta!r}\nBROKER = {ipv4!r}\nPREFIXO = {PREFIXO!r}\n")
        # chaves deslizantes começam à esquerda (ligadas ao GND = 0), como no Wokwi
        pins = {"25": 0, "26": 0} if cps == "cps2" else {}
        with open(os.path.join(pasta, "in.json"), "w") as f:
            json.dump({"dist": {}, "pins": pins}, f)
    log = open(os.path.join(RUN, "mqtt-log.jsonl"), "w")

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="teste-" + ID)
    c.on_message = ao_receber
    c.connect(BROKER, 1883)
    c.subscribe(PREFIXO + "/#", qos=1)
    c.loop_start()
    pub = lambda t, d: c.publish(f"{PREFIXO}/{t}", json.dumps(d), qos=1)
    print("prefixo", PREFIXO)

    try:
        for cps in PASTAS:
            iniciar(cps)

        print("\n# 1. Os três no ar")
        for cps in PASTAS:
            esperar(f"{cps}/status = online", lambda cps=cps: ultimo.get(f"{cps}/status") == "online", 30)
        esperar("CPS1 publica 4 vagas livres", lambda: j("cps1/sensor")["livres"] == 4)
        esperar("Totem mostra 4 e fita verde, verde, amarelo, azul",
                lambda: j("cps3/estado")["display"] == 4
                and j("cps3/estado")["fita"] == ["verde", "verde", "amarelo", "azul"])
        r = subprocess.run([os.path.join(RAIZ, "scripts", "verify"), "--prefix", PREFIXO,
                            "--broker", BROKER, "--timeout", "20"], capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode != 0:
            falhas.append("scripts/verify")

        print("\n# 2. Entrada cadastrada: câmera lê ABC1D23")
        entrada("cps2", dist={18: 10}, pins={26: 0})
        time.sleep(0.5)
        t = time.time()
        apertar("cps2", 13)
        esperar("CPS2 publica entrada de ABC1D23",
                lambda: evento_desde(t, lambda e: e["evento"] == "entrada" and e["placa"] == "ABC1D23"))
        esperar("Servo abriu (duty 4915)", lambda: saida("cps2")["pwm4"][1] == 4915)
        esperar("cps2/estado dentro = 1", lambda: j("cps2/estado")["dentro"] == 1)

        print("\n# 3. Carro estaciona na V1: vagas → totem")
        entrada("cps1", dist={34: 20})
        esperar("CPS1: 3 livres", lambda: j("cps1/sensor")["livres"] == 3)
        esperar("LED vermelho da V1 aceso", lambda: saida("cps1")["pin22"] == 1 and saida("cps1")["pin2"] == 0)
        esperar("Totem: 3 e V1 vermelha", lambda: j("cps3/estado")["display"] == 3
                and j("cps3/estado")["fita"][0] == "vermelho")
        esperar("NeoPixel 0 vermelho", lambda: saida("cps3")["neopixel"][0][0] > 0
                and saida("cps3")["neopixel"][0][1] == 0)

        print("\n# 4. Avulso pelo dashboard (câmera) e estaciona na V2")
        t = time.time()
        pub("cps2/comando", {"placa": "XYZ9K87", "sentido": "entrada"})
        esperar("XYZ9K87 entra como avulso",
                lambda: evento_desde(t, lambda e: e["evento"] == "entrada" and e.get("avulso") is True))
        entrada("cps1", dist={35: 20})
        esperar("CPS1: 0 vagas comuns", lambda: j("cps1/sensor")["livres_comuns"] == 0)

        print("\n# 5. Lotado: placa comum negada, buzzer toca")
        t = time.time()
        pub("cps2/comando", {"placa": "QWE4R56", "sentido": "entrada"})
        # o bip dura 0,6 s e o evento pode demorar mais que isso no broker publico: olha o buzzer primeiro
        esperar("Buzzer ligado", lambda: saida("cps2")["pwm23"][1] > 0, 10)
        esperar("QWE4R56 negada por lotado",
                lambda: evento_desde(t, lambda e: e["evento"] == "negado" and e.get("motivo") == "lotado"))
        t = time.time()
        apertar("cps2", 27)
        esperar("PUC0R26 (PcD) entra mesmo sem vaga comum",
                lambda: evento_desde(t, lambda e: e["evento"] == "entrada" and e["placa"] == "PUC0R26"))
        entrada("cps1", dist={33: 20})

        print("\n# 6. Evasão: V3 ocupada sem passar pela cancela")
        t = time.time()
        entrada("cps1", dist={32: 20})
        esperar("Alarme de evasão ativo", lambda: alarme_desde(t, "evasao", True))
        esperar("Totem com LED vermelho piscando", lambda: j("cps3/estado")["led"] == "vermelho_piscando")
        t = time.time()
        entrada("cps1", dist={32: 400})
        esperar("Evasão resolvida", lambda: alarme_desde(t, "evasao", False))

        print("\n# 7. Saída: avulso só sai depois de pagar")
        entrada("cps2", pins={26: 1})
        time.sleep(0.5)
        t = time.time()
        pub("cps2/comando", {"placa": "XYZ9K87"})
        esperar("XYZ9K87 negada: pagamento pendente",
                lambda: evento_desde(t, lambda e: e.get("motivo") == "pagamento_pendente"))
        t = time.time()
        pub("pagamento", {"placa": "XYZ9K87", "valor": 7.0})
        esperar("Pagamento confirmado",
                lambda: evento_desde(t, lambda e: e["evento"] == "pagamento" and e["ok"]))
        t = time.time()
        pub("cps2/comando", {"placa": "XYZ9K87"})
        esperar("XYZ9K87 sai", lambda: evento_desde(t, lambda e: e["evento"] == "saida"))
        t = time.time()
        apertar("cps2", 13)
        esperar("ABC1D23 sai com débito (saldo 45)",
                lambda: evento_desde(t, lambda e: e["evento"] == "saida" and e.get("saldo") == 45.0))

        print("\n# 8. Cancela travada")
        esperar("Cancela fechou sozinha", lambda: j("cps2/estado")["cancela"] == "fechada", 10)
        t = time.time()
        entrada("cps2", pins={25: 1})
        esperar("Alarme cancela travada", lambda: alarme_desde(t, "cancela_travada", True), 10)
        t = time.time()
        entrada("cps2", pins={25: 0})
        esperar("Alarme cancela travada encerrado", lambda: alarme_desde(t, "cancela_travada", False))

        print("\n# 9. Emergência pelo dashboard")
        pub("cps2/comando", {"modo": "emergencia"})
        esperar("CPS2 em emergência e cancela aberta", lambda: j("cps2/estado")["modo"] == "emergencia"
                and j("cps2/estado")["cancela"] == "aberta")
        esperar("CPS1 pisca os LEDs", lambda: j("cps1/estado")["emergencia"] is True)
        esperar("Totem fita branca piscando", lambda: j("cps3/estado")["fita_pisca"] is True
                and j("cps3/estado")["fita"][0] == "branco")
        pub("cps2/comando", {"modo": "normal"})
        esperar("Volta ao normal", lambda: j("cps2/estado")["modo"] == "normal"
                and j("cps1/estado")["emergencia"] is False)

        print("\n# 10. Ajuda no totem, PIR e vaga interditada")
        t = time.time()
        apertar("cps3", 13)
        esperar("CPS2 recebeu a ajuda do totem e apitou",
                lambda: evento_desde(t, lambda e: e["evento"] == "ajuda_totem"))
        esperar("cps3/sensor pede ajuda", lambda: any(top == "cps3/sensor" and "ajuda" in p
                                                       for _, top, p in historico))
        esperar("Totem: ajuda aguardando", lambda: j("cps3/estado")["ajuda"] == "aguardando")
        pub("cps3/comando", {"ajuda": "atendido"})
        esperar("Totem: ajuda atendida (LED azul)", lambda: j("cps3/estado")["ajuda"] == "atendida"
                and saida("cps3")["pin17"] == 1)
        entrada("cps3", pins={27: 1})
        esperar("PIR: brilho alto", lambda: j("cps3/estado")["brilho"] == "alto")
        entrada("cps3", pins={27: 0})
        pub("cps1/comando", {"manutencao": "V4", "ativo": True})
        esperar("V4 interditada no CPS1 e laranja no totem",
                lambda: j("cps1/sensor")["vagas"][3]["interditada"] is True
                and j("cps3/estado")["fita"][3] == "laranja")
        pub("cps1/comando", {"manutencao": "V4", "ativo": False})

        print("\n# 11. Vaga PcD ocupada sem credencial")
        entrada("cps1", dist={33: 400, 34: 400, 35: 400})   # como no roteiro: V1 e V2 ja vazias depois da saida
        entrada("cps2", pins={26: 1})
        time.sleep(0.5)
        t = time.time()
        apertar("cps2", 27)
        esperar("PUC0R26 sai", lambda: evento_desde(t, lambda e: e["evento"] == "saida" and e["placa"] == "PUC0R26"))
        entrada("cps2", pins={26: 0})
        time.sleep(0.5)
        t = time.time()
        apertar("cps2", 13)
        esperar("ABC1D23 entra", lambda: evento_desde(t, lambda e: e["evento"] == "entrada" and e["placa"] == "ABC1D23"))
        t = time.time()
        entrada("cps1", dist={33: 20})
        esperar("Alarme vaga PcD irregular na V4",
                lambda: alarme_desde(t, "vaga_irregular", True) and j("cps2/estado")["vaga_irregular"] == "V4")
        esperar("Totem pisca só a V4", lambda: j("cps3/estado")["pisca_vaga"] == 3
                and j("cps3/estado")["led"] == "vermelho_piscando")
        t = time.time()
        entrada("cps1", dist={33: 400, 34: 20})   # o carro muda para a V1
        esperar("Alarme vaga PcD encerrado", lambda: alarme_desde(t, "vaga_irregular", False))
        esperar("Totem para de piscar a V4", lambda: j("cps3/estado")["pisca_vaga"] is None)

        print("\n# 12. Queda e volta do CPS1 (Last Will)")
        matar("cps1")
        esperar("cps1/status = offline (LWT)", lambda: ultimo.get("cps1/status") == "offline", 30)
        esperar("Totem mostra ----", lambda: j("cps3/estado")["display"] == "----")
        esperar("CPS2 esquece as vagas velhas", lambda: j("cps2/estado")["vagas_ok"] is False)
        iniciar("cps1")
        esperar("cps1/status = online de novo", lambda: ultimo.get("cps1/status") == "online", 30)
        esperar("Totem volta ao número", lambda: isinstance(j("cps3/estado")["display"], int), 15)
        esperar("CPS2 volta a ter vagas", lambda: j("cps2/estado")["vagas_ok"] is True, 20)

        print("\n# 13. CPS2 reinicia sem esquecer quem está dentro")
        antes = j("cps2/estado")["dentro"]
        matar("cps2")
        esperar("cps2/status = offline (LWT)", lambda: ultimo.get("cps2/status") == "offline", 30)
        iniciar("cps2")
        esperar("cps2/status = online de novo", lambda: ultimo.get("cps2/status") == "online", 30)
        time.sleep(4)
        esperar(f"CPS2 restaurou dentro = {antes}", lambda: j("cps2/estado")["dentro"] == antes)

        print("\n# 14. CPS2 reinicia em emergência e continua em emergência")
        pub("cps2/comando", {"modo": "emergencia"})
        esperar("CPS2 em emergência", lambda: j("cps2/estado")["modo"] == "emergencia")
        matar("cps2")
        esperar("cps2/status = offline (LWT)", lambda: ultimo.get("cps2/status") == "offline", 30)
        iniciar("cps2")
        esperar("cps2/status = online de novo", lambda: ultimo.get("cps2/status") == "online", 30)
        time.sleep(4)
        esperar("CPS2 voltou em emergência com a cancela aberta", lambda: j("cps2/estado")["modo"] == "emergencia"
                and j("cps2/estado")["cancela"] == "aberta")
        pub("cps2/comando", {"modo": "normal"})
        esperar("Volta ao normal", lambda: j("cps2/estado")["modo"] == "normal")
    finally:
        for p in procs.values():
            if p.poll() is None:
                p.send_signal(signal.SIGKILL)
                p.wait()
        time.sleep(1)
        # apaga os retidos do prefixo de teste
        for top in list(ultimo):
            c.publish(f"{PREFIXO}/{top}", b"", qos=1, retain=True)
        time.sleep(1)
        c.loop_stop()
        c.disconnect()
        log.close()

    print(f"\n{len(falhas)} falha(s) em {time.time() - t0:.0f} s. Log: {os.path.relpath(RUN, RAIZ)}/")
    for f in falhas:
        print("  -", f)
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
