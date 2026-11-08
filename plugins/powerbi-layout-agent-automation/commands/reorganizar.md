---
description: Reorganiza o layout de um relatório Power BI (.pbix) — grid, alinhamento, margens, tamanho proporcional e leitura em Z — numa cópia, sem tocar em dados ou formatação
argument-hint: "<caminho do .pbix>"
allowed-tools: Bash(uv run:*), Read, Glob, Grep, Write, Edit, Agent, Task, mcp__plugin_powerbi-layout-agent-automation_pbix-mcp
---

Reorganize o layout do relatório Power BI indicado, seguindo a skill
**reorganizar-layout-power-bi** deste plugin do começo ao fim (carregue-a
agora, se ainda não estiver carregada).

Arquivo pedido (pode estar vazio): `$ARGUMENTS`

- Se vier vazio, procure arquivos `.pbix` no diretório de trabalho. Um só:
  use-o. Mais de um: pergunte qual. Nenhum: peça o caminho.
- Os scripts estão em `${CLAUDE_PLUGIN_ROOT}/skills/reorganizar-layout-power-bi/scripts/`
  e rodam com `uv run --no-project --quiet "<caminho completo>" <argumentos>`,
  uma chamada por comando, sem variável e sem `&&`.
- O resultado vai para `<nome>_reorganizado.pbix`, na mesma pasta; o original
  não é sobrescrito.
- Ligue o guardião no início com `hook_guardiao.py --ligar` e desligue-o assim
  que a cópia estiver salva e o HTML gerado. Se o fluxo parar no meio,
  desligue-o antes de encerrar.
- Use o motor (`propor_layout.py`) para calcular a nova disposição, revise a
  proposta e só então aplique com `pbix_move_visual`.
- Depois de salvar a cópia, rode `pbix_doctor` nela. Em seguida, nesta ordem:
  inventário da cópia com `--herdar`, `antes_depois.html`, `hook_guardiao.py
  --desligar` e, por último, a conferência pelo subagente `auditor-layout`,
  esperando o veredito antes do relatório.
- Termine com o relatório final da skill, a nota de layout antes → depois e o
  caminho do `antes_depois.html`.
