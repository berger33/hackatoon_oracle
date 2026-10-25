#!/usr/bin/env python3
"""Gera o PDF da EPT (Especificação de Procedimento de Teste) do MediFlow.

Entrada: `docs/testes/EPT_MediFlow.csv` (gerado por tools/gerar_ept.py).
Saída:   `docs/testes/EPT_MediFlow.pdf`

Estrutura do documento:
  capa · sumário · como ler · visão geral e cobertura · os 100 casos por suíte ·
  anexos (requisito→caso, §16→caso, fixture→caso, pendências, registro de execução)

Tipografia: DejaVu Sans (regular/bold) e DejaVu Sans Mono — as mesmas do PDF do
mapa de documentos, para o conjunto de PDFs do projeto ficar coerente.
Cabeçalho e rodapé com seção corrente e "página N de M".

Uso:
    python3 tools/gerar_ept_pdf.py
"""
from __future__ import annotations

import csv
import os
from collections import Counter, defaultdict
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_EPT = os.path.join(ROOT, "docs/testes/EPT_MediFlow.csv")
MANIFEST = os.path.join(ROOT, "tests/fixtures/manifest.csv")
SAIDA = os.path.join(ROOT, "docs/testes/EPT_MediFlow.pdf")

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DJ", f"{FONT_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DJB", f"{FONT_DIR}/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DJM", f"{FONT_DIR}/DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJB", italic="DJ", boldItalic="DJB")

# ------------------------------------------------------------------ identidade
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#D7DBE3")
SOFT = colors.HexColor("#F7F8FA")
BRAND = colors.HexColor("#1F4BD8")
BRAND_SOFT = colors.HexColor("#EEF2FE")
RED = colors.HexColor("#B42318")
RED_SOFT = colors.HexColor("#FDECEB")
AMBER = colors.HexColor("#B45309")
AMBER_SOFT = colors.HexColor("#FDF3E0")
GREEN = colors.HexColor("#0B6B3A")
GREEN_SOFT = colors.HexColor("#EAF4EA")

W, H = A4
MARGEM_LAT = 18 * mm
MARGEM_TOPO = 22 * mm
MARGEM_BASE = 18 * mm
BARRA_MAX = 26 * mm   # largura máxima da barra nas tabelas de distribuição
LARGURA = W - 2 * MARGEM_LAT

VERSAO = "1.0"
TITULO = "Especificação de Procedimento de Teste"
PROJETO = "MediFlow — Hackathon ONE G10 · Oracle Next Education & Alura"
BASE = ("Especificação Funcional v1.0, incluindo o Anexo A (decisões A1 a A9) · Análise de "
        "Requisitos v1.1 · contrato de dados app/models.py (R1–R8) · massa de "
        "tests/fixtures/manifest.csv (79 fixtures)")
EMITIDO = date.today().strftime("%d/%m/%Y")

# ------------------------------------------------------------------- estilos
BASE_STYLES = getSampleStyleSheet()


def st(nome: str, **kw) -> ParagraphStyle:
    padrao = dict(fontName="DJ", fontSize=9, leading=13, textColor=INK, spaceBefore=0,
                  spaceAfter=0, alignment=TA_LEFT)
    padrao.update(kw)
    return ParagraphStyle(nome, **padrao)


S = {
    "capa_kicker": st("capa_kicker", fontName="DJB", fontSize=9.5, leading=12, textColor=BRAND),
    "capa_titulo": st("capa_titulo", fontName="DJB", fontSize=27, leading=32, textColor=INK),
    "capa_sub": st("capa_sub", fontSize=12.5, leading=18, textColor=MUTED),
    "capa_meta": st("capa_meta", fontSize=9, leading=13, textColor=INK),
    "h1": st("h1", fontName="DJB", fontSize=16, leading=20, textColor=INK, spaceBefore=2,
             spaceAfter=2),
    "h2": st("h2", fontName="DJB", fontSize=10.5, leading=14, textColor=BRAND, spaceBefore=12,
             spaceAfter=4),
    "h3": st("h3", fontName="DJB", fontSize=9, leading=12, textColor=INK, spaceBefore=8,
             spaceAfter=3),
    "corpo": st("corpo", fontSize=9, leading=13.5),
    "corpo_j": st("corpo_j", fontSize=9, leading=13.5, alignment=TA_JUSTIFY),
    "pequeno": st("pequeno", fontSize=8, leading=11, textColor=MUTED),
    "rotulo": st("rotulo", fontName="DJB", fontSize=7.4, leading=10, textColor=MUTED),
    "celula": st("celula", fontSize=8.2, leading=11.5),
    "celula_j": st("celula_j", fontSize=8.2, leading=11.5, alignment=TA_JUSTIFY),
    "celula_b": st("celula_b", fontName="DJB", fontSize=8.2, leading=11.5),
    "mono": st("mono", fontName="DJM", fontSize=7.4, leading=10.2, textColor=INK),
    "caso_id": st("caso_id", fontName="DJB", fontSize=10.5, leading=13, textColor=BRAND),
    "caso_titulo": st("caso_titulo", fontName="DJB", fontSize=9.6, leading=12.6),
    "chip": st("chip", fontName="DJB", fontSize=6.9, leading=8.4, textColor=INK,
               alignment=TA_CENTER),
    "toc1": st("toc1", fontName="DJB", fontSize=9.6, leading=16, textColor=INK),
    "toc2": st("toc2", fontSize=8.8, leading=13.4, textColor=MUTED, leftIndent=12),
    "tabela_cab": st("tabela_cab", fontName="DJB", fontSize=7.2, leading=9.4, textColor=MUTED),
}
S["caso_id"].name = "caso_id"  # já criado com nome; garante o notify do sumário
S["h1"].name, S["h2"].name = "h1", "h2"


# ------------------------------------------------------------------- helpers
def carregar() -> list[dict]:
    with open(CSV_EPT, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def quebra_id(nome: str, limite: int = 26) -> str:
    """Quebra identificadores longos nos underscores, para caber em coluna estreita."""
    if len(nome) <= limite:
        return nome
    partes, atual = [], ""
    for pedaco in nome.split("_"):
        candidato = f"{atual}_{pedaco}" if atual else pedaco
        if len(candidato) > limite and atual:
            partes.append(atual)
            atual = pedaco
        else:
            atual = candidato
    if atual:
        partes.append(atual)
    return "<br/>".join(partes)


def chips(caso: dict) -> Table:
    """Faixa de etiquetas do caso: prioridade, cenário, tipo, automação, ambiente."""
    prio = caso["PRIORIDADE"]
    cor, fundo = ((RED, RED_SOFT) if prio == "Alta"
                  else (AMBER, AMBER_SOFT) if prio == "Média" else (GREEN, GREEN_SOFT))
    itens = [
        (f"PRIORIDADE {prio.upper()}", cor, fundo),
        (f"CENÁRIO {caso['CENARIO'].upper()}", INK, colors.HexColor("#EDF0F5")),
        (f"TIPO {caso['TIPO_TESTE'].upper()}", INK, colors.HexColor("#EDF0F5")),
        (f"AUTOMAÇÃO {caso['AUTOMATIZAVEL'].upper()}", INK, colors.HexColor("#F1F0FB")),
        (f"AMBIENTE {caso['AMBIENTE'].upper()}", INK, colors.HexColor("#EDF0F5")),
    ]
    def larguras(fonte: float) -> list[float]:
        return [pdfmetrics.stringWidth(t, "DJB", fonte) + 11 for t, _, _ in itens]

    fonte = 6.9
    larguras_col = larguras(fonte)
    while sum(larguras_col) > LARGURA and fonte > 5.6:
        fonte -= 0.25
        larguras_col = larguras(fonte)
    if sum(larguras_col) > LARGURA:                     # ainda não cabe: divide igualmente
        larguras_col = [LARGURA / len(itens)] * len(itens)
    estilo_chip = st(f"chip{fonte}", fontName="DJB", fontSize=fonte, leading=fonte + 1.6,
                     textColor=INK, alignment=TA_CENTER)
    dados = [[Paragraph(t, estilo_chip) for t, _, _ in itens]]
    tabela = Table(dados, colWidths=larguras_col)
    tabela.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        *[("BACKGROUND", (i, 0), (i, 0), fundo) for i, (_, _, fundo) in enumerate(itens)],
    ]))
    return tabela


