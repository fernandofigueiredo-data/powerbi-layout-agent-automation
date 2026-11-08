---
description: Diagnóstico do layout de um relatório Power BI (.pbix) — nota 0–100 por página, problemas de alinhamento, margem, calha e hierarquia — sem alterar nada
argument-hint: "<caminho do .pbix>"
---

Faça só o diagnóstico de layout do relatório indicado. **Nada é gravado no
.pbix**: este comando apenas lê.

Arquivo pedido (pode estar vazio): `$ARGUMENTS` — se vazio, procure `.pbix` no
diretório de trabalho (um só: use; vários: pergunte).

Scripts: `${CLAUDE_PLUGIN_ROOT}/skills/reorganizar-layout-power-bi/scripts/`.

1. Crie a pasta `layout_<nome>/` ao lado do arquivo e rode
   `uv run --no-project --quiet <scripts>/inventario_pbix.py <arquivo> --saida layout_<nome>/layout_antes.json`.
2. Revise as funções sugeridas (`role`) e o visual principal de cada página
   com as regras da tabela de funções da skill **reorganizar-layout-power-bi**,
   corrigindo o JSON onde a sugestão estiver errada.
3. Rode `layout_check.py check` e `layout_check.py score` sobre o inventário.
4. Rode `propor_layout.py` sobre ele para estimar o ganho: depois, rode
   `layout_check.py score layout_proposto.json --before layout_antes.json`.
5. Gere `preview_layout.py layout_antes.json layout_proposto.json layout_<nome>/diagnostico.html`.

Responda com: nota atual por página e geral; os três problemas mais graves de
cada página em uma linha cada; a nota que a reorganização alcançaria; o caminho
do HTML. Termine oferecendo rodar `/reorganizar` no mesmo arquivo.
