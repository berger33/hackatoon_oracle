# Contrato de dados da triagem — MediFlow v1.0

**Projeto:** hackatoon_oracle / MediFlow — Hackathon ONE G10
**Código:** [`app/models.py`](../../app/models.py) (Pydantic 2)
**Data:** 20/10/2026
**Escopo:** o contrato que os 67 `expected.json` documentam e validam.

---

## 1. O que é este documento

O contrato responde a três perguntas, e só a estas:

1. **Qual é o formato da resposta** que o agente devolve para um documento aceito (`TriagemMediFlow`) e para uma requisição recusada (`ErroResposta`).
2. **Quais valores são válidos** em cada campo controlado — sem texto livre, sem acento, sem espaço.
3. **Como a decisão é tomada** a partir dos fatos extraídos (score, campos ausentes, incertos, conflitos, prioridade).

Ele é executável: `app/models.py` roda as regras e recusa payload incoerente. Os 67 fixtures são instâncias válidas desse modelo, e o teste `tests/testar_contrato.py` prova isso a cada execução.

```bash
python3 tests/testar_contrato.py        # 67/67 no contrato
python3 tools/verificar_consistencia.py # estrutura, manifesto, duplicidade
```

---

## 2. Enums (fonte única)

| Enum | Valores | Onde aparece |
| --- | --- | --- |
| `TipoDocumento` | `RECEITUARIO_MEDICO`, `LAUDO_EXAME_LABORATORIAL`, `LAUDO_EXAME_IMAGEM`, `GUIA_PROCEDIMENTO`, `RELATORIO_ALTA_INTERNACAO`, `ATESTADO_MEDICO`, `OUTRO`, `NAO_IDENTIFICADO` | `classificacao.tipo_documento` |
| `NivelPrioridade` | `URGENTE`, `ROTINA`, `NAO_IDENTIFICADA` | `classificacao.nivel_prioridade` |
| `StatusTriagem` | `RECEBIDO`, `PROCESSANDO`, `PROCESSADO`, `EM_REVISAO`, `ERRO_PROCESSAMENTO`, `ERRO_PERSISTENCIA` | `status` |
| `Destino` | `FILA_URGENCIA_MEDICA`, `FARMACIA_HOSPITALAR`, `AUDITORIA_AUTORIZACOES`, `PRONTUARIO_ELETRONICO`, `FILA_REVISAO_HUMANA` | `decisao_roteamento.destinos` |
| `Urgencia` | `SIM`, `NAO`, `INDETERMINADO` | `dados_extraidos.urgencia` |
| `Gravidade` | `ALTA`, `MEDIA`, `BAIXA` | `qualidade.conflitos[].gravidade` |
| `CodigoErro` | `FORMATO_NAO_SUPORTADO`, `CAMPOS_INVALIDOS`, `REQUISICAO_INVALIDA`, `ARQUIVO_MAIOR_QUE_LIMITE`, `MIME_INVALIDO`, `PDF_PROTEGIDO`, `PDF_CORROMPIDO` | erros |

Decisões que fecham divergências antigas:

- **Tokens, não rótulos.** `LAUDO_EXAME_IMAGEM` (não `"Laudo de Exame de Imagem"`), `FILA_URGENCIA_MEDICA` (não `"Fila_Emergencia_Medica"`). Nada de acento, espaço ou barra em valor de enum.
- **`POUCO_URGENTE` não existe.** A especificação define três níveis; o valor foi removido em vez de ficar sem fixture.
- **`OUTRO` e `NAO_IDENTIFICADO` são resultados**, não erros: continuam sendo `TipoDocumento`, com revisão obrigatória.
- **`NAO_IDENTIFICADA` é prioridade**; `N/A` deixou de existir em qualquer campo.

---

## 3. Payload de triagem

