#!/usr/bin/env python3
"""Motor de layout: calcula a nova disposição das páginas a partir do inventário.

Uso:
  python propor_layout.py layout_antes.json --saida layout_proposto.json
         [--margin M --gutter G --base U --columns 12]

Entrada: o inventário (references/pbix-mcp-operacoes.md), com `role` de cada
visual já conferido. Saída: o mesmo formato com a geometria nova, mais `de`
(geometria original) em cada visual que mudou, o `grid` de cada página e as
listas `decisoes` e `limitacoes`, que alimentam o relatório final.

O cálculo é determinístico e segue as regras da skill:
- grid de 12 colunas com margem, calha e unidade-base (padrão proporcional ao
  tamanho da página: 1280×720 → 24/16/8; 1920×1080 → 36/24/12);
- faixas em Z: topo (identidade, KPI principal, demais KPIs, filtros em lista
  suspensa), meio (tendência e comparação), base (detalhe e secundários);
- segmentadores em lista vertical numa coluna de filtros de 2 colunas à direita;
- tamanho proporcional à importância, mesma função com o mesmo tamanho;
- empilhados com geometria idêntica, grupos movidos como unidade (filhos
  escalados junto), formas de fundo envolvendo o bloco, navegação fixa;
- páginas de dica e detalhamento só recebem encaixe na margem e na unidade-base.

Nada no .pbix é alterado: o script só escreve o JSON da proposta.
"""

import argparse
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _grid import distribuir, encaixar, grid_padrao, largura_vao, x_inicio  # noqa: E402

TOPO = {"identidade", "kpi"}
MEIO = {"tendencia", "comparacao"}
BASE = {"detalhe", "secundario"}
POR_LINHA = 4  # máximo de visuais lado a lado no meio e na base


class Pagina:
    def __init__(self, p, g, decisoes, limitacoes):
        self.p = p
        self.g = g
        self.nome = p.get("name", "?")
        self.dec = decisoes
        self.lim = limitacoes
        self.geo = {}  # chave da unidade -> (x, y, w, h)

    def d(self, msg):
        self.dec.append(f"[{self.nome}] {msg}")

    def l(self, msg):
        self.lim.append(f"[{self.nome}] {msg}")


def unidades(p):
    """Agrupa visuais de primeiro nível em vagas: empilhados dividem uma vaga."""
    vagas = {}
    for v in p["visuals"]:
        if v.get("parent") or v.get("role") == "container":
            continue
        chave = v.get("stack") or f"id:{v['id']}"
        u = vagas.setdefault(chave, {"chave": chave, "membros": [], "role": v.get("role", "secundario")})
        u["membros"].append(v)
    for u in vagas.values():
        rep = u["membros"][0]
        u["rep"] = rep
        u["principal"] = any(m.get("principal") for m in u["membros"])
        u["area"] = max(m["width"] * m["height"] for m in u["membros"])
        u["x"], u["y"] = rep["x"], rep["y"]
    return list(vagas.values())


def ordem_leitura(us):
    return sorted(us, key=lambda u: (round(u["y"] / 40), u["x"]))


def linhas(itens, maximo=POR_LINHA):
    return [itens[i:i + maximo] for i in range(0, len(itens), maximo)] or []


