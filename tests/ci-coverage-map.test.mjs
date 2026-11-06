import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { construirMapa, MAPA } from '../scripts/ci-coverage-map.mjs';

// Fatia 06B — guarda do mapa de CI × cobertura.
//
// O plano de execução (item 06) pede "mapa reproduzível; nenhum skip silencioso
// nem teste obrigatório removido; não confundir ausência literal com
// orfandade". Esta guarda cobre as três coisas:
//
//   1. o mapa versionado confere com workflows + package.json + tests/ — se
//      alguém mexer em workflow e esquecer de regenerar, isto reprova;
//   2. os pisos são MEDIDOS, não frouxos: o número de testes cobertos não pode
//      cair. Piso frouxo ("mais de 100") é o que deixou passar gates órfãos
//      antes;
//   3. a lista de órfãos é explícita e cada item tem razão escrita. Se um novo
//      órfão aparecer, o teste falha até alguém decidir (ligar ou documentar).
//
// O que esta guarda NÃO faz: declarar que o CI passou, promover requisito,
// registrar aceite humano. Ela prova o que está escrito, não o que rodou.

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

// Medido em 06/11/2026 na base `d2674a25` + fatia 07. Ao acrescentar teste ou
// workflow, suba o piso na mesma PR — o número é o contrato, não uma estimativa.
const PISO = {
  workflows: 60,
  testes_no_disco: 253,
  testes_cobertos_por_workflow: 251,
  testes_cobertos_pelo_test_unit: 185,
  runners_em_scripts: 116,
};

// Órfãos reais, com a razão de cada um. Nenhum é "provável esquecimento": os
// dois testes precisam de PostgreSQL real e ficam fora do CI por decisão
// registrada; nenhum deles é executado por `npm test`.
const ORFAOS_TESTES = {
  'tests/lead-flow.integration.test.mjs':
    'gate HTTP de captação de lead exige RUN_DATABASE_INTEGRATION=1 + DATABASE_URL de PostgreSQL local; '
    + 'dentro do `npm test` ele viraria skip — e skip silencioso é o que a fatia 06 não aceita. '
    + 'Executado por `npm run test:integration` sob demanda; ligar no ci.yml em fatia própria.',
  'tests/ux-pro-09e-7-text-overflow.test.mjs':
    'guarda da captura opt-in UX-PRO-09E-7; roda em `npm run test:ux-pro-09e-7`, sem workflow. '
    + 'É candidato direto ao `test:unit` (não precisa de banco nem navegador), mas mudar o `test:unit` '
    + 'é decisão de escopo — registrado, não alterado.',
};

// Scripts de teste do package.json sem chamada em workflow. Cada um tem razão.
const ORFAOS_SCRIPTS = {
  'qa:ux-pro-04-pendencias-browser': 'captura de evidência por navegador, opt-in e manual',
  'qa:ux-pro-04-reports-browser': 'captura de evidência por navegador, opt-in e manual',
  'test:integration': 'exige PostgreSQL local e opt-in; leva lead-flow e companhia',
  'test:staff-auth:pg': 'gate L01 em PostgreSQL descartável; roda sob demanda (CI não o chama)',
  'test:ux-pro-04-reports': 'alias local do focal, já coberto pelo `test:unit`',
  'test:ux-pro-09e-7': 'guarda focal sem workflow (ver ORFAOS_TESTES)',
  'test:ux-pro-09e-pu4': 'forma local do step de CI, que chama a variante `:browser`',
  'test:ux-pro-09e-pu6': 'focal já coberto pelo `test:unit`; a forma npm não é chamada',
  'test:ux-pro-10b-keyboard': 'forma local do focal, já coberto pelo `test:unit`',
  'qa:preflight': 'verificação de configuração do destino; roda antes de instalar/subir, quando houver destino aprovado',
};

const mapaVersionado = async () => JSON.parse(await readFile(path.join(root, MAPA), 'utf8'));

test('06B: o mapa versionado confere com workflows, package.json e tests/', async () => {
  const atual = await construirMapa();
  const versionado = await mapaVersionado();
  assert.deepEqual(versionado, atual,
    'o mapa de cobertura está desatualizado: rode `node scripts/ci-coverage-map.mjs` e versione o resultado');
});

test('06B: os pisos de cobertura são medidos e não podem cair', async () => {
  const mapa = await mapaVersionado();
  for (const [chave, piso] of Object.entries(PISO)) {
    assert.ok(mapa.totais[chave] >= piso,
      `${chave} caiu para ${mapa.totais[chave]}; o piso medido é ${piso}. `
      + 'Se a queda é intencional, o piso muda na mesma PR com justificativa — nunca em silêncio.');
  }
  // O piso de testes cobertos precisa acompanhar o disco: um teste novo que
  // ninguém executa é exatamente o que este mapa existe para mostrar.
  assert.equal(mapa.totais.testes_no_disco, mapa.totais.testes_cobertos_por_workflow + mapa.testes_fora_de_workflow_e_test_unit.length,
    'todo teste do disco precisa estar coberto por workflow/`npm test` OU listado como órfão');
});

