# Changelog

## 0.3.0 — 2026-11-08

- Repositório, plugin, marketplace e pasta do plugin renomeados para
  `powerbi-layout-agent-automation`. Os comandos passam a ser
  `/powerbi-layout-agent-automation:...` e o prefixo das ferramentas do
  servidor embutido, `mcp__plugin_powerbi-layout-agent-automation_pbix-mcp__`.
- Quem instalou a 0.2.0 precisa remover o plugin antigo e instalar de novo.
- Novo `docs/regras-de-layout.md`, com todas as regras aplicadas a um .pbix
  escritas para quem usa o plugin. O README ganhou o problema que o plugin
  resolve, o resultado medido no exemplo (nota 48,9 → 100) e um resumo das
  regras.

## 0.2.0 — 2026-11-08

Revisão com o plugin-dev (plugin-validator, skill-reviewer e validadores de
agente e de hook) e teste de ponta a ponta com um .pbix de casos difíceis.

- Identificador do plugin e do marketplace em kebab-case:
  `power-bi-layout-with-pbix-mcp` (comandos `/power-bi-layout-with-pbix-mcp:...`).
- Grid: coluna sempre múltipla da unidade-base, com a sobra nas margens
  laterais; páginas 4:3, carta e tamanhos livres passam a alinhar à unidade.
- Motor: KPIs que não cabem ao lado da coluna de filtros usam as 12 colunas
  (a coluna começa abaixo deles); KPIs demais quebram em linhas equilibradas;
  botões de navegação na ordem do autor; filhos de grupo marcados com
  `aplicar_filho`; limitação para tabela estreita demais para os campos; a
  proposta sai sem as marcas `*_sugerido`.
- `inventario_pbix.py --herdar`: gera o inventário da cópia com as decisões da
  proposta, sem edição manual de JSON.
- `compare_pbix.py`: lista em `camada` os visuais cujo `z` mudou.
- `layout_check.py`, `propor_layout.py` e `preview_layout.py` aceitam as
  mesmas opções de grid; o preview aceita `--proposta` e `--allow-gap`, e a
  nota do HTML é a mesma do relatório.
- Hook guardião: marcador também em `$CLAUDE_PROJECT_DIR`; `--ligar` e
  `--desligar` no próprio script (sem `touch`/`rm`, que pedem aprovação e não
  existem no Windows); ativação documentada no README. Testado numa sessão real:
  `pbix_save` sem destino e `pbix_rename_page` durante a reorganização são
  interceptados, e o arquivo fica intacto.
- Convenção de chamada dos scripts: caminho completo, uma chamada por comando,
  sem variável nem `&&`, para que uma única permissão de `uv run` cubra o fluxo
  inteiro (incluindo o auditor). `/reorganizar` declara `allowed-tools`.
- Mensagens do motor citam o visual pelo título e tipo, não só pelo id.
- O hook também pergunta antes de um `pbix_save` cujo `output_path` é o próprio
  arquivo que aquele alias abriu.
- Os scripts criam a pasta de saída (`layout_<nome>/`), sem depender de
  `mkdir`; no fim do fluxo, o HTML é gerado e o guardião desligado antes do
  auditor, para que a sessão não precise de aprovações depois do veredito.
- Motor à prova de casos-limite (muitas identidades no topo, mais botões do
  que colunas): degrada com limitação registrada em vez de quebrar.
- Agente auditor no formato do plugin-dev (`model`, `color`, exemplos de
  acionamento, "Quando acionar"); usa `--herdar` e confere `camada`.
- SKILL.md mais enxuta (regras detalhadas em `references/regras-de-layout.md`),
  descrição em terceira pessoa com frases de gatilho e limites, convenção
  única de caminho dos scripts, limpeza do marcador se o fluxo parar.
- `examples/` com um inventário e a proposta gerada para ele.
- Testes: 46 (grid 4:3 e tamanhos livres, casos difíceis de um .pbix real,
  KPIs em linhas, tabela estreita, `--herdar`, camada, marcador do projeto e
  por script, preview). Ponta a ponta: `/reorganizar` numa sessão real com o
  plugin carregado, sobre um relatório PBIR (nota 51,2 → 100, contrato ok,
  `pbix_doctor` sem falhas), e um .pbix de casos difíceis com grupo
  redimensionado, empilhados, forma de fundo, 6 KPIs, página 4:3 e dica
  (64,5 → 100).

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
