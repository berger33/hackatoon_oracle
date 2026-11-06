#!/usr/bin/env node
/**
 * Fatia 06B — mapa reproduzível de CI × cobertura.
 *
 * Propósito (plano de execução, item 06): mapear
 * `npm scripts → arquivos → cenários → workflows` e dizer, com número medido,
 * o que o CI executa, o que ele executa por caminho indireto e o que realmente
 * não é executado por workflow nenhum.
 *
 * Por que um gerador e não um documento escrito à mão: um mapa digitado
 * envelhece na primeira PR. Este lê os workflows e o `package.json` como texto
 * e materializa o resultado em JSON — o teste `tests/ci-coverage-map.test.mjs`
 * regenera em memória e compara, então o mapa versionado nunca mente.
 *
 * Distinções que o mapa faz questão de registrar, porque confundi-las é o erro
 * que o plano nomeia:
 *
 *   1. **Menção literal** — `npm run X` ou `node scripts/Y.mjs` escrito no YAML.
 *   2. **Execução indireta** — `npm run X` cujo comando expande para outro
 *      script (ex.: `npm test` → `test:unit`), ou um `test:unit` que já roda o
 *      arquivo.
 *   3. **Loop dinâmico** — o workflow executa `npm run "$gate"` com os nomes
 *      vindo de uma lista de `for`. A varredura literal NÃO vê esses nomes; o
 *      mapa os resolve pela lista, senão o gate de backup (8 variantes) seria
 *      declarado órfão por engano.
 *   4. **Sem workflow** — o arquivo/script não é executado por nenhum workflow.
 *      Isso não é automaticamente um defeito: pode ser utilitário local.
 *
 * O que este script NÃO faz: editar workflow, remover teste, marcar aceite,
 * provar execução remota. Ele só descreve o que está escrito no repositório.
 *
 * Uso:
 *   node scripts/ci-coverage-map.mjs            # regenera docs/CI-MAPA-COBERTURA.json
 *   node scripts/ci-coverage-map.mjs --check    # não escreve; exit 1 se divergir
 *   node scripts/ci-coverage-map.mjs --resumo   # imprime o resumo legível
 */
import { readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const MAPA = 'docs/CI-MAPA-COBERTURA.json';
const WORKFLOWS = '.github/workflows';

const readText = (relative) => readFile(path.join(root, relative), 'utf8');
const uniq = (values) => [...new Set(values)].sort();

/** Nomes de script referenciados por `npm run NAME` / `npm run "expr"`. */
function scriptsCitados(texto) {
  const literais = [...texto.matchAll(/npm run ([a-zA-Z0-9:_-]+)/g)].map((m) => m[1]);
  if (/\bnpm test\b/.test(texto)) literais.push('test');
  const dinamicos = [...texto.matchAll(/npm run "([^"]+)"/g)].map((m) => m[1]);
  return { literais: uniq(literais), dinamicos: uniq(dinamicos) };
}

/**
 * Resolve a lista de um `for VAR in ...; do ... npm run "$VAR"`. Sem isso, as
 * oito variantes de backup pareceriam órfãs (elas não aparecem como literais).
 */
function listaDeLoop(texto) {
  const nomes = [];
  for (const match of texto.matchAll(/for\s+(\w+)\s+in\s+\\?\r?\n([\s\S]*?)\r?\n\s*do\b/g)) {
    for (const nome of match[2].matchAll(/([a-zA-Z0-9:_-]+)/g)) nomes.push(nome[1]);
  }
  return uniq(nomes);
}

/** Arquivos `tests/*.test.mjs` citados no texto (caminho completo ou `node --test`). */
function testesCitados(texto) {
  return uniq([...texto.matchAll(/(tests\/[\w.-]+\.test\.mjs)/g)].map((m) => m[1]));
}

/** Runners `scripts/*.mjs` citados no texto. */
function runnersCitados(texto) {
  return uniq([...texto.matchAll(/(scripts\/[\w.-]+\.mjs)/g)].map((m) => m[1]));
}

/**
 * Testes que um runner `scripts/*.mjs` executa. Ele pode citar o arquivo
 * diretamente (`tests/x.integration.test.mjs`) ou montar o caminho por
 * template (`tests/${name}.integration.test.mjs`). O mapa resolve os dois:
 * o segundo vira prefixo e é cruzado com o disco. Sem isso, a suíte que o
 * gate `test:admin-entry:pg` executa pareceria órfã.
 */
function testesDeRunner(texto) {
  const diretos = testesCitados(texto);
  const templates = [...texto.matchAll(/tests\/\$\{[^}]+\}([\w.-]*)/g)].map((m) => m[1]);
  return { diretos, templates };
}

