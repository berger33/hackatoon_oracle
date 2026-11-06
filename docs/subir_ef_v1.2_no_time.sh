#!/usr/bin/env bash
# Rode com: bash subir_ef_v1.2_no_time.sh
# Ambiente: Git Bash (Windows), WSL, Linux ou macOS. NAO e script para cmd.exe.
# REPO ENVOLVIDO: somente No-Country-simulation/g10-brasil-equipe-15_mediflow.
# O hackertoon_oracle NAO e clonado nem usado aqui.
set -euo pipefail

TIME_REPO="No-Country-simulation/g10-brasil-equipe-15_mediflow"
BRANCH="docs/ef-requisitos-v1.2"
DOWNLOADS="$HOME/mediflow_v1.2"

echo "==> 0/9 checando gh e identidade git"
gh auth status >/dev/null || { echo "Rode: gh auth login"; exit 1; }
git config user.name  >/dev/null || { echo "Rode: git config --global user.name  \"SEU NOME\""; exit 1; }
git config user.email >/dev/null || { echo "Rode: git config --global user.email \"SEU EMAIL\""; exit 1; }

echo "==> 1/9 baixando os 5 arquivos v1.2 do Drive para $DOWNLOADS"
mkdir -p "$DOWNLOADS"
cd "$DOWNLOADS"
# id, nome, tamanho minimo esperado
BAIXAR=(
  "1_VELN_O52rCLKfTUybKhP3lLBHIaXAZZ|MediFlow_Especificacao_Funcional_v1.2.pdf|70000"
  "1mwt2cJHRaMDK1y2HvHfQfIc_1n5o0ePG|MediFlow_Especificacao_Funcional_v1.2.md|50000"
  "1zTuCuCytiaihxlZya7zJCCTqAFq5lmg6|MediFlow_Analise_de_Requisitos_v1.2.pdf|50000"
  "1D8gnMt5J9YmOvH-cWtyiPObsmk5y2g2W|MediFlow_Analise_de_Requisitos_v1.2.md|28000"
  "1PHGEELl6KRNXh2ewARpYysZ1iuKQrKtQ|REGISTRO_DE_ALTERACOES_v1.2.pdf|10000"
)
for item in "${BAIXAR[@]}"; do
  IFS='|' read -r id nome minimo <<< "$item"
  if [ ! -s "$nome" ]; then curl -fL -sS -o "$nome" "https://drive.google.com/uc?export=download&id=$id"; fi
  bytes=$(wc -c < "$nome")
  if [ "$bytes" -lt "$minimo" ]; then
    echo "ERRO: $nome veio com $bytes bytes (esperado >= $minimo)."
    echo "Abra https://drive.google.com/drive/folders/1mkhJJDVcw2A7PLZUjIW_JpE1ksUNxX4h"
    echo "e baixe os arquivos pelo navegador para $DOWNLOADS, depois rode o script de novo."
    exit 1
  fi
  echo "    ok: $nome ($bytes bytes)"
done

echo "==> 2/9 clonando SOMENTE o repo do time + develop atualizada"
cd "$HOME"
if [ -d g10-brasil-equipe-15_mediflow/.git ]; then
  cd g10-brasil-equipe-15_mediflow
  git checkout develop && git pull origin develop
else
  git clone "https://github.com/$TIME_REPO.git"
  cd g10-brasil-equipe-15_mediflow
  git checkout develop
fi

echo "==> 3/9 criando a branch $BRANCH"
git checkout -B "$BRANCH"

echo "==> 4/9 copiando os 5 arquivos para docs/"
for f in MediFlow_Especificacao_Funcional_v1.2.pdf \
         MediFlow_Especificacao_Funcional_v1.2.md \
         MediFlow_Analise_de_Requisitos_v1.2.pdf \
         MediFlow_Analise_de_Requisitos_v1.2.md \
         REGISTRO_DE_ALTERACOES_v1.2.pdf; do
  cp "$DOWNLOADS/$f" docs/
done

echo "==> 5/9 criando docs/ESPECIFICACOES.md"
cat > docs/ESPECIFICACOES.md <<'EOF'
# Especificacoes vigentes do MediFlow

| Documento | Versao vigente | Data | Arquivos |
| --- | --- | --- | --- |
| Especificacao Funcional (EF/EPT) | **v1.2** | 05/11/2026 | `MediFlow_Especificacao_Funcional_v1.2.pdf` / `.md` |
| Analise de Requisitos | **v1.2** | 05/11/2026 | `MediFlow_Analise_de_Requisitos_v1.2.pdf` / `.md` |
| Registro de alteracoes | v1.2 | 05/11/2026 | `REGISTRO_DE_ALTERACOES_v1.2.pdf` |
| Brief original (fonte de precedencia 1) | `Projeto_oracle.pdf` | - | Google Drive da equipe |
| Contrato de Dados da Triagem | v1.0 | - | `docs/testes/CONTRATO_DE_DADOS.md` |

