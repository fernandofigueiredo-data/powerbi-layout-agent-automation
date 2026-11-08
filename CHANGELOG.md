# Changelog

## 0.1.1 — 2026-11-07

Correções encontradas ao rodar o motor nos .pbix reais.

- Título largo dentro das margens (metade da largura ou mais) vira faixa de
  cabeçalho na largura do grid, com data ou subtítulo à direita; o KPI
  principal volta para o canto, logo abaixo.
- Segmentador em lista vertical só vai para a coluna de filtros se não couber
  na altura da faixa superior; os que cabem ficam ao lado dos KPIs.
- Filtros da faixa só vão para a coluna quando não cabem na linha dos KPIs ou
  a página não tem KPI; um campo que vai para a coluna numa página vai em todas
  (duas passadas no motor).
- KPI até um terço da largura quando divide a linha; filtro até 3 colunas.
- Conferência: para filtros, mesma linha é mesmo topo e mesma base.
- Hook, comandos, agente e skill rodam os scripts com `uv run --no-project`
  em vez de `python3`, que não existe no Windows padrão.

## 0.1.0 — 2026-11-07

Primeira versão, a partir da skill `reorganizar-layout-power-bi`.

- Skill de reorganização com fluxo novo: inventário automático, motor de
  layout, auditoria independente e nota de layout no relatório final.
- `inventario_pbix.py`: lê PBIR e legado sem gravar nada e sugere funções.
- `propor_layout.py`: motor de layout determinístico (grid, faixas em Z, coluna
  de filtros, grupos, empilhados, formas de fundo, navegação, páginas de dica).
- `layout_check.py score`: nota de 0 a 100 em cinco critérios; grid padrão por
  tamanho de página em `grid`, `check` e `score`.
- `preview_layout.py`: colunas do grid, nota por página, decisões e tema escuro.
- Hook guardião (PreToolUse) e subagente `auditor-layout`.
- Comandos `/reorganizar`, `/diagnosticar`, `/grid` e `/preview`.
- pbix-mcp 0.9.153 embutido via `uvx`.
