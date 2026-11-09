# Roteiro de gravação do vídeo da demonstração

O enunciado (item 7) pede que o vídeo mostre: os três projetos Wokwi funcionando, as mensagens MQTT sendo transmitidas, o dashboard atualizando, o acionamento remoto dos atuadores e pelo menos uma interação entre os sistemas. O item 9 pede que a equipe explique o broker, publicar × assinar, os tópicos, o caminho de uma mensagem, como a mensagem recebida aciona um atuador, o papel do dashboard e as vantagens do MQTT.

Este roteiro é a ordem exata da gravação. Cada cena vira dois arquivos em `video/gravacoes/`: `cenaNN.mov` (gravação da tela) e `falaNN.m4a` (narração lida do bloco **Fala**). O `video/montar.sh` junta tudo com a abertura animada. Os títulos das cenas (`## Cena NN · …`) viram a legenda no canto da tela: não mude o formato da linha.

| O que o enunciado pede | Onde aparece |
|---|---|
| Três Wokwi funcionando | Cena 01 (e todas as outras) |
| Mensagens MQTT transmitidas | painel **Log MQTT** do dashboard em todas as cenas; Cena 13 |
| Dashboard atualizando | Cenas 02 a 12 |
| Acionamento remoto de atuadores | Cena 04 (câmera do dashboard abre o servo), 07 (pagamento abre a saída), 09 (emergência), 10 (atender ajuda acende o LED azul; interditar vaga pisca o LED) |
| Interação entre sistemas | Cenas 03 (vagas → totem), 05 (lotado → cancela), 06 (evasão), 08 (cancela travada → totem), 09 (emergência → os três), 11 (vaga PcD irregular → totem), 12 (Last Will → totem) |
| Explicações do item 9 | Cenas 01, 03, 05, 13 (e a abertura animada) |

## Antes de gravar (uma vez)

1. Terminal na raiz do repo: `uv run scripts/limpar_retidos.py --prefix cscf/equipe03` (começa sem estado velho no broker).
2. Abrir os três projetos Wokwi, **cada um numa janela própria** (não em abas: aba escondida pausa a simulação). Lado a lado, em cima: CPS1 · Vagas, CPS2 · Cancela, CPS3 · Totem. Embaixo, ou numa quarta janela, o dashboard: rode `python3 -m http.server 8000 --directory dashboard` dentro de `smartpark-pucpr` e abra http://localhost:8000 (aberto direto pelo arquivo, o navegador bloqueia o `codigos/index.js`).
3. Dar play nos três. Esperar no console serial de cada um: `MQTT conectado como smartpark-cpsN-…`.
4. Conferir: `scripts/verify` sai com 0 (os três `online`, 4 vagas, resposta ao `ping`). Se não sair com 0, não grave.
5. Estado inicial no Wokwi: todos os HC-SR04 em 400 cm (vagas livres, nenhum carro na cancela); no CPS2 as duas chaves à esquerda (sentido = entrada, fim de curso = fechada).
6. Gravar a tela: Cmd+Shift+5 → "Gravar a tela inteira" (ou a área das quatro janelas). Uma gravação por cena, salva como `video/gravacoes/cenaNN.mov`.
7. Narração: depois de gravar cada cena, ler o bloco **Fala** no QuickTime (Arquivo → Nova Gravação de Áudio) e exportar como `video/gravacoes/falaNN.m4a`. Se a fala ficar mais longa que a cena, o `montar.sh` congela o último quadro até a fala terminar; se ficar mais curta, a cena segue sem som até o fim.

Nomes no dashboard (`dashboard/index.html`): abas **Operador**, **Pagar pelo celular** e **Mapa da PUC**; na aba Operador, os cartões **CPS1 Vagas**, **CPS2 Cancela** e **CPS3 Totem**, o **Gêmeo digital** 3D, os painéis **Alarmes**, **Interação entre sistemas** e **Log MQTT**, e o formulário **Câmera (simulada)** com o botão **Enviar leitura**.

Como mexer no Wokwi durante a simulação: clicar no HC-SR04 abre o controle deslizante de distância; clicar na chave deslizante muda o lado; clicar no botão aperta; clicar no PIR mostra "Simulate motion".

## Narração gravada (07/11/2026)

Cada fala fica em `video/gravacoes/falaNN.m4a` (fora do git). Grave cada cena de tela com **pelo menos** a duração da fala; o `montar.sh` congela o último quadro se o vídeo for mais curto.

