#!/usr/bin/env python3
"""Verifica a consistência do catálogo de fixtures do MediFlow.

Checa, para os 67 casos:
  1. estrutura das pastas (4 arquivos nos funcionais, 2 nos negativos técnicos)
  2. nome da pasta = nome dos arquivos = fixture_id do expected.json
  3. expected.json válido, com schema mínimo e enums do domínio
  4. manifest.csv x expected.json (tipo, status, revisão, notificação, destinos)
  5. arquivos realmente legíveis (PDF abre, JPG abre, TXT tem marca de fictício)
  6. duplicidade: arquivos byte-idênticos, textos clínicos iguais e saídas idênticas

Uso:
    python3 tools/verificar_consistencia.py           # relatório completo
    python3 tools/verificar_consistencia.py --quiet    # só o resumo e os erros
"""
import csv
import glob
import hashlib
import itertools
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "tests/fixtures")

TIPOS = {"RECEITUARIO_MEDICO", "LAUDO_EXAME_LABORATORIAL", "LAUDO_EXAME_IMAGEM",
         "GUIA_PROCEDIMENTO", "RELATORIO_ALTA_INTERNACAO", "ATESTADO_MEDICO",
         "OUTRO", "NAO_IDENTIFICADO", "N/A"}
PRIORIDADES = {"URGENTE", "ROTINA", "NAO_IDENTIFICADA"}
STATUS = {"PROCESSADO", "EM_REVISAO", "ERRO_PROCESSAMENTO", "ERRO_PERSISTENCIA", "N/A"}
DESTINOS = {"FILA_URGENCIA_MEDICA", "FARMACIA_HOSPITALAR", "AUDITORIA_AUTORIZACOES",
            "PRONTUARIO_ELETRONICO", "FILA_REVISAO_HUMANA", "N/A"}

erros = []
avisos = []
info = {}


def add_erro(msg):
    erros.append(msg)


def add_aviso(msg):
    avisos.append(msg)


def pastas():
    for kind in ("demo", "catalogo"):
        for d in sorted(glob.glob(os.path.join(BASE, kind, "*"))):
            if os.path.isdir(d):
                yield kind, os.path.basename(d), d


