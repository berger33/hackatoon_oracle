# Plano das EPTs — Especificações de Procedimento de Teste

**Projeto:** hackatoon_oracle / MediFlow — Hackathon ONE G10
**Artefato planejado:** 1 EPT por caso da Especificação Funcional v1.0
**Data do plano:** 21/10/2026
**Status do plano:** aprovado em 21/10/2026

---

## 0. Decisões aprovadas

| Decisão | Escolha |
| --- | --- |
| **Escopo** | **41 EPTs**: 7 da tabela de decisão (§8.2) + 15 critérios de aceite (§16) + 8 erros (§12) + 11 RNF (§14) |
| **Natureza** | EPT = Especificação de Procedimento de Teste: um documento por caso, com passo a passo e registro de execução |
| **Formato** | Markdown em `docs/epts/` (um `.md` por EPT) **+ PDF consolidado** gerado por script |
| **Início** | 2 EPTs-piloto (`EPT-D01` e `EPT-A08`) para validar o template antes de escrever as 39 restantes |

---

## 1. O que é uma EPT neste repositório

**EPT = Especificação de Procedimento de Teste.** Um documento por caso, com o passo a passo que um executor segue para provar — ou refutar — um comportamento descrito na especificação funcional.

Diferente do que já existe no repositório:

| Artefato | Pergunta que responde | Situação |
| --- | --- | --- |
| `CONTRATO_DE_DADOS.md` + `app/models.py` | "O que é uma resposta válida?" | ✅ pronto |
| `CATALOGO_DE_DOCUMENTOS_DE_TESTE.md` + 67 fixtures | "Que massa de dados usar?" | ✅ pronto |
| `manifest.csv` | "Qual é o resultado esperado de cada documento?" | ✅ pronto |
| **EPT (novo)** | **"Como executar, o que observar e como registrar o resultado?"** | 🆕 este plano |

A EPT **não** substitui o catálogo nem o `expected.json`: ela aponta para eles. O `expected.json` do fixture é a **resposta esperada canônica**; a EPT descreve o **procedimento** para chegar até ela e o **critério de verificação** de cada campo.

---

## 2. Fontes e precedência

1. `MediFlow_Especificacao_Funcional_v1.0.pdf` — fonte dos casos (§7 RF-01 a RF-30, §8 regras e tabela de decisão, §12 erros, §14 RNF, §16 critérios de aceite).
2. `app/models.py` + `docs/testes/CONTRATO_DE_DADOS.md` — vocabulário controlado e regras executáveis (R1 a R7).
3. `tests/fixtures/manifest.csv` + 67 `expected.json` — massa de dados e resultado esperado.
4. `Projeto_oracle.pdf` — apenas onde a especificação não conflitar com ele (a spec v1.0 é normativa; ver §10 do catálogo).

---

## 3. Inventário de casos → EPTs

Cada caso da especificação vira **uma EPT**, numerada por família. Ao todo: **41 EPTs**, em 4 famílias.

### Família D — Casos de decisão (§8.2, tabela de decisão) — 7 EPTs

