#!/usr/bin/env python3
"""Lê um .pbix (só leitura) e gera o inventário de layout com funções sugeridas.

Uso:
  python inventario_pbix.py relatorio.pbix --saida layout_antes.json

Abre o arquivo como zip e não grava nada nele. Cobre os dois formatos:
- PBIR (Report/definition/pages/<página>/page.json e visuals/<visual>/visual.json)
- legado (Report/Layout, JSON em UTF-16 LE)

Para cada visual registra id (nome interno), tipo, título, campos, posição
absoluta (filhos de grupo já convertidos), grupo, estado oculto e, em
segmentadores, o modo (Dropdown ou Basic). Também sugere a função (`role`) a
partir do tipo e da posição, e marca como `principal` o primeiro KPI na ordem de
leitura. As sugestões ficam marcadas em `role_sugerido: true`: quem conduz a
reorganização confere e corrige antes de rodar o motor de layout.

O formato de saída é o de references/pbix-mcp-operacoes.md.
"""

import argparse
import json
import sys
import zipfile

ROLES_POR_TIPO = {
    "card": "kpi", "cardVisual": "kpi", "multiRowCard": "kpi", "kpi": "kpi", "gauge": "kpi",
    "slicer": "filtro", "advancedSlicerVisual": "filtro", "listSlicer": "filtro", "textSlicer": "filtro",
    "lineChart": "tendencia", "areaChart": "tendencia", "stackedAreaChart": "tendencia",
    "lineClusteredColumnComboChart": "tendencia", "lineStackedColumnComboChart": "tendencia",
    "ribbonChart": "tendencia",
    "clusteredBarChart": "comparacao", "clusteredColumnChart": "comparacao", "barChart": "comparacao",
    "columnChart": "comparacao", "stackedBarChart": "comparacao", "stackedColumnChart": "comparacao",
    "hundredPercentStackedBarChart": "comparacao", "hundredPercentStackedColumnChart": "comparacao",
    "tableEx": "detalhe", "pivotTable": "detalhe", "table": "detalhe", "matrix": "detalhe",
    "actionButton": "navegacao", "pageNavigator": "navegacao", "bookmarkNavigator": "navegacao",
}


