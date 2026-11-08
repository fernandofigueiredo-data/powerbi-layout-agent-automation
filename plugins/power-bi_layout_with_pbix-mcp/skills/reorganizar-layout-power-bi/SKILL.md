---
name: reorganizar-layout-power-bi
description: Esta skill deve ser usada quando o usuário pedir para "reorganizar o layout", "organizar o dashboard", "alinhar os visuais", "arrumar a disposição dos gráficos", "aplicar um grid" ou "diagramar as páginas" de um relatório Power BI (.pbix), ou entregar um .pbix pedindo só melhoria da composição visual, mesmo sem citar pbix-mcp ou grid. Muda apenas posição e tamanho dos visuais (grid de 12 colunas, leitura em Z) e grava numa cópia. Não serve para alterar dados, medidas, cores, formatação ou criar visuais.
---

# Reorganizar o layout de relatórios Power BI

Redistribuir os visuais de cada página de um relatório Power BI pronto sobre um grid consistente, seguindo uma hierarquia de leitura. O conteúdo foi aprovado por quem construiu o relatório; o trabalho é de diagramação. Por isso só a geometria dos visuais muda: x, y, largura, altura e, só para formas de fundo, a ordem de camada.

## Contrato: o que muda e o que fica

Pode mudar: posição (x, y), largura e altura de visuais e grupos; ordem de camada (z) apenas de formas que servem de fundo a um bloco.

Fica intacto: dados, tabelas, relacionamentos, medidas, consultas, campos e agregações, filtros, tipos de visual, formatação, cores, títulos, tema, interações, bookmarks, tamanho e tipo das páginas, layout para celular. Nenhum visual é criado, removido ou oculto.

O motivo é prático: quem pede uma reorganização quer o mesmo relatório mais legível. Qualquer alteração fora da geometria obriga o autor a reauditar o conteúdo, o que anula o ganho.

## Pré-requisitos

- **pbix-mcp conectado.** O plugin traz o seu, na versão fixada no `.mcp.json` do plugin. Usar um só servidor do começo ao fim (os prefixos possíveis estão em `references/pbix-mcp-operacoes.md`), porque o alias aberto num não existe no outro. Sem nenhum conectado, dizer o que falta e parar. Nunca editar o .pbix descompactando ou reescrevendo o arquivo por outros meios: o risco de corromper o modelo de dados é real.
- **Scripts** na pasta `scripts/` ao lado deste arquivo (`${CLAUDE_PLUGIN_ROOT}/skills/reorganizar-layout-power-bi/scripts/`), só com a biblioteca padrão do Python. Rodar cada um com `uv run --no-project --quiet "<caminho completo do script>" <argumentos>`, que funciona igual em macOS, Linux e Windows e baixa um Python se faltar. Cada chamada vai sozinha, com o caminho escrito por inteiro: sem atribuir variável (`S=...`) e sem encadear com `&&`, porque assim uma única permissão para `uv run` cobre todas as chamadas e o usuário não é interrompido a cada passo. Não usar `python3` direto (no Windows ele costuma não existir) nem trechos avulsos de Python na linha de comando para inspecionar JSON: os scripts já imprimem o que é preciso, e os JSONs podem ser lidos com a ferramenta de leitura.

| Script | Para quê |
|---|---|
| `inventario_pbix.py` | lê o .pbix como zip, sem gravar nada, e gera o inventário com funções sugeridas; com `--herdar`, copia as decisões de uma proposta |
| `propor_layout.py` | motor de layout: calcula a nova disposição a partir do inventário |
| `layout_check.py` | `grid` (colunas), `check` (margem, calha, sobreposição, hierarquia) e `score` (nota de 0 a 100) |
| `compare_pbix.py` | prova que original e cópia diferem só na geometria dos visuais |
| `preview_layout.py` | esquema HTML do antes e depois, com as colunas do grid e a nota |
| `_grid.py` | biblioteca interna: cálculo do grid, usada pelos outros scripts |
| `hook_guardiao.py` | o hook guardião do plugin (`hooks/hooks.json`); à mão, só `--ligar` e `--desligar` a vigilância |

