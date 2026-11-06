#!/usr/bin/env node
/**
 * Fatia 17 — pré-validação operacional (somente leitura).
 *
 * Verifica, ANTES de subir o ambiente, o que o planilha de execução chama de
 * "pré-validação": configuração presente e coerente, migrações compatíveis,
 * diretórios privados, segredos presentes sem exibir valor e healthcheck
 * acessível. O objetivo é transformar um erro de configuração em mensagem
 * acionável, agora — em vez de descobrir no meio da operação.
 *
 * Regras de conduta deste script (o que ele NUNCA faz):
 *   * não imprime valor de segredo — só "presente/vazio/inválido" e o motivo;
 *   * não abre conexão com banco remoto, não envia e-mail, não faz requisição
 *     para fora de loopback;
 *   * não altera configuração, não cria/remove diretório fora do modo `--init`;
 *   * não substitui teste de restore, migração real nem healthcheck de
 *     produção. Ele diz "o que está configurado", não "o que funciona".
 *
 * Uso:
 *   node scripts/qa-preflight.mjs                 # perfil local (padrão)
 *   node scripts/qa-preflight.mjs --profile=producao
 *   node scripts/qa-preflight.mjs --json          # saída para máquina
 *   node scripts/qa-preflight.mjs --init          # cria diretórios privados ausentes
 *
 * Códigos de saída: 0 = pronto para o perfil; 1 = bloqueado por erro;
 * 2 = há avisos (nada impeditivo) — usar `--strict` para tratar aviso como erro.
 */
