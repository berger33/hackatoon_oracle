#!/usr/bin/env python3
"""Aplica a decisão de urgência nos dois PDFs de origem do projeto.

Decisão de 21/10/2026 (brief `Projeto_oracle.pdf` prevalece sobre a EF v1.0):
urgência isolada **não** gera revisão humana — o caso vai para a fila urgente,
com alerta, e termina como PROCESSADO. Revisão humana é consequência de
ambiguidade. O caso das duas filas (urgência + ambiguidade) não muda.

O script edita **somente** os trechos ligados a essa regra, no lugar, na mesma
posição, corpo e cor do original. Nada mais no documento é tocado.

Observações técnicas:
  * As fontes embutidas nos PDFs são subconjuntos sem mapa Unicode: não aceitam
    texto novo. O texto novo vai em Helvetica, que tem exatamente as mesmas
    métricas do Arial e da Liberation Sans usados nos originais — por isso nada
    se desloca. Helvetica só não cobre "•" e "≥"; a edição que conteria "≥"
    foi reescrita ("de 0.85 ou mais") e o marcador "•" da RN-01 é preservado do
    original (o trecho não é apagado, só o que vem depois dele).
  * Caracteres fora da faixa Latin-1 são recusados: virariam "·" no PDF.

Uso:
    python3 tools/atualizar_pdfs_urgencia.py               # gera em dist/
    python3 tools/atualizar_pdfs_urgencia.py --verificar   # só confere
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(ROOT, "dist")
UPLOADS = "/tmp/arena-coding-uploads"

FONTES = {
    "ef": "MediFlow_Especificacao_Funcional_v1.0.pdf",
    "analise": "MediFlow_-_Análise_de_Requisitos_v1.1.pdf",
}

# Cada edição: página (1-based), rect a remover, ponto (x, linha de base),
# corpo, largura máxima disponível e o texto novo.
EDICOES = {
    "ef": [
        # §5.3 — EM_REVISAO: urgência sai da lista do que leva à revisão
        dict(pagina=5, rect=(303.6, 285.6, 534.0, 293.4), ponto=(303.6, 291.5),
             corpo=7.7, limite=533.5,
             novo="A análise terminou, mas encontrou ambiguidade, conflito,"),
        # §8.2 — linha 1 da tabela de decisão: revisão deixa de ser obrigatória
        dict(pagina=9, rect=(303.0, 451.5, 358.5, 459.3), ponto=(303.6, 457.4),
             corpo=7.7, limite=357.6,
             novo="Não"),
        # §8.1 — RN-01 (linha 1 de 2): o "•" e o rótulo "RN-01:" ficam intactos
        dict(pagina=9, rect=(94.45, 240.0, 532.0, 250.0), ponto=(94.45, 247.17),
             corpo=9.3, limite=531.72,
             novo="sem ambiguidade/conflito impeditivo ou score abaixo do limiar, "
                  "encaminhar automaticamente ao"),
        # §8.1 — RN-01 (linha 2 de 2)
        dict(pagina=9, rect=(66.5, 253.6, 532.0, 263.0), ponto=(66.86, 260.67),
             corpo=9.3, limite=531.72,
             novo="destino de rotina do tipo; com urgência, à fila urgente e com alerta."),
        # §15 — decisão 1 (linha 1 de 2)
        dict(pagina=13, rect=(56.5, 628.3, 527.0, 637.6), ponto=(56.9, 635.37),
             corpo=9.3, limite=526.16,
             novo="1. Urgência: encaminhar à fila urgente e registrar alerta simulado; "
                  "com ambiguidade,"),
        # §15 — decisão 1 (linha 2 de 2)
        dict(pagina=13, rect=(70.5, 641.8, 527.0, 651.1), ponto=(70.9, 648.9),
             corpo=9.3, limite=526.16,
             novo="incluir também na fila lógica de revisão. Urgência isolada termina "
                  "como processada, sem revisão humana."),
    ],
    "analise": [
        # §7 — RN-01: urgência sai da condição do caso padrão
        dict(pagina=5, rect=(124.7, 192.7, 524.0, 201.2), ponto=(125.06, 199.15),
             corpo=8.5, limite=523.26,
             novo="Casos padrão (sem ambiguidade e com nota combinada de 0.85 ou mais) "
                  "seguem direto ao destino,"),
        # §12 — situação: de "A definir" para "Decidido"
        dict(pagina=7, rect=(198.4, 516.5, 240.0, 525.0), ponto=(198.8, 523.0),
             corpo=8.5, limite=266.8,
             novo="Decidido"),
        # §12 — detalhe da decisão
        dict(pagina=7, rect=(266.4, 516.5, 523.0, 525.0), ponto=(266.8, 523.0),
             corpo=8.5, limite=522.7,
             novo="Urgência prevalece: alerta sempre; revisão só com ambiguidade."),
    ],
}

#: o que não pode mais existir / o que precisa existir / contagens esperadas
ESPERADO = {
    "ef": {
        "ausente": ["mas encontrou urgência", "Sim, obrigatória",
                    "RN-01: sem urgência, ambiguidade",
                    "1. Urgência com ambiguidade/revisão"],
        "presente": ["A análise terminou, mas encontrou ambiguidade",
                     "sem ambiguidade/conflito impeditivo ou score abaixo do limiar",
                     "destino de rotina do tipo; com urgência, à fila urgente e com alerta.",
                     "1. Urgência: encaminhar à fila urgente e registrar alerta simulado;",
                     "Urgência isolada termina como processada, sem revisão humana."],
        "contagem": {},
    },
    "analise": {
        "ausente": ["sem urgência e com nota combinada",
                    "Sugestão inicial: urgência prevalece"],
        "presente": ["Casos padrão (sem ambiguidade e com nota combinada de 0.85 ou mais)",
                     "Urgência prevalece: alerta sempre; revisão só com ambiguidade."],
        "contagem": {"A definir": 4},     # era 5; a linha da urgência virou "Decidido"
    },
}


def checar_edicoes(chave: str) -> list[str]:
    """Confere largura e caracteres suportados antes de mexer no PDF."""
    problemas = []
    for ed in EDICOES[chave]:
        fora = sorted({c for c in ed["novo"] if ord(c) > 255})
        if fora:
            problemas.append(f"p{ed['pagina']}: Helvetica não tem {fora} "
                             f"→ reescreva o trecho")
        largura = pymupdf.get_text_length(ed["novo"], fontname="helv",
                                          fontsize=ed["corpo"])
        if ed["ponto"][0] + largura > ed["limite"]:
            problemas.append(
                f"p{ed['pagina']}: linha nova tem {largura:.1f}pt e só há "
                f"{ed['limite'] - ed['ponto'][0]:.1f}pt → {ed['novo'][:40]!r}")
    return problemas


def aplicar(caminho_saida: str, chave: str) -> int:
    doc = pymupdf.open(caminho_saida)
    for ed in EDICOES[chave]:
        page = doc[ed["pagina"] - 1]
        page.add_redact_annot(pymupdf.Rect(*ed["rect"]))
        page.apply_redactions()
        page.insert_text(pymupdf.Point(*ed["ponto"]), ed["novo"],
                         fontname="helv", fontsize=ed["corpo"], color=(0, 0, 0))
    tmp = caminho_saida + ".tmp"
    doc.save(tmp, garbage=4, deflate=True)
    doc.close()
    os.replace(tmp, caminho_saida)
    return len(EDICOES[chave])


def verificar(caminho: str, chave: str) -> list[str]:
    doc = pymupdf.open(caminho)
    texto = "\n".join(p.get_text() for p in doc)
    doc.close()
    problemas = []
    for frase in ESPERADO[chave]["ausente"]:
        if frase in texto:
            problemas.append(f"ainda existe: {frase!r}")
    for frase in ESPERADO[chave]["presente"]:
        if frase not in texto:
            problemas.append(f"não foi inserido: {frase!r}")
    for frase, n in ESPERADO[chave]["contagem"].items():
        if texto.count(frase) != n:
            problemas.append(f"{frase!r} aparece {texto.count(frase)}x, esperado {n}")
    return problemas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verificar", action="store_true",
                    help="só confere os PDFs já gerados")
    args = ap.parse_args()

    os.makedirs(SAIDA, exist_ok=True)
    if args.verificar:
        return _verificar_tudo()

    total, ok = 0, True
    for chave, nome in FONTES.items():
        origem = os.path.join(ROOT, nome)
        if not os.path.exists(origem):
            origem = os.path.join(UPLOADS, nome)
        destino = os.path.join(SAIDA, nome)
        shutil.copyfile(origem, destino)          # sempre parte do original
        n = aplicar(destino, chave)
        problemas = checar_edicoes(chave) + verificar(destino, chave)
        total += n
        ok = ok and not problemas
        print(f"{nome}: {n} edição(ões) → {'OK' if not problemas else 'PROBLEMAS'}")
        for p in problemas:
            print("   -", p)
    print(f"\n{total} edições aplicadas no total; saída em {SAIDA}")
    return 0 if ok else 1


def _verificar_tudo() -> int:
    ok = True
    for chave, nome in FONTES.items():
        destino = os.path.join(SAIDA, nome)
        if not os.path.exists(destino):
            print(f"[ERRO] falta {destino}")
            ok = False
            continue
        problemas = verificar(destino, chave)
        ok = ok and not problemas
        print(f"{nome}: {'OK' if not problemas else 'PROBLEMAS'}")
        for p in problemas:
            print("   -", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
