# Mapeamento de contrato — repositório do G10 → contrato MediFlow v1.0

**De:** `No-Country-simulation/g10-brasil-equipe-15_mediflow` (branch `develop`)
**Para:** o contrato executável deste repositório (`app/models.py`) e os documentos confirmados
(EF v1.0 atualizada, Análise de Requisitos v1.1, `docs/testes/CONTRATO_DE_DADOS.md`).
**Data:** 22/10/2026

Este arquivo existe para uma coisa só: permitir que os dois repositórios falem a mesma língua
**sem que ninguém reescreva a lógica**. O grafo de decisão do G10 está correto — o que precisa
mudar são os nomes e a forma do payload.

---

## 1. Valores controlados (o bloqueio de integração)

Hoje os 79 `expected.json` deste repositório **não batem** com a resposta da API do G10 por causa
desta tabela. É a mudança mais barata e a de maior efeito.

### 1.1 Prioridade — `NivelPrioridade`

| No G10 (`src/schemas/clinical.py`) | Contrato MediFlow | Referência |
| --- | --- | --- |
| `"Rotina"` | `ROTINA` | §5.2 |
| `"Urgente"` | `URGENTE` | §5.2 |
| `"Ambiguidade/Revisão Humana"` | ⚠️ **não existe** → usar `NAO_IDENTIFICADA` | §5.2, decisão A4 |

"Ambiguidade" não é prioridade: é **cenário** (§8.2). A prioridade tem três valores e o terceiro é
`NAO_IDENTIFICADA`, que é justamente o gatilho da decisão A4 (revisão obrigatória).

### 1.2 Destinos — `DestinoRoteamento`

| No G10 | Contrato MediFlow | Referência |
| --- | --- | --- |
| `"Fila_Emergencia_Medica"` | `FILA_URGENCIA_MEDICA` | §5.4 |
| `"Auditoria_Autorizacoes"` | `AUDITORIA_AUTORIZACOES` | §5.4 |
| `"Farmacia_Hospitalar"` | `FARMACIA_HOSPITALAR` | §5.4 |
| `"Prontuario_Eletronico"` | `PRONTUARIO_ELETRONICO` | §5.4 |
| `"Fila_Revisao_Humana"` | `FILA_REVISAO_HUMANA` | §5.4 |

O README do G10 já usa `FILA_URGENCIA_MEDICA` na tabela de cenários e `FILA_EMERGENCIA_MEDICA` no
texto — ou seja, o próprio repositório está divergente. Vale pelos dois nomes adotar o da §5.4.

### 1.3 Tipo de documento

O G10 usa `tipo_documento: str` livre e normaliza com `normalizar_tipo()`
(`src/workflow/graph.py`). Os rótulos aceitos cobrem os 6 tipos — o comportamento está certo, mas
o payload deve sair com o código estável:

| Rótulo aceito no G10 | Contrato MediFlow |
| --- | --- |
| Receituário Médico / RECEITUARIO MEDICO | `RECEITUARIO_MEDICO` |
| Guia de Procedimento / Guia de Solicitação de Procedimento | `GUIA_PROCEDIMENTO` |
| Laudo de Exame de Imagem / Laudo Exame Imagem | `LAUDO_EXAME_IMAGEM` |
| Laudo Laboratorial / Laudo de Exame Laboratorial | `LAUDO_EXAME_LABORATORIAL` |
| Relatório de Alta / Internação | `RELATORIO_ALTA_INTERNACAO` |
| Atestado Médico | `ATESTADO_MEDICO` |
| (sem mapeamento) | `OUTRO` |
| (ilegível) | `NAO_IDENTIFICADO` |

Sugestão: manter `normalizar_tipo()` para aceitar variações, mas **serializar** o enum canônico.

### 1.4 Status

