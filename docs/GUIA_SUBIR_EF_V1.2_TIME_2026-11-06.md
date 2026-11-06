# Guia — subir EF e Requisitos v1.2 no repo do time, com PR aprovada por outra pessoa

**Data:** 06/11/2026 · **Para:** William
**Objetivo:** atualizar a documentação no GitHub, "remover a 1.1 e colocar a 1.2", gerando movimentação e um PR com Approve de outro integrante.
**Nenhuma branch, commit ou PR foi criada em repositório compartilhado.** Este é só o roteiro para você executar.

---

## 1. O que eu verifiquei (e uma correção)

Varredura em **todas as branches remotas e em todo o histórico** de `No-Country-simulation/g10-brasil-equipe-15_mediflow`:

```text
nenhum arquivo: *Especificacao* / *Analise* / *Requisitos* / *EPT_* / Projeto_oracle*
```

O que existe no repo do time são `docs/testes/` (AUDITORIA, CATÁLOGO, CONTRATO_DE_DADOS, Mapa, README, VISUAL_SCHEMAS) e **menções em texto** a "catálogo EPT v1.0 (§12)" em `ARQUITETURA.md:330,454`, `README.md:187`, `scripts/testar_simulacao_oci.py:163` e `src/api/service.py:195,204,257,675`. Ou seja: **as fixtures e a documentação de testes estão lá, mas a EPT/EF como arquivo não está**. Corrigindo o que eu disse antes: não havia EPT no repositório do time.

Onde cada versão está hoje:

| Lugar | EF | Análise de Requisitos | EPT |
| --- | --- | --- | --- |
| **Repo do time** (`develop` e qualquer branch) | ❌ nenhum arquivo | ❌ | ❌ (só citações "EPT v1.0 §12") |
| **Seu repo** `berger33/hackatoon_oracle` | `MediFlow_Especificacao_Funcional_v1.0.pdf` (tracked) | `MediFlow_-_Análise_de_Requisitos_v1.1.pdf` (tracked) | ❌ |
| **Drive** → `G10-BRASIL-equipe 15 / Documentação` | `MediFlow_Especificacao_Funcional_v1.1.pdf` | `MediFlow_-_Análise_de_Requisitos_v1.1.pdf` | `EPT_MediFlow.pdf` |
| **Nova** (Drive + seu `docs/v1.2/`) | **EF v1.2** PDF/MD/HTML | **Análise v1.2** PDF/MD/HTML | — |

`Projeto_oracle.pdf` (Brief) fica nos dois lugares e **não deve ser removido** — é a fonte de precedência 1.

### Duas consequências práticas

