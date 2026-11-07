# SmartPark 2.0: folhas para a apresentação

Uma folha por parte da apresentação animada (`docs/apresentacao/apresentacao-animada.html`), na ordem em que aparecem. São as mesmas notas da janela do apresentador (tecla N). Gerado por `docs/apresentacao/build.py` a partir de `folhas.json`: edite o JSON, não este arquivo.

## Folha 1. Abertura: a PUCPR em 3D

*0:00 a 0:24 (24 s)*

**Na tela:** Voo 3D sobre o câmpus Curitiba (prédios reais do OpenStreetMap), descendo até os bolsões de estacionamento. Título SmartPark 2.0.

**Falar**

- Este é o câmpus Curitiba da PUCPR, com os prédios reais do OpenStreetMap.
- O SmartPark 2.0 é o estacionamento da PUC sem parar na cancela: a vaga é medida uma a uma, a câmera lê a placa e a cancela avisa quando falha.
- São três sistemas ciberfísicos, cada um com o seu ESP32, que só conversam por MQTT, mais um dashboard.

**Mais para falar**

- Os bolsões em destaque são as áreas marcadas como estacionamento no OpenStreetMap; as alturas vêm das tags height e building:levels quando existem, senão uma altura padrão.
- Tudo roda no Wokwi com MicroPython: três projetos separados, um por ESP32.
- Disciplina: Conectividade em Sistemas Ciberfísicos, 2026.2.

**Se perguntarem:** De onde vem esse 3D?

> Do OpenStreetMap: uma consulta na Overpass API trouxe o contorno dos prédios do câmpus, e o Three.js levanta cada contorno até a altura dele. Os dados ficam salvos em docs/apresentacao/puc-osm.json.

---

## Folha 2. O problema

*0:24 a 0:46 (22 s)*

**Na tela:** Foto real do totem do bolsão E03 e três linhas: o que existe hoje e o que o SmartPark acrescenta.

**Falar**

- Hoje o totem conta as vagas do bolsão inteiro. Não diz qual vaga está livre. O SmartPark mede cada vaga.
- Na entrada, o aluno passa a carteirinha na cancela. No SmartPark a câmera lê a placa e o débito é automático, como o Sem Parar.
- E não há autodiagnóstico de cancela divulgado. O SmartPark avisa quando ela trava aberta e quando entra carro sem registro.

**Mais para falar**

- A PUC já tem contagem por bolsão, app de estacionamento e autoatendimento. Não estamos dizendo que não tem; estamos acrescentando a medição por vaga e o diagnóstico.
- A foto é do totem E03, tirada no semestre passado.

**Se perguntarem:** A PUC já não tem contagem de vagas e app?

> Tem: contagem por bolsão, o app Estacionamento PUCPR e autoatendimento. O SmartPark mede cada vaga, troca a carteirinha pela placa e dá à cancela um autodiagnóstico.

---

## Folha 3. De onde viemos: SmartPark 2026.1

*0:46 a 1:14 (28 s)*

**Na tela:** Fotos reais da PUC do projeto anterior. À esquerda o SmartPark 2026.1 (1 ESP32, 2 HC-SR04, só publicava); à direita o que foi reaproveitado e o que é novo.

**Falar**

- O SmartPark começou em Fundamentos de Sistemas Ciberfísicos, em 2026.1: um ESP32, dois HC-SR04 e um dashboard. Ele só publicava; não assinava nada.
- Reaproveitamos as funções que já funcionavam: medir_distancia, atualizar_led, conectar_wifi, o buzzer em PWM e a ideia do totem de vagas.
- O novo é a conectividade: três ESP32 que publicam e assinam, mensagens em JSON, Last Will, retain, reconexão e uma integração real entre eles.

**Mais para falar**

- medir_distancia está no CPS1 e no CPS2; atualizar_led no CPS1; conectar_wifi nos três; o buzzer em PWM no CPS2; a ideia do totem virou o CPS3.
- Os tópicos antigos eram smartpark/puc/vaga1 e vaga2 (0 ou 1, em texto) e status (um JSON simples). Agora são 14 tópicos em JSON sob cscf/smartpark/.
- O projeto antigo tinha 2 vagas; o novo tem 4, com tipo: 2 comuns, 1 idoso, 1 PcD.

**Se perguntarem:** Pode reaproveitar código de outra disciplina?

> O reuso está marcado no topo de cada main.py, função por função. Tudo o que o enunciado avalia aqui, a comunicação entre os três por MQTT, é novo.

---

## Folha 4. Arquitetura: tudo passa pelo broker

*1:14 a 1:38 (24 s)*

**Na tela:** Os três ESP32 no topo, o broker MQTT no meio e o dashboard embaixo, como no modelo do enunciado. Cada um com PUB + SUB.

