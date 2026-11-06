import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { readdir, readFile } from 'node:fs/promises';

import { createAiRagRealApi } from '../src/server/ai-rag-real-api.mjs';

// Fatia 15 — RAG com corpus real por escopo.
//
// O plano pede: isolar fontes por perfil e permissão, exercitar
// indisponibilidade/timeout/fallback e corrigir defeitos do caminho existente,
// **sem** declarar qualidade de resposta nem entrega de modelo real.
//
// Diferença em relação a `tests/ai-rag-real-scope.test.mjs`: aquele arquivo usa
// pool simulado (as linhas já vêm "prontas"); este aplica a cadeia real de
// migrações em PGlite e grava documentos/chunks com os `CHECK`s e `ENUM`s de
// produção. É o SQL de recuperação que fica sob teste — não um array devolvido
// pelo stub. O provedor de linguagem continua sendo um stub determinístico,
// identificado como tal: nada aqui prova Ollama, qualidade ou latência.

// ---------------------------------------------------------------------------
// Banco real: migrações 001..173 (a 173 é a que amarra o corpus do cliente à
// conta). Montado uma vez e clonado por teste.
// ---------------------------------------------------------------------------
let schemaBase;
async function schemaCompartilhado() {
  if (schemaBase) return schemaBase;
  const { PGlite } = await import('@electric-sql/pglite');
  const pg = new PGlite();
  await pg.exec("CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $t$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $t$ LANGUAGE plpgsql;");
  const dir = new URL('../db/migrations/', import.meta.url);
  const arquivos = (await readdir(dir)).filter((f) => f.endsWith('.sql')).sort();
  for (const arquivo of arquivos) {
    if (Number(arquivo.slice(0, 3)) > 173) break;
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

const poolOf = (pg) => ({ query: (sql, params) => pg.query(sql, params) });

/** Identidades reais: a 095/173 amarram aprovação e vínculo a elas. */
async function identidade(pg, kind = 'staff') {
  const id = randomUUID();
  await pg.query(
    "INSERT INTO auth_identities(id,kind,email,status,verified_at,verification_method) VALUES ($1,$2,$3,'active',NOW(),'manual')",
    [id, kind, `${id.slice(0, 8)}@teste.invalid`],
  );
  return id;
}

/**
 * Semeia um índice publicado + documentos/chunks com o estado pedido.
 * `estado` controla a diferença entre "aprovado e publicado" (recuperável) e
 * "aprovado mas em rascunho/arquivado" (não recuperável).
 */
async function semear(pg, {
  ragKey, aprovador, contaCliente = null, titulo, conteudo, keywords = [],
  isAprovado = true, isPublicado = true, status = 'publicado',
  indexAprovado = true, indexPublicado = true, indexStatus = 'publicado', indexAtivo = true,
}) {
  // A migração 095 já cria um índice por escopo (rascunho, não aprovado).
  // O teste não inventa outro: publica/despublica o índice vigente, que é
  // exatamente o que a curadoria faz em produção.
  await pg.query(
    `UPDATE ai_rag_indexes SET is_approved=$2, is_published=$3, status=$4::ai_rag_status,
       is_active=$5, approved_by_identity=CASE WHEN $2 THEN $6 ELSE approved_by_identity END
     WHERE rag_key=$1`,
    [ragKey, indexAprovado, indexPublicado, indexStatus, indexAtivo, aprovador],
  );
  const { rows: idx } = await pg.query('SELECT id FROM ai_rag_indexes WHERE rag_key=$1', [ragKey]);
  assert.equal(idx.length, 1, `índice ${ragKey} precisa existir (migração 095)`);
  const documento = randomUUID();
  await pg.query(
    `INSERT INTO ai_rag_documents(id,rag_index_id,rag_key,title,content,source,source_type,keywords,is_approved,is_published,status,client_account_id,created_by_identity,approved_by_identity)
     VALUES ($1,$2,$3,$4,$5,'documento sintético de teste','procedimento',$6,$7,$8,$9::ai_rag_status,$10,$11,$11)`,
    [documento, idx[0].id, ragKey, titulo, conteudo, keywords, isAprovado, isPublicado, status, contaCliente, aprovador],
  );
  await pg.query(
    'INSERT INTO ai_rag_chunks(document_id,rag_index_id,rag_key,chunk_index,content,token_count) VALUES ($1,$2,$3,0,$4,$5)',
    [documento, idx[0].id, ragKey, conteudo, Math.max(1, conteudo.split(/\s+/).length)],
  );
  return documento;
}

/**
 * Réplica fiel do `sameOrigin` de `server.mjs` (a função é local ao arquivo e
 * não é exportada). Se o original mudar, este helper precisa acompanhar — por
 * isso o teste abaixo também confere as linhas essenciais do original.
 */
function sameOriginDeServidor(req) {
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method || 'GET')) return true;
  const origin = req.headers.origin;
  const forwardedHost = process.env.TRUST_PROXY === 'true' ? req.headers['x-forwarded-host'] : undefined;
  const expectedHost = String(forwardedHost || req.headers.host || '').split(',')[0].trim().toLowerCase();
  if (!origin || !expectedHost) return false;
  try {
    return new URL(origin).host.toLowerCase() === expectedHost;
  } catch {
    return false;
  }
}

