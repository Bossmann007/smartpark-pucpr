# Tabela de tópicos MQTT

Prefixo: `cscf/equipe03/` (constante `PREFIXO` no topo de cada `main.py`; `equipe03` é o id da equipe 3). Mensagens em JSON, exceto `status`. Placas fictícias. Este arquivo é o contrato: o código dos três CPS e o dashboard seguem exatamente estes campos.

| Tópico | Publica | Assina | Mensagem (exemplo) | QoS / retain |
|---|---|---|---|---|
| `cps1/sensor` | CPS1 | CPS2, CPS3, dashboard | ver abaixo | 0 / retain |
| `cps1/estado` | CPS1 | dashboard | `{"leds": ["vermelho", "verde", "verde", "piscando"], "interditadas": ["V4"], "emergencia": false, "ack": "t1"}` | 0 / retain |
| `cps1/comando` | dashboard | CPS1 | `{"manutencao": "V4", "ativo": true}` (interdita; `false` libera) ou `{"ping": "t1"}` | 1 / nunca retain |
| `cps2/sensor` | CPS2 | dashboard | eventos, ver abaixo | 1 / não |
| `cps2/estado` | CPS2 | CPS2 (só ao reiniciar), CPS1, CPS3, dashboard | ver abaixo | 0 / retain |
| `cps2/alarme` | CPS2 | CPS3, dashboard | `{"tipo": "cancela_travada", "ativo": true}` ou `{"tipo": "evasao", "ativo": true, "diferenca": 1}` ou `{"tipo": "vaga_irregular", "ativo": true, "vaga": "V4"}` | 1 / não |
| `cps2/comando` | dashboard | CPS2 | `{"placa": "XYZ9K87", "sentido": "entrada"}` (câmera simulada; sem `sentido` usa a chave), `{"cancela": "abrir"}`, `{"modo": "emergencia"}` / `{"modo": "normal"}`, `{"ping": "t1"}` | 1 / nunca retain |
| `pagamento` | dashboard (pagar pelo celular) | CPS2 | `{"placa": "XYZ9K87", "valor": 7.0}` | 1 / não |
| `cps3/sensor` | CPS3 | CPS2 (ajuda), dashboard | `{"presenca": true}` ou `{"ajuda": true}` | 0 (ajuda: 1) / não |
| `cps3/estado` | CPS3 | dashboard | `{"display": 2, "led": "verde", "fita": ["vermelho", "verde", "amarelo", "azul"], "fita_pisca": false, "pisca_vaga": null, "ajuda": "nenhuma", "brilho": "baixo", "brilho_forcado": "auto", "presenca": false, "ack": "t1"}` | 0 / retain |
| `cps3/comando` | dashboard | CPS3 | `{"ajuda": "atendido"}`, `{"brilho": "alto"}` (`"baixo"`, `"auto"`), `{"ping": "t1"}` | 1 / nunca retain |
| `cps1/status`, `cps2/status`, `cps3/status` | cada ESP32 (Last Will) | CPS2 e CPS3 (só `cps1/status`), dashboard | texto `online` / `offline` | 1 / retain (a reafirmação de `online` a cada 10 s sai com QoS 0) |

## Campos

**`cps1/sensor`**
```json
{"vagas": [{"id": "V1", "tipo": "comum", "ocupada": true, "interditada": false, "cm": 20},
           {"id": "V2", "tipo": "comum", "ocupada": false, "interditada": false, "cm": 400},
           {"id": "V3", "tipo": "idoso", "ocupada": false, "interditada": false, "cm": 400},
           {"id": "V4", "tipo": "pcd", "ocupada": false, "interditada": false, "cm": 400}],
 "livres": 3, "livres_comuns": 1, "livres_tipo": {"comum": 1, "idoso": 1, "pcd": 1}, "total": 4}
```
Vaga interditada não conta como livre. Republicado a cada mudança e a cada 15 s.

**`cps2/estado`**
```json
{"cancela": "fechada", "fim_curso": "fechada", "modo": "normal", "carro": false, "sentido": "entrada",
 "dentro": 1, "placas": [{"placa": "ABC1D23", "tipo": "comum", "avulso": false, "pago": false}],
 "travada": false, "evasao": 0, "vaga_irregular": "", "vagas_ok": true, "ack": "t1"}
```
`placas` serve para o CPS2 lembrar quem está dentro depois de reiniciar (ele relê o próprio retido uma vez).

