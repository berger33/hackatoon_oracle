# EPT — MediFlow · guia de uso e cobertura

**Projeto:** hackatoon_oracle / MediFlow — Hackathon ONE G10  
**Artefato principal:** [`EPT_MediFlow_v1.1.csv`](EPT_MediFlow_v1.1.csv)  
**Base:** Especificação Funcional v1.0 — **edição de 21/10/2026** (16 páginas, decisões A1–A9), em `dist/MediFlow_Especificacao_Funcional_v1.0.pdf`; contrato `app/models.py` (R1–R8); e os 79 fixtures de [`manifest.csv`](../../tests/fixtures/manifest.csv)  
**Plano oficial de EPTs:** [`docs/epts/PLANO_DE_EPTS.md`](../epts/PLANO_DE_EPTS.md) (41 EPTs D/A/E/R) — cada caso desta EPT consolidada aponta para a EPT do plano em `EPT_DO_PLANO`.  
**Casos:** 111 — gerado por [`tools/gerar_ept.py`](../../tools/gerar_ept.py); não editar o CSV à mão, editar o gerador.

---

## 0. O que mudou na versão 1.1

A v1.0 desta EPT foi construída sobre a edição de 18/10/2026 da especificação e sobre 67 fixtures. A base do projeto avançou; esta versão acompanha:

| Mudança | Efeito na EPT | Casos |
| --- | --- | --- |
| **Urgência isolada não gera revisão** (correção de 21/10/2026, R1 do contrato) | casos urgentes passam a esperar `PROCESSADO`, `requer_auditoria_humana=false` e alerta; revisão só com ambiguidade | CT-003, CT-017, CT-019, CT-052 |
| **A1** — conflito impeditivo é ALTA ou MÉDIA | novos casos de gravidade MÉDIA (bloqueia) e BAIXA (não bloqueia) | CT-101, CT-102 |
| **A2** — dicionário clínico fechado | novo caso de conformidade com o dicionário | CT-110 |
| **A3** — `score_extracao` determinístico | novo caso da fórmula, com piso 0 | CT-103 |
| **A4** — prioridade `NAO_IDENTIFICADA` revisa | caso dedicado com fixture próprio | CT-104 |
| **A5** — urgência `INDETERMINADO` é incerteza | caso dedicado com fixture próprio | CT-105 |
| **A6** — 10 MB, 20 páginas, PDF/JPG/PNG/WEBP/TXT, timeout 60 s, 2 retentativas | limites, formatos e retry ganharam casos próprios; o antigo “limite pendente” saiu | CT-106…CT-109 |
| **A7/A8** — metas fora do MVP, retenção até o fim do hackathon, auth fora do MVP | casos de latência, precisão, privacidade e acesso passaram a registrar isso | CT-093, CT-100, CT-094, CT-075 |
| **A9** — farmacopeia própria da equipe | novo caso, inclusive sem a base carregada | CT-111 |
| **79 fixtures** (eram 67) | massa, cobertura e anexos recalculados | todos |

> **Atenção à base documental:** a cópia da **raiz** do repositório (`MediFlow_Especificacao_Funcional_v1.0.pdf`, 15 páginas, 18/10/2026) é a edição **anterior**. A edição de 21/10/2026 (16 páginas, com o Anexo A das decisões A1–A9) está em `dist/MediFlow_Especificacao_Funcional_v1.0.pdf`. Esta EPT usa a de 21/10.

---

## 1. O que é esta EPT

Uma **Especificação de Procedimento de Teste**: uma linha por caso, com pré-condição, massa, passos numerados, resultado esperado verificável, rastreabilidade ao requisito e colunas de execução para o executor preencher. A EPT não substitui o catálogo de fixtures: ele é a **massa** citada na coluna `MASSA_DE_DADOS`.

Diferença prática:

