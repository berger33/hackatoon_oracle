# Fatia 13 — RH e funcionário: ciclo do documento privado, medido em banco real

**Data:** 06/11/2026. Branch `arena/65b896b8-hackatoon-oracle`. Nenhuma regra alterada. Produção **NO-GO**.

## Escopo

O plano divide a fatia 13 em dois recortes: **documentos/solicitações/ponto** e **comunicados/escala/cursos**, com a exigência de que "hash/comprovante e estados" sejam testados no contrato atual, "sem afirmar HERE/dispositivo/eSocial real nem abrir borda RH".

Este relatório cobre a metade de **documentos privados do funcionário** — o único recorte da fatia com ciclo completo fechado no servidor e exercitável sem hardware. Ponto e escala dependem de dispositivo/geolocalização e continuam sem prova, como estava.

Arquivo de teste: `tests/hr-employee-document-cycle.test.mjs` — **18 casos, 18 verdes**, banco PGlite com a cadeia real de migrações até a **102** (é a 102 que cria `employee_private_documents` e a trilha de acesso).

## O ciclo, como o contrato realmente é

O desenho não é "funcionário envia e o RH publica o envio dele". São dois caminhos distintos, e a diferença importa:

| Etapa | Quem | Efeito medido |
|---|---|---|
| Envio | funcionário | 201, `status='pending'`, `source_authorized=false` **sempre** |
| Envio | RH (`employees.write`) | 201, `pending`; `source_authorized` conforme o corpo |
| Revisão | RH | `under_review` / `approved` / `rejected` (motivo ≥ 5 caracteres) |
| Publicação | RH | só se `source_authorized`; senão **409 `authorized_source_required`** |
| Leitura | funcionário | vê o que ele mesmo enviou **ou** o que foi publicado |

Ou seja: **documento enviado pelo funcionário nunca é publicável**. A justificativa está no requisito ("publicação proveniente de fonte autorizada") e é coerente — o próprio funcionário não pode atestar a autenticidade da própria fonte. Quem publica é o RH, a partir de envio do RH. O caso 13/B fixa isso e prova também que o `CHECK` do banco (`status <> 'published' OR (source_authorized AND published_at IS NOT NULL)`) recusa a mesma coisa por baixo, mesmo que a rota deixasse passar.

## Resultados

| Prova | Medição |
|---|---|
| Envio do funcionário | 201; `pending`; `version=1`; `uploaded_by_kind='employee'`; `content_sha256` 64 hex; bytes em disco idênticos; trilha `upload` 1 linha |
| `employeeId` forjado no corpo | **ignorado** — grava no dono da sessão; o outro funcionário segue vendo `[]` |
| Tipo/vazio | `application/x-executavel` → 400 `invalid_content_type`; base64 vazio → 400 `invalid_file_size`; **0 arquivo** no disco |
| Revisão | `under_review` → `approved`, trilha `review`×2 `actor_kind='staff'`; outro funcionário vê `[]` |
| Rejeição | sem motivo 400 `rejection_reason_required`; motivo "nao" 400; com motivo grava e **o funcionário lê o motivo** |
| Estado inventado | `aprovado`, `PENDING`, ``, `deleted` → 400 `invalid_status`; linha segue `pending` |
| Publicação legítima | RH envia com `sourceAuthorized:true` → publica → 200 com `published_at`; titular lê `published`; outro vê `[]` |
| Publicação indevida | envio do funcionário com `sourceAuthorized:true` no corpo → gravado `false`; PATCH `published` → 409; UPDATE direto → `CHECK` violado; autor segue vendo `pending` |
| Folha/informe | sem `employees.compensation.write` → 403 `compensation_permission_required`, **antes** de INSERT e de escrever arquivo |
| Download do titular | 200, bytes idênticos, `Content-Type`/`Cache-Control: private, no-store`/`nosniff`, trilha `download` 1 linha |
| Download alheio | 404, **zero bytes**, nenhuma trilha de download |
| Arquivo adulterado | mesmo tamanho, conteúdo trocado → 409 `document_integrity_failed`, zero bytes, trilha `integrity_denied` |
| RH sem concessão | PATCH → 403 `permission_scope_denied`, sem trilha de staff, estado intacto |
| Documento inexistente | 404 `document_not_found` |
| Sem sessão | funcionário 401 e RH 401 |
| Reenvio | versão 1 e versão 2 coexistindo, **2 arquivos** distintos no disco |
| Falha de INSERT | CHECK injetado → não-201, 0 linhas e **0 arquivos** (o arquivo escrito antes é removido) |

## Achados de leitura (não são defeitos)

1. **`employeeId` no corpo do funcionário é ignorado de propósito.** O comentário no código diz isso e o teste confirma o efeito. Recusar com 400 também seria defensável; hoje a escolha é ignorar. Não é escalação de privilégio — o registro vai para o dono da sessão.
2. **Publicação é exclusiva do RH.** Não há rota que transforme `source_authorized` em `true` depois do envio. Um documento enviado pelo funcionário fica permanentemente fora do caminho de publicação. É coerente com o requisito, mas é uma decisão de produto: se o RH quiser publicar conteúdo enviado pelo funcionário, precisa reenviar pelo próprio RH.
3. **Documento enviado pelo RH e não publicado não aparece para o funcionário** (nem na lista, nem no download) — o filtro é `uploaded_by_kind='employee' OR status='published'`. O funcionário só vê o que ele mesmo mandou ou o que já foi publicado. O RH vê tudo pela listagem administrativa.

## Limites

- **Sem hardware:** ponto/geolocalização/comprovante de dispositivo e a assinatura de recebimento pelo empregador não têm prova. O hash aqui é do conteúdo enviado, não comprovante de entrega.
- **Sem HERE/eSocial:** nenhuma integração externa foi exercitada.
- **Sem interface:** os testes chamam o handler com sessão injetada; não provam a tela (`RhWorkspace.tsx`) nem o app do funcionário.
- **PGlite:** sem concorrência real; as provas valem para o contrato HTTP + SQL, não para contenção sob carga.
- **Aceite humano:** nenhum. Esta fatia não muda a contagem `0/222`.
