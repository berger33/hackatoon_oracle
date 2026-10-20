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

## Como ler os nomes (a letra é o bloco de teste)

O primeiro caractere de cada ID indica **o que aquele grupo de documentos prova**. Não é ordem alfabética nem tipo de arquivo: é a categoria do teste.

| Bloco | Quantos | Pergunta que responde | Exemplos |
| --- | ---: | --- | --- |
| **M** — Matriz | 24 | "O sistema acerta cada tipo de documento em cada formato?" | `M-REC-PDF`, `M-LAB-IMG`, `M-GUI-TXT` |
| **A** — Ausência | 8 | "O que acontece quando falta um campo?" | `A-PAC-NOME`, `A-MED-CRM`, `A-CID-SO` |
| **B** — Borda | 2 | "O comportamento muda exatamente no limiar 0,85?" | `B-084`, `B-085` |
| **C** — Conflito | 5 | "O sistema detecta contradição clínica?" | `C-DOSE`, `C-CID-CONFLITO` |
| **S** — Simultâneo | 2 | "E quando urgência e ambiguidade acontecem juntas?" | `S-URG-ILEGIVEL` |
| **Q** — Qualidade | 8 | "E quando o arquivo está ruim ou protegido?" | `Q-FOTO-ROTACAO`, `Q-PDF-SENHA` |
| **V** — Validação | 8 | "E quando a entrada é inválida?" | `V-DOCX`, `V-GRANDE`, `V-MIME` |
| **E** — Escaneado | 6 | "E quando o PDF é só imagem, sem texto?" | `E-REC-PDFSCAN` |
| **D** — Diferencial | 4 | "Os opcionais funcionam?" | `D-MANUSCRITA`, `D-HEMOGRAMA` |

### Lendo o resto do nome

Depois do bloco vêm **2 ou 3 partes separadas por hífen**:

```text
M-REC-PDF
│  │   └── formato do arquivo: PDF, IMG (imagem) ou TXT (texto)
│  └────── tipo de documento: REC=receituário, LAB=laboratorial, IMG=imagem,
│           GUI=guia, ALT=alta, ATE=atestado, OUT=outro, NID=não identificado
└───────── bloco M (matriz)
```

Atenção a um detalhe que confunde: **no meio é o tipo, no fim é o formato**. Em `M-IMG-IMG`, o primeiro `IMG` é *laudo de exame de imagem* e o segundo é *formato imagem*. Já `M-IMG-PDF` é o mesmo tipo de documento entregue em PDF.

Nos outros blocos a lógica é **bloco + sujeito + o que está sendo testado**:

| ID | Leitura |
| --- | --- |
| `A-PAC-NOME` | ausência · paciente · nome |
| `A-MED-CRM` | ausência · médico · CRM |
| `A-CID-SO` | ausência · CID · **so**mente o CID (que **não** gera revisão) |
| `C-DOSE` | conflito · dose suspeita |
| `Q-PDF-SENHA` | qualidade · PDF · protegido por senha |
| `E-REC-PDFSCAN` | escaneado · receituário · PDF escaneado |
| `B-084` / `B-085` | borda · score 0,84 / 0,85 |

### Onde está cada coisa

```text
tests/fixtures/
├── manifest.csv     ← comece por aqui: 67 linhas, uma por documento, com o resultado esperado
├── demo/            ← 12 casos que cobrem o pitch (todos os blocos, exceto Q e V)
└── catalogo/        ← 55 casos restantes (Q e V ficam só aqui)
```

O mesmo ID existe em um único lugar — `demo/` e `catalogo/` não se repetem. Para saber o que se espera de um documento, abra o `expected.json` dentro da pasta dele; para ver o catálogo inteiro de uma vez, use o `manifest.csv` ou o PDF em `docs/testes/`.

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
