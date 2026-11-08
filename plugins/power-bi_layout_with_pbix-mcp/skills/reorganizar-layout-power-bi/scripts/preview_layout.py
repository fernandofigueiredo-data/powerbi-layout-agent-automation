#!/usr/bin/env python3
"""Gera um esquema visual (HTML) do antes e depois a partir dos JSONs de layout.

Uso:
  python preview_layout.py layout_antes.json layout_depois.json saida.html
  python preview_layout.py layout_antes.json saida.html          (só o estado atual)

O pbix-mcp não renderiza páginas. Este esquema desenha cada visual como um
retângulo colorido pela função, com o título, sobre as colunas do grid, e mostra
a nota de layout (0–100) de cada lado, para que o usuário avalie a composição
antes de abrir o Power BI Desktop. As páginas são pareadas pelo nome, não pela
ordem, porque a ordem dos arquivos no .pbix pode mudar ao salvar. Se o JSON do
depois trouxer `decisoes` e `limitacoes` (saída do propor_layout.py), elas
aparecem no fim. Funciona em tema claro e escuro.
"""

import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _grid import grid_padrao  # noqa: E402
from layout_check import analisar, nota_pagina  # noqa: E402

CORES = {
    "identidade": "#1F3A5F", "kpi": "#2E8B8B", "filtro": "#B8901C",
    "tendencia": "#3F6E9E", "comparacao": "#4F7CAC", "secundario": "#7D6BA8",
    "detalhe": "#6F7580", "nota": "#9AA0AA", "navegacao": "#A15C38",
    "container": "#C9D3E0",
}
CSS = """
:root{--bg:#ffffff;--fg:#1d2330;--muted:#5b6474;--page:#F4F6FA;--edge:#9aa3b2;--col:rgba(63,110,158,.10);--card:#f7f8fb}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#14171d;--fg:#e6e9ef;--muted:#9aa3b2;--page:#1f242d;--edge:#4a5262;--col:rgba(120,170,230,.12);--card:#1b1f27}}
:root[data-theme="dark"]{--bg:#14171d;--fg:#e6e9ef;--muted:#9aa3b2;--page:#1f242d;--edge:#4a5262;--col:rgba(120,170,230,.12);--card:#1b1f27}
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,"Segoe UI",Arial,sans-serif;margin:0;padding:24px 16px;background:var(--bg);color:var(--fg)}
main{max-width:1400px;margin:0 auto}h1{font-size:22px;margin:0 0 4px}p.sub{color:var(--muted);margin:0 0 16px}
h2{font-size:17px;margin:28px 0 8px}.row{display:flex;gap:20px;flex-wrap:wrap}
figure{margin:0;flex:1 1 420px;min-width:0;background:var(--card);border-radius:10px;padding:10px}
figcaption{display:flex;justify-content:space-between;font-weight:600;margin:0 0 6px;font-size:14px}
figcaption span{color:var(--muted);font-weight:500}svg{width:100%;height:auto;display:block}
svg text{font-family:system-ui,-apple-system,"Segoe UI",Arial,sans-serif}
.lg{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:var(--muted)}
.lg i{display:inline-block;width:12px;height:12px;margin-right:5px;vertical-align:-1px;border-radius:2px}
.nota{font-size:28px;font-weight:700}.ganho{color:#2E8B57}.perda{color:#B5452F}
.resumo{display:flex;gap:28px;align-items:baseline;margin:12px 0 4px;flex-wrap:wrap}
ul{padding-left:20px;line-height:1.5}li{margin:2px 0}
"""


class Opcoes:
    margin = gutter = base = None
    allow_gap = []


def nota(p):
    _, _, mt = analisar(p, Opcoes)
    return nota_pagina(mt)[0]