def carrega_manifest():
    path = os.path.join(BASE, "manifest.csv")
    with open(path, encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def normaliza_texto(path):
    """Remove cabeçalho, rodapé e o ID para comparar só o conteúdo clínico."""
    t = open(path, encoding="utf-8").read()
    t = re.sub(r"(?m)^Fixture: .*$", "", t)
    t = re.sub(r"(?m)^MediFlow · fixture .*$", "", t)
    t = re.sub(r"(?m)^HOSPITAL AURORA.*$", "", t)
    t = re.sub(r"(?m)^Rede Fictícia.*$", "", t)
    t = re.sub(r"(?m)^=+$", "", t)
    t = re.sub(r"(?m)^-+$", "", t)
    t = re.sub(r"(?m)^DOCUMENTO FICTÍCIO.*$", "", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def verifica_estrutura(manifest, quiet):
    print("\n== 1. Estrutura das pastas")
    total = {4: 0, 2: 0}
    vistos = set()
    for kind, fid, d in pastas():
        if fid in vistos:
            add_erro(f"{fid}: aparece em demo/ e catalogo/ ao mesmo tempo")
        vistos.add(fid)
        arquivos = sorted(os.listdir(d))
        negativo = fid.startswith("Validacao_")
        esperado = 2 if negativo else 4
        if len(arquivos) != esperado:
            add_erro(f"{kind}/{fid}: {len(arquivos)} arquivos (esperado {esperado}): {arquivos}")
        total[esperado] = total.get(esperado, 0) + 1

        if not negativo:
            for suf in (".txt", ".pdf", ".jpg"):
                if f"{fid}{suf}" not in arquivos:
                    add_erro(f"{kind}/{fid}: falta {fid}{suf}")
        if "expected.json" not in arquivos:
            add_erro(f"{kind}/{fid}: falta expected.json")

        for f in arquivos:
            if os.path.getsize(os.path.join(d, f)) == 0 and fid != "Validacao_ArquivoVazio":
                add_erro(f"{kind}/{fid}/{f}: arquivo de 0 bytes")

        if fid not in manifest:
            add_erro(f"{kind}/{fid}: não está no manifest.csv")

    for fid in manifest:
        if fid not in vistos:
            add_erro(f"{fid}: está no manifest.csv mas não tem pasta")
    info["pastas"] = len(vistos)
    info["funcionais"] = total.get(4, 0)
    info["negativos"] = total.get(2, 0)
    if not quiet:
        print(f"   {len(vistos)} pastas · {total.get(4,0)} funcionais (4 arquivos) · "
              f"{total.get(2,0)} negativos (2 arquivos)")


def verifica_expected(manifest, quiet):
    print("\n== 2. expected.json (schema e enums)")
    com_erro = 0
    for kind, fid, d in pastas():
        p = os.path.join(d, "expected.json")
        try:
            e = json.load(open(p, encoding="utf-8"))
        except Exception as ex:  # noqa: BLE001
            add_erro(f"{fid}: expected.json inválido ({ex})")
            com_erro += 1
            continue

        if e.get("fixture_id") != fid:
            add_erro(f"{fid}: fixture_id = {e.get('fixture_id')!r}")

        if "erro_esperado" in e:
            ee = e["erro_esperado"]
            for k in ("http", "codigo_funcional", "mensagem"):
                if k not in ee:
                    add_erro(f"{fid}: envelope de erro sem {k}")
            continue

        for k in ("formatos_disponiveis", "renditions", "classificacao_esperada",
                  "dados_esperados", "decisao_esperada", "assercoes"):
            if k not in e:
                add_erro(f"{fid}: expected sem {k}")

        c = e.get("classificacao_esperada", {})
        dec = e.get("decisao_esperada", {})
        if c.get("tipo_documento") not in TIPOS:
            add_erro(f"{fid}: tipo_documento inválido {c.get('tipo_documento')!r}")
        if c.get("nivel_prioridade") not in PRIORIDADES:
            add_erro(f"{fid}: nivel_prioridade inválido {c.get('nivel_prioridade')!r}")
        if dec.get("status") not in STATUS:
            add_erro(f"{fid}: status inválido {dec.get('status')!r}")
        for dest in dec.get("destinos", []):
            if dest not in DESTINOS:
                add_erro(f"{fid}: destino inválido {dest!r}")
        if not isinstance(dec.get("requer_auditoria_humana"), (bool, type(None))):
            add_erro(f"{fid}: requer_auditoria_humana não é booleano/null")
        if dec.get("status") == "ERRO_PROCESSAMENTO" and dec.get("requer_auditoria_humana") is not None:
            add_aviso(f"{fid}: erro de processamento com revisão definida "
                      f"({dec.get('requer_auditoria_humana')}); o esperado é null")
        if not e.get("assercoes"):
            add_erro(f"{fid}: sem asserções")

        for k, rel in e.get("renditions", {}).items():
            if not os.path.exists(os.path.join(BASE, rel)):
                add_erro(f"{fid}: rendition {k} aponta para arquivo inexistente ({rel})")
    if not quiet:
        print(f"   {info['pastas']} expected.json lidos · {com_erro} inválidos")


def verifica_manifest(manifest, quiet):
    print("\n== 3. manifest.csv x expected.json")
    divergencias = 0
    for kind, fid, d in pastas():
        r = manifest.get(fid)
        if not r:
            continue
        e = json.load(open(os.path.join(d, "expected.json"), encoding="utf-8"))
        if "erro_esperado" in e:
            ee = e["erro_esperado"]
            st = r["status_esperado"]
            if str(ee["http"]) not in st:
                add_erro(f"{fid}: HTTP {ee['http']} não bate com '{st}'")
                divergencias += 1
            codigo = ee["codigo_funcional"].split()[0]
            if codigo not in st:
                add_erro(f"{fid}: código {codigo} não bate com '{st}'")
                divergencias += 1
            continue

        c = e["classificacao_esperada"]
        dec = e["decisao_esperada"]
        if r["tipo_documento"] != c["tipo_documento"]:
            add_erro(f"{fid}: tipo manifest={r['tipo_documento']} expected={c['tipo_documento']}")
            divergencias += 1
        if r["status_esperado"] != dec["status"]:
            add_erro(f"{fid}: status manifest={r['status_esperado']} expected={dec['status']}")
            divergencias += 1
        rev = "SIM" if dec["requer_auditoria_humana"] else "NAO"
        if dec["requer_auditoria_humana"] is None:
            rev = "N/A"
        if r["revisao_humana"] != rev:
            add_erro(f"{fid}: revisão manifest={r['revisao_humana']} expected={rev}")
            divergencias += 1
        notif = "SIM" if dec["notificacao"] else "NAO"
        if r["notificacao"] != notif:
            add_erro(f"{fid}: notificação manifest={r['notificacao']} expected={notif}")
            divergencias += 1
        dests = [x.strip() for x in r["destinos_esperados"].split("+")]
        if sorted(dests) != sorted(dec["destinos"]):
            add_erro(f"{fid}: destinos manifest={dests} expected={dec['destinos']}")
            divergencias += 1
        if not fid.startswith(r["bloco"] + "_"):
            add_erro(f"{fid}: nome da pasta não começa com o bloco '{r['bloco']}'")
            divergencias += 1
    if not quiet:
        print(f"   {len(manifest)} linhas conferidas · {divergencias} divergências")


def verifica_arquivos(quiet):
    print("\n== 4. Legibilidade dos arquivos")
    try:
        import pymupdf
        from PIL import Image
    except ImportError:
        add_aviso("pymupdf/Pillow ausentes: checagem de PDF/JPG limitada ao tamanho")
        return

    tolerados = {"Qualidade_Pdf_ComSenha", "Qualidade_Pdf_Corrompido", "Validacao_ArquivoVazio"}
    sem_texto = []
    for kind, fid, d in pastas():
        for f in os.listdir(d):
            p = os.path.join(d, f)
            if f.endswith(".pdf"):
                try:
                    doc = pymupdf.open(p)
                    paginas = doc.page_count
                    chars = sum(len(pg.get_text().strip()) for pg in doc)
                    doc.close()
                except Exception:  # noqa: BLE001
                    if fid not in tolerados:
                        add_erro(f"{fid}/{f}: PDF não abre")
                    continue
                if paginas == 0 and fid != "Qualidade_Pdf_Corrompido":
                    add_erro(f"{fid}/{f}: PDF sem páginas")
                if chars == 0:
                    sem_texto.append(f"{fid}/{f}")
            elif f.lower().endswith(".jpg"):
                try:
                    Image.open(p).verify()
                except Exception:  # noqa: BLE001
                    add_erro(f"{fid}/{f}: imagem inválida")
            elif f.endswith(".txt"):
                t = open(p, encoding="utf-8").read()
                if "DOCUMENTO FICTÍCIO" not in t:
                    add_erro(f"{fid}/{f}: texto sem marca de documento fictício")
                if f"Fixture: {fid}" not in t:
                    add_erro(f"{fid}/{f}: texto não identifica a fixture")
    info["pdfs_sem_texto"] = sem_texto
    if not quiet:
        print(f"   {len(sem_texto)} PDFs sem camada de texto (esperado nos blocos "
              f"Escaneado, Qualidade e Matriz_NaoIdentificado)")


def verifica_duplicidade(quiet):
    print("\n== 5. Duplicidade e redundância")
    arquivos = sorted(p for p in glob.glob(os.path.join(BASE, "*/*/*")) if os.path.isfile(p))
    hashes = {}
    for p in arquivos:
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        hashes.setdefault(h, []).append(p)
    identicos = [v for v in hashes.values() if len(v) > 1]
    for grupo in identicos:
        add_erro("arquivos byte-idênticos: " + ", ".join(
            os.path.relpath(p, BASE) for p in grupo))

    # textos clínicos iguais (ignorando cabeçalho/rodapé/ID)
    textos = {}
    for kind, fid, d in pastas():
        p = os.path.join(d, f"{fid}.txt")
        if os.path.exists(p):
            textos[fid] = normaliza_texto(p)
    iguais = {}
    for fid, t in textos.items():
        iguais.setdefault(hashlib.sha256(t.encode()).hexdigest(), []).append(fid)
    for grupo in iguais.values():
        if len(grupo) > 1:
            add_erro("textos clínicos idênticos: " + ", ".join(grupo))

    # saídas idênticas: mesmo tipo, prioridade, destinos, status, revisão, notificação
    # e mesmos dados extraídos (inclusive paciente)
    saidas = {}
    for kind, fid, d in pastas():
        e = json.load(open(os.path.join(d, "expected.json"), encoding="utf-8"))
        if "erro_esperado" in e:
            ee = e["erro_esperado"]
            chave = ("erro", ee["http"], ee["codigo_funcional"], e.get("arquivo"))
        else:
            c, dec, dd = e["classificacao_esperada"], e["decisao_esperada"], e["dados_esperados"]
            chave = (c["tipo_documento"], c["nivel_prioridade"], tuple(dec["destinos"]),
                     dec["status"], dec["requer_auditoria_humana"], dec["notificacao"],
                     dd.get("paciente", {}).get("nome"), dd.get("diagnostico"), dd.get("cid"))
        saidas.setdefault(chave, []).append(fid)
    iguais_saida = [v for v in saidas.values() if len(v) > 1]

    info["saidas_repetidas"] = iguais_saida
    if not quiet:
        print(f"   {len(arquivos)} arquivos · {len(identicos)} grupos byte-idênticos · "
              f"{sum(len(v) for v in iguais.values() if len(v) > 1)} textos repetidos · "
              f"{len(iguais_saida)} grupos com a mesma saída esperada")
        for grupo in iguais_saida:
            print("     mesma saída: " + ", ".join(grupo))


def main():
    quiet = "--quiet" in sys.argv
    print("Consistência do catálogo de fixtures do MediFlow")
    print(f"Raiz: {BASE}")
    manifest = carrega_manifest()
    verifica_estrutura(manifest, quiet)
    verifica_expected(manifest, quiet)
    verifica_manifest(manifest, quiet)
    verifica_arquivos(quiet)
    verifica_duplicidade(quiet)

    print("\n== Resumo")
    print(f"   pastas: {info.get('pastas')} "
          f"({info.get('funcionais')} funcionais + {info.get('negativos')} negativos)")
    print(f"   erros: {len(erros)}")
    print(f"   avisos: {len(avisos)}")
    for e in erros:
        print("   ERRO  -", e)
    for a in avisos:
        print("   AVISO -", a)
    if not erros:
        print("\nEstrutura consistente.")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
