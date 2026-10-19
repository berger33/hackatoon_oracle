# hackatoon_oracle

> Projeto de hackathon construído sobre **Oracle Cloud Infrastructure (OCI)**.

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Cloud](https://img.shields.io/badge/cloud-Oracle%20Cloud-red)
![Docs](https://img.shields.io/badge/docs-dispon%C3%ADveis-blue)

## Sobre o projeto

O **hackatoon_oracle** é uma solução desenvolvida para hackathon com foco em Oracle Cloud Infrastructure. O projeto busca resolver o seguinte problema:

> ✏️ **[Descreva em 1–2 frases o problema que o projeto resolve e para quem.]**

E entrega como solução:

> ✏️ **[Descreva em 1–2 frases como a solução funciona e qual é o principal benefício.]**

## Problema

✏️ **Contexto:** quem sofre com o problema hoje, com que frequência e qual é o custo (tempo, dinheiro, risco) de continuar assim.

- **Público-alvo:** [ex.: pequenas empresas, equipes de operações, estudantes]
- **Dor principal:** [o que hoje é manual, lento ou caro]
- **Soluções atuais:** [como as pessoas resolvem hoje e por que isso não basta]

## Solução

✏️ **Proposta de valor:** [por que esta solução é melhor do que as alternativas].

| Recurso | Descrição |
| --- | --- |
| [Recurso 1] | [O que faz e qual problema resolve] |
| [Recurso 2] | [O que faz e qual problema resolve] |
| [Recurso 3] | [O que faz e qual problema resolve] |

## Arquitetura

```text
┌─────────────┐     HTTPS      ┌─────────────┐      ┌──────────────────────┐
│  Frontend   │ ─────────────► │  API/Backend│ ───► │  Serviços OCI        │
│  (web/app)  │ ◄───────────── │             │      │  (dados, IA, storage)│
└─────────────┘                └─────────────┘      └──────────────────────┘
```

✏️ **Fluxo resumido:** [descreva o caminho de uma requisição, do usuário até o dado/serviço na OCI].

## Serviços OCI previstos

> Marque os serviços que o projeto realmente usa. Os itens abaixo são sugestões comuns em projetos de hackathon.

- [ ] **OCI Generative AI** — [ex.: geração de respostas, resumos ou classificações]
- [ ] **Autonomous Database** — [ex.: persistência dos dados da aplicação]
- [ ] **Object Storage** — [ex.: armazenamento de arquivos e documentos]
- [ ] **Functions** — [ex.: processamento sob demanda]
- [ ] **Container Engine for Kubernetes (OKE)** — [ex.: deploy dos serviços]
- [ ] **API Gateway** — [ex.: exposição e controle das APIs]
- [ ] **Identity and Access Management (IAM)** — [ex.: autenticação e permissões]

## Stack

| Camada | Tecnologia |
| --- | --- |
| Frontend | ✏️ [ex.: React, Next.js] |
| Backend | ✏️ [ex.: Node.js, Python/FastAPI] |
| Banco de dados | ✏️ [ex.: Autonomous Database, PostgreSQL] |
| IA / Dados | ✏️ [ex.: OCI Generative AI, modelos próprios] |
| Infraestrutura | Oracle Cloud Infrastructure (OCI) |

## Como executar

### Pré-requisitos

- [ ] Conta na Oracle Cloud (OCI)
- [ ] Git
- [ ] ✏️ [runtime da stack, ex.: Node.js 20+ / Python 3.12+]
- [ ] ✏️ [Docker, caso o projeto use containers]

### Passos

```bash
# 1. Clone o repositório
git clone https://github.com/berger33/hackatoon_oracle.git
cd hackatoon_oracle

# 2. Configure as variáveis de ambiente
cp .env.example .env
# edite o .env com as credenciais da sua tenancy OCI

# 3. Instale as dependências
✏️ [ex.: npm install / pip install -r requirements.txt]

# 4. Rode a aplicação
✏️ [ex.: npm run dev / uvicorn app:main --reload]
```

> Os comandos acima são um ponto de partida. Atualize esta seção conforme a stack for definida.

### Variáveis de ambiente

| Variável | Descrição | Obrigatória |
| --- | --- | --- |
| `OCI_TENANCY_OCID` | OCID da tenancy | Sim |
| `OCI_USER_OCID` | OCID do usuário | Sim |
| `OCI_FINGERPRINT` | Fingerprint da chave de API | Sim |
| `OCI_PRIVATE_KEY_PATH` | Caminho da chave privada `.pem` | Sim |
| `OCI_REGION` | Região da OCI (ex.: `sa-saopaulo-1`) | Sim |
| `✏️ [OUTRA_VAR]` | [descrição] | [Sim/Não] |

## Estrutura do repositório

```text
.
├── docs/                     # Documentos do projeto
│   ├── README.md             # Índice da documentação
│   └── modelo-documento.md   # Modelo base para novos documentos
├── ✏️ src/                   # Código-fonte (criar quando a stack for definida)
├── .env.example              # Exemplo de variáveis de ambiente (criar)
└── README.md
```

## Roadmap

- [x] Estrutura inicial de documentação
- [ ] Definição do problema e da proposta de valor
- [ ] Protótipo navegável / MVP
- [ ] Integração com os serviços OCI
- [ ] Deploy na OCI
- [ ] Roteiro e ensaio do pitch final

## Equipe

| Nome | Papel | GitHub |
| --- | --- | --- |
| ✏️ [Nome] | [Papel] | [@usuario](https://github.com/usuario) |

## Documentação

- [Índice de documentos](docs/README.md)
- [Modelo de documento](docs/modelo-documento.md)

## Licença

✏️ **A definir.** Adicione um arquivo `LICENSE` na raiz quando a licença for escolhida.
