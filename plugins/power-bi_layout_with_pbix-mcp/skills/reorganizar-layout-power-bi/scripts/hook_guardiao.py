#!/usr/bin/env python3
"""Hook PreToolUse do plugin: protege o .pbix original e o contrato da reorganização.

Recebe no stdin o JSON do evento (tool_name, tool_input, cwd). Responde com
permissionDecision "ask" (o Claude Code pergunta ao usuário) quando:

1. `pbix_save` vai sobrescrever o arquivo aberto (output_path vazio) ou foi
   chamado com overwrite=true;
2. há uma reorganização em andamento (arquivo `.pbi-layout-ativo` no diretório
   de trabalho) e a ferramenta pode mudar algo além da geometria dos visuais.

Nunca bloqueia: o usuário sempre decide. Em qualquer outro caso não imprime
nada e a chamada segue normalmente. Para desligar, defina PBI_LAYOUT_GUARDIAO=0.
"""

import json
import os
import re
import sys

MARCADOR = ".pbi-layout-ativo"
NOME = re.compile(r"pbix-mcp__(pbix_\w+)$")

# Ferramentas que não alteram o relatório, ou que só mexem na geometria.
SEGURAS = {
    "pbix_open", "pbix_open_pbip", "pbix_close", "pbix_move_visual", "pbix_save",
    "pbix_diff", "pbix_data_diff", "pbix_doctor", "pbix_query_table", "pbix_document",
    "pbix_performance", "pbix_find_value", "pbix_table_stats", "pbix_extract_colors",
    "pbix_clear_dax_cache", "pbix_html_template", "pbix_create",
}
PREFIXOS_SEGUROS = ("pbix_get_", "pbix_list_", "pbix_evaluate_", "pbix_export_")


def responder(motivo):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": motivo,
    }}, ensure_ascii=False))


def decidir(evento):
    """Devolve o motivo para perguntar ao usuário, ou None para seguir."""
    m = NOME.search(evento.get("tool_name", ""))
    if not m:
        return None
    ferramenta = m.group(1)
    entrada = evento.get("tool_input") or {}
    if ferramenta == "pbix_save":
        destino = str(entrada.get("output_path") or "").strip()
        if not destino:
            return ("Guardião do layout: este pbix_save está sem output_path e vai SOBRESCREVER o .pbix "
                    "original. A reorganização deve gravar numa cópia (<nome>_reorganizado.pbix).")
        if entrada.get("overwrite") in (True, "true", "True", 1):
            return (f"Guardião do layout: pbix_save com overwrite=true vai substituir '{destino}' se ele já "
                    "existir. Prefira um sufixo numérico (_reorganizado_2.pbix).")
        return None
    ativo = os.path.exists(os.path.join(evento.get("cwd") or os.getcwd(), MARCADOR))
    if not ativo:
        return None
    if ferramenta in SEGURAS or ferramenta.startswith(PREFIXOS_SEGUROS):
        return None
    return (f"Guardião do layout: há uma reorganização em andamento ({MARCADOR}) e {ferramenta} pode mudar "
            "algo além da geometria (dados, formatação, filtros, visuais). O contrato da reorganização só "
            "permite mudar posição e tamanho. Confirme se é isso mesmo que você quer.")


def main():
    if os.environ.get("PBI_LAYOUT_GUARDIAO") == "0":
        return 0
    try:
        evento = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    motivo = decidir(evento)
    if motivo:
        responder(motivo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
