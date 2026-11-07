# SPEC · SmartPark 2.0 (Projeto CSCF 2026.2)

Fonte do requisito: enunciado do Projeto Final no Canvas (cópia local fora do repo). Desenho: `docs/topicos.md` (tópicos e integrações), `docs/funcionamento.md` (regras por CPS). Pesquisa: `docs/pesquisa.md`. Reuso da versão 2026.1: `docs/reuso.md`.

## Decisões fechadas (06/11/2026)

- Mesma cancela para entrada e saída, com chave de sentido.
- Placa sem cadastro entra como avulso; sai só depois do pagamento.
- Lotado conta por tipo de vaga (comum, idoso, PcD).
- 3D: testar Google 3D Tiles da PUC; se não houver cobertura, chave ou termos, OpenStreetMap via Blender.
- O repositório tem o gabarito completo (fonte da verdade). Enzo refaz cada CPS no Wokwi seguindo o gabarito, passo a passo.
- Conteúdo de 2026.1 vai para `Old/` sem alteração; o que é reaproveitado fica marcado no código, em `docs/reuso.md` e na apresentação.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `cps1-vagas/main.py`, `diagram.json` | 4 HC-SR04, 4 LEDs bicolor |
| `cps2-cancela/main.py`, `diagram.json` | HC-SR04, 3 botões, 2 slide switches, servo, buzzer |
| `cps3-totem/main.py`, `tm1637.py`, `diagram.json` | botão, PIR, TM1637, LEDs, NeoPixel ×4 |
| `sim/lib/*.py`, `sim/teste_integracao.py`, `sim/rodar.py` | hardware falso e teste de integração no MicroPython do computador |
| `scripts/verify` | prova por MQTT contra os Wokwi reais |
| `dashboard/index.html` | MQTT.js, operador, câmera, pagar pelo celular |
| `docs/`, `video/`, `docs/APRESENTACAO.md` | entregas e guia de fala |

## Esqueleto comum (todo `main.py`)

1. Wi-Fi `Wokwi-GUEST`, sem senha.
2. `client_id` único (`smartpark-cps1-<aleatório>`).
3. `set_last_will(status, "offline", retain=True, qos=1)` antes de `connect()`; depois `publish(status, "online", retain=True)`.
4. `set_callback` e `subscribe` do próprio `comando` e dos tópicos dos outros.
5. Loop: ler sensores → decidir → atuar → publicar se mudou → `check_msg()` → `ping()` a cada 10 s (keepalive 30 s). Estado com QoS 0 + retain (não trava o loop); eventos, alarmes e comandos com QoS 1. Botões por `Pin.irq`.
6. Exceção de rede → `cliente = None` e a parte local continua; `tentar_conectar()` a cada 5 s refaz Wi-Fi, connect, LWT, `online` e todas as assinaturas.
7. `{"ping": X}` no `comando` → republica `estado` com `"ack": X`.

## Fora do escopo

Pagamento real, câmera real, placas reais, login, banco de dados, hardware físico.

## Pronto quando

1. `uv run sim/teste_integracao.py` sai com 0 (feito: 0 falhas em 48 s, 06/11/2026, depois das reviews).
2. `scripts/verify` sai com 0 contra os três Wokwi rodando (prefixo real).
3. Cada integração de `docs/topicos.md` foi vista acontecer uma vez e está no vídeo.
4. Os 3 links Wokwi abrem em janela anônima.

## Cortes, nesta ordem, se o tempo acabar

1. Abertura motion graphics renderizada.
2. 3D real (fica OSM ou mapa 2D).
3. Evasão.
4. NeoPixel (ficam LEDs comuns) e TM1637 (fica o LCD ou só LEDs).

Núcleo que não se corta: MQTT nos 3 com LWT e reconexão, lotado → cancela, câmera → cancela, pagamento → saída, dashboard com comandos.