function resposta() {
  return {
    status: 0, headers: {}, corpo: null,
    writeHead(status, headers) { this.status = status; this.headers = headers; },
    end(raw) { this.corpo = raw === undefined ? undefined : JSON.parse(raw); },
  };
}

const CORPO = (rag_key, query) => Buffer.from(JSON.stringify({ rag_key, query }));

async function perguntar(api, { rag_key, query, origin = true }) {
  const req = {
    method: 'POST',
    headers: origin ? { origin: 'http://local.invalid' } : {},
    async *[Symbol.asyncIterator]() { yield CORPO(rag_key, query); },
  };
  const res = resposta();
  api.origemPermitida = origin;
  await api.ask(req, res);
  return res;
}

function apiCom(pg, { cliente = null, staff = null, origemPermitida = true } = {}) {
  const api = createAiRagRealApi({
    pool: poolOf(pg),
    // A flag é do chamador: `perguntar` a ajusta para exercitar origem cruzada
    // sem trocar o restante da configuração.
    sameOrigin: () => api.origemPermitida !== false,
    readStaffSession: async () => staff,
    readClientSession: async () => cliente,
  });
  api.origemPermitida = origemPermitida;
  return api;
}

/** Provedor determinístico, explicitamente um STUB: não é Ollama. */
function stubProvedor(comportamento = 'ok') {
  const chamadas = [];
  const fetch = async (endpoint, init) => {
    chamadas.push({ endpoint: String(endpoint), body: JSON.parse(init.body) });
    if (comportamento === 'http_500') return new Response('erro', { status: 500 });
    if (comportamento === 'vazio') return new Response(JSON.stringify({ model: 'stub', message: { content: '   ' } }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    if (comportamento === 'rejeita') throw new Error('provedor offline (stub)');
    if (comportamento === 'demora') await new Promise((_, reject) => setTimeout(() => reject(Object.assign(new Error('abortado'), { name: 'AbortError' })), 30));
    return new Response(JSON.stringify({ model: 'stub-deterministico', message: { content: 'Resposta do stub determinístico.' } }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
  return { fetch, chamadas };
}

async function comProvedor(comportamento, corpo) {
  const stub = stubProvedor(comportamento);
  const original = globalThis.fetch;
  const antigos = { ENV: process.env.OLLAMA_ENABLED, URL: process.env.OLLAMA_BASE_URL };
  process.env.OLLAMA_ENABLED = 'true';
  process.env.OLLAMA_BASE_URL = 'http://127.0.0.1:11434';
  globalThis.fetch = stub.fetch;
  try { return await corpo(stub); }
  finally {
    globalThis.fetch = original;
    if (antigos.ENV === undefined) delete process.env.OLLAMA_ENABLED; else process.env.OLLAMA_ENABLED = antigos.ENV;
    if (antigos.URL === undefined) delete process.env.OLLAMA_BASE_URL; else process.env.OLLAMA_BASE_URL = antigos.URL;
  }
}

// ---------------------------------------------------------------------------
// Isolamento de fontes por perfil
// ---------------------------------------------------------------------------

test('15/A: cada escopo recupera somente o próprio corpus publicado', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  await semear(pg, { ragKey: 'publico', aprovador, titulo: 'Abertura de chamado', conteudo: 'Para abrir um chamado use o portal do cliente e informe o contrato.', keywords: ['chamado'] });
  await semear(pg, { ragKey: 'rh', aprovador, titulo: 'Férias no RH', conteudo: 'Para solicitar férias use o fluxo de programação e confirme com a liderança.', keywords: ['ferias'] });
  await semear(pg, { ragKey: 'marcelo', aprovador, titulo: 'Férias do Marcelo', conteudo: 'A programação de férias da diretoria é registrada em ata própria.', keywords: ['ferias'] });

  await comProvedor('ok', async (stub) => {
    const rh = await perguntar(apiCom(pg, { staff: { identityId: aprovador, role: 'rh' } }), { rag_key: 'rh', query: 'Como solicitar férias?' });
    assert.equal(rh.status, 200);
    assert.deepEqual(rh.corpo.sources.map((s) => s.title), ['Férias no RH'], 'RH nunca recebe corpus marcelo');

    const aberto = await perguntar(apiCom(pg), { rag_key: 'publico', query: 'Como abrir um chamado?' });
    assert.equal(aberto.status, 200);
    assert.deepEqual(aberto.corpo.sources.map((s) => s.title), ['Abertura de chamado']);

    // O contexto enviado ao provedor é o corpus do escopo, e só ele.
    const enviados = stub.chamadas.map((c) => c.body.messages[1].content).join('\n');
    assert.match(enviados, /Férias no RH/);
    assert.doesNotMatch(enviados, /diretoria/, 'o corpus marcelo não pode vazar para o contexto do RH');
  });
});

test('15/B: staff sem o papel do escopo recebe 403 antes de tocar o banco', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  await semear(pg, { ragKey: 'marcelo', aprovador, titulo: 'Rotina da diretoria', conteudo: 'A rotina da diretoria é revisada na primeira semana do mês.', keywords: ['diretoria'] });

  await comProvedor('ok', async (stub) => {
    const res = await perguntar(apiCom(pg, { staff: { identityId: aprovador, role: 'rh' } }), { rag_key: 'marcelo', query: 'Qual a rotina da diretoria?' });
    assert.equal(res.status, 403);
    assert.equal(res.corpo.error, 'scope_forbidden');
    assert.equal(stub.chamadas.length, 0, 'negado não chama o modelo');
  });
});

test('15/B: cliente sem vínculo não recupera corpus de cliente; com vínculo recupera o da própria conta', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  const contaA = randomUUID();
  const contaB = randomUUID();
  const clienteA = await identidade(pg, 'client');
  await pg.query("INSERT INTO client_accounts(id,status,display_name,created_by) VALUES ($1,'active','Conta A','ti'),($2,'active','Conta B','ti')", [contaA, contaB]);
  await semear(pg, { ragKey: 'cliente', aprovador, contaCliente: contaA, titulo: 'Escala da Conta A', conteudo: 'A escala da portaria da conta A é publicada toda sexta-feira.', keywords: ['escala'] });
  await semear(pg, { ragKey: 'cliente', aprovador, contaCliente: contaB, titulo: 'Escala da Conta B', conteudo: 'A escala da portaria da conta B é publicada toda quinta-feira.', keywords: ['escala'] });

  await comProvedor('ok', async (stub) => {
    // Sem vínculo: nenhum documento é recuperado; a rota declara escopo vazio.
    const semVinculo = await perguntar(apiCom(pg, { cliente: { identityId: clienteA } }), { rag_key: 'cliente', query: 'Qual a escala da portaria?' });
    assert.equal(semVinculo.status, 200);
    assert.deepEqual(semVinculo.corpo.sources, []);
    assert.equal(semVinculo.corpo.reason, 'empty_scope');
    assert.equal(semVinculo.corpo.ollama_used, false);
    assert.equal(stub.chamadas.length, 0, 'escopo vazio não consulta o modelo');

    await pg.query(
      "INSERT INTO client_access_grants(id,identity_id,client_account_id,reason,granted_by) VALUES ($1,$2,$3,'concessão sintética de teste','ti')",
      [randomUUID(), clienteA, contaA],
    );
    const comVinculo = await perguntar(apiCom(pg, { cliente: { identityId: clienteA } }), { rag_key: 'cliente', query: 'Qual a escala da portaria?' });
    assert.equal(comVinculo.status, 200);
    assert.deepEqual(comVinculo.corpo.sources.map((s) => s.title), ['Escala da Conta A'], 'nunca a base de outra conta');
    assert.match(stub.chamadas.at(-1).body.messages[1].content, /conta A/);
    assert.doesNotMatch(stub.chamadas.at(-1).body.messages[1].content, /conta B/);
  });
});

test('15/B: vínculo revogado ou conta suspensa fecham o corpus do cliente', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  const conta = randomUUID();
  const cliente = await identidade(pg, 'client');
  await pg.query("INSERT INTO client_accounts(id,status,display_name,created_by) VALUES ($1,'active','Conta','ti')", [conta]);
  await semear(pg, { ragKey: 'cliente', aprovador, contaCliente: conta, titulo: 'Procedimento da Conta', conteudo: 'O procedimento de ronda da conta está descrito neste documento.', keywords: ['ronda'] });
  await pg.query("INSERT INTO client_access_grants(id,identity_id,client_account_id,reason,granted_by) VALUES ($1,$2,$3,'concessão sintética de teste','ti')", [randomUUID(), cliente, conta]);

  await comProvedor('ok', async () => {
    const ok = await perguntar(apiCom(pg, { cliente: { identityId: cliente } }), { rag_key: 'cliente', query: 'Qual o procedimento de ronda?' });
    assert.deepEqual(ok.corpo.sources.map((s) => s.title), ['Procedimento da Conta']);

    await pg.query('UPDATE client_access_grants SET revoked_at=NOW() WHERE identity_id=$1', [cliente]);
    const revogado = await perguntar(apiCom(pg, { cliente: { identityId: cliente } }), { rag_key: 'cliente', query: 'Qual o procedimento de ronda?' });
    assert.deepEqual(revogado.corpo.sources, [], 'vínculo revogado não recupera nada');
    assert.equal(revogado.corpo.reason, 'empty_scope');

    await pg.query('UPDATE client_access_grants SET revoked_at=NULL WHERE identity_id=$1', [cliente]);
    await pg.query("UPDATE client_accounts SET status='suspended' WHERE id=$1", [conta]);
    const suspensa = await perguntar(apiCom(pg, { cliente: { identityId: cliente } }), { rag_key: 'cliente', query: 'Qual o procedimento de ronda?' });
    assert.deepEqual(suspensa.corpo.sources, [], 'conta suspensa não recupera nada');
  });
});

// ---------------------------------------------------------------------------
// Flag E estado: a recuperação exige os dois
// ---------------------------------------------------------------------------

test('15/B: documento com flag ligada mas estado não publicado não é recuperado', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  await semear(pg, { ragKey: 'rh', aprovador, titulo: 'Rascunho de férias', conteudo: 'Rascunho interno sobre férias que ainda não foi publicado.', keywords: ['ferias'], status: 'rascunho' });
  await semear(pg, { ragKey: 'marcelo', aprovador, titulo: 'Arquivado da diretoria', conteudo: 'Documento arquivado da diretoria sobre férias.', keywords: ['ferias'], isAprovado: false, isPublicado: false, status: 'arquivado' });

  await comProvedor('ok', async (stub) => {
    const rh = await perguntar(apiCom(pg, { staff: { identityId: aprovador, role: 'rh' } }), { rag_key: 'rh', query: 'Como funcionam as férias?' });
    assert.equal(rh.status, 200);
    assert.deepEqual(rh.corpo.sources, [], 'rascunho com flag ligada não pode ser recuperado');
    assert.equal(stub.chamadas.length, 0);
  });
});

