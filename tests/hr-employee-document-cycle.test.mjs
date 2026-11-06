import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtemp, rm, readdir, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

import { createEmployeeApi } from '../src/server/employee-api.mjs';

// Fatia 13 (recorte documentos do funcionário) — envio → revisão → publicação → leitura.
//
// O plano pede: "solicitações/documentos, ponto/comprovante, comunicados/
// escala/cursos" e "hash/comprovante e estados testados no contrato atual; sem
// afirmar HERE/dispositivo/eSocial real nem abrir borda RH".
//
// Este arquivo cobre a metade de **documentos**, que tem o ciclo completo no
// contrato vigente e pode ser exercitada com banco real. Nada aqui altera
// regra: percorre as que existem e confere o efeito no banco e no disco.
//
//   funcionário envia  → 201, status 'pending', hash e arquivo conferem
//   funcionário lê     → vê só o que é dele; download confere bytes e hash
//   RH revisa          → under_review / approved / rejected (motivo obrigatório)
//   RH publica         → só com fonte autorizada, e fonte autorizada é do RH
//   falha de gravação  → o arquivo já escrito sai do disco
//
// O que NÃO é provado: dispositivos reais, HERE, eSocial, a tela do app e
// aceite humano. O hash aqui é do conteúdo enviado, não comprovante de
// recebimento pelo empregador.

