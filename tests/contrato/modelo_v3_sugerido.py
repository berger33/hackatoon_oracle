"""Contrato v3 sugerido — o modelo v2.0 da equipe com os ajustes do relatório.

Uso: referência para o `app/models.py` definitivo. Não é o contrato oficial
ainda; o teste `comparar_v3.py` mostra que ele reproduz 57/57 decisões dos
fixtures funcionais e aceita os 10 negativos sem inventar tipo de documento.

Diferenças em relação à v2.0 (todas justificadas em
`docs/testes/REVISAO_DO_MODELO_DE_CONTRATO_v2.md`):

  1. Enums com os tokens do domínio (sem espaços/acentos) e com os valores que
     faltavam: OUTRO, NAO_IDENTIFICADO, NAO_IDENTIFICADA, POUCO_URGENTE fora.
  2. `status` é enum (6 estados da especificação §5.3).
  3. `dados_extraidos` e `decisao_roteamento` passam a ser opcionais: um PDF
     protegido ou corrompido termina em ERRO_PROCESSAMENTO sem dados.
  4. `ErroResposta` separado para os negativos de requisição (HTTP + código).
  5. `especialidade` é lista; `exames` é lista; `medicamentos` com dosagem
     opcional; `medico.crm` é objeto {numero, uf} (sem campo duplicado).
  6. `urgencia` explícito (SIM/NAO/INDETERMINADO) em vez de inferido.
  7. Qualidade carrega `conflitos` estruturados e `campos_incertos`, e o
     validador *preserva* a evidência recebida em vez de zerar.
  8. Regras: urgência ⇒ notificação + EM_REVISAO; ambiguidade sem urgência
     substitui o destino por FILA_REVISAO_HUMANA; com urgência, acrescenta.
  9. `campos_ausentes` e `campos_incertos` são saída do extrator e o validador
     NÃO recalcula: `null` não distingue "campo não existe no documento" de
     "não foi lido". Só a interseção com os 5 campos de RF-21 dispara revisão
     (CID, medicamentos e exames ausentes são registrados e não bloqueiam).
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

LIMIAR_PADRAO = 0.85

OBRIGATORIOS = (
    "paciente.nome", "paciente.idade", "medico.nome", "medico.crm",
    "diagnostico_principal",
)


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


DESTINO_POR_TIPO = {
    TipoDocumento.RECEITUARIO_MEDICO: Destino.FARMACIA_HOSPITALAR,
    TipoDocumento.LAUDO_EXAME_LABORATORIAL: Destino.PRONTUARIO_ELETRONICO,
    TipoDocumento.LAUDO_EXAME_IMAGEM: Destino.PRONTUARIO_ELETRONICO,
    TipoDocumento.GUIA_PROCEDIMENTO: Destino.AUDITORIA_AUTORIZACOES,
    TipoDocumento.RELATORIO_ALTA_INTERNACAO: Destino.PRONTUARIO_ELETRONICO,
    TipoDocumento.ATESTADO_MEDICO: Destino.PRONTUARIO_ELETRONICO,
}


class Paciente(BaseModel):
    nome: Optional[str] = None
    idade: Optional[int] = Field(None, ge=0, le=120)


class Crm(BaseModel):
    numero: Optional[str] = None
    uf: Optional[str] = Field(None, min_length=2, max_length=2)


class MedicoSolicitante(BaseModel):
    nome: Optional[str] = None
    crm: Optional[Crm] = None


class Medicamento(BaseModel):
    nome: str
    dosagem: Optional[str] = None  # o fixture às vezes só tem o nome
    frequencia: Optional[str] = None


class Conflito(BaseModel):
    tipo: str                      # CID_DIAGNOSTICO, DOSE_SUSPEITA, ...
    campos: List[str] = Field(default_factory=list)
    gravidade: Gravidade = Gravidade.ALTA
    descricao: str = ""


class DadosExtraidos(BaseModel):
    paciente: Paciente = Field(default_factory=Paciente)
    medico: MedicoSolicitante = Field(default_factory=MedicoSolicitante)
    diagnostico: Optional[str] = None
    cid: Optional[str] = None
    exames: List[str] = Field(default_factory=list)
    medicamentos: List[Medicamento] = Field(default_factory=list)
    urgencia: Urgencia = Urgencia.INDETERMINADO
    # Saída do extrator, não do validador: um laudo laboratorial legitimamente
    # não tem diagnóstico, então `null` não distingue "não existe" de "não foi
    # lido". Só esta lista carrega a intenção (ver Matriz_LaudoLaboratorial_Texto
    # × Ausencia_Diagnostico).
    campos_ausentes: List[str] = Field(default_factory=list)
    campos_incertos: List[str] = Field(default_factory=list)


class Classificacao(BaseModel):
    tipo_documento: TipoDocumento
    especialidade: List[str] = Field(default_factory=list)
    nivel_prioridade: NivelPrioridade
    score_classificacao: float = Field(..., ge=0.0, le=1.0)


class Qualidade(BaseModel):
    score_classificacao: float = Field(..., ge=0.0, le=1.0)
    score_extracao: float = Field(..., ge=0.0, le=1.0)
    score_combinado: float = Field(..., ge=0.0, le=1.0)
    limiar_aplicado: float = LIMIAR_PADRAO
    campos_ausentes: List[str] = Field(default_factory=list)
    campos_incertos: List[str] = Field(default_factory=list)
    conflitos: List[Conflito] = Field(default_factory=list)


class Notificacao(BaseModel):
    gerada: bool = False
    canal: str = "SIMULADO_SLACK_PLANTAO"
    status: str = "REGISTRADA"
    mensagem: Optional[str] = None


class Decisao(BaseModel):
    destino_principal: Optional[Destino] = None
    destinos: List[Destino] = Field(default_factory=list)
    requer_auditoria_humana: bool = False
    justificativa_roteamento: str = ""
    notificacao: Optional[Notificacao] = None


class ArmazenamentoOCI(BaseModel):
    bucket: str = "mediflow-documentos-clinicos"
    caminho_objeto: Optional[str] = None
    status_backup: str = "sucesso"


class TriagemMediFlow(BaseModel):
    status: StatusTriagem = StatusTriagem.PROCESSADO
    documento_id: str
    classificacao: Optional[Classificacao] = None
    dados_extraidos: Optional[DadosExtraidos] = None
    qualidade: Optional[Qualidade] = None
    decisao_roteamento: Optional[Decisao] = None
    armazenamento_oci: Optional[ArmazenamentoOCI] = None

    @model_validator(mode="after")
    def aplicar_regras(self):
        if self.classificacao is None or self.dados_extraidos is None:
            return self  # erro de processamento: nada a decidir

        c, d = self.classificacao, self.dados_extraidos
        rota = self.decisao_roteamento or Decisao()
        self.decisao_roteamento = rota
        evidencias = self.qualidade  # preserve o que o pipeline já detectou

        ausentes = list(dict.fromkeys(d.campos_ausentes))
        incertos = list(d.campos_incertos)
        conflitos = list(evidencias.conflitos) if evidencias else []
        score_ext = evidencias.score_extracao if evidencias else 1.0
        score = min(c.score_classificacao, score_ext)
        limiar = evidencias.limiar_aplicado if evidencias else LIMIAR_PADRAO

        self.qualidade = Qualidade(
            score_classificacao=c.score_classificacao,
            score_extracao=score_ext,
            score_combinado=score,
            limiar_aplicado=limiar,
            campos_ausentes=ausentes,
            campos_incertos=incertos,
            conflitos=conflitos,
        )

        urgente = c.nivel_prioridade == NivelPrioridade.URGENTE
        ambiguidade = (
            bool(set(ausentes) & set(OBRIGATORIOS))
            or bool(incertos)
            or bool(conflitos)
            or score < limiar
            or c.tipo_documento in (TipoDocumento.OUTRO, TipoDocumento.NAO_IDENTIFICADO)
        )

        destinos: List[Destino] = []
        if urgente:
            destinos.append(Destino.FILA_URGENCIA_MEDICA)
        elif not ambiguidade:
            destinos.append(DESTINO_POR_TIPO[c.tipo_documento])
        if ambiguidade:
            if urgente:
                destinos.append(Destino.FILA_REVISAO_HUMANA)
            else:
                destinos = [Destino.FILA_REVISAO_HUMANA]

        rota.destinos = destinos
        rota.destino_principal = destinos[0]
        rota.requer_auditoria_humana = urgente or ambiguidade
        self.status = (
            StatusTriagem.EM_REVISAO if rota.requer_auditoria_humana else StatusTriagem.PROCESSADO
        )

        if urgente:
            rota.notificacao = Notificacao(
                gerada=True,
                mensagem=(f"ALERTA URGENTE [{self.documento_id}]: "
                          f"{d.diagnostico or 'achado crítico em triagem'}"),
            )
        return self


class ErroResposta(BaseModel):
    """Negativos de requisição: 400/413/415/422, sem chamar o modelo."""

    http: int
    codigo_funcional: str
    mensagem: str
