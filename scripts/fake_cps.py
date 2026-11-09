# /// script
# requires-python = ">=3.10"
# dependencies = ["paho-mqtt>=2"]
# ///
"""Três CPS falsos para testar o scripts/verify sem o Wokwi.

Uso: uv run scripts/fake_cps.py --prefix teste/smartpark-xyz [--segundos 40]
Não substitui os ESP32: serve só para provar que o verificador funciona.
"""
import argparse, json, time
import paho.mqtt.client as mqtt

ap = argparse.ArgumentParser()
ap.add_argument("--prefix", required=True)
ap.add_argument("--broker", default="broker.hivemq.com")
ap.add_argument("--segundos", type=float, default=40)
a = ap.parse_args()

clients = []
for cps in ["cps1", "cps2", "cps3"]:
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"fake-{cps}-{time.time_ns() % 100000}")
    status = f"{a.prefix}/{cps}/status"
    c.will_set(status, "offline", qos=1, retain=True)

    def on_message(cl, u, m, cps=cps):
        ping = json.loads(m.payload).get("ping")
        if ping:
            cl.publish(f"{a.prefix}/{cps}/estado", json.dumps({"ack": ping}), qos=1, retain=True)

    c.on_message = on_message
    c.connect(a.broker, 1883, keepalive=30)
    c.subscribe(f"{a.prefix}/{cps}/comando", qos=1)
    c.publish(status, "online", qos=1, retain=True)
    if cps == "cps1":
        vagas = [{"id": f"V{i}", "tipo": t, "ocupada": False} for i, t in enumerate(["comum", "comum", "idoso", "pcd"], 1)]
        c.publish(f"{a.prefix}/cps1/sensor", json.dumps({"vagas": vagas, "livres": 4, "livres_comuns": 2, "total": 4}), retain=True)
    c.loop_start()
    clients.append((c, status))

print("fake CPS no ar em", a.prefix)
time.sleep(a.segundos)
for c, status in clients:
    c.publish(status, "offline", qos=1, retain=True)
    c.loop_stop(); c.disconnect()
print("fake CPS desligados")