| EPT | Sinal (linha da §8.2) | Destino | Revisão | Alerta | Fixtures de referência |
| --- | --- | --- | --- | --- | --- |
| `EPT-D01` | Urgência / achado crítico | `FILA_URGENCIA_MEDICA` | Sim, obrigatória | Sim, obrigatório | `Matriz_LaudoDeImagem_Pdf`, `Matriz_LaudoDeImagem_Imagem`, `Matriz_Receituario_Imagem`, `Matriz_Guia_Imagem`, `Conflito_AltoRisco` |
| `EPT-D02` | Score combinado < 0,85 | `FILA_REVISAO_HUMANA` | Sim | Não, salvo urgência | `Borda_Score_084` (contraprova: `Borda_Score_085`) |
| `EPT-D03` | Urgência + ambiguidade/ilegibilidade/conflito | `FILA_URGENCIA_MEDICA` **e** `FILA_REVISAO_HUMANA` | Sim | Sim | `Simultaneo_Urgencia_Ilegivel`, `Simultaneo_Urgencia_Score` |
| `EPT-D04` | Receita de rotina, sem impedimento | `FARMACIA_HOSPITALAR` | Não | Não | `Matriz_Receituario_Pdf`, `Matriz_Receituario_Texto` |
| `EPT-D05` | Guia de procedimento de rotina | `AUDITORIA_AUTORIZACOES` | Não | Não | `Matriz_Guia_Pdf`, `Matriz_Guia_Texto` |
| `EPT-D06` | Laudo, alta ou atestado de rotina | `PRONTUARIO_ELETRONICO` | Não | Não | `Matriz_LaudoLaboratorial_{Pdf,Imagem,Texto}`, `Matriz_RelatorioDeAlta_{Pdf,Imagem}`, `Matriz_Atestado_{Pdf,Imagem,Texto}` |
| `EPT-D07` | Tipo desconhecido / destino não mapeado | `FILA_REVISAO_HUMANA` | Sim | Só se urgente | `Matriz_NaoIdentificado_{Pdf,Texto,Imagem}`, `Matriz_Outro_{Pdf,Imagem,Texto}` |

### Família A — Critérios de aceite do MVP (§16) — 15 EPTs

| EPT | Critério §16 | Observação de escopo |
| --- | --- | --- |
| `EPT-A01` | 1. Texto + PDF + imagem aceitos | 3 formatos do mesmo conteúdo |
| `EPT-A02` | 2. Documento padrão classificado e roteado | destino de rotina correto por tipo |
| `EPT-A03` | 3. Urgente com alerta, nunca só rotina | sobrepõe `EPT-D01`; aqui o foco é "nunca rotina" |
| `EPT-A04` | 4. Ambíguo/ilegível → revisão, sem dado inventado | campos incertos preservados |
| `EPT-A05` | 5. Ausência dos 5 campos obrigatórios × CID isolado | 5 positivos + 3 contraprovas (`Ausencia_SomenteCid`, `Ausencia_SomenteExames`, `Ausencia_SomenteMedicamentos`) |
| `EPT-A06` | 6. 202 Accepted + consulta até estado terminal | assíncrono |
| `EPT-A07` | 7. Alerta simulado, sem envio externo; fila sem decisão humana | verificação de efeito colateral zero |
| `EPT-A08` | 8. 0,84 revisa; 0,85 não revisa por esse critério | duas bordas, mesmo conteúdo |
| `EPT-A09` | 9. Campos ausentes não inferidos | `null` + `campos_ausentes`, nunca palpite |
| `EPT-A10` | 10. Persistência no OCI + falha simulada ≠ sucesso | caminho lógico, sem URL/credencial |
| `EPT-A11` | 11. Histórico ordenado e JSON validado | `GET /historico` |
| `EPT-A12` | 12. Regras, versão, justificativa e destino rastreáveis | `regras_acionadas` + `versao_esquema` |
| `EPT-A13` | 13. Interface mostra estados sem expor segredos | verificação de tela |
| `EPT-A14` | 14. README + demonstração dos 3 cenários | verificação documental |
| `EPT-A15` | 15. Nenhum opcional declarado sem prova | verificação de escopo/claim |

### Família E — Erros, exceções e recuperação (§12) — 8 EPTs

