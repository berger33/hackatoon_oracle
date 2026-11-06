# Mapa de CI × cobertura — medição de 06/11/2026

**Origem:** `scripts/ci-coverage-map.mjs` (gerador) + `tests/ci-coverage-map.test.mjs` (guarda). O JSON versionado em [`CI-MAPA-COBERTURA.json`](CI-MAPA-COBERTURA.json) é a fonte; este arquivo explica como ler e o que a medição encontrou.

**Base:** `d2674a25297e1081fc698d98504635907a4068fe` (`main`, merge da PR #350) + fatia 07 desta sessão.

## Para que serve

O plano de fechamento (item 06) pede: *"mapear scripts→arquivos→cenários→workflows; ligar só jornadas realmente órfãs, adicionar limites proporcionais e diagnóstico sempre que aplicável"* e alerta contra o erro mais comum — **confundir ausência literal com orfandade**. Um `npm run` não aparece no YAML por três razões muito diferentes:

| Razão | Exemplo medido | É órfão? |
| --- | --- | --- |
| Executado por **loop** no workflow | as 8 variantes `test:backup-restore:pg:*` vêm de um `for gate in …; npm run "$gate"` | **não** |
| Executado por **cadeia de scripts** | `ci.yml` roda `npm test` → `test` → `test:unit` (184 arquivos) | **não** |
| Executado por **runner** chamado no workflow | `test:admin-entry:pg` → `qa-admin-entry-postgres.mjs` → `tests/admin-entry.integration.test.mjs` (nome montado por template) | **não** |

O gerador resolve as três. Uma varredura só de texto declararia **117 testes** como órfãos por engano (medido: 136 → 249 cobertos depois de resolver loop, cadeia e runner).

## Números medidos

| Item | Valor |
| --- | --- |
| Workflows | 60 |
| Scripts no `package.json` | 111 |
| Testes `tests/*.test.mjs` no disco | 252 |
| Executados por algum workflow (direto, por loop, por cadeia ou por runner) | 250 |
| Executados pelo `test:unit` | 184 |
| Executados pelo CI **via `npm test`** | 184 |
| **Sem workflow e sem `npm test`** | **2** |
| Runners em `scripts/` | 115 |
| Runners sem workflow nem script npm | 14 |
| Runners importados como helper `null` (não são órfãos) | 14 |
| Scripts npm de teste sem chamada em workflow | 9 |

## Os dois testes sem cobertura

Nenhum dos dois é "provável esquecimento"; ambos estão declarados na guarda com a decisão.

1. **`tests/lead-flow.integration.test.mjs`** — gate HTTP de captação de lead (11 subtestes, PostgreSQL real, servidor real). Exige `RUN_DATABASE_INTEGRATION=1` + `DATABASE_URL` de loopback; fora disso ele **pula**. Colocá-lo no `npm test` produziria skip silencioso, que é exatamente o que a fatia 06 proíbe. Hoje só roda por `npm run test:integration`, sob demanda. **Ligar no `ci.yml` com PostgreSQL efêmero é trabalho de fatia própria** (precisa decidir a variante e o custo do job).

2. **`tests/ux-pro-09e-7-text-overflow.test.mjs`** — guarda estática da captura opt-in UX-PRO-09E-7: lê `scripts/ux-evidence-capture.mjs` e o `package.json`, sem banco e sem navegador. É **candidato direto ao `test:unit`**, mas acrescentar arquivo ao `npm test` muda o contrato de testes numa fatia de mapeamento; fica registrado para a fatia que decidir isso.

## Os nove scripts npm sem workflow

Todos têm razão declarada em `tests/ci-coverage-map.test.mjs`: formas locais de comandos que o CI chama de outro jeito (`test:ux-pro-09e-pu4` × step `:browser`), aliases já cobertos pelo `test:unit` (`test:ux-pro-04-reports`, `test:ux-pro-09e-pu6`, `test:ux-pro-10b-keyboard`), capturas de evidência manuais e gates que exigem PostgreSQL local (`test:integration`, `test:staff-auth:pg`).

## Os 14 runners sem workflow nem script npm

São **ferramentas de operação local**, não gates de CI: geradores de inventário (`e15-route-catalog.mjs`, `requisitos-222-inventory.mjs`, `ux00-inventory.mjs`, `ux-pro-03-ti-inventory.mjs`, `audit-ui-inventory.mjs`), scripts de paleta e captura (`e18-*`), reset de credenciais de demonstração e o próprio gerador deste mapa. Nenhum deles é citado como prova de CI em documento algum — a guarda registra a lista para que a afirmação não apareça por descuido.

## Limites desta medição

- Descreve o **que está escrito** nos workflows, não o que rodou. Verde em CI continua exigindo execução remota.
- A resolução por runner usa o texto do script (nome literal ou template `tests/${…}`). Um runner que montasse o caminho de outra forma apareceria como órfão — o que é o comportamento correto: melhor falhar alto que presumir cobertura.
- Workflows com `paths:` só rodam quando o caminho casa. O mapa não avalia se a mudança da PR toca esses caminhos; isso é decisão de cada workflow.
- Não avalia tempo de fila, custo de minutos, flakiness nem paralelismo — só cobertura declarada.
- Nenhum teste foi removido, desligado ou reduzido nesta fatia; nenhum workflow foi alterado.

## Como manter

```bash
node scripts/ci-coverage-map.mjs          # regenera docs/CI-MAPA-COBERTURA.json
node scripts/ci-coverage-map.mjs --check   # exit 1 se o versionado divergir
node scripts/ci-coverage-map.mjs --resumo  # imprime o resumo sem escrever
```

Acrescentou teste ou workflow? Regenere e suba o piso em `tests/ci-coverage-map.test.mjs` na mesma PR. O piso é o contrato: piso frouxo é o que deixou gates órfãos passarem antes.
