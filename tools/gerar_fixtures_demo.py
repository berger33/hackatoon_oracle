#!/usr/bin/env python3
"""Gera o kit de demonstração do MediFlow: 12 casos x 3 rendições + expected.json."""
import json
import os
import tempfile
from io import BytesIO

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import pymupdf as fitz

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
OUT = os.path.join(ROOT, "tests/fixtures/demo")
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DejaVu", f"{FONT_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", f"{FONT_DIR}/DejaVuSans-Bold.ttf"))

W, H = A4
MARGIN = 46
CONTENT_W = W - 2 * MARGIN
RED = HexColor("#B42318")
INK = HexColor("#1F2937")
MUTED = HexColor("#6B7280")
LINE = HexColor("#D1D5DB")
SOFT = HexColor("#F3F4F6")

HOSPITAL = "HOSPITAL AURORA — UNIDADE DE DEMONSTRAÇÃO"
HOSPITAL_SUB = "Rede Fictícia de Saúde · CNPJ 00.000.000/0001-00 · Cidade Fictícia/SP"
FICTION = "DOCUMENTO FICTÍCIO — USO EXCLUSIVO EM TESTES — SEM VALIDADE CLÍNICA"


def wrap(text, font, size, maxw):
    lines = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        cur = ""
        for word in para.split(" "):
            test = (cur + " " + word).strip()
            if pdfmetrics.stringWidth(test, font, size) <= maxw:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                while pdfmetrics.stringWidth(word, font, size) > maxw:
                    cut = len(word)
                    while cut > 1 and pdfmetrics.stringWidth(word[:cut], font, size) > maxw:
                        cut -= 1
                    lines.append(word[:cut])
                    word = word[cut:]
                cur = word
        lines.append(cur)
    return lines


def header(c, case):
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 12.5)
    c.drawString(MARGIN, H - 44, HOSPITAL)
    c.setFont("DejaVu", 7.2)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, H - 56, HOSPITAL_SUB)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.line(MARGIN, H - 64, W - MARGIN, H - 64)

    c.setFillColor(RED)
    c.rect(MARGIN, H - 82, CONTENT_W, 14, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("DejaVu-Bold", 7.2)
    c.drawString(MARGIN + 6, H - 78, FICTION)
    # o ID pode ser longo: reduz a fonte até caber à direita do aviso
    label = f"Fixture {case['id']}"
    room = CONTENT_W - 12 - pdfmetrics.stringWidth(FICTION, "DejaVu-Bold", 7.2) - 10
    size = 7.0
    while size > 4.6 and pdfmetrics.stringWidth(label, "DejaVu", size) > room:
        size -= 0.2
    c.setFont("DejaVu", size)
    if pdfmetrics.stringWidth(label, "DejaVu", size) > room:
        while label and pdfmetrics.stringWidth(label + "...", "DejaVu", size) > room:
            label = label[:-1]
        label = label.rstrip() + "..."
    c.drawRightString(W - MARGIN - 6, H - 78, label)


def footer(c, case):
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(MARGIN, 42, W - MARGIN, 42)
    c.setFillColor(MUTED)
    right = "página 1 de 1 · gerado para testes automatizados"
    c.setFont("DejaVu", 7.0)
    room = CONTENT_W - pdfmetrics.stringWidth(right, "DejaVu", 7.0) - 12
    left = f"MediFlow · fixture {case['id']} · dados sintéticos"
    if pdfmetrics.stringWidth(left, "DejaVu", 7.0) > room:
        left = f"MediFlow · dados sintéticos"
    c.drawString(MARGIN, 30, left)
    c.drawRightString(W - MARGIN, 30, right)


def watermark(c):
    c.saveState()
    c.translate(W / 2, H / 2)
    c.rotate(42)
    c.setFillColor(Color(0.97, 0.90, 0.90, alpha=1))
    c.setFont("DejaVu-Bold", 78)
    c.drawCentredString(0, -20, "FICTÍCIO")
    c.restoreState()


def draw_pdf(case, path):
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle(f"{case['title']} — {case['id']} (fictício)")
    c.setAuthor("MediFlow — Hackathon ONE G10")
    c.setSubject("Documento fictício para testes do agente de triagem")
    watermark(c)
    header(c, case)
    footer(c, case)

    y = H - 112
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 16)
    c.drawString(MARGIN, y, case["title"])
    y -= 15
    c.setFont("DejaVu", 9)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, y, case["subtitle"])
    y -= 22

    # metadados em duas colunas
    c.setFillColor(SOFT)
    c.roundRect(MARGIN, y - 44, CONTENT_W, 50, 4, fill=1, stroke=0)
    yy = y - 8
    for i, (label, value) in enumerate(case["meta"]):
        col = i % 2
        row = i // 2
        x = MARGIN + 10 + col * (CONTENT_W / 2)
        ly = yy - row * 14
        c.setFillColor(MUTED)
        c.setFont("DejaVu-Bold", 7.2)
        c.drawString(x, ly, label.upper())
        c.setFillColor(INK)
        c.setFont("DejaVu", 8.6)
        c.drawString(x + 72, ly, value)
    y -= 62

    for heading, body in case["sections"]:
        c.setFillColor(RED)
        c.setFont("DejaVu-Bold", 8.2)
        c.drawString(MARGIN, y, heading.upper())
        y -= 3
        c.setStrokeColor(HexColor("#F3D4D1"))
        c.setLineWidth(0.6)
        c.line(MARGIN, y, W - MARGIN, y)
        y -= 13
        c.setFillColor(INK)
        c.setFont("DejaVu", 9.2)
        for line in wrap(body, "DejaVu", 9.2, CONTENT_W):
            if y < 105:
                raise RuntimeError(f"Conteúdo não coube em uma página: {case['id']}")
            c.drawString(MARGIN, y, line)
            y -= 12.6
        y -= 9

    # assinatura
    y = max(y, 120)
    c.setStrokeColor(INK)
    c.setLineWidth(0.7)
    c.line(MARGIN, y, MARGIN + 220, y)
    y -= 12
    c.setFont("DejaVu-Bold", 9)
    c.setFillColor(INK)
    c.drawString(MARGIN, y, case["doctor"][0])
    y -= 11
    c.setFont("DejaVu", 8.4)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, y, case["doctor"][1])

    c.showPage()
    c.save()


