# Fixtures de teste — MediFlow

Este diretório guarda os documentos fictícios usados nos testes do agente de triagem.

- **Catálogo completo:** [`docs/testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md`](../../docs/testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md)
- **Manifesto (fonte de verdade):** [`manifest.csv`](manifest.csv)
- **Total planejado:** 67 documentos + 8 simulações operacionais (sem arquivo novo)

## Estrutura

```text
tests/fixtures/
├── manifest.csv      # 67 linhas com ID, tipo, formato, cenário, destino e status esperados
├── expected/         # 1 JSON de saída esperada por fixture funcional
├── source/           # fonte editável (Markdown/DOCX) que gera PDF e imagem
├── pdf/              # PDFs digitais e digitalizados
├── img/              # JPG/PNG
├── txt/              # documentos de texto
└── invalid/          # DOCX, ZIP, 0 KB, 25 MB, MIME falso
```

## Convenção de nomes

Use o `id` do manifesto como prefixo e o formato como sufixo:

```text
pdf/M-REC-PDF.pdf
img/M-REC-IMG.jpg
txt/M-REC-TXT.txt
invalid/V-DOCX.docx
expected/M-REC-PDF.json
source/M-REC-PDF.md
```

## Regras

1. Somente dados fictícios, com a marca d'água `DOCUMENTO FICTÍCIO — USO EXCLUSIVO EM TESTES`.
2. Um fixture de borda altera **apenas um** atributo em relação ao documento base.
3. Toda fixture funcional precisa de um `expected/{ID}.json`; os blocos V e F usam envelope de erro/estado final.
4. Não comparar scores exatos do LLM: use faixas e, nas bordas 0,84/0,85/0,70, use o modo `FIXTURE_MODE`.
5. Nenhum segredo, chave OCI ou dado pessoal real neste diretório.

## Prioridades

- `OBRIGATORIO` — 43 fixtures que cobrem os critérios de aceite.
- `RECOMENDADO` — 20 fixtures de robustez e bordas.
- `OPCIONAL` — 4 fixtures de diferenciais (OCR, carimbo, tabela, TISS).

A coluna `kit_demo = SIM` marca os **12 arquivos** do kit mínimo de demonstração.
