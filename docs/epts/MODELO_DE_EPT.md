# EPT-XXX — <Título do caso>

**Modelo em branco.** Copiar este arquivo para criar uma EPT, preencher todos os campos e
apagar este aviso. Nenhuma seção pode ficar vazia: se não houver conteúdo, escrever
`Não se aplica` e justificar na seção 9.

| Campo | Valor |
| --- | --- |
| **ID** | `EPT-XXX` — `<D>` decisão, `<A>` aceite, `<E>` erro, `<R>` não funcional + número sequencial |
| **Título** | Sinal ou comportamento sob teste, em uma linha |
| **Versão** | 1.0 |
| **Origem** | Seção e linha da Especificação Funcional v1.0 (ex.: §8.2 linha 1) |
| **Requisitos** | RF-xx, RN-xx cobertos |
| **Critérios §16** | Números dos critérios de aceite atendidos |
| **Prioridade** | Obrigatório · Recomendado · Opcional |
| **Status** | `NAO_EXECUTADO` · `EM_EXECUCAO` · `PASSOU` · `FALHOU` · `BLOQUEADO` |

---

## 1. Objetivo

O que este procedimento prova, em uma ou duas frases. Deve repetir o comportamento descrito na
especificação, citando a seção — não a interpretação de quem escreve.

## 2. Pré-condições e ambiente

| # | Pré-condição | Como verificar |
| --- | --- | --- |
| 1 | Pipeline MediFlow de pé (FastAPI + LangGraph + adaptador Gemini) | `GET /api/v1/health` → 200 |
| 2 | Buckets/prefixos OCI configurados por variável de ambiente | `armazenamento_oci.status = SUCESSO` em um caso de rotina |
| 3 | `FIXTURE_MODE` / stub de score ativo **quando o caso depender de score** | Executar um caso com `modo_fixture` e conferir o score devolvido |
| 4 | Massa de dados íntegra | `python3 tests/testar_contrato.py` → 0 falhas |

## 3. Massa de dados

| Fixture | Formato | Kit | Caminho | `expected.json` |
| --- | --- | --- | --- | --- |
| `<ID>` | TXT / PDF / JPG | demo · catálogo | `tests/fixtures/<kit>/<ID>/<ID>.<ext>` | `tests/fixtures/<kit>/<ID>/expected.json` |

## 4. Procedimento

| # | Ação | Entrada | Resultado esperado |
| --- | --- | --- | --- |
| 1 | Enviar documento | `POST /api/v1/triagens` | `202 Accepted` com `documento_id`, `status = RECEBIDO`, `status_url` |
| 2 | Acompanhar até estado terminal | `GET /api/v1/triagens/{documento_id}` | `RECEBIDO → PROCESSANDO → <terminal>` |
| 3 | Conferir classificação | — | campo a campo, conforme item 5 |
| 4 | Conferir decisão de roteamento | — | campo a campo, conforme item 5 |
| 5 | Repetir para cada fixture da seção 3 | — | Mesmo desfecho em todos os formatos |

## 5. Critérios de verificação

| # | Campo do contrato | Valor esperado | Regra |
| --- | --- | --- | --- |
| 1 | `status` | `<valor>` | R1..R7 do contrato |
| 2 | `decisao_roteamento.destinos` | `["<destino>"]` | §8.2 |
| 3 | `decisao_roteamento.requer_auditoria_humana` | `true` / `false` | RF-21 |
| 4 | `decisao_roteamento.notificacao` | objeto ou `null` | RF-22 |
| 5 | `qualidade.score_combinado` | `min(classificação, extração)` | RF-18 |

## 6. Resultado esperado de referência

Bloco `resposta_esperada` do `expected.json` do fixture citado. A comparação é campo a campo, sem
tradução de nomes: o JSON da API tem de bater com este bloco.

## 7. Pós-condições e limpeza

- Objeto gravado no OCI no prefixo correspondente ao estado (§13).
- Evento registrado no histórico do `documento_id`.
- Nenhum efeito fora do ambiente de teste: sem e-mail, Slack ou chamada externa (§16.7).

## 8. Registro de execução

| Data | Executor | Ambiente | Resultado | Evidência | Observação |
| --- | --- | --- | --- | --- | --- |
| | | | PASSOU · FALHOU · BLOQUEADO | caminho do log/print | |

## 9. Pendências que travam o teste

Pendências da §15 da especificação que afetam este caso, e o que fazer enquanto não forem decididas.