Os scripts que dependem do grid (`layout_check.py`, `propor_layout.py`, `preview_layout.py`) aceitam as mesmas opções `--margin --gutter --base --columns`; sem elas, usam o grid padrão de cada página.

Referências, para ler quando o passo pedir:
- `references/pbix-mcp-operacoes.md`: sequência de ferramentas, armadilhas (grupos, índices, camada) e formato dos JSONs. Ler antes da primeira chamada ao pbix-mcp.
- `references/regras-de-layout.md`: as regras que o motor aplica e que valem para ajustes manuais. Ler ao revisar a proposta.
- `references/boas-praticas-layout.md`: fundamentos, fontes e divergências entre elas. Ler para justificar uma decisão ou resolver um caso que as regras não cobrem.
- `examples/layout_antes.json` e `examples/layout_proposto.json`: um inventário e a proposta que o motor gerou para ele.

Os arquivos de trabalho (`layout_antes.json`, `layout_proposto.json`, `layout_depois.json`, `antes_depois.html`) ficam numa pasta `layout_<nome_original>/` ao lado do .pbix; os scripts criam a pasta ao gravar, sem precisar de `mkdir`.

## Fluxo de trabalho

### 1. Identificar o arquivo, proteger o original e ligar o guardião

Usar o .pbix indicado no pedido; com mais de um candidato e nenhuma indicação, perguntar. O resultado vai para `<nome_original>_reorganizado.pbix`, na mesma pasta; o original só é sobrescrito se o usuário pedir expressamente. Seguir da análise à aplicação sem pedir confirmação a cada etapa: o usuário pediu o trabalho inteiro, e decisões ambíguas vão para o relatório final.

Ligar o guardião com `hook_guardiao.py --ligar`, que cria o marcador `.pbi-layout-ativo` na raiz do projeto (`$CLAUDE_PROJECT_DIR`). Enquanto ele existir, o hook guardião pede confirmação ao usuário antes de qualquer ferramenta do pbix-mcp que mude algo além da geometria; antes de um `pbix_save` que sobrescreveria o arquivo aberto, pede sempre. Se o usuário recusar, não insistir: ajustar o plano. Se o fluxo parar no meio, por erro ou a pedido do usuário, rodar `hook_guardiao.py --desligar` antes de encerrar.

### 2. Inventariar

Rodar `inventario_pbix.py <arquivo>.pbix --saida layout_<nome>/layout_antes.json`. Ele registra cada página (nome, tipo, tamanho) e cada visual: nome interno (`id`, estável entre original e cópia), tipo, título, campos, posição absoluta (filhos de grupo já convertidos), grupo, estado oculto e, em segmentadores, o modo (`Dropdown` ou `Basic`) e o campo.

Abrir o arquivo no pbix-mcp (`pbix_open`) e conferir o inventário com `pbix_get_pages` e `pbix_get_visual_positions`: as posições têm de bater. Se não baterem, o pbix-mcp manda; corrigir o JSON. Para segmentadores em lista vertical, contar os itens que vão aparecer e gravar em `items`, porque a quantidade decide se a lista cabe na faixa superior: `pbix_table_stats(alias, tabela)` dá a contagem de valores distintos das colunas de texto; para colunas numéricas, ler os valores com `pbix_query_table`.

### 3. Classificar cada visual por função

O inventário traz uma função sugerida (`role`, com `role_sugerido: true`), conforme o tipo do visual. Conferir cada uma pelo que o arquivo mostra (tipo, título, campos), porque a função decide a faixa da página:

| Função | Tipos internos comuns (confirmar no arquivo) | Faixa |
|---|---|---|
| identidade | `image` (logotipo), `textbox` de título | canto superior esquerdo, compacta; título largo vira faixa de cabeçalho |
| kpi | `card`, `cardVisual`, `multiRowCard`, `kpi`, `gauge` | faixa superior |
| filtro | `slicer`, `advancedSlicerVisual`, `listSlicer`, `textSlicer` | faixa superior, ou coluna de filtros se a lista não couber |
| tendencia | `lineChart`, `areaChart`, `ribbonChart`, combos de linha e coluna | meio |
| comparacao | `barChart`, `columnChart`, `clusteredBarChart` e variações | meio |
| detalhe | `tableEx`, `table` (tabela), `pivotTable`, `matrix` (matriz) | base |
| secundario | mapas, pizza, rosca, treemap, dispersão, funil, cascata e demais | base |
| nota | `textbox` de fonte, metodologia ou rodapé | base, ou o fim da coluna de filtros |
| navegacao | `actionButton`, `pageNavigator`, `bookmarkNavigator` | linha fixa no rodapé, igual em todas as páginas |
| container | `shape` ou `basicShape` usada como fundo de um bloco | acompanha o bloco que envolve |

