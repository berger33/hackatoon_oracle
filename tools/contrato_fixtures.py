#!/usr/bin/env python3
"""Monta os `expected.json` a partir do contrato oficial (`app/models.py`).

Os geradores descrevem **fatos clínicos** (tipo, prioridade, dados, evidências).
Quem decide status, destinos, revisão e notificação é o contrato. Este módulo:

1. monta o payload `TriagemMediFlow` com os fatos do caso;
2. confere se o desfecho calculado bate com a intenção escrita à mão no caso
   (se não bater, aborta a geração — é assim que uma regra nova quebra o teste);
3. serializa o `expected.json` no formato `mediflow.fixture/2`.

Assim os 77 arquivos são, por construção, instâncias válidas do contrato.
"""
import hashlib
import re

from app.models import (
    Classificacao, Conflito, Crm, DadosExtraidos, Gravidade, Medico, Medicamento,
    NivelPrioridade, Notificacao, Paciente, Qualidade, StatusTriagem,
    TipoDocumento, TriagemMediFlow, Urgencia, CodigoErro, ErroProcessamento,
    LIMIAR_PADRAO,
)

SCHEMA = "mediflow.fixture/2"

#: Scores usados quando o caso não força valores (folga confortável acima do limiar).
SCORE_CLASSIFICACAO_PADRAO = 0.93
SCORE_EXTRACAO_PADRAO = 0.91

_RX_MEDICAMENTO = re.compile(
    r"^(?P<nome>.+?)\s+(?P<dosagem>\d[\d.,]*(?:\s*/\s*\d+)?\s*"
    r"(?:mg|mcg|g|mL|ml|UI|%)(?:\s*/\s*\d+\s*(?:mg|mL|ml))?)$"
)

#: Caminhos aceitos por compatibilidade (nomes que já existiram nas tabelas).
_ALIASES = {"diagnostico_principal": "diagnostico", "cid_extraido": "cid",
            "medicamentos[0].dose": "medicamentos[0].dosagem"}


def documento_id(fixture_id):
    """ID estável e determinístico (mesmo documento, mesmo ID a cada geração)."""
    return "DOC-" + hashlib.sha1(fixture_id.encode("utf-8")).hexdigest()[:8].upper()


def medicamento(linha):
    """'Losartana potássica 50 mg' → {nome: 'Losartana potássica', dosagem: '50 mg'}."""
    m = _RX_MEDICAMENTO.match(linha.strip())
    if m:
        return {"nome": m.group("nome"), "dosagem": m.group("dosagem")}
    return {"nome": linha.strip()}


def _normaliza_caminhos(caminhos):
    return [_ALIASES.get(c, c) for c in (caminhos or [])]


def _score(exp):
    forcado = exp.get("score") or {}
    return (forcado.get("score_classificacao", SCORE_CLASSIFICACAO_PADRAO),
            forcado.get("score_extracao", SCORE_EXTRACAO_PADRAO),
            forcado.get("limiar", LIMIAR_PADRAO))


def payload(fixture_id, exp):
    """Constrói o `TriagemMediFlow` esperado a partir dos fatos do caso."""
    if exp.get("erro"):
        return TriagemMediFlow(
            documento_id=documento_id(fixture_id),
            status=StatusTriagem.ERRO_PROCESSAMENTO,
            erro=ErroProcessamento(**exp["erro"]),
        )

    dados = exp["dados"]
    medico = dados.get("medico") or {}
    s_class, s_ext, limiar = _score(exp)
    conflitos = [
        Conflito(tipo=x["tipo"], campos=_normaliza_caminhos(x["campos"]),
                 gravidade=Gravidade(x.get("gravidade", "ALTA")),
                 descricao=x.get("descricao", ""))
        for x in (exp.get("conflitos") or [])
    ]
    return TriagemMediFlow(
        documento_id=documento_id(fixture_id),
        classificacao=Classificacao(
            tipo_documento=TipoDocumento(exp["tipo"]),
            especialidade=list(exp.get("esp") or []),
            nivel_prioridade=NivelPrioridade(exp["prio"]),
            score_classificacao=s_class,
        ),
        dados_extraidos=DadosExtraidos(
            paciente=Paciente(**dados["paciente"]),
            medico=Medico(nome=medico.get("nome"),
                          crm=Crm(**medico["crm"]) if medico.get("crm") else None),
            diagnostico=dados.get("diagnostico"),
            cid=dados.get("cid"),
            exames=list(dados.get("exames") or []),
            medicamentos=[Medicamento(**medicamento(m)) for m in dados.get("medicamentos") or []],
            urgencia=Urgencia(dados.get("urgencia", "INDETERMINADO")),
        ),
        qualidade=Qualidade(
            score_extracao=s_ext,
            limiar_aplicado=limiar,
            campos_ausentes=_normaliza_caminhos(dados.get("campos_ausentes")),
            campos_incertos=_normaliza_caminhos(dados.get("campos_incertos")),
            conflitos=conflitos,
        ),
    )