// ---------------------------------------------------------------------------
// Banco: cadeia real até a 102 (cria os documentos privados do funcionário).
// ---------------------------------------------------------------------------
let schemaBase;
async function schemaCompartilhado() {
  if (schemaBase) return schemaBase;
  const { PGlite } = await import('@electric-sql/pglite');
  const pg = new PGlite();
  await pg.exec("CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $t$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $t$ LANGUAGE plpgsql;");
  const dir = new URL('../db/migrations/', import.meta.url);
  for (const arquivo of (await readdir(dir)).filter((f) => f.endsWith('.sql')).sort()) {
    if (Number(arquivo.slice(0, 3)) > 102) break;
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

async function identidade(pg) {
  const id = randomUUID();
  await pg.query(
    "INSERT INTO auth_identities(id,kind,email,status,verified_at,verification_method) VALUES ($1,'staff',$2,'active',NOW(),'manual')",
    [id, `${id.slice(0, 8)}@teste.invalid`],
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
  alvo.status = status; alvo.corpo = corpo; alvo.headers = headers;
  return corpo;
};

/** Dois funcionários, RH com/sem concessão, pasta de arquivos temporária. */
async function cenario(t, { concessao = true } = {}) {
  const pg = await openDb(t);
  const funcionarioA = randomUUID();
  const funcionarioB = randomUUID();
  const identidadeA = await identidade(pg);
  const identidadeB = await identidade(pg);
  const staffId = await identidade(pg);
  await pg.query(
    `INSERT INTO hr_employees(id,matricula,identity_id,status,display_name,cargo)
     VALUES ($1,'A-1000',$2,'ativo','Pessoa Sintética A','Analista'),($3,'B-2000',$4,'ativo','Pessoa Sintética B','Analista')`,
    [funcionarioA, identidadeA, funcionarioB, identidadeB],
  );
  if (concessao) {
    await pg.query(
      `INSERT INTO auth_permissions(id,identity_id,permission,scope_type,reason)
       VALUES (gen_random_uuid(),$1,'employees.read','organization','concessão sintética de teste'),
              (gen_random_uuid(),$1,'employees.write','organization','concessão sintética de teste')`,
      [staffId],
    );
  }
  const disco = await mkdtemp(path.join(tmpdir(), 'seg-fatia13-'));
  t.after(() => rm(disco, { recursive: true, force: true }));

  let sessaoFuncionario = { identityId: identidadeA, employeeId: funcionarioA };
  let sessaoStaff = { identityId: staffId, role: 'rh' };
  const api = createEmployeeApi({
    getPool: () => ({ query: (sql, params) => pg.query(sql, params) }),
    json,
    readJson: async (req) => JSON.parse(req.corpoJson || '{}'),
    readEmployeeSession: async () => sessaoFuncionario,
    readStaffSession: async () => sessaoStaff,
    sameOrigin: () => true,
    employeeDocsDir: disco,
  });
  return {
    pg, api, disco, funcionarioA, funcionarioB, identidadeA, identidadeB, staffId,
    setFuncionario: (s) => { sessaoFuncionario = s; },
    setStaff: (s) => { sessaoStaff = s; },
  };
}

const reqJson = (method, corpo) => ({
  method,
  headers: { host: 'sistema.local', origin: 'http://sistema.local' },
  corpoJson: JSON.stringify(corpo || {}),
  url: 'http://sistema.local/api/employee/documents',
});

async function chamar(api, metodo, caminho, corpo) {
  const res = resposta();
  await api.handle(reqJson(metodo, corpo), res, new URL(`http://sistema.local${caminho}`));
  return res;
}

const CONTEUDO = Buffer.from('COMPROVANTE SINTETICO DE CURSO INTERNO', 'utf8');
const envioDe = (ctx, extra = {}) => ({
  employeeId: ctx.funcionarioA,
  documentKind: 'course_proof',
  category: 'treinamento',
  title: 'Comprovante de curso interno',
  filename: 'comprovante.pdf',
  contentType: 'application/pdf',
  contentBase64: CONTEUDO.toString('base64'),
  ...extra,
});

const arquivosNoDisco = async (dir) => (await readdir(dir)).filter((f) => !f.startsWith('.'));

// ---------------------------------------------------------------------------
// Envio e revisão
// ---------------------------------------------------------------------------

test('13/A: funcionário envia; o documento nasce pendente com hash e arquivo conferidos', async (t) => {
  const ctx = await cenario(t);
  const res = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx));

  assert.equal(res.status, 201, JSON.stringify(res.corpo));
  assert.equal(res.corpo.document.status, 'pending', 'envio do funcionário nasce pendente de revisão');
  assert.equal(res.corpo.document.version, 1);

  const { rows } = await ctx.pg.query('SELECT * FROM employee_private_documents WHERE id=$1', [res.corpo.document.id]);
  assert.equal(rows[0].employee_id, ctx.funcionarioA);
  assert.equal(rows[0].uploaded_by_kind, 'employee');
  assert.equal(rows[0].uploaded_by_identity, ctx.identidadeA);
  assert.match(rows[0].content_sha256, /^[0-9a-f]{64}$/);

  const bytes = await readFile(path.join(ctx.disco, rows[0].storage_key));
  assert.deepEqual(bytes, CONTEUDO, 'o arquivo em disco é o enviado');

  const { rows: trilha } = await ctx.pg.query('SELECT action, actor_kind FROM employee_private_document_access WHERE document_id=$1', [res.corpo.document.id]);
  assert.deepEqual(trilha, [{ action: 'upload', actor_kind: 'employee' }]);
});

test('13/B: employeeId forjado no corpo é ignorado — o documento vai para o dono da sessão', async (t) => {
  const ctx = await cenario(t);
  // O funcionário A manda `employeeId` do funcionário B. O servidor ignora o
  // campo de propósito e usa o vínculo da sessão: B não ganha documento e A
  // recebe o próprio. Recusar também seria aceitável; o que não pode é gravar
  // em nome de terceiro.
  const res = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx, { employeeId: ctx.funcionarioB }));
  assert.equal(res.status, 201, JSON.stringify(res.corpo));

  const { rows } = await ctx.pg.query('SELECT employee_id, uploaded_by_identity FROM employee_private_documents');
  assert.equal(rows.length, 1);
  assert.equal(rows[0].employee_id, ctx.funcionarioA, 'gravou no dono da sessão, não no id forjado');
  assert.equal(rows[0].uploaded_by_identity, ctx.identidadeA);

  ctx.setFuncionario({ identityId: ctx.identidadeB, employeeId: ctx.funcionarioB });
  const doOutro = await chamar(ctx.api, 'GET', '/api/employee/documents');
  assert.deepEqual(doOutro.corpo.documents, []);
});