```jsonc
{
  "status": "EM_REVISAO",
  "documento_id": "DOC-A757DAD2",
  "classificacao": {
    "tipo_documento": "RECEITUARIO_MEDICO",
    "especialidade": ["Cardiologia"],
    "nivel_prioridade": "ROTINA",
    "score_classificacao": 0.93
  },
  "dados_extraidos": {
    "paciente": {"nome": "Neusa Ferreira Lima", "idade": 73},
    "medico": {"nome": "Dr. Paulo Mendes Rocha", "crm": {"numero": "203114", "uf": "RJ"}},
    "diagnostico": "Hipertensão arterial sistêmica",
    "cid": "I10",
    "exames": [],
    "medicamentos": [{"nome": "Losartana potássica", "dosagem": "500 mg", "frequencia": null}],
    "urgencia": "NAO"
  },
  "qualidade": {
    "score_extracao": 0.91,
    "score_combinado": 0.91,
    "limiar_aplicado": 0.85,
    "campos_ausentes": [],
    "campos_incertos": [],
    "conflitos": [{"tipo": "DOSE_SUSPEITA", "campos": ["medicamentos[0].dosagem"],
                   "gravidade": "ALTA", "descricao": "Losartana 500 mg excede a dose usual"}]
  },
  "decisao_roteamento": {
    "destino_principal": "FILA_REVISAO_HUMANA",
    "destinos": ["FILA_REVISAO_HUMANA"],
    "requer_auditoria_humana": true,
    "justificativa_roteamento": "Revisão humana obrigatória: conflitos: DOSE_SUSPEITA.",
    "notificacao": null
  },
  "armazenamento_oci": null,
  "erro": null
}
```

Notas de modelagem:

| Campo | Regra |
| --- | --- |
| `especialidade`, `exames` | listas — um documento pode ter mais de uma especialidade e vários exames |
| `medicamentos` | objeto `{nome, dosagem?, frequencia?}`; `dosagem` é opcional porque há prescrição sem dose |
| `medico.crm` | **um** objeto `{numero, uf}`; não existe mais `crm` texto + `crm_detalhado` duplicado |
| `dados_extraidos.urgencia` | declara o que o documento diz (`SIM`/`NAO`/`INDETERMINADO`), em vez de inferir do texto |
| `qualidade.campos_ausentes` / `campos_incertos` | vêm do extrator; o validador **não recalcula** (ver §5) |
| `qualidade.score_combinado` | sempre `min(score_classificacao, score_extracao)` — recalculado pelo validador |
| `decisao_roteamento.destino_principal` | derivado: é sempre `destinos[0]` |
| `armazenamento_oci` | opcional: persistência é etapa posterior e pode falhar (`ERRO_PERSISTENCIA`) |

---

## 4. Erro: dois formatos, cada um no seu nível

| Situação | Formato | Exemplo nos fixtures |
| --- | --- | --- |
| Requisição inválida (formato, tamanho, MIME, envelope, sintaxe) — **não chega a virar triagem** | `ErroResposta {http, codigo_funcional, mensagem}` | os 8 `Validacao_*` |
| Documento aceito, mas ilegível na leitura (PDF protegido/corrompido) | `TriagemMediFlow` com `status=ERRO_PROCESSAMENTO`, `erro={codigo, mensagem}` e sem classificação/dados | `Qualidade_Pdf_ComSenha` (`PDF_PROTEGIDO`), `Qualidade_Pdf_Corrompido` (`PDF_CORROMPIDO`) |

Os dois casos de leitura antes usavam o schema de triagem preenchido com `"N/A"` — um valor que não é enum nenhum. Agora são payloads válidos, com erro tipado.

---

## 5. Regras de decisão

| # | Regra | Efeito |
| --- | --- | --- |
| R1 | `nivel_prioridade == URGENTE` | `FILA_URGENCIA_MEDICA` + `notificacao` + `requer_auditoria_humana=True` + `EM_REVISAO` |
| R2 | Ambiguidade: campo obrigatório ausente **ou** campo incerto **ou** conflito **ou** `score_combinado < limiar` **ou** `OUTRO`/`NAO_IDENTIFICADO` | revisão humana |
| R3 | Ambiguidade **sem** urgência | destino **substituído** por `FILA_REVISAO_HUMANA` |
| R4 | Ambiguidade **com** urgência | `FILA_URGENCIA_MEDICA` **+** `FILA_REVISAO_HUMANA` |
| R5 | `score_combinado = min(...)`, limiar **estrito** | 0,85 passa; 0,84 revisa |
| R6 | `campos_ausentes` é do extrator | só os 5 obrigatórios disparam revisão; CID/medicamentos/exames ausentes são registrados e não bloqueiam |
| R7 | Erro de leitura | `ERRO_PROCESSAMENTO` + `erro.codigo`, sem dados |

**Campos obrigatórios (RF-21):** `paciente.nome`, `paciente.idade`, `medico.nome`, `medico.crm`, `diagnostico`.

### A exceção da urgência, explicada

Um documento urgente sem nenhuma ambiguidade termina com `requer_auditoria_humana = true` e **sem** `FILA_REVISAO_HUMANA`. Não é contradição: a auditoria da urgência acontece **na própria fila de urgência** (alerta no plantão + conferência humana). A `FILA_REVISAO_HUMANA` só é acrescentada quando existe ambiguidade adicional (R4).

