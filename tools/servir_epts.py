#!/usr/bin/env python3
"""Preview local das EPTs: serve docs/epts/ como HTML no navegador.

Uso:
    python3 tools/servir_epts.py                # http://0.0.0.0:8000
    python3 tools/servir_epts.py --port 8080

Rotas:
    /                       indice das EPTs (com status, origem e links)
    /doc/<arquivo.md>       documento renderizado em HTML
    /raw/<caminho>          arquivo do repositorio como texto puro
    /pdf                    o PDF consolidado

Depende apenas da biblioteca padrao: nenhum pacote a instalar.
O renderer cobre o subconjunto de Markdown usado no repo: titulos, paragrafos,
listas, tabelas, blocos de codigo, citacoes e linhas horizontais.
"""
from __future__ import annotations

import argparse
import glob
import html
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_EPTS = os.path.join(ROOT, "docs", "epts")
PDF = os.path.join(DIR_EPTS, "EPTs_MediFlow.pdf")

CSS = """
:root{
  --ink:#111827; --muted:#6B7280; --line:#E5E7EB; --soft:#F9FAFB;
  --red:#B42318; --tint:#FEF2F2; --green:#047857; --amber:#B45309; --blue:#1D4ED8;
}
*{box-sizing:border-box}
body{margin:0;font:16px/1.6 "Helvetica Neue",Arial,sans-serif;color:var(--ink);background:#fff}
a{color:var(--blue)}
.wrap{max-width:960px;margin:0 auto;padding:28px 24px 96px}
header.top{border-bottom:1px solid var(--line);background:var(--soft)}
header.top .wrap{padding-top:22px;padding-bottom:18px}
header.top h1{margin:0;font-size:22px;letter-spacing:-.01em}
header.top p{margin:4px 0 0;color:var(--muted);font-size:13px}
nav.crumb{font-size:13px;color:var(--muted);margin-bottom:18px}
nav.crumb a{color:var(--muted)}
h1.doc{font-size:26px;line-height:1.25;margin:0 0 6px}
.meta{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 22px}
.badge{font-size:11.5px;font-weight:700;letter-spacing:.04em;padding:3px 9px;border-radius:999px;
  border:1px solid var(--line);background:#fff;color:var(--muted);text-transform:uppercase}
.badge.nao{background:var(--soft)}
.badge.em{background:#EFF6FF;color:var(--blue);border-color:#BFDBFE}
.badge.passou{background:#ECFDF5;color:var(--green);border-color:#A7F3D0}
.badge.falhou{background:var(--tint);color:var(--red);border-color:#FECDCA}
.badge.bloqueado{background:#FFFBEB;color:var(--amber);border-color:#FDE68A}
h2{font-size:18px;margin:34px 0 10px;padding-top:14px;border-top:1px solid var(--line)}
h3{font-size:15px;margin:24px 0 8px;color:var(--red)}
h2:first-of-type{border-top:0;padding-top:0}
p{margin:0 0 12px}
ul,ol{padding-left:22px;margin:0 0 14px}
li{margin:3px 0}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.86em;
  background:var(--soft);border:1px solid var(--line);border-radius:4px;padding:1px 4px}
pre{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:12px 14px;
  overflow:auto;font-size:12.5px;line-height:1.5}
pre code{background:none;border:0;padding:0}
blockquote{margin:0 0 14px;padding:8px 14px;border-left:3px solid var(--line);color:var(--muted);background:var(--soft)}
table{border-collapse:collapse;width:100%;margin:6px 0 18px;font-size:13.5px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
th{background:var(--ink);color:#fff;font-weight:700;font-size:12.5px}
tr:nth-child(even) td{background:var(--soft)}
hr{border:0;border-top:1px solid var(--line);margin:26px 0}
.cards{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));margin:18px 0 10px}
.card{border:1px solid var(--line);border-radius:10px;padding:14px 16px;background:#fff}
.card:hover{border-color:#9CA3AF}
.card .id{font-weight:700;font-size:13px;color:var(--red);letter-spacing:.02em}
.card .ti{margin:4px 0 8px;font-size:15px;line-height:1.35}
.card .sub{font-size:12px;color:var(--muted)}
.pend{border-left:3px solid var(--line);padding-left:10px;color:var(--muted);font-size:13.5px}
.foot{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted)}
"""


