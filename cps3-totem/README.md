# CPS3 · Totem contador

Na entrada do estacionamento: mostra quantas vagas estão livres no display de 7 segmentos, um LED verde/vermelho e uma fita NeoPixel com um LED por vaga. Tudo vem do CPS1 pela rede. Se o CPS1 cai (Last Will), mostra `----`.

- Link do Wokwi: https://wokwi.com/projects/480004853605879809
- Arquivos: `main.py`, `tm1637.py` (driver do display, adicionar no projeto Wokwi), `diagram.json`

| Peça | Pino | Uso |
|---|---|---|
| Display TM1637 | CLK D22, DIO D21 | vagas livres ou `----` |
| Fita NeoPixel ×4 | DIN D5 | V1..V4: verde comum, amarelo idoso, azul PcD, vermelho ocupada, laranja interditada; branco piscando = emergência; laranja piscando = CPS1 fora; só uma vaga piscando = vaga PcD irregular |
| LED verde | D4 | tem vaga comum (a que a cancela usa para negar carro comum); com só vaga de idoso ou PcD livre, o display mostra o número e o LED fica vermelho |
| LED vermelho | RX2 (GPIO16) | lotado; piscando = alarme (evasão, cancela travada ou vaga PcD irregular) |
| LED azul | TX2 (GPIO17) | ajuda: piscando = aguardando, aceso = atendida |
| Botão de ajuda | D13 | interfone: avisa o dashboard |
| PIR | D27 | alguém chegou: brilho alto |

- Publica: `cps3/sensor` (presença; ajuda, que faz o CPS2 apitar na cancela), `cps3/estado`, `cps3/status` (Last Will)
- Assina: `cps1/sensor`, `cps1/status`, `cps2/alarme`, `cps2/estado`, `cps3/comando`
- Reaproveitado de `Old/`: `conectar_wifi()` e a ideia do totem de vagas (`Old/imgs/puc-totem-vagas.jpg`)