| EPT | Situação (§12) | Fixtures / mecanismo |
| --- | --- | --- |
| `EPT-E01` | Formato/campos inválidos (rejeitar antes do Gemini) | `Validacao_ArquivoDocx`, `Validacao_ArquivoZip`, `Validacao_MimeInvalido`, `Validacao_JsonMalformado`, `Validacao_EnvelopeVazio`, `Validacao_SemConteudo`, `Validacao_ArquivoVazio`, `Validacao_ArquivoGrande` |
| `EPT-E02` | Documento ilegível / extração inconclusiva | `Qualidade_Foto_Desfocada`, `Qualidade_Foto_BaixoContraste`, `Qualidade_Foto_Cortada`, `Qualidade_Foto_Rotacionada`, `Qualidade_Pdf_SemTexto` |
| `EPT-E03` | Gemini indisponível / timeout | simulação por flag/stub do adaptador |
| `EPT-E04` | Resposta Gemini inválida para o esquema | simulação por stub (payload malformado) |
| `EPT-E05` | Conflito entre dados (registrar sem alterar origem) | `Conflito_Cid_Diagnostico`, `Conflito_Dose`, `Conflito_Dados`, `Conflito_Prioridade`, `Conflito_AltoRisco` |
| `EPT-E06` | Evento urgente registrado como simulado | `canal` + `status` da notificação |
| `EPT-E07` | Falha ao registrar alerta simulado | simulação; triagem não pode ser apagada |
| `EPT-E08` | Falha do OCI ao gravar original e/ou resultado | simulação; `ERRO_PERSISTENCIA` |

### Família R — Requisitos não funcionais convertidos em verificação (§14) — 11 EPTs

`EPT-R01` precisão · `EPT-R02` segurança clínica · `EPT-R03` confiabilidade (Gemini/OCI indisponíveis) · `EPT-R04` rastreabilidade · `EPT-R05` custo (Always Free) · `EPT-R06` formato (JSON válido tipado) · `EPT-R07` agilidade (latência por etapa) · `EPT-R08` privacidade (só dados fictícios) · `EPT-R09` manutenibilidade (README, diagrama, adaptador isolado) · `EPT-R10` flexibilidade (modelo substituível — teste contratual do adaptador) · `EPT-R11` usabilidade (os três fluxos).

---

## 4. Template único de EPT

Todo arquivo segue a mesma estrutura, para que a leitura seja comparável entre casos:

```text
# EPT-D01 — Urgência / achado crítico → FILA_URGENCIA_MEDICA

| Campo            | Valor                                              |
| ---------------- | -------------------------------------------------- |
| ID               | EPT-D01                                            |
| Título           | ...                                                |
| Versão           | 1.0                                                |
| Origem           | Especificação Funcional v1.0 — §8.2 linha 1        |
| Requisitos       | RF-07, RF-13, RF-20, RF-21, RF-22; RN-01, RN-03    |
| Critérios §16    | 3, 7                                               |
| Prioridade       | Obrigatório                                        |
| Status           | NÃO EXECUTADO                                      |

1. Objetivo
2. Pré-condições e ambiente      (inclui flags: FIXTURE_MODE / stub de score / simulador de falha)
3. Massa de dados                (IDs de fixture + renditions TXT/PDF/JPG + expected.json)
4. Procedimento                  (tabela: # | Ação | Entrada | Resultado esperado)
5. Critérios de verificação      (asserções numeradas, cada uma ligada a um campo do contrato)
6. Resultado esperado de referência (trecho/caminho do expected.json)
7. Pós-condições e limpeza
8. Registro de execução          (data | executor | resultado | evidência | observação)
9. Pendências que travam o teste (§15 da especificação)
```

Regras de escrita:

1. **Um caso, uma variável.** Se duas regras podem explicar a falha, o caso está errado.
2. **Nenhum número solto.** Todo valor esperado vem do `expected.json` do fixture citado ou da especificação.
3. **Nada de dado real.** Todo procedimento usa os 67 fixtures fictícios.
4. **Determinístico ou nada.** Onde o score decide (`EPT-A08`, `EPT-D02`, `EPT-D03`), a EPT declara o uso de stub de score — sem isso o teste é intermitente.
5. **Erro esperado explícito.** Nos negativos, comparar HTTP + `codigo_funcional`; nos erros de leitura, comparar `status` + `erro.codigo`.

---

## 5. Estrutura da nova pasta

```text
docs/epts/
├── PLANO_DE_EPTS.md                 # este plano
├── README.md                        # índice + matriz de rastreabilidade (EPT ↔ § ↔ RF/RN ↔ §16 ↔ fixture)
├── MODELO_DE_EPT.md                 # template em branco, copiado para criar cada EPT
├── EPT-D01_Urgencia_Fila_Urgencia.md
├── EPT-D02_Score_Abaixo_Limiar.md
├── ...                              # 41 arquivos, um por caso
├── EPTs_MediFlow.pdf                # PDF consolidado de todas as EPTs
└── epts.csv                         # (opcional) mesma matriz em formato de máquina
```

