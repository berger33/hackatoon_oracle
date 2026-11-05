#!/usr/bin/env python3
"""Gera a Especificação Funcional do MediFlow em PDF a partir do Markdown.

Fonte: docs/especificacao/EF_v1.1.md
Saída: docs/especificacao/MediFlow_Especificacao_Funcional_v1.1.pdf

Dialeto suportado:
    # Título de seção          (nível 1, entra no sumário)
    ## Subtítulo               (nível 2, entra no sumário)
    ### Destaque               (nível 3, não entra no sumário)
    - item                     (lista com marcador)
    1. item                    (lista numerada)
    | a | b |                  (tabela; a 2ª linha |---| separa o cabeçalho)
    ```                        (bloco de código)
    > observação               (caixa de nota)
    texto                      (parágrafo)

Uso:
    python3 tools/gerar_ef_v1_1.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

RAIZ = Path(__file__).resolve().parent.parent
FONTE_MD = RAIZ / "docs" / "especificacao" / "EF_v1.1.md"
SAIDA = RAIZ / "docs" / "especificacao" / "MediFlow_Especificacao_Funcional_v1.1.pdf"

VERSAO = "1.1"
DATA = "05/11/2026"

# Paleta idêntica à da v1.0.
AZUL_ESCURO = colors.HexColor("#12304a")
TEAL = colors.HexColor("#168c8c")
TEAL_ESCURO = colors.HexColor("#176b72")
CINZA = colors.HexColor("#657786")
TEXTO = colors.HexColor("#253746")
LINHA = colors.HexColor("#d5dde3")
FUNDO_NOTA = colors.HexColor("#eef7f7")
FUNDO_CODIGO = colors.HexColor("#f5f7f8")

FONTES = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("Corpo", str(FONTES / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("Corpo-Negrito", str(FONTES / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("Mono", str(FONTES / "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily(
    "Corpo", normal="Corpo", bold="Corpo-Negrito",
    italic="Corpo", boldItalic="Corpo-Negrito",
)

LARGURA_UTIL = A4[0] - 2 * 54
MARGEM_ESQ = 54
MARGEM_DIR = 54
TOPO = 54
RODAPE = 62


# --------------------------------------------------------------------------
# Estilos
# --------------------------------------------------------------------------
def montar_estilos() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["BodyText"]
    estilos = {
        "corpo": ParagraphStyle(
            "corpo", parent=base, fontName="Corpo", fontSize=9.3,
            leading=13.2, textColor=TEXTO, alignment=TA_LEFT,
            spaceAfter=6.5,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base, fontName="Corpo-Negrito", fontSize=17.5,
            leading=21, textColor=AZUL_ESCURO, spaceBefore=6, spaceAfter=11,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base, fontName="Corpo-Negrito", fontSize=12.2,
            leading=15, textColor=TEAL, spaceBefore=9, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base, fontName="Corpo-Negrito", fontSize=10,
            leading=13, textColor=AZUL_ESCURO, spaceBefore=7, spaceAfter=4,
            keepWithNext=True,
        ),
        "item": ParagraphStyle(
            "item", parent=base, fontName="Corpo", fontSize=9.3,
            leading=13.0, textColor=TEXTO, leftIndent=14,
            bulletIndent=3, spaceAfter=3.2,
            bulletFontName="Corpo", bulletFontSize=9.3,
            firstLineIndent=-11,
        ),
        "numerado": ParagraphStyle(
            "numerado", parent=base, fontName="Corpo", fontSize=9.3,
            leading=13.0, textColor=TEXTO, leftIndent=20,
            firstLineIndent=-20, spaceAfter=3.2,
        ),
        "nota": ParagraphStyle(
            "nota", parent=base, fontName="Corpo", fontSize=9.0,
            leading=12.6, textColor=TEXTO, leftIndent=10, rightIndent=8,
            spaceAfter=4,
        ),
        "celula": ParagraphStyle(
            "celula", parent=base, fontName="Corpo", fontSize=8.4,
            leading=11.2, textColor=TEXTO,
        ),
        "celula-cabeca": ParagraphStyle(
            "celula-cabeca", parent=base, fontName="Corpo-Negrito",
            fontSize=8.4, leading=11.2, textColor=colors.white,
        ),
        "codigo": ParagraphStyle(
            "codigo", parent=base, fontName="Mono", fontSize=7.6,
            leading=9.8, textColor=TEXTO, leftIndent=8, spaceAfter=0,
        ),
        "sumario-titulo": ParagraphStyle(
            "sumario-titulo", parent=base, fontName="Corpo-Negrito",
            fontSize=17.5, leading=21, textColor=AZUL_ESCURO, spaceAfter=14,
        ),
    }
    return estilos


# --------------------------------------------------------------------------
# Conversão de sintaxe inline
# --------------------------------------------------------------------------
def inline(texto: str) -> str:
    """`code` -> mono teal; **forte** -> negrito; escapa &,<,>."""
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    texto = re.sub(
        r"`([^`]+)`",
        r'<font name="Mono" size="8.1" color="#176b72">\1</font>',
        texto,
    )
    texto = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", texto)
    return texto


# --------------------------------------------------------------------------
# Leitura do Markdown
# --------------------------------------------------------------------------
def _proximo_numero(blocos: list[tuple[str, str]]) -> int:
    """Número esperado para o próximo item de lista numerada."""
    if blocos and blocos[-1][0] == "numerado":
        return int(blocos[-1][1].split("|", 1)[0]) + 1
    return 1


def ler_blocos(caminho: Path) -> list[tuple[str, str]]:
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    blocos: list[tuple[str, str]] = []
    buffer: list[str] = []
    i = 0

    def descarregar() -> None:
        if buffer:
            texto = " ".join(l.strip() for l in buffer if l.strip())
            if texto:
                blocos.append(("paragrafo", texto))
            buffer.clear()

    while i < len(linhas):
        linha = linhas[i]
        crua = linha.rstrip()
        sem_espaco = crua.strip()

        if sem_espaco.startswith("```"):
            descarregar()
            i += 1
            codigo: list[str] = []
            while i < len(linhas) and not linhas[i].strip().startswith("```"):
                codigo.append(linhas[i].rstrip("\n"))
                i += 1
            blocos.append(("codigo", "\n".join(codigo)))
            i += 1
            continue

        if sem_espaco.startswith("|") and i + 1 < len(linhas) and re.match(
            r"^\|[\s:\-|]+\|$", linhas[i + 1].strip()
        ):
            descarregar()
            cabecalho = [c.strip() for c in sem_espaco.strip("|").split("|")]
            i += 2
            corpo: list[list[str]] = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                corpo.append([c.strip() for c in linhas[i].strip().strip("|").split("|")])
                i += 1
            blocos.append(("tabela", (cabecalho, corpo)))  # type: ignore[arg-type]
            continue

        if sem_espaco.startswith("### "):
            descarregar()
            blocos.append(("h3", sem_espaco[4:]))
        elif sem_espaco.startswith("## "):
            descarregar()
            blocos.append(("h2", sem_espaco[3:]))
        elif sem_espaco.startswith("# "):
            descarregar()
            blocos.append(("h1", sem_espaco[2:]))
        elif sem_espaco.startswith("> "):
            descarregar()
            notas: list[str] = []
            while i < len(linhas) and linhas[i].strip().startswith(">"):
                notas.append(linhas[i].strip().lstrip(">").strip())
                i += 1
            blocos.append(("nota", " ".join(n for n in notas if n)))
            continue
        elif re.match(r"^- ", sem_espaco):
            descarregar()
            blocos.append(("item", sem_espaco[2:]))
        elif re.match(r"^\d+\. ", sem_espaco) and _proximo_numero(blocos) == int(
            sem_espaco.split(".", 1)[0]
        ):
            descarregar()
            numero, resto = sem_espaco.split(". ", 1)
            blocos.append(("numerado", f"{numero}|{resto}"))
        elif not sem_espaco:
            descarregar()
        else:
            # Continuação de um item de lista (linha indentada ou solta).
            if blocos and blocos[-1][0] in {"item", "numerado"} and not buffer:
                tipo, conteudo = blocos[-1]
                if tipo == "item":
                    blocos[-1] = ("item", conteudo + " " + sem_espaco)
                else:
                    numero, resto = conteudo.split("|", 1)
                    blocos[-1] = ("numerado", f"{numero}|{resto} {sem_espaco}")
            else:
                buffer.append(crua)
        i += 1

    descarregar()
    return blocos


# --------------------------------------------------------------------------
# Flowables
# --------------------------------------------------------------------------
def calcular_larguras(cabecalho: list[str], corpo: list[list[str]]) -> list[float]:
    """Larguras proporcionais ao conteúdo, com piso e teto por coluna."""
    pesos = []
    for indice, titulo in enumerate(cabecalho):
        comprimentos = [len(titulo)]
        for linha in corpo:
            if indice < len(linha):
                comprimentos.append(len(linha[indice]))
        # Média ponderada favorece colunas de texto corrido sem esmagar a chave.
        media = sum(comprimentos) / len(comprimentos)
        pesos.append(max(9.0, min(media, 62.0)))
    total = sum(pesos)
    larguras = [LARGURA_UTIL * p / total for p in pesos]

    # Piso real por coluna: o maior token indivisível precisa caber, senão o
    # ReportLab quebra palavras no meio (ex.: DOCUMENTO_NAO_ENCONTRAD|O).
    pisos = []
    for indice in range(len(cabecalho)):
        tokens = list(cabecalho[indice].split())
        for linha in corpo:
            if indice < len(linha):
                tokens += linha[indice].split()
        if not tokens:
            pisos.append(24.0)
            continue
        maior = max(tokens, key=len)
        pisos.append(pdfmetrics.stringWidth(maior, "Corpo", 8.4) + 12)

    for indice, piso in enumerate(pisos):
        larguras[indice] = max(larguras[indice], piso)

    excesso = sum(larguras) - LARGURA_UTIL
    for _ in range(4):
        if excesso <= 0.5:
            break
        ordem = sorted(range(len(larguras)), key=lambda i: -(larguras[i] - pisos[i]))
        for indice in ordem:
            folga = larguras[indice] - pisos[indice]
            if folga <= 0 or excesso <= 0.5:
                continue
            corte = min(folga, excesso)
            larguras[indice] -= corte
            excesso -= corte
    return larguras


def montar_tabela(cabecalho: list[str], corpo: list[list[str]],
                  estilos: dict[str, ParagraphStyle]) -> Table:
    larguras = calcular_larguras(cabecalho, corpo)
    dados = [[Paragraph(inline(c), estilos["celula-cabeca"]) for c in cabecalho]]
    for linha in corpo:
        linha = linha + [""] * (len(cabecalho) - len(linha))
        dados.append([Paragraph(inline(c), estilos["celula"]) for c in linha])

    tabela = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_ESCURO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINHA),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fa")]),
    ]))
    return tabela


def montar_codigo(texto: str, estilos: dict[str, ParagraphStyle]) -> Table:
    linhas = [
        Paragraph(inline(l).replace(" ", "&nbsp;") or "&nbsp;", estilos["codigo"])
        for l in texto.splitlines()
    ]
    # Cada 14 linhas viram uma linha de tabela: assim o bloco pode ser dividido
    # entre páginas sem cortar uma linha de código ao meio.
    pedacos = [linhas[i:i + 14] for i in range(0, len(linhas), 14)] or [[" "]]
    tabela = Table([[p] for p in pedacos], colWidths=[LARGURA_UTIL], hAlign="LEFT")
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FUNDO_CODIGO),
        ("LINEBEFORE", (0, 0), (0, -1), 0.4, LINHA),
        ("LINEAFTER", (-1, 0), (-1, -1), 0.4, LINHA),
        ("LINEABOVE", (0, 0), (-1, 0), 0.4, LINHA),
        ("LINEBELOW", (0, -1), (-1, -1), 0.4, LINHA),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    # Blocos longos (ex.: resposta de triagem) precisam poder atravessar páginas.
    tabela.splitByRow = True
    return tabela


def montar_nota(texto: str, estilos: dict[str, ParagraphStyle]) -> Table:
    paragrafo = Paragraph(inline(texto), estilos["nota"])
    tabela = Table([["", paragrafo]], colWidths=[3, LARGURA_UTIL - 3], hAlign="LEFT")
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), TEAL),
        ("BACKGROUND", (1, 0), (1, 0), FUNDO_NOTA),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
        ("RIGHTPADDING", (1, 0), (1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tabela


def converter(blocos, estilos) -> list:
    flowables: list = []
    for indice, (tipo, conteudo) in enumerate(blocos):
        # Texto de apoio + bloco de código não se separam entre páginas.
        if tipo == "paragrafo" and conteudo.rstrip().endswith(":") and indice + 1 < len(blocos) \
                and blocos[indice + 1][0] == "codigo":
            seguinte = blocos[indice + 1][1]
            flowables.append(KeepTogether([
                Paragraph(inline(conteudo), estilos["corpo"]),
                montar_codigo(seguinte, estilos),
            ]))
            blocos[indice + 1] = ("ignorar", "")
            flowables.append(Spacer(1, 8))
            continue
        if tipo == "ignorar":
            continue
        if tipo == "h1":
            flowables.append(Paragraph(inline(conteudo), estilos["h1"]))
        elif tipo == "h2":
            flowables.append(Paragraph(inline(conteudo), estilos["h2"]))
        elif tipo == "h3":
            flowables.append(Paragraph(inline(conteudo), estilos["h3"]))
        elif tipo == "paragrafo":
            flowables.append(Paragraph(inline(conteudo), estilos["corpo"]))
        elif tipo == "item":
            flowables.append(Paragraph(inline(conteudo), estilos["item"], bulletText="•"))
        elif tipo == "numerado":
            numero, resto = conteudo.split("|", 1)
            flowables.append(
                Paragraph(inline(f"{numero}. {resto}"), estilos["numerado"])
            )
        elif tipo == "nota":
            flowables.append(Spacer(1, 3))
            flowables.append(montar_nota(conteudo, estilos))
            flowables.append(Spacer(1, 7))
        elif tipo == "codigo":
            flowables.append(Spacer(1, 3))
            flowables.append(montar_codigo(conteudo, estilos))
            flowables.append(Spacer(1, 8))
        elif tipo == "tabela":
            cabecalho, corpo = conteudo  # type: ignore[misc]
            flowables.append(Spacer(1, 2))
            flowables.append(montar_tabela(cabecalho, corpo, estilos))
            flowables.append(Spacer(1, 9))
    return flowables


# --------------------------------------------------------------------------
# Documento
# --------------------------------------------------------------------------
class DocumentoEF(BaseDocTemplate):
    def __init__(self, arquivo: str, **kwargs):
        super().__init__(arquivo, **kwargs)
        moldura_capa = Frame(54, 54, LARGURA_UTIL, A4[1] - 108, id="capa")
        moldura_corpo = Frame(
            MARGEM_ESQ, RODAPE, LARGURA_UTIL, A4[1] - TOPO - RODAPE, id="corpo"
        )
        self.addPageTemplates([
            PageTemplate(id="Capa", frames=[moldura_capa], onPage=self.fundo_capa),
            PageTemplate(id="Corpo", frames=[moldura_corpo], onPage=self.cabecalho_rodape),
        ])

    # -- capa -------------------------------------------------------------
    def fundo_capa(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#f2f7f9"))
        canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        canvas.setFillColor(TEAL)
        canvas.rect(54, A4[1] - 120, 70, 4, stroke=0, fill=1)
        canvas.setFillColor(TEAL)
        canvas.rect(54, 250, LARGURA_UTIL, 1.2, stroke=0, fill=1)
        canvas.restoreState()

    # -- cabeçalho e rodapé ----------------------------------------------
    def cabecalho_rodape(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Corpo-Negrito", 7.5)
        canvas.setFillColor(AZUL_ESCURO)
        canvas.drawString(MARGEM_ESQ, A4[1] - 34, "MEDIFLOW")
        canvas.setFont("Corpo", 7.5)
        canvas.setFillColor(CINZA)
        canvas.drawRightString(
            A4[0] - MARGEM_DIR, A4[1] - 34,
            f"ESPECIFICAÇÃO FUNCIONAL  •  VERSÃO {VERSAO}",
        )
        canvas.setStrokeColor(LINHA)
        canvas.setLineWidth(0.6)
        canvas.line(MARGEM_ESQ, A4[1] - 46, A4[0] - MARGEM_DIR, A4[1] - 46)

        canvas.setFont("Corpo", 7.2)
        canvas.setFillColor(CINZA)
        canvas.drawString(MARGEM_ESQ, 40, "Hackathon ONE G10  •  MediFlow")
        canvas.drawRightString(A4[0] - MARGEM_DIR, 40, f"Página {doc.page}")
        canvas.restoreState()

    # -- sumário ----------------------------------------------------------
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            estilo = flowable.style.name
            if estilo in {"h1", "h2"}:
                nivel = 0 if estilo == "h1" else 1
                self.notify("TOCEntry", (nivel, flowable.getPlainText(), self.page))


def montar_capa(estilos) -> list:
    rotulo = ParagraphStyle(
        "rotulo", fontName="Corpo-Negrito", fontSize=8, leading=10,
        textColor=CINZA,
    )
    valor = ParagraphStyle(
        "valor", fontName="Corpo", fontSize=9.4, leading=13.5, textColor=TEXTO,
    )
    titulo = ParagraphStyle(
        "titulo-cap", fontName="Corpo-Negrito", fontSize=29, leading=34,
        textColor=AZUL_ESCURO,
    )
    subtitulo = ParagraphStyle(
        "sub-cap", fontName="Corpo", fontSize=16, leading=20, textColor=TEAL,
    )
    selo = ParagraphStyle(
        "selo", fontName="Corpo-Negrito", fontSize=9, leading=12,
        textColor=AZUL_ESCURO,
    )

    linhas = [
        ("VERSÃO", f"{VERSAO} — urgência isolada, revisão humana e "
                   "reconciliação com o contrato de dados"),
        ("DATA", DATA),
        ("BASE DOCUMENTAL",
         "Projeto Oracle / Hackathon ONE G10, MediFlow — Análise de Requisitos v1.1 "
         "e Contrato de Dados da Triagem v1.0"),
        ("ESTADO",
         "regra de urgência isolada confirmada e alinhada ao contrato de dados; "
         "permanecem definições operacionais e regras clínicas que a equipe deve "
         "registrar antes da implementação correspondente."),
    ]
    tabela = Table(
        [[Paragraph(rot, rotulo), Paragraph(val, valor)] for rot, val in linhas],
        colWidths=[110, LARGURA_UTIL - 110],
        hAlign="LEFT",
    )
    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINHA),
    ]))

    return [
        Spacer(1, 110),
        Paragraph("MediFlow", titulo),
        Spacer(1, 6),
        Paragraph("Especificação Funcional", subtitulo),
        Spacer(1, 34),
        tabela,
        Spacer(1, 52),
        Table(
            [[Paragraph("Documento funcional do MVP", selo)]],
            colWidths=[210], hAlign="LEFT",
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e3f0f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]),
        ),
    ]


def main() -> int:
    if not FONTE_MD.exists():
        print(f"Fonte não encontrada: {FONTE_MD}", file=sys.stderr)
        return 1

    estilos = montar_estilos()
    blocos = ler_blocos(FONTE_MD)

    sumario = TableOfContents()
    sumario.levelStyles = [
        ParagraphStyle("toc0", fontName="Corpo-Negrito", fontSize=9.4, leading=17,
                       textColor=TEXTO),
        ParagraphStyle("toc1", fontName="Corpo", fontSize=9.0, leading=14.5,
                       textColor=TEXTO, leftIndent=14),
    ]
    sumario.dotsMinLevel = 0

    historia = montar_capa(estilos)
    historia += [
        NextPageTemplate("Corpo"),
        PageBreak(),
        Paragraph("Sumário", estilos["sumario-titulo"]),
        sumario,
        PageBreak(),
    ]
    historia += converter(blocos, estilos)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    doc = DocumentoEF(
        str(SAIDA),
        pagesize=A4,
        title=f"MediFlow — Especificação Funcional v{VERSAO}",
        author="Hackathon ONE G10",
        subject="Documento funcional do MVP",
        creator="tools/gerar_ef_v1_1.py",
    )
    doc.multiBuild(historia)
    print(f"Gerado: {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
