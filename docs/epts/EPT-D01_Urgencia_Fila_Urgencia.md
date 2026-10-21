# EPT-D01 — Urgência ou achado crítico → `FILA_URGENCIA_MEDICA`

| Campo | Valor |
| --- | --- |
| **ID** | `EPT-D01` |
| **Título** | Urgência ou achado crítico encaminha à fila de urgência, com revisão obrigatória e alerta |
| **Versão** | 1.0 |
| **Origem** | Especificação Funcional v1.0 — §8.2, tabela de decisão, **linha 1** ("Urgência/achado crítico") |
| **Requisitos** | RF-07, RF-13, RF-20, RF-21, RF-22 · RN-01, RN-03, RN-05 · Regras R1 e R4 do contrato |
| **Critérios §16** | 3 (urgente com alerta, nunca encaminhado somente como rotina) e 7 (evento simulado, sem envio externo) |
| **Prioridade** | Obrigatório |
| **Status** | `NAO_EXECUTADO` |

---

## 1. Objetivo

Provar que um documento com sinal de urgência ou achado crítico é encaminhado a
`FILA_URGENCIA_MEDICA`, com revisão humana obrigatória e evento de alerta registrado, e que
**nunca** é tratado como rotina — nem quando a confiança é alta, nem quando o tipo do documento
teria outro destino natural (receita → farmácia, guia → auditoria, laudo → prontuário).

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

| Fixture | Formato | Kit | Arquivo | `expected.json` |
| --- | --- | --- | --- | --- |
| `Matriz_LaudoDeImagem_Pdf` | PDF | demo | `tests/fixtures/demo/Matriz_LaudoDeImagem_Pdf/Matriz_LaudoDeImagem_Pdf.pdf` | `tests/fixtures/demo/Matriz_LaudoDeImagem_Pdf/expected.json` |
| `Matriz_LaudoDeImagem_Imagem` | JPG | catálogo | `tests/fixtures/catalogo/Matriz_LaudoDeImagem_Imagem/Matriz_LaudoDeImagem_Imagem.jpg` | `tests/fixtures/catalogo/Matriz_LaudoDeImagem_Imagem/expected.json` |
| `Matriz_Receituario_Imagem` | JPG | demo | `tests/fixtures/demo/Matriz_Receituario_Imagem/Matriz_Receituario_Imagem.jpg` | `tests/fixtures/demo/Matriz_Receituario_Imagem/expected.json` |
| `Matriz_Guia_Imagem` | JPG | catálogo | `tests/fixtures/catalogo/Matriz_Guia_Imagem/Matriz_Guia_Imagem.jpg` | `tests/fixtures/catalogo/Matriz_Guia_Imagem/expected.json` |
| `Conflito_AltoRisco` | JPG | catálogo | `tests/fixtures/catalogo/Conflito_AltoRisco/Conflito_AltoRisco.jpg` | `tests/fixtures/catalogo/Conflito_AltoRisco/expected.json` |

Cinco casos, cinco histórias clínicas distintas, um só desfecho — é o que prova que a regra vem do
sinal de urgência e não do tipo de documento.

## 4. Procedimento

