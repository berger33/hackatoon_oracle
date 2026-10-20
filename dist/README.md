# Pacote para download

Arquivo: `hackatoon_oracle-mediflow-completo.zip` (14 MB · 344 arquivos)

Conteúdo: README, documentação, os 67 fixtures (TXT + PDF + JPG + `expected.json`, em pastas com nome por extenso como `Matriz_Guia_Imagem`),
os 3 PDFs de origem do hackathon, os geradores em `tools/` e o `LEIA-ME.txt`.

**Download direto:**

```text
https://github.com/berger33/hackatoon_oracle/raw/arena/9bba261b-hackatoon-oracle/dist/hackatoon_oracle-mediflow-completo.zip
```

Este ZIP é um artefato de entrega gerado a partir do repositório. Para recriá-lo:

```bash
python3 tools/gerar_fixtures_demo.py
python3 tools/gerar_fixtures_catalogo.py
python3 tools/gerar_mapa_documentos.py
zip -r -9 dist/hackatoon_oracle-mediflow-completo.zip . -x ".git/*" -x "dist/*" -x "*/__pycache__/*"
```
