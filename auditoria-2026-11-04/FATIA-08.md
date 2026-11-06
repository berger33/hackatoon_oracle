# Fatia 08 — negativos A/B de escopo (downloads, sessão, conta, unidade, contrato)

**Data:** 06/11/2026. Base `d2674a25297e1081fc698d98504635907a4068fe` (`main`, merge da PR #350); branch `arena/65b896b8-hackatoon-oracle`. Nenhum deploy, restore, envio externo ou dado real. Produção **NO-GO**.

## O que o plano pede (e o que não pede)

`auditoria-2026-11-04/PLANO-EXECUCAO.md`: ampliar os **negativos A/B** já cobertos — sessões revogadas, 401/403, escopo de conta/unidade/contrato — **sem inventar uma nova matriz CLI-02** e sem mudar a regra vigente. Ou seja: exercitar o que o código já decide, com prova observável, em vez de propor permissões novas. A matriz de permissões do portal continua decisão do proprietário (0/222 aceites).

## Inventário antes da mudança

Os caminhos de download já existiam e já eram fail-closed; o que faltava era prova de escopo A/B com **banco real**:

| Caminho | Arquivo | Regra vigente |
|---|---|---|
| Portal — download | `client-space-api.mjs` `handleClientDocumentDownload` | método GET → sessão → UUID → documento → `requireAccountScope` (grant ativo + conta `active` + unidade) → `streamDocument` (sha256+tamanho → auditoria → bytes) |
| Portal — contratos | `client-space-api.mjs` `handleClientContracts` | `contract_scope_mode` `all`/`selected`; `selected` com lista vazia = **zero** contratos |
| Funcionário — download | `employee-api.mjs` `sendPrivateDocument` | sessão de funcionário filtrada por `employee_id` (404 fora do escopo) ou staff com `employees.read` (`hasPermission`) |
| Sessão do cliente | `client-access-api.mjs` `readClientSession` | `revoked_at`, `expires_at`, status da identidade, vínculo MFA |

`createClientSpaceApi` **não** expõe um `handle` genérico: devolve handlers nomeados. O primeiro esboço do teste chamava `api.handle(...)` e falhou 6/12 com `ctx.api.handle is not a function`. O teste passou a chamar exatamente o handler que o despacho do servidor chama (`handleClientDocumentDownload`, `handleClientContracts`) — não foi criado roteador novo.

## Mudança

`tests/security-scope-ab-downloads.test.mjs` — 18 casos, no `test:unit` (186 arquivos). **Nenhum código de produção foi alterado**; nenhuma permissão, rota, mensagem de erro ou status foi mudado. O que mudou foi o **meio de prova**:

- **Schema real, não de conveniência.** O arquivo aplica a cadeia `001..102` das migrações do repositório (as mesmas do runtime), montada uma vez e clonada por teste via `dumpDataDir`/`loadDataDir`. Consequência imediata: os `CHECK`s de verdade passaram a valer — `client_accounts.created_by`, `client_access_grants.reason`, `client_documents.uploaded_by`, `employee_private_documents.document_kind`/`uploaded_by_identity`/`storage_key` único, `auth_permissions.id` sem default. Um schema escrito à mão teria aceitado fixtures que a produção recusa.
- **Bytes reais em disco temporário** e resposta HTTP capturada em memória (`writeHead`/`end`), sem socket.
- **Sessão de produção.** Nos casos de sessão revogada/expirada quem responde é o `readClientSession` de `client-access-api`, lendo `auth_sessions`; um stub de `readClientSession` teria provado apenas que o teste sabe dizer `null`.
- **Controles positivos ao lado de cada negativo** (vínculo vigente com o mesmo leitor, contrato permitido × não permitido, unidade própria × alheia). Sem isso, `403`/`401` não distingue "regra correta" de "tudo quebrado".

## Resultados (18/18 em execução local)

Portal do cliente:

| Cenário | Esperado | Observado |
|---|---|---|
| A: vínculo ativo, documento da própria conta | 200 + bytes idênticos | 200, `private, no-store`, `nosniff`, auditoria `document_download`/`allowed` |
| B: vínculo em **outra** conta (a conta do documento existe e está ativa) | 403 | 403 `forbidden`, sem bytes, auditoria `authorization_denied` |
| B: vínculo revogado / conta `suspended` | 403 | 403, sem bytes |
| B: sem sessão | 401 antes de ler o documento | 401 `client_session_required` |
| B: id não-UUID / inexistente | 400 / 404 | 400 `invalid_document_id` / 404 `document_not_found` |
| Arquivo adulterado (mesmo tamanho, outro conteúdo) | 409, sem bytes | 409 `document_integrity_failed` + auditoria `denied` |
| Falha da auditoria | 503, sem bytes | 503, nenhum byte e nenhum header de entrega |
| B: sessão revogada no servidor (leitor de produção) | 401 | 401 |
| B: sessão expirada; controle com token vigente | 401 / 200 | 401 / 200 com os mesmos bytes |
| B: restrição de unidade para conta fora da unidade | 403 | 403 `forbidden` + auditoria |
| A: restrição de unidade para a própria conta | 200 | 200 |
| B: contrato único permitido / lista vazia | só o permitido / zero | 1 contrato / `[]` |
| A: vínculo `all` | os dois contratos | 2 contratos |

Funcionário e RH:

| Cenário | Esperado | Observado |
|---|---|---|
| A: funcionário baixa o próprio | 200 + `download` | 200, 1 linha `download` |
| B: documento de outro funcionário | 404 | 404, sem bytes |
| B: RH sem concessão | 403 | 403 `permission_scope_denied`, **nenhuma** linha de acesso |
| A: RH com `employees.read` organização | 200 | 200, `actor_kind='staff'` |
| B: sem sessão (funcionário e RH) | 401 | 401 nos dois |
| Adulteração | 409 + `integrity_denied` | 409, 1 linha `integrity_denied` |

## Limites

- Prova **regra de código sobre banco real de teste**; não prova operação em produção, conta de terceiro real nem correção da matriz CLI-02.
- O PGlite aplica as migrações na mesma sessão: não exercita concorrência real de PostgreSQL, réplica, `statement_timeout` ou pool esgotado.
- Os bytes ficam em diretório temporário local; não cobre storage de objeto, antivírus, disco cheio nem corrupção parcial de escrita.
- Chromium, PostgreSQL de verdade, e-mail real e restauração continuam não exercitados nesta fatia.
- Fatia 05 continua **67/68** (E6 administrativo bloqueado por OOM, não repetido); fatia 06 é parcial; client-security/N8 e N9 seguem abertos.
