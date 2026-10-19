# Catálogo de documentos de teste — MediFlow

**Projeto:** hackatoon_oracle / MediFlow — Hackathon ONE G10
**Versão:** 1.0 — 19/10/2026
**Base documental:** `Projeto_oracle.pdf`, `MediFlow_-_Análise_de_Requisitos_v1.1.pdf` e `MediFlow_Especificacao_Funcional_v1.0.pdf`
**Manifesto executável:** [`tests/fixtures/manifest.csv`](../../tests/fixtures/manifest.csv)

---

## 1. Resposta curta

Você não precisa de um documento por especialidade médica. Precisa de **um documento por tipo controlado × formato**, mais um conjunto pequeno de **variações deliberadas** para provar as regras de revisão, o limiar de confiança, os conflitos e os erros.

| Nível | Quantidade | Para que serve |
| --- | ---: | --- |
| **Kit de demonstração** | **12 arquivos** ✅ | Cobre os 3 cenários obrigatórios, os 5 destinos, os 3 formatos e as 8 classes de tipo. É o mínimo defensável para o pitch. |
| **Kit recomendado** | **57 arquivos** ✅ | Cobre tipos × formatos, ausência de campos, limiar, conflitos, urgência simultânea, qualidade de imagem e negativos técnicos. É o conjunto que eu levaria para a banca. |
| **Kit completo** | **67 arquivos** ✅ | Acrescenta PDF digitalizado para todos os tipos e os 4 casos de diferenciais (OCR, carimbo, tabela de exames, guia TISS). |
| **Simulações operacionais** | **8 cenários, 0 documentos novos** | Falhas de Gemini e de OCI, testadas por stub/flag reutilizando os documentos acima. |

> **Mínimo literal dos critérios de aceite (seção 16 da especificação): 8 arquivos.** Três rendições do mesmo conteúdo (texto, PDF e imagem) + cinco variações de campo ausente. Esse número passa na leitura literal, mas não prova os 5 destinos nem os 8 tipos — por isso não recomendo usá-lo como meta.

**Distribuição do kit completo (67):** 19 PDFs digitais, 7 PDFs digitalizados, 16 imagens, 17 textos e 8 arquivos inválidos. Por desfecho: 29 de rotina, 7 de urgência, 21 de ambiguidade e 10 de erro.

> **Status: 67 de 67 fixtures produzidos.** O kit de demonstração está em [`tests/fixtures/demo/`](../../tests/fixtures/demo/) — 12 casos × (TXT + PDF + JPG + `expected.json`) = 48 arquivos. O restante está em [`tests/fixtures/catalogo/`](../../tests/fixtures/catalogo/) — 47 casos funcionais × 4 arquivos + 8 negativos técnicos = 196 arquivos. O mapa visual dos 67 está em [Mapa_de_Documentos_de_Teste_MediFlow.pdf](Mapa_de_Documentos_de_Teste_MediFlow.pdf).

---

## 2. O que o sistema precisa avaliar

Tudo abaixo vem da especificação funcional v1.0 e define as dimensões do catálogo.

| Dimensão | Valores | Fonte |
| --- | --- | --- |
| **Tipo de documento** | `RECEITUARIO_MEDICO`, `LAUDO_EXAME_LABORATORIAL`, `LAUDO_EXAME_IMAGEM`, `GUIA_PROCEDIMENTO`, `RELATORIO_ALTA_INTERNACAO`, `ATESTADO_MEDICO`, `OUTRO`, `NAO_IDENTIFICADO` | §5.1 |
| **Formato de entrada** | PDF digital, PDF digitalizado, imagem (JPG/PNG) e texto | RF-02, §3.1 |
| **Prioridade** | `URGENTE`, `ROTINA`, `NAO_IDENTIFICADA` | §5.2 |
| **Status** | `RECEBIDO`, `PROCESSANDO`, `PROCESSADO`, `EM_REVISAO`, `ERRO_PROCESSAMENTO`, `ERRO_PERSISTENCIA` | §5.3 |
| **Destino lógico** | `FILA_URGENCIA_MEDICA`, `FARMACIA_HOSPITALAR`, `AUDITORIA_AUTORIZACOES`, `PRONTUARIO_ELETRONICO`, `FILA_REVISAO_HUMANA` | §5.4 |
| **Desfecho do cenário** | rotina, urgência, ambiguidade/ilegibilidade, erro | §8.2, §16 |

### Duas leituras importantes

