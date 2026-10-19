# MediFlow

> Agente autônomo para triagem, extração e roteamento de documentos clínicos.
> **Hackathon ONE G10 — Oracle Next Education & Alura**

![Status](https://img.shields.io/badge/status-especifica%C3%A7%C3%A3o-definida-yellow)
![Cloud](https://img.shields.io/badge/cloud-Oracle%20Cloud-red)
![Stack](https://img.shields.io/badge/stack-Gemini%20%C2%B7%20LangGraph%20%C2%B7%20FastAPI%20%C2%B7%20React-blue)

## Sobre o projeto

Hospitais, laboratórios e operadoras perdem milhares de horas lendo laudos, receitas e guias manualmente para digitar dados em sistemas legados. O processo é lento, caro e sujeito a erros que atrasam autorizações e colocam pacientes em risco.

O **MediFlow** recebe documentos clínicos e administrativos em **PDF, imagem ou texto**, descobre sozinho o tipo do documento, extrai os dados clínicos, avalia a confiança e **roteia para o setor correto**. Quando há dúvida ou risco, o caso vai para revisão humana com o motivo registrado.

> A solução é apoio à triagem documental. Não substitui diagnóstico, prescrição, decisão clínica ou auditoria profissional.

## Como o agente funciona

1. **Recebe** o documento (PDF digital, PDF digitalizado, imagem ou texto) e valida formato, tamanho e campos.
2. **Classifica** o tipo, a especialidade e a prioridade (`URGENTE`, `ROTINA` ou `NAO_IDENTIFICADA`).
3. **Extrai** paciente, médico/CRM, diagnóstico/CID, medicamentos, exames e sinais de urgência — sem inventar dados ausentes.
4. **Avalia** consistência, conflitos e a nota combinada de confiança: `min(score_classificação, score_extração)`.
5. **Decide** o destino no grafo condicional (LangGraph) e aciona revisão humana e alerta quando necessário.
6. **Persiste** documento e resultado no OCI Object Storage e devolve a resposta em JSON validado.

## Regras de decisão

| Situação | Destino | Revisão humana | Alerta |
| --- | --- | --- | --- |
| Urgência ou achado crítico | `FILA_URGENCIA_MEDICA` | Sim | Sim |
| Score combinado < 0,85 | `FILA_REVISAO_HUMANA` | Sim | Não, salvo urgência |
| Urgência + ambiguidade/ilegibilidade | `FILA_URGENCIA_MEDICA` + `FILA_REVISAO_HUMANA` | Sim | Sim |
| Receita de rotina | `FARMACIA_HOSPITALAR` | Não | Não |
| Guia de procedimento de rotina | `AUDITORIA_AUTORIZACOES` | Não | Não |
| Laudo, alta ou atestado de rotina | `PRONTUARIO_ELETRONICO` | Não | Não |
| Tipo desconhecido ou fora da taxonomia | `FILA_REVISAO_HUMANA` | Sim | Só se urgente |

**Campos cuja ausência obriga revisão:** nome do paciente, idade, nome do médico solicitante, CRM e diagnóstico/hipótese. A ausência de CID-10, medicamentos ou exames **não** obriga revisão por si só.

## Stack

| Camada | Tecnologia |
| --- | --- |
| LLM multimodal | Google Gemini |
| Orquestração | LangGraph |
| Validação | Pydantic |
| API | FastAPI |
| Interface | React |
| Armazenamento | OCI Object Storage (Always Free) |
| Deploy (opcional) | OCI Compute (Always Free) |

## Arquitetura

```text
┌──────────────┐     multipart/JSON      ┌──────────────────┐
│  React       │ ──────────────────────► │  FastAPI         │
│  triagem     │ ◄────────────────────── │  /api/v1/triagens│
└──────────────┘     202 + polling       └────────┬─────────┘
                                                  │
                                       ┌──────────▼──────────┐
                                       │  LangGraph          │
                                       │  classificar →      │
                                       │  extrair → avaliar  │
                                       │  → rotear           │
                                       └──────────┬──────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    ▼                             ▼                             ▼
          ┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
          │ Gemini           │          │ OCI Object       │          │ Filas lógicas    │
          │ (multimodal)     │          │ Storage          │          │ (simuladas)      │
          └──────────────────┘          └──────────────────┘          └──────────────────┘
```

O processamento é **assíncrono**: `POST /api/v1/triagens` responde `202 Accepted` com `documento_id`, e o cliente consulta `GET /api/v1/triagens/{id}` até o estado terminal (`PROCESSADO` ou `EM_REVISAO`).

## Estrutura do repositório

```text
.
├── docs/
│   ├── README.md
│   ├── modelo-documento.md
│   └── testes/
│       └── CATALOGO_DE_DOCUMENTOS_DE_TESTE.md   # quantos e quais fixtures criar
├── tests/
│   └── fixtures/
│       ├── README.md
│       ├── manifest.csv                         # 67 fixtures com resultado esperado
│       ├── demo/                                # 12 casos de pitch (TXT + PDF + JPG + expected.json)
│       └── catalogo/                            # 55 casos restantes, inclusive negativos técnicos
├── tools/
│   ├── gerar_fixtures_demo.py
│   ├── gerar_fixtures_catalogo.py
│   └── gerar_mapa_documentos.py
├── README.md
└── .env.example
```

> O código da aplicação será adicionado nas próximas etapas. A especificação funcional está na base documental do projeto (Google Drive) e o catálogo de testes já está versionado aqui.

## Documentação

- [Mapa de documentos de teste (PDF)](docs/testes/Mapa_de_Documentos_de_Teste_MediFlow.pdf) — visão visual de cobertura, fluxo e catálogo completo.
- [Catálogo de documentos de teste](docs/testes/CATALOGO_DE_DOCUMENTOS_DE_TESTE.md) — 12 para demonstrar, 57 para testar de verdade, 67 para cobertura completa.
- [Kit de demonstração](tests/fixtures/demo/README.md) — os 12 casos de pitch em TXT, PDF e JPG.
- [Catálogo completo de fixtures](tests/fixtures/catalogo/README.md) — os 55 casos restantes, incluindo negativos técnicos.
- [Manifesto de fixtures](tests/fixtures/manifest.csv) — IDs, tipo, formato, cenário, destino e status esperados.
- [Índice de documentos](docs/README.md)
- [Modelo de documento](docs/modelo-documento.md)

## Critérios de aceite do MVP

- [ ] Texto, pelo menos um PDF e uma imagem aceitos com resultado coerente
- [ ] Documento padrão classificado, extraído e roteado para a rotina correta
- [ ] Documento urgente detectado, roteado para a fila urgente com alerta simulado
- [ ] Documento ambíguo/ilegível em revisão humana, sem dado inventado
- [ ] Ausência dos 5 campos obrigatórios força revisão
- [ ] Submissão `202` + consulta por `documento_id` + histórico ordenado
- [ ] Score < 0,85 revisa; score = 0,85 não revisa por esse critério
- [ ] Documento e resultado persistidos no OCI, com caminho lógico informado
- [ ] Interface mostra estados, urgência, revisão e falhas sem expor segredos
- [ ] README com arquitetura e demonstração dos 3 cenários

## Configuração

Copie `.env.example` para `.env` e preencha as credenciais da tenancy OCI. **Nunca comite o `.env`.**

```bash
cp .env.example .env
```

## Equipe

| Nome | Papel |
| --- | --- |
| A definir | Product / Pitch |
| A definir | Agentes e IA |
| A definir | Back-end e OCI |
| A definir | Front-end e QA |

## Licença

A definir.
