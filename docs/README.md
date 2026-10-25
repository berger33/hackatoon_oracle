# Documentos do projeto — hackatoon_oracle

Esta pasta reúne a documentação da **massa de dados de teste** do MediFlow.

## Documentos

| Documento | Conteúdo |
| --- | --- |
| [Contrato de dados](testes/CONTRATO_DE_DADOS.md) | Enums, payload, formatos de erro e as 7 regras de decisão — em português, com o porquê de cada uma |
| [Catálogo de documentos de teste](testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md) | Os 67 casos, bloco por bloco: o que cada um testa e qual desfecho esperar |
| [EPT — Especificação de Procedimento de Teste (CSV)](testes/EPT_MediFlow_v1.0.csv) | 100 casos executáveis: pré-condição, massa, passos, resultado esperado, rastreabilidade e colunas de execução |
| [EPT — guia e cobertura](testes/EPT_MediFlow_GUIA_E_COBERTURA.md) | Dicionário de colunas, ordem de execução, cobertura de RF/RN/RNF, fixtures e itens de aceite |
| [EPT — versão navegável (HTML)](testes/EPT_MediFlow_preview.html) | Os 100 casos com filtros, detalhe do caso e as matrizes de cobertura, em um arquivo único |
| [Mapa de documentos de teste (PDF)](testes/Mapa_de_Documentos_de_Teste_MediFlow.pdf) | Visão visual: cobertura, fluxo de decisão, kit de demonstração e catálogo completo |
| [Auditoria de consistência (2026-10-20)](testes/AUDITORIA_2026-10-20.md) | O que foi conferido em todos os formatos (CRM-SP, contagens, pacote ZIP), o que estava errado e o que foi corrigido |

## Ordem de leitura

1. **Contrato** — entenda o formato da resposta e as regras.
2. **Catálogo** — veja quais casos existem e por que existem.
3. **EPT (CSV)** — veja como executar e como saber se passou; o guia explica as colunas e a cobertura.
4. **Mapa (PDF)** — a mesma informação em uma página por bloco, para apresentar.

Os arquivos em si ficam em [`tests/fixtures/`](../tests/fixtures/), e o índice em formato de máquina é o [`manifest.csv`](../tests/fixtures/manifest.csv).
