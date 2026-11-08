---
description: Diagnóstico do layout de um relatório Power BI (.pbix) — nota 0–100 por página, problemas de alinhamento, margem, calha e hierarquia — sem alterar o .pbix
argument-hint: "<caminho do .pbix>"
allowed-tools: Bash(uv run:*), Read, Glob, Edit, Write
---

Faça só o diagnóstico de layout do relatório indicado. **O .pbix não é
alterado**: os scripts o leem como zip. Os únicos arquivos escritos são os de
trabalho, na pasta `layout_<nome>/` ao lado do .pbix; não escreva em nenhum
outro lugar.

Arquivo pedido (pode estar vazio): `$ARGUMENTS`. Se vier vazio, procure `.pbix`
no diretório de trabalho (um só: use; vários: pergunte; nenhum: peça o caminho).

Scripts: `${CLAUDE_PLUGIN_ROOT}/skills/reorganizar-layout-power-bi/scripts/`.
Rode cada um com `uv run --no-project --quiet "<caminho completo>" <argumentos>`,
uma chamada por comando, sem variável e sem `&&`.

1. Rode `inventario_pbix.py <arquivo> --saida layout_<nome>/layout_antes.json`
   (o script cria a pasta `layout_<nome>/` ao lado do arquivo).
2. Revise as funções sugeridas (`role`) e o visual principal de cada página
   com a tabela de funções da skill **reorganizar-layout-power-bi**, corrigindo
   o JSON onde a sugestão estiver errada.
3. Rode `layout_check.py check layout_<nome>/layout_antes.json` e
   `layout_check.py score layout_<nome>/layout_antes.json`.
4. Rode `propor_layout.py layout_<nome>/layout_antes.json --saida layout_<nome>/layout_proposto.json`
   para estimar o ganho e depois
   `layout_check.py score layout_<nome>/layout_proposto.json --before layout_<nome>/layout_antes.json`.
5. Gere `preview_layout.py layout_<nome>/layout_antes.json layout_<nome>/layout_proposto.json layout_<nome>/diagnostico.html`.

Responda com: nota atual por página e geral; os três problemas mais graves de
cada página, em uma linha cada; a nota que a reorganização alcançaria; o caminho
completo do HTML. Termine oferecendo rodar `/power-bi-layout-with-pbix-mcp:reorganizar`
no mesmo arquivo.
