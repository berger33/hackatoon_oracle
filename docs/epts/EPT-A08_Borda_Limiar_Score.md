# EPT-A08 — Borda do limiar: 0,84 revisa; 0,85 não revisa por esse critério

| Campo | Valor |
| --- | --- |
| **ID** | `EPT-A08` |
| **Título** | Comparação estrita do limiar de confiança (`< 0,85` revisa, `= 0,85` não revisa) |
| **Versão** | 1.0 |
| **Origem** | Especificação Funcional v1.0 — §16 critério 8 · §15 decisão 4 · RF-18 · RN-02 |
| **Requisitos** | RF-17, RF-18, RF-21 · RN-02, RN-05 · Regras R3, R4 e R5 do contrato |
| **Critérios §16** | 8 (score abaixo de 0,85 revisa; igual ao limiar não é encaminhado por esse critério isoladamente) |
| **Prioridade** | Obrigatório |
| **Status** | `NAO_EXECUTADO` |

---

## 1. Objetivo

Provar as **duas bordas** do limiar de confiança com o mesmo conteúdo clínico de rotina:

- `score_combinado = 0,84` → revisão humana obrigatória, e o destino do tipo **é substituído** por
  `FILA_REVISAO_HUMANA`;
- `score_combinado = 0,85` → **não** há revisão por esse critério, e o documento segue para o
  destino natural do seu tipo (`FARMACIA_HOSPITALAR`).

E provar que a comparação é **estrita** (`< 0,85`), e não `<= 0,85`: um documento no valor exato do
limiar não pode ser barrado.

## 2. Pré-condições e ambiente

| # | Pré-condição | Como verificar |
| --- | --- | --- |
| 1 | Pipeline de triagem de pé | `GET /api/v1/health` → `200` |
| 2 | **`FIXTURE_MODE` ativo no adaptador Gemini**, com o mapa de score por `documento_id` | Submeter `Borda_Score_084` e conferir `score_extracao = 0.84` na resposta — se vier outro valor, o stub não está ativo |
| 3 | Os três `expected.json` desta EPT declaram `modo_fixture.score_forcado` | `python3 -c "import json; ..."` ou leitura direta do arquivo |
| 4 | Massa de dados íntegra | `python3 tests/testar_contrato.py` → `0 falhas` |

> **Sem o stub, este teste é intermitente e não serve como evidência.** O score devolvido pelo modelo
> varia entre execuções; a borda 0,84/0,85 só é observável com score determinístico. Se o stub não
> existir, a EPT fica `BLOQUEADA`, nunca `FALHOU` — a falha seria do ambiente, não do sistema.

## 3. Massa de dados

| Fixture | Papel | Formato | Kit | `modo_fixture.score_forcado` |
| --- | --- | --- | --- | --- |
| `Borda_Score_084` | **Abaixo** do limiar | TXT (também PDF e JPG) | demo | `score_classificacao = 0.92`, `score_extracao = 0.84` |
| `Borda_Score_085` | **Exatamente no** limiar | TXT (também PDF e JPG) | catálogo | `score_classificacao = 0.94`, `score_extracao = 0.85` |
| `Simultaneo_Urgencia_Score` | Extensão: score baixo **com** urgência | PDF (também TXT e JPG) | catálogo | `score_classificacao = 0.88`, `score_extracao = 0.70` |

Os dois primeiros são receitas de rotina, legíveis e completas: **a única diferença entre eles é o
score**. É o que permite atribuir a revisão ao limiar, e não ao conteúdo.

## 4. Procedimento

### Parte A — 0,84: abaixo do limiar

| # | Ação | Entrada | Resultado esperado |
| --- | --- | --- | --- |
| 1 | Submeter a receita com score forçado 0,84 | `POST /api/v1/triagens` (JSON, `documento_texto`) | `202 Accepted` com `documento_id` e `status = RECEBIDO` |
| 2 | Acompanhar até estado terminal | `GET /api/v1/triagens/{documento_id}` | `RECEBIDO → PROCESSANDO → EM_REVISAO` |
| 3 | Conferir os scores | `classificacao` e `qualidade` | `score_classificacao = 0.92`, `score_extracao = 0.84`, `score_combinado = 0.84`, `limiar_aplicado = 0.85` |
| 4 | Conferir que o documento está **correto** | `classificacao`, `dados_extraidos`, `qualidade` | `RECEITUARIO_MEDICO`, `ROTINA`, `campos_ausentes = []`, `campos_incertos = []`, `conflitos = []` — o desfecho de revisão vem **só** do score |
| 5 | Conferir a decisão | `decisao_roteamento` | `destinos = ["FILA_REVISAO_HUMANA"]`, `destino_principal = FILA_REVISAO_HUMANA`, `requer_auditoria_humana = true` |
| 6 | Conferir o destino substituído | `decisao_roteamento.destinos` | `FARMACIA_HOSPITALAR` **não** aparece: sem urgência, a revisão substitui o destino do tipo (regra R3) |
| 7 | Conferir a ausência de alerta | `decisao_roteamento.notificacao` | `null` — não há urgência (§8.2, linha 2: "Não, salvo urgência simultânea") |
| 8 | Conferir a justificativa | `justificativa_roteamento`, `regras_acionadas` | `"Revisão humana obrigatória: score combinado 0.84 < limiar 0.85."`; regra `RF-18`/`RN-02` rastreável |

