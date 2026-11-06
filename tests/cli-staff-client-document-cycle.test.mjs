import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID, createHash } from 'node:crypto';
import { mkdtemp, rm, writeFile, readFile, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

import { createClientSpaceApi } from '../src/server/client-space-api.mjs';

// Fatia 09 — ciclo staff → cliente, ponta a ponta, no caminho que já existe.
//
// O plano pede: exercitar criar/revisar/aprovar/publicar/ler/revogar nos
// recursos CLI-05…CLI-08 e corrigir lacunas demonstradas no contrato vigente,
// **sem** declarar aceite humano.
//
// O recurso exercitado aqui é o documento do cliente, porque é o único que tem
// as pontas nas duas mãos: a equipe (sessão administrativa) cria, e o cliente
// (sessão de cliente) lê. Nenhuma regra foi criada: o teste percorre as que
// existem e verifica o efeito no banco e no disco.
//
//   staff cria      → 201, bytes gravados, hash conferido, auditoria allowed
//   staff repete    → 200 `replayed`, sem segunda linha e sem segundo arquivo
//   staff conflita  → 409 quando a mesma chave muda o conteúdo
//   cliente lê      → 200 com os MESMOS bytes que a equipe gravou
//   cliente indevido→ 403 (outra conta) / 401 (sem sessão)
//   staff revoga    → 200; o cliente perde o acesso imediatamente
//   staff remove?   → não existe remoção: o contrato não apaga documento
//
// O que NÃO é provado: interface (nenhum navegador neste ambiente), aceite
// humano, operação em produção e PostgreSQL real (PGlite aplica as mesmas
// migrações, mas serializa as consultas).

// ---------------------------------------------------------------------------
// Banco: cadeia real de migrações. A 139 é a última que este caminho usa
// (índice único de idempotência por uploader).
// ---------------------------------------------------------------------------
let schemaBase;
async function schemaCompartilhado() {
  if (schemaBase) return schemaBase;
  const { PGlite } = await import('@electric-sql/pglite');
  const pg = new PGlite();
  await pg.exec("CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $t$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $t$ LANGUAGE plpgsql;");
  const dir = new URL('../db/migrations/', import.meta.url);
  for (const arquivo of (await readdir(dir)).filter((f) => f.endsWith('.sql')).sort()) {
    if (Number(arquivo.slice(0, 3)) > 139) break;
    await pg.exec(await readFile(new URL(arquivo, dir), 'utf8'));
  }
  schemaBase = await pg.dumpDataDir('none');
  await pg.close();
  return schemaBase;
}

async function openDb(t) {
  const { PGlite } = await import('@electric-sql/pglite');
  const pg = new PGlite({ loadDataDir: await schemaCompartilhado() });
  t.after(() => pg.close());
  return pg;
}

async function identidade(pg, kind = 'client') {
  const id = randomUUID();
  await pg.query(
    "INSERT INTO auth_identities(id,kind,email,status,verified_at,verification_method) VALUES ($1,$2,$3,'active',NOW(),'manual')",
    [id, kind, `${id.slice(0, 8)}@teste.invalid`],
  );
  return id;
}

function resposta() {
  return {
    status: 0, headers: {}, corpo: null, bytes: null,
    writeHead(status, headers) { this.status = status; this.headers = headers; },
    end(chunk) {
      if (Buffer.isBuffer(chunk)) this.bytes = chunk;
      else this.corpo = chunk === undefined ? undefined : JSON.parse(String(chunk));
    },
  };
}

const json = (alvo, status, corpo, headers = {}) => {
  if (alvo.status) throw new Error('resposta duplicada');
  alvo.status = status;
  alvo.corpo = corpo;
  alvo.headers = headers;
  return corpo;
};

/** Ponto de entrada único do cenário: staff `ti` + cliente + conta + disco. */
async function cenario(t) {
  const pg = await openDb(t);
  const staffId = await identidade(pg, 'staff');
  const clienteId = await identidade(pg, 'client');
  const conta = randomUUID();
  const outraConta = randomUUID();
  await pg.query(
    "INSERT INTO client_accounts(id,status,display_name,created_by) VALUES ($1,'active','Conta Sintética','ti'),($2,'active','Outra Conta','ti')",
    [conta, outraConta],
  );
  const disco = await mkdtemp(path.join(tmpdir(), 'seg-fatia09-'));
  t.after(() => rm(disco, { recursive: true, force: true }));

  const auditoria = [];
  const base = { query: (sql, params) => pg.query(sql, params) };
  const pool = {
    query: async (sql, params) => {
      const r = await base.query(sql, params);
      if (sql.includes('auth_access_audit')) auditoria.push({ sql, params });
      return r;
    },
    connect: async () => {
      const c = {
        query: async (sql, params) => {
          const r = await base.query(sql, params);
          if (sql.includes('auth_access_audit')) auditoria.push({ sql, params });
          return r;
        },
        release() {},
      };
      return c;
    },
  };

  let sessaoAdmin = { role: 'ti', identityId: staffId };
  let sessaoCliente = { identityId: clienteId };
  const api = createClientSpaceApi({
    getPool: () => pool,
    docsDir: disco,
    readAdminSession: async () => sessaoAdmin,
    readClientSession: async () => sessaoCliente,
    sameOrigin: () => true,
    readJson: async (req) => JSON.parse(req.corpoJson || '{}'),
    json,
  });

  return {
    pg, api, disco, auditoria, conta, outraConta, staffId, clienteId,
    setAdmin: (s) => { sessaoAdmin = s; },
    setCliente: (s) => { sessaoCliente = s; },
  };
}

function reqJson(method, corpo, headers = {}) {
  return {
    method,
    headers: { host: 'sistema.local', origin: 'http://sistema.local', ...headers },
    corpoJson: JSON.stringify(corpo),
    url: 'http://sistema.local/api/admin/client-documents',
  };
}

async function upload(ctx, corpo, headers = { 'idempotency-key': 'chave-unica-0001' }) {
  const res = resposta();
  await ctx.api.handleAdminDocuments(reqJson('POST', corpo, headers), res, new URL('http://sistema.local/x'));
  return res;
}

async function baixarComoCliente(ctx, documento) {
  const res = resposta();
  await ctx.api.handleClientDocumentDownload(
    { method: 'GET', headers: {}, url: `http://sistema.local/api/client/documents/${documento}/download` },
    res, documento,
  );
  return res;
}

const CONTEUDO = Buffer.from('CONTRATO ASSINADO - CONTEUDO SINTETICO DE TESTE', 'utf8');
// `filename` (não `originalFilename`) e sem `contentType`: o servidor deriva o
// tipo permitido da extensão, e é ele quem manda no registro.
const corpoDeUpload = (ctx, extra = {}) => ({
  accountId: ctx.conta,
  title: 'Contrato assinado',
  category: 'contrato',
  filename: 'contrato-assinado.txt',
  contentBase64: CONTEUDO.toString('base64'),
  ...extra,
});

/** Arquivos realmente gravados no diretório privado. */
const arquivosNoDisco = async (dir) => (await readdir(dir)).filter((f) => !f.startsWith('.'));

// ---------------------------------------------------------------------------
// Criação pela equipe
// ---------------------------------------------------------------------------

test('09/A: staff cria o documento; bytes, hash e auditoria conferem no banco e no disco', async (t) => {
  const ctx = await cenario(t);
  const res = await upload(ctx, corpoDeUpload(ctx));

  assert.equal(res.status, 201, JSON.stringify(res.corpo));
  assert.equal(res.corpo.replayed, false);
  assert.equal(res.corpo.contentSha256, createHash('sha256').update(CONTEUDO).digest('hex'));

  const { rows } = await ctx.pg.query('SELECT * FROM client_documents WHERE id=$1', [res.corpo.documentId]);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].client_account_id, ctx.conta);
  assert.equal(rows[0].uploaded_by, 'ti', 'o papel fica registrado');
  assert.equal(rows[0].uploaded_by_identity, ctx.staffId, 'a identidade individual também');
  assert.equal(Number(rows[0].size_bytes), CONTEUDO.length);
  assert.match(rows[0].storage_key, /^[0-9a-f]{48}$/);

  const gravado = await readFile(path.join(ctx.disco, rows[0].storage_key));
  assert.deepEqual(gravado, CONTEUDO, 'o que está no disco é exatamente o enviado');
  assert.equal(createHash('sha256').update(gravado).digest('hex'), rows[0].content_sha256);

  assert.ok(ctx.auditoria.some((a) => a.params.includes('document_upload') && a.params.includes('allowed')),
    'upload precisa gerar auditoria allowed');
});