**Falar**

- A arquitetura segue o modelo do enunciado: três CPS em cima, o broker no meio e o dashboard embaixo.
- CPS1 mede as vagas, CPS2 é o módulo da cancela, CPS3 é o totem da entrada.
- Nenhum sistema fala direto com outro. Os ESP32 conectam no broker HiveMQ pela porta 1883, e o dashboard pelo WebSocket seguro, na 8884.

**Mais para falar**

- Todos publicam e assinam: o enunciado pede os dois papéis em cada ESP32.
- O broker é público, então os tópicos têm o prefixo cscf/smartpark e as placas são fictícias.
- Reserva se o HiveMQ cair: broker.emqx.io.

**Se perguntarem:** Por que não ligar um ESP32 direto no outro?

> Porque aí cada um teria que conhecer o endereço do outro. Com o broker, quem publica não sabe quem assina: dá para pôr um quarto CPS sem mexer nos três.

---

## Folha 5. Publicar × assinar e o papel do broker

*1:38 a 2:06 (28 s)*

**Na tela:** Os assinantes avisam o broker; o CPS1 publica cps1/sensor e o broker entrega uma cópia a cada assinante; o dashboard publica cps2/comando e só o CPS2 recebe. Depois: QoS, retain e Last Will.

**Falar**

- Assinar é avisar o broker: quero tudo o que chegar neste tópico. O CPS2, o CPS3 e o dashboard assinam cps1/sensor.
- Publicar é mandar uma mensagem para um tópico. O CPS1 publica as vagas; o broker entrega uma cópia para cada assinante.
- O dashboard também é cliente: ele publica no comando do CPS2, e só o CPS2 recebe, porque só ele assina esse tópico.

**Mais para falar**

- QoS 0 nas leituras e no estado; QoS 1 em comandos, alarmes e pagamento, que precisam de confirmação.
- Retain: o broker guarda a última mensagem do tópico e entrega na hora a quem conectar depois.
- Last Will: cada ESP32 deixa um offline com o broker ao conectar; se cair, o broker publica por ele.
- As mensagens na tela são reais: vêm do log do teste de integração, com os três main.py rodando contra o broker.

**Se perguntarem:** O CPS1 sabe que o CPS3 existe?

> Não. Ele só publica em cps1/sensor. Quem decide receber é o assinante; o broker faz a entrega.

---

## Folha 6. Integração 1: vagas → totem

*2:06 a 2:18 (12 s)*

**Na tela:** Carro para na V1. O CPS1 publica cps1/sensor; o totem (CPS3) muda para 3 e pinta a V1 de vermelho na fita.

**Falar**

- Um carro para na V1. O HC-SR04 mede 19 centímetros, abaixo do limite de 50: a vaga está ocupada e o LED fica vermelho.
- O CPS1 publica cps1/sensor. O totem assina esse tópico: o display vai de 4 para 3 e a primeira luz da fita fica vermelha.

**Mais para falar**

- Na fita, cada cor é um tipo de vaga livre: verde comum, amarelo idoso, azul PcD; vermelho é ocupada.
- O CPS1 usa histerese: ocupa abaixo de 50 cm e só libera acima de 60 cm, para o LED não piscar na borda.

**Se perguntarem:** O totem lê o sensor da vaga?

> Não. O totem não tem sensor de vaga: tudo o que ele mostra chega pela rede, no cps1/sensor.

---

## Folha 7. Integração 2: lotado → cancela nega

*2:18 a 2:32 (14 s)*

**Na tela:** Avulso XYZ9K87 entra; V2 ocupa e as vagas comuns acabam; QWE4R56 é negada com buzzer; PUC0R26 (PcD) ainda entra.

**Falar**

- A câmera do dashboard manda a placa XYZ9K87, sem cadastro: ela entra como avulso.
- Quando a V2 é ocupada, o CPS1 publica zero vagas comuns livres. O CPS2 guarda isso.
- A próxima placa comum é negada por lotado e o buzzer toca. Mas a PUC0R26 é PcD e ainda tem vaga do tipo dela: a cancela abre.

**Mais para falar**

- A regra fica no ESP32 da cancela: comum precisa de vaga comum; idoso e PcD usam a sua ou uma comum.
- O dado que decide vem de outro ESP32: é a integração do item 4.4.

**Se perguntarem:** E se o CPS1 estiver fora do ar?

> Se o CPS2 nunca recebeu as vagas, ele não bloqueia a entrada (vagas_cps1 é None e tem_vaga devolve verdadeiro): falha segura para o fluxo.

---

## Folha 8. Integração 3: evasão

*2:32 a 2:44 (12 s)*

