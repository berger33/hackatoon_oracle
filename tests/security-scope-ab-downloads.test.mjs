import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID, createHash } from 'node:crypto';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

import { createClientSpaceApi } from '../src/server/client-space-api.mjs';
import { createClientAccessApi, CLIENT_SESSION_COOKIE } from '../src/server/client-access-api.mjs';
import { createEmployeeApi } from '../src/server/employee-api.mjs';

// Fatia 08 — escopos de download: conta (A/B) e funcionário (próprio × RH).
//
// O plano pede "ampliar negativos A/B, sessões revogadas, 401/403,
// conta/unidade/contrato" **sem inventar nova matriz CLI-02** e sem alterar a
// regra vigente. Este arquivo exercita as regras que já existem, com banco
// real (PGlite com as migrações do repositório) e bytes reais em disco
// temporário:
//
//   A (autorizado) — cliente com vínculo ativo baixa o documento da própria conta.
//   B (indevido)   — mesmo cliente, outra conta: **403** e nenhum byte servido.
//   B (indevido)   — sem sessão: 401 antes de qualquer leitura de banco útil.
//   B (indevido)   — vínculo revogado: 403.
//   B (indevido)   — conta inativa: 403 (o vínculo sozinho não basta).
//   Funcionário    — baixa o próprio documento; não baixa o de outro (404).
//   RH             — sem concessão sobre o funcionário: 403, sem bytes.
//   Integridade    — arquivo adulterado: 409, sem bytes, com auditoria de negação.
//   Auditoria      — negativa é registrada; falha de auditoria não libera bytes.
//
// O que este arquivo NÃO prova: operação real, produção, conta de terceiros
// real ou que a matriz de permissões aprovada (CLI-02) esteja correta — a
// matriz de negócio continua sendo decisão do proprietário.

// Schema: a cadeia real de migrações do repositório (001..102), a mesma que o
// runtime aplica — não um schema de conveniência. Assim o teste também cobre os
// CHECKs de verdade (ação de auditoria, categoria de detalhe, formato de
// storage key, tamanho) em vez de uma cópia mais permissiva.
//
// `001`..`102` é o recorte necessário: 057 cria `hr_employees`, 101 acrescenta
// `content_sha256` em `client_documents` e 102 cria os documentos privados do
// funcionário. Nada depois disso é lido por estes caminhos.

/** Aplica a cadeia real de migrações até o número indicado. */
async function migrate(pg, ate) {
  const { readdir, readFile } = await import('node:fs/promises');
  const dir = new URL('../db/migrations/', import.meta.url);
  const arquivos = (await readdir(dir)).filter((f) => f.endsWith('.sql')).sort();
  for (const arquivo of arquivos) {
    if (Number(arquivo.slice(0, 3)) > ate) break;
    await pg.exec(await readFile(new URL(arquivo, dir), 'utf8'));
  }
}

/**
 * Banco-base: a cadeia real até a última migração usada aqui. O schema é
 * construído uma vez e clonado por teste (cada teste recebe um banco próprio,
 * sem estado herdado).
 */
let schemaBase;
async function schemaCompartilhado() {
  if (schemaBase) return schemaBase;
  const { PGlite } = await import('@electric-sql/pglite');
  const pg = new PGlite();
  await pg.exec("CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $t$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $t$ LANGUAGE plpgsql;");
  await migrate(pg, 102);
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

/** Identidade sintética: a 003 exige kind/email e a 099 acrescentou session_epoch. */
async function novaIdentidade(pg, { kind = 'client', email } = {}) {
  const id = randomUUID();
  await pg.query(
    "INSERT INTO auth_identities(id,kind,email,status,verified_at,verification_method) VALUES ($1,$2,$3,'active',NOW(),'manual')",
    [id, kind, email || `${id.slice(0, 8)}@teste.invalid`],
  );
  return id;
}

function poolOf(pg) {
  return { query: (sql, params) => pg.query(sql, params) };
}

/** Resposta HTTP mínima: captura status/cabeçalhos/bytes sem abrir socket. */
function resposta() {
  const res = {
    status: 0, headers: {}, bytes: null, corpo: null, terminou: false,
    writeHead(status, headers) { this.status = status; this.headers = headers; },
    end(chunk) { this.terminou = true; this.bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk ?? '')); },
  };
  return res;
}

