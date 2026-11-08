"""Cálculo do grid e distribuição de colunas, compartilhado pelos scripts da skill.

Grid padrão de uma página: unidade-base proporcional à largura (8 px em 1280,
12 px em 1920, 4 px numa dica de 320), calha de 2 unidades, margem de cima e de
baixo de 3 unidades e 12 colunas. A largura da coluna é sempre um múltiplo da
unidade, para que toda borda de visual caia na unidade-base; a sobra da divisão
vai para as margens laterais, dividida entre esquerda e direita em unidades
inteiras (com pelo menos 3 unidades de cada lado). Em 1280×720 e 1920×1080 não
há sobra: margens de 24 e 36 px e colunas de 88 e 132 px. Em 1024×768 (4:3), as
colunas têm 64 px e as margens laterais 40 px.

Com margem ou calha informadas, valem os valores dados: a coluna é a maior
largura inteira que cabe, e a sobra vai para a margem direita.
"""

import math

COLUNAS_PADRAO = 12


def unidade_padrao(largura):
    """Unidade-base proporcional à largura da página, múltipla de 4 (mínimo 4)."""
    return max(4, int(round(8 * largura / 1280 / 4)) * 4)


def grid_padrao(largura, altura, colunas=COLUNAS_PADRAO, margem=None, calha=None, base=None):
    """Devolve o grid de uma página como dicionário.

    Campos: largura, altura, base, margem (de cima e de baixo), margem_esquerda,
    margem_direita, calha, colunas, largura_coluna, largura_coluna_exata,
    x_colunas (borda esquerda de cada coluna), area_util e automatico.
    Parâmetros omitidos usam o padrão proporcional ao tamanho da página.
    """
    base = base or unidade_padrao(largura)
    automatico = margem is None and calha is None
    if automatico:
        calha = 2 * base
        margem = 3 * base
        unidades = int(largura // base)
        resto_px = largura - unidades * base
        livre = unidades - (colunas - 1) * 2          # colunas + margens, em unidades
        c = max(1, (livre - 6) // colunas)             # pelo menos 3 unidades por margem
        sobra = livre - c * colunas
        m_esq = (sobra // 2) * base
        m_dir = (sobra - sobra // 2) * base + resto_px
        col = c * base
        col_exata = col
    else:
        margem = 3 * base if margem is None else margem
        calha = 2 * base if calha is None else calha
        util = largura - 2 * margem
        col_exata = (util - (colunas - 1) * calha) / colunas
        col = math.floor(col_exata) if col_exata > 0 else col_exata
        m_esq = margem
        m_dir = margem + util - (colunas * col + (colunas - 1) * calha)
    x_colunas = [m_esq + i * (col + calha) for i in range(colunas)]
    return {
        "largura": largura,
        "altura": altura,
        "base": base,
        "margem": margem,
        "margem_esquerda": m_esq,
        "margem_direita": m_dir,
        "calha": calha,
        "colunas": colunas,
        "largura_coluna": col,
        "largura_coluna_exata": round(col_exata, 2),
        "x_colunas": x_colunas,
        "area_util": [largura - m_esq - m_dir, altura - 2 * margem],
        "automatico": automatico,
    }


def x_inicio(g, coluna):
    """Borda esquerda da coluna (0-based)."""
    return g["x_colunas"][coluna]


def largura_vao(g, n):
    """Largura de um vão de n colunas, incluindo as calhas internas."""
    return n * g["largura_coluna"] + (n - 1) * g["calha"]


def bordas_verticais(g):
    """Conjunto de x em que uma borda de visual pode cair (inícios e fins de coluna)."""
    inicios = set(g["x_colunas"])
    fins = {x + g["largura_coluna"] for x in g["x_colunas"]}
    return inicios | fins


def distribuir(pesos, total=COLUNAS_PADRAO, minimo=1):
    """Distribui `total` colunas entre itens proporcionalmente aos pesos.

    Método do maior resto: cada item recebe pelo menos `minimo` colunas (se
    couber) e a soma é sempre exatamente `total`. Em empate de resto, vence o
    item mais à esquerda, para o resultado ser determinístico.
    """
    n = len(pesos)
    if n == 0:
        return []
    if minimo * n > total:
        minimo = 0
    livre = total - minimo * n
    soma = float(sum(pesos)) or float(n)
    quotas = [livre * (p if sum(pesos) else 1) / soma for p in pesos]
    base = [int(math.floor(q)) for q in quotas]
    resto = livre - sum(base)
    ordem = sorted(range(n), key=lambda i: (-(quotas[i] - base[i]), i))
    for i in ordem[:resto]:
        base[i] += 1
    return [b + minimo for b in base]


def encaixar(valor, base, modo="round"):
    """Arredonda um valor para múltiplo da unidade-base."""
    f = {"round": round, "floor": math.floor, "ceil": math.ceil}[modo]
    return int(f(valor / base) * base)
