# Integração com o repositório do G10

**Repositório analisado:** `No-Country-simulation/g10-brasil-equipe-15_mediflow` (branch `develop`)
**Referência:** EF v1.0 atualizada, Análise de Requisitos v1.1 e `docs/testes/CONTRATO_DE_DADOS.md`
**Data da análise:** 22/10/2026

## Conclusão em uma linha

O **grafo de decisão** está de acordo com os nossos documentos (acertou R1, A1, A3, A4 e A5);
o **contrato de dados** diverge nos nomes dos enums e em três blocos que a resposta da API não
expõe. Nenhuma regra de negócio precisa ser reescrita.

## O que tem aqui

| Arquivo | Para que serve |
| --- | --- |
| [`MAPEAMENTO_DE_CONTRATO.md`](MAPEAMENTO_DE_CONTRATO.md) | Tabela completa nome-delas → nome-canônico, campo a campo, com a citação da regra |
| [`ISSUES_PARA_O_G10.md`](ISSUES_PARA_O_G10.md) | 10 issues prontas para colar no repositório delas, em ordem de prioridade |
| [`cenarios/`](cenarios/) | Os 3 cenários de demonstração delas traduzidos para o nosso contrato |
| `tools/validar_cenarios_g10.py` | Prova que os cenários validam e são ponto fixo das regras |

## Como verificar

```bash
python3 tools/validar_cenarios_g10.py      # 3 cenários válidos e estáveis
python3 tools/validar_cenarios_g10.py -v   # mostra as asserções de cada um
```

## As três prioridades

1. **Enums canônicos** (`Rotina` → `ROTINA`, `Fila_Emergencia_Medica` → `FILA_URGENCIA_MEDICA`…).
   Enquanto isso não mudar, nenhum dos 79 `expected.json` aprovados casa com a resposta da API.
2. **`destinos` em lista + notificação como objeto** na resposta (§8.2 e RF-07).
3. **Alto risco sem texto de urgência → fila urgente** (RN-03) — a única regra de roteamento
   obrigatória que ainda não existe nem no código nem nos testes.

## O que elas fazem melhor que nós

`idade = 0` tratada como presente, deduplicação de conflitos idênticos, validação de `NaN`/`Inf`
no limiar e o marcador `etapa: "DECISAO_CALCULADA"` (o grafo declara que não confirma
persistência — a leitura mais limpa da RF-30 que vimos até agora). Vale trazer para cá.
