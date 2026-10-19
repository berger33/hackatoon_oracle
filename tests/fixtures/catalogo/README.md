# Catálogo — 55 fixtures

Casos que complementam o kit de demonstração. Cada pasta `{ID}/` contém `{ID}.txt`, `{ID}.pdf`, `{ID}.jpg` e `expected.json`, exceto os negativos técnicos do bloco V.

| Bloco | IDs | Foco |
| --- | --- | --- |
| **M** | `M-LAB-IMG`, `M-LAB-TXT`, `M-IMG-IMG`, `M-IMG-TXT`, `M-GUI-IMG`, `M-GUI-TXT`, `M-ALT-IMG`, `M-ALT-TXT`, `M-ATE-PDF`, `M-ATE-IMG`, `M-OUT-PDF`, `M-OUT-IMG`, `M-NID-PDF`, `M-NID-TXT` | Fecha a matriz 8 tipos × 3 formatos |
| **A** | `A-PAC-IDADE`, `A-MED-NOME`, `A-MED-CRM`, `A-DIAG`, `A-CID-SO`, `A-MEDIC-SO`, `A-EXAMES-SO` | Ausência de campo: 4 obrigam revisão, 3 não obrigam |
| **B** | `B-085` | Score exatamente 0,85 não revisa por esse critério |
| **C** | `C-CID-CONFLITO`, `C-DOSE`, `C-PRIORIDADE`, `C-DADOS`, `C-ALTO-RISCO` | Conflitos e risco clínico |
| **S** | `S-URG-ILEGIVEL`, `S-URG-SCORE` | Urgência + ambiguidade, com dois destinos |
| **Q** | `Q-FOTO-DESFOCO`, `Q-FOTO-ROTACAO`, `Q-FOTO-CORTADA`, `Q-FOTO-BAIXA`, `Q-PDF-SEM-TEXTO`, `Q-PDF-MULTIPAGINA`, `Q-PDF-SENHA`, `Q-PDF-CORROMPIDO` | Qualidade, ilegibilidade e PDFs especiais |
| **V** | `V-DOCX`, `V-VAZIO`, `V-JSON-MALFORMADO`, `V-ENVELOPE`, `V-SEM-CONTEUDO`, `V-ZIP`, `V-GRANDE`, `V-MIME` | Negativos técnicos de entrada |
| **E** | `E-REC-PDFSCAN`, `E-LAB-PDFSCAN`, `E-GUI-PDFSCAN`, `E-ALT-PDFSCAN`, `E-ATE-PDFSCAN`, `E-OUT-PDFSCAN` | PDF escaneado (somente imagem) |
| **D** | `D-MANUSCRITA`, `D-CARIMBO`, `D-HEMOGRAMA`, `D-GUIA-TISS` | Diferenciais opcionais |

## Negativos técnicos (bloco V)

Os 8 casos têm um único arquivo de entrada inválido e um `expected.json` com o **envelope de erro** (`http`, `codigo_funcional`, `mensagem`) — não há documento de triagem esperado.

| ID | Arquivo | HTTP | Código funcional |
| --- | --- | ---: | --- |
| `V-DOCX` | `V-DOCX.docx` | 415 | `FORMATO_NAO_SUPORTADO` |
| `V-VAZIO` | `V-VAZIO.pdf` (0 bytes) | 422 | `CAMPOS_INVALIDOS` |
| `V-JSON-MALFORMADO` | `V-JSON-MALFORMADO.json` | 400 | `REQUISICAO_INVALIDA` |
| `V-ENVELOPE` | `V-ENVELOPE.json` (`{}`) | 422 | `CAMPOS_INVALIDOS` |
| `V-SEM-CONTEUDO` | `V-SEM-CONTEUDO.http` | 422 | `CAMPOS_INVALIDOS` |
| `V-ZIP` | `V-ZIP.zip` | 415 | `FORMATO_NAO_SUPORTADO` |
| `V-GRANDE` | `V-GRANDE.pdf` (25 MB) | 413 | `ARQUIVO_MAIOR_QUE_LIMITE` |
| `V-MIME` | `V-MIME.pdf` (PNG real) | 415 | `MIME_INVALIDO` |

> `V-GRANDE.pdf` não é versionado (25 MB). Regenere com `python3 tools/gerar_fixtures_catalogo.py`.

## Scores forçados

`B-085` e `S-URG-SCORE` trazem `score_forcado` no `expected.json`. Use o modo de fixture para definir os scores de classificação e extração, senão o resultado é intermitente.

## Regerar

```bash
python3 tools/gerar_fixtures_catalogo.py
```

O script é determinístico: mesmos documentos, mesmos textos e mesmos `expected.json`.
