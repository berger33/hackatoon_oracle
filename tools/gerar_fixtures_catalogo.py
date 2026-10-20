#!/usr/bin/env python3
"""Gera os 55 fixtures restantes do catalogo do MediFlow (blocos Ausencia a Validacao).

Saida: tests/fixtures/catalogo/{ID}/{ID}.txt|pdf|jpg|expected.json

Casos especiais:
  - PDF escaneado (somente imagem, sem camada de texto)
  - PDF multipagina, protegido por senha e corrompido
  - foto rotacionada, cortada, com sombra/baixo contraste e desfocada
  - manuscrito simulado e carimbo sobreposto
  - negativos tecnicos (docx, zip, 0 KB, 25 MB, MIME falso, JSON invalido)
"""
import json
import os
import random
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gerar_fixtures_demo import (  # noqa: E402
    A4, CONTENT_W, FICTION, H, HOSPITAL, HOSPITAL_SUB, INK, LINE, MARGIN, MUTED, RED,
    SOFT, W, canvas, fitz, pdfmetrics, wrap,
)
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tests/fixtures/catalogo")
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DejaVuMono", f"{FONT_DIR}/DejaVuSansMono.ttf"))

CASES = []


def c(**kw):
    kw.setdefault("flags", {})
    kw.setdefault("pages", 1)
    CASES.append(kw)


def sec(title, body, mono=False):
    return (title, body, mono)


# ============================================================ BLOCO M (14)
c(id="Matriz_LaudoLaboratorial_Imagem", titulo="LAUDO DE EXAME LABORATORIAL",
  sub="Perfil lipídico e glicemia — rotina",
  meta=[("Paciente", "Sônia Regina Duarte"), ("Idade", "55 anos"), ("Documento", "DOC-LAB-2026-0013"),
        ("Data", "16/10/2026"), ("Origem", "Laboratório Central")],
  secs=[sec("Hipótese diagnóstica", "Dislipidemia mista — CID-10 E78.2."),
        sec("Material", "Soro, coleta em 16/10/2026 às 07h20, jejum de 12 horas."),
        sec("Resultados", "Colesterol total: 248 mg/dL (desejável < 190)\nLDL-colesterol: 168 mg/dL (desejável < 130)\nHDL-colesterol: 38 mg/dL (desejável > 40)\nTriglicerídeos: 210 mg/dL (desejável < 150)\nGlicemia de jejum: 98 mg/dL (referência 70–99)"),
        sec("Conclusão", "Dislipidemia mista. Orientada dieta e retorno ambulatorial.")],
  doc=("Dr. Marcos Vinícius Tavares", "CRM 176543-MG"),
  exp=dict(tipo="LAUDO_EXAME_LABORATORIAL", esp=["Hematologia", "Clínica Médica"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Sônia Regina Duarte", idade=55),
                      medico=dict(nome="Dr. Marcos Vinícius Tavares", crm=dict(numero="176543", uf="MG")),
                      diagnostico="Dislipidemia mista", cid="E78.2", medicamentos=[],
                      exames=["Perfil lipídico", "Glicemia de jejum"], urgencia="NAO"),
           ass=["Foto de laudo laboratorial aceita", "Cinco analitos extraídos com unidade e referência",
                "Destino PRONTUARIO_ELETRONICO sem revisão"]))

c(id="Matriz_LaudoLaboratorial_Texto", titulo="LAUDO DE EXAME LABORATORIAL",
  sub="Glicemia e hemoglobina glicada — rotina, sem CID",
  meta=[("Paciente", "Elias Moreira Pires"), ("Idade", "62 anos"), ("Documento", "DOC-LAB-2026-0014"),
        ("Data", "16/10/2026"), ("Origem", "Ambulatório de Endocrinologia")],
  secs=[sec("Material", "Sangue venoso, coleta em 16/10/2026."),
        sec("Resultados", "Glicemia de jejum: 132 mg/dL (referência 70–99)\nHemoglobina glicada: 7,4% (referência < 5,7%)"),
        sec("Conclusão", "Controle glicêmico inadequado. Ajustar terapia conforme avaliação clínica.")],
  doc=("Dra. Helena Prado", "CRM 187432-SP"),
  exp=dict(tipo="LAUDO_EXAME_LABORATORIAL", esp=["Endocrinologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Elias Moreira Pires", idade=62),
                      medico=dict(nome="Dra. Helena Prado", crm=dict(numero="187432", uf="SP")),
                      diagnostico=None, cid=None, medicamentos=[],
                      exames=["Glicemia de jejum", "Hemoglobina glicada"], urgencia="NAO"),
           ass=["Texto de laudo laboratorial aceito", "CID ausente permanece null",
                "Ausência de CID isolada NÃO exige revisão (RF-21)"]))

c(id="Matriz_LaudoDeImagem_Imagem", titulo="LAUDO DE EXAME DE IMAGEM",
  sub="Radiografia de tórax — pronto-socorro",
  meta=[("Paciente", "Antônio Carlos Vieira"), ("Idade", "71 anos"), ("Documento", "DOC-IMG-2026-0015"),
        ("Data", "17/10/2026"), ("Origem", "Pronto-Socorro")],
  secs=[sec("Exame realizado", "Radiografia de tórax, incidência PA e perfil."),
        sec("Achados", "Hipertransparência difusa no hemitórax direito com ausência de trama vascular periférica e desvio contralateral do mediastino."),
        sec("Conclusão", "Pneumotórax espontâneo à direita, com sinais de hipertensão. Avaliação médica imediata.")],
  doc=("Dra. Renata Silveira", "CRM 145892-SP"),
  exp=dict(tipo="LAUDO_EXAME_IMAGEM", esp=["Radiologia", "Pneumologia"], prio="URGENTE",
           status="EM_REVISAO", dest=["FILA_URGENCIA_MEDICA"], rev=True, notif=True,
           dados=dict(paciente=dict(nome="Antônio Carlos Vieira", idade=71),
                      medico=dict(nome="Dra. Renata Silveira", crm=dict(numero="145892", uf="SP")),
                      diagnostico="Pneumotórax espontâneo à direita", cid=None, medicamentos=[],
                      exames=["Radiografia de tórax"], urgencia="SIM"),
           ass=["Foto de laudo com achado crítico", "Prioridade URGENTE detectada",
                "Destino FILA_URGENCIA_MEDICA com alerta simulado"]))

c(id="Matriz_LaudoDeImagem_Texto", titulo="LAUDO DE EXAME DE IMAGEM",
  sub="Ultrassonografia de abdome total — rotina",
  meta=[("Paciente", "Patrícia Nogueira Alves"), ("Idade", "38 anos"), ("Documento", "DOC-IMG-2026-0016"),
        ("Data", "17/10/2026"), ("Origem", "Ambulatório de Gastroenterologia")],
  secs=[sec("Exame realizado", "Ultrassonografia de abdome total."),
        sec("Achados", "Fígado de dimensões normais, ecotextura homogênea. Vesícula biliar sem cálculos. Vias biliares de calibre normal. Rins de dimensões e ecogenicidade preservadas. Ausência de líquido livre."),
        sec("Conclusão", "Exame ultrassonográfico dentro da normalidade.")],
  doc=("Dr. André Luiz Barbosa", "CRM 165432-SP"),
  exp=dict(tipo="LAUDO_EXAME_IMAGEM", esp=["Radiologia", "Gastroenterologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Patrícia Nogueira Alves", idade=38),
                      medico=dict(nome="Dr. André Luiz Barbosa", crm=dict(numero="165432", uf="SP")),
                      diagnostico="Exame dentro da normalidade", cid=None, medicamentos=[],
                      exames=["Ultrassonografia de abdome total"], urgencia="NAO"),
           ass=["Texto de laudo de imagem de rotina", "Sem sinais de urgência",
                "Destino PRONTUARIO_ELETRONICO"]))

c(id="Matriz_Guia_Imagem", titulo="GUIA DE SOLICITAÇÃO DE PROCEDIMENTO",
  sub="Endoscopia digestiva alta — urgência",
  meta=[("Paciente", "Márcia Helena dos Santos"), ("Idade", "49 anos"), ("Documento", "DOC-GUI-2026-0017"),
        ("Data", "17/10/2026"), ("Origem", "Pronto-Socorro")],
  secs=[sec("Diagnóstico / CID", "Hemorragia digestiva alta — CID-10 K92.2."),
        sec("Procedimento solicitado", "Endoscopia digestiva alta diagnóstica e terapêutica."),
        sec("Justificativa clínica", "Paciente com hematêmese e melena, instabilidade hemodinâmica. Procedimento com caráter de urgência nas próximas 6 horas."),
        sec("Autorização", "Solicitação URGENTE. Autorização em análise pela auditoria.")],
  doc=("Dr. Paulo Mendes Rocha", "CRM 203114-RJ"),
  exp=dict(tipo="GUIA_PROCEDIMENTO", esp=["Gastroenterologia"], prio="URGENTE",
           status="EM_REVISAO", dest=["FILA_URGENCIA_MEDICA"], rev=True, notif=True,
           dados=dict(paciente=dict(nome="Márcia Helena dos Santos", idade=49),
                      medico=dict(nome="Dr. Paulo Mendes Rocha", crm=dict(numero="203114", uf="RJ")),
                      diagnostico="Hemorragia digestiva alta", cid="K92.2", medicamentos=[],
                      exames=["Endoscopia digestiva alta"], urgencia="SIM"),
           ass=["Foto de guia com pedido de urgência", "Sinal crítico detectado no texto",
                "Destino FILA_URGENCIA_MEDICA com alerta"]))

c(id="Matriz_Guia_Texto", titulo="GUIA DE SOLICITAÇÃO DE PROCEDIMENTO",
  sub="Colonoscopia — eletiva",
  meta=[("Paciente", "Roberto Yukio Tanaka"), ("Idade", "60 anos"), ("Documento", "DOC-GUI-2026-0018"),
        ("Data", "17/10/2026"), ("Origem", "Ambulatório de Gastroenterologia")],
  secs=[sec("Diagnóstico / CID", "Rastreamento de neoplasia colorretal — CID-10 Z12.1."),
        sec("Procedimento solicitado", "Colonoscopia diagnóstica com sedação."),
        sec("Justificativa clínica", "História familiar de câncer colorretal em parente de primeiro grau. Paciente assintomático, exame de rastreamento eletivo."),
        sec("Autorização", "Solicitação eletiva, sem caráter de urgência.")],
  doc=("Dra. Camila Ferreira Lopes", "CRM 198765-SP"),
  exp=dict(tipo="GUIA_PROCEDIMENTO", esp=["Gastroenterologia"], prio="ROTINA",
           status="PROCESSADO", dest=["AUDITORIA_AUTORIZACOES"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Roberto Yukio Tanaka", idade=60),
                      medico=dict(nome="Dra. Camila Ferreira Lopes", crm=dict(numero="198765", uf="SP")),
                      diagnostico="Rastreamento de neoplasia colorretal", cid="Z12.1", medicamentos=[],
                      exames=["Colonoscopia"], urgencia="NAO"),
           ass=["Texto de guia eletiva", "Destino AUDITORIA_AUTORIZACOES",
                "Nenhum sinal de urgência"]))

c(id="Matriz_RelatorioDeAlta_Imagem", titulo="RELATÓRIO DE ALTA HOSPITALAR",
  sub="Internação por insuficiência cardíaca — alta por melhora",
  meta=[("Paciente", "José Ricardo Almeida"), ("Idade", "68 anos"), ("Documento", "DOC-ALT-2026-0019"),
        ("Data", "18/10/2026"), ("Origem", "Enfermaria 2A")],
  secs=[sec("Período de internação", "Admissão em 11/10/2026, alta em 18/10/2026."),
        sec("Diagnóstico principal", "Insuficiência cardíaca congestiva descompensada — CID-10 I50.0."),
        sec("Resumo", "Paciente internado com dispneia progressiva, edema de membros inferiores e ortopneia. Tratado com diurético endovenoso e otimização de terapia oral, com melhora funcional."),
        sec("Medicações de alta", "Furosemida 40 mg — 1 comprimido por via oral pela manhã, uso contínuo.\nCarvedilol 6,25 mg — 1 comprimido por via oral a cada 12 horas, uso contínuo."),
        sec("Orientações", "Restrição hídrica de 1,5 L/dia, controle de peso diário e retorno em 7 dias.")],
  doc=("Dr. Paulo Mendes Rocha", "CRM 203114-RJ"),
  exp=dict(tipo="RELATORIO_ALTA_INTERNACAO", esp=["Cardiologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="José Ricardo Almeida", idade=68),
                      medico=dict(nome="Dr. Paulo Mendes Rocha", crm=dict(numero="203114", uf="RJ")),
                      diagnostico="Insuficiência cardíaca congestiva descompensada", cid="I50.0",
                      medicamentos=["Furosemida 40 mg", "Carvedilol 6,25 mg"],
                      exames=[], urgencia="NAO"),
           ass=["Foto de relatório de alta", "Dois medicamentos extraídos com dose e frequência",
                "Destino PRONTUARIO_ELETRONICO"]))

