#!/usr/bin/env python3
"""Gera a EPT (Especificação de Procedimento de Teste) do MediFlow em CSV.

Fonte de verdade: `MediFlow_Especificacao_Funcional_v1.0.pdf` (RF-01..RF-30,
RN-01..RN-07, RNF-01..RNF-11, §8.2, §10, §11, §12, §16) + os 67 fixtures de
`tests/fixtures/manifest.csv`.

Saídas:
  docs/testes/EPT_MediFlow_v1.0.csv   → EPT executável (uma linha por caso)
  docs/testes/EPT_MediFlow_GUIA_E_COBERTURA.md
                                      → dicionário de dados + cobertura
                                        requisito × caso × massa

Formato do CSV (o que abre bem no Excel pt-BR):
  - separador `;`
  - UTF-8 com BOM (Excel não corrompe acento)
  - CRLF (padrão de planilha)
  - uma linha por caso, sem quebras de linha dentro da célula
  - campos com `;`, aspas ou vírgula sempre entre aspas

Uso:
    python3 tools/gerar_ept.py            # gera CSV + guia
    python3 tools/gerar_ept.py --check    # só valida a cobertura e sai != 0 se faltar
"""
from __future__ import annotations

import csv
import fnmatch
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_CSV = os.path.join(ROOT, "docs/testes/EPT_MediFlow_v1.0.csv")
SAIDA_GUIA = os.path.join(ROOT, "docs/testes/EPT_MediFlow_GUIA_E_COBERTURA.md")
MANIFEST = os.path.join(ROOT, "tests/fixtures/manifest.csv")

COLUNAS = [
    # identificação
    "ID_CASO", "SUITE", "ID_REQUISITO", "REGRAS_NEGOCIO", "CENARIO",
    # classificação do teste
    "TIPO_TESTE", "TECNICA", "PRIORIDADE",
    # conteúdo do procedimento
    "TITULO", "OBJETIVO", "PRE_CONDICOES", "MASSA_DE_DADOS", "PASSOS",
    "RESULTADO_ESPERADO", "POS_CONDICOES",
    # rastreabilidade
    "CRITERIO_DE_ACEITE", "AUTOMATIZAVEL", "AMBIENTE", "OBSERVACOES",
    # execução (preenchido pelo executor)
    "STATUS_EXECUCAO", "RESULTADO_OBTIDO", "EVIDENCIA", "DEFEITO",
    "DATA_EXECUCAO", "EXECUTOR",
]

PENDENTE = "PENDENTE (§15)"


def ct(id_caso, suite, req, rn, cenario, tipo, tecnica, prioridade, titulo,
       objetivo, pre, massa, passos, esperado, pos, ca,
       auto="Sim", ambiente="API", obs=""):
    """Monta um caso da EPT. `passos` é lista; o resto é texto."""
    if isinstance(passos, (list, tuple)):
        passos = " | ".join(f"{i}) {p}" for i, p in enumerate(passos, 1))
    return {
        "ID_CASO": id_caso,
        "SUITE": suite,
        "ID_REQUISITO": req,
        "REGRAS_NEGOCIO": rn,
        "CENARIO": cenario,
        "TIPO_TESTE": tipo,
        "TECNICA": tecnica,
        "PRIORIDADE": prioridade,
        "TITULO": titulo,
        "OBJETIVO": objetivo,
        "PRE_CONDICOES": pre,
        "MASSA_DE_DADOS": massa,
        "PASSOS": passos,
        "RESULTADO_ESPERADO": esperado,
        "POS_CONDICOES": pos,
        "CRITERIO_DE_ACEITE": ca,
        "AUTOMATIZAVEL": auto,
        "AMBIENTE": ambiente,
        "OBSERVACOES": obs,
        "STATUS_EXECUCAO": "NAO EXECUTADO",
        "RESULTADO_OBTIDO": "",
        "EVIDENCIA": "",
        "DEFEITO": "",
        "DATA_EXECUCAO": "",
        "EXECUTOR": "",
    }


PRE_API = ("API FastAPI no ar em ambiente de homologação; OCI Object Storage e adaptador Gemini "
           "configurados por variável de ambiente; limiar padrão 0,85; dados exclusivamente fictícios.")

CASOS: list[dict] = []

#: Casos cuja automação é parcial (validação visual/humana) — sobrescreve o default.
AUTO_MANUAL: dict[str, str] = {
    "CT-081": "Parcial", "CT-082": "Parcial", "CT-083": "Parcial", "CT-084": "Não",
    "CT-085": "Parcial", "CT-086": "Parcial", "CT-087": "Parcial", "CT-088": "Parcial",
    "CT-089": "Parcial", "CT-095": "Não", "CT-097": "Não", "CT-099": "Não",
    "CT-100": "Parcial", "CT-098": "Parcial", "CT-094": "Parcial",
}

#: Casos opcionais no MVP.
PRIORIDADE_BAIXA = {"CT-072"}

# =====================================================================
# SUITE 1 — Ingestão e validação de entrada (RF-01, RF-02, RF-03)
# =====================================================================
S = "Ingestão e validação"
CASOS += [
    ct("CT-001", S, "RF-01; RF-25", "RN-07", "Rotina", "Funcional",
       "Caso de uso", "Alta",
       "Envio de documento textual pela API retorna 202 com ID e URLs de consulta",
       "Provar que a submissão é assíncrona: aceita, gera documento_id e devolve referências sem "
       "entregar o resultado na mesma chamada.",
       PRE_API + " Massa fictícia carregada.",
       "Matriz_Receituario_Texto",
       ["Enviar POST /api/v1/triagens com JSON {tipo_arquivo: TEXTO, documento_texto: <texto do fixture>, "
        "canal_origem: 'Prontuário', metadados: {}}",
        "Conferir código HTTP e corpo da resposta",
        "Chamar GET no status_url devolvido",
        "Chamar GET no historico_url devolvido"],
       "HTTP 202; corpo contém documento_id único no formato DOC-…, status RECEBIDO (ou PROCESSANDO), "
       "status_url e historico_url; nenhum campo de classificação ou extração vem na submissão; a consulta "
       "ao status_url responde 200 com estado válido do enum §5.3.",
       "Triagem registrada no OCI no prefixo de recebidos; evento de recebimento no histórico.",
       "§16 item 6", obs="Regra do modo assíncrono é decisão aprovada (§10)."),

    ct("CT-002", S, "RF-01; RF-02", "", "Rotina", "Funcional",
       "Partição de equivalência", "Alta",
       "Envio de PDF digital por multipart/form-data",
       "Validar o segundo canal de entrada previsto: arquivo PDF com camada de texto.",
       PRE_API, "Matriz_Guia_Pdf",
       ["Enviar POST /api/v1/triagens como multipart/form-data com o PDF e o campo canal_origem",
        "Conferir HTTP 202 e documento_id",
        "Aguardar estado terminal via GET e comparar com expected.json"],
       "HTTP 202 com documento_id; estado terminal PROCESSADO; classificação GUIA_PROCEDIMENTO; "
       "destino AUDITORIA_AUTORIZACOES; sem notificação.",
       "Original gravado em recebidos/; resultado em processados/.", "§16 itens 1 e 2"),

    ct("CT-003", S, "RF-01; RF-02; RF-04", "", "Urgência", "Funcional",
       "Partição de equivalência", "Alta",
       "Envio de imagem (JPG) pelo pipeline multimodal",
       "Provar que imagem raster comum é aceita e analisada pelo adaptador multimodal, não só o texto.",
       PRE_API, "Matriz_Receituario_Imagem",
       ["Enviar POST /api/v1/triagens em multipart com o JPG",
        "Consultar o resultado até PROCESSADO ou EM_REVISAO",
        "Verificar se o conteúdo esperado (paciente, médico, CRM, medicamento, urgência) foi extraído"],
       "HTTP 202; estado terminal EM_REVISAO; prioridade URGENTE; FILA_URGENCIA_MEDICA; notificação "
       "registrada como SIMULADO; dados extraídos compatíveis com o expected.json.",
       "Resultado em processados/ ou auditoria/ conforme o estado.", "§16 itens 1 e 3"),

    ct("CT-004", S, "RF-02; RF-04", "", "Rotina", "Integração",
       "Partição de equivalência", "Alta",
       "PDF digitalizado sem camada de texto é lido pelo caminho multimodal",
       "Diferenciar PDF digital de PDF digitalizado: o segundo tem 0 caracteres extraíveis e precisa "
       "chegar ao mesmo resultado pelo pipeline de visão.",
       PRE_API, "Qualidade_Pdf_SemTexto; Escaneado_*",
       ["Enviar o PDF digitalizado pelo endpoint de triagem",
        "Medir a quantidade de texto extraível (deve ser 0)",
        "Conferir classificação, extração e destino"],
       "HTTP 202 e estado terminal igual ao do PDF digital equivalente; tipo, prioridade e destino "
       "coerentes com o expected.json; nenhum campo extraído sem respaldo no documento.",
       "Resultado persistido no estado correspondente.", "§16 itens 1 e 2",
       obs="O bloco Escaneado cobre os 6 tipos restantes com a mesma verificação."),

    ct("CT-005", S, "RF-01", "", "Rotina", "Funcional",
       "Partição de equivalência", "Média",
       "Metadados da requisição são recebidos e preservados sem virar dado clínico",
       "Garantir que canal_origem e metadados são opcionais, aceitos e não contaminam a extração.",
       PRE_API, "Matriz_Receituario_Texto",
       ["Enviar a mesma triagem duas vezes: uma sem canal_origem/metadados, outra com "
        "canal_origem='Pronto_Socorro' e metadados={lote: 'QA-01'}",
        "Comparar classificação, extração e destino das duas respostas"],
       "Ambas retornam 202 e o mesmo resultado funcional; metadados aparecem apenas no registro/"
       "histórico, nunca em dados_extraidos; requisição sem metadados não é rejeitada.",
       "Histórico com canal de origem registrado.", "§16 item 11"),

    ct("CT-006", S, "RF-01", "RN-07", "Transversal", "Funcional",
       "Partição de equivalência", "Média",
       "documento_id informado é respeitado; ausente é gerado sem colisão",
       "Cobrir a regra RN-07 nos dois sentidos e a unicidade do identificador.",
       PRE_API, "",
       ["Enviar triagem com documento_id='DOC-TESTE-0001'",
        "Enviar duas triagens sem documento_id",
        "Conferir se o ID informado voltou igual e se os IDs gerados são distintos"],
       "ID informado é aceito e devolvido igual; IDs gerados são únicos, com formato estável e sem "
       "reaproveitamento; nenhuma resposta devolve 409/500 por colisão.",
       "Três documentos rastreáveis por ID.", "§16 item 6"),

    ct("CT-007", S, "RF-01; RF-03", "", "Erro", "Funcional negativo",
       "Partição de equivalência", "Alta",
       "Requisição sem arquivo e sem texto é rejeitada antes da inferência",
       "Impedir que uma chamada vazia chegue ao modelo.",
       PRE_API, "Validacao_SemConteudo",
       ["Enviar POST /api/v1/triagens multipart sem arquivo e sem documento_texto",
        "Conferir HTTP, código funcional e mensagem",
        "Verificar no log que o adaptador Gemini não foi chamado"],
       "HTTP 422; código CAMPOS_INVALIDOS; mensagem indica que é preciso enviar arquivo ou texto; "
       "nenhuma triagem é criada e nenhum documento_id é devolvido; sem stack trace.",
       "Nada persistido no OCI.", "§16 item 1"),

    ct("CT-008", S, "RF-03", "", "Erro", "Funcional negativo",
       "Partição de equivalência", "Alta",
       "JSON malformado retorna 400 REQUISICAO_INVALIDA",
       "Validar a rejeição de envelope sintaticamente inválido.",
       PRE_API, "Validacao_JsonMalformado",
       ["Enviar corpo JSON com vírgula final e chaves desbalanceadas",
        "Conferir HTTP e código funcional",
        "Repetir com JSON válido porém sem campos obrigatórios"],
       "HTTP 400 com REQUISICAO_INVALIDA no caso malformado; HTTP 422 com CAMPOS_INVALIDOS no caso "
       "estruturalmente válido e incompleto; mensagens distintas e seguras.",
       "Nenhuma triagem criada.", "§16 item 1"),

    ct("CT-009", S, "RF-03", "", "Erro", "Funcional negativo",
       "Partição de equivalência", "Alta",
       "Formato fora do allowlist retorna 415 FORMATO_NAO_SUPORTADO",
       "Cobrir DOCX e ZIP como entradas tecnicamente válidas, mas não suportadas.",
       PRE_API, "Validacao_ArquivoDocx; Validacao_ArquivoZip",
       ["Enviar um .docx válido", "Enviar um .zip válido",
        "Conferir HTTP, código funcional e mensagem nos dois casos"],
       "HTTP 415 com FORMATO_NAO_SUPORTADO nos dois envios; mensagem lista os formatos aceitos "
       "(PDF, imagem, texto); nenhuma inferência é executada.",
       "Nenhum objeto gravado.", "§16 item 1"),

    ct("CT-010", S, "RF-03", "", "Erro", "Borda",
       "Valor limite", "Alta",
       "Arquivo de 0 byte e arquivo acima do limite de tamanho",
       "Provar a validação de limites: nem vazio, nem maior que o configurado.",
       PRE_API + " Limite de tamanho configurado em variável de ambiente.",
       "Validacao_ArquivoVazio; Validacao_ArquivoGrande",
       ["Enviar arquivo de 0 byte", "Enviar PDF válido de 25 MB (acima do limite configurado)",
        "Enviar arquivo com exatamente o tamanho do limite, se o limite estiver definido"],
       "0 byte → HTTP 422 CAMPOS_INVALIDOS; 25 MB → HTTP 413 ARQUIVO_MAIOR_QUE_LIMITE; ambos sem "
       "chamar o modelo; a mensagem informa o limite aplicado.",
       "Nenhum objeto gravado.", "§16 item 1",
       obs=f"Limite máximo e nº de páginas ainda não definidos na spec: {PENDENTE}. "
           "Sem o limite, o caso de 25 MB fica bloqueado."),

    ct("CT-011", S, "RF-03", "", "Erro", "Funcional negativo",
       "Análise de risco", "Média",
       "Extensão .pdf com conteúdo real de PNG é rejeitada por inconsistência de MIME",
       "Impedir bypass de validação por troca de extensão.",
       PRE_API, "Validacao_MimeInvalido",
       ["Renomear um PNG para .pdf", "Enviar como multipart com content-type application/pdf",
        "Conferir código funcional"],
       "Rejeição com MIME_INVALIDO (ou FORMATO_NAO_SUPORTADO, conforme contrato em §10.1) e mensagem "
       "que não revela detalhe interno; nenhuma triagem é iniciada.",
       "Nenhum objeto gravado.", "§16 item 1",
       obs="A spec propõe 415; o contrato do repositório tem o código MIME_INVALIDO. Alinhar antes de executar."),

    ct("CT-012", S, "RF-01; RF-03", "", "Erro", "Funcional negativo",
       "Valor limite", "Média",
       "Envelope JSON vazio é tratado como campos inválidos",
       "Cobrir o envio de JSON válido sem nenhum campo de conteúdo.",
       PRE_API, "Validacao_EnvelopeVazio",
       ["Enviar POST com corpo {}", "Enviar POST com {'metadados': {}}",
        "Conferir HTTP e mensagem"],
       "HTTP 422 CAMPOS_INVALIDOS nos dois envios; mensagem cita os campos ausentes; sem stack trace "
       "e sem criação de documento_id.",
       "Nenhuma triagem criada.", "§16 item 1"),
]

