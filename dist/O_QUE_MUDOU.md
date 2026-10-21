# MediFlow — PDFs atualizados em 21/10/2026

Pacote: `MediFlow_PDFs_atualizados_2026-10-21.zip`, com os dois documentos
atualizados.

| Documento | Antes | Depois |
| --- | --- | --- |
| `MediFlow_Especificacao_Funcional_v1.0.pdf` | 15 páginas | 16 páginas (nova página de anexo) |
| `MediFlow_-_Análise_de_Requisitos_v1.1.pdf` | 7 páginas | 8 páginas (nova página de anexo) |

Cada edição foi feita **no lugar**: o trecho antigo é apagado e o novo é
reescrito na mesma posição, com o mesmo corpo, cor e entrelinha. O que não cabia
no corpo do texto foi para um anexo, referenciado no próprio trecho. Nenhuma
outra numeração, seção ou formatação foi alterada.

---

## Rodada 2 — decisões A1 a A9 e consistência entre os documentos

### Bloco A — as 9 decisões

| # | Decisão | Onde entrou |
| --- | --- | --- |
| A1 | Conflito **impeditivo** é o de gravidade `ALTA` ou `MÉDIA`; `BAIXA` é registrado e não bloqueia | RF-16 (p. 7), §5.3 (p. 5), Anexo A.2 |
| A2 | Dicionário clínico fechado: conflitos, achados críticos e medicamentos de alto risco | Anexo A.2 (p. 15) |
| A3 | `score_extracao` determinístico: `1 − 0,2×obrigatório ausente − 0,1×incerto − 0,3/0,2/0,1 por conflito ALTA/MÉDIA/BAIXA`, piso 0 | RF-18 (p. 7), Anexo A.4 |
| A4 | `nivel_prioridade = NAO_IDENTIFICADA` gera revisão | §5.2, §5.3, RN-02 da Análise, Anexo A.6 |
| A5 | `urgencia = INDETERMINADO` conta como campo incerto e gera revisão | RF-13 (p. 7), Anexo A.6 |
| A6 | Limites: 10 MB, 20 páginas, PDF/JPG/PNG/WEBP/TXT, timeout de 60 s no Gemini, 2 retentativas com backoff | §12 (p. 12), §15 (p. 14), Anexo A.5 |
| A7 | Metas numéricas fora do MVP; aceite pelos casos aprovados; latência por etapa, sem meta; retenção até o fim do hackathon | §14 (p. 13), §13 (p. 13), §15 (p. 14), Anexo A.7 |
| A8 | Autenticação/autorização fora do MVP (demo local), com a ressalva de que exposição pública exige auth antes | §4 (p. 4), §10.1 (p. 11), §15 (p. 14), Anexo A.7 |
| A9 | RF-11 **mantém** a comparação com a farmacopeia, agora com **lista própria da equipe** (PDF de consulta do modelo); sem o arquivo, vale a regra de dose suspeita de RF-16 | RF-11 (p. 7), Anexo A.2 |

### Bloco B — consistência entre os dois documentos

| # | Ajuste | Onde |
| --- | --- | --- |
| 1 | As quatro linhas “A definir” da §12 da Análise viraram “Decidido”: fórmula da nota, níveis de prioridade e tempo-alvo (este, sem meta numérica) | Análise §12 (p. 7) |
| 2 | Linha do caso das duas filas na tabela de roteamento da Análise | Análise §7 (p. 5) |
| 3 | Caminho `processados/urgentes/{documento_id}.json` para casos urgentes, como no exemplo do brief | EF §13 (p. 12) |
| 4 | Ponteiro para o exemplo do caso urgente que termina `PROCESSADO` | EF §9.2 (p. 10), Anexo A.3 |
| 5 | `EM_REVISAO` em §5.3 passa a citar ilegibilidade e “conflito impeditivo” | EF §5.3 (p. 5) |
| 6 | Vocabulário: status em maiúsculas na Análise; JSON como envelope da requisição, não como formato de documento | Análise §8 (p. 6), RF-02 (p. 3) |
| 7 | Anexo com o detalhamento de todas as decisões nos dois documentos | EF Anexo A (p. 15-16), Análise Anexo (p. 8) |

### O que a rodada 2 **não** mexeu

Bloco C, conferido e considerado conforme: regra de urgência (já corrigida na
rodada 1), RN-02/RN-03 da Análise, caso das duas filas, 5 destinos, 8 tipos de
documento, limiar 0,85, `min()` dos scores, dados fictícios, API 202, fila
lógica sem decisão humana, alerta simulado, 3 cenários, OCI Always Free,
segregação recebidos/processados/auditoria e `cid_extraido` (divergência
consciente com `cid_sugerido`, registrada em EF §9.2).

---

## Rodada 1 — a regra de urgência

O `Projeto_oracle.pdf` (brief) prevalece sobre a EF v1.0 onde as duas divergem:
**urgência isolada não gera revisão humana**. O caso vai para a fila urgente,
com alerta, e termina em `PROCESSADO`. Revisão é consequência de **ambiguidade**.