c(id="Matriz_RelatorioDeAlta_Texto", titulo="RELATÓRIO DE ALTA HOSPITALAR",
  sub="Resumo de internação truncado — sem diagnóstico",
  meta=[("Paciente", "Vanessa Cristina Lopes"), ("Idade", "33 anos"), ("Documento", "DOC-ALT-2026-0020"),
        ("Data", "18/10/2026"), ("Origem", "Enfermaria 4C")],
  secs=[sec("Período de internação", "Admissão em 15/10/2026, alta em 18/10/2026."),
        sec("Resumo", "Paciente internada para investigação de quadro álgico abdominal. Realizados exames laboratoriais e de imagem durante a internação."),
        sec("Evolução", "Houve melhora parcial dos sintomas. A equipe assistente optou pela alta hospitalar com orientação de retorno ambulatorial."),
        sec("Pendências", "Laudo anatomopatológico pendente. Retorno em 15 dias.")],
  doc=("Dr. André Luiz Barbosa", "CRM 165432-SP"),
  exp=dict(tipo="RELATORIO_ALTA_INTERNACAO", esp=["Cirurgia Geral"], prio="ROTINA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome="Vanessa Cristina Lopes", idade=33),
                      medico=dict(nome="Dr. André Luiz Barbosa", crm=dict(numero="165432", uf="SP")),
                      diagnostico=None, cid=None, medicamentos=[], exames=[], urgencia="NAO",
                      campos_ausentes=["diagnostico_principal"]),
           ass=["Documento truncado sem diagnóstico/hipótese",
                "Ausência de diagnóstico força revisão (RF-21)",
                "Nenhum diagnóstico é inventado"]))

c(id="Matriz_Atestado_Pdf", titulo="ATESTADO MÉDICO",
  sub="Afastamento de 3 dias — CID explícito",
  meta=[("Paciente", "Bruno Henrique Castro"), ("Idade", "26 anos"), ("Documento", "DOC-ATE-2026-0021"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Ortopedia")],
  secs=[sec("Finalidade", "Atestado de afastamento laboral."),
        sec("Texto do atestado", "Atesto que o paciente necessita de afastamento de suas atividades laborais por 3 (três) dias, a contar de 18/10/2026."),
        sec("Diagnóstico / CID", "Lombalgia aguda com radiculopatia — CID-10 M54.5.")],
  doc=("Dr. André Luiz Barbosa", "CRM 165432-SP"),
  exp=dict(tipo="ATESTADO_MEDICO", esp=["Ortopedia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Bruno Henrique Castro", idade=26),
                      medico=dict(nome="Dr. André Luiz Barbosa", crm=dict(numero="165432", uf="SP")),
                      diagnostico="Lombalgia aguda com radiculopatia", cid="M54.5",
                      medicamentos=[], exames=[], urgencia="NAO"),
           ass=["Atestado em PDF digital", "CID explícito extraído",
                "Destino PRONTUARIO_ELETRONICO"]))

c(id="Matriz_Atestado_Imagem", titulo="ATESTADO MÉDICO",
  sub="Atestado com carimbo e assinatura",
  meta=[("Paciente", "Larissa Fontes Amaral"), ("Idade", "31 anos"), ("Documento", "DOC-ATE-2026-0022"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Clínica Médica")],
  secs=[sec("Finalidade", "Atestado de comparecimento e afastamento de 1 dia."),
        sec("Texto do atestado", "Atesto que a paciente compareceu a consulta médica nesta data e necessita de afastamento de 1 (um) dia de suas atividades habituais."),
        sec("Diagnóstico / CID", "Infecção viral de vias aéreas superiores — CID-10 J06.9.")],
  doc=("Dra. Helena Prado", "CRM 187432-SP"),
  exp=dict(tipo="ATESTADO_MEDICO", esp=["Clínica Médica"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Larissa Fontes Amaral", idade=31),
                      medico=dict(nome="Dra. Helena Prado", crm=dict(numero="187432", uf="SP")),
                      diagnostico="Infecção viral de vias aéreas superiores", cid="J06.9",
                      medicamentos=[], exames=[], urgencia="NAO"),
           ass=["Foto de atestado com carimbo", "Carimbo não interfere na extração",
                "Destino PRONTUARIO_ELETRONICO"]))

c(id="Matriz_Outro_Pdf", titulo="DECLARAÇÃO DE COMPARECIMENTO",
  sub="Declaração emitida a acompanhante — fora da taxonomia",
  meta=[("Paciente", "—"), ("Idade", "—"), ("Documento", "DOC-OUT-2026-0023"),
        ("Data", "18/10/2026"), ("Origem", "Recepção Ambulatorial")],
  secs=[sec("Declaração", "Declaramos, para os devidos fins, que a acompanhante Sra. Denise Prado Figueiredo compareceu a esta unidade no dia 18/10/2026, acompanhando paciente em consulta ambulatorial."),
        sec("Finalidade", "Comprovação de comparecimento para fins trabalhistas do acompanhante."),
        sec("Observação", "Documento administrativo, sem informações clínicas do paciente.")],
  doc=("—", "—"),
  exp=dict(tipo="OUTRO", esp=[], prio="NAO_IDENTIFICADA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome=None, idade=None), medico=dict(nome=None, crm=None),
                      diagnostico=None, cid=None, medicamentos=[], exames=[], urgencia="INDETERMINADO",
                      campos_ausentes=["paciente.nome", "paciente.idade", "medico.nome", "medico.crm",
                                       "diagnostico_principal"]),
           ass=["Declaração administrativa fora da taxonomia clínica", "Classificação OUTRO",
                "Destino não mapeado vai para FILA_REVISAO_HUMANA"]))

c(id="Matriz_Outro_Imagem", titulo="RELATÓRIO DE ENFERMAGEM",
  sub="Registro de sinais vitais — fora da taxonomia",
  meta=[("Paciente", "—"), ("Idade", "—"), ("Documento", "DOC-OUT-2026-0024"),
        ("Data", "18/10/2026"), ("Origem", "Enfermaria 3B")],
  secs=[sec("Registro", "Controle de sinais vitais de 4 horas: temperatura 36,7 °C; frequência cardíaca 78 bpm; pressão arterial 122/78 mmHg; saturação de O2 97% em ar ambiente."),
        sec("Cuidados", "Paciente orientado, deambulando, aceitando dieta. Punção venosa periférica em membro superior esquerdo sem sinais flogísticos."),
        sec("Responsável", "Equipe de Enfermagem — Enfermeira responsável pela unidade.")],
  doc=("—", "—"),
  exp=dict(tipo="OUTRO", esp=[], prio="NAO_IDENTIFICADA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome=None, idade=None), medico=dict(nome=None, crm=None),
                      diagnostico=None, cid=None, medicamentos=[], exames=[], urgencia="INDETERMINADO",
                      campos_ausentes=["paciente.nome", "paciente.idade", "medico.nome", "medico.crm",
                                       "diagnostico_principal"]),
           ass=["Registro de enfermagem não é documento médico do MVP", "Classificação OUTRO",
                "Revisão humana obrigatória"]))

c(id="Matriz_NaoIdentificado_Pdf", titulo="REGISTRO CLÍNICO",
  sub="Documento escaneado ilegível",
  meta=[("Paciente", "—"), ("Idade", "—"), ("Documento", "DOC-NID-2026-0025"),
        ("Data", "18/10/2026"), ("Origem", "Digitalização externa")],
  secs=[sec("Conteúdo", "PDF recebido a partir de digitalização de baixa resolução, com manchas e trechos cortados. Não há texto legível suficiente para identificar o tipo documental ou os dados clínicos."),
        sec("Qualidade", "Resolução abaixo de 100 dpi, inclinação acentuada e ruído de digitalização. Recomenda-se reenvio do original.")],
  doc=("—", "CRM —"),
  flags=dict(degrade=True),
  exp=dict(tipo="NAO_IDENTIFICADO", esp=[], prio="NAO_IDENTIFICADA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome=None, idade=None), medico=dict(nome=None, crm=None),
                      diagnostico=None, cid=None, medicamentos=[], exames=[], urgencia="INDETERMINADO",
                      campos_ausentes=["paciente.nome", "paciente.idade", "medico.nome", "medico.crm",
                                       "diagnostico_principal"]),
           ass=["PDF escaneado ilegível não é classificado", "Classificação NAO_IDENTIFICADO",
                "Nenhum dado inventado e revisão obrigatória"],
           obs="PDF somente imagem, com desfoque e ruído. Sem camada de texto."))

c(id="Matriz_NaoIdentificado_Texto", titulo="TEXTO SEM CONTEÚDO CLÍNICO",
  sub="Lista de compras enviada por engano",
  meta=[("Paciente", "—"), ("Idade", "—"), ("Documento", "DOC-NID-2026-0026"),
        ("Data", "18/10/2026"), ("Origem", "Upload manual")],
  secs=[sec("Conteúdo", "Lista de compras do mercado: arroz, feijão, óleo, café, açúcar, leite, pão, ovos, frutas da estação e produtos de limpeza."),
        sec("Observação", "Não há qualquer elemento clínico, identificação de paciente ou profissional de saúde no conteúdo.")],
  doc=("—", "—"),
  exp=dict(tipo="NAO_IDENTIFICADO", esp=[], prio="NAO_IDENTIFICADA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome=None, idade=None), medico=dict(nome=None, crm=None),
                      diagnostico=None, cid=None, medicamentos=[], exames=[], urgencia="INDETERMINADO",
                      campos_ausentes=["paciente.nome", "paciente.idade", "medico.nome", "medico.crm",
                                       "diagnostico_principal"]),
           ass=["Texto sem conteúdo clínico", "Classificação NAO_IDENTIFICADO",
                "Revisão humana obrigatória"]))

# ============================================================ BLOCO A (7)
c(id="Ausencia_Paciente_Idade", titulo="RECEITUÁRIO MÉDICO",
  sub="Prescrição sem a idade do paciente",
  meta=[("Paciente", "Otávio Sampaio Reis"), ("Idade", "não informada"), ("Documento", "DOC-REC-2026-0027"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Clínica Médica")],
  secs=[sec("Hipótese diagnóstica", "Cistite aguda não complicada — CID-10 N30.0."),
        sec("Prescrição", "Nitrofurantoína 100 mg — 1 cápsula por via oral a cada 6 horas, por 7 dias."),
        sec("Orientações", "Aumentar ingestão hídrica e retornar se febre ou dor lombar.")],
  doc=("Dra. Camila Ferreira Lopes", "CRM 198765-SP"),
  exp=dict(tipo="RECEITUARIO_MEDICO", esp=["Clínica Médica"], prio="ROTINA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome="Otávio Sampaio Reis", idade=None),
                      medico=dict(nome="Dra. Camila Ferreira Lopes", crm=dict(numero="198765", uf="SP")),
                      diagnostico="Cistite aguda não complicada", cid="N30.0",
                      medicamentos=["Nitrofurantoína 100 mg"], exames=[], urgencia="NAO",
                      campos_ausentes=["paciente.idade"]),
           ass=["Idade ausente força revisão (RF-21)", "Nome do paciente preservado",
                "Idade não é inferida"]))

c(id="Ausencia_Medico_Nome", titulo="LAUDO DE EXAME LABORATORIAL",
  sub="Laudo com CRM preenchido e nome do médico ausente",
  meta=[("Paciente", "Simone Aparecida Rocha"), ("Idade", "47 anos"), ("Documento", "DOC-LAB-2026-0028"),
        ("Data", "18/10/2026"), ("Origem", "Laboratório Central")],
  secs=[sec("Hipótese diagnóstica", "Hipotireoidismo primário — CID-10 E03.9."),
        sec("Resultados", "TSH: 8,9 mUI/L (referência 0,4–4,0)\nT4 livre: 0,72 ng/dL (referência 0,8–1,8)"),
        sec("Conclusão", "Perfil compatível com hipotireoidismo primário. Correlacionar clinicamente.")],
  doc=("", "CRM 154321-PR"),
  exp=dict(tipo="LAUDO_EXAME_LABORATORIAL", esp=["Endocrinologia"], prio="ROTINA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome="Simone Aparecida Rocha", idade=47),
                      medico=dict(nome=None, crm=dict(numero="154321", uf="PR")),
                      diagnostico="Hipotireoidismo primário", cid="E03.9", medicamentos=[],
                      exames=["TSH", "T4 livre"], urgencia="NAO", campos_ausentes=["medico.nome"]),
           ass=["Nome do médico ausente força revisão", "CRM preservado e normalizado em número/UF",
                "Nome não é inventado"]))

