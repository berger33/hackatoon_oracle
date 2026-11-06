#!/usr/bin/env python3
"""Gera HTML e PDF a partir dos Markdown v1.2 (md -> html -> pdf via xhtml2pdf)."""
from pathlib import Path
import html as html_lib
import markdown
from xhtml2pdf import pisa

BASE = Path(__file__).resolve().parent

CSS = """
@page { size: a4; margin: 1.7cm 1.6cm 1.8cm 1.6cm; }
body { font-family: Helvetica; font-size: 9.5pt; line-height: 1.42; color: #1b2430; }
h1 { font-size: 20pt; color: #0b4f6c; margin: 0 0 6pt 0; }
h2 { font-size: 13.5pt; color: #0b4f6c; margin: 16pt 0 6pt 0;
     border-bottom: 0.6pt solid #b9d4de; padding-bottom: 3pt; page-break-after: avoid; }
h3 { font-size: 11pt; color: #125e7d; margin: 11pt 0 4pt 0; page-break-after: avoid; }
h4 { font-size: 10pt; color: #125e7d; margin: 9pt 0 3pt 0; page-break-after: avoid; }
p { margin: 0 0 6pt 0; text-align: justify; }
ul, ol { margin: 0 0 7pt 0; padding-left: 16pt; }
li { margin-bottom: 2pt; }
strong { color: #0a3f57; }
blockquote { background-color: #f0f7fa; border-left: 2.5pt solid #2b8caa;
             padding: 6pt 9pt; margin: 7pt 0; color: #264653; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt 0; font-size: 8.3pt; }
th { background-color: #0b4f6c; color: #ffffff; text-align: left;
     padding: 4pt 5pt; border: 0.4pt solid #7fa8b8; }
td { padding: 3.5pt 5pt; border: 0.4pt solid #c6d8e0; vertical-align: top; }
tr { page-break-inside: avoid; }
code { font-family: Courier; font-size: 8.2pt; color: #8a2b3c; }
pre { background-color: #f5f6f8; border: 0.4pt solid #d8dde2; padding: 6pt;
      font-family: Courier; font-size: 7.8pt; line-height: 1.25; margin: 5pt 0 9pt 0;
      white-space: pre-wrap; }
pre code { font-size: 7.8pt; color: #24313d; }
hr { border: 0; border-top: 0.6pt solid #c6d8e0; margin: 12pt 0; }
a { color: #0b62a4; }
"""

# xhtml2pdf/Helvetica (Latin-1) nao tem estes glifos; troca por equivalentes seguros.
SAFE = {
    "\u2014": "-", "\u2013": "-", "\u201c": '"', "\u201d": '"',
    "\u2018": "'", "\u2019": "'", "\u2026": "...", "\u2192": "->",
    "\u00b7": "-", "\u2265": ">=", "\u2264": "<=", "\u00a0": " ",
    "\u2022": "-", "\u00bb": ">>", "\u00ab": "<<",
}


def to_html(md_text: str, title: str) -> str:
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
    )
    return (
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
        f"<title>{html_lib.escape(title)}</title><style>{CSS}</style></head>"
        f"<body>{body}</body></html>"
    )


def main() -> None:
    docs = [
        ("MediFlow_Especificacao_Funcional_v1.2", "MediFlow - Especificacao Funcional v1.2"),
        ("MediFlow_Analise_de_Requisitos_v1.2", "MediFlow - Analise de Requisitos v1.2"),
        ("REGISTRO_DE_ALTERACOES_v1.2", "Registro de Alteracoes v1.2"),
    ]
    for stem, title in docs:
        md = (BASE / f"{stem}.md").read_text(encoding="utf-8")
        page = to_html(md, title)
        (BASE / f"{stem}.html").write_text(page, encoding="utf-8")

        pdf_html = page
        for bad, good in SAFE.items():
            pdf_html = pdf_html.replace(bad, good)
        # "<" solto em celulas de tabela pode virar tag; protege apenas sequencias "< espaco".
        pdf_html = pdf_html.replace("< 0.85", "&lt; 0.85").replace("< limiar", "&lt; limiar")
        out = BASE / f"{stem}.pdf"
        with out.open("wb") as fh:
            result = pisa.CreatePDF(pdf_html, dest=fh, encoding="utf-8")
        if result.err:
            raise SystemExit(f"Falha ao gerar {out.name}: {result.err} erros")
        print(f"{out.name}: {out.stat().st_size} bytes")

    index = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>MediFlow - Documentos v1.2</title>