def spans_linha(itens, colunas, pesos):
    return distribuir(pesos, colunas, minimo=min(2, max(1, colunas // max(1, len(itens)))))


def pesos_meio(itens):
    if len(itens) == 1:
        return [1]
    a0, a1 = itens[0]["area"], itens[1]["area"]
    destaque = itens[0]["principal"] or a0 >= 1.3 * a1
    if len(itens) == 2:
        return [2, 1] if destaque else [1, 1]
    return [1.5 if destaque else 1] + [1] * (len(itens) - 1)


def colocar_linha(pg, itens, y, h, col0, colunas, pesos):
    g = pg.g
    spans = spans_linha(itens, colunas, pesos)
    c = col0
    for u, s in zip(itens, spans):
        pg.geo[u["chave"]] = (x_inicio(g, c), y, largura_vao(g, s), h)
        c += s


def layout_normal(pg, us, forcar_coluna=frozenset()):
    g = pg.g
    W, H = g["largura"], g["altura"]
    b, m, gt, C = g["base"], g["margem"], g["calha"], g["colunas"]
    s = W / 1280
    h_card = encaixar(80 * s, b, "ceil")
    h_graf = 200 * s
    util_h = H - 2 * m

    for u in us:
        if u["role"] not in TOPO | MEIO | BASE | {"filtro", "nota", "navegacao"}:
            pg.d(f"{u['rep']['id']} tem função '{u['role']}' desconhecida; tratado como secundário.")
            u["role"] = "secundario"

    header = [u for u in us if u["role"] == "identidade" and u["rep"].get("full_bleed")]
    ident = [u for u in us if u["role"] == "identidade" and not u["rep"].get("full_bleed")]
    kpis = [u for u in us if u["role"] == "kpi"]
    filtros = [u for u in us if u["role"] == "filtro"]
    # Lista vertical só vai para a coluna de filtros se não couber na altura da faixa superior.
    h_topo_ref = max(h_card, min(encaixar(0.18 * util_h, b), encaixar(0.22 * util_h, b, "floor")))

    def cabe_na_faixa(u):
        itens = u["rep"].get("items")
        precisa = (40 + 24 * int(itens)) * s if itens else u["rep"]["height"]
        return precisa <= h_topo_ref + b

    basicos = [u for u in filtros if str(u["rep"].get("slicer_mode", "Dropdown")).lower() == "basic"]
    f_lista = [u for u in basicos if not cabe_na_faixa(u)]
    f_susp = [u for u in filtros if u not in f_lista]
    if len(f_lista) < len(basicos):
        pg.d(f"{len(basicos) - len(f_lista)} segmentador(es) em lista vertical cabem na altura da faixa "
             "superior e ficam nela, ao lado dos KPIs.")
    meio = [u for u in us if u["role"] in MEIO]
    base_ = [u for u in us if u["role"] in BASE]
    notas = [u for u in us if u["role"] == "nota"]
    nav = [u for u in us if u["role"] == "navegacao"]

    # KPI principal primeiro; sem principal declarado, o primeiro na ordem de leitura.
    kpis = ordem_leitura(kpis)
    principal = next((u for u in kpis if u["principal"]), None)
    if principal:
        kpis.remove(principal)
        kpis.insert(0, principal)
    elif kpis and not any(u["principal"] for u in us):
        pg.d(f"sem visual principal declarado; o KPI {kpis[0]['rep']['id']} (primeiro na ordem de leitura) assume.")

    y0 = m
    # Faixa de título de borda a borda.
    if header:
        h_head = 0
        for u in ordem_leitura(header):
            h = max(b, encaixar(u["rep"]["height"], b))
            pg.geo[u["chave"]] = (0, h_head, W, h)
            h_head += h
        y0 = h_head + gt
        pg.d("faixa de título de borda a borda mantida como cabeçalho; o conteúdo começa abaixo dela.")

    # Título largo dentro das margens: vira faixa de cabeçalho com a largura do grid.
    # Identidades pequenas da mesma faixa (data, subtítulo, logo) ficam à direita dele.
    largos = [u for u in ident if u["rep"]["width"] >= 0.5 * W]
    if largos:
        faixa = sorted(ident, key=lambda u: u["x"])
        pequenos = [u for u in faixa if u not in largos]
        livre = C - 2 * len(pequenos)
        if livre < 4 * len(largos):
            pequenos, livre = [], C
            faixa = sorted(largos, key=lambda u: u["x"])
        spans = []
        cotas = iter(distribuir([1] * len(largos), livre, minimo=1))
        for u in faixa:
            spans.append(next(cotas) if u in largos else 2)
        h_cab = max(5 * b, min(max(encaixar(u["rep"]["height"], b) for u in faixa), 10 * b))
        c = 0
        for u, sp in zip(faixa, spans):
            pg.geo[u["chave"]] = (x_inicio(g, c), y0, largura_vao(g, sp), h_cab)
            c += sp
        y0 += h_cab + gt
        ident = [u for u in ident if u not in faixa]
        pg.d("título largo virou faixa de cabeçalho dentro das margens; o KPI principal abre a faixa "
             "superior logo abaixo dele.")

    y_fim = H - m
    # Linha de navegação: mesma posição em todas as páginas do mesmo tamanho.
    if nav:
        h_nav = 5 * b
        y_nav = y_fim - h_nav
        largura_bt = min(2, C // max(1, len(nav)))
        col = C - largura_bt * len(nav)
        for u in sorted(nav, key=lambda u: (u["rep"].get("title") or "", u["rep"]["id"])):
            pg.geo[u["chave"]] = (x_inicio(g, col), y_nav, largura_vao(g, largura_bt), h_nav)
            col += largura_bt
        y_fim = y_nav - gt
        pg.d("navegação numa linha fixa no rodapé, à direita, igual em todas as páginas deste tamanho.")

    # Coluna de filtros para segmentadores em lista vertical.
    Cm = C
    notas_coluna = []
    if f_lista:
        fc = 2 if C >= 10 else 1
        Cm = C - fc
        xc, wc = x_inicio(g, Cm), largura_vao(g, fc)
        if notas:
            notas_coluna, notas = notas, []
        # Com coluna de filtros, os demais segmentadores abrem a coluna, no alto, quando não há
        # KPI na página ou quando não cabem na linha dos KPIs com 2 colunas cada.
        # Filtros cujo campo foi para a coluna em outra página vão para a coluna aqui também.
        forcados = [u for u in f_susp if u["rep"].get("field") in forcar_coluna]
        livres = [u for u in f_susp if u not in forcados]
        cabem_no_topo = 2 * (len(ident) + len(kpis) + len(livres)) <= Cm
        if kpis and cabem_no_topo:
            susp_coluna, f_susp = forcados, livres
        else:
            susp_coluna, f_susp = f_susp, []
        susp_coluna = sorted(susp_coluna, key=lambda u: (u["y"], u["x"]))
        if forcados:
            pg.d(f"{len(forcados)} filtro(s) na coluna para repetir a posição que têm nas outras páginas.")
        alt_notas = [max(4 * b, min(encaixar(u["rep"]["height"], b, "ceil"), 12 * b)) for u in notas_coluna]
        reserva = sum(alt_notas) + gt * len(alt_notas)
        disponivel = y_fim - y0 - reserva - gt * (len(f_lista) - 1)
        pesos = [max(1, int(u["rep"].get("items") or 1)) + 3 for u in f_lista]
        y = y0
        for u in susp_coluna:
            h = max(7 * b, min(encaixar(u["rep"]["height"], b), 10 * b))
            pg.geo[u["chave"]] = (xc, y, wc, h)
            y += h + gt
        unid = distribuir(pesos, max(len(f_lista), int((disponivel - (y - y0)) // b)),
                          minimo=min(8, int((disponivel - (y - y0)) // b) // len(f_lista)))
        for u, n in zip(f_lista, unid):
            pg.geo[u["chave"]] = (xc, y, wc, n * b)
            y += n * b + gt
        y = y_fim
        for u, h in reversed(list(zip(notas_coluna, alt_notas))):
            y -= h
            pg.geo[u["chave"]] = (xc, y, wc, h)
            y -= gt
        pg.d(f"{len(f_lista)} segmentador(es) em lista vertical na coluna de filtros à direita ({fc} colunas). "
             "Alternativa fora do escopo: trocar para lista suspensa e levar para a faixa superior.")
        if notas_coluna:
            pg.d("nota(s) fecham a coluna de filtros.")
        if susp_coluna:
            pg.d(f"{len(susp_coluna)} segmentador(es) em lista suspensa no alto da coluna de filtros.")

    # Faixa superior.
    y = y0
    topo = ordem_leitura(ident) + kpis
    linha_susp = []
    if topo or f_susp:
        ni, nk, nf = len(ident), len(kpis), len(f_susp)
        resto = Cm - 2 * ni - 2 * nf
        if nk and resto < 2 * nk:
            linha_susp, f_susp_linha = f_susp, []
            resto = Cm - 2 * ni
            if f_susp:
                pg.d("segmentadores em lista suspensa numa segunda linha estreita da faixa superior.")
        else:
            f_susp_linha = f_susp
        itens = topo + f_susp_linha
        spans = [2] * ni
        if nk:
            k = max(1, resto // nk)
            # Com filtros ou identidade na linha, um KPI não passa de um terço da largura.
            teto = max(2, Cm // 3)
            if k > teto and (f_susp_linha or ni):
                k = teto
            if resto < 2 * nk:
                pg.l(f"{nk} KPIs não cabem com 2 colunas cada; ficaram com {k}.")
            sobra = Cm - 2 * ni - 2 * len(f_susp_linha) - k * nk
            spans += [k] * nk
            # Filtros crescem no máximo até 3 colunas; o resto da sobra vai para o KPI principal.
            por_filtro = min(1, sobra // len(f_susp_linha)) if f_susp_linha and sobra >= nk else 0
            spans += [2 + por_filtro] * len(f_susp_linha)
            sobra -= por_filtro * len(f_susp_linha)
            if sobra > 0:
                # A sobra que não se divide igualmente vai para o KPI principal, o mais importante.
                spans[ni] += sobra
                if nk > 1:
                    pg.d(f"KPI principal {kpis[0]['rep']['id']} com {sobra} coluna(s) a mais que os demais, "
                         "para fechar a faixa no grid.")
                else:
                    pg.d(f"KPI único {kpis[0]['rep']['id']} ocupa as colunas livres da faixa superior.")
        elif ident:
            spans = distribuir([2 if u in ident else 1 for u in itens], Cm, minimo=1)
        elif itens:
            # Só filtros no topo: largura de 2 a 3 colunas cada, alinhados à esquerda.
            spans = [max(1, min(3, Cm // len(itens)))] * len(itens)
        if nk:
            h_topo = max(h_card, min(encaixar(0.18 * util_h, b), encaixar(0.22 * util_h, b, "floor")))
        else:
            h_topo = max(encaixar(0.6 * h_card, b), encaixar(0.12 * util_h, b))
        c = 0
        for u, sp in zip(itens, spans):
            pg.geo[u["chave"]] = (x_inicio(g, c), y, largura_vao(g, sp), h_topo)
            c += sp
        if itens:
            y += h_topo + gt
        if linha_susp:
            h_f = 7 * b
            sp = max(1, min(3, Cm // len(linha_susp)))
            for i, u in enumerate(sorted(linha_susp, key=lambda u: u["x"])):
                pg.geo[u["chave"]] = (x_inicio(g, i * sp), y, largura_vao(g, sp), h_f)
            y += h_f + gt
    y_meio0 = y

    # Notas sem coluna de filtros: linha estreita no fim da área principal.
    y_fim_main = y_fim
    if notas:
        h_n = max(4 * b, min(max(encaixar(u["rep"]["height"], b, "ceil") for u in notas), 8 * b))
        y_n = y_fim - h_n
        colocar_linha(pg, sorted(notas, key=lambda u: u["x"]), y_n, h_n, 0, Cm, [1] * len(notas))
        y_fim_main = y_n - gt

    # Meio e base.
    meio_o = sorted(meio, key=lambda u: (not u["principal"], -u["area"], u["x"]))
    if len(meio_o) > 1:
        meio_o = [meio_o[0]] + sorted(meio_o[1:], key=lambda u: u["x"])
    base_o = sorted([u for u in base_ if u["role"] == "secundario"], key=lambda u: u["x"]) + \
        sorted([u for u in base_ if u["role"] == "detalhe"], key=lambda u: u["x"])
    lin_meio, lin_base = linhas(meio_o), linhas(base_o)
    n_lin = len(lin_meio) + len(lin_base)
    R = y_fim_main - y_meio0 - gt * max(0, n_lin - 1)
    if n_lin:
        if lin_meio and lin_base:
            h_m_total = encaixar(R * 0.55, b)
            h_b_total = encaixar(R - h_m_total, b, "floor")
        elif lin_meio:
            h_m_total, h_b_total = encaixar(R, b, "floor"), 0
        else:
            h_m_total, h_b_total = 0, encaixar(R, b, "floor")
        # Se a base ficou abaixo do mínimo e o meio tem folga, equilibra as duas.
        if lin_meio and lin_base and h_b_total < h_graf * len(lin_base):
            falta = encaixar(h_graf * len(lin_base) - h_b_total, b, "ceil")
            folga = h_m_total - encaixar(h_graf * len(lin_meio), b, "ceil")
            mover = min(falta, max(0, folga))
            h_m_total -= mover
            h_b_total += mover
        for grupo_linhas, total, nome in ((lin_meio, h_m_total, "meio"), (lin_base, h_b_total, "base")):
            if not grupo_linhas:
                continue
            alturas = [n * b for n in distribuir([1] * len(grupo_linhas), int(total // b), minimo=1)]
            for itens, h in zip(grupo_linhas, alturas):
                if nome == "meio":
                    pesos = pesos_meio(itens)
                else:
                    pesos = [2 if u["role"] == "detalhe" else 1 for u in itens]
                colocar_linha(pg, itens, y_meio0, h, 0, Cm, pesos)
                if h < h_graf:
                    pg.l(f"linha do {nome} com {h} px de altura, abaixo do mínimo de legibilidade ({h_graf:.0f} px).")
                y_meio0 += h + gt
        if lin_meio and len(lin_meio[0]) == 2 and pesos_meio(lin_meio[0]) == [2, 1]:
            pg.d(f"no meio, {lin_meio[0][0]['rep']['id']} fica à esquerda com 2/3 da largura por ser o mais importante.")
    if not topo and not f_susp:
        pg.d("página sem faixa superior; o meio sobe para o topo.")
    if not meio and base_:
        pg.d("página sem tendência ou comparação; a base sobe e ocupa o meio.")
    densidade = len(us)
    if densidade > 8:
        pg.l(f"{densidade} vagas na página, acima da referência de 6 a 8 por página (observação, não alterado).")


def layout_auxiliar(pg, us):
    """Dica de ferramenta e detalhamento: só margem e unidade-base."""
    g = pg.g
    W, H, b, m = g["largura"], g["altura"], g["base"], g["margem"]
    if not us:
        return
    x0 = min(u["rep"]["x"] for u in us)
    y0 = min(u["rep"]["y"] for u in us)
    x1 = max(u["rep"]["x"] + u["rep"]["width"] for u in us)
    y1 = max(u["rep"]["y"] + u["rep"]["height"] for u in us)
    md = g["margem_direita"]
    ex = min(1.0, (W - m - md) / max(1, x1 - x0))
    ey = min(1.0, (H - 2 * m) / max(1, y1 - y0))
    for u in us:
        r = u["rep"]
        ax0 = m + (r["x"] - x0) * ex
        ay0 = m + (r["y"] - y0) * ey
        ax1 = ax0 + r["width"] * ex
        ay1 = ay0 + r["height"] * ey
        nx0, ny0 = encaixar(ax0, b), encaixar(ay0, b)
        nx1 = min(encaixar(ax1, b, "floor"), W - md)
        ny1 = min(encaixar(ay1, b), H - m)
        pg.geo[u["chave"]] = [max(m, nx0), max(m, ny0), max(b, nx1 - max(m, nx0)), max(b, ny1 - max(m, ny0))]
    # Garante a calha entre vizinhos: encolhe o visual de cima (ou da esquerda).
    gt = g["calha"]
    caixas = [pg.geo[u["chave"]] for u in us]
    for a in caixas:
        for c in caixas:
            if a is c:
                continue
            cruza_x = a[0] < c[0] + c[2] and c[0] < a[0] + a[2]
            cruza_y = a[1] < c[1] + c[3] and c[1] < a[1] + a[3]
            if cruza_x and c[1] >= a[1] + a[3] - b and c[1] - (a[1] + a[3]) < gt:
                a[3] = max(b, c[1] - gt - a[1])
            elif cruza_y and c[0] >= a[0] + a[2] - b and c[0] - (a[0] + a[2]) < gt:
                a[2] = max(b, c[0] - gt - a[0])
    for u in us:
        pg.geo[u["chave"]] = tuple(pg.geo[u["chave"]])
    pg.d(f"página do tipo '{pg.p.get('type')}': só encaixe na margem e na unidade-base, sem faixas.")


def contem(caixa, v):
    cx, cy = v["x"] + v["width"] / 2, v["y"] + v["height"] / 2
    return caixa["x"] <= cx <= caixa["x"] + caixa["width"] and caixa["y"] <= cy <= caixa["y"] + caixa["height"]


def aplicar(pg, us):
    p, g = pg.p, pg.g
    por_id = {v["id"]: v for v in p["visuals"]}
    original = {v["id"]: {k: v[k] for k in ("x", "y", "width", "height")} for v in p["visuals"]}
    for u in us:
        geo = pg.geo.get(u["chave"])
        if geo is None:
            continue
        for mbr in u["membros"]:
            mbr["x"], mbr["y"], mbr["width"], mbr["height"] = geo
    # Filhos de grupo: mesma disposição interna, escalada para a nova vaga do grupo.
    for v in p["visuals"]:
        pai = por_id.get(v.get("parent"))
        if not pai:
            continue
        o_pai, o_v = original[pai["id"]], original[v["id"]]
        fx = pai["width"] / max(1, o_pai["width"])
        fy = pai["height"] / max(1, o_pai["height"])
        v["x"] = round(pai["x"] + (o_v["x"] - o_pai["x"]) * fx)
        v["y"] = round(pai["y"] + (o_v["y"] - o_pai["y"]) * fy)
        v["width"] = round(o_v["width"] * fx)
        v["height"] = round(o_v["height"] * fy)
        v["rel_x"], v["rel_y"] = v["x"] - pai["x"], v["y"] - pai["y"]
    # Formas de fundo envolvem o bloco que já envolviam, com folga de uma unidade-base.
    b = g["base"]
    for c in (v for v in p["visuals"] if v.get("role") == "container" and not v.get("parent")):
        dentro = [v for v in p["visuals"] if v is not c and v.get("role") != "container"
                  and not v.get("parent") and contem(original[c["id"]], original[v["id"]])]
        if not dentro:
            pg.d(f"forma de fundo {c['id']} não envolve nenhum visual; geometria mantida.")
            continue
        x0 = min(v["x"] for v in dentro) - b
        y0 = min(v["y"] for v in dentro) - b
        x1 = max(v["x"] + v["width"] for v in dentro) + b
        y1 = max(v["y"] + v["height"] for v in dentro) + b
        c["x"], c["y"] = max(0, x0), max(0, y0)
        c["width"], c["height"] = min(g["largura"], x1) - c["x"], min(g["altura"], y1) - c["y"]
        c["z_atras"] = True
    for v in p["visuals"]:
        o = original[v["id"]]
        if any(abs(o[k] - v[k]) > 0.5 for k in o):
            v["de"] = o


def sobrepoe(a, b):
    return (a[0] < b[0] + b[2] - 1 and b[0] < a[0] + a[2] - 1 and
            a[1] < b[1] + b[3] - 1 and b[1] < a[1] + a[3] - 1)


def alinhar_filtros_entre_paginas(paginas):
    """Filtros do mesmo campo e mesmo modo recebem a mesma geometria entre páginas."""
    ref = {}
    for pg, us in paginas:
        if pg.p.get("type", "normal") != "normal":
            continue
        for u in us:
            campo = u["rep"].get("field")
            if u["role"] != "filtro" or not campo:
                continue
            chave = (campo, str(u["rep"].get("slicer_mode")), pg.g["largura"], pg.g["altura"])
            geo = pg.geo.get(u["chave"])
            if chave not in ref:
                ref[chave] = (geo, pg.nome)
                continue
            alvo, origem = ref[chave]
            if geo == alvo:
                continue
            outros = [pg.geo[o["chave"]] for o in us if o is not u and o["chave"] in pg.geo
                      and o["role"] != "container"]
            if any(sobrepoe(alvo, o) for o in outros):
                pg.d(f"filtro de {campo} não pôde repetir a posição usada em '{origem}' sem sobrepor outro visual.")
            else:
                pg.geo[u["chave"]] = alvo
                pg.d(f"filtro de {campo} na mesma posição e tamanho que em '{origem}'.")


def grid_da_pagina(p, args):
    return grid_padrao(p["width"], p["height"], colunas=args.columns,
                       margem=args.margin, calha=args.gutter, base=args.base)


def montar(out, args, forcar_coluna):
    decisoes, limitacoes, paginas = [], [], []
    for p in out["pages"]:
        g = grid_da_pagina(p, args)
        pg = Pagina(p, g, decisoes, limitacoes)
        us = unidades(p)
        if p.get("type", "normal") == "normal":
            layout_normal(pg, us, forcar_coluna)
        else:
            layout_auxiliar(pg, us)
        paginas.append((pg, us))
    return decisoes, limitacoes, paginas


def campos_na_coluna(paginas):
    """Campos de filtro que terminaram na coluna de filtros em alguma página."""
    campos = set()
    for pg, us in paginas:
        if pg.p.get("type", "normal") != "normal":
            continue
        x_coluna = x_inicio(pg.g, pg.g["colunas"] - 2)
        for u in us:
            geo = pg.geo.get(u["chave"])
            if u["role"] == "filtro" and u["rep"].get("field") and geo and geo[0] == x_coluna:
                campos.add(u["rep"]["field"])
    return frozenset(campos)


def propor(doc, args):
    out = copy.deepcopy(doc)
    # Duas passadas: a primeira descobre quais campos de filtro vão para a coluna em alguma
    # página; a segunda leva esses campos para a coluna em todas as páginas que a têm.
    _, _, paginas = montar(copy.deepcopy(out), args, frozenset())
    decisoes, limitacoes, paginas = montar(out, args, campos_na_coluna(paginas))
    alinhar_filtros_entre_paginas(paginas)
    for pg, us in paginas:
        aplicar(pg, us)
        g = pg.g
        pg.p["grid"] = {k: g[k] for k in ("base", "margem", "margem_direita", "calha", "colunas", "largura_coluna")}
        if abs(g["largura_coluna_exata"] - g["largura_coluna"]) > 0.01:
            pg.d(f"coluna arredondada para {g['largura_coluna']} px; a sobra vai para a margem direita "
                 f"({g['margem_direita']} px).")
    out["decisoes"] = decisoes
    out["limitacoes"] = limitacoes
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("layout")
    ap.add_argument("--saida", help="arquivo de saída (padrão: imprime na tela)")
    ap.add_argument("--margin", type=float)
    ap.add_argument("--gutter", type=float)
    ap.add_argument("--base", type=float)
    ap.add_argument("--columns", type=int, default=12)
    args = ap.parse_args()
    with open(args.layout, encoding="utf-8") as f:
        doc = json.load(f)
    out = propor(doc, args)
    texto = json.dumps(out, ensure_ascii=False, indent=2)
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as f:
            f.write(texto)
        n = sum(1 for p in out["pages"] for v in p["visuals"] if "de" in v)
        print(json.dumps({"saida": args.saida, "visuais_movidos": n,
                          "decisoes": len(out["decisoes"]), "limitacoes": len(out["limitacoes"])},
                         ensure_ascii=False))
    else:
        print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