### Parte B — 0,85: exatamente no limiar

| # | Ação | Entrada | Resultado esperado |
| --- | --- | --- | --- |
| 9 | Submeter a receita com score forçado 0,85 | `POST /api/v1/triagens` | `202 Accepted` |
| 10 | Acompanhar até estado terminal | `GET /api/v1/triagens/{documento_id}` | `RECEBIDO → PROCESSANDO → PROCESSADO` |
| 11 | Conferir os scores | `classificacao` e `qualidade` | `score_classificacao = 0.94`, `score_extracao = 0.85`, `score_combinado = 0.85`, `limiar_aplicado = 0.85` |
| 12 | Conferir a decisão | `decisao_roteamento` | `destinos = ["FARMACIA_HOSPITALAR"]`, `requer_auditoria_humana = false`, `notificacao = null` |
| 13 | Conferir que o limiar **não** barrou | passos 10 e 12 em conjunto | Documento com score igual ao limiar não é encaminhado à revisão por esse critério — se for, a comparação está `<=` e está errada (RF-18) |

### Parte C — score baixo com urgência (não rebaixa a urgência)

| # | Ação | Entrada | Resultado esperado |
| --- | --- | --- | --- |
| 14 | Submeter o laudo com score forçado 0,70 e urgência | `POST /api/v1/triagens` (multipart) | `202 Accepted` |
| 15 | Acompanhar até estado terminal | `GET /api/v1/triagens/{documento_id}` | `EM_REVISAO` |
| 16 | Conferir os dois destinos | `decisao_roteamento.destinos` | `["FILA_URGENCIA_MEDICA", "FILA_REVISAO_HUMANA"]`, **nesta ordem**: `destino_principal = FILA_URGENCIA_MEDICA` |
| 17 | Conferir que o alerta sobreviveu ao score baixo | `decisao_roteamento.notificacao` | `gerada = true`, `canal = SIMULADO_SLACK_PLANTAO`, `status = REGISTRADA` |
| 18 | Conferir a persistência | `armazenamento_oci` | `status = SUCESSO`, caminho no prefixo de auditoria |

### Parte D — reprodutibilidade

| # | Ação | Resultado esperado |
| --- | --- | --- |
| 19 | Repetir as partes A e B três vezes, em execuções separadas | Mesmo `status`, mesmos `destinos`, mesmos scores nas três — o stub elimina a variação do modelo |
| 20 | Validar os `expected.json` contra o contrato | `python3 tests/testar_contrato.py` → `0 falhas`, ponto fixo |

## 5. Critérios de verificação