c(id="Ausencia_Medico_Crm", titulo="LAUDO DE EXAME LABORATORIAL",
  sub="Laudo com nome do médico e CRM ausente",
  meta=[("Paciente", "Gustavo Henrique Barros"), ("Idade", "52 anos"), ("Documento", "DOC-LAB-2026-0029"),
        ("Data", "18/10/2026"), ("Origem", "Laboratório Central")],
  secs=[sec("Hipótese diagnóstica", "Diabetes mellitus tipo 2 — CID-10 E11.9."),
        sec("Resultados", "Glicemia de jejum: 148 mg/dL (referência 70–99)\nHemoglobina glicada: 8,1% (referência < 5,7%)\nCreatinina: 1,1 mg/dL (referência 0,7–1,3)"),
        sec("Conclusão", "Controle glicêmico inadequado. Ajustar terapia.")],
  doc=("Dr. Marcos Vinícius Tavares", "CRM não informado"),
  exp=dict(tipo="LAUDO_EXAME_LABORATORIAL", esp=["Endocrinologia"], prio="ROTINA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome="Gustavo Henrique Barros", idade=52),
                      medico=dict(nome="Dr. Marcos Vinícius Tavares", crm=None),
                      diagnostico="Diabetes mellitus tipo 2", cid="E11.9", medicamentos=[],
                      exames=["Glicemia de jejum", "Hemoglobina glicada", "Creatinina"],
                      urgencia="NAO", campos_ausentes=["medico.crm"]),
           ass=["CRM ausente força revisão", "Nome do médico preservado",
                "CRM não é inventado"]))

