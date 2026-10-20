# Revisão do modelo de contrato v2.0 contra os 67 fixtures

**Projeto:** hackatoon_oracle / MediFlow — Hackathon ONE G10
**Data:** 20/10/2026
**Objeto:** `app/models.py` v2.0 (Pydantic) proposto pela equipe — `TriagemMediFlow`
**Base de comparação:** os 67 `expected.json` de [`tests/fixtures/`](../../tests/fixtures/) (59 funcionais + 8 negativos técnicos)
**Veredito:** a estrutura geral está certa, mas **o modelo não fecha o contrato** — 18 dos 67 casos não são representáveis e, dos 49 restantes, 12 não chegam ao resultado esperado quando o validador decide sozinho.

---

## 1. Resposta curta

| Pergunta | Resposta |
| --- | --- |
| A estrutura (classificação → dados → qualidade → decisão → armazenamento) está de acordo? | **Sim.** É a mesma ordem que os fixtures esperam e cobre o payload final. |
| Os valores dos enums estão de acordo? | **Não.** Todos os enums usam texto livre/acentuado em vez dos tokens do domínio, e faltam `OUTRO`, `NAO_IDENTIFICADO`, `NAO_IDENTIFICADA`. |
| As regras de decisão estão de acordo? | **Em parte.** Limiar 0,85 e notificação por urgência batem; urgência sem EM_REVISAO, conflito e campo incerto não disparam revisão. |
| O modelo representa os 67 casos? | **Não. 49 de 67.** Ficam de fora os 8 tipos `OUTRO`/`NAO_IDENTIFICADO`, os 2 PDFs com erro de leitura e os 8 negativos de requisição. |
| O que fazer? | Patch de 10 itens (§7). A versão corrigida (v3) reproduz **57/57 decisões + 10/10 erros** — rode `tests/contrato/comparar_v3.py`. |

Números medidos, não estimados:

```text
v2.0 · fixtures representáveis ........ 49/67
v2.0 · "echo"   (preserva o esperado) .. 43/49
v2.0 · "derive" (chega sozinho) ........ 37/49
v3   · decisões ........................ 57/57
v3   · negativos ....................... 10/10
```

---

## 2. Como a comparação foi feita

Dois testes novos, ambos executáveis, sem depender do pipeline:

| Script | O que mede |
| --- | --- |
| [`tests/contrato/comparar_com_fixtures.py`](../../tests/contrato/comparar_com_fixtures.py) | Converte cada `expected.json` em payload da v2.0 e compara a saída em dois modos: **echo** (o pipeline já entrega o resultado esperado — o modelo preserva?) e **derive** (o modelo recebe só os fatos e decide). |
| [`tests/contrato/verificar_regras_do_contrato.py`](../../tests/contrato/verificar_regras_do_contrato.py) | Aplica *apenas* as regras documentadas (sem modelo nenhum) e confere se reproduzem a decisão dos 59 funcionais. É a especificação executável: **57/57**. |
| [`tests/contrato/comparar_v3.py`](../../tests/contrato/comparar_v3.py) | Mesma prova para o contrato corrigido sugerido em [`modelo_v3_sugerido.py`](../../tests/contrato/modelo_v3_sugerido.py): **57/57 + 10/10**. |

Os dois últimos são o argumento mais forte desta revisão: **as regras dos fixtures são fechadas** — com os campos certos, nenhuma decisão fica ambígua. O problema não é o catálogo, é o schema.

```bash
python3 tests/contrato/comparar_com_fixtures.py     # v2.0
python3 tests/contrato/comparar_v3.py               # contrato corrigido
python3 tests/contrato/verificar_regras_do_contrato.py
```

---

## 3. O que está aderente (não mexer)