# =====================================================================
# SUITE 2 — Classificação (RF-05, RF-06, RF-07, RF-17)
# =====================================================================
S = "Classificação"
CASOS += [
    ct("CT-013", S, "RF-05; RF-06", "", "Rotina", "Funcional",
       "Tabela de decisão", "Alta",
       "Matriz tipo documental × formato classifica os 6 tipos clínicos nos 3 canais",
       "Provar cobertura completa da taxonomia do MVP: 6 tipos clínicos × PDF, imagem e texto.",
       PRE_API, "Matriz_Receituario_*; Matriz_LaudoLaboratorial_*; Matriz_LaudoDeImagem_*; "
                "Matriz_Guia_*; Matriz_RelatorioDeAlta_*; Matriz_Atestado_*",
       ["Enviar os 18 documentos (6 tipos × 3 formatos) como triagens independentes",
        "Comparar tipo_documento e especialidade de cada resposta com o expected.json",
        "Conferir se o código estável e o rótulo exibido correspondem ao mesmo tipo"],
       "18/18 classificações corretas; especialidade preenchida quando explícita no documento; "
       "nenhum tipo trocado por outro do mesmo grupo (laboratorial × imagem em especial).",
       "18 resultados persistidos.", "§16 item 2"),

    ct("CT-014", S, "RF-05", "RN-02", "Ambiguidade", "Funcional", "Partição de equivalência", "Alta",
       "Documento fora da taxonomia é classificado como OUTRO e vai para revisão",
       "OUTRO é resultado de classificação, não tipo escrito no documento.",
       PRE_API, "Matriz_Outro_*; Escaneado_Outro_PdfDigitalizado",
       ["Enviar os 4 documentos fora da taxonomia (PDF, imagem, texto e digitalizado)",
        "Conferir tipo e destino"],
       "tipo_documento=OUTRO nas 4 respostas; status EM_REVISAO; destino FILA_REVISAO_HUMANA; "
       "justificativa cita tipo fora da taxonomia/destino não mapeado.",
       "Resultados em auditoria/.", "§16 itens 4 e 12"),

    ct("CT-015", S, "RF-05; RF-15; RF-21", "RN-02", "Ambiguidade", "Funcional negativo",
       "Partição de equivalência", "Alta",
       "Documento ilegível resulta em NAO_IDENTIFICADO sem dado inventado",
       "Garantir que ilegibilidade não vira chute: os 5 campos obrigatórios ficam nulos.",
       PRE_API, "Matriz_NaoIdentificado_*; Qualidade_Foto_Desfocada",
       ["Enviar os 4 documentos ilegíveis",
        "Inspecionar dados_extraidos, campos_ausentes e urgencia",
        "Conferir destino e justificativa"],
       "tipo=NAO_IDENTIFICADO; urgencia=INDETERMINADO; paciente, médico, CRM e diagnóstico nulos e "
       "listados em campos_ausentes; nenhum valor inventado; destino FILA_REVISAO_HUMANA.",
       "Resultados em auditoria/.", "§16 itens 4 e 9",
       obs="Comparar por asserção: não exigir texto igual ao modelo, exigir ausência de invenção."),

    ct("CT-016", S, "RF-06", "", "Transversal", "Funcional negativo",
       "Partição de equivalência", "Média",
       "Especialidade ausente retorna null/lista vazia com sinalização, nunca inferência",
       "Distinguir 'não consta' de 'não consegui ler' e proibir especialidade inventada.",
       PRE_API, "Matriz_Outro_Texto; Matriz_NaoIdentificado_Pdf",
       ["Enviar documentos sem especialidade explícita",
        "Conferir especialidade e campos_ausentes/incertos"],
       "especialidade ausente vem como lista vazia ou null e o motivo é registrado; nenhuma "
       "especialidade aparece sem trecho de respaldo no documento.",
       "Resultado persistido.", "§16 item 9"),

    ct("CT-017", S, "RF-07", "RN-03", "Urgência", "Funcional", "Tabela de decisão", "Alta",
       "Sinal textual de urgência eleva a prioridade e aciona a fila urgente",
       "Cobrir o caminho padrão de urgência com notificação simulada.",
       PRE_API, "Matriz_LaudoDeImagem_Pdf; Matriz_LaudoDeImagem_Imagem; Matriz_Guia_Imagem",
       ["Enviar os três documentos com urgência explícita",
        "Conferir nivel_prioridade, urgencia, destino e notificação"],
       "prioridade=URGENTE; urgencia=SIM com sinais e justificativa; destino FILA_URGENCIA_MEDICA; "
       "notificação gerada com canal SIMULADO_SLACK_PLANTAO e status REGISTRADA.",
       "Evento de alerta no histórico.", "§16 item 3"),

    ct("CT-018", S, "RF-07", "RN-01", "Rotina", "Funcional", "Tabela de decisão", "Alta",
       "Documento sem sinal de urgência mantém prioridade ROTINA",
       "Evitar falso positivo de urgência, que gera alerta indevido.",
       PRE_API, "Matriz_Receituario_Pdf; Matriz_Receituario_Texto; Matriz_Guia_Pdf; "
                "Matriz_Atestado_Texto; Matriz_LaudoLaboratorial_Pdf",
       ["Enviar os documentos de rotina",
        "Conferir prioridade, urgencia e notificação"],
       "prioridade=ROTINA; urgencia=NAO; notificação ausente; status PROCESSADO com destino de rotina.",
       "Resultados em processados/.", "§16 item 2"),

    ct("CT-019", S, "RF-07", "RN-03", "Urgência", "Funcional", "Análise de risco", "Alta",
       "Prescrição de alto risco sem texto de urgência ainda dispara urgência",
       "Garantir que o risco clínico explícito prevalece sobre a ausência da palavra 'urgente'.",
       PRE_API, "Conflito_AltoRisco",
       ["Enviar receita de varfarina 10 mg sem texto de urgência",
        "Conferir prioridade, destino e notificação"],
       "prioridade=URGENTE e destino FILA_URGENCIA_MEDICA com alerta; justificativa cita a regra de "
       "alto risco (RN-03) e o sinal considerado.",
       "Evento de alerta no histórico.", "§16 item 3",
       obs="O dicionário de medicamentos de alto risco é definição pendente da equipe (§15)."),

    ct("CT-020", S, "RF-07; RF-13", "RN-03", "Urgência", "Funcional", "Tabela de decisão", "Alta",
       "Urgência é detectada mesmo com confiança geral baixa",
       "Provar a precedência do sinal crítico sobre o score.",
       PRE_API + " Stub de score ativo (FIXTURE_MODE).", "Simultaneo_Urgencia_Score",
       ["Forçar score_classificacao e score_extracao em 0,70",
        "Enviar laudo com sinal de urgência", "Conferir prioridade e destinos"],
       "prioridade=URGENTE; destinos=[FILA_URGENCIA_MEDICA, FILA_REVISAO_HUMANA]; notificação "
       "registrada; justificativa cita urgência e score abaixo do limiar.",
       "Resultado em auditoria/.", "§16 itens 3 e 8"),

    ct("CT-021", S, "RF-07; RF-21", "RN-02", "Ambiguidade", "Funcional", "Tabela de decisão", "Média",
       "Prioridade NAO_IDENTIFICADA obriga revisão",
       "Cobrir o terceiro valor do enum de prioridade e sua consequência.",
       PRE_API, "Matriz_NaoIdentificado_Texto",
       ["Enviar documento sem informação suficiente para priorizar",
        "Conferir prioridade, status e destino"],
       "prioridade=NAO_IDENTIFICADA; status EM_REVISAO; destino FILA_REVISAO_HUMANA; motivo da "
       "revisão informado na decisão.",
       "Resultado em auditoria/.", "§16 item 4",
       obs="A spec não define prioridades intermediárias no MVP; não criar classificações extras."),

    ct("CT-022", S, "RF-17", "", "Transversal", "Funcional", "Contrato", "Média",
       "Score de classificação está em [0,1] e sua origem é documentada",
       "Evitar que score autorrelatado seja lido como probabilidade calibrada.",
       PRE_API, "",
       ["Executar 10 triagens variadas", "Coletar score_classificacao de todas",
        "Conferir faixa, presença em toda resposta e documentação da origem"],
       "10/10 scores no intervalo [0,1]; nenhum nulo ou string; a documentação declara que o score do "
       "LLM não é probabilidade calibrada.",
       "Evidência anexada à EPT.", "§16 item 12"),
]

