# MediFlow — PDFs atualizados em 21/10/2026

## Por que

O `Projeto_oracle.pdf` (brief do solicitante) prevalece sobre a Especificação
Funcional v1.0 onde as duas divergem. Pelo brief, **urgência isolada não gera
revisão humana**: o caso é encaminhado à fila urgente, com alerta, e termina
como `PROCESSADO`. Revisão humana é consequência de **ambiguidade**, nunca de
urgência por si só.

Estes dois PDFs foram editados **só** nos trechos que contrariavam essa regra.
Nenhum outro texto, numeração, seção ou formatação foi alterado.

## O que mudou — Especificação Funcional v1.0 (6 edições)

| # | Seção (pág.) | Antes | Depois |
|---|---|---|---|
| 1 | §5.3 `EM_REVISAO` (p. 5) | “A análise terminou, mas encontrou **urgência**, ambiguidade, conflito,” | “A análise terminou, mas encontrou ambiguidade, conflito,” |
| 2 | §8.1 RN-01 (p. 9) | “• RN-01: **sem urgência**, ambiguidade/conflito impeditivo ou score abaixo do limiar, encaminhar automaticamente ao destino de rotina.” | “• RN-01: sem ambiguidade/conflito impeditivo ou score abaixo do limiar, encaminhar automaticamente ao destino de rotina do tipo; com urgência, à fila urgente e com alerta.” |
| 3 | §8.2 tabela de decisão, linha “Urgência/achado crítico”, coluna **Revisão** (p. 9) | “Sim, obrigatória” | “Não” |
| 4 | §15 decisão 1 (p. 13) | “1. Urgência com ambiguidade/revisão: encaminhar à fila urgente, registrar alerta simulado e também incluir na fila lógica de revisão.” | “1. Urgência: encaminhar à fila urgente e registrar alerta simulado; com ambiguidade, incluir também na fila lógica de revisão. Urgência isolada termina como processada, sem revisão humana.” |

(As edições 2 e 4 ocupam duas linhas cada uma no documento, por isso a contagem
de 6 edições para 4 trechos.)

## O que mudou — Análise de Requisitos v1.1 (3 edições)

| # | Seção (pág.) | Antes | Depois |
|---|---|---|---|
| 5 | §7 RN-01 (p. 5) | “Casos padrão (sem ambiguidade, **sem urgência** e com nota combinada ≥ 0.85) seguem direto ao destino,” | “Casos padrão (sem ambiguidade e com nota combinada de 0.85 ou mais) seguem direto ao destino,” |
| 6 | §12 Pendências, linha “Urgência e ambiguidade simultâneas”, coluna Situação (p. 7) | “A definir” | “Decidido” |
| 7 | §12 Pendências, linha “Urgência e ambiguidade simultâneas”, coluna Detalhamento (p. 7) | “Sugestão inicial: urgência prevalece e o caso alerta E pede revisão.” | “Urgência prevalece: alerta sempre; revisão só com ambiguidade.” |

## O que **não** mudou (e por que)

* **RN-02 e RN-03 da Análise v1.1 já estavam corretas** — “ambíguo, ilegível,
  inconsistente ou nota < 0,85 → Revisão Humana” e “achado crítico ou prescrição
  de alto risco → Fila de Urgência Médica **com alerta**”. A divergência estava
  na Especificação Funcional, não na Análise. Não “corrigir” essas duas regras.
* **O caso das duas filas não muda**: urgência + ambiguidade continua indo para
  `FILA_URGENCIA_MEDICA` **e** `FILA_REVISÃO_HUMANA`, com `EM_REVISAO`, alerta e
  `requer_auditoria_humana = true`.
* **EF §15 decisões 2 a 6, §13 (armazenamento) e todo o restante** seguem
  intocados — a revisão da decisão de urgência não os afeta.
* Os PDFs originais da raiz do repositório continuam na versão enviada pela
  equipe; as cópias atualizadas estão nesta pasta e no ZIP.

## Observação técnica sobre as fontes

As fontes embutidas nos PDFs (Arial e Liberation Sans) são subconjuntos sem mapa
Unicode e não aceitam texto novo. O texto reescrito usa Helvetica, que tem
exatamente as mesmas métricas das fontes originais — por isso **nada se
desloca**: posição, corpo, cor e entrelinhas são os do original.

Duas consequências menores:

* O símbolo “≥” não existe em Helvetica; na edição 5 ele foi reescrito como
  “de 0.85 ou mais”, com o mesmo significado da regra (“abaixo de 0.85 exige
  revisão”).
* O marcador “•” da RN-01 (edição 2) foi preservado do original: só o texto
  depois dele é reescrito.

## Como reproduzir

```bash
pip install pymupdf
python3 tools/atualizar_pdfs_urgencia.py               # gera em dist/
python3 tools/atualizar_pdfs_urgencia.py --verificar   # confere o resultado
```

O script parte sempre dos originais (é idempotente), confere a largura de cada
linha antes de escrever e valida o resultado reabrindo o PDF.

## O que já estava atualizado no repositório

A mesma decisão (R1) já tinha sido propagada no branch
`arena/b33f82cc-hackatoon-oracle`:

* `app/models.py` — R1 e R4 reescritas; `requer_auditoria_humana = ambiguidade`
* `tests/fixtures/` — 5 fixtures viraram `PROCESSADO` / `revisao = NAO`
  (`Matriz_LaudoDeImagem_Pdf`, `Matriz_Receituario_Imagem`,
  `Matriz_LaudoDeImagem_Imagem`, `Matriz_Guia_Imagem`, `Conflito_AltoRisco`)
* `docs/testes/CONTRATO_DE_DADOS.md`, `CATALOGO_DE_DOCUMENTOS_DE_TESTE.md` e
  `AUDITORIA_2026-10-20.md` — regras e exemplos alinhados
* `tools/gerar_fixtures_demo.py` e `tools/gerar_fixtures_catalogo.py`

As EPTs (`docs/epts/`) seguem **congeladas**, porque ainda não foram aprovadas —
nada nelas foi alterado e elas não fazem parte deste pacote.
