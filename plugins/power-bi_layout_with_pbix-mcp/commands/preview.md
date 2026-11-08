---
description: Gera o esquema visual HTML do layout antes e depois (colunas do grid, cores por função, nota 0–100)
argument-hint: "[layout_antes.json] [layout_depois.json]"
allowed-tools: Bash(uv run:*), Read, Glob
---

Gere o esquema visual do layout. Argumentos (podem estar vazios): `$ARGUMENTS`

- Com dois JSONs: antes e depois.
- Com um: só o estado atual.
- Vazio: procure `layout_antes.json` e, nesta ordem, `layout_depois.json` ou
  `layout_proposto.json` nas pastas `layout_*/` do diretório de trabalho; se
  houver mais de uma pasta, pergunte qual.

Rode:

```
uv run --no-project --quiet "${CLAUDE_PLUGIN_ROOT}/skills/reorganizar-layout-power-bi/scripts/preview_layout.py" <antes.json> [<depois.json>] <pasta>/antes_depois.html [--proposta <pasta>/layout_proposto.json]
```

Passe `--proposta` quando o depois for `layout_depois.json` e existir um
`layout_proposto.json` na mesma pasta: é de lá que vêm as decisões e as
limitações listadas no fim do HTML. Se a proposta tiver formas de fundo
(`z_atras`), acrescente `--allow-gap` com a unidade-base da página (8 em
1280×720), para que a nota do HTML seja a mesma do relatório.

Informe o caminho completo do HTML e diga em uma linha a nota antes → depois.