# =====================================================================
# SUITE 3 — Extração (RF-08 a RF-15)
# =====================================================================
S = "Extração"
CASOS += [
    ct("CT-023", S, "RF-08", "", "Rotina", "Funcional", "Partição de equivalência", "Alta",
       "Extrair nome e idade do paciente quando explícitos",
       "Validar o caminho feliz da extração de paciente.",
       PRE_API, "Matriz_Receituario_Pdf; Matriz_LaudoLaboratorial_Pdf",
       ["Enviar os documentos com paciente identificado",
        "Conferir paciente.nome e paciente.idade"],
       "Nome idêntico ao documento; idade como inteiro dentro de 0..120; campos_ausentes não cita "
       "paciente; nenhum caractere de cabeçalho/rodapé agregado ao nome.",
       "Resultado persistido.", "§16 item 2"),

    ct("CT-024", S, "RF-08; RF-15; RF-21", "RN-02", "Ambiguidade", "Funcional negativo",
       "Partição de equivalência", "Alta",
       "Nome do paciente ausente permanece null e força revisão",
       "Impedir preenchimento por inferência a partir de outros documentos.",
       PRE_API, "Ausencia_Paciente_Nome",
       ["Enviar receita sem nome do paciente",
        "Conferir paciente.nome, campos_ausentes e destino"],
       "paciente.nome=null; campos_ausentes contém 'paciente.nome'; status EM_REVISAO; destino "
       "FILA_REVISAO_HUMANA; justificativa cita o campo obrigatório ausente.",
       "Resultado em auditoria/.", "§16 itens 5 e 9"),

    ct("CT-025", S, "RF-08; RF-21", "RN-02", "Ambiguidade", "Funcional negativo",
       "Partição de equivalência", "Alta",
       "Idade ausente permanece null e força revisão",
       "Tratar idade como campo obrigatório independente do nome.",
       PRE_API, "Ausencia_Paciente_Idade",
       ["Enviar receita com nome e sem idade", "Conferir idade e campos_ausentes"],
       "paciente.idade=null; campos_ausentes contém 'paciente.idade'; status EM_REVISAO.",
       "Resultado em auditoria/.", "§16 item 5"),

    ct("CT-026", S, "RF-15", "RN-02", "Ambiguidade", "Funcional negativo",
       "Análise de risco", "Alta",
       "Idade ilegível vai para campos_incertos, não para valor chutado",
       "Separar ausência (null) de incerteza (campo lido parcialmente).",
       PRE_API, "Qualidade_Foto_BaixoContraste",
       ["Enviar atestado com mancha sobre a idade",
        "Conferir idade, campos_incertos e campos_ausentes"],
       "Idade nula, listada em campos_incertos (não em campos_ausentes) quando lida parcialmente; "
       "status EM_REVISAO; nenhum número inferido a partir de contexto.",
       "Resultado em auditoria/.", "§16 item 9"),

    ct("CT-027", S, "RF-09", "", "Rotina", "Funcional", "Partição de equivalência", "Alta",
       "Extrair médico solicitante e CRM com número e UF separados",
       "Validar o formato do CRM como estrutura (numero, uf) e não string solta.",
       PRE_API, "Matriz_Guia_Pdf; Matriz_Atestado_Pdf",
       ["Enviar documentos com CRM completo",
        "Conferir medico.nome, medico.crm.numero e medico.crm.uf"],
       "Nome do médico preservado; numero só com dígitos; uf com 2 caracteres; nenhum CRM validado "
       "contra base externa (fora do MVP).",
       "Resultado persistido.", "§16 item 2"),

    ct("CT-028", S, "RF-09; RF-21", "RN-02", "Ambiguidade", "Funcional negativo",
       "Tabela de decisão", "Alta",
       "Nome do médico ou CRM ausente força revisão",
       "Cobrir os dois campos obrigatórios do solicitante separadamente.",
       PRE_API, "Ausencia_Medico_Nome; Ausencia_Medico_Crm; Qualidade_Foto_Cortada",
       ["Enviar laudo sem nome do médico (CRM presente)",
        "Enviar laudo sem CRM (nome presente)",
        "Conferir campos_ausentes e destino em cada um"],
       "No primeiro, medico.nome=null e 'medico.nome' em campos_ausentes; no segundo, "
       "medico.crm=null e 'medico.crm' em campos_ausentes; ambos EM_REVISAO com "
       "FILA_REVISAO_HUMANA.",
       "Resultados em auditoria/.", "§16 item 5"),

    ct("CT-029", S, "RF-09", "", "Transversal", "Funcional", "Contrato", "Média",
       "CRM é normalizado e preserva a UF de atuação do hospital",
       "Evitar CRM sem UF, com UF minúscula ou com número formatado de formas diferentes.",
       PRE_API, "Matriz_* (todos os documentos com CRM)",
       ["Executar a bateria de documentos que têm CRM",
        "Comparar uf, numero e valor original quando presente"],
       "uf sempre 'SP' (Hospital Aurora/SP) em todos os casos; numero sem máscara; valor original "
       "preservado quando houver formatação de origem; nenhuma sigla de conselho trocada.",
       "Evidência anexada.", "§16 item 12",
       obs="O verificador tools/verificar_consistencia.py já reprova CRM fora de SP na massa."),

    ct("CT-030", S, "RF-10", "", "Rotina", "Funcional", "Partição de equivalência", "Alta",
       "Extrair diagnóstico e CID quando explícitos",
       "Validar extração de diagnóstico principal e CID-10 presente no documento.",
       PRE_API, "Matriz_Guia_Pdf; Matriz_RelatorioDeAlta_Pdf; Matriz_Atestado_Pdf",
       ["Enviar documentos com diagnóstico e CID explícitos",
        "Conferir diagnostico e cid"],
       "diagnostico idêntico ao texto; cid no padrão CID-10 (letra + dígitos) exatamente como no "
       "documento; nenhum CID sugerido quando já existe; campos_ausentes sem 'cid'.",
       "Resultado persistido.", "§16 item 2"),

    ct("CT-031", S, "RF-10; RF-21", "RN-01", "Rotina", "Funcional negativo",
       "Partição de equivalência", "Alta",
       "CID ausente não é sugerido e não obriga revisão",
       "Provar que a ausência de CID é tolerada — decisão confirmada nº 2 e nº 3.",
       PRE_API, "Ausencia_SomenteCid",
       ["Enviar laudo com diagnóstico e sem CID",
        "Conferir cid, campos_ausentes, status e destino"],
       "cid=null e 'cid' em campos_ausentes; status PROCESSADO; destino PRONTUARIO_ELETRONICO; "
       "nenhum CID inferido a partir do diagnóstico.",
       "Resultado em processados/.", "§16 item 5"),

    ct("CT-032", S, "RF-10; RF-21", "RN-02", "Ambiguidade", "Funcional negativo",
       "Partição de equivalência", "Alta",
       "Diagnóstico/hipótese ausente força revisão",
       "Cobrir o quinto campo obrigatório.",
       PRE_API, "Ausencia_Diagnostico; Matriz_RelatorioDeAlta_Texto",
       ["Enviar guia sem diagnóstico", "Enviar relatório de alta truncado, sem hipótese",
        "Conferir diagnóstico, campos_ausentes e destino"],
       "diagnostico=null; 'diagnostico' em campos_ausentes; EM_REVISAO com FILA_REVISAO_HUMANA; "
       "justificativa cita o campo obrigatório.",
       "Resultados em auditoria/.", "§16 item 5"),

    ct("CT-033", S, "RF-16", "", "Ambiguidade", "Funcional negativo",
       "Tabela de decisão", "Alta",
       "CID incompatível com o diagnóstico é registrado como conflito, sem alterar valores",
       "Validar a regra de consistência CID × diagnóstico.",
       PRE_API, "Conflito_Cid_Diagnostico",
       ["Enviar laudo com diagnóstico de lombalgia e CID de infarto agudo (I21)",
        "Conferir conflitos, valores extraídos e destino"],
       "Conflito com tipo CID_DIAGNOSTICO, campos e gravidade preenchidos; diagnostico e cid mantidos "
       "como no documento (nada corrigido); EM_REVISAO com FILA_REVISAO_HUMANA.",
       "Resultado em auditoria/.", "§16 item 12",
       obs="A tabela clínica CID × diagnóstico precisa ser aprovada pela equipe (§15)."),

    ct("CT-034", S, "RF-11", "", "Rotina", "Funcional", "Partição de equivalência", "Alta",
       "Extrair medicamentos com os atributos explícitos e null no que faltar",
       "Cobrir nome, concentração, dose, via, frequência e duração.",
       PRE_API, "Matriz_Receituario_Texto; Matriz_Receituario_Pdf",
       ["Enviar receitas com medicamentos detalhados",
        "Conferir a lista de medicamentos e cada atributo"],
       "Lista com os medicamentos prescritos; atributos presentes no documento preenchidos; "
       "atributo ausente null; nenhuma dose completada por convenção.",
       "Resultado persistido.", "§16 item 2"),

    ct("CT-035", S, "RF-11; RF-21", "RN-01", "Rotina", "Funcional negativo",
       "Partição de equivalência", "Média",
       "Lista vazia de medicamentos é diferente de falha de leitura e não obriga revisão",
       "Garantir que 'nenhum identificado' não seja confundido com 'leitura falhou'.",
       PRE_API, "Ausencia_SomenteMedicamentos",
       ["Enviar laudo laboratorial sem medicamentos",
        "Conferir lista, sinalizador de extração e status"],
       "medicamentos=[] com sinalizador indicando 'nenhum identificado'; status PROCESSADO; "
       "nenhuma revisão apenas por isso.",
       "Resultado em processados/.", "§16 item 5"),

    ct("CT-036", S, "RF-11; RF-16", "", "Ambiguidade", "Funcional negativo",
       "Análise de risco", "Alta",
       "Dose suspeita é sinalizada como conflito sem alterar o valor prescrito",
       "Provar que o sistema alerta e não corrige dose por conta própria.",
       PRE_API, "Conflito_Dose",
       ["Enviar receita com losartana 500 mg (10× acima do usual)",
        "Conferir dose extraída, conflitos e destino"],
       "Dose registrada exatamente como no documento; conflito DOSE_SUSPEITA com descrição e "
       "gravidade; EM_REVISAO; nenhuma dose 'corrigida' na saída.",
       "Resultado em auditoria/.", "§16 item 9",
       obs="Comparação com farmacopeia é requisito de extração; a base aprovada é pendência (§15)."),

    ct("CT-037", S, "RF-12", "", "Rotina", "Funcional", "Partição de equivalência", "Alta",
       "Exames solicitados e realizados vêm em listas separadas",
       "Evitar dedução de exames a partir do diagnóstico.",
       PRE_API, "Matriz_LaudoLaboratorial_Texto; Diferencial_HemogramaCompleto; Diferencial_GuiaTiss",
       ["Enviar laudo com exames realizados", "Enviar guia com exame solicitado",
        "Conferir exames_solicitados e exames_realizados"],
       "Cada exame aparece na lista correta; guia de solicitação não gera 'realizado'; laudo não gera "
       "'solicitado'; nenhum exame criado por dedução do diagnóstico.",
       "Resultado persistido.", "§16 item 2"),

    ct("CT-038", S, "RF-12; RF-21", "RN-01", "Rotina", "Funcional negativo",
       "Partição de equivalência", "Média",
       "Exames ausentes não obrigam revisão",
       "Cobrir o terceiro campo tolerado pela regra de ausência.",
       PRE_API, "Ausencia_SomenteExames",
       ["Enviar atestado sem exames", "Conferir listas e status"],
       "Listas vazias; status PROCESSADO; nenhuma menção a exame em campos_ausentes que dispare "
       "revisão.",
       "Resultado em processados/.", "§16 item 5"),

    ct("CT-039", S, "RF-13", "", "Transversal", "Funcional", "Tabela de decisão", "Alta",
       "Indicador de urgência usa SIM / NAO / INDETERMINADO com sinais e justificativa",
       "Provar o uso do terceiro estado e a proibição de declarar 'não' em documento ilegível.",
       PRE_API, "Matriz_Receituario_Imagem; Matriz_Atestado_Texto; Matriz_NaoIdentificado_Imagem",
       ["Enviar um documento urgente, um de rotina e um ilegível",
        "Conferir urgencia, sinais, justificativa e trecho de referência"],
       "URGENTE→SIM; rotina→NAO; ilegível→INDETERMINADO; todo estado acompanhado de sinais "
       "encontrados ou do motivo da indeterminação; nenhum INDETERMINADO convertido em NAO.",
       "Resultado persistido.", "§16 itens 3, 4 e 9"),

    ct("CT-040", S, "RF-15", "", "Ambiguidade", "Funcional negativo",
       "Análise de risco", "Média",
       "Campos contraditórios no mesmo documento geram conflito de contradição interna",
       "Cobrir divergência entre cabeçalho e corpo do documento.",
       PRE_API, "Conflito_Dados",
       ["Enviar relatório com dois nomes/idades divergentes",
        "Conferir qual valor foi extraído, conflitos e destino"],
       "Um valor registrado como extraído, o outro preservado na descrição do conflito; conflito "
       "CONTRADICAO_INTERNA com gravidade; EM_REVISAO.",
       "Resultado em auditoria/.", "§16 item 12"),

    ct("CT-041", S, "RF-14", "", "Transversal", "Funcional negativo",
       "Contrato", "Alta",
       "Resposta fora do esquema é rejeitada e não vaza para o consumidor",
       "Validar a barreira Pydantic contra payload malformado do modelo.",
       PRE_API + " Stub do adaptador Gemini configurado para devolver payload inválido.",
       "",
       ["Forçar resposta sem campo obrigatório, com tipo errado e com campo desconhecido",
        "Observar status, erro e log",
        "Repetir com o payload correto para provar recuperação"],
       "Payload inválido não é aceito silenciosamente: aplica reparo limitado e, persistindo, "
       "ERRO_PROCESSAMENTO com código e mensagem segura; campo desconhecido isolado não quebra o "
       "consumidor; falha fica registrada no histórico.",
       "Erro registrado; nenhum dado inválido persistido.", "§16 itens 11 e 15"),

    ct("CT-042", S, "RF-15", "", "Transversal", "Funcional", "Contrato", "Média",
       "Cada campo extraído permite distinguir explícito, ausente e incerto",
       "Garantir a rastreabilidade de evidência por campo.",
       PRE_API, "Matriz_Guia_Pdf; Ausencia_Paciente_Idade; Qualidade_Foto_BaixoContraste",
       ["Executar os três documentos (explícito, ausente, incerto)",
        "Conferir presença de valor, campos_ausentes, campos_incertos e evidência/trecho"],
       "Os três estados são distinguíveis na resposta e no histórico; trecho de evidência existe "
       "quando há valor; explicação interna do modelo não é exposta como prova.",
       "Evidência anexada.", "§16 itens 9 e 12"),

    ct("CT-043", S, "RF-14; RF-18", "", "Transversal", "Funcional", "Contrato", "Média",
       "Versão de esquema é declarada em toda resposta",
       "Permitir evolução do contrato sem quebrar consumidor.",
       PRE_API, "",
       ["Executar triagens de estados diferentes (sucesso e erro)",
        "Conferir versao_esquema e versão das regras"],
       "Toda resposta válida traz versao_esquema; a decisão registra a versão do grafo/regras; "
       "nenhuma resposta vem sem versão.",
       "Evidência anexada.", "§16 item 12"),
]

