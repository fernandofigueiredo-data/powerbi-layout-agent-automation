# Power BI Layout — plugin para o Claude Code

Reorganiza o layout de qualquer relatório Power BI (`.pbix`) com o
[pbix-mcp](https://pypi.org/project/pbix-mcp/): **grid de 12 colunas,
alinhamento, margens e calhas constantes, tamanho proporcional à importância e
leitura em Z** — KPIs e filtros no topo, tendências no meio, tabelas na base.

A regra que não se negocia: **só a geometria muda** (x, y, largura, altura).
Dados, medidas, filtros, formatação, cores, títulos, tema, bookmarks e tamanho
das páginas ficam intactos, e o resultado vai para uma cópia
`<nome>_reorganizado.pbix`. O original não é tocado.

## O que tem de diferente

| Recurso | O que faz |
|---|---|
| **Motor de layout** (`propor_layout.py`) | Calcula a nova disposição de forma determinística: grid por tamanho de página, faixas em Z, coluna de filtros para segmentadores em lista vertical, KPIs do mesmo tamanho, gráfico principal com 2/3 da largura, grupos, empilhados por bookmark, formas de fundo e navegação. Nada de contas de cabeça. |
| **Nota de layout 0–100** (`layout_check.py score`) | Pontua cada página em cinco critérios — alinhamento (25), espaço (20), integridade (20), hierarquia em Z (20) e proporção (15) — antes e depois. |
| **Inventário automático** (`inventario_pbix.py`) | Lê o `.pbix` como zip (PBIR e formato legado), sem gravar nada, e sugere a função de cada visual. |
| **Prova do contrato** (`compare_pbix.py`) | Compara original e cópia arquivo por arquivo e prova que só a geometria mudou. |
| **Hook guardião** | Pede confirmação antes de um `pbix_save` que sobrescreveria o original e, durante uma reorganização, antes de qualquer ferramenta do pbix-mcp que mude dados ou formatação. Nunca bloqueia: você decide. |
| **Auditor independente** (subagente) | Confere a cópia sem a memória da sessão que a fez: contrato, sobreposições, proposta aplicada e nota. |
| **Esquema antes/depois** (`preview_layout.py`) | HTML com cada visual colorido pela função, as colunas do grid e a nota por página. Tema claro e escuro. Veja [docs/exemplo_antes_depois.html](docs/exemplo_antes_depois.html). |

## Comandos

| Comando | Para quê |
|---|---|
| `/power-bi-layout-with-pbix-mcp:reorganizar <arquivo.pbix>` | Fluxo completo: inventário, diagnóstico, grid, motor, aplicação, cópia salva, auditoria e relatório. |
| `/power-bi-layout-with-pbix-mcp:diagnosticar <arquivo.pbix>` | Só leitura: nota atual, problemas por página e a nota que a reorganização alcançaria. |
| `/power-bi-layout-with-pbix-mcp:grid 1920x1080` | Grid de uma página: colunas, margens, calha, vãos de n colunas. |
| `/power-bi-layout-with-pbix-mcp:preview` | Regenera o esquema HTML antes/depois. |

A skill também dispara sozinha quando você pede algo como "organize o layout
deste dashboard" ou "alinhe os gráficos do relatório".

## Instalação

Pré-requisitos: [Claude Code](https://claude.com/claude-code) (testado na
versão 2.1.302; o hook usa o formato `command` + `args`) e
[uv](https://docs.astral.sh/uv/). O plugin sobe o pbix-mcp com `uvx`, que baixa
o pacote `pbix-mcp==0.9.153` do PyPI na primeira execução, e roda os scripts e
o hook com `uv run`, que funciona igual em macOS, Linux e Windows e baixa um
Python se faltar.

```bash
claude plugin marketplace add fernandofigueiredo-data/power-bi_layout_with_pbix-mcp
```

```bash
claude plugin install power-bi-layout-with-pbix-mcp@power-bi-layout-with-pbix-mcp
```

Para testar a partir de uma cópia local do repositório:

```bash
claude --plugin-dir ./plugins/power-bi_layout_with_pbix-mcp
```

Se você já tem o pbix-mcp configurado à parte, as ferramentas dele e as do
plugin convivem; a skill usa um servidor só do começo ao fim. Se você tinha a
skill `reorganizar-layout-power-bi` instalada solta, desative-a para ela não
disparar junto com a do plugin.

## Guardião (hook)

O plugin registra um hook `PreToolUse` para as ferramentas do pbix-mcp. Ele
nunca bloqueia; quando é preciso, devolve `ask` e o Claude Code pede a sua
confirmação:

- **Sempre**: antes de um `pbix_save` que sobrescreveria o .pbix aberto (sem
  `output_path`, ou com o caminho do próprio arquivo aberto) ou com
  `overwrite=true`.
- **Durante uma reorganização**: enquanto existir o arquivo `.pbi-layout-ativo`
  na raiz do projeto (`$CLAUDE_PROJECT_DIR`) ou no diretório de trabalho, antes
  de qualquer ferramenta que mude algo além da geometria (formatação, tema,
  filtros, dados, visuais). A skill liga o guardião no início e desliga no fim
  (`hook_guardiao.py --ligar` e `--desligar`). Se uma reorganização for
  interrompida, apague o arquivo `.pbi-layout-ativo` à mão.

Para desligar o guardião numa sessão, defina `PBI_LAYOUT_GUARDIAO=0` antes de
abrir o Claude Code. Como todo hook, ele é carregado no início da sessão:
depois de atualizar o plugin, reinicie o Claude Code.

## Como funciona

1. **Inventário** — `inventario_pbix.py` lê páginas e visuais e sugere funções
   (identidade, kpi, filtro, tendência, comparação, detalhe, secundário, nota,
   navegação, container). O Claude confere cada uma e elege o visual principal
   de cada página.
2. **Diagnóstico** — `layout_check.py check` e `score` sobre o estado atual.
3. **Proposta** — `propor_layout.py` calcula a nova geometria; o Claude revisa e
   ajusta casos ambíguos.
4. **Aplicação** — `pbix_move_visual` visual por visual (grupos com os filhos em
   coordenadas relativas) e `pbix_save` numa cópia, conferida com `pbix_doctor`.
5. **Auditoria** — o subagente `auditor-layout` roda `compare_pbix.py`, o
   inventário da cópia com `--herdar`, `layout_check.py` e a nota.
6. **Relatório** — grid adotado, nota antes → depois, tabela de mudanças,
   decisões, recomendações fora do escopo e o esquema HTML.

Grid padrão: 12 colunas, calha de 2 unidades-base, coluna sempre múltipla da
unidade e a sobra da largura nas margens laterais.

| Página | Unidade | Margens (cima/baixo, laterais) | Calha | Coluna |
|---|---|---|---|---|
| 1280×720 | 8 px | 24, 24 px | 16 px | 88 px |
| 1920×1080 | 12 px | 36, 36 px | 24 px | 132 px |
| 1024×768 (4:3) | 8 px | 24, 40 px | 16 px | 64 px |
| 320×240 (dica) | 4 px | 12, 20 px | 8 px | 16 px |

Qualquer outro tamanho: `/power-bi-layout-with-pbix-mcp:grid LxA`.

O pbix-mcp não renderiza páginas: abra a cópia no Power BI Desktop para a
conferência visual final (rótulos cortados, quebras de título).

## Desenvolvimento

```
.claude-plugin/marketplace.json          # este repositório é o marketplace
plugins/power-bi_layout_with_pbix-mcp/
  .claude-plugin/plugin.json
  .mcp.json                              # pbix-mcp embutido (uvx, versão fixada)
  skills/reorganizar-layout-power-bi/    # SKILL.md, references/, examples/ e scripts/
  commands/                              # reorganizar, diagnosticar, grid, preview
  agents/auditor-layout.md
  hooks/hooks.json                       # guardião (PreToolUse)
tests/                                   # unittest, sem dependências
  fixtures/casos_pbix.json               # inventário real de um .pbix de casos difíceis
```

```bash
uv run --no-project python -m unittest discover tests -v
```

```bash
claude plugin validate plugins/power-bi_layout_with_pbix-mcp
```

O plugin também passa pelo `plugin-validator` e pelo `skill-reviewer` do plugin
oficial [plugin-dev](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/plugin-dev).

O identificador do plugin e do marketplace é `power-bi-layout-with-pbix-mcp`
(kebab-case, como o manifesto exige); o repositório e a pasta mantêm o nome
`power-bi_layout_with_pbix-mcp`.

## Fundamentos

As regras vêm de Microsoft Learn (relatórios visualmente eficazes, dicas de
dashboard, linhas de grade), da regra 3-30-300 da SQLBI e dos padrões de
leitura em Z/F. Fontes e divergências entre elas em
[boas-praticas-layout.md](plugins/power-bi_layout_with_pbix-mcp/skills/reorganizar-layout-power-bi/references/boas-praticas-layout.md).

## Licença

MIT — veja [LICENSE](LICENSE).
