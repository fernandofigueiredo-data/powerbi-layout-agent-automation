---
description: Gera o esquema visual HTML do layout antes e depois (colunas do grid, cores por função, nota 0–100)
argument-hint: "[layout_antes.json] [layout_depois.json]"
---

Gere o esquema visual do layout. Argumentos (podem estar vazios): `$ARGUMENTS`

- Com dois JSONs: antes e depois.
- Com um: só o estado atual.
- Vazio: procure `layout_antes.json` e, nesta ordem, `layout_depois.json` ou
  `layout_proposto.json` nas pastas `layout_*/` do diretório de trabalho; se
  houver mais de uma pasta, pergunte qual.

Rode:

```
uv run --no-project --quiet ${CLAUDE_PLUGIN_ROOT}/skills/reorganizar-layout-power-bi/scripts/preview_layout.py <antes.json> [<depois.json>] <pasta>/antes_depois.html
```

Abra o HTML para o usuário e diga em uma linha a nota antes → depois.