# =====================================================================
# SUITE 4 — Confiança, limiar e conflitos (RF-16, RF-18, RF-19)
# =====================================================================
S = "Confiança e limiar"
CASOS += [
    ct("CT-044", S, "RF-18", "", "Transversal", "Funcional", "Contrato", "Alta",
       "Score combinado é o mínimo entre classificação e extração",
       "Provar a fórmula aprovada min(classificação, extração) em três combinações.",
       PRE_API + " Stub de scores ativo (FIXTURE_MODE).", "",
       ["Forçar (0,99; 0,90), (0,80; 0,99) e (0,90; 0,80)",
        "Conferir score_combinado em cada resposta"],
       "combinados 0,90 / 0,80 / 0,80 respectivamente; nenhuma média ou produto usado; valor sempre "
       "igual ou menor que o menor dos dois scores.",
       "Evidência anexada.", "§16 item 8"),

    ct("CT-045", S, "RF-18", "RN-02", "Ambiguidade", "Borda", "Valor limite", "Alta",
       "Score combinado 0,84 (abaixo do limiar) força revisão",
       "Cobrir a borda inferior do limiar 0,85.",
       PRE_API + " Stub de score ativo (FIXTURE_MODE).", "Borda_Score_084",
       ["Forçar score_combinado em 0,84", "Conferir status, limiar_aplicado e destino"],
       "limiar_aplicado=0,85; status EM_REVISAO; destino FILA_REVISAO_HUMANA; justificativa cita "
       "'0,84 < 0,85'.",
       "Resultado em auditoria/.", "§16 item 8"),

    ct("CT-046", S, "RF-18", "RN-01", "Rotina", "Borda", "Valor limite", "Alta",
       "Score combinado exatamente 0,85 não revisa por esse critério",
       "Cobrir a borda superior: o limiar é estrito.",
       PRE_API + " Stub de score ativo (FIXTURE_MODE).", "Borda_Score_085",
       ["Forçar score_combinado em 0,85", "Conferir status, limiar e destino"],
       "status PROCESSADO; destino FARMACIA_HOSPITALAR; nenhuma revisão motivada por score; "
       "justificativa não cita score abaixo do limiar.",
       "Resultado em processados/.", "§16 item 8"),

    ct("CT-047", S, "RF-18", "", "Transversal", "Funcional", "Valor limite", "Média",
       "Limiar é configurável por variável de ambiente, com padrão 0,85",
       "Provar que o limiar não está hard-coded e que o padrão é o aprovado.",
       PRE_API, "",
       ["Executar com a configuração padrão e conferir limiar_aplicado=0,85",
        "Subir a aplicação com LIMIAR_CONFIANCA=0,70 e repetir o caso de 0,84",
        "Conferir decisão nos dois cenários"],
       "Padrão aplica 0,85; com 0,70 o mesmo documento (0,84) passa a PROCESSADO; a resposta informa "
       "o limiar efetivamente aplicado e o histórico registra a configuração usada.",
       "Configuração revertida ao padrão.", "§16 item 8",
       obs="Nome da variável deve ser confirmado no README da implementação."),

    ct("CT-048", S, "RF-16", "RN-02", "Ambiguidade", "Funcional", "Tabela de decisão", "Alta",
       "Qualquer conflito impeditivo leva à revisão, independentemente do score",
       "Provar que a presença de conflito vence um score alto.",
       PRE_API, "Conflito_Cid_Diagnostico; Conflito_Dose; Conflito_Dados",
       ["Executar os três documentos com score alto (0,91)",
        "Conferir status, destinos e lista de conflitos"],
       "Os três terminam EM_REVISAO com FILA_REVISAO_HUMANA apesar do score ≥ limiar; cada um lista "
       "seu conflito com tipo, campos e gravidade.",
       "Resultados em auditoria/.", "§16 item 12"),
]

# =====================================================================
# SUITE 5 — Decisão e roteamento (RF-19 a RF-24, §8.2, RN-01..RN-05)
# =====================================================================
S = "Decisão e roteamento"
CASOS += [
    ct("CT-049", S, "RF-20", "RN-01", "Rotina", "Funcional", "Tabela de decisão", "Alta",
       "Receita de rotina vai para FARMACIA_HOSPITALAR",
       "Validar o destino natural do receituário sem urgência e sem ambiguidade.",
       PRE_API, "Matriz_Receituario_Pdf; Matriz_Receituario_Texto; "
                "Escaneado_Receituario_PdfDigitalizado; Diferencial_ReceituarioManuscrito",
       ["Enviar as receitas de rotina", "Conferir destino_principal, destinos e status"],
       "destino_principal=FARMACIA_HOSPITALAR; destinos com um único item; status PROCESSADO; "
       "requer_auditoria_humana=false; notificação ausente.",
       "Resultado em processados/.", "§16 item 2"),

    ct("CT-050", S, "RF-20", "RN-01", "Rotina", "Funcional", "Tabela de decisão", "Alta",
       "Guia de procedimento eletiva vai para AUDITORIA_AUTORIZACOES",
       "Validar o destino da guia quando não há urgência.",
       PRE_API, "Matriz_Guia_Pdf; Matriz_Guia_Texto; Escaneado_Guia_PdfDigitalizado; Diferencial_GuiaTiss",
       ["Enviar as guias de rotina", "Conferir destino e status"],
       "destino AUDITORIA_AUTORIZACOES; status PROCESSADO; nenhuma notificação.",
       "Resultado em processados/.", "§16 item 2"),

    ct("CT-051", S, "RF-20", "RN-01", "Rotina", "Funcional", "Tabela de decisão", "Alta",
       "Laudo, alta e atestado de rotina vão para PRONTUARIO_ELETRONICO",
       "Validar o agrupamento de três tipos no mesmo destino.",
       PRE_API, "Matriz_LaudoLaboratorial_Pdf; Matriz_LaudoDeImagem_Texto; Matriz_RelatorioDeAlta_Pdf; "
                "Matriz_Atestado_Pdf; Matriz_Atestado_Imagem; Qualidade_Foto_Rotacionada; "
                "Diferencial_CarimboSobreposto",
       ["Enviar os documentos de rotina dos três tipos", "Conferir destino e status"],
       "Todos com destino PRONTUARIO_ELETRONICO e status PROCESSADO; sem revisão e sem alerta.",
       "Resultados em processados/.", "§16 item 2"),

    ct("CT-052", S, "RF-20; RF-22", "RN-03", "Urgência", "Funcional", "Tabela de decisão", "Alta",
       "Urgência sem ambiguidade usa apenas FILA_URGENCIA_MEDICA com alerta",
       "Provar que a auditoria da urgência acontece na própria fila urgente (R1 do contrato).",
       PRE_API, "Matriz_Receituario_Imagem; Matriz_LaudoDeImagem_Pdf; Matriz_Guia_Imagem",
       ["Enviar os três documentos urgentes sem ambiguidade",
        "Conferir destinos, status e notificação"],
       "destinos=[FILA_URGENCIA_MEDICA] (sem FILA_REVISAO_HUMANA); status EM_REVISAO; "
       "requer_auditoria_humana=true; notificação REGISTRADA.",
       "Evento de alerta no histórico.", "§16 item 3"),

    ct("CT-053", S, "RF-20; RF-21; RF-22", "RN-02; RN-03", "Urgência", "Funcional",
       "Tabela de decisão", "Alta",
       "Urgência + ilegibilidade gera os dois destinos e um único alerta",
       "Validar a decisão composta da tabela §8.2.",
       PRE_API, "Simultaneo_Urgencia_Ilegivel",
       ["Enviar receita urgente parcialmente ilegível",
        "Conferir destinos, campos_incertos e notificação"],
       "destinos=[FILA_URGENCIA_MEDICA, FILA_REVISAO_HUMANA] nesta ordem; requer_auditoria_humana=true; "
       "notificação gerada uma única vez; campos_incertos indica o atributo ilegível (ex.: dosagem).",
       "Resultado em auditoria/ e alerta registrado.", "§16 itens 3, 4 e 7"),

    ct("CT-054", S, "RF-21", "RN-02", "Ambiguidade", "Funcional", "Tabela de decisão", "Alta",
       "Urgência + score baixo também gera dois destinos",
       "Cobrir a combinação de urgência com falha de confiança.",
       PRE_API + " Stub de score ativo (FIXTURE_MODE).", "Simultaneo_Urgencia_Score",
       ["Forçar score 0,70 em laudo com urgência", "Conferir destinos e justificativa"],
       "destinos com FILA_URGENCIA_MEDICA e FILA_REVISAO_HUMANA; justificativa cita urgência e score "
       "abaixo do limiar; alerta registrado.",
       "Resultado em auditoria/.", "§16 itens 3 e 8"),

    ct("CT-055", S, "RF-07; RF-16", "RN-03", "Urgência", "Funcional negativo",
       "Tabela de decisão", "Alta",
       "Rótulo ROTINA no cabeçalho não prevalece sobre sinais de urgência no corpo",
       "Evitar que a prioridade declarada no documento ofusque o conteúdo clínico.",
       PRE_API, "Conflito_Prioridade",
       ["Enviar guia marcada ROTINA com texto de urgência e sinais críticos",
        "Conferir prioridade, conflitos e destinos"],
       "prioridade=URGENTE; conflito PRIORIDADE_TEXTO registrado; destinos com FILA_URGENCIA_MEDICA e "
       "FILA_REVISAO_HUMANA; nenhuma rota só de rotina.",
       "Resultado em auditoria/.", "§16 item 3"),

    ct("CT-056", S, "RF-21", "RN-02", "Ambiguidade", "Funcional", "Tabela de decisão", "Alta",
       "Tipo fora da taxonomia cai na revisão humana por destino não mapeado",
       "Validar a última linha da tabela §8.2.",
       PRE_API, "Matriz_Outro_Pdf; Matriz_Outro_Imagem; Matriz_Outro_Texto",
       ["Enviar os documentos fora da taxonomia", "Conferir destino e motivo"],
       "destino FILA_REVISAO_HUMANA; status EM_REVISAO; nenhuma notificação (não há urgência); "
       "justificativa cita destino não mapeado.",
       "Resultado em auditoria/.", "§16 item 4"),

    ct("CT-057", S, "RF-21", "RN-02", "Ambiguidade", "Funcional", "Tabela de decisão", "Alta",
       "Toda revisão informa código e motivo",
       "Garantir que a fila humana seja acionável, não apenas um status.",
       PRE_API, "Ausencia_Paciente_Nome; Ausencia_Diagnostico; Borda_Score_084",
       ["Executar os três documentos que revisam por motivos diferentes",
        "Conferir o motivo registrado em cada decisão"],
       "Cada decisão traz o motivo específico (campo ausente nomeado, score abaixo do limiar, "
       "conflito etc.) e as regras acionadas; nenhuma revisão sem motivo.",
       "Motivos no histórico.", "§16 item 12"),

    ct("CT-058", S, "RF-21", "RN-02", "Ambiguidade", "Funcional", "Tabela de decisão", "Alta",
       "Os 5 campos obrigatórios forçam revisão individualmente",
       "Provar campo a campo a regra de RF-21, sem agregar indevidamente.",
       PRE_API, "Ausencia_Paciente_Nome; Ausencia_Paciente_Idade; Ausencia_Medico_Nome; "
                "Ausencia_Medico_Crm; Ausencia_Diagnostico",
       ["Enviar os 5 documentos, um por vez",
        "Conferir status e o campo citado em campos_ausentes"],
       "5/5 em EM_REVISAO com FILA_REVISAO_HUMANA; em cada um, exatamente o campo faltante aparece em "
       "campos_ausentes e na justificativa.",
       "Resultados em auditoria/.", "§16 item 5"),

    ct("CT-059", S, "RF-21", "RN-01", "Rotina", "Funcional negativo", "Tabela de decisão", "Alta",
       "Os 3 campos tolerados (CID, medicamentos, exames) não forçam revisão",
       "Provar o contraponto de RF-21 e a decisão confirmada nº 3.",
       PRE_API, "Ausencia_SomenteCid; Ausencia_SomenteMedicamentos; Ausencia_SomenteExames",
       ["Enviar os 3 documentos", "Conferir status e destino"],
       "3/3 PROCESSADO com destino de rotina; as ausências aparecem registradas, mas não como motivo "
       "de revisão.",
       "Resultados em processados/.", "§16 item 5"),

    ct("CT-060", S, "RF-22", "RN-03", "Urgência", "Funcional", "Contrato", "Alta",
       "Evento de notificação contém os campos exigidos e nunca afirma entrega externa",
       "Validar o conteúdo do alerta simulado e a proibição de alegar integração real.",
       PRE_API, "Matriz_LaudoDeImagem_Pdf; Conflito_AltoRisco",
       ["Enviar documentos urgentes", "Inspecionar o bloco de notificação na resposta e no histórico"],
       "Notificação com identificador do documento, prioridade, canal lógico, motivo, timestamp e "
       "status REGISTRADA/SIMULADO; nenhuma menção a Slack/e-mail entregue; nenhuma chamada externa "
       "no log.",
       "Evento no histórico.", "§16 item 7"),

    ct("CT-061", S, "RF-23", "RN-05", "Transversal", "Funcional", "Contrato", "Alta",
       "Toda decisão tem justificativa estruturada e rastreável",
       "Garantir auditoria: sem justificativa não há decisão válida.",
       PRE_API, "Matriz_Receituario_Pdf; Borda_Score_084; Simultaneo_Urgencia_Ilegivel",
       ["Executar um caso de rotina, um de revisão e um de urgência+revisão",
        "Conferir justificativa e regras acionadas"],
       "Todas as respostas trazem justificativa concisa, sem alegar certeza clínica; as regras "
       "acionadas aparecem por identificador (RF/RN); nenhuma justificativa vazia ou genérica.",
       "Justificativas no histórico.", "§16 item 12"),

    ct("CT-062", S, "RF-19", "", "Transversal", "Funcional", "Contrato", "Média",
       "Decisão é reprodutível a partir dos mesmos sinais e registra versões",
       "Provar determinismo do grafo de decisão.",
       PRE_API + " Stub de sinais ativo.", "",
       ["Executar 3 vezes a mesma entrada com os mesmos sinais forçados",
        "Comparar destino, status e justificativa",
        "Conferir versão do grafo/regras e timestamps"],
       "As três execuções produzem a mesma decisão; a versão do grafo/regras é registrada; timestamps "
       "de início e fim existem e são coerentes.",
       "Evidência anexada.", "§16 item 12"),

    ct("CT-063", S, "RF-20; RF-24", "", "Transversal", "Funcional", "Tabela de decisão", "Média",
       "Destino lógico é registrado como simulado, sem transmissão externa",
       "Evitar que a demonstração sugira integração com prontuário, farmácia ou operadora.",
       PRE_API, "Matriz_Receituario_Pdf; Matriz_Guia_Pdf; Matriz_LaudoLaboratorial_Pdf",
       ["Executar triagens dos três destinos de rotina",
        "Conferir texto da interface/resposta sobre simulação e ausência de chamadas externas"],
       "Resposta e interface declaram destino lógico/simulado; nenhuma chamada de rede para sistemas "
       "hospitalares no log; nenhuma afirmação de transmissão.",
       "Evidência anexada.", "§16 itens 7 e 15"),

    ct("CT-064", "API e erros", "RF-24", "", "Erro", "Funcional negativo", "Análise de risco", "Alta",
       "Falha do grafo/notificação não apaga a triagem já calculada",
       "Cobrir o fallback de exceções internas.",
       PRE_API + " Stub que força exceção no nó de notificação.", "Matriz_LaudoDeImagem_Pdf",
       ["Forçar falha na geração do evento de alerta",
        "Conferir status, destinos e registro da falha"],
       "Triagem preservada com destino urgente; falha do evento registrada de forma rastreável; "
       "nenhum falso sucesso de alerta e nenhum dado perdido.",
       "Falha no histórico.", "§16 itens 7 e 10"),

    ct("CT-065", "Persistência e histórico", "RF-24", "", "Erro", "Funcional negativo", "Análise de risco", "Média",
       "Falha de persistência é informada e nunca aparece como sucesso",
       "Cobrir o princípio de RF-24: sem storage, não há confirmação.",
       PRE_API + " Credencial OCI inválida simulada.", "Matriz_Guia_Pdf",
       ["Executar triagem com o bucket indisponível",
        "Conferir HTTP, status e mensagem",
        "Repetir após restabelecer o storage"],
       "ERRO_PERSISTENCIA com mensagem segura e indicação de reenvio; nenhuma resposta afirma "
       "documento armazenado; após restabelecer, o reenvio conclui normalmente.",
       "Erro registrado; nenhum objeto fantasma.", "§16 item 10"),
]