**`cps2/sensor` (eventos)**

| `evento` | Quando | Campos extras |
|---|---|---|
| `entrada` | cancela abriu para entrar | `placa`, `tipo`, `sentido`, `cadastrada`, `avulso` |
| `saida` | cancela abriu para sair | `placa`, `tipo`; cadastrada: `valor` (débito) e `saldo` |
| `negado` | não abriu | `placa`, `motivo`: `lotado`, `ja_dentro`, `nao_registrado`, `pagamento_pendente`, `sem_carro_na_cancela` |
| `pagamento` | chegou um pagamento | `placa`, `valor`, `ok`; se `ok` é falso, `motivo: sem_entrada_avulsa` |
| `abertura_manual` | dashboard mandou abrir | – |
| `ajuda_totem` | chegou pedido de ajuda do CPS3 (bip na cancela) | – |
| `modo` | entrou ou saiu da emergência | `modo` |
| `livre` | placa lida durante emergência | `placa`, `motivo: emergencia` |

## Integrações (o que um sistema muda no outro)

1. **Vagas → totem:** CPS1 publica cada vaga com o tipo → CPS3 mostra o número no display, LED verde/vermelho e a cor de cada vaga na fita (verde comum, amarelo idoso, azul PcD, vermelho ocupada, laranja interditada).
2. **Lotado → cancela:** placa comum sem vaga comum livre → CPS2 nega e toca o buzzer. Idoso e PcD entram se houver vaga do seu tipo ou comum.
3. **Evasão:** CPS2 compara as vagas ocupadas do CPS1 com os carros `dentro` (entradas − saídas). Mais ocupadas do que dentro = alguém entrou sem passar pela cancela → `cps2/alarme` evasão → CPS3 pisca o LED vermelho e o dashboard registra.
4. **Cancela travada:** mandou fechar e o fim de curso continua aberto por 3 s → `cps2/alarme` → CPS3 pisca o LED vermelho.
5. **Pagamento → saída:** placa avulsa só sai depois do `pagamento` publicado pelo dashboard.
6. **Emergência:** dashboard publica `{"modo": "emergencia"}` → CPS2 abre e mantém; CPS1 (assina `cps2/estado`) pisca os LEDs; CPS3 pisca a fita em branco.
7. **Ajuda no totem:** botão no CPS3 → `cps3/sensor` → o CPS2 dá um bip na cancela (onde fica o operador) e o dashboard mostra o chamado → operador responde em `cps3/comando` → LED azul fica aceso 10 s.
8. **Confiabilidade:** CPS2 e CPS3 assinam `cps1/status`. Se o CPS1 cai (Last Will `offline`), o totem mostra `----` e a fita pisca laranja, e a cancela esquece as vagas velhas (`vagas_ok: false`) e para de negar por lotado até o CPS1 voltar.
9. **Vaga PcD irregular:** CPS2 compara as vagas PcD ocupadas (CPS1) com os carros PcD cadastrados `dentro`. Mais vagas PcD ocupadas do que carros PcD = alguém sem cadastro PcD parou na vaga → `cps2/alarme` `vaga_irregular` → CPS3 pisca só aquela vaga na fita e o LED vermelho; o dashboard avisa o operador. O CPS2 não sabe qual carro está em qual vaga, só compara as contas.

Se o CPS2 reinicia em emergência, ele relê o `modo` do próprio `cps2/estado` retido e a cancela continua aberta. Se o CPS2 cai em emergência, CPS1 e CPS3 continuam piscando com o último `modo` retido: é falha segura, a evacuação não para porque um equipamento saiu do ar.

Em emergência a cancela fica aberta, mas continua registrando quem entra e sai pela câmera, para a conta de evasão não ficar errada depois.

## Regras de QoS e retain

- Estado e leituras: QoS 0 com retain. Quem conecta depois recebe o último valor na hora, e o loop não trava esperando confirmação.
- Eventos, alarmes, comandos e pagamento: QoS 1, sem retain (um comando retido seria executado de novo a cada reconexão).
- `status`: QoS 1 com retain, publicado `online` ao conectar e `offline` pelo Last Will.
- `ping`: todo CPS que recebe `{"ping": X}` no seu `comando` republica o `estado` com `"ack": X` (usado pelo `scripts/verify`).