import { existsSync, mkdirSync, statSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
import path from 'node:path';

import { readMailTransportConfig, MAILER_STATE } from '../src/server/admin-mailer.mjs';

export const PERFIS = ['local', 'producao'];

/** Um achado é: severidade, chave estável, mensagem acionável. */
const erro = (codigo, mensagem) => ({ severidade: 'erro', codigo, mensagem });
const aviso = (codigo, mensagem) => ({ severidade: 'aviso', codigo, mensagem });
const ok = (codigo, mensagem) => ({ severidade: 'ok', codigo, mensagem });

const PLACEHOLDERS = new Set([
  'changeme', 'change-me', 'troque-me', 'altere-me', 'placeholder', 'senha', 'password',
  'secret', 'segredo', 'teste', 'test', 'dev', 'exemplo', 'example', 'admin',
]);

/** Segredo forte o bastante para a regra do código (>= 32 caracteres). */
function avaliarSegredoDeSessao(nome, env) {
  const valor = String(env[nome] ?? '');
  if (!valor) return erro(`${nome}_ausente`, `${nome} não está definido; sem ele a sessão não é emitida.`);
  if (valor.length < 32) {
    return erro(`${nome}_curto`, `${nome} tem ${valor.length} caracteres; o código exige ao menos 32.`);
  }
  // Placeholder detectado pelo prefixo: `change-me-change-me-…` repetido é
  // tão fraco quanto `change-me` e passaria do mínimo de 32 caracteres.
  const normalizado = valor.trim().toLowerCase();
  const parecePlaceholder = PLACEHOLDERS.has(normalizado)
    || /^(change-?me|troque-?me|altere-?me|segredo|senha|password|secret|example|exemplo|teste|test)/.test(normalizado);
  if (parecePlaceholder) {
    return erro(`${nome}_placeholder`, `${nome} parece um valor de exemplo ou repetição; gerar um segredo aleatório e guardá-lo fora do repositório.`);
  }
  return ok(`${nome}_ok`, `${nome} presente com ${valor.length} caracteres (valor não exibido).`);
}

/** CLIENT_MFA_ENCRYPTION_KEY precisa ser 32 bytes em base64url canônico. */
function avaliarChaveMfa(env) {
  const valor = String(env.CLIENT_MFA_ENCRYPTION_KEY ?? '');
  if (!valor) return erro('CLIENT_MFA_ENCRYPTION_KEY_ausente', 'CLIENT_MFA_ENCRYPTION_KEY vazia: MFA falha fechado, como o código exige.');
  let bytes;
  try {
    bytes = Buffer.from(valor, 'base64url');
  } catch {
    return erro('CLIENT_MFA_ENCRYPTION_KEY_invalida', 'CLIENT_MFA_ENCRYPTION_KEY não é base64url decodificável.');
  }
  if (bytes.length !== 32) {
    return erro('CLIENT_MFA_ENCRYPTION_KEY_tamanho', `CLIENT_MFA_ENCRYPTION_KEY decodifica para ${bytes.length} bytes; precisa de 32.`);
  }
  if (bytes.toString('base64url') !== valor) {
    return erro('CLIENT_MFA_ENCRYPTION_KEY_nao_canonica', 'CLIENT_MFA_ENCRYPTION_KEY não está em base64url canônico (o código compara a forma exata).');
  }
  return ok('CLIENT_MFA_ENCRYPTION_KEY_ok', 'CLIENT_MFA_ENCRYPTION_KEY presente com 32 bytes (valor não exibido).');
}

/** URL de banco: loopback é aceitável em local; em produção precisa ser explícita. */
function avaliarBanco(env, perfil) {
  const url = String(env.DATABASE_URL ?? '').trim();
  const achados = [];
  if (!url) {
    achados.push(erro('DATABASE_URL_ausente', 'DATABASE_URL vazia: a aplicação não tem banco configurado.'));
    return achados;
  }
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    achados.push(erro('DATABASE_URL_invalida', 'DATABASE_URL não é uma URL válida (formato esperado: postgres://usuario:senha@host:porta/banco).'));
    return achados;
  }
  if (!/^postgres(ql)?:$/.test(parsed.protocol)) {
    achados.push(erro('DATABASE_URL_protocolo', `DATABASE_URL usa protocolo "${parsed.protocol}"; o esperado é postgres:// ou postgresql://.`));
  }
  const loopback = new Set(['127.0.0.1', 'localhost', '::1', '[::1]']);
  if (perfil === 'producao' && loopback.has(parsed.hostname)) {
    achados.push(aviso('DATABASE_URL_loopback', 'DATABASE_URL aponta para loopback; em produção o banco costuma estar em host dedicado. Confirmar o destino aprovado.'));
  }
  if (perfil === 'local' && !loopback.has(parsed.hostname)) {
    achados.push(erro('DATABASE_URL_remota', 'DATABASE_URL aponta para host não-loopback em perfil local; os gates locais recusam e não devem tocar banco externo.'));
  }
  if (parsed.password && PLACEHOLDERS.has(parsed.password.toLowerCase())) {
    achados.push(erro('DATABASE_URL_senha_placeholder', 'A senha da DATABASE_URL parece placeholder.'));
  }
  if (!achados.length) achados.push(ok('DATABASE_URL_ok', `DATABASE_URL configurada para host ${parsed.hostname} (credenciais não exibidas).`));
  return achados;
}

/** Diretório privado: existe, é gravável e NÃO está dentro de `public/`. */
function avaliarDiretorioPrivado(nome, padrao, env, raiz, init) {
  const bruto = String(env[nome] ?? '').trim();
  const destino = bruto || padrao;
  const absoluto = path.isAbsolute(destino) ? destino : path.join(raiz, destino);
  const pastaPublica = path.join(raiz, 'public');
  if (absoluto === pastaPublica || absoluto.startsWith(pastaPublica + path.sep)) {
    return erro(`${nome}_em_public`, `${nome} aponta para dentro de public/: documento privado ficaria servido pela web.`);
  }
  if (!existsSync(absoluto)) {
    if (init) {
      try {
        // `recursive` cria a árvore necessária; o modo 0700 evita leitura por outros usuários.
        mkdirSync(absoluto, { recursive: true, mode: 0o700 });
        return ok(`${nome}_criado`, `${nome} não existia e foi criado com permissão restrita (${absoluto}).`);
      } catch (e) {
        return erro(`${nome}_criacao_falhou`, `${nome}: não foi possível criar ${absoluto}: ${e?.code ?? 'erro'}.`);
      }
    }
    return aviso(`${nome}_ausente`, `${nome} ainda não existe (${absoluto}). O servidor cria no primeiro uso; rode com --init para criar agora com permissão restrita.`);
  }
  try {
    const info = statSync(absoluto);
    if (!info.isDirectory()) return erro(`${nome}_nao_e_diretorio`, `${nome} aponta para um arquivo, não um diretório: ${absoluto}.`);
    // 0o077 = qualquer permissão para grupo/outros.
    if ((info.mode & 0o077) !== 0) {
      return aviso(`${nome}_permissivo`, `${nome} permite acesso de grupo/outros (modo ${(info.mode & 0o777).toString(8)}); documentos privados pedem 0700.`);
    }
  } catch (e) {
    return erro(`${nome}_inacessivel`, `${nome}: não foi possível inspecionar ${absoluto}: ${e?.code ?? 'erro'}.`);
  }
  return ok(`${nome}_ok`, `${nome} existe fora de public/ com permissão restrita.`);
}