# =====================================================================
# SUITE 6 — Persistência e histórico (RF-26, RF-28, RF-29, RF-30)
# =====================================================================
S = "Persistência e histórico"
CASOS += [
    ct("CT-066", S, "RF-28", "RN-04", "Rotina", "Integração", "Caso de uso", "Alta",
       "Original e resultado são persistidos no OCI",
       "Provar a persistência dos dois objetos exigidos.",
       PRE_API + " Bucket Always Free acessível.", "Matriz_Receituario_Pdf",
       ["Executar a triagem até o estado terminal",
        "Listar o bucket nos prefixos de recebidos e de resultado",
        "Abrir o objeto de resultado e comparar com a resposta da API"],
       "Original presente em recebidos/…; resultado JSON presente no prefixo do estado; conteúdo do "
       "objeto igual ao da API; caminho informado na resposta corresponde ao objeto real.",
       "Objetos armazenados.", "§16 item 10"),

    ct("CT-067", S, "RF-29", "", "Ambiguidade", "Funcional", "Tabela de decisão", "Alta",
       "Objetos são segregados por estado funcional",
       "Garantir que caso em revisão não fica no mesmo prefixo de caso processado.",
       PRE_API, "Matriz_Receituario_Pdf; Ausencia_Paciente_Nome",
       ["Executar uma triagem de rotina e uma que vá para revisão",
        "Comparar os caminhos devolvidos"],
       "Rotina em processados/…; revisão em auditoria/…; nenhum objeto de revisão em processados/; "
       "padrão recebidos/{ano}/{mes}/{id}/original preservado.",
       "Objetos nos prefixos corretos.", "§16 item 10"),

    ct("CT-068", S, "RF-30", "", "Transversal", "Funcional negativo", "Contrato", "Alta",
       "Resposta informa armazenamento lógico sem URL pública nem credencial",
       "Conciliar RF-30 com a exigência de não expor segredo.",
       PRE_API, "Matriz_Guia_Pdf",
       ["Executar uma triagem", "Inspecionar armazenamento_oci e o corpo inteiro da resposta"],
       "Resposta traz bucket lógico, caminho do objeto e status de persistência; nenhuma URL "
       "pré-assinada, chave, token ou namespace sensível; nenhum base64 de credencial.",
       "Evidência anexada.", "§16 itens 10 e 13"),

    ct("CT-069", S, "RF-28; RF-29", "RN-06", "Transversal", "Não funcional", "Análise de risco", "Média",
       "Recursos OCI são Always Free e não estão hard-coded",
       "Validar custo e configurabilidade da persistência.",
       PRE_API, "",
       ["Revisar a configuração de recursos na conta OCI",
        "Trocar bucket/namespace por variável de ambiente e executar a triagem",
        "Conferir o consumo no painel OCI"],
       "Apenas recursos Always Free em uso; nenhum bucket ou namespace no código; a aplicação funciona "
       "apontando para outro bucket configurado; consumo compatível com o free tier.",
       "Configuração documentada.", "§16 item 10",
       obs="Nome dos buckets é configuração de ambiente, conforme RF-28."),

    ct("CT-070", S, "RF-26", "RN-04; RN-05", "Transversal", "Funcional", "Contrato", "Alta",
       "Histórico devolve eventos ordenados e completos por documento_id",
       "Validar a rastreabilidade mínima de §9.3.",
       PRE_API, "Matriz_Receituario_Pdf",
       ["Executar uma triagem", "Chamar GET /api/v1/triagens/{id}/historico",
        "Conferir campos e ordenação"],
       "Lista com evento_id, documento_id, tipo_evento, criado_em, ator, status_anterior, status_novo, "
       "motivo, versao_esquema e correlação; ordem cronológica crescente; sem lacunas entre recebimento "
       "e decisão.",
       "Histórico consultável.", "§16 item 11"),

    ct("CT-071", S, "RF-26", "", "Erro", "Funcional negativo", "Partição de equivalência", "Média",
       "Histórico de documento inexistente retorna 404 e não vaza outro documento",
       "Cobrir isolamento entre triagens.",
       PRE_API, "Matriz_Receituario_Pdf",
       ["Consultar histórico com ID inexistente", "Consultar com ID de outro remetente, se houver "
        "autenticação", "Conferir códigos e corpos"],
       "404 DOCUMENTO_NAO_ENCONTRADO para ID inexistente; quando a autorização estiver implementada, "
       "403 para documento de outro usuário; nenhum conteúdo de terceiro na resposta.",
       "Nenhum dado exposto.", "§16 itens 11 e 13"),

    ct("CT-072", S, "RF-26", "", "Ambiguidade", "Funcional", "Contrato", "Média",
       "Reprocessamento gera novo evento sem apagar o resultado anterior",
       "Cobrir correção/reprocessamento previsto em §9.3 e §4.",
       PRE_API, "Ausencia_Paciente_Nome",
       ["Reprocessar manualmente uma triagem em revisão (se habilitado)",
        "Consultar o histórico",
        "Conferir valor anterior preservado"],
       "Novo evento com ator, motivo e status novo; resultado anterior preservado; nenhuma "
       "sobrescrita silenciosa; se o recurso não existir, deve constar como fora do MVP e o caso "
       "vira 'não aplicável'.",
       "Histórico consistente.", "§16 item 11",
       obs="Reprocessamento manual é opcional no MVP (§4)."),
]