test('13/B: tipo de conteúdo não permitido e arquivo vazio são recusados', async (t) => {
  const ctx = await cenario(t);
  const tipo = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx, { contentType: 'application/x-executavel' }));
  assert.equal(tipo.status, 400);
  assert.equal(tipo.corpo.error, 'invalid_content_type');

  const vazio = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx, { contentBase64: '' }));
  assert.equal(vazio.status, 400);
  assert.equal(vazio.corpo.error, 'invalid_file_size');

  assert.deepEqual(await arquivosNoDisco(ctx.disco), [], 'recusa não deixa arquivo no disco');
});

test('13/A/B: RH revisa e aprova; o outro funcionário não vê o documento', async (t) => {
  const ctx = await cenario(t);
  const enviado = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx));

  const revisao = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: enviado.corpo.document.id, status: 'under_review' });
  assert.equal(revisao.status, 200, JSON.stringify(revisao.corpo));
  assert.equal(revisao.corpo.document.status, 'under_review');

  const aprovacao = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: enviado.corpo.document.id, status: 'approved' });
  assert.equal(aprovacao.status, 200);
  assert.equal(aprovacao.corpo.document.status, 'approved');

  const { rows: trilha } = await ctx.pg.query(
    'SELECT action, actor_kind FROM employee_private_document_access WHERE document_id=$1 ORDER BY created_at',
    [enviado.corpo.document.id],
  );
  assert.deepEqual(trilha.map((r) => r.action), ['upload', 'review', 'review']);
  assert.deepEqual(trilha.slice(1).map((r) => r.actor_kind), ['staff', 'staff']);

  // O dono continua vendo (é o autor do envio).
  const doDono = await chamar(ctx.api, 'GET', '/api/employee/documents');
  assert.equal(doDono.status, 200);
  assert.deepEqual(doDono.corpo.documents.map((d) => d.id), [enviado.corpo.document.id]);

  // O outro funcionário não vê: o filtro é por employee_id.
  ctx.setFuncionario({ identityId: ctx.identidadeB, employeeId: ctx.funcionarioB });
  const doOutro = await chamar(ctx.api, 'GET', '/api/employee/documents');
  assert.equal(doOutro.status, 200);
  assert.deepEqual(doOutro.corpo.documents, [], 'documento de A não aparece para B');
});

test('13/B: rejeitar exige motivo escrito e o motivo fica gravado', async (t) => {
  const ctx = await cenario(t);
  const enviado = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx));

  const semMotivo = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: enviado.corpo.document.id, status: 'rejected' });
  assert.equal(semMotivo.status, 400);
  assert.equal(semMotivo.corpo.error, 'rejection_reason_required');

  const curto = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: enviado.corpo.document.id, status: 'rejected', rejectionReason: 'nao' });
  assert.equal(curto.status, 400, 'motivo curto não serve');

  const comMotivo = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: enviado.corpo.document.id, status: 'rejected', rejectionReason: 'Documento ilegível; reenviar com melhor resolução' });
  assert.equal(comMotivo.status, 200, JSON.stringify(comMotivo.corpo));
  assert.equal(comMotivo.corpo.document.status, 'rejected');
  assert.match(comMotivo.corpo.document.rejection_reason, /ilegível/);

  const doDono = await chamar(ctx.api, 'GET', '/api/employee/documents');
  assert.equal(doDono.corpo.documents[0].rejection_reason, comMotivo.corpo.document.rejection_reason,
    'o funcionário precisa conseguir ler por que foi rejeitado');
});

test('13/B: transição de estado inventada é recusada sem alterar a linha', async (t) => {
  const ctx = await cenario(t);
  const enviado = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx));

  for (const status of ['aprovado', 'PENDING', '', 'deleted']) {
    const res = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: enviado.corpo.document.id, status });
    assert.equal(res.status, 400, `status "${status}" precisa ser recusado`);
    assert.equal(res.corpo.error, 'invalid_status');
  }
  const { rows } = await ctx.pg.query('SELECT status FROM employee_private_documents WHERE id=$1', [enviado.corpo.document.id]);
  assert.equal(rows[0].status, 'pending', 'recusa não pode mexer no estado');
});

// ---------------------------------------------------------------------------
// Publicação: fonte autorizada é do RH
// ---------------------------------------------------------------------------

