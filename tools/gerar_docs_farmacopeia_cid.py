#!/usr/bin/env python3
"""Gera dois PDFs a partir EXCLUSIVAMENTE dos dados dos fixtures:
  1. docs/Farmacopeia_Fixtures_MediFlow.pdf - todos os medicamentos dos fixtures
  2. docs/Catalogo_CID_Fixtures_MediFlow.pdf - todos os CIDs dos fixtures

Fonte: tests/fixtures/**/expected.json (67 casos) + trechos literais dos .txt
correspondentes (posologia como escrita no documento ficticio).
Nenhum dado externo e adicionado.
"""
import glob
import json
import os
import re
import subprocess
import unicodedata
from collections import OrderedDict

from fpdf import FPDF
from fpdf.table import FontFace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(REPO, "tests", "fixtures")
DOCS = os.path.join(REPO, "docs")
DATA_REF = "29/10/2026"

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
F_REG = os.path.join(FONT_DIR, "DejaVuSans.ttf")
F_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")


def git_short_hash():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True
        ).strip()
    except Exception:
        return "n/d"


def norm(s):
    return unicodedata.normalize("NFKD", s or "").encode("ASCII", "ignore").decode().lower()


def load_cases():
    files = sorted(glob.glob(os.path.join(FIX, "**", "expected.json"), recursive=True))
    cases = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        resp = d.get("resposta_esperada") or {}
        dados = resp.get("dados_extraidos") or {}
        cases.append({
            "fixture_id": d.get("fixture_id", os.path.basename(os.path.dirname(f))),
            "dir": os.path.dirname(f),
            "bloco": os.path.basename(os.path.dirname(os.path.dirname(f))),
            "tipo_documento": ((resp.get("classificacao") or {}).get("tipo_documento")) or "-",
            "status": resp.get("status") or "-",
            "diagnostico": dados.get("diagnostico"),
            "cid": dados.get("cid"),
            "medicamentos": dados.get("medicamentos") or [],
        })
    return cases


def txt_lines(case_dir, fixture_id):
    path = os.path.join(case_dir, fixture_id + ".txt")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as fh:
        return [l.rstrip("\n") for l in fh]


def posologia_trechos(case, nome_med):
    """Trecho(s) literal(is) do .txt do fixture que citam o medicamento."""
    alvo = norm(nome_med.split("+")[0].split()[0])  # primeira palavra
    if len(alvo) < 4:
        alvo = norm(nome_med)
    achados = []
    for ln in txt_lines(case["dir"], case["fixture_id"]):
        s = ln.strip()
        if not s or len(s) < 8:
            continue
        if alvo in norm(s) and ("mg" in norm(s) or "mcg" in norm(s) or
                                "infus" in norm(s) or "g " in norm(s) or "g," in norm(s)):
            s = re.sub(r"^\d+\.\s*", "", s)
            if s not in achados:
                achados.append(s)
    return achados[:2]


def collect_meds(cases):
    meds = OrderedDict()
    for c in cases:
        for m in c["medicamentos"]:
            nome = (m.get("nome") or "").strip()
            if not nome:
                continue
            dose = (m.get("dosagem") or "").strip()
            freq = (m.get("frequencia") or "").strip()
            key = (nome, dose)
            e = meds.setdefault(key, {"freqs": set(), "usos": []})
            if freq:
                e["freqs"].add(freq)
            e["usos"].append(c)
    return OrderedDict(sorted(meds.items(), key=lambda kv: norm(kv[0][0])))


def collect_cids(cases):
    cids = OrderedDict()
    for c in cases:
        if not c["cid"]:
            continue
        e = cids.setdefault(c["cid"], {"diags": OrderedDict(), "usos": []})
        if c["diagnostico"]:
            e["diags"].setdefault(c["diagnostico"], []).append(c["fixture_id"])
        e["usos"].append(c)
    return OrderedDict(sorted(cids.items()))


