#!/usr/bin/env python3
"""Verifica a consistência do catálogo de fixtures do MediFlow.

Checa, para os 67 casos:
  1. estrutura das pastas (4 arquivos funcionais; 2 nos negativos, exceto o PDF
     de 25 MB do Validacao_ArquivoGrande, ignorado pelo Git até ser regerado)
  2. nome da pasta = nome dos arquivos = fixture_id do expected.json
  3. expected.json com o schema `mediflow.fixture/2` e os enums do domínio
     (importados de `app/models.py`, para não haver duas listas)
  4. manifest.csv x expected.json (tipo, status, revisão, notificação, destinos)
  5. arquivos realmente legíveis (PDF abre, JPG abre, TXT tem marca de fictício)
  6. coerência clínica: o que o expected diz ter sido extraído existe mesmo no TXT
     (paciente, médico, CRM, diagnóstico, CID, idade) e todo CRM é da UF do hospital
  7. duplicidade: arquivos byte-idênticos, textos clínicos iguais e saídas idênticas

A validação profunda do payload (ponto fixo das regras) fica em
`tests/testar_contrato.py`.

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
sys.path.insert(0, ROOT)
BASE = os.path.join(ROOT, "tests/fixtures")

from app.models import Destino, NivelPrioridade, StatusTriagem, TipoDocumento  # noqa: E402

TIPOS = {x.value for x in TipoDocumento}
PRIORIDADES = {x.value for x in NivelPrioridade}
STATUS = {x.value for x in StatusTriagem}
DESTINOS = {x.value for x in Destino}
SCHEMA = "mediflow.fixture/2"
#: Nas 10 fixtures de erro não há tipo, destino nem revisão a comparar.
NA = "-"
#: O Hospital Aurora fica em São Paulo: todo médico que assina tem CRM-SP.
#: (Um CRM de outra UF num hospital paulista é erro de domínio, não variação.)
UF_DO_HOSPITAL = "SP"

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
        # Este fixture inclui um PDF válido de 25 MB, explicitamente ignorado
        # pelo Git; a pasta contém expected.json até o gerador ser executado.
        # Quando o PDF existe localmente, continuam sendo esperados 2 arquivos.
        if fid == "Validacao_ArquivoGrande" and f"{fid}.pdf" not in arquivos:
            esperado = 1
        if len(arquivos) != esperado:
            add_erro(f"{kind}/{fid}: {len(arquivos)} arquivos (esperado {esperado}): {arquivos}")
        total[2 if negativo else 4] = total.get(2 if negativo else 4, 0) + 1

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
              f"{total.get(2,0)} negativos (expected.json + entrada; PDF grande opcional)")


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
        if e.get("schema") != SCHEMA:
            add_erro(f"{fid}: schema = {e.get('schema')!r} (esperado {SCHEMA})")
        if not e.get("assercoes"):
            add_erro(f"{fid}: sem asserções")

        tipo_teste = e.get("tipo_de_teste")
        if tipo_teste not in ("funcional", "erro_processamento", "negativo_tecnico"):
            add_erro(f"{fid}: tipo_de_teste inválido {tipo_teste!r}")
        resp = e.get("resposta_esperada") or {}

        if tipo_teste == "negativo_tecnico":
            for k in ("http", "codigo_funcional", "mensagem"):
                if k not in resp:
                    add_erro(f"{fid}: envelope de erro sem {k}")
            if "entrada" not in e or "requisicao" not in e["entrada"]:
                add_erro(f"{fid}: negativo sem 'entrada.requisicao'")
            continue

        c = resp.get("classificacao") or {}
        dec = resp.get("decisao_roteamento") or {}
        if tipo_teste == "funcional":
            if c.get("tipo_documento") not in TIPOS:
                add_erro(f"{fid}: tipo_documento inválido {c.get('tipo_documento')!r}")
            if c.get("nivel_prioridade") not in PRIORIDADES:
                add_erro(f"{fid}: nivel_prioridade inválido {c.get('nivel_prioridade')!r}")
            if resp.get("status") not in STATUS:
                add_erro(f"{fid}: status inválido {resp.get('status')!r}")
            for dest in dec.get("destinos", []):
                if dest not in DESTINOS:
                    add_erro(f"{fid}: destino inválido {dest!r}")
            if not isinstance(dec.get("requer_auditoria_humana"), bool):
                add_erro(f"{fid}: requer_auditoria_humana não é booleano")
        else:  # erro_processamento
            if resp.get("status") != StatusTriagem.ERRO_PROCESSAMENTO.value:
                add_erro(f"{fid}: status de erro esperado ERRO_PROCESSAMENTO")
            erro = resp.get("erro") or {}
            if "codigo" not in erro or "mensagem" not in erro:
                add_erro(f"{fid}: erro de processamento sem código/mensagem")
            if c or resp.get("dados_extraidos"):
                add_erro(f"{fid}: erro de processamento não pode ter dados extraídos")

        for k, rel in (e.get("entrada", {}).get("renditions") or {}).items():
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
        resp = e["resposta_esperada"]

        if e["tipo_de_teste"] == "negativo_tecnico":
            st = r["status_esperado"]
            if str(resp["http"]) not in st:
                add_erro(f"{fid}: HTTP {resp['http']} não bate com '{st}'")
                divergencias += 1
            if resp["codigo_funcional"] not in st:
                add_erro(f"{fid}: código {resp['codigo_funcional']} não bate com '{st}'")
                divergencias += 1
            continue

        if e["tipo_de_teste"] == "erro_processamento":
            if r["status_esperado"] != resp["status"]:
                add_erro(f"{fid}: status manifest={r['status_esperado']} expected={resp['status']}")
                divergencias += 1
            for campo in ("tipo_documento", "destinos_esperados", "revisao_humana"):
                if r[campo] != NA:
                    add_erro(f"{fid}: {campo} deveria ser '{NA}' em caso de erro")
                    divergencias += 1
            continue

        c = resp["classificacao"]
        dec = resp["decisao_roteamento"]
        if r["tipo_documento"] != c["tipo_documento"]:
            add_erro(f"{fid}: tipo manifest={r['tipo_documento']} expected={c['tipo_documento']}")
            divergencias += 1
        if r["status_esperado"] != resp["status"]:
            add_erro(f"{fid}: status manifest={r['status_esperado']} expected={resp['status']}")
            divergencias += 1
        rev = "SIM" if dec["requer_auditoria_humana"] else "NAO"
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


def normaliza(s):
    """Compara texto sem acento, sem caixa e sem espaços repetidos."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def verifica_coerencia_clinica(quiet):
    """O TXT é a fonte dos dados extraídos: o que o expected afirma tem de estar lá."""
    print("\n== 6. Coerência clínica (expected x TXT)")
    conferidos = 0
    for kind, fid, d in pastas():
        e = json.load(open(os.path.join(d, "expected.json"), encoding="utf-8"))
        if e["tipo_de_teste"] != "funcional":
            continue
        txt_path = os.path.join(d, f"{fid}.txt")
        if not os.path.exists(txt_path):
            continue
        bruto = open(txt_path, encoding="utf-8").read()
        txt = normaliza(bruto)
        resp = e["resposta_esperada"]
        dados = resp["dados_extraidos"]
        medico = dados.get("medico") or {}
        crm = medico.get("crm") or {}
        ausentes = set(resp["qualidade"]["campos_ausentes"])
        incertos = set(resp["qualidade"]["campos_incertos"])
        conferidos += 1

        def contem(valor, campo):
            if valor and normaliza(str(valor)) not in txt:
                add_erro(f"{fid}: {campo} esperado ({valor!r}) não aparece no TXT")

        contem((dados.get("paciente") or {}).get("nome"), "paciente.nome")
        contem(medico.get("nome"), "medico.nome")
        contem(dados.get("diagnostico"), "diagnostico")
        contem(dados.get("cid"), "cid")
        if (dados.get("paciente") or {}).get("idade") is not None:
            idade = str(dados["paciente"]["idade"])
            if not re.search(rf"\bidade:\s*{idade}\b", txt):
                add_erro(f"{fid}: idade esperada ({idade}) não aparece no TXT")

        # CRM: número, UF e presença coerentes com o que se espera extrair
        numeros = re.findall(r"crm\s+(\d{4,6})-([a-z]{2})", txt)
        for numero, uf in numeros:
            if not crm.get("numero"):
                if "medico.crm" in ausentes:
                    add_erro(f"{fid}: TXT exibe CRM {numero}-{uf.upper()} mas o expected "
                             f"declara medico.crm ausente")
            elif (numero, uf.upper()) != (str(crm.get("numero")), crm.get("uf")):
                add_erro(f"{fid}: TXT traz CRM {numero}-{uf.upper()}, "
                         f"expected traz {crm.get('numero')}-{crm.get('uf')}")
            if uf.upper() != UF_DO_HOSPITAL:
                add_erro(f"{fid}: CRM {numero}-{uf.upper()} fora da UF do hospital "
                         f"({UF_DO_HOSPITAL})")
        if crm.get("numero") and not any(n == str(crm["numero"]) for n, _ in numeros):
            add_erro(f"{fid}: expected tem CRM {crm.get('numero')}-{crm.get('uf')} "
                     f"que não aparece no TXT")
        if crm.get("uf") and crm.get("uf") != UF_DO_HOSPITAL:
            add_erro(f"{fid}: CRM com UF {crm.get('uf')} (esperado {UF_DO_HOSPITAL})")

        # Idade declarada incerta não pode estar legível no texto
        if "paciente.idade" in incertos:
            m = re.search(r"^idade:\s*(.+)$", bruto, re.M | re.I)
            if m and re.fullmatch(r"\s*\d{1,3}\s*(anos)?\s*", m.group(1)):
                add_erro(f"{fid}: paciente.idade é incerto, mas o TXT mostra "
                         f"{m.group(1).strip()!r} legível")

        # Campo declarado incerto não pode estar legível no texto
        for campo in incertos:
            if campo == "medicamentos[0].dosagem":
                dose = re.search(r"\d[\d.,]*\s*(mg|mcg|g|ml)\b", txt)
                if dose and "mancha" not in txt and "ilegivel" not in txt and "ilegível" not in bruto.lower():
                    add_aviso(f"{fid}: {campo} é incerto, mas o TXT mostra dose legível "
                              f"({dose.group(0)})")
    if not quiet:
        print(f"   {conferidos} casos funcionais conferidos contra o próprio texto")


def verifica_duplicidade(quiet):
    print("\n== 7. Duplicidade e redundância")
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
        resp = e["resposta_esperada"]
        if e["tipo_de_teste"] == "negativo_tecnico":
            chave = ("erro", resp["http"], resp["codigo_funcional"], e["entrada"].get("arquivo"))
        elif e["tipo_de_teste"] == "erro_processamento":
            chave = ("erro_processamento", resp["erro"]["codigo"])
        else:
            c, dec, dd = resp["classificacao"], resp["decisao_roteamento"], resp["dados_extraidos"]
            chave = (c["tipo_documento"], c["nivel_prioridade"], tuple(dec["destinos"]),
                     resp["status"], dec["requer_auditoria_humana"],
                     bool(dec["notificacao"]),
                     (dd.get("paciente") or {}).get("nome"), dd.get("diagnostico"), dd.get("cid"))
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
    verifica_coerencia_clinica(quiet)
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
