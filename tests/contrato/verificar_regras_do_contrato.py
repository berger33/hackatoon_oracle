#!/usr/bin/env python3
"""Prova que as regras de decisão do contrato são fechadas sobre os 67 fixtures.

Este script não usa o modelo da equipe: ele aplica *apenas* as regras que os
fixtures documentam e confere se elas reproduzem, sozinhas, o `decisao_esperada`
de cada caso. Serve de especificação executável para o `app/models.py`:

  - entrada: tipo, prioridade, score combinado, campos ausentes, campos
    incertos e conflitos (as duas últimas são *evidências* produzidas pelo
    pipeline, não algo que o schema possa adivinhar);
  - saída: status, destinos, requer_auditoria_humana, notificação.

Regras (RF-16, RF-18, RF-21, §8.2):
  R1. Urgência  → FILA_URGENCIA_MEDICA + notificação; status EM_REVISAO.
  R2. Ambiguidade (campo obrigatório ausente, campo incerto, conflito ou
      score combinado < 0.85) → revisão humana.
  R3. Sem urgência, revisão *substitui* o destino primário por
      FILA_REVISAO_HUMANA (não acumula).
  R4. Com urgência, revisão *acrescenta* FILA_REVISAO_HUMANA (caso misto).
  R5. OUTRO e NAO_IDENTIFICADO são sempre revisão.
  R6. campos_ausentes registra também ausências não bloqueantes (CID,
      medicamentos, exames); só o conjunto obrigatório dispara revisão.

Uso: python3 tests/contrato/verificar_regras_do_contrato.py [-v]
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OBRIGATORIOS = {
    "paciente.nome", "paciente.idade", "medico.nome", "medico.crm",
    "diagnostico_principal",
}
DESTINO_POR_TIPO = {
    "RECEITUARIO_MEDICO": "FARMACIA_HOSPITALAR",
    "LAUDO_EXAME_LABORATORIAL": "PRONTUARIO_ELETRONICO",
    "LAUDO_EXAME_IMAGEM": "PRONTUARIO_ELETRONICO",
    "GUIA_PROCEDIMENTO": "AUDITORIA_AUTORIZACOES",
    "RELATORIO_ALTA_INTERNACAO": "PRONTUARIO_ELETRONICO",
    "ATESTADO_MEDICO": "PRONTUARIO_ELETRONICO",
}
LIMIAR = 0.85
ERROS = []  # (fixture, esperado, calculado)


def score_combinado(e):
    s = e.get("score_forcado")
    if s:
        return min(s["score_classificacao"], s["score_extracao"])
    return 1.0  # acima do limiar; o valor exato não importa para a decisão


def decide(e):
    c, dd = e["classificacao_esperada"], e["dados_esperados"]
    tipo, prio = c["tipo_documento"], c["nivel_prioridade"]
    ausentes = set(dd.get("campos_ausentes") or [])
    incertos = dd.get("campos_incertos") or []
    conflitos = e.get("conflitos_esperados") or []

    urgente = prio == "URGENTE"
    ambiguidade = (
        bool(ausentes & OBRIGATORIOS)
        or bool(incertos)
        or bool(conflitos)
        or score_combinado(e) < LIMIAR
        or tipo in ("OUTRO", "NAO_IDENTIFICADO")
    )

    destinos = []
    if urgente:
        destinos.append("FILA_URGENCIA_MEDICA")
    elif not ambiguidade:
        destinos.append(DESTINO_POR_TIPO[tipo])

    if ambiguidade:
        if urgente:
            destinos.append("FILA_REVISAO_HUMANA")
        else:
            destinos = ["FILA_REVISAO_HUMANA"]

    status = "EM_REVISAO" if (urgente or ambiguidade) else "PROCESSADO"
    return {
        "status": status,
        "destinos": destinos,
        "requer_auditoria_humana": status == "EM_REVISAO",
        "notificacao": urgente,
    }


def main():
    verboso = "-v" in sys.argv
    funcionais = 0

    for f in sorted(glob.glob(os.path.join(ROOT, "tests/fixtures/*/*/expected.json"))):
        e = json.load(open(f, encoding="utf-8"))
        if "erro_esperado" in e or e["classificacao_esperada"]["tipo_documento"] == "N/A":
            continue  # negativos são checados no bloco de baixo
        esperado, calculado = e["decisao_esperada"], decide(e)
        if esperado == calculado:
            funcionais += 1
        else:
            ERROS.append((e["fixture_id"], esperado, calculado))

    # --- negativos: 8 com envelope de erro + 2 com status ERRO_PROCESSAMENTO
    negativos = []
    for f in sorted(glob.glob(os.path.join(ROOT, "tests/fixtures/*/*/expected.json"))):
        e = json.load(open(f, encoding="utf-8"))
        if "erro_esperado" in e:
            err = e["erro_esperado"]
            ok = isinstance(err.get("http"), int) and err.get("codigo_funcional")
            negativos.append((e["fixture_id"], "envelope de erro", ok, err))
        elif e["decisao_esperada"]["status"] == "ERRO_PROCESSAMENTO":
            d = e["decisao_esperada"]
            ok = (
                d["destinos"] == ["N/A"]
                and d["requer_auditoria_humana"] is None
                and not d["notificacao"]
            )
            negativos.append((e["fixture_id"], "triagem com ERRO_PROCESSAMENTO", ok, None))

    print(f"Funcionais: {funcionais}/{funcionais + len(ERROS)} reproduzidos pelas regras")
    for fid, esp, calc in ERROS:
        print(f"  ✗ {fid}\n      esperado : {esp}\n      calculado: {calc}")

    falhas_neg = [n for n in negativos if not n[2]]
    print(f"Negativos:  {len(negativos) - len(falhas_neg)}/{len(negativos)} com contrato de erro explícito")
    for fid, tipo, ok, err in falhas_neg:
        print(f"  ✗ {fid} ({tipo}) {err or ''}")
    if verboso:
        for fid, tipo, ok, err in negativos:
            print(f"  {'✓' if ok else '✗'} {fid:34s} {tipo:32s} {err or ''}")

    total_falhas = len(ERROS) + len(falhas_neg)
    print("\nContrato fechado." if total_falhas == 0 else f"\n{total_falhas} divergência(s).")
    return 1 if total_falhas else 0


if __name__ == "__main__":
    sys.exit(main())
