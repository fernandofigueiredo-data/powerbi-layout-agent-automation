# Changelog

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
