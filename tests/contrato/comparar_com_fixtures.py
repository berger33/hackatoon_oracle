#!/usr/bin/env python3
"""Testa o modelo de contrato da v2.0 contra os 67 fixtures do catálogo.

O objetivo é responder, com dados e não com opinião, a duas perguntas:

  (a) ECHO   — se o pipeline entrega exatamente o que o fixture espera, o
               validador do modelo preserva esse resultado ou o sobrescreve?
  (b) DERIVE — partindo apenas dos fatos clínicos (scores, dados, prioridade),
               o validador chega sozinho ao resultado esperado?

Uso:
    python3 tests/contrato/comparar_com_fixtures.py            # resumo
    python3 tests/contrato/comparar_com_fixtures.py --detalhe  # caso a caso
"""
import glob
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)

from modelo_v2_proposto import (  # noqa: E402
    ArmazenamentoOCI, ClassificacaoDocumento, DadosClinicosExtraidos,
    DecisaoRoteamento, DestinoRoteamentoEnum, MedicamentoPrescrito,
    MedicoSolicitante, NivelPrioridadeEnum, Notificacao, Paciente,
    TipoDocumentoEnum, TriagemMediFlow, CrmEstruturado,
)

# ---------------------------------------------------------------- mapeamentos
TIPO = {
    "RECEITUARIO_MEDICO": TipoDocumentoEnum.RECEITUARIO_MEDICO,
    "LAUDO_EXAME_LABORATORIAL": TipoDocumentoEnum.LAUDO_LABORATORIAL,
    "LAUDO_EXAME_IMAGEM": TipoDocumentoEnum.LAUDO_IMAGEM,
    "GUIA_PROCEDIMENTO": TipoDocumentoEnum.GUIA_SOLICITACAO,
    "RELATORIO_ALTA_INTERNACAO": TipoDocumentoEnum.RELATORIO_ALTA,
    "ATESTADO_MEDICO": TipoDocumentoEnum.ATESTADO_MEDICO,
}
PRIO = {"URGENTE": NivelPrioridadeEnum.URGENTE, "ROTINA": NivelPrioridadeEnum.ROTINA}
DEST = {
    "FILA_URGENCIA_MEDICA": DestinoRoteamentoEnum.EMERGENCIA_MEDICA,
    "FARMACIA_HOSPITALAR": DestinoRoteamentoEnum.FARMACIA_HOSPITALAR,
    "AUDITORIA_AUTORIZACOES": DestinoRoteamentoEnum.AUDITORIA_AUTORIZACOES,
    "PRONTUARIO_ELETRONICO": DestinoRoteamentoEnum.PRONTUARIO_ELETRONICO,
    "FILA_REVISAO_HUMANA": DestinoRoteamentoEnum.REVISAO_HUMANA,
}
DEST_INV = {v: k for k, v in DEST.items()}


def carrega_fixtures():
    for f in sorted(glob.glob(os.path.join(ROOT, "tests/fixtures/*/*/expected.json"))):
        yield os.path.basename(os.path.dirname(f)), json.load(open(f, encoding="utf-8"))


def score_de(e):
    forcado = e.get("score_forcado")
    if forcado:
        return forcado["score_classificacao"], forcado["score_extracao"]
    return 0.92, 0.92  # valor confortável acima do limiar


def monta(fid, e, modo):
    """Converte o expected.json num payload do modelo. modo = 'echo' | 'derive'."""
    c, d, dd = e["classificacao_esperada"], e["decisao_esperada"], e["dados_esperados"]
    s_class, s_ext = score_de(e)

    esperados = [DEST[x] for x in d["destinos"] if x in DEST]
    if not esperados:
        raise ValueError("sem destino representável")

    meds = []
    for m in dd["medicamentos"]:
        meds.append(MedicamentoPrescrito(nome=str(m), dosagem="conforme receita"))

    crm = dd["medico"]["crm"] or {}
    medico = MedicoSolicitante(
        nome=dd["medico"]["nome"],
        crm=f"{crm.get('numero')}-{crm.get('uf')}" if crm.get("numero") else None,
        crm_detalhado=CrmEstruturado(numero=crm.get("numero"), uf=crm.get("uf")) if crm else None,
    )
    dados = DadosClinicosExtraidos(
        paciente=Paciente(nome=dd["paciente"]["nome"], idade=dd["paciente"]["idade"]),
        medico_solicitante=medico,
        exame_ou_procedimento=dd["exames"][0] if dd["exames"] else None,
        diagnostico_principal=dd["diagnostico"],
        cid_extraido=dd["cid"],
        medicamentos=meds,
        score_confianca_extracao=s_ext,
    )

    if modo == "echo":
        decisao = DecisaoRoteamento(
            destino_principal=esperados[0],
            destinos=esperados,
            requer_auditoria_humana=bool(d["requer_auditoria_humana"]),
            justificativa_roteamento="fixture",
            notificacao_gerada=Notificacao(gerada=True) if d["notificacao"] else None,
        )
        status = d["status"]
    else:  # derive: só os fatos, roteamento neutro
        decisao = DecisaoRoteamento(
            destino_principal=esperados[0],
            destinos=[],
            requer_auditoria_humana=False,
            justificativa_roteamento="fixture",
            notificacao_gerada=None,
        )
        status = "PROCESSADO"

    return TriagemMediFlow(
        status=status,
        documento_id=f"DOC-{fid[:12].upper()}",
        classificacao=ClassificacaoDocumento(
            tipo_documento=TIPO[c["tipo_documento"]],
            especialidade=c["especialidade"][0] if c["especialidade"] else None,
            nivel_prioridade=PRIO[c["nivel_prioridade"]],
            score_confianca_classificacao=s_class,
        ),
        dados_extraidos=dados,
        decisao_roteamento=decisao,
        armazenamento_oci=ArmazenamentoOCI(caminho_objeto=f"processados/{fid}.json"),
    )