c(id="Ausencia_Diagnostico", titulo="GUIA DE SOLICITAÇÃO DE PROCEDIMENTO",
  sub="Guia sem diagnóstico ou hipótese diagnóstica",
  meta=[("Paciente", "Heloísa Martins Braga"), ("Idade", "44 anos"), ("Documento", "DOC-GUI-2026-0030"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Dermatologia")],
  secs=[sec("Procedimento solicitado", "Exérese de lesão cutânea em dorso, com estudo anatomopatológico."),
        sec("Justificativa clínica", "Lesão pigmentada de crescimento progressivo nos últimos 6 meses, com bordas irregulares."),
        sec("Autorização", "Solicitação eletiva.")],
  doc=("Dra. Helena Prado", "CRM 187432-SP"),
  exp=dict(tipo="GUIA_PROCEDIMENTO", esp=["Dermatologia"], prio="ROTINA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome="Heloísa Martins Braga", idade=44),
                      medico=dict(nome="Dra. Helena Prado", crm=dict(numero="187432", uf="SP")),
                      diagnostico=None, cid=None, medicamentos=[],
                      exames=["Exérese de lesão cutânea"], urgencia="NAO",
                      campos_ausentes=["diagnostico_principal"]),
           ass=["Diagnóstico/hipótese ausente força revisão",
                "Justificativa clínica não substitui o campo diagnóstico",
                "Nenhum CID é sugerido"]))

c(id="Ausencia_SomenteCid", titulo="LAUDO DE EXAME DE IMAGEM",
  sub="Laudo com diagnóstico explícito e sem CID",
  meta=[("Paciente", "Celso Ribeiro Nunes"), ("Idade", "57 anos"), ("Documento", "DOC-IMG-2026-0031"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Ortopedia")],
  secs=[sec("Exame realizado", "Radiografia de joelho direito, incidências AP e perfil."),
        sec("Achados", "Redução do espaço articular medial, osteófitos marginais e esclerose subcondral."),
        sec("Conclusão", "Gonartrose à direita, grau moderado.")],
  doc=("Dr. André Luiz Barbosa", "CRM 165432-SP"),
  exp=dict(tipo="LAUDO_EXAME_IMAGEM", esp=["Ortopedia", "Radiologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Celso Ribeiro Nunes", idade=57),
                      medico=dict(nome="Dr. André Luiz Barbosa", crm=dict(numero="165432", uf="SP")),
                      diagnostico="Gonartrose à direita", cid=None, medicamentos=[],
                      exames=["Radiografia de joelho direito"], urgencia="NAO",
                      campos_ausentes=["cid_extraido"]),
           ass=["Diagnóstico presente mantém o fluxo automático",
                "CID ausente fica null e NÃO força revisão (RF-21)",
                "Status PROCESSADO"]))

c(id="Ausencia_SomenteMedicamentos", titulo="LAUDO DE EXAME LABORATORIAL",
  sub="Laudo sem medicamentos — lista vazia",
  meta=[("Paciente", "Débora Cristina Melo"), ("Idade", "29 anos"), ("Documento", "DOC-LAB-2026-0032"),
        ("Data", "18/10/2026"), ("Origem", "Laboratório Central")],
  secs=[sec("Hipótese diagnóstica", "Anemia ferropriva — CID-10 D50.9."),
        sec("Resultados", "Hemoglobina: 9,8 g/dL (referência 12,0–16,0)\nFerritina: 8 ng/mL (referência 15–150)\nSaturação de transferrina: 12% (referência 20–50%)"),
        sec("Conclusão", "Anemia ferropriva. Reposição de ferro conforme avaliação clínica.")],
  doc=("Dra. Camila Ferreira Lopes", "CRM 198765-SP"),
  exp=dict(tipo="LAUDO_EXAME_LABORATORIAL", esp=["Hematologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Débora Cristina Melo", idade=29),
                      medico=dict(nome="Dra. Camila Ferreira Lopes", crm=dict(numero="198765", uf="SP")),
                      diagnostico="Anemia ferropriva", cid="D50.9", medicamentos=[],
                      exames=["Hemograma", "Ferritina", "Saturação de transferrina"], urgencia="NAO"),
           ass=["Lista de medicamentos vazia não força revisão (RF-21)",
                "Distinguir 'nenhum identificado' de 'leitura falhou'",
                "Status PROCESSADO"]))

c(id="Ausencia_SomenteExames", titulo="ATESTADO MÉDICO",
  sub="Atestado sem exames solicitados ou realizados",
  meta=[("Paciente", "Igor Nascimento Prado"), ("Idade", "24 anos"), ("Documento", "DOC-ATE-2026-0033"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Clínica Médica")],
  secs=[sec("Finalidade", "Atestado de comparecimento."),
        sec("Texto do atestado", "Atesto que o paciente compareceu a consulta médica nesta data, no período das 14h00 às 15h10."),
        sec("Diagnóstico / CID", "Dermatite de contato — CID-10 L23.9.")],
  doc=("Dr. Paulo Mendes Rocha", "CRM 203114-RJ"),
  exp=dict(tipo="ATESTADO_MEDICO", esp=["Clínica Médica", "Dermatologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Igor Nascimento Prado", idade=24),
                      medico=dict(nome="Dr. Paulo Mendes Rocha", crm=dict(numero="203114", uf="RJ")),
                      diagnostico="Dermatite de contato", cid="L23.9", medicamentos=[], exames=[],
                      urgencia="NAO"),
           ass=["Ausência de exames não força revisão (RF-21)",
                "Diagnóstico presente mantém o fluxo",
                "Status PROCESSADO"]))

# ============================================================ BLOCO B (1)
c(id="Borda_Score_085", titulo="RECEITUÁRIO MÉDICO",
  sub="Prescrição ambulatorial — limiar exato de 0,85",
  meta=[("Paciente", "Ricardo Almeida Prado"), ("Idade", "45 anos"), ("Documento", "DOC-REC-2026-0034"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Clínica Médica")],
  secs=[sec("Hipótese diagnóstica", "Rinite alérgica persistente — CID-10 J30.4."),
        sec("Prescrição", "Loratadina 10 mg — 1 comprimido por via oral uma vez ao dia, por 30 dias."),
        sec("Orientações", "Evitar exposição a alérgenos e retorno se piora dos sintomas.")],
  doc=("Dra. Helena Prado", "CRM 187432-SP"),
  exp=dict(tipo="RECEITUARIO_MEDICO", esp=["Clínica Médica", "Alergologia"], prio="ROTINA",
           status="PROCESSADO", dest=["FARMACIA_HOSPITALAR"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Ricardo Almeida Prado", idade=45),
                      medico=dict(nome="Dra. Helena Prado", crm=dict(numero="187432", uf="SP")),
                      diagnostico="Rinite alérgica persistente", cid="J30.4",
                      medicamentos=["Loratadina 10 mg"], exames=[], urgencia="NAO"),
           score=dict(score_classificacao=0.94, score_extracao=0.85, score_combinado=0.85, limiar=0.85),
           ass=["Score exatamente 0,85 NÃO revisa por esse critério isolado",
                "Comparação usa < 0,85, não <= 0,85 (RF-18)",
                "Exige FIXTURE_MODE para forçar os scores"],
           obs="Documento de rotina legível. O score forçado em 0,85 é a única borda testada."))

# ============================================================ BLOCO C (5)
c(id="Conflito_Cid_Diagnostico", titulo="LAUDO DE EXAME DE IMAGEM",
  sub="Diagnóstico e CID incompatíveis",
  meta=[("Paciente", "Marcelo Tavares Lins"), ("Idade", "59 anos"), ("Documento", "DOC-IMG-2026-0035"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Cardiologia")],
  secs=[sec("Exame realizado", "Radiografia de tórax, incidência PA."),
        sec("Achados", "Campos pulmonares com trama vascular preservada, sem consolidações ou derrames. Área cardíaca de dimensões normais."),
        sec("Conclusão", "Lombalgia mecânica crônica sem alterações no exame de imagem."),
        sec("CID informado", "CID-10 I21.9 — infarto agudo do miocárdio.")],
  doc=("Dr. André Luiz Barbosa", "CRM 165432-SP"),
  exp=dict(tipo="LAUDO_EXAME_IMAGEM", esp=["Ortopedia", "Radiologia"], prio="ROTINA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome="Marcelo Tavares Lins", idade=59),
                      medico=dict(nome="Dr. André Luiz Barbosa", crm=dict(numero="165432", uf="SP")),
                      diagnostico="Lombalgia mecânica crônica", cid="I21.9", medicamentos=[],
                      exames=["Radiografia de tórax"], urgencia="NAO"),
           conflitos=[dict(tipo="CID_DIAGNOSTICO", campos=["cid_extraido", "diagnostico_principal"],
                           gravidade="ALTA", descricao="CID de infarto agudo incompatível com lombalgia")],
           ass=["Conflito explícito entre CID e diagnóstico", "Valores originais preservados (RF-16)",
                "Revisão humana obrigatória por conflito impeditivo"],
           obs="Exige o dicionário de CID-10 aprovado pela equipe para a regra de compatibilidade."))

c(id="Conflito_Dose", titulo="RECEITUÁRIO MÉDICO",
  sub="Dose dez vezes acima do usual",
  meta=[("Paciente", "Neusa Ferreira Lima"), ("Idade", "73 anos"), ("Documento", "DOC-REC-2026-0036"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Cardiologia")],
  secs=[sec("Hipótese diagnóstica", "Hipertensão arterial sistêmica — CID-10 I10."),
        sec("Prescrição", "Losartana potássica 500 mg — 1 comprimido por via oral uma vez ao dia, por 30 dias."),
        sec("Orientações", "Retorno em 30 dias para controle pressórico.")],
  doc=("Dr. Paulo Mendes Rocha", "CRM 203114-RJ"),
  exp=dict(tipo="RECEITUARIO_MEDICO", esp=["Cardiologia"], prio="ROTINA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome="Neusa Ferreira Lima", idade=73),
                      medico=dict(nome="Dr. Paulo Mendes Rocha", crm=dict(numero="203114", uf="RJ")),
                      diagnostico="Hipertensão arterial sistêmica", cid="I10",
                      medicamentos=["Losartana potássica 500 mg"], exames=[], urgencia="NAO"),
           conflitos=[dict(tipo="DOSE_SUSPEITA", campos=["medicamentos[0].dose"],
                           gravidade="ALTA", descricao="Losartana 500 mg excede a dose usual (50–100 mg)")],
           ass=["Dose suspeita sinalizada sem alterar o valor (RF-16)",
                "Valor original 500 mg preservado", "Revisão humana obrigatória"],
           obs="Depende da tabela de doses de referência aprovada pela equipe."))

c(id="Conflito_Prioridade", titulo="GUIA DE SOLICITAÇÃO DE PROCEDIMENTO",
  sub="Guia marcada como rotina, com texto de urgência",
  meta=[("Paciente", "Rogério Pinto Machado"), ("Idade", "61 anos"), ("Documento", "DOC-GUI-2026-0037"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Cirurgia Vascular")],
  secs=[sec("Prioridade declarada", "ROTINA — atendimento eletivo."),
        sec("Diagnóstico / CID", "Trombose venosa profunda de membro inferior — CID-10 I80.2."),
        sec("Procedimento solicitado", "Ultrassonografia Doppler venoso de membros inferiores."),
        sec("Justificativa clínica", "Paciente com edema súbito e dor em panturrilha direita. Há risco de embolia pulmonar; avaliação necessária com urgência.")],
  doc=("Dra. Camila Ferreira Lopes", "CRM 198765-SP"),
  exp=dict(tipo="GUIA_PROCEDIMENTO", esp=["Cirurgia Vascular"], prio="URGENTE",
           status="EM_REVISAO", dest=["FILA_URGENCIA_MEDICA", "FILA_REVISAO_HUMANA"], rev=True, notif=True,
           dados=dict(paciente=dict(nome="Rogério Pinto Machado", idade=61),
                      medico=dict(nome="Dra. Camila Ferreira Lopes", crm=dict(numero="198765", uf="SP")),
                      diagnostico="Trombose venosa profunda de membro inferior", cid="I80.2",
                      medicamentos=[], exames=["Ultrassonografia Doppler venoso"], urgencia="SIM"),
           conflitos=[dict(tipo="PRIORIDADE_TEXTO", campos=["nivel_prioridade", "texto"],
                           gravidade="ALTA", descricao="Cabeçalho ROTINA conflita com texto de urgência")],
           ass=["Discrepância entre prioridade declarada e sinais textuais",
                "Sinal crítico prevalece sobre o cabeçalho (RN-03)",
                "Dois destinos: urgência e revisão"]))

c(id="Conflito_Dados", titulo="RELATÓRIO DE ALTA HOSPITALAR",
  sub="Identificação do paciente contraditória no documento",
  meta=[("Paciente", "Fernando Augusto Reis"), ("Idade", "66 anos"), ("Documento", "DOC-ALT-2026-0038"),
        ("Data", "18/10/2026"), ("Origem", "Enfermaria 5A")],
  secs=[sec("Identificação", "Paciente: Fernando Augusto Reis, 66 anos, prontuário 448211."),
        sec("Resumo da internação", "Paciente do sexo masculino internado por pielonefrite aguda, tratado com antibioticoterapia endovenosa por 7 dias."),
        sec("Corpo do relatório", "Ao exame, paciente Fernando Augusto dos Reis, 56 anos, prontuário 448211, apresenta melhora clínica e laboratorial."),
        sec("Diagnóstico principal", "Pielonefrite aguda — CID-10 N10.")],
  doc=("Dr. André Luiz Barbosa", "CRM 165432-SP"),
  exp=dict(tipo="RELATORIO_ALTA_INTERNACAO", esp=["Nefrologia", "Clínica Médica"], prio="ROTINA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome="Fernando Augusto Reis", idade=66),
                      medico=dict(nome="Dr. André Luiz Barbosa", crm=dict(numero="165432", uf="SP")),
                      diagnostico="Pielonefrite aguda", cid="N10", medicamentos=[], exames=[],
                      urgencia="NAO"),
           conflitos=[dict(tipo="CONTRADICAO_INTERNA", campos=["paciente.nome", "paciente.idade"],
                           gravidade="ALTA", descricao="Nome e idade divergem entre cabeçalho e corpo")],
           ass=["Contradição interna em nome e idade", "Valores originais preservados",
                "Revisão humana obrigatória"]))

c(id="Conflito_AltoRisco", titulo="RECEITUÁRIO MÉDICO",
  sub="Prescrição de alto risco sem texto de urgência",
  meta=[("Paciente", "Alzira Mendes Coelho"), ("Idade", "70 anos"), ("Documento", "DOC-REC-2026-0039"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Cardiologia")],
  secs=[sec("Hipótese diagnóstica", "Fibrilação atrial crônica — CID-10 I48.9."),
        sec("Prescrição", "Varfarina sódica 10 mg — 1 comprimido por via oral uma vez ao dia, uso contínuo."),
        sec("Orientações", "Controle de INR conforme protocolo. Não há menção a urgência no documento.")],
  doc=("Dra. Helena Prado", "CRM 187432-SP"),
  exp=dict(tipo="RECEITUARIO_MEDICO", esp=["Cardiologia"], prio="URGENTE",
           status="EM_REVISAO", dest=["FILA_URGENCIA_MEDICA"], rev=True, notif=True,
           dados=dict(paciente=dict(nome="Alzira Mendes Coelho", idade=70),
                      medico=dict(nome="Dra. Helena Prado", crm=dict(numero="187432", uf="SP")),
                      diagnostico="Fibrilação atrial crônica", cid="I48.9",
                      medicamentos=["Varfarina sódica 10 mg"], exames=[], urgencia="SIM"),
           ass=["Medicamento de alto risco aciona a fila urgente (RN-03)",
                "Sem texto de urgência: a regra vem do dicionário de alto risco",
                "Alerta simulado registrado"],
           obs="Depende da lista de medicamentos de alto risco aprovada pela equipe."))

# ============================================================ BLOCO S (2)
c(id="Simultaneo_Urgencia_Ilegivel", titulo="RECEITUÁRIO MÉDICO",
  sub="Prescrição urgente parcialmente ilegível",
  meta=[("Paciente", "Joana Batista Ferraz"), ("Idade", "58 anos"), ("Documento", "DOC-REC-2026-0040"),
        ("Data", "18/10/2026"), ("Origem", "Pronto-Socorro")],
  secs=[sec("Hipótese diagnóstica", "Crise hipertensiva com risco de lesão de órgão-alvo — CID-10 I16.9."),
        sec("Prescrição", "Nitroprussiato de sódio — infusão contínua conforme protocolo. Dose inicial ilegível no documento."),
        sec("Sinal de urgência", "ATENDIMENTO IMEDIATO — PA 210/120 mmHg. Iniciar tratamento agora.")],
  doc=("Dra. Camila Ferreira Lopes", "CRM 198765-SP"),
  flags=dict(degrade_mild=True),
  exp=dict(tipo="RECEITUARIO_MEDICO", esp=["Cardiologia"], prio="URGENTE",
           status="EM_REVISAO", dest=["FILA_URGENCIA_MEDICA", "FILA_REVISAO_HUMANA"], rev=True, notif=True,
           dados=dict(paciente=dict(nome="Joana Batista Ferraz", idade=58),
                      medico=dict(nome="Dra. Camila Ferreira Lopes", crm=dict(numero="198765", uf="SP")),
                      diagnostico="Crise hipertensiva", cid="I16.9",
                      medicamentos=["Nitroprussiato de sódio"], exames=[], urgencia="SIM",
                      campos_incertos=["medicamentos[0].dose"]),
           ass=["Urgência e ilegibilidade simultâneas (§8.2)",
                "Dois destinos no mesmo payload",
                "Nunca reduzir a decisão a um destino único"],
           obs="Imagem com desfoque leve: os campos de dose ficam incertos, o restante é legível."))

c(id="Simultaneo_Urgencia_Score", titulo="LAUDO DE EXAME DE IMAGEM",
  sub="Achado crítico com score abaixo do limiar",
  meta=[("Paciente", "Wilson Aparecido Rangel"), ("Idade", "64 anos"), ("Documento", "DOC-IMG-2026-0041"),
        ("Data", "18/10/2026"), ("Origem", "Pronto-Socorro")],
  secs=[sec("Exame realizado", "Tomografia computadorizada de crânio sem contraste."),
        sec("Achados", "Hematoma subdural agudo em convexidade frontoparietal esquerda, com desvio da linha média de 6 mm."),
        sec("Conclusão", "Hematoma subdural agudo com efeito de massa. Avaliação neurocirúrgica imediata.")],
  doc=("Dra. Renata Silveira", "CRM 145892-SP"),
  exp=dict(tipo="LAUDO_EXAME_IMAGEM", esp=["Radiologia", "Neurocirurgia"], prio="URGENTE",
           status="EM_REVISAO", dest=["FILA_URGENCIA_MEDICA", "FILA_REVISAO_HUMANA"], rev=True, notif=True,
           dados=dict(paciente=dict(nome="Wilson Aparecido Rangel", idade=64),
                      medico=dict(nome="Dra. Renata Silveira", crm=dict(numero="145892", uf="SP")),
                      diagnostico="Hematoma subdural agudo", cid=None, medicamentos=[],
                      exames=["Tomografia de crânio"], urgencia="SIM"),
           score=dict(score_classificacao=0.88, score_extracao=0.70, score_combinado=0.70, limiar=0.85),
           ass=["Urgência + score 0,70: dois destinos e alerta",
                "Score baixo não rebaixa a urgência",
                "Exige FIXTURE_MODE para forçar os scores"]))

# ============================================================ BLOCO Q (8)
c(id="Qualidade_Foto_Desfocada", titulo="RECEITUÁRIO MANUSCRITO",
  sub="Foto de receita manuscrita muito desfocada",
  meta=[("Paciente", "—"), ("Idade", "—"), ("Documento", "DOC-Q-2026-0042"),
        ("Data", "18/10/2026"), ("Origem", "Foto enviada por celular")],
  secs=[sec("Conteúdo", "Receita manuscrita fotografada com desfoque severo. Apenas o cabeçalho é legível; o corpo da prescrição não permite leitura segura."),
        sec("Orientação", "Reenviar imagem nítida ou o documento original para revisão humana.")],
  doc=("—", "—"),
  flags=dict(degrade_handwritten=True),
  exp=dict(tipo="NAO_IDENTIFICADO", esp=[], prio="NAO_IDENTIFICADA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome=None, idade=None), medico=dict(nome=None, crm=None),
                      diagnostico=None, cid=None, medicamentos=[], exames=[], urgencia="INDETERMINADO",
                      campos_ausentes=["paciente.nome", "paciente.idade", "medico.nome", "medico.crm",
                                       "diagnostico_principal"]),
           ass=["Imagem muito desfocada não permite extração", "Nenhuma lacuna é preenchida",
                "Revisão humana indicada"],
           obs="JPG e PDF fortemente degradados; cabeçalho de identificação preservado."))

c(id="Qualidade_Foto_Rotacionada", titulo="LAUDO DE EXAME DE IMAGEM",
  sub="Laudo fotografado com rotação de 90 graus",
  meta=[("Paciente", "Cláudio Roberto Farias"), ("Idade", "48 anos"), ("Documento", "DOC-Q-2026-0043"),
        ("Data", "18/10/2026"), ("Origem", "Foto enviada por celular")],
  secs=[sec("Exame realizado", "Ultrassonografia de abdome total."),
        sec("Achados", "Fígado de dimensões normais. Vesícula biliar com cálculo único de 8 mm, sem sinais de colecistite. Vias biliares não dilatadas."),
        sec("Conclusão", "Colelitíase sem sinais inflamatórios agudos.")],
  doc=("Dr. Marcos Vinícius Tavares", "CRM 176543-MG"),
  flags=dict(rotate90=True),
  exp=dict(tipo="LAUDO_EXAME_IMAGEM", esp=["Radiologia", "Gastroenterologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Cláudio Roberto Farias", idade=48),
                      medico=dict(nome="Dr. Marcos Vinícius Tavares", crm=dict(numero="176543", uf="MG")),
                      diagnostico="Colelitíase sem sinais inflamatórios agudos", cid=None, medicamentos=[],
                      exames=["Ultrassonografia de abdome total"], urgencia="NAO"),
           ass=["Rotação de 90° deve ser tolerada pelo pipeline multimodal",
                "Extração correta apesar da orientação", "Destino PRONTUARIO_ELETRONICO"],
           obs="A imagem e o PDF estão rotacionados; o texto permanece legível."))

c(id="Qualidade_Foto_Cortada", titulo="GUIA DE SOLICITAÇÃO DE PROCEDIMENTO",
  sub="Guia com metade da página fora do enquadramento",
  meta=[("Paciente", "Elaine Souza Barreto"), ("Idade", "36 anos"), ("Documento", "DOC-Q-2026-0044"),
        ("Data", "18/10/2026"), ("Origem", "Foto enviada por celular")],
  secs=[sec("Diagnóstico / CID", "Nódulo tireoidiano a esclarecer — CID-10 E04.1."),
        sec("Procedimento solicitado", "Punção aspirativa por agulha fina de tireoide."),
        sec("Justificativa clínica", "Nódulo de 1,8 cm em lobo direito, hipoecoico, com microcalcificações.")],
  doc=("Dra. Helena Prado", "CRM 187432-SP"),
  flags=dict(crop=True),
  exp=dict(tipo="GUIA_PROCEDIMENTO", esp=["Endocrinologia"], prio="ROTINA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome="Elaine Souza Barreto", idade=36),
                      medico=dict(nome="Dra. Helena Prado", crm=None),
                      diagnostico="Nódulo tireoidiano a esclarecer", cid="E04.1", medicamentos=[],
                      exames=["Punção aspirativa por agulha fina de tireoide"], urgencia="NAO",
                      campos_ausentes=["medico.crm"]),
           ass=["Recorte remove o CRM da assinatura", "Ausência de CRM força revisão",
                "Demais campos permanecem extraíveis"],
           obs="A imagem e o PDF mostram apenas a metade superior da página."))

c(id="Qualidade_Foto_BaixoContraste", titulo="ATESTADO MÉDICO",
  sub="Atestado com sombra e baixo contraste",
  meta=[("Paciente", "Michele Andrade Pinto"), ("Idade", "40 anos"), ("Documento", "DOC-Q-2026-0045"),
        ("Data", "18/10/2026"), ("Origem", "Foto enviada por celular")],
  secs=[sec("Finalidade", "Atestado de afastamento de 2 dias."),
        sec("Texto do atestado", "Atesto que a paciente necessita de afastamento de suas atividades por 2 (dois) dias, a contar de 18/10/2026."),
        sec("Diagnóstico / CID", "Lombalgia aguda — CID-10 M54.5.")],
  doc=("Dr. André Luiz Barbosa", "CRM 165432-SP"),
  flags=dict(low_contrast=True),
  exp=dict(tipo="ATESTADO_MEDICO", esp=["Ortopedia"], prio="ROTINA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome="Michele Andrade Pinto", idade=None),
                      medico=dict(nome="Dr. André Luiz Barbosa", crm=dict(numero="165432", uf="SP")),
                      diagnostico="Lombalgia aguda", cid="M54.5", medicamentos=[], exames=[],
                      urgencia="NAO", campos_incertos=["paciente.idade"]),
           ass=["Sombra sobre a linha da idade gera campo incerto",
                "Campo incerto é sinalizado, não inventado (RF-15)",
                "Revisão humana indicada"],
           obs="Degradação leve: sombra no canto inferior esquerdo compromete a linha da idade."))

c(id="Qualidade_Pdf_SemTexto", titulo="LAUDO DE EXAME DE IMAGEM",
  sub="PDF escaneado sem camada de texto",
  meta=[("Paciente", "Sérgio Luiz Monteiro"), ("Idade", "54 anos"), ("Documento", "DOC-Q-2026-0046"),
        ("Data", "18/10/2026"), ("Origem", "Digitalização externa")],
  secs=[sec("Exame realizado", "Tomografia computadorizada de tórax de baixa dose."),
        sec("Achados", "Nódulo pulmonar sólido de 6 mm em lobo superior direito. Sem linfonodomegalias mediastinais. Ausência de derrame pleural."),
        sec("Conclusão", "Nódulo pulmonar de 6 mm, categoria Lung-RADS 3. Sugere-se seguimento em 6 meses.")],
  doc=("Dra. Renata Silveira", "CRM 145892-SP"),
  flags=dict(scan=True),
  exp=dict(tipo="LAUDO_EXAME_IMAGEM", esp=["Radiologia", "Pneumologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Sérgio Luiz Monteiro", idade=54),
                      medico=dict(nome="Dra. Renata Silveira", crm=dict(numero="145892", uf="SP")),
                      diagnostico="Nódulo pulmonar sólido de 6 mm", cid=None, medicamentos=[],
                      exames=["Tomografia de tórax de baixa dose"], urgencia="NAO"),
           ass=["PDF sem camada de texto é aceito", "Leitura feita pelo caminho multimodal",
                "Destino PRONTUARIO_ELETRONICO"],
           obs="PDF gerado somente com imagem (0 caracteres extraíveis)."))

c(id="Qualidade_Pdf_Multipagina", titulo="RELATÓRIO DE ALTA HOSPITALAR",
  sub="Relatório extenso com seis páginas",
  meta=[("Paciente", "Iracema Barbosa Teixeira"), ("Idade", "74 anos"), ("Documento", "DOC-Q-2026-0047"),
        ("Data", "18/10/2026"), ("Origem", "Enfermaria 6B")],
  secs=[sec("Período de internação", "Admissão em 05/10/2026, alta em 18/10/2026 (13 dias)."),
        sec("Diagnóstico principal", "Sepse de foco pulmonar — CID-10 A41.9."),
        sec("Resumo da internação", "Paciente internada com febre, tosse produtiva e rebaixamento do nível de consciência. Diagnosticada pneumonia com derrame parapneumônico, tratada com antibioticoterapia endovenosa por 14 dias e drenagem torácica.")] +
        [sec(f"Evolução — dia {d}", f"Dia {d} de internação: paciente em antibioticoterapia endovenosa, "
              f"hemodinamicamente estável, afebril nas últimas 24 horas. Controle laboratorial diário sem "
              f"novas alterações significativas. Fisioterapia respiratória mantida. Aceitação parcial da dieta, "
              f"diurese preservada e balanço hídrico equilibrado nas últimas 24 horas.") for d in range(1, 21)] +
        [sec("Medicações de alta", "Amoxicilina + clavulanato 875/125 mg — 1 comprimido por via oral a cada 12 horas, por 7 dias."),
         sec("Orientações", "Retorno em 7 dias com radiografia de controle. Sinais de alarme: febre, dispneia ou dor torácica.")],
  doc=("Dr. Paulo Mendes Rocha", "CRM 203114-RJ"),
  flags=dict(multipage=True, break_every=4),
  exp=dict(tipo="RELATORIO_ALTA_INTERNACAO", esp=["Infectologia", "Pneumologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Iracema Barbosa Teixeira", idade=74),
                      medico=dict(nome="Dr. Paulo Mendes Rocha", crm=dict(numero="203114", uf="RJ")),
                      diagnostico="Sepse de foco pulmonar", cid="A41.9",
                      medicamentos=["Amoxicilina + clavulanato 875/125 mg"], exames=[],
                      urgencia="NAO"),
           ass=["PDF com 6+ páginas é aceito", "Conteúdo completo é considerado na extração",
                "Limite de páginas ainda pendente na spec (§15)"]))

c(id="Qualidade_Pdf_ComSenha", titulo="RECEITUÁRIO MÉDICO",
  sub="PDF protegido por senha",
  meta=[("Paciente", "—"), ("Idade", "—"), ("Documento", "DOC-Q-2026-0048"),
        ("Data", "18/10/2026"), ("Origem", "Upload manual")],
  secs=[sec("Conteúdo", "Documento protegido por senha. O conteúdo não pode ser lido sem a credencial fornecida pelo emissor."),
        sec("Observação", "O contrato de erro deve definir se o documento é rejeitado (415/422) ou encaminhado para revisão humana.")],
  doc=("—", "—"),
  flags=dict(secure=True),
  exp=dict(tipo="N/A", esp=[], prio="NAO_IDENTIFICADA",
           status="ERRO_PROCESSAMENTO", dest=["N/A"], rev=None, notif=False,
           dados=dict(paciente=dict(nome=None, idade=None), medico=dict(nome=None, crm=None),
                      diagnostico=None, cid=None, medicamentos=[], exames=[], urgencia="INDETERMINADO"),
           ass=["PDF protegido não pode ser lido", "Erro controlado, sem stack trace (RF-03/§12)",
                "Contrato de erro ainda a definir"],
           obs="Senha de teste: mediflow123. O fixture existe para testar a rejeição, não o sucesso."))

c(id="Qualidade_Pdf_Corrompido", titulo="LAUDO DE EXAME LABORATORIAL",
  sub="PDF truncado / arquivo corrompido",
  meta=[("Paciente", "—"), ("Idade", "—"), ("Documento", "DOC-Q-2026-0049"),
        ("Data", "18/10/2026"), ("Origem", "Upload manual")],
  secs=[sec("Conteúdo", "Arquivo PDF truncado durante a transferência. Estrutura de objetos incompleta e tabela de referências cruzadas ausente."),
        sec("Observação", "Deve gerar erro controlado, com mensagem segura e possibilidade de reenvio.")],
  doc=("—", "—"),
  flags=dict(corrupt=True),
  exp=dict(tipo="N/A", esp=[], prio="NAO_IDENTIFICADA",
           status="ERRO_PROCESSAMENTO", dest=["N/A"], rev=None, notif=False,
           dados=dict(paciente=dict(nome=None, idade=None), medico=dict(nome=None, crm=None),
                      diagnostico=None, cid=None, medicamentos=[], exames=[], urgencia="INDETERMINADO"),
           ass=["Arquivo corrompido gera ERRO_PROCESSAMENTO",
                "Mensagem segura, sem stack trace", "Permitir reenvio"],
           obs="Arquivo truncado em 40% do tamanho original."))

# ============================================================ BLOCO E (6)
E_BASE = dict(
    meta_data="18/10/2026", origem="Digitalização externa",
)


TIPO_POR_TITULO = {
    "RECEITUÁRIO MÉDICO": "RECEITUARIO_MEDICO",
    "LAUDO DE EXAME LABORATORIAL": "LAUDO_EXAME_LABORATORIAL",
    "LAUDO DE EXAME DE IMAGEM": "LAUDO_EXAME_IMAGEM",
    "GUIA DE SOLICITAÇÃO DE PROCEDIMENTO": "GUIA_PROCEDIMENTO",
    "RELATÓRIO DE ALTA HOSPITALAR": "RELATORIO_ALTA_INTERNACAO",
    "ATESTADO MÉDICO": "ATESTADO_MEDICO",
    "TERMO DE CONSENTIMENTO": "OUTRO",
}


def ecase(id_, titulo, sub, paciente, idade, docnum, secs, doc, esp, dest, dados, ass):
    c(id=id_, titulo=titulo, sub=sub,
      meta=[("Paciente", paciente), ("Idade", idade), ("Documento", docnum),
            ("Data", "18/10/2026"), ("Origem", "Digitalização externa")],
      secs=secs, doc=doc, flags=dict(scan=True),
      exp=dict(tipo=TIPO_POR_TITULO[titulo], esp=esp, prio="ROTINA", status="PROCESSADO", dest=[dest],
               rev=False, notif=False, dados=dados, ass=ass))


ecase("Escaneado_Receituario_PdfDigitalizado", "RECEITUÁRIO MÉDICO", "Receita impressa escaneada em PDF",
      "Marli Aparecida Fonseca", "50 anos", "DOC-E-2026-0050",
      [sec("Hipótese diagnóstica", "Hipertensão arterial sistêmica — CID-10 I10."),
       sec("Prescrição", "Anlodipino 5 mg — 1 comprimido por via oral uma vez ao dia, por 30 dias."),
       sec("Orientações", "Retorno em 30 dias para controle pressórico.")],
      ("Dr. Marcos Vinícius Tavares", "CRM 176543-MG"), ["Cardiologia"], "FARMACIA_HOSPITALAR",
      dict(paciente=dict(nome="Marli Aparecida Fonseca", idade=50),
           medico=dict(nome="Dr. Marcos Vinícius Tavares", crm=dict(numero="176543", uf="MG")),
           diagnostico="Hipertensão arterial sistêmica", cid="I10",
           medicamentos=["Anlodipino 5 mg"], exames=[], urgencia="NAO"),
      ["PDF escaneado com camada de imagem", "Extração correta pelo caminho multimodal",
       "Destino FARMACIA_HOSPITALAR"])

ecase("Escaneado_LaudoLaboratorial_PdfDigitalizado", "LAUDO DE EXAME LABORATORIAL", "Laudo laboratorial escaneado em PDF",
      "Jorge Luís Andrade", "44 anos", "DOC-E-2026-0051",
      [sec("Hipótese diagnóstica", "Gota — CID-10 M10.9."),
       sec("Resultados", "Ácido úrico: 9,2 mg/dL (referência 3,5–7,2)\nCreatinina: 1,0 mg/dL (referência 0,7–1,3)\nPCR: 18 mg/L (referência < 5)"),
       sec("Conclusão", "Hiperuricemia com resposta inflamatória. Correlacionar com quadro articular.")],
      ("Dra. Helena Prado", "CRM 187432-SP"), ["Reumatologia", "Clínica Médica"], "PRONTUARIO_ELETRONICO",
      dict(paciente=dict(nome="Jorge Luís Andrade", idade=44),
           medico=dict(nome="Dra. Helena Prado", crm=dict(numero="187432", uf="SP")),
           diagnostico="Gota", cid="M10.9", medicamentos=[],
           exames=["Ácido úrico", "Creatinina", "PCR"], urgencia="NAO"),
      ["PDF escaneado sem camada de texto", "Três analitos extraídos",
       "Destino PRONTUARIO_ELETRONICO"])

ecase("Escaneado_Guia_PdfDigitalizado", "GUIA DE SOLICITAÇÃO DE PROCEDIMENTO", "Guia de procedimento escaneada em PDF",
      "Adriana Lopes Siqueira", "42 anos", "DOC-E-2026-0052",
      [sec("Diagnóstico / CID", "Hérnia de disco lombar — CID-10 M51.2."),
       sec("Procedimento solicitado", "Ressonância magnética de coluna lombar."),
       sec("Justificativa clínica", "Dor irradiada para membro inferior esquerdo refratária a tratamento conservador por 8 semanas.")],
      ("Dr. André Luiz Barbosa", "CRM 165432-SP"), ["Ortopedia"], "AUDITORIA_AUTORIZACOES",
      dict(paciente=dict(nome="Adriana Lopes Siqueira", idade=42),
           medico=dict(nome="Dr. André Luiz Barbosa", crm=dict(numero="165432", uf="SP")),
           diagnostico="Hérnia de disco lombar", cid="M51.2", medicamentos=[],
           exames=["Ressonância magnética de coluna lombar"], urgencia="NAO"),
      ["Guia escaneada é classificada corretamente", "Destino AUDITORIA_AUTORIZACOES",
       "CID e procedimento extraídos"])

ecase("Escaneado_RelatorioDeAlta_PdfDigitalizado", "RELATÓRIO DE ALTA HOSPITALAR", "Relatório de alta escaneado em PDF",
      "Sebastião Ferreira Gomes", "69 anos", "DOC-E-2026-0053",
      [sec("Período de internação", "Admissão em 12/10/2026, alta em 18/10/2026."),
       sec("Diagnóstico principal", "Doença pulmonar obstrutiva crônica exacerbada — CID-10 J44.1."),
       sec("Resumo", "Paciente internado com dispneia e tosse produtiva, tratado com broncodilatadores e corticoide sistêmico, com melhora."),
       sec("Medicações de alta", "Prednisona 20 mg — 1 comprimido por via oral pela manhã, por 5 dias.\nBudesonida + formoterol 6/200 mcg — 1 inalação a cada 12 horas, uso contínuo.")],
      ("Dr. Paulo Mendes Rocha", "CRM 203114-RJ"), ["Pneumologia"], "PRONTUARIO_ELETRONICO",
      dict(paciente=dict(nome="Sebastião Ferreira Gomes", idade=69),
           medico=dict(nome="Dr. Paulo Mendes Rocha", crm=dict(numero="203114", uf="RJ")),
           diagnostico="Doença pulmonar obstrutiva crônica exacerbada", cid="J44.1",
           medicamentos=["Prednisona 20 mg", "Budesonida + formoterol 6/200 mcg"],
           exames=[], urgencia="NAO"),
      ["Relatório escaneado é classificado", "Medicações de alta extraídas",
       "Destino PRONTUARIO_ELETRONICO"])

ecase("Escaneado_Atestado_PdfDigitalizado", "ATESTADO MÉDICO", "Atestado escaneado em PDF",
      "Tânia Regina Oliveira", "35 anos", "DOC-E-2026-0054",
      [sec("Finalidade", "Atestado de afastamento de 1 dia."),
       sec("Texto do atestado", "Atesto que a paciente necessita de afastamento de suas atividades laborais por 1 (um) dia, em 18/10/2026."),
       sec("Diagnóstico / CID", "Enxaqueca sem aura — CID-10 G43.0.")],
      ("Dra. Camila Ferreira Lopes", "CRM 198765-SP"), ["Neurologia"], "PRONTUARIO_ELETRONICO",
      dict(paciente=dict(nome="Tânia Regina Oliveira", idade=35),
           medico=dict(nome="Dra. Camila Ferreira Lopes", crm=dict(numero="198765", uf="SP")),
           diagnostico="Enxaqueca sem aura", cid="G43.0", medicamentos=[], exames=[], urgencia="NAO"),
      ["Atestado escaneado é classificado", "Afastamento e CID extraídos",
       "Destino PRONTUARIO_ELETRONICO"])

c(id="Escaneado_Outro_PdfDigitalizado", titulo="TERMO DE CONSENTIMENTO",
  sub="Termo administrativo escaneado — fora da taxonomia",
  meta=[("Paciente", "—"), ("Idade", "—"), ("Documento", "DOC-E-2026-0055"),
        ("Data", "18/10/2026"), ("Origem", "Digitalização externa")],
  secs=[sec("Documento", "Termo de consentimento para uso de imagem institucional, assinado por acompanhante, sem finalidade clínica."),
        sec("Conteúdo", "Autorizo o uso da minha imagem em materiais institucionais de comunicação interna da unidade de saúde.")],
  doc=("—", "—"),
  flags=dict(scan=True),
  exp=dict(tipo="OUTRO", esp=[], prio="NAO_IDENTIFICADA",
           status="EM_REVISAO", dest=["FILA_REVISAO_HUMANA"], rev=True, notif=False,
           dados=dict(paciente=dict(nome=None, idade=None), medico=dict(nome=None, crm=None),
                      diagnostico=None, cid=None, medicamentos=[], exames=[], urgencia="INDETERMINADO",
                      campos_ausentes=["paciente.nome", "paciente.idade", "medico.nome", "medico.crm",
                                       "diagnostico_principal"]),
           ass=["Termo administrativo escaneado fora da taxonomia",
                "Classificação OUTRO", "Revisão humana obrigatória"]))

# ============================================================ BLOCO D (4)
c(id="Diferencial_ReceituarioManuscrito", titulo="RECEITUÁRIO MÉDICO",
  sub="Receita manuscrita legível",
  meta=[("Paciente", "Vera Lúcia Santana"), ("Idade", "61 anos"), ("Documento", "DOC-D-2026-0056"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Clínica Médica")],
  secs=[sec("Hipótese diagnóstica", "Osteoartrite de joelhos — CID-10 M17.9."),
        sec("Prescrição", "Paracetamol 750 mg — 1 comprimido por via oral a cada 8 horas, por 7 dias.")],
  doc=("Dra. Helena Prado", "CRM 187432-SP"),
  flags=dict(handwritten=True),
  exp=dict(tipo="RECEITUARIO_MEDICO", esp=["Ortopedia", "Clínica Médica"], prio="ROTINA",
           status="PROCESSADO", dest=["FARMACIA_HOSPITALAR"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Vera Lúcia Santana", idade=61),
                      medico=dict(nome="Dra. Helena Prado", crm=dict(numero="187432", uf="SP")),
                      diagnostico="Osteoartrite de joelhos", cid="M17.9",
                      medicamentos=["Paracetamol 750 mg"], exames=[], urgencia="NAO"),
           ass=["Diferencial opcional: OCR de manuscrito", "Receita legível é classificada",
                "Destino FARMACIA_HOSPITALAR"],
           obs="Diferencial opcional (OCR/visão). Não é critério de aceite obrigatório do MVP."))

c(id="Diferencial_CarimboSobreposto", titulo="LAUDO DE EXAME DE IMAGEM",
  sub="Laudo escaneado com carimbo sobreposto ao texto",
  meta=[("Paciente", "Hugo Leonardo Peixoto"), ("Idade", "46 anos"), ("Documento", "DOC-D-2026-0057"),
        ("Data", "18/10/2026"), ("Origem", "Digitalização externa")],
  secs=[sec("Exame realizado", "Ultrassonografia de vias urinárias."),
        sec("Achados", "Rins de dimensões normais, sem dilatação pielocalicinal. Bexiga com parede regular, sem cálculos."),
        sec("Conclusão", "Exame ultrassonográfico sem alterações significativas.")],
  doc=("Dr. André Luiz Barbosa", "CRM 165432-SP"),
  flags=dict(scan=True, stamp=True),
  exp=dict(tipo="LAUDO_EXAME_IMAGEM", esp=["Radiologia", "Urologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Hugo Leonardo Peixoto", idade=46),
                      medico=dict(nome="Dr. André Luiz Barbosa", crm=dict(numero="165432", uf="SP")),
                      diagnostico="Exame ultrassonográfico sem alterações significativas", cid=None,
                      medicamentos=[], exames=["Ultrassonografia de vias urinárias"], urgencia="NAO"),
           ass=["Carimbo sobreposto não impede a extração",
                "Texto sob o carimbo permanece interpretável", "Destino PRONTUARIO_ELETRONICO"],
           obs="Diferencial opcional. Carimbo institucional aplicado sobre o rodapé do laudo."))

c(id="Diferencial_HemogramaCompleto", titulo="LAUDO DE EXAME LABORATORIAL",
  sub="Tabela de hemograma com 20 analitos",
  meta=[("Paciente", "Otávio Luiz Cardoso"), ("Idade", "39 anos"), ("Documento", "DOC-D-2026-0058"),
        ("Data", "18/10/2026"), ("Origem", "Laboratório Central")],
  secs=[sec("Hipótese diagnóstica", "Investigação de anemia — CID-10 D64.9."),
        sec("Resultados", "\n".join([
            "HEMOGRAMA COMPLETO                      RESULTADO    UNIDADE     REFERENCIA",
            "Hemacias ............................    4,62    milhoes/mm3   4,00 - 5,40",
            "Hemoglobina .........................    13,8    g/dL          12,0 - 16,0",
            "Hematocrito .........................    41,2    %             36,0 - 46,0",
            "VCM .................................    89,2    fL            80,0 - 100,0",
            "HCM .................................    29,9    pg            27,0 - 33,0",
            "CHCM ................................    33,5    g/dL          32,0 - 36,0",
            "RDW .................................    13,1    %             11,5 - 14,5",
            "Leucocitos ..........................    6.800   /mm3          4.000 - 11.000",
            "Neutrofilos .........................    58,0    %             40,0 - 70,0",
            "Linfocitos ..........................    30,0    %             20,0 - 45,0",
            "Monocitos ...........................    8,0     %             2,0 - 10,0",
            "Eosinofilos .........................    3,0     %             1,0 - 6,0",
            "Basofilos ...........................    1,0     %             0,0 - 2,0",
            "Plaquetas ...........................    268.000 /mm3          150.000 - 450.000",
            "VPM .................................    9,8     fL            7,5 - 11,0",
            "Ferritina ...........................    86      ng/mL         15 - 150",
            "Ferro serico ........................    92      mcg/dL        60 - 170",
            "Transferrina ........................    268     mg/dL         200 - 360",
            "Saturacao de transferrina ...........    28      %             20 - 50",
            "Vitamina B12 ........................    412     pg/mL         200 - 900",
        ]), mono=True),
        sec("Conclusão", "Hemograma dentro dos valores de referência. Sem evidência de anemia carencial.")],
  doc=("Dra. Camila Ferreira Lopes", "CRM 198765-SP"),
  exp=dict(tipo="LAUDO_EXAME_LABORATORIAL", esp=["Hematologia"], prio="ROTINA",
           status="PROCESSADO", dest=["PRONTUARIO_ELETRONICO"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Otávio Luiz Cardoso", idade=39),
                      medico=dict(nome="Dra. Camila Ferreira Lopes", crm=dict(numero="198765", uf="SP")),
                      diagnostico="Investigação de anemia", cid="D64.9", medicamentos=[],
                      exames=["Hemograma completo", "Ferritina", "Ferro sérico", "Transferrina",
                              "Saturação de transferrina", "Vitamina B12"], urgencia="NAO"),
           ass=["Tabela com 20 analitos é interpretada", "Valores e unidades preservados",
                "Destino PRONTUARIO_ELETRONICO"],
           obs="Diferencial opcional. Tabela em fonte monoespaçada para testar leitura estruturada."))

c(id="Diferencial_GuiaTiss", titulo="GUIA DE SOLICITAÇÃO DE PROCEDIMENTO",
  sub="Guia no padrão TISS com códigos de procedimento",
  meta=[("Paciente", "Renata Aparecida Moura"), ("Idade", "38 anos"), ("Documento", "DOC-D-2026-0059"),
        ("Data", "18/10/2026"), ("Origem", "Ambulatório de Ginecologia")],
  secs=[sec("Operadora / Plano", "Operadora Fictícia Saúde — Plano Ambulatorial Plus — Registro ANS 000000."),
        sec("Beneficiário", "Renata Aparecida Moura — carteirinha 0000 0000 0000 0000 — validade 12/2027."),
        sec("Diagnóstico / CID", "Mioma uterino — CID-10 D25.9."),
        sec("Procedimento solicitado", "Histeroscopia diagnóstica com polipectomia — código TUSS 31309136."),
        sec("Justificativa clínica", "Sangramento uterino anormal refratário ao tratamento clínico, com mioma submucoso à ultrassonografia."),
        sec("Autorização", "Solicitação eletiva. Número de guia 000000000000000 — senha 000000.")],
  doc=("Dra. Helena Prado", "CRM 187432-SP"),
  exp=dict(tipo="GUIA_PROCEDIMENTO", esp=["Ginecologia"], prio="ROTINA",
           status="PROCESSADO", dest=["AUDITORIA_AUTORIZACOES"], rev=False, notif=False,
           dados=dict(paciente=dict(nome="Renata Aparecida Moura", idade=38),
                      medico=dict(nome="Dra. Helena Prado", crm=dict(numero="187432", uf="SP")),
                      diagnostico="Mioma uterino", cid="D25.9", medicamentos=[],
                      exames=["Histeroscopia diagnóstica com polipectomia"], urgencia="NAO"),
           ass=["Guia TISS é classificada como GUIA_PROCEDIMENTO",
                "Código TUSS e número de guia preservados",
                "Destino AUDITORIA_AUTORIZACOES"],
           obs="Diferencial opcional. Códigos TUSS fictícios, apenas para teste de extração."))

# ============================================================ BLOCO V (8) — erros
V_CASES = [
    dict(id="Validacao_ArquivoDocx", arquivo="Validacao_ArquivoDocx.docx", kind="docx",
         http=415, codigo="FORMATO_NAO_SUPORTADO",
         desc="Arquivo .docx válido: formato fora do allowlist do MVP.",
         aceita="Não deve chamar o modelo."),
    dict(id="Validacao_ArquivoVazio", arquivo="Validacao_ArquivoVazio.pdf", kind="empty",
         http=422, codigo="CAMPOS_INVALIDOS",
         desc="Arquivo de 0 bytes: rejeitar antes de chamar o modelo.",
         aceita="Arquivo vazio não pode ser processado."),
    dict(id="Validacao_JsonMalformado", arquivo="Validacao_JsonMalformado.json", kind="badjson",
         http=400, codigo="REQUISICAO_INVALIDA",
         desc="JSON com vírgula final e sintaxe inválida.",
         aceita="Envelope não é interpretável."),
    dict(id="Validacao_EnvelopeVazio", arquivo="Validacao_EnvelopeVazio.json", kind="emptyenvelope",
         http=422, codigo="CAMPOS_INVALIDOS",
         desc="Envelope JSON vazio, sem campos obrigatórios.",
         aceita="Faltam tipo_arquivo e conteúdo."),
    dict(id="Validacao_SemConteudo", arquivo="Validacao_SemConteudo.http", kind="multipart",
         http=422, codigo="CAMPOS_INVALIDOS",
         desc="Requisição sem arquivo e sem documento_texto.",
         aceita="Requisição válida em sintaxe, vazia em conteúdo."),
    dict(id="Validacao_ArquivoZip", arquivo="Validacao_ArquivoZip.zip", kind="zip",
         http=415, codigo="FORMATO_NAO_SUPORTADO",
         desc="Arquivo .zip: formato não suportado.",
         aceita="Não deve descompactar nem chamar o modelo."),
    dict(id="Validacao_ArquivoGrande", arquivo="Validacao_ArquivoGrande.pdf", kind="big",
         http=413, codigo="ARQUIVO_MAIOR_QUE_LIMITE",
         desc="Arquivo de 25 MB: acima do limite configurado (limite ainda pendente na spec).",
         aceita="Rejeitar pelo tamanho antes de qualquer inferência."),
    dict(id="Validacao_MimeInvalido", arquivo="Validacao_MimeInvalido.pdf", kind="fakemime",
         http=415, codigo="MIME_INVALIDO",
         desc="Extensão .pdf com conteúdo real de PNG: inconsistência extensão × MIME.",
         aceita="Validar o conteúdo, não apenas a extensão."),
]


# ============================================================ RENDERIZAÇÃO
def draw_case(case, path, stamp=False, total_pages=None):
    """Desenha o PDF com paginação automática, seções mono e carimbo opcional."""
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle(f"{case['titulo']} — {case['id']} (fictício)")
    c.setAuthor("MediFlow — Hackathon ONE G10")
    c.setSubject("Documento fictício para testes do agente de triagem")

    state = {"page": 1, "total": total_pages}

    def start_page():
        from gerar_fixtures_demo import header, watermark
        watermark(c)
        header(c, {"id": case["id"]})
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.line(MARGIN, 42, W - MARGIN, 42)
        c.setFillColor(MUTED)
        c.setFont("DejaVu", 7.0)
        c.drawString(MARGIN, 30, f"MediFlow · fixture {case['id']} · dados sintéticos")
        label = (f"página {state['page']} de {total_pages}" if total_pages
                 else f"página {state['page']}")
        c.drawRightString(W - MARGIN, 30, f"{label} · gerado para testes automatizados")

    def new_page():
        c.showPage()
        state["page"] += 1
        start_page()
        return H - 108

    start_page()
    y = H - 112
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 16)
    c.drawString(MARGIN, y, case["titulo"])
    y -= 15
    c.setFont("DejaVu", 9)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, y, case["sub"])
    y -= 22

    c.setFillColor(SOFT)
    meta = case["meta"]
    rows = (len(meta) + 1) // 2
    box_h = 16 + rows * 14
    c.roundRect(MARGIN, y - box_h, CONTENT_W, box_h, 4, fill=1, stroke=0)
    yy = y - 8
    for i, (label, value) in enumerate(meta):
        col = i % 2
        row = i // 2
        x = MARGIN + 10 + col * (CONTENT_W / 2)
        ly = yy - row * 14
        c.setFillColor(MUTED)
        c.setFont("DejaVu-Bold", 7.2)
        c.drawString(x, ly, label.upper())
        c.setFillColor(INK)
        c.setFont("DejaVu", 8.6)
        c.drawString(x + 78, ly, value)
    y -= box_h + 18

    break_every = case["flags"].get("break_every")
    for idx, (heading, body, mono) in enumerate(case["secs"]):
        font = "DejaVuMono" if mono else "DejaVu"
        size = 6.4 if mono else 9.2
        lead = 8.4 if mono else 12.6

        if y < 130 or (break_every and idx > 0 and idx % break_every == 0):
            y = new_page()

        c.setFillColor(RED)
        c.setFont("DejaVu-Bold", 8.2)
        c.drawString(MARGIN, y, heading.upper())
        y -= 3
        c.setStrokeColor(SOFT)
        c.setLineWidth(0.6)
        c.line(MARGIN, y, W - MARGIN, y)
        y -= 13
        c.setFillColor(INK)
        c.setFont(font, size)
        for line in body.split("\n"):
            wrapped = [line] if mono else wrap(line, font, size, CONTENT_W)
            for part in wrapped:
                if y < 95:
                    y = new_page()
                    c.setFont(font, size)
                    c.setFillColor(INK)
                c.drawString(MARGIN, y, part)
                y -= lead
        y -= 9

    if y > 120:
        c.setStrokeColor(INK)
        c.setLineWidth(0.7)
        c.line(MARGIN, y, MARGIN + 220, y)
        y -= 12
        c.setFont("DejaVu-Bold", 9)
        c.setFillColor(INK)
        c.drawString(MARGIN, y, case["doc"][0])
        y -= 11
        c.setFont("DejaVu", 8.4)
        c.setFillColor(MUTED)
        c.drawString(MARGIN, y, case["doc"][1])

    if stamp:
        # carimbo institucional sobreposto ao texto da CONCLUSÃO
        c.saveState()
        c.translate(W - 210, y + 34)
        c.rotate(-11)
        c.setStrokeColor(RED)
        c.setLineWidth(1.8)
        c.roundRect(-92, -31, 184, 62, 7, fill=0, stroke=1)
        c.setFillColor(RED)
        c.setFont("DejaVu-Bold", 11)
        c.drawCentredString(0, 8, "RECEBIDO")
        c.setFont("DejaVu", 7.2)
        c.drawCentredString(0, -6, "Hospital Aurora · 18/10/2026")
        c.drawCentredString(0, -17, "Protocolo 000000")
        c.restoreState()

    c.showPage()
    c.save()



def draw_case_paged(case, path, stamp=False):
    """Desenha em duas passadas para numerar 'página N de M' corretamente."""
    tmp = tempfile.mktemp(suffix=".pdf")
    draw_case(case, tmp, stamp=stamp)
    total = fitz.open(tmp).page_count
    os.unlink(tmp)
    draw_case(case, path, stamp=stamp, total_pages=total)


def write_txt_case(case, path):
    lines = [
        HOSPITAL, HOSPITAL_SUB, "=" * 78, FICTION, "=" * 78, "",
        case["titulo"], case["sub"], "", f"Fixture: {case['id']}",
    ]
    for label, value in case["meta"]:
        lines.append(f"{label}: {value}")
    lines.append("")
    for heading, body, mono in case["secs"]:
        lines.append(heading.upper())
        lines.extend(body.split("\n"))
        lines.append("")
    lines += ["-" * 78, case["doc"][0], case["doc"][1], "-" * 78,
              f"MediFlow · fixture {case['id']} · dados sintéticos · página 1 de 1"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def rasterize(pdf_path, jpg_path, rot=0.35, blur=0.0, contrast=1.0, brightness=1.0,
              noise=0, rotate90=False, crop=None, shadow=False, quality=86):
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()

    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if noise:
        n = Image.effect_noise(img.size, noise).convert("L")
        img = Image.composite(img, Image.new("RGB", img.size, (236, 236, 234)),
                              n.point(lambda p: 22 if p > 140 else 0))
    if shadow:
        # mancha elíptica suave sobre a linha da IDADE (bloco de metadados, coluna direita)
        w, h = img.size
        overlay = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(overlay)
        cx, cy = int(w * 0.70), int(h * 0.198)
        rx, ry = int(w * 0.185), int(h * 0.024)
        steps = 26
        for i in range(steps, 0, -1):
            f = i / steps
            val = int(165 * (1 - f) ** 0.7)
            d.ellipse([cx - rx * f, cy - ry * f, cx + rx * f, cy + ry * f], fill=val)
        overlay = overlay.filter(ImageFilter.GaussianBlur(14))
        img = Image.composite(Image.new("RGB", (w, h), (86, 86, 84)), img, overlay)

    if crop:
        w, h = img.size
        img = img.crop((0, 0, int(w * crop[0]), int(h * crop[1])))

    if rotate90:
        img = img.rotate(-90, expand=True)
    elif rot:
        img = img.rotate(rot, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))

    img = ImageOps.expand(img, border=12, fill=(226, 226, 224))
    img.save(jpg_path, "JPEG", quality=quality, optimize=True)
    return jpg_path


def image_only_pdf(jpg_path, pdf_path):
    """PDF A4 retrato contendo apenas a imagem, preservando a proporção."""
    doc = fitz.open()
    page = doc.new_page(width=W, height=H)
    with Image.open(jpg_path) as im:
        iw, ih = im.size
    scale = min(W / iw, H / ih)
    w, h = iw * scale, ih * scale
    x, y = (W - w) / 2, (H - h) / 2
    page.insert_image(fitz.Rect(x, y, x + w, y + h), filename=jpg_path)
    doc.save(pdf_path, deflate=True)
    doc.close()


def degrade_strong(pdf_path, jpg_path, mode="scan"):
    """Degrada o miolo do documento mantendo o cabeçalho de identificação legível.

    mode="scan"  -> digitalização ruim: inclinação, ruído e manchas no corpo
    mode="photo" -> foto de manuscrito com desfoque severo no corpo
    """
    tmp = tempfile.mktemp(suffix=".jpg")
    rasterize(pdf_path, tmp, rot=1.8 if mode == "scan" else 2.6, quality=76)
    with Image.open(tmp) as im:
        img = im.convert("RGB")
    os.unlink(tmp)

    w, h = img.size
    top, bottom = int(h * 0.155), int(h * 0.905)      # preserva o cabeçalho
    body = img.crop((0, top, w, bottom))
    if mode == "photo":
        body = body.filter(ImageFilter.GaussianBlur(7.5))
        body = ImageEnhance.Contrast(body).enhance(0.68)
        body = ImageEnhance.Brightness(body).enhance(1.03)
    else:
        body = body.filter(ImageFilter.GaussianBlur(2.0))
        body = ImageEnhance.Contrast(body).enhance(0.72)
        noise = Image.effect_noise(body.size, 34).convert("L")
        body = Image.composite(body, Image.new("RGB", body.size, (232, 232, 230)),
                               noise.point(lambda px: 26 if px > 140 else 0))
        overlay = Image.new("L", body.size, 0)
        d = ImageDraw.Draw(overlay)
        rnd = random.Random(7)
        bw, bh = body.size
        for _ in range(14):
            cx, cy = rnd.uniform(0.06, 0.94) * bw, rnd.uniform(0.04, 0.96) * bh
            rx, ry = rnd.uniform(0.03, 0.10) * bw, rnd.uniform(0.02, 0.06) * bh
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=rnd.randint(45, 100))
        overlay = overlay.filter(ImageFilter.GaussianBlur(24))
        body = Image.composite(Image.new("RGB", body.size, (124, 124, 121)), body, overlay)

    img.paste(body, (0, top))
    img.save(jpg_path, "JPEG", quality=72, optimize=True)
    image_only_pdf(jpg_path, pdf_path)


def degrade_handwritten(case, jpg_path, pdf_path):
    """Manuscrito (letra de médico) fotografado com desfoque severo."""
    tmpjpg = tempfile.mktemp(suffix=".jpg")
    tmppdf = tempfile.mktemp(suffix=".pdf")
    make_handwritten(case, tmpjpg, tmppdf)
    with Image.open(tmpjpg) as im:
        img = im.convert("RGB")
    os.unlink(tmpjpg)
    os.unlink(tmppdf)
    # perde definição de verdade: reduz a resolução, desfoca e devolve ao tamanho
    w, h = img.size
    img = img.resize((int(w * 0.35), int(h * 0.35)), Image.BILINEAR)
    img = img.filter(ImageFilter.GaussianBlur(5.2))
    img = img.resize((w, h), Image.BICUBIC)
    img = ImageEnhance.Contrast(img).enhance(0.58)
    img = img.rotate(1.6, resample=Image.BICUBIC, expand=True, fillcolor=(250, 249, 244))
    img = ImageOps.expand(img, border=8, fill=(226, 226, 224))
    img.save(jpg_path, "JPEG", quality=72, optimize=True)
    image_only_pdf(jpg_path, pdf_path)


def make_handwritten(case, jpg_path, pdf_path):
    """Simula manuscrito: cada linha é desenhada com jitter e leve rotação."""
    random.seed(42)
    width, height = 1240, 1754
    img = Image.new("RGB", (width, height), (252, 251, 246))
    d = ImageDraw.Draw(img)

    from PIL import ImageFont
    font_big = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 34)
    font_label = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 19)
    font_body = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 30)

    d.text((70, 70), "HOSPITAL AURORA — UNIDADE DE DEMONSTRAÇÃO", font=font_big, fill=(25, 32, 42))
    d.text((70, 118), "Documento fictício — uso exclusivo em testes", font=font_label, fill=(150, 30, 25))
    d.line([(70, 150), (1170, 150)], fill=(160, 160, 158), width=2)
    d.text((70, 180), "RECEITUÁRIO MÉDICO — manuscrito", font=font_label, fill=(25, 32, 42))

    body_lines = [
        "Paciente: Vera Lúcia Santana      Idade: 61 anos",
        "Data: 18/10/2026      Documento: DOC-D-2026-0056",
        "",
        "Hipótese diagnóstica: Osteoartrite de joelhos — CID M17.9",
        "",
        "Prescrição:",
        "Paracetamol 750 mg ................ 1 comprimido",
        "por via oral a cada 8 horas, por 7 dias.",
        "",
        "Dra. Helena Prado",
        "CRM 187432-SP",
    ]

    y = 250
    for line in body_lines:
        if not line:
            y += 26
            continue
        # desenha cada palavra com um pequeno deslocamento vertical
        x = 80
        for word in line.split(" "):
            jitter = random.uniform(-2.4, 2.4)
            tmp = Image.new("RGBA", (700, 70), (0, 0, 0, 0))
            td = ImageDraw.Draw(tmp)
            td.text((6, 10 + jitter), word, font=font_body, fill=(28, 42, 78, 255))
            tmp = tmp.rotate(random.uniform(-0.9, 0.9), resample=Image.BICUBIC)
            img.paste(tmp, (int(x), int(y - 6)), tmp)
            x += td.textlength(word, font=font_body) + 12
        y += 52

    img = ImageOps.expand(img, border=10, fill=(228, 226, 220))
    img = img.rotate(-0.8, resample=Image.BICUBIC, expand=True, fillcolor=(250, 249, 244))
    img.save(jpg_path, "JPEG", quality=88, optimize=True)
    image_only_pdf(jpg_path, pdf_path)


