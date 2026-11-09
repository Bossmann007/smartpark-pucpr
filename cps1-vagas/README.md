# CPS1 · Vagas

Mede as 4 vagas com HC-SR04 e acende o LED verde (livre) ou vermelho (ocupada). Publica as vagas livres por tipo; a cancela (CPS2) e o totem (CPS3) usam esse dado.

- Link do Wokwi: https://wokwi.com/projects/480003924044144641
- Arquivos: `main.py`, `diagram.json`
- Ocupada abaixo de 50 cm, livre acima de 60 cm (histerese). No Wokwi, clique no HC-SR04 e mova o slider.

| Vaga | Tipo | TRIG | ECHO | LED verde | LED vermelho |
|---|---|---|---|---|---|
| V1 | comum | D5 | D34 | D2 | D22 |
| V2 | comum | D18 | D35 | D4 | D23 |
| V3 | idoso | D19 | D32 | RX2 (GPIO16) | D25 |
| V4 | PcD | D21 | D33 | TX2 (GPIO17) | D26 |

- Publica: `cps1/sensor`, `cps1/estado`, `cps1/status` (Last Will)
- Assina: `cps1/comando` (interditar vaga, ping), `cps2/estado` (emergência: LEDs piscam)
- Reaproveitado de `Old/main.py`: `medir_distancia()`, `atualizar_led()`, `conectar_wifi()`