1. **`OUTRO` e `NAO_IDENTIFICADO` são resultados de classificação, não tipos que se "escrevem".** Você não cria um atestado "não identificado": você cria um documento fora da taxonomia (declaração de acompanhante, relatório de enfermagem) ou um documento ilegível, e o sistema deve devolver `OUTRO` ou `NAO_IDENTIFICADO`. Por isso o bloco M tem 3 arquivos para cada um: são **testes negativos de classificação**, não documentos clínicos válidos.
2. **JSON não é um tipo de documento.** O JSON é o envelope da API (`documento_texto`, `metadados`, `canal_origem`). Um texto enviado como JSON continua sendo um documento de texto. Não é preciso criar "um JSON por tipo".

---

## 3. Por que 24 não bastam

A matriz 8 tipos × 3 formatos = **24** é o piso, não o teto. A especificação exige comportamentos que só aparecem quando você **quebra uma coisa de cada vez**:

- **RF-21** lista 5 campos cuja ausência obriga revisão (nome do paciente, idade, nome do médico, CRM, diagnóstico) e 3 cuja ausência **não** obriga (CID, medicamentos, exames). São 8 asserções diferentes.
- **RF-18** exige o comportamento nas duas bordas do limiar: `0,84` revisa e `0,85` não revisa. Um único documento não prova as duas.
- **RF-16** pede conflito de CID × diagnóstico, dose suspeita, campos contraditórios e discrepância de prioridade. Cada conflito tem uma regra distinta.
- **§8.2** exige o caso simultâneo de urgência + ambiguidade, com **dois destinos** no mesmo payload.
- **RF-02/RF-04** separam PDF digital de PDF digitalizado; **RF-03** exige rejeições de formato, tamanho, MIME e envelope.

Um mesmo arquivo pode servir a vários **casos de teste** (submissão 202, polling, histórico, persistência), mas não a várias **asserções de conteúdo** — se ele falhar, você não sabe qual regra quebrou.

---

## 4. Contagem por bloco

| Bloco | Para que serve | Arquivos | Acumulado |
| --- | --- | ---: | ---: |
| **M** | Matriz 8 tipos × 3 formatos | 24 | 24 |
| **A** | Ausência de campos (5 que revisam + 3 que não revisam) | 8 | 32 |
| **B** | Fronteira do limiar (0,84 e 0,85) | 2 | 34 |
| **C** | Conflitos, contradições e alto risco | 5 | 39 |
| **S** | Urgência + ambiguidade simultâneas | 2 | 41 |
| **Q** | Qualidade, ilegibilidade e PDFs especiais | 8 | 49 |
| **V** | Negativos técnicos de entrada | 8 | 57 |
| **E** | PDF digitalizado para os 6 tipos restantes | 6 | 63 |
| **D** | Diferenciais opcionais | 4 | **67** |

---

## 5. Bloco M — Matriz tipo × formato (24)

Composição: 6 tipos clínicos × 3 formatos = 18; `OUTRO` × 3 = 3; `NAO_IDENTIFICADO` × 3 = 3.

Regra de Ouro: **PDF = PDF digital com camada de texto** (não escaneado). O PDF digitalizado tem bloco próprio (Q e E), porque o caminho de leitura é diferente.

#### Bloco M — Matriz tipo × formato (24)

