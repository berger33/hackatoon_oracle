#!/usr/bin/env python3
"""Atualiza os dois PDFs de origem do MediFlow com as decisões registradas.

Rodada 1 (21/10/2026) - regra de urgência
    O `Projeto_oracle.pdf` prevalece sobre a EF v1.0: urgência isolada **não**
    gera revisão humana (vai para a fila urgente, com alerta, e termina em
    PROCESSADO). Revisão é consequência de ambiguidade.

Rodada 2 (21/10/2026) - decisões A1-A9 e bloco de consistência
    A1 conflito impeditivo = gravidade ALTA ou MÉDIA; BAIXA só registra.
    A2 dicionário clínico fechado (achados críticos, alto risco, conflitos).
    A3 fórmula determinística do score de extração.
    A4 prioridade NAO_IDENTIFICADA exige revisão.
    A5 urgência INDETERMINADA conta como campo incerto.
    A6 limites: 10 MB, 20 páginas, PDF/JPG/PNG/WEBP/TXT, 60 s, 2 retries.
    A7 metas numéricas fora do MVP; retenção até o fim do hackathon.
    A8 autenticação fora do MVP.
    A9 farmacopeia própria da equipe (PDF de consulta do modelo).
    Mais o bloco de consistência: anexo de decisões, exemplo do caso urgente,
    caminho `processados/urgentes/`, vocabulário e a tabela de roteamento.

O PDF tem layout fixo: cada edição remove o trecho antigo com redaction e
reinsere o texto novo na mesma posição, corpo e cor. O que não cabe no corpo do
texto vai para o Anexo A, referenciado no próprio trecho.

O texto novo é gravado em Helvetica, que tem exatamente as mesmas métricas do
Arial e da Liberation Sans dos originais - por isso nada se desloca. Helvetica
só cobre Latin-1: "•", "≥", "—", "“" e "”" não podem ser usados no texto novo
(o script recusa e avisa).

Uso:
    python3 tools/atualizar_pdfs.py              # gera em dist/
    python3 tools/atualizar_pdfs.py --simular    # mostra o plano, não altera nada
    python3 tools/atualizar_pdfs.py --verificar  # confere os PDFs gerados
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(ROOT, "dist")
UPLOADS = "/tmp/arena-coding-uploads"
DATA = "21/10/2026"

FONTES = {
    "ef": "MediFlow_Especificacao_Funcional_v1.0.pdf",
    "analise": "MediFlow_-_Análise_de_Requisitos_v1.1.pdf",
}


# --------------------------------------------------------------------- rodada 1
# Regra de urgência. Rect e ponto medidos no original.
EDICOES_URGENCIA = {
    "ef": [
        dict(pagina=5, rect=(303.6, 285.6, 534.0, 293.4), ponto=(303.6, 291.5),
             corpo=7.7, limite=533.5,
             novo="A análise terminou, mas encontrou ambiguidade, conflito,"),
        dict(pagina=9, rect=(303.0, 451.5, 358.5, 459.3), ponto=(303.6, 457.4),
             corpo=7.7, limite=357.6,
             novo="Não"),
        dict(pagina=9, rect=(94.45, 240.0, 532.0, 250.0), ponto=(94.45, 247.17),
             corpo=9.3, limite=531.72,
             novo="sem ambiguidade/conflito impeditivo ou score abaixo do limiar, "
                  "encaminhar automaticamente ao"),
        dict(pagina=9, rect=(66.5, 253.6, 532.0, 263.0), ponto=(66.86, 260.67),
             corpo=9.3, limite=531.72,
             novo="destino de rotina do tipo; com urgência, à fila urgente e com alerta."),
        dict(pagina=13, rect=(56.5, 628.3, 527.0, 637.6), ponto=(56.9, 635.37),
             corpo=9.3, limite=526.16,
             novo="1. Urgência: encaminhar à fila urgente e registrar alerta simulado; "
                  "com ambiguidade,"),
        dict(pagina=13, rect=(70.5, 641.8, 527.0, 651.1), ponto=(70.9, 648.9),
             corpo=9.3, limite=526.16,
             novo="incluir também na fila lógica de revisão. Urgência isolada termina "
                  "como processada, sem revisão humana."),
    ],
    "analise": [
        dict(pagina=5, rect=(124.7, 192.7, 524.0, 201.2), ponto=(125.06, 199.15),
             corpo=8.5, limite=523.26,
             novo="Casos padrão (sem ambiguidade e com nota combinada de 0.85 ou mais) "
                  "seguem direto ao destino,"),
        dict(pagina=7, rect=(198.4, 516.5, 240.0, 525.0), ponto=(198.8, 523.0),
             corpo=8.5, limite=266.8,
             novo="Decidido"),
        dict(pagina=7, rect=(266.4, 516.5, 523.0, 525.0), ponto=(266.8, 523.0),
             corpo=8.5, limite=522.7,
             novo="Urgência prevalece: alerta sempre; revisão só com ambiguidade."),
    ],
}


# --------------------------------------------------------------------- rodada 2
# `rect` é a área apagada; `linhas` é a lista de (x, y, texto). `corpo` e
# `limite` servem à conferência de largura. `obs` documenta a decisão aplicada.
EDICOES_DECISOES = {
    "ef": [
        # §4 - A8
        dict(obs="§4 autenticação fora do MVP", pagina=4, corpo=9.3, limite=533.5,
             rect=(53.5, 580.8, 533.5, 616.0),
             linhas=[(53.9, 588.07, "Decisão registrada: autenticação, autorização por papel e identificação do auditor estão fora do"),
                     (53.9, 601.57, "MVP. A aplicação roda em demonstração local, sem controle de acesso; qualquer exposição pública"),
                     (53.9, 615.07, "exige autenticação antes (§10.1).")]),
        # §5.3 - B5
        dict(obs="§5.3 EM_REVISAO com ilegibilidade e conflito impeditivo",
             pagina=5, corpo=7.7, limite=533.5,
             rect=(303.2, 282.7, 533.5, 324.2),
             linhas=[(303.6, 291.50, "A análise terminou, mas encontrou ambiguidade,"),
                     (303.6, 301.67, "ilegibilidade, conflito impeditivo, score"),
                     (303.6, 311.87, "abaixo do limite ou ausência de campo"),
                     (303.6, 322.07, "obrigatório. Entra na fila lógica; no MVP, sem")]),
        # RF-11 - A9
        dict(obs="RF-11 farmacopeia própria da equipe", pagina=7, corpo=9.3, limite=533.5,
             rect=(53.5, 204.9, 533.5, 216.0),
             linhas=[(53.9, 212.17, "ara validar nome e dosagem. A farmacopeia é a da equipe (PDF de consulta"),
                     (53.9, 224.17, "do modelo, Anexo A.2); sem o arquivo, vale a regra de dose suspeita de RF-16.")]),
        # RF-13 - A5
        dict(obs="RF-13 urgência INDETERMINADA exige revisão", pagina=7, corpo=9.3, limite=533.5,
             rect=(53.5, 318.8, 533.5, 340.2),
             linhas=[(53.9, 326.17, "Não declarar nao se o documento estiver ilegível ou a análise não tiver sido concluída; nesse"),
                     (53.9, 339.67, "caso usar indeterminado. Urgência INDETERMINADA conta como campo incerto e exige revisão")]),
        # RF-16 - A1/A2
        dict(obs="RF-16 conflito impeditivo = ALTA ou MÉDIA; dicionário no anexo",
             pagina=7, corpo=9.3, limite=533.5,
             rect=(53.5, 557.4, 545.0, 578.9),
             linhas=[(53.9, 564.67, "(sem alterar dose), campos contraditórios e discrepância entre prioridade e sinais textuais."),
                     (53.9, 578.17, "Regras aprovadas: conflito impeditivo é o de gravidade ALTA ou MÉDIA; BAIXA só registra."),
                     (53.9, 591.17, "Dicionário clínico fechado (achado crítico, alto risco e conflitos): Anexo A.2.")]),
        # RF-18 - A3
        dict(obs="RF-18 fórmula determinística do score de extração", pagina=7, corpo=9.3, limite=533.5,
             rect=(53.5, 684.8, 533.5, 719.8),
             linhas=[(53.9, 692.17, "0.85, vindo de variável de configuração. A fórmula aprovada é min(score_confianca_classificacao,"),
                     (53.9, 705.67, "score_extracao). O score_extracao é determinístico: parte de 1 e subtrai 0,2 por campo obrigatório"),
                     (53.9, 719.17, "ausente, 0,1 por campo incerto e 0,3/0,2/0,1 por conflito ALTA/MÉDIA/BAIXA, com piso 0 (Anexo"),
                     (53.9, 732.67, "A.4). Comparação: combinado < limiar envia para revisão; combinado >= limiar apenas permite"),
                     (53.9, 746.17, "fluxo automático se nenhuma outra regra exigir revisão/urgência. O limiar padrão é 0.85.")]),
        # §9.2 - B4
        dict(obs="§9.2 ponteiro para o exemplo do caso urgente", pagina=10, corpo=9.3, limite=533.5,
             rect=(53.5, 661.9, 545.0, 696.7),
             linhas=[(53.9, 669.17, "Exemplo ilustrativo de contrato, não define dados reais nem confirma decisões pendentes."),
                     (53.9, 682.67, "Valores clínicos devem vir do documento fictício da demonstração. O exemplo do projeto usa"),
                     (53.9, 696.17, "cid_sugerido; este contrato evita misturar sugestão com extração até validação. O caso"),
                     (53.9, 708.67, "urgente sem ambiguidade, que é o exemplo do Projeto_oracle.pdf, está no Anexo A.3.")]),
        # §10.1 - A8
        dict(obs="§10.1 401/403 fora do MVP", pagina=11, corpo=7.7, limite=535.5,
             rect=(384.5, 486.0, 535.5, 504.2),
             linhas=[(384.9, 492.07, "Fora do MVP: sem autenticação"),
                     (384.9, 502.27, "na demonstração local.")]),
        # §12 - A6
        dict(obs="§12 limites operacionais registrados", pagina=12, corpo=9.3, limite=533.5,
             rect=(53.5, 623.5, 533.5, 644.8),
             linhas=[(53.9, 630.77, "Limites registrados: 10 MB por arquivo, até 20 páginas, extensões PDF/JPG/PNG/WEBP/TXT;"),
                     (53.9, 644.27, "timeout de 60 s na chamada ao Gemini; 2 retentativas com backoff exponencial. São variáveis"),
                     (53.9, 657.77, "operacionais, não regras clínicas.")]),
        # §13 - B3
        dict(obs="§13 caminho dos casos urgentes", pagina=12, corpo=9.3, limite=528.4,
             rect=(63.5, 707.5, 528.4, 742.4),
             linhas=[(63.74, 714.87, "Proposta de organização por prefixo: recebidos/{ano}/{mes}/{documento_id}/original,"),
                     (66.9, 728.37, "processados/{ano}/{mes}/{documento_id}/resultado.json, processados/urgentes/{documento_id}.json"),
                     (66.9, 741.87, "para urgências e auditoria/.../resultado.json. Buckets separados mantêm o significado.")]),
        # §13 - A7
        dict(obs="§13 retenção registrada", pagina=13, corpo=9.3, limite=528.4,
             rect=(63.5, 103.5, 528.4, 125.0),
             linhas=[(63.74, 110.77, "Política registrada: dados fictícios e históricos ficam até o fim do hackathon e são excluídos"),
                     (66.9, 124.27, "ao término. Nenhum dado real entra no MVP (RNF-08 e Anexo A.7).")]),
        # §14 - A7 (RNF-01)
        dict(obs="§14 RNF-01 sem meta numérica", pagina=13, corpo=7.7, limite=533.5,
             rect=(384.5, 212.4, 533.5, 251.0),
             linhas=[(384.9, 218.67, "Casos de demonstração com resultado"),
                     (384.9, 228.67, "esperado aprovado pela equipe (conjunto"),
                     (384.9, 238.87, "de casos aprovados). Sem meta"),
                     (384.9, 249.07, "numérica no MVP.")]),
        # §14 - A7 (RNF-07)
        dict(obs="§14 RNF-07 sem meta numérica", pagina=13, corpo=7.7, limite=535.1,
             rect=(384.5, 415.2, 535.5, 433.4),
             linhas=[(384.9, 421.27, "Medir latência por etapa no primeiro"),
                     (384.9, 431.47, "pipeline; sem meta numérica no MVP.")]),
        # §15 - A6 a A9: de "definições restantes" para "decisões registradas"
        dict(obs="§15 título", pagina=14, corpo=9.3, limite=533.5,
             rect=(53.5, 138.9, 533.5, 148.6),
             linhas=[(53.9, 146.17, "Definições registradas pela equipe (todas fechadas nesta versão):")]),
        dict(obs="§15 limites", pagina=14, corpo=9.3, limite=528.4,
             rect=(63.5, 157.4, 528.4, 167.1),
             linhas=[(63.74, 164.67, "Limites: 10 MB por arquivo, até 20 páginas, extensões PDF/JPG/PNG/WEBP/TXT, timeout de 60 s e"),
                     (66.9, 176.67, "2 retentativas com backoff exponencial (§12).")]),
        dict(obs="§15 upload", pagina=14, corpo=9.3, limite=528.4,
             rect=(63.5, 174.5, 528.4, 184.2),
             linhas=[(63.74, 191.67, "Upload: multipart/form-data para arquivo e JSON textual para texto (§9.1).")]),
        dict(obs="§15 dicionário", pagina=14, corpo=9.3, limite=528.4,
             rect=(63.5, 191.6, 528.4, 212.9),
             linhas=[(63.74, 206.67, "Dicionário clínico fechado (achado crítico, medicamento de alto risco e conflitos):"),
                     (66.9, 218.67, "Anexo A.2. Fonte: farmacopeia própria da equipe; responsável: time clínico do G10.")]),
        dict(obs="§15 autenticação", pagina=14, corpo=9.3, limite=528.4,
             rect=(63.5, 222.2, 528.4, 231.9),
             linhas=[(63.74, 233.67, "Autenticação: fora do MVP; expor publicamente exige autenticação antes (§4 e §10.1).")]),
        dict(obs="§15 retenção", pagina=14, corpo=9.3, limite=528.4,
             rect=(63.5, 239.3, 528.4, 249.0),
             linhas=[(63.74, 248.67, "Retenção: dados fictícios e históricos até o fim do hackathon; exclusão ao término (§13).")]),
        dict(obs="§15 metas", pagina=14, corpo=9.3, limite=528.4,
             rect=(63.5, 256.4, 528.4, 266.1),
             linhas=[(63.74, 263.67, "Metas numéricas: fora do MVP; aceite pelos casos aprovados e latência por etapa (§14).")]),
    ],
    "analise": [
        # RF-02 - B6
        dict(obs="RF-02 JSON é envelope", pagina=3, corpo=8.5, limite=483.8,
             rect=(124.7, 166.5, 483.8, 175.5),
             linhas=[(125.1, 172.70, "Aceitar PDF (digital e digitalizado), imagem e texto; JSON é o envelope da requisição.")]),
        # RN-02 - A4/A5
        dict(obs="RN-02 prioridade/urgência indeterminadas", pagina=5, corpo=8.5, limite=483.8,
             rect=(124.7, 225.5, 483.8, 246.0),
             linhas=[(125.1, 232.20, "Documento ambíguo, ilegível, inconsistente, com prioridade ou urgência"),
                     (125.1, 243.70, "indeterminada, ou com nota combinada < 0.85 (limiar padrão) vai obrigatoriamente para a"),
                     (125.1, 255.00, "Fila de Revisão Humana.")]),
        # Roteamento proposto - B2 (linha nova abaixo da tabela, sem apagar nada)
        dict(obs="Roteamento: caso das duas filas", pagina=5, corpo=8.5, limite=533.5,
             rect=None,
             linhas=[(57.0, 527.00, "Urgência com ambiguidade: o caso vai para as duas filas e gera alerta (EF §8.2 e §15).")]),
        # §8 - B6
        dict(obs="§8 status em maiúsculas", pagina=6, corpo=8.5, limite=537.5,
             rect=(175.7, 94.2, 403.3, 103.0),
             linhas=[(176.1, 100.40, "Situação do processamento (ex.: PROCESSADO, EM_REVISAO)")]),
        # §12 - B1/A4/A7
        dict(obs="§12 fórmula - situação", pagina=7, corpo=8.5, limite=233.2,
             rect=(198.4, 468.8, 240.0, 480.5),
             linhas=[(198.8, 478.50, "Decidido")]),
        dict(obs="§12 fórmula - detalhe", pagina=7, corpo=8.5, limite=522.4,
             rect=(266.4, 468.8, 522.4, 504.0),
             linhas=[(266.8, 478.50, "Decidido: mínimo entre a nota de"),
                     (266.8, 490.00, "classificação e a de extração (EF §15.4).")]),
        dict(obs="§12 prioridade - situação", pagina=7, corpo=8.5, limite=233.2,
             rect=(198.4, 546.3, 240.0, 558.0),
             linhas=[(198.8, 556.00, "Decidido")]),
        dict(obs="§12 prioridade - detalhe", pagina=7, corpo=8.5, limite=522.4,
             rect=(266.4, 546.3, 522.4, 559.8),
             # a linha desta célula só cabe uma vez: a regra da indeterminada
             # fica na RN-02 (§7) e no anexo, e não invade a linha de baixo
             linhas=[(266.8, 556.00, "URGENTE, ROTINA e NAO_IDENTIFICADA (EF §5.2).")]),
        dict(obs="§12 tempo-alvo - situação", pagina=7, corpo=8.5, limite=233.2,
             rect=(198.4, 567.8, 240.0, 579.5),
             linhas=[(198.8, 577.50, "Decidido")]),
        dict(obs="§12 tempo-alvo - detalhe", pagina=7, corpo=8.5, limite=522.4,
             rect=(266.4, 567.8, 522.4, 592.5),
             linhas=[(266.8, 577.50, "Sem meta numérica no MVP: latência"),
                     (266.8, 588.50, "medida por etapa no primeiro pipeline."),
                     (266.8, 599.50, "Aceite pelo conjunto de casos aprovados.")]),
    ],
}


# ----------------------------------------------------------------------- anexos
ANEXO_EF = [
    ("t", "Anexo A - Decisões registradas em %s" % DATA),
    ("p", "Este anexo fecha as definições que a versão 1.0 deixou em aberto e registra as decisões "
          "tomadas pela equipe. Ele tem força de especificação: onde o corpo do texto e este anexo "
          "divergirem, vale o anexo, que é posterior."),
    ("s", "A.1 Urgência (substitui a leitura anterior de §5.3, §8.1 e §8.2)"),
    ("p", "Urgência isolada não gera revisão humana: o caso vai para FILA_URGENCIA_MEDICA, registra "
          "alerta simulado e termina em PROCESSADO, com requer_auditoria_humana = false. É o "
          "comportamento do exemplo do Projeto_oracle.pdf. Revisão humana é consequência de "
          "ambiguidade. Com urgência e ambiguidade juntas, valem os dois destinos e o caso termina "
          "em EM_REVISAO."),
    ("s", "A.2 Dicionário clínico fechado (decisões A1, A2 e A9)"),
    ("p", "Fonte: equipe clínica do G10 e farmacopeia própria da equipe. Responsável pela aprovação: "
          "time clínico, com registro no repositório. O sistema não inventa tabela clínica."),
    ("i", "- Conflitos reconhecidos: CID_DIAGNOSTICO (ALTA), CONTRADICAO_INTERNA (ALTA), "
          "DOSE_SUSPEITA (MÉDIA), PRIORIDADE_TEXTO (MÉDIA)."),
    ("i", "- Conflito impeditivo é o de gravidade ALTA ou MÉDIA: exige revisão humana. Gravidade "
          "BAIXA é registrada e não bloqueia o fluxo."),
    ("i", "- Achados críticos (disparam urgência): TEP agudo, IAM, AVC agudo, sepse e hemorragia ativa."),
    ("i", "- Medicamentos de alto risco: anticoagulantes, opioides, insulinas e quimioterápicos."),
    ("i", "- Farmacopeia: PDF próprio da equipe, usado como base de consulta do modelo (RF-11). Até o "
          "arquivo estar disponível, vale a regra de dose suspeita de RF-16."),
    ("s", "A.3 Exemplo de resposta: caso urgente sem ambiguidade (exemplo do Projeto_oracle.pdf)"),
    ("c", '{ "status": "PROCESSADO",'),
    ("c", '  "documento_id": "DOC-CLIN-2026-8942",'),
    ("c", '  "classificacao": { "tipo_documento": "LAUDO_EXAME_IMAGEM",'),
    ("c", '                     "especialidade": ["Radiologia", "Pneumologia"],'),
    ("c", '                     "nivel_prioridade": "URGENTE",'),
    ("c", '                     "score_classificacao": 0.99 },'),
    ("c", '  "dados_extraidos": { "paciente": { "nome": "Carlos Eduardo Mendes", "idade": 52 },'),
    ("c", '                       "medico": { "nome": "Dra. Renata Silveira",'),
    ("c", '                                   "crm": { "numero": "145892", "uf": "SP" } },'),
    ("c", '                       "diagnostico": "Tromboembolismo pulmonar agudo",'),
    ("c", '                       "cid": null, "medicamentos": [],'),
    ("c", '                       "exames": ["Tomografia de tórax com contraste"],'),
    ("c", '                       "urgencia": "SIM" },'),
    ("c", '  "qualidade": { "score_extracao": 0.91, "score_combinado": 0.91,'),
    ("c", '                 "limiar_aplicado": 0.85, "campos_ausentes": [],'),
    ("c", '                 "campos_incertos": [], "conflitos": [] },'),
    ("c", '  "decisao_roteamento": { "destino_principal": "FILA_URGENCIA_MEDICA",'),
    ("c", '                          "destinos": ["FILA_URGENCIA_MEDICA"],'),
    ("c", '                          "requer_auditoria_humana": false,'),
    ("c", '                          "notificacao": { "gerada": true,'),
    ("c", '                                           "canal": "SIMULADO_SLACK_PLANTAO",'),
    ("c", '                                           "status": "REGISTRADA" } },'),
    ("c", '  "armazenamento_oci": { "bucket": "mediflow-documentos-clinicos",'),
    ("c", '                         "caminho_objeto": "processados/urgentes/DOC-CLIN-2026-8942.json",'),
    ("c", '                         "status_backup": "sucesso" } }'),
    ("s", "A.4 Score de extração: fórmula determinística (decisão A3)"),
    ("p", "score_extracao começa em 1 e subtrai 0,2 por campo obrigatório ausente, 0,1 por campo "
          "incerto e 0,3 (ALTA), 0,2 (MÉDIA) ou 0,1 (BAIXA) por conflito; piso 0 e teto 1. "
          "score_combinado = min(score_classificacao, score_extracao) (§15.4). Limiar 0,85: abaixo "
          "revisa; igual ao limiar passa."),
    ("s", "A.5 Limites operacionais e retries (decisão A6)"),
    ("p", "10 MB por arquivo; até 20 páginas; PDF, JPG, PNG, WEBP e TXT; timeout de 60 s na chamada "
          "ao Gemini; 2 retentativas com backoff exponencial. Upload: multipart/form-data para "
          "arquivo e JSON textual para texto."),
    ("s", "A.6 Prioridade e urgência indeterminadas (decisões A4 e A5)"),
    ("p", "nivel_prioridade = NAO_IDENTIFICADA e urgencia = INDETERMINADO contam como ambiguidade e "
          "levam o caso à FILA_REVISAO_HUMANA (§5.2, RF-13 e RN-02 da Análise de Requisitos v1.1)."),
    ("s", "A.7 Fora do MVP (decisões A7 e A8)"),
    ("i", "- Autenticação e autorização: aplicação local de demonstração, sem controle de acesso; "
          "expor publicamente exige autenticação antes."),
    ("i", "- Metas numéricas de precisão e latência: o aceite é o conjunto de casos aprovados; a "
          "latência é medida por etapa, sem meta."),
    ("i", "- Retenção: dados fictícios e históricos ficam até o fim do hackathon e são excluídos ao "
          "término; nenhum dado real entra no MVP."),
]

ANEXO_ANALISE = [
    ("t", "Anexo - Decisões registradas em %s" % DATA),
    ("p", "As linhas que estavam como \"A definir\" na seção 12 foram fechadas nesta versão, junto "
          "com a regra de urgência. O detalhamento de cada decisão está no Anexo A da Especificação "
          "Funcional v1.0."),
    ("i", "- Urgência: vai para a Fila de Urgência Médica com alerta e não gera revisão humana por "
          "si só. Revisão é consequência de ambiguidade."),
    ("i", "- Urgência com ambiguidade: o caso vai para as duas filas (Urgência Médica e Revisão "
          "Humana) e gera alerta."),
    ("i", "- Fórmula da nota combinada: mínimo entre a nota de classificação e a de extração."),
    ("i", "- Níveis de prioridade: URGENTE, ROTINA e NAO_IDENTIFICADA. Prioridade ou urgência "
          "indeterminadas levam à revisão humana."),
    ("i", "- Tempo-alvo: sem meta numérica no MVP; a latência é medida por etapa e o aceite é o "
          "conjunto de casos aprovados."),
    ("i", "- Conflito impeditivo é o de gravidade ALTA ou MÉDIA; gravidade BAIXA é registrada e não "
          "bloqueia. Dicionário clínico fechado no Anexo A.2 da EF."),
    ("i", "- Vocabulário: status em maiúsculas (PROCESSADO, EM_REVISAO) e JSON como envelope da "
          "requisição, não como formato de documento."),
]

# tipo: (corpo, entrelinha [fator], espaço depois [pontos])
ESTILOS = {"t": (12.0, 1.25, 16.0), "s": (9.5, 1.30, 6.0), "p": (8.5, 1.35, 10.0),
           "i": (8.5, 1.32, 4.0), "c": (7.0, 1.25, 0.0)}


# --------------------------------------------------------------------- utilitários
def largura(texto: str, corpo: float) -> float:
    return pymupdf.get_text_length(texto, fontname="helv", fontsize=corpo)


def problema_caracteres(texto: str) -> list[str]:
    return sorted({c for c in texto if ord(c) > 255})


def conferir(chave: str) -> list[str]:
    """Valida todas as edições antes de tocar no PDF."""
    problemas = []
    for ed in EDICOES_URGENCIA[chave]:
        if problema_caracteres(ed["novo"]):
            problemas.append(f"p{ed['pagina']}: {problema_caracteres(ed['novo'])} fora do Latin-1")
    for ed in EDICOES_DECISOES[chave]:
        for x, y, texto in ed["linhas"]:
            fora = problema_caracteres(texto)
            if fora:
                problemas.append(f"p{ed['pagina']} {ed['obs']}: {fora} fora do Latin-1")
            if x + largura(texto, ed["corpo"]) > ed["limite"]:
                problemas.append(
                    f"p{ed['pagina']} {ed['obs']}: linha com "
                    f"{largura(texto, ed['corpo']):.1f}pt, só há "
                    f"{ed['limite'] - x:.1f}pt -> {texto[:45]!r}")
    return problemas


def aplicar_rodada1(caminho: str, chave: str) -> None:
    doc = pymupdf.open(caminho)
    for ed in EDICOES_URGENCIA[chave]:
        page = doc[ed["pagina"] - 1]
        page.add_redact_annot(pymupdf.Rect(*ed["rect"]))
        page.apply_redactions(graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        page.insert_text(pymupdf.Point(*ed["ponto"]), ed["novo"],
                         fontname="helv", fontsize=ed["corpo"], color=(0, 0, 0))
    tmp = caminho + ".tmp"
    doc.save(tmp, garbage=4, deflate=True)
    doc.close()
    os.replace(tmp, caminho)


def aplicar_rodada2(doc: pymupdf.Document, chave: str, simular: bool,
                    saida=print) -> None:
    for ed in EDICOES_DECISOES[chave]:
        page = doc[ed["pagina"] - 1]
        if ed["rect"] is not None:
            if simular:
                texto_antigo = page.get_textbox(pymupdf.Rect(*ed["rect"])).strip()
                saida(f"   p{ed['pagina']} [{ed['obs']}]")
                saida(f"      sai : {' / '.join(l for l in texto_antigo.splitlines() if l.strip())[:150]}")
            else:
                page.add_redact_annot(pymupdf.Rect(*ed["rect"]))
                page.apply_redactions(graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        for x, y, texto in ed["linhas"]:
            if simular:
                saida(f"      entra: {texto[:150]}")
            else:
                page.insert_text(pymupdf.Point(x, y), texto, fontname="helv",
                                 fontsize=ed["corpo"], color=(0, 0, 0))


def escrever_anexo(doc: pymupdf.Document, itens, primeira: int, fonte=None,
                   pagina_fonte: int = 1, x0=53.9, x1=533.5,
                   topo=395.0, base=790.0) -> int:
    """Escreve o anexo a partir da página `primeira`, criando páginas novas se
    precisar. Devolve o número da última página usada."""
    pagina = primeira
    y = topo
    for tipo, texto in itens:
        corpo, entrelinha, depois = ESTILOS[tipo]
        while True:
            page = doc[pagina]
            rect = pymupdf.Rect(x0, y, x1, base)
            usado = page.insert_textbox(rect, texto, fontname="helv", fontsize=corpo,
                                        lineheight=entrelinha, color=(0, 0, 0),
                                        align=pymupdf.TEXT_ALIGN_LEFT)
            if usado >= 0 or y <= 60:          # coube (ou já está no topo da página)
                y = base - usado + depois
                break
            pagina = nova_pagina(doc, pagina, fonte, pagina_fonte)
            y = 60.0
        if y > base - 20:
            pagina = nova_pagina(doc, pagina, fonte, pagina_fonte)
            y = 60.0
    return pagina


def nova_pagina(doc: pymupdf.Document, depois_de: int, fonte: pymupdf.Document,
                pagina_fonte: int = 1, cabecalho: bool = True) -> int:
    """Cria uma página nova, replicando o cabeçalho e o rodapé da anterior.

    A réplica é feita desenhando a faixa do original como objeto vetorial
    (`show_pdf_page`), e não reescrevendo o texto: assim o cabeçalho mantém a
    fonte original, inclusive o "•" que a Helvetica não tem. O PyMuPDF não
    aceita o próprio documento como origem, daí o `fonte` separado.
    """
    modelo = doc[depois_de]
    largura, altura = modelo.rect.width, modelo.rect.height
    modelo = None                        # a estrutura muda abaixo: objeto inválido
    indice = doc.new_page(depois_de + 1, width=largura, height=altura).number
    page = doc[indice]
    if cabecalho:
        page.show_pdf_page(pymupdf.Rect(0, 0, largura, 50), fonte, pagina_fonte,
                           clip=pymupdf.Rect(0, 0, largura, 50))
    page.show_pdf_page(pymupdf.Rect(0, 780, largura, altura), fonte, pagina_fonte,
                       clip=pymupdf.Rect(0, 780, largura, altura))
    return indice


def atualizar_rodape(doc: pymupdf.Document, chave: str) -> None:
    """Numera as páginas novas (o rodapé copiado repete o número da anterior)."""
    total = doc.page_count
    for i in range(total):
        page = doc[i]
        for bl in page.get_text("dict")["blocks"]:
            for ln in bl.get("lines", []):
                for sp in ln["spans"]:
                    if sp["text"].startswith("Página"):
                        page.add_redact_annot(pymupdf.Rect(*sp["bbox"]))
                        page.apply_redactions(graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
                        page.insert_text(pymupdf.Point(sp["origin"][0], sp["origin"][1]),
                                         f"Página {i + 1} de {total}" if chave == "analise"
                                         else f"Página {i + 1}",
                                         fontname="helv", fontsize=sp["size"], color=(0, 0, 0))


# ------------------------------------------------------------------------- fluxo
def processar(chave: str, nome: str, simular: bool) -> tuple[int, list[str]]:
    origem = os.path.join(ROOT, nome)
    if not os.path.exists(origem):
        origem = os.path.join(UPLOADS, nome)
    destino = os.path.join(SAIDA, nome)

    problemas = conferir(chave)
    if simular:
        print(f"\n===== {nome} (simulação)")
        for p in problemas:
            print("   [PROBLEMA]", p)
        doc = pymupdf.open(origem)
        aplicar_rodada2(doc, chave, True)
        doc.close()
        return 0, problemas

    if problemas:
        return 0, problemas

    shutil.copyfile(origem, destino)
    aplicar_rodada1(destino, chave)
    doc = pymupdf.open(destino)
    aplicar_rodada2(doc, chave, False)
    fonte = pymupdf.open(origem)   # cabeçalho/rodapé originais, para as páginas novas
    if chave == "ef":
        # a última página tem espaço livre depois das referências
        ultima = escrever_anexo(doc, ANEXO_EF, primeira=doc.page_count - 1,
                                fonte=fonte, pagina_fonte=1, topo=395.0)
    else:
        # a última página está cheia e a Análise não tem cabeçalho corrente (na
        # faixa de cima há texto de seção): o anexo entra numa página nova, só
        # com o rodapé replicado
        ultima = escrever_anexo(doc, ANEXO_ANALISE,
                                primeira=nova_pagina(doc, doc.page_count - 1,
                                                     fonte, 1, cabecalho=False),
                                fonte=fonte, pagina_fonte=1, topo=60.0)
    fonte.close()
    atualizar_rodape(doc, chave)
    paginas = doc.page_count
    tmp = destino + ".tmp"
    doc.save(tmp, garbage=4, deflate=True)
    doc.close()
    os.replace(tmp, destino)
    print(f"   {nome}: {len(EDICOES_URGENCIA[chave])} + "
          f"{len(EDICOES_DECISOES[chave])} edições, anexo até a página {ultima + 1}, "
          f"{paginas} páginas")
    return 0, []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simular", action="store_true",
                    help="mostra o plano sem alterar nada")
    ap.add_argument("--verificar", action="store_true", help="confere os PDFs gerados")
    args = ap.parse_args()

    os.makedirs(SAIDA, exist_ok=True)
    if args.verificar:
        return verificar()
    if args.simular:
        for chave, nome in FONTES.items():
            processar(chave, nome, True)
        return 0

    problemas = []
    for chave, nome in FONTES.items():
        _, p = processar(chave, nome, False)
        problemas += [f"{nome}: {x}" for x in p]
    for p in problemas:
        print("[PROBLEMA]", p)
    return 1 if problemas else 0


def verificar() -> int:
    """Confere frases que precisam existir (e as que não podem mais existir)."""
    esperado = {
        "ef": dict(
            presente=["A análise terminou, mas encontrou ambiguidade,",
                      "ilegibilidade, conflito impeditivo, score",
                      "destino de rotina do tipo; com urgência, à fila urgente e com alerta.",
                      "Urgência isolada termina como processada, sem revisão humana.",
                      "Regras aprovadas: conflito impeditivo é o de gravidade ALTA ou MÉDIA",
                      "O score_extracao é determinístico",
                      "processados/urgentes/{documento_id}.json",
                      "Definições registradas pela equipe",
                      "Anexo A - Decisões registradas em " + DATA,
                      "score_extracao começa em 1 e subtrai 0,2 por campo obrigatório ausente"],
            ausente=["Limites/retries/timeouts concretos são variáveis operacionais a definir",
                     "Meta numérica pendente",
                     "quando autenticação/autorização for",
                     "Definições restantes para a equipe"],
            contagem={"A definir": 0}),
        "analise": dict(
            presente=["Decidido: mínimo entre a nota de",
                      "URGENTE, ROTINA e NAO_IDENTIFICADA.",
                      "Sem meta numérica no MVP: latência",
                      "Urgência com ambiguidade: o caso vai para as duas filas",
                      "prioridade ou urgência",
                      "Anexo - Decisões registradas em " + DATA],
            ausente=["Sugestão inicial: usar a menor",
                     "No mínimo “Urgente” e “Rotina”."],
            contagem={"A definir": 0}),
    }
    # o texto "A definir" também aparece citado no anexo: a contagem vale só
    # para o corpo do documento, antes da página do anexo.
    INICIO_ANEXO = {"ef": 14, "analise": 6}
    ok = True
    for chave, nome in FONTES.items():
        caminho = os.path.join(SAIDA, nome)
        if not os.path.exists(caminho):
            print(f"[ERRO] falta {caminho}")
            ok = False
            continue
        doc = pymupdf.open(caminho)
        texto = "\n".join(p.get_text() for p in doc)
        corpo = "".join(doc[i].get_text() for i in range(INICIO_ANEXO[chave]))
        paginas = doc.page_count
        doc.close()
        problemas = []
        for f in esperado[chave]["presente"]:
            if f not in texto:
                problemas.append(f"não encontrado: {f!r}")
        for f in esperado[chave]["ausente"]:
            if f in texto:
                problemas.append(f"ainda existe: {f!r}")
        for f, n in esperado[chave]["contagem"].items():
            if corpo.count(f) != n:
                problemas.append(f"{f!r} aparece {corpo.count(f)}x no corpo, esperado {n}")
        ok = ok and not problemas
        print(f"{nome} ({paginas} páginas): {'OK' if not problemas else 'PROBLEMAS'}")
        for p in problemas:
            print("   -", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