| Fala | Situação |
|---|---|
| 00 | opcional (narração da abertura; sem ela a abertura sai muda) |
| 01 a 10 | gravadas |
| 11 | gravar (cena nova: vaga PcD irregular) |
| 12 | gravar (era a 11; o texto ganhou a cancela esquecendo as vagas velhas) |
| 13 | gravar (era a 12; QoS 1 explicado direito) |

As telas das cenas 02 a 12 precisam ser regravadas com o código novo no Wokwi (o console antigo mostra "JSON invalido"). A tela da cena 13 é o motion, já pronta em `video/gravacoes/cena13.mp4`.

## Cena 01 · Os três ESP32 no ar

- **Na tela:** as três janelas do Wokwi rodando e o dashboard. No dashboard, o painel de status com CPS1, CPS2 e CPS3 `online`.
- **Ações:**
  1. Começar com as quatro janelas visíveis, sem mexer em nada (3 s).
  2. Passar o mouse pelo console serial de cada Wokwi mostrando `MQTT conectado como …`.
  3. Apontar o status `online` dos três no dashboard e o número 4 no display do totem (CPS3).
- **Duração:** 20 s.
- **Fala:**
  > "Estes são os três sistemas ciberfísicos do SmartPark rodando no Wokwi, cada um com o seu ESP32 e MicroPython: o CPS1 mede as vagas, o CPS2 é o módulo da cancela e o CPS3 é o totem da entrada. Os três estão conectados no broker público da HiveMQ. Nenhum fala direto com o outro: todos só publicam e assinam tópicos no broker. O dashboard é mais um cliente desse broker. O online de cada um foi publicado com retain, e cada ESP32 deixou um Last Will com o broker: se ele cair, o broker publica offline por ele."

## Cena 02 · Entrada pela placa cadastrada

- **Na tela:** janela do CPS2 em destaque; dashboard com o estado da cancela, o contador `dentro` e o **Log MQTT**.
- **Ações:**
  1. CPS2: confirmar a chave de sentido à esquerda (entrada).
  2. CPS2: clicar no HC-SR04 e baixar a distância para 20 cm (carro parado na cancela).
  3. CPS2: apertar o botão verde **Câmera: ABC1D23**.
  4. Mostrar o servo girando (cancela aberta) e, no dashboard, o evento `entrada ABC1D23` e `dentro = 1`.
  5. Esperar a cancela fechar sozinha (5 s) e subir a distância do HC-SR04 do CPS2 para 400 cm (o carro passou).
- **Duração:** 25 s.
- **Fala:**
  > "Um carro para na cancela: o HC-SR04 do CPS2 vê o carro e dispara a câmera. O Wokwi não tem câmera, então cada botão é a câmera lendo uma placa de teste. A ABC1D23 é cadastrada: o ESP32 decide sozinho, abre o servo e publica o evento de entrada em cps2/sensor. A regra fica no ESP32 da cancela, por isso ela funciona mesmo com o dashboard fechado. O dashboard assinou esse tópico e mostra um carro dentro."

## Cena 03 · Vagas → totem

- **Na tela:** CPS1 e CPS3 lado a lado; no dashboard, o cartão **CPS1 Vagas** e o **Gêmeo digital**.
- **Ações:**
  1. CPS1: clicar no HC-SR04 da V1 e baixar para 20 cm.
  2. Mostrar o LED da V1 ficando vermelho no CPS1.
  3. Mostrar no CPS3 o display indo de 4 para 3 e o primeiro LED da fita ficando vermelho.
  4. Mostrar no dashboard a V1 ocupada e a mensagem `cps1/sensor` no log.
- **Duração:** 20 s.
- **Fala:**
  > "O carro estaciona na V1. O HC-SR04 mede menos de 50 centímetros: o CPS1 decide que a vaga está ocupada e acende o LED vermelho. Esse é o ciclo ciberfísico: aquisição, processamento e atuação local. Depois vem a conectividade: o CPS1 publica as quatro vagas em cps1/sensor. O broker entrega uma cópia para cada assinante. O totem é um deles: recebe no callback, muda o display para 3 e pinta a vaga de vermelho na fita. O totem não tem sensor de vaga: tudo o que ele mostra chegou pela rede."

## Cena 04 · Placa sem cadastro pela câmera do dashboard

- **Na tela:** dashboard, formulário **Câmera (simulada)** (cartão CPS2 Cancela); CPS2 ao lado.
- **Ações:**
  1. CPS2: HC-SR04 em 20 cm (carro na cancela).
  2. Dashboard, Câmera (simulada): digitar `XYZ9K87`, sentido entrada, **Enviar leitura**.
  3. Mostrar o servo do CPS2 abrindo e o evento `entrada XYZ9K87 · avulso` no dashboard.
  4. Esperar a cancela fechar; CPS2 HC-SR04 de volta a 400 cm.
  5. CPS1: HC-SR04 da V2 em 20 cm. Mostrar o totem indo para 2 e o dashboard com 0 vagas comuns livres.
