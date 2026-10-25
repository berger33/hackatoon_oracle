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
| Urgência ou achado crítico | `FILA_URGENCIA_MEDICA` | Não — só se houver ambiguidade junto | Sim |
| Score combinado < 0,85 | `FILA_REVISAO_HUMANA` | Sim | Não, salvo urgência |
| Urgência + ambiguidade/ilegibilidade | `FILA_URGENCIA_MEDICA` + `FILA_REVISAO_HUMANA` | Sim | Sim |
| Receita de rotina | `FARMACIA_HOSPITALAR` | Não | Não |
| Guia de procedimento de rotina | `AUDITORIA_AUTORIZACOES` | Não | Não |
| Laudo, alta ou atestado de rotina | `PRONTUARIO_ELETRONICO` | Não | Não |
| Tipo desconhecido ou fora da taxonomia | `FILA_REVISAO_HUMANA` | Sim | Só se urgente |

**Campos cuja ausência obriga revisão:** nome do paciente, idade, nome do médico solicitante, CRM e diagnóstico/hipótese. A ausência de CID-10, medicamentos ou exames **não** obriga revisão por si só.

O contrato completo — enums, payload, formato de erro e o porquê de cada regra — está em [`docs/testes/CONTRATO_DE_DADOS.md`](docs/testes/CONTRATO_DE_DADOS.md) e é executável em [`app/models.py`](app/models.py).

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

Este repositório entrega a **massa de dados de teste** do MediFlow e o **contrato** que ela valida. As pastas de fixture usam nomes por extenso, sem abreviações: `Matriz_Guia_Imagem` é o bloco **Matriz**, tipo **guia**, formato **imagem**. Os blocos são Matriz, Ausencia, Borda, Conflito, Simultaneo, Qualidade, Validacao, Escaneado e Diferencial.

```text
.
├── app/
│   └── models.py                                # CONTRATO v1.0 (Pydantic): payload, enums, regras
├── docs/
│   ├── README.md
│   ├── epts/                                # EPTs: um procedimento por caso da especificação funcional
│   └── testes/
│       ├── CONTRATO_DE_DADOS.md                 # o contrato em português, com o porquê de cada regra
│       ├── CATALOGO_DE_DOCUMENTOS_DE_TESTE.md   # os 79 casos, bloco por bloco
│       ├── EPT_MediFlow.csv                    # EPT executável: casos com passo a passo e rastreabilidade
│       ├── EPT_MediFlow_GUIA_E_COBERTURA.md     # dicionário da EPT + cobertura RF/RN/RNF/fixtures
│       ├── EPT_MediFlow.pdf                    # a EPT em PDF: capa, sumário, casos por suíte, anexos
│       ├── EPT_MediFlow_preview.html            # a EPT navegável: filtros, detalhe e cobertura
│       ├── Mapa_de_Documentos_de_Teste_MediFlow.pdf
│       └── AUDITORIA_2026-10-20.md              # auditoria de consistência: CRM-SP, datas, pacote, verificadores
├── tests/
│   ├── testar_contrato.py                       # valida os 79 expected.json no contrato
│   └── fixtures/
│       ├── README.md                            # como ler os nomes e os blocos
│       ├── manifest.csv                         # 79 linhas: uma por documento
│       ├── demo/                                # 12 casos de pitch (TXT + PDF + JPG + expected.json)
│       └── catalogo/                            # 55 casos restantes, inclusive negativos técnicos
├── tools/
│   ├── gerar_epts_pdf.py                        # PDF consolidado das EPTs
│   ├── verificar_epts.py                        # estrutura, IDs, fixtures citadas e cobertura das EPTs
│   ├── contrato_fixtures.py                     # monta os expected.json a partir do contrato
│   ├── gerar_fixtures_demo.py                   # recria os 12 casos
│   ├── gerar_fixtures_catalogo.py               # recria os 55 casos
│   ├── gerar_mapa_documentos.py                 # recria o PDF do mapa
│   ├── gerar_ept.py                             # gera a EPT (CSV + guia) a partir da spec e do manifesto
│   ├── gerar_ept_pdf.py                         # gera o PDF da EPT (capa, sumário, casos, anexos)
│   ├── gerar_ept_preview.py                     # gera a versão HTML navegável da EPT
│   ├── gerar_pacote.py                          # gera o ZIP de entrega (nomes UTF-8, datas fixas)
│   └── verificar_consistencia.py                # estrutura, manifesto, legibilidade, CRM-SP, duplicidade
├── dist/
│   └── hackatoon_oracle-mediflow-completo.zip   # pacote pronto para download
└── README.md
```

## Como rodar

```bash
python3 -m pip install -r requirements.txt   # pydantic, reportlab, pymupdf, pillow

python3 tests/testar_contrato.py             # 79/79 expected.json válidos e estáveis
python3 tools/verificar_consistencia.py      # estrutura, manifesto, legibilidade, CRM-SP, duplicidade
python3 tools/verificar_epts.py              # EPTs: seções, IDs, fixtures citadas, cobertura das seções
python3 tools/gerar_epts_pdf.py              # docs/epts/EPTs_MediFlow.pdf
python3 tools/gerar_ept.py --check           # EPT consolidada: RF/RN/RNF, 79 fixtures, §16 e as 41 EPTs do plano
```

Para regerar os documentos (só necessário se mudar um caso):

```bash
python3 tools/gerar_fixtures_demo.py
python3 tools/gerar_fixtures_catalogo.py
python3 tools/gerar_mapa_documentos.py
python3 tools/gerar_ept.py                   # EPT: docs/testes/EPT_MediFlow.csv
python3 tools/gerar_ept_pdf.py               # EPT em PDF: docs/testes/EPT_MediFlow.pdf
python3 tools/gerar_ept_preview.py           # EPT navegável: docs/testes/EPT_MediFlow_preview.html
```

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

## Dados

Todos os documentos são **fictícios**: nomes, CRMs, CIDs e resultados não correspondem a pessoa real. Nenhuma credencial ou dado pessoal está no repositório.

Todas as fixtures acontecem no **Hospital Aurora (São Paulo)** — por isso todo CRM é `SP`, e os documentos usam a mesma cidade fictícia. Um CRM de outra UF num hospital paulista seria erro de domínio, não variação de teste: o verificador reprova.

## Equipe

| Nome | Papel |
| --- | --- |
| A definir | Product / Pitch |
| A definir | Agentes e IA |
| A definir | Back-end e OCI |
| A definir | Front-end e QA |

## Licença

A definir.