| Artefato | Responde |
| --- | --- |
| `CATALOGO_DE_DOCUMENTOS_DE_TESTE.md` | **O que existe** para testar (79 documentos) |
| `CONTRATO_DE_DADOS.md` / `app/models.py` | **O que é uma resposta válida** |
| `EPT_MediFlow_v1.1.csv` (esta) | **Como executar e como saber se passou** |
| `EPT_MediFlow_v1.1.pdf` | **A EPT como documento**: capa, sumário, os 111 casos por suíte e os anexos de cobertura, com folha de aprovação |
| `docs/epts/` | **O plano oficial**: 41 EPTs (D/A/E/R), uma por caso da especificação |
| `EPT_MediFlow_preview.html` | **A mesma EPT navegável**: filtros por suíte/cenário/prioridade, detalhe do caso e as matrizes de cobertura |

## 2. Como o arquivo está montado

| Item | Escolha | Por quê |
| --- | --- | --- |
| Codificação | UTF-8 **com BOM** | Excel pt-BR abre acento corretamente |
| Separador | `;` | padrão de planilha em português |
| Fim de linha | CRLF | compatível com Excel/Sheets |
| Quebra de linha na célula | nenhuma | evita linha “quebrada” na importação |
| Passos | `1) …` até `N) …` na mesma célula | mantém um caso por linha |
| Listas | `;` ou `*` (curinga de fixture) | `Matriz_Guia_*` expande para os 3 formatos |

Se a sua planilha usar `,` como separador, ajuste `delimiter` em `gravar_csv()` e rode o gerador de novo — ou importe no Excel com “separado por ponto e vírgula”.

## 3. Dicionário de dados

| Coluna | O que vai nela | Regra de preenchimento |
| --- | --- | --- |
| `ID_CASO` | identificador único (`CT-001`) | imutável; usado em evidência e defeito |
| `SUITE` | agrupamento funcional | 9 suítes: ingestão, classificação, extração, confiança, decisão, persistência, API, interface, não funcionais |
| `ID_REQUISITO` | RF/RNF da especificação | rastreabilidade para cima |
| `REGRAS_NEGOCIO` | RN aplicada | vazio quando não há regra de negócio |
| `CENARIO` | `Rotina`, `Urgência`, `Ambiguidade`, `Erro` ou `Transversal` | espelha os cenários de §16 |
| `TIPO_TESTE` | funcional, negativo, borda, integração, não funcional, usabilidade, segurança |
| `TECNICA` | valor limite, partição de equivalência, tabela de decisão, caso de uso, contrato, análise de risco |
| `PRIORIDADE` | `Alta` (bloqueia o MVP), `Média` (entra na entrega), `Baixa` |
| `TITULO` | uma frase, no imperativo | começa pelo verbo |
| `OBJETIVO` | o que a falha provaria | não repetir o título |
| `PRE_CONDICOES` | ambiente, dados e configuração | se faltar, o caso é bloqueado |
| `MASSA_DE_DADOS` | fixture(s) do catálogo | aceita `*` e `;` |
| `PASSOS` | passos numerados | cada passo tem ação verificável |
| `RESULTADO_ESPERADO` | asserções objetivas | valores e códigos, não “funciona bem” |
| `CRITERIO_DE_ACEITE` | item de §16 | usado no relatório de aceite |
| `EPT_DO_PLANO` | EPT do plano oficial (`EPT-D01`…`EPT-R11`) | liga esta execução ao documento de procedimento correspondente em `docs/epts/` |
| `AUTOMATIZAVEL` | `Sim`, `Parcial`, `Não` | orienta a automação |
| `AMBIENTE` | `API`, `Interface`, `Ambos`, `Repositório` | onde executar |
| `OBSERVACOES` | pendências, cuidados, dependências | `PENDENTE (§15)` marca bloqueio |
| `STATUS_EXECUCAO` | começa `NAO EXECUTADO` | valores: `PASSOU`, `FALHOU`, `BLOQUEADO`, `NAO APLICAVEL` |
| `RESULTADO_OBTIDO`, `EVIDENCIA`, `DEFEITO`, `DATA_EXECUCAO`, `EXECUTOR` | preenchidos na execução | evidência = print/log/arquivo; defeito = ID do bug |