- **Duração:** 25 s.
- **Fala:**
  > "Agora a placa vem do dashboard: ele publica a leitura da câmera em cps2/comando, e só o CPS2 assina esse tópico. É um acionamento remoto: uma mensagem do dashboard faz o servo abrir. A XYZ9K87 não tem cadastro, então entra como avulso e só vai poder sair depois de pagar. O carro estaciona na V2, e agora as duas vagas comuns estão ocupadas."

## Cena 05 · Lotado → a cancela nega

- **Na tela:** CPS2 em destaque (servo e buzzer); dashboard com o painel **Interação entre sistemas**.
- **Ações:**
  1. CPS2: HC-SR04 em 20 cm.
  2. Dashboard, Câmera (simulada): digitar `QWE4R56`, sentido entrada, **Enviar leitura**.
  3. Mostrar: o servo não se mexe, o buzzer toca e o dashboard registra `negado QWE4R56 · lotado`.
  4. CPS2: apertar o botão azul **Câmera: PUC0R26** (placa PcD). Mostrar o servo abrindo e `entrada PUC0R26`.
  5. Esperar a cancela fechar; CPS2 HC-SR04 em 400 cm. CPS1: HC-SR04 da V4 (PcD) em 20 cm. Totem mostra 1.
- **Duração:** 30 s.
- **Fala:**
  > "Esta é a integração principal. Uma placa comum chega, mas o CPS1 já publicou que não há vaga comum livre. O CPS2 guardou essa mensagem no callback, então nega a entrada e toca o buzzer. A decisão de um ESP32 usou o dado de outro ESP32, que chegou pelo broker. A PUC0R26 é PcD: idoso e PcD usam a vaga do seu tipo, e a V4 está livre, então a cancela abre."

## Cena 06 · Evasão

- **Na tela:** CPS1, CPS3 e o painel **Alarmes** do dashboard. Cancela fechada, nenhum carro na cancela.
- **Ações:**
  1. Mostrar no dashboard `dentro = 3` (ABC1D23, XYZ9K87, PUC0R26) e três vagas ocupadas.
  2. CPS1: HC-SR04 da V3 em 20 cm, **sem** passar nenhum carro pelo CPS2.
  3. Mostrar o LED vermelho do totem piscando e o alarme `evasão` no dashboard.
  4. CPS1: HC-SR04 da V3 de volta a 400 cm. Mostrar o alarme encerrando.
- **Duração:** 20 s.
- **Fala:**
  > "Três carros entraram pela cancela. Agora um quarto carro aparece na V3 sem ter passado por ela. O CPS2 compara as vagas ocupadas, que vêm do CPS1, com os carros que entraram: quatro contra três. Diferença de um: alguém entrou sem registro. O CPS2 publica o alarme de evasão em cps2/alarme, e o totem e o dashboard, que assinam esse tópico, avisam. Nenhum dos dois sistemas sabe disso sozinho."

## Cena 07 · Saída: débito automático e pagamento pelo celular

- **Na tela:** CPS2 e o formulário Câmera (simulada) e a aba **Pagar pelo celular** do dashboard.
- **Ações:**
  1. CPS2: chave de sentido para a direita (saída).
  2. CPS1: HC-SR04 da V2 em 400 cm (o avulso deixou a vaga). CPS2: HC-SR04 em 20 cm.
  3. Dashboard, Câmera (simulada): `XYZ9K87`, sentido saída, **Enviar leitura**. Mostrar `negado · pagamento_pendente` e o buzzer.
  4. Dashboard, aba **Pagar pelo celular**: placa `XYZ9K87`, **Pagar R$ 7,00**. Mostrar `pagamento XYZ9K87 · ok`.
  5. Câmera (simulada) de novo: `XYZ9K87`, saída, **Enviar leitura**. Mostrar o servo abrindo e `saída XYZ9K87`.
  6. Esperar a cancela fechar. CPS1: V1 em 400 cm. CPS2: HC-SR04 em 20 cm e botão verde **Câmera: ABC1D23**. Mostrar `saída ABC1D23` com débito de R$ 5,00 e saldo 45.
  7. CPS2: HC-SR04 em 400 cm.
