#!/usr/bin/env python3
"""Gera a versão navegável da EPT (HTML autocontido) a partir do CSV.

Lê `docs/testes/EPT_MediFlow.csv` e escreve
`docs/testes/EPT_MediFlow_preview.html`: um arquivo único, sem dependência
externa (CSS/JS embutidos, dados em JSON), que abre por duplo clique e também
serve como preview local.

Abas:
  Casos     — tabela filtrável (suíte, cenário, tipo, prioridade, automação) + detalhe do caso
  Cobertura — requisito → casos, fixture → casos, item de aceite §16 → casos
  Como usar — formato do arquivo, dicionário de colunas e ordem de execução

Uso:
    python3 tools/gerar_ept_preview.py
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_EPT = os.path.join(ROOT, "docs/testes/EPT_MediFlow.csv")
MANIFEST = os.path.join(ROOT, "tests/fixtures/manifest.csv")
SAIDA = os.path.join(ROOT, "docs/testes/EPT_MediFlow_preview.html")

HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EPT — MediFlow</title>
<style>
:root{
  --bg:#f6f7f9; --surface:#ffffff; --ink:#16181d; --muted:#5b6270; --line:#e3e6ec;
  --brand:#1f4bd8; --brand-soft:#e8edfd; --alta:#b3261e; --alta-soft:#fdeceb;
  --media:#8a5a00; --media-soft:#fdf3e0; --baixa:#3d6b3d; --baixa-soft:#eaf4ea;
  --radius:12px; --shadow:0 1px 2px rgba(16,24,40,.06),0 8px 24px rgba(16,24,40,.06);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
header{background:var(--surface);border-bottom:1px solid var(--line);padding:22px 28px 0}
.wrap{max-width:1440px;margin:0 auto}
.brandline{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
h1{font-size:21px;margin:0;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:13px}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;
  background:var(--brand-soft);color:var(--brand)}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:12px 16px;min-width:132px;box-shadow:var(--shadow)}
.card b{display:block;font-size:22px;line-height:1.2}
.card span{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
nav{display:flex;gap:4px;margin-top:6px}
nav button{border:0;background:transparent;padding:10px 14px;font:inherit;font-weight:600;
  color:var(--muted);border-bottom:2px solid transparent;cursor:pointer}
nav button[aria-selected=true]{color:var(--brand);border-bottom-color:var(--brand)}
main{padding:22px 28px 64px}
.filters{display:grid;grid-template-columns:minmax(220px,2fr) repeat(4,minmax(130px,1fr));
  gap:10px;margin-bottom:14px}
input,select{font:inherit;padding:9px 11px;border:1px solid var(--line);border-radius:10px;
  background:var(--surface);color:var(--ink);width:100%}
input:focus,select:focus{outline:2px solid var(--brand-soft);border-color:var(--brand)}
.bar{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:0 0 10px;
  color:var(--muted);font-size:13px;flex-wrap:wrap}
button.ghost{border:1px solid var(--line);background:var(--surface);color:var(--ink);
  padding:7px 12px;border-radius:10px;font:inherit;cursor:pointer}
button.ghost:hover{border-color:var(--brand);color:var(--brand)}
.tablewrap{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  overflow:auto;box-shadow:var(--shadow)}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:13.5px}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{position:sticky;top:0;background:#fbfcfd;font-size:11.5px;text-transform:uppercase;
  letter-spacing:.05em;color:var(--muted);z-index:1;white-space:nowrap}
tbody tr{cursor:pointer}
tbody tr:hover{background:#fafbff}
tbody tr.aberta{background:var(--brand-soft)}
td.id{font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
td.req{white-space:nowrap;color:var(--muted);font-size:12.5px}
.tag{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11.5px;font-weight:600;
  white-space:nowrap}
.tag.alta{background:var(--alta-soft);color:var(--alta)}
.tag.media{background:var(--media-soft);color:var(--media)}
.tag.baixa{background:var(--baixa-soft);color:var(--baixa)}
.tag.cen{background:#eef1f6;color:#3d4657}
.tag.auto{background:#f1f0fb;color:#4b3fa8}
.detalhe{padding:0;background:#fbfcff}
.detalhe .inner{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
  gap:16px;padding:16px 18px 20px;border-bottom:1px solid var(--line)}
.detalhe h3{margin:0 0 6px;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;
  color:var(--muted)}
.detalhe p{margin:0}
.detalhe .block{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.detalhe ol{margin:0;padding-left:20px}
.detalhe li{margin-bottom:4px}
.obs{border-left:3px solid var(--media);background:var(--media-soft);padding:10px 12px;border-radius:8px}
.empty{padding:40px;text-align:center;color:var(--muted)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:16px 18px;box-shadow:var(--shadow)}
.panel h2{font-size:15px;margin:0 0 10px}
.krow{display:flex;gap:10px;padding:6px 0;border-bottom:1px dashed var(--line);font-size:13.5px}
.krow:last-child{border-bottom:0}
.krow b{min-width:104px;font-variant-numeric:tabular-nums}
.krow span{color:var(--muted)}
.prose{max-width:900px}
.prose h2{font-size:17px;margin:26px 0 8px}
.prose h2:first-child{margin-top:0}
.prose code{background:#eef1f6;padding:1px 6px;border-radius:6px;font-size:12.5px}
.prose table{font-size:13.5px}
.prose table td,.prose table th{padding:7px 10px}
footer{padding:0 28px 40px;color:var(--muted);font-size:12px;max-width:1440px;margin:0 auto}
.hidden{display:none}
@media (max-width:900px){
  .filters{grid-template-columns:1fr 1fr}
  header,main,footer{padding-left:16px;padding-right:16px}
  th:nth-child(5),td:nth-child(5){display:none}
}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <div class="brandline">
      <h1>EPT — Especificação de Procedimento de Teste</h1>
      <span class="pill">MediFlow</span>
      <span class="sub">Hackathon ONE G10 · Oracle Next Education &amp; Alura</span>
    </div>
    <div class="cards" id="cards"></div>
    <nav role="tablist">
      <button role="tab" aria-selected="true" data-tab="casos">Casos</button>
      <button role="tab" aria-selected="false" data-tab="cobertura">Cobertura</button>
      <button role="tab" aria-selected="false" data-tab="uso">Como usar</button>
    </nav>
  </div>
</header>
<main>
  <section id="tab-casos">
    <div class="filters">
      <input id="busca" type="search" placeholder="Buscar por ID, título, requisito, fixture…">
      <select id="f-suite"></select>
      <select id="f-cenario"></select>
      <select id="f-tipo"></select>
      <select id="f-prio"></select>
      <select id="f-auto"></select>
    </div>
    <div class="bar">
      <span id="contagem"></span>
      <span>
        <button class="ghost" id="limpar">Limpar filtros</button>
        <button class="ghost" id="expandir">Expandir todos</button>
        <a class="ghost" href="EPT_MediFlow.csv" download
           style="text-decoration:none;margin-left:6px">Baixar CSV</a>
      </span>
    </div>
    <div class="tablewrap">
      <table>
        <thead><tr>
          <th>ID</th><th>Suíte</th><th>Requisito</th><th>Prioridade</th>
          <th>Cenário</th><th>Tipo</th><th>Título</th>
        </tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </section>

  <section id="tab-cobertura" class="hidden">
    <div class="grid2">
      <div class="panel"><h2>Requisito → casos</h2><div id="cov-req"></div></div>
      <div class="panel"><h2>Item de aceite (§16) → casos</h2><div id="cov-aceite"></div></div>
      <div class="panel" style="grid-column:1/-1"><h2>Fixture → casos</h2><div id="cov-massa"></div></div>
    </div>
  </section>

  <section id="tab-uso" class="hidden">
    <div class="panel prose">
      <h2>O que é este arquivo</h2>
      <p>Uma linha por caso de teste, com pré-condição, massa, passos numerados, resultado esperado
      verificável, rastreabilidade ao requisito e colunas de execução em branco. A EPT não substitui o
      catálogo de fixtures: ele é a <b>massa</b> citada em <code>MASSA_DE_DADOS</code>.</p>
      <table>
        <tr><th>Artefato</th><th>Responde</th></tr>
        <tr><td><code>CATALOGO_DE_DOCUMENTOS_DE_TESTE.md</code></td><td>O que existe para testar (67 documentos)</td></tr>
        <tr><td><code>CONTRATO_DE_DADOS.md</code> / <code>app/models.py</code></td><td>O que é uma resposta válida</td></tr>
        <tr><td><code>EPT_MediFlow.csv</code></td><td>Como executar e como saber se passou</td></tr>
      </table>
      <h2>Formato</h2>
      <p>CSV com separador <code>;</code>, UTF-8 com BOM, CRLF e uma linha por caso (sem quebra de
      linha dentro da célula). Os passos ficam como <code>1) … 2) …</code> na mesma célula. No Excel:
      <i>Dados → Obter dados → De texto/CSV</i> e escolha ponto e vírgula.</p>
      <h2>Colunas</h2>
      <table id="cols"></table>
      <h2>Ordem de execução recomendada</h2>
      <ol>
        <li><b>CT-001 a CT-012</b> — ingestão e validação: sem isso, nenhum outro caso tem massa válida.</li>
        <li><b>CT-049 a CT-063</b> — decisão e roteamento, com <code>FIXTURE_MODE</code> nos casos de borda.</li>
        <li><b>CT-013 a CT-048</b> — classificação, extração, confiança: o núcleo clínico.</li>
        <li><b>CT-064 a CT-080</b> — erros, persistência e API.</li>
        <li><b>CT-081 a CT-100</b> — interface e requisitos não funcionais, no fechamento.</li>
      </ol>
      <h2>Como registrar a execução</h2>
      <p>Preencha <code>STATUS_EXECUCAO</code> com <code>PASSOU</code>, <code>FALHOU</code>,
      <code>BLOQUEADO</code> ou <code>NAO APLICAVEL</code>; <code>RESULTADO_OBTIDO</code> com o que
      aconteceu (e o valor observado, não “ok”); <code>EVIDENCIA</code> com o caminho do print/log;
      <code>DEFEITO</code> com o ID do bug. Casos com <code>PENDENTE (§15)</code> em observações ficam
      BLOQUEADOS até a definição correspondente.</p>
      <h2>Reprodutibilidade</h2>
      <p>Não edite o CSV à mão: rode <code>python3 tools/gerar_ept.py</code>. O
      <code>--check</code> falha se faltar requisito, fixture ou item de aceite.</p>
    </div>
  </section>
</main>
<footer id="rodape"></footer>

<script>
const DADOS = __DADOS__;
const COLS = __COLUNAS__;
const COV = __COBERTURA__;

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const tagPrio = (p) => `<span class="tag ${p === "Alta" ? "alta" : p === "Média" ? "media" : "baixa"}">${esc(p)}</span>`;

/* ---------- cards ---------- */
const c = DADOS.reduce((a, r) => {
  a.suites.add(r.SUITE); a.tipos.add(r.TIPO_TESTE); a.cenarios.add(r.CENARIO);
  a.auto[r.AUTOMATIZAVEL] = (a.auto[r.AUTOMATIZAVEL] || 0) + 1;
  a.prio[r.PRIORIDADE] = (a.prio[r.PRIORIDADE] || 0) + 1;
  return a;
}, {suites:new Set(), tipos:new Set(), cenarios:new Set(), auto:{}, prio:{}});

$("#cards").innerHTML = [
  [DADOS.length, "casos"],
  [COV.fixtures_total, "fixtures na massa"],
  [c.suites.size, "suítes"],
  [Object.keys(COV.req).length, "requisitos cobertos"],
  [c.prio.Alta || 0, "prioridade alta"],
  [(c.auto.Sim || 0) + " / " + (c.auto.Parcial || 0) + " / " + (c.auto["Não"] || 0), "auto / parcial / manual"],
].map(([v, l]) => `<div class="card"><b>${esc(v)}</b><span>${esc(l)}</span></div>`).join("");

$("#rodape").textContent =
  `Gerado por tools/gerar_ept_preview.py a partir de ${DADOS.length} casos · base: Especificação Funcional v1.0, incluindo o Anexo A (A1–A9) ` +
  `(RF-01…RF-30, RN-01…RN-07, RNF-01…RNF-11, §8.2, §10–§12, §16) + 67 fixtures do manifest.csv. ` +
  `Todos os dados são fictícios.`;

/* ---------- filtros ---------- */
const unicos = (campo) => [...new Set(DADOS.map(r => r[campo]))].sort((a, b) =>
  a.localeCompare(b, "pt-BR"));
function preencher(sel, valores, rotulo) {
  const el = $(sel);
  el.innerHTML = `<option value="">${rotulo}</option>` +
    valores.map(v => `<option>${esc(v)}</option>`).join("");
}
preencher("#f-suite", unicos("SUITE"), "Todas as suítes");
preencher("#f-cenario", unicos("CENARIO"), "Todos os cenários");
preencher("#f-tipo", unicos("TIPO_TESTE"), "Todos os tipos");
preencher("#f-prio", unicos("PRIORIDADE"), "Todas as prioridades");
preencher("#f-auto", unicos("AUTOMATIZAVEL"), "Automação: todas");

const expandidos = new Set();
let filtrados = DADOS.slice();

function linha(r) {
  const aberta = expandidos.has(r.ID_CASO);
  const det = aberta ? `<tr class="detalhe"><td colspan="7">${detalhe(r)}</td></tr>` : "";
  return `<tr class="${aberta ? "aberta" : ""}" data-id="${esc(r.ID_CASO)}">
    <td class="id">${esc(r.ID_CASO)}</td>
    <td>${esc(r.SUITE)}</td>
    <td class="req">${esc(r.ID_REQUISITO || "—")}</td>
    <td>${tagPrio(r.PRIORIDADE)}</td>
    <td><span class="tag cen">${esc(r.CENARIO)}</span></td>
    <td>${esc(r.TIPO_TESTE)}</td>
    <td>${esc(r.TITULO)}</td>
  </tr>${det}`;
}

function detalhe(r) {
  const passos = String(r.PASSOS).split(" | ").map(p =>
    `<li>${esc(p.replace(/^\\d+\\)\\s*/, ""))}</li>`).join("");
  return `<div class="inner">
    <div class="block">
      <h3>Objetivo</h3><p>${esc(r.OBJETIVO)}</p>
      <h3 style="margin-top:12px">Pré-condições</h3><p>${esc(r.PRE_CONDICOES)}</p>
    </div>
    <div class="block">
      <h3>Massa de dados</h3><p>${esc(r.MASSA_DE_DADOS || "—")}</p>
      <h3 style="margin-top:12px">Técnica · automação · ambiente</h3>
      <p>${esc(r.TECNICA)} · <span class="tag auto">${esc(r.AUTOMATIZAVEL)}</span> · ${esc(r.AMBIENTE)}</p>
      <h3 style="margin-top:12px">Rastreabilidade</h3>
      <p>${esc(r.ID_REQUISITO || "—")}${r.REGRAS_NEGOCIO ? " · " + esc(r.REGRAS_NEGOCIO) : ""} · ${esc(r.CRITERIO_DE_ACEITE)}</p>
    </div>
    <div class="block">
      <h3>Passos</h3><ol>${passos}</ol>
    </div>
    <div class="block">
      <h3>Resultado esperado</h3><p>${esc(r.RESULTADO_ESPERADO)}</p>
      <h3 style="margin-top:12px">Pós-condições</h3><p>${esc(r.POS_CONDICOES || "—")}</p>
      ${r.OBSERVACOES ? `<h3 style="margin-top:12px">Observações</h3><div class="obs">${esc(r.OBSERVACOES)}</div>` : ""}
    </div>
  </div>`;
}

function render() {
  const q = $("#busca").value.trim().toLowerCase();
  const fs = $("#f-suite").value, fc = $("#f-cenario").value,
        ft = $("#f-tipo").value, fp = $("#f-prio").value, fa = $("#f-auto").value;
  filtrados = DADOS.filter(r => {
    if (fs && r.SUITE !== fs) return false;
    if (fc && r.CENARIO !== fc) return false;
    if (ft && r.TIPO_TESTE !== ft) return false;
    if (fp && r.PRIORIDADE !== fp) return false;
    if (fa && r.AUTOMATIZAVEL !== fa) return false;
    if (!q) return true;
    return ["ID_CASO","TITULO","OBJETIVO","ID_REQUISITO","REGRAS_NEGOCIO","MASSA_DE_DADOS",
            "SUITE","RESULTADO_ESPERADO","OBSERVACOES"]
      .some(k => String(r[k] || "").toLowerCase().includes(q));
  });
  $("#tbody").innerHTML = filtrados.length
    ? filtrados.map(linha).join("")
    : `<tr><td colspan="7" class="empty">Nenhum caso com esses filtros.</td></tr>`;
  $("#contagem").textContent = `${filtrados.length} de ${DADOS.length} casos`;
}

$("#tbody").addEventListener("click", (e) => {
  const tr = e.target.closest("tr[data-id]");
  if (!tr) return;
  const id = tr.dataset.id;
  expandidos.has(id) ? expandidos.delete(id) : expandidos.add(id);
  render();
});

["#busca","#f-suite","#f-cenario","#f-tipo","#f-prio","#f-auto"]
  .forEach(s => $(s).addEventListener("input", render));
$("#limpar").addEventListener("click", () => {
  ["#busca","#f-suite","#f-cenario","#f-tipo","#f-prio","#f-auto"]
    .forEach(s => { $(s).value = ""; });
  expandidos.clear(); render();
});
$("#expandir").addEventListener("click", () => {
  filtrados.forEach(r => expandidos.add(r.ID_CASO)); render();
});

/* ---------- cobertura ---------- */
function krows(mapa, rotulo) {
  return Object.entries(mapa || {}).map(([k, v]) =>
    `<div class="krow"><b>${esc(rotulo ? rotulo(k) : k)}</b><span>${esc(v.join(", ")) || "—"}</span></div>`
  ).join("") || `<div class="empty">—</div>`;
}
$("#cov-req").innerHTML = krows(COV.req);
$("#cov-aceite").innerHTML = krows(COV.aceite, k => "§16 item " + k);
$("#cov-massa").innerHTML = krows(COV.massa);

$("#cols").innerHTML = `<tr><th>Coluna</th><th>Conteúdo</th></tr>` +
  COLS.map(([c, d]) => `<tr><td><code>${esc(c)}</code></td><td>${esc(d)}</td></tr>`).join("");

/* ---------- abas ---------- */
document.querySelectorAll("nav button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach(b => b.setAttribute("aria-selected",
      String(b === btn)));
    ["casos","cobertura","uso"].forEach(t =>
      $("#tab-" + t).classList.toggle("hidden", t !== btn.dataset.tab));
  });
});

render();
</script>
</body>
</html>
"""

