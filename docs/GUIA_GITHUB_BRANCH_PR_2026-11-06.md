# Guia prático — branch e PR no GitHub (MediFlow e qualquer outro repo)

**Data:** 06/11/2026 · **Para:** William (QA & Requirements Lead)
**Objetivo:** responder "posso fazer isso?", apontar as regras do projeto e ensinar o passo a passo. **Nenhuma branch ou PR foi criada em repositório compartilhado** — este é só um roteiro para você executar.

---

## 1. Respostas diretas

| Pergunta | Resposta | Onde se apoia |
| --- | --- | --- |
| Eu posso criar branch e PR no repo compartilhado? | **Sim.** Sua conta tem `admin`, `maintain`, `pull` e `push` = `true` em `No-Country-simulation/g10-brasil-equipe-15_mediflow`. Não precisa de fork. | `gh api repos/... --jq .permissions` |
| Existe documento sobre organização do GitHub? | **Sim: `CONTRIBUTING.md`** ("Guia de Colaboração e Engenharia de Software — Equipe 15 MediFlow", 184 linhas). Complementos: `.github/pull_request_template.md`, `.gitignore`, `README.md` (mapa do repositório, L171-194) e `ARQUITETURA.md`. | Raiz do repo do time |
| Posso criar uma branch só para isso? | **Sim — é exatamente a regra.** O padrão é `docs/*` para "atualizações exclusivas de documentação, guias e diagramas", criada a partir de `develop` e mesclada de volta via PR. Já existem `docs/sincronizacao-testes-298` e `docs/mapeamento-ing-cla-ext` seguindo esse padrão. | CONTRIBUTING §1, §4 Passo 2; branches remotas |
| Posso mandar direto pra `develop`? | **Não.** `develop` e `main` são protegidas: push direto bloqueado; merge somente por PR aprovado por **pelo menos 1 colega**. PR sempre com **base `develop`, nunca `main`**. | CONTRIBUTING §1 e §4 Passo 6 |

---

## 2. As regras que você precisa seguir (texto do projeto)

**`CONTRIBUTING.md` §1 — GitFlow simplificado**

| Branch | Papel | Regra |
| --- | --- | --- |
| `main` | Produção, congelada para a banca | Totalmente protegida; merge só via PR vindo de `develop` |
| `develop` | Branch padrão, integração das frentes | Protegida; push direto bloqueado; merge só via PR com ≥ 1 approve |
| `feature/*` | Nova funcionalidade | Nasce de `develop`, volta por PR |
| `fix/*` | Correção pontual | Nasce de `develop`, volta por PR |
| **`docs/*`** | **Documentação, guias, diagramas** | **Nasce de `develop`, volta por PR** ← é o seu caso |