test('15/B: índice não ativo fecha o corpus inteiro, mesmo com documento publicado', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  await semear(pg, { ragKey: 'publico', aprovador, titulo: 'Serviço de portaria', conteudo: 'O serviço de portaria atende em regime integral conforme contrato.', keywords: ['portaria'], indexAtivo: false });

  await comProvedor('ok', async (stub) => {
    const res = await perguntar(apiCom(pg), { rag_key: 'publico', query: 'Qual o serviço de portaria?' });
    assert.deepEqual(res.corpo.sources, []);
    assert.equal(res.corpo.reason, 'empty_scope');
    assert.equal(stub.chamadas.length, 0);
  });
});

// ---------------------------------------------------------------------------
// Indisponibilidade, timeout e recusa — nunca resposta inventada
// ---------------------------------------------------------------------------

test('15: banco indisponível vira 503 rag_unavailable, sem inventar resposta', async (t) => {
  const api = createAiRagRealApi({
    pool: { query: async () => { throw new Error('conexão recusada (simulada)'); } },
    sameOrigin: () => true,
    readStaffSession: async () => ({ identityId: randomUUID(), role: 'rh' }),
    readClientSession: async () => null,
  });
  const res = await perguntar(api, { rag_key: 'rh', query: 'Como solicitar férias?' });
  assert.equal(res.status, 503);
  assert.equal(res.corpo.error, 'rag_unavailable');
  assert.equal('response' in res.corpo, false);
});