DESCRICAO_COLUNAS = [
    ("ID_CASO", "Identificador único do caso (CT-001…CT-100)."),
    ("SUITE", "Agrupamento funcional: ingestão, classificação, extração, confiança, decisão, persistência, API, interface, não funcionais."),
    ("ID_REQUISITO", "RF/RNF da especificação que o caso verifica."),
    ("REGRAS_NEGOCIO", "RN aplicada; vazio quando não há regra de negócio."),
    ("CENARIO", "Rotina, Urgência, Ambiguidade, Erro ou Transversal."),
    ("TIPO_TESTE", "Funcional, funcional negativo, borda, integração, não funcional, usabilidade ou segurança."),
    ("TECNICA", "Valor limite, partição de equivalência, tabela de decisão, caso de uso, contrato, análise de risco ou inspeção."),
    ("PRIORIDADE", "Alta bloqueia o MVP; Média entra na entrega; Baixa é opcional."),
    ("TITULO", "Uma frase, começando pelo verbo."),
    ("OBJETIVO", "O que a falha do caso provaria."),
    ("PRE_CONDICOES", "Ambiente, configuração e dados necessários."),
    ("MASSA_DE_DADOS", "Fixture(s) do catálogo; aceita curinga (Matriz_Guia_*) e ponto e vírgula."),
    ("PASSOS", "Passos numerados, separados por barra vertical, na mesma célula."),
    ("RESULTADO_ESPERADO", "Asserções objetivas: valores, códigos HTTP e campos do payload."),
    ("POS_CONDICOES", "Estado esperado do ambiente após a execução."),
    ("CRITERIO_DE_ACEITE", "Item de §16 associado ao caso."),
    ("AUTOMATIZAVEL", "Sim, Parcial ou Não."),
    ("AMBIENTE", "API, Interface, Ambos ou Repositório."),
    ("OBSERVACOES", "Cuidados, dependências e pendências (PENDENTE (§15))."),
    ("STATUS_EXECUCAO", "Inicia NAO EXECUTADO; passa a PASSOU, FALHOU, BLOQUEADO ou NAO APLICAVEL."),
    ("RESULTADO_OBTIDO", "O que aconteceu na execução, com valores observados."),
    ("EVIDENCIA", "Caminho do print/log que comprova o resultado."),
    ("DEFEITO", "ID do defeito aberto, quando houver."),
    ("DATA_EXECUCAO", "Data da execução."),
    ("EXECUTOR", "Quem executou."),
]