- **Duração:** 40 s.
- **Fala:**
  > "Na saída, a mesma cancela muda de sentido pela chave. O avulso XYZ9K87 é negado: pagamento pendente. Pelo celular, o dashboard publica no tópico pagamento, com QoS 1: o broker confirma que recebeu e entrega pelo menos uma vez ao CPS2 conectado. O CPS2 assina, marca a placa como paga e confirma. Na segunda leitura a cancela abre. Já a ABC1D23 é cadastrada: sai direto, com débito automático de cinco reais, como o Sem Parar. O pagamento é simulado: nenhuma cobrança real."

## Cena 08 · Cancela travada

- **Na tela:** CPS2 (chave de fim de curso e buzzer), CPS3 e o painel **Alarmes**.
- **Ações:**
  1. Dashboard: clicar em **Abrir cancela** (o servo abre; evento `abertura_manual`).
  2. Com a cancela ainda aberta, mover a chave **Fim de curso** do CPS2 para a direita (aberta), como uma cancela que vai travar.
  3. A cancela fecha sozinha depois de 5 s, mas o fim de curso continua aberto. Esperar 3 s: buzzer toca, LED vermelho do totem piscando, alarme `cancela travada` no dashboard.
  4. Voltar a chave para a esquerda. Mostrar o alarme encerrando.
- **Atenção:** os 3 s contam a partir da ordem de fechar. Se a chave for movida muito depois da cancela fechar, o alarme sai na hora (o código compara com o instante em que mandou fechar).
- **Duração:** 25 s.
- **Fala:**
  > "O operador abre a cancela pelo dashboard: outro acionamento remoto. Quando ela fecha, o fim de curso continua dizendo aberta. Depois de três segundos sem confirmação, o CPS2 toca o buzzer e publica cancela travada. O totem e o dashboard assinam o alarme. É o autodiagnóstico: a própria cancela avisa que não fechou."

## Cena 09 · Emergência pelo dashboard

- **Na tela:** os três Wokwi e o botão Emergência do dashboard.
- **Ações:**
  1. Dashboard: clicar em **Emergência**.
  2. Mostrar: servo do CPS2 aberto e parado, LEDs das vagas do CPS1 piscando, fita do totem piscando em branco.
  3. Dashboard: clicar em **Encerrar emergência**. Mostrar a cancela fechando e os LEDs voltando.
- **Duração:** 20 s.
- **Fala:**
  > "O operador aperta emergência. O dashboard publica um comando só para o CPS2, que abre a cancela e mantém aberta. O CPS2 publica o novo estado, e o CPS1 e o CPS3 assinam esse estado: os LEDs das vagas piscam e a fita do totem pisca em branco. Um comando, três sistemas reagindo pela rede."

## Cena 10 · Ajuda no totem e vaga interditada

- **Na tela:** CPS3 (botão de ajuda e LED azul), CPS1 e o dashboard (alarmes e botões do operador).
- **Ações:**
  1. CPS3: apertar o botão **Ajuda (interfone)**. Mostrar o LED azul piscando, o bip curto no buzzer do CPS2 e o chamado no dashboard.
  2. Dashboard: clicar em **Atender ajuda** (ou **Atender** no painel Alarmes). Mostrar o LED azul aceso (fica 10 s).
  3. Dashboard, cartão CPS1 Vagas: **Interditar** na V3. Mostrar o LED da V3 piscando no CPS1, a V3 laranja na fita do totem e o número de livres caindo.
  4. Dashboard: **Liberar** na V3.
- **Duração:** 30 s.
- **Fala:**
  > "O motorista aperta ajuda no totem. O CPS3 publica em cps3/sensor e o LED azul pisca enquanto espera. O CPS2 assina esse tópico e dá um bip na cancela, onde fica o operador: é o totem mudando outro ESP32. O operador vê o chamado e clica em atender: o dashboard publica em cps3/comando e o LED azul fica aceso. Do mesmo jeito, o operador interdita uma vaga: o CPS1 recebe o comando, pisca o LED e tira a vaga da conta, e o totem mostra a vaga em laranja. Comandos vão com QoS 1 e sem retain, para não serem executados de novo quando o ESP32 reconecta."

## Cena 11 · Vaga PcD ocupada sem credencial