/** Scripts que um comando npm invoca por `npm run X` (transitividade). */
function encadeados(comando) {
  const comRun = [...comando.matchAll(/npm run ([a-zA-Z0-9:_-]+)/g)].map((m) => m[1]);
  // `npm test` é a forma abreviada de `npm run test`; sem isto a cadeia
  // `npm test → test:unit` se perde e 183 testes viram "órfãos" por engano.
  const abreviados = /npm test/.test(comando) ? ['test'] : [];
  return uniq([...comRun, ...abreviados]);
}

/**
 * Fecha a transitividade: se `npm test` chama `test:unit`, então tudo que
 * `test:unit` cobre também é coberto por quem chama `npm test`.
 */
function expandir(nomes, scripts, visitados = new Set()) {
  const fila = [...nomes];
  const testes = new Set();
  const runners = new Set();
  while (fila.length) {
    const nome = fila.shift();
    if (visitados.has(nome)) continue;
    visitados.add(nome);
    const comando = scripts[nome];
    if (!comando) continue;
    for (const teste of testesCitados(comando)) testes.add(teste);
    for (const runner of runnersCitados(comando)) runners.add(runner);
    for (const filho of encadeados(comando)) fila.push(filho);
  }
  return { testes: [...testes].sort(), runners: [...runners].sort(), scripts: [...visitados].sort() };
}

