# Kit de demonstração — 12 casos prontos

Cada pasta `{ID}/` contém quatro arquivos com o mesmo caso:

| Arquivo | O que é |
| --- | --- |
| `{ID}.txt` | Documento em texto puro (UTF-8) |
| `{ID}.pdf` | A mesma peça em PDF digital, com camada de texto |
| `{ID}.jpg` | A mesma peça fotografada, levemente inclinada, JPEG 150 dpi |
| `expected.json` | Saída esperada: tipo, prioridade, destinos, revisão, dados e asserções |

## Os 12 casos

| # | ID | Caso | Destino esperado | Status |
| ---: | --- | --- | --- | --- |
| 1 | `M-REC-TXT` | Receituário — rotina | `FARMACIA_HOSPITALAR` | `PROCESSADO` |
| 2 | `M-REC-PDF` | Receituário — rotina, 2 medicamentos | `FARMACIA_HOSPITALAR` | `PROCESSADO` |
| 3 | `M-REC-IMG` | Receituário — urgência com opioide | `FILA_URGENCIA_MEDICA` | `EM_REVISAO` |
| 4 | `M-IMG-PDF` | TC de tórax — TEP agudo | `FILA_URGENCIA_MEDICA` | `EM_REVISAO` |
| 5 | `M-LAB-PDF` | Hemograma — rotina | `PRONTUARIO_ELETRONICO` | `PROCESSADO` |
| 6 | `M-GUI-PDF` | Guia de ressonância — eletiva | `AUDITORIA_AUTORIZACOES` | `PROCESSADO` |
| 7 | `M-ALT-PDF` | Relatório de alta — pneumonia | `PRONTUARIO_ELETRONICO` | `PROCESSADO` |
| 8 | `M-ATE-TXT` | Atestado de comparecimento | `PRONTUARIO_ELETRONICO` | `PROCESSADO` |
| 9 | `M-NID-IMG` | Documento ilegível | `FILA_REVISAO_HUMANA` | `EM_REVISAO` |
| 10 | `M-OUT-TXT` | Comunicação administrativa | `FILA_REVISAO_HUMANA` | `EM_REVISAO` |
| 11 | `A-PAC-NOME` | Receita sem nome do paciente | `FILA_REVISAO_HUMANA` | `EM_REVISAO` |
| 12 | `B-084` | Receita com score forçado 0,84 | `FILA_REVISAO_HUMANA` | `EM_REVISAO` |

## Como usar

1. Submeta `{ID}.txt`, `{ID}.pdf` e `{ID}.jpg` como três triagens independentes — o resultado esperado é o mesmo nos três formatos, exceto em `M-NID-IMG`.
2. Compare a resposta com `expected.json` **por asserção**, nunca por score exato do modelo.
3. Em `B-084`, ative o modo de fixture (`FIXTURE_MODE`) para forçar `score_extracao = 0,84`; sem isso o caso é intermitente.
4. Para os três formatos, o `documento_id` deve ser distinto: são três requisições, não uma.

## Regras

- Todos os dados são fictícios. Nomes, CRMs, CID e resultados não correspondem a pessoa real.
- A marca d'água `DOCUMENTO FICTÍCIO — USO EXCLUSIVO EM TESTES` aparece em todas as páginas.
- Não edite os arquivos à mão: regenere com `python3 tools/gerar_fixtures_demo.py`.

## Regerar

```bash
python3 -m pip install reportlab pymupdf pillow
python3 tools/gerar_fixtures_demo.py     # 12 casos → 48 arquivos
python3 tools/gerar_mapa_documentos.py   # PDF do mapa de documentos
```
