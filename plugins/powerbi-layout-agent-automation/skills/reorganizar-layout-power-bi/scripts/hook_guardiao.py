#!/usr/bin/env python3
"""Hook PreToolUse do plugin: protege o .pbix original e o contrato da reorganização.

Recebe no stdin o JSON do evento (tool_name, tool_input, cwd). Responde com
permissionDecision "ask" (o Claude Code pergunta ao usuário) quando:

1. `pbix_save` vai sobrescrever o arquivo aberto (output_path vazio ou igual ao
   arquivo que aquele alias abriu) ou foi chamado com overwrite=true;
2. há uma reorganização em andamento (arquivo `.pbi-layout-ativo` na raiz do
   projeto, $CLAUDE_PROJECT_DIR, ou no diretório de trabalho do evento) e a
   ferramenta pode mudar algo além da geometria dos visuais.

Nunca bloqueia: o usuário sempre decide. Em qualquer outro caso não imprime
nada e a chamada segue normalmente. Para desligar, defina PBI_LAYOUT_GUARDIAO=0.

Também liga e desliga a vigilância de uma reorganização, sem depender de touch
ou rm (que pedem aprovação e não existem no Windows):
  uv run --no-project --quiet hook_guardiao.py --ligar      cria o marcador
  uv run --no-project --quiet hook_guardiao.py --desligar   apaga o marcador
O marcador vai para $CLAUDE_PROJECT_DIR, ou para o diretório atual, ou para
--pasta, se informada.
"""

import json
import os
import re
import sys
import tempfile

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


def _registro(evento):
    """Arquivo temporário, por sessão, que liga cada alias ao .pbix que ele abriu."""
    sessao = re.sub(r"[^A-Za-z0-9_-]", "", str(evento.get("session_id") or "sem-sessao"))[:64]
    return os.path.join(tempfile.gettempdir(), f"pbi-layout-guardiao-{sessao}.json")


def _caminho(evento, caminho):
    base = evento.get("cwd") or os.getcwd()
    return os.path.realpath(os.path.join(base, os.path.expanduser(str(caminho))))


def _ler_aliases(evento):
    try:
        with open(_registro(evento), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _lembrar_abertura(evento, entrada):
    alias, arquivo = entrada.get("alias"), entrada.get("file_path")
    if not alias or not arquivo:
        return
    aliases = _ler_aliases(evento)
    aliases[str(alias)] = _caminho(evento, arquivo)
    try:
        with open(_registro(evento), "w", encoding="utf-8") as f:
            json.dump(aliases, f)
    except OSError:
        pass


def responder(motivo):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": motivo,
    }}, ensure_ascii=False))


def reorganizacao_ativa(evento):
    """O marcador vale na raiz do projeto ou no diretório de trabalho do evento."""
    pastas = (os.environ.get("CLAUDE_PROJECT_DIR"), evento.get("cwd") or os.getcwd())
    return any(p and os.path.exists(os.path.join(p, MARCADOR)) for p in pastas)


def decidir(evento):
    """Devolve o motivo para perguntar ao usuário, ou None para seguir."""
    m = NOME.search(evento.get("tool_name", ""))
    if not m:
        return None
    ferramenta = m.group(1)
    entrada = evento.get("tool_input") or {}
    if ferramenta in ("pbix_open", "pbix_open_pbip"):
        _lembrar_abertura(evento, entrada)
        return None
    if ferramenta == "pbix_save":
        destino = str(entrada.get("output_path") or "").strip()
        if not destino:
            return ("Guardião do layout: este pbix_save está sem output_path e vai SOBRESCREVER o .pbix "
                    "original. A reorganização deve gravar numa cópia (<nome>_reorganizado.pbix).")
        aberto = _ler_aliases(evento).get(str(entrada.get("alias")))
        if aberto and _caminho(evento, destino) == aberto:
            return (f"Guardião do layout: o output_path deste pbix_save é o próprio arquivo aberto ({aberto}) e "
                    "vai SOBRESCREVER o original. A reorganização deve gravar numa cópia "
                    "(<nome>_reorganizado.pbix).")
        if entrada.get("overwrite") in (True, "true", "True", 1):
            return (f"Guardião do layout: pbix_save com overwrite=true vai substituir '{destino}' se ele já "
                    "existir. Prefira um sufixo numérico (_reorganizado_2.pbix).")
        return None
    if not reorganizacao_ativa(evento):
        return None
    if ferramenta in SEGURAS or ferramenta.startswith(PREFIXOS_SEGUROS):
        return None
    return (f"Guardião do layout: há uma reorganização em andamento ({MARCADOR}) e {ferramenta} pode mudar "
            "algo além da geometria (dados, formatação, filtros, visuais). O contrato da reorganização só "
            "permite mudar posição e tamanho. Confirme se é isso mesmo que você quer.")


def marcador(argv):
    """Modo de linha de comando: --ligar ou --desligar a vigilância."""
    pasta = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if "--pasta" in argv:
        pasta = argv[argv.index("--pasta") + 1]
    caminho = os.path.join(pasta, MARCADOR)
    if "--ligar" in argv:
        with open(caminho, "w", encoding="utf-8"):
            pass
        print(f"Guardião ligado: {caminho}")
    else:
        if os.path.exists(caminho):
            os.remove(caminho)
        print(f"Guardião desligado: {caminho} removido")
    return 0


def main():
    if "--ligar" in sys.argv or "--desligar" in sys.argv:
        return marcador(sys.argv[1:])
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
