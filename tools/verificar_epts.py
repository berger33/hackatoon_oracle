#!/usr/bin/env python3
"""Verifica as EPTs de docs/epts/.

Checagens:
  1. Estrutura: as 9 secoes do MODELO_DE_EPT.md, na ordem, sem duplicidade.
  2. Cabecalho: os 8 campos obrigatorios, preenchidos e com ID coerente com o nome do arquivo.
  3. IDs unicos, sem buraco na numeracao de cada familia.
  4. Status em um dos valores controlados.
  5. Fixtures citadas: toda citacao tem de existir no manifest.csv (inclusive
     a notacao com chaves, Matriz_Guia_{Pdf,Texto}).
  6. Cobertura: cada linha da secao 8.2, cada criterio da secao 16, cada
     situacao da secao 12 e cada RNF da secao 14 tem EPT.
  7. Indice: docs/epts/README.md cita todas as EPTs escritas.

Erros sao problemas reais nos arquivos existentes. Avisos marcam o que ainda
esta por escrever — eles desaparecem quando as 41 EPTs existirem.

Uso:
    python3 tools/verificar_epts.py
"""
from __future__ import annotations

import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_EPTS = os.path.join(ROOT, "docs", "epts")
MANIFEST = os.path.join(ROOT, "tests", "fixtures", "manifest.csv")
README = os.path.join(DIR_EPTS, "README.md")

SECOES = [
    "1. Objetivo",
    "2. Pré-condições e ambiente",
    "3. Massa de dados",
    "4. Procedimento",
    "5. Critérios de verificação",
    "6. Resultado esperado de referência",
    "7. Pós-condições e limpeza",
    "8. Registro de execução",
    "9. Pendências que travam o teste",
]

CAMPOS = ["ID", "Título", "Versão", "Origem", "Requisitos",
          "Critérios §16", "Prioridade", "Status"]

STATUS_VALIDOS = {"NAO_EXECUTADO", "EM_EXECUCAO", "PASSOU", "FALHOU", "BLOQUEADO"}
PRIORIDADES = {"Obrigatório", "Recomendado", "Opcional"}

# Fonte de cada caso: ID da EPT -> (secao da especificacao, descricao)
COBERTURA = {
    "decisao (§8.2)": [
        ("EPT-D01", "Urgência/achado crítico"),
        ("EPT-D02", "Score combinado abaixo de 0,85"),
        ("EPT-D03", "Urgência associada a ambiguidade/ilegibilidade/conflito"),
        ("EPT-D04", "Receita de rotina"),
        ("EPT-D05", "Guia de procedimento de rotina"),
        ("EPT-D06", "Laudo, alta ou atestado de rotina"),
        ("EPT-D07", "Tipo desconhecido ou destino não mapeado"),
    ],
    "aceite (§16)": [(f"EPT-A{n:02d}", f"critério {n}") for n in range(1, 16)],
    "erros (§12)": [
        ("EPT-E01", "Formato/campos inválidos"),
        ("EPT-E02", "Documento ilegível ou extração inconclusiva"),
        ("EPT-E03", "Gemini indisponível/timeout"),
        ("EPT-E04", "Resposta Gemini inválida"),
        ("EPT-E05", "Conflito entre dados"),
        ("EPT-E06", "Evento urgente registrado como simulado"),
        ("EPT-E07", "Falha ao registrar alerta simulado"),
        ("EPT-E08", "Falha do OCI ao gravar"),
    ],
    "nao funcionais (§14)": [
        ("EPT-R01", "RNF-01 Precisão"), ("EPT-R02", "RNF-02 Segurança clínica"),
        ("EPT-R03", "RNF-03 Confiabilidade"), ("EPT-R04", "RNF-04 Rastreabilidade"),
        ("EPT-R05", "RNF-05 Custo"), ("EPT-R06", "RNF-06 Formato"),
        ("EPT-R07", "RNF-07 Agilidade"), ("EPT-R08", "RNF-08 Privacidade"),
        ("EPT-R09", "RNF-09 Manutenibilidade"), ("EPT-R10", "RNF-10 Flexibilidade"),
        ("EPT-R11", "RNF-11 Usabilidade"),
    ],
}

BLOCOS = ("Matriz", "Ausencia", "Borda", "Conflito", "Simultaneo",
          "Qualidade", "Validacao", "Escaneado", "Diferencial")
TOKEN = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+(?:_\{[A-Za-z0-9,]+\})?)\b")


class Verificador:
    def __init__(self) -> None:
        self.erros: list[str] = []
        self.avisos: list[str] = []
        self.info: list[str] = []

    def erro(self, onde: str, msg: str) -> None:
        self.erros.append(f"{onde}: {msg}")

    def aviso(self, onde: str, msg: str) -> None:
        self.avisos.append(f"{onde}: {msg}")

    # ------------------------------------------------------------ leitura

    @staticmethod
    def secoes(md: str) -> list[str]:
        return [m.group(1).strip() for m in re.finditer(r"^##\s+(.+?)\s*$", md, re.M)]

    @staticmethod
    def campos_cabecalho(md: str) -> dict:
        dados = {}
        for m in re.finditer(r"^\|\s*\*{0,2}([^*|]+?)\*{0,2}\s*\|\s*(.*?)\s*\|\s*$", md, re.M):
            dados[m.group(1).strip()] = m.group(2).strip()
        return dados

    def fixtures_citadas(self, md: str) -> list[str]:
        """IDs de fixture citados, expandindo a notacao com chaves."""
        achados = []
        for token in TOKEN.findall(md):
            if not token.startswith(BLOCOS):
                continue
            if "{" in token:
                m = re.match(r"^([A-Za-z0-9_]+)_\{([^}]+)\}$", token)
                if m:
                    base, opcoes = m.group(1), m.group(2)
                    for op in opcoes.split(","):
                        achados.append(f"{base}_{op.strip()}")
                    continue
            achados.append(token)
        return achados