test('09/A: a mesma chave de idempotência não cria segundo documento nem segundo arquivo', async (t) => {
  const ctx = await cenario(t);
  const primeiro = await upload(ctx, corpoDeUpload(ctx));
  const arquivosAntes = await arquivosNoDisco(ctx.disco);
  const segundo = await upload(ctx, corpoDeUpload(ctx));

  assert.equal(primeiro.status, 201);
  assert.equal(segundo.status, 200);
  assert.equal(segundo.corpo.replayed, true);
  assert.equal(segundo.corpo.documentId, primeiro.corpo.documentId, 'devolve o mesmo documento');

  const { rows } = await ctx.pg.query('SELECT id FROM client_documents');
  assert.equal(rows.length, 1, 'uma linha só');
  assert.deepEqual(await arquivosNoDisco(ctx.disco), arquivosAntes, 'nenhum arquivo órfão no disco');
});

test('09/B: mesma chave com conteúdo diferente é conflito, não sobrescrita', async (t) => {
  const ctx = await cenario(t);
  await upload(ctx, corpoDeUpload(ctx));
  const conflito = await upload(ctx, corpoDeUpload(ctx, {
    contentBase64: Buffer.from('OUTRO CONTEUDO COMPLETAMENTE DIFERENTE AQUI', 'utf8').toString('base64'),
  }));

  assert.equal(conflito.status, 409);
  assert.equal(conflito.corpo.error, 'idempotency_conflict');
  const { rows } = await ctx.pg.query('SELECT content_sha256 FROM client_documents');
  assert.equal(rows.length, 1);
  assert.equal(rows[0].content_sha256, createHash('sha256').update(CONTEUDO).digest('hex'),
    'o conteúdo gravado continua sendo o primeiro');
});

