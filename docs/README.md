# Documentos do projeto — hackatoon_oracle

Esta pasta reúne a documentação da **massa de dados de teste** do MediFlow.

## Documentos

| Documento | Conteúdo |
| --- | --- |
| [Contrato de dados](testes/CONTRATO_DE_DADOS.md) | Enums, payload, formatos de erro e as 7 regras de decisão — em português, com o porquê de cada uma |
| [Catálogo de documentos de teste](testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md) | Os 79 casos, bloco por bloco: o que cada um testa e qual desfecho esperar |
| [EPT consolidada (CSV)](testes/EPT_MediFlow_v1.1.csv) | 111 casos executáveis com pré-condição, massa, passos, resultado esperado, rastreabilidade à EPT do plano e colunas de execução |
| [EPT consolidada — guia e cobertura](testes/EPT_MediFlow_GUIA_E_COBERTURA.md) | Dicionário de colunas, ordem de execução, cobertura de RF/RN/RNF, fixtures, §16 e EPTs D/A/E/R |
| [EPT consolidada — documento (PDF)](testes/EPT_MediFlow_v1.1.pdf) | Capa, sumário, os casos por suíte, anexos de cobertura e folha de aprovação — versão de leitura e assinatura |
| [EPT consolidada — versão navegável (HTML)](testes/EPT_MediFlow_preview.html) | Os casos com filtros, detalhe e as matrizes de cobertura, em um arquivo único |
| [Mapa de documentos de teste (PDF)](testes/Mapa_de_Documentos_de_Teste_MediFlow.pdf) | Visão visual: cobertura, fluxo de decisão, kit de demonstração e catálogo completo |
| [Auditoria de consistência (2026-10-20)](testes/AUDITORIA_2026-10-20.md) | O que foi conferido em todos os formatos (CRM-SP, contagens, pacote ZIP), o que estava errado e o que foi corrigido |
| [Integração com o G10](integracao/) | Análise do repositório da equipe: mapeamento de contrato, 10 issues prontas e os 3 cenários delas traduzidos para o nosso contrato |
| [EPTs — Procedimentos de teste](epts/) | Um procedimento por caso da Especificação Funcional v1.0: 41 planejados, com plano, modelo, índice e PDF consolidado |

## Ordem de leitura

1. **Contrato** — entenda o formato da resposta e as regras.
2. **Catálogo** — veja quais casos existem e por que existem.
3. **Mapa (PDF)** — a mesma informação em uma página por bloco, para apresentar.
4. **EPTs** — o passo a passo para provar cada caso da especificação funcional (41 no plano, em `epts/`).
5. **EPT consolidada (CSV/PDF)** — a visão de execução em lote: todos os casos, com massa, passos e resultado esperado em um só artefato.

Os arquivos em si ficam em [`tests/fixtures/`](../tests/fixtures/), e o índice em formato de máquina é o [`manifest.csv`](../tests/fixtures/manifest.csv).