| # | Campo do contrato | `Borda_Score_084` | `Borda_Score_085` | `Simultaneo_Urgencia_Score` | Regra |
| --- | --- | --- | --- | --- | --- |
| 1 | `status` | `EM_REVISAO` | `PROCESSADO` | `EM_REVISAO` | §5.3 |
| 2 | `classificacao.tipo_documento` | `RECEITUARIO_MEDICO` | `RECEITUARIO_MEDICO` | `LAUDO_EXAME_IMAGEM` | RF-05 |
| 3 | `classificacao.nivel_prioridade` | `ROTINA` | `ROTINA` | `URGENTE` | RF-07 |
| 4 | `score_classificacao` | `0.92` | `0.94` | `0.88` | RF-17 |
| 5 | `score_extracao` | `0.84` | `0.85` | `0.70` | RF-18 |
| 6 | `score_combinado = min(4, 5)` | `0.84` | `0.85` | `0.70` | RF-18, regra R5 |
| 7 | `limiar_aplicado` | `0.85` | `0.85` | `0.85` | RF-18 |
| 8 | Revisão por score? | **Sim** (`0,84 < 0,85`) | **Não** (`0,85` não é `< 0,85`) | **Sim** | §16.8, regra R5 |
| 9 | `destinos` | `["FILA_REVISAO_HUMANA"]` | `["FARMACIA_HOSPITALAR"]` | `["FILA_URGENCIA_MEDICA", "FILA_REVISAO_HUMANA"]` | §8.2, regras R3 e R4 |
| 10 | `requer_auditoria_humana` | `true` | `false` | `true` | RF-21 |
| 11 | `notificacao` | `null` | `null` | `gerada = true`, `status = REGISTRADA` | RF-22 |
| 12 | `justificativa_roteamento` | `"Revisão humana obrigatória: score combinado 0.84 < limiar 0.85."` | `"Classificação de rotina: RECEITUARIO_MEDICO encaminhado para FARMACIA_HOSPITALAR."` | `"Urgência com ambiguidade: mantém FILA_URGENCIA_MEDICA e acrescenta FILA_REVISAO_HUMANA. score combinado 0.70 < limiar 0.85."` | RF-23, RN-05 |
| 13 | `campos_ausentes` / `campos_incertos` / `conflitos` | `[]` / `[]` / `[]` | `[]` / `[]` / `[]` | `[]` / `[]` / `[]` | A revisão destes casos é **só** de score |

**Contraprova (o caso que não pode acontecer):** `Borda_Score_085` em `EM_REVISAO` com
`justificativa` mencionando limiar significa comparação `<=` e **falha** o teste. Do mesmo modo,
`Borda_Score_084` com destino `FARMACIA_HOSPITALAR` na lista de destinos falha o teste.

## 6. Resultado esperado de referência

Bloco `resposta_esperada` de cada `expected.json` listado na seção 3, comparado campo a campo com a
resposta da API, sem tradução de nomes.

Trecho de referência (`Borda_Score_085` — a borda que **não** revisa):

```jsonc
{
  "status": "PROCESSADO",
  "classificacao": {"tipo_documento": "RECEITUARIO_MEDICO", "especialidade": ["Clínica Médica", "Alergologia"],
                    "nivel_prioridade": "ROTINA", "score_classificacao": 0.94},
  "qualidade": {"score_extracao": 0.85, "score_combinado": 0.85, "limiar_aplicado": 0.85,
                "campos_ausentes": [], "campos_incertos": [], "conflitos": []},
  "decisao_roteamento": {
    "destino_principal": "FARMACIA_HOSPITALAR",
    "destinos": ["FARMACIA_HOSPITALAR"],
    "requer_auditoria_humana": false,
    "notificacao": null
  }
}
```

## 7. Pós-condições e limpeza

- `Borda_Score_085` gravado no prefixo `processados/`; os outros dois, no prefixo de auditoria (§13, RF-29).
- Três históricos distintos, cada um com o evento de decisão e o `score_combinado` registrado.
- `FIXTURE_MODE` desligado ao fim da execução: deixá-lo ativo invalida qualquer outro teste de score.

## 8. Registro de execução

| Data | Executor | Ambiente | Resultado | Evidência | Observação |
| --- | --- | --- | --- | --- | --- |
| | | | PASSOU · FALHOU · BLOQUEADO | | |

## 9. Pendências que travam o teste

| Pendência | Efeito nesta EPT | Tratamento |
| --- | --- | --- |
| **`FIXTURE_MODE` / stub de score não existe na implementação** | Os scores reais do modelo variam; a borda 0,84/0,85 não é observável de forma reprodutível | EPT fica `BLOQUEADA` até o stub existir. Nunca registrar `FALHOU` por variação de score do modelo |
| **Comparação do limiar (`<` × `<=`)** | A spec diz "abaixo do limiar" e "igual ao limiar não é encaminhado"; o contrato fixa `<` estrito (R5) | Se a implementação usar `<=`, o passo 13 falha — é falha real, não do ambiente |
| **A prioridade `RECOMENDADO` de `Borda_Score_085`** (manifesto) | Menor que `OBRIGATORIO`, mas a borda é o único lugar onde `>= limiar` é provado | Executar em toda rodada de regressão de regras de decisão |
| **Origem do score** (RF-17: não tratar score autorrelatado como probabilidade calibrada) | Os valores forçados pelo stub não medem a calibração do modelo | Registrar, no campo "Ambiente", que os scores desta EPT são injetados e **não** são evidência de precisão (isso é `EPT-R01`) |
