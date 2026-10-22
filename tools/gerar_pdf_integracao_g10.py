#!/usr/bin/env python3
"""Gera o PDF de alinhamento de contrato endereçado à equipe do G10.

Uso:
    python3 tools/gerar_pdf_integracao_g10.py
"""
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs/integracao/Alinhamento_de_Contrato_MediFlow_G10.pdf")
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
VERDE = colors.HexColor("#047857")
VERDE_BG = colors.HexColor("#ECFDF5")
AMBER = colors.HexColor("#B45309")
AMBER_BG = colors.HexColor("#FFFBEB")
AZUL_BG = colors.HexColor("#EFF6FF")
AZUL = colors.HexColor("#1D4ED8")

PAG = {"n": 0}
Y = {"y": 0}


# ------------------------------------------------------------------ utilidades
def wrap(text, font, size, maxw):
    out, cur = [], ""
    for word in text.split(" "):
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


def fit(text, font, size, maxw):
    if pdfmetrics.stringWidth(text, font, size) <= maxw:
        return text
    out = text
    while out and pdfmetrics.stringWidth(out + "…", font, size) > maxw:
        out = out[:-1]
    return out.rstrip() + "…"


def nova_pagina(titulo="", subtitulo=None, capa=False):
    if PAG["n"]:
        c.showPage()
    PAG["n"] += 1
    if capa:
        Y["y"] = H - 60
        return
    c.setFillColor(INK)
    c.setFont("DJB", 8)
    c.drawString(M, H - 34, "MEDIFLOW · ALINHAMENTO DE CONTRATO ENTRE REPOSITÓRIOS")
    c.setFillColor(MUTED)
    c.setFont("DJ", 7)
    c.drawRightString(W - M, H - 34, "Hackathon ONE G10 · 22/10/2026")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(M, H - 42, W - M, H - 42)

    c.setFillColor(INK)
    c.setFont("DJB", 15)
    c.drawString(M, H - 66, titulo)
    y = H - 66
    if subtitulo:
        y -= 12
        c.setFillColor(MUTED)
        c.setFont("DJ", 8.4)
        for ln in wrap(subtitulo, "DJ", 8.4, CW):
            c.drawString(M, y, ln)
            y -= 10.5
    Y["y"] = y - 12

    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(M, 38, W - M, 38)
    c.setFont("DJ", 6.6)
    c.setFillColor(MUTED)
    c.drawString(M, 28, "Documento de alinhamento entre repositórios · MediFlow · Hackathon ONE G10")
    c.drawRightString(W - M, 28, f"página {PAG['n']}")


def precisa(altura):
    if Y["y"] - altura < 52:
        nova_pagina("Continuação")


def h2(texto, cor=INK):
    precisa(26)
    Y["y"] -= 16
    c.setFillColor(cor)
    c.setFont("DJB", 10.2)
    c.drawString(M, Y["y"], texto)
    Y["y"] -= 9


def p(texto, tamanho=8.4, cor=INK, lead=11.4, recuo=0, negrito=False):
    font = "DJB" if negrito else "DJ"
    for ln in wrap(texto, font, tamanho, CW - recuo):
        precisa(lead + 2)
        c.setFillColor(cor)
        c.setFont(font, tamanho)
        c.drawString(M + recuo, Y["y"], ln)
        Y["y"] -= lead
    Y["y"] -= 3