test('06B: cada teste órfão tem razão escrita e nenhum é silencioso', async () => {
  const mapa = await mapaVersionado();
  assert.deepEqual([...mapa.testes_fora_de_workflow_e_test_unit].sort(), Object.keys(ORFAOS_TESTES).sort(),
    'lista de testes sem cobertura mudou: ajuste o código ou documente a decisão aqui');
  for (const [teste, razao] of Object.entries(ORFAOS_TESTES)) {
    assert.ok(razao.length >= 40, `${teste}: a razão precisa explicar a decisão, não repetir o nome`);
  }
});

test('06B: cada script de teste sem workflow tem razão escrita', async () => {
  const mapa = await mapaVersionado();
  assert.deepEqual([...mapa.scripts_de_teste_sem_workflow].sort(), Object.keys(ORFAOS_SCRIPTS).sort(),
    'lista de scripts npm sem workflow mudou: ligue no CI ou documente a decisão aqui');
});

test('06B: o loop dinâmico do workflow de backup não é confundido com orfandade', async () => {
  const mapa = await mapaVersionado();
  // As oito variantes são executadas por `npm run "$gate"` a partir de um `for`;
  // uma varredura literal não vê esses nomes e as chamaria de órfãs.
  const backup = mapa.workflows.find((w) => w.arquivo === 'backup-restore-delivery.yml');
  assert.ok(backup, 'o workflow de backup precisa estar no mapa');
  assert.equal(backup.scripts_via_loop.length, 8,
    `esperava as 8 variantes executadas por loop, veio ${JSON.stringify(backup.scripts_via_loop)}`);
  for (const gate of backup.scripts_via_loop) {
    assert.match(gate, /^test:backup-restore:pg/, `${gate} não parece variante de backup/restore`);
    assert.ok(backup.scripts_efetivos.includes(gate),
      `${gate} é executado pelo loop e precisa estar entre os scripts efetivos do workflow`);
  }
  for (const gate of backup.scripts_via_loop) {
    assert.equal(mapa.scripts_de_teste_sem_workflow.includes(gate), false,
      `${gate} roda no CI via loop; não pode ser listado como script sem workflow`);
  }
});

test('06B: a cadeia `npm test` → `test:unit` conta como cobertura de CI', async () => {
  const mapa = await mapaVersionado();
  const ci = mapa.workflows.find((w) => w.arquivo === 'ci.yml');
  assert.ok(ci.scripts_efetivos.includes('test'), 'ci.yml roda `npm test`, então o script `test` é efetivo');
  assert.ok(ci.scripts_efetivos.includes('test:unit'), '`npm test` expande para `test:unit`');
  // Se a expansão se perdesse, 183 testes apareceriam como órfãos por engano.
  assert.ok(mapa.totais.testes_cobertos_via_test_unit >= 180,
    `esperava ao menos 180 testes cobertos via npm test, veio ${mapa.totais.testes_cobertos_via_test_unit}`);
  const exemplo = mapa.cobertura_testes.find((t) => t.teste === 'tests/package-artifacts.test.mjs');
  assert.ok(exemplo.workflows_via_test_unit.includes('ci.yml'),
    'um teste do test:unit precisa aparecer como coberto pelo ci.yml via npm test');
});

test('06B: a suíte de integração executada por runner conta como coberta', async () => {
  const mapa = await mapaVersionado();
  // `test:admin-entry:pg` → scripts/qa-admin-entry-postgres.mjs → monta o nome
  // do arquivo por template. Sem resolver essa cadeia, a suíte pareceria órfã.
  const entrada = mapa.cobertura_testes.find((t) => t.teste === 'tests/admin-entry.integration.test.mjs');
  assert.ok(entrada.workflows.length > 0,
    'admin-entry.integration roda dentro de um runner chamado pelo CI e não pode ser órfão');
  const runner = mapa.cobertura_runners.find((r) => r.runner === 'scripts/qa-admin-entry-postgres.mjs');
  assert.ok(runner.workflows.length > 0, 'o runner precisa aparecer em ao menos um workflow');
});

test('06B: o mapa não depende de data nem de hora (é reprodutível)', async () => {
  const primeiro = await construirMapa();
  const segundo = await construirMapa();
  assert.deepEqual(primeiro, segundo, 'duas execuções seguidas precisam devolver o mesmo mapa');
  assert.equal(Object.keys(primeiro).includes('gerado_em'), false,
    'carimbo de data quebraria o `--check` a cada execução');
});