| ID | Tipo | Formato | Cenário | Destino(s) esperado(s) | Status | Revisão | O que testa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `M-REC-PDF` | RECEITUARIO_MEDICO | PDF | ROTINA | FARMACIA_HOSPITALAR | PROCESSADO | NAO | Receita médica de rotina, 2 medicamentos, paciente e CRM completos, legível. |
| `M-REC-IMG` | RECEITUARIO_MEDICO | IMAGEM | URGENCIA | FILA_URGENCIA_MEDICA | EM_REVISAO | SIM | Foto de receita com prescrição de alto risco (opioide) e sinal textual de urgência. |
| `M-REC-TXT` | RECEITUARIO_MEDICO | TEXTO | ROTINA | FARMACIA_HOSPITALAR | PROCESSADO | NAO | Texto de receita de rotina com medicamento, dose, via e frequência explícitos. |
| `M-LAB-PDF` | LAUDO_EXAME_LABORATORIAL | PDF | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Hemograma de rotina com resultados nominais, sem medicamentos. |
| `M-LAB-IMG` | LAUDO_EXAME_LABORATORIAL | IMAGEM | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Foto de laudo laboratorial impresso, boa qualidade, rotina. |
| `M-LAB-TXT` | LAUDO_EXAME_LABORATORIAL | TEXTO | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Texto de laudo laboratorial com exames realizados e ausência de CID (não exige revisão). |
| `M-IMG-PDF` | LAUDO_EXAME_IMAGEM | PDF | URGENCIA | FILA_URGENCIA_MEDICA | EM_REVISAO | SIM | Laudo de tomografia com TEP agudo e recomendação de correlação clínica urgente (caso do brief). |
| `M-IMG-IMG` | LAUDO_EXAME_IMAGEM | IMAGEM | URGENCIA | FILA_URGENCIA_MEDICA | EM_REVISAO | SIM | Foto de laudo de raio-X com achado crítico e recomendação de urgência. |
| `M-IMG-TXT` | LAUDO_EXAME_IMAGEM | TEXTO | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Texto de laudo de ultrassom de rotina, sem sinais de urgência. |
| `M-GUI-PDF` | GUIA_PROCEDIMENTO | PDF | ROTINA | AUDITORIA_AUTORIZACOES | PROCESSADO | NAO | Guia de solicitação de ressonância eletiva, diagnóstico e CID explícitos. |
| `M-GUI-IMG` | GUIA_PROCEDIMENTO | IMAGEM | URGENCIA | FILA_URGENCIA_MEDICA | EM_REVISAO | SIM | Foto de guia com pedido de urgência e justificativa clínica crítica. |
| `M-GUI-TXT` | GUIA_PROCEDIMENTO | TEXTO | ROTINA | AUDITORIA_AUTORIZACOES | PROCESSADO | NAO | Texto de guia de procedimento eletivo, sem sinais de risco. |
| `M-ALT-PDF` | RELATORIO_ALTA_INTERNACAO | PDF | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Relatório de alta completo: diagnóstico, CID, medicações de alta e orientações. |
| `M-ALT-IMG` | RELATORIO_ALTA_INTERNACAO | IMAGEM | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Foto de relatório de internação impresso, rotina e legível. |
| `M-ALT-TXT` | RELATORIO_ALTA_INTERNACAO | TEXTO | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Texto de relatório de alta truncado, sem diagnóstico/hipótese: ausência obrigatória. |
| `M-ATE-PDF` | ATESTADO_MEDICO | PDF | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Atestado de afastamento de 3 dias, com CID e CRM completos. |
| `M-ATE-IMG` | ATESTADO_MEDICO | IMAGEM | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Foto de atestado com carimbo e assinatura, dados legíveis. |
| `M-ATE-TXT` | ATESTADO_MEDICO | TEXTO | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Texto de atestado de comparecimento, sem exames e sem medicamentos (não exige revisão). |
| `M-OUT-PDF` | OUTRO | PDF | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Declaração de comparecimento de acompanhante: fora da taxonomia, destino não mapeado. |
| `M-OUT-IMG` | OUTRO | IMAGEM | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Foto de relatório de enfermagem: fora da taxonomia de documentos clínicos do MVP. |
| `M-OUT-TXT` | OUTRO | TEXTO | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Texto administrativo de agendamento, sem dados clínicos: deve resultar em OUTRO + revisão. |
| `M-NID-PDF` | NAO_IDENTIFICADO | PDF | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | PDF escaneado ilegível (manchas/baixa qualidade): NAO_IDENTIFICADO, sem inventar dados. |
| `M-NID-IMG` | NAO_IDENTIFICADO | IMAGEM | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Foto totalmente desfocada de um documento: NAO_IDENTIFICADO e revisão obrigatória. |
| `M-NID-TXT` | NAO_IDENTIFICADO | TEXTO | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Texto genérico sem conteúdo clínico (lista de compras): NAO_IDENTIFICADO e revisão. |

#### Bloco A — Ausência de campos (8)

| ID | Tipo | Formato | Cenário | Destino(s) esperado(s) | Status | Revisão | O que testa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `A-PAC-NOME` | RECEITUARIO_MEDICO | TEXTO | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Receita sem nome do paciente, com todos os demais campos presentes. |
| `A-PAC-IDADE` | RECEITUARIO_MEDICO | TEXTO | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Receita sem idade do paciente, com nome presente. |
| `A-MED-NOME` | LAUDO_EXAME_LABORATORIAL | PDF | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Laudo sem nome do médico solicitante, mantendo CRM preenchido. |
| `A-MED-CRM` | LAUDO_EXAME_LABORATORIAL | PDF | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Laudo sem CRM do solicitante, mantendo nome preenchido. |
| `A-DIAG` | GUIA_PROCEDIMENTO | TEXTO | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Guia sem diagnóstico/hipótese diagnóstica. |
| `A-CID-SO` | LAUDO_EXAME_IMAGEM | PDF | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Laudo com diagnóstico explícito mas sem CID: ausência de CID isolada NÃO exige revisão. |
| `A-MEDIC-SO` | LAUDO_EXAME_LABORATORIAL | TEXTO | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Laudo sem medicamentos (lista vazia): NÃO exige revisão por si só. |
| `A-EXAMES-SO` | ATESTADO_MEDICO | TEXTO | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Atestado sem exames: NÃO exige revisão por si só. |

