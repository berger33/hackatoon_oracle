# Pacote para download

Arquivo: `hackatoon_oracle-mediflow-completo.zip` (16 MB · 335 arquivos)

Conteúdo: README, documentação, os 79 fixtures (TXT + PDF + JPG + `expected.json`, em pastas com nome por extenso como `Matriz_Guia_Imagem`),
os 3 PDFs de origem do hackathon, os geradores em `tools/` e o `LEIA-ME.txt`.

**Download direto:**

```text
https://github.com/berger33/hackatoon_oracle/raw/main/dist/hackatoon_oracle-mediflow-completo.zip
```

Este ZIP é um artefato de entrega gerado a partir do repositório. Para recriá-lo:

```bash
python3 tools/gerar_fixtures_demo.py
python3 tools/gerar_fixtures_catalogo.py
python3 tools/gerar_mapa_documentos.py
python3 tools/gerar_ept.py
python3 tools/gerar_ept_pdf.py
python3 tools/gerar_ept_preview.py
python3 tools/gerar_pacote.py    # ZIP com nomes UTF-8 e datas fixas; atualiza a contagem acima
```