| Item | Evidência nos fixtures |
| --- | --- |
| `score_combinado = min(score_classificacao, score_extracao)` | `Simultaneo_Urgencia_Score` força 0,88 × 0,70 e espera 0,70. |
| Limiar **0,85 estrito**: 0,85 passa, 0,84 para revisão | `Borda_Score_085` (PROCESSADO) × `Borda_Score_084` (EM_REVISAO). |
| Cinco campos obrigatórios de RF-21 | As 7 pastas `Ausencia_*` provam campo a campo. |
| Ausência de CID, medicamentos ou exames **não** bloqueia | `Ausencia_SomenteCid`, `Ausencia_SomenteMedicamentos`, `Ausencia_SomenteExames` → `PROCESSADO`. |
| Notificação disparada só por `URGENTE` | 8/8 urgentes com `notificacao: true`; 51/51 demais com `false`. |
| Caso misto com dois destinos | `Simultaneo_*` → `FILA_URGENCIA_MEDICA` + `FILA_REVISAO_HUMANA`; score baixo não rebaixa a urgência. |
| Estrutura em camadas (classificação, dados, qualidade, decisão, storage) | Compatível com os 59 `expected.json` funcionais. |

---

## 4. Divergências bloqueantes

### D1. Enums com texto livre em vez de tokens do domínio

A v2.0 usa rótulos legíveis como valor de enum. O contrato usa identificadores estáveis — e é isso que o front, o banco e o `manifest.csv` consomem.

| Enum v2.0 | Valor na v2.0 | Valor no contrato | Observação |
| --- | --- | --- | --- |
| `TipoDocumentoEnum` | `"Laudo de Exame de Imagem"` | `LAUDO_EXAME_IMAGEM` | 8 valores no contrato × 6 no modelo |
| | `"Laudo Laboratorial"` | `LAUDO_EXAME_LABORATORIAL` | |
| | `"Guia de Solicitação de Procedimento"` | `GUIA_PROCEDIMENTO` | |
| | `"Relatorio de Alta/Internação"` | `RELATORIO_ALTA_INTERNACAO` | |
| | — | `OUTRO` | **faltando** |
| | — | `NAO_IDENTIFICADO` | **faltando** |
| `NivelPrioridadeEnum` | `"Urgente"`, `"Pouco_Urgente"`, `"Rotina"` | `URGENTE`, `ROTINA`, `NAO_IDENTIFICADA` | `POUCO_URGENTE` não existe no contrato; `NAO_IDENTIFICADA` (10 casos) não existe no modelo |
| `DestinoRoteamentoEnum` | `"Fila_Emergencia_Medica"` | `FILA_URGENCIA_MEDICA` | **nenhum dos 5 valores coincide** |
| | `"Prontuario_Eletronico_Paciente"` | `PRONTUARIO_ELETRONICO` | |
| | `"Auditoria_Autorizacoes"` | `AUDITORIA_AUTORIZACOES` | |
| | `"Farmacia_Hospitalar"` | `FARMACIA_HOSPITALAR` | |
| | `"Fila_Revisao_Humana"` | `FILA_REVISAO_HUMANA` | |

Impacto: 8 fixtures (`Matriz_Outro_*`, `Matriz_NaoIdentificado_*`, `Qualidade_Foto_Desfocada`, `Escaneado_Outro_PdfDigitalizado`) nem entram no modelo; 10 fixtures usam `NAO_IDENTIFICADA` e não têm valor correspondente.

> Acentos também atrapalham: `"Relatorio de Alta/Internação"` mistura palavra sem acento com palavra acentuada — sinal de que o valor foi escrito à mão. Token não tem esse problema.

### D2. `status` é `str` livre, com default `PROCESSADO`

O contrato tem 4 estados observados (`PROCESSADO`, `EM_REVISAO`, `ERRO_PROCESSAMENTO`, `ERRO_PERSISTENCIA`) e a especificação §5.3 define 6 (`RECEBIDO` e `PROCESSANDO` completam). Com `str`, nada impede `"em revisao"`, `"ERRO"` ou `"OK"`; e o default `PROCESSADO` faz um payload incompleto parecer sucesso.

### D3. O modelo não representa erro

- `dados_extraidos: DadosClinicosExtraidos` é **obrigatório** → um PDF protegido ou corrompido (`Qualidade_Pdf_ComSenha`, `Qualidade_Pdf_Corrompido`, ambos `ERRO_PROCESSAMENTO` sem dados) não pode ser validado.
- Não existe modelo de resposta de erro. Os 8 negativos técnicos esperam envelope `{http, codigo_funcional, mensagem}` com `FORMATO_NAO_SUPORTADO`, `CAMPOS_INVALIDOS`, `REQUISICAO_INVALIDA`, `ARQUIVO_MAIOR_QUE_LIMITE`, `MIME_INVALIDO` — nada disso cabe em `TriagemMediFlow`.