#### Bloco B — Limiar de confiança (2)

| ID | Tipo | Formato | Cenário | Destino(s) esperado(s) | Status | Revisão | O que testa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `B-084` | RECEITUARIO_MEDICO | TEXTO | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Score combinado forçado em 0,84 (< 0,85): revisão obrigatória. Exige stub de score. |
| `B-085` | RECEITUARIO_MEDICO | TEXTO | ROTINA | FARMACIA_HOSPITALAR | PROCESSADO | NAO | Score combinado exatamente 0,85: NÃO revisa por esse critério isolado. Exige stub de score. |

#### Bloco C — Conflitos e risco (5)

| ID | Tipo | Formato | Cenário | Destino(s) esperado(s) | Status | Revisão | O que testa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `C-CID-CONFLITO` | LAUDO_EXAME_IMAGEM | PDF | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Diagnóstico de lombalgia com CID de infarto agudo (I21): conflito explícito CID × diagnóstico. |
| `C-DOSE` | RECEITUARIO_MEDICO | TEXTO | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Dose 10× acima do usual (ex.: losartana 500 mg): sinaliza conflito sem alterar o valor. |
| `C-PRIORIDADE` | GUIA_PROCEDIMENTO | TEXTO | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Guia marcada como ROTINA no cabeçalho, mas com texto de urgência e sinais críticos. |
| `C-DADOS` | RELATORIO_ALTA_INTERNACAO | PDF | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Relatório com dois nomes/idades divergentes no cabeçalho e no corpo: contradição interna. |
| `C-ALTO-RISCO` | RECEITUARIO_MEDICO | IMAGEM | URGENCIA | FILA_URGENCIA_MEDICA | EM_REVISAO | SIM | Receita de varfarina 10 mg sem texto de urgência: alto risco deve acionar a fila urgente. |

#### Bloco S — Urgência + ambiguidade (2)

| ID | Tipo | Formato | Cenário | Destino(s) esperado(s) | Status | Revisão | O que testa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `S-URG-ILEGIVEL` | RECEITUARIO_MEDICO | IMAGEM | URGENCIA | FILA_URGENCIA_MEDICA + FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Foto de receita urgente parcialmente ilegível: dois destinos, alerta e revisão simultâneos. |
| `S-URG-SCORE` | LAUDO_EXAME_IMAGEM | PDF | URGENCIA | FILA_URGENCIA_MEDICA + FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Laudo legível com urgência e score forçado em 0,70: dois destinos e alerta. Exige stub de score. |

#### Bloco Q — Qualidade, ilegibilidade e PDFs especiais (8)