| # | Documento, seção (pág.) | Antes | Depois |
| --- | --- | --- | --- |
| 1 | EF §5.3 `EM_REVISAO` (p. 5) | “encontrou **urgência**, ambiguidade, conflito,” | “encontrou ambiguidade, conflito,” |
| 2 | EF §8.1 RN-01 (p. 9) | “**sem urgência**, ambiguidade/conflito impeditivo ou score abaixo do limiar…” | “sem ambiguidade/conflito impeditivo ou score abaixo do limiar…; com urgência, à fila urgente e com alerta.” |
| 3 | EF §8.2 tabela, coluna **Revisão** (p. 9) | “Sim, obrigatória” | “Não” |
| 4 | EF §15 decisão 1 (p. 13) | “1. Urgência com ambiguidade/revisão: …” | “1. Urgência: … Urgência isolada termina como processada, sem revisão humana.” |
| 5 | Análise §7 RN-01 (p. 5) | “(sem ambiguidade, **sem urgência** e com nota combinada ≥ 0,85)” | “(sem ambiguidade e com nota combinada de 0.85 ou mais)” |
| 6 | Análise §12, coluna Situação (p. 7) | “A definir” | “Decidido” |
| 7 | Análise §12, coluna Detalhamento (p. 7) | “Sugestão inicial: urgência prevalece e o caso alerta E pede revisão.” | “Urgência prevalece: alerta sempre; revisão só com ambiguidade.” |

---

## Propagação no repositório

* `app/models.py` — R2 reescrita com os gatilhos novos; `GRAVIDADES_IMPEDITIVAS`
  (A1), `PESO_CONFLITO` e `calcular_score_extracao` (A3)
* `docs/testes/CONTRATO_DE_DADOS.md` — R2, nova R8, tabela de decisões de
  21/10/2026
* `tools/atualizar_pdfs.py` — gerador dos dois PDFs (substitui
  `tools/atualizar_pdfs_urgencia.py`)
* `tests/fixtures/` — inalterados **neste pacote**: A1, A4 e A5 não mudam nenhum
  dos 67 casos existentes (os 4 conflitos das fixtures são `ALTA`; os 8
  `NAO_IDENTIFICADA` e os 8 `INDETERMINADO` já chegavam a `EM_REVISAO` por outros
  gatilhos)

Verificação: `tests/testar_contrato.py` 67/67 e `tools/verificar_consistencia.py`
com 0 erros.

> **21/10/2026, mais tarde — a suíte saiu de 67 para 77 fixtures.** As três
> regras acima ficaram explícitas no contrato, mas nenhum caso as exercitava em
> isolamento, e não havia **nenhum** teste de tamanho acima do limite nem de
> documento com mais páginas do que o permitido. Entraram 10 casos:
> `Conflito_Gravidade_Media`, `Conflito_Gravidade_Baixa` (A1),
> `Borda_Prioridade_NaoIdentificada` (A4), `Borda_Urgencia_Indeterminada` (A5) e
> o bloco **Limite** — `Limite_Tamanho_10MB`, `Limite_Tamanho_Acima10MB`,
> `Limite_Paginas_20`, `Limite_Paginas_21`, `Limite_Formato_Png` e
> `Limite_Formato_Webp` (A6). Detalhe no catálogo.

Os PDFs originais da raiz do repositório continuam na versão enviada pela
equipe; as cópias atualizadas estão nesta pasta e no ZIP. As EPTs
(`docs/epts/`) seguem **congeladas**, porque ainda não foram aprovadas — nada
nelas foi alterado e elas não fazem parte deste pacote.

---

## Observação técnica sobre as fontes

As fontes embutidas nos PDFs (Arial e Liberation Sans) são subconjuntos sem mapa
Unicode e não aceitam texto novo. O texto reescrito usa Helvetica, que tem
exatamente as mesmas métricas — por isso **nada se desloca**. Helvetica só cobre
Latin-1, o que traz três consequências, todas contornadas:

* “•” (marcador de lista) é preservado do original: o rect de edição começa
  depois dele e só o texto é reescrito.
* “≥” foi reescrito como “de 0.85 ou mais”, com o mesmo significado da regra.
* Nas páginas novas do anexo, o cabeçalho e o rodapé não são reescritos: são
  replicados do original como objeto vetorial, mantendo a fonte e os símbolos.

## Como reproduzir

```bash
pip install pymupdf
python3 tools/atualizar_pdfs.py               # gera em dist/
python3 tools/atualizar_pdfs.py --simular     # mostra o plano, sem alterar nada
python3 tools/atualizar_pdfs.py --verificar   # confere o resultado
```

O script parte sempre dos originais (é idempotente), recusa caracteres fora do
Latin-1, confere a largura de cada linha antes de escrever e valida o resultado
reabrindo os PDFs.
