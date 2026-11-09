"""Testes do plugin powerbi-layout-agent-automation (só biblioteca padrão).

Rodar da raiz do repositório:
  python3 -m unittest discover tests -v
"""

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(RAIZ, "plugins", "powerbi-layout-agent-automation")
SCRIPTS = os.path.join(PLUGIN, "skills", "reorganizar-layout-power-bi", "scripts")
FIXTURES = os.path.join(RAIZ, "tests", "fixtures")
sys.path.insert(0, SCRIPTS)

import _grid  # noqa: E402
import compare_pbix  # noqa: E402
import hook_guardiao  # noqa: E402
import inventario_pbix  # noqa: E402
import layout_check  # noqa: E402
import propor_layout  # noqa: E402


def fixture(nome):
    with open(os.path.join(FIXTURES, nome), encoding="utf-8") as f:
        return json.load(f)


def opcoes(**kw):
    o = types.SimpleNamespace(margin=None, gutter=None, base=None, columns=12, allow_gap=[])
    for k, v in kw.items():
        setattr(o, k, v)
    return o


def conferir(doc):
    erros, avisos = [], []
    for p in doc["pages"]:
        e, w, _ = layout_check.analisar(p, opcoes())
        erros += e
        avisos += w
    return erros, avisos


def nota(doc):
    return layout_check.notas(doc, opcoes())[0]


def por_id(doc):
    return {v["id"]: v for p in doc["pages"] for v in p["visuals"]}


class TestGrid(unittest.TestCase):
    def test_tamanhos_padrao_dao_coluna_inteira(self):
        for (w, h), col, base in (((1280, 720), 88, 8), ((1920, 1080), 132, 12)):
            g = _grid.grid_padrao(w, h)
            self.assertEqual(g["largura_coluna"], col)
            self.assertEqual(g["base"], base)
            self.assertEqual(g["margem"], g["margem_direita"])
            ultima = g["x_colunas"][-1] + g["largura_coluna"]
            self.assertEqual(ultima, w - g["margem"])

    def test_tamanho_livre_joga_sobra_na_margem_direita(self):
        g = _grid.grid_padrao(1366, 768)
        self.assertEqual(g["largura_coluna"], int(g["largura_coluna"]))
        self.assertEqual(g["x_colunas"][-1] + g["largura_coluna"] + g["margem_direita"], 1366)

    def test_distribuir_soma_total(self):
        casos = [[1], [1, 1], [2, 1], [1.5, 1, 1], [1] * 5, [3, 1, 1, 1], [0, 0], [1] * 13]
        for pesos in casos:
            for total in (6, 10, 12):
                r = _grid.distribuir(pesos, total)
                self.assertEqual(sum(r), total, (pesos, total, r))
                self.assertEqual(len(r), len(pesos))

    def test_distribuir_respeita_proporcao(self):
        self.assertEqual(_grid.distribuir([2, 1], 12), [8, 4])
        self.assertEqual(_grid.distribuir([1, 1, 1], 12), [4, 4, 4])