Quando o papel não for evidente (uma rosca que é o principal indicador da página, uma tabela de três linhas que funciona como KPI), decidir pela função que o visual cumpre e registrar a decisão. A tabela orienta, a função manda.

Em cada página, eleger o visual mais importante (`principal: true`) e declarar o critério (o indicador que responde à pergunta central da página, ou o KPI de maior agregação). O inventário sugere o primeiro KPI na ordem de leitura. Confirmar também os empilhamentos sugeridos (`stack`): visuais com a mesma geometria exata costumam alternar por bookmark (`pbix_get_bookmarks` ajuda), mas pode ser sobreposição acidental. As marcas `*_sugerido` não precisam ser apagadas: a proposta sai sem elas.

### 4. Diagnosticar a disposição atual

Rodar `layout_check.py check layout_antes.json` e `layout_check.py score layout_antes.json`. Listar, por página, os problemas: bordas desalinhadas, sobreposições, espaçamentos irregulares, visuais encostados na borda, mesma função com tamanhos diferentes e desvios da leitura em Z. O diagnóstico e a nota de partida justificam cada mudança no relatório.

### 5. Declarar o grid

Declarar um grid para cada tamanho de página: unidade-base (margem, calha e dimensões são múltiplos dela), calha constante e 12 colunas, que dividem em 2, 3, 4 e 6 blocos iguais. No padrão dos scripts, a coluna é sempre múltipla da unidade e a sobra da largura vai para as margens laterais:

| Página | Unidade-base | Margens (cima/baixo, laterais) | Calha | Coluna (12 col.) |
|---|---|---|---|---|
| 1280×720 | 8 px | 24 px, 24 px | 16 px | 88 px |
| 1920×1080 | 12 px | 36 px, 36 px | 24 px | 132 px |
| 1024×768 (4:3) | 8 px | 24 px, 40 px | 16 px | 64 px |
| 320×240 (dica) | 4 px | 12 px, 20 px | 8 px | 16 px |

Para outros tamanhos, rodar `layout_check.py grid --width W --height H`: ele devolve a borda de cada coluna, a largura de cada vão de n colunas e as margens laterais. Valores diferentes do padrão vão, iguais, para todos os scripts (`--margin --gutter --base --columns`).

### 6. Calcular a nova disposição com o motor e revisar

Rodar `propor_layout.py layout_antes.json --saida layout_proposto.json`. O motor aplica as regras de `references/regras-de-layout.md` de forma determinística e devolve a geometria nova de cada visual (com a original em `de`), o grid de cada página e as listas `decisoes` e `limitacoes`. Ele existe para que as contas de grid não sejam feitas de cabeça.

A proposta é ponto de partida, não ordem. Revisá-la contra as regras e contra o que se sabe do relatório; quando um caso pedir outra solução (dois gráficos de mesma importância que o motor desigualou por área, por exemplo), editar `layout_proposto.json` mantendo as bordas nas colunas do grid e registrar a decisão. Rodar `layout_check.py check` na proposta antes de aplicar (com `--allow-gap` igual à unidade-base se houver formas de fundo): ela precisa sair sem erros.

### 7. Aplicar e salvar

Aplicar a proposta visual por visual com `pbix_move_visual`, na mesma sessão aberta do passo 2. O `visual_index` é o da lista de `pbix_get_page_visuals`; ligar cada `id` da proposta ao índice pelo nome interno que a lista mostra (`name=...`), nunca pela ordem do JSON. Passar `-1` em `z`, exceto para formas de fundo com `z_atras`, que vão para trás do bloco.

