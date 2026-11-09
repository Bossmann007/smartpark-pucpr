"""Deixa os 3 CPS simulados rodando (sem cenário), para testar o dashboard sem o Wokwi.

Uso (na raiz do repo):  python3 sim/rodar.py [--prefixo cscf/equipe03-teste] [--segundos 0]
O hardware falso de cada CPS fica em sim/run/rodar/<cps>/in.json:
  {"dist": {"34": 20}, "pins": {"13": 0}}   # V1 ocupada; botão no GPIO 13 apertado
Ctrl+C para parar (os ESP32 simulados caem e o broker publica o Last Will).
"""
import argparse
import json
import os
import signal
import socket
import subprocess
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTAS = {"cps1": "cps1-vagas", "cps2": "cps2-cancela", "cps3": "cps3-totem"}

ap = argparse.ArgumentParser()
ap.add_argument("--prefixo", default="cscf/equipe03-teste")
ap.add_argument("--broker", default="broker.hivemq.com")
ap.add_argument("--segundos", type=float, default=0, help="0 = até Ctrl+C")
a = ap.parse_args()

run = os.path.join(RAIZ, "sim", "run", "rodar")
ipv4 = socket.getaddrinfo(a.broker, 1883, socket.AF_INET)[0][4][0]
procs = []
for cps, pasta_cps in PASTAS.items():
    pasta = os.path.join(run, cps)
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, "sim_config.py"), "w") as f:
        f.write(f"DIR = {pasta!r}\nBROKER = {ipv4!r}\nPREFIXO = {a.prefixo!r}\n")
    with open(os.path.join(pasta, "in.json"), "w") as f:
        json.dump({"dist": {}, "pins": {"25": 0, "26": 0} if cps == "cps2" else {}}, f)
    env = dict(os.environ, MICROPYPATH=f"{pasta}:{os.path.join(RAIZ, 'sim', 'lib')}:"
               + os.path.expanduser("~/.micropython/lib"))
    log = open(os.path.join(pasta, "console.log"), "w")
    procs.append(subprocess.Popen(["micropython", os.path.join(pasta_cps, "main.py")],
                                  cwd=RAIZ, env=env, stdout=log, stderr=subprocess.STDOUT))
    print(f"{cps}: hardware em {os.path.relpath(pasta, RAIZ)}/in.json, console em console.log")

print(f"prefixo {a.prefixo} no broker {a.broker}")


def parar(sinal, quadro):
    raise KeyboardInterrupt


# em segundo plano o Ctrl+C não chega; SIGTERM (kill) também para os ESP32 simulados
signal.signal(signal.SIGTERM, parar)
signal.signal(signal.SIGHUP, parar)
try:
    if a.segundos:
        time.sleep(a.segundos)
    else:
        signal.pause()
except KeyboardInterrupt:
    pass
finally:
    for p in procs:
        p.send_signal(signal.SIGKILL)
        p.wait()
    print("CPS simulados parados")
