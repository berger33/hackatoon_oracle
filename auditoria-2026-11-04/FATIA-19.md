# Fatia 19 — distribuição e rotas: verificação do estado vigente

**Data:** 06/11/2026. Branch `arena/65b896b8-hackatoon-oracle`. Nenhum deploy, publicação de release, remoção de pacote ou alteração de política. Produção **NO-GO**.

## O que o plano pede

`auditoria-2026-11-04/PLANO-EXECUCAO.md`, fatia 19: reforçar avisos/versionamento/manifests e regressão de paridade borda↔dispatcher, preservando pacotes e aliases existentes. Saída esperada: artefatos identificáveis e rotas verificadas. Remoção de pacotes e mudança de política de releases ficam para decisão do proprietário; refatoração ampla do monólito está fora de escopo.

## Método

Verificação **somente leitura**: medir cada afirmação do aviso de distribuição contra o código, e medir a paridade borda/despacho com o catálogo canônico já existente. Nada foi alterado — se algo estivesse errado, o registro seria o defeito, não uma correção oportunista numa fatia de verificação.

## Resultados medidos

### Paridade borda ↔ despacho (E15)

| Métrica | Medido |
|---|---|
| Regras na borda (`API_PATH_MATCH`) | **1517** (1396 exatas, 121 prefixos) |
| Regras no despacho (`routeApi`) | **1735** (1704 handlers, 31 pré-autorizações, 223 regexes) |
| Módulos de despacho identificados | **128** |
| **Borda sem despacho** (caminho que termina em 404 interno) | **0** |
| **Inalcançáveis** (só no despacho; código morto) | **0** |
| Sombreadas (regra anterior captura o caminho) | **7** — todas com decisão publicada |
| Avisos | 0 |
| `tests/e15-route-catalog.test.mjs` | **19/19** |

As 7 sombreadas não são código morto: cada uma tem decisão registrada no relatório datado e gate próprio (as quatro de integrações são falso positivo medido; as três `journey-corrections`/`faq-assisted` foram decididas e removidas onde cabia).

### Aviso de distribuição (`downloads/LEIA-ME.md`, materializado em `dist/`)

| Afirmação do aviso | Medição | Veredito |
|---|---|---|
| "**183** migrações (001–183)" | `ls db/migrations/*.sql` = **183** | confere |
| "**101** rotas" | `src/app/**/page.tsx` = **101** | confere |
| "`next` 16.4.2" | `package.json` = `^16.4.2` | confere |
| "`nodemailer` 10.2.1" | `package.json` = `^10.2.1` | confere |
| "os três pacotes foram gerados com ~96 migrações" | ZIP versionado tem 20 MB, gerado quando o repositório tinha menos migrações | coerente com o histórico |

O aviso é **exigido por teste** (`PLT-DEF-024` e `E21` em `tests/package-artifacts.test.mjs`): se uma migração ou uma rota nova entrar sem atualizar o texto, a suíte falha. Isso é o que impede o aviso de envelhecer em silêncio — e é exatamente o tipo de guarda que esta fatia deveria confirmar.

### Semântica do aviso

As três consequências práticas declaradas continuam corretas e **não** foram enfraquecidas: os ZIPs não servem como instalação, não devem ser distribuídos por link externo, não são backup operacional e não contêm dados reais. A instrução de regenerar por `scripts/build-qa-download.py` / `scripts/build-homologacao-download.py` e publicar como artefato de release versionado **fora do índice do Git** permanece.

## O que esta fatia NÃO fez

- **Não** removeu os ZIPs históricos nem mudou a política de releases: o plano reserva isso ao proprietário.
- **Não** publicou release, não fez upload nem distribuição externa.
- **Não** refatorou o monólito `server.mjs`.
- **Não** criou manifesto novo de distribuição: o aviso atual já carrega versão, contagens e instruções, e a guarda o mantém vivo. Criar outro mecanismo seria adicionar superfície sem demanda demonstrada.

## Limites

- A paridade é **estática** (texto de `server.mjs` × catálogo): não prova que cada rota responde em runtime, nem que o corpo/contrato de cada uma está correto. Isso é coberto por outros gates (rotas públicas, gates `*:pg`, focais por superfície).
- O ZIP não foi aberto nem reexecutado: a conclusão "obsoleto" vem do aviso versionado e da diferença de contagem de migrações, não de uma tentativa de instalação a partir dele.
- Distribuição real (download público, assinatura de release) não é exercitável neste sandbox.