def conferir(t, exp, fixture_id):  # noqa: PLR0912 - mensagens explícitas valem a repetição
    """Aborta a geração se o contrato não reproduzir a intenção escrita no caso."""
    problemas = []
    if exp.get("erro"):
        if t.status is not StatusTriagem.ERRO_PROCESSAMENTO or t.erro is None:
            problemas.append("caso de erro não terminou em ERRO_PROCESSAMENTO")
    else:
        d = t.decisao_roteamento
        if t.status.value != exp["status"]:
            problemas.append(f"status: caso={exp['status']} contrato={t.status.value}")
        if [x.value for x in d.destinos] != list(exp["dest"]):
            problemas.append(f"destinos: caso={exp['dest']} contrato={[x.value for x in d.destinos]}")
        if d.requer_auditoria_humana != bool(exp["rev"]):
            problemas.append(f"revisão: caso={exp['rev']} contrato={d.requer_auditoria_humana}")
        notif = bool(d.notificacao and d.notificacao.gerada)
        if notif != bool(exp["notif"]):
            problemas.append(f"notificação: caso={exp['notif']} contrato={notif}")
    if problemas:
        raise SystemExit(
            f"\n[contrato] {fixture_id}: a intenção do caso diverge do contrato v1.0\n  - "
            + "\n  - ".join(problemas)
            + "\n  Ajuste a tabela do caso ou as regras em app/models.py — mas não gere um "
              "expected.json que não represente o contrato."
        )


def expected_json(fixture_id, exp, base, assercoes, observacoes="", rendicoes=True,
                  rendicoes_extra=None):
    """Objeto completo do `expected.json` (payload já calculado pelo contrato).

    `rendicoes_extra` declara arquivos além de txt/pdf/jpg — é assim que os
    casos de formato (PNG, WEBP) documentam qual arquivo está sob teste. A
    lista é a fonte da verdade para o verificador de consistência.
    """
    t = payload(fixture_id, exp)
    conferir(t, exp, fixture_id)
    corpo = t.model_dump(mode="json", exclude_none=False)

    renditions = {
        "txt": f"{base}/{fixture_id}/{fixture_id}.txt",
        "pdf": f"{base}/{fixture_id}/{fixture_id}.pdf",
        "jpg": f"{base}/{fixture_id}/{fixture_id}.jpg",
    }
    formatos = ["TXT", "PDF", "JPG"]
    for chave, sufixo in (rendicoes_extra or {}).items():
        renditions[chave] = f"{base}/{fixture_id}/{fixture_id}.{sufixo}"
        formatos.append(sufixo.upper())

    out = {
        "schema": SCHEMA,
        "fixture_id": fixture_id,
        "documento_ficticio": True,
        "tipo_de_teste": "erro_processamento" if exp.get("erro") else "funcional",
        "entrada": {
            "formatos_disponiveis": formatos,
            "renditions": renditions,
        } if rendicoes else {},
        "resposta_esperada": corpo,
    }
    if exp.get("score"):
        out["modo_fixture"] = {
            "score_forcado": {
                "score_classificacao": exp["score"]["score_classificacao"],
                "score_extracao": exp["score"]["score_extracao"],
            }
        }
    out["assercoes"] = list(assercoes)
    out["observacoes"] = observacoes
    return out


def expected_negativo(fixture_id, arquivo, http, codigo, mensagem, assercoes, observacoes=""):
    """Envelope de rejeição de requisição (não é triagem)."""
    return {
        "schema": SCHEMA,
        "fixture_id": fixture_id,
        "documento_ficticio": True,
        "tipo_de_teste": "negativo_tecnico",
        "entrada": {
            "requisicao": "POST /api/v1/triagens",
            "arquivo": arquivo,
        },
        "resposta_esperada": {
            "http": http,
            "codigo_funcional": codigo,
            "mensagem": mensagem,
        },
        "assercoes": list(assercoes),
        "observacoes": observacoes,
    }


__all__ = [
    "SCHEMA", "CodigoErro", "documento_id", "medicamento", "payload", "conferir",
    "expected_json", "expected_negativo", "Notificacao", "LIMIAR_PADRAO",
]