| ID | Tipo | Formato | Cenário | Destino(s) esperado(s) | Status | Revisão | O que testa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Q-FOTO-DESFOCO` | NAO_IDENTIFICADO | IMAGEM | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Receita manuscrita muito desfocada: não preencher lacunas, encaminhar para revisão. |
| `Q-FOTO-ROTACAO` | LAUDO_EXAME_IMAGEM | IMAGEM | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Laudo fotografado com rotação de 90 graus: testa robustez do pipeline multimodal. |
| `Q-FOTO-CORTADA` | GUIA_PROCEDIMENTO | IMAGEM | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Guia com metade da página fora do enquadramento, sem CRM: ausência obrigatória. |
| `Q-FOTO-BAIXA` | ATESTADO_MEDICO | IMAGEM | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Atestado com sombra e baixo contraste: campos incertos devem ser sinalizados. |
| `Q-PDF-SEM-TEXTO` | LAUDO_EXAME_IMAGEM | PDF_DIGITALIZADO | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | PDF escaneado sem camada de texto (apenas imagem): prova o caminho multimodal do PDF digitalizado. |
| `Q-PDF-MULTIPAGINA` | RELATORIO_ALTA_INTERNACAO | PDF | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Relatório com 6+ páginas: testa limite de páginas e custo. Limite ainda pendente na spec. |
| `Q-PDF-SENHA` | RECEITUARIO_MEDICO | PDF | ERRO | N/A | ERRO_PROCESSAMENTO | N/A | PDF protegido por senha: contrato de erro a definir (rejeitar ou revisar). |
| `Q-PDF-CORROMPIDO` | LAUDO_EXAME_LABORATORIAL | PDF | ERRO | N/A | ERRO_PROCESSAMENTO | N/A | PDF truncado/arquivo corrompido: erro controlado, sem stack trace na resposta. |

#### Bloco V — Negativos técnicos de entrada (8)

| ID | Tipo | Formato | Cenário | Destino(s) esperado(s) | Status | Revisão | O que testa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `V-DOCX` | N/A | DOCX | ERRO | N/A | 415 FORMATO_NAO_SUPORTADO | NAO | Arquivo .docx válido: formato fora do allowlist do MVP. |
| `V-VAZIO` | N/A | ARQUIVO_0KB | ERRO | N/A | 422 CAMPOS_INVALIDOS | NAO | Arquivo de 0 bytes: rejeitar antes de chamar o modelo. |
| `V-JSON-MALFORMADO` | N/A | JSON | ERRO | N/A | 400 REQUISICAO_INVALIDA | NAO | JSON com vírgula final/sintaxe inválida. |
| `V-ENVELOPE` | N/A | JSON | ERRO | N/A | 422 CAMPOS_INVALIDOS | NAO | Envelope JSON vazio ou sem campos obrigatórios. |
| `V-SEM-CONTEUDO` | N/A | MULTIPART | ERRO | N/A | 422 CAMPOS_INVALIDOS | NAO | Requisição sem arquivo e sem documento_texto. |
| `V-ZIP` | N/A | ZIP | ERRO | N/A | 415 FORMATO_NAO_SUPORTADO | NAO | Arquivo .zip: formato não suportado. |
| `V-GRANDE` | N/A | ARQUIVO_25MB | ERRO | N/A | 413 ARQUIVO_MAIOR_QUE_LIMITE | NAO | Arquivo acima do limite configurado. Limite ainda pendente na spec: definir antes. |
| `V-MIME` | N/A | PDF_FALSO | ERRO | N/A | 415/422 MIME_INVALIDO | NAO | Extensão .pdf com conteúdo real de PNG: inconsistência extensão × MIME. |

#### Bloco E — PDFs digitalizados dos 6 tipos restantes (6)

| ID | Tipo | Formato | Cenário | Destino(s) esperado(s) | Status | Revisão | O que testa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `E-REC-PDFSCAN` | RECEITUARIO_MEDICO | PDF_DIGITALIZADO | ROTINA | FARMACIA_HOSPITALAR | PROCESSADO | NAO | Receita impressa escaneada em PDF (com camada de imagem), rotina. |
| `E-LAB-PDFSCAN` | LAUDO_EXAME_LABORATORIAL | PDF_DIGITALIZADO | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Laudo laboratorial escaneado em PDF, rotina. |
| `E-GUI-PDFSCAN` | GUIA_PROCEDIMENTO | PDF_DIGITALIZADO | ROTINA | AUDITORIA_AUTORIZACOES | PROCESSADO | NAO | Guia de procedimento escaneada em PDF, rotina. |
| `E-ALT-PDFSCAN` | RELATORIO_ALTA_INTERNACAO | PDF_DIGITALIZADO | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Relatório de alta escaneado em PDF, rotina. |
| `E-ATE-PDFSCAN` | ATESTADO_MEDICO | PDF_DIGITALIZADO | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Atestado médico escaneado em PDF, rotina. |
| `E-OUT-PDFSCAN` | OUTRO | PDF_DIGITALIZADO | AMBIGUIDADE | FILA_REVISAO_HUMANA | EM_REVISAO | SIM | Documento administrativo escaneado fora da taxonomia: OUTRO + revisão. |

#### Bloco D — Diferenciais opcionais (4)

| ID | Tipo | Formato | Cenário | Destino(s) esperado(s) | Status | Revisão | O que testa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `D-MANUSCRITA` | RECEITUARIO_MEDICO | IMAGEM | ROTINA | FARMACIA_HOSPITALAR | PROCESSADO | NAO | Receita manuscrita legível (letra de médico): diferencial de OCR/visão. |
| `D-CARIMBO` | LAUDO_EXAME_IMAGEM | IMAGEM | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Laudo escaneado com carimbo/assinatura sobreposta ao texto. |
| `D-HEMOGRAMA` | LAUDO_EXAME_LABORATORIAL | PDF | ROTINA | PRONTUARIO_ELETRONICO | PROCESSADO | NAO | Tabela de hemograma com 20 analitos, unidades e valores de referência. |
| `D-GUIA-TISS` | GUIA_PROCEDIMENTO | PDF | ROTINA | AUDITORIA_AUTORIZACOES | PROCESSADO | NAO | Guia no formato TISS com códigos de procedimento e autorização. |

---

## 6. Simulações operacionais (bloco F — 8 cenários, sem documentos novos)

Estas falhas não se testam com um documento novo: testam-se com **stub, flag de ambiente ou mock do adaptador**. Reutilize `M-IMG-PDF` (urgente) ou `M-REC-TXT` (rotina) como entrada.

| ID | Falha simulada | Resultado esperado | Regra |
| --- | --- | --- | --- |
| `F-GEMINI-TIMEOUT` | Gemini não responde no timeout | Retry limitado; se persistir, `ERRO_PROCESSAMENTO` (ou `EM_REVISAO` se já houver sinal de risco) | RF-04, §12 |
| `F-GEMINI-503` | Provedor indisponível (502/503/504) | Erro seguro, sem stack trace; possibilidade de reenvio | RF-04, §10.1 |
| `F-GEMINI-JSON` | Resposta do modelo não valida no Pydantic | Reparo limitado; se falhar, fallback para revisão/erro | RF-14, §12 |
| `F-GEMINI-CAMPO` | Campo desconhecido ou tipo errado na resposta | Não quebrar o consumidor; validar campos obrigatórios e enums | RF-14 |
| `F-OCI-ORIGINAL` | OCI falha ao gravar o original | `ERRO_PERSISTENCIA`; **não** declarar recebimento durável | RF-28/RF-30, §12 |
| `F-OCI-RESULTADO` | OCI falha ao gravar o resultado | `ERRO_PERSISTENCIA`; não marcar sucesso completo | RF-30, §12 |
| `F-ALERTA` | Falha ao registrar o evento de alerta | Preservar a triagem urgente e registrar a falha do evento | §12 |
| `F-RETRY` | Retries esgotados | Estado de erro observável + correlação; permitir reenvio | RF-24 |

---

## 7. Kit de demonstração — os 12 arquivos

Se o tempo apertar, produza **estes 12** primeiro. Eles cobrem os 15 critérios de aceite de forma defensável.

| # | ID | Prova que… |
| ---: | --- | --- |
| 1 | `M-REC-TXT` | Texto é aceito e uma receita de rotina vai para `FARMACIA_HOSPITALAR` |
| 2 | `M-REC-PDF` | PDF digital é aceito e classificado |
| 3 | `M-REC-IMG` | Imagem é aceita e um sinal de urgência nunca vira rotina |
| 4 | `M-IMG-PDF` | Urgência explícita gera `FILA_URGENCIA_MEDICA` + alerta |
| 5 | `M-LAB-PDF` | Laudo laboratorial de rotina vai para `PRONTUARIO_ELETRONICO` |
| 6 | `M-GUI-PDF` | Guia de procedimento vai para `AUDITORIA_AUTORIZACOES` |
| 7 | `M-ALT-PDF` | Relatório de alta é classificado e extraído |
| 8 | `M-ATE-TXT` | Atestado é classificado; ausência de exames não gera revisão |
| 9 | `M-NID-IMG` | Documento ilegível vira `NAO_IDENTIFICADO` + revisão, sem dado inventado |
| 10 | `M-OUT-TXT` | Documento fora da taxonomia vira `OUTRO` + revisão |
| 11 | `A-PAC-NOME` | Ausência de campo obrigatório força `EM_REVISAO` |
| 12 | `B-084` | Score abaixo de 0,85 força `EM_REVISAO` |

**Cobertura do kit:** 5 destinos, 3 formatos, 3 cenários, 8 classes de tipo, 1 ausência obrigatória e 1 caso de limiar.

---

## 8. Artefatos que acompanham cada documento

O documento sozinho não é um teste. Para cada fixture funcional, produza também:

| Artefato | Quantidade | Formato |
| --- | ---: | --- |
| Documento de entrada | 67 | PDF / JPG / PNG / TXT |
| **Saída esperada** (`expected/{ID}.json`) | 67 | JSON com tipo, prioridade, destinos, revisão, campos ausentes e status |
| **Fonte editável** (`source/{ID}.md` ou `.docx`) | 59 | Markdown/DOCX a partir do qual o PDF e a imagem são gerados |
| **Manifesto** | 1 | `tests/fixtures/manifest.csv` (este catálogo, em formato de máquina) |

Para os 8 negativos do bloco V, o "expected" é um **envelope de erro** (HTTP + código funcional), não um JSON de triagem. Para o bloco F, o expected é o estado final após a falha simulada.

**Não compare scores exatos.** O score autorrelatado pelo LLM não é probabilidade calibrada (RF-17). Compare faixas (`< 0,85`, `>= 0,85`, `== 0,85`) e, para os casos de borda B-084/B-085/S-URG-SCORE, use **stub de score** — sem isso o teste é intermitente e não serve como evidência.

---

## 9. Regras de construção dos documentos

1. **Somente dados fictícios**, conforme decisão confirmada da especificação (§15, item 5). Nada de nome, CPF, telefone, CRM ou e-mail de pessoa real.
2. **Marca d'água** em toda página: `DOCUMENTO FICTÍCIO — USO EXCLUSIVO EM TESTES`.
3. **Identidades consistentes**: um mesmo hospital fictício, um mesmo paciente por fixture e um mesmo médico por fixture. Se o paciente muda no meio do documento, isso deve ser um teste de contradição (C-DADOS), não um acidente.
4. **Uma variável por vez**: cada fixture de borda parte de um documento "base" e altera **só** o atributo testado. Se `A-PAC-NOME` também estiver sem CRM, você não sabe qual regra disparou.
5. **CRM no formato `número-UF`** (RF-09), com `numero` e `uf` separados na saída.
6. **CID-10 só quando explícito** (RF-10). Ausência vira `null`, nunca sugestão.
7. **Ground truth revisada por uma pessoa** antes de virar `expected.json`. Um expected errado é pior do que não ter teste.
8. **Sem segredo no fixture**: nenhuma chave, token, URL assinada ou credencial da OCI.
9. **Nada de dado clínico real**, nem "anonimizado". O MVP inteiro é fictício.

---

## 10. Decisões pendentes que travam os testes

A especificação (§15) deixa pontos abertos. Enquanto eles não forem decididos, alguns fixtures não têm resposta esperada inequívoca.

| Pendência | Impacto nos testes | Recomendação para o time |
| --- | --- | --- |
| Limite de tamanho, páginas, MIME, timeout e retry | `V-GRANDE`, `Q-PDF-MULTIPAGINA`, `F-*` não têm limite para validar | Fixar: 10 MB, 10 páginas, `application/pdf` + `image/jpeg` + `image/png` + `text/plain`, timeout 30 s, 2 retries |
| Contrato final do upload (multipart × JSON) | `V-SEM-CONTEUDO`, `V-ENVELOPE`, `V-MIME` | Aceitar multipart para arquivo e JSON para texto; rejeitar os dois vazios |
| Regras clínicas de "achado crítico", "medicamento de alto risco" e conflitos | `C-CID-CONFLITO`, `C-DOSE`, `C-ALTO-RISCO` dependem de dicionário aprovado | Criar `rules/cid10.csv` e `rules/medicamentos_alto_risco.csv` como **dados de referência**, não como documentos de teste |
| **Urgência isolada exige revisão?** | A tabela §8.2 diz "Sim, obrigatória" para urgência; o parágrafo seguinte diz que a revisão é obrigatória **quando coexiste** com ambiguidade/dado ausente/score baixo. A §5.3 inclui "encontrou urgência" em `EM_REVISAO`. O exemplo do `Projeto_oracle.pdf` mostra um caso urgente com `requer_auditoria_humana: false` e status `processado`, o que conflita com a spec. | Padronizar: urgência → `EM_REVISAO` + `FILA_URGENCIA_MEDICA` + alerta; `FILA_REVISAO_HUMANA` só entra quando houver ambiguidade/dado ausente/score baixo. Este catálogo segue a **especificação v1.0** (documento mais recente e normativo), não o exemplo do brief. Registrar a decisão antes de codificar. |
| Autenticação e autorização | `403` e consulta por terceiros não têm contrato | Fora do MVP; se entrar, criar fixtures de acesso negado |
| Política de retenção | Não afeta o conteúdo, mas afeta o teste de persistência | Definir antes de qualquer dado real (que não deve existir no MVP) |
| Meta de latência e precisão | `F-GEMINI-TIMEOUT` e `F-RETRY` dependem do alvo | Medir o primeiro pipeline e então fixar a meta |

**Dica de implementação:** exponha um modo `FIXTURE_MODE` no adaptador Gemini que leia `score_classificacao` e `score_extracao` de um mapa fixo por `documento_id`. Isso torna B-084, B-085 e S-URG-SCORE determinísticos sem alterar a lógica de negócio.

---

## 11. Estrutura de pastas e nomes

```text
tests/fixtures/
├── manifest.csv                  # este catálogo em formato de máquina
├── README.md                     # regras, convenção de nomes e casos especiais
├── demo/                         # ✅ 12 casos de pitch
│   ├── M-REC-TXT/
│   │   ├── M-REC-TXT.txt
│   │   ├── M-REC-TXT.pdf
│   │   ├── M-REC-TXT.jpg
│   │   └── expected.json
│   └── ... (12 pastas)
└── catalogo/                     # ✅ 55 casos restantes
    ├── README.md
    ├── A-PAC-IDADE/ ...          # 47 casos funcionais com 4 arquivos cada
    └── V-GRANDE/                 # 8 negativos técnicos com 1 arquivo inválido cada