def par(texto: str, estilo: str = "celula") -> Paragraph:
    return Paragraph(texto or "—", S[estilo])


def tabela_kv(linhas: list[tuple[str, str]], largura_rotulo: float = 30 * mm) -> Table:
    """Tabela rótulo/valor usada no corpo de cada caso."""
    dados = [[Paragraph(rot, S["rotulo"]), par(valor)] for rot, valor in linhas if valor]
    t = Table(dados, colWidths=[largura_rotulo, LARGURA - largura_rotulo])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("LEFTPADDING", (1, 0), (1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
        ("BACKGROUND", (0, 0), (0, -1), SOFT),
    ]))
    return t


def passos_html(passos: str) -> str:
    itens = [p.strip() for p in passos.split(" | ") if p.strip()]
    limpos = []
    for item in itens:
        if ") " in item[:4]:
            item = item.split(") ", 1)[1]
        limpos.append(f"{len(limpos) + 1}. {item}")
    return "<br/>".join(limpos)


# --------------------------------------------------------------- documento
class EPTDoc(BaseDocTemplate):
    """DocTemplate com sumário automático e cabeçalho/rodapé por seção."""

    def __init__(self, arquivo: str, **kw):
        super().__init__(arquivo, pagesize=A4, leftMargin=MARGEM_LAT, rightMargin=MARGEM_LAT,
                         topMargin=MARGEM_TOPO, bottomMargin=MARGEM_BASE,
                         title=f"EPT MediFlow v{VERSAO}", author="MediFlow — Hackathon ONE G10",
                         subject="Especificação de Procedimento de Teste",
                         creator="tools/gerar_ept_pdf.py", **kw)
        self.secao = ""
        quadro = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="corpo",
                       leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        quadro_capa = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                            id="capa", leftPadding=0, rightPadding=0, topPadding=0,
                            bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="capa", frames=[quadro_capa], onPage=self.decorar_capa),
            PageTemplate(id="corpo", frames=[quadro], onPageEnd=self.decorar_corpo),
        ])

    # cabeçalho/rodapé ------------------------------------------------------
    def decorar_capa(self, canv, doc):
        canv.saveState()
        canv.setFillColor(BRAND)
        canv.rect(0, H - 14 * mm, W, 14 * mm, stroke=0, fill=1)
        canv.setFillColor(INK)
        canv.setFont("DJ", 7.4)
        canv.drawString(MARGEM_LAT, 12 * mm,
                        "Documento de teste — dados exclusivamente fictícios · Hospital Aurora (SP)")
        canv.setStrokeColor(LINE)
        canv.setLineWidth(0.5)
        canv.line(MARGEM_LAT, 15 * mm, W - MARGEM_LAT, 15 * mm)
        canv.restoreState()

    def decorar_corpo(self, canv, doc):
        canv.saveState()
        canv.setFont("DJB", 7.2)
        canv.setFillColor(BRAND)
        canv.drawString(MARGEM_LAT, H - 13.5 * mm, "MEDIFLOW")
        canv.setFont("DJ", 7.2)
        canv.setFillColor(MUTED)
        canv.drawRightString(W - MARGEM_LAT, H - 13.5 * mm, self.secao.upper())
        canv.setStrokeColor(LINE)
        canv.setLineWidth(0.6)
        canv.line(MARGEM_LAT, H - 16 * mm, W - MARGEM_LAT, H - 16 * mm)
        canv.line(MARGEM_LAT, 13.5 * mm, W - MARGEM_LAT, 13.5 * mm)
        canv.setFont("DJ", 7.2)
        canv.setFillColor(MUTED)
        canv.drawString(MARGEM_LAT, 9.6 * mm, f"EPT MediFlow v{VERSAO} · {EMITIDO}")
        canv.restoreState()

    # sumário automático ----------------------------------------------------
    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        nome = flowable.style.name
        if nome in ("h1", "h2"):
            texto = flowable.getPlainText()
            if texto.strip().lower() == "sumário":
                return
            if nome == "h1":
                self.secao = texto
            nivel = 0 if nome == "h1" else 1
            self.notify("TOCEntry", (nivel, texto, self.page))