test('15: provedor recusando, respondendo vazio ou fora do ar não produz resposta', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  await semear(pg, { ragKey: 'rh', aprovador, titulo: 'Férias no RH', conteudo: 'Para solicitar férias use o fluxo de programação e confirme com a liderança.', keywords: ['ferias'] });

  for (const [comportamento, motivo] of [['http_500', 'ollama_http_error'], ['vazio', 'empty_response'], ['rejeita', 'ollama_timeout_or_offline']]) {
    await comProvedor(comportamento, async () => {
      const res = await perguntar(apiCom(pg, { staff: { identityId: aprovador, role: 'rh' } }), { rag_key: 'rh', query: 'Como solicitar férias?' });
      assert.equal(res.status, 503, `${comportamento} precisa falhar fechado`);
      assert.equal(res.corpo.reason, motivo);
      assert.equal('response' in res.corpo, false, `${comportamento} não pode devolver texto inventado`);
      assert.equal('sources' in res.corpo, false, 'falha não devolve fontes como se houvesse resposta');
    });
  }
});

test('15: timeout aborta a chamada e devolve 503 sanitizado', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  await semear(pg, { ragKey: 'rh', aprovador, titulo: 'Férias no RH', conteudo: 'Para solicitar férias use o fluxo de programação e confirme com a liderança.', keywords: ['ferias'] });

  await comProvedor('demora', async () => {
    const res = await perguntar(apiCom(pg, { staff: { identityId: aprovador, role: 'rh' } }), { rag_key: 'rh', query: 'Como solicitar férias?' });
    assert.equal(res.status, 503);
    assert.equal(res.corpo.reason, 'ollama_timeout_or_offline');
    // A mensagem do stub e qualquer traço de pilha não podem aparecer; a chave
    // `error` do contrato, sim, é esperada.
    const corpo = JSON.stringify(res.corpo);
    assert.doesNotMatch(corpo, /provedor offline|AbortError|at async|node:internal/, 'o erro interno não pode vazar');
  });
});

