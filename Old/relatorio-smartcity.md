---
notion_id: "36fcfea1-0584-8156-bba7-fac770017860"
---
# SmartPark PUC — Relatório do Projeto
**Disciplina:** Fundamentos de Sistemas Ciberfísicos  
**Curso:** Ciência da Computação — PUCPR  
**Alunos:** Enzo Bossmann · Gabriel Henrique · Diego Feltrin
**Data:** Junho de 2026  

---

## 1. O que é o SmartPark e por que fizemos isso

Quem estuda na PUC sabe o sofrimento de entrar no estacionamento sem saber se tem vaga. A gente entra, anda por um corredor inteiro, chega no fundo, nada — aí volta e tenta o outro lado. Enquanto isso o motor tá ligado, queimando combustível e soltando CO₂ à toa.

O SmartPark PUC resolve exatamente isso: um sensor por vaga, um LED que mostra na hora se está livre ou ocupada, e os dados sendo enviados pra um dashboard via MQTT. Simples, barato (em torno de R$35 por vaga) e fácil de escalar pro campus inteiro.

A ideia surgiu porque a PUC tem totens que mostram "lotado" ou "disponível" na entrada — mas são contadores gerais, não mostram onde exatamente tem vaga. A gente quis resolver o problema no nível da vaga individual.

**Simulação Wokwi:** https://wokwi.com/projects/465089138268468225

---

## 2. Como o sistema funciona — os requisitos

### O que o sistema precisa fazer

| ID | Requisito | Componente responsável |
|----|-----------|----------------------|
| RF01 | Detectar se tem carro na vaga (precisão >95%) | HC-SR04 + ESP32 |
| RF02 | Acender LED correto em menos de 2 segundos | ESP32 + LEDs |
| RF03 | Publicar status das vagas por MQTT quando muda | ESP32 + WiFi |
| RF04 | Continuar funcionando (com LEDs e buzzer) mesmo sem WiFi | ESP32 |
| RF05 | Mandar JSON com identificação da vaga e distância medida | MQTT |
| RF06 | Buzzer sonoro quando as duas vagas estão ocupadas | ESP32 + Buzzer |

### Características não funcionais

| ID | O que precisa | Meta |
|----|---------------|------|
| RNF01 | Tempo do sensor até o MQTT | menos de 2 segundos |
| RNF02 | Consumo de energia | menos de 500mA em 5V |
| RNF03 | Frequência de leitura | 1 vez por segundo |
| RNF04 | Se cair o WiFi | modo offline automático |

### Por que isso é um Sistema Ciberfísico (CPS)

Um CPS é um sistema onde software e hardware estão integrados e se comunicam com o mundo físico. O SmartPark tem as quatro camadas:

- **Sensing:** os HC-SR04 medem a distância real até o carro (mundo físico → dados digitais)
- **Computation:** o ESP32 processa a distância e decide se a vaga está ocupada
- **Communication:** envia o status via WiFi + MQTT pro dashboard
- **Actuation:** acende o LED certo e liga o buzzer quando necessário (dados digitais → mundo físico)

---

## 3. Arquitetura do sistema

### Diagrama geral

```
┌──────────────────────────────────────────────────────────────┐
│                      MUNDO FÍSICO                            │
│                                                              │
│    [Veículo]                         [Veículo]               │
│       ↕                                   ↕                  │
│   ┌────────┐                         ┌────────┐              │
│   │HC-SR04 │                         │HC-SR04 │  ← Sensing   │
│   │ Vaga 1 │                         │ Vaga 2 │              │
│   └───┬────┘                         └───┬────┘              │
└───────┼──────────────────────────────────┼───────────────────┘
        │                                  │
┌───────▼──────────────────────────────────▼────────────────┐
│                    ESP32 DevKit V1                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MicroPython - main.py              Computation      │  │
│  │  medir_distancia() → distância em cm                │  │
│  │  atualizar_led() · apitar() · MQTT                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  [LED V/R Vaga 1]  [LED V/R Vaga 2]  ← Atuador Visual     │
│  [Buzzer 1 kHz — quando lotado]      ← Atuador Sonoro      │
│                                                            │
│  [WiFi STA] ──────────────────────────────► MQTT Broker    │
└────────────────────────────────────────────────────────────┘
                                           │
                               ┌───────────▼──────────────┐
                               │  Interface Processing     │
                               │  (Dashboard em tempo real)│
                               └──────────────────────────┘
```

### Protocolo MQTT

O ESP32 publica nos mesmos tópicos que o dashboard Processing (PegadaCampus) assina:

| Tópico | Payload | Significado |
|--------|---------|-------------|
| `smartpark/puc/vaga1` | `0` / `1` | 0 = livre, 1 = ocupada |
| `smartpark/puc/vaga2` | `0` / `1` | 0 = livre, 1 = ocupada |
| `smartpark/puc/status` | `{"v1":0,"v2":1}` | estado das duas vagas em JSON |

A gente publica só quando o estado muda — não fica mandando a mesma informação repetida toda hora. Isso reduziu bastante o tráfego na rede.

### Pinagem

**Sensores HC-SR04:**

| Pino | ESP32 Vaga 1 | ESP32 Vaga 2 | Observação |
|------|-------------|-------------|------------|
| VCC | 3V3 | 3V3 | funciona em simulação |
| GND | GND | GND | — |
| TRIG | GPIO 5 | GPIO 19 | saída |
| ECHO | GPIO 18 | GPIO 21 | ⚠️ em hardware real: divisor resistivo 1kΩ/2kΩ porque o HC-SR04 manda 5V mas o ESP32 aguenta só 3,3V |