# ------------------------------------------------------------- markdown

def _esc(t: str) -> str:
    return html.escape(t, quote=False)


def _inline(t: str) -> str:
    """`codigo`, **negrito**, *italico* e [texto](url)."""
    out, buf, i = [], "", 0
    while i < len(t):
        if t[i] == "`":
            j = t.find("`", i + 1)
            if j == -1:
                buf += t[i]
                i += 1
                continue
            out.append(_esc(buf) + f"<code>{_esc(t[i + 1:j])}</code>")
            buf, i = "", j + 1
        elif t.startswith("**", i):
            j = t.find("**", i + 2)
            if j == -1:
                buf += t[i]
                i += 1
                continue
            out.append(_esc(buf) + f"<strong>{_esc(t[i + 2:j])}</strong>")
            buf, i = "", j + 2
        elif t[i] == "*":
            j = t.find("*", i + 1)
            if j == -1:
                buf += t[i]
                i += 1
                continue
            out.append(_esc(buf) + f"<em>{_esc(t[i + 1:j])}</em>")
            buf, i = "", j + 1
        elif t[i] == "[":
            m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", t[i:])
            if m:
                rotulo, alvo = m.group(1), m.group(2)
                out.append(_esc(buf))
                out.append(f'<a href="{link_de(alvo)}">{_esc(rotulo)}</a>')
                buf, i = "", i + m.end()
            else:
                buf += t[i]
                i += 1
        else:
            buf += t[i]
            i += 1
    out.append(_esc(buf))
    return "".join(out)


def link_de(alvo: str) -> str:
    """Resolve um link relativo do Markdown para uma rota do preview."""
    if alvo.startswith(("http://", "https://", "#")):
        return alvo
    alvo = alvo.split("#")[0]
    if not alvo:
        return "#"
    if alvo.endswith(".pdf"):
        return "/raw/docs/epts/" + os.path.basename(alvo)
    caminho = os.path.normpath(os.path.join(DIR_EPTS, alvo))
    if os.path.dirname(caminho) == DIR_EPTS and alvo.endswith(".md"):
        return "/doc/" + os.path.basename(caminho)
    rel = os.path.relpath(caminho, ROOT)
    if not rel.startswith(".."):
        return "/raw/" + rel.replace(os.sep, "/")
    return "#"


def _linha_tabela(l: str) -> list[str]:
    l = l.strip()
    if l.startswith("|"):
        l = l[1:]
    if l.endswith("|"):
        l = l[:-1]
    return [c.strip() for c in l.split("|")]


def _sep(l: str) -> bool:
    return bool(re.fullmatch(r"\|[\s:|-]+\|?", l.strip()))


