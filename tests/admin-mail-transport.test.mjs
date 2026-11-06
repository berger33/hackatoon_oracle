import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { createServer } from 'node:net';
import { readFile } from 'node:fs/promises';
import nodemailer from 'nodemailer';
import { PGlite } from '@electric-sql/pglite';

import {
  MAILER_STATE,
  readMailTransportConfig,
  createAdminMailTransport,
  describeAdminMailerState,
} from '../src/server/admin-mailer.mjs';
import { createNotificationQueue } from '../src/server/notification-queue.mjs';

// Fatia 07 — transporte da fila administrativa de e-mails.
//
// O que este arquivo prova, e com que instrumento:
//
//   * CONFIGURAÇÃO: `readMailTransportConfig` classifica ausente, completo,
//     parcial e inválido sem inventar remetente/host e sem devolver valores
//     sensíveis nos diagnósticos.
//   * LIGAÇÃO: o transporte injetado é o único caminho usado; sem configuração
//     devolve `null` e a fila mantém o comportamento vigente (caixa local).
//   * ENTREGA: prova em SMTP DE CAPTURA REAL E LOCAL (servidor mínimo em
//     loopback, nesta máquina — nada sai da máquina) e leitura do envelope
//     recebido, com remetente, destinatário, assunto e corpo conferidos no
//     fio. Não é mock de função: é conexão TCP + protocolo SMTP de verdade.
//   * FALHA/RETRY: falha do provedor vira `failed` + backoff; falha repetida
//     vira `dead` no limite de tentativas; o erro fica registrado e nunca é
//     `sent`.
//   * DUPLICIDADE: chave de deduplicação não cria segunda linha; reprocessar a
//     mesma linha não gera segundo envio; reivindicação concorrente envia uma
//     vez só; `retry` explícito de item `dead` reenvia com nova prova.
//
// Banco: PGlite com as MESMAS migrações do PostgreSQL (não um schema de
// conveniência), como o resto da suíte. Não usa servidor de e-mail externo,
// não usa credencial e não deixa processo vivo.

// 003 cria `auth_identities` e `auth_access_audit`; 011 amplia o CHECK de
// auditoria e cria a fila; 100 acrescenta o estado `local_outbox`, as colunas de
// reivindicação e as ações do L02. São as mesmas migrações que o runtime aplica.
const MIGRATIONS = [
  '003-client-access.sql',
  '011-audit-and-notifications.sql',
  '100-l02-local-outbox.sql',
];

async function openDatabase(t) {
  const pg = new PGlite();
  t.after(() => pg.close());
  for (const file of MIGRATIONS) {
    const sql = await readFile(new URL('../db/migrations/' + file, import.meta.url), 'utf8');
    await pg.exec(sql);
  }
  return pg;
}

function poolOf(pg) {
  return { query: (sql, params) => pg.query(sql, params) };
}