test('13/A: RH publica o documento que ELE enviou (fonte autorizada) e o funcionário lê', async (t) => {
  const ctx = await cenario(t);
  // Publicação vem de fonte autorizada: é o RH quem envia o documento, com
  // `sourceAuthorized: true`. O envio do próprio funcionário não se publica.
  const doRh = await chamar(ctx.api, 'POST', '/api/admin/hr/l03/documents', {
    employeeId: ctx.funcionarioA,
    documentKind: 'course_proof',
    category: 'treinamento',
    title: 'Certificado de curso obrigatório 2026-10',
    filename: 'certificado.txt',
    contentType: 'text/plain',
    contentBase64: Buffer.from('CERTIFICADO SINTETICO DE CURSO OBRIGATORIO', 'utf8').toString('base64'),
    sourceAuthorized: true,
    sourceLabel: 'Fonte de treinamento autorizada pelo operador',
  });
  assert.equal(doRh.status, 201, JSON.stringify(doRh.corpo));
  assert.equal(doRh.corpo.document.status, 'pending');
  assert.equal(doRh.corpo.document.source_authorized, true);

  const publicar = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: doRh.corpo.document.id, status: 'published' });
  assert.equal(publicar.status, 200, JSON.stringify(publicar.corpo));
  assert.ok(publicar.corpo.document.published_at, 'publicação registra o instante');

  const { rows: trilha } = await ctx.pg.query(
    'SELECT action, actor_kind FROM employee_private_document_access WHERE document_id=$1 ORDER BY created_at',
    [doRh.corpo.document.id],
  );
  assert.deepEqual(trilha.map((r) => r.action), ['upload', 'publish']);
  assert.deepEqual(trilha.map((r) => r.actor_kind), ['staff', 'staff']);

  // O titular lê o próprio documento publicado.
  const lista = await chamar(ctx.api, 'GET', '/api/employee/documents');
  assert.equal(lista.status, 200);
  const publicado = lista.corpo.documents.find((d) => d.id === doRh.corpo.document.id);
  assert.ok(publicado, 'o titular precisa enxergar o documento publicado');
  assert.equal(publicado.status, 'published');
  assert.ok(publicado.published_at);

  // O outro funcionário não enxerga nada.
  ctx.setFuncionario({ identityId: ctx.identidadeB, employeeId: ctx.funcionarioB });
  const doOutro = await chamar(ctx.api, 'GET', '/api/employee/documents');
  assert.deepEqual(doOutro.corpo.documents, []);
});

test('13/B: envio do próprio funcionário nunca vira publicação (fonte autorizada é do RH)', async (t) => {
  const ctx = await cenario(t);
  const enviado = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx, { sourceAuthorized: true }));
  assert.equal(enviado.status, 201);

  // O servidor descarta a autorização auto-declarada no envio do funcionário.
  const { rows } = await ctx.pg.query('SELECT status, source_authorized FROM employee_private_documents WHERE id=$1', [enviado.corpo.document.id]);
  assert.equal(rows[0].status, 'pending');
  assert.equal(rows[0].source_authorized, false, 'o funcionário não autoriza a própria fonte');

  const publicar = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: enviado.corpo.document.id, status: 'published' });
  assert.equal(publicar.status, 409);
  assert.equal(publicar.corpo.error, 'authorized_source_required');

  // O banco também recusa, mesmo que a rota deixasse passar.
  await assert.rejects(
    () => ctx.pg.query("UPDATE employee_private_documents SET status='published', published_at=NOW() WHERE id=$1", [enviado.corpo.document.id]),
    /check constraint|violates/,
    'o CHECK do banco é a última barreira contra publicar sem fonte autorizada',
  );

  // Mas o autor continua vendo o próprio envio pendente.
  const doDono = await chamar(ctx.api, 'GET', '/api/employee/documents');
  assert.deepEqual(doDono.corpo.documents.map((d) => d.id), [enviado.corpo.document.id]);
});

