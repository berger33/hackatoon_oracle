# Issues para o repositório do G10 — prontas para colar

**Repositório:** `No-Country-simulation/g10-brasil-equipe-15_mediflow`
**Branch alvo:** `develop`
**Data:** 22/10/2026

Dez issues, em ordem de prioridade. Cada uma traz a referência no documento que originou a
exigência — é só copiar o bloco como corpo da issue.

> Antes de abrir: as três primeiras são as que destravam a integração com os 79 fixtures
> já aprovados. Sem elas, nenhuma resposta da API casa com o `expected.json` do caso.

---

## 1 — Adotar os valores canônicos dos enums de prioridade e destino

**Labels:** `contrato`, `prioridade-alta`

Os valores atuais (`"Rotina"`, `"Urgente"`, `"Fila_Emergencia_Medica"`, `"Prontuario_Eletronico"`…)
diferem dos valores controlados da especificação, e o próprio README do repositório usa uma
grafia diferente do código.

**Referências:** EF v1.0 §5.2 (prioridade), §5.4 (destinos), §9.2 (exemplo de payload).

**O que fazer:** trocar os valores dos enums `NivelPrioridade` e `DestinoRoteamento` pelos
canônicos da tabela em `MAPEAMENTO_DE_CONTRATO.md` §1. Manter `normalizar_tipo()` aceitando
variações de rótulo na entrada, mas **serializar** sempre o valor canônico.

**Critério de aceite:**
- [ ] `NivelPrioridade` serializa `ROTINA`, `URGENTE`, `NAO_IDENTIFICADA`
- [ ] `DestinoRoteamento` serializa `FILA_URGENCIA_MEDICA`, `FARMACIA_HOSPITALAR`,
      `AUDITORIA_AUTORIZACOES`, `PRONTUARIO_ELETRONICO`, `FILA_REVISAO_HUMANA`
- [ ] README e código usam exatamente os mesmos nomes
- [ ] Os 48 testes continuam passando

---

## 2 — `NAO_IDENTIFICADA` é prioridade; "Ambiguidade/Revisão Humana" não é

**Labels:** `contrato`, `regra-de-negócio`

Hoje o terceiro valor de prioridade é `"Ambiguidade/Revisão Humana"`. Ambiguidade é **cenário**
(§8.2), não prioridade. A especificação define três valores de prioridade, e o terceiro é
`NAO_IDENTIFICADA`.

**Referências:** EF v1.0 §5.2; decisão A4 de 21/10/2026 (prioridade não identificada gera revisão).

**O que fazer:** renomear o membro `AMBIGUO` para `NAO_IDENTIFICADA` com o valor
`"NAO_IDENTIFICADA"`. O comportamento atual (adicionar `classificacao.nivel_prioridade` aos
campos incertos, gerando revisão) está **correto** e deve ser mantido.

**Critério de aceite:**
- [ ] `test_prioridade_ambigua_exige_revisao` continua passando com o valor novo
- [ ] `data/samples/03_cenario_ambiguidade.json` atualizado para `"NAO_IDENTIFICADA"`

---

## 3 — Expor `destinos` (lista) e a notificação como objeto

**Labels:** `contrato`, `prioridade-alta`

O modelo interno `DecisaoWorkflow` já tem `destinos`, mas o modelo da API
(`DecisaoRoteamento`) expõe só `destino_principal`. A especificação é explícita: quando
urgência e ambiguidade coexistem, o payload registra **os dois destinos**.

**Referências:** EF v1.0 §8.2 ("sem reduzir a decisão a um destino único"); RF-07; §5.4.

**O que fazer:**
1. Incluir `destinos: List[DestinoRoteamento]` em `DecisaoRoteamento`, com
   `destino_principal = destinos[0]`.
2. Substituir `alerta_simulado: bool` pelo objeto `Notificacao` que já existe no schema
   (`{canal, mensagem}`), porque a RF-07 pede **evento de alerta registrado**, não um booleano.

