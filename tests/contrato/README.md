# Contrato × fixtures

Testes que comparam o **modelo de dados da triagem** com o contrato congelado nos
67 `expected.json`. Não dependem do pipeline, nem de rede: só Pydantic.

| Arquivo | Papel |
| --- | --- |
| `modelo_v2_proposto.py` | Cópia fiel da v2.0 enviada pela equipe. **Não é o contrato oficial** — existe para medir a v2.0. |
| `modelo_v3_sugerido.py` | A v2.0 com os ajustes de [`docs/testes/REVISAO_DO_MODELO_DE_CONTRATO_v2.md`](../../docs/testes/REVISAO_DO_MODELO_DE_CONTRATO_v2.md). Referência para o `app/models.py`. |
| `comparar_com_fixtures.py` | Mede a v2.0: quantos fixtures são representáveis, quantos ela preserva (echo) e quantos ela decide sozinha (derive). |
| `comparar_v3.py` | Mede a v3: decisões dos 57 funcionais + aceitação dos 10 negativos. |
| `verificar_regras_do_contrato.py` | Especificação executável: aplica só as regras, sem modelo, e confere 57/57 decisões. |

```bash
python3 tests/contrato/comparar_com_fixtures.py
python3 tests/contrato/comparar_v3.py
python3 tests/contrato/verificar_regras_do_contrato.py
```

Resultado esperado hoje:

```text
v2.0 · representáveis 49/67 · echo 43/49 · derive 37/49
v3   · decisões 57/57 · negativos 10/10
regras · 57/57 decisões + 10/10 erros explícitos
```

## O que estes testes NÃO fazem

- Não chamam Gemini nem o pipeline real.
- Não substituem os testes de API (HTTP, upload, polling) — cobrem só o **contrato de dados**.
- Não tratam `conflitos`/`campos_incertos` como algo que o schema possa adivinhar: são evidências produzidas pelo extrator e entram como campo.

## Quando o contrato for congelado

1. Mover a v3 para `app/models.py` (ajustando imports e `Settings`).
2. Trocar `from modelo_v3_sugerido import ...` por `from app.models import ...` nos dois testes.
3. Apagar `modelo_v2_proposto.py` e `modelo_v3_sugerido.py` — o `app/models.py` passa a ser a única fonte.
4. Ligar os três comandos no CI.