/**
 * Migrações: o ledger precisa ser contínuo a partir de 001 e cada arquivo
 * precisa ter um nome no padrão. Isto NÃO aplica nada — só confere o que o
 * migrador encontraria.
 */
async function avaliarMigracoes(raiz) {
  const pasta = path.join(raiz, 'db/migrations');
  let arquivos;
  try {
    arquivos = (await readdir(pasta)).filter((n) => /^\d{3}-.+\.sql$/.test(n)).sort();
  } catch {
    return [erro('migracoes_pasta', 'db/migrations não encontrado; o migrador não teria o que aplicar.')];
  }
  if (!arquivos.length) return [erro('migracoes_vazias', 'db/migrations está vazio.')];
  const numeros = arquivos.map((n) => Number(n.slice(0, 3)));
  const achados = [];
  for (let esperado = 1; esperado <= numeros.length; esperado += 1) {
    if (numeros[esperado - 1] !== esperado) {
      achados.push(erro('migracoes_descontinuas', `ledger descontínuo: esperava a migração ${String(esperado).padStart(3, '0')} na posição ${esperado} e encontrei ${arquivos[esperado - 1]}.`));
      break;
    }
  }
  const duplicadas = numeros.filter((n, i) => i > 0 && n === numeros[i - 1]);
  if (duplicadas.length) achados.push(erro('migracoes_duplicadas', `numeração repetida no ledger: ${duplicadas.join(', ')}.`));
  if (!achados.length) achados.push(ok('migracoes_ok', `ledger contínuo: ${arquivos.length} migrações de 001 a ${arquivos.at(-1).slice(0, 3)} (nenhuma aplicada por este script).`));
  return achados;
}

/** SMTP: reutiliza o MESMO validador da fila administrativa (contrato único). */
function avaliarSmtp(env) {
  const leitura = readMailTransportConfig(env);
  if (leitura.state === MAILER_STATE.NOT_CONFIGURED) {
    return aviso('MAIL_nao_configurado', 'SMTP não configurado: lead e fila administrativa ficam sem transporte e a notificação vai para a caixa local (nunca "enviada").');
  }
  if (leitura.state === MAILER_STATE.INVALID) {
    return erro('MAIL_invalido', `Configuração SMTP recusada: ${leitura.problems.join(', ')}. Configuração parcial não vira transporte.`);
  }
  return ok('MAIL_ok', `SMTP configurado para ${leitura.config.host}:${leitura.config.port} (usuário e senha não exibidos).`);
}

