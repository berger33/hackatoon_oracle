#!/usr/bin/env python3
"""Gera o pacote ZIP para download (dist/hackatoon_oracle-mediflow-completo.zip).

Empacota tudo o que está na árvore do projeto, inclusive arquivos ignorados pelo Git
(como o Validacao_ArquivoGrande.pdf de 25 MB), e deixa de fora só o que é cache ou
histórico de Git. Mantém o mesmo layout de sempre: LEIA-ME.txt na raiz do ZIP.

Garantias:
  - nomes em UTF-8 de verdade (flag 0x800); o ZIP antigo saía com "An├ílise";
  - datas fixas dentro do ZIP: rodar duas vezes gera o mesmo arquivo;
  - a contagem de arquivos e o tamanho em dist/README.md são atualizados aqui,
    para o texto nunca mais declarar um número diferente do conteúdo.

Uso:
    python3 tools/gerar_pacote.py
"""
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(ROOT, "dist", "hackatoon_oracle-mediflow-completo.zip")
LEIA_ME = os.path.join(ROOT, "dist", "LEIA-ME.txt")
README_DIST = os.path.join(ROOT, "dist", "README.md")

#: Pastas que nunca entram no pacote.
EXCLUIR_PASTAS = {".git", "dist", "__pycache__", ".pytest_cache", ".venv", "venv"}
#: Arquivos de sistema que nunca entram no pacote.
EXCLUIR_ARQUIVOS = {".DS_Store", "Thumbs.db"}
#: Data fixa para o ZIP ser reprodutível (ZIP não guarda hora antes de 1980).
DATA_FIXA = (2026, 10, 20, 0, 0, 0)


def arquivos_do_projeto():
    """Lista (caminho_no_zip, caminho_no_disco) em ordem estável."""
    itens = []
    for raiz, pastas, nomes in os.walk(ROOT):
        pastas[:] = sorted(p for p in pastas if p not in EXCLUIR_PASTAS)
        for nome in sorted(nomes):
            if nome in EXCLUIR_ARQUIVOS or nome.endswith(".pyc"):
                continue
            disco = os.path.join(raiz, nome)
            if os.path.abspath(disco) == os.path.abspath(SAIDA):
                continue
            relativo = os.path.relpath(disco, ROOT).replace(os.sep, "/")
            itens.append((relativo, disco))
    # LEIA-ME.txt fica na raiz do ZIP, como sempre
    itens.append(("LEIA-ME.txt", LEIA_ME))
    return sorted(itens)


def main():
    itens = arquivos_do_projeto()
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    tmp = SAIDA + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for nome_zip, disco in itens:
            info = zipfile.ZipInfo(nome_zip, date_time=DATA_FIXA)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(disco, "rb") as fh:
                z.writestr(info, fh.read(), compresslevel=9)
    os.replace(tmp, SAIDA)

    tamanho_mb = os.path.getsize(SAIDA) / (1024 * 1024)
    n = len(itens)
    print(f"ok: {SAIDA} — {n} arquivos, {tamanho_mb:.1f} MB")

    # mantém a contagem declarada em dist/README.md igual ao conteúdo real
    with open(README_DIST, encoding="utf-8") as fh:
        texto = fh.read()
    novo = re.sub(r"\(\d+(?:[.,]\d+)? MB · \d+ arquivos\)",
                  f"({tamanho_mb:.0f} MB · {n} arquivos)", texto, count=1)
    if novo != texto:
        with open(README_DIST, "w", encoding="utf-8") as fh:
            fh.write(novo)
        print("dist/README.md: contagem atualizada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