def main() -> int:
    v = Verificador()
    paths = sorted(glob.glob(os.path.join(DIR_EPTS, "EPT-*.md")), key=os.path.basename)

    if not paths:
        print("Nenhuma EPT escrita ainda: docs/epts/EPT-*.md não encontrado.")
        return 1

    fixtures = {r["id"] for r in csv.DictReader(open(MANIFEST, encoding="utf-8"))}
    v.info.append(f"{len(fixtures)} fixtures no manifesto")

    vistos: dict[str, str] = {}
    todas_citadas: set[str] = set()

    for path in paths:
        nome = os.path.basename(path)
        md = open(path, encoding="utf-8").read()

        # 1. secoes
        secoes = [s for s in v.secoes(md) if not s.startswith("Modelo")]
        esperado = SECOES
        if secoes != esperado:
            faltando = [s for s in esperado if s not in secoes]
            extras = [s for s in secoes if s not in esperado]
            if faltando:
                v.erro(nome, f"seção(ões) ausente(s): {', '.join(faltando)}")
            if extras:
                v.erro(nome, f"seção(ões) fora do modelo: {', '.join(extras)}")
            if not faltando and not extras:
                v.erro(nome, "seções fora de ordem em relação ao MODELO_DE_EPT.md")

        # 2. cabecalho
        campos = v.campos_cabecalho(md)
        for c in CAMPOS:
            if c not in campos or not campos[c] or campos[c] in ("—", "-", ""):
                v.erro(nome, f"campo obrigatório ausente ou vazio no cabeçalho: {c}")
        ept_id = campos.get("ID", "").strip("` ")
        if not ept_id:
            v.erro(nome, "campo ID vazio")
        elif not nome.startswith(ept_id):
            v.erro(nome, f"ID do cabeçalho ({ept_id}) não casa com o nome do arquivo")
        if ept_id in vistos:
            v.erro(nome, f"ID duplicado: também está em {vistos[ept_id]}")
        vistos[ept_id] = nome

        # 3. status e prioridade
        status = campos.get("Status", "").strip("` ")
        if status and status not in STATUS_VALIDOS:
            v.erro(nome, f"Status inválido: {status!r} (use um de {', '.join(sorted(STATUS_VALIDOS))})")
        prio = campos.get("Prioridade", "")
        if prio and prio not in PRIORIDADES:
            v.erro(nome, f"Prioridade inválida: {prio!r}")

        # 4. registro de execucao preenchido quando ha resultado
        if status in ("PASSOU", "FALHOU", "BLOQUEADO"):
            registro = md.split("## 8. Registro de execução")[-1].split("## 9.")[0]
            linhas = [l for l in registro.splitlines() if l.strip().startswith("|")]
            preenchidas = [l for l in linhas if re.search(r"\|\s*\d{2}/\d{2}/\d{4}\s*\|", l)]
            if not preenchidas:
                v.erro(nome, f"Status {status} exige ao menos uma linha datada no registro de execução")

        # 5. fixtures citadas existem no manifesto
        for fid in v.fixtures_citadas(md):
            todas_citadas.add(fid)
            if fid not in fixtures:
                v.erro(nome, f"fixture citada não existe no manifest.csv: {fid}")

    # 6. numeracao sem buraco por familia
    for familia in ("D", "A", "E", "R"):
        numeros = sorted(int(re.sub(r"\D", "", i)) for i in vistos if re.match(rf"EPT-{familia}\d", i))
        if not numeros:
            continue
        buracos = [n for n in range(1, max(numeros) + 1) if n not in numeros]
        if buracos:
            v.aviso(f"família {familia}",
                    f"numeração com buraco: falta(m) EPT-{familia}"
                    + ", ".join(f"{n:02d}" for n in buracos))

    # 7. cobertura das secoes da especificacao
    for origem, casos in COBERTURA.items():
        faltando = [f"{ept} ({desc})" for ept, desc in casos if ept not in vistos]
        if faltando:
            v.aviso(f"cobertura {origem}", f"{len(faltando)} EPT(s) a escrever: " + "; ".join(faltando))

    # 8. README cita as EPTs escritas
    if os.path.exists(README):
        readme = open(README, encoding="utf-8").read()
        for ept in vistos:
            if ept not in readme:
                v.erro("README.md", f"não cita a EPT escrita {ept}")
    else:
        v.erro("README.md", "índice das EPTs não encontrado")

    # 9. fixtures sem nenhuma EPT (informativo)
    sem_ept = sorted(fixtures - todas_citadas)
    if sem_ept:
        v.aviso("fixtures", f"{len(sem_ept)} fixture(s) ainda não citada(s) por nenhuma EPT")

    # ------------------------------------------------------------- saida
    print("== 1. Arquivos")
    for nome in sorted(vistos.values()):
        print(f"   {nome}")
    print(f"\n== 2. Resumo\n   {len(paths)} EPT(s) escrita(s); "
          f"{len(todas_citadas & fixtures)} fixture(s) citada(s) de {len(fixtures)}")
    print("\n== 3. Erros")
    if v.erros:
        for e in v.erros:
            print(f"   ERRO {e}")
    else:
        print("   nenhum")
    print("\n== 4. Avisos")
    if v.avisos:
        for a in v.avisos:
            print(f"   AVISO {a}")
    else:
        print("   nenhum")
    print(f"\nResultado: {len(v.erros)} erro(s), {len(v.avisos)} aviso(s)")
    return 1 if v.erros else 0


if __name__ == "__main__":
    sys.exit(main())
