# SmartPark 2.0: guia para apresentar

Mesmo formato do TDE de Web: primeiro como usar a apresentação animada, depois a cola rápida, as partes, o glossário e as perguntas do professor com resposta pronta. As folhas por parte estão em `FOLHAS.md` (geradas de `docs/apresentacao/folhas.json`).

## Como usar

**A apresentação animada** (`docs/apresentacao/apresentacao-animada.html`, um arquivo só, abre offline em qualquer navegador):

| Tecla | Faz |
|---|---|
| Espaço | começa; depois pausa e continua |
| → | pula para o começo da próxima parte |
| ← | volta ao começo da parte (se ela começou há menos de 2 s, vai para a anterior) |
| R | reinicia do zero |
| N | abre as notas do apresentador numa janela separada (Na tela, Falar, Mais para falar, Se perguntarem), sincronizada com a parte atual; as teclas também funcionam com a janela de notas em foco |

São 16 partes, 4:59 no total: abertura 3D, problema, de onde viemos, arquitetura, publicar × assinar, as 8 integrações, ciclo CPS, respostas do item 9 e fechamento. Abra em tela cheia, aperte N, arraste a janela de notas para o outro monitor (ou para o lado) e aperte Espaço. `?parte=5` na URL começa na parte 6 (conta do zero).

As mensagens das integrações são o log real de `sim/teste_integracao.py` (os três `main.py` rodando contra o broker), copiado para `docs/apresentacao/mqtt-log.jsonl`. O 3D usa os prédios do OpenStreetMap (`docs/apresentacao/puc-osm.json`).

**Gerar de novo** (depois de mudar `folhas.json` ou `template.html`):

```bash
cd docs/apresentacao
npm install                 # uma vez: three, fontes Inter e JetBrains Mono, playwright-core
python3 build.py            # apresentacao-animada.html e ../FOLHAS.md
node render.mjs --partes abertura,arquitetura --saida abertura.mp4   # 48 s
node render.mjs --saida motion.mp4                                   # as 16 partes, ~10 min para renderizar
node render.mjs --quadros 3,96,150 --pasta frames                    # PNGs para conferir o layout
```

O `render.mjs` usa o Brave (ou o Chrome) sem janela, chama `window.renderAt(t)` quadro a quadro (30 fps, 1920x1080) e manda para o ffmpeg: o vídeo sai igual toda vez.

**Gravar a demonstração e narrar:** siga `video/roteiro.md` cena por cena. Para cada cena, grave a tela (Cmd+Shift+5) como `video/gravacoes/cenaNN.mov` e leia o bloco **Fala** no QuickTime (Arquivo → Nova Gravação de Áudio), salvando `video/gravacoes/falaNN.m4a`. Narração da abertura (opcional): `fala00.m4a`.

**Montar o vídeo final:**

```bash
video/montar.sh                    # abertura.mp4 + cenas 01 a 12 → video/smartpark-final.mp4
video/montar.sh --intro motion     # usa a apresentação animada inteira no lugar da abertura
video/montar.sh --parcial          # monta só com o que já foi gravado
```

O script põe tudo em 1920x1080 a 30 fps, troca o áudio da gravação pela fala, congela o último quadro se a fala for mais longa e mostra o título da cena no canto nos primeiros segundos. Se faltar arquivo, ele lista o que falta e para.

**Apresentando ao vivo:** a apresentação animada no telão, as notas (N) na sua tela; nas integrações, pause (Espaço) para responder pergunta. Se o professor pedir para ver rodando, troque para as janelas do Wokwi e siga as cenas 02 a 11 do roteiro.

## Cola rápida (para decorar)

**A frase de abertura**
> "O SmartPark 2.0 é o estacionamento da PUC sem parar na cancela: a vaga é medida uma a uma, a câmera lê a placa e a cancela avisa quando falha. São três sistemas ciberfísicos que só conversam por MQTT."

**De onde viemos (SmartPark 2026.1, Fundamentos de SCF)**
- 1 ESP32, 2 HC-SR04, LEDs por vaga e buzzer de lotado; só **publicava** (`smartpark/puc/vaga1`, `vaga2` em texto 0/1 e `status` num JSON simples) para um dashboard em Processing. Nenhuma assinatura.
- Reaproveitado (marcado no topo de cada `main.py`): `medir_distancia()` no CPS1 e no CPS2, `atualizar_led()` no CPS1, `conectar_wifi()` nos três, o buzzer em PWM no CPS2 e a ideia do totem de vagas (`Old/imgs/puc-totem-vagas.jpg`), que virou o CPS3.
- Novo: três ESP32 que publicam e assinam, 14 tópicos em JSON, Last Will e retain, reconexão com re-assinatura, 4 vagas com tipo, câmera de placa simulada, fim de curso com alarmes e dashboard com comandos.

