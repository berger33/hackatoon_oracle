# Fatia 09 — ciclo staff → cliente (documento do cliente)

**Data:** 06/11/2026. Branch `arena/65b896b8-hackatoon-oracle`. Nenhum deploy, restore, envio externo ou dado real. Produção **NO-GO**.

## O que o plano pede

`auditoria-2026-11-04/PLANO-EXECUCAO.md`, fatia 09: exercitar criar/revisar/aprovar/publicar/ler/revogar nos recursos CLI-05…CLI-08, com cliente correto **e** indevido, banco e UI, corrigindo lacunas demonstradas no contrato vigente — sem declarar aceite humano.

## Recorte escolhido e por quê

Dos recursos CLI-05…CLI-08, o **documento do cliente** é o único com as duas pontas já implementadas: a equipe cria (`handleAdminDocuments`) e o cliente lê (`handleClientDocumentDownload`). Os demais (chamados, visitas, relatórios) têm leitura no portal, mas o ciclo de vida administrativo deles está em outras rotas; cobri-los exigiria inventar fluxo, o que o plano proíbe. Este recorte é o que fecha o ciclo **sem** tocar em regra.

## Inventário antes da mudança

| Etapa | Rota/handler | Regra vigente |
|---|---|---|
| criar | `handleAdminDocuments` POST | sessão admin `marcelo`/`ti` + `identityId` → mesma origem → `accountId` UUID → `validateDocumentMeta` → base64 válido → `idempotency-key` obrigatória → transação com `FOR SHARE` na conta → idempotência por (uploader, chave) → grava arquivo com `flag: 'wx'` → INSERT → auditoria `document_upload` |
| ler (cliente) | `handleClientDocumentDownload` | sessão de cliente → UUID → documento → vínculo ativo + conta ativa + unidade → sha256/tamanho → auditoria `document_download` → bytes |
| revogar | `handleAdminGrantRevoke` | DELETE/POST + mesma origem + sessão admin → motivo obrigatório → `revoked_at`/`revoked_by`/`revoke_reason` → auditoria `grant_revoke` |
| remover documento | **não existe** | `Allow: GET, POST` — o contrato não apaga documento |

## Resultados (13/13 local)

| Cenário | Esperado | Observado |
|---|---|---|
| Staff cria | 201 | linha com `uploaded_by='ti'`, `uploaded_by_identity` = identidade, `storage_key` 48 hex, bytes no disco idênticos, sha256 confere, auditoria `document_upload`/`allowed` |
| Mesma chave de idempotência | 200 `replayed` | mesmo `documentId`, **1 linha**, **nenhum arquivo novo** |
| Mesma chave, outro conteúdo | 409 | `idempotency_conflict`, hash gravado continua o primeiro |
| Chave ausente/curta | 400 | `idempotency_key_required_or_invalid`; banco e disco vazios |
| Conta inexistente / papel `rh` / sem sessão | 404 / 403 / 401 | nada gravado em nenhum dos três |
| Cliente vinculado lê | 200 | bytes **idênticos** aos enviados, `private, no-store`, `nosniff`, auditoria `allowed` |
| Cliente de outra conta | 403 | sem bytes |
| Revogar vínculo | 200 `revoked` | antes: cliente lê; depois: **403**; documento continua no banco |
| Revogar duas vezes | `already_revoked` | **uma** auditoria `grant_revoke`/`allowed` |
| Revogar sem motivo / sem sessão | 400 / 401 | `revoked_at` permanece nulo |
| DELETE/PUT/PATCH em documentos | 405 | `Allow: GET, POST`; documento e arquivo intactos |
| Listagem por conta | 200 | só a conta pedida; conta sem documento devolve `[]`; `rh` recebe 403 |
| Falha no INSERT após gravar arquivo | 503 | **nenhum arquivo órfão** no diretório privado |

O último caso é o que mais importa para operação: o código grava o arquivo antes do INSERT. Forcei a falha do INSERT com um `CHECK` temporário e confirmei que o `catch` remove o arquivo — sem isso, cada falha de banco deixaria lixo privado em disco sem nenhuma linha que o referencie.

## Achado fora do código — o repositório remoto divergiu

Durante esta fatia o checkout foi re-clonado e a guarda N1 (`package-artifacts`) passou a acusar `stale-or-unproven-base`. Medido:

- `origin/main` = `bf58fda` ("Add files via upload"), **não** descendente de `d2674a2` (merge da PR #350) que a fotografia declara como base;
- `bf58fda` tem **um** pai e conteúdo de outro projeto (MediFlow: PDFs, `app/`, `requirements.txt`), então não é o merge publicador desta fotografia;
- o branch desta sessão **continua** descendente direto de `d2674a2`.

**Não mudei a base declarada no ledger**: trocá-la para `bf58fda` afirmaria uma proveniência que o próprio repositório não contém. Restaurei `main` local para `d2674a2` (mesma correção já usada na fatia 07) e registrei o achado. Se o destino do trabalho for o `hackatoon_oracle` tal como está no remoto, o branch não aplica sobre ele — é uma decisão do proprietário, não uma correção técnica.

## Limites

- **UI não exercitada**: sem Chromium neste ambiente (download do Playwright bloqueado), a fatia cobre API + banco + disco, não a tela.
- PGlite serializa consultas: a janela de corrida entre duas requisições simultâneas com a mesma chave não é exercitada de verdade; o teste cobre a repetição sequencial e o índice único.
- PostgreSQL real, storage de objeto, antivírus e disco cheio não são cobertos.
- Nenhum aceite humano: 0/222 continua.