# =====================================================================
# SUITE 7 — Contrato de API e erros (§10, §12, RF-25, RF-27)
# =====================================================================
S = "API e erros"
CASOS += [
    ct("CT-073", S, "RF-25", "", "Transversal", "Funcional", "Contrato", "Alta",
       "GET de triagem devolve o payload completo no estado terminal",
       "Validar o contrato de §9.2 campo a campo.",
       PRE_API, "Matriz_RelatorioDeAlta_Pdf",
       ["Submeter e aguardar o estado terminal",
        "Comparar a resposta com o esquema esperado"],
       "200 OK com status, documento_id, classificacao, dados_extraidos, qualidade, "
       "decisao_roteamento, armazenamento_oci e versao_esquema; campos nulos aparecem como null (não "
       "ausentes); tipos corretos.",
       "Payload validado.", "§16 item 11"),

    ct("CT-074", S, "RF-25", "", "Transversal", "Funcional", "Partição de equivalência", "Alta",
       "Consulta de ID inexistente retorna 404 DOCUMENTO_NAO_ENCONTRADO",
       "Cobrir o erro de leitura previsto em §10.1.",
       PRE_API, "",
       ["Chamar GET /api/v1/triagens/DOC-INEXISTENTE",
        "Chamar o histórico do mesmo ID"],
       "404 com código DOCUMENTO_NAO_ENCONTRADO e mensagem segura nas duas rotas; nenhum stack trace.",
       "Nenhum dado criado.", "§16 item 11"),

    ct("CT-075", S, "RF-27", "", "Transversal", "Segurança", "Análise de risco", "Média",
       "Acesso a documento de outro usuário retorna 403 quando a autorização existir",
       "Preparar o limite de acesso exigido antes de expor a aplicação.",
       PRE_API + " Autenticação/autorização implementada (pendente de definição).", "",
       ["Autenticar como usuário A e submeter triagem",
        "Autenticar como usuário B e consultar o ID de A",
        "Conferir código e corpo"],
       "403 NAO_AUTORIZADO sem revelar existência ou conteúdo do documento; log com correlação e sem "
       "dado clínico.",
       "Acesso negado registrado.", "§16 item 13",
       obs=f"Autenticação/autorização ainda {PENDENTE}; sem isso, o caso fica bloqueado."),

    ct("CT-076", S, "RF-27", "", "Transversal", "Funcional", "Contrato", "Média",
       "Health check responde sem expor segredo nem dado clínico",
       "Provar o endpoint de disponibilidade de §10.",
       PRE_API, "",
       ["Chamar GET /api/v1/health com as dependências no ar", "Derrubar o storage e repetir",
        "Inspecionar o corpo"],
       "200 quando tudo responde; 503 quando dependência essencial falha; corpo sem credencial, "
       "namespace, string de conexão ou dado clínico.",
       "Nenhum efeito colateral.", "§16 item 13"),

    ct("CT-077", S, "RF-24; RF-25", "", "Erro", "Funcional negativo", "Contrato", "Alta",
       "Erro interno e indisponibilidade de dependência usam envelopes seguros",
       "Cobrir 500, 502, 503 e 504 com mensagem utilizável.",
       PRE_API + " Stubs de falha do Gemini.", "",
       ["Forçar erro interno, timeout do provedor e indisponibilidade",
        "Comparar códigos, mensagens e ausência de stack trace"],
       "Mapeamento coerente (500 ERRO_INTERNO, 502 PROVEDOR_INDISPONIVEL, 503 SERVICO_INDISPONIVEL, "
       "504 TIMEOUT); mensagem indica ação possível (reenviar/consultar ID); identificador de "
       "correlação presente; nenhum prompt, chave ou stack trace.",
       "Falhas registradas.", "§16 itens 13 e 15"),

    ct("CT-078", S, "RF-24", "", "Erro", "Funcional negativo", "Análise de risco", "Alta",
       "Gemini indisponível aplica retry limitado e resulta em erro ou revisão conforme o risco",
       "Cobrir a linha 'Gemini indisponível/timeout' de §12.",
       PRE_API + " Stub de timeout do adaptador.", "Matriz_LaudoDeImagem_Pdf",
       ["Forçar timeout na primeira tentativa", "Observar tentativas e resultado final",
        "Repetir com falha persistente"],
       "Retry limitado e registrado; em falha persistente, ERRO_PROCESSAMENTO (ou EM_REVISAO quando o "
       "documento já indica risco); nenhuma triagem marcada como concluída sem análise.",
       "Falha no histórico; reenvio possível.", "§16 itens 3 e 10",
       obs=f"Número de retries e timeout são {PENDENTE}."),

    ct("CT-079", S, "RF-24; RF-04", "", "Erro", "Funcional negativo", "Partição de equivalência", "Alta",
       "PDF protegido e PDF corrompido terminam em ERRO_PROCESSAMENTO com código distinto",
       "Separar as duas causas de ilegibilidade técnica.",
       PRE_API, "Qualidade_Pdf_ComSenha; Qualidade_Pdf_Corrompido",
       ["Enviar o PDF protegido (senha de teste mediflow123, se houver suporte)",
        "Enviar o PDF truncado em 40%", "Conferir status, erro.codigo e mensagem"],
       "status ERRO_PROCESSAMENTO nos dois; códigos PDF_PROTEGIDO e PDF_CORROMPIDO; sem classificação "
       "nem dados extraídos; mensagem segura; nenhum objeto de resultado marcado como sucesso.",
       "Erros registrados.", "§16 item 1"),

    ct("CT-080", S, "RF-25; RF-27", "", "Erro", "Funcional negativo", "Contrato", "Alta",
       "Nenhuma resposta expõe segredo, prompt ou stack trace",
       "Verificação transversal de vazamento em todos os estados de erro.",
       PRE_API, "Validacao_*; Qualidade_Pdf_*",
       ["Executar todos os casos de erro mapeados",
        "Buscar no corpo, nos logs e na interface padrões de chave, token, prompt, variável de "
        "ambiente e stack trace"],
       "Nenhuma ocorrência encontrada; mensagens citam apenas o necessário para o usuário agir; logs "
       "técnicos ficam restritos ao servidor.",
       "Evidência anexada.", "§16 item 13"),
]

# =====================================================================
# SUITE 8 — Interface (§11, RF-27)
# =====================================================================
S = "Interface"
CASOS += [
    ct("CT-081", S, "RF-27", "", "Rotina", "Usabilidade", "Caso de uso", "Alta",
       "Tela de envio aceita arquivo ou texto e exige origem",
       "Validar o caminho de entrada do usuário remetente.",
       "Interface React publicada apontando para a API de homologação.", "",
       ["Abrir a tela de triagem",
        "Enviar um arquivo por seleção e, em outra execução, digitar texto",
        "Preencher canal de origem e acionar Enviar"],
       "A tela permite as duas formas de entrada (mutuamente exclusivas), exibe o arquivo escolhido, "
       "exige origem e bloqueia envio vazio; o envio chega à API e a tela passa a mostrar o "
       "acompanhamento.",
       "Triagem criada.", "§16 item 13", ambiente="Interface"),

    ct("CT-082", S, "RF-27", "", "Transversal", "Usabilidade", "Caso de uso", "Alta",
       "Interface representa todos os estados do processamento",
       "Cobrir a lista de estados de §11 item 3, inclusive erro.",
       "Interface React no ar; stubs disponíveis para forçar estados.",
       "Matriz_Receituario_Pdf; Ausencia_Paciente_Nome; Qualidade_Pdf_Corrompido",
       ["Acompanhar uma triagem de rotina, uma de revisão e uma com erro",
        "Conferir o rótulo de estado exibido em cada fase"],
       "Estados aguardando, enviando, recebido, processando, processado, em revisão e erro são "
       "visualmente distinguíveis; a tela não fica presa em 'processando' quando o estado terminal "
       "chega; o polling respeita o intervalo configurado.",
       "Nenhum estado inconsistente.", "§16 item 13", ambiente="Interface"),

    ct("CT-083", S, "RF-27", "", "Transversal", "Usabilidade", "Caso de uso", "Alta",
       "Resultado exibe todos os blocos exigidos pela especificação",
       "Garantir que o operador vê o suficiente para agir sem abrir o JSON.",
       "Interface React no ar.", "Simultaneo_Urgencia_Ilegivel",
       ["Abrir o resultado de uma triagem completa",
        "Conferir cada bloco na tela"],
       "A tela mostra tipo, especialidade, prioridade, scores, dados extraídos, ausências/incertezas, "
       "conflitos, destino(s), justificativa, status do alerta e status de persistência — sem exigir "
       "inspeção do payload.",
       "Evidência (print) anexada.", "§16 item 13", ambiente="Interface"),

    ct("CT-084", S, "RF-27", "", "Urgência", "Usabilidade", "Análise de risco", "Alta",
       "Urgência tem destaque acessível por texto e não apenas por cor",
       "Cobrir requisito de acessibilidade de §11 item 5.",
       "Interface React no ar.", "Matriz_LaudoDeImagem_Pdf",
       ["Abrir um resultado urgente",
        "Verificar rótulo textual de urgência, contraste e leitura em escala de cinza"],
       "A urgência é identificada por texto explícito além da cor; contraste atende leitura; nenhuma "
       "informação depende só de cor.",
       "Evidência (print) anexada.", "§16 item 13", ambiente="Interface"),

    ct("CT-085", S, "RF-27; RF-15", "", "Ambiguidade", "Usabilidade", "Caso de uso", "Alta",
       "Ausência é exibida como 'não identificado no documento' e sugestão não vira extração",
       "Evitar que o operador leia inferência como dado do documento.",
       "Interface React no ar.", "Ausencia_Paciente_Idade; Matriz_NaoIdentificado_Texto",
       ["Abrir resultado com idade ausente",
        "Abrir resultado de documento ilegível",
        "Conferir o texto exibido nos campos vazios"],
       "Campos ausentes aparecem como 'não identificado no documento' (nunca em branco silencioso); "
       "nenhum valor sugerido é apresentado como extraído; se houver sugestão, ela é rotulada como "
       "sugestão.",
       "Evidência (print) anexada.", "§16 itens 9 e 13", ambiente="Interface"),

    ct("CT-086", S, "RF-27", "", "Erro", "Usabilidade", "Caso de uso", "Alta",
       "Erros na interface orientam a ação e não expõem detalhe interno",
       "Validar §11 item 7.",
       "Interface React no ar.", "Validacao_ArquivoDocx; Validacao_ArquivoGrande; Qualidade_Pdf_Corrompido",
       ["Provocar erro de formato, de tamanho e de documento corrompido",
        "Ler a mensagem exibida"],
       "Cada erro indica ação possível (corrigir arquivo, tentar novamente, consultar ID); nenhum "
       "stack trace, prompt ou segredo na tela; mensagem em português claro.",
       "Evidência (print) anexada.", "§16 item 13", ambiente="Interface"),

    ct("CT-087", S, "RF-27; RF-26", "", "Transversal", "Usabilidade", "Caso de uso", "Média",
       "Histórico na interface é ordenado por data com status e motivo",
       "Validar §11 item 8.",
       "Interface React no ar.", "Matriz_Receituario_Pdf",
       ["Abrir o histórico de uma triagem com vários eventos",
        "Conferir ordem, data, status e motivo"],
       "Eventos em ordem cronológica com data/hora, status anterior→novo e motivo; nenhum evento "
       "oculto ou fora de ordem.",
       "Evidência (print) anexada.", "§16 item 11", ambiente="Interface"),

    ct("CT-088", S, "RF-27", "", "Transversal", "Usabilidade", "Caso de uso", "Média",
       "Interface esclarece que destinos, alertas e fila são simulados no MVP",
       "Evitar promessa de integração não entregue.",
       "Interface React no ar.", "Matriz_Receituario_Pdf; Matriz_LaudoDeImagem_Pdf",
       ["Abrir tela de resultado e a fila de revisão",
        "Procurar o aviso de simulação"],
       "Aviso visível de que destinos e alertas são simulados e de que a fila é lógica, sem aprovação/"
       "rejeição humana no MVP; nenhum botão sugere decisão do auditor.",
       "Evidência (print) anexada.", "§16 itens 7 e 15", ambiente="Interface"),

    ct("CT-089", S, "RF-03; RF-27", "", "Erro", "Funcional negativo", "Partição de equivalência", "Média",
       "Validação de tipo e tamanho acontece no cliente e é refeita na API",
       "Provar defesa em profundidade: usabilidade no cliente, segurança no servidor.",
       "Interface React no ar.", "Validacao_ArquivoDocx; Validacao_ArquivoGrande",
       ["Selecionar arquivo com extensão não permitida na tela",
        "Selecionar arquivo acima do limite na tela",
        "Enviar diretamente à API, ignorando a tela, um arquivo inválido"],
       "A tela impede o envio com mensagem clara; a API rejeita igualmente com 415/413 quando chamada "
       "diretamente; nenhum dos dois caminhos chega ao modelo.",
       "Nenhum objeto gravado.", "§16 item 13", ambiente="Ambos"),
]

