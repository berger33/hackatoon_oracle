# Fatia 15 — RAG com corpus real por escopo

**Data:** 06/11/2026. Base `d2674a25297e1081c...` (topo de `main` da fotografia); branch `arena/65b896b8-hackatoon-oracle`. Nenhum envio externo, modelo real, deploy ou dado real. Produção **NO-GO**.

## O que o plano pede

`auditoria-2026-11-04/PLANO-EXECUCAO.md`, fatia 15: testar isolamento de fontes por perfil e permissão, indisponibilidade, timeout e fallback, corrigindo defeitos do caminho existente, **sem** declarar qualidade de resposta nem entrega de modelo real.

## Inventário antes da mudança

`src/server/ai-rag-real-api.mjs` decide o escopo no servidor, antes do modelo:

| Barreira | Linha de código | Ordem |
|---|---|---|
| método `POST` | `ask` | 1ª |
| mesma origem | `ask` | 2ª |
| `rag_key` na lista fechada (`publico`,`cliente`,`rh`,`marcelo`) | `ask` | 3ª |
| sessão + papel do escopo (`rh`/`admin`, `marcelo`/`admin`) | `authorize` | 4ª |
| consulta 5..500 caracteres | `ask` | 5ª |
| SQL com flag **e** estado (`status IN ('aprovado','publicado')`) no documento e no índice | `retrieve` | 6ª |
| vínculo ativo + conta ativa + unidade para corpus `cliente` | `retrieve` | 7ª |
| `rankApprovedChunks` → modelo só se houver trecho relevante | `ask` | 8ª |
| host do provedor apenas loopback `http:` | `ask` | 9ª |

O teste existente (`tests/ai-rag-real-scope.test.mjs`, 10 casos) injeta um pool que **devolve linhas prontas**: prova a lógica do handler, não o SQL. A lacuna real era essa — nenhuma das condições SQL era exercitada por dados.

## Mudança

`tests/ai-rag-scope-real-db.test.mjs` — 14 casos, no `test:unit` (187 arquivos). Nenhum código de produção alterado.

- Banco: cadeia real de migrações `001..173` em PGlite, montada uma vez e clonada por teste. A `095` **semeia** um índice por `rag_key` (rascunho, não aprovado) e a `173` amarra o corpus do cliente a `client_account_id` com `CHECK` — o teste publica/despublica o índice vigente em vez de inventar um segundo (a coluna é `UNIQUE`).
- Provedor: stub determinístico, identificado como stub. `fetch` é substituído no teste e restaurado em `finally`.
- Origem: réplica fiel do `sameOrigin` de `server.mjs` (a função é local e não é exportada) **mais** uma guarda que falha se o original mudar — sem isso, o teste de origem cruzada poderia ficar verde com uma cópia divergente.

## Resultados (14/14 local)

| Cenário | Esperado | Observado |
|---|---|---|
| Cada escopo só lê o próprio corpus | RH vê só `rh` | fontes `['Férias no RH']`; contexto enviado ao stub sem o documento `marcelo` |
| Staff sem o papel do escopo | 403 antes do banco | `scope_forbidden`, 0 chamadas ao stub |
| Cliente sem vínculo | `empty_scope`, modelo não chamado | `sources: []`, `ollama_used: false` |
| Cliente com vínculo na conta A | só a base A | `['Escala da Conta A']`, contexto sem "conta B" |
| Vínculo revogado / conta suspensa | nada recuperado | `empty_scope` nos dois |
| Flag ligada, `status` = rascunho | nada recuperado | `sources: []` |
| Índice inativo | corpus fechado | `empty_scope` |
| Banco fora | 503 `rag_unavailable` | sem `response` no corpo |
| Provedor 500 / vazio / offline | `ollama_http_error` / `empty_response` / `ollama_timeout_or_offline` | 503, sem `response`, sem `sources` |
| Timeout (abort) | 503 sanitizado | mensagem do stub e pilha ausentes do corpo |
| Host `10.0.0.5` | `ollama_configuration_invalid` | 0 requisições de rede |
| Pergunta sem trecho relevante | `no_relevant_source` | modelo não chamado |
| `rag_key`/consulta/origem inválidos | 400/400/403 | `invalid_rag_key`, `invalid_query` (curta e >500), `same_origin_required` |
| `sameOrigin` do servidor | cruzada e sem Origin/Host barradas | 403 nos três; mesma origem chega ao passo seguinte (`ollama_disabled`) |

Falhas do **próprio teste** encontradas no caminho, todas corrigidas: `ai_rag_chunks.token_count` é `NOT NULL`; o índice por escopo já existe (inserir duplicava `rag_key`); `Error` casava com a chave `"error"` do contrato na checagem de vazamento; papel `marcelo` era barrado antes da validação de consulta; o helper de origem fixava `sameOrigin: () => true` e o caso "origem cruzada" não media nada.

## Limites

- Um único índice por escopo (imposto pela `095`): não há concorrência entre índices do mesmo escopo.
- PGlite serializa consultas; concorrência, réplica, `statement_timeout` e pool esgotado não são exercitados.
- O provedor é stub: **não** prova Ollama, modelo, qualidade, latência, timeout real de 60 s nem comportamento do Qwen3.
- Embedding, curadoria, aprovação por pessoa e auditoria da curadoria não entram neste recorte.
- **Fatia 10 registrada como impedimento de ambiente**: sem Chromium e com download do Playwright bloqueado (`Download failure, code=1`), evidência de navegador não é produzível aqui; os gates existentes seguem pulando como antes.