export async function construirMapa() {
  const pkg = JSON.parse(await readText('package.json'));
  const scripts = pkg.scripts ?? {};
  const arquivosWorkflow = (await readdir(path.join(root, WORKFLOWS))).filter((n) => n.endsWith('.yml')).sort();

  // Runners do disco, lidos uma vez: a cadeia workflow → npm script → runner →
  // suíte de integração é o que evita declarar órfão o que roda em CI.
  const scriptsNoDisco = (await readdir(path.join(root, 'scripts')))
    .filter((nome) => nome.endsWith('.mjs'))
    .map((nome) => `scripts/${nome}`)
    .sort();
  const testesNoDisco = (await readdir(path.join(root, 'tests')))
    .filter((nome) => nome.endsWith('.test.mjs'))
    .map((nome) => `tests/${nome}`)
    .sort();

  // Runners importados como módulo (helper) não são "executados" pelo
  // workflow, mas não são código morto: entram em `referenciados` para não
  // serem confundidos com runner esquecido.
  const todoTexto = [];
  for (const arquivo of arquivosWorkflow) todoTexto.push(await readText(`${WORKFLOWS}/${arquivo}`));
  for (const nome of Object.values(scripts)) todoTexto.push(nome);
  for (const pasta of ['scripts', 'tests', 'src/server']) {
    let entradas = [];
    try { entradas = await readdir(path.join(root, pasta)); } catch { continue; }
    for (const entrada of entradas.filter((n) => n.endsWith('.mjs')).sort()) {
      try { todoTexto.push(await readText(`${pasta}/${entrada}`)); } catch { /* ignora binário */ }
    }
  }
  const textoGlobal = todoTexto.join('\n');
  const runnerReferenciado = (runner) => {
    const base = runner.split('/').pop();
    return textoGlobal.includes(base) && !textoGlobal.includes(`node ${runner}`) ? 'importado' : null;
  };

  const testesDeRunnerCache = new Map();
  async function testesDoRunner(runner) {
    if (testesDeRunnerCache.has(runner)) return testesDeRunnerCache.get(runner);
    let texto = '';
    try { texto = await readText(runner); } catch { texto = ''; }
    const { diretos, templates } = testesDeRunner(texto);
    const porTemplate = templates.length
      ? testesNoDisco.filter((teste) => templates.some((sufixo) => teste.endsWith(sufixo)))
      : [];
    const resultado = uniq([...diretos, ...porTemplate]);
    testesDeRunnerCache.set(runner, resultado);
    return resultado;
  }

  // Quem chama quem: `npm test` → `test:unit`. Um script chamado por outro é
  // executado indiretamente, e a varredura literal do YAML não vê isso.
  const dependentes = new Map();
  for (const [nome, comando] of Object.entries(scripts)) {
    for (const filho of encadeados(comando ?? '')) {
      if (!dependentes.has(filho)) dependentes.set(filho, []);
      dependentes.get(filho).push(nome);
    }
  }

  const workflows = [];
  const testesPorWorkflow = new Map();
  const runnersPorWorkflow = new Map();
  const scriptsPorWorkflow = new Map();

  for (const arquivo of arquivosWorkflow) {
    const texto = await readText(`${WORKFLOWS}/${arquivo}`);
    const { literais, dinamicos } = scriptsCitados(texto);
    const loop = listaDeLoop(texto);
    const resolvidos = uniq([...literais, ...loop]);
    const expansao = expandir(resolvidos, scripts);
    const testesDiretos = testesCitados(texto);
    const runnersDiretos = runnersCitados(texto);

    const runners = uniq([...runnersDiretos, ...expansao.runners]);
    // A suíte que os runners executam também é coberta por este workflow.
    const testesDosRunners = [];
    for (const runner of runners) testesDosRunners.push(...await testesDoRunner(runner));
    const testes = uniq([...testesDiretos, ...expansao.testes, ...testesDosRunners]);

    testesPorWorkflow.set(arquivo, testes);
    runnersPorWorkflow.set(arquivo, runners);
    scriptsPorWorkflow.set(arquivo, resolvidos);

    const gatilhos = [...texto.matchAll(/^ {2}(push|pull_request|workflow_dispatch|schedule):/gm)].map((m) => m[1]);
    workflows.push({
      arquivo,
      nome: /^name:\s*(.+)$/m.exec(texto)?.[1]?.trim() ?? null,
      gatilhos: uniq(gatilhos),
      // Nomes de script que o YAML nomeia explicitamente.
      scripts_literais: literais,
      // Nomes que só aparecem dentro de um `for` (o executor os chama, o texto
      // não os nomeia): a diferença que a varredura literal perde.
      scripts_via_loop: uniq(loop.filter((nome) => !literais.includes(nome))),
      // Tudo o que o workflow executa, já fechado por transitividade.
      // Fechado por transitividade: `npm test` aparece junto de `test:unit`.
      scripts_efetivos: expansao.scripts,
      testes: testes.length,
      runners: runners.length,
    });
  }

  // Cobertura por teste: em quais workflows ele aparece.
  // `npm test` é o comando do `test:unit`; um teste que só aparece ali ainda
  // é executado pelo workflow que roda `npm test`.
  const workflowsQueRodamTestUnit = arquivosWorkflow.filter((w) => {
    const efetivos = expandir(scriptsPorWorkflow.get(w), scripts).scripts;
    return efetivos.includes('test:unit');
  });
  const coberturaTestes = testesNoDisco.map((teste) => {
    const diretos = arquivosWorkflow.filter((w) => testesPorWorkflow.get(w).includes(teste));
    const viaTestUnit = (scripts['test:unit'] ?? '').includes(teste) ? workflowsQueRodamTestUnit : [];
    return {
      teste,
      workflows: uniq([...diretos]),
      workflows_via_test_unit: uniq([...viaTestUnit]),
      no_test_unit: (scripts['test:unit'] ?? '').includes(teste),
    };
  });

  const coberturaRunners = scriptsNoDisco.map((runner) => ({
    runner,
    workflows: arquivosWorkflow.filter((w) => runnersPorWorkflow.get(w).includes(runner)),
    npm_scripts: uniq(Object.entries(scripts).filter(([, cmd]) => cmd.includes(runner)).map(([nome]) => nome)),
  }));

  const testesForaDeWorkflow = coberturaTestes
    .filter((t) => t.workflows.length === 0 && t.workflows_via_test_unit.length === 0)
    .map((t) => t.teste);
  const runnersSemUso = coberturaRunners
    .filter((r) => r.workflows.length === 0 && r.npm_scripts.length === 0)
    .map((r) => ({ runner: r.runner, referencia: runnerReferenciado(r.runner) }));
  const runnersForaDeWorkflow = runnersSemUso.filter((r) => !r.referencia).map((r) => r.runner);
  const runnersImportados = runnersSemUso.filter((r) => r.referencia).map((r) => r.runner);

  // Scripts de teste declarados no package.json e não executados por workflow.
  const scriptsDeTeste = Object.keys(scripts).filter((n) => /^(test|qa):/.test(n) || n === 'test');
  // Um script "sem menção" ainda pode ser coberto: `npm test` expande para
  // `test:unit`, e quem chama `npm test` executa tudo que o `test:unit` lista.
  const scriptsSemWorkflow = uniq(
    scriptsDeTeste.filter((nome) => !arquivosWorkflow.some((w) => {
      const efetivos = expandir(scriptsPorWorkflow.get(w), scripts).scripts;
      if (efetivos.includes(nome)) return true;
      // Coberto por runner direto: o workflow chama `node scripts/X.mjs`
      // enquanto o script npm é a forma local do mesmo comando.
      const runnersDoWorkflow = runnersPorWorkflow.get(w);
      return runnersCitados(scripts[nome] ?? '').some((runner) => runnersDoWorkflow.includes(runner));
    })),
  );

  return {
    schema: 'ci-mapa-cobertura/1',
    gerado_por: 'scripts/ci-coverage-map.mjs',
    // Nenhuma data: o arquivo precisa ser determinístico para o `--check`.
    fontes: {
      workflows: `${WORKFLOWS}/*.yml`,
      scripts: 'package.json#scripts',
      testes: 'tests/*.test.mjs',
    },
    totais: {
      workflows: arquivosWorkflow.length,
      scripts_package: Object.keys(scripts).length,
      testes_no_disco: testesNoDisco.length,
      runners_em_scripts: scriptsNoDisco.length,
      testes_cobertos_por_workflow: coberturaTestes.filter((t) => t.workflows.length > 0).length,
      testes_cobertos_via_test_unit: coberturaTestes.filter((t) => t.workflows_via_test_unit.length > 0).length,
      testes_cobertos_pelo_test_unit: coberturaTestes.filter((t) => t.no_test_unit).length,
      testes_sem_workflow_nem_test_unit: testesForaDeWorkflow.length,
      runners_sem_workflow_nem_script: runnersForaDeWorkflow.length,
      runners_importados_como_helper: runnersImportados.length,
      scripts_de_teste_sem_workflow: scriptsSemWorkflow.length,
    },
    workflows,
    testes_fora_de_workflow_e_test_unit: testesForaDeWorkflow,
    runners_sem_workflow_nem_script: runnersForaDeWorkflow,
    runners_importados_como_helper: runnersImportados,
    scripts_de_teste_sem_workflow: scriptsSemWorkflow,
    // Para cada script sem chamada direta: quem o chama (ou nada).
    scripts_de_teste_chamados_por: Object.fromEntries(
      scriptsSemWorkflow.map((nome) => [nome, uniq(dependentes.get(nome) ?? [])]).filter(([, v]) => v.length > 0),
    ),
    cobertura_testes: coberturaTestes,
    cobertura_runners: coberturaRunners,
  };
}