def page_svg(p, rotulo, mostrar_grid):
    w, h = p["width"], p["height"]
    partes = [f'<figure><figcaption>{html.escape(rotulo)}<span>nota {nota(p):.0f}/100</span></figcaption>'
              f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(rotulo)}">'
              f'<rect width="{w}" height="{h}" fill="var(--page)" stroke="var(--edge)" stroke-width="2"/>']
    if mostrar_grid and p.get("type", "normal") == "normal":
        g = grid_padrao(w, h, margem=(p.get("grid") or {}).get("margem"),
                        calha=(p.get("grid") or {}).get("calha"), base=(p.get("grid") or {}).get("base"))
        for x in g["x_colunas"]:
            partes.append(f'<rect x="{x}" y="0" width="{g["largura_coluna"]}" height="{h}" fill="var(--col)"/>')
    vis = [v for v in p["visuals"] if not v.get("parent")]
    for v in sorted(vis, key=lambda v: v["width"] * v["height"], reverse=True):
        cor = CORES.get(v.get("role"), "#999")
        opac = "0.45" if v.get("role") == "container" else "0.9"
        partes.append(f'<rect x="{v["x"]}" y="{v["y"]}" width="{v["width"]}" height="{v["height"]}" rx="4" '
                      f'fill="{cor}" fill-opacity="{opac}" stroke="var(--bg)" stroke-width="3"/>')
        fs = max(12, min(26, h / 42)) if v["height"] > 40 else 11
        titulo = str(v.get("title") or v.get("type", ""))
        maxc = max(4, int(v["width"] / (fs * 0.58)) - 2)
        if len(titulo) > maxc:
            titulo = titulo[:maxc - 1] + "…"
        estrela = " ★" if v.get("principal") else ""
        partes.append(f'<text x="{v["x"] + 8}" y="{v["y"] + fs + 4}" font-size="{fs}" fill="#fff">'
                      f'{html.escape(titulo)}{estrela}</text>')
    partes.append("</svg></figure>")
    return "".join(partes)


def media(pages):
    return sum(nota(p) for p in pages) / len(pages) if pages else 0.0


def gerar(antes, depois, saida):
    legenda = "".join(f'<span><i style="background:{c}"></i>{r}</span>' for r, c in CORES.items())
    corpo = ""
    na = media(antes["pages"])
    if depois:
        nd = media(depois["pages"])
        classe = "ganho" if nd >= na else "perda"
        corpo += (f'<div class="resumo"><div>Antes <span class="nota">{na:.0f}</span></div>'
                  f'<div>Depois <span class="nota">{nd:.0f}</span></div>'
                  f'<div class="{classe}">{nd - na:+.0f} pontos</div></div>')
        por_nome = {p["name"]: p for p in depois["pages"]}
    else:
        corpo += f'<div class="resumo"><div>Nota atual <span class="nota">{na:.0f}</span></div></div>'
    for p in antes["pages"]:
        corpo += f'<h2>{html.escape(str(p["name"]))}</h2><div class="row">{page_svg(p, "Antes" if depois else "Atual", False)}'
        if depois:
            d = por_nome.get(p["name"])
            corpo += page_svg(d, "Depois", True) if d else "<p>Página ausente no depois.</p>"
        corpo += "</div>"
    for chave, titulo in (("decisoes", "Decisões"), ("limitacoes", "Limitações")):
        itens = (depois or {}).get(chave) or []
        if itens:
            corpo += f"<h2>{titulo}</h2><ul>" + "".join(f"<li>{html.escape(i)}</li>" for i in itens) + "</ul>"
    doc = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>Layout antes e depois</title><style>{CSS}</style></head><body><main>'
           '<h1>Layout antes e depois</h1>'
           '<p class="sub">Esquema por coordenadas: cada retângulo é um visual, colorido pela função. '
           'As faixas claras no depois são as colunas do grid. Confira o resultado final no Power BI Desktop.</p>'
           f'<div class="lg">{legenda}<span>★ visual principal</span></div>{corpo}</main></body></html>')
    with open(saida, "w", encoding="utf-8") as f:
        f.write(doc)
    print(saida)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivos", nargs="+", help="antes.json [depois.json] saida.html")
    a = ap.parse_args().arquivos
    if len(a) not in (2, 3):
        print(__doc__)
        return 2
    with open(a[0], encoding="utf-8") as f:
        antes = json.load(f)
    depois = None
    if len(a) == 3:
        with open(a[1], encoding="utf-8") as f:
            depois = json.load(f)
    gerar(antes, depois, a[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