| # | Ação | Entrada | Resultado esperado |
| --- | --- | --- | --- |
| 1 | Submeter o laudo de imagem em PDF | `POST /api/v1/triagens` (multipart, `arquivo`, `canal_origem=Pronto_Socorro`) | `202 Accepted`; corpo com `documento_id`, `status = RECEBIDO`, `status_url`, `historico_url` |
| 2 | Acompanhar até estado terminal | `GET /api/v1/triagens/{documento_id}` | Sequência observada `RECEBIDO → PROCESSANDO → EM_REVISAO`; **nunca** `PROCESSADO` |
| 3 | Conferir a classificação | resposta do passo 2 | `tipo_documento = LAUDO_EXAME_IMAGEM`, `nivel_prioridade = URGENTE`, `score_classificacao = 0.93` |
| 4 | Conferir o sinal de urgência extraído | `dados_extraidos` | `urgencia = SIM`, `diagnostico = "Tromboembolismo pulmonar agudo"`, `cid = null` |
| 5 | Conferir a decisão de roteamento | `decisao_roteamento` | `destinos = ["FILA_URGENCIA_MEDICA"]`, `destino_principal = FILA_URGENCIA_MEDICA`, `requer_auditoria_humana = true` |
| 6 | Conferir o alerta | `decisao_roteamento.notificacao` | `gerada = true`, `canal = SIMULADO_SLACK_PLANTAO`, `status = REGISTRADA`, `mensagem = "ALERTA URGENTE [DOC-BEFDD90A]: Tromboembolismo pulmonar agudo"` |
| 7 | Conferir a ausência de destino de rotina | `decisao_roteamento.destinos` | Nenhum `PRONTUARIO_ELETRONICO`, `FARMACIA_HOSPITALAR`, `AUDITORIA_AUTORIZACOES` ou `FILA_REVISAO_HUMANA` na lista |
| 8 | Conferir que nada saiu do ambiente | log/rede do ambiente de teste | Nenhuma chamada a e-mail, Slack, n8n ou serviço externo; o alerta é só um evento registrado |
| 9 | Conferir o histórico | `GET /api/v1/triagens/{documento_id}/historico` | `200`, eventos em ordem cronológica, incluindo decisão, destino e alerta, cada um com `ator`, `motivo`, `status_anterior`, `status_novo`, `versao_esquema` |
| 10 | Validar o JSON contra o contrato | `python3 tests/testar_contrato.py` | `0 falhas` e ponto fixo: reprocessar o `expected.json` devolve o mesmo JSON |
| 11 | Repetir os passos 1 a 10 para as outras quatro fixtures | JPG do laudo, JPG da receita, JPG da guia, JPG do alto risco | Mesmo desfecho em todas (ver tabela abaixo) |
| 12 | Repetir o passo 1 com o texto puro de uma das fixtures | `POST /api/v1/triagens` (JSON, `documento_texto`) | Mesmo desfecho: o formato de entrada não muda a decisão de urgência |

### Valores esperados por fixture (passo 11)

| Fixture | `documento_id` | `tipo_documento` | `nivel_prioridade` | Mensagem do alerta |
| --- | --- | --- | --- | --- |
| `Matriz_LaudoDeImagem_Pdf` | `DOC-BEFDD90A` | `LAUDO_EXAME_IMAGEM` | `URGENTE` | `ALERTA URGENTE [DOC-BEFDD90A]: Tromboembolismo pulmonar agudo` |
| `Matriz_LaudoDeImagem_Imagem` | `DOC-3ACD51ED` | `LAUDO_EXAME_IMAGEM` | `URGENTE` | `ALERTA URGENTE [DOC-3ACD51ED]: Pneumotórax espontâneo à direita` |
| `Matriz_Receituario_Imagem` | `DOC-291D9643` | `RECEITUARIO_MEDICO` | `URGENTE` | `ALERTA URGENTE [DOC-291D9643]: Dor pós-operatória aguda intensa` |
| `Matriz_Guia_Imagem` | `DOC-D06D8B78` | `GUIA_PROCEDIMENTO` | `URGENTE` | `ALERTA URGENTE [DOC-D06D8B78]: Hemorragia digestiva alta` |
| `Conflito_AltoRisco` | `DOC-071326FD` | `RECEITUARIO_MEDICO` | `URGENTE` | `ALERTA URGENTE [DOC-071326FD]: Fibrilação atrial crônica` |

Em todos os cinco: `status = EM_REVISAO`, `score_extracao = 0.91`, `score_combinado = 0.91`,
`limiar_aplicado = 0.85`, `destinos = ["FILA_URGENCIA_MEDICA"]`, `requer_auditoria_humana = true`,
`notificacao.status = REGISTRADA`.

## 5. Critérios de verificação

| # | Campo do contrato | Valor esperado | Regra |
| --- | --- | --- | --- |
| 1 | `status` | `EM_REVISAO` | §5.3 — urgência é motivo de `EM_REVISAO`; regra R1 |
| 2 | `classificacao.nivel_prioridade` | `URGENTE` | RF-07 |
| 3 | `dados_extraidos.urgencia` | `SIM` | RF-13 |
| 4 | `decisao_roteamento.destinos` | `["FILA_URGENCIA_MEDICA"]` — um destino, não dois | §8.2 linha 1; regra R1 (a `FILA_REVISAO_HUMANA` só entra com ambiguidade, regra R4) |
| 5 | `decisao_roteamento.requer_auditoria_humana` | `true` | §8.2 — "Sim, obrigatória" |
| 6 | `decisao_roteamento.notificacao.gerada` | `true` | RF-22, RN-03 |
| 7 | `decisao_roteamento.notificacao.canal` / `.status` | `SIMULADO_SLACK_PLANTAO` / `REGISTRADA` | §3.2.1 e §16.7 — alerta é simulado |
| 8 | `decisao_roteamento.justificativa_roteamento` | `"Urgência clínica: FILA_URGENCIA_MEDICA com notificação e auditoria humana na própria fila de urgência."` | RF-23, RN-05 |
| 9 | `decisao_roteamento.regras_acionadas` | contém `RN-03` | §16.12 — rastreabilidade |
| 10 | `qualidade.score_combinado` | `0.91` = `min(0.93, 0.91)` | RF-18, regra R5 |
| 11 | `armazenamento_oci` | `status = SUCESSO`, caminho no prefixo de auditoria, sem URL pública | RF-28, RF-30, §13 |
| 12 | Resposta validada no contrato | `TriagemMediFlow` válido, `versao_esquema = 1.0` | RF-14, RNF-06 |