test('15: host de provedor fora de loopback é recusado (configuração não vira destino de rede)', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  await semear(pg, { ragKey: 'rh', aprovador, titulo: 'Férias no RH', conteudo: 'Para solicitar férias use o fluxo de programação e confirme com a liderança.', keywords: ['ferias'] });

  const original = globalThis.fetch;
  const antigos = { ENV: process.env.OLLAMA_ENABLED, URL: process.env.OLLAMA_BASE_URL };
  let chamou = 0;
  process.env.OLLAMA_ENABLED = 'true';
  process.env.OLLAMA_BASE_URL = 'http://10.0.0.5:11434';
  globalThis.fetch = async () => { chamou++; return new Response('{}'); };
  try {
    const res = await perguntar(apiCom(pg, { staff: { identityId: aprovador, role: 'rh' } }), { rag_key: 'rh', query: 'Como solicitar férias?' });
    assert.equal(res.status, 503);
    assert.equal(res.corpo.error, 'ollama_configuration_invalid');
    assert.equal(chamou, 0, 'nenhuma requisição pode sair para host fora de loopback');
  } finally {
    globalThis.fetch = original;
    if (antigos.ENV === undefined) delete process.env.OLLAMA_ENABLED; else process.env.OLLAMA_ENABLED = antigos.ENV;
    if (antigos.URL === undefined) delete process.env.OLLAMA_BASE_URL; else process.env.OLLAMA_BASE_URL = antigos.URL;
  }
});

test('15: corpus sem trecho relevante responde no_relevant_source e não chama o modelo', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  await semear(pg, { ragKey: 'rh', aprovador, titulo: 'Férias no RH', conteudo: 'Para solicitar férias use o fluxo de programação e confirme com a liderança.', keywords: ['ferias'] });

  await comProvedor('ok', async (stub) => {
    const res = await perguntar(apiCom(pg, { staff: { identityId: aprovador, role: 'rh' } }), { rag_key: 'rh', query: 'Qual o código do convênio odontológico?' });
    assert.equal(res.status, 200);
    assert.equal(res.corpo.reason, 'no_relevant_source');
    assert.deepEqual(res.corpo.sources, []);
    assert.equal(res.corpo.ollama_used, false);
    assert.equal(stub.chamadas.length, 0);
  });
});

