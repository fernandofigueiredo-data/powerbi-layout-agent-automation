#!/usr/bin/env python3
"""Confirma que dois .pbix diferem apenas na geometria dos visuais.

Uso (com uv, que funciona igual em macOS, Linux e Windows):
  uv run --no-project --quiet compare_pbix.py original.pbix reorganizado.pbix

Por que existe: o pbix_diff do pbix-mcp compara modelo, medidas, páginas e
visuais, mas não posições; ele responde "sem mudanças" mesmo depois da
reorganização. Este script abre os dois arquivos como zip e compara tudo,
ignorando apenas a geometria (x, y, z, width, height) e diferenças de
formatação de JSON (espaços e quebras de linha).

Cobre os dois formatos de relatório:
- PBIR (Report/definition/pages/<página>/visuals/<visual>/visual.json)
- legado (Report/Layout, JSON em UTF-16 LE)

Saída: JSON com "geometria" (o que mudou de lugar), "camada" (visuais cuja
ordem de camada, z, mudou: o contrato só permite isso em formas de fundo, então
confira cada um), "outras_mudancas" (violam o contrato da skill) e "info".
Código de saída 1 se houver outras mudanças.
"""

import json
import sys
import zipfile

GEOM = ("x", "y", "z", "width", "height")
# Arquivos que o pbix-mcp regrava ou remove ao salvar sem mudar o conteúdo.
INFO_ONLY = {"SecurityBindings"}


def load_json(raw):
    for enc in ("utf-8-sig", "utf-16-le", "utf-16"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return None


def strip_legacy(layout):
    """Remove a geometria dos containers do Layout legado e devolve {id: geometria}."""
    geom = {}
    for sec in layout.get("sections", []):
        for vc in sec.get("visualContainers", []):
            cfg = vc.get("config")
            cfg_obj = json.loads(cfg) if isinstance(cfg, str) else (cfg or {})
            vid = f"{sec.get('displayName', sec.get('name'))}/{cfg_obj.get('name', '?')}"
            geom[vid] = {k: vc.pop(k, None) for k in GEOM}
            for lay in cfg_obj.get("layouts", []):
                lay.pop("position", None)
            if isinstance(cfg, str):
                vc["config"] = json.dumps(cfg_obj, sort_keys=True)
            elif cfg is not None:
                vc["config"] = cfg_obj
    return geom


def main(a_path, b_path):
    a, b = zipfile.ZipFile(a_path), zipfile.ZipFile(b_path)
    na, nb = set(a.namelist()), set(b.namelist())
    out = {"geometria": [], "outras_mudancas": [], "info": []}
    for n in sorted(na ^ nb):
        target = "info" if n in INFO_ONLY else "outras_mudancas"
        lado = "removido na cópia" if n in na else "novo na cópia"
        msg = f"{n}: {lado}"
        if n in INFO_ONLY:
            msg += " (o pbix-mcp descarta essa assinatura ao salvar; confirme que a cópia abre no Power BI Desktop)"
        out[target].append(msg)
    for n in sorted(na & nb):
        ra, rb = a.read(n), b.read(n)
        if ra == rb:
            continue
        ja, jb = load_json(ra), load_json(rb)
        if ja is None or jb is None:
            out["outras_mudancas"].append(f"{n}: conteúdo binário diferente")
            continue
        if n.endswith("visual.json"):
            pa, pb = ja.pop("position", {}), jb.pop("position", {})
            vid = n.split("/")[-2]
            extra_a = {k: v for k, v in pa.items() if k not in GEOM}
            extra_b = {k: v for k, v in pb.items() if k not in GEOM}
            if ja != jb or extra_a != extra_b:
                out["outras_mudancas"].append(f"{n}: mudou além da geometria")
            else:
                out["geometria"].append({"visual": vid,
                                         "antes": {k: pa.get(k) for k in GEOM},
                                         "depois": {k: pb.get(k) for k in GEOM}})
        elif n == "Report/Layout":
            ga, gb = strip_legacy(ja), strip_legacy(jb)
            if ja != jb:
                out["outras_mudancas"].append(f"{n}: mudou além da geometria")
            for vid in sorted(set(ga) | set(gb)):
                if ga.get(vid) != gb.get(vid):
                    out["geometria"].append({"visual": vid, "antes": ga.get(vid), "depois": gb.get(vid)})
        elif ja == jb:
            out["info"].append(f"{n}: só a formatação do JSON mudou")
        else:
            out["outras_mudancas"].append(f"{n}: conteúdo diferente")
    out["camada"] = [g["visual"] for g in out["geometria"]
                     if (g["antes"] or {}).get("z") != (g["depois"] or {}).get("z")]
    out["resultado"] = "ok" if not out["outras_mudancas"] else "falhou"
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if out["outras_mudancas"] else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
