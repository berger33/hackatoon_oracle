#!/usr/bin/env python3
"""Gera o PDF do mapa de documentos de teste do MediFlow."""
import csv
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs/testes/Mapa_de_Documentos_de_Teste_MediFlow.pdf")
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DJ", f"{FONT_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DJB", f"{FONT_DIR}/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DJM", f"{FONT_DIR}/DejaVuSansMono.ttf"))

W, H = A4
M = 42
CW = W - 2 * M

RED = colors.HexColor("#B42318")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#D1D5DB")
SOFT = colors.HexColor("#F9FAFB")
TINT = colors.HexColor("#FEF2F2")
GREEN = colors.HexColor("#047857")
AMBER = colors.HexColor("#B45309")

ROWS = list(csv.DictReader(open(os.path.join(ROOT, "tests/fixtures/manifest.csv"), encoding="utf-8")))
DEMO_IDS = ["Matriz_Receituario_Texto", "Matriz_Receituario_Pdf", "Matriz_Receituario_Imagem", "Matriz_LaudoDeImagem_Pdf", "Matriz_LaudoLaboratorial_Pdf", "Matriz_Guia_Pdf",
            "Matriz_RelatorioDeAlta_Pdf", "Matriz_Atestado_Texto", "Matriz_NaoIdentificado_Imagem", "Matriz_Outro_Texto", "Ausencia_Paciente_Nome", "Borda_Score_084"]


def _produced():
    import glob
    out = set()
    for pat in ("tests/fixtures/demo/*/expected.json", "tests/fixtures/catalogo/*/expected.json"):
        for p in glob.glob(os.path.join(ROOT, pat)):
            out.add(os.path.basename(os.path.dirname(p)))
    return out


PRODUCED = _produced()

TITLES = {
    "Matriz_Receituario_Texto": "Receituário — rotina (texto)",
    "Matriz_Receituario_Pdf": "Receituário — rotina, 2 medicamentos (PDF)",
    "Matriz_Receituario_Imagem": "Receituário — urgência com opioide (imagem)",
    "Matriz_LaudoDeImagem_Pdf": "TC de tórax — TEP agudo (PDF)",
    "Matriz_LaudoLaboratorial_Pdf": "Hemograma — rotina (PDF)",
    "Matriz_Guia_Pdf": "Guia de ressonância — eletiva (PDF)",
    "Matriz_RelatorioDeAlta_Pdf": "Relatório de alta — pneumonia (PDF)",
    "Matriz_Atestado_Texto": "Atestado de comparecimento (texto)",
    "Matriz_NaoIdentificado_Imagem": "Documento ilegível (imagem degradada)",
    "Matriz_Outro_Texto": "Comunicação administrativa (texto)",
    "Ausencia_Paciente_Nome": "Receita sem nome do paciente (texto)",
    "Borda_Score_084": "Receita com score forçado 0,84 (texto)",
}

PAGE = {"n": 0}


def _segments(word):
    """Divide uma palavra em pedaços quebras nos underscores (IDs e enums)."""
    if "_" not in word:
        return [word]
    parts, buf = [], ""
    for ch in word:
        buf += ch
        if ch == "_":
            parts.append(buf)
            buf = ""
    if buf:
        parts.append(buf)
    return parts


def wrap(text, font, size, maxw):
    out, cur = [], ""
    for word in text.split(" "):
        # quebra palavras longas: primeiro nos underscores, depois por caractere
        if pdfmetrics.stringWidth(word, font, size) > maxw:
            chunks, buf = [], ""
            for part in _segments(word):
                if pdfmetrics.stringWidth(buf + part, font, size) <= maxw:
                    buf += part
                else:
                    if buf:
                        chunks.append(buf)
                    buf = ""
                    while pdfmetrics.stringWidth(part, font, size) > maxw:
                        cut = len(part)
                        while cut > 1 and pdfmetrics.stringWidth(part[:cut], font, size) > maxw:
                            cut -= 1
                        chunks.append(part[:cut])
                        part = part[cut:]
                    buf = part
            if buf:
                chunks.append(buf)
            chunks = [c for c in chunks if c]
            if cur:
                out.append(cur)
                cur = ""
            out.extend(chunks[:-1])
            cur = chunks[-1] if chunks else ""
            continue
        test = (cur + " " + word).strip()
        if pdfmetrics.stringWidth(test, font, size) <= maxw:
            cur = test
        else:
            if cur:
                out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out or [""]


def new_page(c, title, subtitle=None, cover=False):
    if PAGE["n"]:
        c.showPage()
    PAGE["n"] += 1
    if cover:
        return
    c.setFillColor(INK)
    c.setFont("DJB", 8)
    c.drawString(M, H - 34, "MEDIFLOW · MAPA DE DOCUMENTOS DE TESTE")
    c.setFont("DJ", 7)
    c.setFillColor(MUTED)
    c.drawRightString(W - M, H - 34, "Hackathon ONE G10 · v1.1")
    c.setStrokeColor(LINE)
    c.line(M, H - 42, W - M, H - 42)

    c.setFillColor(INK)
    c.setFont("DJB", 16)
    c.drawString(M, H - 68, title)
    if subtitle:
        c.setFillColor(MUTED)
        c.setFont("DJ", 8.4)
        yy = H - 82
        for ln in wrap(subtitle, "DJ", 8.4, CW):
            c.drawString(M, yy, ln)
            yy -= 11

    c.setStrokeColor(LINE)
    c.line(M, 38, W - M, 38)
    c.setFont("DJ", 6.8)
    c.setFillColor(MUTED)
    c.drawString(M, 28, "Documento fictício — uso exclusivo em testes. Sem dados reais de pacientes.")
    c.drawRightString(W - M, 28, f"página {PAGE['n']}")


def fit_text(text, font, size, maxw):
    if pdfmetrics.stringWidth(text, font, size) <= maxw:
        return text
    out = text
    while out and pdfmetrics.stringWidth(out + "...", font, size) > maxw:
        out = out[:-1]
    return out.rstrip() + "..."


def table(c, x, y, cols, rows, header_bg=INK, font_size=6.6, row_h=11.4, zebra=True,
          fills=None, align=None, wrap_cols=None):
    """Desenha tabela simples; retorna y final. wrap_cols = índices com quebra de linha."""
    total = sum(w for w, _ in cols)
    c.setFillColor(header_bg)
    c.rect(x, y - row_h, total, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("DJB", font_size)
    cx = x
    for i, (wd, label) in enumerate(cols):
        c.drawString(cx + 2.4, y - row_h + 3.4, label)
        cx += wd
    yy = y - row_h
    c.setFont("DJ", font_size)
    used_h = row_h
    current_h = row_h
    for r_i, row in enumerate(rows):
        # altura da linha = maior número de linhas entre as colunas com wrap
        lines_per_cell = {}
        if wrap_cols:
            for ci in wrap_cols:
                if ci < len(row):
                    lines_per_cell[ci] = wrap(row[ci], "DJ", font_size, cols[ci][0] - 5)
        current_h = row_h * max([1] + [len(v) for v in lines_per_cell.values()])

        fill = None
        if fills and fills[r_i]:
            fill = fills[r_i]
        elif zebra and r_i % 2 == 1:
            fill = SOFT
        if fill:
            c.setFillColor(fill)
            c.rect(x, yy - current_h, total, current_h, fill=1, stroke=0)
        cx = x
        c.setFillColor(INK)
        for i, (wd, _) in enumerate(cols):
            raw = row[i] if i < len(row) else ""
            if i in lines_per_cell:
                for li, ln in enumerate(lines_per_cell[i]):
                    c.drawString(cx + 2.4, yy - row_h + 3.4 - li * row_h, ln)
            else:
                c.drawString(cx + 2.4, yy - row_h + 3.4, fit_text(raw, "DJ", font_size, wd - 5))
            cx += wd
        yy -= current_h
        used_h += current_h
    c.setStrokeColor(LINE)
    c.setLineWidth(0.4)
    c.rect(x, yy, total, used_h, fill=0, stroke=1)
    return yy


def kv(c, x, y, label, value, w_label=118):
    c.setFillColor(MUTED)
    c.setFont("DJB", 7)
    c.drawString(x, y, label.upper())
    c.setFillColor(INK)
    c.setFont("DJ", 8.6)
    c.drawString(x + w_label, y, value)


def bullets(c, x, y, items, size=8.4, lead=12.4, bullet="—", indent=11):
    for it in items:
        c.setFillColor(RED)
        c.setFont("DJB", size)
        c.drawString(x, y, bullet)
        c.setFillColor(INK)
        c.setFont("DJ", size)
        for j, line in enumerate(wrap(it, "DJ", size, CW - indent - 4)):
            c.drawString(x + indent, y, line)
            y -= lead
        y -= 3
    return y


def box(c, x, y, w, h, title, lines, bg=SOFT, border=LINE, title_color=INK):
    c.setFillColor(bg)
    c.setStrokeColor(border)
    c.setLineWidth(0.6)
    c.roundRect(x, y - h, w, h, 4, fill=1, stroke=1)
    c.setFillColor(title_color)
    c.setFont("DJB", 7.6)
    c.drawString(x + 8, y - 15, title)
    yy = y - 27
    c.setFillColor(INK)
    c.setFont("DJ", 7.2)
    for ln in lines:
        c.drawString(x + 8, yy, ln)
        yy -= 9.4


def main():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle("Mapa de Documentos de Teste — MediFlow")
    c.setAuthor("MediFlow — Hackathon ONE G10")
    c.setSubject("Catálogo completo de fixtures, status de produção e critérios de aceite")

    # ---------------------------------------------------------------- capa
    new_page(c, "", cover=True)
    c.setFillColor(RED)
    c.rect(0, H - 12, W, 12, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("DJB", 9)
    c.drawString(M, H - 56, "MEDIFLOW · HACKATHON ONE G10")
    c.setFont("DJ", 8.4)
    c.setFillColor(MUTED)
    c.drawString(M, H - 70, "Oracle Next Education & Alura · Grupo 10")

    c.setFillColor(INK)
    c.setFont("DJB", 38)
    c.drawString(M, H - 145, "Mapa de documentos")
    c.drawString(M, H - 186, "de teste")
    c.setFillColor(RED)
    c.setFont("DJ", 13)
    for i, ln in enumerate(wrap("Quantos fixtures o MediFlow precisa, quais são e o que cada um prova", "DJ", 13, CW - 10)):
        c.drawString(M, H - 222 - i * 18, ln)

    c.setStrokeColor(LINE)
    c.line(M, H - 258, W - M, H - 258)

    y = H - 286
    for label, value in [
        ("Projeto", "MediFlow — triagem, extração e roteamento de documentos clínicos"),
        ("Versão", "1.1 — 20/10/2026"),
        ("Base documental", "Projeto_oracle.pdf · Análise de Requisitos v1.1 · Especificação Funcional v1.0"),
        ("Escopo", "MVP do hackathon — somente dados fictícios, OCI Always Free"),
    ]:
        kv(c, M, y, label, value)
        y -= 18

    # números
    y -= 22
    n_produced = len(PRODUCED)
    n_files = 0
    import glob as _glob
    for _pat in ("tests/fixtures/demo/*/*", "tests/fixtures/catalogo/*/*"):
        n_files += len([f for f in _glob.glob(os.path.join(ROOT, _pat)) if os.path.isfile(f)])
    cards = [("67", "fixtures no catálogo"), (str(n_produced), "já produzidos"),
             (str(n_files), "arquivos no repositório"), ("8", "simulações sem arquivo")]
    cw = (CW - 3 * 10) / 4
    for i, (num, label) in enumerate(cards):
        x = M + i * (cw + 10)
        c.setFillColor(TINT)
        c.setStrokeColor(colors.HexColor("#F3D4D1"))
        c.roundRect(x, y - 62, cw, 62, 5, fill=1, stroke=1)
        c.setFillColor(RED)
        c.setFont("DJB", 24)
        c.drawCentredString(x + cw / 2, y - 34, num)
        c.setFillColor(MUTED)
        c.setFont("DJ", 7.4)
        c.drawCentredString(x + cw / 2, y - 50, label)
    y -= 100

    c.setFillColor(INK)
    c.setFont("DJB", 10)
    c.drawString(M, y, "Como este mapa está organizado")
    y -= 16
    y = bullets(c, M, y, [
        "Seção 1 — cobertura: os 8 tipos controlados contra os 4 formatos de entrada.",
        "Seção 2 — fluxo de decisão que cada fixture exercita (rotina, urgência, ambiguidade, erro).",
        "Seção 3 — kit de demonstração: os 12 casos de pitch, com TXT, PDF, JPG e expected.json.",
        "Seção 4 — catálogo completo dos 67 fixtures, bloco por bloco, com destino e status esperados.",
        "Seção 5 — pendências da especificação e como regenerar o catálogo.",
    ], size=8.6, lead=13)

    c.setFillColor(TINT)
    c.setStrokeColor(colors.HexColor("#F3D4D1"))
    c.roundRect(M, 92, CW, 46, 5, fill=1, stroke=1)
    c.setFillColor(RED)
    c.setFont("DJB", 8)
    c.drawString(M + 10, 122, "AVISO")
    c.setFillColor(INK)
    c.setFont("DJ", 7.6)
    c.drawString(M + 10, 110, "Todos os documentos deste catálogo são fictícios: nomes, CRMs, CID e resultados")
    c.drawString(M + 10, 100, "existem apenas para testar o agente. Nenhum dado de paciente real é usado.")

    # ---------------------------------------------------------------- 1. cobertura
    new_page(c, "1. Cobertura: tipos × formatos",
             "A matriz 8 × 4 é o piso do catálogo. Os números indicam quantos fixtures existem em cada célula.")

    types = ["RECEITUARIO_MEDICO", "LAUDO_EXAME_LABORATORIAL", "LAUDO_EXAME_IMAGEM",
             "GUIA_PROCEDIMENTO", "RELATORIO_ALTA_INTERNACAO", "ATESTADO_MEDICO",
             "OUTRO", "NAO_IDENTIFICADO"]
    cells = {(r["tipo_documento"], r["formato"]): 0 for r in ROWS for _ in [0]}
    for r in ROWS:
        key = (r["tipo_documento"], r["formato"])
        if key in cells:
            cells[key] += 1

    cols = [(148, "TIPO DE DOCUMENTO"), (62, "PDF"), (68, "PDF escaneado"), (58, "Imagem"), (52, "Texto"), (55, "Total")]
    data = []
    for t in types:
        row = [t]
        for f in ["PDF", "PDF_DIGITALIZADO", "IMAGEM", "TEXTO"]:
            n = cells.get((t, f), 0)
            row.append(str(n) if n else "—")
        row.append(str(sum(cells.get((t, f), 0) for f in ["PDF", "PDF_DIGITALIZADO", "IMAGEM", "TEXTO"])))
        data.append(row)
    table(c, M, H - 118, cols, data, font_size=7.2, row_h=15)

    y = H - 118 - 15 * (len(data) + 1) - 26
    c.setFillColor(INK)
    c.setFont("DJB", 10)
    c.drawString(M, y, "Leituras que mudam o plano")
    y -= 16
    y = bullets(c, M, y, [
        "OUTRO e NAO_IDENTIFICADO não são tipos que se escrevem: são resultados de classificação. Por isso cada um entra com 3 testes negativos (documento fora da taxonomia ou ilegível).",
        "JSON não é tipo de documento: é apenas o envelope da API. Um texto enviado como JSON continua sendo um documento de texto.",
        "PDF digital e PDF escaneado têm caminhos de leitura diferentes (RF-02/RF-04) e por isso colunas separadas.",
        "Especialidade médica é texto livre (RF-06) — não existe lista fechada e não é preciso um documento por especialidade.",
    ], size=8.2, lead=12)

    # resumo por bloco
    y -= 10
    c.setFillColor(INK)
    c.setFont("DJB", 10)
    c.drawString(M, y, "Composição do catálogo por bloco")
    y -= 14
    blocos = [
        ("Matriz", "Tipos × formatos", 24, "24"),
        ("Ausencia", "Campos ausentes", 8, "32"),
        ("Borda", "Fronteira do limiar (0,84 e 0,85)", 2, "34"),
        ("Conflito", "Contradições e alto risco", 5, "39"),
        ("Simultaneo", "Urgência + ambiguidade simultâneas", 2, "41"),
        ("Qualidade", "Ilegibilidade e PDFs especiais", 8, "49"),
        ("Validacao", "Negativos técnicos de entrada", 8, "57"),
        ("Escaneado", "PDF escaneado dos 6 tipos restantes", 6, "63"),
        ("Diferencial", "Itens opcionais", 4, "67"),
    ]
    table(c, M, y, [(72, "Bloco"), (196, "O que cobre"), (56, "Arquivos"), (60, "Acumulado")],
          [[b, d, str(n), acc] for b, d, n, acc in blocos], font_size=7.2, row_h=13)

    y = y - 13 * (len(blocos) + 1) - 20
    c.setFillColor(TINT)
    c.setStrokeColor(colors.HexColor("#F3D4D1"))
    c.roundRect(M, y - 58, CW, 58, 5, fill=1, stroke=1)
    c.setFillColor(RED)
    c.setFont("DJB", 8)
    c.drawString(M + 10, y - 20, "MÍNIMO LITERAL DOS CRITÉRIOS DE ACEITE (§16)")
    c.setFillColor(INK)
    c.setFont("DJ", 7.8)
    c.drawString(M + 10, y - 34, "8 arquivos: texto + um PDF + uma imagem do mesmo caso, mais as 5 variações de campo ausente.")
    c.drawString(M + 10, y - 46, "Passa na leitura literal, mas não prova os 5 destinos nem as 8 classes de tipo. Não use como meta.")
    c.drawString(M + 10, y - 56, "Meta recomendada: 57 arquivos. Demonstração mínima: 12.")

    # ---------------------------------------------------------------- 2. fluxo
    new_page(c, "2. Fluxo de decisão que os fixtures exercitam",
             "Cada caminho precisa de pelo menos um documento diferente para ser comprovado.")

    def step(x, y, w, h, title, lines, bg=SOFT, border=LINE, tcolor=INK, num=None):
        c.setFillColor(bg)
        c.setStrokeColor(border)
        c.setLineWidth(0.7)
        c.roundRect(x, y - h, w, h, 5, fill=1, stroke=1)
        if num:
            c.setFillColor(tcolor)
            c.setFont("DJB", 6.4)
            c.drawString(x + 9, y - 13, num)
        c.setFillColor(tcolor)
        c.setFont("DJB", 7.4)
        for i, ln in enumerate(wrap(title, "DJB", 7.4, w - 18)):
            c.drawString(x + 9, y - 26 - i * 9, ln)
        c.setFillColor(INK)
        c.setFont("DJ", 7.0)
        yy = y - 26 - len(wrap(title, "DJB", 7.4, w - 18)) * 9 - 5
        for ln in lines:
            for part in wrap(ln, "DJ", 7.0, w - 18):
                c.drawString(x + 9, yy, part)
                yy -= 9.2

    # cadeia de entrada
    chain = [("1. ENTRADA", ["PDF digital · PDF escaneado", "Imagem · texto"], "RF-01 / RF-02"),
             ("2. VALIDAÇÃO", ["formato, tamanho, MIME", "envelope da requisição"], "RF-03"),
             ("3. LEITURA", ["Gemini multimodal", "classificação + extração"], "RF-04"),
             ("4. GRAFO", ["scores, conflitos", "regras determinísticas"], "RF-16 a RF-19")]
    gap = 12
    bw = (CW - 3 * gap) / 4
    ytop = H - 110
    for i, (t, lines, ref) in enumerate(chain):
        x = M + i * (bw + gap)
        step(x, ytop, bw, 62, t, lines, num=ref)
        if i < 3:
            c.setStrokeColor(MUTED)
            c.setLineWidth(0.9)
            ax = x + bw + 2
            c.line(ax, ytop - 31, ax + gap - 4, ytop - 31)
            c.setFillColor(MUTED)
            c.setFont("DJ", 6)
            c.drawCentredString(ax + (gap - 4) / 2, ytop - 27, "→")

    # ramos de decisão
    ybr = ytop - 88
    c.setFillColor(INK)
    c.setFont("DJB", 9)
    c.drawString(M, ybr, "Cinco desfechos possíveis")
    ybr -= 12
    cards = [
        ("URGENTE / CRÍTICO", ["destino FILA_URGENCIA_MEDICA", "alerta simulado registrado", "status EM_REVISAO"], RED, colors.HexColor("#FEF2F2"), colors.HexColor("#F3D4D1")),
        ("AMBÍGUO / ILEGÍVEL", ["destino FILA_REVISAO_HUMANA", "campos incertos preservados", "status EM_REVISAO"], AMBER, colors.HexColor("#FFFBEB"), colors.HexColor("#FDE68A")),
        ("ROTINA (score ≥ 0,85)", ["FARMACIA · AUDITORIA · PRONTUARIO", "revisão apenas se outra regra exigir", "status PROCESSADO"], GREEN, colors.HexColor("#ECFDF5"), colors.HexColor("#A7F3D0")),
    ]
    cg = 10
    cw3 = (CW - 2 * cg) / 3
    for i, (t, lines, tcol, bg, bd) in enumerate(cards):
        step(M + i * (cw3 + cg), ybr, cw3, 74, t, lines, bg=bg, border=bd, tcolor=tcol)

    ybr -= 74 + 26
    c.setFillColor(INK)
    c.setFont("DJB", 9.4)
    c.drawString(M, ybr, "Fixture que exercita cada caminho")
    ybr -= 14
    ybr = table(c, M, ybr, [(80, "Caminho"), (322, "Fixtures de teste"), (96, "Bloco")],
                [["Rotina", "Matriz_Receituario_Texto · Matriz_Receituario_Pdf · Matriz_LaudoLaboratorial_Pdf · Matriz_Guia_Pdf · Matriz_RelatorioDeAlta_Pdf · Matriz_Atestado_Texto", "Matriz"],
                 ["Urgência", "Matriz_Receituario_Imagem · Matriz_LaudoDeImagem_Pdf · Conflito_AltoRisco", "Matriz · Conflito"],
                 ["Ambiguidade", "Matriz_NaoIdentificado_Imagem · Matriz_Outro_Texto · Ausencia_Paciente_Nome · Borda_Score_084", "Matriz · Ausência · Borda"],
                 ["Urgência + ambiguidade", "Simultaneo_Urgencia_Ilegivel · Simultaneo_Urgencia_Score", "Simultâneo"],
                 ["Erro de entrada", "Validacao_ArquivoDocx · Validacao_ArquivoVazio · Validacao_JsonMalformado · Validacao_MimeInvalido", "Validação"],
                 ["Erro de provedor/OCI", "falhas de Gemini e OCI são simuladas por stub, sem arquivo novo", "Simulação"]],
                font_size=6.4, row_h=9.6, wrap_cols=[0, 1, 2])

    ybr -= 22
    c.setFillColor(INK)
    c.setFont("DJB", 9.4)
    c.drawString(M, ybr, "Regras de bolso")
    ybr -= 14
    bullets(c, M, ybr, [
        "Urgência nunca vira rotina, mesmo com score baixo (RN-03, RNF-02).",
        "Score combinado = mínimo entre classificação e extração; abaixo de 0,85 obriga revisão (RF-18).",
        "Cinco ausências obrigam revisão: nome do paciente, idade, nome do médico, CRM e diagnóstico.",
        "CID, medicamentos e exames ausentes NÃO obrigam revisão por si só (RF-21).",
        "Nada é preenchido por inferência: ausente fica null e entra em campos_ausentes (RF-15).",
    ], size=8.2, lead=11.8)

    # ---------------------------------------------------------------- 3. kit demo
    new_page(c, "3. Kit de demonstração — 12 casos prontos",
             "Cada caso foi gerado em TXT, PDF e JPG, com expected.json ao lado. Caminho: tests/fixtures/demo/")

    demo_rows = []
    for i, fid in enumerate(DEMO_IDS, 1):
        r = next(x for x in ROWS if x["id"] == fid)
        demo_rows.append([str(i), fid, TITLES[fid], r["destinos_esperados"], r["status_esperado"],
                          "SIM" if r["revisao_humana"] == "SIM" else "—"])
    table(c, M, H - 118, [(16, "#"), (112, "ID"), (150, "Caso"), (108, "Destino esperado"),
                          (76, "Status"), (28, "Rev.")],
          demo_rows, font_size=6.2, row_h=15.6, wrap_cols=[1, 2])

    y = H - 118 - 15.6 * 13 - 22
    c.setFillColor(INK)
    c.setFont("DJB", 9.6)
    c.drawString(M, y, "Conteúdo de cada pasta")
    y -= 14
    table(c, M, y, [(92, "Arquivo"), (300, "O que é"), (80, "Formato")],
          [["{ID}.txt", "Documento em texto puro", "UTF-8"],
           ["{ID}.pdf", "Mesma peça em PDF digital, com camada de texto", "PDF 1.4"],
           ["{ID}.jpg", "Mesma peça fotografada e levemente inclinada", "JPEG 150 dpi"],
           ["expected.json", "Saída esperada: tipo, prioridade, destinos, revisão, asserções", "JSON"]],
          font_size=7.0, row_h=14)

    y = y - 14 * 5 - 22
    c.setFillColor(INK)
    c.setFont("DJB", 9.6)
    c.drawString(M, y, "Cobertura do kit")
    y -= 14
    y = bullets(c, M, y, [
        "5 destinos lógicos: urgência, farmácia, auditoria de autorizações, prontuário e revisão humana.",
        "3 formatos de entrada + 8 classes de tipo (6 clínicos, OUTRO e NAO_IDENTIFICADO).",
        "3 cenários obrigatórios do hackathon: rotina, urgência e ambiguidade.",
        "2 regras de borda: ausência de campo obrigatório e score abaixo de 0,85.",
    ], size=8.2, lead=11.6)

    # ---------------------------------------------------------------- 4. catálogo
    blocks = [
        ("Matriz", "4.1 Bloco Matriz — tipos × formatos (24)"),
        ("Ausencia", "4.2 Bloco Ausência — campos ausentes (8)"),
        ("Borda", "4.3 Bloco Borda — fronteira do limiar (2)"),
        ("Conflito", "4.4 Bloco Conflito — contradições e alto risco (5)"),
        ("Simultaneo", "4.5 Bloco Simultâneo — urgência + ambiguidade (2)"),
        ("Qualidade", "4.6 Bloco Qualidade — ilegibilidade e PDFs especiais (8)"),
        ("Validacao", "4.7 Bloco Validação — negativos técnicos de entrada (8)"),
        ("Escaneado", "4.8 Bloco Escaneado — PDF digitalizado dos tipos restantes (6)"),
        ("Diferencial", "4.9 Bloco Diferencial — itens opcionais (4)"),
    ]
    colspec = [(122, "ID / pasta"), (92, "Tipo"), (46, "Formato"), (44, "Cenário"),
               (76, "Destino esperado"), (94, "Status / HTTP"), (14, "Rev"), (20, "OK")]
    formato_rotulo = {"PDF": "PDF", "IMAGEM": "Imagem", "TEXTO": "Texto",
                      "PDF_DIGITALIZADO": "PDF escaneado", "DOCX": "DOCX",
                      "ARQUIVO_0KB": "Arquivo vazio", "JSON": "JSON", "MULTIPART": "Multipart",
                      "ZIP": "ZIP", "ARQUIVO_25MB": "Arquivo 25 MB", "PDF_FALSO": "PDF falso"}
    WRAP = [0, 1, 2, 4, 5]
    FS, RH = 5.2, 8.4

    def rh(row):
        n = 1
        for ci in WRAP:
            n = max(n, len(wrap(row[ci], "DJ", FS, colspec[ci][0] - 5)))
        return RH * n

    new_page(c, "4. Catálogo completo — 67 fixtures",
             "Rev = requer auditoria humana · OK = fixture produzido e versionado")
    y = H - 104
    for key, title in blocks:
        rows = [r for r in ROWS if r["bloco"] == key]
        data, fills = [], []
        for r in rows:
            data.append([r["id"], r["tipo_documento"],
                         formato_rotulo.get(r["formato"], r["formato"].replace("_", " ").title()),
                         r["cenario"].title(), r["destinos_esperados"], r["status_esperado"],
                         "S" if r["revisao_humana"] == "SIM" else "—",
                         "✓" if r["id"] in PRODUCED else ""])
            fills.append(colors.HexColor("#F0FDF4") if r["id"] in PRODUCED else None)

        if y - 40 < 90:
            new_page(c, "4. Catálogo completo (continuação)",
                     "Rev = requer auditoria humana · OK = fixture produzido e versionado")
            y = H - 104

        c.setFillColor(INK)
        c.setFont("DJB", 9.4)
        c.drawString(M, y - 4, title)
        y -= 16

        # quebra o bloco em partes que cabem na página
        i = 0
        while i < len(data):
            chunk, h = [], RH
            while i < len(data) and y - h - rh(data[i]) > 78:
                chunk.append((data[i], fills[i]))
                h += rh(data[i])
                i += 1
            if not chunk:
                new_page(c, "4. Catálogo completo (continuação)",
                         "Rev = requer auditoria humana · OK = fixture produzido e versionado")
                y = H - 104
                continue
            y = table(c, M, y, colspec, [c0 for c0, _ in chunk], font_size=FS,
                      row_h=RH, fills=[f for _, f in chunk], wrap_cols=WRAP)
            y -= 8
            if i < len(data):
                new_page(c, "4. Catálogo completo (continuação)",
                         "Rev = requer auditoria humana · OK = fixture produzido e versionado")
                y = H - 104
        y -= 16

    c.setFillColor(MUTED)
    c.setFont("DJ", 7.2)
    c.drawString(M, max(y, 62), "Cada linha corresponde a um arquivo de entrada. O bloco Validacao usa envelope de erro (HTTP + código); os PDFs ilegíveis usam ERRO_PROCESSAMENTO.")

    # ---------------------------------------------------------------- 5. pendências
    new_page(c, "5. Pendências e regeneração",
             "Pontos abertos na especificação v1.0 (§15) que ainda impedem resposta inequívoca em parte dos fixtures.")

    pend = [
        ["Limite de tamanho, páginas, MIME, timeout e retry", "Validacao_ArquivoGrande, Qualidade_Pdf_Multipagina", "Fixar: 10 MB, 10 páginas, timeout 30 s, 2 retries"],
        ["Contrato final do upload (multipart × JSON)", "Validacao_SemConteudo, Validacao_EnvelopeVazio, Validacao_MimeInvalido", "Multipart para arquivo; JSON para texto"],
        ["Dicionário de achado crítico e alto risco", "Conflito_Cid_Diagnostico, Conflito_Dose, Conflito_AltoRisco", "Criar rules/cid10.csv e rules/medicamentos_alto_risco.csv"],
        ["Urgência isolada exige revisão?", "Resolvido no contrato (R1)", "Auditoria na própria fila de urgência; FILA_REVISAO_HUMANA só com ambiguidade (R4)"],
        ["Autenticação e autorização", "403 e consulta por terceiros", "Fora do MVP; se entrar, criar fixture de acesso negado"],
        ["Política de retenção e exclusão", "Teste de persistência no OCI", "Definir antes de qualquer dado real (que não deve existir)"],
        ["Meta de latência e precisão", "Medição do primeiro pipeline", "Medir e só então fixar a meta"],
    ]
    y_end = table(c, M, H - 118, [(168, "Pendência"), (150, "O que fica bloqueado"), (191, "Recomendação")],
                  pend, font_size=6.4, row_h=11.4, wrap_cols=[0, 1, 2])

    y = y_end - 30
    c.setFillColor(INK)
    c.setFont("DJB", 9.6)
    c.drawString(M, y, "Como regenerar o catálogo")
    y -= 15
    steps = [
        "Instalar as dependências: python3 -m pip install -r requirements.txt.",
        "python3 tools/gerar_fixtures_demo.py — recria os 12 casos do kit de demonstração.",
        "python3 tools/gerar_fixtures_catalogo.py — recria os 55 restantes, incluindo PDFs escaneados, senha e corrompido.",
        "python3 tools/gerar_mapa_documentos.py — recria este PDF.",
        "python3 tests/testar_contrato.py — confere os 67 expected.json no contrato (app/models.py).",
    ]
    for i, st in enumerate(steps, 1):
        c.setFillColor(RED)
        c.setFont("DJB", 8.4)
        c.drawString(M, y, f"{i}.")
        c.setFillColor(INK)
        c.setFont("DJ", 8.4)
        for ln in wrap(st, "DJ", 8.4, CW - 16):
            c.drawString(M + 16, y, ln)
            y -= 11.6
        y -= 3

    y -= 14
    c.setFillColor(TINT)
    c.setStrokeColor(colors.HexColor("#F3D4D1"))
    c.roundRect(M, y - 52, CW, 52, 5, fill=1, stroke=1)
    c.setFillColor(RED)
    c.setFont("DJB", 8)
    c.drawString(M + 10, y - 18, "REGRA DE OURO DOS FIXTURES")
    c.setFillColor(INK)
    c.setFont("DJ", 7.8)
    c.drawString(M + 10, y - 32, "Nunca compare score exato do modelo: ele não é probabilidade calibrada (RF-17).")
    c.drawString(M + 10, y - 44, "Compare faixas (< 0,85) e, nas bordas, use FIXTURE_MODE para forçar os scores.")

    # ---------------------------------------------------------------- 6. referências
    new_page(c, "6. Arquivos e referências",
             "Tudo versionado no repositório, exceto os PDFs de origem que ficam no Google Drive.")

    y = H - 112
    table(c, M, y, [(210, "Arquivo"), (299, "Conteúdo")],
          [["docs/testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md", "Catálogo analítico completo, regras e rastreabilidade"],
           ["docs/testes/Mapa_de_Documentos_de_Teste_MediFlow.pdf", "Este documento"],
           ["tests/fixtures/manifest.csv", "Os 67 fixtures em formato de máquina"],
           ["tests/fixtures/demo/", "12 casos de pitch × (TXT + PDF + JPG + expected.json)"],
           ["tests/fixtures/catalogo/", "55 casos restantes, incluindo os 8 negativos técnicos"],
           ["tools/gerar_fixtures_*.py", "Geradores reprodutíveis de todo o catálogo"],
           ["tests/fixtures/README.md", "Convenção de nomes e regras de produção"],
           ["README.md", "Visão do produto, arquitetura e critérios de aceite"]],
          font_size=6.8, row_h=16)

    y = y - 16 * 9 - 30
    c.setFillColor(INK)
    c.setFont("DJB", 9.6)
    c.drawString(M, y, "Base documental (Google Drive)")
    y -= 15
    y = bullets(c, M, y, [
        "Projeto_oracle.pdf — brief do hackathon: formatos, entregáveis e checklist de avaliação.",
        "MediFlow_-_Análise_de_Requisitos_v1.1.pdf — requisitos RF/RNF/RN e decisões do time.",
        "MediFlow_Especificacao_Funcional_v1.0.pdf — §5 vocabulário, §7 requisitos, §8 regras, §16 critérios de aceite.",
    ], size=8.4, lead=12)

    y -= 12
    c.setFillColor(MUTED)
    c.setFont("DJ", 7.4)
    for ln in wrap("Este documento e todos os fixtures citados usam exclusivamente dados fictícios, "
                   "em conformidade com a decisão registrada na seção 15 da especificação funcional. "
                   "Nenhum nome, CRM, CID ou resultado clínico corresponde a pessoa real.", "DJ", 7.4, CW):
        c.drawString(M, y, ln)
        y -= 10

    c.save()
    print("ok:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
