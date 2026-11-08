#!/usr/bin/env python3
"""Calcula o grid, confere o layout e dá uma nota de 0 a 100 às páginas de um relatório Power BI.

Uso:
  python layout_check.py grid --width 1280 --height 720 [--margin 24 --gutter 16 --columns 12]
  python layout_check.py check layout_depois.json [--margin M --gutter G --base U]
                                [--before layout_antes.json] [--allow-gap 32]
  python layout_check.py score layout_depois.json [--before layout_antes.json] [mesmas opções]

Margem, calha e unidade-base omitidas usam o grid padrão de cada página
(proporcional ao tamanho: 1280×720 → 24/16/8; 1920×1080 → 36/24/12; páginas de
dica 320×240 → 12/8/4). Informadas, valem para todas as páginas.

O formato do JSON de layout está em references/pbix-mcp-operacoes.md.

`check`: JSON com erros (violam o contrato da skill) e avisos (desvios das
regras de layout que podem ser aceitos com justificativa). Código de saída 1
quando houver erros.

`score`: nota por página e geral, somando cinco critérios:
  alinhamento (25)  bordas na unidade-base e nas linhas das colunas do grid
  espaco      (20)  margem respeitada e espaçamentos iguais à calha
  integridade (20)  sem sobreposição, sem visual fora da página, empilhados intactos
  hierarquia  (20)  faixas em Z na ordem certa, identidade/KPI no canto, principal no alto
  proporcao   (15)  mesma função com o mesmo tamanho, área cresce com a importância
Com --before, mostra a nota do antes e do depois lado a lado.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _grid import bordas_verticais, grid_padrao  # noqa: E402

TOL = 1.0  # tolerância em px para arredondamentos

RANK = {
    "identidade": 0, "kpi": 0, "filtro": 0,
    "tendencia": 1, "comparacao": 1,
    "detalhe": 2, "secundario": 2,
}
PESOS = {"alinhamento": 25, "espaco": 20, "integridade": 20, "hierarquia": 20, "proporcao": 15}


def grid(args):
    g = grid_padrao(args.width, args.height, colunas=args.columns, margem=args.margin, calha=args.gutter)
    spans = {str(n): n * g["largura_coluna"] + (n - 1) * g["calha"] for n in range(1, args.columns + 1)}
    out = {
        "pagina": [args.width, args.height],
        "unidade_base": g["base"],
        "margem": g["margem"],
        "margem_direita": g["margem_direita"],
        "calha": g["calha"],
        "area_util": g["area_util"],
        "largura_coluna": g["largura_coluna"],
        "colunas": [{"coluna": i + 1, "x": x, "largura": g["largura_coluna"]} for i, x in enumerate(g["x_colunas"])],
        "largura_por_numero_de_colunas": spans,
    }
    if abs(g["largura_coluna_exata"] - g["largura_coluna"]) > 0.01:
        out["aviso"] = (f"A largura exata da coluna seria {g['largura_coluna_exata']} px. Arredondada para "
                        f"{g['largura_coluna']} px, com a sobra na margem direita ({g['margem_direita']} px). "
                        "Para colunas exatas, ajuste margem, calha ou número de colunas.")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def box(v):
    return v["x"], v["y"], v["x"] + v["width"], v["y"] + v["height"]


def overlap(a, b):
    ax0, ay0, ax1, ay1 = box(a)
    bx0, by0, bx1, by1 = box(b)
    return ax0 < bx1 - TOL and bx0 < ax1 - TOL and ay0 < by1 - TOL and by0 < ay1 - TOL


def label(v):
    t = v.get("title") or v.get("type", "?")
    if len(str(t)) > 40:
        t = str(t)[:37] + "..."
    return f"{v.get('id', '?')} ({t})"


def multiplo(valor, base):
    return abs(valor / base - round(valor / base)) * base <= TOL


def config_pagina(p, args):
    g = grid_padrao(p["width"], p["height"], margem=args.margin, calha=args.gutter, base=args.base)
    return g


def analisar(p, args):
    """Confere uma página. Devolve erros, avisos e as métricas usadas na nota."""
    g = config_pagina(p, args)
    m, gt, base = g["margem"], g["calha"], g["base"]
    name = p.get("name", "?")
    W, H = p["width"], p["height"]
    normal = p.get("type", "normal") == "normal"
    errors, warnings = [], []
    mt = {"n": 0, "base_ok": 0, "col_ok": 0, "col_n": 0, "margem_ok": 0,
          "gaps": 0, "gaps_ok": 0, "problemas": 0, "rank_n": 0, "rank_ok": 0,
          "canto": None, "principal": None, "linhas": 0, "linhas_ok": 0,
          "prop_n": 0, "prop_ok": 0}
    # Filhos de grupo seguem o grupo; a conferência olha o primeiro nível.
    vis = [v for v in p.get("visuals", []) if not v.get("parent")]
    content = [v for v in vis if v.get("role") != "container"]
    bordas = bordas_verticais(g)

    for v in vis:
        x0, y0, x1, y1 = box(v)
        if x0 < -TOL or y0 < -TOL or x1 > W + TOL or y1 > H + TOL:
            errors.append(f"[{name}] {label(v)} sai da área da página.")
            mt["problemas"] += 1
        if v.get("role") == "container":
            continue
        mt["n"] += 1
        if v.get("full_bleed"):
            # Faixa de cabeçalho de borda a borda: só confere a altura.
            ok = multiplo(v["height"], base)
            if not ok:
                warnings.append(f"[{name}] {label(v)}: altura {v['height']} não é múltiplo de {base}.")
            mt["base_ok"] += ok
            mt["margem_ok"] += 1
            continue
        if x0 < m - TOL or y0 < m - TOL or x1 > W - g["margem_direita"] + TOL or y1 > H - m + TOL:
            warnings.append(f"[{name}] {label(v)} invade a margem de {m} px.")
        else:
            mt["margem_ok"] += 1
        fora = [k for k in ("x", "y", "width", "height") if not multiplo(v[k], base)]
        if fora:
            k = fora[0]
            warnings.append(f"[{name}] {label(v)}: {k}={v[k]} não é múltiplo de {base}.")
        else:
            mt["base_ok"] += 1
        if normal:
            mt["col_n"] += 1
            if any(abs(x0 - e) <= TOL for e in bordas) and any(abs(x1 - e) <= TOL for e in bordas):
                mt["col_ok"] += 1

    for i, a in enumerate(content):
        for b in content[i + 1:]:
            if a.get("stack") and a.get("stack") == b.get("stack"):
                if box(a) != box(b):
                    errors.append(f"[{name}] {label(a)} e {label(b)} são empilhados de propósito "
                                  "mas têm geometria diferente; a alternância vai quebrar.")
                    mt["problemas"] += 1
                continue
            if overlap(a, b):
                errors.append(f"[{name}] {label(a)} e {label(b)} se sobrepõem.")
                mt["problemas"] += 1

    # Calhas: menor distância até o vizinho à direita e abaixo que compartilham faixa.
    allowed = {gt, *args.allow_gap}
    gaps = []
    slots = {}
    for v in content:
        slots.setdefault(v.get("stack") or id(v), v)
    uniq = list(slots.values())
    for a in uniq:
        ax0, ay0, ax1, ay1 = box(a)
        right = [box(b)[0] - ax1 for b in uniq if b is not a
                 and box(b)[1] < ay1 - TOL and ay0 < box(b)[3] - TOL and box(b)[0] >= ax1 - TOL]
        below = [box(b)[1] - ay1 for b in uniq if b is not a
                 and box(b)[0] < ax1 - TOL and ax0 < box(b)[2] - TOL and box(b)[1] >= ay1 - TOL]
        for gp in (min(right) if right else None, min(below) if below else None):
            if gp is not None:
                gaps.append(round(gp, 1))
    odd = [gp for gp in gaps if all(abs(gp - a) > TOL for a in allowed)]
    mt["gaps"], mt["gaps_ok"] = len(gaps), len(gaps) - len(odd)
    if odd:
        warnings.append(f"[{name}] espaçamentos fora da calha declarada ({sorted(allowed)}): {sorted(set(odd))}.")

    # Mesma função na mesma linha com tamanhos diferentes.
    rows = {}
    for v in uniq:
        if v.get("role") == "kpi":
            rows.setdefault((v["role"], round(v["y"])), []).append(v)
        elif v.get("role") == "filtro":
            # Um filtro da coluna lateral pode começar na mesma altura da faixa sem fazer parte
            # da linha: para filtros, mesma linha é mesmo topo e mesma base.
            rows.setdefault((v["role"], round(v["y"]), round(v["y"] + v["height"])), []).append(v)
    for (role, y, *_), group in rows.items():
        if len(group) < 2:
            continue
        mt["linhas"] += 1
        principal = [v for v in group if v.get("principal")]
        resto = [v for v in group if not v.get("principal")]
        sizes = {(round(v["width"]), round(v["height"])) for v in (resto or group)}
        if len(sizes) > 1:
            warnings.append(f"[{name}] visuais '{role}' na linha y={y} com tamanhos diferentes: {sorted(sizes)}.")
        else:
            mt["linhas_ok"] += 1

    # Proporção: o principal é o maior da sua função; o meio tem área maior que os KPIs.
    area = lambda v: v["width"] * v["height"]  # noqa: E731
    pv = next((v for v in uniq if v.get("principal")), None)
    if pv:
        pares = [v for v in uniq if v.get("role") == pv.get("role") and v is not pv]
        if pares:
            mt["prop_n"] += 1
            mt["prop_ok"] += area(pv) >= max(area(v) for v in pares) - TOL
    kpis = [area(v) for v in uniq if v.get("role") == "kpi"]
    meio = [area(v) for v in uniq if v.get("role") in ("tendencia", "comparacao")]
    if kpis and meio:
        mt["prop_n"] += 1
        mt["prop_ok"] += sum(meio) / len(meio) >= sum(kpis) / len(kpis)

    if not normal:
        return errors, warnings, mt

    # Hierarquia em faixas: nenhum visual começa acima do primeiro visual do nível anterior.
    # Usa o topo mínimo do nível anterior porque um segmentador em lista pode descer
    # pela coluna de filtros sem que isso inverta a ordem de leitura.
    tops = {}
    for v in uniq:
        r = RANK.get(v.get("role"))
        if r is not None:
            tops.setdefault(r, []).append(v)
    for r in (1, 2):
        for v in tops.get(r, []):
            prev = [w for k in range(r) for w in tops.get(k, [])]
            if not prev:
                continue
            mt["rank_n"] += 1
            limit = min(w["y"] for w in prev)
            if v["y"] < limit - TOL:
                warnings.append(f"[{name}] {label(v)} ({v['role']}) está acima de um visual de nível anterior.")
            else:
                mt["rank_ok"] += 1

    # Canto superior esquerdo.
    ranked = [v for v in uniq if v.get("role") in RANK]
    if ranked:
        first = min(ranked, key=lambda v: (v["y"] + v["x"]))
        mt["canto"] = first.get("role") in ("identidade", "kpi")
        if not mt["canto"]:
            warnings.append(f"[{name}] o canto superior esquerdo é ocupado por {label(first)} "
                            f"({first.get('role')}), não por identidade ou KPI.")
        if pv:
            # No quadrante: o centro do visual na metade esquerda e na metade de cima da página.
            cx, cy = pv["x"] + pv["width"] / 2, pv["y"] + pv["height"] / 2
            mt["principal"] = cx <= W / 2 + TOL and cy <= H / 2 + TOL
            if not mt["principal"]:
                warnings.append(f"[{name}] o visual principal {label(pv)} não está no quadrante superior esquerdo.")
    return errors, warnings, mt


def frac(ok, n):
    return 1.0 if n == 0 else ok / n


def nota_pagina(mt):
    al = 0.5 * frac(mt["base_ok"], mt["n"]) + 0.5 * frac(mt["col_ok"], mt["col_n"])
    es = 0.5 * frac(mt["margem_ok"], mt["n"]) + 0.5 * frac(mt["gaps_ok"], mt["gaps"])
    it = max(0.0, 1 - 0.25 * mt["problemas"])
    partes_h = [frac(mt["rank_ok"], mt["rank_n"])]
    if mt["canto"] is not None:
        partes_h.append(1.0 if mt["canto"] else 0.0)
    if mt["principal"] is not None:
        partes_h.append(1.0 if mt["principal"] else 0.0)
    hi = (0.6 * partes_h[0] + 0.4 * sum(partes_h[1:]) / len(partes_h[1:])) if len(partes_h) > 1 else partes_h[0]
    pr = 0.5 * frac(mt["linhas_ok"], mt["linhas"]) + 0.5 * frac(mt["prop_ok"], mt["prop_n"])
    criterios = {"alinhamento": al, "espaco": es, "integridade": it, "hierarquia": hi, "proporcao": pr}
    detalhe = {k: round(PESOS[k] * v, 1) for k, v in criterios.items()}
    return round(sum(detalhe.values()), 1), detalhe


def notas(doc, args):
    paginas = []
    for p in doc["pages"]:
        _, _, mt = analisar(p, args)
        nota, det = nota_pagina(mt)
        paginas.append({"pagina": p.get("name", "?"), "nota": nota, "criterios": det})
    geral = round(sum(x["nota"] for x in paginas) / len(paginas), 1) if paginas else 0.0
    return geral, paginas


def compare(before, after, errors):
    def index(doc):
        return {p.get("name"): {str(v.get("id")): v for v in p.get("visuals", [])} for p in doc["pages"]}
    b, a = index(before), index(after)
    if set(b) != set(a):
        errors.append(f"Páginas diferentes entre antes e depois: {sorted(set(b) ^ set(a))}.")
    pages_b = {p.get("name"): p for p in before["pages"]}
    pages_a = {p.get("name"): p for p in after["pages"]}
    for name in set(b) & set(a):
        if set(b[name]) != set(a[name]):
            errors.append(f"[{name}] visuais diferentes entre antes e depois: {sorted(set(b[name]) ^ set(a[name]))}.")
        for vid in set(b[name]) & set(a[name]):
            if b[name][vid].get("type") != a[name][vid].get("type"):
                errors.append(f"[{name}] o visual {vid} mudou de tipo.")
        for k in ("width", "height", "type"):
            if pages_b[name].get(k) != pages_a[name].get(k):
                errors.append(f"[{name}] a página mudou de {k}.")


def carregar(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def check(args):
    doc = carregar(args.layout)
    errors, warnings = [], []
    for p in doc["pages"]:
        e, w, _ = analisar(p, args)
        errors += e
        warnings += w
    if args.before:
        compare(carregar(args.before), doc, errors)
    print(json.dumps({"erros": errors, "avisos": warnings,
                      "resultado": "ok" if not errors else "falhou"}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


def score(args):
    geral, paginas = notas(carregar(args.layout), args)
    out = {"nota_geral": geral, "paginas": paginas}
    if args.before:
        geral_a, paginas_a = notas(carregar(args.before), args)
        antes = {x["pagina"]: x["nota"] for x in paginas_a}
        out = {"nota_geral": {"antes": geral_a, "depois": geral, "ganho": round(geral - geral_a, 1)},
               "paginas": [dict(x, antes=antes.get(x["pagina"])) for x in paginas]}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grid", help="calcula colunas do grid")
    g.add_argument("--width", type=float, required=True)
    g.add_argument("--height", type=float, required=True)
    g.add_argument("--margin", type=float)
    g.add_argument("--gutter", type=float)
    g.add_argument("--columns", type=int, default=12)
    for nome, ajuda in (("check", "confere um layout"), ("score", "nota de 0 a 100 do layout")):
        c = sub.add_parser(nome, help=ajuda)
        c.add_argument("layout")
        c.add_argument("--margin", type=float)
        c.add_argument("--gutter", type=float)
        c.add_argument("--base", type=float)
        c.add_argument("--before")
        c.add_argument("--allow-gap", type=float, action="append", default=[],
                       help="espaçamento adicional aceito (por exemplo, folga de container)")
    args = ap.parse_args()
    sys.exit({"grid": grid, "check": check, "score": score}[args.cmd](args))


if __name__ == "__main__":
    main()
