#!/usr/bin/env python3
"""Gera o PDF consolidado das EPTs (Especificacoes de Procedimento de Teste).

Le todos os `docs/epts/EPT-*.md`, em ordem, e produz `docs/epts/EPTs_MediFlow.pdf`
com capa, indice e o conteudo integral de cada EPT.

Uso:
    python3 tools/gerar_epts_pdf.py                 # todos os EPT-*.md
    python3 tools/gerar_epts_pdf.py --sem-capa      # sem capa nem indice

O renderizador cobre o subconjunto de Markdown usado nos documentos do repo:
titulos (#, ##, ###), paragrafos, listas (- e 1.), tabelas (| ... |), blocos de
codigo (```), citacoes (>) e linhas horizontais (---). A formatacao inline
aceita `codigo`, **negrito** e *italico*.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, ListFlowable,
                                ListItem, PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle, XPreformatted)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_EPTS = os.path.join(ROOT, "docs", "epts")
OUT = os.path.join(DIR_EPTS, "EPTs_MediFlow.pdf")

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DJ", f"{FONT_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DJB", f"{FONT_DIR}/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DJM", f"{FONT_DIR}/DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJB", italic="DJ", boldItalic="DJB")

INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#D1D5DB")
SOFT = colors.HexColor("#F9FAFB")
RED = colors.HexColor("#B42318")
TINT = colors.HexColor("#FEF2F2")

# ---------------------------------------------------------------- estilos

S = {
    "h1": ParagraphStyle("h1", fontName="DJB", fontSize=17, leading=21, textColor=INK,
                         spaceBefore=0, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="DJB", fontSize=11.5, leading=15, textColor=RED,
                         spaceBefore=14, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName="DJB", fontSize=9.8, leading=13, textColor=INK,
                         spaceBefore=10, spaceAfter=4),
    "p": ParagraphStyle("p", fontName="DJ", fontSize=8.8, leading=12.6, textColor=INK,
                        alignment=TA_LEFT, spaceBefore=0, spaceAfter=6),
    "li": ParagraphStyle("li", fontName="DJ", fontSize=8.8, leading=12.4, textColor=INK,
                         spaceAfter=2),
    "quote": ParagraphStyle("quote", fontName="DJ", fontSize=8.4, leading=12, textColor=MUTED,
                            leftIndent=10, spaceBefore=2, spaceAfter=8),
    "code": ParagraphStyle("code", fontName="DJM", fontSize=7.2, leading=9.6, textColor=INK),
    "th": ParagraphStyle("th", fontName="DJB", fontSize=7.4, leading=9.6, textColor=colors.white),
    "td": ParagraphStyle("td", fontName="DJ", fontSize=7.4, leading=9.8, textColor=INK),
    "capa_t": ParagraphStyle("capa_t", fontName="DJB", fontSize=26, leading=31, textColor=INK),
    "capa_s": ParagraphStyle("capa_s", fontName="DJ", fontSize=11.5, leading=16, textColor=MUTED),
    "capa_h": ParagraphStyle("capa_h", fontName="DJB", fontSize=11, leading=15, textColor=INK,
                             spaceBefore=14, spaceAfter=6),
}


# ------------------------------------------------------- markdown -> fluxos

def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    """Converte `codigo`, **negrito** e *italico* para tags do reportlab."""
    out, buf, i = [], "", 0
    while i < len(text):
        ch = text[i]
        if ch == "`":
            j = text.find("`", i + 1)
            if j == -1:
                buf += ch
                i += 1
                continue
            out.append(_esc(buf))
            out.append(f'<font face="DJM" size="7.6">{_esc(text[i + 1:j])}</font>')
            buf, i = "", j + 1
        elif text.startswith("**", i):
            j = text.find("**", i + 2)
            if j == -1:
                buf += ch
                i += 1
                continue
            out.append(_esc(buf))
            out.append(f"<b>{_esc(text[i + 2:j])}</b>")
            buf, i = "", j + 2
        elif ch == "*" and not text.startswith("**", i):
            j = text.find("*", i + 1)
            if j == -1:
                buf += ch
                i += 1
                continue
            out.append(_esc(buf))
            out.append(f"<i>{_esc(text[i + 1:j])}</i>")
            buf, i = "", j + 1
        else:
            buf += ch
            i += 1
    out.append(_esc(buf))
    return "".join(out)


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\|[\s:|-]+\|?", line.strip()))


def _table(rows: list[list[str]], avail: float) -> Table:
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    header, body = rows[0], rows[1:]

    def par(cell: str, style):
        return Paragraph(inline(cell) or "&nbsp;", style)

    data = [[par(c, S["th"]) for c in header]] + [[par(c, S["td"]) for c in r] for r in body]
    widths = _col_widths(rows, avail, ncol)
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), SOFT))
    t.setStyle(TableStyle(style))
    return t


def _cell_widths(rows: list[list[str]], ncol: int, size: float = 7.4) -> tuple[list[float], list[float]]:
    """Largura desejada e largura minima (a maior palavra) de cada coluna."""
    desejado, minimo = [], []
    for c in range(ncol):
        d = m = 0.0
        for r in rows:
            if c >= len(r):
                continue
            texto = inline(r[c])
            d = max(d, pdfmetrics.stringWidth(re.sub(r"<[^>]+>", "", texto), "DJ", size))
            for palavra in re.sub(r"<[^>]+>", "", texto).split():
                m = max(m, pdfmetrics.stringWidth(palavra, "DJ", size))
        desejado.append(d + 10)
        minimo.append(min(d + 10, m + 10))
    return desejado, minimo


def _col_widths(rows: list[list[str]], avail: float, ncol: int) -> list[float]:
    """Distribui a largura disponivel: comeca pelo minimo de cada coluna e
    reparte o resto proporcionalmente ao que cada uma pede."""
    desejado, minimo = _cell_widths(rows, ncol)
    maximo = 0.46 * avail

    if sum(minimo) >= avail:
        soma = sum(minimo)
        return [avail * w / soma for w in minimo]

    larguras = list(minimo)
    resto = avail - sum(minimo)
    folga = [max(0.0, min(d, maximo) - m) for d, m in zip(desejado, minimo)]
    soma_folga = sum(folga)
    if soma_folga > 0:
        for i, f in enumerate(folga):
            larguras[i] += resto * f / soma_folga
    else:
        for i in range(ncol):
            larguras[i] += resto / ncol

    sobra = avail - sum(larguras)
    if abs(sobra) > 0.01:
        alvo = larguras.index(max(w for w in larguras if w < maximo)) if any(w < maximo for w in larguras) else 0
        larguras[alvo] += sobra
    return larguras


def render(md: str, avail: float) -> list:
    """Converte o Markdown em uma lista de fluxos do reportlab."""
    fluxos: list = []
    lines = md.splitlines()
    i, n = 0, len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # linha em branco
        if not stripped:
            i += 1
            continue

        # bloco de codigo
        if stripped.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            code = XPreformatted(_esc("\n".join(buf)), S["code"])
            box = Table([[code]], colWidths=[avail], hAlign="LEFT")
            box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.4, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            fluxos.append(KeepTogether([box, Spacer(1, 7)]))
            continue

        # linha horizontal
        if re.fullmatch(r"-{3,}", stripped):
            rule = Table([[""]], colWidths=[avail], rowHeights=[1], hAlign="LEFT")
            rule.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.6, LINE)]))
            fluxos.append(Spacer(1, 6))
            fluxos.append(rule)
            fluxos.append(Spacer(1, 8))
            i += 1
            continue

        # tabela
        if stripped.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                if not _is_separator(lines[i]):
                    rows.append(_split_row(lines[i]))
                i += 1
            if rows:
                fluxos.append(Spacer(1, 2))
                fluxos.append(_table(rows, avail))
                fluxos.append(Spacer(1, 9))
            continue

        # titulos
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            nivel, texto = len(m.group(1)), m.group(2).strip()
            est = S["h1"] if nivel == 1 else S["h2"] if nivel == 2 else S["h3"]
            fluxos.append(Paragraph(inline(texto), est))
            i += 1
            continue

        # citacao
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            fluxos.append(Paragraph(inline(" ".join(buf)), S["quote"]))
            continue

        # lista com marcador
        if re.match(r"^[-*+]\s+", stripped):
            itens = []
            while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                itens.append(Paragraph(inline(re.sub(r"^[-*+]\s+", "", lines[i].strip())), S["li"]))
                i += 1
            fluxos.append(ListFlowable([ListItem(it, leftIndent=12) for it in itens],
                                       bulletType="bullet", bulletFontSize=7,
                                       leftIndent=12, spaceAfter=6))
            continue

        # lista numerada
        if re.match(r"^\d+[.)]\s+", stripped):
            itens = []
            while i < n and re.match(r"^\d+[.)]\s+", lines[i].strip()):
                itens.append(Paragraph(inline(re.sub(r"^\d+[.)]\s+", "", lines[i].strip())), S["li"]))
                i += 1
            fluxos.append(ListFlowable([ListItem(it, leftIndent=16) for it in itens],
                                       bulletType="1", bulletFontSize=7.6,
                                       leftIndent=16, spaceAfter=6))
            continue

        # paragrafo
        buf = []
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,4}\s|[-*+]\s|\d+[.)]\s|\||>|```|-{3,}$)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        fluxos.append(Paragraph(inline(" ".join(buf)), S["p"]))

    return fluxos


# ------------------------------------------------------------- cabecalhos

def cabecalho(md: str) -> dict:
    """Extrai o campo/valor da primeira tabela do arquivo (o cabecalho da EPT)."""
    linhas = md.splitlines()
    for i, l in enumerate(linhas):
        if l.strip().startswith("|"):
            dados = {}
            j = i
            while j < len(linhas) and linhas[j].strip().startswith("|"):
                if not _is_separator(linhas[j]) and not linhas[j].strip().startswith("| ---"):
                    c = _split_row(linhas[j])
                    if len(c) >= 2:
                        chave = c[0].strip("* ").strip()
                        dados[chave] = c[1]
                j += 1
            return dados
    return {}


def titulo_do(md: str, padrao: str) -> str:
    for l in md.splitlines():
        if l.startswith("# "):
            return l[2:].strip()
    return padrao


# ------------------------------------------------------------------ capa

def capa(paths: list[str], data: str) -> list:
    hoje = data
    metas = [cabecalho(open(p, encoding="utf-8").read()) for p in paths]
    titulos = [titulo_do(open(p, encoding="utf-8").read(), os.path.basename(p)) for p in paths]

    f: list = [Spacer(1, 120)]
    f.append(Paragraph("MediFlow", S["capa_s"]))
    f.append(Paragraph("Especificações de<br/>Procedimento de Teste", S["capa_t"]))
    f.append(Spacer(1, 14))
    f.append(Paragraph("Hackathon ONE G10 — Oracle Next Education &amp; Alura", S["capa_s"]))
    f.append(Paragraph(f"Edição de {hoje} · {len(paths)} EPT(s) nesta edição", S["capa_s"]))
    f.append(Spacer(1, 26))

    linhas = [["EPT", "Origem", "Requisitos", "Status"]]
    for meta, tit in zip(metas, titulos):
        ept = tit.split("—")[0].strip()
        linhas.append([
            ept,
            meta.get("Origem", "—"),
            meta.get("Requisitos", "—"),
            meta.get("Status", "—"),
        ])
    f.append(Paragraph("Índice desta edição", S["capa_h"]))
    f.append(_table(linhas, 468))
    f.append(Spacer(1, 18))
    f.append(Paragraph(
        "Cada EPT descreve o procedimento para provar um caso da Especificação Funcional v1.0. "
        "A massa de dados vem de <font face='DJM' size='9'>tests/fixtures/</font> e o resultado "
        "esperado é o <font face='DJM' size='9'>expected.json</font> de cada fixture.", S["p"]))
    f.append(PageBreak())
    return f


ORDEM_FAMILIA = {"D": 0, "A": 1, "E": 2, "R": 3}
DATA_EDICAO = "21/10/2026"   # fixa: o PDF tem de ser reproduzível, como os demais geradores


def ordem(caminho: str) -> tuple:
    """D antes de A antes de E antes de R; dentro da familia, ordem numerica."""
    nome = os.path.basename(caminho)
    m = re.match(r"EPT-([DAER])(\d+)", nome)
    if not m:
        return (9, 0, nome)
    return (ORDEM_FAMILIA.get(m.group(1), 9), int(m.group(2)), nome)


# ------------------------------------------------------------------- main

def _rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("DJ", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(42, 26, "MediFlow — EPTs · Hackathon ONE G10 · dados fictícios")
    canvas.drawRightString(A4[0] - 42, 26, f"página {canvas.getPageNumber()}")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(42, 38, A4[0] - 42, 38)
    canvas.restoreState()


def main() -> int:
    ap = argparse.ArgumentParser(description="Gera o PDF consolidado das EPTs.")
    ap.add_argument("--sem-capa", action="store_true", help="omite capa e índice")
    ap.add_argument("--data", default=DATA_EDICAO, help="data impressa na capa (padrão: fixa, para reprodutibilidade)")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(DIR_EPTS, "EPT-*.md")), key=ordem)
    if not paths:
        print("Nenhum arquivo EPT-*.md encontrado em docs/epts/.")
        return 1

    doc = BaseDocTemplate(OUT, pagesize=A4,
                          leftMargin=42, rightMargin=42, topMargin=46, bottomMargin=48,
                          title="MediFlow — Especificações de Procedimento de Teste",
                          author="hackatoon_oracle")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="corpo")
    doc.addPageTemplates([PageTemplate(id="todas", frames=[frame], onPage=_rodape)])

    avail = doc.width
    fluxos: list = []
    if not args.sem_capa:
        fluxos += capa(paths, args.data)

    for k, p in enumerate(paths):
        md = open(p, encoding="utf-8").read()
        if k > 0:
            fluxos.append(PageBreak())
        fluxos += render(md, avail)

    doc.build(fluxos)
    print(f"{OUT}: {len(paths)} EPT(s), {doc.page} páginas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