class TestMotor(unittest.TestCase):
    def proposta(self, nome):
        antes = fixture(nome)
        depois = propor_layout.propor(antes, opcoes())
        return antes, depois

    def test_fixtures_saem_sem_erros_e_com_nota_maior(self):
        for nome in ("pagina_1280.json", "pagina_1920_coluna.json", "casos_especiais.json", "titulo_largo.json"):
            antes, depois = self.proposta(nome)
            erros, _ = conferir(depois)
            self.assertEqual(erros, [], nome)
            comp = []
            layout_check.compare(antes, depois, comp)
            self.assertEqual(comp, [], nome)
            self.assertGreater(nota(depois), nota(antes), nome)
            self.assertGreaterEqual(nota(depois), 90, nome)

    def test_kpi_principal_no_canto_e_ordem_em_z(self):
        _, depois = self.proposta("pagina_1280.json")
        v = por_id(depois)
        self.assertEqual((v["logo"]["x"], v["logo"]["y"]), (24, 24))
        self.assertEqual(v["fat"]["y"], 24)
        self.assertLess(v["fat"]["x"], v["margem"]["x"])
        self.assertLess(v["margem"]["x"], v["ano"]["x"])
        self.assertGreater(v["tend"]["y"], v["fat"]["y"] + v["fat"]["height"])
        self.assertGreater(v["tab"]["y"], v["tend"]["y"] + v["tend"]["height"])
        # Mesma função, mesmo tamanho (fora o principal).
        self.assertEqual((v["margem"]["width"], v["margem"]["height"]), (v["meta"]["width"], v["meta"]["height"]))

    def test_mais_importante_do_meio_tem_mais_area(self):
        _, depois = self.proposta("pagina_1280.json")
        v = por_id(depois)
        self.assertEqual(v["tend"]["x"], 24)
        self.assertGreater(v["tend"]["width"], v["comp"]["width"])

    def test_coluna_de_filtros_e_consistencia_entre_paginas(self):
        _, depois = self.proposta("pagina_1920_coluna.json")
        v = por_id(depois)
        g = _grid.grid_padrao(1920, 1080)
        x_coluna = g["x_colunas"][10]
        for vid in ("seg", "uf", "seg2", "uf2"):
            self.assertEqual(v[vid]["x"], x_coluna, vid)
        self.assertLess(v["uf"]["y"], v["seg"]["y"])  # lista suspensa abre a coluna
        geo = lambda x: (x["x"], x["y"], x["width"], x["height"])  # noqa: E731
        self.assertEqual(geo(v["seg"]), geo(v["seg2"]))
        self.assertEqual(geo(v["uf"]), geo(v["uf2"]))
        # Nota sem texto que no original era uma linha larga: fica no fim da área principal.
        self.assertEqual(v["fonte"]["x"], g["x_colunas"][0])
        self.assertEqual(v["fonte"]["y"] + v["fonte"]["height"], 1080 - g["margem"])
        self.assertEqual((v["titulo"]["x"], v["titulo"]["y"], v["titulo"]["width"]), (0, 0, 1920))

    def test_titulo_largo_vira_cabecalho_e_kpi_abre_a_faixa(self):
        _, depois = self.proposta("titulo_largo.json")
        v = por_id(depois)
        g = _grid.grid_padrao(1280, 720)
        self.assertEqual((v["titulo"]["x"], v["titulo"]["y"]), (24, 24))
        self.assertEqual(v["data"]["x"] + v["data"]["width"], 1280 - g["margem"])
        self.assertEqual(v["titulo"]["height"], v["data"]["height"])
        # KPI principal no canto, logo abaixo do cabeçalho.
        self.assertEqual(v["total"]["x"], 24)
        self.assertEqual(v["total"]["y"], v["titulo"]["y"] + v["titulo"]["height"] + g["calha"])
        # Listas que cabem na faixa ficam ao lado do KPI; a de 30 itens vai para a coluna.
        self.assertEqual(v["f1"]["y"], v["total"]["y"])
        self.assertEqual((v["f1"]["width"], v["f1"]["height"]), (v["f2"]["width"], v["f2"]["height"]))
        self.assertEqual(v["f3"]["x"], g["x_colunas"][10])
        self.assertGreater(v["f3"]["height"], v["f1"]["height"])
        # O KPI não passa de um terço da largura quando divide a linha com filtros.
        self.assertLessEqual(v["total"]["width"], _grid.largura_vao(g, 6))

    def test_empilhados_grupos_fundo_e_navegacao(self):
        _, depois = self.proposta("casos_especiais.json")
        v = por_id(depois)
        geo = lambda x: (x["x"], x["y"], x["width"], x["height"])  # noqa: E731
        self.assertEqual(geo(v["linhaA"]), geo(v["linhaB"]))
        grp = v["grp"]
        self.assertEqual(v["g1"]["x"], grp["x"])
        self.assertEqual(v["g1"]["rel_x"], 0)
        self.assertEqual(v["g2"]["rel_x"], v["g2"]["x"] - grp["x"])
        self.assertAlmostEqual(v["g1"]["width"] + v["g2"]["width"], grp["width"], delta=2)
        fundo = v["fundo"]
        self.assertTrue(fundo.get("z_atras"))
        for k in ("c1", "c2"):
            self.assertLessEqual(fundo["x"], v[k]["x"] - 8)
            self.assertGreaterEqual(fundo["x"] + fundo["width"], v[k]["x"] + v[k]["width"] + 8)
        self.assertEqual(v["nav1"]["y"], v["nav2"]["y"])
        self.assertEqual(v["nav1"]["y"] + v["nav1"]["height"], 720 - 24)

    def test_pagina_de_dica_so_recebe_encaixe(self):
        _, depois = self.proposta("casos_especiais.json")
        dica = next(p for p in depois["pages"] if p["name"] == "Dica")
        g = _grid.grid_padrao(320, 240)
        for v in dica["visuals"]:
            self.assertGreaterEqual(v["x"], g["margem"])
            self.assertLessEqual(v["x"] + v["width"], 320 - g["margem_direita"])
            self.assertEqual(v["y"] % g["base"], 0)
        t1, t2 = dica["visuals"]
        self.assertGreaterEqual(t2["y"] - (t1["y"] + t1["height"]), g["calha"])

    def test_motor_e_deterministico_e_nao_altera_entrada(self):
        antes = fixture("pagina_1280.json")
        copia = copy.deepcopy(antes)
        a = propor_layout.propor(antes, opcoes())
        b = propor_layout.propor(antes, opcoes())
        self.assertEqual(a, b)
        self.assertEqual(antes, copia)