É o que acontece em `Matriz_Guia_Imagem`, `Matriz_LaudoDeImagem_Pdf`, `Matriz_LaudoDeImagem_Imagem`, `Matriz_Receituario_Imagem` e `Conflito_AltoRisco` — cinco casos, um destino.

### Por que o validador não deduz "campo ausente"

`Matriz_LaudoLaboratorial_Texto` tem `diagnostico: null` e termina em `PROCESSADO` — um laudo laboratorial legitimamente não tem diagnóstico. `Ausencia_Diagnostico` também tem `diagnostico: null` e termina em `EM_REVISAO`. O dado é o mesmo; a diferença está na intenção registrada em `qualidade.campos_ausentes`, que é saída do extrator. Recalcular essa lista olhando para `null` erraria um dos dois lados.

---

## 6. Formato de um `expected.json`

```jsonc
{
  "schema": "mediflow.fixture/2",
  "fixture_id": "Conflito_Dose",
  "documento_ficticio": true,
  "tipo_de_teste": "funcional",              // funcional | erro_processamento | negativo_tecnico
  "entrada": {
    "formatos_disponiveis": ["TXT", "PDF", "JPG"],
    "renditions": {"txt": "...", "pdf": "...", "jpg": "..."}
  },
  "resposta_esperada": { /* TriagemMediFlow ou ErroResposta */ },
  "modo_fixture": {"score_forcado": {"score_classificacao": 0.92, "score_extracao": 0.84}},
  "assercoes": ["..."],
  "observacoes": ""
}
```

- `resposta_esperada` é o payload **completo**: quem consome o fixture compara o JSON da API com este bloco, sem tradução de nomes.
- `modo_fixture` só existe nos três casos que exigem score forçado (`Borda_Score_084`, `Borda_Score_085`, `Simultaneo_Urgencia_Score`).
- `tipo_de_teste` elimina a ambiguidade que existia entre "triagem normal", "triagem com erro" e "requisição recusada".

### Como os arquivos são gerados

Os geradores descrevem os **fatos clínicos** do caso; quem decide status, destinos, revisão e notificação é o contrato. Se o contrato e a intenção escrita no caso divergirem, a geração **aborta** — é assim que uma mudança de regra aparece imediatamente.

```bash
python3 tools/gerar_fixtures_demo.py                  # 12 casos (TXT+PDF+JPG+expected.json)
python3 tools/gerar_fixtures_catalogo.py              # 55 casos
python3 tools/gerar_fixtures_demo.py --somente-expected    # reescreve só os JSON
python3 tools/gerar_fixtures_catalogo.py --somente-expected
```

---

## 7. Verificação

| Comando | O que garante |
| --- | --- |
| `python3 tests/testar_contrato.py` | cada `expected.json` valida no modelo certo e é **ponto fixo**: rodar as regras de novo devolve o mesmo JSON |
| `python3 tools/verificar_consistencia.py` | estrutura (4/2 arquivos por pasta), `manifest.csv` × expected, legibilidade de PDF/JPG/TXT, duplicidade |
| `python3 tools/gerar_mapa_documentos.py` | regera o mapa em PDF a partir do manifesto |

Resultado atual:

```text
tests/testar_contrato.py        → 67 fixtures: 57 funcionais + 2 erros de leitura + 8 negativos, 0 falhas
tools/verificar_consistencia.py → 67 pastas, 0 erros, 0 avisos
```

---

## 8. O que mudou em relação ao modelo v2.0

O modelo anterior (v2.0) foi descartado. Resumo do que ele não cobria e que agora está no contrato:

| Antes (v2.0) | Agora (v1.0) |
| --- | --- |
| enums com texto livre (`"Urgente"`, `"Fila_Emergencia_Medica"`) | tokens do domínio + `OUTRO`, `NAO_IDENTIFICADO`, `NAO_IDENTIFICADA` |
| `status: str` com default `PROCESSADO` | `StatusTriagem` com os 6 estados, sem default |
| sem contrato de erro; `dados_extraidos` obrigatório | `ErroResposta` (HTTP) e `TriagemMediFlow.erro` (leitura) |
| validador apagava `campos_incertos`/`conflitos` recebidos | evidência preservada e cobrada nas regras |
| urgência não gerava `EM_REVISAO`; diagnóstico "ou exame" | R1 e R6 acima |
| `especialidade: str`, `exame_ou_procedimento: str`, `crm` duplicado | listas e objeto CRM único |
| limiar 0,85 fixo no corpo do validador | `qualidade.limiar_aplicado` (default 0,85, por payload) |

O histórico completo dessa comparação está no commit `cacdfba` (relatório removido depois de resolvido).
