# EPT — MediFlow · guia de uso e cobertura

**Projeto:** hackatoon_oracle / MediFlow — Hackathon ONE G10  
**Artefato principal:** [`EPT_MediFlow_v1.0.csv`](EPT_MediFlow_v1.0.csv)  
**Base:** `MediFlow_Especificacao_Funcional_v1.0.pdf` (RF-01…RF-30, RN-01…RN-07, RNF-01…RNF-11, §8.2, §10, §11, §12, §16) + os 67 fixtures de [`manifest.csv`](../../tests/fixtures/manifest.csv)  
**Casos:** 100 — gerado por [`tools/gerar_ept.py`](../../tools/gerar_ept.py); não editar o CSV à mão, editar o gerador.

---

## 1. O que é esta EPT

Uma **Especificação de Procedimento de Teste**: uma linha por caso, com pré-condição, massa, passos numerados, resultado esperado verificável, rastreabilidade ao requisito e colunas de execução para o executor preencher. A EPT não substitui o catálogo de fixtures: ele é a **massa** citada na coluna `MASSA_DE_DADOS`.

Diferença prática:

| Artefato | Responde |
| --- | --- |
| `CATALOGO_DE_DOCUMENTOS_DE_TESTE.md` | **O que existe** para testar (67 documentos) |
| `CONTRATO_DE_DADOS.md` / `app/models.py` | **O que é uma resposta válida** |
| `EPT_MediFlow_v1.0.csv` (esta) | **Como executar e como saber se passou** |

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
| Classificação | 10 |
| Confiança e limiar | 5 |
| Decisão e roteamento | 15 |
| Extração | 21 |
| Ingestão e validação | 12 |
| Interface | 9 |
| Não funcionais | 11 |
| Persistência e histórico | 8 |
| **Total** | **100** |

### 5.2 Por tipo, cenário, prioridade e automação

| Tipo de teste | Casos | Cenário | Casos | Prioridade | Casos | Automação | Casos |
| --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| Funcional | 44 | Transversal | 32 | Alta | 69 | Sim | 85 |
| Funcional negativo | 30 | Rotina | 21 | Média | 30 | Parcial | 11 |
| Não funcional | 12 | Ambiguidade | 20 | Baixa | 1 | Não | 4 |
| Usabilidade | 8 | Erro | 16 |  |  |  |  |
| Borda | 3 | Urgência | 11 |  |  |  |  |
| Integração | 2 |  |  |  |  |  |  |
| Segurança | 1 |  |  |  |  |  |  |

### 5.3 Requisito → casos

| Requisito | Casos |
| --- | --- |
| RF-01 | CT-001, CT-002, CT-003, CT-005, CT-006, CT-007, CT-012 |
| RF-02 | CT-002, CT-003, CT-004 |
| RF-03 | CT-007, CT-008, CT-009, CT-010, CT-011, CT-012, CT-089 |
| RF-04 | CT-003, CT-004, CT-079 |
| RF-05 | CT-013, CT-014, CT-015 |
| RF-06 | CT-013, CT-016 |
| RF-07 | CT-017, CT-018, CT-019, CT-020, CT-021, CT-055 |
| RF-08 | CT-023, CT-024, CT-025 |
| RF-09 | CT-027, CT-028, CT-029 |
| RF-10 | CT-030, CT-031, CT-032 |
| RF-11 | CT-034, CT-035, CT-036 |
| RF-12 | CT-037, CT-038 |
| RF-13 | CT-020, CT-039 |
| RF-14 | CT-041, CT-043 |
| RF-15 | CT-015, CT-024, CT-026, CT-040, CT-042, CT-085 |
| RF-16 | CT-033, CT-036, CT-048, CT-055 |
| RF-17 | CT-022 |
| RF-18 | CT-043, CT-044, CT-045, CT-046, CT-047 |
| RF-19 | CT-062 |
| RF-20 | CT-049, CT-050, CT-051, CT-052, CT-053, CT-063 |
| RF-21 | CT-015, CT-021, CT-024, CT-025, CT-028, CT-031, CT-032, CT-035, CT-038, CT-053, CT-054, CT-056, CT-057, CT-058, CT-059 |
| RF-22 | CT-052, CT-053, CT-060 |
| RF-23 | CT-061 |
| RF-24 | CT-063, CT-064, CT-065, CT-077, CT-078, CT-079 |
| RF-25 | CT-001, CT-073, CT-074, CT-077, CT-080 |
| RF-26 | CT-070, CT-071, CT-072, CT-087 |
| RF-27 | CT-075, CT-076, CT-080, CT-081, CT-082, CT-083, CT-084, CT-085, CT-086, CT-087, CT-088, CT-089 |
| RF-28 | CT-066, CT-069 |
| RF-29 | CT-067, CT-069 |
| RF-30 | CT-068 |
| RN-01 | CT-018, CT-031, CT-035, CT-038, CT-046, CT-049, CT-050, CT-051, CT-059 |
| RN-02 | CT-014, CT-015, CT-021, CT-024, CT-025, CT-026, CT-028, CT-032, CT-045, CT-048, CT-053, CT-054, CT-056, CT-057, CT-058, CT-090 |
| RN-03 | CT-017, CT-019, CT-020, CT-052, CT-053, CT-055, CT-060, CT-090 |
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