function jsonPara(res) {
  return (alvo, status, corpo) => {
    if (alvo.status) throw new Error('resposta duplicada: o handler respondeu duas vezes');
    alvo.status = status;
    alvo.corpo = corpo;
    alvo.terminou = true;
    return corpo;
  };
}

async function streamParaDisk(conteudo, t) {
  const dir = await mkdtemp(path.join(tmpdir(), 'seg-sec-docs-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const key = createHash('sha256').update(randomUUID()).digest('hex').slice(0, 48);
  const bytes = Buffer.from(conteudo);
  await writeFile(path.join(dir, key), bytes);
  return { dir, key, bytes, sha: createHash('sha256').update(bytes).digest('hex') };
}

// ---------------------------------------------------------------------------
// Portal do cliente
// ---------------------------------------------------------------------------

async function cenarioCliente(t, {
  sessao = true, vencido = false, statusConta = 'active', contaDoVinculo = 'A',
  unidade = null, sessaoReal = null, contratosPermitidos = null,
} = {}) {
  const pg = await openDb(t);
  const contaA = randomUUID();
  const contaB = randomUUID();
  const identidade = await novaIdentidade(pg);
  const documento = randomUUID();
  // A conta B existe e está ativa: se o escopo falhasse, haveria dado para vazar.
  await pg.query(
    "INSERT INTO client_accounts(id,status,display_name,created_by) VALUES ($1,$2,'Conta Sintética A','ti'),($3,'active','Conta Sintética B','ti')",
    [contaA, statusConta, contaB],
  );
  // `reason` e `granted_by` são NOT NULL na 004: a concessão sempre tem motivo
  // declarado por um papel administrativo — o mesmo que a API exige.
  // Um único vínculo: com A (caso autorizado) ou com B (caso indevido). Nos dois
  // cenários a conta B existe e está ativa — se o escopo falhasse, haveria conta
  // para onde "vazar" e o documento A seria servido.
  const contaVinculada = contaDoVinculo === 'A' ? contaA : contaB;
  // Unidade/filial sintética ('propria' = a própria conta do documento;
  // 'outra' = uma unidade da qual a conta do documento não faz parte).
  let unidadeId = null;
  if (unidade) {
    unidadeId = unidade === 'propria' ? contaVinculada : randomUUID();
    if (unidade === 'outra') {
      await pg.query(
        "INSERT INTO client_accounts(id,status,display_name,created_by) VALUES ($1,'active','Outra Unidade Sintética','ti')",
        [unidadeId],
      );
    }
  }
  await pg.query(
    `INSERT INTO client_access_grants(id,identity_id,client_account_id,reason,granted_by,revoked_at,unit_account_id,contract_scope_mode,allowed_contract_ids)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)`,
    [randomUUID(), identidade, contaVinculada, 'concessão sintética de teste', 'ti',
      vencido ? new Date() : null, unidadeId,
      contratosPermitidos ? 'selected' : 'all', contratosPermitidos || []],
  );
  const disco = await streamParaDisk('CONTEUDO-CONFIDENCIAL-DA-CONTA-A', t);
  await pg.query(
    `INSERT INTO client_documents(id,client_account_id,title,category,original_filename,content_type,size_bytes,storage_key,content_sha256,uploaded_by,uploaded_by_identity)
     VALUES ($1,$2,'Contrato A','contrato','contrato-a.txt','text/plain',$3,$4,$5,'ti',$6)`,
    [documento, contaA, disco.bytes.length, disco.key, disco.sha, identidade],
  );

  const auditoria = [];
  const pool = poolOf(pg);
  const poolAuditado = {
    query: async (sql, params) => {
      const r = await pool.query(sql, params);
      if (sql.includes('auth_access_audit')) auditoria.push({ sql, params });
      return r;
    },
  };
  // Sessão real: quando pedida, quem responde é o `readClientSession` de
  // produção (client-access-api), lendo auth_sessions — não um stub.
  let leitorSessao = async () => (sessao ? { identityId: identidade } : null);
  if (sessaoReal) {
    const { token, revogadaEm = null, expiraEm = null } = sessaoReal;
    await pg.query(
      'INSERT INTO auth_sessions(id,identity_id,token_hash,expires_at,revoked_at) VALUES ($1,$2,$3,$4,$5)',
      [randomUUID(), identidade, createHash('sha256').update(token).digest('hex'),
        expiraEm || new Date(Date.now() + 3600_000), revogadaEm],
    );
    const acessos = createClientAccessApi({
      getPool: () => poolAuditado,
      json: jsonPara(),
      readJson: async () => ({}),
      sameOrigin: () => true,
      cookieSecure: () => false,
      clientIp: () => '203.0.113.9',
    });
    leitorSessao = (req) => acessos.readClientSession(req);
  }
  const api = createClientSpaceApi({
    getPool: () => poolAuditado,
    docsDir: disco.dir,
    readClientSession: leitorSessao,
    sameOrigin: () => true,
    readJson: async () => ({}),
    json: jsonPara(),
  });
  return { api, contaA, contaB, identidade, documento, disco, auditoria, pg, unidadeId };
}

// O módulo do portal expõe handlers nomeados (não um `handle` único): o teste
// chama exatamente o handler que o despacho do servidor chamaria.
async function baixarCliente(ctx, documento = ctx.documento, cookie = null) {
  const res = resposta();
  const req = {
    method: 'GET',
    headers: cookie ? { cookie: `${CLIENT_SESSION_COOKIE}=${cookie}` } : {},
    url: `http://local.invalid/api/client/documents/${documento}/download`,
  };
  await ctx.api.handleClientDocumentDownload(req, res, documento);
  return res;
}

test('08/A: cliente com vínculo ativo baixa o próprio documento e a ação é auditada', async (t) => {
  const ctx = await cenarioCliente(t);
  const res = await baixarCliente(ctx);
  assert.equal(res.status, 200, JSON.stringify(res.corpo));
  assert.deepEqual(res.bytes, ctx.disco.bytes, 'os bytes servidos precisam ser exatamente os do arquivo');
  assert.equal(res.headers['Cache-Control'], 'private, no-store');
  assert.equal(res.headers['X-Content-Type-Options'], 'nosniff');
  const permitida = ctx.auditoria.find((a) => JSON.stringify(a.params).includes('document_download')
    && JSON.stringify(a.params).includes('allowed'));
  assert.ok(permitida, 'download autorizado precisa gerar auditoria "allowed"');
});

test('08/B: documento de OUTRA conta é negado com 403, sem byte e com auditoria de negação', async (t) => {
  const ctx = await cenarioCliente(t, { contaDoVinculo: 'B' });
  // Documento pertence à conta A, mas o vínculo ativo com A foi revogado; B
  // existe e está ativa — o teste garante que não há "vazamento por fallback".
  const res = await baixarCliente(ctx);
  assert.equal(res.status, 403);
  assert.equal(res.corpo?.error, 'forbidden');
  assert.equal(res.bytes, null, 'negação não pode servir bytes');
  assert.equal(res.headers['Content-Disposition'], undefined);
  const negada = ctx.auditoria.find((a) => JSON.stringify(a.params).includes('authorization_denied'));
  assert.ok(negada, 'negativa de escopo precisa ser auditada');
});

test('08/B: vínculo revogado e conta inativa são negados mesmo com sessão válida', async (t) => {
  const revogado = await cenarioCliente(t, { vencido: true });
  const resRevogado = await baixarCliente(revogado);
  assert.equal(resRevogado.status, 403, 'vínculo revogado não pode baixar');
  assert.equal(resRevogado.bytes, null);

  const inativa = await cenarioCliente(t, { statusConta: 'suspended' });
  const resInativa = await baixarCliente(inativa);
  assert.equal(resInativa.status, 403, 'conta inativa não pode baixar, mesmo com vínculo');
  assert.equal(resInativa.bytes, null);
});

test('08/B: sem sessão é 401 antes de qualquer entrega; id inválido é 400', async (t) => {
  const ctx = await cenarioCliente(t, { sessao: false });
  const res = await baixarCliente(ctx);
  assert.equal(res.status, 401);
  assert.equal(res.corpo?.error, 'client_session_required');
  assert.equal(res.bytes, null);

  const comSessao = await cenarioCliente(t);
  const invalido = await baixarCliente(comSessao, 'nao-e-uuid');
  assert.equal(invalido.status, 400);
  assert.equal(invalido.corpo?.error, 'invalid_document_id');

  const inexistente = await baixarCliente(comSessao, randomUUID());
  assert.equal(inexistente.status, 404);
});

test('08: adulteração no armazenamento privado entrega 409 e nenhum byte', async (t) => {
  const ctx = await cenarioCliente(t);
  // Mesmo tamanho, conteúdo diferente: só o hash pode detectar.
  await writeFile(path.join(ctx.disco.dir, ctx.disco.key), Buffer.from('CONTEUDO-CONFIDENCIAL-DA-CONTA-B'));
  const res = await baixarCliente(ctx);
  assert.equal(res.status, 409);
  assert.equal(res.corpo?.error, 'document_integrity_failed');
  assert.equal(res.bytes, null, 'arquivo adulterado não pode ser servido');
  const negada = ctx.auditoria.find((a) => JSON.stringify(a.params).includes('document_download')
    && JSON.stringify(a.params).includes('denied'));
  assert.ok(negada, 'integridade violada precisa registrar negação');
});

test('08: falha de auditoria impede o download (fail-closed), não libera o arquivo', async (t) => {
  const ctx = await cenarioCliente(t);
  const poolQuebrado = {
    query: async (sql, params) => {
      if (sql.includes('INSERT INTO auth_access_audit')) throw new Error('audit offline');
      return poolOf(ctx.pg).query(sql, params);
    },
  };
  const api = createClientSpaceApi({
    getPool: () => poolQuebrado,
    docsDir: ctx.disco.dir,
    readClientSession: async () => ({ identityId: ctx.identidade }),
    sameOrigin: () => true,
    readJson: async () => ({}),
    json: jsonPara(),
  });
  const res = resposta();
  await api.handleClientDocumentDownload(
    { method: 'GET', headers: {}, url: `http://local.invalid/api/client/documents/${ctx.documento}/download` },
    res, ctx.documento,
  );
  assert.equal(res.status, 503, 'sem trilha de auditoria o byte privado não sai');
  assert.equal(res.bytes, null);
});

// ---------------------------------------------------------------------------
// Documentos privados do funcionário (próprio × RH)
// ---------------------------------------------------------------------------

async function cenarioFuncionario(t, { papel = 'employee', concessao = false } = {}) {
  const pg = await openDb(t);
  const funcionarioA = randomUUID();
  const funcionarioB = randomUUID();
  const identidadeA = await novaIdentidade(pg, { kind: 'staff' });
  const identidadeB = await novaIdentidade(pg, { kind: 'staff' });
  const identidadeStaff = await novaIdentidade(pg, { kind: 'staff' });
  const documentoA = randomUUID();
  await pg.query(
    `INSERT INTO hr_employees(id,matricula,identity_id,status,display_name,cargo)
     VALUES ($1,'A-0001',$2,'ativo','Pessoa Sintética A','Analista'),($3,'B-0002',$4,'ativo','Pessoa Sintética B','Analista')`,
    [funcionarioA, identidadeA, funcionarioB, identidadeB],
  );
  const disco = await streamParaDisk('PRONTUARIO-DO-FUNCIONARIO-A', t);
  await pg.query(
    `INSERT INTO employee_private_documents(id,employee_id,document_kind,category,title,original_filename,content_type,size_bytes,storage_key,content_sha256,uploaded_by_kind,uploaded_by_identity,status,source_authorized,published_at)
     VALUES ($1,$2,'payroll','holerite','Holerite A','holerite-a.pdf','application/pdf',$3,$4,$5,'employee',$6,'published',TRUE,NOW())`,
    [documentoA, funcionarioA, disco.bytes.length, disco.key, disco.sha, identidadeA],
  );
  if (concessao) {
    await pg.query(
      `INSERT INTO auth_permissions(id,identity_id,permission,scope_type,reason)
       VALUES (gen_random_uuid(),$1,'employees.read','organization','concessão sintética de teste')`,
      [identidadeStaff],
    );
  }
  const api = createEmployeeApi({
    getPool: () => poolOf(pg),
    json: jsonPara(),
    readJson: async () => ({}),
    readEmployeeSession: async () => (papel === 'employee' ? { identityId: identidadeA, employeeId: funcionarioA } : null),
    readStaffSession: async () => (papel === 'rh' ? { identityId: identidadeStaff, role: 'rh' } : null),
    sameOrigin: () => true,
    employeeDocsDir: disco.dir,
  });
  return { api, funcionarioA, funcionarioB, identidadeA, identidadeB, identidadeStaff, documentoA, disco, pg };
}

async function baixarFuncionario(ctx, documento) {
  const res = resposta();
  await ctx.api.handle({ method: 'GET', headers: {} }, res,
    new URL(`http://local.invalid/api/employee/documents/${documento}/download`));
  return res;
}

test('08/A: funcionário baixa o próprio documento; download é registrado', async (t) => {
  const ctx = await cenarioFuncionario(t);
  const res = await baixarFuncionario(ctx, ctx.documentoA);
  assert.equal(res.status, 200, JSON.stringify(res.corpo));
  assert.deepEqual(res.bytes, ctx.disco.bytes);
  const { rows } = await ctx.pg.query("SELECT action FROM employee_private_document_access WHERE document_id=$1", [ctx.documentoA]);
  assert.deepEqual(rows.map((r) => r.action), ['download']);
});

test('08/B: funcionário não baixa documento de outro funcionário (404, sem bytes)', async (t) => {
  const ctx = await cenarioFuncionario(t);
  const outroDocumento = randomUUID();
  const outroDisco = await streamParaDisk('PRONTUARIO-DO-FUNCIONARIO-B', t);
  await ctx.pg.query(
    `INSERT INTO employee_private_documents(id,employee_id,document_kind,category,title,original_filename,content_type,size_bytes,storage_key,content_sha256,uploaded_by_kind,uploaded_by_identity,status,source_authorized,published_at)
     VALUES ($1,$2,'payroll','holerite','Holerite B','holerite-b.pdf','application/pdf',$3,$4,$5,'employee',$6,'published',TRUE,NOW())`,
    [outroDocumento, ctx.funcionarioB, outroDisco.bytes.length, outroDisco.key, outroDisco.sha, ctx.identidadeB],
  );
  const res = await baixarFuncionario(ctx, outroDocumento);
  assert.equal(res.status, 404, 'documento de outro funcionário não pode ser revelado nem servido');
  assert.equal(res.bytes, null);
});

test('08/B: RH sem concessão sobre o funcionário recebe 403 e nenhum byte', async (t) => {
  const ctx = await cenarioFuncionario(t, { papel: 'rh', concessao: false });
  const res = resposta();
  await ctx.api.handle({ method: 'GET', headers: {} }, res,
    new URL(`http://local.invalid/api/admin/hr/l03/documents/${ctx.documentoA}/download`));
  assert.equal(res.status, 403, JSON.stringify(res.corpo));
  assert.equal(res.corpo?.error, 'permission_scope_denied');
  assert.equal(res.bytes, null);
  const { rows } = await ctx.pg.query('SELECT action FROM employee_private_document_access');
  assert.equal(rows.length, 0, 'negativa não pode gravar download');
});

test('08/A: RH com concessão organizacional baixa com auditoria de ator staff', async (t) => {
  const ctx = await cenarioFuncionario(t, { papel: 'rh', concessao: true });
  const res = resposta();
  await ctx.api.handle({ method: 'GET', headers: {} }, res,
    new URL(`http://local.invalid/api/admin/hr/l03/documents/${ctx.documentoA}/download`));
  assert.equal(res.status, 200, JSON.stringify(res.corpo));
  assert.deepEqual(res.bytes, ctx.disco.bytes);
  const { rows } = await ctx.pg.query('SELECT actor_kind, action FROM employee_private_document_access');
  assert.deepEqual(rows, [{ actor_kind: 'staff', action: 'download' }]);
});

test('08/B: sem sessão nem funcionário nem RH alcançam o byte', async (t) => {
  const ctx = await cenarioFuncionario(t, { papel: 'ninguem' });
  const proprio = await baixarFuncionario(ctx, ctx.documentoA);
  assert.equal(proprio.status, 401);
  assert.equal(proprio.bytes, null);

  const staff = resposta();
  await ctx.api.handle({ method: 'GET', headers: {} }, staff,
    new URL(`http://local.invalid/api/admin/hr/l03/documents/${ctx.documentoA}/download`));
  assert.equal(staff.status, 401);
  assert.equal(staff.bytes, null);
});

test('08: documento do funcionário adulterado é 409 e registra integrity_denied', async (t) => {
  const ctx = await cenarioFuncionario(t);
  await writeFile(path.join(ctx.disco.dir, ctx.disco.key), Buffer.from('PRONTUARIO-DE-OUTRA-PESSOA'));
  const res = await baixarFuncionario(ctx, ctx.documentoA);
  assert.equal(res.status, 409);
  assert.equal(res.corpo?.error, 'document_integrity_failed');
  assert.equal(res.bytes, null);
  const { rows } = await ctx.pg.query('SELECT action FROM employee_private_document_access');
  assert.deepEqual(rows.map((r) => r.action), ['integrity_denied']);
});

// ---------------------------------------------------------------------------
// Sessões revogadas / expiradas — com o leitor de sessão de PRODUÇÃO
// ---------------------------------------------------------------------------

test('08/B: sessão revogada no servidor não baixa, mesmo com vínculo e cookie válidos', async (t) => {
  const token = 'sessao-revogada-sintetica';
  const ctx = await cenarioCliente(t, { sessaoReal: { token, revogadaEm: new Date() } });
  const res = await baixarCliente(ctx, ctx.documento, token);
  assert.equal(res.status, 401, 'revogação no servidor precisa vencer o cookie');
  assert.equal(res.corpo?.error, 'client_session_required');
  assert.equal(res.bytes, null);
});

test('08/B: sessão expirada não baixa; o mesmo token sem revogação baixa (controle A)', async (t) => {
  const token = 'sessao-expirada-sintetica';
  const expirada = await cenarioCliente(t, {
    sessaoReal: { token, expiraEm: new Date(Date.now() - 60_000) },
  });
  const resExpirada = await baixarCliente(expirada, expirada.documento, token);
  assert.equal(resExpirada.status, 401);
  assert.equal(resExpirada.bytes, null);

  // Controle positivo: com o MESMO leitor real e o mesmo formato de linha, uma
  // sessão vigente entrega o documento. Sem isso, o 401 acima não provaria nada
  // além de "o leitor não funciona".
  const vigente = await cenarioCliente(t, { sessaoReal: { token } });
  const resVigente = await baixarCliente(vigente, vigente.documento, token);
  assert.equal(resVigente.status, 200, JSON.stringify(resVigente.corpo));
  assert.deepEqual(resVigente.bytes, vigente.disco.bytes);
});

// ---------------------------------------------------------------------------
// Escopo de unidade e de contrato (regras vigentes, não matriz nova)
// ---------------------------------------------------------------------------

test('08/B: vínculo restrito a unidade não alcança conta fora da unidade', async (t) => {
  const ctx = await cenarioCliente(t, { unidade: 'outra' });
  // O vínculo aponta para uma unidade à qual a conta do documento NÃO pertence.
  const res = await baixarCliente(ctx);
  assert.equal(res.status, 403, 'restrição de unidade precisa barrar o download');
  assert.equal(res.corpo?.error, 'forbidden');
  assert.equal(res.bytes, null);
  const negada = ctx.auditoria.find((a) => JSON.stringify(a.params).includes('authorization_denied'));
  assert.ok(negada, 'negativa por unidade precisa ser auditada');
});

test('08/A: vínculo restrito à unidade da conta continua permitindo o próprio documento', async (t) => {
  const ctx = await cenarioCliente(t, { unidade: 'propria' });
  const res = await baixarCliente(ctx);
  assert.equal(res.status, 200, JSON.stringify(res.corpo));
  assert.deepEqual(res.bytes, ctx.disco.bytes);
});

// ---------------------------------------------------------------------------
// Escopo de contrato na listagem (mesma regra vigente do vínculo)
// ---------------------------------------------------------------------------

/** Dois contratos na conta A; o vínculo pode liberar nenhum, um ou ambos. */
async function cenarioContratos(t, { permitidos = null, liberar }) {
  const ctx = await cenarioCliente(t);
  const ids = {};
  for (const titulo of ['Contrato Um', 'Contrato Dois']) {
    const id = randomUUID();
    await ctx.pg.query(
      "INSERT INTO client_contracts(id,client_account_id,title,service,created_by) VALUES ($1,$2,$3,'Vigilância','ti')",
      [id, ctx.contaA, titulo],
    );
    ids[titulo] = id;
  }
  // O vínculo é reescrito depois: `liberar` decide o que o grant permite.
  const escopo = liberar ? 'selected' : 'all';
  const lista = liberar === 'um' ? [ids['Contrato Um']] : liberar === 'nenhum' ? [] : [];
  await ctx.pg.query(
    'UPDATE client_access_grants SET contract_scope_mode=$2, allowed_contract_ids=$3 WHERE identity_id=$1',
    [ctx.identidade, escopo, lista],
  );
  const url = new URL(`http://local.invalid/api/client/contracts?account=${ctx.contaA}`);
  const res = resposta();
  await ctx.api.handleClientContracts({ method: 'GET', headers: {}, url }, res, url);
  return { ctx, ids, res };
}

test('08/A: vínculo com todos os contratos lista os dois contratos da conta', async (t) => {
  const { ids, res } = await cenarioContratos(t, { liberar: null });
  assert.equal(res.status, 200, JSON.stringify(res.corpo));
  assert.deepEqual(res.corpo.contracts.map((c) => c.id).sort(), Object.values(ids).sort());
});

test('08/B: vínculo restrito a um contrato lista só ele; lista vazia não lista nada', async (t) => {
  const um = await cenarioContratos(t, { liberar: 'um' });
  assert.equal(um.res.status, 200, JSON.stringify(um.res.corpo));
  assert.deepEqual(um.res.corpo.contracts.map((c) => c.id), [um.ids['Contrato Um']],
    'contrato fora da lista não pode aparecer, e o de dentro precisa aparecer');

  const nenhum = await cenarioContratos(t, { liberar: 'nenhum' });
  assert.equal(nenhum.res.status, 200, JSON.stringify(nenhum.res.corpo));
  assert.deepEqual(nenhum.res.corpo.contracts, [], 'lista vazia libera zero contratos (deny all)');
});
