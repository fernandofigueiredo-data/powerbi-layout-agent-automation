---
description: Calcula o grid de uma página Power BI — colunas, margens, calha e largura de cada vão de n colunas
argument-hint: "<LarguraxAltura> [margem calha colunas] — ex.: 1920x1080"
---

Calcule o grid pedido: `$ARGUMENTS` (vazio = 1280x720).

Leia largura e altura do primeiro argumento (`1920x1080`, `1920 1080` ou
`1920×1080`); margem, calha e número de colunas, se vierem, nessa ordem. Rode:

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/reorganizar-layout-power-bi/scripts/layout_check.py grid --width L --height A [--margin M --gutter G --columns N]
```

Mostre uma tabela curta: unidade-base, margem (e margem direita, se diferente),
calha, largura da coluna e a largura dos vãos de 2, 3, 4, 6, 8 e 12 colunas,
mais o x inicial de cada coluna. Se o script avisar que a coluna não é inteira,
explique o arredondamento e sugira uma combinação de margem e calha que dê
coluna inteira.