### D4. `destino_principal` obrigatório e fora do conjunto

Além do valor divergente (`EMERGENCIA_MEDICA` × `FILA_URGENCIA_MEDICA`), o campo é **estado duplicado** de `destinos`: o validador sincroniza um com o outro em duas direções, e não há fixture que use `destino_principal`. Sugestão: derivar (`destinos[0]`) ou manter opcional, só para leitura.

### D5. O validador **apaga** a evidência que recebe

`self.qualidade = QualidadeExtracao(..., campos_incerto=[], conflitos=[])` sobrescreve o objeto inteiro. Toda vez que o pipeline detecta algo, o modelo joga fora:

- 4 fixtures de conflito (`Conflito_Cid_Diagnostico`, `Conflito_Dados`, `Conflito_Dose`, `Conflito_Prioridade`);
- 2 de campo incerto (`Qualidade_Foto_BaixoContraste`, `Simultaneo_Urgencia_Ilegivel`).

É a causa das 6 falhas do modo echo. O validador deve **acrescentar** o que calcula e preservar o que recebeu.

### D6. As regras de decisão divergem em 4 pontos

Modo *derive*, 12 casos fora. Agrupando:

| Regra do contrato | O que a v2.0 faz | Casos afetados |
| --- | --- | --- |
| Urgência ⇒ `EM_REVISAO` + notificação | mantém `PROCESSADO` quando não há campo ausente | `Matriz_Guia_Imagem`, `Matriz_LaudoDeImagem_Imagem`, `Matriz_LaudoDeImagem_Pdf`, `Matriz_Receituario_Imagem`, `Conflito_AltoRisco` |
| Conflito ⇒ revisão | não há entrada de conflito; nunca dispara | `Conflito_Cid_Diagnostico`, `Conflito_Dados`, `Conflito_Dose`, `Conflito_Prioridade` |
| Campo incerto ⇒ revisão | não há entrada de incerto; nunca dispara | `Simultaneo_Urgencia_Ilegivel` |
| Diagnóstico ausente ⇒ revisão (exame não substitui) | usa `diagnóstico **ou** exame`, então passa batido | `Ausencia_Diagnostico` |
| Revisão **substitui** o destino primário (sem urgência) | acumula: mantém a fila do tipo e acrescenta revisão | os 12 casos de revisão não urgente representáveis |
| Revisão **acrescenta** ao destino urgente (com urgência) | correto no caso misto | ✔ |

Duas observações importantes:

1. **"Diagnóstico ou exame" é uma regra que os fixtures rejeitam.** `Ausencia_Diagnostico` tem `exames: ["Exérese de lesão cutânea"]` e ainda assim espera revisão. O exame é o procedimento solicitado, não o diagnóstico.
2. **Não dá para inferir "ausente" de `null`.** `Matriz_LaudoLaboratorial_Texto` tem `diagnostico: null` e espera `PROCESSADO` (laudo laboratorial legitimamente não tem diagnóstico); `Ausencia_Diagnostico` também tem `diagnostico: null` e espera `EM_REVISAO`. A diferença não está no dado, está na **lista `campos_ausentes`** — que é saída do extrator. Ou seja: `campos_ausentes` precisa ser campo de entrada do modelo, não algo que o validador recalcula. A v2.0 recalcula, e por isso erra os dois lados.

### D7. Modelagem de dados perde informação

| Campo do contrato | v2.0 | Problema |
| --- | --- | --- |
| `especialidade: ["Radiologia", "Pneumologia"]` | `Optional[str]` | 18 fixtures têm 2 especialidades — a segunda some |
| `exames: [...]` (até 6 itens) | `exame_ou_procedimento: Optional[str]` | 7 fixtures têm 2+ exames; `Diferencial_HemogramaCompleto` tem 6 |
| `medicamentos: ["Losartana 500 mg"]` | `{nome, dosagem, frequencia}`, `dosagem` obrigatória | 16 fixtures trazem nome + dose numa string única, sem separação; em `Simultaneo_Urgencia_Ilegivel` o medicamento chega sem dose nenhuma |
| `medico.crm: {numero, uf}` | `crm: str` **e** `crm_detalhado: {numero, uf}` | dois campos para o mesmo dado, sem regra de precedência |
| `urgencia: SIM / NAO / INDETERMINADO` | não existe | 10 casos `INDETERMINADO`; hoje a informação só vive no texto |
| `campos_incertos` | `campos_incerto` (typo), sempre `[]` | nome errado e conteúdo descartado |
| `conflitos_esperados: [{tipo, campos, gravidade, descricao}]` | `List[str]` | perde tipo, gravidade e campos — o front não consegue explicar a revisão |

