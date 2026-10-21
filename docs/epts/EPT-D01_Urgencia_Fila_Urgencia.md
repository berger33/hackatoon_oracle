# EPT-D01 — Urgência ou achado crítico → `FILA_URGENCIA_MEDICA`, sem revisão humana

| Campo | Valor |
| --- | --- |
| **ID** | `EPT-D01` |
| **Título** | Urgência ou achado crítico encaminha à fila de urgência com alerta e termina em `PROCESSADO`, sem revisão humana |
| **Versão** | 2.0 — regra alinhada ao `Projeto_oracle.pdf` (antes: `EM_REVISAO`, conforme a EF v1.0) |
| **Origem** | `Projeto_oracle.pdf` — exemplo de resposta (`status: processado`, `requer_auditoria_humana: false`) e item 5 ("Fila de Urgência Médica [...] ou Fila de Revisão Humana em caso de ambiguidade") |
| **Requisitos** | RF-07, RF-13, RF-20, RF-22 · RN-01, RN-03, RN-05 · Regras R1 e R4 do contrato |
| **Critérios §16** | 3 (urgente com alerta, nunca encaminhado somente como rotina) e 7 (evento simulado, sem envio externo) |
| **Prioridade** | Obrigatório |
| **Status** | `NAO_EXECUTADO` |

---

## 1. Objetivo

Provar que um documento com sinal de urgência ou achado crítico é encaminhado a
`FILA_URGENCIA_MEDICA`, com alerta registrado, e **encerrado como `PROCESSADO`, sem revisão
humana** — porque, pelo `Projeto_oracle.pdf`, revisão é consequência de **ambiguidade**, nunca de
urgência isolada.

E provar a fronteira: quando a urgência coexiste com ambiguidade, o caso passa a `EM_REVISAO` e
ganha a `FILA_REVISAO_HUMANA` **além** da fila de urgência.

> **Mudança de regra (21/10/2026).** A Especificação Funcional v1.0 (§5.3 e §8.2) previa
> `EM_REVISAO` para urgência. O time decidiu seguir o `Projeto_oracle.pdf`, cujo exemplo devolve
> `"status": "processado"`, `"requer_auditoria_humana": false` e guarda o objeto em
> `processados/urgentes/`. O contrato (`app/models.py`, regra R1) e os 67 fixtures já refletem essa
> decisão. A EF e a Análise de Requisitos serão atualizadas pela equipe.

## 2. Pré-condições e ambiente

| # | Pré-condição | Como verificar |
| --- | --- | --- |
| 1 | Pipeline de triagem de pé (FastAPI + LangGraph + adaptador Gemini) | `GET /api/v1/health` → `200`, sem dado clínico |
| 2 | Buckets/prefixos OCI configurados por variável de ambiente (RF-28) | um caso de rotina devolve `armazenamento_oci.status = SUCESSO` |
| 3 | Dicionário de medicamentos de alto risco disponível (afeta `Conflito_AltoRisco`) | `rules/medicamentos_alto_risco.csv` presente ou regra equivalente aprovada |
| 4 | Sem stub de score: nenhum caso desta EPT depende de score forçado | nenhum `expected.json` desta EPT tem `modo_fixture` |
| 5 | Massa de dados íntegra | `python3 tests/testar_contrato.py` → `0 falhas` |
| 6 | Nenhum serviço externo de notificação configurado (§16.7) | variáveis de e-mail/Slack/n8n ausentes no ambiente de teste |

## 3. Massa de dados

| Fixture | Papel | Formato | Kit | `expected.json` |
| --- | --- | --- | --- | --- |
| `Matriz_LaudoDeImagem_Pdf` | urgência isolada (caso do brief) | PDF | demo | `tests/fixtures/demo/Matriz_LaudoDeImagem_Pdf/expected.json` |
| `Matriz_LaudoDeImagem_Imagem` | urgência isolada | JPG | catálogo | `tests/fixtures/catalogo/Matriz_LaudoDeImagem_Imagem/expected.json` |
| `Matriz_Receituario_Imagem` | urgência isolada (alto risco) | JPG | demo | `tests/fixtures/demo/Matriz_Receituario_Imagem/expected.json` |
| `Matriz_Guia_Imagem` | urgência isolada | JPG | catálogo | `tests/fixtures/catalogo/Matriz_Guia_Imagem/expected.json` |
| `Conflito_AltoRisco` | urgência isolada (sem texto de urgência) | JPG | catálogo | `tests/fixtures/catalogo/Conflito_AltoRisco/expected.json` |
| `Simultaneo_Urgencia_Score` | **fronteira**: urgência + ambiguidade | PDF | catálogo | `tests/fixtures/catalogo/Simultaneo_Urgencia_Score/expected.json` |
| `Conflito_Prioridade` | **fronteira**: urgência + ambiguidade | TEXTO | catálogo | `tests/fixtures/catalogo/Conflito_Prioridade/expected.json` |