/** Healthcheck: só loopback, prazo curto, e NÃO promove "ok" de produção. */
async function avaliarHealthcheck(env, fetchImpl) {
  const porta = String(env.PORT ?? '3000').trim() || '3000';
  const bind = String(env.BIND_HOST ?? '').trim() || '0.0.0.0';
  const host = bind === '0.0.0.0' || bind === '::' ? '127.0.0.1' : bind;
  const url = `http://${host}:${porta}/api/health/ready`;
  try {
    const controle = new AbortController();
    const prazo = setTimeout(() => controle.abort(), 3_000);
    const resposta = await fetchImpl(url, { signal: controle.signal });
    clearTimeout(prazo);
    if (resposta.ok) return ok('health_ok', `healthcheck de prontidão respondeu ${resposta.status} em ${url}.`);
    return aviso('health_status', `healthcheck respondeu ${resposta.status} em ${url}; conferir dependências antes de seguir.`);
  } catch {
    return aviso('health_indisponivel', `healthcheck não acessível em ${url}: o servidor não está no ar ou ainda inicializa. Pré-validação não exige servidor rodando.`);
  }
}

/**
 * Executa todas as verificações. `env`, `raiz` e `fetchImpl` são injetáveis
 * para que o teste possa medir cada regra sem tocar no ambiente real.
 */
export async function preflight({ env = process.env, perfil = 'local', raiz = process.cwd(), init = false, fetch: fetchImpl = globalThis.fetch } = {}) {
  if (!PERFIS.includes(perfil)) throw new Error(`perfil inválido: ${perfil}`);
  if (typeof fetchImpl !== 'function') throw new Error('fetch indisponível: use Node 22 ou injete um fetch');

  const achados = [];
  achados.push(...avaliarBanco(env, perfil));
  achados.push(avaliarSegredoDeSessao('SITE_ADMIN_SESSION_SECRET', env));
  achados.push(avaliarSegredoDeSessao('EMPLOYEE_SESSION_SECRET', env));
  achados.push(avaliarChaveMfa(env));

  // Modo de produção exige as duas flags de indexação coerentes; no local,
  // indexação ligada é risco de exposição do ambiente de teste.
  const envPublico = String(env.NEXT_PUBLIC_ENV ?? '').trim();
  const indexar = String(env.NEXT_PUBLIC_ALLOW_INDEX ?? '').trim();
  if (perfil === 'producao') {
    if (envPublico !== 'production') achados.push(erro('NEXT_PUBLIC_ENV', 'NEXT_PUBLIC_ENV precisa ser "production" no perfil de produção.'));
    else achados.push(ok('NEXT_PUBLIC_ENV_ok', 'NEXT_PUBLIC_ENV=production.'));
    if (indexar === 'true') achados.push(ok('indexacao_liberada', 'indexação liberada explicitamente (NEXT_PUBLIC_ALLOW_INDEX=true).'));
    else achados.push(aviso('indexacao_bloqueada', 'com NEXT_PUBLIC_ALLOW_INDEX diferente de "true" o site fica noindex — decisão de negócio, não defeito.'));
  } else if (indexar === 'true' && envPublico === 'production') {
    achados.push(erro('indexacao_em_local', 'perfil local com NEXT_PUBLIC_ENV=production e indexação ligada: risco de expor ambiente de teste aos buscadores.'));
  }

  // PUBLIC_BASE_URL: link absoluto e sem barra final, como o código espera.
  const base = String(env.PUBLIC_BASE_URL ?? '').trim();
  if (!base) {
    achados.push(perfil === 'producao'
      ? erro('PUBLIC_BASE_URL_ausente', 'PUBLIC_BASE_URL vazia: os links de convite/recuperação sairiam sem origem correta.')
      : aviso('PUBLIC_BASE_URL_ausente', 'PUBLIC_BASE_URL vazia; o fallback é localhost, inadequado para links externos.'));
  } else if (base.endsWith('/')) {
    achados.push(aviso('PUBLIC_BASE_URL_barra', 'PUBLIC_BASE_URL termina com "/"; o contrato pede sem barra final (os links concatenam caminho).'));
  } else if (perfil === 'producao' && !base.startsWith('https://')) {
    achados.push(erro('PUBLIC_BASE_URL_https', 'PUBLIC_BASE_URL em produção precisa ser https://.'));
  } else {
    achados.push(ok('PUBLIC_BASE_URL_ok', `PUBLIC_BASE_URL definida (${base}).`));
  }

  achados.push(avaliarSmtp(env));

  // Em produção, o bootstrap legado por token não deve estar ativo.
  const legado = ['SITE_ADMIN_LEGACY_TOKENS', 'SITE_ADMIN_TOKEN_MARCELO', 'SITE_ADMIN_TOKEN_TI']
    .filter((nome) => String(env[nome] ?? '').trim().length > 0);
  if (legado.length) {
    achados.push(perfil === 'producao'
      ? erro('bootstrap_legado_ativo', `Bootstrap legado ativo em produção (${legado.join(', ')}): usar identidade individual.`)
      : aviso('bootstrap_legado_ativo', `Bootstrap legado ativo (${legado.join(', ')}); aceitável em demo local, não em produção.`));
  } else {
    achados.push(ok('bootstrap_legado_ok', 'Bootstrap legado desativado (nenhum token fixo definido).'));
  }

  // BIND_HOST exposto: decisão consciente, nunca fallback silencioso.
  const bindHost = String(env.BIND_HOST ?? '').trim();
  if (!bindHost) {
    achados.push(aviso('BIND_HOST_ausente', 'BIND_HOST não definido: o servidor usa 0.0.0.0. Restringir por configuração, não por dependência do padrão.'));
  } else if (bindHost === '0.0.0.0' && perfil === 'producao') {
    achados.push(aviso('BIND_HOST_aberto', 'BIND_HOST=0.0.0.0 em produção: aceitável só atrás de proxy/firewall aprovado.'));
  } else {
    achados.push(ok('BIND_HOST_ok', `BIND_HOST definido (${bindHost}).`));
  }

  const docsPadrao = path.join('.data', 'documents');
  const empPadrao = path.join('.data', 'employee-documents');
  achados.push((await avaliarDiretorioPrivado('CLIENT_DOCS_DIR', docsPadrao, env, raiz, init)));
  achados.push((await avaliarDiretorioPrivado('EMPLOYEE_DOCS_DIR', empPadrao, env, raiz, init)));

  achados.push(...(await avaliarMigracoes(raiz)));
  achados.push(await avaliarHealthcheck(env, fetchImpl));

  const erros = achados.filter((a) => a.severidade === 'erro');
  const avisos = achados.filter((a) => a.severidade === 'aviso');
  return {
    schema: 'qa-preflight/1',
    perfil,
    // Sem data: o resultado precisa ser comparável entre execuções.
    resumo: { erros: erros.length, avisos: avisos.length, ok: achados.length - erros.length - avisos.length },
    achados,
  };
}