class TestNota(unittest.TestCase):
    def test_layout_proposto_vale_cem_e_sobreposicao_derruba(self):
        depois = propor_layout.propor(fixture("pagina_1280.json"), opcoes())
        self.assertEqual(nota(depois), 100.0)
        ruim = copy.deepcopy(depois)
        v = ruim["pages"][0]["visuals"]
        v[1]["x"], v[1]["y"] = v[2]["x"] + 10, v[2]["y"] + 10
        self.assertLess(nota(ruim), 95)
        erros, _ = conferir(ruim)
        self.assertTrue(any("sobrepõem" in e for e in erros))

    def test_criterios_somam_a_nota(self):
        antes = fixture("pagina_1280.json")
        geral, paginas = layout_check.notas(antes, opcoes())
        for p in paginas:
            self.assertAlmostEqual(sum(p["criterios"].values()), p["nota"], delta=0.2)
            self.assertLessEqual(p["nota"], 100)


class TestHook(unittest.TestCase):
    def test_save_sem_destino_ou_com_overwrite_pergunta(self):
        base = {"tool_name": "mcp__pbix-mcp__pbix_save"}
        self.assertIsNotNone(hook_guardiao.decidir(dict(base, tool_input={"alias": "a"})))
        self.assertIsNotNone(hook_guardiao.decidir(dict(base, tool_input={"alias": "a", "output_path": "x.pbix",
                                                                          "overwrite": True})))
        self.assertIsNone(hook_guardiao.decidir(dict(base, tool_input={"alias": "a", "output_path": "x.pbix"})))

    def test_prefixo_do_plugin_tambem_e_vigiado(self):
        ev = {"tool_name": "mcp__plugin_powerbi-layout-agent-automation_pbix-mcp__pbix_save", "tool_input": {}}
        self.assertIsNotNone(hook_guardiao.decidir(ev))

    def test_marcador_liga_a_vigilancia_de_formatacao(self):
        with tempfile.TemporaryDirectory() as d:
            ev = {"tool_name": "mcp__pbix-mcp__pbix_set_theme", "tool_input": {}, "cwd": d}
            self.assertIsNone(hook_guardiao.decidir(ev))
            open(os.path.join(d, hook_guardiao.MARCADOR), "w").close()
            self.assertIsNotNone(hook_guardiao.decidir(ev))
            for seguro in ("pbix_move_visual", "pbix_get_pages", "pbix_open", "pbix_evaluate_dax"):
                ev2 = dict(ev, tool_name=f"mcp__pbix-mcp__{seguro}")
                self.assertIsNone(hook_guardiao.decidir(ev2), seguro)

    def test_saida_do_processo_e_json_valido(self):
        ev = json.dumps({"tool_name": "mcp__pbix-mcp__pbix_save", "tool_input": {"alias": "a"}})
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "hook_guardiao.py")],
                           input=ev, capture_output=True, text=True, check=True)
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "ask")
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "hook_guardiao.py")],
                           input="não é json", capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


def pbix_pbir(caminho, x=10, titulo="Vendas"):
    vis = {"name": "v1", "position": {"x": x, "y": 20, "z": 0, "width": 300, "height": 200, "tabOrder": 0},
           "visual": {"visualType": "card", "visualContainerObjects": {
               "title": [{"properties": {"text": {"expr": {"Literal": {"Value": f"'{titulo}'"}}}}}]}}}
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("Report/definition/pages/pages.json", json.dumps({"pageOrder": ["p1"]}))
        z.writestr("Report/definition/pages/p1/page.json",
                   json.dumps({"name": "p1", "displayName": "Página", "width": 1280, "height": 720}))
        z.writestr("Report/definition/pages/p1/visuals/v1/visual.json", json.dumps(vis))
        z.writestr("DataModel", b"\x00binario")