# =====================================================================
# SUITE 9 — Requisitos não funcionais (RNF-01 a RNF-11)
# =====================================================================
S = "Não funcionais"
CASOS += [
    ct("CT-090", S, "RNF-02", "RN-02; RN-03", "Urgência", "Não funcional", "Análise de risco", "Alta",
       "Nenhum caso urgente é roteado apenas como rotina",
       "Verificação agregada de segurança clínica sobre toda a massa urgente.",
       PRE_API + " Bateria completa disponível.", "Matriz_Receituario_Imagem; Matriz_LaudoDeImagem_*; "
                                                "Matriz_Guia_Imagem; Conflito_AltoRisco; "
                                                "Simultaneo_Urgencia_*; Conflito_Prioridade",
       ["Executar os 7 documentos com sinal de urgência",
        "Conferir destino de cada um",
        "Repetir a bateria 3 vezes para detectar não determinismo"],
       "7/7 com FILA_URGENCIA_MEDICA presente nos destinos e alerta registrado, em todas as 3 "
       "execuções; nenhuma execução isolada roteia urgência apenas para destino de rotina.",
       "Evidência anexada.", "§16 item 3", obs="Requisito de segurança clínica: falha aqui bloqueia o MVP."),

    ct("CT-091", S, "RNF-03", "", "Erro", "Não funcional", "Análise de risco", "Alta",
       "Indisponibilidade de dependências é observável e não perde documento",
       "Validar confiabilidade com falhas de Gemini e de OCI.",
       PRE_API + " Stubs de indisponibilidade.", "Matriz_Guia_Pdf",
       ["Derrubar Gemini durante a análise", "Derrubar o storage durante a gravação",
        "Restabelecer e reprocessar"],
       "Os dois cenários geram status de erro observável e rastreável; o original não é perdido; o "
       "reenvio conclui com sucesso; nenhum sucesso falso é reportado.",
       "Evidência anexada.", "§16 item 10"),

    ct("CT-092", S, "RNF-06", "", "Transversal", "Não funcional", "Contrato", "Alta",
       "Saída é JSON válido e tipado contra o contrato versionado",
       "Garantir interoperabilidade do payload.",
       "Ambiente com o schema do projeto publicado (Pydantic/OpenAPI).", "Matriz_*",
       ["Coletar as respostas de uma execução completa da matriz",
        "Validar cada resposta contra o schema",
        "Conferir versão declarada"],
       "100% das respostas válidas; nenhum campo extra não previsto; enums apenas com valores "
       "permitidos; versão declarada presente.",
       "Relatório de validação anexado.", "§16 item 11"),

    ct("CT-093", S, "RNF-07", "", "Urgência", "Não funcional", "Análise de risco", "Média",
       "Latência por etapa é medida, inclusive no fluxo urgente",
       "Criar base para a meta de agilidade ainda pendente.",
       PRE_API + " Instrumentação de tempo habilitada.", "Matriz_LaudoDeImagem_Pdf",
       ["Executar 10 triagens urgentes",
        "Coletar tempo de upload, inferência, decisão e persistência",
        "Registrar mediana e p95"],
       "Tempos por etapa registrados e recuperáveis; resultado reprodutível entre execuções; valor "
       "medido documentado para definição da meta.",
       "Relatório de latência anexado.", "§16 item 12",
       obs=f"Meta numérica de latência {PENDENTE}; o caso mede, não aprova."),

    ct("CT-094", S, "RNF-08", "", "Transversal", "Não funcional", "Análise de risco", "Alta",
       "Somente dados fictícios e nenhum segredo em repositório, logs ou respostas",
       "Validar privacidade e higiene de credenciais.",
       "Repositório clonado e ambiente de homologação.", "tests/fixtures (67 documentos)",
       ["Varrer o repositório por credenciais e dados pessoais reais",
        "Varrer logs de execução",
        "Varrer corpos de resposta e interface"],
       "Nenhuma credencial versionada; documentos com marca de fictício; logs sem nome de paciente "
       "completo e sem chave; .env fora do Git; nenhum dado de pessoa real.",
       "Evidência anexada.", "§16 itens 13 e 15"),

    ct("CT-095", S, "RNF-09", "", "Transversal", "Não funcional", "Inspeção", "Média",
       "README, diagrama e separação do adaptador estão atualizados",
       "Validar manutenibilidade do entregável.",
       "Repositório na versão da entrega.", "",
       ["Ler README e conferir arquitetura, grafo de decisão e instruções de execução",
        "Verificar se o adaptador LLM está isolado do restante",
        "Executar os comandos documentados em ambiente limpo"],
       "README descreve arquitetura, grafo e execução; comandos funcionam como documentado; o adaptador "
       "é substituível sem tocar nas regras; histórico de commits rastreável.",
       "Evidência anexada.", "§16 item 14", ambiente="Repositório"),

    ct("CT-096", S, "RNF-10", "", "Transversal", "Não funcional", "Análise de risco", "Média",
       "Modelo é substituível sem refazer as regras de decisão",
       "Provar o teste contratual do adaptador.",
       "Adaptador Gemini isolado atrás de interface.", "",
       ["Trocar o adaptador por um stub equivalente",
        "Executar a bateria de decisão",
        "Comparar decisões com a execução original"],
       "Mesmas decisões para os mesmos sinais; nenhuma regra de negócio alterada na troca; apenas a "
       "camada de integração muda.",
       "Evidência anexada.", "§16 item 15"),

    ct("CT-097", S, "RNF-11", "", "Transversal", "Não funcional", "Revisão", "Média",
       "Os três fluxos obrigatórios são demonstráveis de ponta a ponta",
       "Validar usabilidade e completude da demonstração do MVP.",
       "Ambiente de demonstração com os 12 fixtures do kit.", "Matriz_Receituario_Pdf; "
                                                            "Matriz_LaudoDeImagem_Pdf; Ausencia_Paciente_Nome",
       ["Executar o fluxo padrão", "Executar o fluxo urgente", "Executar o fluxo ambíguo",
        "Pedir a alguém externo à equipe para repetir sem ajuda"],
       "Os três fluxos rodam sem intervenção manual no código; a pessoa externa identifica tipo, "
       "prioridade, destino e justificativa; nenhuma etapa exige editar arquivo.",
       "Roteiro de demonstração anexado.", "§16 item 14"),

    ct("CT-098", S, "RNF-04", "", "Transversal", "Não funcional", "Inspeção", "Alta",
       "Toda decisão é auditável: ator, motivo, status e versões",
       "Fechar a exigência de rastreabilidade do MVP.",
       PRE_API, "Matriz_Guia_Pdf; Ausencia_Paciente_Nome; Conflito_Dose",
       ["Para cada triagem, coletar histórico e decisão",
        "Conferir ator, motivo, status anterior/novo, versão de regra e de esquema"],
       "Nenhum evento sem ator, motivo ou versão; correlação da requisição presente; consulta "
       "autorizada e ordenada.",
       "Evidência anexada.", "§16 itens 11 e 12"),

    ct("CT-099", S, "RNF-05", "", "Transversal", "Não funcional", "Inspeção", "Média",
       "Consumo de recursos permanece no Always Free",
       "Evitar custo e violação da restrição do brief.",
       "Conta OCI com painel de consumo acessível.", "",
       ["Revisar recursos provisionados", "Executar a bateria completa",
        "Conferir consumo e alertas de limite"],
       "Somente recursos Always Free; nenhum serviço pago habilitado; consumo dentro do limite durante "
       "a bateria; configuração registrada no README.",
       "Print do painel anexado.", "§16 item 10"),

    ct("CT-100", S, "RNF-01", "", "Transversal", "Não funcional", "Inspeção", "Média",
       "Casos de demonstração têm resultado esperado aprovado e métrica declarada",
       "Evitar alegar precisão sem conjunto de validação.",
       "67 expected.json revisados pela equipe.", "tests/fixtures (67 documentos)",
       ["Executar a bateria completa e comparar por asserção",
        "Calcular acertos por tipo e por cenário",
        "Conferir se a meta numérica está declarada"],
       "Relatório com acertos por bloco e por asserção; nenhuma alegação de precisão sem número; meta "
       "declarada ou explicitamente pendente no README.",
       "Relatório anexado.", "§16 itens 2 a 5",
       obs=f"Meta numérica de precisão {PENDENTE}."),
]


for _caso in CASOS:
    if _caso["ID_CASO"] in AUTO_MANUAL:
        _caso["AUTOMATIZAVEL"] = AUTO_MANUAL[_caso["ID_CASO"]]
    if _caso["ID_CASO"] in PRIORIDADE_BAIXA:
        _caso["PRIORIDADE"] = "Baixa"


# =====================================================================
# Geração
# =====================================================================
def fixtures_do_manifest() -> list[str]:
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        return [linha["id"] for linha in csv.DictReader(f)]


def expandir_massa(massa: str, fixtures: list[str]) -> set[str]:
    """Expande `Matriz_Guia_*` e nomes exatos nos IDs do manifesto."""
    achados: set[str] = set()
    for bruto in massa.split(";"):
        token = bruto.split(" (")[0].strip()
        if not token:
            continue
        achados.update(f for f in fixtures if fnmatch.fnmatch(f, token))
    return achados


