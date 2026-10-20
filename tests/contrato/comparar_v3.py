#!/usr/bin/env python3
"""Confere o contrato v3 sugerido contra os 67 fixtures.

Para cada fixture funcional monta o payload com os *fatos* (classificação,
dados, scores, conflitos e campos incertos) e deixa o validador decidir
sozinho. Compara com `decisao_esperada`. Para os negativos, confere que o
modelo de erro aceita o envelope (8) e que a falha de leitura de PDF cabe em
ERRO_PROCESSAMENTO sem dados extraídos (2).

Uso: python3 tests/contrato/comparar_v3.py [-v]
"""
import glob
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)

from pydantic import ValidationError  # noqa: E402

from modelo_v3_sugerido import (  # noqa: E402
    Classificacao, Conflito, Crm, DadosExtraidos, Decisao, ErroResposta,
    Gravidade, Medicamento, MedicoSolicitante, NivelPrioridade, Paciente,
    Qualidade, StatusTriagem, TipoDocumento, TriagemMediFlow, Urgencia,
)


def score_de(e):
    s = e.get("score_forcado")
    return (s["score_classificacao"], s["score_extracao"]) if s else (0.92, 0.92)


def monta(e):
    c, d = e["classificacao_esperada"], e["dados_esperados"]
    s_class, s_ext = score_de(e)
    crm = d["medico"]["crm"]
    conflitos = [
        Conflito(tipo=x["tipo"], campos=x["campos"],
                 gravidade=Gravidade(x["gravidade"]), descricao=x["descricao"])
        for x in (e.get("conflitos_esperados") or [])
    ]
    return TriagemMediFlow(
        documento_id=f"DOC-{e['fixture_id'][:12].upper()}",
        classificacao=Classificacao(
            tipo_documento=TipoDocumento(c["tipo_documento"]),
            especialidade=list(c["especialidade"]),
            nivel_prioridade=NivelPrioridade(c["nivel_prioridade"]),
            score_classificacao=s_class,
        ),
        dados_extraidos=DadosExtraidos(
            paciente=Paciente(**d["paciente"]),
            medico=MedicoSolicitante(
                nome=d["medico"]["nome"],
                crm=Crm(**crm) if crm else None,
            ),
            diagnostico=d["diagnostico"],
            cid=d["cid"],
            exames=list(d["exames"]),
            medicamentos=[Medicamento(nome=m) for m in d["medicamentos"]],
            urgencia=Urgencia(d["urgencia"]),
            campos_ausentes=list(d.get("campos_ausentes") or []),
            campos_incertos=list(d.get("campos_incertos") or []),
        ),
        # evidências que o pipeline entrega; o validador deve preservá-las
        qualidade=Qualidade(
            score_classificacao=s_class,
            score_extracao=s_ext,
            score_combinado=min(s_class, s_ext),
            conflitos=conflitos,
        ),
        decisao_roteamento=Decisao(),
    )


def main():
    verboso = "-v" in sys.argv
    ok, falhas = 0, []
    neg_ok, neg_falhas = 0, []

    for f in sorted(glob.glob(os.path.join(ROOT, "tests/fixtures/*/*/expected.json"))):
        e = json.load(open(f, encoding="utf-8"))
        fid = e["fixture_id"]

        if "erro_esperado" in e:
            try:
                ErroResposta(**e["erro_esperado"])
                neg_ok += 1
            except ValidationError as ex:
                neg_falhas.append((fid, str(ex).splitlines()[0]))
            continue

        if e["classificacao_esperada"]["tipo_documento"] == "N/A":
            t = TriagemMediFlow(
                documento_id=f"DOC-{fid[:12].upper()}",
                status=StatusTriagem.ERRO_PROCESSAMENTO,
            )
            if t.status is StatusTriagem.ERRO_PROCESSAMENTO and t.dados_extraidos is None:
                neg_ok += 1
            else:
                neg_falhas.append((fid, "ERRO_PROCESSAMENTO não cabe no modelo"))
            continue

        t = monta(e)
        esp = e["decisao_esperada"]
        got = {
            "status": t.status.value,
            "destinos": [x.value for x in t.decisao_roteamento.destinos],
            "requer_auditoria_humana": t.decisao_roteamento.requer_auditoria_humana,
            "notificacao": bool(t.decisao_roteamento.notificacao
                                and t.decisao_roteamento.notificacao.gerada),
        }
        difs = [f"{k}: esperado {esp[k]!r}, modelo {got[k]!r}"
                for k in esp if esp[k] != got[k]]
        # evidência preservada?
        if e.get("conflitos_esperados") and not t.qualidade.conflitos:
            difs.append("conflitos apagados")
        if e["dados_esperados"].get("campos_incertos") and not t.qualidade.campos_incertos:
            difs.append("campos_incertos apagados")
        if difs:
            falhas.append((fid, difs))
        else:
            ok += 1

    total = ok + len(falhas)
    print(f"Funcionais: {ok}/{total} decisões reproduzidas pelo validador v3")
    for fid, difs in falhas:
        print(f"  ✗ {fid}")
        for d in difs:
            print(f"      {d}")
    print(f"Negativos:  {neg_ok}/{neg_ok + len(neg_falhas)} aceitos pelo contrato de erro")
    for fid, msg in neg_falhas:
        print(f"  ✗ {fid}: {msg}")
    if verboso:
        for f in sorted(glob.glob(os.path.join(ROOT, "tests/fixtures/*/*/expected.json"))):
            e = json.load(open(f, encoding="utf-8"))
            if "erro_esperado" in e:
                print(f"  ✓ {e['fixture_id']:34s} {e['erro_esperado']['http']} "
                      f"{e['erro_esperado']['codigo_funcional']}")
    print()
    print("Contrato v3 fecha os 67 fixtures." if not falhas and not neg_falhas
          else f"{len(falhas) + len(neg_falhas)} divergência(s).")
    return 1 if falhas or neg_falhas else 0


if __name__ == "__main__":
    sys.exit(main())