def pbix_legado(caminho, x=10, tipo="card"):
    cfg = {"name": "v1", "singleVisual": {"visualType": tipo},
           "layouts": [{"id": 0, "position": {"x": x, "y": 20, "z": 0, "width": 300, "height": 200}}]}
    layout = {"sections": [{"displayName": "Página", "name": "s1", "ordinal": 0, "width": 1280, "height": 720,
                            "config": "{}", "filters": "[]",
                            "visualContainers": [{"x": x, "y": 20, "z": 0, "width": 300, "height": 200,
                                                  "config": json.dumps(cfg)}]}]}
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("Report/Layout", json.dumps(layout).encode("utf-16-le"))
        z.writestr("DataModel", b"\x00binario")


def rodar_compare(a, b):
    buf = io.StringIO()
    antigo, sys.stdout = sys.stdout, buf
    try:
        codigo = compare_pbix.main(a, b)
    finally:
        sys.stdout = antigo
    return codigo, json.loads(buf.getvalue())


class TestCompare(unittest.TestCase):
    def test_pbir_so_geometria_ok_e_titulo_falha(self):
        with tempfile.TemporaryDirectory() as d:
            a, b, c = (os.path.join(d, n) for n in ("a.pbix", "b.pbix", "c.pbix"))
            pbix_pbir(a)
            pbix_pbir(b, x=24)
            pbix_pbir(c, x=24, titulo="Outro")
            codigo, out = rodar_compare(a, b)
            self.assertEqual((codigo, out["resultado"], len(out["geometria"])), (0, "ok", 1))
            codigo, out = rodar_compare(a, c)
            self.assertEqual((codigo, out["resultado"]), (1, "falhou"))

    def test_legado_so_geometria_ok_e_tipo_falha(self):
        with tempfile.TemporaryDirectory() as d:
            a, b, c = (os.path.join(d, n) for n in ("a.pbix", "b.pbix", "c.pbix"))
            pbix_legado(a)
            pbix_legado(b, x=24)
            pbix_legado(c, x=24, tipo="lineChart")
            self.assertEqual(rodar_compare(a, b)[1]["resultado"], "ok")
            self.assertEqual(rodar_compare(a, c)[1]["resultado"], "falhou")