**Critério de aceite:**
- [ ] Caso urgência + ambiguidade devolve `["FILA_URGENCIA_MEDICA", "FILA_REVISAO_HUMANA"]`
- [ ] `destino_principal` é sempre `destinos[0]`
- [ ] Urgência gera `notificacao` preenchida; os demais casos, `notificacao = null`

---

## 4 — `status` como enum de 6 valores + bloco `erro`

**Labels:** `contrato`

`ResultadoTriagemClinica.status` é `str` livre com default `"processado"`.

**Referências:** EF v1.0 §5.3 (seis status), §12 (erros), RF-01 (fluxo assíncrono).

**O que fazer:** criar o enum `StatusTriagem` com `RECEBIDO, PROCESSANDO, PROCESSADO, EM_REVISAO,
ERRO_PROCESSAMENTO, ERRO_PERSISTENCIA` e o bloco opcional `erro: {codigo, mensagem}` para as duas
situações de erro.

**Critério de aceite:**
- [ ] `status` valida contra os 6 valores
- [ ] `ERRO_PROCESSAMENTO` e `ERRO_PERSISTENCIA` exigem o bloco `erro` e não aceitam
      `classificacao`/`dados_extraidos`
- [ ] Os códigos seguem a tabela do §12 (`PDF_PROTEGIDO`, `PDF_CORROMPIDO`, …)

---

## 5 — Expor o bloco `qualidade` na resposta

**Labels:** `contrato`, `auditoria`

O `QualidadeWorkflow` já calcula tudo (scores, campos ausentes, incertos, limiar), mas nada
disso chega à resposta da API. Sem isso não é possível auditar a decisão nem provar o limiar.

**Referências:** RF-17, RF-18 (`score_combinado = min(classificação, extração)`), RN-05
(justificativa estruturada), RF-30.

**O que fazer:** incluir `qualidade` em `ResultadoTriagemClinica`, com
`score_extracao`, `score_combinado`, `limiar_aplicado`, `campos_ausentes`, `campos_incertos`
e `conflitos` (com `gravidade`).

**Critério de aceite:**
- [ ] `score_combinado == min(score_classificacao, score_extracao)` em todos os casos
- [ ] `campos_ausentes` lista os campos obrigatórios que faltaram (RF-21)
- [ ] Conflitos chegam com `tipo`, `campos`, `gravidade` e `descricao`

---

## 6 — Alto risco sem texto de urgência vai para a fila urgente (RN-03)

**Labels:** `regra-de-negócio`, `prioridade-alta`

Hoje a urgência só é detectada por `urgencia == "SIM"` ou prioridade `URGENTE`. A RN-03 exige
que **achado crítico ou prescrição de alto risco** encaminhe para a fila urgente e gere alerta
**mesmo sem texto de urgência**.

**Referências:** RN-03; EF v1.0 §8.2; decisão A2 (dicionário clínico mínimo).

**O que fazer:** criar o sinal `alto_risco` (booleano) alimentado pelo dicionário clínico —
no nosso catálogo o caso equivalente é `Conflito_AltoRisco` (varfarina 10 mg sem texto de
urgência, que espera `FILA_URGENCIA_MEDICA` e `PROCESSADO`). O dicionário de medicamentos de
alto risco depende do time clínico (A2/A9).

**Critério de aceite:**
- [ ] Receita de medicamento de alto risco sem texto de urgência → `FILA_URGENCIA_MEDICA`
- [ ] Gera notificação de alerta
- [ ] Se houver ambiguidade junto, os dois destinos, nesta ordem:
      `["FILA_URGENCIA_MEDICA", "FILA_REVISAO_HUMANA"]`
- [ ] Teste parametrizado cobrindo ALTA/MEDIA/BAIXA continua verde

---

## 7 — Caminhos do bucket por estado (inclui `processados/urgentes/`)

**Labels:** `oci`, `armazenamento`