| No G10 | Contrato MediFlow | Referência |
| --- | --- | --- |
| `status: str`, default `"processado"` | enum `StatusTriagem` com 6 valores | §5.3 |
| `"pendente_auditoria"` | `EM_REVISAO` | §5.3 |
| `"erro"` | `ERRO_PROCESSAMENTO` **ou** `ERRO_PERSISTENCIA` | §5.3, §12 |

Faltam `RECEBIDO` e `PROCESSANDO`, que são obrigatórios no fluxo assíncrono (202 + polling, RF-01).

---

## 2. Campos: formato diferente

| Campo no G10 | Formato no contrato MediFlow | Referência |
| --- | --- | --- |
| `DadosExtraidos.medicamentos: List[str]` | `medicamentos: [{nome, dosagem?, frequencia?}]` | §9.2, RF-08 |
| `DadosExtraidos.exame_realizado: str` | `exames: List[str]` | §9.2 |
| `EntradaWorkflow.urgencia` (fora de `dados_extraidos`) | `dados_extraidos.urgencia: SIM\|NAO\|INDETERMINADO` | decisão A5 |
| `ClassificacaoClinica.especialidade: str` | `especialidade: List[str]` | §9.2 |
| `DecisaoRoteamento.notificacao_gerada` | `decisao_roteamento.notificacao: {gerada, canal, status, mensagem}` | RF-07, §8.2 |
| `ArmazenamentoOCI.status_backup` default `"pendente"` | default `"sucesso"`, `caminho_objeto` opcional | RF-30 |
| `DecisaoWorkflow.alerta_simulado: bool` | vira o objeto `notificacao` registrado | RF-07 |

---

## 3. Blocos que faltam na resposta

| Bloco | Onde está hoje no G10 | Onde deveria estar | Referência |
| --- | --- | --- | --- |
| `destinos` (lista) | existe no `DecisaoWorkflow` interno | ausente em `DecisaoRoteamento` (só `destino_principal`) | §8.2 ("não reduzir a decisão a um destino único") |
| `qualidade` (scores, ausentes, incertos, conflitos, limiar) | existe no `QualidadeWorkflow` interno | ausente em `ResultadoTriagemClinica` | RF-17, RF-18, RN-05 |
| `erro` (`{codigo, mensagem}`) | inexistente | resposta da triagem com status de erro | §12 |

Nos três casos o dado **já é calculado** — só não é exposto.

---

## 4. Regras que faltam

| Regra | Situação no G10 | Referência |
| --- | --- | --- |
| Alto risco sem texto de urgência → fila urgente | não implementado: urgência só vem de `urgencia == "SIM"` ou prioridade `URGENTE` | RN-03 |
| Caminho do bucket por estado | README lista `/recebidos`, `/processados`, `/auditoria_humana`; falta `processados/urgentes/` | RF-29, §13 |
| Documento em revisão → caminho de auditoria | não derivado da decisão | §6 passo 7 |
| `ERRO_PROCESSAMENTO` / `ERRO_PERSISTENCIA` | só existe `etapa: "DECISAO_CALCULADA"` | §5.3, §12 |
| Limites de entrada (10 MB, 20 páginas, extensões, MIME) | `src/ingestion/` vazio | RF-03, decisão A6 |

---

## 5. O que o G10 faz **melhor** do que nós

Registrado para não se perder na convergência:

1. **`idade = 0` é tratada como presente**, não como ausente (`vazio()` em `graph.py`).
2. **Deduplicação de conflitos idênticos** antes de somar a penalidade.
3. **Validação de `NaN` e `Inf` no limiar** (`allow_inf_nan=False`).
4. **`etapa: "DECISAO_CALCULADA"`** — o grafo declara explicitamente que não confirma
   persistência, o que é a leitura mais limpa da RF-30 que já vimos.

---

## 6. Como usar este mapeamento

```bash
# valida os 3 cenários traduzidos contra o contrato executável
python3 tools/validar_cenarios_g10.py
```

Os arquivos de `docs/integracao/cenarios/` são os três cenários de demonstração do G10
traduzidos para o nosso contrato, já validados e estáveis (ponto fixo das regras).