// ---------------------------------------------------------------------------
// Contrato de entrada
// ---------------------------------------------------------------------------

test('15/B: escopo, método, origem e consulta inválidos são recusados antes do banco', async (t) => {
  const pg = await openDb(t);
  // Papel com acesso ao escopo `rh`: assim o 400 medido é da validação de
  // entrada, e não o 403 de escopo (que tem teste próprio).
  const api = apiCom(pg, { staff: { identityId: randomUUID(), role: 'rh' } });

  const escopo = await perguntar(api, { rag_key: 'diretoria', query: 'Como solicitar férias?' });
  assert.equal(escopo.status, 400);
  assert.equal(escopo.corpo.error, 'invalid_rag_key');

  const curta = await perguntar(api, { rag_key: 'rh', query: 'oi' });
  assert.equal(curta.status, 400);
  assert.equal(curta.corpo.error, 'invalid_query');

  const longa = await perguntar(api, { rag_key: 'rh', query: 'a'.repeat(501) });
  assert.equal(longa.status, 400);
  assert.equal(longa.corpo.error, 'invalid_query');

  const origem = await perguntar(api, { rag_key: 'rh', query: 'Como solicitar férias?', origin: false });
  assert.equal(origem.status, 403);
  assert.equal(origem.corpo.error, 'same_origin_required');
});

test('15/B: com o sameOrigin do servidor, origem cruzada é recusada e a mesma origem passa', async (t) => {
  const pg = await openDb(t);
  const aprovador = await identidade(pg);
  await semear(pg, { ragKey: 'rh', aprovador, titulo: 'Férias no RH', conteudo: 'Para solicitar férias use o fluxo de programação e confirme com a liderança.', keywords: ['ferias'] });

  const api = createAiRagRealApi({
    pool: poolOf(pg),
    sameOrigin: sameOriginDeServidor,
    readStaffSession: async () => ({ identityId: aprovador, role: 'rh' }),
    readClientSession: async () => null,
  });

  const cruzar = async (headers) => {
    const req = { method: 'POST', headers, async *[Symbol.asyncIterator]() { yield CORPO('rh', 'Como solicitar férias?'); } };
    const res = resposta();
    await api.ask(req, res);
    return res;
  };

  const cruzada = await cruzar({ origin: 'http://atacante.invalid', host: 'sistema.local' });
  assert.equal(cruzada.status, 403);
  assert.equal(cruzada.corpo.error, 'same_origin_required');

  const semOrigem = await cruzar({ host: 'sistema.local' });
  assert.equal(semOrigem.status, 403, 'POST sem Origin não passa');

  const semHost = await cruzar({ origin: 'http://sistema.local' });
  assert.equal(semHost.status, 403, 'sem Host não há como provar mesma origem');

  // Mesma origem com OLLAMA desligado: a barreira de origem é vencida e a
  // rota segue para a checagem seguinte (prova que o 403 acima é da origem).
  const antigo = process.env.OLLAMA_ENABLED;
  delete process.env.OLLAMA_ENABLED;
  try {
    const legitima = await cruzar({ origin: 'http://sistema.local', host: 'sistema.local' });
    assert.equal(legitima.status, 503);
    assert.equal(legitima.corpo.reason, 'ollama_disabled');
  } finally {
    if (antigo !== undefined) process.env.OLLAMA_ENABLED = antigo;
  }
});

test('15/B: a réplica do sameOrigin acompanha o server.mjs (guarda de deriva)', async () => {
  const fonte = await readFile(new URL('../server.mjs', import.meta.url), 'utf8');
  // Se alguma destas linhas mudar, a réplica acima deixa de representar o
  // servidor e este teste avisa antes de a suíte ficar verde por engano.
  assert.match(fonte, /if \(\["GET", "HEAD", "OPTIONS"\]\.includes\(req\.method \|\| "GET"\)\) return true;/);
  assert.match(fonte, /const expectedHost = String\(forwardedHost \|\| req\.headers\.host \|\| ""\)\.split\(","\)\[0\]\.trim\(\)\.toLowerCase\(\);/);
  assert.match(fonte, /return new URL\(origin\)\.host\.toLowerCase\(\) === expectedHost;/);
});