test('09/B: chave de idempotência ausente ou inválida recusa antes de gravar', async (t) => {
  const ctx = await cenario(t);
  const semChave = await upload(ctx, corpoDeUpload(ctx), {});
  assert.equal(semChave.status, 400);
  assert.equal(semChave.corpo.error, 'idempotency_key_required_or_invalid');

  const curta = await upload(ctx, corpoDeUpload(ctx), { 'idempotency-key': 'curta' });
  assert.equal(curta.status, 400);

  const { rows } = await ctx.pg.query('SELECT id FROM client_documents');
  assert.equal(rows.length, 0);
  assert.deepEqual(await arquivosNoDisco(ctx.disco), [], 'nada é gravado quando a chave falta');
});

test('09/B: conta inexistente e papel sem permissão não criam documento', async (t) => {
  const ctx = await cenario(t);
  const inexistente = await upload(ctx, corpoDeUpload(ctx, { accountId: randomUUID() }));
  assert.equal(inexistente.status, 404);
  assert.equal(inexistente.corpo.error, 'account_not_found');

  // Papel `rh` não administra o espaço do cliente (só `marcelo`/`ti`).
  ctx.setAdmin({ role: 'rh', identityId: ctx.staffId });
  const rh = await upload(ctx, corpoDeUpload(ctx, { accountId: ctx.conta }), { 'idempotency-key': 'chave-rh-0000001' });
  assert.equal(rh.status, 403);
  assert.equal(rh.corpo.error, 'forbidden');

  // Sessão administrativa ausente: 401 e nada gravado.
  ctx.setAdmin(null);
  const anonimo = await upload(ctx, corpoDeUpload(ctx), { 'idempotency-key': 'chave-anon-000001' });
  assert.equal(anonimo.status, 401);
  assert.equal(anonimo.corpo.error, 'admin_session_required');

  const { rows } = await ctx.pg.query('SELECT id FROM client_documents');
  assert.equal(rows.length, 0);
  assert.deepEqual(await arquivosNoDisco(ctx.disco), []);
});

// ---------------------------------------------------------------------------
// Leitura pelo cliente
// ---------------------------------------------------------------------------

test('09/A: a equipe grava e o cliente vinculado lê os MESMOS bytes', async (t) => {
  const ctx = await cenario(t);
  const criado = await upload(ctx, corpoDeUpload(ctx));
  const grant = await ctx.pg.query(
    "INSERT INTO client_access_grants(id,identity_id,client_account_id,reason,granted_by) VALUES ($1,$2,$3,'concessão sintética de teste','ti') RETURNING id",
    [randomUUID(), ctx.clienteId, ctx.conta],
  );

  const res = await baixarComoCliente(ctx, criado.corpo.documentId);
  assert.equal(res.status, 200, JSON.stringify(res.corpo));
  assert.deepEqual(res.bytes, CONTEUDO, 'o cliente recebe exatamente o que a equipe gravou');
  assert.equal(res.headers['Cache-Control'], 'private, no-store');
  assert.equal(res.headers['X-Content-Type-Options'], 'nosniff');
  assert.ok(ctx.auditoria.some((a) => a.params.includes('document_download') && a.params.includes('allowed')),
    'leitura do cliente também é auditada');

  void grant;
});