Grupos: mover o container do grupo com a geometria absoluta da proposta. Filhos com `aplicar_filho: true` (grupo redimensionado) recebem depois `x = rel_x`, `y = rel_y`, `width` e `height` da proposta, em coordenadas relativas ao grupo; filhos com `aplicar_filho: false` não precisam ser movidos. Reler com `pbix_get_visual_positions` para confirmar.

Salvar em `<nome_original>_reorganizado.pbix` com `overwrite=False`; se já existir, usar `_reorganizado_2.pbix`. Salvar com outro nome não limpa as alterações pendentes do original aberto: fechar com `force=True` depois de confirmar que a cópia foi gravada. Abrir a cópia com outro alias, rodar `pbix_doctor` e fechar.

### 8. Gerar o esquema, desligar o guardião e conferir com o auditor

Nesta ordem, para que tudo o que pede ferramenta aconteça antes de a conferência começar:

1. `inventario_pbix.py <cópia>.pbix --herdar layout_proposto.json --saida layout_<nome>/layout_depois.json`: o inventário da cópia salva, com as funções e decisões da proposta (`sem_correspondencia` precisa vir vazio).
2. `preview_layout.py layout_<nome>/layout_antes.json layout_<nome>/layout_depois.json layout_<nome>/antes_depois.html --proposta layout_<nome>/layout_proposto.json`, com as mesmas opções de grid e `--allow-gap` da proposta.
3. `hook_guardiao.py --desligar`: a aplicação acabou, e daqui em diante nada mais mexe no .pbix.
4. Delegar a conferência ao subagente `auditor-layout` do plugin, com os caminhos do original, da cópia e de `layout_proposto.json`, e esperar o veredito antes do relatório. Ele trabalha sem a memória desta sessão: lê a cópia direto do arquivo, roda `compare_pbix.py`, `layout_check.py check` e `score` e compara com a proposta.

Sem o subagente, fazer a conferência aqui:

- `compare_pbix.py <original>.pbix <cópia>.pbix` precisa dar `ok`, com mudanças só em `geometria`, e cada visual listado em `camada` precisa ser forma de fundo. Qualquer item em `outras_mudancas` viola o contrato: refazer a partir do original. O `pbix_diff` do pbix-mcp não compara posições e responde "sem mudanças" mesmo depois de uma reorganização correta, então não basta.
- `layout_check.py check layout_<nome>/layout_depois.json --before layout_<nome>/layout_antes.json` e `layout_check.py score` com os mesmos argumentos. Erros têm de ser corrigidos; avisos podem ser aceitos com justificativa.

Usar sempre os mesmos `--allow-gap` e opções de grid da proposta. Se o auditor ou a conferência apontarem erros, ligar o guardião de novo, corrigir com `pbix_move_visual` a partir de uma nova abertura da cópia, salvar como `_reorganizado_2.pbix` e repetir este passo.

## Relatório final

Encerrar com um relatório curto, em português, nesta ordem:

1. **Grid adotado**: tamanho da página, unidade-base, margens, calha, colunas.
2. **Nota de layout**: geral e por página, antes → depois.
3. **Por página**: o visual mais importante e o critério, e os problemas da disposição original, em até três frases.
4. **Antes e depois**: por página, uma tabela com visual (tipo e título), posição e tamanho originais, posição e tamanho novos.
5. **Decisões em casos ambíguos**: uma linha cada, com as `decisoes` do motor que importam para o usuário e os ajustes manuais feitos na proposta.
6. **Conferência**: veredito do auditor, resultado do `compare_pbix.py`, do `pbix_doctor` e do `layout_check.py`, com a contagem de desvios antes e depois.
7. **Recomendações fora do escopo**: o que melhoraria o relatório mas exige mudar formatação ou configuração (trocar o modo de um segmentador, ajustar a ordem de tabulação à nova ordem de leitura). Incluir as `limitacoes` do motor. A skill não aplica, só registra.
8. **Arquivos**: caminho completo da cópia salva e do `antes_depois.html`.

Lembrar o usuário de abrir a cópia no Power BI Desktop para a conferência visual: o pbix-mcp trabalha com coordenadas e não renderiza a página, então rótulos cortados e quebras de título só aparecem na tela.
