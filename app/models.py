"""MediFlow — contrato de dados da triagem (v1.0).

Este é o **único** contrato do projeto: o payload que o agente devolve, os
enums aceitos, as regras de decisão e o formato de erro. Tudo o que a equipe
chamar de "JSON de triagem" tem de validar aqui — inclusive os 67
`expected.json` de `tests/fixtures/`.

Regras de negócio implementadas (RF-16, RF-18, RF-21, §5.3, §5.4, §8.2):

  R1. Prioridade `URGENTE` → destino `FILA_URGENCIA_MEDICA` e notificação
      registrada. **Urgência isolada não gera revisão humana**: o caso termina
      em `PROCESSADO`, com `requer_auditoria_humana = False` — é o
      comportamento do exemplo do `Projeto_oracle.pdf` (`status: processado`,
      `requer_auditoria_humana: false`, objeto em `processados/urgentes/`).
      A `FILA_REVISAO_HUMANA` só entra quando há ambiguidade além da urgência
      (R4).
  R2. Ambiguidade → revisão humana. Conta como ambiguidade: campo obrigatório
      ausente (RF-21), campo incerto, conflito detectado, score combinado
      abaixo do limiar, ou tipo fora da taxonomia (`OUTRO`/`NAO_IDENTIFICADO`).
  R3. Sem urgência, a revisão **substitui** o destino primário: o documento vai
      para `FILA_REVISAO_HUMANA` e não para a fila do seu tipo.
  R4. Urgência **com** ambiguidade → os dois destinos: mantém
      `FILA_URGENCIA_MEDICA`, soma `FILA_REVISAO_HUMANA` e termina em
      `EM_REVISAO`. A urgência, sozinha, não revisa; a ambiguidade, sim.
  R5. `score_combinado = min(score_classificacao, score_extracao)`.
      Limiar é **estrito**: 0,85 passa, 0,84 revisa.
  R6. `campos_ausentes` é saída do extrator, não inferência do validador:
      `null` não distingue "o documento não tem o campo" de "o campo não foi
      lido". Só os 5 campos de RF-21 disparam revisão; CID, medicamentos e
      exames ausentes são registrados e **não** bloqueiam.
  R7. Erro de leitura do documento (PDF protegido/corrompido) termina em
      `status=ERRO_PROCESSAMENTO` com `erro.codigo`, sem classificação nem
      dados extraídos. Rejeição de requisição (formato, tamanho, MIME,
      envelope) não gera triagem: é `ErroResposta` (HTTP + código funcional).
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSAO_CONTRATO = "1.0"
LIMIAR_PADRAO = 0.85

#: Campos cuja ausência obriga revisão humana (RF-21).
CAMPOS_OBRIGATORIOS = frozenset({
    "paciente.nome",
    "paciente.idade",
    "medico.nome",
    "medico.crm",
    "diagnostico",
})

#: Destino natural de cada tipo de documento, quando não há urgência nem ambiguidade.
DESTINO_POR_TIPO: dict["TipoDocumento", "Destino"] = {}


class TipoDocumento(str, Enum):
    RECEITUARIO_MEDICO = "RECEITUARIO_MEDICO"
    LAUDO_EXAME_LABORATORIAL = "LAUDO_EXAME_LABORATORIAL"
    LAUDO_EXAME_IMAGEM = "LAUDO_EXAME_IMAGEM"
    GUIA_PROCEDIMENTO = "GUIA_PROCEDIMENTO"
    RELATORIO_ALTA_INTERNACAO = "RELATORIO_ALTA_INTERNACAO"
    ATESTADO_MEDICO = "ATESTADO_MEDICO"
    OUTRO = "OUTRO"
    NAO_IDENTIFICADO = "NAO_IDENTIFICADO"


class NivelPrioridade(str, Enum):
    URGENTE = "URGENTE"
    ROTINA = "ROTINA"
    NAO_IDENTIFICADA = "NAO_IDENTIFICADA"


class StatusTriagem(str, Enum):
    RECEBIDO = "RECEBIDO"
    PROCESSANDO = "PROCESSANDO"
    PROCESSADO = "PROCESSADO"
    EM_REVISAO = "EM_REVISAO"
    ERRO_PROCESSAMENTO = "ERRO_PROCESSAMENTO"
    ERRO_PERSISTENCIA = "ERRO_PERSISTENCIA"


class Destino(str, Enum):
    FILA_URGENCIA_MEDICA = "FILA_URGENCIA_MEDICA"
    FARMACIA_HOSPITALAR = "FARMACIA_HOSPITALAR"
    AUDITORIA_AUTORIZACOES = "AUDITORIA_AUTORIZACOES"
    PRONTUARIO_ELETRONICO = "PRONTUARIO_ELETRONICO"
    FILA_REVISAO_HUMANA = "FILA_REVISAO_HUMANA"


class Urgencia(str, Enum):
    SIM = "SIM"
    NAO = "NAO"
    INDETERMINADO = "INDETERMINADO"


class Gravidade(str, Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


class CodigoErro(str, Enum):
    # Antes da triagem (envelope HTTP)
    FORMATO_NAO_SUPORTADO = "FORMATO_NAO_SUPORTADO"
    CAMPOS_INVALIDOS = "CAMPOS_INVALIDOS"
    REQUISICAO_INVALIDA = "REQUISICAO_INVALIDA"
    ARQUIVO_MAIOR_QUE_LIMITE = "ARQUIVO_MAIOR_QUE_LIMITE"
    MIME_INVALIDO = "MIME_INVALIDO"
    # Durante a leitura do documento (triagem com status de erro)
    PDF_PROTEGIDO = "PDF_PROTEGIDO"
    PDF_CORROMPIDO = "PDF_CORROMPIDO"


DESTINO_POR_TIPO.update({
    TipoDocumento.RECEITUARIO_MEDICO: Destino.FARMACIA_HOSPITALAR,
    TipoDocumento.LAUDO_EXAME_LABORATORIAL: Destino.PRONTUARIO_ELETRONICO,
    TipoDocumento.LAUDO_EXAME_IMAGEM: Destino.PRONTUARIO_ELETRONICO,
    TipoDocumento.GUIA_PROCEDIMENTO: Destino.AUDITORIA_AUTORIZACOES,
    TipoDocumento.RELATORIO_ALTA_INTERNACAO: Destino.PRONTUARIO_ELETRONICO,
    TipoDocumento.ATESTADO_MEDICO: Destino.PRONTUARIO_ELETRONICO,
})


# --------------------------------------------------------------------- entidades
class Paciente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: Optional[str] = None
    idade: Optional[int] = Field(None, ge=0, le=120)


class Crm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numero: Optional[str] = None
    uf: Optional[str] = Field(None, min_length=2, max_length=2)


class Medico(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: Optional[str] = None
    crm: Optional[Crm] = None


class Medicamento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str
    dosagem: Optional[str] = None
    frequencia: Optional[str] = None


class Conflito(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: str
    campos: List[str] = Field(default_factory=list)
    gravidade: Gravidade = Gravidade.ALTA
    descricao: str = ""


# ------------------------------------------------------------------ classificação
class Classificacao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_documento: TipoDocumento
    especialidade: List[str] = Field(default_factory=list)
    nivel_prioridade: NivelPrioridade
    score_classificacao: float = Field(..., ge=0.0, le=1.0)


class DadosExtraidos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paciente: Paciente = Field(default_factory=Paciente)
    medico: Medico = Field(default_factory=Medico)
    diagnostico: Optional[str] = None
    cid: Optional[str] = None
    exames: List[str] = Field(default_factory=list)
    medicamentos: List[Medicamento] = Field(default_factory=list)
    urgencia: Urgencia = Urgencia.INDETERMINADO


class Qualidade(BaseModel):
    """Evidência de extração + scores calculados.

    `campos_ausentes` e `campos_incertos` vêm do extrator; `score_combinado` é
    recalculado pelo validador a partir da classificação e da extração.
    """

    model_config = ConfigDict(extra="forbid")

    score_extracao: float = Field(..., ge=0.0, le=1.0)
    score_combinado: float = Field(0.0, ge=0.0, le=1.0)
    limiar_aplicado: float = Field(LIMIAR_PADRAO, ge=0.0, le=1.0)
    campos_ausentes: List[str] = Field(default_factory=list)
    campos_incertos: List[str] = Field(default_factory=list)
    conflitos: List[Conflito] = Field(default_factory=list)


# ----------------------------------------------------------------------- decisão
class Notificacao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gerada: bool = True
    canal: str = "SIMULADO_SLACK_PLANTAO"
    status: str = "REGISTRADA"
    mensagem: Optional[str] = None


class DecisaoRoteamento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destino_principal: Optional[Destino] = None
    destinos: List[Destino] = Field(default_factory=list)
    requer_auditoria_humana: bool = False
    justificativa_roteamento: str = ""
    notificacao: Optional[Notificacao] = None


class ArmazenamentoOCI(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bucket: str = "mediflow-documentos-clinicos"
    caminho_objeto: Optional[str] = None
    status_backup: str = "sucesso"


class ErroProcessamento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: CodigoErro
    mensagem: str


# ------------------------------------------------------------------- payload final
class TriagemMediFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: StatusTriagem = StatusTriagem.PROCESSADO
    documento_id: str
    classificacao: Optional[Classificacao] = None
    dados_extraidos: Optional[DadosExtraidos] = None
    qualidade: Optional[Qualidade] = None
    decisao_roteamento: Optional[DecisaoRoteamento] = None
    armazenamento_oci: Optional[ArmazenamentoOCI] = None
    erro: Optional[ErroProcessamento] = None

    @model_validator(mode="after")
    def aplicar_regras(self) -> "TriagemMediFlow":
        em_erro = self.status in (StatusTriagem.ERRO_PROCESSAMENTO, StatusTriagem.ERRO_PERSISTENCIA)
        if em_erro:
            if self.erro is None:
                raise ValueError(f"status {self.status.value} exige o bloco 'erro'")
            if self.classificacao is not None or self.dados_extraidos is not None:
                raise ValueError(f"status {self.status.value} não pode ter classificação nem dados")
            self.decisao_roteamento = None
            self.qualidade = None
            return self

        if self.classificacao is None or self.dados_extraidos is None or self.qualidade is None:
            raise ValueError("triagem sem erro exige classificacao, dados_extraidos e qualidade")

        c, d, q = self.classificacao, self.dados_extraidos, self.qualidade
        limiar = q.limiar_aplicado
        q.score_combinado = min(c.score_classificacao, q.score_extracao)
        ausentes, incertos = list(q.campos_ausentes), list(q.campos_incertos)

        urgente = c.nivel_prioridade is NivelPrioridade.URGENTE
        fora_da_taxonomia = c.tipo_documento in (TipoDocumento.OUTRO, TipoDocumento.NAO_IDENTIFICADO)
        abaixo_do_limiar = q.score_combinado < limiar
        falta_obrigatorio = bool(set(ausentes) & CAMPOS_OBRIGATORIOS)
        ambiguidade = bool(
            falta_obrigatorio or incertos or q.conflitos or abaixo_do_limiar or fora_da_taxonomia
        )

        destinos: List[Destino] = []
        if urgente:
            destinos.append(Destino.FILA_URGENCIA_MEDICA)
        elif not ambiguidade:
            destinos.append(DESTINO_POR_TIPO[c.tipo_documento])
        if ambiguidade:
            destinos = ([Destino.FILA_URGENCIA_MEDICA, Destino.FILA_REVISAO_HUMANA]
                        if urgente else [Destino.FILA_REVISAO_HUMANA])

        motivos = []
        if abaixo_do_limiar:
            motivos.append(f"score combinado {q.score_combinado:.2f} < limiar {limiar:.2f}")
        if falta_obrigatorio:
            motivos.append("campos obrigatórios ausentes: " + ", ".join(sorted(set(ausentes) & CAMPOS_OBRIGATORIOS)))
        if incertos:
            motivos.append("campos incertos: " + ", ".join(incertos))
        if q.conflitos:
            motivos.append("conflitos: " + ", ".join(x.tipo for x in q.conflitos))
        if fora_da_taxonomia:
            motivos.append(f"tipo fora da taxonomia: {c.tipo_documento.value}")

        if urgente and ambiguidade:
            justificativa = ("Urgência com ambiguidade: mantém FILA_URGENCIA_MEDICA e acrescenta "
                             "FILA_REVISAO_HUMANA. " + "; ".join(motivos) + ".")
        elif urgente:
            justificativa = ("Urgência clínica: FILA_URGENCIA_MEDICA com alerta registrado. "
                             "Sem ambiguidade, segue sem revisão humana.")
        elif ambiguidade:
            justificativa = "Revisão humana obrigatória: " + "; ".join(motivos) + "."
        else:
            justificativa = (f"Classificação de rotina: {c.tipo_documento.value} encaminhado para "
                             f"{DESTINO_POR_TIPO[c.tipo_documento].value}.")

        decisao = self.decisao_roteamento or DecisaoRoteamento()
        decisao.destinos = destinos
        decisao.destino_principal = destinos[0]
        decisao.requer_auditoria_humana = ambiguidade
        decisao.justificativa_roteamento = justificativa
        decisao.notificacao = (
            Notificacao(mensagem=f"ALERTA URGENTE [{self.documento_id}]: "
                                 f"{d.diagnostico or 'achado crítico em triagem'}")
            if urgente else None
        )
        self.decisao_roteamento = decisao
        self.status = StatusTriagem.EM_REVISAO if decisao.requer_auditoria_humana else StatusTriagem.PROCESSADO
        return self


class ErroResposta(BaseModel):
    """Rejeição de requisição — não chega a ser uma triagem."""

    model_config = ConfigDict(extra="forbid")

    http: int = Field(..., ge=400, le=499)
    codigo_funcional: CodigoErro
    mensagem: str