class CanvasNumerado(pdfcanvas.Canvas):
    """Adia o rodapé para saber o total de páginas e escrever 'página N de M'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estados = []

    def showPage(self):
        self._estados.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._estados)
        for estado in self._estados:
            self.__dict__.update(estado)
            if self._pageNumber > 1:
                self.setFont("DJ", 7.2)
                self.setFillColor(MUTED)
                self.drawRightString(W - MARGEM_LAT, 9.6 * mm,
                                     f"página {self._pageNumber} de {total}")
            super().showPage()
        super().save()


# ------------------------------------------------------------------- blocos
def capa() -> list:
    blocos = [
        Spacer(1, 26 * mm),
        Paragraph("MEDIFLOW · HACKATHON ONE G10", S["capa_kicker"]),
        Spacer(1, 5 * mm),
        Paragraph("EPT", S["capa_titulo"]),
        Paragraph(TITULO, st("t2", fontName="DJB", fontSize=15, leading=20, textColor=BRAND)),
        Spacer(1, 6 * mm),
        Paragraph("Roteiro de execução do MVP de triagem documental: pré-condição, massa, passos e "
                  "resultado esperado de cada caso, com rastreabilidade a requisitos, critérios de "
                  "aceite e fixtures.", S["capa_sub"]),
        Spacer(1, 14 * mm),
    ]
    meta = [
        ("Versão", f"{VERSAO} · {EMITIDO}"),
        ("Projeto", PROJETO),
        ("Base documental", BASE),
        ("Formato", "CSV com uma linha por caso (execução) e este PDF (leitura e aprovação); "
                    "gerado por tools/gerar_ept.py e tools/gerar_ept_pdf.py"),
        ("Escopo", "MVP conforme a Especificação Funcional v1.0: ingestão, classificação, "
                   "extração, confiança e conflitos, decisão e roteamento, persistência, "
                   "API, interface e requisitos não funcionais"),
        ("Uso", "Apoio à triagem documental. Não substitui diagnóstico, prescrição, decisão "
                "clínica ou auditoria profissional."),
    ]
    linhas = [[Paragraph(k.upper(), S["rotulo"]), Paragraph(v, S["capa_meta"])] for k, v in meta]
    t = Table(linhas, colWidths=[32 * mm, LARGURA - 32 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("LEFTPADDING", (1, 0), (1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEABOVE", (0, 0), (-1, 0), 1, INK),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, LINE),
    ]))
    blocos += [t, Spacer(1, 12 * mm)]
    blocos += [Paragraph(
        "Todos os documentos, nomes, CRMs, CIDs e resultados citados são fictícios. Nenhum dado "
        "de paciente real, credencial ou segredo faz parte deste documento.", S["pequeno"])]
    blocos += [NextPageTemplate("corpo"), PageBreak()]
    return blocos


def sumario() -> list:
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    toc.dotsMinLevel = 0
    return [
        Paragraph("Sumário", S["h1"]),
        Spacer(1, 5 * mm),
        toc,
        PageBreak(),
    ]


def como_ler(casos: list[dict]) -> list:
    colunas = [
        ("ID_CASO", "Identificador único do caso (CT-001…CT-111); usado em evidência e defeito."),
        ("SUITE", "Agrupamento funcional do caso."),
        ("ID_REQUISITO", "RF/RNF da especificação que o caso verifica."),
        ("REGRAS_NEGOCIO", "RN aplicada; vazio quando não há regra de negócio."),
        ("CENARIO", "Rotina, Urgência, Ambiguidade, Erro ou Transversal."),
        ("TIPO_TESTE", "Funcional, negativo, borda, integração, não funcional, usabilidade, segurança."),
        ("TECNICA", "Particularidade de projeto do caso: valor limite, partição de equivalência etc."),
        ("PRIORIDADE", "Alta bloqueia o MVP; Média entra na entrega; Baixa é opcional."),
        ("TITULO", "O que o caso prova, em uma frase."),
        ("OBJETIVO", "O que uma falha aqui revelaria."),
        ("PRE_CONDICOES", "Ambiente, configuração e dados necessários."),
        ("MASSA_DE_DADOS", "Fixtures do catálogo usadas como entrada."),
        ("PASSOS", "Roteiro numerado de execução."),
        ("RESULTADO_ESPERADO", "Asserções objetivas: valores, códigos HTTP e campos do payload."),
        ("POS_CONDICOES", "Estado esperado do ambiente após a execução."),
        ("CRITERIO_DE_ACEITE", "Item de §16 da especificação associado ao caso."),
        ("AUTOMATIZAVEL", "Sim, Parcial ou Não."),
        ("AMBIENTE", "API, Interface, Ambos ou Repositório."),
        ("OBSERVACOES", "Cuidados, dependências e pendências sinalizadas."),
        ("STATUS_EXECUCAO", "Inicia NAO EXECUTADO; passa a PASSOU, FALHOU, BLOQUEADO ou NAO APLICAVEL."),
        ("RESULTADO_OBTIDO", "O que aconteceu na execução, com os valores observados."),
        ("EVIDENCIA", "Caminho do print/log que comprova o resultado."),
        ("DEFEITO", "Identificador do defeito aberto, quando houver."),
        ("DATA_EXECUCAO", "Data da execução."),
        ("EXECUTOR", "Quem executou."),
    ]
    dados = [[Paragraph("COLUNA", S["tabela_cab"]), Paragraph("CONTEÚDO", S["tabela_cab"])]]
    dados += [[Paragraph(f"<font name='DJM' size='7.2'>{c}</font>", S["celula"]), par(d)]
              for c, d in colunas]
    t = Table(dados, colWidths=[42 * mm, LARGURA - 42 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    ordem = [
        ("1", "CT-001 a CT-012", "Ingestão e validação — sem isso, nenhum outro caso tem massa válida."),
        ("2", "CT-049 a CT-063", "Decisão e roteamento, com FIXTURE_MODE nos casos de borda."),
        ("3", "CT-013 a CT-048", "Classificação, extração, confiança e conflitos — o núcleo clínico."),
        ("4", "CT-064 a CT-080", "Erros, persistência e API."),
        ("5", "CT-081 a CT-100", "Interface e requisitos não funcionais, no fechamento."),
    ]
    dados_ordem = [[Paragraph("ETAPA", S["tabela_cab"]), Paragraph("CASOS", S["tabela_cab"]),
                    Paragraph("POR QUÊ", S["tabela_cab"])]]
    dados_ordem += [[par(o, "celula_b"), par(c, "mono"), par(p)] for o, c, p in ordem]
    t_ordem = Table(dados_ordem, colWidths=[14 * mm, 32 * mm, LARGURA - 46 * mm], repeatRows=1)
    t_ordem.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [
        Paragraph("Como ler esta EPT", S["h1"]),
        Spacer(1, 3 * mm),
        Paragraph("Cada caso é um procedimento fechado: pré-condição, massa, passos e resultado "
                  "esperado verificável. O resultado esperado é escrito como asserção — valor, "
                  "código HTTP ou campo do payload — e não como “funciona corretamente”.", S["corpo_j"]),
        Spacer(1, 2 * mm),
        Paragraph("O mesmo conteúdo existe em CSV, com as colunas de execução vazias para o "
                  "executor preencher: <font name='DJM' size='8'>docs/testes/EPT_MediFlow.csv</font>. "
                  "Este PDF é a versão de leitura, revisão e assinatura.", S["corpo_j"]),
        Paragraph("Dicionário de colunas", S["h2"]),
        t,
        Paragraph("Ordem de execução recomendada", S["h2"]),
        t_ordem,
        Paragraph("Casos que exigem stub de score", S["h2"]),
        Paragraph("CT-020, CT-044, CT-045, CT-046, CT-054 e CT-062 dependem do modo de fixture: "
                  "ative <font name='DJM' size='8'>FIXTURE_MODE</font> e use "
                  "<font name='DJM' size='8'>modo_fixture.score_forcado</font> do "
                  "<font name='DJM' size='8'>expected.json</font>. Score de modelo não é determinístico "
                  "e não deve ser comparado por igualdade.", S["corpo_j"]),
        PageBreak(),
    ]


def visao_geral(casos: list[dict], fixtures: list[str]) -> list:
    suites = Counter(c["SUITE"] for c in casos)
    cenarios = Counter(c["CENARIO"] for c in casos)
    tipos = Counter(c["TIPO_TESTE"] for c in casos)
    prioridades = Counter(c["PRIORIDADE"] for c in casos)
    autos = Counter(c["AUTOMATIZAVEL"] for c in casos)
    reqs = set()
    aceites = set()
    for c in casos:
        for campo in ("ID_REQUISITO", "REGRAS_NEGOCIO"):
            for tok in str(c[campo]).replace("/", " ").replace(";", " ").split():
                if tok.startswith(("RF-", "RN-", "RNF-")):
                    reqs.add(tok.strip("()."))
        for parte in str(c["CRITERIO_DE_ACEITE"]).replace(",", " ").split():
            for tok in parte.split():
                if tok.isdigit():
                    aceites.add(int(tok))

    cartoes = [
        (str(len(casos)), "casos", 17),
        (str(len(fixtures)), "fixtures", 17),
        (str(len(suites)), "suítes", 17),
        (str(len(reqs)), "requisitos", 17),
        (f"{len(aceites)}/15", "aceite §16", 17),
        (str(autos["Sim"]), "automatizáveis", 17),
    ]
    dados = [[Paragraph(f"<font name='DJB' size='{tam}'>{n}</font><br/>"
                        f"<font size='6.4' color='#6B7280'>{r.upper()}</font>",
                        st("cartao", alignment=TA_CENTER, leading=20))
              for n, r, tam in cartoes]]
    largura_cartao = LARGURA / len(cartoes)
    t_cartoes = Table(dados, colWidths=[largura_cartao] * len(cartoes))
    t_cartoes.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    def distribuicao(titulo: str, contagem: Counter, total: int) -> list:
        linhas = [[Paragraph("VALOR", S["tabela_cab"]), Paragraph("Nº", S["tabela_cab"]),
                   Paragraph("", S["tabela_cab"])]]
        for chave, qtd in sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0])):
            pct = 100 * qtd / total
            barra = Table([[""]], colWidths=[max(1.6, BARRA_MAX * pct / 100)], rowHeights=[4])
            barra.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                       ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                       ("TOPPADDING", (0, 0), (-1, -1), 0),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            linhas.append([par(chave), par(str(qtd), "celula_b"), barra])
        t = Table(linhas, colWidths=[42 * mm, 12 * mm, LARGURA / 2 - 56 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, 0), SOFT),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return [Paragraph(titulo, S["h3"]), t]

    esquerda = []
    esquerda += distribuicao("Por suíte", suites, len(casos))
    esquerda += distribuicao("Por cenário", cenarios, len(casos))
    esquerda += distribuicao("Por prioridade", prioridades, len(casos))
    direita = []
    direita += distribuicao("Por tipo de teste", tipos, len(casos))
    direita += distribuicao("Por automação", autos, len(casos))
    duas_colunas = Table([[esquerda, direita]], colWidths=[LARGURA / 2, LARGURA / 2])
    duas_colunas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 6 * mm),
        ("LEFTPADDING", (1, 0), (1, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ]))

    return [
        Paragraph("Visão geral e cobertura", S["h1"]),
        Spacer(1, 3 * mm),
        Paragraph("A EPT cobre a Especificação Funcional v1.0 — RF-01 a RF-30, RN-01 a RN-07, "
                  "RNF-01 a RNF-11 e as decisões A1 a A9 —, os 15 critérios de aceite de §16, os "
                  f"{len(fixtures)} documentos fictícios do catálogo. Cada requisito tem pelo "
                  "menos um caso; as matrizes completas estão nos anexos A a C.", S["corpo_j"]),
        Spacer(1, 4 * mm),
        t_cartoes,
        Spacer(1, 5 * mm),
        duas_colunas,
        Spacer(1, 3 * mm),
        Paragraph("O que a EPT não faz", S["h2"]),
        Paragraph("Ela não define critérios clínicos: verifica os que a equipe aprovou. Limites, "
                  "dicionário clínico, farmacopeia e metas seguem as decisões A1 a A9; o que está "
                  "fora do escopo do MVP e o único ponto em aberto (formato final do upload) estão "
                  "no Anexo D.", S["corpo_j"]),
        PageBreak(),
    ]


def caso_flowables(caso: dict) -> list:
    cabeca = Table(
        [[Paragraph(caso["ID_CASO"], S["caso_id"]), Paragraph(caso["TITULO"], S["caso_titulo"])]],
        colWidths=[24 * mm, LARGURA - 24 * mm])
    cabeca.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -1), 1, BRAND),
    ]))
    corpo = tabela_kv([
        ("OBJETIVO", caso["OBJETIVO"]),
        ("PRÉ-CONDIÇÕES", caso["PRE_CONDICOES"]),
        ("MASSA", caso["MASSA_DE_DADOS"]),
        ("PASSOS", passos_html(caso["PASSOS"])),
        ("ESPERADO", caso["RESULTADO_ESPERADO"]),
        ("PÓS-CONDIÇÕES", caso["POS_CONDICOES"]),
        ("RASTREABILIDADE", " · ".join(x for x in [
            caso["ID_REQUISITO"], caso["REGRAS_NEGOCIO"],
            f"técnica: {caso['TECNICA']}", caso["CRITERIO_DE_ACEITE"]] if x)),
        ("OBSERVAÇÕES", caso["OBSERVACOES"]),
    ])
    return [Spacer(1, 5 * mm), cabeca, Spacer(1, 2.4 * mm), chips(caso), Spacer(1, 1.8 * mm), corpo]


def casos_por_suite(casos: list[dict]) -> list:
    ordem_suites = ["Ingestão e validação", "Classificação", "Extração", "Confiança e limiar",
                    "Decisão e roteamento", "Persistência e histórico", "API e erros",
                    "Interface", "Não funcionais"]
    grupos: dict[str, list[dict]] = defaultdict(list)
    for c in casos:
        grupos[c["SUITE"]].append(c)

    blocos: list = []
    for suíte in ordem_suites:
        lista = grupos.pop(suíte, [])
        if not lista:
            continue
        ids = f"{lista[0]['ID_CASO']} a {lista[-1]['ID_CASO']}"
        blocos += [
            Paragraph(suíte, S["h1"]),
            Spacer(1, 2 * mm),
            Paragraph(f"{len(lista)} casos · {ids} · suíte do roteiro de execução", S["pequeno"]),
            Spacer(1, 3 * mm),
        ]
        for caso in lista:
            blocos += caso_flowables(caso)
        blocos += [PageBreak()]
    return blocos


def anexo(titulo: str, subtitulo: str, cabecalhos: list[str], linhas: list[list],
          larguras: list[float]) -> list:
    dados = [[Paragraph(h, S["tabela_cab"]) for h in cabecalhos]] + linhas
    t = Table(dados, colWidths=larguras, repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBFCFD")]),
    ]))
    return [
        Paragraph(titulo, S["h1"]),
        Spacer(1, 2 * mm),
        Paragraph(subtitulo, S["pequeno"]),
        Spacer(1, 3 * mm),
        t,
        PageBreak(),
    ]


def montar(casos: list[dict], fixtures: list[str]) -> list:
    # --- cobertura por requisito
    req: dict[str, list[str]] = defaultdict(list)
    for c in casos:
        for campo in ("ID_REQUISITO", "REGRAS_NEGOCIO"):
            for tok in str(c[campo]).replace("/", " ").replace(";", " ").split():
                if tok.startswith(("RF-", "RN-", "RNF-")):
                    req[tok.strip("().")].append(c["ID_CASO"])
    def chave(k: str):
        pre, num = k.split("-")
        return ({"RF": 0, "RN": 1, "RNF": 2}[pre], int(num))
    linhas_req = [[par(k, "mono"), par(str(len(set(v))), "celula_b"), par(", ".join(sorted(set(v))))]
                  for k, v in sorted(req.items(), key=lambda kv: chave(kv[0]))]

    # --- cobertura por item de aceite
    aceite: dict[int, list[str]] = defaultdict(list)
    for c in casos:
        for parte in str(c["CRITERIO_DE_ACEITE"]).replace(",", " ").split():
            for tok in parte.split():
                if tok.isdigit():
                    aceite[int(tok)].append(c["ID_CASO"])
    linhas_aceite = [[par(f"§16 · item {i}", "celula_b"), par(str(len(set(aceite.get(i, []))))),
                      par(", ".join(sorted(set(aceite.get(i, [])))))]
                     for i in range(1, 16)]

    # --- cobertura por fixture
    def expandir(massa: str) -> list[str]:
        import fnmatch
        achados = []
        for bruto in massa.split(";"):
            token = bruto.split(" (")[0].strip()
            if token:
                achados += [f for f in fixtures if fnmatch.fnmatch(f, token)]
        return sorted(set(achados))

    por_fixture: dict[str, list[str]] = defaultdict(list)
    for c in casos:
        for f in expandir(c["MASSA_DE_DADOS"]):
            por_fixture[f].append(c["ID_CASO"])
    linhas_fixture = [[Paragraph(f"<font name='DJM' size='7'>{quebra_id(f)}</font>", S["celula"]),
                       par(str(len(por_fixture.get(f, [])))),
                       par(", ".join(por_fixture.get(f, [])) or "—")]
                      for f in fixtures]

    pend = [
        ("Limites de tamanho, páginas e MIME", "A6", "CT-106, CT-107, CT-108",
         "10 MB, 20 páginas, PDF/JPG/PNG/WEBP/TXT — verificados nas duas bordas."),
        ("Timeout e política de retry", "A6", "CT-109, CT-078, CT-091",
         "60 s no Gemini, 2 retentativas com backoff e falha registrada."),
        ("Dicionário clínico (conflitos, alto risco, achados)", "A1, A2", "CT-101, CT-110",
         "Anexo A.2 é a fonte; o modelo não define risco livremente."),
        ("Farmacopeia da comparação de doses", "A9", "CT-111",
         "Lista própria da equipe; sem o arquivo, vale a regra de conflito de RF-16."),
        ("Autenticação e autorização", "fora do escopo (A8)", "CT-071, CT-075",
         "Demonstração local; exposição pública exige auth antes. Caso NAO APLICAVEL no MVP."),
        ("Metas de latência e de precisão", "fora do escopo (A7)", "CT-093, CT-100",
         "Os casos medem e registram; o aceite é pelos casos aprovados."),
        ("Formato final do upload (multipart × JSON)", "em aberto", "CT-001, CT-002, CT-012",
         "Os dois caminhos estão previstos na especificação; o contrato final deve ser registrado."),
    ]
    linhas_pend = [[par(a), par(b, "celula_b"), par(c, "mono"), par(d)] for a, b, c, d in pend]

    registro = [
        [par("Resultado", "celula_b"), par("PASSOU · FALHOU · BLOQUEADO · NAO APLICAVEL")],
        [par("Evidência", "celula_b"),
         par("Print, log ou arquivo que comprova o resultado observado; referenciar o caminho.")],
        [par("Defeito", "celula_b"), par("Identificador do defeito aberto com o resultado obtido e o esperado.")],
        [par("Bloqueio", "celula_b"),
         par("Registrar o motivo e a pendência do Anexo D que impede a execução.")],
    ]
    t_registro = Table(registro, colWidths=[28 * mm, LARGURA - 28 * mm])
    t_registro.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), SOFT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    blocos: list = [NextPageTemplate("capa"), *capa(), *sumario(), *como_ler(casos),
                    *visao_geral(casos, fixtures)]
    blocos += casos_por_suite(casos)
    blocos += anexo("Anexo A — Requisito → casos",
                    "RF-01 a RF-30, RN-01 a RN-07 e RNF-01 a RNF-11. Nenhum requisito da "
                    "especificação funcional fica sem caso.",
                    ["REQUISITO", "CASOS", "ONDE"], linhas_req,
                    [24 * mm, 15 * mm, LARGURA - 39 * mm])
    blocos += anexo("Anexo B — Item de aceite (§16) → casos",
                    "Os 15 critérios de aceite do MVP e os casos que os comprovam.",
                    ["ITEM", "CASOS", "ONDE"], linhas_aceite,
                    [26 * mm, 15 * mm, LARGURA - 41 * mm])
    blocos += anexo("Anexo C — Fixture → casos",
                    "Os 67 documentos fictícios do catálogo, cada um citado ao menos uma vez.",
                    ["FIXTURE", "CASOS", "ONDE"], linhas_fixture,
                    [54 * mm, 15 * mm, LARGURA - 69 * mm])
    blocos += anexo("Anexo D — Definições aplicadas e pendências",
                    "De onde vem cada definição que a EPT usa e o que ainda depende da equipe.",
                    ["DEFINIÇÃO", "ORIGEM", "CASOS", "ESTADO ESPERADO"], linhas_pend,
                    [46 * mm, 26 * mm, 30 * mm, LARGURA - 102 * mm])
    blocos += [
        Paragraph("Anexo E — Registro de execução", S["h1"]),
        Spacer(1, 2 * mm),
        Paragraph("Preencha no CSV, mantendo este documento como a versão de referência aprovada.",
                  S["pequeno"]),
        Spacer(1, 3 * mm),
        t_registro,
        Spacer(1, 8 * mm),
        Spacer(1, 10 * mm),
        Paragraph("Aprovação", S["h2"]),
        Paragraph("A EPT é o roteiro oficial de verificação do MVP. A execução completa dos casos "
                  "de prioridade Alta é a condição mínima para a entrega.", S["corpo_j"]),
        Spacer(1, 4 * mm),
        _tabela_assinaturas(),
        Spacer(1, 8 * mm),
        Paragraph("Encerramento", S["h2"]),
        Paragraph("Esta EPT cobre todos os casos de teste do MVP e é gerada por script a partir da "
                  "especificação e do "
                  "manifesto de fixtures: a cobertura é revalidada a cada geração. A execução "
                  "completa dos casos de prioridade Alta é a condição mínima para declarar o MVP "
                  "pronto para a banca.", S["corpo_j"]),
    ]
    return blocos


def _tabela_assinaturas() -> Table:
    """Três linhas de assinatura — o documento circula para aprovação da equipe."""
    papeis = ["Product / Pitch", "Agentes e IA", "Back-end e OCI / Front-end e QA"]
    vazio = Paragraph("&nbsp;", S["celula"])
    dados = [
        [Paragraph("PAPEL", S["tabela_cab"]), Paragraph("RESPONSÁVEL", S["tabela_cab"]),
         Paragraph("ASSINATURA", S["tabela_cab"]), Paragraph("DATA", S["tabela_cab"])],
        *[[par(p, "celula_b"), vazio, vazio, vazio] for p in papeis],
    ]
    t = Table(dados, colWidths=[46 * mm, 52 * mm, LARGURA - 46 * mm - 52 * mm - 26 * mm, 26 * mm],
              rowHeights=[None, 14 * mm, 14 * mm, 14 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def main() -> None:
    casos = carregar()
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        fixtures = [linha["id"] for linha in csv.DictReader(f)]

    doc = EPTDoc(SAIDA, )
    doc.page_label = ""  # preenchido pelo CanvasNumerado
    doc.multiBuild(montar(casos, fixtures), canvasmaker=CanvasNumerado)
    tamanho = os.path.getsize(SAIDA) / 1024
    print(f"PDF: {os.path.relpath(SAIDA, ROOT)} ({len(casos)} casos, {tamanho:.0f} KB)")


if __name__ == "__main__":
    main()