**Os três sistemas, uma linha cada**
- **CPS1 Vagas:** HC-SR04 em cada vaga → LED verde ou vermelho → publica as vagas livres.
- **CPS2 Cancela:** câmera lê a placa → decide → servo abre ou nega com buzzer; detecta cancela travada e evasão.
- **CPS3 Totem:** mostra as vagas livres no display, na fita de LEDs e no LED; botão de ajuda chama o operador.

**O caminho de uma mensagem**
- ESP32 publica em `cscf/smartpark/cps1/sensor` → o broker HiveMQ recebe → entrega a todos que assinaram esse tópico (CPS2, CPS3 e dashboard).
- Ninguém fala direto com ninguém: só com o broker.

**As integrações que a demo mostra**
1. Vagas → totem: número, fita e LED mudam sozinhos.
2. Lotado → cancela nega (PcD e idoso ainda entram na vaga do seu tipo).
3. Vagas × entradas → alarme de evasão.
4. Cancela travada → totem pisca.
5. Pagamento pelo celular → saída abre.
6. Emergência → tudo abre e pisca.
7. Ajuda no totem → operador atende → LED azul aceso.
8. CPS1 cai → totem mostra `----` (Last Will).

**MQTT em 5 palavras:** broker · publicar · assinar · retain · Last Will.

## Partes da apresentação animada (ver `FOLHAS.md`)

| Parte | Na tela | Falar (resumo) |
|---|---|---|
| 1 Abertura (24 s) | voo 3D sobre a PUC (OpenStreetMap) até os bolsões | o que é o SmartPark 2.0 |
| 2 Problema (22 s) | foto do totem E03, hoje × SmartPark | contagem por bolsão, carteirinha na cancela, sem autodiagnóstico de cancela divulgado |
| 3 De onde viemos (28 s) | fotos do 2026.1, reuso e novo | o que foi reaproveitado, função por função |
| 4 Arquitetura (24 s) | 3 ESP32, broker, dashboard; ping do verify | tudo passa pelo broker; TCP 1883 e WSS 8884 |
| 5 Publicar × assinar (28 s) | SUBSCRIBE, PUBLISH, dashboard publica; QoS, retain, Last Will | papel do broker |
| 6 a 13 Integrações (101 s) | as 8 integrações com o JSON real do teste | o dado de um CPS muda o atuador de outro |
| 14 Ciclo CPS (22 s) | aquisição → processamento → conectividade → atuação → realimentação | item 6 |
| 15 Item 9 (38 s) | as 7 perguntas com resposta curta | item 9 |
| 16 Fechamento (12 s) | 3 ESP32 · 1 broker · 1 dashboard · 14 tópicos · 8 integrações | MQTT em 5 palavras |

## Cenas do vídeo da demonstração (ordem de `video/roteiro.md`)

| Cena | Na tela | Falar (resumo) |
|---|---|---|
| 01 | três Wokwi e o dashboard, os três `online` | três CPS, um broker; retain e Last Will |
| 02 | carro na cancela, câmera lê `ABC1D23`, servo abre | a regra fica no ESP32 da cancela |
| 03 | V1 ocupada, totem vai para 3 e a fita fica vermelha | ciclo CPS e o caminho de uma mensagem |
| 04 | câmera do dashboard manda `XYZ9K87` (avulso); V2 ocupada | acionamento remoto pelo `cps2/comando` |
| 05 | `QWE4R56` negada por lotado com buzzer; `PUC0R26` (PcD) entra | o dado do CPS1 decide a ação do CPS2 |
| 06 | V3 ocupada sem passar pela cancela → alarme de evasão | vagas × entradas |
| 07 | avulso negado, paga pelo celular, sai; `ABC1D23` sai com débito | o dashboard também publica |
| 08 | dashboard abre a cancela; fim de curso continua aberto → alarme | autodiagnóstico da cancela |
| 09 | emergência pelo dashboard: cancela aberta, LEDs e fita piscando | um comando, três sistemas |
| 10 | ajuda no totem → atender → LED azul; interditar V3 | comandos com QoS 1 sem retain |
| 11 | parar o CPS1 → `offline`, totem `----`; volta | Last Will e reconexão |
| 12 | log de mensagens | item 9 completo |

## Glossário rápido

- **Broker:** servidor que recebe toda mensagem e entrega a quem assinou o tópico. Aqui, o HiveMQ público.
- **Tópico:** endereço da mensagem, em níveis separados por `/` (`cscf/smartpark/cps2/estado`).
- **Publicar:** mandar uma mensagem para um tópico. Quem publica não sabe quem vai receber.
- **Assinar:** pedir ao broker para receber tudo o que chegar num tópico. `#` assina todos os níveis abaixo.
- **QoS 0 / 1:** 0 entrega no máximo uma vez, sem confirmação (leituras periódicas); 1 entrega pelo menos uma vez, com confirmação (comandos, pagamento, alarmes).
- **Retain:** o broker guarda a última mensagem do tópico e entrega na hora a quem assinar depois. Por isso o dashboard abre já com as vagas.
- **Last Will (LWT):** mensagem que o ESP32 deixa com o broker ao conectar; se ele cair sem avisar, o broker publica `offline` por ele.
- **Keepalive / ping:** o ESP32 dá sinal de vida de tempos em tempos; sem sinal, o broker considera que caiu e solta o Last Will.
- **client_id:** nome único de cada conexão; dois iguais derrubam um ao outro.
- **WebSocket:** como o navegador fala MQTT (porta 8884, `wss`).

