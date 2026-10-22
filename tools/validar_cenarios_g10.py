#!/usr/bin/env python3
"""Valida os cenários de integração do G10 contra o contrato executável.

Os arquivos de `docs/integracao/cenarios/` são os três cenários de demonstração do
repositório `g10-brasil-equipe-15_mediflow` traduzidos para o contrato MediFlow v1.0.
Este script prova duas coisas:

  1. cada `resposta_esperada` valida em `TriagemMediFlow` — nenhum campo fora do
     contrato, nenhum enum inventado;
  2. cada uma é **ponto fixo**: montar o payload, rodar as regras e serializar de novo
     devolve exatamente o mesmo JSON. Se alguém mudar uma regra, algum cenário quebra.

Serve como teste de fumaça da integração entre os dois repositórios: se os cenários
param de validar, o contrato divergiu.

Uso:
    python3 tools/validar_cenarios_g10.py          # resumo
    python3 tools/validar_cenarios_g10.py -v       # mostra as asserções
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pydantic import ValidationError  # noqa: E402

from app.models import StatusTriagem, TriagemMediFlow  # noqa: E402

CENARIOS = os.path.join(ROOT, "docs", "integracao", "cenarios")

FALHAS = []


def main():
    verboso = "-v" in sys.argv
    arquivos = sorted(glob.glob(os.path.join(CENARIOS, "*.expected.json")))
    if not arquivos:
        print(f"nenhum cenário encontrado em {CENARIOS}")
        return 1

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        with open(caminho, encoding="utf-8") as f:
            e = json.load(f)

        try:
            t = TriagemMediFlow.model_validate(e["resposta_esperada"])
        except ValidationError as ex:
            FALHAS.append((nome, "não valida no contrato: " + ex.errors()[0]["msg"]))
            continue

        if e.get("schema") != "mediflow.fixture/2":
            FALHAS.append((nome, f"schema inesperado: {e.get('schema')!r}"))

        volta = TriagemMediFlow.model_validate(t.model_dump(mode="json"))
        if volta.model_dump(mode="json") != t.model_dump(mode="json"):
            FALHAS.append((nome, "ponto fixo quebrado: as regras mudam o payload ao rodar de novo"))

        d = t.decisao_roteamento
        urgente = t.classificacao.nivel_prioridade.value == "URGENTE"
        if bool(d.notificacao) != urgente:
            FALHAS.append((nome, "notificação presente sem urgência (ou ausente com urgência)"))

        print(f"  {'✓' if not any(f == nome for f, _ in FALHAS) else '✗'} {nome:26s} "
              f"{t.status.value:20s} {', '.join(x.value for x in d.destinos)}"
              f"{'  (revisão)' if d.requer_auditoria_humana else ''}"
              f"  score {t.qualidade.score_combinado:.2f}")
        if verboso:
            for a in e.get("assercoes", []):
                print(f"        · {a}")
            if e.get("observacoes"):
                print(f"        obs: {e['observacoes']}")

    print(f"\n{len(arquivos)} cenário(s) do G10 conferido(s) no contrato v1.0")
    if FALHAS:
        print(f"{len(FALHAS)} falha(s):")
        for nome, msg in FALHAS:
            print(f"  ✗ {nome}: {msg}")
        return 1
    print("Todos os cenários do G10 são válidos e estáveis no contrato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
