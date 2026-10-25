# EPTs — Especificações de Procedimento de Teste

**Projeto:** hackatoon_oracle / MediFlow — Hackathon ONE G10
**Fonte dos casos:** `MediFlow_Especificacao_Funcional_v1.0.pdf`
**Total planejado:** 41 EPTs · **Escritas:** 2 · **A escrever:** 39
**Plano:** [`PLANO_DE_EPTS.md`](PLANO_DE_EPTS.md) · **Template:** [`MODELO_DE_EPT.md`](MODELO_DE_EPT.md) · **PDF consolidado:** `EPTs_MediFlow.pdf`

---

## 1. O que é uma EPT aqui

Um documento por caso da especificação funcional, com o passo a passo que um executor segue para
provar — ou refutar — o comportamento. A EPT **não** repete o catálogo nem o contrato: ela aponta
para eles.

| Artefato | Pergunta que responde |
| --- | --- |
| [`docs/testes/CONTRATO_DE_DADOS.md`](../testes/CONTRATO_DE_DADOS.md) + `app/models.py` | O que é uma resposta válida? |
| [`docs/testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md`](../testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md) + 67 fixtures | Que massa de dados usar? |
| `tests/fixtures/manifest.csv` e cada `expected.json` | Qual é o resultado esperado? |
| **EPT** | **Como executar, o que observar e como registrar o resultado?** |

## 2. Convenções

| Item | Regra |
| --- | --- |
| **Arquivo** | `EPT-<FAMÍLIA><NN>_<Assunto>.md`, sem acento e sem abreviação — igual à convenção `Bloco_Assunto_Detalhe` dos fixtures |
| **Famílias** | `D` decisão (§8.2) · `A` aceite (§16) · `E` erros (§12) · `R` não funcionais (§14) |
| **Status** | `NAO_EXECUTADO` · `EM_EXECUCAO` · `PASSOU` · `FALHOU` · `BLOQUEADO` |
| **Seções** | 9, sempre na mesma ordem do [`MODELO_DE_EPT.md`](MODELO_DE_EPT.md) |
| **Como criar** | copiar `MODELO_DE_EPT.md`, preencher tudo, apagar o aviso do topo e atualizar esta matriz |

## 3. Matriz de rastreabilidade

### Família D — Casos de decisão (§8.2) — 7 de 7 linhas cobertas

| EPT | Caso | Fixtures | Status |
| --- | --- | --- | --- |
| [`EPT-D01`](EPT-D01_Urgencia_Fila_Urgencia.md) | Urgência/achado crítico → `FILA_URGENCIA_MEDICA` | `Matriz_LaudoDeImagem_Pdf`, `Matriz_LaudoDeImagem_Imagem`, `Matriz_Receituario_Imagem`, `Matriz_Guia_Imagem`, `Conflito_AltoRisco` | ✅ escrita · `NAO_EXECUTADO` |
| [`EPT-A08`](EPT-A08_Borda_Limiar_Score.md) | Borda do limiar 0,84 / 0,85 (§16.8) | `Borda_Score_084`, `Borda_Score_085`, `Simultaneo_Urgencia_Score` | ✅ escrita · `NAO_EXECUTADO` |
| `EPT-D02` | Score combinado < 0,85 → `FILA_REVISAO_HUMANA` | `Borda_Score_084` (contraprova `Borda_Score_085`) | ⬜ a escrever |
| `EPT-D03` | Urgência + ambiguidade → dois destinos | `Simultaneo_Urgencia_Ilegivel`, `Simultaneo_Urgencia_Score` | ⬜ a escrever |
| `EPT-D04` | Receita de rotina → `FARMACIA_HOSPITALAR` | `Matriz_Receituario_Pdf`, `Matriz_Receituario_Texto`, `Escaneado_Receituario_PdfDigitalizado`, `Diferencial_ReceituarioManuscrito` | ⬜ a escrever |
| `EPT-D05` | Guia de rotina → `AUDITORIA_AUTORIZACOES` | `Matriz_Guia_Pdf`, `Matriz_Guia_Texto`, `Escaneado_Guia_PdfDigitalizado`, `Diferencial_GuiaTiss` | ⬜ a escrever |
| `EPT-D06` | Laudo, alta ou atestado de rotina → `PRONTUARIO_ELETRONICO` | `Matriz_LaudoLaboratorial_{Pdf,Imagem,Texto}`, `Matriz_LaudoDeImagem_Texto`, `Matriz_RelatorioDeAlta_{Pdf,Imagem}`, `Matriz_Atestado_{Pdf,Imagem,Texto}` | ⬜ a escrever |
| `EPT-D07` | Tipo desconhecido/destino não mapeado → `FILA_REVISAO_HUMANA` | `Matriz_NaoIdentificado_{Pdf,Imagem,Texto}`, `Matriz_Outro_{Pdf,Imagem,Texto}`, `Escaneado_Outro_PdfDigitalizado` | ⬜ a escrever |

