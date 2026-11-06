# Fatia 18 — ensaio de recuperação sintética: impedimento técnico medido

**Data:** 06/11/2026. Branch `arena/65b896b8-hackatoon-oracle`. Nenhum dump, restore, deploy ou dado real. Produção **NO-GO**.

## O que o plano pede

`auditoria-2026-11-04/PLANO-EXECUCAO.md`, fatia 18: verificar a possibilidade de disponibilizar `pg_dump`/`pg_restore` **17** no ambiente permitido, executar as variantes existentes (DB + arquivos + assinatura/inventário) e corrigir defeitos reproduzidos. Critério de saída aceito pelo plano: **"restore sintético comprovado OU impedimento técnico registrado"**. Também é explícito: **não instalar versão incompatível para obter verde**.

## Medição

| Verificação | Resultado |
|---|---|
| `which pg_dump pg_restore psql initdb postgres` | nenhum no `PATH` |
| `pg_dump --version` / `pg_restore --version` | ausentes |
| `docker` | ausente |
| `node_modules/@embedded-postgres/linux-x64` | presente — **PG 17.9** real |
| binários que o pacote entrega | `initdb`, `pg_ctl`, `postgres` — **sem** clientes de dump/restore |
| `node scripts/qa-backup-restore-postgres.mjs` | **exit 2** |

Saída íntegra da execução do runner:

```
QA_RESTORE_CLIENT_MISSING_OR_INCOMPATIBLE: requires pg_dump and pg_restore version 17 for PostgreSQL 17.9; no database created.
QA_PG_TEMP_CLEANED: true
QA_PG_SUPERVISOR: worker-failed; phase=boot; exit=2
QA_RESTORE_TEMP_CLEANED: true (cluster(s), archive and synthetic data)
```

O runner **já falha fechado**, e o fez no caminho certo: recusou antes de criar banco, não converteu ausência em sucesso (exit 2, não 0) e limpou os temporários que havia preparado. Nada precisou ser corrigido — o comportamento observado é exatamente o que a fatia 05AI construiu.

## Por que não instalei os clientes

- O PG do ambiente é **17.9**; a política do plano proíbe instalar versão incompatível só para fechar verde, e `pg_dump` 16 contra servidor 17.9 é justamente o tipo de mistura que produz arquivo que "passa" e não restaura.
- Não há `docker` para subir uma imagem oficial, e a rede do sandbox só alcança os hosts de pacotes (`registry.npmjs.org`, `pypi.org`, GitHub), não os repositórios de distribuição do PostgreSQL.
- Compilar os clientes a partir do fonte exigiria `libpq`/`zlib`/`readline` e um toolchain que o sandbox não oferece de forma verificável — e continuaria sendo software construído aqui, não o cliente homologado que a operação usaria.

## Consequência declarada

- **Restore sintético NÃO foi comprovado** nesta sessão. A capacidade de recuperação continua **não medida**.
- O que **está** provado: o gate recusa corretamente quando o cliente falta, e a limpeza funciona até nesse caminho de falha.
- A fatia 05AI documentou o mesmo bloqueio quando compilou clientes PG17 temporariamente para QA e registrou que eles **não** são homologados para produção. Nada aqui muda essa conclusão.
- Continua válido: **nenhum backup/restore operacional, nenhuma restauração de dados reais**, e a operação de recuperação em destino segue exigindo autorização específica.

## Como fechar esta fatia (quando houver ambiente)

1. Disponibilizar `pg_dump`/`pg_restore` **17.x** no `PATH` (ou em `QA_PG_DUMP_BIN`/`QA_PG_RESTORE_BIN`) num ambiente autorizado.
2. Rodar as oito variantes de `scripts/qa-backup-restore-postgres.mjs` e guardar o TAP de cada uma.
3. Exercitar as corrupções previstas (arquivo truncado, assinatura/inventário divergentes, cobertura parcial) e confirmar exit não zero com limpeza.
4. Só então tratar recuperação como medida — e ainda assim com dados sintéticos, nunca reais.