## 4. Como executar (ordem recomendada)

1. **CT-001 a CT-012** (ingestão) — sem isso, nenhum outro caso tem massa válida.
2. **CT-049 a CT-063** (decisão) com `FIXTURE_MODE` nos casos de borda.
3. **CT-013 a CT-048** (classificação e extração) — o núcleo clínico.
4. **CT-066 a CT-080** (persistência, API e erros).
5. **CT-081 a CT-089** (interface) e **CT-090 a CT-100** (não funcionais) no fechamento.

Nos casos de borda (`CT-020`, `CT-044`, `CT-045`, `CT-046`, `CT-054`, `CT-062`) ative o `FIXTURE_MODE` e use `modo_fixture.score_forcado` do `expected.json`: score do LLM não é determinístico e não deve ser comparado por igualdade.

## 5. Cobertura

### 5.1 Por suíte

| Suíte | Casos |
| --- | ---: |
| API e erros | 9 |
| Classificação | 11 |
| Confiança e limiar | 8 |
| Decisão e roteamento | 15 |
| Extração | 24 |
| Ingestão e validação | 12 |
| Interface | 9 |
| Limites de entrada | 4 |
| Não funcionais | 11 |
| Persistência e histórico | 8 |
| **Total** | **111** |

### 5.2 Por tipo, cenário, prioridade e automação

| Tipo de teste | Casos | Cenário | Casos | Prioridade | Casos | Automação | Casos |
| --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| Funcional | 50 | Transversal | 34 | Alta | 78 | Sim | 95 |
| Funcional negativo | 33 | Rotina | 25 | Média | 32 | Parcial | 11 |
| Não funcional | 12 | Ambiguidade | 24 | Baixa | 1 | Não | 5 |
| Usabilidade | 8 | Erro | 17 |  |  |  |  |
| Borda | 5 | Urgência | 11 |  |  |  |  |
| Integração | 2 |  |  |  |  |  |  |
| Segurança | 1 |  |  |  |  |  |  |

### 5.3 Requisito → casos

| Requisito | Casos |
| --- | --- |
| RF-01 | CT-001, CT-002, CT-003, CT-005, CT-006, CT-007, CT-012 |
| RF-02 | CT-002, CT-003, CT-004, CT-108 |
| RF-03 | CT-007, CT-008, CT-009, CT-010, CT-011, CT-012, CT-089, CT-106, CT-107 |
| RF-04 | CT-003, CT-004, CT-079, CT-109 |
| RF-05 | CT-013, CT-014, CT-015 |
| RF-06 | CT-013, CT-016 |
| RF-07 | CT-017, CT-018, CT-019, CT-020, CT-021, CT-055, CT-104 |
| RF-08 | CT-023, CT-024, CT-025 |
| RF-09 | CT-027, CT-028, CT-029 |
| RF-10 | CT-030, CT-031, CT-032 |
| RF-11 | CT-034, CT-035, CT-036, CT-111 |
| RF-12 | CT-037, CT-038 |
| RF-13 | CT-020, CT-039, CT-105 |
| RF-14 | CT-041, CT-043 |
| RF-15 | CT-015, CT-024, CT-026, CT-040, CT-042, CT-085 |
| RF-16 | CT-033, CT-036, CT-048, CT-055, CT-101, CT-102, CT-110 |
| RF-17 | CT-022 |
| RF-18 | CT-043, CT-044, CT-045, CT-046, CT-047, CT-102, CT-103 |
| RF-19 | CT-062 |
| RF-20 | CT-049, CT-050, CT-051, CT-052, CT-053, CT-063 |
| RF-21 | CT-015, CT-021, CT-024, CT-025, CT-028, CT-031, CT-032, CT-035, CT-038, CT-053, CT-054, CT-056, CT-057, CT-058, CT-059, CT-104, CT-105 |
| RF-22 | CT-052, CT-053, CT-060 |
| RF-23 | CT-061 |
| RF-24 | CT-063, CT-064, CT-065, CT-077, CT-078, CT-079, CT-109 |
| RF-25 | CT-001, CT-073, CT-074, CT-077, CT-080 |
| RF-26 | CT-070, CT-071, CT-072, CT-087 |
| RF-27 | CT-075, CT-076, CT-080, CT-081, CT-082, CT-083, CT-084, CT-085, CT-086, CT-087, CT-088, CT-089 |
| RF-28 | CT-066, CT-069 |
| RF-29 | CT-067, CT-069 |
| RF-30 | CT-068 |
| RN-01 | CT-018, CT-031, CT-035, CT-038, CT-046, CT-049, CT-050, CT-051, CT-059, CT-102 |
| RN-02 | CT-014, CT-015, CT-021, CT-024, CT-025, CT-026, CT-028, CT-032, CT-045, CT-048, CT-053, CT-054, CT-056, CT-057, CT-058, CT-090, CT-101, CT-104, CT-105 |
| RN-03 | CT-017, CT-019, CT-020, CT-052, CT-053, CT-055, CT-060, CT-090, CT-110 |
| RN-04 | CT-066, CT-070 |
| RN-05 | CT-061, CT-070 |
| RN-06 | CT-069 |
| RN-07 | CT-001, CT-006 |
| RNF-01 | CT-100 |
| RNF-02 | CT-090 |
| RNF-03 | CT-091 |
| RNF-04 | CT-098 |
| RNF-05 | CT-099 |
| RNF-06 | CT-092 |
| RNF-07 | CT-093 |
| RNF-08 | CT-094 |
| RNF-09 | CT-095 |
| RNF-10 | CT-096 |
| RNF-11 | CT-097 |