function imprimir(relatorio, strict) {
  const simbolo = { ok: 'OK  ', aviso: 'AVISO', erro: 'ERRO' };
  for (const achado of relatorio.achados) {
    console.log(`${simbolo[achado.severidade]} ${achado.codigo}: ${achado.mensagem}`);
  }
  const { erros, avisos, ok: totalOk } = relatorio.resumo;
  console.log(`\nperfil=${relatorio.perfil} · ${totalOk} ok · ${avisos} aviso(s) · ${erros} erro(s)`);
  if (erros) console.log('Resultado: BLOQUEADO. Corrija os erros acima antes de seguir.');
  else if (avisos && strict) console.log('Resultado: BLOQUEADO por --strict com avisos pendentes.');
  else if (avisos) console.log('Resultado: liberado com avisos — cada aviso é uma decisão a registrar.');
  else console.log('Resultado: pronto para o perfil. Isto NÃO é teste de restore, migração real nem aceite.');
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const arg = (nome) => process.argv.find((a) => a.startsWith(`--${nome}=`))?.split('=')[1];
  const perfil = arg('profile') ?? 'local';
  const strict = process.argv.includes('--strict');
  const relatorio = await preflight({ perfil, init: process.argv.includes('--init') });
  if (process.argv.includes('--json')) console.log(JSON.stringify(relatorio, null, 1));
  else imprimir(relatorio, strict);
  process.exit(relatorio.resumo.erros > 0 || (strict && relatorio.resumo.avisos > 0) ? 1 : 0);
}
