# Funcionamento e integração

O SmartPark 2.0 tem três sistemas ciberfísicos independentes, cada um com seu ESP32, que só se falam pelo broker MQTT. Cada um funciona sozinho; juntos, a informação de um muda o que o outro faz.

## CPS1 · Vagas

Um HC-SR04 sobre cada uma das 4 vagas (2 comuns, 1 idoso, 1 PcD) mede a distância; abaixo do limiar, a vaga está ocupada e o LED fica vermelho, senão verde. O CPS1 publica as vagas, o total livre e as comuns livres em `cps1/sensor` (retido). Ele assina o próprio `comando` (o operador interdita uma vaga, que pisca e sai da conta) e o `cps2/estado`: em emergência, pisca todos os LEDs.

## CPS2 · Cancela

Módulo acoplado à cancela existente, que serve entrada e saída. Um HC-SR04 detecta o carro parado e dispara a câmera simulada (botões com placas de teste, ou a placa digitada no dashboard). O CPS2 decide sozinho: placa cadastrada entra com débito automático; placa sem cadastro entra como avulso e só sai depois do pagamento; sem vaga do tipo da placa, nega e toca o buzzer. Um fim de curso confirma que a cancela fechou: se não fecha, alarme de cancela travada. Ele conta os carros `dentro` e compara com as vagas ocupadas do CPS1: se há mais carros nas vagas do que entraram, alarme de evasão.

## CPS3 · Totem contador

Na entrada, mostra o número de vagas livres num display de 7 segmentos, um LED verde/vermelho e uma fita NeoPixel com um LED por vaga (verde comum, amarelo idoso, azul PcD, vermelho ocupada), tudo a partir do `cps1/sensor`. Se o CPS1 cai (LWT `offline`), o display mostra `----`. O PIR acende o totem quando alguém chega, e o botão de ajuda abre um chamado no dashboard; quando o operador atende, o LED azul acende.

## Dashboard

Página HTML com MQTT.js por WebSocket. Mostra as vagas, a cancela, o contador `dentro`, o status online/offline dos três, os alarmes e o log das mensagens; envia comandos aos três (interditar vaga, abrir cancela, emergência, atender ajuda, brilho), simula a câmera e tem a página de pagar pelo celular.

## Câmera de placa simulada

O Wokwi não tem câmera. No CPS2, o HC-SR04 detecta o carro parado na cancela (como o laço indutivo real) e "dispara a câmera". A leitura vem de:

- botões no CPS2, um por placa de teste cadastrada (`ABC1D23`, `BRA2E19`, `PUC0R26`);
- ou o dashboard, que publica uma placa digitada em `cps2/comando` (placa sem cadastro).

Na operação real, ali fica uma câmera de leitura de placa (LPR). O cadastro e o saldo das placas de teste ficam no CPS2, então a cancela funciona mesmo com o dashboard fechado.

## Cenário da demo

1. Vagas: o CPS1 mede as quatro vagas (2 comuns, 1 idoso, 1 PcD) e publica; o totem (CPS3) atualiza o display, o LED e a fita NeoPixel; o dashboard também.
2. Entrada cadastrada: sentido = entrada, carro na cancela, câmera lê `ABC1D23` → cancela abre, `dentro` sobe, dashboard registra.
3. Entrada avulsa: o dashboard (câmera) envia `XYZ9K87` → entra como avulso.
4. Lotado: sem vaga comum livre, nova placa comum → cancela não abre, buzzer, totem com LED vermelho. Placa PcD ainda entra se a V4 estiver livre.
5. Saída: sentido = saída. `ABC1D23` sai direto (débito automático); `XYZ9K87` só sai depois de pagar pelo celular no dashboard.
6. Cancela travada: fim de curso fica aberto → LED do totem piscando e alarme no dashboard.
7. Evasão: ocupar uma vaga sem passar pela cancela → alarme de evasão.
8. Emergência: comando do dashboard → cancela aberta, LEDs das vagas e fita piscando.
9. Ajuda: botão no totem → chamado no dashboard → operador atende → LED azul aceso.
10. Vaga PcD irregular: o carro PcD sai, uma placa comum entra e para na V4 → alarme `vaga_irregular`, a V4 pisca no totem; o carro muda de vaga → alarme some.
11. Queda: parar o CPS1 → status `offline` (LWT), display do totem mostra `----`; reiniciar → volta.