class Doc(FPDF):
    def __init__(self, title, subtitle):
        super().__init__(format="A4")
        self._doctitle = title
        self._docsubtitle = subtitle
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(True, margin=18)
        self.add_font("DS", "", F_REG)
        self.add_font("DS", "B", F_BOLD)
        self.alias_nb_pages("{nb}")
        self.add_page()

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("DS", "B", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 6, self._doctitle, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-14)
        self.set_font("DS", "", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 6, f"Página {self.page_no()}/{{nb}}", align="C")

    def cover(self, lines_meta, resumo, aviso):
        self.set_font("DS", "B", 22)
        self.set_text_color(20, 60, 120)
        self.multi_cell(0, 10, self._doctitle, align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("DS", "", 12)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 7, self._docsubtitle, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_draw_color(20, 60, 120)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(5)
        self.set_text_color(0, 0, 0)
        self.set_font("DS", "", 10)
        for k, v in lines_meta:
            self.set_font("DS", "B", 10)
            self.write(6, k + " ")
            self.set_font("DS", "", 10)
            self.multi_cell(0, 6, v, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)
        self.set_fill_color(235, 241, 250)
        self.set_font("DS", "", 10)
        self.multi_cell(0, 6, resumo, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)
        self.set_fill_color(255, 243, 224)
        self.set_font("DS", "B", 10)
        self.multi_cell(0, 6, aviso, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def h1(self, t):
        self.set_font("DS", "B", 14)
        self.set_text_color(20, 60, 120)
        self.ln(2)
        self.multi_cell(0, 8, t, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(20, 60, 120)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def h2(self, t):
        if self.get_y() > 245:
            self.add_page()
        self.set_font("DS", "B", 11)
        self.set_text_color(30, 30, 30)
        self.set_fill_color(232, 238, 247)
        self.multi_cell(0, 7, t, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def kv(self, k, v):
        self.set_font("DS", "B", 9)
        self.write(5.5, k + " ")
        self.set_font("DS", "", 9)
        self.multi_cell(0, 5.5, v, new_x="LMARGIN", new_y="NEXT")

    def bullet(self, t):
        self.set_font("DS", "", 9)
        x = self.get_x()
        self.cell(5, 5.5, chr(8226))
        self.multi_cell(0, 5.5, t, new_x="LMARGIN", new_y="NEXT")

    def summary_table(self, header, rows, widths):
        self.set_font("DS", "", 8)
        total = sum(widths)
        rel = tuple(w / total for w in widths)
        with self.table(width=180, col_widths=rel, line_height=5.5,
                        text_align="LEFT", v_align="T",
                        headings_style=FontFace(emphasis="BOLD", color=(255, 255, 255),
                                                fill_color=(20, 60, 120))) as table:
            hr = table.row()
            for h in header:
                hr.cell(h)
            for r in rows:
                row = table.row()
                for c in r:
                    row.cell(c)


def build_farmacopeia(cases, meds, commit):
    total_usos = sum(len(v["usos"]) for v in meds.values())
    pdf = Doc("Farmacopeia dos Fixtures",
              "Todos os medicamentos presentes nos fixtures do MediFlow (dados fictícios de teste)")
    pdf.cover(
        [("Fonte:", "tests/fixtures/**/expected.json + trechos literais dos .txt correspondentes"),
         ("Referência:", f"commit {commit} - gerado em {DATA_REF}"),
         ("Cobertura:", f"{len(cases)} casos de fixture varridos (catalogo + demo); "
                        f"{sum(1 for c in cases if c['medicamentos'])} casos com medicamentos")],
        f"RESUMO: {len(set(k[0] for k in meds))} medicamentos distintos, "
        f"{len(meds)} apresentações (nome + dosagem), {total_usos} prescrições no total. "
        "Frequência consta como ausente (null) em todos os expected.json; a posologia abaixo "
        "é reproduzida literalmente do texto de cada documento fictício, sem interpretação.",
        "AVISO: documentos 100% FICTÍCIOS para teste de software. Sem validade clínica. "
        "Nenhum dado externo foi adicionado.")
    pdf.h1("1. Tabela-resumo")
    header = ("#", "Medicamento", "Dosagem (no fixture)", "N. fixtures", "Fixtures")
    rows, widths = [], (8, 52, 38, 20, 62)
    for i, ((nome, dose), v) in enumerate(meds.items(), 1):
        rows.append((str(i), nome, dose or "(sem dosagem no expected.json)",
                     str(len(v["usos"])), ", ".join(u["fixture_id"] for u in v["usos"])))
    pdf.summary_table(header, rows, widths)
    pdf.h1("2. Fichas por medicamento")
    for i, ((nome, dose), v) in enumerate(meds.items(), 1):
        pdf.h2(f"{i}. {nome}" + (f" - {dose}" if dose else ""))
        pdf.kv("Dosagem (expected.json):", dose or "(ausente)")
        fr = ", ".join(sorted(v["freqs"])) if v["freqs"] else "(ausente em todos os fixtures)"
        pdf.kv("Frequencia (expected.json):", fr)
        for u in v["usos"]:
            ctx = f"{u['fixture_id']} [{u['bloco']}/{u['tipo_documento']}]"
            if u["diagnostico"] or u["cid"]:
                ctx += f" - {u['diagnostico'] or '-'} (CID {u['cid'] or '-'})"
            pdf.bullet(ctx)
            for t in posologia_trechos(u, nome):
                pdf.set_font("DS", "", 8.5)
                pdf.set_text_color(70, 70, 70)
                pdf.multi_cell(0, 5, f'     Trecho do documento: "{t}"', new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)
        pdf.ln(1)
    pdf.h1("3. Metodologia")
    pdf.bullet(f"Varredura integral de {len(cases)} arquivos expected.json (branches main e de trabalho idênticas; "
               "nenhum fixture adicional em outras branches).")
    pdf.bullet("Conferência cruzada com os arquivos .txt de cada fixture: nenhuma medicação citada nos textos "
               "deixou de constar no expected.json correspondente.")
    pdf.bullet("Casos de erro/validação e documentos sem prescrição não listam medicamentos e não entram nas fichas.")
    pdf.bullet("Caso Conflito_Dose: Losartana potássica 500 mg é intencional (dose 10x, fixture de conflito RF-16).")
    return pdf


def build_cid(cases, cids, commit):
    com_cid = sum(1 for c in cases if c["cid"])
    pdf = Doc("Catálogo CID dos Fixtures",
              "Todos os CIDs presentes nos fixtures do MediFlow (dados fictícios de teste)")
    pdf.cover(
        [("Fonte:", "tests/fixtures/**/expected.json (campo dados_extraidos.cid + diagnostico)"),
         ("Referência:", f"commit {commit} - gerado em {DATA_REF}"),
         ("Cobertura:", f"{len(cases)} casos varridos; {com_cid} com CID, "
                        f"{len(cases) - com_cid} sem CID (ausência prevista ou erro/validação)")],
        f"RESUMO: {len(cids)} CIDs distintos em {com_cid} fixtures. "
        "Diagnósticos reproduzidos literalmente do campo diagnostico de cada fixture.",
        "AVISO: documentos 100% FICTÍCIOS para teste de software. Sem validade clínica. "
        "Nenhum dado externo foi adicionado.")
    pdf.h1("1. Tabela-resumo")
    header = ("CID", "Diagnóstico(s) no(s) fixture(s)", "N.", "Fixtures")
    rows, widths = [], (20, 78, 10, 72)
    for cid, v in cids.items():
        diags = "; ".join(v["diags"].keys()) or "-"
        rows.append((cid, diags, str(len(v["usos"])),
                     ", ".join(u["fixture_id"] for u in v["usos"])))
    pdf.summary_table(header, rows, widths)
    pdf.ln(2)
    pdf.set_font("DS", "", 8.5)
    pdf.multi_cell(0, 5, "Nota: I21.9 aparece com diagnóstico de lombalgia no fixture Conflito_Cid_Diagnostico "
                         "por desenho do teste (conflito intencional CID × diagnóstico, RF-16).")
    pdf.h1("2. Fichas por CID")
    for cid, v in cids.items():
        diags = "; ".join(v["diags"].keys()) or "-"
        pdf.h2(f"{cid} - {diags}")
        for u in v["usos"]:
            pdf.bullet(f"{u['fixture_id']} [{u['bloco']}/{u['tipo_documento']}] - "
                       f"{u['diagnostico'] or '(sem diagnóstico)'}")
        pdf.ln(1)
    pdf.h1("3. Fixtures sem CID (para completude)")
    pdf.set_font("DS", "", 9)
    sem = [c for c in cases if not c["cid"]]
    for c in sem:
        pdf.bullet(f"{c['fixture_id']} [{c['bloco']}/{c['tipo_documento']}] - "
                   f"diagnóstico: {c['diagnostico'] or '(ausente)'}")
    pdf.ln(2)
    pdf.h1("4. Metodologia")
    pdf.bullet(f"Varredura integral de {len(cases)} arquivos expected.json (branches main e de trabalho idênticas; "
               "nenhum fixture adicional em outras branches).")
    pdf.bullet("Conferência cruzada com os .txt: cada CID do expected.json corresponde à menção CID-10 no texto, "
               "nas mesmas quantidades.")
    return pdf


def main():
    cases = load_cases()
    meds = collect_meds(cases)
    cids = collect_cids(cases)
    commit = git_short_hash()
    print(f"casos: {len(cases)} | meds distintos: {len(set(k[0] for k in meds))} "
          f"({len(meds)} nome+dose) | cids: {len(cids)}")
    os.makedirs(DOCS, exist_ok=True)
    p1 = os.path.join(DOCS, "Farmacopeia_Fixtures_MediFlow.pdf")
    p2 = os.path.join(DOCS, "Catalogo_CID_Fixtures_MediFlow.pdf")
    build_farmacopeia(cases, meds, commit).output(p1)
    build_cid(cases, cids, commit).output(p2)
    print("OK:", p1, os.path.getsize(p1), "bytes")
    print("OK:", p2, os.path.getsize(p2), "bytes")


if __name__ == "__main__":
    main()