**Versoes obsoletas:** EF v1.0 e v1.1, Analise de Requisitos v1.1 e `EPT_MediFlow.pdf`
permanecem apenas como historico na pasta `Documentacao` do Google Drive e nao devem
ser usadas como referencia normativa.

A v1.2 realinha EF e Analise ao `Projeto_oracle.pdf` conforme a secao 2 da EF, sem
reduzir nenhum requisito obrigatorio do Brief e sem reverter decisoes da v1.1
(RN-08/ADR-001 de urgencia isolada, Anexo de 21/10/2026 e Contrato de Dados v1.0).
Decisoes D-01, D-02 e D-03 estao em `REGISTRO_DE_ALTERACOES_v1.2.pdf`.
EOF

echo "==> 6/9 criando corpo do PR FORA do repo (nao entra no commit)"
cat > "$DOWNLOADS/corpo_pr.md" <<'EOF'
## MediFlow - Descricao do Pull Request

### Tipo de alteracao
- [x] Documentacao ou diagramas (`docs`)

### O que foi implementado/modificado?
Publica a Especificacao Funcional v1.2 e a Analise de Requisitos v1.2 em `docs/`,
com o registro de alteracoes (D-01, D-02, D-03) e o indice `docs/ESPECIFICACOES.md`
que marca EF v1.0/v1.1, Analise v1.1 e EPT_MediFlow.pdf como obsoletos.
Revisao de alinhamento ao Projeto_oracle.pdf (fonte de precedencia 1, EF secao 2),
sem reduzir requisito obrigatorio do Brief e sem reverter RN-08/ADR-001.
Nao altera codigo, schemas, fixtures, `docs/testes/` nem `CONTRIBUTING.md`.

### Relacao com os Requisitos do Hackathon MediFlow
- [x] Outro: documentacao normativa e rastreabilidade com o Brief original

### Como isso foi testado?
1. `python -m pytest -q` executado localmente, suite verde (nenhum codigo alterado).
2. `git diff --cached --stat` confere que so entram arquivos novos em `docs/`.
3. Conferido que nenhum arquivo de `tests/fixtures/` ou `docs/testes/` foi tocado.

### Checklist antes de solicitar revisao
- [x] Minha branch esta atualizada com a `develop`.
- [x] O codigo segue as boas praticas e nao contem dados confidenciais.
- [x] Testei localmente e a aplicacao executa sem quebrar fluxos existentes.
- [x] Solicitei a revisao de pelo menos 1 integrante do time.
EOF

echo "==> 7/9 conferindo e preparando o commit"
git status
git add docs/MediFlow_Especificacao_Funcional_v1.2.pdf \
        docs/MediFlow_Especificacao_Funcional_v1.2.md \
        docs/MediFlow_Analise_de_Requisitos_v1.2.pdf \
        docs/MediFlow_Analise_de_Requisitos_v1.2.md \
        docs/REGISTRO_DE_ALTERACOES_v1.2.pdf \
        docs/ESPECIFICACOES.md
git diff --cached --stat

echo "==> 8/9 quality gate (venv + dependencias + pytest)"
if [ ! -d .venv ]; then python -m venv .venv; fi
if [ -f .venv/Scripts/activate ]; then source .venv/Scripts/activate; else source .venv/bin/activate; fi
pip install -q -r requirements.txt
python -m pytest -q || { echo "ERRO: suite falhou. Nada sera commitado."; exit 1; }

echo "==> 9/9 commit, push e PR"
git commit -m "docs(especificacao): publica EF e Analise de Requisitos v1.2 alinhadas ao Brief"
git push -u origin "$BRANCH"

EXISTENTE=$(gh pr list --repo "$TIME_REPO" --head "$BRANCH" --state open --json number --jq 'length')
if [ "$EXISTENTE" = "0" ]; then
  gh pr create --repo "$TIME_REPO" \
    --base develop \
    --head "$BRANCH" \
    --title "docs(especificacao): publica EF e Analise de Requisitos v1.2" \
    --body-file "$DOWNLOADS/corpo_pr.md" \
    --reviewer crisgdo
else
  echo "PR aberta para essa branch ja existe; nada a criar."
fi

echo "==> PRONTO. Falta o Approve de outro integrante antes do merge."
echo "    Acompanhe: gh pr view --json reviewDecision,reviews,state"