### 5.4 Massa → casos

Os 79 fixtures do `manifest.csv` são citados em pelo menos um caso (79/79 cobertos diretamente). Curingas como `Matriz_*` cobrem os demais sem repetir 24 linhas idênticas.

<details><summary>Mapa completo fixture → caso</summary>

| Fixture | Casos |
| --- | --- |
| `Matriz_Receituario_Pdf` | CT-013, CT-018, CT-023, CT-029, CT-034, CT-049, CT-061, CT-063, CT-066, CT-067, CT-070, CT-071, CT-082, CT-087, CT-088, CT-092, CT-097 |
| `Matriz_Receituario_Imagem` | CT-003, CT-013, CT-029, CT-039, CT-052, CT-090, CT-092 |
| `Matriz_Receituario_Texto` | CT-111, CT-001, CT-005, CT-013, CT-018, CT-029, CT-034, CT-049, CT-092 |
| `Matriz_LaudoLaboratorial_Pdf` | CT-013, CT-018, CT-023, CT-029, CT-051, CT-063, CT-092 |
| `Matriz_LaudoLaboratorial_Imagem` | CT-013, CT-029, CT-092 |
| `Matriz_LaudoLaboratorial_Texto` | CT-013, CT-029, CT-037, CT-092 |
| `Matriz_LaudoDeImagem_Pdf` | CT-013, CT-017, CT-029, CT-052, CT-060, CT-064, CT-078, CT-084, CT-088, CT-090, CT-092, CT-093, CT-097 |
| `Matriz_LaudoDeImagem_Imagem` | CT-013, CT-017, CT-029, CT-090, CT-092 |
| `Matriz_LaudoDeImagem_Texto` | CT-013, CT-029, CT-051, CT-090, CT-092 |
| `Matriz_Guia_Pdf` | CT-109, CT-002, CT-013, CT-018, CT-027, CT-029, CT-030, CT-042, CT-050, CT-063, CT-065, CT-068, CT-091, CT-092, CT-098 |
| `Matriz_Guia_Imagem` | CT-013, CT-017, CT-029, CT-052, CT-090, CT-092 |
| `Matriz_Guia_Texto` | CT-013, CT-029, CT-050, CT-092 |
| `Matriz_RelatorioDeAlta_Pdf` | CT-013, CT-029, CT-030, CT-051, CT-073, CT-092 |
| `Matriz_RelatorioDeAlta_Imagem` | CT-013, CT-029, CT-092 |
| `Matriz_RelatorioDeAlta_Texto` | CT-013, CT-029, CT-032, CT-092 |
| `Matriz_Atestado_Pdf` | CT-013, CT-027, CT-029, CT-030, CT-051, CT-092 |
| `Matriz_Atestado_Imagem` | CT-013, CT-029, CT-051, CT-092 |
| `Matriz_Atestado_Texto` | CT-013, CT-018, CT-029, CT-039, CT-092 |
| `Matriz_Outro_Pdf` | CT-014, CT-029, CT-056, CT-092 |
| `Matriz_Outro_Imagem` | CT-014, CT-029, CT-056, CT-092 |
| `Matriz_Outro_Texto` | CT-014, CT-016, CT-029, CT-056, CT-092 |
| `Matriz_NaoIdentificado_Pdf` | CT-015, CT-016, CT-029, CT-092 |
| `Matriz_NaoIdentificado_Imagem` | CT-015, CT-029, CT-039, CT-092 |
| `Matriz_NaoIdentificado_Texto` | CT-015, CT-021, CT-029, CT-085, CT-092 |
| `Ausencia_Paciente_Nome` | CT-024, CT-057, CT-058, CT-067, CT-072, CT-082, CT-097, CT-098 |
| `Ausencia_Paciente_Idade` | CT-025, CT-042, CT-058, CT-085 |
| `Ausencia_Medico_Nome` | CT-028, CT-058 |
| `Ausencia_Medico_Crm` | CT-028, CT-058 |
| `Ausencia_Diagnostico` | CT-032, CT-057, CT-058 |
| `Ausencia_SomenteCid` | CT-031, CT-059 |
| `Ausencia_SomenteMedicamentos` | CT-035, CT-059 |
| `Ausencia_SomenteExames` | CT-038, CT-059 |
| `Borda_Score_084` | CT-045, CT-057, CT-061 |
| `Borda_Score_085` | CT-046 |
| `Borda_Prioridade_NaoIdentificada` | CT-104, CT-021 |
| `Borda_Urgencia_Indeterminada` | CT-105, CT-039 |
| `Conflito_Cid_Diagnostico` | CT-033, CT-048 |
| `Conflito_Dose` | CT-111, CT-036, CT-048, CT-098 |
| `Conflito_Prioridade` | CT-055, CT-090 |
| `Conflito_Dados` | CT-040, CT-048 |
| `Conflito_AltoRisco` | CT-110, CT-019, CT-060, CT-090 |
| `Conflito_Gravidade_Media` | CT-101, CT-110 |
| `Conflito_Gravidade_Baixa` | CT-102, CT-110 |
| `Simultaneo_Urgencia_Ilegivel` | CT-053, CT-061, CT-083, CT-090 |
| `Simultaneo_Urgencia_Score` | CT-020, CT-054, CT-090 |
| `Qualidade_Foto_Desfocada` | CT-015 |
| `Qualidade_Foto_Rotacionada` | CT-051 |
| `Qualidade_Foto_Cortada` | CT-028 |
| `Qualidade_Foto_BaixoContraste` | CT-026, CT-042 |
| `Qualidade_Pdf_SemTexto` | CT-004, CT-080 |
| `Qualidade_Pdf_Multipagina` | CT-080 |
| `Qualidade_Pdf_ComSenha` | CT-079, CT-080 |
| `Qualidade_Pdf_Corrompido` | CT-079, CT-080, CT-082, CT-086 |
| `Validacao_ArquivoDocx` | CT-009, CT-080, CT-086, CT-089 |
| `Validacao_ArquivoVazio` | CT-010, CT-080 |
| `Validacao_JsonMalformado` | CT-008, CT-080 |
| `Validacao_EnvelopeVazio` | CT-012, CT-080 |
| `Validacao_SemConteudo` | CT-007, CT-080 |
| `Validacao_ArquivoZip` | CT-009, CT-080 |
| `Validacao_ArquivoGrande` | CT-080, CT-086, CT-089 |
| `Validacao_MimeInvalido` | CT-011, CT-080 |
| `Limite_Tamanho_10MB` | CT-106 |
| `Limite_Tamanho_Acima10MB` | CT-106 |
| `Limite_Paginas_20` | CT-107 |
| `Limite_Paginas_21` | CT-107 |
| `Limite_Formato_Png` | CT-108 |
| `Limite_Formato_Webp` | CT-108 |
| `Limite_Texto_Acima10MB` | CT-106 |
| `Limite_Paginas_21_Digitalizado` | CT-107 |
| `Escaneado_Receituario_PdfDigitalizado` | CT-004, CT-049 |
| `Escaneado_LaudoLaboratorial_PdfDigitalizado` | CT-004 |
| `Escaneado_Guia_PdfDigitalizado` | CT-004, CT-050 |
| `Escaneado_RelatorioDeAlta_PdfDigitalizado` | CT-004 |
| `Escaneado_Atestado_PdfDigitalizado` | CT-004 |
| `Escaneado_Outro_PdfDigitalizado` | CT-004, CT-014 |
| `Diferencial_ReceituarioManuscrito` | CT-049 |
| `Diferencial_CarimboSobreposto` | CT-051 |
| `Diferencial_HemogramaCompleto` | CT-037 |
| `Diferencial_GuiaTiss` | CT-037, CT-050 |