**LEDs:**

| LED | GPIO | Resistor |
|-----|------|----------|
| Verde Vaga 1 | GPIO 2 | 220Ω |
| Vermelho Vaga 1 | GPIO 4 | 220Ω |
| Verde Vaga 2 | GPIO 22 | 220Ω |
| Vermelho Vaga 2 | GPIO 23 | 220Ω |

**Buzzer:**

| Componente | GPIO | Controle | Quando ativa |
|------------|------|----------|-------------|
| Buzzer passivo | GPIO 25 | PWM 1kHz, 50% duty | Ambas as vagas ocupadas |

---

## 4. Tecnologias utilizadas

| Tecnologia | Versão/Modelo | Para que serve |
|------------|--------------|----------------|
| ESP32 DevKit V1 | ESP32-WROOM-32 | microcontrolador principal |
| MicroPython | v1.22+ | linguagem embarcada |
| HC-SR04 | — | sensor ultrassônico de distância |
| umqtt.simple | nativo MicroPython | cliente MQTT |
| MQTT | v3.1.1 | protocolo de comunicação |
| Mosquitto | 2.x | broker MQTT |
| Buzzer passivo | — | alerta sonoro de lotação |
| Processing | 4.x | dashboard visual em tempo real |
| Wokwi | web | simulador ESP32 + MicroPython |

---

## 5. Como calculamos a distância

O HC-SR04 emite um pulso ultrassônico e mede quanto tempo o eco demora pra voltar. A fórmula é simples:

```
distância (cm) = (tempo_do_eco_em_µs × 0,0343) / 2
```

O 0,0343 é a velocidade do som em cm/µs (343 m/s a 20°C). Divide por 2 porque o som vai e volta.

Se o sensor não recebe o eco em 30ms, a função retorna 999cm — isso evita que o código trave esperando eternamente quando não tem nada na frente do sensor.

---

## 6. Como foi o desenvolvimento

### Primeiros testes com o sensor

A primeira coisa que a gente descobriu na prática foi o problema de tensão: o pino ECHO do HC-SR04 manda 5V, mas o ESP32 só suporta 3,3V nos GPIOs. Nos primeiros testes as leituras saíam instáveis e erradas. Depois de pesquisar um pouco, a solução foi usar um divisor resistivo (1kΩ em série + 2kΩ pro GND) que reduz os 5V pra aproximadamente 3,3V.

### Ajustando o limiar de detecção

O primeiro valor que tentei foi 10cm — tava muito baixo. O sensor captava reflexos do chão e ficava mostrando vaga ocupada sem ter carro nenhum. Testei alguns valores diferentes e 20cm ficou bom: detecta carro com folga mas não dá falso positivo com o piso.

### Integrando o MQTT

Usar a `umqtt.simple` foi mais direto do que esperava — ela já vem no MicroPython. O ponto de atenção foi implementar a lógica de publicar só quando o estado muda. No começo o código publicava a cada segundo, o que não fazia sentido: se o estado da vaga não mudou, por que mandar a mesma informação de novo? Com a publicação condicional, o tráfego caiu muito.

Também adicionei um bloco de reconexão automática pra quando o WiFi cai — o sistema tenta reconectar silenciosamente sem travar o loop dos sensores.

### Adicionando o buzzer

A gente percebeu que só o LED visual não seria suficiente pra avisar o pessoal da administração quando o estacionamento enche. Adicionamos um buzzer no GPIO 25 usando PWM a 1kHz — toca quando as duas vagas estão ocupadas ao mesmo tempo. Usamos PWM em vez de sinal digital direto porque dá mais controle sobre o som.

### Compatibilidade com Wokwi

O Wokwi não tem a `umqtt.simple` disponível, então envolvemos o import num `try/except`. Com isso o mesmo código roda na simulação sem precisar de versão separada — os sensores e atuadores funcionam normalmente, só a parte do MQTT que fica desligada.

---

## 7. Limitações e o que melhorar

| Problema atual | Como melhorar |
|---------------|---------------|
| Só 2 vagas no protótipo | Adicionar mais ESP32 em rede |
| Broker MQTT local (LAN) | Migrar pra nuvem (HiveMQ ou AWS IoT) |
| Sem autenticação no MQTT | Adicionar TLS + senha |
| Limiar fixo no código | Interface web pra configurar remotamente |
| Sensor pode ser obstruído por lixo | Câmera com visão computacional como backup |

---

## 8. Conclusão

O SmartPark mostrou que dá pra resolver um problema real do campus com hardware barato e código simples. O custo por vaga fica em torno de R$35 e a arquitetura escala facilmente — é só adicionar mais nós ESP32 na mesma rede MQTT.

O maior aprendizado do projeto foi entender na prática como um sistema ciberfísico une o mundo físico (sensor medindo o carro) com o mundo digital (dashboard mostrando a vaga em tempo real). A parte de ajustar o limiar e resolver o problema de tensão do HC-SR04 foi onde a gente mais aprendeu, porque não era coisa que tava em nenhum tutorial pronto.

---

## Referências

- MQTT v3.1.1 Specification — OASIS Standard, 2014
- MicroPython Documentation — micropython.org
- HC-SR04 Datasheet — Elec Freaks, 2013
- ESPRESSIF. ESP32 Technical Reference Manual, 2023
- KOLBAN, N. Kolban's Book on ESP32, 2017