def compara(saida, e):
    """Compara o resultado do modelo com o expected. Devolve lista de diferenças."""
    d = e["decisao_esperada"]
    difs = []
    if saida.status != d["status"]:
        difs.append(f"status: esperado {d['status']}, modelo {saida.status}")

    destinos = sorted(DEST_INV[x] for x in saida.decisao_roteamento.destinos)
    if destinos != sorted(d["destinos"]):
        difs.append(f"destinos: esperado {d['destinos']}, modelo {destinos}")

    if saida.decisao_roteamento.requer_auditoria_humana != bool(d["requer_auditoria_humana"]):
        difs.append(f"revisão: esperado {d['requer_auditoria_humana']}, "
                    f"modelo {saida.decisao_roteamento.requer_auditoria_humana}")

    notif = bool(saida.decisao_roteamento.notificacao_gerada
                 and saida.decisao_roteamento.notificacao_gerada.gerada)
    if notif != bool(d["notificacao"]):
        difs.append(f"notificação: esperado {d['notificacao']}, modelo {notif}")

    # evidências que o modelo recebeu (ou deveria calcular)
    dd = e["dados_esperados"]
    if dd.get("conflitos_esperados") is not None:
        pass
    if e.get("conflitos_esperados"):
        if not saida.qualidade or not saida.qualidade.conflitos:
            difs.append("conflitos: esperado registrar, modelo apagou")
    if dd.get("campos_incertos"):
        if not saida.qualidade or not saida.qualidade.campos_incerto:
            difs.append("campos_incertos: esperado registrar, modelo apagou")
    return difs


def main():
    detalhe = "--detalhe" in sys.argv
    total = 0
    nao_representavel = []
    resultado = {"echo": {"ok": 0, "falha": []}, "derive": {"ok": 0, "falha": []}}

    for fid, e in carrega_fixtures():
        total += 1
        if "erro_esperado" in e:
            nao_representavel.append((fid, "negativo técnico: o modelo não tem bloco de erro"))
            continue
        tipo = e["classificacao_esperada"]["tipo_documento"]
        prio = e["classificacao_esperada"]["nivel_prioridade"]
        if tipo not in TIPO:
            nao_representavel.append((fid, f"tipo_documento {tipo!r} não existe no enum"))
            continue
        if prio not in PRIO:
            nao_representavel.append((fid, f"nivel_prioridade {prio!r} não existe no enum"))
            continue

        for modo in ("echo", "derive"):
            try:
                saida = monta(fid, e, modo)
            except Exception as ex:  # noqa: BLE001
                resultado[modo]["falha"].append((fid, [f"erro de validação: {ex}"]))
                continue
            difs = compara(saida, e)
            if difs:
                resultado[modo]["falha"].append((fid, difs))
            else:
                resultado[modo]["ok"] += 1

    representaveis = total - len(nao_representavel)
    print(f"Fixtures: {total}")
    print(f"Representáveis no modelo: {representaveis}   "
          f"Fora do modelo: {len(nao_representavel)}")
    print()
    for modo, rotulo in (("echo", "(a) ECHO   — o modelo preserva o resultado esperado?"),
                         ("derive", "(b) DERIVE — o modelo chega sozinho ao resultado esperado?")):
        r = resultado[modo]
        print(f"{rotulo}")
        print(f"   {r['ok']}/{representaveis} ok · {len(r['falha'])} divergências")
        grupos = {}
        for fid, difs in r["falha"]:
            chave = difs[0].split(":")[0]
            grupos.setdefault(chave, []).append(fid)
        for chave, ids in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
            print(f"     {chave:22s} {len(ids):2d}x  {', '.join(ids[:4])}"
                  + (" ..." if len(ids) > 4 else ""))
        if detalhe:
            for fid, difs in r["falha"]:
                print(f"     - {fid}")
                for d in difs:
                    print(f"         {d}")
        print()

    print("Fora do modelo:")
    for fid, motivo in nao_representavel:
        print(f"   - {fid:42s} {motivo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