def expected_json(case, base="catalogo"):
    e = case["exp"]
    out = {
        "fixture_id": case["id"],
        "documento_ficticio": True,
        "formatos_disponiveis": ["TXT", "PDF", "JPG"],
        "renditions": {
            "txt": f"{base}/{case['id']}/{case['id']}.txt",
            "pdf": f"{base}/{case['id']}/{case['id']}.pdf",
            "jpg": f"{base}/{case['id']}/{case['id']}.jpg",
        },
        "classificacao_esperada": {
            "tipo_documento": e["tipo"],
            "especialidade": e["esp"],
            "nivel_prioridade": e["prio"],
            "score_classificacao": (e.get("score") or {}).get("score_classificacao", ">= 0.85"),
        },
        "dados_esperados": e["dados"],
        "decisao_esperada": {
            "status": e["status"],
            "destinos": e["dest"],
            "requer_auditoria_humana": e["rev"],
            "notificacao": e["notif"],
        },
        "assercoes": e["ass"],
        "observacoes": e.get("obs", ""),
    }
    if e.get("conflitos"):
        out["conflitos_esperados"] = e["conflitos"]
    if e.get("score"):
        out["score_forcado"] = e["score"]
    return out


def expected_error_json(case):
    return {
        "fixture_id": case["id"],
        "documento_ficticio": True,
        "tipo_de_teste": "negativo_tecnico",
        "arquivo": case["arquivo"],
        "requisicao": "POST /api/v1/triagens",
        "erro_esperado": {
            "http": case["http"],
            "codigo_funcional": case["codigo"],
            "mensagem": case["desc"],
        },
        "assercoes": [
            case["aceita"],
            "Nenhuma inferência é executada para entrada inválida",
            "Mensagem de erro é segura, sem stack trace ou segredo",
        ],
        "observacoes": "O expected deste fixture é um envelope de erro, não um JSON de triagem.",
    }