### Família A — Critérios de aceite (§16) — 15 de 15 cobertos

| EPT | Critério | Fixtures | Status |
| --- | --- | --- | --- |
| `EPT-A01` | 1. Texto + PDF + imagem aceitos | `Matriz_Receituario_{Texto,Pdf,Imagem}` | ⬜ a escrever |
| `EPT-A02` | 2. Documento padrão classificado e roteado | `Matriz_Receituario_Pdf`, `Matriz_LaudoLaboratorial_Pdf`, `Matriz_Guia_Pdf`, `Matriz_RelatorioDeAlta_Pdf`, `Matriz_Atestado_Pdf` | ⬜ a escrever |
| `EPT-A03` | 3. Urgente com alerta, nunca só rotina | as 5 de `EPT-D01` (foco: contraprova) | ⬜ a escrever |
| `EPT-A04` | 4. Ambíguo/ilegível → revisão, sem dado inventado | `Matriz_NaoIdentificado_{Pdf,Imagem,Texto}`, `Qualidade_Foto_Desfocada`, `Matriz_RelatorioDeAlta_Texto` | ⬜ a escrever |
| `EPT-A05` | 5. Ausência dos 5 obrigatórios × CID isolado | `Ausencia_Paciente_Nome`, `Ausencia_Paciente_Idade`, `Ausencia_Medico_Nome`, `Ausencia_Medico_Crm`, `Ausencia_Diagnostico` + `Ausencia_SomenteCid`, `Ausencia_SomenteMedicamentos`, `Ausencia_SomenteExames` | ⬜ a escrever |
| `EPT-A06` | 6. 202 + consulta até estado terminal | qualquer funcional (sugerido `Matriz_Receituario_Texto`) | ⬜ a escrever |
| `EPT-A07` | 7. Alerta simulado, sem envio externo | `Matriz_LaudoDeImagem_Pdf`, `Simultaneo_Urgencia_*` | ⬜ a escrever |
| [`EPT-A08`](EPT-A08_Borda_Limiar_Score.md) | 8. 0,84 revisa; 0,85 não revisa | `Borda_Score_084`, `Borda_Score_085`, `Simultaneo_Urgencia_Score` | ✅ escrita · `NAO_EXECUTADO` |
| `EPT-A09` | 9. Campos ausentes não inferidos | `Ausencia_*`, `Matriz_NaoIdentificado_*` | ⬜ a escrever |
| `EPT-A10` | 10. Persistência no OCI; falha ≠ sucesso | `Matriz_Receituario_Pdf` + simulação de falha do OCI | ⬜ a escrever |
| `EPT-A11` | 11. Histórico ordenado e JSON validado | `Matriz_Guia_Pdf` + `GET /historico` | ⬜ a escrever |
| `EPT-A12` | 12. Regras, versão, justificativa e destino rastreáveis | `Conflito_Cid_Diagnostico`, `Conflito_Dose`, `Conflito_Dados`, `Conflito_Prioridade`, `Conflito_AltoRisco` | ⬜ a escrever |
| `EPT-A13` | 13. Interface sem expor segredos | `Matriz_*` + `Validacao_*` na tela | ⬜ a escrever |
| `EPT-A14` | 14. README + demonstração dos 3 cenários | documentação (sem fixture) | ⬜ a escrever |
| `EPT-A15` | 15. Nenhum opcional declarado sem prova | `Diferencial_ReceituarioManuscrito`, `Diferencial_CarimboSobreposto`, `Diferencial_HemogramaCompleto`, `Diferencial_GuiaTiss` | ⬜ a escrever |

### Família E — Erros, exceções e recuperação (§12) — 8 de 8 cobertos