- **Na tela:** CPS1, CPS2, a fita do totem e o painel **Alarmes** do dashboard. Começa como a cena 10 termina: só a PUC0R26 dentro, na V4, chave do CPS2 em saída.
- **Ações:**
  1. CPS1: HC-SR04 da V4 em 400 cm (o carro PcD deixou a vaga). Tem que ser antes da saída, senão o alarme dispara cedo.
  2. CPS2: HC-SR04 em 20 cm e botão azul **Câmera: PUC0R26**. Mostrar `saída PUC0R26`. Esperar a cancela fechar; HC-SR04 em 400 cm.
  3. CPS2: chave para a esquerda (entrada), HC-SR04 em 20 cm e botão verde **Câmera: ABC1D23**. Mostrar `entrada ABC1D23`. Esperar a cancela fechar; HC-SR04 em 400 cm.
  4. CPS1: HC-SR04 da V4 em 20 cm (a ABC1D23 parou na vaga PcD). Mostrar o alarme **Vaga PcD V4 ocupada sem credencial** no dashboard, o LED vermelho do totem piscando e só a V4 piscando na fita.
  5. CPS1: primeiro a V4 de volta a 400 cm, depois a V1 em 20 cm (o carro mudou de vaga; nessa ordem para não piscar evasão). Mostrar o alarme encerrando.
- **Duração:** 40 s.
- **Fala:**
  > "Agora um caso que acontece em todo estacionamento: carro sem cadastro PcD parado na vaga PcD. O carro PcD sai e entra a ABC1D23, que é uma placa comum. Ela para na V4, a vaga PcD. O CPS1 publica que a V4 está ocupada, e o CPS2 sabe pela cancela que nenhum carro PcD entrou. Então o CPS2 publica o alarme de vaga irregular em cps2/alarme. O totem pisca só a V4 e o dashboard avisa o operador, que chama a fiscalização, porque quem multa é o agente de trânsito. O sistema não sabe qual carro está em qual vaga: ele compara as contas, como na evasão. O carro muda para a V1 e o alarme some."

## Cena 12 · Queda do CPS1 e Last Will

- **Na tela:** CPS1, CPS3 e o status no dashboard.
- **Ações:**
  1. CPS1: parar a simulação (botão de stop do Wokwi).
  2. Esperar o dashboard mostrar CPS1 `offline` e o totem mostrar `----` com a fita piscando em laranja (no cartão CPS2, a cancela deixa de usar as vagas velhas). Se demorar, cortar a espera na edição (não verificado no Wokwi quanto tempo o broker leva: no teste local foi menos de 1 s; no pior caso, 1,5 × o keepalive de 30 s = 45 s).
  3. CPS1: dar play de novo. Mostrar `online` e o número voltando no totem.
- **Duração:** 30 s.
- **Fala:**
  > "Agora o CPS1 cai sem avisar. Quem publica o offline é o broker, com o Last Will que o CPS1 deixou ao conectar. O totem e a cancela assinam esse status: o totem, em vez de mostrar um número velho, mostra quatro traços e pisca a fita em laranja, e a cancela esquece as vagas velhas e para de negar por lotado. Quando o CPS1 volta, ele reconecta, publica online e as vagas, e o totem volta ao número."

## Cena 13 · As mensagens e o item 9

- **Na tela:** trecho da apresentação animada (publicar × assinar e as 7 respostas), já pronto em `video/gravacoes/cena13.mp4`. Não precisa gravar tela.
- **Duração:** 53 s.
- **Fala:**
  > "Aqui estão as mensagens passando pelo broker. O broker é o intermediário: todos conectam só nele, e cada mensagem que chega num tópico vira uma cópia para cada cliente que assinou esse tópico. Publicar é mandar para um tópico; assinar é pedir ao broker o que chegar nele, e quem publica não sabe quem assina. Cada CPS tem os tópicos sensor, estado, comando e status; o CPS2 tem também alarme; e há o pagamento. A mensagem do CPS1 chega ao CPS2 e ao CPS3 pelo broker, no callback; o callback lê o JSON e atualiza o estado, e o loop decide o atuador: o servo, o buzzer, os LEDs, o display. O dashboard é só mais um cliente, pelo WebSocket: assina os tópicos e publica os comandos. E as vantagens do MQTT: é leve para microcontrolador, desacopla quem publica de quem assina, tem QoS 1, em que o broker confirma o recebimento dos eventos e comandos, retain para o estado atual e Last Will para detectar quem caiu."

## Depois de gravar

```bash
video/montar.sh                 # abertura animada (48 s) + cenas 01 a 13
video/montar.sh --intro motion  # usa a apresentação animada inteira (5 min) no lugar da abertura
video/montar.sh --parcial       # monta só com as cenas que já existem (para conferir)
```

Narração da abertura: opcional, em `video/gravacoes/fala00.m4a` (ler a folha 1 e a folha 4 de `docs/FOLHAS.md`). Saída: `video/smartpark-final.mp4`.
