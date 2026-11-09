# Arquitetura de conectividade

Segue o modelo do enunciado: três CPS no topo, todos publicando e assinando no broker, e o dashboard abaixo. Nenhum sistema fala direto com outro; toda mensagem passa pelo broker.

Imagem para a entrega: `docs/arquitetura.png` (gerada deste diagrama com `mmdc`).

```mermaid
flowchart TB
  subgraph CPS[" "]
    direction LR
    CPS1["<b>CPS 1 · Vagas</b><br/>Wokwi + ESP32<br/>MicroPython<br/>4× HC-SR04 / 8 LEDs (verde e vermelho por vaga)<br/><b>PUB + SUB</b>"]
    CPS2["<b>CPS 2 · Cancela</b><br/>Wokwi + ESP32<br/>MicroPython<br/>HC-SR04, câmera simulada, sentido, fim de curso / servo, buzzer<br/><b>PUB + SUB</b>"]
    CPS3["<b>CPS 3 · Totem</b><br/>Wokwi + ESP32<br/>MicroPython<br/>botão de ajuda, PIR / display 7 seg, LEDs, fita NeoPixel<br/><b>PUB + SUB</b>"]
  end
  B(["<b>BROKER MQTT</b><br/>broker.hivemq.com<br/>recebe e distribui mensagens<br/>tópicos cscf/equipe03/…"])
  D["<b>DASHBOARD</b><br/>HTML + MQTT.js (WebSocket)<br/>monitoramento + comandos<br/><b>PUB + SUB</b>"]
  CPS1 <-->|"TCP 1883"| B
  CPS2 <-->|"TCP 1883"| B
  CPS3 <-->|"TCP 1883"| B
  B <-->|"WSS 8884"| D
```

## Fluxos de integração (todos passando pelo broker)

![Fluxos de comunicação](fluxos.png)

Quem publica e quem assina cada tópico, e o que cada assinatura faz no atuador (imagem gerada com `mmdc`).

```mermaid
%%{init: {"flowchart": {"curve": "step", "nodeSpacing": 40, "rankSpacing": 90}, "themeVariables": {"edgeLabelBackground": "#d9d9d9"}}}%%
flowchart TB
  C1["<b>CPS1 Vagas</b><br/>HC-SR04 ×4 → LEDs"]
  B(("<b>Broker MQTT</b><br/>HiveMQ"))
  C2["<b>CPS2 Cancela</b><br/>câmera, HC-SR04, fim de curso<br/>→ servo, buzzer"]
  C3["<b>CPS3 Totem</b><br/>PIR, ajuda<br/>→ display, LEDs, fita"]
  D["<b>Dashboard</b><br/>MQTT.js"]
  C1 -->|"PUB cps1/sensor<br/>cps1/estado<br/>cps1/status"| B
  B -->|"SUB cps1/comando, cps2/estado<br/>→ interditar, emergência"| C1
  C2 -->|"PUB cps2/sensor<br/>cps2/estado<br/>cps2/alarme<br/>cps2/status"| B
  B -->|"SUB cps1/sensor, cps1/status,<br/>cps3/sensor, cps2/comando, pagamento<br/>→ lotado, evasão, vaga PcD irregular,<br/>bip da ajuda, saída paga"| C2
  C3 -->|"PUB cps3/sensor<br/>cps3/estado<br/>cps3/status"| B
  B -->|"SUB cps1/sensor, cps1/status,<br/>cps2/alarme, cps2/estado, cps3/comando<br/>→ número, cores, ----, alarme"| C3
  D -->|"PUB cpsN/comando,<br/>pagamento"| B
  B -->|"SUB cscf/equipe03/#"| D
```

| De | Tópico | Para | Efeito |
|---|---|---|---|
| CPS1 | `cps1/sensor` | CPS2 | lotado por tipo → cancela nega; vagas × `dentro` → evasão e vaga PcD irregular |
| CPS1 | `cps1/sensor`, `cps1/status` | CPS3 | display, LED e fita; `----` se o CPS1 cai |
| CPS2 | `cps2/alarme` | CPS3, dashboard | cancela travada, evasão ou vaga PcD irregular → LED piscando e alarme |
| CPS2 | `cps2/estado` | CPS1 | emergência → LEDs das vagas piscam |
| CPS3 | `cps3/sensor` | CPS2, dashboard | pedido de ajuda → bip na cancela e chamado no dashboard |
| CPS1 | `cps1/status` (Last Will) | CPS2 | CPS1 caiu → cancela esquece as vagas velhas e não nega por lotado |
| Dashboard | `cpsN/comando`, `pagamento` | CPS1, CPS2, CPS3 | interditar vaga, câmera, abrir cancela, emergência, pagamento, atender ajuda |

Tabela completa de tópicos: `docs/topicos.md`.

Ciclo CPS (item 6): aquisição (sensores) → processamento (ESP32 decide) → conectividade (MQTT pelo broker) → atuação (cancela, LEDs, display, fita) → realimentação (estado publicado com retain para os outros e o dashboard).
