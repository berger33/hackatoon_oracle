# Fixtures do MediFlow

Este diretório guarda os documentos fictícios usados nos testes do agente de triagem.

- **Catálogo analítico:** [`docs/testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md`](../../docs/testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md)
- **Mapa em PDF:** [`docs/testes/Mapa_de_Documentos_de_Teste_MediFlow.pdf`](../../docs/testes/Mapa_de_Documentos_de_Teste_MediFlow.pdf)
- **Manifesto (fonte de verdade):** [`manifest.csv`](manifest.csv)
- **Status:** **67 de 67 fixtures produzidos**

## Estrutura

```text
tests/fixtures/
├── manifest.csv        # 67 linhas: ID, tipo, formato, cenário, destino e status esperados
├── demo/               # 12 casos de pitch (1 pasta por fixture)
├── catalogo/           # 55 casos restantes, incluindo os 8 negativos técnicos
└── README.md           # este arquivo
```

Cada pasta de fixture contém:

| Arquivo | O que é |
| --- | --- |
| `{ID}.txt` | Documento em texto puro (UTF-8) |
| `{ID}.pdf` | Mesma peça em PDF (digital, escaneado, protegido ou corrompido, conforme o caso) |
| `{ID}.jpg` | Mesma peça fotografada, em JPEG 150 dpi |
| `expected.json` | Saída esperada: tipo, prioridade, destinos, revisão, dados e asserções |

Os 8 negativos do bloco V são a exceção: têm **um único arquivo inválido** (`V-DOCX.docx`, `V-VAZIO.pdf`, `V-GRANDE.pdf`, etc.) e um `expected.json` com o **envelope de erro** (HTTP + código funcional), não um JSON de triagem.

## Os 12 casos de pitch (`demo/`)

| # | ID | Caso | Destino | Status |
| ---: | --- | --- | --- | --- |
| 1 | `M-REC-TXT` | Receituário — rotina | `FARMACIA_HOSPITALAR` | `PROCESSADO` |
| 2 | `M-REC-PDF` | Receituário — 2 medicamentos | `FARMACIA_HOSPITALAR` | `PROCESSADO` |
| 3 | `M-REC-IMG` | Receituário — urgência com opioide | `FILA_URGENCIA_MEDICA` | `EM_REVISAO` |
| 4 | `M-IMG-PDF` | TC de tórax — TEP agudo | `FILA_URGENCIA_MEDICA` | `EM_REVISAO` |
| 5 | `M-LAB-PDF` | Hemograma — rotina | `PRONTUARIO_ELETRONICO` | `PROCESSADO` |
| 6 | `M-GUI-PDF` | Guia de ressonância — eletiva | `AUDITORIA_AUTORIZACOES` | `PROCESSADO` |
| 7 | `M-ALT-PDF` | Relatório de alta — pneumonia | `PRONTUARIO_ELETRONICO` | `PROCESSADO` |
| 8 | `M-ATE-TXT` | Atestado de comparecimento | `PRONTUARIO_ELETRONICO` | `PROCESSADO` |
| 9 | `M-NID-IMG` | Documento ilegível | `FILA_REVISAO_HUMANA` | `EM_REVISAO` |
| 10 | `M-OUT-TXT` | Comunicação administrativa | `FILA_REVISAO_HUMANA` | `EM_REVISAO` |
| 11 | `A-PAC-NOME` | Receita sem nome do paciente | `FILA_REVISAO_HUMANA` | `EM_REVISAO` |
| 12 | `B-084` | Score forçado em 0,84 | `FILA_REVISAO_HUMANA` | `EM_REVISAO` |

## Os 55 casos do catálogo (`catalogo/`)

| Bloco | Casos | O que cobre |
| --- | ---: | --- |
| M | 14 | Matriz tipos × formatos (os 2 formatos que faltavam em cada tipo) |
| A | 7 | Ausência de campos que revisam e que não revisam |
| B | 1 | Limiar exato de 0,85 |
| C | 5 | Conflitos, dose suspeita, contradições e alto risco |
| S | 2 | Urgência + ambiguidade simultâneas |
| Q | 8 | Desfoque, rotação, corte, sombra, PDF sem texto, 7 páginas, senha e corrompido |
| V | 8 | Negativos técnicos (DOCX, 0 KB, JSON inválido, envelope vazio, ZIP, 25 MB, MIME falso) |
| E | 6 | PDF escaneado dos tipos restantes |
| D | 4 | Diferenciais: manuscrito, carimbo, hemograma de 20 analitos e guia TISS |

## Casos especiais

| Fixture | Particularidade |
| --- | --- |
| `M-NID-IMG`, `M-NID-PDF`, `Q-FOTO-DESFOCO` | PDF somente imagem e JPG com desfoque forte; cabeçalho de identificação preservado |
| `Q-FOTO-ROTACAO` | Imagem e PDF rotacionados em 90° |
| `Q-FOTO-CORTADA` | Recorte remove o CRM da assinatura — deve gerar revisão |
| `Q-FOTO-BAIXA` | Mancha elíptica sobre a idade — campo incerto, não inventado |
| `Q-PDF-SEM-TEXTO`, `E-*` | PDFs sem camada de texto (0 caracteres extraíveis) |
| `Q-PDF-MULTIPAGINA` | 7 páginas, rodapé "página N de 7" |
| `Q-PDF-SENHA` | Protegido por AES-256; senha de teste `mediflow123` |
| `Q-PDF-CORROMPIDO` | Truncado em 40% do tamanho original |
| `V-GRANDE` | 25 MB, **não versionado** — regenere com o script |
| `B-084`, `B-085`, `S-URG-SCORE` | Exigem `FIXTURE_MODE` para forçar os scores |

## Regras

1. Somente dados fictícios, com a marca d'água `DOCUMENTO FICTÍCIO — USO EXCLUSIVO EM TESTES`.
2. Um fixture de borda altera **apenas um** atributo em relação ao documento base.
3. Toda fixture funcional tem `expected.json`; os blocos V e F usam envelope de erro/estado final.
4. Não comparar scores exatos do LLM: use faixas e, nas bordas 0,84 / 0,85 / 0,70, o modo `FIXTURE_MODE`.
5. Nenhum segredo, chave OCI ou dado pessoal real neste diretório.

## Regerar

```bash
python3 -m pip install reportlab pymupdf pillow

python3 tools/gerar_fixtures_demo.py       # 12 casos → 48 arquivos em tests/fixtures/demo/
python3 tools/gerar_fixtures_catalogo.py   # 55 casos → 204 arquivos em tests/fixtures/catalogo/
python3 tools/gerar_mapa_documentos.py     # PDF do mapa em docs/testes/
```

> `V-GRANDE.pdf` (25 MB) é ignorado pelo Git por padrão. O script o recria quando necessário.