export function resumoLegivel(mapa) {
  const linhas = [
    `workflows: ${mapa.totais.workflows}`,
    `scripts no package.json: ${mapa.totais.scripts_package}`,
    `testes no disco: ${mapa.totais.testes_no_disco}`,
    `  cobertos por workflow: ${mapa.totais.testes_cobertos_por_workflow}`,
    `  cobertos pelo test:unit: ${mapa.totais.testes_cobertos_pelo_test_unit}`,
    `  cobertos pelo CI via npm test: ${mapa.totais.testes_cobertos_via_test_unit}`,
    `  sem workflow nem test:unit: ${mapa.totais.testes_sem_workflow_nem_test_unit}`,
    `runners em scripts/: ${mapa.totais.runners_em_scripts}`,
    `  sem workflow nem npm script: ${mapa.totais.runners_sem_workflow_nem_script}`,
    `scripts de teste sem workflow: ${mapa.totais.scripts_de_teste_sem_workflow}`,
  ];
  for (const item of mapa.runners_sem_workflow_nem_script) linhas.push(`  runner sem workflow: ${item}`);
  for (const item of mapa.testes_fora_de_workflow_e_test_unit) linhas.push(`  teste sem workflow: ${item}`);
  return linhas.join('\n');
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const mapa = await construirMapa();
  const json = JSON.stringify(mapa, null, 1) + '\n';
  const check = process.argv.includes('--check');
  if (check) {
    let atual = null;
    try { atual = await readText(MAPA); } catch { atual = null; }
    if (atual !== json) {
      console.error(`DESATUALIZADO: ${MAPA} — rode "node scripts/ci-coverage-map.mjs" e versione o resultado.`);
      process.exit(1);
    }
    console.log(`OK: ${MAPA} confere com workflows, package.json e tests/.`);
  } else {
    await writeFile(path.join(root, MAPA), json, 'utf8');
    console.log(resumoLegivel(mapa));
    console.log(`\nGravado em ${MAPA}.`);
  }
}