Cinco casos de urgência pura, cinco histórias clínicas distintas, um só desfecho — é o que prova que
a regra vem do sinal de urgência e não do tipo de documento.

## 4. Procedimento

### Parte A — urgência isolada termina em `PROCESSADO`

| # | Ação | Entrada | Resultado esperado |
| --- | --- | --- | --- |
| 1 | Submeter o laudo de imagem em PDF | `POST /api/v1/triagens` (multipart, `arquivo`, `canal_origem=Pronto_Socorro`) | `202 Accepted`; corpo com `documento_id`, `status = RECEBIDO`, `status_url`, `historico_url` |
| 2 | Acompanhar até estado terminal | `GET /api/v1/triagens/{documento_id}` | `RECEBIDO → PROCESSANDO → PROCESSADO` |
| 3 | Conferir a classificação | resposta do passo 2 | `tipo_documento = LAUDO_EXAME_IMAGEM`, `nivel_prioridade = URGENTE`, `score_classificacao = 0.93` |
| 4 | Conferir o sinal de urgência extraído | `dados_extraidos` | `urgencia = SIM`, `diagnostico = "Tromboembolismo pulmonar agudo"`, `cid = null` |
| 5 | Conferir a decisão de roteamento | `decisao_roteamento` | `destinos = ["FILA_URGENCIA_MEDICA"]`, `destino_principal = FILA_URGENCIA_MEDICA`, `requer_auditoria_humana = false` |
| 6 | Conferir o alerta | `decisao_roteamento.notificacao` | `gerada = true`, `canal = SIMULADO_SLACK_PLANTAO`, `status = REGISTRADA`, `mensagem = "ALERTA URGENTE [DOC-BEFDD90A]: Tromboembolismo pulmonar agudo"` |
| 7 | Conferir que **não** há revisão humana | `status` e `decisao_roteamento` | `status = PROCESSADO` e `FILA_REVISAO_HUMANA` ausente de `destinos` |
| 8 | Conferir a ausência de destino de rotina | `decisao_roteamento.destinos` | Nenhum `PRONTUARIO_ELETRONICO`, `FARMACIA_HOSPITALAR` ou `AUDITORIA_AUTORIZACOES` na lista |
| 9 | Conferir que nada saiu do ambiente | log/rede do ambiente de teste | Nenhuma chamada a e-mail, Slack, n8n ou serviço externo; o alerta é só um evento registrado |
| 10 | Conferir o histórico | `GET /api/v1/triagens/{documento_id}/historico` | `200`, eventos em ordem cronológica, incluindo decisão, destino e alerta, cada um com `ator`, `motivo`, `status_anterior`, `status_novo`, `versao_esquema` |
| 11 | Validar o JSON contra o contrato | `python3 tests/testar_contrato.py` | `0 falhas` e ponto fixo: reprocessar o `expected.json` devolve o mesmo JSON |
| 12 | Repetir os passos 1 a 11 para as outras quatro fixtures | JPG do laudo, JPG da receita, JPG da guia, JPG do alto risco | Mesmo desfecho em todas (ver tabela abaixo) |
| 13 | Repetir o passo 1 com o texto puro de uma das fixtures | `POST /api/v1/triagens` (JSON, `documento_texto`) | Mesmo desfecho: o formato de entrada não muda a decisão de urgência |

### Valores esperados por fixture (passo 12)