def md_para_html(md: str) -> str:
    linhas = md.splitlines()
    saida: list[str] = []
    i, n = 0, len(linhas)

    while i < n:
        l = linhas[i]
        s = l.strip()

        if not s:
            i += 1
            continue

        if s.startswith("```"):
            i += 1
            buf = []
            while i < n and not linhas[i].strip().startswith("```"):
                buf.append(linhas[i])
                i += 1
            i += 1
            saida.append("<pre><code>" + _esc("\n".join(buf)) + "</code></pre>")
            continue

        if re.fullmatch(r"-{3,}", s):
            saida.append("<hr>")
            i += 1
            continue

        if s.startswith("|"):
            linhas_tab = []
            while i < n and linhas[i].strip().startswith("|"):
                if not _sep(linhas[i]):
                    linhas_tab.append(_linha_tabela(linhas[i]))
                i += 1
            if linhas_tab:
                saida.append("<table><thead><tr>"
                             + "".join(f"<th>{_inline(c)}</th>" for c in linhas_tab[0])
                             + "</tr></thead><tbody>")
                for r in linhas_tab[1:]:
                    saida.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
                saida.append("</tbody></table>")
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            nivel = len(m.group(1))
            saida.append(f"<h{nivel}>{_inline(m.group(2).strip())}</h{nivel}>")
            i += 1
            continue

        if s.startswith(">"):
            buf = []
            while i < n and linhas[i].strip().startswith(">"):
                buf.append(linhas[i].strip().lstrip(">").strip())
                i += 1
            saida.append("<blockquote>" + _inline(" ".join(buf)) + "</blockquote>")
            continue

        if re.match(r"^[-*+]\s+", s):
            itens = []
            while i < n and re.match(r"^[-*+]\s+", linhas[i].strip()):
                itens.append("<li>" + _inline(re.sub(r"^[-*+]\s+", "", linhas[i].strip())) + "</li>")
                i += 1
            saida.append("<ul>" + "".join(itens) + "</ul>")
            continue

        if re.match(r"^\d+[.)]\s+", s):
            itens = []
            while i < n and re.match(r"^\d+[.)]\s+", linhas[i].strip()):
                itens.append("<li>" + _inline(re.sub(r"^\d+[.)]\s+", "", linhas[i].strip())) + "</li>")
                i += 1
            saida.append("<ol>" + "".join(itens) + "</ol>")
            continue

        buf = []
        while i < n and linhas[i].strip() and not re.match(
                r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|\||>|```|-{3,}$)", linhas[i].strip()):
            buf.append(linhas[i].strip())
            i += 1
        saida.append("<p>" + _inline(" ".join(buf)) + "</p>")

    return "\n".join(saida)


# ---------------------------------------------------------------- dados

ORDEM = {"D": 0, "A": 1, "E": 2, "R": 3}


def epts() -> list[str]:
    paths = glob.glob(os.path.join(DIR_EPTS, "EPT-*.md"))
    return sorted(paths, key=lambda p: (
        ORDEM.get(re.findall(r"EPT-([DAER])", os.path.basename(p))[0], 9)
        if re.findall(r"EPT-([DAER])", os.path.basename(p)) else 9,
        os.path.basename(p)))


def cabecalho(md: str) -> dict:
    dados = {}
    for m in re.finditer(r"^\|\s*\*{0,2}([^*|]+?)\*{0,2}\s*\|\s*(.*?)\s*\|\s*$", md, re.M):
        dados[m.group(1).strip()] = m.group(2).strip()
    return dados


def titulo(md: str, padrao: str) -> str:
    for l in md.splitlines():
        if l.startswith("# "):
            return re.sub(r"^EPT-[DAER]\d+\s*—\s*", "", l[2:].strip())
    return padrao


def classe_status(status: str) -> str:
    return {"NAO_EXECUTADO": "nao", "EM_EXECUCAO": "em", "PASSOU": "passou",
            "FALHOU": "falhou", "BLOQUEADO": "bloqueado"}.get(status.upper(), "nao")


def pagina(corpo: str, titulo_pag: str, navio: str = "") -> bytes:
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo_pag)} — MediFlow EPTs</title><style>{CSS}</style></head>
<body><header class="top"><div class="wrap">
<h1>MediFlow — Especificações de Procedimento de Teste</h1>
<p>Hackathon ONE G10 · casos da Especificação Funcional v1.0 · dados fictícios</p>
</div></header><div class="wrap">{navio}{corpo}
<div class="foot">hackatoon_oracle · preview gerado por <code>tools/servir_epts.py</code></div>
</div></body></html>""".encode("utf-8")


def indice() -> bytes:
    docs = epts()
    outros = ["PLANO_DE_EPTS.md", "MODELO_DE_EPT.md"]
    cards = []
    for p in docs:
        md = open(p, encoding="utf-8").read()
        c = cabecalho(md)
        eid = (re.findall(r"EPT-[DAER]\d+", os.path.basename(p)) or ["?"])[0]
        status = c.get("Status", "—").strip("` ")
        cards.append(f"""<a class="card" href="/doc/{os.path.basename(p)}" style="text-decoration:none;color:inherit">
<div class="id">{html.escape(eid)} · {html.escape(c.get('Origem', '—'))[:70]}</div>
<div class="ti">{html.escape(titulo(md, os.path.basename(p)))}</div>
<div class="sub">Prioridade {html.escape(c.get('Prioridade', '—'))} ·
<span class="badge {classe_status(status)}">{html.escape(status)}</span></div></a>""")

    pend = """<p class="pend">41 EPTs planejadas: 7 de decisão (§8.2), 15 de aceite (§16),
    8 de erros (§12) e 11 não funcionais (§14). Escritas agora: <strong>%d</strong>.
    O <a href="/doc/PLANO_DE_EPTS.md">plano</a> traz o inventário completo e as ondas de execução.</p>""" % len(docs)

    pdf = '<p><a href="/pdf">📄 PDF consolidado</a> · <a href="/doc/README.md">índice e matriz de rastreabilidade</a></p>' if os.path.exists(PDF) else ""

    corpo = (f"<h1 class='doc'>EPTs do MediFlow</h1>"
             f"<p>Cada EPT é o procedimento para provar — ou refutar — um caso da especificação funcional.</p>"
             f"{pend}{pdf}<div class='cards'>{''.join(cards)}</div>"
             f"<h2>Documentos de apoio</h2><ul>"
             + "".join(f"<li><a href='/doc/{a}'>{a}</a></li>" for a in outros)
             + "<li><a href='/doc/README.md'>README.md — índice e matriz</a></li>"
             + "<li><a href='/raw/tests/fixtures/manifest.csv'>manifest.csv — 77 fixtures</a></li>"
               "<li><a href='/raw/docs/testes/CONTRATO_DE_DADOS.md'>Contrato de dados</a></li>"
               "<li><a href='/raw/app/models.py'>app/models.py — regras executáveis</a></li>"
               "</ul>")
    return pagina(corpo, "EPTs do MediFlow")


def doc(nome: str) -> bytes | None:
    caminho = os.path.join(DIR_EPTS, os.path.basename(nome))
    if not os.path.exists(caminho) or not caminho.endswith(".md"):
        return None
    md = open(caminho, encoding="utf-8").read()
    c = cabecalho(md)
    status = c.get("Status", "").strip("` ")
    corpo = md_para_html(md)
    badges = ""
    if status:
        badges = (f"<div class='meta'><span class='badge {classe_status(status)}'>{html.escape(status)}</span>"
                  f"<span class='badge'>{html.escape(c.get('Prioridade', '—'))}</span>"
                  f"<span class='badge'>{html.escape(c.get('Versão', 'v1.0'))}</span></div>")
    # insere os badges depois do titulo
    corpo = re.sub(r"(</h1>)", r"\1" + badges, corpo, count=1)
    nav = '<nav class="crumb"><a href="/">EPTs</a> · ' + html.escape(os.path.basename(nome)) + "</nav>"
    return pagina(corpo, os.path.basename(nome), nav)


# ------------------------------------------------------------- servidor

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, corpo: bytes, tipo: str = "text/html; charset=utf-8", codigo: int = 200) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self) -> None:  # noqa: N802
        rota = unquote(urlparse(self.path).path)

        if rota in ("/", "/index.html"):
            self._send(indice())
            return

        if rota == "/pdf":
            if os.path.exists(PDF):
                self._send(open(PDF, "rb").read(), "application/pdf")
            else:
                self._send(b"PDF ainda nao gerado. Rode: python3 tools/gerar_epts_pdf.py",
                           "text/plain; charset=utf-8", 404)
            return

        if rota.startswith("/doc/"):
            pag = doc(rota[len("/doc/"):])
            if pag is None:
                self._send(b"Documento nao encontrado", "text/plain; charset=utf-8", 404)
            else:
                self._send(pag)
            return

        if rota.startswith("/raw/"):
            rel = rota[len("/raw/"):]
            caminho = os.path.normpath(os.path.join(ROOT, rel))
            if caminho.startswith(ROOT) and os.path.isfile(caminho):
                corpo = open(caminho, "rb").read()
                tipo = ("application/pdf" if caminho.endswith(".pdf")
                        else "text/plain; charset=utf-8")
                self._send(corpo, tipo)
            else:
                self._send(b"Arquivo nao encontrado", "text/plain; charset=utf-8", 404)
            return

        self._send(b"Rota desconhecida", "text/plain; charset=utf-8", 404)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


def main() -> int:
    ap = argparse.ArgumentParser(description="Preview das EPTs em HTML.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"EPTs no ar: http://{args.host}:{args.port}/  ({len(epts())} EPTs)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