/** SMTP de captura mínimo (RFC 5321, só o necessário) em portas de loopback. */
async function startCaptureSmtp(t, { failWith = null, acceptAll = true } = {}) {
  const messages = [];
  const sockets = new Set();
  const server = createServer((socket) => {
    sockets.add(socket);
    socket.on('close', () => sockets.delete(socket));
    socket.on('error', () => {});
    socket.setTimeout(15_000);
    let buffer = '';
    let inData = false;
    let current = { rcpt: [], data: '' };
    const write = (line) => socket.write(line + '\r\n');
    write('220 captura.local ESMTP pronto');

    socket.on('data', (chunk) => {
      buffer += chunk.toString('utf8');
      for (;;) {
        if (inData) {
          const end = buffer.indexOf('\r\n.\r\n');
          if (end < 0) return;
          current.data = buffer.slice(0, end);
          buffer = buffer.slice(end + 5);
          inData = false;
          const rejected = !acceptAll ? current.rcpt : [];
          if (rejected.length > 0) {
            messages.push({ ...current, rejected });
            write('554 5.7.1 mensagem recusada pelo provedor de captura');
          } else {
            messages.push({ ...current, rejected: [] });
            write('250 2.0.0 Ok: aceito (captura local)');
          }
          current = { rcpt: [], data: '' };
          continue;
        }
        const index = buffer.indexOf('\r\n');
        if (index < 0) return;
        const line = buffer.slice(0, index);
        buffer = buffer.slice(index + 2);
        const upper = line.toUpperCase();
        if (upper.startsWith('EHLO') || upper.startsWith('HELO')) {
          write('250-captura.local');
          write('250-8BITMIME');
          write('250 OK');
        } else if (upper.startsWith('MAIL FROM')) {
          current.fromRaw = line;
          if (failWith) { write(failWith); } else { write('250 2.1.0 remetente ok'); }
        } else if (upper.startsWith('RCPT TO')) {
          current.rcpt.push(line.slice(line.indexOf(':') + 1).trim());
          write('250 2.1.5 destinatário ok');
        } else if (upper === 'DATA') {
          inData = true;
          write('354 envie os dados e finalize com .');
        } else if (upper === 'RSET') {
          current = { rcpt: [], data: '' };
          write('250 OK');
        } else if (upper === 'QUIT') {
          write('221 2.0.0 tchau');
          socket.end();
        } else if (upper.startsWith('NOOP')) {
          write('250 OK');
        } else {
          write('502 5.5.2 comando não implementado na captura');
        }
      }
    });
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const port = server.address().port;
  t.after(() => new Promise((resolve) => {
    for (const socket of sockets) socket.destroy();
    server.close(() => resolve());
  }));
  return { port, messages };
}

function captureTransportFactory(port) {
  // Usa o nodemailer real: o protocolo é falado de verdade; o destino é o
  // servidor de captura local. Nenhum host externo é resolvido.
  return (options) => nodemailer.createTransport({
    ...options,
    host: '127.0.0.1',
    port,
    secure: false,
    auth: undefined,
    tls: { rejectUnauthorized: false },
  });
}

/**
 * Decodifica quoted-printable do corpo recebido. O transporte real usa
 * `quoted-printable` para texto com acento; conferir o corpo no fio exige
 * decodificar, não afrouxar a asserção.
 */
function decodeQuotedPrintable(text) {
  // Só o corpo: os cabeçalhos usam encoded-word e quebrariam a decodificação.
  const separator = text.indexOf('\r\n\r\n');
  if (separator < 0) return text;
  const header = text.slice(0, separator);
  const body = text.slice(separator + 4);
  const bytes = Buffer.from(
    body.replace(/=\r\n/g, '').replace(/=([0-9A-F]{2})/gi, (_, hex) => String.fromCharCode(parseInt(hex, 16))),
    'latin1',
  );
  return `${header}\n\n${bytes.toString('utf8')}`;
}

function envFor(port) {
  return {
    MAIL_HOST: '127.0.0.1',
    MAIL_PORT: String(port),
    MAIL_SECURE: 'false',
    MAIL_FROM: 'avisos@gruposeg.example',
  };
}

async function enqueueEmail(pg, { email = 'operador@gruposeg.example', dedup = null, maxAttempts = 5 } = {}) {
  const queue = createNotificationQueue({ getPool: () => poolOf(pg) });
  return queue.enqueue({
    recipientKind: 'staff',
    recipientId: randomUUID(),
    recipientEmail: email,
    channel: 'email',
    template: 'teste_fatia_07',
    payload: { aviso: 'mensagem sintética de teste' },
    dedupKey: dedup,
    maxAttempts,
  });
}

test('fatia 07: configuração ausente, completa, parcial e inválida não inventam transporte', () => {
  const empty = readMailTransportConfig({});
  assert.equal(empty.state, MAILER_STATE.NOT_CONFIGURED, 'ambiente vazio precisa ser "não configurado", não erro');
  assert.equal(empty.config, null);

  const ready = readMailTransportConfig({
    MAIL_HOST: 'smtp.example.invalid',
    MAIL_PORT: '587',
    MAIL_SECURE: 'false',
    MAIL_USER: 'usuario',
    MAIL_PASSWORD: 'segredo-ficticio',
    MAIL_FROM: 'avisos@gruposeg.example',
  });
  assert.equal(ready.state, MAILER_STATE.READY);
  assert.equal(ready.config.port, 587);
  assert.equal(ready.config.secure, false);

  // Descrição pública não pode vazar senha nem usuário.
  const described = describeAdminMailerState({
    MAIL_HOST: 'smtp.example.invalid',
    MAIL_FROM: 'avisos@gruposeg.example',
    MAIL_USER: 'usuario',
    MAIL_PASSWORD: 'segredo-ficticio',
  });
  assert.equal(described.state, MAILER_STATE.READY);
  assert.equal(JSON.stringify(described).includes('segredo-ficticio'), false, 'a descrição não pode conter a senha');
  assert.equal(JSON.stringify(described).includes('usuario'), false, 'a descrição não pode conter o usuário');

  // Porta 465 força TLS implícito mesmo com MAIL_SECURE=false (mesma regra do lead).
  assert.equal(readMailTransportConfig({
    MAIL_HOST: 'smtp.example.invalid', MAIL_PORT: '465', MAIL_SECURE: 'false', MAIL_FROM: 'a@b.example',
  }).config.secure, true);

  // Metade da configuração é inválida, nunca "não configurado" silencioso.
  const hostOnly = readMailTransportConfig({ MAIL_HOST: 'smtp.example.invalid' });
  assert.equal(hostOnly.state, MAILER_STATE.INVALID);
  assert.ok(hostOnly.problems.includes('incomplete_mail_configuration'));

  const fromOnly = readMailTransportConfig({ MAIL_FROM: 'avisos@gruposeg.example' });
  assert.equal(fromOnly.state, MAILER_STATE.INVALID);

  const badPort = readMailTransportConfig({
    MAIL_HOST: 'smtp.example.invalid', MAIL_FROM: 'avisos@gruposeg.example', MAIL_PORT: 'abc',
  });
  assert.equal(badPort.state, MAILER_STATE.INVALID);
  assert.ok(badPort.problems.includes('invalid_mail_port'));

  const badSecure = readMailTransportConfig({
    MAIL_HOST: 'smtp.example.invalid', MAIL_FROM: 'avisos@gruposeg.example', MAIL_SECURE: 'talvez',
  });
  assert.equal(badSecure.state, MAILER_STATE.INVALID);
  assert.ok(badSecure.problems.includes('invalid_mail_secure'));

  const badFrom = readMailTransportConfig({
    MAIL_HOST: 'smtp.example.invalid', MAIL_FROM: 'nao-e-endereco',
  });
  assert.equal(badFrom.state, MAILER_STATE.INVALID);
  assert.ok(badFrom.problems.includes('invalid_mail_from'));

  const orphanPassword = readMailTransportConfig({
    MAIL_HOST: 'smtp.example.invalid', MAIL_FROM: 'avisos@gruposeg.example', MAIL_PASSWORD: 'so-senha',
  });
  assert.equal(orphanPassword.state, MAILER_STATE.INVALID);
  assert.ok(orphanPassword.problems.includes('orphan_mail_password'));

  const missingPassword = readMailTransportConfig({
    MAIL_HOST: 'smtp.example.invalid', MAIL_FROM: 'avisos@gruposeg.example', MAIL_USER: 'so-usuario',
  });
  assert.equal(missingPassword.state, MAILER_STATE.INVALID);
  assert.ok(missingPassword.problems.includes('missing_mail_password'));

  // Diagnóstico é só código: nenhum valor do ambiente aparece nele.
  for (const problem of [...hostOnly.problems, ...badPort.problems, ...badSecure.problems, ...badFrom.problems]) {
    assert.match(problem, /^[a-z_]+$/, `código de problema fora do padrão: ${problem}`);
  }
});

test('fatia 07: sem configuração, nenhum transporte é criado (fail-closed, comportamento vigente)', () => {
  const refused = [];
  const logger = { error: (...args) => refused.push(args) };
  assert.equal(createAdminMailTransport({ env: {}, logger }), null, 'ambiente vazio não pode criar transporte');
  assert.equal(createAdminMailTransport({
    env: { MAIL_HOST: 'smtp.example.invalid' }, logger,
  }), null, 'configuração parcial não pode criar transporte');
  assert.equal(refused.length, 1, 'configuração inválida precisa ser registrada para diagnóstico');
  assert.equal(JSON.stringify(refused).includes('smtp.example.invalid'), false, 'o diagnóstico não pode ecoar o host');
});

test('fatia 07: fila envia por SMTP real local, grava prova e não duplica', async (t) => {
  const pg = await openDatabase(t);
  const smtp = await startCaptureSmtp(t);
  const mailer = createAdminMailTransport({
    env: envFor(smtp.port),
    createTransport: captureTransportFactory(smtp.port),
  });
  assert.ok(mailer, 'com configuração válida o transporte precisa existir');

  const queue = createNotificationQueue({ getPool: () => poolOf(pg) });
  const enqueued = await enqueueEmail(pg, { dedup: 'teste-fatia-07-unico' });
  assert.equal(enqueued.dedup, false);

  // Duplicidade: mesma chave, nenhuma linha nova e nenhum segundo envio.
  const again = await enqueueEmail(pg, { dedup: 'teste-fatia-07-unico' });
  assert.equal(again.dedup, true);
  assert.equal(again.notification.id, enqueued.notification.id);
  assert.equal((await pg.query('SELECT count(*)::int AS n FROM notification_queue')).rows[0].n, 1);

  const processed = await queue.processNext({ batchSize: 10, mailer });
  assert.equal(processed.length, 1);
  assert.equal(processed[0].status, 'sent', `esperava envio confirmado, veio ${JSON.stringify(processed[0])}`);
  assert.equal(smtp.messages.length, 1, 'uma linha da fila precisa gerar exatamente uma mensagem');

  const message = smtp.messages[0];
  assert.equal(message.rcpt.length, 1);
  assert.match(message.rcpt[0], /<operador@gruposeg\.example>/);
  // Envelope não vazio: um `MAIL FROM:<>` seria remetente nulo, e o provedor
  // real recusaria — o `from` configurado tem de chegar ao fio.
  assert.doesNotMatch(message.fromRaw, /MAIL FROM:<>/i);
  assert.match(message.fromRaw, /<avisos@gruposeg\.example>/i);
  assert.match(message.data, /^From: avisos@gruposeg\.example$/im);
  assert.match(message.data, /^To: operador@gruposeg\.example$/im);
  // Assunto com template: o nodemailer codifica cabeçalho não-ASCII, então a
  // conferência aceita a forma literal ou a codificação MIME equivalente.
  assert.match(
    message.data,
    /^Subject: (\[teste_fatia_07\] Notifica|=\?UTF-8\?Q\?=5Bteste=5Ffatia=5F07=5D_Notifica)/im,
  );
  assert.match(message.data, /^Message-ID: /im, 'o provedor precisa devolver identificador da mensagem');
  assert.match(message.data, /^X-Seg-Notification-Id: /im);
  assert.ok(message.data.includes(enqueued.notification.id), 'o cabeçalho de rastro precisa citar o id da fila');

  const body = decodeQuotedPrintable(message.data);
  assert.match(body, /mensagem sintética de teste/);
  assert.match(body, /Notificação teste_fatia_07/);

  const row = (await pg.query('SELECT status, attempts, sent_at, last_error FROM notification_queue WHERE id = $1', [enqueued.notification.id])).rows[0];
  assert.equal(row.status, 'sent');
  assert.equal(row.attempts, 1);
  assert.ok(row.sent_at, 'envio confirmado precisa registrar o instante');
  assert.equal(row.last_error, null);

  // Reprocessar não reenvia: a linha já saiu de queued/failed.
  const reprocessed = await queue.processNext({ batchSize: 10, mailer });
  assert.equal(reprocessed.length, 0);
  assert.equal(smtp.messages.length, 1, 'reprocessar não pode gerar segundo e-mail');

  const audit = (await pg.query("SELECT action, result FROM auth_access_audit WHERE target = $1 ORDER BY action", [enqueued.notification.id])).rows;
  assert.deepEqual(audit.map((entry) => entry.action), ['notification_enqueue', 'notification_send']);
  assert.ok(audit.every((entry) => entry.result === 'allowed'));
});

test('fatia 07: falha do provedor vira failed com last_error, respeita backoff e não perde a mensagem', async (t) => {
  const pg = await openDatabase(t);
  // Servidor que recusa o remetente: falha real de protocolo, não mock.
  const smtp = await startCaptureSmtp(t, { failWith: '451 4.3.0 falha temporária simulada' });
  const mailer = createAdminMailTransport({
    env: envFor(smtp.port),
    createTransport: captureTransportFactory(smtp.port),
  });

  const queue = createNotificationQueue({ getPool: () => poolOf(pg) });
  const enqueued = await enqueueEmail(pg, { maxAttempts: 3 });

  const first = await queue.processNext({ batchSize: 5, mailer });
  assert.equal(first.length, 1);
  assert.equal(first[0].status, 'failed', `falha do provedor não pode ser "sent": ${JSON.stringify(first[0])}`);
  assert.ok(first[0].nextAttemptInMs >= 60_000, 'falha precisa respeitar o backoff da fila');

  const afterFirst = (await pg.query('SELECT status, attempts, last_error, sent_at FROM notification_queue WHERE id = $1', [enqueued.notification.id])).rows[0];
  assert.equal(afterFirst.status, 'failed');
  assert.equal(afterFirst.attempts, 1);
  assert.equal(afterFirst.sent_at, null, 'falha não pode gravar instante de envio');
  assert.match(afterFirst.last_error, /451|falha|remetente/i, `last_error precisa contar o que aconteceu: ${afterFirst.last_error}`);

  // Backoff impede nova tentativa imediata.
  assert.equal((await queue.processNext({ batchSize: 5, mailer })).length, 0, 'a fila não pode reenviar antes do backoff');
  assert.equal(smtp.messages.length, 0, 'mensagem recusada no envelope não pode contar como entregue');

  // Nova conexão, agora aceitando: o retry explícito entrega.
  const okSmtp = await startCaptureSmtp(t);
  const okMailer = createAdminMailTransport({
    env: envFor(okSmtp.port),
    createTransport: captureTransportFactory(okSmtp.port),
  });
  await queue.retry(enqueued.notification.id, { actorKind: 'ti' });
  const retried = await queue.processNext({ batchSize: 5, mailer: okMailer });
  assert.equal(retried[0].status, 'sent');
  assert.equal(okSmtp.messages.length, 1);
  assert.equal((await pg.query('SELECT attempts FROM notification_queue WHERE id = $1', [enqueued.notification.id])).rows[0].attempts, 2);
});

test('fatia 07: falha repetida encerra como dead após max_attempts, sem nunca declarar envio', async (t) => {
  const pg = await openDatabase(t);
  // Remetente recusado em todas as tentativas.
  const smtp = await startCaptureSmtp(t, { failWith: '550 5.7.1 remetente recusado (teste)' });
  const mailer = createAdminMailTransport({
    env: envFor(smtp.port),
    createTransport: captureTransportFactory(smtp.port),
  });
  const queue = createNotificationQueue({ getPool: () => poolOf(pg) });
  const enqueued = await enqueueEmail(pg, { maxAttempts: 2 });

  const first = await queue.processNext({ batchSize: 5, mailer });
  assert.equal(first[0].status, 'failed');
  // Vence o backoff explicitamente, como faria o relógio do servidor.
  await pg.query("UPDATE notification_queue SET next_attempt_at = NOW() - INTERVAL '1 second' WHERE id = $1", [enqueued.notification.id]);
  const second = await queue.processNext({ batchSize: 5, mailer });
  assert.equal(second[0].status, 'dead', `ao atingir max_attempts o estado precisa ser dead: ${JSON.stringify(second[0])}`);

  const row = (await pg.query('SELECT status, attempts, sent_at, last_error FROM notification_queue WHERE id = $1', [enqueued.notification.id])).rows[0];
  assert.equal(row.status, 'dead');
  assert.equal(row.attempts, 2);
  assert.equal(row.sent_at, null);
  assert.ok(row.last_error && row.last_error.length > 0, 'item dead precisa manter o motivo');

  const audit = (await pg.query("SELECT action FROM auth_access_audit WHERE target = $1 ORDER BY created_at", [enqueued.notification.id])).rows.map((entry) => entry.action);
  assert.deepEqual(audit, ['notification_enqueue', 'notification_failed', 'notification_dead']);
});

test('fatia 07: dois consumidores concorrentes enviam a mesma linha uma única vez', async (t) => {
  const pg = await openDatabase(t);
  const smtp = await startCaptureSmtp(t);
  const mailer = createAdminMailTransport({
    env: envFor(smtp.port),
    createTransport: captureTransportFactory(smtp.port),
  });
  const queue = createNotificationQueue({ getPool: () => poolOf(pg) });
  await enqueueEmail(pg, { dedup: 'teste-fatia-07-concorrencia' });

  // Duas chamadas simultâneas contra o mesmo banco: a reivindicação atômica
  // decide o vencedor; a outra não pode enviar.
  const [a, b] = await Promise.all([
    queue.processNext({ batchSize: 5, mailer }),
    queue.processNext({ batchSize: 5, mailer }),
  ]);
  const sent = [...a, ...b].filter((entry) => entry.status === 'sent');
  assert.equal(sent.length, 1, `exatamente um envio confirmado: ${JSON.stringify([a, b])}`);
  assert.equal(smtp.messages.length, 1, 'concorrência não pode gerar dois e-mails');
});

test('fatia 07: o caminho `mailer.sendMail` da fila também preserva o remetente', async (t) => {
  const pg = await openDatabase(t);
  const smtp = await startCaptureSmtp(t);
  const mailer = createAdminMailTransport({
    env: envFor(smtp.port),
    createTransport: captureTransportFactory(smtp.port),
  });
  const queue = createNotificationQueue({ getPool: () => poolOf(pg) });
  await enqueueEmail(pg, { dedup: 'teste-fatia-07-sendmail' });

  // Força o ramo `typeof mailer === "object"` da fila: comportamento vigente
  // que não pode regredir só porque o transporte real foi ligado.
  const objectTransport = { sendMail: (options) => mailer.sendMail(options) };
  const processed = await queue.processNext({ batchSize: 5, mailer: objectTransport });
  assert.equal(processed[0].status, 'sent');
  assert.equal(smtp.messages.length, 1);
  assert.match(smtp.messages[0].fromRaw, /<avisos@gruposeg\.example>/i, 'sendMail sem from explícito precisa usar o remetente configurado');
});

test('fatia 07: destinatário inválido e provedor sem prova de aceite não viram "sent"', async (t) => {
  const pg = await openDatabase(t);
  const smtp = await startCaptureSmtp(t);
  const mailer = createAdminMailTransport({
    env: envFor(smtp.port),
    createTransport: captureTransportFactory(smtp.port),
  });

  // Destinatário recusado pelo protocolo não pode retornar "sent".
  await assert.rejects(
    () => mailer.sendNotification({ id: randomUUID(), recipient_email: 'nao-e-endereco', template: 't', payload: {} }),
    /invalid_recipient_email_for_delivery/,
  );

  // Provedor que aceita a mensagem mas não devolve prova: a fila não pode
  // declarar envio a partir de um resultado vazio.
  const noEvidence = createAdminMailTransport({
    env: envFor(smtp.port),
    createTransport: () => ({ sendMail: async () => ({}) }),
  });
  await assert.rejects(
    () => noEvidence.sendNotification({ id: randomUUID(), recipient_email: 'operador@gruposeg.example', template: 't', payload: {} }),
    /sendmail_without_acceptance_evidence|recipient_not_accepted/,
  );

  // Provedor que recusa o destinatário explicitamente.
  const rejected = createAdminMailTransport({
    env: envFor(smtp.port),
    createTransport: () => ({ sendMail: async () => ({ accepted: [], rejected: ['operador@gruposeg.example'] }) }),
  });
  await assert.rejects(
    () => rejected.sendNotification({ id: randomUUID(), recipient_email: 'operador@gruposeg.example', template: 't', payload: {} }),
    /recipient_not_accepted/,
  );

  // E o caminho de sucesso continua devolvendo exatamente "sent".
  const result = await mailer.sendNotification({
    id: randomUUID(),
    recipient_email: 'operador@gruposeg.example',
    template: 'teste_fatia_07',
    payload: { ok: true },
  });
  assert.equal(result, 'sent');
  assert.equal(pg !== null, true, 'o banco de apoio permanece aberto durante as recusas');
});

test('fatia 07: sem SMTP configurado a fila mantém a caixa local, nunca "sent"', async (t) => {
  const pg = await openDatabase(t);
  const deliveries = [];
  const localOutbox = {
    deliver: async (message) => {
      deliveries.push(message);
      return { id: randomUUID(), label: 'disponível na caixa local (sem SMTP; não houve envio)' };
    },
  };
  const queue = createNotificationQueue({ getPool: () => poolOf(pg), localOutbox });
  const enqueued = await enqueueEmail(pg);

  // O servidor passa `mailer: null` quando não há configuração válida.
  const processed = await queue.processNext({ batchSize: 5, mailer: createAdminMailTransport({ env: {} }) });
  assert.equal(processed[0].status, 'local_outbox', 'sem SMTP o comportamento vigente precisa ser preservado');
  assert.equal(deliveries.length, 1);
  assert.equal(deliveries[0].recipientAddress, 'operador@gruposeg.example');

  const row = (await pg.query('SELECT status, sent_at FROM notification_queue WHERE id = $1', [enqueued.notification.id])).rows[0];
  assert.equal(row.status, 'local_outbox');
  assert.equal(row.sent_at, null, 'caixa local nunca registra instante de envio');

  // E a configuração inválida também cai no caminho vigente, nunca em envio.
  const invalid = createAdminMailTransport({ env: { MAIL_HOST: 'smtp.example.invalid' }, logger: { error() {} } });
  assert.equal(invalid, null);
});