| Fixture | `documento_id` | `tipo_documento` | Mensagem do alerta |
| --- | --- | --- | --- |
| `Matriz_LaudoDeImagem_Pdf` | `DOC-BEFDD90A` | `LAUDO_EXAME_IMAGEM` | `ALERTA URGENTE [DOC-BEFDD90A]: Tromboembolismo pulmonar agudo` |
| `Matriz_LaudoDeImagem_Imagem` | `DOC-3ACD51ED` | `LAUDO_EXAME_IMAGEM` | `ALERTA URGENTE [DOC-3ACD51ED]: Pneumotórax espontâneo à direita` |
| `Matriz_Receituario_Imagem` | `DOC-291D9643` | `RECEITUARIO_MEDICO` | `ALERTA URGENTE [DOC-291D9643]: Dor pós-operatória aguda intensa` |
| `Matriz_Guia_Imagem` | `DOC-D06D8B78` | `GUIA_PROCEDIMENTO` | `ALERTA URGENTE [DOC-D06D8B78]: Hemorragia digestiva alta` |
| `Conflito_AltoRisco` | `DOC-071326FD` | `RECEITUARIO_MEDICO` | `ALERTA URGENTE [DOC-071326FD]: Fibrilação atrial crônica` |

Em todos os cinco: `status = PROCESSADO`, `score_extracao = 0.91`, `score_combinado = 0.91`,
`limiar_aplicado = 0.85`, `destinos = ["FILA_URGENCIA_MEDICA"]`, `requer_auditoria_humana = false`,
`notificacao.status = REGISTRADA`.

### Parte B — a fronteira: urgência **com** ambiguidade

| # | Ação | Entrada | Resultado esperado |
| --- | --- | --- | --- |
| 14 | Submeter o laudo com urgência e score forçado 0,70 | `POST /api/v1/triagens` (multipart), `FIXTURE_MODE` ativo | `202 Accepted` |
| 15 | Acompanhar até estado terminal | `GET /api/v1/triagens/{documento_id}` | `EM_REVISAO` — **diferente** da Parte A |
| 16 | Conferir os dois destinos | `decisao_roteamento.destinos` | `["FILA_URGENCIA_MEDICA", "FILA_REVISAO_HUMANA"]`, nesta ordem; `destino_principal = FILA_URGENCIA_MEDICA` |
| 17 | Conferir a revisão e o alerta | `requer_auditoria_humana`, `notificacao` | `true` e alerta `REGISTRADA` — a ambiguidade não desliga o alerta |
| 18 | Submeter a guia com prioridade em conflito | `Conflito_Prioridade` | Mesmo desfecho: `EM_REVISAO`, dois destinos, alerta |

## 5. Critérios de verificação

| # | Campo do contrato | Valor esperado | Regra |
| --- | --- | --- | --- |
| 1 | `status` | `PROCESSADO` na Parte A; `EM_REVISAO` na Parte B | R1 e R4 |
| 2 | `classificacao.nivel_prioridade` | `URGENTE` | RF-07 |
| 3 | `dados_extraidos.urgencia` | `SIM` | RF-13 |
| 4 | `decisao_roteamento.destinos` | `["FILA_URGENCIA_MEDICA"]` na Parte A; os dois destinos na Parte B | R1, R4 |
| 5 | `decisao_roteamento.requer_auditoria_humana` | `false` na Parte A; `true` na Parte B | R1, R4 |
| 6 | `decisao_roteamento.notificacao.gerada` | `true` nos dois casos | RF-22, RN-03 |
| 7 | `decisao_roteamento.notificacao.canal` / `.status` | `SIMULADO_SLACK_PLANTAO` / `REGISTRADA` | §16.7 — alerta é simulado |
| 8 | `decisao_roteamento.justificativa_roteamento` | `"Urgência clínica: FILA_URGENCIA_MEDICA com alerta registrado. Sem ambiguidade, segue sem revisão humana."` | RF-23, RN-05 |
| 9 | `decisao_roteamento.regras_acionadas` | contém `RN-03` | §16.12 — rastreabilidade |
| 10 | `qualidade.score_combinado` | `0.91` = `min(0.93, 0.91)` | RF-18, regra R5 |
| 11 | `armazenamento_oci` | `status = SUCESSO`, caminho no prefixo `processados/urgentes/`, sem URL pública | RF-28, RF-30; exemplo do `Projeto_oracle.pdf` |
| 12 | Resposta validada no contrato | `TriagemMediFlow` válido, `versao_esquema = 1.0` | RF-14, RNF-06 |

**Contraprovas (o que não pode acontecer):**