### D8. Nomes de campo: escolher um lado e documentar o "de/para"

O contrato observa o documento com nomes diferentes dos do modelo:

| Contrato (`expected.json`) | v2.0 |
| --- | --- |
| `medico` | `medico_solicitante` |
| `diagnostico` | `diagnostico_principal` |
| `cid` | `cid_extraido` |
| `exames` | `exame_ou_procedimento` |
| `score_classificacao` | `score_confianca_classificacao` |
| `notificacao` (bool) | `notificacao_gerada` (objeto) |
| `limiar` | `limiar_aplicado` |
| `dose` | `dosagem` |

Não é erro por si — mas note que **as listas `campos_ausentes`/`campos_incertos` dos fixtures já usam os caminhos do modelo** (`paciente.nome`, `medico.crm`, `diagnostico_principal`, `cid_extraido`, `medicamentos[0].dose`). Ou seja: o contrato já pende para os nomes da v2.0. Recomendação: adotar os nomes do modelo no `app/models.py` e publicar a tabela de/para no README da API, em vez de manter dois vocabulários sem tradução.

### D9. Limiar e scores fixos no código

`limiar = 0.85` está escrito dentro do validador (e repetido no `Field(default=0.85)` e na docstring). Os fixtures têm `score_forcado.limiar` justamente para provar que o limiar é **configurável**. Além disso, `score_confianca_extracao` tem default `0.90`: se o pipeline esquecer de informar, o score combinado vira 0,90 em silêncio — mascarando extração de baixa qualidade.

### D10. Defaults que escondem ausência de dado

`requer_auditoria_humana` é obrigatório (bom), mas `justificativa_roteamento` é `str` obrigatório sem default, `armazenamento_oci` é obrigatório e os fixtures não têm nenhum dos dois. Ou o pipeline preenche sempre, ou o modelo rejeita payload legítimo. Sugestão: `justificativa_roteamento: str = ""` e `armazenamento_oci: Optional[...] = None` (a persistência pode falhar depois da triagem — `ERRO_PERSISTENCIA`).

---

## 5. Achados do lado do contrato (não do modelo)

Três coisas que a revisão revelou nos nossos próprios fixtures:

| # | Achado | Situação |
| --- | --- | --- |
| 1 | `Validacao_MimeInvalido` tinha `codigo_funcional: "MIME_INVALIDO (ou 422)"` — um parêntese dentro de um código de máquina, e o HTTP já era 415 | **corrigido** nesta revisão: `MIME_INVALIDO`, HTTP 415, no `expected.json`, `manifest.csv` e catálogo |
| 2 | Os 2 PDFs com erro usam o schema de triagem com `"N/A"`, enquanto os 8 negativos técnicos usam envelope `erro_esperado`. São **duas formas de representar erro** | decisão pendente: unificar (ver §8) |
| 3 | 4 casos urgentes (`Matriz_Guia_Imagem`, `Matriz_LaudoDeImagem_{Pdf,Imagem}`, `Matriz_Receituario_Imagem`) e `Conflito_AltoRisco` têm `requer_auditoria_humana: true` mas **nenhuma** `FILA_REVISAO_HUMANA` nos destinos | decisão pendente: ou a urgência é auditada na própria fila urgente (documentar), ou esses 5 recebem a fila de revisão |

O item 3 não bloqueia o modelo (as regras fecham 57/57 com a leitura "urgência = revisão na fila urgente"), mas precisa estar escrito — é a pergunta que a banca vai fazer.

---

## 6. Cobertura caso a caso

**Fora do modelo (18):**

| Grupo | Casos | Por quê |
| --- | ---: | --- |
| Tipos `OUTRO` / `NAO_IDENTIFICADO` | 8 | enum não tem os valores |
| PDFs com erro de leitura (`N/A`) | 2 | `dados_extraidos` obrigatório e `status` livre |
| Negativos técnicos | 8 | não há envelope de erro |

