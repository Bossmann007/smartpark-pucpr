# Broker MQTT

- Broker: HiveMQ público, `broker.hivemq.com`. ESP32 na porta 1883 (TCP); dashboard por WebSocket na 8000 (`ws://…/mqtt`) ou 8884 (`wss://…/mqtt`, obrigatório se a página estiver em HTTPS). Portas testadas em 06/11/2026.
- Usado nas atividades da disciplina (enunciado item 4.1). Grátis, sem senha, sem garantia de disponibilidade.
- Reserva, se o HiveMQ cair: `broker.emqx.io` (1883; WebSocket 8083/8084 em `/mqtt`).
- Público: por isso o prefixo único `cscf/<id-da-equipe>/` e só placas fictícias nas mensagens. Num broker público qualquer um também pode **publicar** (por exemplo, mandar emergência). Em produção: broker próprio com usuário e senha por dispositivo, ACL (cada ESP32 só publica e assina os seus tópicos; só o dashboard publica comando) e TLS (porta 8883).
- Camada: o MQTT é protocolo da **camada de aplicação** sobre **TCP** (porta 1883). O `umqtt` abre um socket TCP, manda CONNECT e recebe CONNACK; depois troca PUBLISH, SUBSCRIBE/SUBACK e PINGREQ/PINGRESP. TCP porque a entrega precisa ser confiável e em ordem (o CoAP, por exemplo, usa UDP). O navegador não abre TCP cru, só HTTP/WebSocket: por isso o dashboard fala MQTT dentro de WebSocket seguro na 8884.
- Pacote PUBLISH: cabeçalho fixo (2 a 5 bytes: tipo, flags de QoS/retain, tamanho), cabeçalho variável (nome do tópico e, com QoS 1, o id do pacote) e o payload (aqui, o JSON).
- Recursos usados:
  - Last Will (LWT): cada ESP32 registra `offline` com retain em `cpsN/status` antes de conectar e publica `online` logo depois.
  - Retain nos tópicos de estado: quem conecta (dashboard, ESP32 que reiniciou) recebe o último valor na hora. O CPS2 relê o próprio estado retido ao reiniciar para lembrar quem está dentro.
  - QoS 1 em comandos, pagamentos, eventos e alarmes; QoS 0 no estado e nas leituras (com retain), para o loop não travar esperando confirmação.
  - Botões lidos por interrupção (`Pin.irq`): um clique curto não se perde enquanto o ESP32 conversa com o broker.
  - Reconexão: se a publicação ou o `check_msg()` falhar, o ESP32 segue com as regras locais (sensores e atuadores não param) e tenta reconectar a cada 5 s, refazendo Last Will, `online` e todas as assinaturas. `ping()` a cada 10 s com keepalive de 30 s.
  - QoS é por trecho: publicador → broker e broker → assinante. O assinante recebe com o menor dos dois (o `cps1/sensor` sai com QoS 0, então chega com QoS 0 mesmo assinado com QoS 1).
  - QoS 1 pode entregar duas vezes; o código aguenta: pagamento repetido só marca `pago` de novo, e placa repetida na entrada vira `negado ja_dentro`.
  - Reserva manual: se o HiveMQ cair, trocar a constante `BROKER` (e a URL do dashboard) para o EMQX.
  - QoS 1 confirma entre cliente e broker e entrega a quem está conectado; com sessão limpa (padrão do `umqtt`), mensagem para um ESP32 desconectado não fica guardada.
  - `client_id` com número aleatório: no Wokwi todo ESP32 tem o mesmo MAC, e dois clientes com o mesmo id derrubam um ao outro.
