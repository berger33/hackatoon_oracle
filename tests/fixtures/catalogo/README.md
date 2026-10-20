# Catálogo — 55 fixtures

Casos que complementam o kit de demonstração. Cada pasta `{ID}/` contém `{ID}.txt`, `{ID}.pdf`, `{ID}.jpg` e `expected.json`, exceto os negativos técnicos do bloco **Validacao**.

O nome de cada pasta segue o padrão `Bloco_Assunto_Detalhe`, sem abreviações: começa pelo nome do bloco de teste, e por isso a ordenação alfabética do diretório já agrupa os casos por assunto.

| Bloco | IDs | Foco |
| --- | --- | --- |
| **Matriz** | `Matriz_LaudoLaboratorial_Imagem`, `Matriz_LaudoLaboratorial_Texto`, `Matriz_LaudoDeImagem_Imagem`, `Matriz_LaudoDeImagem_Texto`, `Matriz_Guia_Imagem`, `Matriz_Guia_Texto`, `Matriz_RelatorioDeAlta_Imagem`, `Matriz_RelatorioDeAlta_Texto`, `Matriz_Atestado_Pdf`, `Matriz_Atestado_Imagem`, `Matriz_Outro_Pdf`, `Matriz_Outro_Imagem`, `Matriz_NaoIdentificado_Pdf`, `Matriz_NaoIdentificado_Texto` | Fecha a matriz 8 tipos × 3 formatos |
| **Ausencia** | `Ausencia_Paciente_Idade`, `Ausencia_Medico_Nome`, `Ausencia_Medico_Crm`, `Ausencia_Diagnostico`, `Ausencia_SomenteCid`, `Ausencia_SomenteMedicamentos`, `Ausencia_SomenteExames` | Ausência de campo: 4 obrigam revisão, 3 não obrigam |
| **Borda** | `Borda_Score_085` | Score exatamente 0,85 não revisa por esse critério |
| **Conflito** | `Conflito_Cid_Diagnostico`, `Conflito_Dose`, `Conflito_Prioridade`, `Conflito_Dados`, `Conflito_AltoRisco` | Conflitos e risco clínico |
| **Simultaneo** | `Simultaneo_Urgencia_Ilegivel`, `Simultaneo_Urgencia_Score` | Urgência + ambiguidade, com dois destinos |
| **Qualidade** | `Qualidade_Foto_Desfocada`, `Qualidade_Foto_Rotacionada`, `Qualidade_Foto_Cortada`, `Qualidade_Foto_BaixoContraste`, `Qualidade_Pdf_SemTexto`, `Qualidade_Pdf_Multipagina`, `Qualidade_Pdf_ComSenha`, `Qualidade_Pdf_Corrompido` | Ilegibilidade e PDFs especiais |
| **Validacao** | `Validacao_ArquivoDocx`, `Validacao_ArquivoVazio`, `Validacao_JsonMalformado`, `Validacao_EnvelopeVazio`, `Validacao_SemConteudo`, `Validacao_ArquivoZip`, `Validacao_ArquivoGrande`, `Validacao_MimeInvalido` | Negativos técnicos de entrada |
| **Escaneado** | `Escaneado_Receituario_PdfDigitalizado`, `Escaneado_LaudoLaboratorial_PdfDigitalizado`, `Escaneado_Guia_PdfDigitalizado`, `Escaneado_RelatorioDeAlta_PdfDigitalizado`, `Escaneado_Atestado_PdfDigitalizado`, `Escaneado_Outro_PdfDigitalizado` | PDF digitalizado (somente imagem, sem texto) |
| **Diferencial** | `Diferencial_ReceituarioManuscrito`, `Diferencial_CarimboSobreposto`, `Diferencial_HemogramaCompleto`, `Diferencial_GuiaTiss` | Itens opcionais |

## Negativos técnicos (bloco Validacao)

Os 8 casos têm um único arquivo de entrada inválido e um `expected.json` com o **envelope de erro** (`http`, `codigo_funcional`, `mensagem`) — não há documento de triagem esperado.

| ID | Arquivo | HTTP | Código funcional |
| --- | --- | ---: | --- |
| `Validacao_ArquivoDocx` | `Validacao_ArquivoDocx.docx` | 415 | `FORMATO_NAO_SUPORTADO` |
| `Validacao_ArquivoVazio` | `Validacao_ArquivoVazio.pdf` (0 bytes) | 422 | `CAMPOS_INVALIDOS` |
| `Validacao_JsonMalformado` | `Validacao_JsonMalformado.json` | 400 | `REQUISICAO_INVALIDA` |
| `Validacao_EnvelopeVazio` | `Validacao_EnvelopeVazio.json` (`{}`) | 422 | `CAMPOS_INVALIDOS` |
| `Validacao_SemConteudo` | `Validacao_SemConteudo.http` | 422 | `CAMPOS_INVALIDOS` |
| `Validacao_ArquivoZip` | `Validacao_ArquivoZip.zip` | 415 | `FORMATO_NAO_SUPORTADO` |
| `Validacao_ArquivoGrande` | `Validacao_ArquivoGrande.pdf` (25 MB) | 413 | `ARQUIVO_MAIOR_QUE_LIMITE` |
| `Validacao_MimeInvalido` | `Validacao_MimeInvalido.pdf` (PNG real) | 415 | `MIME_INVALIDO` |

> `Validacao_ArquivoGrande.pdf` não é versionado (25 MB). Regenere com `python3 tools/gerar_fixtures_catalogo.py`.

## Scores forçados

`Borda_Score_085` e `Simultaneo_Urgencia_Score` trazem `score_forcado` no `expected.json`. Use o modo de fixture para definir os scores de classificação e extração, senão o resultado é intermitente.

## Regerar

```bash
python3 tools/gerar_fixtures_catalogo.py
```

O script é determinístico: mesmos documentos, mesmos textos e mesmos `expected.json`.