1. **O PR precisa ser no repo do time.** No seu `berger33/hackatoon_oracle` o único colaborador é `berger33` (você mesmo) — `gh api repos/berger33/hackatoon_oracle/collaborators` retorna só você. Não existe "outra pessoa" para aprovar lá, e o GitHub não deixa você aprovar o próprio PR. No repo do time há 5 integrantes (`crisgdo` aprovou os PRs #22, #23 e #25; `IzaCoelho1` é autora de PRs).
2. **Dentro desse PR não há 1.1 para deletar**, porque a 1.1 nunca esteve no repo do time. O PR é de **adição** da v1.2. A "remoção da 1.1" é uma limpeza separada, feita no **Drive** e no **seu repo** (seções 5 e 6). Para o PR registrar a substituição de forma honesta, inclua o `docs/ESPECIFICACOES.md` da seção 4, declarando v1.2 vigente e v1.1 obsoleta.

---

## 2. Regras do projeto que se aplicam

`CONTRIBUTING.md` (raiz do repo do time):

- §1: `develop` e `main` protegidas; branch de documentação = **`docs/*`**, criada a partir de `develop`, volta por PR.
- §2: `docs/` = "Documentação técnica e governança de QA"; `docs/testes/` = "Contrato Canônico, Catálogo dos 79 Fixtures e Auditorias". **Não misture**: a EF/Análise vão em `docs/`, não em `docs/testes/`.
- §4: `develop` atualizada → branch semântica → commits `docs:` → `python -m pytest` → push da sua branch → PR com **base `develop`, nunca `main`** → ≥ 1 Approve → apagar branch após merge.
- §6: nunca `--force` em `develop`/`main`; PRs enxutos (uma responsabilidade).
- `.github/pull_request_template.md`: preencher tipo, relação com requisitos, como testou, checklist.

> **Aviso:** os números de testes no CONTRIBUTING (208/245) e README (217) estão desatualizados; a regra de rodar a suíte vale, mas não corrija esses números neste PR (§6).

---

## 3. Passo 0 — baixar os arquivos v1.2 para a SUA máquina

⚠️ **Correção do guia anterior:** os caminhos `/home/user/hackatoon_oracle/...` são do sandbox da Arena, não do seu computador. Antes de copiar, obtenha os arquivos de uma destas formas:

```bash
# Opção A — clonar seu repo e pegar a pasta v1.2 (recomendado, já está publicado)
git clone https://github.com/berger33/hackatoon_oracle.git
cd hackatoon_oracle
git checkout arena/cc3a89ce-hackatoon-oracle
ls docs/v1.2/
```

Ou baixe pela pasta do Drive (`Download all`): https://drive.google.com/drive/folders/1mkhJJDVcw2A7PLZUjIW_JpE1ksUNxX4h

Arquivos que interessam: `MediFlow_Especificacao_Funcional_v1.2.pdf/.md`, `MediFlow_Analise_de_Requisitos_v1.2.pdf/.md` e `REGISTRO_DE_ALTERACOES_v1.2.md`.

---

## 4. Passo a passo — o PR no repo do time

```bash
# 1) clonar o repo do time (se ainda não tem) e entrar
git clone https://github.com/No-Country-simulation/g10-brasil-equipe-15_mediflow.git
cd g10-brasil-equipe-15_mediflow

# 2) conferir permissão e branch padrão
gh auth status
gh api repos/No-Country-simulation/g10-brasil-equipe-15_mediflow --jq '.permissions'
gh repo view No-Country-simulation/g10-brasil-equipe-15_mediflow --json defaultBranchRef

# 3) SEMPRE partir da develop atualizada  (CONTRIBUTING §4 Passo 1)
git checkout develop
git pull origin develop

# 4) branch de documentação  (§4 Passo 2)
git checkout -b docs/ef-requisitos-v1.2

# 5) copiar os arquivos para docs/ (raiz de docs, sem criar estrutura nova)
#    SUBSTITUA ~/hackatoon_oracle pelo caminho real na sua maquina
cp ~/hackatoon_oracle/docs/v1.2/MediFlow_Especificacao_Funcional_v1.2.pdf docs/
cp ~/hackatoon_oracle/docs/v1.2/MediFlow_Especificacao_Funcional_v1.2.md  docs/
cp ~/hackatoon_oracle/docs/v1.2/MediFlow_Analise_de_Requisitos_v1.2.pdf   docs/
cp ~/hackatoon_oracle/docs/v1.2/MediFlow_Analise_de_Requisitos_v1.2.md    docs/
cp ~/hackatoon_oracle/docs/v1.2/REGISTRO_DE_ALTERACOES_v1.2.md            docs/

# 6) criar o indice de versoes (conteudo logo abaixo)
#    use seu editor: nano docs/ESPECIFICACOES.md

# 7) conferir ANTES de commitar — nunca git add -A sem olhar
git status
git diff --stat

# 8) quality gate obrigatório (§4 Passo 4)
python -m pytest -q
# PR so de documentacao: a suite deve continuar verde. Se falhar, pare.

# 9) commit atomico, Conventional Commits  (§4 Passo 3)
git add docs/MediFlow_Especificacao_Funcional_v1.2.pdf \
        docs/MediFlow_Especificacao_Funcional_v1.2.md \
        docs/MediFlow_Analise_de_Requisitos_v1.2.pdf \
        docs/MediFlow_Analise_de_Requisitos_v1.2.md \
        docs/REGISTRO_DE_ALTERACOES_v1.2.md \
        docs/ESPECIFICACOES.md
git commit -m "docs(especificacao): publica EF e Analise de Requisitos v1.2 alinhadas ao Brief"

# 10) push da SUA branch — nunca push em develop  (§4 Passo 5)
git push -u origin docs/ef-requisitos-v1.2

# 11) abrir o PR  (§4 Passo 6). Para a primeira vez, use --web:
gh pr create --web
# ...ou direto pelo CLI:
gh pr create \
  --repo No-Country-simulation/g10-brasil-equipe-15_mediflow \
  --base develop \
  --head docs/ef-requisitos-v1.2 \
  --title "docs(especificacao): publica EF e Analise de Requisitos v1.2" \
  --body-file corpo_pr.md \
  --reviewer crisgdo
```

Com `--web`, o GitHub abre com o template do time já carregado e a base `develop` pré-selecionada. **Base** = para onde vai (`develop`); **head** = de onde vem (sua branch); **Reviewers** = quem dá o Approve.

### Conteúdo sugerido de `docs/ESPECIFICACOES.md`

```markdown
# Especificações vigentes do MediFlow

| Documento | Versão vigente | Data | Arquivos |
| --- | --- | --- | --- |
| Especificação Funcional (EF/EPT) | **v1.2** | 05/11/2026 | `MediFlow_Especificacao_Funcional_v1.2.pdf` / `.md` |
| Análise de Requisitos | **v1.2** | 05/11/2026 | `MediFlow_Analise_de_Requisitos_v1.2.pdf` / `.md` |
| Registro de alterações | v1.2 | 05/11/2026 | `REGISTRO_DE_ALTERACOES_v1.2.md` |
| Brief original (fonte de precedência 1) | `Projeto_oracle.pdf` | — | Google Drive da equipe |
| Contrato de Dados da Triagem | v1.0 | — | `docs/testes/CONTRATO_DE_DADOS.md` |

**Versões obsoletas:** EF v1.0 e v1.1, Análise de Requisitos v1.1 e `EPT_MediFlow.pdf`
permanecem apenas como histórico na pasta `Documentação` do Google Drive e não devem
ser usadas como referência normativa.

A v1.2 realinha EF e Análise ao `Projeto_oracle.pdf` conforme a seção 2 da EF,
sem reduzir nenhum requisito obrigatório do Brief e sem reverter decisões da v1.1
(RN-08/ADR-001 de urgência isolada, Anexo de 21/10/2026 e Contrato de Dados v1.0).
Decisões D-01, D-02 e D-03 estão detalhadas em `REGISTRO_DE_ALTERACOES_v1.2.md`.
```

> Esse arquivo é o que faz o PR "atualizar a documentação" de fato: ele declara a v1.1 como obsoleta dentro do próprio repositório, já que não havia arquivo 1.1 lá para deletar.

### Corpo do PR (preenche `.github/pull_request_template.md`)

```markdown
## 🏥 MediFlow - Descrição do Pull Request

### 📌 Tipo de alteração
- [x] Documentação ou diagramas (`docs`)

### 📝 O que foi implementado/modificado?
Publica a Especificação Funcional v1.2 e a Análise de Requisitos v1.2 em `docs/`,
com o registro de alterações (D-01, D-02, D-03) e o índice `docs/ESPECIFICACOES.md`
que marca EF v1.0/v1.1, Análise v1.1 e EPT_MediFlow.pdf como obsoletos.
Revisão de alinhamento ao Projeto_oracle.pdf (fonte de precedência 1, EF §2),
sem reduzir requisito obrigatório do Brief e sem reverter RN-08/ADR-001.
Não altera código, schemas, fixtures, `docs/testes/` nem `CONTRIBUTING.md`.

### 🎯 Relação com os Requisitos do Hackathon MediFlow
- [x] Outro: documentação normativa e rastreabilidade com o Brief original

### 🧪 Como isso foi testado?
1. `python -m pytest -q` executado localmente, suíte verde (nenhum código alterado).
2. `git diff --stat` confere que só entram arquivos novos em `docs/`.
3. Conferido que nenhum arquivo de `tests/fixtures/` ou `docs/testes/` foi tocado.

### ✅ Checklist antes de solicitar revisão
- [x] Minha branch está atualizada com a `develop`.
- [x] O código segue as boas práticas e não contém dados confidenciais.
- [x] Testei localmente e a aplicação executa sem quebrar fluxos existentes.
- [x] Solicitei a revisão de pelo menos 1 integrante do time.
```

---

## 5. Como conseguir o Approve de outra pessoa

1. Ao abrir o PR, marque um revisor no campo **Reviewers** (ou `--reviewer crisgdo`). Logins confirmados no histórico de PRs: `crisgdo` (aprovou #22, #23, #25) e `IzaCoelho1`. Para Luciana e Giovane, use o autocomplete do GitHub ou pergunte o login no grupo — não invente.
2. Avise no Discord com o link do PR e o que precisa ser olhado (é um PR só de docs, revisão rápida).
3. **Você não pode aprovar o próprio PR** — e, mesmo sendo `admin`, não deve fazer merge sem Approve: a regra do §1/§4 exige ≥ 1 colega.
4. Acompanhe:
   ```bash
   gh pr view --json number,reviewDecision,reviews,state \
     --jq '{number,reviewDecision,state,reviews:[.reviews[]|{author:.author.login,state}]}'
   gh pr checks
   ```
5. Com `reviewDecision = APPROVED`, faça o merge (`gh pr merge <NUM> --merge`) pela interface ou CLI, **apague a branch remota** (§4 Passo 6) e atualize seu local: `git checkout develop && git pull origin develop`.
6. Para ver a movimentação: `gh pr list --state all`, ou a aba *Insights → Pulse* do repo.

---

## 6. Limpeza da 1.1 (fora do PR, em dois lugares)

### 6.1 Google Drive — pasta `Documentação`

Link da pasta: https://drive.google.com/drive/folders/1v9ffzqE_x5BcgyOU0L_s4BkwD896Lyn2

Crie uma subpasta `Historico/` e **mova** para lá (não apague de vez, para manter rastreabilidade):

- `MediFlow_Especificacao_Funcional_v1.1.pdf` (id `1brgsHPywft5Q1hrcFB8t9C08YmnviWa8`)
- `MediFlow_-_Análise_de_Requisitos_v1.1.pdf` (id `1G_Y_enZAB8cnIgWMu4JBk-aBSToGAtHl`)
- `EPT_MediFlow.pdf` (id `1pDaruUCpfiiOsfHZoZzyvZFG_CQlTI9w`)

**Mantenha** `Projeto_oracle.pdf` (id `1fVmAfGIv-hr8MGvEcSfgd1Nl3-aqtCJC`) e a pasta `MediFlow v1.2 - 05-11-2026` que já publicamos. Se quiser, mova os 3 PDFs da pasta v1.2 para `Documentação` também, para ficar tudo no mesmo nível.

> Isso não gera PR nem Approve — é só arrumação da pasta de referência.

### 6.2 Seu repo `berger33/hackatoon_oracle` (opcional, commit separado)

Lá existe sim uma versão antiga trackeada. Se quiser "remover a 1.1" também no seu repo:

```bash
cd hackatoon_oracle
git checkout main   # ou a branch que voce usa
git pull origin main
git checkout -b docs/remove-versoes-obsoletas

git rm "MediFlow_Especificacao_Funcional_v1.0.pdf" \
       "MediFlow_-_Análise_de_Requisitos_v1.1.pdf"
# NAO remova Projeto_oracle.pdf
git commit -m "docs: remove EF v1.0 e Analise v1.1 obsoletas, mantem v1.2 em docs/"
git push -u origin docs/remove-versoes-obsoletas
gh pr create --base main --head docs/remove-versoes-obsoletas \
  --title "docs: remove versoes obsoletas de EF e Requisitos" --web
```

Atenção: como você é o único colaborador desse repo, **esse PR não terá Approve de outra pessoa** a menos que você convide alguém em *Settings → Collaborators*. Para o seu objetivo de "PR aprovada por outra pessoa", conte apenas com o PR do repo do time (seção 4).

---

## 7. Checklist final

- [ ] Branch `docs/ef-requisitos-v1.2` criada a partir de `develop` atualizada.
- [ ] Só arquivos novos em `docs/`; nenhum arquivo de `docs/testes/`, `tests/fixtures/` ou `src/schemas/`.
- [ ] `docs/ESPECIFICACOES.md` declara v1.2 vigente e v1.1 obsoleta.
- [ ] `python -m pytest -q` verde antes do push.
- [ ] Commit com prefixo `docs:`.
- [ ] PR com **base `develop`**, corpo seguindo o template, reviewer marcado.
- [ ] Approve de outro integrante recebido **antes** do merge.
- [ ] Sem `git push --force`; branch apagada depois do merge.
- [ ] 1.1 movida para `Historico/` no Drive; `Projeto_oracle.pdf` mantido.

---

## 8. Estado do repo do time em 06/11/2026

- `develop` em `18eab91` (merge do PR #22).
- PRs **#22, #23 e #25 mesclados** em 05/11 23:57Z, 06/11 01:09Z e 01:27Z — todos com base `develop`.
- Abertos: **#24** (`feature/frontend-react-base`) e **#26** (`fix/streamlit-responsividade`), ambos para `develop` e sem reviewers solicitados no momento.
- Branch protection não é consultável pelo token dessa integração (`403 Resource not accessible by integration`); você é `admin`, então consegue ver as regras em *Settings → Branches* no navegador. As regras documentadas no `CONTRIBUTING.md` são as que valem para o time.
