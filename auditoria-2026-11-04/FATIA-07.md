# Fatia 07 — transporte da fila administrativa de e-mails

**Data:** 06/11/2026 · **Base:** `d2674a25297e1081fc698d98504635907a4068fe` (`main`, merge da PR #350) · **Branch:** `arena/65b896b8-hackatoon-oracle`

**Escopo autorizado:** conectar apenas o transporte previsto pelo contrato existente (`MAIL_*`), com testes locais de configuração, falha, retry e prevenção de duplicidade; **sem envio externo**, sem deploy, sem restore e sem operação externa.

## 1. Estado medido antes de alterar

O achado **N7** da auditoria de 02/11 (`docs/AUDITORIA-PENDENCIAS-2026-11-02.md:163,204`) descrevia a ausência de ligação: `server.mjs` criava `createAdminNotificationsApi({ …, mailer: null })`. `src/server/admin-notifications-api.mjs` repassava `mailer: ctx.mailer` a `notificationQueue.processNext({ mailer })`, e `src/server/notification-queue.mjs` mantinha este caminho:

| Situação | Comportamento vigente antes desta fatia |
| --- | --- |
| `mailer` nulo **e** caixa local disponível | grava em `local_outbox_messages`, marca `status='local_outbox'`, nunca `sent` |
| `mailer` nulo **e** caixa local indisponível | `not_configured`, `failed` com backoff e, no limite, `dead` |
| `mailer` presente | dois ramos: função (`await mailer(row)`) ou objeto (`mailer.sendMail({ to, subject, text })`) |

Inventário confirmado por leitura do código no commit de base:

- `MAIL_*` era lido **apenas** em `sendLeadEmail` (`server.mjs`), que monta o próprio transporte do `nodemailer` — outro caminho, intocado;
- `.env.example` declarava a limitação ("preencher MAIL_* não a conecta"); `docs/PRODUCAO-GATE.md` §6 registrava "fila administrativa: bloqueada nesta base";
- `tests/backup-gate-documentation.test.mjs` exigia literalmente `mailer: null` em `server.mjs` como **gate transitório** ("a fatia de conexão da fila deverá reconciliar este contrato");
- **nenhuma migração era necessária**: `notification_queue` (011) e `local_outbox_messages` + colunas de reivindicação (100) já existiam, e as ações de auditoria `notification_send`/`notification_failed`/`notification_dead`/`notification_local_outbox` já constavam do `CHECK`. **A migração 184 continua livre.**

**Baseline local antes da alteração:** `npm ci` (83 pacotes, 12 s) e `npm test` **1632/1632, exit 0** em 61 s.

## 2. O que foi alterado

| Arquivo | Alteração | Natureza |
| --- | --- | --- |
| `src/server/admin-mailer.mjs` | **novo**: leitura/validação de `MAIL_*`, criação do transporte e envio de uma linha da fila | aditivo |
| `server.mjs` | `+20/−1`: importa o módulo e troca `mailer: null` por `mailer: adminMailer`; registra o estado pronto sem segredo | substituição do ponto de injeção |
| `tests/admin-mail-transport.test.mjs` | **novo** (9 testes): configuração, falha, retry, duplicidade e concorrência com SMTP de captura real | aditivo |
| `tests/backup-gate-documentation.test.mjs` | o gate transitório passou a exigir o estado novo (transporte ligado e fail-closed) | reconciliação do contrato |
| `docs/PRODUCAO-GATE.md`, `.env.example`, `README.md` | texto de SMTP/fila atualizado; limite de entrega declarado | documentação |
| `docs/E15-ROTAS-CATALOGO-2026-11-02.json`, `docs/E15-SOMBREADAS-DECISAO-2026-11-02.json`, `docs/REQUISITOS-222-INVENTARIO-2026-10-27.json`, `docs/REQUISITOS-222-REAUDITORIA-INVENTARIO-2026-10-27.md` | artefatos derivados regenerados/remarcados (ver §5) | inventário |
| `package.json` | `test:unit` lista o teste novo (182 → 183 arquivos) | registro de teste |

### 2.1 Contrato do transporte (fail-closed)

`readMailTransportConfig(env)` devolve `ready`, `not_configured` ou `invalid`:

| Entrada | Estado | Efeito |
| --- | --- | --- |
| sem `MAIL_HOST` e sem `MAIL_FROM` | `not_configured` | nenhum transporte (`null`), caminho vigente preservado |
| host **e** remetente válidos | `ready` | transporte criado |
| só host ou só remetente | `invalid` | `null` + diagnóstico `incomplete_mail_configuration` |
| porta não inteira/fora de 1..65535 | `invalid` | `invalid_mail_port` |
| `MAIL_SECURE` fora de true/false/1/0/sim/não | `invalid` | `invalid_mail_secure` (não se adivinha TLS) |
| remetente implausível | `invalid` | `invalid_mail_from` |
| usuário sem senha / senha sem usuário | `invalid` | `missing_mail_password` / `orphan_mail_password` |

Regras herdadas do caminho de lead, mantidas para não haver dois contratos: porta padrão 587 e TLS implícito quando `MAIL_SECURE=true` **ou** porta 465.

### 2.2 Prova de envio

`sendNotification(row)` só devolve `"sent"` quando o provedor **aceita** o destinatário (`accepted` contendo o endereço) ou devolve identificador de mensagem. Recusa explícita (`accepted: []`), resultado vazio ou exceção viram erro; a fila traduz erro em `failed` + backoff e, no limite de `max_attempts`, em `dead` — nunca em `sent`. O remetente configurado entra no envelope (`MAIL FROM:<…>`), o que o ramo `mailer.sendMail` da fila não fazia sozinho (`MAIL FROM:<>`); por isso o transporte é exposto como **função** (ramo que monta a mensagem neste módulo) e `sendMail` também injeta `from`.

## 3. Provas locais

Executadas neste sandbox (2 vCPU, 3,9 GiB, Node 22.22.3). Nenhum envio externo: o SMTP de captura é um servidor mínimo em `127.0.0.1` com porta efêmera, e o banco é PGlite com as migrações `003`, `011` e `100` do próprio repositório.

| Prova | Resultado |
| --- | --- |
| Configuração: ausente, completa, parcial, porta inválida, `MAIL_SECURE` inválido, remetente inválido, senha órfã, usuário sem senha | **ok**; diagnóstico só com códigos estáveis, sem valor sensível |
| Fail-closed: ambiente vazio e configuração parcial não criam transporte | **ok**; diagnóstico registrado sem ecoar o host |
| Envio capturado local | **ok**; 1 mensagem no fio para 1 linha da fila, envelope `MAIL FROM:<avisos@gruposeg.example>` → `RCPT TO:<operador@…>`, assunto e corpo conferidos após decodificação MIME, `X-Seg-Notification-Id` presente |
| Estado após envio | `sent`, `attempts=1`, `sent_at` preenchido, `last_error` nulo, auditoria `notification_enqueue` + `notification_send` |
| Duplicidade (mesma `dedup_key`) | **ok**; segunda chamada devolve `dedup: true`, mesma linha, **1** registro no banco, **1** e-mail |
| Reprocessar fila já enviada | **0** itens processados, **0** e-mail novo |
| Falha do provedor (`451` no remetente) | **ok**; `failed`, `last_error` com o motivo, `sent_at` nulo, backoff de 60 s respeitado (nova chamada não reenvia antes do prazo) |
| Retry explícito após falha | **ok**; `retry()` devolve a linha para `queued`, novo envio confirma `sent`, `attempts=2` |
| Falha repetida até o limite (`max_attempts=2`) | **ok**; `dead`, `attempts=2`, `sent_at` nulo, motivo preservado, auditoria `notification_enqueue → notification_failed → notification_dead` |
| Concorrência: dois consumidores no mesmo banco | **ok**; exatamente **1** envio confirmado e **1** mensagem |
| Recusas que não podem virar "sent" | **ok**; destinatário inválido, `accepted: []` e resultado sem prova de aceite lançam erro |
| Ramo `mailer.sendMail` da fila | **ok**; `sent` e envelope com o remetente configurado |
| Sem SMTP: caixa local | **ok**; `local_outbox`, `sent_at` nulo, entrega na caixa local preservada |
| Estabilidade do arquivo | **9/9 em 3 execuções consecutivas** |
| Suíte completa | `npm test` **1641/1641, exit 0** (1632 da base + 9 desta fatia) |
| Estáticas | `npm run typecheck` exit 0; `npm run build` exit 0; `node scripts/qa-wave0-static.mjs` **5/5** |

## 4. Preservação verificada

- **Lead:** `sendLeadEmail` não foi tocado (transporte próprio, `LEADS_NOTIFY_EMAIL`, retorno `not_configured`).
- **Autenticação do cliente:** `trySendAuthEmail`/`localOutbox` inalterados.
- **Fila:** `notification-queue.mjs` e `admin-notifications-api.mjs` **não foram editados**; estados, backoff, reivindicação atômica, permissões (`ti`/`admin`/`marcelo` para processar) e auditoria seguem os mesmos.
- **Comportamento sem SMTP:** idêntico ao anterior (`null` → caixa local / `not_configured`), coberto por teste.
- **Dados e contratos de API:** nenhuma rota, campo ou resposta alterada; nenhuma migração criada (184 segue livre).

## 5. Reconciliação de inventários derivados (com medição)

Mudar `server.mjs` e acrescentar dois arquivos invalida artefatos derivados. Todos foram **regenerados por script** ou remarcados a partir da medida, nunca "ajustados para passar":

| Artefato | Ação | Medida |
| --- | --- | --- |
| `docs/E15-ROTAS-CATALOGO-2026-11-02.json` | `node scripts/e15-route-catalog.mjs` (regeneração oficial) | borda 1517, despacho 1735, handlers 1704, inalcançáveis 0, sombreadas 7 (3 intencionais) |
| `docs/E15-SOMBREADAS-DECISAO-2026-11-02.json` | remarcação das 4 sombreadas + prefixo de sha256 | linhas `3211/3214/3217/3223`, cobertura `2827`, sha256 `d3418dbee9eabb87…`; as 9 decisões e a decisão `manter_rota` não mudaram |
| `docs/REQUISITOS-222-INVENTARIO-2026-10-27.json` | `node scripts/requisitos-222-inventory.mjs` | arquivos varridos 1742 → **1744** (os dois arquivos novos); 222 IDs, classes e aceite inalterados |
| `docs/REQUISITOS-222-REAUDITORIA-INVENTARIO-2026-10-27.md` | §Método | "1.744 arquivos após a fatia 07" |

Nenhuma classe de evidência foi promovida e o aceite humano continua **0/222**.

## 6. Limites — o que esta fatia NÃO prova

- **Entrega real:** o provedor usado nas provas é um SMTP de captura em loopback. Não há prova de recebimento em provedor externo, reputação de domínio, SPF/DKIM, limites de taxa do fornecedor nem caixa de entrada real.
- **Autenticação SMTP:** o caminho com `MAIL_USER`/`MAIL_PASSWORD` é validado por configuração, mas as provas de envio usam servidor local sem autenticação. STARTTLS/TLS não foram exercitados.
- **Operação:** nenhum processo de produção, deploy, restore ou reenvio real foi executado. Windows não coberto.
- **Disparo:** a fila é processada quando um operador autorizado chama `POST /api/admin/notifications/process`; não há worker autônomo novo, e isso não foi alterado.
- **N7 não está "resolvido" no sentido de produto:** a ligação existe e é testada; a promessa de "aviso por e-mail funciona" continua dependendo de configuração real e verificação de entrega por quem opera.

## 7. Estado final

- Produção segue **NO-GO**; aceite humano **0/222**; reauditoria integral **0/222**.
- Fatia 05 continua **67/68** (E6 administrativo pendente por OOM) — **não** foi repetida nesta sessão, por decisão de não repetir o E6 em ambiente insuficiente.
- N8/N9 seguem abertos.
- `npm test` **1641/1641**; nenhuma migração criada; lockfile inalterado.
