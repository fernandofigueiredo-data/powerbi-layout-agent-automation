---
description: Reorganiza o layout de um relatório Power BI (.pbix) — grid, alinhamento, margens, tamanho proporcional e leitura em Z — numa cópia, sem tocar em dados ou formatação
argument-hint: "<caminho do .pbix>"
---

Reorganize o layout do relatório Power BI indicado, seguindo a skill
**reorganizar-layout-power-bi** deste plugin do começo ao fim (carregue-a
agora, se ainda não estiver carregada).

Arquivo pedido (pode estar vazio): `$ARGUMENTS`

- Se vier vazio, procure arquivos `.pbix` no diretório de trabalho. Um só:
  use-o. Mais de um: pergunte qual. Nenhum: peça o caminho.
- Os scripts estão em `${CLAUDE_PLUGIN_ROOT}/skills/reorganizar-layout-power-bi/scripts/`.
- O resultado vai para `<nome>_reorganizado.pbix`, na mesma pasta; o original
  não é sobrescrito.
- Crie o marcador `.pbi-layout-ativo` no início e apague no fim, para o
  guardião do plugin vigiar a reorganização.
- Use o motor (`propor_layout.py`) para calcular a nova disposição, revise a
  proposta e só então aplique com `pbix_move_visual`.
- Delegue a conferência final ao subagente `auditor-layout`.
- Termine com o relatório final da skill, a nota de layout antes → depois e o
  caminho do `antes_depois.html`.
