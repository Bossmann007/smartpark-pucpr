# CPS2 · Cancela

Módulo acoplado à cancela que já existe; a mesma cancela serve entrada e saída. O HC-SR04 vê o carro parado, a câmera (simulada) lê a placa e o ESP32 decide: abre o servo ou nega com o buzzer. Usa as vagas do CPS1 para saber se lotou e para achar evasão. O fim de curso confirma se a cancela fechou.

- Link do Wokwi: [colar aqui]
- Arquivos: `main.py`, `diagram.json`

| Peça | Pino | Uso |
|---|---|---|
| HC-SR04 | TRIG D5, ECHO D18 | carro na cancela abaixo de 30 cm |
| Botão verde | D13 | câmera lê `ABC1D23` (comum, cadastrada) |
| Botão amarelo | D14 | câmera lê `BRA2E19` (idoso, cadastrada) |
| Botão azul | D27 | câmera lê `PUC0R26` (PcD, cadastrada) |
| Chave de sentido | D26 | esquerda = entrada, direita = saída |
| Chave fim de curso | D25 | esquerda = fechada, direita = aberta (simula cancela travada) |
| Servo | D4 | 0° fechada, 90° aberta; fecha sozinha em 5 s |
| Buzzer | D23 | nega (0,6 s), cancela travada (1,5 s) |

- Placa sem cadastro: digitada no dashboard (câmera simulada). Entra como avulso e só sai depois do pagamento pelo celular.
- Débito automático de R$ 5,00 na saída das placas cadastradas (saldo inicial R$ 50,00).
- Publica: `cps2/sensor` (eventos), `cps2/estado`, `cps2/alarme`, `cps2/status` (Last Will)
- Assina: `cps1/sensor`, `cps1/status` (CPS1 caiu: esquece as vagas), `cps3/sensor` (ajuda no totem: bip), `cps2/comando`, `pagamento`, `cps2/estado` (só ao reiniciar, para lembrar quem está dentro)
- Reaproveitado de `Old/main.py`: `medir_distancia()`, `conectar_wifi()`, buzzer em PWM
