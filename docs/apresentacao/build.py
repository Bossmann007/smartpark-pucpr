"""Gera a apresentação animada (um HTML só, sem rede) e as folhas do apresentador.

Uso (na pasta docs/apresentacao):
    npm install            # uma vez: three, fontes Inter/JetBrains Mono, playwright-core
    python3 build.py       # escreve apresentacao-animada.html e ../FOLHAS.md

Entradas: template.html, folhas.json (notas + duração de cada parte),
mqtt-log.jsonl (log real do teste de integração), puc-osm.json (OpenStreetMap)
e as fotos de Old/imgs.
"""
import base64
import json
import math
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
NM = os.path.join(AQUI, "node_modules")


def ler(caminho, modo="r"):
    with open(caminho, modo, **({} if "b" in modo else {"encoding": "utf-8"})) as f:
        return f.read()


def b64(caminho):
    return base64.b64encode(ler(caminho, "rb")).decode()


def js(valor):
    return json.dumps(valor, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


# ---------- fontes locais (embutidas: nada de rede na hora de renderizar) ----------
def fontes():
    css = []
    for familia, pasta, pesos in [("Inter", "inter", [400, 500, 600, 700, 800]),
                                  ("JetBrains Mono", "jetbrains-mono", [400, 600])]:
        for p in pesos:
            arq = os.path.join(NM, "@fontsource", pasta, "files", f"{pasta}-latin-{p}-normal.woff2")
            css.append(f"@font-face{{font-family:'{familia}';font-style:normal;font-weight:{p};"
                       f"font-display:block;src:url(data:font/woff2;base64,{b64(arq)}) format('woff2')}}")
    return "\n".join(css)


# ---------- log MQTT real ----------
def log_mqtt():
    msgs, anterior = [], None
    for linha in ler(os.path.join(AQUI, "mqtt-log.jsonl")).splitlines():
        if not linha.strip():
            continue
        m = json.loads(linha)
        if not m["payload"]:
            continue   # limpeza de retidos no fim do teste
        chave = (m["topico"], m["payload"])
        if anterior and chave == anterior[0] and m["t"] - anterior[1] < 0.01:
            continue   # mesma mensagem duas vezes no mesmo instante (republicação do loop)
        anterior = (chave, m["t"])
        msgs.append({"t": m["t"], "topico": m["topico"], "payload": m["payload"]})
    return msgs


# ---------- OpenStreetMap -> metros em volta do centro do câmpus ----------
def osm():
    dados = json.loads(ler(os.path.join(AQUI, "puc-osm.json")))
    els = dados["elements"]
    campus = next(e for e in els if e.get("tags", {}).get("amenity") == "university")
    lats = [p["lat"] for p in campus["geometry"]]
    lons = [p["lon"] for p in campus["geometry"]]
    lat0, lon0 = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
    kx = math.cos(math.radians(lat0)) * 111320
    ky = 110540

    def xy(geom):
        return [[round((p["lon"] - lon0) * kx, 1), round((p["lat"] - lat0) * ky, 1)] for p in geom]

    def contornos(e):
        if e["type"] == "way":
            return [xy(e["geometry"])] if e.get("geometry") else []
        return [xy(m["geometry"]) for m in e.get("members", [])
                if m.get("role") == "outer" and m.get("geometry")]

    def numero(v):
        try:
            return float(str(v).replace(",", ".").split()[0])
        except (ValueError, IndexError):
            return None

    predios, vagas, ruas = [], [], []
    for e in els:
        t = e.get("tags", {})
        if "building" in t:
            h = numero(t.get("height"))
            if h is None and numero(t.get("building:levels")):
                h = numero(t["building:levels"]) * 3.4
            if h is None:
                h = 12.0 if t.get("building") == "university" else 7.0
            for c in contornos(e):
                predios.append({"h": round(max(h, 4), 1), "n": t.get("name", ""), "p": c})
        elif t.get("amenity") == "parking":
            for c in contornos(e):
                cx = sum(p[0] for p in c) / len(c)
                cy = sum(p[1] for p in c) / len(c)
                vagas.append({"n": t.get("name", ""), "c": [round(cx, 1), round(cy, 1)], "p": c})
        elif "highway" in t and e["type"] == "way" and e.get("geometry"):
            ruas.append({"k": t["highway"], "p": xy(e["geometry"])})
    return {"campus": xy(campus["geometry"]), "predios": predios, "vagas": vagas, "ruas": ruas,
            "base": dados.get("osm3s", {}).get("timestamp_osm_base", "")}


def fotos():
    pasta = os.path.join(RAIZ, "Old", "imgs")
    nomes = ["puc-totem-vagas", "puc-portao02", "puc-estac-lotado", "puc-aerea"]
    return {n: "data:image/jpeg;base64," + b64(os.path.join(pasta, n + ".jpg")) for n in nomes}


def folhas_md(folhas):
    md = ["# SmartPark 2.0: folhas para a apresentação", "",
          "Uma folha por parte da apresentação animada (`docs/apresentacao/apresentacao-animada.html`), na ordem em que aparecem. "
          "São as mesmas notas da janela do apresentador (tecla N). Gerado por `docs/apresentacao/build.py` a partir de `folhas.json`: edite o JSON, não este arquivo.", ""]
    inicio = 0
    for n, f in enumerate(folhas, 1):
        md += [f"## Folha {n}. {f['titulo']}", "",
               f"*{inicio // 60}:{inicio % 60:02d} a {(inicio + f['dur']) // 60}:{(inicio + f['dur']) % 60:02d} ({f['dur']} s)*", "",
               f"**Na tela:** {f['tela']}", "", "**Falar**", ""]
        md += [f"- {x}" for x in f["falar"]] + ["", "**Mais para falar**", ""] + [f"- {x}" for x in f["mais"]]
        md += ["", f"**Se perguntarem:** {f['pergunta'][0]}", "", f"> {f['pergunta'][1]}", "", "---", ""]
        inicio += f["dur"]
    return "\n".join(md)


def main():
    folhas = json.loads(ler(os.path.join(AQUI, "folhas.json")))
    t = ler(os.path.join(AQUI, "template.html"))
    trocas = {
        "/*__FONTES__*/": fontes(),
        "/*__THREE__*/": ler(os.path.join(NM, "three", "build", "three.min.js")),
        "__FOLHAS__": js(folhas),
        "__LOG__": js(log_mqtt()),
        "__OSM__": js(osm()),
        "__FOTOS__": js(fotos()),
    }
    for chave, valor in trocas.items():
        if chave not in t:
            raise SystemExit(f"template.html sem o marcador {chave}")
        t = t.replace(chave, valor)
    saida = os.path.join(AQUI, "apresentacao-animada.html")
    with open(saida, "w", encoding="utf-8") as f:
        f.write(t)
    with open(os.path.join(os.path.dirname(AQUI), "FOLHAS.md"), "w", encoding="utf-8") as f:
        f.write(folhas_md(folhas))
    total = sum(f["dur"] for f in folhas)
    print(f"ok: {os.path.relpath(saida, RAIZ)} ({len(t) / 1e6:.1f} MB), {len(folhas)} partes, "
          f"{total // 60}:{total % 60:02d} min; docs/FOLHAS.md")


if __name__ == "__main__":
    main()