## As 7 perguntas do item 9, com resposta

**1. Qual é a função do broker e como ele encaminha as mensagens?**
> O broker é o intermediário: todos os ESP32 e o dashboard conectam nele e em mais ninguém. Quando chega uma mensagem num tópico, ele entrega uma cópia para cada cliente que assinou aquele tópico. Ele também guarda as mensagens retidas e publica o Last Will de quem cai.

**2. Qual é a diferença entre publicar e assinar?**
> Publicar é enviar uma mensagem para um tópico. Assinar é avisar o broker que quero receber o que chegar num tópico. O CPS1 publica as vagas; o CPS2, o CPS3 e o dashboard assinam. Quem publica não conhece quem assina.

**3. Quais tópicos são usados e quem publica e assina cada um?**
> Cada CPS tem `sensor`, `estado`, `comando` e `status`; o CPS2 tem também `alarme`; e há o `pagamento`. A tabela completa está em `docs/topicos.md`. Exemplo: `cps1/sensor` é publicado pelo CPS1 e assinado pelo CPS2, pelo CPS3 e pelo dashboard.

**4. Como uma mensagem enviada por um sistema chega aos demais?**
> O CPS1 detecta a vaga ocupada e publica em `cps1/sensor`. O broker recebe e repassa para os assinantes. O CPS2 recebe no callback, atualiza quantas vagas comuns estão livres e passa a negar a entrada se chegar a zero. O CPS3 recebe a mesma mensagem e muda o display e a fita.

**5. Como a informação recebida pela rede aciona um atuador?**
> No callback do `umqtt` (chamado dentro do `check_msg()`), o ESP32 lê o JSON e atualiza o estado; o loop principal decide o atuador. O CPS2 guarda o `cps1/sensor` e só gira o servo se há vaga do tipo da placa (placa sem cadastro entra como avulso, tipo comum); comandos do dashboard vão para uma fila e são executados no loop, fora do callback. O CPS3 recebe o `cps1/sensor` e reescreve display, LED e fita; o CPS1 recebe o `cps2/estado` e pisca os LEDs na emergência. A decisão usa um dado que veio de outro ESP32 pela rede.

**6. Como o dashboard participa da comunicação MQTT?**
> Ele é só mais um cliente do broker, pelo WebSocket seguro (`wss`, porta 8884), com `client_id` único por aba. Assina `cscf/smartpark/#` para mostrar tudo e publica nos tópicos `comando` (câmera simulada, abrir cancela, emergência, interditar vaga, atender ajuda, brilho) e `pagamento`. Não fala direto com nenhum ESP32.

**7. Quais as vantagens do MQTT em sistemas ciberfísicos distribuídos?**
> É leve (cabeçalho de 2 bytes, bom para microcontrolador), desacopla quem publica de quem assina (dá para adicionar um quarto CPS sem mudar os outros), tem QoS para mensagens importantes, retain para o estado atual e Last Will para detectar falha. Funciona em rede instável porque o cliente reconecta e o broker guarda o estado.

## Outras perguntas prováveis

**Por que não usar HTTP?**
> No HTTP, cada sistema teria que perguntar ao outro de tempos em tempos. No MQTT, a mensagem chega na hora para todos os interessados, por uma conexão só.

**E se o broker cair?**
> Tudo para de se comunicar, mas cada ESP32 continua com as regras locais (o CPS1 ainda acende os LEDs, a cancela decide com as últimas vagas recebidas) e tenta reconectar a cada 5 s sem travar. Em produção usaríamos um broker próprio ou em cluster; aqui a reserva é manual: trocar a constante `BROKER` para o EMQX.

**Por que a placa no broker público?**
> São placas fictícias. Em produção, placa é dado pessoal pela LGPD: usaríamos um ID pseudônimo e um broker com usuário e TLS.

**A PUC já não tem contagem de vagas?**
> Tem, por bolsão, e tem app e autoatendimento. O SmartPark mede cada vaga, troca a carteirinha pela placa e dá à cancela um autodiagnóstico.

**Por que a câmera é simulada?**
> O Wokwi não tem câmera. O HC-SR04 faz o papel do sensor de presença que dispara a câmera, e os botões ou o dashboard fazem o papel da leitura da placa.
