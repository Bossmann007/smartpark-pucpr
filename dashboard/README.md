# Dashboard

Um único arquivo, `index.html`: HTML, CSS e JavaScript juntos, sem build e sem framework. As bibliotecas vêm de CDN, com versão fixa:

- MQTT.js 5.16.1 (`unpkg.com/mqtt@5.16.1`), que conecta ao broker por WebSocket
- Three.js 0.170.0 (`unpkg.com/three@0.170.0`), usado no gêmeo digital 3D
- MapLibre GL 5.6.0 com o estilo gratuito OpenFreeMap `liberty`, usado no mapa da PUC. Só carrega quando a aba do mapa é aberta.

Tudo o que aparece na tela vem do broker. O dashboard segue `docs/topicos.md`: assina `<prefixo>/#` e publica comandos com QoS 1, sem retain.

## Como abrir

O navegador bloqueia módulos ES abertos por `file://`, então sirva a pasta:

```bash
cd dashboard
python3 -m http.server 8000
# abrir http://localhost:8000/
```

Também funciona publicado em qualquer hospedagem estática (GitHub Pages, Vercel). Em HTTPS o broker precisa ser `wss://`. O padrão já é esse.

## Parâmetros na URL

| Parâmetro | Padrão | Exemplo |
|---|---|---|
| `broker` | `wss://broker.hivemq.com:8884/mqtt` | `?broker=wss://test.mosquitto.org:8081` |
| `prefixo` | `cscf/smartpark` | `?prefixo=cscf/equipe7` |
| `pagina` | operador | `?pagina=pagar` abre só a página do motorista; `?pagina=mapa` abre o mapa |

O `client_id` é `smartpark-dash-` mais um número aleatório. Cada aba tem o seu, senão o broker derruba a aba anterior. Se a conexão cai, o MQTT.js reconecta sozinho a cada 2 s (`reconnectPeriod`) e assina de novo.

## O que tem na tela

**Operador** (página inicial)

- Topo: status online/offline do CPS1 Vagas, CPS2 Cancela e CPS3 Totem (`cpsN/status`, Last Will retido) e o estado da conexão com o broker.
- Indicadores: vagas livres (com gráfico da sessão e a divisão por tipo), carros dentro, cancela aberta/fechada e alarmes ativos.
- Gêmeo digital 3D: as 4 vagas com a cor do tipo (verde comum, amarelo idoso, azul PcD; vermelho ocupada, laranja interditada), carros nas vagas ocupadas, carro parado na cancela, braço da cancela que abre e fecha pelo `cps2/estado`, totem com o número e a fita. Cada mensagem MQTT vira uma luz que sai do ESP32, passa pelo broker e chega em quem assina aquele tópico. A câmera gira sozinha; dá para arrastar e dar zoom.
- CPS1: cada vaga com tipo, ocupada/livre/interditada, distância medida e LED (`cps1/estado`). Botão **Interditar/Liberar** publica `{"manutencao": "V2", "ativo": true|false}` em `cps1/comando`.
- CPS2: cancela, fim de curso, modo, carro na cancela, sentido, quantos estão dentro e as placas (cadastrada, avulso a pagar, avulso pago), travada e evasão. Botões **Abrir cancela** (`{"cancela": "abrir"}`) e **Emergência** (`{"modo": "emergencia"}` / `{"modo": "normal"}`). **Câmera (simulada)**: placa e sentido viram `{"placa", "sentido"}` em `cps2/comando`. O CPS2 só lê a placa se o sensor vê um carro na cancela.
- CPS3: espelho do totem com o display de 7 segmentos (ou `----`), o LED, as 4 cores da fita (piscando quando `fita_pisca`), ajuda, brilho e presença. **Atender ajuda** (`{"ajuda": "atendido"}`) fica destacado quando há chamado; brilho **Alto/Baixo/Auto (PIR)**.
- Alarmes: cancela travada, evasão (com a diferença), pedido de ajuda, emergência e ESP32 offline, enquanto estiverem ativos.
- Interação entre sistemas: linha do tempo em português dos eventos do `cps2/sensor` e das mudanças que um sistema causa no outro, por exemplo "CPS1 lotado, CPS2 negou QWE4R56", cada um com os sistemas envolvidos.
- Log MQTT: as últimas 100 mensagens (hora, tópico sem prefixo, R para retida, payload), com filtro por texto e por sistema.

**Pagar pelo celular** (`?pagina=pagar` ou a aba)

Página para celular: mostra as vagas livres, lista as placas que estão dentro como avulso e ainda não pagaram (do `cps2/estado`), cobra R$ 7,00 e publica `{"placa": "XYZ9K87", "valor": 7.0}` em `<prefixo>/pagamento`. A confirmação só aparece quando o CPS2 responde `{"evento": "pagamento", "ok": true}` para aquela placa.

**Mapa da PUC** (extra)

Campus em 3D com os prédios do OpenStreetMap (PUCPR Curitiba, Nominatim: -25.4524, -49.2513) e um marcador no estacionamento E 11 com as vagas livres ao vivo do `cps1/sensor`. O marcador avisa "demo: bolsão simulado".

## Rubrica (item 5, Dashboard MQTT)

| O que a rubrica pede | Onde está |
|---|---|
| Mostrar dados dos sensores dos 3 sistemas | Cartões CPS1 (HC-SR04 de cada vaga), CPS2 (HC-SR04 da cancela, fim de curso, chave de sentido), CPS3 (PIR, botão de ajuda) |
| Identificar cada sistema | Cor e nome fixos (CPS1 azul, CPS2 laranja, CPS3 verde-água) no topo, nos cartões, no 3D e na linha do tempo |
| Atualizar ao vivo pelo MQTT | Tudo vem de mensagens; nada é simulado na página |
| Mostrar o estado dos atuadores | LEDs das vagas, braço da cancela (servo), display, LED e fita do totem, no cartão e no 3D |
| Enviar comandos aos atuadores dos 3 | Interditar/Liberar (CPS1); abrir, emergência e câmera (CPS2); atender ajuda e brilho (CPS3) |
| Mostrar interação entre sistemas | Linha do tempo "Interação entre sistemas" e as luzes no 3D indo de um ESP32 ao broker e aos outros |

## Teste

Testado com os três firmwares reais rodando no MicroPython do Mac (`sim/rodar.py`) e o navegador comandado pelo Playwright: status online, vaga ocupada no cartão e no 3D, entrada pela câmera, lotado, interdição, emergência, cancela travada, ajuda atendida, brilho, pagamento e saída do avulso. As capturas estão em `screenshots/`.

Para depurar no console do navegador: `smartpark.estado` mostra o estado atual e `smartpark.gemeo().resumo()` mostra o que o 3D está desenhando.