def tabela(cols, linhas, tamanho=6.9, row_h=11.6, wrap_cols=(), fundos=None):
    """cols = [(largura, rótulo)]; retorna desenhar a tabela a partir de Y."""
    total = sum(w for w, _ in cols)
    alturas = []
    for row in linhas:
        n = 1
        for ci in wrap_cols:
            n = max(n, len(wrap(row[ci], "DJ", tamanho, cols[ci][0] - 5)))
        alturas.append(row_h * n)
    bloco = row_h + sum(alturas)
    precisa(bloco + 6)

    c.setFillColor(INK)
    c.rect(M, Y["y"] - row_h, total, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("DJB", tamanho)
    cx = M
    for wd, rot in cols:
        c.drawString(cx + 3, Y["y"] - row_h + 3.6, rot)
        cx += wd
    y = Y["y"] - row_h
    for i, row in enumerate(linhas):
        h_linha = alturas[i]
        if fundos and fundos[i]:
            c.setFillColor(fundos[i])
        elif i % 2 == 1:
            c.setFillColor(SOFT)
        else:
            c.setFillColor(colors.white)
        c.rect(M, y - h_linha, total, h_linha, fill=1, stroke=0)
        cx = M
        for j, (wd, _) in enumerate(cols):
            c.setFillColor(INK)
            c.setFont("DJ", tamanho)
            if j in wrap_cols:
                for li, ln in enumerate(wrap(row[j], "DJ", tamanho, wd - 6)):
                    c.drawString(cx + 3, y - row_h + 3.6 - li * row_h, ln)
            else:
                c.drawString(cx + 3, y - row_h + 3.6, fit(row[j], "DJ", tamanho, wd - 6))
            cx += wd
        y -= h_linha
    c.setStrokeColor(LINE)
    c.setLineWidth(0.4)
    c.rect(M, y, total, row_h + sum(alturas), fill=0, stroke=1)
    Y["y"] = y - 12


def caixa(titulo, linhas, bg=SOFT, borda=LINE, cor_titulo=INK, altura=None, tamanho=7.4):
    larg = len(linhas)
    h = altura or (30 + 10.2 * larg)
    precisa(h + 8)
    c.setFillColor(bg)
    c.setStrokeColor(borda)
    c.setLineWidth(0.6)
    c.roundRect(M, Y["y"] - h, CW, h, 4, fill=1, stroke=1)
    c.setFillColor(cor_titulo)
    c.setFont("DJB", 7.8)
    c.drawString(M + 9, Y["y"] - 15, titulo)
    yy = Y["y"] - 28
    for ln in linhas:
        c.setFillColor(INK)
        c.setFont("DJ", tamanho)
        for l in wrap(ln, "DJ", tamanho, CW - 22):
            c.drawString(M + 9, yy, l)
            yy -= 9.6
        yy -= 1.4
    Y["y"] = Y["y"] - h - 12


def marcadores(itens, tamanho=8.2, lead=11.2, simbolo="•", cor=RED):
    for it in itens:
        precisa(lead + 4)
        c.setFillColor(cor)
        c.setFont("DJB", tamanho)
        c.drawString(M, Y["y"], simbolo)
        c.setFillColor(INK)
        c.setFont("DJ", tamanho)
        for ln in wrap(it, "DJ", tamanho, CW - 14):
            precisa(lead)
            c.drawString(M + 12, Y["y"], ln)
            Y["y"] -= lead
        Y["y"] -= 3


def checklist(itens, tamanho=8.0, lead=11.0):
    precisa(lead * len(itens))
    for it in itens:
        c.setStrokeColor(MUTED)
        c.setLineWidth(0.7)
        c.rect(M + 1, Y["y"] - 2.5, 7, 7, fill=0, stroke=1)
        c.setFillColor(INK)
        c.setFont("DJ", tamanho)
        linhas = wrap(it, "DJ", tamanho, CW - 16)
        for k, ln in enumerate(linhas):
            precisa(lead)
            c.drawString(M + 14, Y["y"], ln)
            Y["y"] -= lead
        Y["y"] -= 2


def codigo(linhas, tamanho=6.5, lead=8.4):
    h = 14 + lead * len(linhas)
    precisa(h + 6)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.roundRect(M, Y["y"] - h, CW, h, 3, fill=1, stroke=0)
    yy = Y["y"] - 14
    for ln in linhas:
        c.setFillColor(colors.HexColor("#E2E8F0"))
        c.setFont("DJM", tamanho)
        c.drawString(M + 8, yy, ln[:118])
        yy -= lead
    Y["y"] = Y["y"] - h - 12


# -------------------------------------------------------------------- conteúdo
def desenhar():
    # ---------------------------------------------------------------- capa
    nova_pagina(capa=True)
    c.setFillColor(RED)
    c.rect(0, H - 8, W, 8, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.setFont("DJB", 8)
    c.drawString(M, H - 60, "MEDIFLOW · HACKATHON ONE G10 · BRASIL")
    Y["y"] = H - 96
    c.setFillColor(INK)
    c.setFont("DJB", 23)
    c.drawString(M, Y["y"], "Alinhamento de contrato")
    Y["y"] -= 26
    c.setFont("DJB", 15)
    c.drawString(M, Y["y"], "entre os dois repositórios do MediFlow")
    Y["y"] -= 22
    c.setFillColor(MUTED)
    c.setFont("DJ", 9.4)
    for ln in wrap("Leitura do repositório g10-brasil-equipe-15_mediflow (branch develop, 24 arquivos) "
                   "contra os documentos confirmados do projeto: Especificação Funcional v1.0 atualizada, "
                   "Análise de Requisitos v1.1 e o contrato de dados executável.", "DJ", 9.4, CW):
        c.drawString(M, Y["y"], ln)
        Y["y"] -= 12
    Y["y"] -= 8

    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(M, Y["y"], W - M, Y["y"])
    Y["y"] -= 20
    c.setFont("DJB", 7.4)
    c.setFillColor(MUTED)
    c.drawString(M, Y["y"], "PARA")
    c.drawString(M + 120, Y["y"], "DE")
    c.drawString(M + 260, Y["y"], "DATA")
    Y["y"] -= 13
    c.setFont("DJ", 9)
    c.setFillColor(INK)
    c.drawString(M, Y["y"], "Izabela — G10 Brasil · Equipe 15")
    c.drawString(M + 120, Y["y"], "Time de documentação e testes")
    c.drawString(M + 260, Y["y"], "22/10/2026")
    Y["y"] -= 26

    # números
    caixa("RESUMO EM TRÊS NÚMEROS", [
        "10 regras de negócio já estão corretas no seu grafo — nenhuma precisa ser reescrita.",
        "7 ajustes de contrato (nomes de enums, campos e blocos que a resposta não expõe).",
        "5 itens que ainda faltam implementar — dois deles são a sua parte dos buckets.",
    ], bg=AZUL_BG, borda=colors.HexColor("#BFDBFE"), cor_titulo=AZUL, tamanho=8.4)

    caixa("COMO LER ESTE DOCUMENTO", [
        "Cada ajuste traz a referência no documento que originou a exigência (§5.2, RN-03, RF-21…). "
        "Se a referência não bastar, o arquivo está nos links da última página.",
        "Nada aqui é opinião: tudo é consequência direta dos documentos que o time já aprovou.",
        "A ordem é a ordem sugerida de execução — as três primeiras destravam o resto.",
    ], bg=SOFT, tamanho=8.0)

    # ------------------------------------------------- 1. o que está correto
    nova_pagina("1. O que já está correto",
                "Seu grafo acertou todas as decisões que tomamos em 21/10 — inclusive uma em que a "
                "especificação original divergia do brief.")
    p("Antes de qualquer coisa: o print que circulou no grupo mostrava só a cauda dos testes. Vendo a lista completa — "
      "25 funções de teste, sem contar as parametrizadas — a implementação está bem mais avançada do que parecia, "
      "e em três pontos, melhor que a nossa.",
      tamanho=8.4)

    tabela([(196, "Regra"), (92, "Referência"), (223, "Onde está no seu código")],
           [["Urgência isolada NÃO gera revisão", "brief (R1)", "test_urgencia_isolada_nao_exige_revisao"],
            ["Conflito ALTA e MÉDIA revisam; BAIXA só registra", "decisão A1",
             "test_penalidade_por_conflito (0,70 / 0,80 / 0,90)"],
            ["Fórmula do score de extração", "decisão A3", "idêntica: 1 − 0,2 − 0,1 − 0,3/0,2/0,1"],
            ["Prioridade não identificada gera revisão", "decisão A4", "test_prioridade_ambigua_exige_revisao"],
            ["Urgência INDETERMINADO conta como incerto", "decisão A5", "test_urgencia_indeterminada_exige_revisao"],
            ["Score combinado = min(classificação, extração)", "RF-18", "avalia_qualidade()"],
            ["5 campos obrigatórios; CID isolado NÃO revisa", "RF-21",
             "test_campo_obrigatorio_ausente + test_cid_ausente_isoladamente_nao_exige_revisao"],
            ["Urgência + ambiguidade = dois destinos", "§8.2", "test_urgencia_com_ambiguidade_tem_dois_destinos"],
            ["Justificativa e regra registradas em toda decisão", "RN-05", "test_decisao_tem_justificativa_e_regra"],
            ["Grafo não confirma persistência", "RF-30", "etapa: DECISAO_CALCULADA"]],
           wrap_cols=(2,))

    caixa("O PONTO MAIS DIFÍCIL, E VOCÊ ACERTOU", [
        "A §8.2 da Especificação Funcional v1.0 original manda revisar obrigatoriamente todo caso urgente. "
        "O brief do hackathon mostra o contrário: urgência isolada é PROCESSADO, com alerta e um destino só.",
        "Você seguiu o brief, não a spec antiga. É exatamente a decisão que registramos como R1 — e foi a que "
        "mais gente errou.",
    ], bg=VERDE_BG, borda=colors.HexColor("#A7F3D0"), cor_titulo=VERDE, tamanho=8.0)

    h2("Três coisas que você faz e nós não fazemos")
    p("Anotado para não se perder na convergência — vamos trazer para o nosso lado:", tamanho=8.2)
    marcadores([
        "idade = 0 é tratada como presente, não como ausente (o nosso verificador ainda não testa isso).",
        "Conflitos idênticos são deduplicados antes de somar a penalidade.",
        "O limiar rejeita NaN e infinito (allow_inf_nan=False).",
        'O marcador etapa: "DECISAO_CALCULADA" — o grafo declara que não confirma persistência, que é a '
        "leitura mais limpa da RF-30 que vimos até agora.",
    ], cor=VERDE, simbolo="+")

    # ------------------------------------------------- 2. ajuste de nomes
    nova_pagina("2. Ajuste 1 — os nomes dos enums",
                "É a mudança mais barata e a de maior efeito: enquanto ela não acontecer, nenhuma resposta "
                "da sua API casa com os 79 casos aprovados.")
    caixa("POR QUE ISSO TRAVA A INTEGRAÇÃO", [
        "Os 79 fixtures do catálogo trazem o resultado esperado de cada caso já no formato do contrato. "
        "Como os valores dos enums são diferentes, a comparação falha em 100% dos casos — mesmo com a "
        "lógica correta.",
        "Você mesma está com duas grafias: o README usa FILA_EMERGENCIA_MEDICA e o código usa "
        "Fila_Emergencia_Medica. Vale aproveitar para uniformizar nos dois lugares.",
    ], bg=TINT, borda=colors.HexColor("#F3D4D1"), cor_titulo=RED, tamanho=8.0)

    h2("Prioridade e destinos")
    tabela([(232, "Hoje no seu código"), (206, "Valor canônico"), (73, "Referência")],
           [["\"Rotina\"", "ROTINA", "§5.2"],
            ["\"Urgente\"", "URGENTE", "§5.2"],
            ["\"Ambiguidade/Revisão Humana\"", "NAO_IDENTIFICADA", "§5.2, A4"],
            ["\"Fila_Emergencia_Medica\"", "FILA_URGENCIA_MEDICA", "§5.4"],
            ["\"Auditoria_Autorizacoes\"", "AUDITORIA_AUTORIZACOES", "§5.4"],
            ["\"Farmacia_Hospitalar\"", "FARMACIA_HOSPITALAR", "§5.4"],
            ["\"Prontuario_Eletronico\"", "PRONTUARIO_ELETRONICO", "§5.4"],
            ["\"Fila_Revisao_Humana\"", "FILA_REVISAO_HUMANA", "§5.4"]])

    caixa("SOBRE \"AMBIGUIDADE / REVISÃO HUMANA\"", [
        "Ambiguidade não é prioridade — é cenário (§8.2). A prioridade tem três valores e o terceiro é "
        "NAO_IDENTIFICADA, que é justamente o gatilho da decisão A4.",
        "O comportamento que você implementou está certo (prioridade indeterminada entra como campo incerto "
        "e gera revisão). Só o nome precisa mudar.",
    ], bg=AMBER_BG, borda=colors.HexColor("#FDE68A"), cor_titulo=AMBER, tamanho=8.0)

    h2("Status")
    tabela([(232, "Hoje"), (206, "Valor canônico"), (73, "Referência")],
           [["status: str, default \"processado\"", "enum com 6 valores", "§5.3"],
            ["\"pendente_auditoria\"", "EM_REVISAO", "§5.3"],
            ["\"erro\"", "ERRO_PROCESSAMENTO ou ERRO_PERSISTENCIA", "§5.3, §12"]])
    p("Os seis valores: RECEBIDO, PROCESSANDO, PROCESSADO, EM_REVISAO, ERRO_PROCESSAMENTO, ERRO_PERSISTENCIA. "
      "RECEBIDO e PROCESSANDO são obrigatórios no fluxo assíncrono (202 + polling, RF-01).", tamanho=8.0, cor=MUTED)

    h2("Tipo de documento")
    p("O tipo continua sendo str livre na entrada — e pode continuar. A sua função normalizar_tipo() aceita as "
      "variações de rótulo, o que é ótimo. A sugestão é só serializar o código estável na resposta: "
      "RECEITUARIO_MEDICO, LAUDO_EXAME_LABORATORIAL, LAUDO_EXAME_IMAGEM, GUIA_PROCEDIMENTO, "
      "RELATORIO_ALTA_INTERNACAO, ATESTADO_MEDICO, OUTRO, NAO_IDENTIFICADO.", tamanho=8.2)

    # ------------------------------------------------- 3. campos e blocos
    nova_pagina("3. Ajustes 2 e 3 — campos e blocos da resposta",
                "Nada aqui muda cálculo: em dois dos três casos o dado já é calculado no seu modelo interno "
                "e só não chega à resposta da API.")
    h2("Campos com formato diferente")
    tabela([(196, "Hoje"), (238, "Formato do contrato"), (77, "Referência")],
           [["medicamentos: List[str]", "medicamentos: [{nome, dosagem?, frequencia?}]", "§9.2, RF-08"],
            ["exame_realizado: str", "exames: List[str]", "§9.2"],
            ["urgencia fora de dados_extraidos", "dados_extraidos.urgencia: SIM | NAO | INDETERMINADO", "A5"],
            ["especialidade: str", "especialidade: List[str]", "§9.2"],
            ["status_backup default \"pendente\"", "default \"sucesso\", caminho_objeto opcional", "RF-30"]],
           wrap_cols=(0, 1))

    h2("Blocos que a resposta não expõe")
    tabela([(150, "Bloco"), (150, "Onde já existe"), (211, "O que muda")],
           [["destinos (lista)", "DecisaoWorkflow interno",
             "A API devolve só destino_principal. A §8.2 pede os dois destinos, sem reduzir a decisão a um."],
            ["qualidade", "QualidadeWorkflow interno",
             "Scores, campos ausentes, incertos, conflitos e limiar não saem na resposta — sem isso não dá "
             "para auditar nem provar RF-17/RF-18."],
            ["erro {codigo, mensagem}", "inexistente",
             "Necessário quando o status for de erro (§12)."]],
           wrap_cols=(0, 1, 2))

    caixa("ALERTA: DE BOOLEANO PARA EVENTO REGISTRADO", [
        "Hoje o grafo devolve alerta_simulado: true. A RF-07 e a §8.2 pedem um evento de alerta registrado, "
        "não um booleano — e você já tem o modelo Notificacao {canal, mensagem} pronto no schema. É só o grafo "
        "preenchê-lo em vez de devolver True.",
    ], bg=AMBER_BG, borda=colors.HexColor("#FDE68A"), cor_titulo=AMBER, tamanho=8.0)

    # ------------------------------------------------- 4. o que falta
    nova_pagina("4. O que ainda falta implementar",
                "Cinco itens. Os dois primeiros são os de maior peso — e o segundo é exatamente a sua parte "
                "dos buckets.")
    caixa("1 · ALTO RISCO SEM TEXTO DE URGÊNCIA VAI PARA A FILA URGENTE (RN-03)", [
        "Hoje a urgência só é detectada por urgencia = \"SIM\" ou prioridade URGENTE. A RN-03 exige que achado "
        "crítico ou medicamento de alto risco encaminhe para a fila urgente e gere alerta, mesmo sem nenhuma "
        "palavra de urgência no texto.",
        "É a única regra de roteamento obrigatória que não existe nem no código nem nos testes. O nosso caso "
        "equivalente é Conflito_AltoRisco: receita de varfarina 10 mg, sem texto de urgência, que espera "
        "FILA_URGENCIA_MEDICA e status PROCESSADO.",
        "Depende do dicionário clínico (decisão A2) — que é a lista fechada que o time ainda vai fechar.",
    ], bg=TINT, borda=colors.HexColor("#F3D4D1"), cor_titulo=RED, tamanho=8.0)

    caixa("2 · CAMINHO DO BUCKET POR ESTADO (RF-29, RF-30, §6 PASSO 7)", [
        "Seu README lista /recebidos, /processados e /auditoria_humana. Falta o subcaminho de urgentes, que "
        "entrou no §13 quando aplicamos o bloco de consistência.",
        "Sugestão de derivação a partir da decisão: rotina → processados/ … urgência → processados/urgentes/ … "
        "revisão → auditoria_humana/.",
        "A regra do §6 é explícita: documento roteado a revisão tem de ser armazenado no estado/caminho de "
        "auditoria. E a RF-30 proíbe URL pública ou credencial na resposta.",
    ], bg=TINT, borda=colors.HexColor("#F3D4D1"), cor_titulo=RED, tamanho=8.0)

    h2("Os outros três")
    marcadores([
        "ERRO_PROCESSAMENTO e ERRO_PERSISTENCIA: hoje só existe o marcador de etapa. Falta produzir o status "
        "de erro e o envelope {codigo, mensagem} da §12.",
        "Ingestão (RF-03 + A6): src/ingestion/ está vazio. Nada valida os limites de 10 MB, 20 páginas, "
        "extensões e MIME. O limite é inclusivo: 10 MB e 20 páginas passam; 10,5 MB e 21 não.",
        "documento_id: o grafo exigir está correto internamente — a API é que precisa gerar quando ausente "
        "(RN-07). Vale registrar esse limite no README para ninguém se perder.",
    ])

    caixa("DOIS PONTOS DE RISCO NA APRESENTAÇÃO", [
        "O README promete reduzir a triagem \"de 15 minutos para menos de 5 segundos\". As metas numéricas "
        "ficaram fora do MVP: o critério de aceite são os casos aprovados, com latência medida por etapa e "
        "sem meta (decisão A7). Prometer 5 segundos expõe o time a uma cobrança que o critério não define.",
        "O README cita FILA_EMERGENCIA_MEDICA; o nome da §5.4 é FILA_URGENCIA_MEDICA.",
    ], bg=AMBER_BG, borda=colors.HexColor("#FDE68A"), cor_titulo=AMBER, tamanho=8.0)

    # ------------------------------------------------- 5. cenários
    nova_pagina("5. Seus três cenários, no nosso contrato",
                "Traduzimos os data/samples para o contrato MediFlow v1.0. Os três validam e são ponto fixo "
                "das regras — se o contrato divergir, o script quebra.")
    tabela([(120, "Cenário"), (150, "Documento"), (86, "Status"), (155, "Destino")],
           [["1 · Rotina", "Hemograma — Maria F. Lima", "PROCESSADO", "PRONTUARIO_ELETRONICO"],
            ["2 · Urgência", "TC de tórax — TEP agudo", "PROCESSADO", "FILA_URGENCIA_MEDICA + alerta"],
            ["3 · Ambíguo", "Receita de morfina ilegível", "EM_REVISAO", "FILA_REVISAO_HUMANA"]])

    h2("Dois achados na tradução")
    marcadores([
        "O score de extração de 0,65 do cenário 3 é ilustrativo. Pela fórmula aprovada (A3) ele vale 0,00: "
        "são 4 campos obrigatórios ausentes (−0,8) e 2 incertos (−0,2). O desfecho não muda, mas o número "
        "precisa ser calculado, não estimado — vale ajustar antes da banca perguntar.",
        "Se morfina entrar no dicionário de alto risco (A2), o cenário 3 passa a ter DOIS destinos, com alerta: "
        "FILA_URGENCIA_MEDICA + FILA_REVISAO_HUMANA. Deixamos isso marcado como pendência, não resolvido, "
        "porque depende da lista clínica do time.",
    ])

    h2("Exemplo: o payload do cenário 2 (urgência)")
    p("É o mesmo conteúdo do nosso caso Matriz_LaudoDeImagem_Pdf, que já está no kit de demonstração:",
      tamanho=8.0, cor=MUTED)
    codigo([
        '{',
        '  "status": "PROCESSADO",',
        '  "documento_id": "DOC-CLIN-2026-8942",',
        '  "classificacao": {"tipo_documento": "LAUDO_EXAME_IMAGEM",',
        '                    "especialidade": ["Radiologia", "Pneumologia"],',
        '                    "nivel_prioridade": "URGENTE", "score_classificacao": 0.98},',
        '  "dados_extraidos": {"paciente": {"nome": "Carlos Eduardo Mendes", "idade": 52},',
        '                      "medico": {"nome": "Dra. Renata Silveira",',
        '                                 "crm": {"numero": "145892", "uf": "SP"}},',
        '                      "diagnostico": "Tromboembolismo pulmonar agudo",',
        '                      "cid": "I26.9", "urgencia": "SIM"},',
        '  "qualidade": {"score_extracao": 0.98, "score_combinado": 0.98,',
        '                "limiar_aplicado": 0.85, "campos_ausentes": [], "conflitos": []},',
        '  "decisao_roteamento": {"destinos": ["FILA_URGENCIA_MEDICA"],',
        '                         "destino_principal": "FILA_URGENCIA_MEDICA",',
        '                         "requer_auditoria_humana": false,',
        '                         "notificacao": {"gerada": true, "status": "REGISTRADA"}}',
        '}',
    ])

    # ------------------------------------------------- 6. checklist
    nova_pagina("6. Checklist de alinhamento",
                "Ordem sugerida de execução. As três primeiras destravam o resto e são as mais baratas.")
    h2("Contrato (mecânico, sem mudar regra)")
    checklist([
        "Trocar os valores de NivelPrioridade e DestinoRoteamento pelos canônicos (§5.2, §5.4).",
        "Renomear AMBIGUO para NAO_IDENTIFICADA mantendo o comportamento atual.",
        "Expor destinos (lista) em DecisaoRoteamento, com destino_principal = destinos[0].",
        "Criar o enum StatusTriagem com os 6 valores e o bloco erro {codigo, mensagem}.",
        "Expor o bloco qualidade na resposta da API.",
        "Trocar alerta_simulado pelo objeto Notificacao que já existe no seu schema.",
        "medicamentos como objetos, exames como lista, urgencia dentro de dados_extraidos.",
    ])
    h2("Regras")
    checklist([
        "Alto risco sem texto de urgência → FILA_URGENCIA_MEDICA + alerta (RN-03).",
        "Derivar o caminho do bucket por estado, incluindo processados/urgentes/ (RF-29, §6 passo 7).",
        "Produzir status e envelope de erro nas duas situações de falha (§12).",
        "Validar entrada na ingestão: 10 MB, 20 páginas, extensões e MIME (RF-03, A6).",
    ])
    h2("Apresentação")
    checklist([
        "Tirar a meta de 5 segundos do README (decisão A7).",
        "Uniformizar FILA_URGENCIA_MEDICA no README inteiro.",
        "Registrar no README que a API gera o documento_id quando ausente (RN-07).",
    ])

    h2("Como validar do seu lado")
    codigo([
        '# no nosso repositório, depois de clonar',
        'python3 tools/validar_cenarios_g10.py     # 3 cenários válidos e estáveis',
        'python3 tests/testar_contrato.py          # 79/79 no contrato',
        'python3 tools/verificar_consistencia.py   # 0 erro; avisos só de arquivos grandes não versionados',
    ])

    caixa("O QUE LEVAR PARA O SEU REPOSITÓRIO", [
        "app/models.py — o contrato executável. Ele recusa payload incoerente e já tem A1, A3, A4, A5 e R1 "
        "implementados. Você não precisa reescrever o grafo: pode usar o nosso modelo só como validador da "
        "resposta, se preferir.",
        "Os 79 fixtures — cada um com o resultado esperado já no formato do contrato. Servem de corpus de "
        "teste de integração.",
        "MAPEAMENTO_DE_CONTRATO.md e ISSUES_PARA_O_G10.md — as tabelas deste PDF em markdown, com as 10 issues "
        "prontas para abrir no seu repositório.",
    ], bg=VERDE_BG, borda=colors.HexColor("#A7F3D0"), cor_titulo=VERDE, tamanho=8.0)

    p("Links: o pacote completo (documentação, os 79 fixtures, os PDFs de origem e os geradores) e os dois "
      "PDFs atualizados com as decisões A1–A9 estão no dist/ do branch arena/b33f82cc-hackatoon-oracle do "
      "repositório berger33/hackatoon_oracle.", tamanho=8.0, cor=MUTED)
    p("Obrigado pelo nível do código — a parte difícil (as regras) você resolveu. O que falta é encaixe de "
      "nomes e exposição de dados que você já calcula.", tamanho=8.6, negrito=True)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    c = canvas.Canvas(OUT, pagesize=A4, invariant=1)
    c.setTitle("MediFlow — Alinhamento de contrato entre repositórios")
    c.setAuthor("MediFlow · Hackathon ONE G10")
    c.setSubject("Leitura do repositório g10-brasil-equipe-15_mediflow contra os documentos confirmados")
    desenhar()
    c.save()
    print("ok:", OUT)