test('09/B: cliente de outra conta não lê o documento da equipe', async (t) => {
  const ctx = await cenario(t);
  const criado = await upload(ctx, corpoDeUpload(ctx));
  await ctx.pg.query(
    "INSERT INTO client_access_grants(id,identity_id,client_account_id,reason,granted_by) VALUES ($1,$2,$3,'concessão sintética de teste','ti')",
    [randomUUID(), ctx.clienteId, ctx.outraConta],
  );

  const res = await baixarComoCliente(ctx, criado.corpo.documentId);
  assert.equal(res.status, 403);
  assert.equal(res.bytes, null, 'negação não entrega byte');
});

// ---------------------------------------------------------------------------
// Revogação: o ciclo fecha
// ---------------------------------------------------------------------------

test('09/A/B: revogar o vínculo corta o acesso imediatamente, sem apagar o documento', async (t) => {
  const ctx = await cenario(t);
  const criado = await upload(ctx, corpoDeUpload(ctx));
  const { rows: [grant] } = await ctx.pg.query(
    "INSERT INTO client_access_grants(id,identity_id,client_account_id,reason,granted_by) VALUES ($1,$2,$3,'concessão sintética de teste','ti') RETURNING id",
    [randomUUID(), ctx.clienteId, ctx.conta],
  );

  const antes = await baixarComoCliente(ctx, criado.corpo.documentId);
  assert.equal(antes.status, 200, 'antes da revogação o cliente lê');

  const resRevoga = resposta();
  await ctx.api.handleAdminGrantRevoke(
    { method: 'DELETE', headers: { host: 'sistema.local', origin: 'http://sistema.local' }, corpoJson: JSON.stringify({ reason: 'Fim do contrato de teste' }) },
    resRevoga, grant.id,
  );
  assert.equal(resRevoga.status, 200, JSON.stringify(resRevoga.corpo));
  assert.equal(resRevoga.corpo.outcome, 'revoked');

  const depois = await baixarComoCliente(ctx, criado.corpo.documentId);
  assert.equal(depois.status, 403, 'revogar vence a sessão do cliente');
  assert.equal(depois.bytes, null);

  // O documento continua existindo: revogar acesso não apaga prova.
  const { rows } = await ctx.pg.query('SELECT id FROM client_documents WHERE id=$1', [criado.corpo.documentId]);
  assert.equal(rows.length, 1, 'o contrato não apaga o documento ao revogar o vínculo');
  assert.ok(ctx.auditoria.some((a) => a.params.includes('grant_revoke') && a.params.includes('allowed')));
});

test('09/B: revogar duas vezes é idempotente e não duplica auditoria permitida', async (t) => {
  const ctx = await cenario(t);
  const { rows: [grant] } = await ctx.pg.query(
    "INSERT INTO client_access_grants(id,identity_id,client_account_id,reason,granted_by) VALUES ($1,$2,$3,'concessão sintética de teste','ti') RETURNING id",
    [randomUUID(), ctx.clienteId, ctx.conta],
  );
  const corpo = { method: 'DELETE', headers: { host: 'sistema.local', origin: 'http://sistema.local' }, corpoJson: JSON.stringify({ reason: 'Encerramento do teste' }) };

  const primeira = resposta();
  await ctx.api.handleAdminGrantRevoke(corpo, primeira, grant.id);
  const segunda = resposta();
  await ctx.api.handleAdminGrantRevoke(corpo, segunda, grant.id);

  assert.equal(primeira.corpo.outcome, 'revoked');
  assert.equal(segunda.corpo.outcome, 'already_revoked');
  const permitidas = ctx.auditoria.filter((a) => a.params.includes('grant_revoke') && a.params.includes('allowed'));
  assert.equal(permitidas.length, 1, 'a segunda revogação não inventa um segundo evento permitido');
});

test('09/B: revogação exige motivo e sessão administrativa', async (t) => {
  const ctx = await cenario(t);
  const { rows: [grant] } = await ctx.pg.query(
    "INSERT INTO client_access_grants(id,identity_id,client_account_id,reason,granted_by) VALUES ($1,$2,$3,'concessão sintética de teste','ti') RETURNING id",
    [randomUUID(), ctx.clienteId, ctx.conta],
  );

  const semMotivo = resposta();
  await ctx.api.handleAdminGrantRevoke(
    { method: 'DELETE', headers: { host: 'sistema.local', origin: 'http://sistema.local' }, corpoJson: '{}' },
    semMotivo, grant.id,
  );
  assert.equal(semMotivo.status, 400, 'motivo é obrigatório');

  ctx.setAdmin(null);
  const anonimo = resposta();
  await ctx.api.handleAdminGrantRevoke(
    { method: 'DELETE', headers: { host: 'sistema.local', origin: 'http://sistema.local' }, corpoJson: JSON.stringify({ reason: 'Sem sessão' }) },
    anonimo, grant.id,
  );
  assert.equal(anonimo.status, 401);

  const { rows } = await ctx.pg.query('SELECT revoked_at FROM client_access_grants WHERE id=$1', [grant.id]);
  assert.equal(rows[0].revoked_at, null, 'nenhuma das recusas pode revogar');
});