def load_json(raw):
    for enc in ("utf-8-sig", "utf-16-le", "utf-16"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return None


def literal(prop):
    """Extrai o valor de {'expr': {'Literal': {'Value': "'texto'"}}}."""
    try:
        v = prop["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return None
    if isinstance(v, str) and len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1]
    return v


def first_prop(objs, objeto, prop):
    for item in (objs or {}).get(objeto, []) or []:
        val = literal((item.get("properties") or {}).get(prop))
        if val is not None:
            return val
    return None


def campos_pbir(query):
    out = []
    for bucket in ((query or {}).get("queryState") or {}).values():
        for pr in bucket.get("projections", []):
            ref = pr.get("queryRef") or pr.get("nativeQueryRef")
            if ref:
                out.append(ref)
    return out


def campos_legado(sv):
    out = []
    for sel in ((sv.get("prototypeQuery") or {}).get("Select") or []):
        if sel.get("Name"):
            out.append(sel["Name"])
    if not out:
        for lst in (sv.get("projections") or {}).values():
            out += [p.get("queryRef") for p in lst if p.get("queryRef")]
    return out


def tipo_pagina_pbir(page):
    t = str(page.get("type", "")).lower()
    if "tooltip" in t:
        return "tooltip"
    if str((page.get("pageBinding") or {}).get("type", "")).lower() == "drillthrough":
        return "drillthrough"
    if (page.get("width"), page.get("height")) == (320, 240):
        return "tooltip"
    return "normal"


def tipo_pagina_legado(sec, cfg):
    t = cfg.get("type")
    if t == 1 or (sec.get("width"), sec.get("height")) == (320, 240):
        return "tooltip"
    if cfg.get("pageBinding", {}).get("type") in ("Drillthrough", 1):
        return "drillthrough"
    for f in load_json(sec.get("filters", "[]").encode()) or []:
        if f.get("howCreated") == 5:
            return "drillthrough"
    return "normal"


def ler_pbir(z, nomes):
    base = "Report/definition/pages/"
    ordem = []
    if base + "pages.json" in nomes:
        ordem = (load_json(z.read(base + "pages.json")) or {}).get("pageOrder", [])
    pastas = sorted({n[len(base):].split("/")[0] for n in nomes
                     if n.startswith(base) and n.endswith("/page.json")})
    pastas = [p for p in ordem if p in pastas] + [p for p in pastas if p not in ordem]
    pages = []
    for pasta in pastas:
        page = load_json(z.read(f"{base}{pasta}/page.json")) or {}
        brutos = {}
        prefixo = f"{base}{pasta}/visuals/"
        for n in nomes:
            if n.startswith(prefixo) and n.endswith("/visual.json"):
                d = load_json(z.read(n)) or {}
                brutos[d.get("name") or n.split("/")[-2]] = d
        visuals = []
        for vid, d in brutos.items():
            pos = d.get("position") or {}
            vis = d.get("visual") or {}
            grupo = d.get("visualGroup")
            v = {
                "id": vid,
                "type": "group" if grupo is not None else vis.get("visualType", "?"),
                "x": pos.get("x", 0), "y": pos.get("y", 0),
                "width": pos.get("width", 0), "height": pos.get("height", 0),
                "z": pos.get("z"),
            }
            titulo = first_prop(vis.get("visualContainerObjects"), "title", "text")
            if grupo is not None:
                titulo = grupo.get("displayName") or titulo
                v["is_group"] = True
            if titulo:
                v["title"] = titulo
            campos = campos_pbir(vis.get("query"))
            if campos:
                v["fields"] = campos
            if v["type"] in ("slicer", "advancedSlicerVisual", "listSlicer"):
                modo = first_prop(vis.get("objects"), "data", "mode")
                v["slicer_mode"] = modo or "Basic"
                if campos:
                    v["field"] = campos[0]
            if d.get("parentGroupName"):
                v["parent"] = d["parentGroupName"]
            if d.get("isHidden"):
                v["hidden"] = True
            visuals.append(v)
        pages.append({
            "name": page.get("displayName", pasta),
            "internal_name": pasta,
            "type": tipo_pagina_pbir(page),
            "hidden": page.get("visibility") == "HiddenInViewMode",
            "width": page.get("width", 1280), "height": page.get("height", 720),
            "visuals": visuals,
        })
    return "PBIR", pages


def ler_legado(z):
    layout = load_json(z.read("Report/Layout")) or {}
    secs = sorted(layout.get("sections", []), key=lambda s: s.get("ordinal", 0))
    pages = []
    for sec in secs:
        cfg = load_json((sec.get("config") or "{}").encode()) or {}
        visuals = []
        for vc in sec.get("visualContainers", []):
            c = load_json((vc.get("config") or "{}").encode()) if isinstance(vc.get("config"), str) else (vc.get("config") or {})
            c = c or {}
            sv = c.get("singleVisual") or {}
            grupo = c.get("singleVisualGroup")
            v = {
                "id": c.get("name", "?"),
                "type": "group" if grupo is not None else sv.get("visualType", "?"),
                "x": vc.get("x", 0), "y": vc.get("y", 0),
                "width": vc.get("width", 0), "height": vc.get("height", 0),
                "z": vc.get("z"),
            }
            titulo = first_prop(sv.get("vcObjects"), "title", "text")
            if grupo is not None:
                titulo = grupo.get("displayName") or titulo
                v["is_group"] = True
            if titulo:
                v["title"] = titulo
            campos = campos_legado(sv)
            if campos:
                v["fields"] = campos
            if v["type"] in ("slicer", "advancedSlicerVisual", "listSlicer"):
                v["slicer_mode"] = first_prop(sv.get("objects"), "data", "mode") or "Basic"
                if campos:
                    v["field"] = campos[0]
            if c.get("parentGroupName"):
                v["parent"] = c["parentGroupName"]
            if sv.get("display", {}).get("mode") == "hidden":
                v["hidden"] = True
            visuals.append(v)
        pages.append({
            "name": sec.get("displayName", sec.get("name")),
            "internal_name": sec.get("name"),
            "type": tipo_pagina_legado(sec, cfg),
            "hidden": cfg.get("visibility") == 1,
            "width": sec.get("width", 1280), "height": sec.get("height", 720),
            "visuals": visuals,
        })
    return "legado", pages


def absolutizar(page):
    """Converte coordenadas de filhos de grupo (relativas) em absolutas."""
    por_id = {v["id"]: v for v in page["visuals"]}

    def offset(v, visto=()):
        pai = por_id.get(v.get("parent"))
        if not pai or pai["id"] in visto:
            return 0, 0
        ox, oy = offset(pai, visto + (v["id"],))
        return pai["x"] + ox, pai["y"] + oy

    desl = {v["id"]: offset(v) for v in page["visuals"]}
    for v in page["visuals"]:
        ox, oy = desl[v["id"]]
        if v.get("parent"):
            v["rel_x"], v["rel_y"] = v["x"], v["y"]
        v["x"] += ox
        v["y"] += oy


def contem(a, b):
    cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    return a["x"] <= cx <= a["x"] + a["width"] and a["y"] <= cy <= a["y"] + a["height"]


def sugerir_roles(page):
    W, H = page["width"], page["height"]
    vis = page["visuals"]
    for v in vis:
        if v.get("role"):
            continue
        t = v["type"]
        role = ROLES_POR_TIPO.get(t)
        if t == "group":
            filhos = [f for f in vis if f.get("parent") == v["id"]]
            tipos = {ROLES_POR_TIPO.get(f["type"]) for f in filhos} - {None}
            role = tipos.pop() if len(tipos) == 1 else "secundario"
        elif t == "textbox":
            if v["y"] < 0.15 * H:
                role = "identidade"
                if v["width"] >= 0.95 * W and v["y"] <= 8:
                    v["full_bleed"] = True
            else:
                role = "nota"
        elif t == "image":
            role = "identidade" if v["y"] < 0.15 * H and v["x"] < 0.3 * W else "secundario"
        elif t in ("shape", "basicShape"):
            dentro = [o for o in vis if o is not v and o["type"] not in ("shape", "basicShape") and contem(v, o)]
            role = "container" if dentro else "secundario"
        if role is None:
            role = "secundario"
        v["role"] = role
        v["role_sugerido"] = True
    kpis = sorted((v for v in vis if v["role"] == "kpi" and not v.get("parent")),
                  key=lambda v: (round(v["y"] / 40), v["x"]))
    if kpis and not any(v.get("principal") for v in vis):
        kpis[0]["principal"] = True
        kpis[0]["principal_sugerido"] = True
    # Visuais com a mesma geometria exata costumam alternar por bookmark.
    geo = {}
    for v in vis:
        if v.get("parent"):
            continue
        geo.setdefault((v["x"], v["y"], v["width"], v["height"]), []).append(v)
    n = 0
    for grupo in geo.values():
        if len(grupo) > 1:
            n += 1
            for v in grupo:
                v.setdefault("stack", f"empilhado-{n}")
                v["stack_sugerido"] = True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pbix")
    ap.add_argument("--saida", help="arquivo JSON de saída (padrão: imprime na tela)")
    ap.add_argument("--sem-sugestoes", action="store_true", help="não sugere role/principal/stack")
    args = ap.parse_args()
    z = zipfile.ZipFile(args.pbix)
    nomes = z.namelist()
    if any(n.startswith("Report/definition/pages/") for n in nomes):
        formato, pages = ler_pbir(z, nomes)
    elif "Report/Layout" in nomes:
        formato, pages = ler_legado(z)
    else:
        print(json.dumps({"erro": "relatório sem Report/Layout nem Report/definition"}, ensure_ascii=False))
        return 1
    for p in pages:
        absolutizar(p)
        if not args.sem_sugestoes:
            sugerir_roles(p)
    doc = {"arquivo": args.pbix, "formato": formato, "pages": pages}
    texto = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as f:
            f.write(texto)
        print(args.saida)
    else:
        print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