def build_negative(case):
    d = os.path.join(OUT, case["id"])
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, case["arquivo"])
    kind = case["kind"]

    if kind == "docx":
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml",
                       '<?xml version="1.0" encoding="UTF-8"?>'
                       '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                       '<Default Extension="xml" ContentType="application/xml"/>'
                       '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                       '</Types>')
            z.writestr("_rels/.rels",
                       '<?xml version="1.0" encoding="UTF-8"?>'
                       '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                       '</Relationships>')
            z.writestr("word/document.xml",
                       '<?xml version="1.0" encoding="UTF-8"?>'
                       '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                       '<w:body><w:p><w:r><w:t>Receituário em DOCX — formato não suportado no MVP.</w:t></w:r></w:p></w:body>'
                       '</w:document>')
    elif kind == "empty":
        open(path, "wb").close()
    elif kind == "badjson":
        with open(path, "w", encoding="utf-8") as f:
            f.write('{\n  "tipo_arquivo": "TEXTO",\n  "documento_texto": "Paciente: teste",\n}\n')
    elif kind == "emptyenvelope":
        with open(path, "w", encoding="utf-8") as f:
            f.write("{}\n")
    elif kind == "multipart":
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "POST /api/v1/triagens HTTP/1.1\n"
                "Host: localhost:8000\n"
                "Content-Type: multipart/form-data; boundary=----MediFlowBoundary\n"
                "\n"
                "------MediFlowBoundary\n"
                "Content-Disposition: form-data; name=\"canal_origem\"\n"
                "\n"
                "Pronto_Socorro\n"
                "------MediFlowBoundary--\n"
                "\n"
                "# Nenhum arquivo e nenhum documento_texto foram enviados.\n"
                "# Esperado: 422 CAMPOS_INVALIDOS antes de qualquer chamada ao modelo.\n"
            )
    elif kind == "zip":
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("laudo.txt", "Conteúdo dentro de um ZIP — formato não suportado.")
    elif kind == "big":
        # 25 MB em PDF VÁLIDO: o conteúdo é uma página normal e o tamanho vem de um
        # comentário de preenchimento antes do %%EOF. Assim o único defeito é o
        # tamanho (413) e o arquivo ainda abre em qualquer leitor (e comprime no ZIP).
        from gerar_fixtures_demo import footer, header, watermark
        tmp = tempfile.mktemp(suffix=".pdf")
        cv = canvas.Canvas(tmp, pagesize=A4)
        cv.setTitle("Documento de teste de limite de tamanho (fictício)")
        hdr = {"id": "Validacao_ArquivoGrande", "title": "DOCUMENTO DE TESTE DE LIMITE DE TAMANHO"}
        watermark(cv)
        header(cv, hdr)
        footer(cv, hdr)
        y = H - 130
        cv.setFillColor(INK)
        cv.setFont("DejaVu-Bold", 16)
        cv.drawString(MARGIN, y, "Arquivo de 25 MB — teste de limite")
        y -= 22
        cv.setFont("DejaVu", 9.4)
        for ln in wrap("Este PDF é válido e legível. O único defeito é o tamanho: "
                       "25 MB, acima do limite configurado para o upload. O serviço deve "
                       "recusar pelo tamanho (413 ARQUIVO_MAIOR_QUE_LIMITE) antes de "
                       "qualquer inferência, sem baixar o conteúdo em memória.", "DejaVu", 9.4, CONTENT_W):
            cv.drawString(MARGIN, y, ln)
            y -= 13
        cv.showPage()
        cv.save()

        base = open(tmp, "rb").read()
        os.unlink(tmp)
        cut = base.rfind(b"%%EOF")
        pad = 25 * 1024 * 1024 - len(base)
        blob = (base[:cut] + b"% preenchimento de teste de tamanho - MediFlow\n%"
                + b"0" * max(pad, 0) + b"\n" + base[cut:])
        with open(path, "wb") as f:
            f.write(blob)
    elif kind == "fakemime":
        img = Image.new("RGB", (900, 1200), (250, 250, 248))
        d2 = ImageDraw.Draw(img)
        d2.rectangle([40, 40, 860, 120], fill=(180, 40, 32))
        d2.text((60, 62), "CONTEUDO REAL: PNG RENOMEADO PARA .PDF", fill=(255, 255, 255))
        img.save(path, "PNG")

    with open(os.path.join(d, "expected.json"), "w", encoding="utf-8") as f:
        json.dump(expected_error_json(case), f, ensure_ascii=False, indent=2)
    print(f"ok {case['id']}: {case['arquivo']} (negativo técnico)")


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for case in CASES:
        d = os.path.join(OUT, case["id"])
        os.makedirs(d, exist_ok=True)
        txt = os.path.join(d, f"{case['id']}.txt")
        pdf = os.path.join(d, f"{case['id']}.pdf")
        jpg = os.path.join(d, f"{case['id']}.jpg")
        flags = case["flags"]

        write_txt_case(case, txt)

        if flags.get("handwritten"):
            make_handwritten(case, jpg, pdf)
        elif flags.get("degrade_handwritten"):
            degrade_handwritten(case, jpg, pdf)
        elif flags.get("degrade"):
            draw_case_paged(case, pdf)
            degrade_strong(pdf, jpg)
        elif flags.get("corrupt"):
            draw_case_paged(case, pdf)
            size = os.path.getsize(pdf)
            with open(pdf, "rb") as f:
                data = f.read()
            with open(pdf, "wb") as f:
                f.write(data[: int(size * 0.4)])
            # jpg ilustrativo: renderiza o original antes de truncar
            tmp = tempfile.mktemp(suffix=".pdf")
            draw_case(case, tmp)
            rasterize(tmp, jpg, quality=80)
            os.unlink(tmp)
        elif flags.get("secure"):
            draw_case_paged(case, pdf)
            doc = fitz.open(pdf)
            doc.save(pdf + ".tmp", encryption=fitz.PDF_ENCRYPT_AES_256,
                     owner_pw="mediflow-owner", user_pw="mediflow123")
            doc.close()
            os.replace(pdf + ".tmp", pdf)
            # jpg ilustrativo (o PDF protegido não abre)
            tmp = tempfile.mktemp(suffix=".pdf")
            draw_case(case, tmp)
            rasterize(tmp, jpg, quality=80)
            os.unlink(tmp)
        elif flags.get("multipage"):
            draw_case_paged(case, pdf)
            rasterize(pdf, jpg, quality=86)
        elif flags.get("scan"):
            draw_case_paged(case, pdf)
            rasterize(pdf, jpg, rot=0.5, blur=0.5, contrast=0.94, quality=82)
            image_only_pdf(jpg, pdf)
            if flags.get("stamp"):
                draw_case_paged(case, pdf, stamp=True)
                rasterize(pdf, jpg, rot=0.4, blur=0.4, contrast=0.96, quality=84)
                image_only_pdf(jpg, pdf)
        elif flags.get("degrade_mild"):
            draw_case_paged(case, pdf)
            rasterize(pdf, jpg, rot=1.2, blur=1.9, contrast=0.82, quality=78)
            image_only_pdf(jpg, pdf)
        elif flags.get("rotate90"):
            draw_case_paged(case, pdf)
            rasterize(pdf, jpg, rotate90=True, rot=0, quality=84)
            image_only_pdf(jpg, pdf)
        elif flags.get("crop"):
            draw_case_paged(case, pdf)
            rasterize(pdf, jpg, rot=0.6, crop=(0.98, 0.42), quality=84)
            image_only_pdf(jpg, pdf)
        elif flags.get("low_contrast"):
            draw_case_paged(case, pdf)
            rasterize(pdf, jpg, rot=0.8, contrast=0.55, brightness=0.92, shadow=True, quality=76)
            image_only_pdf(jpg, pdf)
        else:
            draw_case_paged(case, pdf)
            rasterize(pdf, jpg, quality=86)

        with open(os.path.join(d, "expected.json"), "w", encoding="utf-8") as f:
            json.dump(expected_json(case), f, ensure_ascii=False, indent=2)
        total += 4
        print(f"ok {case['id']}: txt + pdf + jpg + expected.json")

    for vcase in V_CASES:
        build_negative(vcase)
        total += 2

    print(f"\n{len(CASES)} casos funcionais + {len(V_CASES)} negativos = {len(CASES) + len(V_CASES)} fixtures")
    print(f"{total} arquivos em {OUT}")


if __name__ == "__main__":
    main()
