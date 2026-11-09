# O que veio do SmartPark 2026.1 e o que é novo

O SmartPark começou em Fundamentos de Sistemas Ciberfísicos (2026.1, Grupo 1). Aquela versão está inteira em `Old/`, sem alteração. O SmartPark 2.0 é o projeto de Conectividade em Sistemas Ciberfísicos (2026.2) e parte dela.

## A versão 2026.1 em uma frase

Um ESP32 com 2 sensores HC-SR04, LEDs verde/vermelho por vaga e um buzzer quando lotava; publicava o estado das vagas por MQTT para um dashboard em Processing. Só publicava: não assinava nada, não recebia comando e desistia do MQTT na primeira falha.

## Reaproveitado (com a origem marcada no código)

| O quê | Origem | Onde está agora | Mudou? |
|---|---|---|---|
| `medir_distancia(trig, echo)`: pulso de 10 µs, `time_pulse_us` com timeout de 30 ms, distância = tempo × 0,0343 / 2, 999 sem eco | `Old/main.py` | `cps1-vagas/main.py`, `cps2-cancela/main.py` | igual |
| `atualizar_led(ocupada, verde, vermelho)` | `Old/main.py` | `cps1-vagas/main.py` | igual na ideia; agora com `value()` |
| `conectar_wifi()` com tentativas na rede `Wokwi-GUEST` | `Old/main.py` | os três `main.py` | agora levanta erro para a reconexão tentar de novo |
| Buzzer em PWM: `duty 0` = silêncio, liga só para apitar | `Old/main.py` (`apitar()`) | `cps2-cancela/main.py` | agora não trava o loop (desliga por tempo) |
| Problema do totem que só diz "lotado/disponível" | `Old/README.md`, `Old/imgs/puc-totem-vagas.jpg` | CPS3 Totem contador | agora medido vaga a vaga |
| Fotos do campus | `Old/imgs/*.jpg` | apresentação | – |
| Aviso de hardware real: ECHO do HC-SR04 é 5 V, ESP32 aceita 3,3 V; usar divisor 1 kΩ/2 kΩ | `Old/README.md` | este arquivo (abaixo) | – |

## Novo no SmartPark 2.0

- **Três sistemas** independentes em vez de um: vagas (4, com tipo comum/idoso/PcD), cancela (entrada e saída pela placa) e totem contador.
- **Publicar e assinar** em todos, com tópicos por sistema (`docs/topicos.md`).
- **Integração**: o dado de um sistema muda o atuador do outro (lotado → cancela, vagas × entradas → evasão, CPS1 caiu → totem mostra `----`).
- **Conectividade robusta**: Last Will (`offline` automático), retain no estado, QoS 1 em comandos e alarmes, reconexão com nova assinatura, `ping()` de keepalive, `client_id` aleatório (todo ESP32 do Wokwi tem o mesmo MAC).
- **Câmera de placa simulada** e cobrança estilo Sem Parar; placa sem cadastro entra como avulso e só sai depois de pagar pelo celular.
- **Autodiagnóstico da cancela** (fim de curso) e **evasão** por conciliação.
- **Dashboard web** com MQTT.js no lugar do Processing, com comandos para os três sistemas.
- **Prova automática**: `scripts/verify` e `sim/teste_integracao.py` rodam o firmware de verdade contra o broker.

## Correção de uma afirmação da versão antiga

O `Old/README.md` diz que a `umqtt.simple` não existe no Wokwi. Ela existe: o exemplo oficial de MQTT do Wokwi em MicroPython usa `from umqtt.simple import MQTTClient`, e o SmartPark 2.0 depende dela.

## Se for montar em hardware real

O ECHO do HC-SR04 sai em 5 V e o GPIO do ESP32 aceita 3,3 V. Use um divisor resistivo em cada ECHO (do `Old/README.md`):

```
ECHO ──[1kΩ]──┬── GPIO ESP32
              [2kΩ]
              │
             GND
```

No Wokwi isso não é necessário.
