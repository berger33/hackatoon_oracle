# Registro de alterações — EF v1.2 e Análise de Requisitos v1.2

**Data:** 05/11/2026
**Responsável:** William — QA & Requirements Lead (autor e responsável por ambos os documentos)
**Referência de precedência:** `Projeto_oracle.pdf` (documento original do projeto), conforme EF seção 2.
**Status:** alterações aplicadas e publicadas nesta pasta.

---

## 1. Fundamento

A Especificação Funcional, na própria **seção 2 "Fontes e precedência"**, estabelece:

1. `Projeto_oracle.pdf` — define objetivo, escopo do hackathon, capacidades e entregáveis mínimos.
2. Análise de Requisitos — organiza o entendimento da equipe, **propõe requisitos** e registra decisões.
3. Especificação Funcional — **detalha comportamento** para implementação.

> "Quando a análise acrescenta uma restrição ou decisão que não está no brief, ela é identificada como proposta da equipe, não como exigência original do Projeto Oracle."

Reforços: EF seção 17 (matriz toda ancorada em `Brief: ...`), EF seção 18 (referências), Análise seção 6 (coluna `Origem` = Brief / Derivado) e `README.md` do time (`William | QA & Requirements Lead | Especificação Funcional & Suíte de Testes Pytest`).

**Conclusão:** EF e Análise são documentos derivados, de autoria do QA Lead e editáveis por ele. O Brief é a fonte 1 e a referência a manter de acordo. As alterações abaixo são de **conformidade com o Brief**, não exceções ou flexibilizações.

## 2. O que o Brief exige e o que não exige

| Brief exige | Brief não exige |
| --- | --- |
| Resultados e histórico de triagem em JSON estruturado | `202 Accepted` + consulta posterior por ID (é decisão 6 da EF seção 15; o exemplo do Brief é síncrono) |
| Persistência de documentos e decisões no OCI Object Storage Always Free | Retomada de processamento após reiniciar a API |
| Tratamento de exceções e fallback para revisão humana | Validação E2E por cliente HTTP real contra o bucket no ambiente final |
| Integração ativa com OCI para segregação e armazenamento | Eventos de destino/alerta/persistência dentro do histórico |
| README com arquitetura/diagrama e 3 cenários de demonstração | Composição específica dos eventos de histórico |
| Recursos opcionais/diferenciais explicitamente listados | Continuidade entre processos (sequer listada como opcional) |

## 3. Decisões aplicadas

| ID | Decisão | Onde foi aplicado |
| --- | --- | --- |
| **D-01** | Continuidade entre processos (retomada após reiniciar a API) fora do escopo obrigatório do MVP. RNF-03 delimitado a falhas dentro do mesmo processo, com status e retry observáveis. Limitação documentada; sem "RNF-03 100%". | EF: 3.2.4, 12 (nova linha), 14 (RNF-03), 15 item 10, 16 item 15, 17. Análise: 2 (glossário), 4, 6 (RNF-03), 11 (risco), 12, 14. |
| **D-02** | Decisão, destino, alerta e persistência constam do resultado estruturado (EF seção 9.2); histórico cobre recebimento/início/conclusão/erro/recuperação. Sem campo novo em `EventoHistorico`. | EF: 9.2, 13, 14 (RNF-04), 15 item 11, 16 item 11. Análise: 5.5 (RF-26), 8, 12, 14. |
| **D-03** | Integração ativa com OCI comprovada por escrita/leitura byte a byte no bucket real + suíte automatizada. E2E por cliente HTTP real no ambiente final é reforço de QA, dispensado no MVP. | EF: 3.2.4, 15 item 12, 16 item 10. Análise: 4, 10, 12, 14. |
| — | 202 + consulta por ID identificado como decisão da equipe, não exigência do Brief. | EF: 10, 15 item 6, 16 item 6, 17. Análise: 14.2. |
| — | Matriz de rastreabilidade com coluna de origem e linha "Decisões de escopo da equipe". | EF: 17. |
| — | Registro de volumetria de testes (245 / 208 / 304 / 306 / 317 / 319 são marcos diferentes; vigente = 319 aprovados, 1 ignorado). | Análise: 10. |

## 4. Ressalvas registradas (não removidas)

- **`src/api/routes.py` não é mera delegação:** parsing de JSON/multipart, `background_tasks`, `_tratar_erro_ingestao` e `GET /triagens/{id}` disparando `executar_triagem` sincronamente (L195-213). A dispensa do E2E não apaga essa lógica, que é coberta pela suíte com cliente de teste.
- **Limitação real de restart:** índice de triagens, resultado e histórico consultável ficam em memória; após reinício, consultas por ID não são reconstruídas a partir do OCI. Objetos gravados no bucket permanecem íntegros. Registrada, não escondida.
- **Evidência de OCI real:** `scripts/testar_historico_oci.py` L142 (`TriagemService(storage=storage)`) e L184-186 (`ler_bytes`), com original, resultado e histórico. Sem HTTP.
- **Evidência de suíte:** PR #22 `57025fe`, 319 aprovados / 1 ignorado (05/11/2026).
- **D-01/D-02/D-03 são propostas de endurecimento para versões futuras**, não redução de requisito obrigatório. Se adotadas, devem entrar como nova exigência da equipe.

## 5. O que NÃO foi alterado

- Nenhum requisito funcional RF-01 a RF-30, nenhuma regra RN-01 a RN-07, nenhum valor controlado, limiar 0.85, fórmula da nota combinada, três cenários de demonstração ou restrição de Always Free.
- Nenhum arquivo do repositório de implementação `No-Country-simulation/g10-brasil-equipe-15_mediflow` foi modificado.
- **Pendência que permanece com a autora do PR #22:** atualizar o corpo do PR de **304** para **319 aprovados, 1 ignorado** (registro de evidência, não decisão normativa).

## 6. Arquivos desta pasta

| Arquivo | Formato |
| --- | --- |
| `MediFlow_Especificacao_Funcional_v1.2.md` / `.html` / `.pdf` | Especificação Funcional v1.2 |
| `MediFlow_Analise_de_Requisitos_v1.2.md` / `.html` / `.pdf` | Análise de Requisitos v1.2 |
| `REGISTRO_DE_ALTERACOES_v1.2.md` | Este registro |
| `index.html` | Índice com links diretos para todos os formatos |

**Nota de versão:** por decisão do autor, ambos os documentos saem como **v1.2** nesta revisão de 05/11/2026. A EF publicada anteriormente era v1.0 (18/10/2026); a numeração v1.2 consolida o alinhamento ao Brief.