// ---------------------------------------------------------------------------
// Limite do contrato: não existe remoção de documento
// ---------------------------------------------------------------------------

test('09: o contrato administrativo de documentos não expõe remoção (só GET e POST)', async (t) => {
  const ctx = await cenario(t);
  const criado = await upload(ctx, corpoDeUpload(ctx));

  for (const metodo of ['DELETE', 'PUT', 'PATCH']) {
    const res = resposta();
    await ctx.api.handleAdminDocuments(
      reqJson(metodo, {}, { 'idempotency-key': 'chave-remocao-001' }), res,
      new URL(`http://sistema.local/api/admin/client-documents/${criado.corpo.documentId}`),
    );
    assert.equal(res.status, 405, `${metodo} precisa ser recusado`);
    assert.equal(res.headers.Allow, 'GET, POST');
  }

  const { rows } = await ctx.pg.query('SELECT id FROM client_documents WHERE id=$1', [criado.corpo.documentId]);
  assert.equal(rows.length, 1, 'nenhuma tentativa de remoção pode apagar o documento');
  assert.equal((await arquivosNoDisco(ctx.disco)).length, 1);
});

// ---------------------------------------------------------------------------
// Listagem administrativa
// ---------------------------------------------------------------------------

test('09/A/B: a listagem administrativa mostra o documento na conta certa e respeita papel', async (t) => {
  const ctx = await cenario(t);
  const criado = await upload(ctx, corpoDeUpload(ctx));

  const res = resposta();
  await ctx.api.handleAdminDocuments(
    { method: 'GET', headers: {}, url: `http://sistema.local/api/admin/client-documents?account=${ctx.conta}` },
    res, new URL(`http://sistema.local/api/admin/client-documents?account=${ctx.conta}`),
  );
  assert.equal(res.status, 200, JSON.stringify(res.corpo));
  assert.deepEqual(res.corpo.documents.map((d) => d.id), [criado.corpo.documentId]);

  const vazia = resposta();
  await ctx.api.handleAdminDocuments(
    { method: 'GET', headers: {}, url: `http://sistema.local/api/admin/client-documents?account=${ctx.outraConta}` },
    vazia, new URL(`http://sistema.local/api/admin/client-documents?account=${ctx.outraConta}`),
  );
  assert.deepEqual(vazia.corpo.documents, [], 'a conta sem documento não lista o da outra');

  ctx.setAdmin({ role: 'rh', identityId: ctx.staffId });
  const rh = resposta();
  await ctx.api.handleAdminDocuments(
    { method: 'GET', headers: {}, url: `http://sistema.local/api/admin/client-documents?account=${ctx.conta}` },
    rh, new URL(`http://sistema.local/api/admin/client-documents?account=${ctx.conta}`),
  );
  assert.equal(rh.status, 403, 'RH não enxerga o espaço do cliente');
});

// ---------------------------------------------------------------------------
// Falha no meio da gravação
// ---------------------------------------------------------------------------

test('09: falha ao gravar a linha não deixa arquivo órfão no diretório privado', async (t) => {
  const ctx = await cenario(t);
  // Força a falha no INSERT depois de o arquivo já ter sido gravado: é o
  // caminho em que um rollback sem limpeza deixaria lixo privado no disco.
  await ctx.pg.query('ALTER TABLE client_documents ADD CONSTRAINT teste_falha_documento CHECK (title <> \'Forcar Falha\')');

  const res = await upload(ctx, corpoDeUpload(ctx, { title: 'Forcar Falha' }), { 'idempotency-key': 'chave-falha-00001' });
  assert.equal(res.status, 503, 'falha de banco não vira 201');

  const { rows } = await ctx.pg.query('SELECT id FROM client_documents');
  assert.equal(rows.length, 0);
  assert.deepEqual(await arquivosNoDisco(ctx.disco), [], 'o arquivo gravado antes do INSERT precisa ser removido');
});