class TestInventario(unittest.TestCase):
    def ler(self, caminho):
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "inventario_pbix.py"), caminho],
                           capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def test_le_os_dois_formatos(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.pbix"), os.path.join(d, "b.pbix")
            pbix_pbir(a)
            pbix_legado(b)
            for caminho, formato in ((a, "PBIR"), (b, "legado")):
                doc = self.ler(caminho)
                self.assertEqual(doc["formato"], formato)
                v = doc["pages"][0]["visuals"][0]
                self.assertEqual((v["id"], v["type"], v["role"], v["x"]), ("v1", "card", "kpi", 10))
                self.assertTrue(v.get("principal"))
            self.assertEqual(self.ler(a)["pages"][0]["visuals"][0]["title"], "Vendas")

    def test_filhos_de_grupo_viram_absolutos(self):
        p = {"width": 1280, "height": 720, "visuals": [
            {"id": "g", "type": "group", "x": 100, "y": 50, "width": 400, "height": 300},
            {"id": "f", "type": "card", "parent": "g", "x": 10, "y": 20, "width": 100, "height": 80}]}
        inventario_pbix.absolutizar(p)
        f = p["visuals"][1]
        self.assertEqual((f["x"], f["y"], f["rel_x"], f["rel_y"]), (110, 70, 10, 20))


class TestManifestos(unittest.TestCase):
    def test_jsons_do_plugin_sao_validos(self):
        for rel in (".claude-plugin/plugin.json", ".mcp.json", "hooks/hooks.json"):
            with open(os.path.join(PLUGIN, rel), encoding="utf-8") as f:
                json.load(f)
        with open(os.path.join(RAIZ, ".claude-plugin", "marketplace.json"), encoding="utf-8") as f:
            m = json.load(f)
        with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            p = json.load(f)
        self.assertEqual(m["plugins"][0]["name"], p["name"])

    def test_hook_aponta_para_script_existente(self):
        with open(os.path.join(PLUGIN, "hooks", "hooks.json"), encoding="utf-8") as f:
            h = json.load(f)
        hook = h["hooks"]["PreToolUse"][0]["hooks"][0]
        self.assertEqual(hook["command"], "uv")  # python3 não existe no Windows padrão
        arg = next(a for a in hook["args"] if a.endswith(".py"))
        self.assertTrue(os.path.exists(arg.replace("${CLAUDE_PLUGIN_ROOT}", PLUGIN)))

    def test_nenhum_texto_do_plugin_manda_rodar_python3(self):
        for pasta, _, arquivos in os.walk(PLUGIN):
            for nome in arquivos:
                if nome.endswith((".md", ".json")):
                    with open(os.path.join(pasta, nome), encoding="utf-8") as f:
                        texto = f.read()
                    self.assertNotIn("python3 ", texto, nome)
                    self.assertNotIn("`python ", texto, nome)

    @unittest.skipUnless(shutil.which("uv"), "uv não instalado")
    def test_hook_roda_pelo_uv_como_no_hooks_json(self):
        with open(os.path.join(PLUGIN, "hooks", "hooks.json"), encoding="utf-8") as f:
            hook = json.load(f)["hooks"]["PreToolUse"][0]["hooks"][0]
        cmd = [hook["command"]] + [a.replace("${CLAUDE_PLUGIN_ROOT}", PLUGIN) for a in hook["args"]]
        ev = json.dumps({"tool_name": "mcp__pbix-mcp__pbix_save", "tool_input": {"alias": "a"}})
        r = subprocess.run(cmd, input=ev, capture_output=True, text=True, timeout=hook["timeout"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")


class TestGridNaoPadrao(unittest.TestCase):
    def test_4x3_tem_coluna_multipla_da_unidade(self):
        g = _grid.grid_padrao(1024, 768)
        self.assertEqual((g["base"], g["largura_coluna"], g["margem_esquerda"], g["margem_direita"]), (8, 64, 40, 40))
        for x in g["x_colunas"]:
            self.assertEqual(x % g["base"], 0)

    def test_qualquer_largura_fecha_na_pagina(self):
        for w in (320, 816, 960, 1024, 1280, 1366, 1440, 1600, 1920, 2560):
            g = _grid.grid_padrao(w, 720)
            self.assertEqual(g["largura_coluna"] % g["base"], 0, w)
            self.assertGreaterEqual(g["margem_esquerda"], 3 * g["base"], w)
            self.assertEqual(g["x_colunas"][-1] + g["largura_coluna"] + g["margem_direita"], w, w)

    def test_margem_informada_vale_como_dada(self):
        g = _grid.grid_padrao(1280, 720, margem=16, calha=16)
        self.assertEqual((g["margem_esquerda"], g["margem"]), (16, 16))
        self.assertFalse(g["automatico"])


class TestCasosDoPbix(unittest.TestCase):
    """Inventário real de um .pbix gerado pelo pbix-mcp com grupo, empilhados, forma de fundo,
    6 KPIs, navegação, página 4:3 e página de dica (tests/fixtures/casos_pbix.json)."""

    @classmethod
    def setUpClass(cls):
        cls.antes = fixture("casos_pbix.json")
        cls.depois = propor_layout.propor(cls.antes, opcoes())
        cls.v = por_id(cls.depois)
        cls.pagina = {p["name"]: p for p in cls.depois["pages"]}

    def test_conferencia_limpa_e_nota_cem(self):
        erros, avisos = conferir(self.depois)
        self.assertEqual((erros, avisos), ([], []))
        self.assertEqual(nota(self.depois), 100.0)

    def test_seis_kpis_iguais_na_largura_toda_e_coluna_abaixo(self):
        kpis = [v for v in self.pagina["Page 1"]["visuals"] if v["role"] == "kpi"]
        self.assertEqual(len(kpis), 6)
        self.assertEqual(len({(v["width"], v["height"]) for v in kpis}), 1)
        self.assertEqual(kpis[0]["width"], _grid.largura_vao(_grid.grid_padrao(1280, 720), 2))
        fundo_kpis = max(v["y"] + v["height"] for v in kpis)
        filtros = [v for v in self.pagina["Page 1"]["visuals"] if v["role"] == "filtro"]
        self.assertTrue(all(f["y"] > fundo_kpis for f in filtros))

    def test_botoes_na_ordem_do_autor_e_na_mesma_linha(self):
        for nome in ("Page 1", "Detalhe"):
            nav = sorted((v for v in self.pagina[nome]["visuals"] if v["role"] == "navegacao"),
                         key=lambda v: v["x"])
            self.assertEqual([v["title"] for v in nav], ["Início", "Detalhe"], nome)
            self.assertEqual(len({v["y"] for v in nav}), 1)

    def test_pagina_4x3_alinhada_a_unidade(self):
        for v in self.pagina["Detalhe"]["visuals"]:
            for k in ("x", "y", "width", "height"):
                self.assertEqual(v[k] % 8, 0, (v["id"], k))

    def test_grupo_redimensionado_marca_filhos_para_aplicar(self):
        grupo = next(v for v in self.pagina["Page 1"]["visuals"] if v.get("is_group"))
        filhos = [v for v in self.pagina["Page 1"]["visuals"] if v.get("parent") == grupo["id"]]
        self.assertEqual(len(filhos), 2)
        for f in filhos:
            self.assertTrue(f["aplicar_filho"])
            self.assertEqual(f["x"] - grupo["x"], f["rel_x"])
            self.assertLessEqual(f["y"] + f["height"], grupo["y"] + grupo["height"])

    def test_empilhados_e_forma_de_fundo(self):
        pilha = [v for v in self.pagina["Page 1"]["visuals"] if v.get("stack")]
        self.assertEqual(len({(v["x"], v["y"], v["width"], v["height"]) for v in pilha}), 1)
        fundo = next(v for v in self.pagina["Page 1"]["visuals"] if v["role"] == "container")
        self.assertTrue(fundo["z_atras"])

    def test_proposta_sai_sem_marcas_de_sugestao(self):
        marcas = [k for p in self.depois["pages"] for v in p["visuals"] for k in v if k.endswith("_sugerido")]
        self.assertEqual(marcas, [])


def pagina_sintetica(visuais, w=1280, h=720):
    return {"pages": [{"name": "P", "type": "normal", "width": w, "height": h, "visuals": visuais}]}


class TestMotorBordas(unittest.TestCase):
    def test_muitos_kpis_quebram_em_linhas_equilibradas(self):
        vis = [{"id": f"k{i}", "type": "card", "role": "kpi", "x": 10 + 150 * i, "y": 10, "width": 140,
                "height": 90} for i in range(8)]
        vis[0]["principal"] = True
        vis.append({"id": "lista", "type": "slicer", "role": "filtro", "slicer_mode": "Basic", "items": 30,
                    "x": 1150, "y": 120, "width": 120, "height": 500})
        vis.append({"id": "linha", "type": "lineChart", "role": "tendencia", "x": 10, "y": 200, "width": 900,
                    "height": 300})
        depois = propor_layout.propor(pagina_sintetica(vis), opcoes())
        erros, _ = conferir(depois)
        self.assertEqual(erros, [])
        kpis = [v for v in depois["pages"][0]["visuals"] if v["role"] == "kpi"]
        linhas = sorted({v["y"] for v in kpis})
        self.assertEqual(len(linhas), 2)
        self.assertEqual(sorted(sum(1 for v in kpis if v["y"] == y) for y in linhas), [4, 4])
        self.assertTrue(any("linhas" in l for l in depois["limitacoes"]))

    def test_tabela_estreita_para_os_campos_gera_limitacao(self):
        vis = [{"id": "tab", "type": "tableEx", "role": "detalhe", "fields": [f"T.c{i}" for i in range(14)],
                "x": 10, "y": 400, "width": 400, "height": 200},
               {"id": "pizza", "type": "pieChart", "role": "secundario", "x": 420, "y": 400, "width": 400,
                "height": 200},
               {"id": "mapa", "type": "map", "role": "secundario", "x": 830, "y": 400, "width": 400,
                "height": 200}]
        depois = propor_layout.propor(pagina_sintetica(vis), opcoes())
        self.assertTrue(any("tab" in l and "por campo" in l for l in depois["limitacoes"]))


class TestCasoRealIFData(unittest.TestCase):
    """Correções vindas do teste real com o painel IFData (1920×1080, filtros em coluna)."""

    def setUp(self):
        self.depois = propor_layout.propor(fixture("pagina_1920_coluna.json"), opcoes())
        self.v = por_id(self.depois)
        self.g = _grid.grid_padrao(1920, 1080)

    def pagina_com_nota(self, texto):
        doc = copy.deepcopy(fixture("pagina_1920_coluna.json"))
        doc["pages"][0]["visuals"][-1]["title"] = texto
        return por_id(propor_layout.propor(doc, opcoes()))

    def test_nota_curta_fecha_a_coluna_e_longa_vai_para_o_rodape(self):
        x_coluna = self.g["x_colunas"][10]
        curta = self.pagina_com_nota("Fonte: IF.data, Banco Central.")
        self.assertEqual(curta["fonte"]["x"], x_coluna)
        longa = self.pagina_com_nota("Valores originais em R$ mil (junho/2026); exibidos em R$ bi e R$ tri. " * 4)
        self.assertEqual(longa["fonte"]["x"], self.g["x_colunas"][0])
        self.assertEqual(longa["fonte"]["width"], _grid.largura_vao(self.g, 10))

    def test_tabela_apertada_leva_o_secundario_para_o_meio(self):
        doc = copy.deepcopy(fixture("pagina_1920_coluna.json"))
        doc["pages"][0]["visuals"][8]["fields"] = [f"ifdata.c{i}" for i in range(7)]
        depois = propor_layout.propor(doc, opcoes())
        v = por_id(depois)
        self.assertEqual(v["rosca"]["y"], v["barras"]["y"])  # rosca ao lado das barras
        self.assertEqual(v["tabela"]["width"], _grid.largura_vao(self.g, 10))  # tabela com a largura toda
        self.assertFalse(any("por campo" in l for l in depois["limitacoes"]))
        self.assertTrue(any("sobem para o meio" in d for d in depois["decisoes"]))
        self.assertEqual(conferir(depois)[0], [])

    def test_lista_curta_nao_estica_ate_a_base(self):
        # 6 itens: (40 + 24 × 6) × 1,5 × 1,2 = 331 → 336 px na unidade de 12.
        self.assertEqual(self.v["seg"]["height"], 336)
        self.assertEqual(self.v["seg2"]["height"], 336)

    def test_grafico_que_encolhe_muito_gera_limitacao(self):
        doc = copy.deepcopy(fixture("pagina_1920_coluna.json"))
        doc["pages"][0]["visuals"][8]["fields"] = [f"ifdata.c{i}" for i in range(7)]
        depois = propor_layout.propor(doc, opcoes())
        self.assertTrue(any("donutChart" in l and "encolhe" in l for l in depois["limitacoes"]))
        self.assertTrue(any("scatterChart" in l and "encolhe" in l for l in self.depois["limitacoes"]))


class TestHerdarECamada(unittest.TestCase):
    def test_herdar_copia_decisoes_e_tira_marcas(self):
        proposta = propor_layout.propor(fixture("pagina_1280.json"), opcoes())
        with tempfile.TemporaryDirectory() as d:
            prop = os.path.join(d, "prop.json")
            with open(prop, "w", encoding="utf-8") as f:
                json.dump(proposta, f)
            doc = {"pages": [{"name": "Visão geral", "visuals": [
                {"id": "fat", "role": "secundario", "role_sugerido": True, "principal_sugerido": True},
                {"id": "novo", "role": "kpi"}]}]}
            inventario_pbix.herdar(doc, prop)
        fat = doc["pages"][0]["visuals"][0]
        self.assertEqual((fat["role"], fat.get("principal")), ("kpi", True))
        self.assertFalse(any(k.endswith("_sugerido") for k in fat))
        self.assertEqual(doc["sem_correspondencia"], ["novo"])
        self.assertIn("decisoes", doc)

    def test_mudanca_de_camada_aparece_em_camada(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.pbix"), os.path.join(d, "b.pbix")
            pbix_pbir(a)
            pbix_pbir(b)
            with zipfile.ZipFile(b) as z:
                arquivos = {n: z.read(n) for n in z.namelist()}
            vis = json.loads(arquivos["Report/definition/pages/p1/visuals/v1/visual.json"])
            vis["position"]["z"] = 5000
            arquivos["Report/definition/pages/p1/visuals/v1/visual.json"] = json.dumps(vis).encode()
            with zipfile.ZipFile(b, "w") as z:
                for n, conteudo in arquivos.items():
                    z.writestr(n, conteudo)
            codigo, out = rodar_compare(a, b)
        self.assertEqual((codigo, out["resultado"], out["camada"]), (0, "ok", ["v1"]))


class TestHookProjeto(unittest.TestCase):
    def test_marcador_na_raiz_do_projeto_liga_a_vigilancia(self):
        with tempfile.TemporaryDirectory() as raiz, tempfile.TemporaryDirectory() as outro:
            open(os.path.join(raiz, hook_guardiao.MARCADOR), "w").close()
            ev = {"tool_name": "mcp__pbix-mcp__pbix_recolor", "tool_input": {}, "cwd": outro}
            antigo = os.environ.get("CLAUDE_PROJECT_DIR")
            os.environ["CLAUDE_PROJECT_DIR"] = raiz
            try:
                self.assertIsNotNone(hook_guardiao.decidir(ev))
            finally:
                if antigo is None:
                    os.environ.pop("CLAUDE_PROJECT_DIR", None)
                else:
                    os.environ["CLAUDE_PROJECT_DIR"] = antigo


class TestPreview(unittest.TestCase):
    def test_preview_com_proposta_mostra_decisoes_e_a_mesma_nota(self):
        antes = fixture("casos_pbix.json")
        proposta = propor_layout.propor(antes, opcoes())
        with tempfile.TemporaryDirectory() as d:
            caminhos = {}
            for nome, doc in (("antes", antes), ("prop", proposta)):
                caminhos[nome] = os.path.join(d, nome + ".json")
                with open(caminhos[nome], "w", encoding="utf-8") as f:
                    json.dump(doc, f)
            depois = {"pages": proposta["pages"]}  # como o inventário da cópia: sem decisões
            caminhos["depois"] = os.path.join(d, "depois.json")
            with open(caminhos["depois"], "w", encoding="utf-8") as f:
                json.dump(depois, f)
            saida = os.path.join(d, "a.html")
            subprocess.run([sys.executable, os.path.join(SCRIPTS, "preview_layout.py"), caminhos["antes"],
                            caminhos["depois"], saida, "--proposta", caminhos["prop"], "--allow-gap", "8"],
                           check=True, capture_output=True)
            with open(saida, encoding="utf-8") as f:
                html_ = f.read()
        self.assertIn("<h2>Decisões</h2>", html_)
        self.assertIn("nota 100/100", html_)


class TestMarcadorPorScript(unittest.TestCase):
    def test_ligar_e_desligar_pelo_script(self):
        script = os.path.join(SCRIPTS, "hook_guardiao.py")
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, script, "--ligar", "--pasta", d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertTrue(os.path.exists(os.path.join(d, hook_guardiao.MARCADOR)))
            ev = {"tool_name": "mcp__pbix-mcp__pbix_set_theme", "tool_input": {}, "cwd": d}
            self.assertIsNotNone(hook_guardiao.decidir(ev))
            subprocess.run([sys.executable, script, "--desligar", "--pasta", d], check=True, capture_output=True)
            self.assertFalse(os.path.exists(os.path.join(d, hook_guardiao.MARCADOR)))

    def test_textos_nao_pedem_variavel_nem_rm(self):
        for pasta, _, arquivos in os.walk(PLUGIN):
            for nome in arquivos:
                if nome.endswith(".md"):
                    with open(os.path.join(pasta, nome), encoding="utf-8") as f:
                        texto = f.read()
                    self.assertNotIn('"$S/', texto, nome)
                    self.assertNotIn("touch .pbi", texto, nome)
                    self.assertNotIn("rm .pbi", texto, nome)


class TestMensagens(unittest.TestCase):
    def test_decisoes_citam_o_titulo_do_visual(self):
        depois = propor_layout.propor(fixture("pagina_1280.json"), opcoes())
        self.assertTrue(any('"Faturamento" (card, fat)' in d for d in depois["decisoes"]), depois["decisoes"])


class TestHookDestinoIgualAoOriginal(unittest.TestCase):
    def test_save_para_o_proprio_arquivo_aberto_pergunta(self):
        with tempfile.TemporaryDirectory() as d:
            base = {"session_id": f"teste-{os.getpid()}", "cwd": d}
            abrir = dict(base, tool_name="mcp__pbix-mcp__pbix_open",
                         tool_input={"file_path": "Vendas.pbix", "alias": "v"})
            self.assertIsNone(hook_guardiao.decidir(abrir))
            mesmo = dict(base, tool_name="mcp__pbix-mcp__pbix_save",
                         tool_input={"alias": "v", "output_path": os.path.join(d, "Vendas.pbix")})
            copia = dict(base, tool_name="mcp__pbix-mcp__pbix_save",
                         tool_input={"alias": "v", "output_path": "Vendas_reorganizado.pbix"})
            try:
                self.assertIsNotNone(hook_guardiao.decidir(mesmo))
                self.assertIsNone(hook_guardiao.decidir(copia))
            finally:
                registro = hook_guardiao._registro(base)
                if os.path.exists(registro):
                    os.remove(registro)


if __name__ == "__main__":
    unittest.main()