**Contraprova (o caso que não pode acontecer):** se qualquer um dos cinco documentos terminar em
`PROCESSADO`, em `PRONTUARIO_ELETRONICO`/`FARMACIA_HOSPITALAR`/`AUDITORIA_AUTORIZACOES`, ou sem
`notificacao`, o teste **falha** — é exatamente o erro que o critério 3 do §16 proíbe ("nunca
encaminhado somente como rotina").

## 6. Resultado esperado de referência

Bloco `resposta_esperada` de cada `expected.json` listado na seção 3. A comparação é campo a campo,
sem tradução de nomes: o JSON devolvido pela API tem de bater com esse bloco.

Trecho de referência (`Matriz_LaudoDeImagem_Pdf`):

```jsonc
{
  "status": "EM_REVISAO",
  "classificacao": {"tipo_documento": "LAUDO_EXAME_IMAGEM", "especialidade": ["Radiologia", "Pneumologia"],
                    "nivel_prioridade": "URGENTE", "score_classificacao": 0.93},
  "qualidade": {"score_extracao": 0.91, "score_combinado": 0.91, "limiar_aplicado": 0.85,
                "campos_ausentes": [], "campos_incertos": [], "conflitos": []},
  "decisao_roteamento": {
    "destino_principal": "FILA_URGENCIA_MEDICA",
    "destinos": ["FILA_URGENCIA_MEDICA"],
    "requer_auditoria_humana": true,
    "notificacao": {"gerada": true, "canal": "SIMULADO_SLACK_PLANTAO", "status": "REGISTRADA"}
  }
}
```

## 7. Pós-condições e limpeza

- Objeto original e resultado gravados no prefixo de auditoria (§13), não em `processados/`.
- Cinco eventos de alerta registrados no histórico, um por fixture, todos com `status = REGISTRADA`.
- Nenhum efeito fora do ambiente: sem e-mail, Slack ou chamada externa.
- Nenhum segredo (chave, bucket URL assinada, prompt) na resposta, no log ou na interface (RF-27, §16.13).

## 8. Registro de execução

| Data | Executor | Ambiente | Resultado | Evidência | Observação |
| --- | --- | --- | --- | --- | --- |
| | | | PASSOU · FALHOU · BLOQUEADO | | |

## 9. Pendências que travam o teste

| Pendência | Efeito nesta EPT | Tratamento |
| --- | --- | --- |
| **RF-13 pede `sinais`, `motivo` e referência ao conteúdo, mas o contrato v1.0 só expõe `dados_extraidos.urgencia` como enum (`SIM`/`NAO`/`INDETERMINADO`).** | O critério 4 só verifica o enum; os sinais que justificaram a urgência não são observáveis na resposta | Verificar o que é observável hoje (enum) e registrar a lacuna. Quando o contrato expuser os sinais, acrescentar uma asserção de conteúdo a este procedimento |
| **Divergência entre a spec e o brief:** o exemplo do `Projeto_oracle.pdf` mostra um caso urgente com `status = processado` e `requer_auditoria_humana: false`; a spec v1.0 (§5.3 e §8.2) diz `EM_REVISAO` | Se a implementação seguir o brief, os passos 2 e 5 falham | Esta EPT segue a **spec v1.0**, que é normativa. Se a equipe decidir pelo comportamento do brief, a EPT muda de versão e o `expected.json` precisa ser regerado |
| **Dicionário de medicamentos de alto risco** não aprovado (§15) | `Conflito_AltoRisco` depende da lista para disparar RN-03 sem texto de urgência | Com o dicionário ausente, executar a EPT com as quatro primeiras fixtures e marcar `Conflito_AltoRisco` como `BLOQUEADO` |
| **Achado crítico** depende de regra clínica aprovada (§15) | A detecção não pode ser inventada pelo modelo | Registrar qual regra/dicionário foi aplicado no campo "Ambiente" do registro de execução |