test('13/B: publicar documento sem fonte autorizada é bloqueado', async (t) => {
  const ctx = await cenario(t);
  const enviado = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx));
  assert.equal(enviado.status, 201);

  const publicar = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: enviado.corpo.document.id, status: 'published' });
  assert.equal(publicar.status, 409);
  assert.equal(publicar.corpo.error, 'authorized_source_required');

  const { rows } = await ctx.pg.query('SELECT status, published_at FROM employee_private_documents WHERE id=$1', [enviado.corpo.document.id]);
  assert.equal(rows[0].status, 'pending');
  assert.equal(rows[0].published_at, null);
});

test('13/B: folha/informe exigem permissão de remuneração e a recusa acontece antes de gravar arquivo', async (t) => {
  const ctx = await cenario(t);
  // `cenario` dá employees.read/write, mas não employees.compensation.write.
  for (const documentKind of ['payroll', 'income_report']) {
    const res = await chamar(ctx.api, 'POST', '/api/admin/hr/l03/documents', {
      employeeId: ctx.funcionarioA,
      documentKind,
      category: 'folha',
      title: `Documento sensível ${documentKind}`,
      filename: 'sensivel.txt',
      contentType: 'text/plain',
      contentBase64: Buffer.from('CONTEUDO SINTETICO SENSIVEL', 'utf8').toString('base64'),
      sourceAuthorized: true,
    });
    assert.equal(res.status, 403, `${documentKind} precisa de permissão própria`);
    assert.equal(res.corpo.error, 'compensation_permission_required');
  }

  const { rows } = await ctx.pg.query('SELECT id FROM employee_private_documents');
  assert.equal(rows.length, 0, 'a guarda roda antes do INSERT');
  assert.deepEqual(await arquivosNoDisco(ctx.disco), [], 'e antes de escrever o arquivo');
});

// ---------------------------------------------------------------------------
// Download
// ---------------------------------------------------------------------------

test('13/A: o titular baixa o próprio documento com os bytes exatos e trilha de download', async (t) => {
  const ctx = await cenario(t);
  const enviado = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx));

  const res = await chamar(ctx.api, 'GET', `/api/employee/documents/${enviado.corpo.document.id}/download`);
  assert.equal(res.status, 200, JSON.stringify(res.corpo));
  assert.deepEqual(res.bytes, CONTEUDO, 'os bytes baixados são exatamente os enviados');
  assert.equal(res.headers['Content-Type'], 'application/pdf');
  assert.equal(res.headers['Cache-Control'], 'private, no-store');
  assert.equal(res.headers['X-Content-Type-Options'], 'nosniff');

  const { rows } = await ctx.pg.query("SELECT action FROM employee_private_document_access WHERE document_id=$1 AND action='download'", [enviado.corpo.document.id]);
  assert.equal(rows.length, 1, 'o download fica registrado na trilha');
});

test('13/B: download de documento alheio é 404, sem vazar existência', async (t) => {
  const ctx = await cenario(t);
  const enviado = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx));

  ctx.setFuncionario({ identityId: ctx.identidadeB, employeeId: ctx.funcionarioB });
  const res = await chamar(ctx.api, 'GET', `/api/employee/documents/${enviado.corpo.document.id}/download`);
  assert.equal(res.status, 404);
  assert.equal(res.bytes, null, 'nenhum byte pode sair');

  const { rows } = await ctx.pg.query("SELECT action FROM employee_private_document_access WHERE document_id=$1 AND action='download'", [enviado.corpo.document.id]);
  assert.equal(rows.length, 0, 'tentativa negada não registra download bem-sucedido');
});

test('13/A: arquivo trocado no disco é detectado pelo hash e o download é negado', async (t) => {
  const ctx = await cenario(t);
  const enviado = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx));
  const { rows } = await ctx.pg.query('SELECT storage_key FROM employee_private_documents WHERE id=$1', [enviado.corpo.document.id]);
  const caminho = path.join(ctx.disco, rows[0].storage_key);

  // Mesmo tamanho, conteúdo diferente: só o hash pega.
  await writeFile(caminho, Buffer.from('X'.repeat(CONTEUDO.length)));

  const res = await chamar(ctx.api, 'GET', `/api/employee/documents/${enviado.corpo.document.id}/download`);
  assert.equal(res.status, 409);
  assert.equal(res.corpo.error, 'document_integrity_failed');
  assert.equal(res.bytes, null, 'conteúdo adulterado não pode ser entregue');

  const { rows: trilha } = await ctx.pg.query(
    "SELECT action FROM employee_private_document_access WHERE document_id=$1 AND action='integrity_denied'",
    [enviado.corpo.document.id],
  );
  assert.equal(trilha.length, 1, 'a adulteração fica registrada');
});