**Na tela:** Quatro vagas ocupadas, só três carros entraram pela cancela: o CPS2 publica cps2/alarme evasão com diferença 1; o totem pisca o LED vermelho.

**Falar**

- O CPS2 compara duas coisas: as vagas ocupadas, que vêm do CPS1, e os carros que entraram pela cancela.
- Quatro ocupadas e três dentro: alguém entrou sem passar pela cancela. O CPS2 publica o alarme de evasão, e o totem e o dashboard reagem.

**Mais para falar**

- Evasão só existe porque os dois sistemas conversam: nenhum dos dois sabe isso sozinho.
- O alarme é publicado com QoS 1 e sem retain, só quando começa ou termina.

**Se perguntarem:** Como o CPS2 sabe quantos estão dentro?

> Ele soma entradas e tira saídas, e publica a lista em cps2/estado com retain; se reiniciar, relê esse retido e lembra quem estava dentro.

---

## Folha 9. Integração 4: cancela travada

*2:44 a 2:56 (12 s)*

**Na tela:** A cancela recebe ordem de fechar, mas o fim de curso continua aberto. Depois de 3 s, o CPS2 publica cps2/alarme cancela_travada.

**Falar**

- A cancela fechou no tempo dela, mas o fim de curso diz que ela continua aberta.
- Depois de três segundos sem confirmação, o CPS2 toca o buzzer e publica cancela travada. O CPS3 e o dashboard assinam o alarme.

**Mais para falar**

- É o autodiagnóstico da cancela: ela mesma avisa que não fechou.
- No teste, o alarme de evasão ainda estava ativo, então o LED do totem já piscava; com a cancela travada ele continua piscando.
- Os 3 s são a constante TEMPO_TRAVADA_MS do CPS2.

**Se perguntarem:** O que é o fim de curso no Wokwi?

> Uma chave deslizante: à esquerda a cancela está fechada, à direita continua aberta. Na cancela real seria um sensor de fim de curso.

---

## Folha 10. Integração 5: pagamento → saída

*2:56 a 3:11 (15 s)*

**Na tela:** Saída do avulso XYZ9K87 negada (pagamento pendente); o dashboard publica em pagamento; o CPS2 confirma; a cancela abre. ABC1D23 sai com débito automático (saldo 45).

**Falar**

- Na saída, o avulso XYZ9K87 é negado: pagamento pendente.
- Pelo celular, o dashboard publica no tópico pagamento. O CPS2 assina, marca como pago e confirma.
- Na segunda leitura, a cancela abre. Já a ABC1D23 é cadastrada: sai direto, com débito automático de 5 reais.

**Mais para falar**

- O pagamento é simulado: é uma mensagem MQTT, sem cobrança real.
- O cadastro e o saldo das placas de teste ficam no CPS2: a cancela funciona mesmo com o dashboard fechado.

**Se perguntarem:** Por que o pagamento usa QoS 1?

> Porque é importante: com QoS 1 o broker confirma que recebeu e entrega pelo menos uma vez a quem está conectado. Se o CPS2 estiver fora do ar, a mensagem não fica guardada (sessão limpa) e o celular mostra que não houve confirmação.

---

## Folha 11. Integração 6: emergência

*3:11 a 3:23 (12 s)*

**Na tela:** O dashboard publica {"modo": "emergencia"} em cps2/comando: a cancela abre e fica aberta; o CPS1 pisca os LEDs; o totem pisca a fita em branco.

**Falar**

- O operador aperta emergência. O dashboard publica no comando do CPS2.
- A cancela abre e fica aberta. O CPS2 publica o novo estado; o CPS1 e o CPS3 assinam esse estado: os LEDs das vagas piscam e a fita do totem pisca em branco.

**Mais para falar**

- Um comando, três sistemas reagindo: o dashboard só falou com o CPS2; o resto chegou pelo estado publicado.
- Em emergência, placa lida não abre nem nega: o CPS2 registra o evento livre.

**Se perguntarem:** Como o CPS1 fica sabendo da emergência?

> Ele assina cps2/estado. Quando o campo modo vira emergencia, ele pisca os LEDs.

---

## Folha 12. Integração 7: ajuda no totem

*3:23 a 3:34 (11 s)*

**Na tela:** Botão de ajuda no CPS3 → cps3/sensor {"ajuda": true} → o dashboard mostra o chamado → o operador responde em cps3/comando → LED azul aceso.

**Falar**

- O motorista aperta o botão de ajuda no totem. O CPS3 publica em cps3/sensor e o LED azul pisca enquanto espera.
- O dashboard mostra o chamado; o operador clica em atender, que publica em cps3/comando. O LED azul fica aceso por 10 segundos.

**Mais para falar**