</details>

### 5.5 Itens de aceite do MVP (§16) → casos

| Item de §16 | Casos que provam o item |
| ---: | --- |
| 1 | CT-002, CT-003, CT-004, CT-007, CT-008, CT-009, CT-010, CT-011, CT-012, CT-079, CT-106, CT-107, CT-108 |
| 2 | CT-002, CT-004, CT-013, CT-018, CT-023, CT-027, CT-030, CT-034, CT-037, CT-049, CT-050, CT-051, CT-100, CT-102 |
| 3 | CT-003, CT-017, CT-019, CT-020, CT-039, CT-052, CT-053, CT-054, CT-055, CT-078, CT-090 |
| 4 | CT-014, CT-015, CT-021, CT-039, CT-053, CT-056, CT-104 |
| 5 | CT-024, CT-025, CT-028, CT-031, CT-032, CT-035, CT-038, CT-058, CT-059, CT-100 |
| 6 | CT-001, CT-006 |
| 7 | CT-053, CT-060, CT-063, CT-064, CT-088 |
| 8 | CT-020, CT-044, CT-045, CT-046, CT-047, CT-054, CT-103 |
| 9 | CT-015, CT-016, CT-024, CT-026, CT-036, CT-039, CT-042, CT-085, CT-105, CT-111 |
| 10 | CT-064, CT-065, CT-066, CT-067, CT-068, CT-069, CT-078, CT-091, CT-099, CT-109 |
| 11 | CT-005, CT-041, CT-070, CT-071, CT-072, CT-073, CT-074, CT-087, CT-092, CT-098 |
| 12 | CT-014, CT-022, CT-029, CT-033, CT-040, CT-042, CT-043, CT-048, CT-057, CT-061, CT-062, CT-093, CT-098, CT-101, CT-102, CT-110 |
| 13 | CT-068, CT-071, CT-075, CT-076, CT-077, CT-080, CT-081, CT-082, CT-083, CT-084, CT-085, CT-086, CT-089, CT-094, CT-109 |
| 14 | CT-095, CT-097 |
| 15 | CT-041, CT-063, CT-077, CT-088, CT-094, CT-096 |