O PDF consolidado é gerado por `python3 tools/gerar_epts_pdf.py`, que lê todos os
`docs/epts/EPT-*.md` e produz `docs/epts/EPTs_MediFlow.pdf` — mesmo padrão do
`tools/gerar_mapa_documentos.py`.

Convenção de nome: `EPT-<FAMÍLIA><NN>_<Assunto>.md`, sem acento, sem abreviação — igual à convenção `Bloco_Assunto_Detalhe` dos fixtures.

---

## 6. Ondas de execução

| Onda | Conteúdo | EPTs | Por que primeiro |
| --- | --- | ---: | --- |
| **1** | Família D (7) + Família A (15) | 22 | É o que a banca lê: os três cenários obrigatórios e os 15 critérios de aceite do MVP |
| **2** | Família E (8) | 8 | Erros e recuperação — prova RNF-02/RNF-03 |
| **3** | Família R (11) | 11 | Não funcionais e simulações operacionais |

Sugestão: aprovar o template com **2 EPTs-piloto** (`EPT-D01` e `EPT-A08` — o caso mais representativo e o caso mais sensível a intermitência), validar o formato e só então gerar o restante.

---

## 7. Verificação automática (o que já existe no repo sugere)

Criar `tools/verificar_epts.py`, no mesmo estilo de `tools/verificar_consistencia.py`, checando:

1. Todo arquivo `docs/epts/EPT-*.md` tem as 9 seções do template e o cabeçalho completo.
2. IDs únicos e sequência sem buraco por família.
3. Todo ID de fixture citado existe no `manifest.csv` (evita EPT órfã).
4. Toda linha da §8.2 tem EPT; todo critério §16 tem EPT; todo RNF §14 tem EPT.
5. `Status` sempre em um dos valores controlados: `NAO_EXECUTADO`, `EM_EXECUCAO`, `PASSOU`, `FALHOU`, `BLOQUEADO`.
6. Nenhum EPT com `Status = PASSOU` sem data e executor no registro de execução.

Saída esperada no fim: `0 erros, 0 avisos`, como os demais verificadores.

---

## 8. O que o plano **não** faz

- Não cria novos fixtures. Os 67 existentes cobrem os 41 casos; se um caso ficar sem fixture, isso será registrado como pendência, não resolvido com massa nova.
- Não implementa o pipeline (FastAPI/LangGraph/Gemini). As EPTs ficam com `Status = NAO_EXECUTADO` até que ele exista; hoje o que se pode executar é a validação do `expected.json` contra o contrato (`python3 tests/testar_contrato.py`).
- Não repete o catálogo nem o contrato — apenas aponta para eles.

---

## 9. Pendências herdadas da §15 que afetam as EPTs

| Pendência | EPTs travadas | Tratamento proposto |
| --- | --- | --- |
| Limites de tamanho, MIME, timeout, retry | `EPT-E01`, `EPT-E03`, `EPT-R03` | Escrever com o valor **configurável em destaque** e campo "limite aplicado" a preencher |
| Contrato final do upload (multipart × JSON) | `EPT-E01` | Escrever as duas variantes, marcando a escolha pendente |
| Dicionário clínico (achado crítico, alto risco, conflitos) | `EPT-D01`, `EPT-E05` | Referenciar `rules/*.csv` como dado de referência; EPT fica `BLOQUEADO` até o dicionário existir |
| Urgência isolada exige revisão? | `EPT-D01` × `EPT-D03` | Seguir a spec v1.0 (`EM_REVISAO`), registrando a divergência com o exemplo do brief |
| Autenticação/autorização | `EPT-A11`, `EPT-A13` | Fora do MVP; EPT marcada como não aplicável até decisão |
| Meta de latência e precisão | `EPT-R01`, `EPT-R07` | EPT mede e registra; a meta entra quando definida |