- É o acionamento remoto de um atuador: o LED do totem muda por uma mensagem do dashboard.
- O PIR do totem também publica presença e aumenta o brilho.

**Se perguntarem:** Por que o comando não usa retain?

> Comando retido seria executado de novo a cada reconexão. Por isso comandos, alarmes e pagamento vão com QoS 1 e sem retain.

---

## Folha 13. Integração 8: queda e Last Will

*3:34 a 3:47 (13 s)*

**Na tela:** O CPS1 cai sem avisar; o broker publica cps1/status offline (Last Will); o totem mostra ---- e a fita pisca laranja; o CPS1 volta, publica online e o número volta.

**Falar**

- Agora o CPS1 cai sem avisar. Quem publica o offline é o broker, com o Last Will que o CPS1 deixou ao conectar.
- O totem assina cps1/status: mostra quatro traços e a fita pisca laranja, para não mostrar um número velho.
- Quando o CPS1 volta, publica online e as vagas, e o totem volta ao número.

**Mais para falar**

- Last Will com retain: quem conectar depois também fica sabendo que o CPS1 está offline.
- Cada ESP32 reconecta sozinho e refaz as assinaturas quando a rede cai.

**Se perguntarem:** Como o broker sabe que o ESP32 caiu?

> Pelo keepalive: o ESP32 manda ping a cada 10 s, com keepalive de 30 s. Se a conexão fecha, o broker publica o Last Will na hora; se ela fica muda, publica depois de 1,5 × 30 s = 45 s.

---

## Folha 14. O ciclo ciberfísico

*3:47 a 4:09 (22 s)*

**Na tela:** Aquisição → processamento → conectividade → atuação → realimentação, cada etapa com um exemplo do código.

**Falar**

- Aquisição: o HC-SR04 mede a distância na vaga.
- Processamento: o ESP32 compara com o limite e decide que a vaga está ocupada.
- Conectividade: publica no broker. Atuação: o totem e a cancela mudam por causa dessa mensagem.
- Realimentação: cada um publica o próprio estado com retain, para os outros e para o dashboard.

**Mais para falar**

- Mundo físico, mundo digital e de volta ao físico: é o desenho do item 6 do enunciado.
- A rede amplia o controle: a cancela decide com o dado da vaga, e o operador comanda tudo de longe.

**Se perguntarem:** Onde está a realimentação no código?

> No estado publicado com retain: cps1/estado, cps2/estado e cps3/estado, republicados a cada mudança. O dashboard e os outros CPS leem isso.

---

## Folha 15. As 7 perguntas do item 9

*4:09 a 4:47 (38 s)*

**Na tela:** As sete perguntas do enunciado com a resposta curta, uma de cada vez.

**Falar**

- Broker: o intermediário. Recebe toda mensagem e entrega a quem assinou o tópico.
- Publicar envia para um tópico; assinar pede para receber. Quem publica não conhece quem assina.
- Tópicos: sensor, estado, comando e status em cada CPS, alarme no CPS2 e pagamento.
- A mensagem chega aos outros pelo broker: o CPS1 publica, o CPS2 e o CPS3 recebem no callback.
- O callback atualiza o estado e o loop decide o atuador: servo, buzzer, LEDs, display.
- O dashboard é só mais um cliente MQTT, pelo WebSocket: assina e publica comandos.
- Vantagens do MQTT: leve, desacoplado, com QoS, retain e Last Will.

**Mais para falar**

- As respostas longas estão em docs/APRESENTACAO.md.
- A tabela completa de tópicos está em docs/topicos.md.

**Se perguntarem:** Por que não HTTP?

> No HTTP cada sistema teria que perguntar ao outro de tempos em tempos. No MQTT a mensagem chega na hora para todos os interessados, por uma conexão só.

---

## Folha 16. Fechamento

*4:47 a 4:59 (12 s)*

**Na tela:** SmartPark 2.0: 3 ESP32, 1 broker, 1 dashboard, 14 tópicos, 8 integrações. MQTT em 5 palavras.

**Falar**

- Três ESP32, um broker e um dashboard: cada informação de um sistema muda o que o outro faz.
- MQTT em cinco palavras: broker, publicar, assinar, retain e Last Will. Obrigado.

**Mais para falar**

- Os links dos três Wokwi, o dashboard, a tabela de tópicos e o diagrama estão no repositório.
- A prova de funcionamento é o scripts/verify e o teste de integração em sim/.

**Se perguntarem:** E se o broker cair?

> A comunicação para, mas cada ESP32 continua com as regras locais (o CPS1 acende os LEDs, a cancela usa as últimas vagas recebidas) e tenta reconectar a cada 5 s sem travar. Em produção seria um broker próprio, com usuário e TLS; aqui a reserva é manual: trocar a constante BROKER para o EMQX.

---