Os 67 fixtures do `manifest.csv` são citados em pelo menos um caso (67/67 cobertos diretamente). Curingas como `Matriz_*` cobrem os demais sem repetir 24 linhas idênticas.

<details><summary>Mapa completo fixture → caso</summary>

| Fixture | Casos |
| --- | --- |
| `Matriz_Receituario_Pdf` | CT-013, CT-018, CT-023, CT-029, CT-034, CT-049, CT-061, CT-063, CT-066, CT-067, CT-070, CT-071, CT-082, CT-087, CT-088, CT-092, CT-097 |
| `Matriz_Receituario_Imagem` | CT-003, CT-013, CT-029, CT-039, CT-052, CT-090, CT-092 |
| `Matriz_Receituario_Texto` | CT-001, CT-005, CT-013, CT-018, CT-029, CT-034, CT-049, CT-092 |
| `Matriz_LaudoLaboratorial_Pdf` | CT-013, CT-018, CT-023, CT-029, CT-051, CT-063, CT-092 |
| `Matriz_LaudoLaboratorial_Imagem` | CT-013, CT-029, CT-092 |
| `Matriz_LaudoLaboratorial_Texto` | CT-013, CT-029, CT-037, CT-092 |
| `Matriz_LaudoDeImagem_Pdf` | CT-013, CT-017, CT-029, CT-052, CT-060, CT-064, CT-078, CT-084, CT-088, CT-090, CT-092, CT-093, CT-097 |
| `Matriz_LaudoDeImagem_Imagem` | CT-013, CT-017, CT-029, CT-090, CT-092 |
| `Matriz_LaudoDeImagem_Texto` | CT-013, CT-029, CT-051, CT-090, CT-092 |
| `Matriz_Guia_Pdf` | CT-002, CT-013, CT-018, CT-027, CT-029, CT-030, CT-042, CT-050, CT-063, CT-065, CT-068, CT-091, CT-092, CT-098 |
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
| `Conflito_Cid_Diagnostico` | CT-033, CT-048 |
| `Conflito_Dose` | CT-036, CT-048, CT-098 |
| `Conflito_Prioridade` | CT-055, CT-090 |
| `Conflito_Dados` | CT-040, CT-048 |
| `Conflito_AltoRisco` | CT-019, CT-060, CT-090 |
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
| `Validacao_ArquivoGrande` | CT-010, CT-080, CT-086, CT-089 |
| `Validacao_MimeInvalido` | CT-011, CT-080 |
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
| 1 | CT-002, CT-003, CT-004, CT-007, CT-008, CT-009, CT-010, CT-011, CT-012, CT-079 |
| 2 | CT-002, CT-004, CT-013, CT-018, CT-023, CT-027, CT-030, CT-034, CT-037, CT-049, CT-050, CT-051, CT-100 |
| 3 | CT-003, CT-017, CT-019, CT-020, CT-039, CT-052, CT-053, CT-054, CT-055, CT-078, CT-090 |
| 4 | CT-014, CT-015, CT-021, CT-039, CT-053, CT-056 |
| 5 | CT-024, CT-025, CT-028, CT-031, CT-032, CT-035, CT-038, CT-058, CT-059, CT-100 |
| 6 | CT-001, CT-006 |
| 7 | CT-053, CT-060, CT-063, CT-064, CT-088 |
| 8 | CT-020, CT-044, CT-045, CT-046, CT-047, CT-054 |
| 9 | CT-015, CT-016, CT-024, CT-026, CT-036, CT-039, CT-042, CT-085 |
| 10 | CT-064, CT-065, CT-066, CT-067, CT-068, CT-069, CT-078, CT-091, CT-099 |
| 11 | CT-005, CT-041, CT-070, CT-071, CT-072, CT-073, CT-074, CT-087, CT-092, CT-098 |
| 12 | CT-014, CT-022, CT-029, CT-033, CT-040, CT-042, CT-043, CT-048, CT-057, CT-061, CT-062, CT-093, CT-098 |
| 13 | CT-068, CT-071, CT-075, CT-076, CT-077, CT-080, CT-081, CT-082, CT-083, CT-084, CT-085, CT-086, CT-089, CT-094 |
| 14 | CT-095, CT-097 |
| 15 | CT-041, CT-063, CT-077, CT-088, CT-094, CT-096 |

## 6. Pendências que bloqueiam ou limitam casos

A própria especificação (§15) lista definições que a equipe precisa fechar. Elas aparecem aqui como risco de execução, não como falha de teste:

| Pendência (§15) | Casos afetados |
| --- | --- |
| Limite de tamanho, páginas e MIME | CT-010, CT-089 |
| Timeout e política de retry | CT-078, CT-091 |
| Dicionário de alto risco / conflitos | CT-019, CT-033, CT-036 |
| Autenticação e autorização | CT-071, CT-075 |
| Meta de latência e de precisão | CT-093, CT-100 |
| Formato final do upload | CT-001, CT-002, CT-012 |

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

O verificador garante: IDs únicos, campos obrigatórios preenchidos, enums de cenário e prioridade válidos, cobertura de **RF-01…RF-30**, **RN-01…RN-07**, **RNF-01…RNF-11**, cobertura dos **67 fixtures** e dos **15 itens de aceite de §16**.