| Situação | Veredito |
| --- | --- |
| Documento urgente terminando em `PRONTUARIO_ELETRONICO`, `FARMACIA_HOSPITALAR` ou `AUDITORIA_AUTORIZACOES` | **FALHA** — é o erro que o critério 3 do §16 proíbe ("nunca encaminhado somente como rotina") |
| Documento urgente sem `notificacao` | **FALHA** — RN-03 |
| Documento urgente **sem ambiguidade** terminando em `EM_REVISAO` ou com `FILA_REVISAO_HUMANA` | **FALHA** — tratou urgência como ambiguidade; é a regressão mais provável desta mudança |
| Documento urgente **com** ambiguidade terminando em `PROCESSADO` | **FALHA** — perdeu a revisão que a ambiguidade exige (R4) |

## 6. Resultado esperado de referência

Bloco `resposta_esperada` de cada `expected.json` listado na seção 3. A comparação é campo a campo,
sem tradução de nomes: o JSON devolvido pela API tem de bater com esse bloco.

Trecho de referência (`Matriz_LaudoDeImagem_Pdf`):

```jsonc
{
  "status": "PROCESSADO",
  "classificacao": {"tipo_documento": "LAUDO_EXAME_IMAGEM", "especialidade": ["Radiologia", "Pneumologia"],
                    "nivel_prioridade": "URGENTE", "score_classificacao": 0.93},
  "qualidade": {"score_extracao": 0.91, "score_combinado": 0.91, "limiar_aplicado": 0.85,
                "campos_ausentes": [], "campos_incertos": [], "conflitos": []},
  "decisao_roteamento": {
    "destino_principal": "FILA_URGENCIA_MEDICA",
    "destinos": ["FILA_URGENCIA_MEDICA"],
    "requer_auditoria_humana": false,
    "justificativa_roteamento": "Urgência clínica: FILA_URGENCIA_MEDICA com alerta registrado. "
                                "Sem ambiguidade, segue sem revisão humana.",
    "notificacao": {"gerada": true, "canal": "SIMULADO_SLACK_PLANTAO", "status": "REGISTRADA"}
  }
}
```

## 7. Pós-condições e limpeza

- Cinco objetos gravados no prefixo `processados/urgentes/` (Parte A) e dois em `auditoria/` (Parte B).
- Sete eventos de alerta registrados no histórico, todos com `status = REGISTRADA`.
- Nenhum efeito fora do ambiente: sem e-mail, Slack ou chamada externa.
- Nenhum segredo (chave, bucket URL assinada, prompt) na resposta, no log ou na interface (RF-27, §16.13).
- `FIXTURE_MODE` desligado ao fim da Parte B.

## 8. Registro de execução

| Data | Executor | Ambiente | Resultado | Evidência | Observação |
| --- | --- | --- | --- | --- | --- |
| | | | PASSOU · FALHOU · BLOQUEADO | | |

## 9. Pendências que travam o teste

| Pendência | Efeito nesta EPT | Tratamento |
| --- | --- | --- |
| **RF-13 pede `sinais`, `motivo` e referência ao conteúdo, mas o contrato v1.0 só expõe `dados_extraidos.urgencia` como enum (`SIM`/`NAO`/`INDETERMINADO`).** | O critério 4 só verifica o enum; os sinais que justificaram a urgência não são observáveis na resposta | Verificar o que é observável hoje (enum) e registrar a lacuna. Quando o contrato expuser os sinais, acrescentar uma asserção de conteúdo a este procedimento |
| **Dicionário de medicamentos de alto risco** não aprovado (§15) | `Conflito_AltoRisco` depende da lista para disparar RN-03 sem texto de urgência | Com o dicionário ausente, executar a EPT com as quatro primeiras fixtures e marcar `Conflito_AltoRisco` como `BLOQUEADO` |
| **Achado crítico** depende de regra clínica aprovada (§15) | A detecção não pode ser inventada pelo modelo | Registrar qual regra/dicionário foi aplicado no campo "Ambiente" do registro de execução |
| **EF v1.0 e Análise de Requisitos ainda dizem o contrário** (§5.3, §8.2: urgência → `EM_REVISAO`) | Quem ler os PDFs pode implementar o comportamento antigo | Atualização dos PDFs pela equipe; até lá, esta EPT e o contrato são a referência |
