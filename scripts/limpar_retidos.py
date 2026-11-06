# /// script
# requires-python = ">=3.10"
# dependencies = ["paho-mqtt>=2"]
# ///
"""Apaga os retidos de um prefixo (publica payload vazio com retain). Rodar antes de gravar o vídeo.

Uso: uv run scripts/limpar_retidos.py --prefix cscf/smartpark
"""
import argparse, time
import paho.mqtt.client as mqtt

ap = argparse.ArgumentParser()
ap.add_argument("--prefix", required=True)
ap.add_argument("--broker", default="broker.hivemq.com")
a = ap.parse_args()
topics = set()
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.on_message = lambda cl, u, m: m.retain and m.payload and topics.add(m.topic)
c.connect(a.broker, 1883)
c.subscribe(a.prefix + "/#")
c.loop_start(); time.sleep(3)
for t in sorted(topics):
    c.publish(t, b"", qos=1, retain=True).wait_for_publish()
    print("limpo", t)
c.loop_stop(); c.disconnect()
print(len(topics), "retidos apagados")