<style>
body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
       max-width: 860px; margin: 40px auto; padding: 0 22px; color: #1b2430; line-height: 1.55; }
h1 { color: #0b4f6c; font-size: 28px; margin-bottom: 4px; }
.sub { color: #5b6b78; margin-top: 0; }
h2 { color: #0b4f6c; font-size: 19px; margin-top: 30px; border-bottom: 1px solid #b9d4de; padding-bottom: 6px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0 22px; font-size: 14px; }
th { background: #0b4f6c; color: white; text-align: left; padding: 9px 10px; }
td { border: 1px solid #d3e0e6; padding: 9px 10px; }
a { color: #0b62a4; text-decoration: none; font-weight: 600; }
a:hover { text-decoration: underline; }
.note { background: #f0f7fa; border-left: 4px solid #2b8caa; padding: 12px 16px; margin: 20px 0; }
code { background: #eef2f5; padding: 1px 5px; border-radius: 3px; font-size: 13px; }
ul { padding-left: 20px; }
</style></head><body>
<h1>MediFlow - Documentos v1.2</h1>
<p class="sub">Especificacao Funcional e Analise de Requisitos | Revisao de 05/11/2026 | William (QA &amp; Requirements Lead)</p>
<div class="note"><strong>Referencia de precedencia:</strong> <code>Projeto_oracle.pdf</code> (documento original do projeto), conforme a secao 2 da EF. Esta revisao realinha os dois documentos ao Brief; nao reduz nenhum requisito obrigatorio dele.</div>
<h2>Documentos</h2>
<table><tr><th>Documento</th><th>Leitura</th><th>Download / fonte</th></tr>
<tr><td><strong>Especificacao Funcional v1.2</strong></td>
<td><a href="MediFlow_Especificacao_Funcional_v1.2.html">HTML</a> &middot; <a href="MediFlow_Especificacao_Funcional_v1.2.pdf">PDF</a></td>
<td><a href="MediFlow_Especificacao_Funcional_v1.2.pdf">PDF</a> &middot; <a href="MediFlow_Especificacao_Funcional_v1.2.md">Markdown</a></td></tr>
<tr><td><strong>Analise de Requisitos v1.2</strong></td>
<td><a href="MediFlow_Analise_de_Requisitos_v1.2.html">HTML</a> &middot; <a href="MediFlow_Analise_de_Requisitos_v1.2.pdf">PDF</a></td>
<td><a href="MediFlow_Analise_de_Requisitos_v1.2.pdf">PDF</a> &middot; <a href="MediFlow_Analise_de_Requisitos_v1.2.md">Markdown</a></td></tr>
<tr><td><strong>Registro de alteracoes v1.2</strong></td>
<td><a href="REGISTRO_DE_ALTERACOES_v1.2.html">HTML</a> &middot; <a href="REGISTRO_DE_ALTERACOES_v1.2.pdf">PDF</a></td>
<td><a href="REGISTRO_DE_ALTERACOES_v1.2.md">Markdown</a></td></tr></table>
<h2>O que mudou</h2>
<ul>
<li><strong>D-01</strong> - continuidade entre processos (retomada apos reiniciar a API) registrada como fora do escopo obrigatorio do MVP; RNF-03 delimitado a falhas dentro do mesmo processo.</li>
<li><strong>D-02</strong> - decisao, destino, alerta e persistencia ficam no resultado estruturado; sem evento proprio no historico no MVP.</li>
<li><strong>D-03</strong> - integracao ativa com OCI comprovada por escrita/leitura byte a byte no bucket + suite automatizada; E2E por cliente HTTP real no ambiente final e reforco de QA dispensado no MVP.</li>
<li>202 + consulta por ID identificado como decisao da equipe (EF secao 15, item 6), nao exigencia do Brief; matriz de rastreabilidade com coluna de origem.</li>
</ul>
<p><strong>Ressalvas mantidas:</strong> <code>src/api/routes.py</code> nao e mera delegacao (L195-213); a limitacao de restart esta documentada, nao escondida; evidencia vigente da suite = 319 aprovados, 1 ignorado.</p>
<p><strong>Unica pendencia que nao e do QA:</strong> atualizar o corpo do PR #22 de 304 para 319 aprovados, 1 ignorado.</p>
</body></html>
"""
    (BASE / "index.html").write_text(index, encoding="utf-8")
    print("index.html gerado")


if __name__ == "__main__":
    main()