def write_txt(case, path):
    lines = [
        HOSPITAL,
        HOSPITAL_SUB,
        "=" * 78,
        FICTION,
        "=" * 78,
        "",
        case["title"],
        case["subtitle"],
        "",
        f"Fixture: {case['id']}",
    ]
    for label, value in case["meta"]:
        lines.append(f"{label}: {value}")
    lines.append("")
    for heading, body in case["sections"]:
        lines.append(heading.upper())
        lines.extend(body.split("\n"))
        lines.append("")
    lines += ["-" * 78, case["doctor"][0], case["doctor"][1], "-" * 78,
              f"MediFlow · fixture {case['id']} · dados sintéticos · página 1 de 1"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def render_jpg(pdf_path, jpg_path, degrade=False):
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()

    if degrade:
        # mantém o cabeçalho e o rodapé de identificação legíveis; degrada só o miolo
        img = img.rotate(2.1, resample=Image.BICUBIC, expand=True, fillcolor=(246, 246, 244))
        w, h = img.size
        top = int(h * 0.155)
        bottom = int(h * 0.905)
        body = img.crop((0, top, w, bottom))
        body = body.filter(ImageFilter.GaussianBlur(4.6))
        body = ImageEnhance.Contrast(body).enhance(0.62)
        body = ImageEnhance.Brightness(body).enhance(0.98)
        noise = Image.effect_noise(body.size, 30).convert("L")
        body = Image.composite(body, Image.new("RGB", body.size, (240, 240, 238)),
                               noise.point(lambda px: 26 if px > 138 else 0))
        img = img.copy()
        img.paste(body, (0, top))
        quality = 74
    else:
        img = img.rotate(-0.35, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
        quality = 86

    img = ImageOps.expand(img, border=14, fill=(228, 228, 226))
    img.save(jpg_path, "JPEG", quality=quality, optimize=True)


def make_degraded(case, pdf_path, jpg_path):
    """Gera um PDF somente-imagem e um JPG fortemente desfocado."""
    tmp_pdf = tempfile.mktemp(suffix=".pdf")
    tmp_jpg = tempfile.mktemp(suffix=".jpg")
    draw_pdf(case, tmp_pdf)
    render_jpg(tmp_pdf, tmp_jpg, degrade=True)

    # jpg final
    img = Image.open(tmp_jpg)
    img.save(jpg_path, "JPEG", quality=72, optimize=True)

    # pdf somente imagem
    doc = fitz.open()
    page = doc.new_page(width=W, height=H)
    page.insert_image(fitz.Rect(0, 0, W, H), filename=tmp_jpg)
    doc.save(pdf_path, deflate=True)
    doc.close()
    os.unlink(tmp_pdf)
    os.unlink(tmp_jpg)


CASES = []


def C(**kw):
    CASES.append(kw)


C(
    id="Matriz_Receituario_Texto",
    title="RECEITUÁRIO MÉDICO",
    subtitle="Prescrição ambulatorial — rotina",
    meta=[("Paciente", "Marina Alves Ferreira"), ("Idade", "34 anos"),
          ("Documento", "DOC-REC-2026-0001"), ("Data", "12/10/2026"),
          ("Origem", "Ambulatório de Clínica Médica")],
    sections=[
        ("Hipótese diagnóstica", "Cefaleia tensional — CID-10 G44.2."),
        ("Prescrição", "1. Dipirona sódica 500 mg — 1 comprimido por via oral a cada 8 horas, por 3 dias.\n2. Hidratação oral e repouso por 24 horas."),
        ("Orientações", "Retornar ao ambulatório se a dor persistir por mais de 72 horas ou se surgirem sinais neurológicos."),
    ],
    doctor=("Dra. Helena Prado", "CRM 187432-SP"),
    expected={
        "tipo_documento": "RECEITUARIO_MEDICO", "especialidade": ["Clínica Médica"],
        "prioridade": "ROTINA", "status": "PROCESSADO", "destinos": ["FARMACIA_HOSPITALAR"],
        "revisao": False, "notificacao": False,
        "dados": {"paciente": {"nome": "Marina Alves Ferreira", "idade": 34},
                  "medico": {"nome": "Dra. Helena Prado", "crm": {"numero": "187432", "uf": "SP"}},
                  "diagnostico": "Cefaleia tensional", "cid": "G44.2",
                  "medicamentos": ["Dipirona sódica 500 mg"], "exames": [], "urgencia": "NAO"},
        "assercoes": ["Texto aceito e classificado como receituário",
                      "Prioridade ROTINA e destino FARMACIA_HOSPITALAR",
                      "Nenhum campo obrigatório ausente", "Sem revisão humana e sem alerta"],
    },
)

C(
    id="Matriz_Receituario_Pdf",
    title="RECEITUÁRIO MÉDICO",
    subtitle="Prescrição ambulatorial — rotina com dois medicamentos",
    meta=[("Paciente", "Rafael Nunes de Souza"), ("Idade", "58 anos"),
          ("Documento", "DOC-REC-2026-0002"), ("Data", "13/10/2026"),
          ("Origem", "Ambulatório de Cardiologia")],
    sections=[
        ("Hipótese diagnóstica", "Hipertensão arterial sistêmica — CID-10 I10."),
        ("Prescrição", "1. Losartana potássica 50 mg — 1 comprimido por via oral uma vez ao dia, por 30 dias.\n2. Hidroclorotiazida 25 mg — 1 comprimido por via oral uma vez ao dia, por 30 dias."),
        ("Orientações", "Manter dieta hipossódica, atividade física regular e retorno em 30 dias para controle pressórico."),
    ],
    doctor=("Dr. Paulo Mendes Rocha", "CRM 203114-RJ"),
    expected={
        "tipo_documento": "RECEITUARIO_MEDICO", "especialidade": ["Cardiologia"],
        "prioridade": "ROTINA", "status": "PROCESSADO", "destinos": ["FARMACIA_HOSPITALAR"],
        "revisao": False, "notificacao": False,
        "dados": {"paciente": {"nome": "Rafael Nunes de Souza", "idade": 58},
                  "medico": {"nome": "Dr. Paulo Mendes Rocha", "crm": {"numero": "203114", "uf": "RJ"}},
                  "diagnostico": "Hipertensão arterial sistêmica", "cid": "I10",
                  "medicamentos": ["Losartana potássica 50 mg", "Hidroclorotiazida 25 mg"],
                  "exames": [], "urgencia": "NAO"},
        "assercoes": ["PDF digital aceito", "Dois medicamentos extraídos com dose e frequência",
                      "Destino FARMACIA_HOSPITALAR sem revisão"],
    },
)

C(
    id="Matriz_Receituario_Imagem",
    title="RECEITUÁRIO MÉDICO",
    subtitle="Prescrição em pronto-socorro — sinal de urgência",
    meta=[("Paciente", "João Batista Nogueira"), ("Idade", "67 anos"),
          ("Documento", "DOC-REC-2026-0003"), ("Data", "14/10/2026"),
          ("Origem", "Pronto-Socorro")],
    sections=[
        ("Hipótese diagnóstica", "Dor pós-operatória aguda intensa — CID-10 R52.1."),
        ("Prescrição", "1. Morfina 10 mg/mL — 1 mL por via intravenosa, dose única, administrar agora.\n2. Dipirona 1 g por via intravenosa se dor persistente após 30 minutos."),
        ("Sinal de urgência", "PACIENTE EM PÓS-OPERATÓRIO IMEDIATO. ADMINISTRAÇÃO COM URGÊNCIA NAS PRÓXIMAS 2 HORAS."),
    ],
    doctor=("Dra. Camila Ferreira Lopes", "CRM 198765-SP"),
    expected={
        "tipo_documento": "RECEITUARIO_MEDICO", "especialidade": ["Clínica Médica"],
        "prioridade": "URGENTE", "status": "EM_REVISAO", "destinos": ["FILA_URGENCIA_MEDICA"],
        "revisao": True, "notificacao": True,
        "dados": {"paciente": {"nome": "João Batista Nogueira", "idade": 67},
                  "medico": {"nome": "Dra. Camila Ferreira Lopes", "crm": {"numero": "198765", "uf": "SP"}},
                  "diagnostico": "Dor pós-operatória aguda intensa", "cid": "R52.1",
                  "medicamentos": ["Morfina 10 mg/mL", "Dipirona 1 g"],
                  "exames": [], "urgencia": "SIM"},
        "assercoes": ["Imagem aceita", "Sinal textual de urgência detectado",
                      "Destino FILA_URGENCIA_MEDICA com alerta simulado",
                      "Nunca encaminhado como rotina"],
        "obs": "Prescrição de alto risco (opioide) com urgência explícita: dispara RN-03 pelo texto, sem depender do dicionário de alto risco.",
    },
)

C(
    id="Matriz_LaudoDeImagem_Pdf",
    title="LAUDO DE EXAME DE IMAGEM",
    subtitle="Tomografia computadorizada — pronto-socorro",
    meta=[("Paciente", "Carlos Eduardo Mendes"), ("Idade", "52 anos"),
          ("Documento", "DOC-IMG-2026-0004"), ("Data", "15/10/2026"),
          ("Origem", "Pronto-Socorro")],
    sections=[
        ("Exame realizado", "Tomografia computadorizada de tórax com contraste intravenoso."),
        ("Indicação", "Suspeita de embolia pulmonar aguda; dispneia súbita e dor torácica."),
        ("Achados", "Falha de enchimento em artéria pulmonar principal direita, compatível com tromboembolismo pulmonar agudo. Derrame pleural laminar à direita. Parênquima pulmonar sem consolidações."),
        ("Conclusão", "Tromboembolismo pulmonar agudo (TEP). Correlação clínica urgente."),
    ],
    doctor=("Dra. Renata Silveira", "CRM 145892-SP"),
    expected={
        "tipo_documento": "LAUDO_EXAME_IMAGEM", "especialidade": ["Radiologia", "Pneumologia"],
        "prioridade": "URGENTE", "status": "EM_REVISAO", "destinos": ["FILA_URGENCIA_MEDICA"],
        "revisao": True, "notificacao": True,
        "dados": {"paciente": {"nome": "Carlos Eduardo Mendes", "idade": 52},
                  "medico": {"nome": "Dra. Renata Silveira", "crm": {"numero": "145892", "uf": "SP"}},
                  "diagnostico": "Tromboembolismo pulmonar agudo", "cid": None,
                  "medicamentos": [], "exames": ["Tomografia de tórax com contraste"], "urgencia": "SIM"},
        "assercoes": ["Caso oficial do brief reproduzido em PDF",
                      "Achado crítico detectado e prioridade URGENTE",
                      "Destino FILA_URGENCIA_MEDICA com alerta",
                      "CID ausente permanece null e não exige revisão por si só"],
        "obs": "Espelha o exemplo do Projeto_oracle.pdf. A spec v1.0 prevê EM_REVISAO para urgência, embora o exemplo do brief mostre 'processado'.",
    },
)

C(
    id="Matriz_LaudoLaboratorial_Pdf",
    title="LAUDO DE EXAME LABORATORIAL",
    subtitle="Hemograma completo — rotina",
    meta=[("Paciente", "Ana Paula Ribeiro"), ("Idade", "41 anos"),
          ("Documento", "DOC-LAB-2026-0005"), ("Data", "16/10/2026"),
          ("Origem", "Laboratório Central")],
    sections=[
        ("Hipótese diagnóstica", "Anemia ferropriva — CID-10 D50.9."),
        ("Material", "Sangue periférico, coleta em 16/10/2026 às 07h40."),
        ("Resultados", "Hemoglobina: 10,2 g/dL (referência 12,0–16,0)\nHematócrito: 32,1% (referência 36–46)\nHemácias: 3,8 milhões/mm³ (referência 4,0–5,4)\nLeucócitos: 7.200/mm³ (referência 4.000–11.000)\nPlaquetas: 245.000/mm³ (referência 150.000–450.000)\nVCM: 84 fL (referência 80–100)\nHCM: 27 pg (referência 27–33)"),
        ("Conclusão", "Anemia microcítica leve. Correlacionar com ferritina e quadro clínico."),
    ],
    doctor=("Dr. Marcos Vinícius Tavares", "CRM 176543-MG"),
    expected={
        "tipo_documento": "LAUDO_EXAME_LABORATORIAL", "especialidade": ["Hematologia", "Clínica Médica"],
        "prioridade": "ROTINA", "status": "PROCESSADO", "destinos": ["PRONTUARIO_ELETRONICO"],
        "revisao": False, "notificacao": False,
        "dados": {"paciente": {"nome": "Ana Paula Ribeiro", "idade": 41},
                  "medico": {"nome": "Dr. Marcos Vinícius Tavares", "crm": {"numero": "176543", "uf": "MG"}},
                  "diagnostico": "Anemia ferropriva", "cid": "D50.9",
                  "medicamentos": [], "exames": ["Hemograma completo"], "urgencia": "NAO"},
        "assercoes": ["Laudo laboratorial de rotina", "Valores numéricos preservados",
                      "Destino PRONTUARIO_ELETRONICO", "Sem revisão"],
    },
)

C(
    id="Matriz_Guia_Pdf",
    title="GUIA DE SOLICITAÇÃO DE PROCEDIMENTO",
    subtitle="Ressonância magnética — eletiva",
    meta=[("Paciente", "Luciana Martins Costa"), ("Idade", "46 anos"),
          ("Documento", "DOC-GUI-2026-0006"), ("Data", "16/10/2026"),
          ("Origem", "Ambulatório de Ortopedia")],
    sections=[
        ("Diagnóstico / CID", "Lombalgia crônica com radiculopatia — CID-10 M54.5."),
        ("Procedimento solicitado", "Ressonância magnética de coluna lombar, sem contraste."),
        ("Justificativa clínica", "Dor lombar há 6 meses, refratária a tratamento conservador por 12 semanas, com irradiação para membro inferior direito."),
        ("Autorização", "Solicitação eletiva. Aguardando autorização da operadora."),
    ],
    doctor=("Dr. André Luiz Barbosa", "CRM 165432-SP"),
    expected={
        "tipo_documento": "GUIA_PROCEDIMENTO", "especialidade": ["Ortopedia"],
        "prioridade": "ROTINA", "status": "PROCESSADO", "destinos": ["AUDITORIA_AUTORIZACOES"],
        "revisao": False, "notificacao": False,
        "dados": {"paciente": {"nome": "Luciana Martins Costa", "idade": 46},
                  "medico": {"nome": "Dr. André Luiz Barbosa", "crm": {"numero": "165432", "uf": "SP"}},
                  "diagnostico": "Lombalgia crônica com radiculopatia", "cid": "M54.5",
                  "medicamentos": [], "exames": ["Ressonância magnética de coluna lombar"], "urgencia": "NAO"},
        "assercoes": ["Guia de procedimento eletivo", "Destino AUDITORIA_AUTORIZACOES",
                      "CID e justificativa extraídos", "Sem revisão"],
    },
)

C(
    id="Matriz_RelatorioDeAlta_Pdf",
    title="RELATÓRIO DE ALTA HOSPITALAR",
    subtitle="Internação clínica — alta por melhora",
    meta=[("Paciente", "Beatriz Gonçalves Pereira"), ("Idade", "63 anos"),
          ("Documento", "DOC-ALT-2026-0007"), ("Data", "17/10/2026"),
          ("Origem", "Enfermaria 3B")],
    sections=[
        ("Período de internação", "Admissão em 10/10/2026, alta em 17/10/2026."),
        ("Motivo da internação", "Pneumonia adquirida na comunidade com necessidade de antibioticoterapia intravenosa."),
        ("Resumo da internação", "Paciente internada com tosse produtiva, febre e dispneia. Tomografia de tórax com consolidação em lobo inferior direito. Tratada com ceftriaxona e azitromicina por 7 dias, com melhora clínica e laboratorial."),
        ("Diagnóstico principal", "Pneumonia adquirida na comunidade — CID-10 J18.9."),
        ("Medicações de alta", "Amoxicilina + clavulanato 875/125 mg — 1 comprimido por via oral a cada 12 horas, por 5 dias."),
        ("Orientações", "Retorno em 7 dias no ambulatório de clínica médica. Sinais de alarme: febre persistente, dispneia ou piora do estado geral."),
    ],
    doctor=("Dra. Helena Prado", "CRM 187432-SP"),
    expected={
        "tipo_documento": "RELATORIO_ALTA_INTERNACAO", "especialidade": ["Clínica Médica", "Pneumologia"],
        "prioridade": "ROTINA", "status": "PROCESSADO", "destinos": ["PRONTUARIO_ELETRONICO"],
        "revisao": False, "notificacao": False,
        "dados": {"paciente": {"nome": "Beatriz Gonçalves Pereira", "idade": 63},
                  "medico": {"nome": "Dra. Helena Prado", "crm": {"numero": "187432", "uf": "SP"}},
                  "diagnostico": "Pneumonia adquirida na comunidade", "cid": "J18.9",
                  "medicamentos": ["Amoxicilina + clavulanato 875/125 mg"],
                  "exames": ["Tomografia de tórax"], "urgencia": "NAO"},
        "assercoes": ["Relatório de alta multimodal", "Diagnóstico, CID e medicação de alta extraídos",
                      "Destino PRONTUARIO_ELETRONICO", "Sem revisão"],
    },
)

C(
    id="Matriz_Atestado_Texto",
    title="ATESTADO MÉDICO",
    subtitle="Atestado de comparecimento",
    meta=[("Paciente", "Thiago Almeida Santos"), ("Idade", "29 anos"),
          ("Documento", "DOC-ATE-2026-0008"), ("Data", "17/10/2026"),
          ("Origem", "Ambulatório de Clínica Médica")],
    sections=[
        ("Finalidade", "Atestado de comparecimento para fins administrativos."),
        ("Texto do atestado", "Atesto, para os devidos fins, que o paciente compareceu a consulta médica nesta unidade no dia 17/10/2026, no período das 09h00 às 10h15."),
        ("Diagnóstico / justificativa", "Infecção viral de vias aéreas superiores — CID-10 J06.9."),
        ("Período", "Comparecimento no dia 17/10/2026."),
    ],
    doctor=("Dr. Paulo Mendes Rocha", "CRM 203114-RJ"),
    expected={
        "tipo_documento": "ATESTADO_MEDICO", "especialidade": ["Clínica Médica"],
        "prioridade": "ROTINA", "status": "PROCESSADO", "destinos": ["PRONTUARIO_ELETRONICO"],
        "revisao": False, "notificacao": False,
        "dados": {"paciente": {"nome": "Thiago Almeida Santos", "idade": 29},
                  "medico": {"nome": "Dr. Paulo Mendes Rocha", "crm": {"numero": "203114", "uf": "RJ"}},
                  "diagnostico": "Infecção viral de vias aéreas superiores", "cid": "J06.9",
                  "medicamentos": [], "exames": [], "urgencia": "NAO"},
        "assercoes": ["Ausência de medicamentos e exames NÃO força revisão",
                      "Diagnóstico presente mantém o fluxo automático",
                      "Destino PRONTUARIO_ELETRONICO"],
    },
)

C(
    id="Matriz_NaoIdentificado_Imagem",
    title="REGISTRO CLÍNICO",
    subtitle="Documento recebido com baixa qualidade",
    meta=[("Paciente", "—"), ("Idade", "—"), ("Documento", "DOC-NID-2026-0009"),
          ("Data", "18/10/2026"), ("Origem", "Digitalização externa")],
    sections=[
        ("Conteúdo", "Imagem recebida com desfoque intenso e baixo contraste. Não há trechos legíveis suficientes para identificar o tipo do documento ou os dados clínicos."),
        ("Qualidade da captura", "Resolução insuficiente, inclinação acentuada e ruído elevado. Recomenda-se revisão humana e eventual reenvio do original."),
    ],
    doctor=("—", "CRM —"),
    expected={
        "tipo_documento": "NAO_IDENTIFICADO", "especialidade": [], "prioridade": "NAO_IDENTIFICADA",
        "status": "EM_REVISAO", "destinos": ["FILA_REVISAO_HUMANA"],
        "revisao": True, "notificacao": False,
        "dados": {"paciente": {"nome": None, "idade": None}, "medico": {"nome": None, "crm": None},
                  "diagnostico": None, "cid": None, "medicamentos": [], "exames": [], "urgencia": "INDETERMINADO",
                  "campos_ausentes": ["paciente.nome", "paciente.idade", "medico.nome", "medico.crm", "diagnostico_principal"]},
        "assercoes": ["Documento ilegível não pode ser classificado",
                      "Nenhum dado clínico é inventado",
                      "Destino FILA_REVISAO_HUMANA e status EM_REVISAO"],
        "obs": "O PDF e o JPG são intencionalmente degradados (somente imagem, sem camada de texto). O TXT simula uma transcrição OCR truncada.",
    },
)

C(
    id="Matriz_Outro_Texto",
    title="COMUNICAÇÃO ADMINISTRATIVA",
    subtitle="Mensagem do setor de agendamento",
    meta=[("Destinatário", "Paciente cadastrado"), ("Documento", "DOC-OUT-2026-0010"),
          ("Data", "18/10/2026"), ("Origem", "Central de Agendamento")],
    sections=[
        ("Assunto", "Reagendamento de consulta."),
        ("Mensagem", "Prezado(a) paciente, informamos que a consulta prevista para 14/10/2026 foi remarcada para 21/10/2026, às 09h30, na recepção do 2º andar. Em caso de dúvida, procure a central de atendimento."),
        ("Setor responsável", "Setor Administrativo — Central de Agendamento."),
    ],
    doctor=("—", "—"),
    expected={
        "tipo_documento": "OUTRO", "especialidade": [], "prioridade": "NAO_IDENTIFICADA",
        "status": "EM_REVISAO", "destinos": ["FILA_REVISAO_HUMANA"],
        "revisao": True, "notificacao": False,
        "dados": {"paciente": {"nome": None, "idade": None}, "medico": {"nome": None, "crm": None},
                  "diagnostico": None, "cid": None, "medicamentos": [], "exames": [], "urgencia": "INDETERMINADO",
                  "campos_ausentes": ["paciente.nome", "paciente.idade", "medico.nome", "medico.crm", "diagnostico_principal"]},
        "assercoes": ["Documento fora da taxonomia clínica", "Classificação OUTRO",
                      "Destino FILA_REVISAO_HUMANA (destino não mapeado)"],
    },
)

C(
    id="Ausencia_Paciente_Nome",
    title="RECEITUÁRIO MÉDICO",
    subtitle="Prescrição ambulatorial — campo obrigatório ausente",
    meta=[("Paciente", "________________________"), ("Idade", "44 anos"),
          ("Documento", "DOC-REC-2026-0011"), ("Data", "18/10/2026"),
          ("Origem", "Ambulatório de Clínica Médica")],
    sections=[
        ("Hipótese diagnóstica", "Faringoamigdalite bacteriana — CID-10 J03.9."),
        ("Prescrição", "Amoxicilina 500 mg — 1 cápsula por via oral a cada 8 horas, por 7 dias."),
        ("Orientações", "Concluir o tratamento mesmo com melhora dos sintomas. Retorno se febre persistir por mais de 72 horas."),
    ],
    doctor=("Dra. Camila Ferreira Lopes", "CRM 198765-SP"),
    expected={
        "tipo_documento": "RECEITUARIO_MEDICO", "especialidade": ["Clínica Médica"],
        "prioridade": "ROTINA", "status": "EM_REVISAO", "destinos": ["FILA_REVISAO_HUMANA"],
        "revisao": True, "notificacao": False,
        "dados": {"paciente": {"nome": None, "idade": 44},
                  "medico": {"nome": "Dra. Camila Ferreira Lopes", "crm": {"numero": "198765", "uf": "SP"}},
                  "diagnostico": "Faringoamigdalite bacteriana", "cid": "J03.9",
                  "medicamentos": ["Amoxicilina 500 mg"], "exames": [], "urgencia": "NAO",
                  "campos_ausentes": ["paciente.nome"]},
        "assercoes": ["Ausência de nome do paciente força revisão",
                      "Demais campos permanecem preenchidos e não são inventados",
                      "Status EM_REVISAO e destino FILA_REVISAO_HUMANA"],
    },
)

C(
    id="Borda_Score_084",
    title="RECEITUÁRIO MÉDICO",
    subtitle="Prescrição ambulatorial — teste de limiar de confiança",
    meta=[("Paciente", "Fernanda Lima Rocha"), ("Idade", "37 anos"),
          ("Documento", "DOC-REC-2026-0012"), ("Data", "18/10/2026"),
          ("Origem", "Ambulatório de Clínica Médica")],
    sections=[
        ("Hipótese diagnóstica", "Lombalgia aguda — CID-10 M54.5."),
        ("Prescrição", "Ibuprofeno 400 mg — 1 comprimido por via oral a cada 8 horas, por 5 dias, após as refeições."),
        ("Orientações", "Evitar esforço físico por 5 dias. Retorno se dor intensa ou déficit neurológico."),
    ],
    doctor=("Dr. André Luiz Barbosa", "CRM 165432-SP"),
    expected={
        "tipo_documento": "RECEITUARIO_MEDICO", "especialidade": ["Clínica Médica"],
        "prioridade": "ROTINA", "status": "EM_REVISAO", "destinos": ["FILA_REVISAO_HUMANA"],
        "revisao": True, "notificacao": False,
        "dados": {"paciente": {"nome": "Fernanda Lima Rocha", "idade": 37},
                  "medico": {"nome": "Dr. André Luiz Barbosa", "crm": {"numero": "165432", "uf": "SP"}},
                  "diagnostico": "Lombalgia aguda", "cid": "M54.5",
                  "medicamentos": ["Ibuprofeno 400 mg"], "exames": [], "urgencia": "NAO"},
        "score_forcado": {"score_classificacao": 0.92, "score_extracao": 0.84, "score_combinado": 0.84, "limiar": 0.85},
        "assercoes": ["Score combinado 0,84 < 0,85 força revisão",
                      "A classificação e a extração em si estão corretas",
                      "Exige FIXTURE_MODE para forçar os scores"],
        "obs": "O documento é uma receita de rotina legível. O desfecho de revisão vem exclusivamente do score forçado, não do conteúdo.",
    },
)


def expected_json(case, base="demo"):
    e = case["expected"]
    return {
        "fixture_id": case["id"],
        "documento_ficticio": True,
        "formatos_disponiveis": ["TXT", "PDF", "JPG"],
        "renditions": {
            "txt": f"{base}/{case['id']}/{case['id']}.txt",
            "pdf": f"{base}/{case['id']}/{case['id']}.pdf",
            "jpg": f"{base}/{case['id']}/{case['id']}.jpg",
        },
        "classificacao_esperada": {
            "tipo_documento": e["tipo_documento"],
            "especialidade": e["especialidade"],
            "nivel_prioridade": e["prioridade"],
            "score_classificacao": ">= 0.85" if not e.get("score_forcado") else e["score_forcado"]["score_classificacao"],
        },
        "dados_esperados": e["dados"],
        "decisao_esperada": {
            "status": e["status"],
            "destinos": e["destinos"],
            "requer_auditoria_humana": e["revisao"],
            "notificacao": e["notificacao"],
        },
        "assercoes": e["assercoes"],
        "observacoes": e.get("obs", ""),
        **({"score_forcado": e["score_forcado"]} if e.get("score_forcado") else {}),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for case in CASES:
        d = os.path.join(OUT, case["id"])
        os.makedirs(d, exist_ok=True)
        txt = os.path.join(d, f"{case['id']}.txt")
        pdf = os.path.join(d, f"{case['id']}.pdf")
        jpg = os.path.join(d, f"{case['id']}.jpg")

        write_txt(case, txt)
        if case["id"] == "Matriz_NaoIdentificado_Imagem":
            make_degraded(case, pdf, jpg)
        else:
            draw_pdf(case, pdf)
            render_jpg(pdf, jpg)

        with open(os.path.join(d, "expected.json"), "w", encoding="utf-8") as f:
            json.dump(expected_json(case), f, ensure_ascii=False, indent=2)
        total += 4
        print(f"ok {case['id']}: txt + pdf + jpg + expected.json")
    print(f"\n{len(CASES)} casos, {total} arquivos em {OUT}")


if __name__ == "__main__":
    main()