def gravar_csv() -> None:
    os.makedirs(os.path.dirname(SAIDA_CSV), exist_ok=True)
    with open(SAIDA_CSV, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS, delimiter=";",
                                  quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        escritor.writeheader()
        escritor.writerows(CASOS)


def validar(fixtures: list[str]) -> list[str]:
    erros = []
    ids = [c["ID_CASO"] for c in CASOS]
    if len(ids) != len(set(ids)):
        erros.append("ID_CASO duplicado")
    obrigatorios = ["ID_CASO", "SUITE", "ID_REQUISITO", "CENARIO", "TIPO_TESTE", "PRIORIDADE",
                    "TITULO", "OBJETIVO", "PRE_CONDICOES", "PASSOS", "RESULTADO_ESPERADO",
                    "CRITERIO_DE_ACEITE"]
    for c in CASOS:
        for campo in obrigatorios:
            if not str(c[campo]).strip():
                erros.append(f"{c['ID_CASO']}: campo obrigatório vazio ({campo})")
        if c["CENARIO"] not in {"Rotina", "Urgência", "Ambiguidade", "Erro", "Transversal"}:
            erros.append(f"{c['ID_CASO']}: cenário fora do padrão ({c['CENARIO']})")
        if c["PRIORIDADE"] not in {"Alta", "Média", "Baixa"}:
            erros.append(f"{c['ID_CASO']}: prioridade fora do padrão")

    # cobertura de requisitos: RF-01..30, RN-01..07, RNF-01..11
    citados = set()
    for c in CASOS:
        for campo in ("ID_REQUISITO", "REGRAS_NEGOCIO", "TITULO", "OBJETIVO",
                      "RESULTADO_ESPERADO", "PASSOS", "OBSERVACOES"):
            for parte in str(c[campo]).replace("/", " ").replace(";", " ").replace(",", " ").split():
                parte = parte.strip("().")
                if parte.startswith(("RF-", "RN-", "RNF-")):
                    citados.add(parte)
    esperados = ({f"RF-{i:02d}" for i in range(1, 31)}
                 | {f"RN-{i:02d}" for i in range(1, 8)}
                 | {f"RNF-{i:02d}" for i in range(1, 12)})
    faltando = sorted(esperados - citados)
    if faltando:
        erros.append("requisitos sem caso: " + ", ".join(faltando))

    # cobertura de massa: todo fixture citado ao menos uma vez
    cobertos: set[str] = set()
    for c in CASOS:
        cobertos |= expandir_massa(c["MASSA_DE_DADOS"], fixtures)
    sem_caso = sorted(set(fixtures) - cobertos)
    if sem_caso:
        erros.append("fixtures sem caso: " + ", ".join(sem_caso))

    # itens de aceite §16 (1..15)
    aceites = set()
    for c in CASOS:
        for parte in c["CRITERIO_DE_ACEITE"].replace(",", " ").replace("e", " ").split():
            if parte.isdigit():
                aceites.add(int(parte))
    faltando_aceite = sorted(set(range(1, 16)) - aceites)
    if faltando_aceite:
        erros.append("itens de aceite §16 sem caso: " + ", ".join(map(str, faltando_aceite)))
    return erros


def gerar_guia(fixtures: list[str]) -> None:
    por_suite = Counter(c["SUITE"] for c in CASOS)
    por_tipo = Counter(c["TIPO_TESTE"] for c in CASOS)
    por_prioridade = Counter(c["PRIORIDADE"] for c in CASOS)
    por_cenario = Counter(c["CENARIO"] for c in CASOS)
    por_auto = Counter(c["AUTOMATIZAVEL"] for c in CASOS)

    req_para_casos: dict[str, list[str]] = defaultdict(list)
    for c in CASOS:
        for campo in ("ID_REQUISITO", "REGRAS_NEGOCIO"):
            for parte in str(c[campo]).replace("/", " ").replace(";", " ").split():
                parte = parte.strip("().")
                if parte.startswith(("RF-", "RN-", "RNF-")):
                    req_para_casos[parte].append(c["ID_CASO"])
    for k in req_para_casos:
        req_para_casos[k] = sorted(set(req_para_casos[k]))

    fixture_para_casos: dict[str, list[str]] = defaultdict(list)
    for c in CASOS:
        for f in sorted(expandir_massa(c["MASSA_DE_DADOS"], fixtures)):
            fixture_para_casos[f].append(c["ID_CASO"])

    linhas = []
    a = linhas.append
    a("# EPT — MediFlow · guia de uso e cobertura\n")
    a("**Projeto:** hackatoon_oracle / MediFlow — Hackathon ONE G10  ")
    a("**Artefato principal:** [`EPT_MediFlow_v1.0.csv`](EPT_MediFlow_v1.0.csv)  ")
    a("**Base:** `MediFlow_Especificacao_Funcional_v1.0.pdf` (RF-01…RF-30, RN-01…RN-07, "
      "RNF-01…RNF-11, §8.2, §10, §11, §12, §16) + os 67 fixtures de "
      "[`manifest.csv`](../../tests/fixtures/manifest.csv)  ")
    a(f"**Casos:** {len(CASOS)} — gerado por [`tools/gerar_ept.py`](../../tools/gerar_ept.py); "
      "não editar o CSV à mão, editar o gerador.\n")
    a("---\n")
    a("## 1. O que é esta EPT\n")
    a("Uma **Especificação de Procedimento de Teste**: uma linha por caso, com pré-condição, massa, "
      "passos numerados, resultado esperado verificável, rastreabilidade ao requisito e colunas de "
      "execução para o executor preencher. A EPT não substitui o catálogo de fixtures: ele é a "
      "**massa** citada na coluna `MASSA_DE_DADOS`.\n")
    a("Diferença prática:\n")
    a("| Artefato | Responde |")
    a("| --- | --- |")
    a("| `CATALOGO_DE_DOCUMENTOS_DE_TESTE.md` | **O que existe** para testar (67 documentos) |")
    a("| `CONTRATO_DE_DADOS.md` / `app/models.py` | **O que é uma resposta válida** |")
    a("| `EPT_MediFlow_v1.0.csv` (esta) | **Como executar e como saber se passou** |")
    a("| `EPT_MediFlow_preview.html` | **A mesma EPT navegável**: filtros por suíte/cenário/prioridade, "
      "detalhe do caso e as matrizes de cobertura |\n")
    a("## 2. Como o arquivo está montado\n")
    a("| Item | Escolha | Por quê |")
    a("| --- | --- | --- |")
    a("| Codificação | UTF-8 **com BOM** | Excel pt-BR abre acento corretamente |")
    a("| Separador | `;` | padrão de planilha em português |")
    a("| Fim de linha | CRLF | compatível com Excel/Sheets |")
    a("| Quebra de linha na célula | nenhuma | evita linha “quebrada” na importação |")
    a("| Passos | `1) …` até `N) …` na mesma célula | mantém um caso por linha |")
    a("| Listas | `;` ou `*` (curinga de fixture) | `Matriz_Guia_*` expande para os 3 formatos |\n")
    a("Se a sua planilha usar `,` como separador, ajuste `delimiter` em `gravar_csv()` e rode o "
      "gerador de novo — ou importe no Excel com “separado por ponto e vírgula”.\n")
    a("## 3. Dicionário de dados\n")
    a("| Coluna | O que vai nela | Regra de preenchimento |")
    a("| --- | --- | --- |")
    a("| `ID_CASO` | identificador único (`CT-001`) | imutável; usado em evidência e defeito |")
    a("| `SUITE` | agrupamento funcional | 9 suítes: ingestão, classificação, extração, confiança, "
      "decisão, persistência, API, interface, não funcionais |")
    a("| `ID_REQUISITO` | RF/RNF da especificação | rastreabilidade para cima |")
    a("| `REGRAS_NEGOCIO` | RN aplicada | vazio quando não há regra de negócio |")
    a("| `CENARIO` | `Rotina`, `Urgência`, `Ambiguidade`, `Erro` ou `Transversal` | espelha os "
      "cenários de §16 |")
    a("| `TIPO_TESTE` | funcional, negativo, borda, integração, não funcional, usabilidade, segurança |")
    a("| `TECNICA` | valor limite, partição de equivalência, tabela de decisão, caso de uso, contrato, "
      "análise de risco |")
    a("| `PRIORIDADE` | `Alta` (bloqueia o MVP), `Média` (entra na entrega), `Baixa` |")
    a("| `TITULO` | uma frase, no imperativo | começa pelo verbo |")
    a("| `OBJETIVO` | o que a falha provaria | não repetir o título |")
    a("| `PRE_CONDICOES` | ambiente, dados e configuração | se faltar, o caso é bloqueado |")
    a("| `MASSA_DE_DADOS` | fixture(s) do catálogo | aceita `*` e `;` |")
    a("| `PASSOS` | passos numerados | cada passo tem ação verificável |")
    a("| `RESULTADO_ESPERADO` | asserções objetivas | valores e códigos, não “funciona bem” |")
    a("| `CRITERIO_DE_ACEITE` | item de §16 | usado no relatório de aceite |")
    a("| `AUTOMATIZAVEL` | `Sim`, `Parcial`, `Não` | orienta a automação |")
    a("| `AMBIENTE` | `API`, `Interface`, `Ambos`, `Repositório` | onde executar |")
    a("| `OBSERVACOES` | pendências, cuidados, dependências | `PENDENTE (§15)` marca bloqueio |")
    a("| `STATUS_EXECUCAO` | começa `NAO EXECUTADO` | valores: `PASSOU`, `FALHOU`, `BLOQUEADO`, "
      "`NAO APLICAVEL` |")
    a("| `RESULTADO_OBTIDO`, `EVIDENCIA`, `DEFEITO`, `DATA_EXECUCAO`, `EXECUTOR` | preenchidos na "
      "execução | evidência = print/log/arquivo; defeito = ID do bug |\n")
    a("## 4. Como executar (ordem recomendada)\n")
    a("1. **CT-001 a CT-012** (ingestão) — sem isso, nenhum outro caso tem massa válida.")
    a("2. **CT-049 a CT-063** (decisão) com `FIXTURE_MODE` nos casos de borda.")
    a("3. **CT-013 a CT-048** (classificação e extração) — o núcleo clínico.")
    a("4. **CT-066 a CT-080** (persistência, API e erros).")
    a("5. **CT-081 a CT-089** (interface) e **CT-090 a CT-100** (não funcionais) no fechamento.\n")
    a("Nos casos de borda (`CT-020`, `CT-044`, `CT-045`, `CT-046`, `CT-054`, `CT-062`) ative o "
      "`FIXTURE_MODE` e use `modo_fixture.score_forcado` do `expected.json`: score do LLM não é "
      "determinístico e não deve ser comparado por igualdade.\n")
    a("## 5. Cobertura\n")
    a("### 5.1 Por suíte\n")
    a("| Suíte | Casos |")
    a("| --- | ---: |")
    for suite, qtd in sorted(por_suite.items(), key=lambda x: x[0]):
        a(f"| {suite} | {qtd} |")
    a(f"| **Total** | **{len(CASOS)}** |\n")
    a("### 5.2 Por tipo, cenário, prioridade e automação\n")
    a("| Tipo de teste | Casos | Cenário | Casos | Prioridade | Casos | Automação | Casos |")
    a("| --- | ---: | --- | ---: | --- | ---: | --- | ---: |")
    tipos = sorted(por_tipo.items(), key=lambda x: (-x[1], x[0]))
    cenario = sorted(por_cenario.items(), key=lambda x: (-x[1], x[0]))
    prior = sorted(por_prioridade.items(), key=lambda x: (-x[1], x[0]))
    auto = sorted(por_auto.items(), key=lambda x: (-x[1], x[0]))
    for i in range(max(len(tipos), len(cenario), len(prior), len(auto))):
        t = tipos[i] if i < len(tipos) else ("", "")
        c_ = cenario[i] if i < len(cenario) else ("", "")
        p = prior[i] if i < len(prior) else ("", "")
        au = auto[i] if i < len(auto) else ("", "")
        a(f"| {t[0]} | {t[1]} | {c_[0]} | {c_[1]} | {p[0]} | {p[1]} | {au[0]} | {au[1]} |")
    a("")
    a("### 5.3 Requisito → casos\n")
    a("| Requisito | Casos |")
    a("| --- | --- |")
    for req in sorted(req_para_casos, key=lambda r: (r.split("-")[0], int(r.split("-")[1]))):
        a(f"| {req} | {', '.join(req_para_casos[req])} |")
    a("")
    a("### 5.4 Massa → casos\n")
    a(f"Os {len(fixtures)} fixtures do `manifest.csv` são citados em pelo menos um caso "
      f"({len({f for f in fixtures if f in fixture_para_casos})}/{len(fixtures)} cobertos "
      f"diretamente). Curingas como `Matriz_*` cobrem os demais sem repetir 24 linhas idênticas.\n")
    a("<details><summary>Mapa completo fixture → caso</summary>\n")
    a("| Fixture | Casos |")
    a("| --- | --- |")
    for f in fixtures:
        a(f"| `{f}` | {', '.join(fixture_para_casos.get(f, [])) or '—'} |")
    a("\n</details>\n")
    a("### 5.5 Itens de aceite do MVP (§16) → casos\n")
    a("| Item de §16 | Casos que provam o item |")
    a("| ---: | --- |")
    aceite_para_casos: dict[int, list[str]] = defaultdict(list)
    for c in CASOS:
        for parte in c["CRITERIO_DE_ACEITE"].replace(",", " ").split():
            for token in parte.split():
                if token.isdigit():
                    aceite_para_casos[int(token)].append(c["ID_CASO"])
    for item in range(1, 16):
        a(f"| {item} | {', '.join(sorted(set(aceite_para_casos.get(item, [])))) or '—'} |")
    a("")
    a("## 6. Pendências que bloqueiam ou limitam casos\n")
    a("A própria especificação (§15) lista definições que a equipe precisa fechar. Elas aparecem "
      "aqui como risco de execução, não como falha de teste:\n")
    a("| Pendência (§15) | Casos afetados |")
    a("| --- | --- |")
    a("| Limite de tamanho, páginas e MIME | CT-010, CT-089 |")
    a("| Timeout e política de retry | CT-078, CT-091 |")
    a("| Dicionário de alto risco / conflitos | CT-019, CT-033, CT-036 |")
    a("| Autenticação e autorização | CT-071, CT-075 |")
    a("| Meta de latência e de precisão | CT-093, CT-100 |")
    a("| Formato final do upload | CT-001, CT-002, CT-012 |\n")
    a("## 7. Adaptando ao template da sua área\n")
    a("O conteúdo não muda; só o cabeçalho. Se a Função Sistemas tiver um modelo próprio, ajuste a "
      "constante `COLUNAS` e o dicionário de mapeamento em `tools/gerar_ept.py` e rode de novo — o "
      "CSV continua reprodutível. Mapeamento usual:\n")
    a("| Nossa coluna | Equivalentes comuns |")
    a("| --- | --- |")
    a("| `ID_CASO` | ID, Código do caso, CT |")
    a("| `TITULO` | Caso de teste, Descrição, Cenário |")
    a("| `PRE_CONDICOES` | Pré-requisitos, Setup |")
    a("| `MASSA_DE_DADOS` | Massa, Dados de entrada |")
    a("| `PASSOS` | Procedimento, Passos para execução, Roteiro |")
    a("| `RESULTADO_ESPERADO` | Resultado esperado, Saída esperada |")
    a("| `RESULTADO_OBTIDO` | Resultado obtido, Evidência de execução |")
    a("| `STATUS_EXECUCAO` | Status, Situação, Aprovado/Reprovado |")
    a("| `DEFEITO` | ID do defeito, Bug, Chamado |\n")
    a("## 8. Verificação automática\n")
    a("```bash")
    a("python3 tools/gerar_ept.py --check   # falha se faltar requisito, fixture ou item de aceite")
    a("python3 tools/gerar_ept.py           # regrava o CSV e este guia")
    a("```\n")
    a("Para ler a EPT no navegador, sem planilha:\n")
    a("```bash")
    a("python3 tools/gerar_ept_preview.py   # docs/testes/EPT_MediFlow_preview.html (arquivo único)")
    a("```\n")
    a("O verificador garante: IDs únicos, campos obrigatórios preenchidos, enums de cenário e "
      "prioridade válidos, cobertura de **RF-01…RF-30**, **RN-01…RN-07**, **RNF-01…RNF-11**, "
      f"cobertura dos **{len(fixtures)} fixtures** e dos **15 itens de aceite de §16**.\n")
    with open(SAIDA_GUIA, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))


def main() -> int:
    fixtures = fixtures_do_manifest()
    erros = validar(fixtures)
    if erros:
        print("EPT inconsistente:")
        for e in erros:
            print("  -", e)
        if "--check" in sys.argv:
            return 1
    if "--check" in sys.argv:
        print(f"OK — {len(CASOS)} casos, {len(fixtures)} fixtures, requisitos cobertos.")
        return 0
    gravar_csv()
    gerar_guia(fixtures)
    print(f"CSV:   {os.path.relpath(SAIDA_CSV, ROOT)} ({len(CASOS)} casos)")
    print(f"Guia:  {os.path.relpath(SAIDA_GUIA, ROOT)}")
    if erros:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