```

**Nome do arquivo:** use o ID como prefixo e o formato como sufixo: `M-REC-PDF.pdf`, `M-REC-IMG.jpg`, `M-REC-TXT.txt`. O ID já é único e casa com o `manifest.csv` e o `expected/`.

---

## 12. Como produzir (fluxo de 6 passos)

> **Os 67 fixtures já estão produzidos.** Para recriar: `python3 tools/gerar_fixtures_demo.py` (12 casos), `python3 tools/gerar_fixtures_catalogo.py` (55 casos) e `python3 tools/gerar_mapa_documentos.py` (este catálogo em PDF).

1. **Escolha a fonte**: escreva o conteúdo clínico em `source/{ID}.md`, com dados fictícios e marca d'água.
2. **Gere as três rendições**: texto puro, PDF digital (com camada de texto) e imagem (foto/scan). Para o PDF digitalizado, gere o PDF a partir de uma imagem, sem camada de texto.
3. **Crie as bordas**: para cada fixture dos blocos A, B, C e S, remova ou altere **um único** campo em relação ao documento base.
4. **Escreva o `expected.json`** com tipo, prioridade, destinos, `requer_auditoria_humana`, campos ausentes/incertos, status e regra acionada.
5. **Rode o pipeline** e compare com o expected. Para os blocos V e F, compare o envelope de erro e o status, não o JSON de triagem.
6. **Atualize o manifesto** se algum comportamento mudar — o `manifest.csv` é a fonte de verdade dos testes.

---

## 13. Rastreabilidade com os critérios de aceite (§16)

| Critério | Fixtures que comprovam |
| --- | --- |
| 1. Texto + 1 PDF + 1 imagem aceitos | `M-REC-TXT`, `M-REC-PDF`, `M-REC-IMG` |
| 2. Documento padrão classificado e roteado | `M-REC-*`, `M-LAB-*`, `M-GUI-*`, `M-ALT-*`, `M-ATE-*` |
| 3. Documento urgente com alerta | `M-IMG-PDF`, `M-IMG-IMG`, `M-GUI-IMG`, `C-ALTO-RISCO` |
| 4. Documento ambíguo/ilegível em revisão | `M-NID-*`, `Q-FOTO-DESFOCO`, `M-ALT-TXT` |
| 5. Ausência dos 5 campos obrigatórios | `A-PAC-NOME`, `A-PAC-IDADE`, `A-MED-NOME`, `A-MED-CRM`, `A-DIAG` |
| 6. Submissão 202 + consulta posterior | Qualquer fixture funcional (mesmo `documento_id`) |
| 7. Evento urgente simulado, sem envio externo | `M-IMG-PDF`, `S-URG-*` |
| 8. Score < 0,85 revisa; == 0,85 não revisa | `B-084`, `B-085` |
| 9. Campos ausentes não inferidos | `A-*`, `M-NID-*` |
| 10. Persistência no OCI informada | `F-OCI-ORIGINAL`, `F-OCI-RESULTADO` + qualquer fixture |
| 11. Histórico ordenado e JSON validado | Qualquer fixture funcional + `GET /historico` |
| 12. Regras, versão, justificativa e destino rastreáveis | `C-*`, `S-*` |
| 13. Interface mostra estados sem segredos | `M-*`, `F-*` |
| 14. README + demonstração dos 3 cenários | Kit de demonstração (12) |
| 15. Nenhum opcional declarado sem prova | Bloco D (se implementado) |

---

## 14. O que você **não** precisa criar

- **Um documento por especialidade médica.** A especialidade é texto livre (RF-06); não há lista fechada. Use 3 ou 4 especialidades variadas (radiologia, cardiologia, clínica médica, pediatria) e siga.
- **Um JSON por tipo de documento.** O JSON é envelope de transporte, não tipo documental.
- **Um caso urgente para cada um dos 8 tipos.** Dois ou três já provam a regra; o resto é custo sem cobertura nova.
- **Integrações reais** com prontuário, farmácia, operadora, TISS/TUSS, Slack ou e-mail. Os destinos são lógicos/simulados no MVP (§3.2).
- **Documentos com dados reais ou "anonimizados".** O MVP inteiro usa dados fictícios.
- **67 arquivos antes de codificar.** Comece pelos 12 do kit de demonstração; o restante entra em paralelo ao desenvolvimento.

---

## 15. Referências

- `Projeto_oracle.pdf` — brief do hackathon, formatos, entregáveis e checklist de avaliação.
- `MediFlow_-_Análise_de_Requisitos_v1.1.pdf` — visão geral, requisitos RF/RNF/RN e decisões do time.
- `MediFlow_Especificacao_Funcional_v1.0.pdf` — §5 (vocabulário), §6 (fluxo), §7 (RF-01 a RF-30), §8 (regras e tabela de decisão), §9 (modelo de dados), §10 (API), §12 (erros), §16 (critérios de aceite) e §15 (pendências).
- [`tests/fixtures/manifest.csv`](../../tests/fixtures/manifest.csv) — os 67 fixtures em formato de máquina.