### 5.6 EPT do plano oficial → casos

As 41 EPTs planejadas em `docs/epts/PLANO_DE_EPTS.md` têm pelo menos um caso executável aqui. As duas já escritas (EPT-D01 e EPT-A08) são o modelo de procedimento detalhado; as demais ganham procedimento completo à medida que o plano avança.

| EPT do plano | Família | Casos nesta EPT consolidada |
| --- | --- | --- |
| `EPT-A01` | Aceite (§16) | CT-002, CT-003, CT-004, CT-007, CT-008, CT-009, CT-010, CT-011, CT-012, CT-079, CT-106, CT-107, CT-108 |
| `EPT-A02` | Aceite (§16) | CT-002, CT-004, CT-013, CT-018, CT-023, CT-027, CT-030, CT-034, CT-037, CT-049, CT-050, CT-051, CT-100, CT-102 |
| `EPT-A03` | Aceite (§16) | CT-003, CT-017, CT-019, CT-020, CT-039, CT-052, CT-053, CT-054, CT-055, CT-078, CT-090 |
| `EPT-A04` | Aceite (§16) | CT-014, CT-015, CT-021, CT-039, CT-053, CT-056, CT-104 |
| `EPT-A05` | Aceite (§16) | CT-024, CT-025, CT-028, CT-031, CT-032, CT-035, CT-038, CT-058, CT-059, CT-100 |
| `EPT-A06` | Aceite (§16) | CT-001, CT-006 |
| `EPT-A07` | Aceite (§16) | CT-053, CT-060, CT-063, CT-064, CT-088 |
| `EPT-A08` | Aceite (§16) | CT-020, CT-044, CT-045, CT-046, CT-047, CT-054, CT-103 |
| `EPT-A09` | Aceite (§16) | CT-015, CT-016, CT-024, CT-026, CT-036, CT-039, CT-042, CT-085, CT-105, CT-111 |
| `EPT-A10` | Aceite (§16) | CT-064, CT-065, CT-066, CT-067, CT-068, CT-069, CT-078, CT-091, CT-099, CT-109 |
| `EPT-A11` | Aceite (§16) | CT-005, CT-041, CT-070, CT-071, CT-072, CT-073, CT-074, CT-087, CT-092, CT-098 |
| `EPT-A12` | Aceite (§16) | CT-014, CT-022, CT-029, CT-033, CT-040, CT-042, CT-043, CT-048, CT-057, CT-061, CT-062, CT-093, CT-098, CT-101, CT-102, CT-110 |
| `EPT-A13` | Aceite (§16) | CT-068, CT-071, CT-075, CT-076, CT-077, CT-080, CT-081, CT-082, CT-083, CT-084, CT-085, CT-086, CT-089, CT-094, CT-109 |
| `EPT-A14` | Aceite (§16) | CT-095, CT-097 |
| `EPT-A15` | Aceite (§16) | CT-041, CT-063, CT-077, CT-088, CT-094, CT-096 |
| `EPT-D01` | Decisão (§8.2) | CT-003, CT-017, CT-019, CT-052 |
| `EPT-D02` | Decisão (§8.2) | CT-045 |
| `EPT-D03` | Decisão (§8.2) | CT-020, CT-053, CT-054 |
| `EPT-D04` | Decisão (§8.2) | CT-049 |
| `EPT-D05` | Decisão (§8.2) | CT-049, CT-050 |
| `EPT-D06` | Decisão (§8.2) | CT-051 |
| `EPT-D07` | Decisão (§8.2) | CT-014, CT-056 |
| `EPT-E01` | Erros (§12) | CT-007, CT-008, CT-009, CT-010, CT-011, CT-012, CT-106, CT-107 |
| `EPT-E02` | Erros (§12) | CT-015, CT-026 |
| `EPT-E03` | Erros (§12) | CT-078, CT-091, CT-109 |
| `EPT-E04` | Erros (§12) | CT-041 |
| `EPT-E05` | Erros (§12) | CT-033, CT-036, CT-040, CT-048, CT-055, CT-101, CT-102, CT-110, CT-111 |
| `EPT-E06` | Erros (§12) | CT-060 |
| `EPT-E07` | Erros (§12) | CT-064 |
| `EPT-E08` | Erros (§12) | CT-065, CT-066, CT-067 |
| `EPT-R01` | Não funcional (§14) | CT-100 |
| `EPT-R02` | Não funcional (§14) | CT-090 |
| `EPT-R03` | Não funcional (§14) | CT-065 |
| `EPT-R04` | Não funcional (§14) | CT-098 |
| `EPT-R05` | Não funcional (§14) | CT-099 |
| `EPT-R06` | Não funcional (§14) | CT-092 |
| `EPT-R07` | Não funcional (§14) | CT-093 |
| `EPT-R08` | Não funcional (§14) | CT-094 |
| `EPT-R09` | Não funcional (§14) | CT-095 |
| `EPT-R10` | Não funcional (§14) | CT-096 |
| `EPT-R11` | Não funcional (§14) | CT-097 |

