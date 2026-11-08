"""Testes do plugin power-bi_layout_with_pbix-mcp (só biblioteca padrão).

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
PLUGIN = os.path.join(RAIZ, "plugins", "power-bi_layout_with_pbix-mcp")
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
        self.assertEqual(v["fonte"]["x"], x_coluna)  # nota fecha a coluna
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
        ev = {"tool_name": "mcp__plugin_power-bi_layout_with_pbix-mcp_pbix-mcp__pbix_save", "tool_input": {}}
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


if __name__ == "__main__":
    unittest.main()