def main() -> None:
    with open(CSV_EPT, newline="", encoding="utf-8-sig") as f:
        dados = list(csv.DictReader(f, delimiter=";"))

    req: dict[str, list[str]] = defaultdict(list)
    aceite: dict[str, list[str]] = defaultdict(list)
    massa: dict[str, list[str]] = defaultdict(list)
    for r in dados:
        for campo in ("ID_REQUISITO", "REGRAS_NEGOCIO"):
            for tok in str(r[campo]).replace("/", " ").replace(";", " ").split():
                if tok.startswith(("RF-", "RN-", "RNF-")):
                    req[tok.strip("().")].append(r["ID_CASO"])
        for parte in str(r["CRITERIO_DE_ACEITE"]).replace(",", " ").split():
            for tok in parte.split():
                if tok.isdigit():
                    aceite[tok].append(r["ID_CASO"])
        for tok in str(r["MASSA_DE_DADOS"]).split(";"):
            tok = tok.split(" (")[0].strip()
            if tok:
                massa[tok].append(r["ID_CASO"])

    def ordena(m: dict[str, list[str]]) -> dict[str, list[str]]:
        return {k: sorted(set(v)) for k, v in sorted(
            m.items(), key=lambda kv: (kv[0].split("-")[0], int(kv[0].split("-")[1]))
            if "-" in kv[0] and kv[0].split("-")[-1].isdigit() else (99, 0))}

    with open(MANIFEST, newline="", encoding="utf-8") as f:
        total_fixtures = sum(1 for _ in csv.DictReader(f))

    cobertura = {
        "req": ordena(req),
        "aceite": {k: sorted(set(v)) for k, v in sorted(aceite.items(), key=lambda kv: int(kv[0]))},
        "massa": {k: sorted(set(v)) for k, v in sorted(massa.items())},
        "fixtures_total": total_fixtures,
    }

    html = (HTML
            .replace("__DADOS__", json.dumps(dados, ensure_ascii=False))
            .replace("__COLUNAS__", json.dumps(DESCRICAO_COLUNAS, ensure_ascii=False))
            .replace("__COBERTURA__", json.dumps(cobertura, ensure_ascii=False)))

    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Preview: {os.path.relpath(SAIDA, ROOT)} ({len(dados)} casos, "
          f"{len(html)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