**§4 — Ciclo de trabalho (6 passos):** (1) `git checkout develop && git pull origin develop`; (2) criar branch semântica; (3) commits atômicos com **Conventional Commits** (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`); (4) **quality gate obrigatório** `python -m pytest` — "Nenhum Pull Request será aceito se algum dos testes estiver falhando"; (5) `git push origin <sua-branch>`; (6) PR com base `develop`, descrever, marcar revisores, ≥ 1 Approve, **apagar a branch remota depois do merge**.

**§5 — Governança do Contrato de Dados:** `src/schemas/clinical.py` é a fonte única da verdade. Alterar schema/enums unilateralmente é proibido e qualquer mudança deve ser discutida e refletida em `docs/testes/CONTRATO_DE_DADOS.md`.

**§6 — Segurança:** nunca subir `GEMINI_API_KEY`, `*.pem`, credenciais OCI ou senhas (`.env` já está no `.gitignore`); **nunca `git push --force`** em `develop`/`main`; **PRs enxutos**, uma responsabilidade por PR.

**`.github/pull_request_template.md`:** o corpo do PR precisa preencher tipo de alteração, relação com os requisitos do hackathon, como foi testado e o checklist (branch atualizada com `develop`, sem dados confidenciais, testado localmente, ≥ 1 revisor solicitado).

**`.gitignore` do time:** ignora `.env`, `*.pem`, `config`, `credentials.json` e **quatro fixtures pesadas de >10 MB** (geradas por script). Não force a inclusão desses arquivos.

> ⚠️ **Números desatualizados no documento:** o CONTRIBUTING fala em "208 testes" e "245 testes" no cabeçalho, e o README em "217 testes". A regra (rodar a suíte e não quebrar nada) continua valendo; a volumetria real hoje é bem maior (319 aprovados / 1 ignorado no PR #22, já mesclado). Não corrija esses números no mesmo PR da EPT — §6 pede PR enxuto.

---

## 3. ⚠️ Antes de copiar: o que JÁ existe no repo do time

Comparei `develop` (clone de 06/11/2026) com o seu `hackatoon_oracle`:

| Item | Seu oracle (local) | Time (`develop`) | Conclusão |
| --- | --- | --- | --- |
| `tests/fixtures/manifest.csv` | 68 linhas (67 fixtures) | **80 linhas (79 fixtures)** | Time está à frente |
| `tests/fixtures/` | 254 arquivos / 12 MB | **296 arquivos / 16 MB** | Time está à frente |
| `docs/testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md` | 35.247 bytes | **53.513 bytes** | Diverge; time mais completo |
| `docs/testes/CONTRATO_DE_DADOS.md` | 11.984 bytes | **21.588 bytes** | Diverge; é arquivo de governança |
| `docs/testes/AUDITORIA_2026-10-20.md` | 7.411 bytes | **12.008 bytes** | Diverge |
| `docs/testes/README.md`, `VISUAL_SCHEMAS.md` | ausentes | **presentes** | Time tem a mais |
| `Mapa_de_Documentos_de_Teste_MediFlow.pdf` | 71.377 bytes | 72.415 bytes | Diverge |
| **EPT / EF / Análise / `Projeto_oracle.pdf`** | presentes (PDFs, Drive, e agora v1.2) | **AUSENTES** | ✅ É o que realmente falta |

**Consequência prática:** os **79 fixtures e a documentação de testes já estão no GitHub do time** e são a versão oficial (CONTRIBUTING §2: `docs/testes/` = "Contrato Canônico, Catálogo dos 79 Fixtures e Auditorias"; README L190: "79 fixtures canônicos"). Se você copiar a pasta do oracle por cima, vai **apagar conteúdo, rebaixar o `CONTRATO_DE_DADOS.md`** (o que fere o §5) e gerar um PR gigante com dezenas de deleções — contra o §6.

**Escopo recomendado do seu PR:** somente **`docs/` com a EPT** (Especificação Funcional / `EPT_MediFlow.pdf` e, se quiser, as EF v1.2 + Análise v1.2 + registro de alterações que publicamos). Não toque em `tests/fixtures/`, `docs/testes/` ou `src/schemas/`.

Se você quiser levar algum fixture novo, gere com `tools/gerar_fixtures_catalogo.py` e adicione **apenas os arquivos novos**, nunca a pasta inteira.

---

## 4. Roteiro A — branch + PR no repo compartilhado do time

Cole no terminal, um bloco por vez, lendo o resultado de cada um.

```bash
# 0) uma vez só: conferir que o gh está autenticado e que você tem permissão
gh auth status
gh api repos/No-Country-simulation/g10-brasil-equipe-15_mediflow --jq '.permissions'
gh repo view No-Country-simulation/g10-brasil-equipe-15_mediflow --json defaultBranchRef

# 1) clonar (se ainda não tem) e entrar
git clone https://github.com/No-Country-simulation/g10-brasil-equipe-15_mediflow.git
cd g10-brasil-equipe-15_mediflow

# 2) SEMPRE partir da develop atualizada  (CONTRIBUTING §4 Passo 1)
git checkout develop
git pull origin develop

# 3) criar a branch de documentação  (§4 Passo 2; prefixo docs/)
git checkout -b docs/ept-v1.2-especificacao
# dica: um nome curto e semântico, sem espaços nem acentos

# 4) colocar SÓ os arquivos que faltam
mkdir -p docs/especificacao
cp /home/user/hackatoon_oracle/docs/v1.2/MediFlow_Especificacao_Funcional_v1.2.pdf docs/especificacao/
cp /home/user/hackatoon_oracle/docs/v1.2/MediFlow_Analise_de_Requisitos_v1.2.pdf docs/especificacao/
cp /home/user/hackatoon_oracle/docs/v1.2/REGISTRO_DE_ALTERACOES_v1.2.pdf docs/especificacao/
cp /home/user/hackatoon_oracle/docs/v1.2/MediFlow_Especificacao_Funcional_v1.2.md docs/especificacao/
cp /home/user/hackatoon_oracle/docs/v1.2/MediFlow_Analise_de_Requisitos_v1.2.md docs/especificacao/

# 5) conferir ANTES de commitar (nunca use git add -A sem olhar)
git status
git diff --stat
# se algum arquivo não aparecer, ele pode estar no .gitignore:
git check-ignore -v docs/especificacao/MediFlow_Especificacao_Funcional_v1.2.pdf || echo "nao ignorado"

# 6) quality gate obrigatório (§4 Passo 4)
python -m pytest -q
# como seu PR só mexe em docs/, a suíte deve continuar verde; se falhar, pare e investigue

# 7) commit atômico com Conventional Commits (§4 Passo 3)
git add docs/especificacao/
git commit -m "docs(ept): adiciona Especificacao Funcional e Analise de Requisitos v1.2"

# 8) push da SUA branch — nunca push em develop (§4 Passo 5)
git push -u origin docs/ept-v1.2-especificacao

# 9) abrir o PR com base develop  (§4 Passo 6)
gh pr create \
  --repo No-Country-simulation/g10-brasil-equipe-15_mediflow \
  --base develop \
  --head docs/ept-v1.2-especificacao \
  --title "docs(ept): adiciona Especificacao Funcional v1.2" \
  --body-file corpo_pr.md \
  --reviewer LOGIN_DO_COLEGA
```

**Alternativa para a primeira vez (mais visual):** no passo 9 use `gh pr create --web` — o GitHub abre no navegador já com o template `.github/pull_request_template.md`, a base `develop` pré-selecionada e o campo de revisores. Você preenche e clica em *Create pull request*. É a melhor forma de aprender o que cada campo significa.

Conceitos: **base** = para onde o código vai (`develop`); **head** = de onde vem (sua branch); **reviewer** = quem dá o Approve; **Approve** = o que libera o merge.

Depois do merge: `gh pr view --web`, clique em *Delete branch* (§4 Passo 6) e atualize seu local com `git checkout develop && git pull origin develop`.

### Modelo de corpo do PR (segue o template do time)

```markdown
## 🏥 MediFlow - Descrição do Pull Request

### 📌 Tipo de alteração
- [x] Documentação ou diagramas (`docs`)

### 📝 O que foi implementado/modificado?
Adiciona em `docs/especificacao/` a Especificação Funcional v1.2 e a Análise de
Requisitos v1.2, alinhadas ao `Projeto_oracle.pdf` conforme a seção 2 da EF,
além do registro de alterações (D-01, D-02, D-03). Não altera código, schemas,
fixtures nem `docs/testes/`: os 79 fixtures e a documentação de testes canônica
já estão em `develop`.

### 🎯 Relação com os Requisitos do Hackathon MediFlow
- [x] Outro: documentação normativa / rastreabilidade com o Brief original

### 🧪 Como isso foi testado?
1. `python -m pytest -q` executado localmente, suíte verde (sem alteração de código).
2. Conferido que nenhum arquivo de `tests/fixtures/`, `docs/testes/` ou
   `src/schemas/` entra neste PR (`git diff --stat`).

### ✅ Checklist antes de solicitar revisão
- [x] Minha branch está atualizada com a `develop`.
- [x] O código segue as boas práticas e não contém dados confidenciais.
- [x] Testei localmente e a aplicação executa sem quebrar fluxos existentes.
- [x] Solicitei a revisão de pelo menos 1 integrante do time.
```

---

## 5. Roteiro B — PR em **outro** repositório (nunca fez isso antes)

A primeira pergunta é sempre: **você tem permissão de escrita no repo de destino?**

```bash
gh api repos/DONO/REPO --jq '.permissions.push'
gh repo view DONO/REPO --json defaultBranchRef
```

- `true` → **Caso 1**: repita o Roteiro A trocando o `--repo`, o nome da branch e a `--base` (em repositórios pessoais o padrão costuma ser `main`, não `develop`). Você cria a branch **no próprio repo de destino** e abre o PR de lá.
- `false` / vazio → **Caso 2 (fork)**: você não pode criar branch no repo alheio, então faz uma cópia na sua conta.

### Caso 2 — fork (é assim que se contribui com repo de outra pessoa/org)

```bash
# 1) criar o fork na SUA conta e já clonar
gh repo fork DONO/REPO --clone=true
cd REPO

# 2) conferir os remotos: origin = SEU fork, upstream = repo original
git remote -v
# se o upstream não existir, adicione:
git remote add upstream https://github.com/DONO/REPO.git

# 3) partir da branch padrão do ORIGINAL (não do seu fork desatualizado)
git fetch upstream
git checkout -b docs/minha-alteracao upstream/main   # ou upstream/develop

# 4) editar, conferir e commitar
git status
git add CAMINHO/DO/ARQUIVO
git commit -m "docs: descreve a alteracao"

# 5) push vai para o SEU fork (origin), não para o original
git push -u origin docs/minha-alteracao

# 6) PR apontando para o repo original
gh pr create \
  --repo DONO/REPO \
  --base main \
  --head SEU_LOGIN:docs/minha-alteracao \
  --title "docs: descreve a alteracao" \
  --body "Descreva o que mudou e como validar."
```

**A parte que mais confunde na primeira vez:** quando a branch está no fork, `--head` precisa vir no formato **`SEU_LOGIN:branch`**, e `--repo DONO/REPO` é obrigatório (senão o `gh` tenta abrir o PR dentro do seu fork, não no original). Na interface web é mais simples: depois do push, o GitHub mostra um banner *"Compare & pull request"* — clique, confira que **base** é o repo original e **head** é o seu fork, e preencha o template.

Se o destino for o seu próprio `berger33/hackatoon_oracle`, você é `admin` → **Caso 1**, sem fork.

---

## 6. Checklist final das regras do projeto

- [ ] Branch `docs/*` criada a partir de `develop` atualizada.
- [ ] PR com **base `develop`**, nunca `main`.
- [ ] Commits com prefixo `docs:` (Conventional Commits).
- [ ] `python -m pytest` rodado e verde antes do push.
- [ ] Nenhuma chave, `.env`, `*.pem` ou credencial no commit.
- [ ] `git diff --stat` confere que **só** `docs/especificacao/` entra.
- [ ] Corpo do PR preenche `.github/pull_request_template.md`.
- [ ] Pelo menos 1 revisor marcado e Approve recebido antes do merge.
- [ ] Sem `git push --force`.
- [ ] Branch remota apagada depois do merge.

---

## 7. Estado atual do GitHub (mudou desde a nossa conversa anterior)

Consultado em 06/11/2026:

| PR | Estado | Merge |
| --- | --- | --- |
| #25 `fix(api): respeita negacao na heuristica de urgencia` | fechado, **merged** | 05/11/2026 23:57:51Z |
| #23 `docs: relaciona casos ING, CLA e EXT as fixtures` | fechado, **merged** | 06/11/2026 01:09:29Z |
| #22 `feat(oci): persiste historico JSON e recupera falhas` | fechado, **merged** | 06/11/2026 01:27:15Z |
| #24 frontend React | aberto | — |
| #26 `fix(streamlit): responsividade` | aberto | — |

`develop` agora está em `18eab91` (merge do #22). Todos os três PRs tinham base `develop`, o que confirma na prática a regra do CONTRIBUTING.

**Atenção:** a pendência que eu vinha citando — "atualizar o corpo do PR #22 de 304 para 319" — **não é mais um bloqueio de PR aberto**, porque o #22 foi mesclado. O corpo de um PR fechado ainda pode ser editado pelo autor, mas o certo agora é registrar a volumetria correta no cartão 09 / README, não condicionar um aceite a isso. Não leve "PR #22 aberto, aguardando aprovação" para o Discord.