// ---------------------------------------------------------------------------
// Permissão
// ---------------------------------------------------------------------------

test('13/B: RH sem concessão recebe 403 e não grava trilha', async (t) => {
  const ctx = await cenario(t, { concessao: false });
  const enviado = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx));

  const negado = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: enviado.corpo.document.id, status: 'approved' });
  assert.equal(negado.status, 403);
  assert.equal(negado.corpo.error, 'permission_scope_denied');

  const { rows } = await ctx.pg.query(
    "SELECT action FROM employee_private_document_access WHERE document_id=$1 AND actor_kind='staff'",
    [enviado.corpo.document.id],
  );
  assert.deepEqual(rows, [], 'negado não escreve revisão');
  const { rows: doc } = await ctx.pg.query('SELECT status FROM employee_private_documents WHERE id=$1', [enviado.corpo.document.id]);
  assert.equal(doc[0].status, 'pending');
});

test('13/B: revisão de documento inexistente é 404, sem revelar conteúdo', async (t) => {
  const ctx = await cenario(t);
  const res = await chamar(ctx.api, 'PATCH', '/api/admin/hr/l03/documents', { id: randomUUID(), status: 'approved' });
  assert.equal(res.status, 404);
  assert.equal(res.corpo.error, 'document_not_found');
});

test('13/B: sem sessão, nem funcionário nem RH alcançam os documentos', async (t) => {
  const ctx = await cenario(t);
  ctx.setFuncionario(null);
  ctx.setStaff(null);

  const doFuncionario = await chamar(ctx.api, 'GET', '/api/employee/documents');
  assert.equal(doFuncionario.status, 401);

  const doRh = await chamar(ctx.api, 'GET', '/api/admin/hr/l03/documents');
  assert.equal(doRh.status, 401);
});

// ---------------------------------------------------------------------------
// Versionamento e falha de gravação
// ---------------------------------------------------------------------------

test('13/A: reenvio do mesmo tipo cria versão seguinte, não sobrescreve a anterior', async (t) => {
  const ctx = await cenario(t);
  const primeira = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx));
  const segunda = await chamar(ctx.api, 'POST', '/api/employee/documents',
    envioDe(ctx, { contentBase64: Buffer.from('COMPROVANTE SINTETICO CORRIGIDO E REENVIADO', 'utf8').toString('base64') }));

  assert.equal(primeira.corpo.document.version, 1);
  assert.equal(segunda.status, 201, JSON.stringify(segunda.corpo));
  assert.equal(segunda.corpo.document.version, 2, 'a segunda redação é a versão 2');

  const { rows } = await ctx.pg.query('SELECT id, version FROM employee_private_documents ORDER BY version');
  assert.equal(rows.length, 2, 'a versão anterior continua existindo como prova');
  assert.deepEqual(rows.map((r) => r.version), [1, 2]);
  assert.equal((await arquivosNoDisco(ctx.disco)).length, 2, 'cada versão tem seu próprio arquivo');
});

test('13: falha ao gravar a linha remove o arquivo já escrito', async (t) => {
  const ctx = await cenario(t);
  await ctx.pg.query("ALTER TABLE employee_private_documents ADD CONSTRAINT teste_falha_envio CHECK (title <> 'Forcar Falha')");

  const res = await chamar(ctx.api, 'POST', '/api/employee/documents', envioDe(ctx, { title: 'Forcar Falha' }));
  assert.notEqual(res.status, 201, 'falha de banco não pode virar sucesso');
  const { rows } = await ctx.pg.query('SELECT id FROM employee_private_documents');
  assert.equal(rows.length, 0);
  assert.deepEqual(await arquivosNoDisco(ctx.disco), [], 'o arquivo gravado antes do INSERT precisa sair do disco');
});