## 6. Pendências que bloqueiam ou limitam casos

A própria especificação (§15) lista definições que a equipe precisa fechar. Elas aparecem aqui como risco de execução, não como falha de teste:

| Pendência (§15) | Casos afetados |
| --- | --- |
| Limite de tamanho, páginas e MIME | **decidido em A6** | 10 MB, 20 páginas, PDF/JPG/PNG/WEBP/TXT — CT-106, CT-107, CT-108 |
| Timeout e política de retry | **decidido em A6** | 60 s e 2 retentativas com backoff — CT-109, CT-078, CT-091 |
| Dicionário de alto risco e conflitos | **decidido em A1/A2** | anexo fechado da EF — CT-019, CT-033, CT-101, CT-110 |
| Farmacopeia da comparação de doses | **decidido em A9** | lista própria da equipe — CT-111 |
| Autenticação e autorização | **fora do MVP (A8)** | CT-075 fica NAO APLICAVEL; exposição pública exige auth |
| Metas de latência e de precisão | **fora do MVP (A7)** | CT-093 mede, CT-100 aprova pelos casos |
| Formato final do upload | em aberto | CT-001, CT-002, CT-012 |

## 7. Adaptando ao template da sua área

O conteúdo não muda; só o cabeçalho. Se a Função Sistemas tiver um modelo próprio, ajuste a constante `COLUNAS` e o dicionário de mapeamento em `tools/gerar_ept.py` e rode de novo — o CSV continua reprodutível. Mapeamento usual:

| Nossa coluna | Equivalentes comuns |
| --- | --- |
| `ID_CASO` | ID, Código do caso, CT |
| `TITULO` | Caso de teste, Descrição, Cenário |
| `PRE_CONDICOES` | Pré-requisitos, Setup |
| `MASSA_DE_DADOS` | Massa, Dados de entrada |
| `PASSOS` | Procedimento, Passos para execução, Roteiro |
| `RESULTADO_ESPERADO` | Resultado esperado, Saída esperada |
| `RESULTADO_OBTIDO` | Resultado obtido, Evidência de execução |
| `STATUS_EXECUCAO` | Status, Situação, Aprovado/Reprovado |
| `DEFEITO` | ID do defeito, Bug, Chamado |

## 8. Verificação automática

```bash
python3 tools/gerar_ept.py --check   # falha se faltar requisito, fixture ou item de aceite
python3 tools/gerar_ept.py           # regrava o CSV e este guia
```

Para ler a EPT no navegador, sem planilha:

```bash
python3 tools/gerar_ept_pdf.py       # docs/testes/EPT_MediFlow_v1.1.pdf
python3 tools/gerar_ept_preview.py   # docs/testes/EPT_MediFlow_preview.html (arquivo único)
```

O verificador garante: IDs únicos, campos obrigatórios preenchidos, enums de cenário e prioridade válidos, cobertura de **RF-01…RF-30**, **RN-01…RN-07**, **RNF-01…RNF-11**, cobertura dos **79 fixtures** e dos **15 itens de aceite de §16**.