O README lista `/recebidos`, `/processados` e `/auditoria_humana`. Falta o subcaminho de
urgentes, e falta a regra que amarra o caminho à decisão.

**Referências:** RF-29 (segregar por estado), RF-30 (informar bucket + caminho + status, sem URL
pública), §6 passo 7 (documento roteado a revisão vai para o estado/caminho de auditoria), §13.

**O que fazer:** derivar `armazenamento_oci.caminho_objeto` da decisão:

| Decisão | Caminho |
| --- | --- |
| entrada recebida | `recebidos/…` |
| rotina processada | `processados/…` |
| urgência | `processados/urgentes/…` |
| revisão humana | `auditoria_humana/…` |

**Critério de aceite:**
- [ ] Cada decisão produz o prefixo correspondente
- [ ] `status_backup` reflete o resultado real da gravação (`sucesso` / `falha`)
- [ ] Nenhuma URL pública ou credencial na resposta

---

## 8 — Formato de `medicamentos`, `exames` e posição de `urgencia`

**Labels:** `contrato`

**Referências:** EF v1.0 §9.2, RF-08, decisão A5.

**O que fazer:**
- `medicamentos`: lista de objetos `{nome, dosagem?, frequencia?}` em vez de `List[str]`
- `exame_realizado: str` → `exames: List[str]`
- `urgencia` passa a viver dentro de `dados_extraidos`, com os valores
  `SIM | NAO | INDETERMINADO` (é o que a decisão A5 consome)

**Critério de aceite:**
- [ ] Prescrição sem dose é representada com `dosagem: null` (não inferida)
- [ ] `urgencia` serializa os três valores do enum

---

## 9 — Limites de entrada na ingestão (decisão A6)

**Labels:** `ingestão`

`src/ingestion/` está vazio. Os limites foram fixados em 21/10/2026 e nenhum teste os cobre.

**Referências:** RF-03 (validar entrada), decisão A6, EF v1.0 §10.1 (códigos de erro).

**O que fazer:** validar antes de qualquer inferência, rejeitando com o código correto:

| Situação | Código |
| --- | --- |
| Arquivo > 10 MB ou documento com mais de 20 páginas | `413 ARQUIVO_MAIOR_QUE_LIMITE` |
| Extensão fora de PDF/JPG/PNG/WEBP/TXT | `415 FORMATO_NAO_SUPORTADO` |
| Extensão e MIME divergentes | `415 MIME_INVALIDO` |
| Arquivo vazio ou envelope sem campos | `422 CAMPOS_INVALIDOS` |
| JSON com sintaxe inválida | `400 REQUISICAO_INVALIDA` |

O limite é **inclusivo**: 10 MB e 20 páginas passam; 10,5 MB e 21 páginas não.

**Critério de aceite:**
- [ ] Rejeição acontece antes de chamar o modelo
- [ ] Mensagem de erro sem stack trace e sem segredo
- [ ] Timeout de 60 s e 2 retentativas com backoff no provedor

---

## 10 — README: remover a meta de "5 segundos"

**Labels:** `documentação`

O README promete reduzir a triagem "de 15 minutos para menos de 5 segundos". As metas
numéricas ficaram **fora do MVP**: o critério de aceite são os casos aprovados, com latência
medida por etapa e sem meta.

**Referências:** decisão A7 de 21/10/2026, EF v1.0 §14.

**Critério de aceite:**
- [ ] README sem promessa de tempo
- [ ] Se quiser manter o número, rotular explicitamente como aspiração, não como critério

---

## Observação final para a equipe

O grafo de decisão está alinhado com as decisões A1, A3, A4, A5 e R1 — inclusive no ponto em
que a especificação original divergia do brief (urgência isolada **não** gera revisão). Nenhuma
issue acima pede para reescrever regra de negócio. São ajustes de contrato e duas regras que
faltavam (RN-03 e caminhos do bucket).