**Dentro do modelo, mas com decisão errada (12/49):** 5 por urgência sem revisão, 4 por conflito ignorado, 1 por campo incerto, 1 por "diagnóstico ou exame", 1 só por perda de evidência (`Qualidade_Foto_BaixoContraste` — acerta a decisão por outro motivo, mas apaga `campos_incertos`).

---

## 7. Patch mínimo

| # | Onde | Mudança | Resolve |
| ---: | --- | --- | --- |
| 1 | enums | tokens do domínio (`LAUDO_EXAME_IMAGEM`, `URGENTE`, …) + `OUTRO`, `NAO_IDENTIFICADO`, `NAO_IDENTIFICADA`; remover `POUCO_URGENTE` | D1 |
| 2 | `status` | `class StatusTriagem(str, Enum)` com os 6 estados; sem default | D2 |
| 3 | topo | `dados_extraidos`, `decisao_roteamento`, `armazenamento_oci` opcionais; `class ErroResposta` (`http`, `codigo_funcional`, `mensagem`) | D3, D10 |
| 4 | `Decisao` | `destino_principal` opcional, derivado de `destinos[0]`; `justificativa_roteamento: str = ""` | D4, D10 |
| 5 | validador | preservar `campos_incertos`/`conflitos` recebidos e **acrescentar** o calculado | D5 |
| 6 | regras | urgência ⇒ `EM_REVISAO`; conflito/incerto ⇒ revisão; revisão sem urgência substitui o destino; urgência com ambiguidade acrescenta | D6 |
| 7 | `DadosClinicos` | `especialidade: List[str]`, `exames: List[str]`, `medicamentos[].dosagem` opcional, `medico.crm` objeto único, `urgencia` enum | D7 |
| 8 | extrator | `campos_ausentes` e `campos_incertos` como **campos de entrada** (não recalcular) | D6 (parte 2) |
| 9 | config | limiar em `Settings` (default 0.85) e `score_extracao` sem default otimista | D9 |
| 10 | nomes | adotar nomes do modelo + tabela de/para documentada; corrigir `campos_incerto` → `campos_incertos` | D8 |

O patch completo, já rodando, está em [`tests/contrato/modelo_v3_sugerido.py`](../../tests/contrato/modelo_v3_sugerido.py) (~230 linhas, Pydantic 2). Ele é a referência para o `app/models.py` definitivo — **não** é o arquivo oficial ainda.

Prova:

```text
$ python3 tests/contrato/comparar_com_fixtures.py
Fixtures: 67 · Representáveis no modelo: 49 · Fora do modelo: 18
(a) ECHO  43/49 ok · 6 divergências
(b) DERIVE 37/49 ok · 12 divergências

$ python3 tests/contrato/comparar_v3.py
Funcionais: 57/57 decisões reproduzidas pelo validador v3
Negativos:  10/10 aceitos pelo contrato de erro
Contrato v3 fecha os 67 fixtures.
```

---

## 8. Decisões pendentes (precisam de dono)

1. **Erro tem um ou dois contratos?** Recomendação: dois, e ambos explícitos —
   `ErroResposta` (400/413/415/422, antes de qualquer inferência) e `TriagemMediFlow` com `status=ERRO_PROCESSAMENTO` e `dados_extraidos=null` (falha ao ler o documento). Se for essa a escolha, os 2 `expected.json` de PDF com erro devem ganhar `erro_esperado` próprio (`PDF_PROTEGIDO`, `PDF_CORROMPIDO`) ou um campo `status_esperado` explícito.
2. **Revisão humana na urgência:** documentar a exceção (§5, item 3) ou acrescentar `FILA_REVISAO_HUMANA` aos 5 casos. A primeira opção não mexe em nenhum fixture.
3. **`POUCO_URGENTE`:** remover do enum (não existe no contrato) ou criar os fixtures que o exercitam. Hoje é valor morto.

---

## 9. Como reexecutar tudo

```bash
python3 tools/verificar_consistencia.py            # catálogo: 67 pastas, 0 erros
python3 tests/contrato/comparar_com_fixtures.py    # v2.0 × fixtures
python3 tests/contrato/comparar_v3.py              # v3 × fixtures
python3 tests/contrato/verificar_regras_do_contrato.py
```
