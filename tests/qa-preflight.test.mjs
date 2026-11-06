import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, chmod, rm, writeFile, readFile } from 'node:fs/promises';
import { existsSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';

import { preflight, PERFIS } from '../scripts/qa-preflight.mjs';

// Fatia 17 — guarda da pré-validação operacional.
//
// O verificador precisa ser útil justamente quando o ambiente está errado,
// então cada regra é medida com um ambiente SINTÉTICO construído no teste:
// diretório temporário, variáveis inventadas, `fetch` injetado. Nada toca
// banco, rede externa, e-mail ou configuração da máquina.
//
// O que se prova aqui:
//   * ausência, tamanho, placeholder e forma canônica dos segredos;
//   * URL de banco inválida, protocolo errado, host remoto em perfil local;
//   * diretório privado dentro de `public/`, ausente, permissivo e o `--init`;
//   * ledger de migrações contínuo, descontínuo e duplicado;
//   * SMTP ausente/inválido/válido usando o MESMO validador da fila;
//   * healthcheck ok, não-ok e indisponível;
//   * NENHUM valor sensível na saída (nem no texto, nem no JSON).

const raizDoRepo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/** Ambiente sintético completo e válido para o perfil local. */
function envValido(raiz, extras = {}) {
  const chaveMfa = randomBytes(32).toString('base64url');
  return {
    DATABASE_URL: 'postgres://usuario:senha-forte-do-teste@127.0.0.1:5432/seg_qa',
    SITE_ADMIN_SESSION_SECRET: 'a'.repeat(40),
    EMPLOYEE_SESSION_SECRET: 'b'.repeat(40),
    CLIENT_MFA_ENCRYPTION_KEY: chaveMfa,
    PUBLIC_BASE_URL: 'http://localhost:3000',
    NEXT_PUBLIC_ENV: 'beta',
    NEXT_PUBLIC_ALLOW_INDEX: 'false',
    BIND_HOST: '127.0.0.1',
    PORT: '3000',
    CLIENT_DOCS_DIR: path.join(raiz, 'docs-privados'),
    EMPLOYEE_DOCS_DIR: path.join(raiz, 'docs-funcionario'),
    ...extras,
  };
}

const achado = (relatorio, codigo) => relatorio.achados.find((a) => a.codigo === codigo);
const temErro = (relatorio) => relatorio.achados.some((a) => a.severidade === 'erro');

/** Raiz descartável com `db/migrations` contínuo e `public/`. */
async function raizTemporaria(t, { migracoes = 3 } = {}) {
  const raiz = await mkdtemp(path.join(tmpdir(), 'seg-preflight-'));
  t.after(() => rm(raiz, { recursive: true, force: true }));
  await mkdir(path.join(raiz, 'db/migrations'), { recursive: true });
  await mkdir(path.join(raiz, 'public'), { recursive: true });
  for (let i = 1; i <= migracoes; i += 1) {
    const nome = `${String(i).padStart(3, '0')}-teste-${i}.sql`;
    await writeFile(path.join(raiz, 'db/migrations', nome), '-- sintético\n');
  }
  return raiz;
}

const fetchIndisponivel = async () => { throw new Error('offline'); };
const fetchOk = async () => ({ ok: true, status: 200 });
const fetchErro = async () => ({ ok: false, status: 503 });

test('17: ambiente local completo e coerente é liberado sem erro', async (t) => {
  const raiz = await raizTemporaria(t);
  const relatorio = await preflight({ env: envValido(raiz), perfil: 'local', raiz, fetch: fetchOk });
  assert.equal(relatorio.resumo.erros, 0, JSON.stringify(relatorio.achados.filter((a) => a.severidade === 'erro')));
  assert.equal(achado(relatorio, 'DATABASE_URL_ok').severidade, 'ok');
  assert.equal(achado(relatorio, 'migracoes_ok').severidade, 'ok');
  assert.equal(achado(relatorio, 'health_ok').severidade, 'ok');
});

test('17: segredos — ausente, curto, placeholder e chave MFA não canônica viram erro', async (t) => {
  const raiz = await raizTemporaria(t);
  const casos = [
    [{ SITE_ADMIN_SESSION_SECRET: '' }, 'SITE_ADMIN_SESSION_SECRET_ausente'],
    [{ SITE_ADMIN_SESSION_SECRET: 'curto' }, 'SITE_ADMIN_SESSION_SECRET_curto'],
    // 33 caracteres (passa do mínimo) mas é literalmente um valor de exemplo.
    [{ SITE_ADMIN_SESSION_SECRET: 'change-me-'.repeat(4) }, 'SITE_ADMIN_SESSION_SECRET_placeholder'],
    [{ EMPLOYEE_SESSION_SECRET: '' }, 'EMPLOYEE_SESSION_SECRET_ausente'],
    [{ EMPLOYEE_SESSION_SECRET: 'x'.repeat(31) }, 'EMPLOYEE_SESSION_SECRET_curto'],
    [{ CLIENT_MFA_ENCRYPTION_KEY: '' }, 'CLIENT_MFA_ENCRYPTION_KEY_ausente'],
    [{ CLIENT_MFA_ENCRYPTION_KEY: randomBytes(16).toString('base64url') }, 'CLIENT_MFA_ENCRYPTION_KEY_tamanho'],
    // 32 bytes em hex: 64 caracteres, decodificável como base64url, mas com 48 bytes.
    [{ CLIENT_MFA_ENCRYPTION_KEY: randomBytes(32).toString('hex') }, 'CLIENT_MFA_ENCRYPTION_KEY_tamanho'],
  ];
  for (const [override, codigo] of casos) {
    const relatorio = await preflight({ env: envValido(raiz, override), perfil: 'local', raiz, fetch: fetchOk });
    const encontrado = achado(relatorio, codigo);
    assert.ok(encontrado, `esperava ${codigo} para ${JSON.stringify(override).slice(0, 90)}`);
    assert.equal(encontrado.severidade, 'erro', `${codigo} precisa bloquear`);
  }
});

test('17: segredos nunca aparecem na saída, nem no texto nem no JSON', async (t) => {
  const raiz = await raizTemporaria(t);
  const env = envValido(raiz, {
    SITE_ADMIN_SESSION_SECRET: 'SEGREDO-STAFF-NAO-DEVE-VAZAR-1234567890',
    EMPLOYEE_SESSION_SECRET: 'SEGREDO-FUNCIONARIO-NAO-DEVE-VAZAR-123456',
    DATABASE_URL: 'postgres://usuario:SENHA-DO-BANCO-NAO-DEVE-VAZAR@127.0.0.1:5432/seg_qa',
    MAIL_HOST: 'smtp.example.invalid',
    MAIL_FROM: 'avisos@gruposeg.example',
    MAIL_USER: 'USUARIO-SMTP-NAO-DEVE-VAZAR',
    MAIL_PASSWORD: 'SENHA-SMTP-NAO-DEVE-VAZAR',
  });
  const relatorio = await preflight({ env, perfil: 'local', raiz, fetch: fetchOk });
  const saida = JSON.stringify(relatorio);
  for (const segredo of [
    'SEGREDO-STAFF-NAO-DEVE-VAZAR', 'SEGREDO-FUNCIONARIO-NAO-DEVE-VAZAR',
    'SENHA-DO-BANCO-NAO-DE-VAZAR', 'USUARIO-SMTP-NAO-DEVE-VAZAR', 'SENHA-SMTP-NAO-DE-VAZAR',
    env.CLIENT_MFA_ENCRYPTION_KEY,
  ]) {
    assert.equal(saida.includes(segredo), false, `o relatório não pode conter ${segredo.slice(0, 12)}…`);
  }
});

test('17: banco — ausente, URL inválida, protocolo errado e host remoto em local', async (t) => {
  const raiz = await raizTemporaria(t);
  const casos = [
    [{ DATABASE_URL: '' }, 'DATABASE_URL_ausente'],
    [{ DATABASE_URL: 'isto-nao-e-url' }, 'DATABASE_URL_invalida'],
    [{ DATABASE_URL: 'mysql://u:p@127.0.0.1:3306/x' }, 'DATABASE_URL_protocolo'],
    [{ DATABASE_URL: 'postgres://u:senha@db.exemplo.invalid:5432/x' }, 'DATABASE_URL_remota'],
    [{ DATABASE_URL: 'postgres://u:senha-forte-do-teste@127.0.0.1:5432/x' }, 'controle_positivo'],
  ];
  for (const [override, codigo] of casos.slice(0, 4)) {
    const relatorio = await preflight({ env: envValido(raiz, override), perfil: 'local', raiz, fetch: fetchOk });
    assert.ok(achado(relatorio, codigo), `esperava ${codigo}`);
    assert.equal(achado(relatorio, codigo).severidade, 'erro');
  }
  // O último caso é o controle positivo: URL loopback correta não gera erro.
  const controle = await preflight({ env: envValido(raiz, casos[4][0]), perfil: 'local', raiz, fetch: fetchOk });
  assert.equal(temErro(controle), false, 'URL postgres de loopback com senha comum precisa passar');
});

test('17: diretório privado dentro de public/ é erro; ausente é aviso; --init cria 0700', async (t) => {
  const raiz = await raizTemporaria(t);

  const dentroDePublic = await preflight({
    env: envValido(raiz, { CLIENT_DOCS_DIR: path.join(raiz, 'public', 'documentos') }),
    perfil: 'local', raiz, fetch: fetchOk,
  });
  assert.equal(achado(dentroDePublic, 'CLIENT_DOCS_DIR_em_public').severidade, 'erro',
    'documento privado em public/ ficaria servido pela web');

  const ausente = await preflight({ env: envValido(raiz), perfil: 'local', raiz, fetch: fetchOk });
  assert.equal(achado(ausente, 'CLIENT_DOCS_DIR_ausente').severidade, 'aviso');

  const criado = await preflight({ env: envValido(raiz), perfil: 'local', raiz, init: true, fetch: fetchOk });
  assert.equal(achado(criado, 'CLIENT_DOCS_DIR_criado').severidade, 'ok');
  const destino = path.join(raiz, 'docs-privados');
  assert.equal(existsSync(destino), true);
  assert.equal(statSync(destino).mode & 0o077, 0, 'o diretório criado precisa ser 0700');
});

test('17: diretório com permissão de grupo/outros gera aviso, não silêncio', async (t) => {
  const raiz = await raizTemporaria(t);
  const destino = path.join(raiz, 'docs-privados');
  await mkdir(destino, { recursive: true });
  await chmod(destino, 0o755);
  const relatorio = await preflight({ env: envValido(raiz), perfil: 'local', raiz, fetch: fetchOk });
  assert.equal(achado(relatorio, 'CLIENT_DOCS_DIR_permissivo').severidade, 'aviso',
    'permissão aberta em documento privado precisa aparecer');
});

test('17: ledger de migrações — contínuo passa; buraco e duplicidade bloqueiam', async (t) => {
  const raiz = await raizTemporaria(t, { migracoes: 5 });
  const ok = await preflight({ env: envValido(raiz), perfil: 'local', raiz, fetch: fetchOk });
  assert.match(achado(ok, 'migracoes_ok').mensagem, /001 a 005/);

  await rm(path.join(raiz, 'db/migrations/003-teste-3.sql'));
  const comBuraco = await preflight({ env: envValido(raiz), perfil: 'local', raiz, fetch: fetchOk });
  assert.equal(achado(comBuraco, 'migracoes_descontinuas').severidade, 'erro');

  await writeFile(path.join(raiz, 'db/migrations/004-teste-4.sql'), '-- sintético\n');
  const duplicada = await preflight({ env: envValido(raiz), perfil: 'local', raiz, fetch: fetchOk });
  assert.ok(achado(duplicada, 'migracoes_duplicadas') || achado(duplicada, 'migracoes_descontinuas'));
});

test('17: SMTP usa o mesmo validador da fila — ausente é aviso, parcial é erro', async (t) => {
  const raiz = await raizTemporaria(t);

  const semSmtp = await preflight({ env: envValido(raiz), perfil: 'local', raiz, fetch: fetchOk });
  assert.equal(achado(semSmtp, 'MAIL_nao_configurado').severidade, 'aviso',
    'sem SMTP a fila vai para a caixa local; não é erro de pré-validação');

  const parcial = await preflight({
    env: envValido(raiz, { MAIL_HOST: 'smtp.example.invalid' }), perfil: 'local', raiz, fetch: fetchOk,
  });
  assert.equal(achado(parcial, 'MAIL_invalido').severidade, 'erro');
  assert.match(achado(parcial, 'MAIL_invalido').mensagem, /incomplete_mail_configuration/);

  const completo = await preflight({
    env: envValido(raiz, { MAIL_HOST: 'smtp.example.invalid', MAIL_PORT: '587', MAIL_FROM: 'avisos@gruposeg.example' }),
    perfil: 'local', raiz, fetch: fetchOk,
  });
  assert.equal(achado(completo, 'MAIL_ok').severidade, 'ok');
});

test('17: perfil de produção exige HTTPS, NEXT_PUBLIC_ENV e recusa bootstrap legado', async (t) => {
  const raiz = await raizTemporaria(t);
  const base = {
    NEXT_PUBLIC_ENV: 'production',
    PUBLIC_BASE_URL: 'http://seg.example.invalid',
    DATABASE_URL: 'postgres://u:senha@db.example.invalid:5432/x',
  };
  const relatorio = await preflight({ env: envValido(raiz, base), perfil: 'producao', raiz, fetch: fetchOk });
  assert.equal(achado(relatorio, 'PUBLIC_BASE_URL_https').severidade, 'erro');

  const comSegredoLegado = await preflight({
    env: envValido(raiz, { ...base, PUBLIC_BASE_URL: 'https://seg.example.invalid', SITE_ADMIN_TOKEN_TI: 'token-fixo' }),
    perfil: 'producao', raiz, fetch: fetchOk,
  });
  assert.equal(achado(comSegredoLegado, 'bootstrap_legado_ativo').severidade, 'erro');

  const envErrado = await preflight({
    env: envValido(raiz, { ...base, PUBLIC_BASE_URL: 'https://seg.example.invalid', NEXT_PUBLIC_ENV: 'beta' }),
    perfil: 'producao', raiz, fetch: fetchOk,
  });
  assert.equal(achado(envErrado, 'NEXT_PUBLIC_ENV').severidade, 'erro');
});

test('17: indexação ligada em perfil local é erro de exposição', async (t) => {
  const raiz = await raizTemporaria(t);
  const relatorio = await preflight({
    env: envValido(raiz, { NEXT_PUBLIC_ENV: 'production', NEXT_PUBLIC_ALLOW_INDEX: 'true' }),
    perfil: 'local', raiz, fetch: fetchOk,
  });
  assert.equal(achado(relatorio, 'indexacao_em_local').severidade, 'erro');
});

test('17: healthcheck — 200 é ok, 503 é aviso, indisponível é aviso (não erro)', async (t) => {
  const raiz = await raizTemporaria(t);
  const ok = await preflight({ env: envValido(raiz), perfil: 'local', raiz, fetch: fetchOk });
  assert.equal(achado(ok, 'health_ok').severidade, 'ok');

  const degradado = await preflight({ env: envValido(raiz), perfil: 'local', raiz, fetch: fetchErro });
  assert.equal(achado(degradado, 'health_status').severidade, 'aviso');

  const fora = await preflight({ env: envValido(raiz), perfil: 'local', raiz, fetch: fetchIndisponivel });
  assert.equal(achado(fora, 'health_indisponivel').severidade, 'aviso');
  assert.equal(temErro(fora), false, 'servidor fora do ar não pode bloquear a pré-validação');
});

test('17: a pré-validação nunca toca o ambiente real do repositório', async (t) => {
  const raiz = await raizTemporaria(t);
  const antes = await readFile(path.join(raizDoRepo, 'package.json'), 'utf8');
  await preflight({ env: envValido(raiz), perfil: 'local', raiz, init: true, fetch: fetchOk });
  const depois = await readFile(path.join(raizDoRepo, 'package.json'), 'utf8');
  assert.equal(antes, depois, 'a verificação é somente leitura sobre o repositório');
});

test('17: o CLI respeita o contrato de exit code (bloqueado, avisos e --strict)', async (t) => {
  const raiz = await raizTemporaria(t);
  const base = { ...process.env };
  const limpo = { PATH: base.PATH, HOME: base.HOME, NODE_ENV: 'test' };
  const rodar = (env, args = []) => {
    try {
      const saida = execFileSync(process.execPath, [path.join(raizDoRepo, 'scripts/qa-preflight.mjs'), ...args], {
        cwd: raiz, env: { ...limpo, ...env }, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
      });
      return { codigo: 0, saida };
    } catch (error) {
      return { codigo: error.status, saida: `${error.stdout ?? ''}${error.stderr ?? ''}` };
    }
  };

  // Ambiente vazio: bloqueado (exit 1) e com diagnóstico acionável.
  const bloqueado = rodar({});
  assert.equal(bloqueado.codigo, 1);
  assert.match(bloqueado.saida, /BLOQUEADO/);
  assert.match(bloqueado.saida, /DATABASE_URL_ausente/);

  // Ambiente completo: liberado, mas com avisos (SMTP ausente, diretório, health).
  const completo = rodar(envValido(raiz));
  assert.equal(completo.codigo, 0, completo.saida);
  assert.match(completo.saida, /liberado com avisos/);

  // --strict transforma aviso em bloqueio: a decisão é de quem opera.
  const estrito = rodar(envValido(raiz), ['--strict']);
  assert.equal(estrito.codigo, 1);
  assert.match(estrito.saida, /--strict/);

  // --json entrega o mesmo relatório para máquina.
  const json = rodar(envValido(raiz), ['--json']);
  const relatorio = JSON.parse(json.saida);
  assert.equal(relatorio.schema, 'qa-preflight/1');
  assert.equal(relatorio.perfil, 'local');
  assert.ok(Array.isArray(relatorio.achados));
});

test('17: perfis são explícitos — nada de perfil implícito', () => {
  assert.deepEqual([...PERFIS], ['local', 'producao']);
});
