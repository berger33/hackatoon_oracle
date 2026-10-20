#!/usr/bin/env python3
"""Confere os 67 fixtures contra o contrato oficial (`app/models.py`).

Para cada `expected.json`:

  1. valida `resposta_esperada` no modelo certo — `TriagemMediFlow` nos 59
     funcionais e nos 2 erros de leitura, `ErroResposta` nos 8 negativos;
  2. confere o **ponto fixo**: montar o payload, rodar as regras e serializar de
     novo tem de devolver exatamente o mesmo JSON. Se alguém mudar uma regra,
     algum dos 67 quebra aqui;
  3. confere a coerência dos campos de saída (destino principal = 1º destino,
     revisão = status EM_REVISAO, notificação só em urgência).

Uso:
    python3 tests/testar_contrato.py          # resumo
    python3 tests/testar_contrato.py -v       # um bloco por fixture
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pydantic import ValidationError  # noqa: E402

from app.models import (  # noqa: E402
    CAMPOS_OBRIGATORIOS, ErroResposta, StatusTriagem, TriagemMediFlow,
)

FALHAS = []


def falha(fid, msg):
    FALHAS.append((fid, msg))


def valida(fid, esperado):
    try:
        return TriagemMediFlow.model_validate(esperado)
    except ValidationError as ex:
        falha(fid, "não valida como TriagemMediFlow: " + ex.errors()[0]["msg"])
        return None


def confere_regras(fid, t):
    """Ponto fixo + coerência do que foi decidido."""
    novamente = TriagemMediFlow.model_validate(t.model_dump(mode="json"))
    if novamente.model_dump(mode="json") != t.model_dump(mode="json"):
        falha(fid, "o validador muda o payload ao rodar de novo (ponto fixo quebrado)")
        return

    if t.status is StatusTriagem.ERRO_PROCESSAMENTO:
        if t.erro is None or t.classificacao or t.dados_extraidos:
            falha(fid, "erro de processamento com dados de triagem")
        return

    d = t.decisao_roteamento
    if d.destino_principal is not d.destinos[0]:
        falha(fid, "destino_principal diferente do primeiro destino")
    if d.requer_auditoria_humana != (t.status is StatusTriagem.EM_REVISAO):
        falha(fid, "requer_auditoria_humana incoerente com o status")
    urgente = t.classificacao.nivel_prioridade.value == "URGENTE"
    if bool(d.notificacao) != urgente:
        falha(fid, "notificação presente sem urgência (ou ausente com urgência)")

    q = t.qualidade
    if abs(q.score_combinado - min(t.classificacao.score_classificacao, q.score_extracao)) > 1e-9:
        falha(fid, "score_combinado != min(classificação, extração)")
    if q.campos_ausentes and set(q.campos_ausentes) & CAMPOS_OBRIGATORIOS and not d.requer_auditoria_humana:
        falha(fid, "campo obrigatório ausente sem revisão")
    if q.campos_incertos and not d.requer_auditoria_humana:
        falha(fid, "campo incerto sem revisão")
    if q.conflitos and not d.requer_auditoria_humana:
        falha(fid, "conflito registrado sem revisão")


def main():
    verboso = "-v" in sys.argv
    total = {"funcional": 0, "erro_processamento": 0, "negativo_tecnico": 0}

    for caminho in sorted(glob.glob(os.path.join(ROOT, "tests/fixtures/*/*/expected.json"))):
        e = json.load(open(caminho, encoding="utf-8"))
        fid, tipo = e["fixture_id"], e["tipo_de_teste"]
        total[tipo] = total.get(tipo, 0) + 1

        if e.get("schema") != "mediflow.fixture/2":
            falha(fid, f"schema inesperado: {e.get('schema')!r}")

        if tipo == "negativo_tecnico":
            try:
                ErroResposta.model_validate(e["resposta_esperada"])
            except ValidationError as ex:
                falha(fid, "envelope de erro inválido: " + ex.errors()[0]["msg"])
        else:
            t = valida(fid, e["resposta_esperada"])
            if t is not None:
                confere_regras(fid, t)
                esperado_erro = tipo == "erro_processamento"
                if (t.status is StatusTriagem.ERRO_PROCESSAMENTO) != esperado_erro:
                    falha(fid, "status incoerente com tipo_de_teste")

        if verboso:
            print(f"  {'✓' if not any(f == fid for f, _ in FALHAS) else '✗'} {fid} ({tipo})")

    print(f"Fixtures: {sum(total.values())}  "
          f"({total['funcional']} funcionais + {total['erro_processamento']} erro de leitura + "
          f"{total['negativo_tecnico']} negativos)")
    if FALHAS:
        print(f"\n{len(FALHAS)} falha(s):")
        for fid, msg in FALHAS:
            print(f"  ✗ {fid}: {msg}")
        return 1
    print("Todos os expected.json validam no contrato v1.0 e são ponto fixo das regras.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