| EPT | Situação | Fixtures / mecanismo | Status |
| --- | --- | --- | --- |
| `EPT-E01` | Formato/campos inválidos — rejeitar antes do Gemini | `Validacao_ArquivoDocx`, `Validacao_ArquivoZip`, `Validacao_MimeInvalido`, `Validacao_JsonMalformado`, `Validacao_EnvelopeVazio`, `Validacao_SemConteudo`, `Validacao_ArquivoVazio`, `Validacao_ArquivoGrande` | ⬜ a escrever |
| `EPT-E02` | Documento ilegível / extração inconclusiva | `Qualidade_Foto_Desfocada`, `Qualidade_Foto_BaixoContraste`, `Qualidade_Foto_Cortada`, `Qualidade_Pdf_SemTexto` | ⬜ a escrever |
| `EPT-E03` | Gemini indisponível / timeout | simulação por flag no adaptador | ⬜ a escrever |
| `EPT-E04` | Resposta Gemini inválida para o esquema | simulação por stub (payload malformado) | ⬜ a escrever |
| `EPT-E05` | Conflito entre dados — registrar sem alterar origem | `Conflito_Cid_Diagnostico`, `Conflito_Dose`, `Conflito_Dados`, `Conflito_Prioridade`, `Conflito_AltoRisco` | ⬜ a escrever |
| `EPT-E06` | Evento urgente registrado como simulado | `Matriz_LaudoDeImagem_Pdf`, `Simultaneo_Urgencia_*` | ⬜ a escrever |
| `EPT-E07` | Falha ao registrar alerta — não apagar a triagem | simulação de falha do emissor do evento | ⬜ a escrever |
| `EPT-E08` | Falha do OCI no original e no resultado | simulação; `ERRO_PERSISTENCIA` | ⬜ a escrever |

### Família R — Requisitos não funcionais (§14) — 11 de 11 cobertos

| EPT | RNF | Mecanismo | Status |
| --- | --- | --- | --- |
| `EPT-R01` | RNF-01 Precisão | conjunto de validação aprovado; métrica por tipo | ⬜ a escrever |
| `EPT-R02` | RNF-02 Segurança clínica | urgentes e ambíguos, inclusive sinais contraditórios | ⬜ a escrever |
| `EPT-R03` | RNF-03 Confiabilidade | simulação de indisponibilidade de Gemini e OCI | ⬜ a escrever |
| `EPT-R04` | RNF-04 Rastreabilidade | `GET /historico`: ator, motivo, status, versões | ⬜ a escrever |
| `EPT-R05` | RNF-05 Custo (Always Free) | revisão de configuração dos recursos OCI | ⬜ a escrever |
| `EPT-R06` | RNF-06 Formato | resposta validada em Pydantic/OpenAPI + `versao_esquema` | ⬜ a escrever |
| `EPT-R07` | RNF-07 Agilidade | medição de latência por etapa | ⬜ a escrever |
| `EPT-R08` | RNF-08 Privacidade | dados fictícios; nenhum segredo no repositório | ⬜ a escrever |
| `EPT-R09` | RNF-09 Manutenibilidade | README, diagrama, adaptador LLM isolado | ⬜ a escrever |
| `EPT-R10` | RNF-10 Flexibilidade | teste contratual do adaptador sem refazer regras | ⬜ a escrever |
| `EPT-R11` | RNF-11 Usabilidade | revisão dos três fluxos pela equipe | ⬜ a escrever |

---

## 4. Cobertura

| Fonte na especificação | Casos | EPTs | Cobertura |
| --- | ---: | ---: | --- |
| §8.2 — tabela de decisão | 7 | 7 | 7/7 |
| §16 — critérios de aceite | 15 | 15 | 15/15 |
| §12 — erros e exceções | 8 | 8 | 8/8 |
| §14 — requisitos não funcionais | 11 | 11 | 11/11 |
| **Total** | **41** | **41** | **41/41 planejados** |

## 5. Verificação

```bash
python3 tools/verificar_epts.py      # seções, IDs, fixtures órfãs, cobertura das seções
python3 tools/gerar_epts_pdf.py      # PDF consolidado das EPTs escritas
python3 tests/testar_contrato.py     # segue sendo a validação da massa de dados
```

## 6. Observação sobre execução

O repositório entrega contrato e massa de dados; o pipeline (FastAPI + LangGraph + Gemini) ainda
não existe nele. Por isso todas as EPTs nascem com `Status = NAO_EXECUTADO`. O que já é executável
hoje é a validação do resultado esperado contra o contrato (`python3 tests/testar_contrato.py`) e a
verificação de consistência da massa (`python3 tools/verificar_consistencia.py`).
