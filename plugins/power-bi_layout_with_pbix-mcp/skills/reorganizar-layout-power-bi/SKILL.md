---
name: reorganizar-layout-power-bi
description: Reorganiza a disposição (posição e tamanho) dos visuais de todas as páginas de um relatório Power BI (.pbix) com o pbix-mcp, aplicando grid, alinhamento, margens, tamanho proporcional e hierarquia de leitura em Z (KPIs e filtros no topo, tendências no meio, tabelas na base), sem alterar dados, medidas, filtros ou formatação. Usa um motor de layout determinístico, dá uma nota de layout de 0 a 100 antes e depois e confere o resultado com um auditor independente. Use sempre que o usuário pedir para reorganizar, rearranjar, alinhar, diagramar, organizar o layout, "arrumar a disposição dos gráficos", aplicar grid ou melhorar a hierarquia visual de um dashboard ou relatório Power BI, mesmo que não cite o pbix-mcp, layout ou grid, e também quando ele entregar um .pbix pronto pedindo apenas melhoria visual da composição das páginas.
---

# Reorganizar o layout de relatórios Power BI

Esta skill pega um relatório Power BI já pronto e redistribui os visuais de cada página sobre um grid consistente, seguindo uma hierarquia de leitura. O conteúdo do relatório foi aprovado por quem o construiu; o trabalho é de diagramação. Por isso a única coisa que muda é a geometria dos visuais: x, y, largura, altura e, só para formas de fundo, a ordem de camada.

## O que pode e o que não pode mudar

Pode mudar: posição (x, y), largura, altura de visuais e grupos; ordem de camada (z) apenas de formas que servem de fundo a um bloco.

Fica intacto: dados, tabelas, relacionamentos, medidas, consultas, campos e agregações dos visuais, filtros, tipos de visual, formatação, cores, títulos, tema, interações, bookmarks, tamanho e tipo das páginas, layout para celular. Nenhum visual é criado, removido ou oculto.

O motivo é prático: quem pede uma reorganização quer o mesmo relatório mais legível. Qualquer alteração fora da geometria obriga o autor a reauditar o conteúdo, o que anula o ganho.

## Pré-requisitos

- Servidor MCP pbix-mcp conectado. O plugin traz o seu (`uvx --from pbix-mcp==0.9.153 pbix-mcp-server`), e as ferramentas podem aparecer com o prefixo `mcp__plugin_power-bi_layout_with_pbix-mcp_pbix-mcp__` ou, se o usuário já tiver o pbix-mcp configurado, `mcp__pbix-mcp__`. Use um só servidor do começo ao fim: o alias aberto num não existe no outro. Se nenhum estiver conectado, diga o que falta e pare. Não edite o .pbix descompactando ou reescrevendo o arquivo por outros meios, porque o risco de corromper o modelo de dados é real e o usuário perderia o arquivo.
- Os scripts ficam na pasta `scripts/` desta skill (`${CLAUDE_PLUGIN_ROOT}/skills/reorganizar-layout-power-bi/scripts/`) e usam só a biblioteca padrão do Python. Rode-os com `uv run --no-project --quiet <script>`, que funciona igual em macOS, Linux e Windows e baixa um Python se faltar; o `uv` já é exigido para subir o pbix-mcp. Não use `python3` direto: no Windows ele costuma não existir.
  - `inventario_pbix.py`: lê o .pbix como zip, sem gravar nada, e gera o inventário com funções sugeridas;
  - `propor_layout.py`: o motor de layout, que calcula a nova disposição a partir do inventário;
  - `layout_check.py`: calcula o grid (`grid`), confere margem, calha, sobreposições e hierarquia (`check`) e dá a nota de 0 a 100 (`score`);
  - `compare_pbix.py`: prova que original e cópia diferem só na geometria dos visuais;
  - `preview_layout.py`: gera um esquema HTML do antes e depois com as colunas do grid e a nota, já que o pbix-mcp não renderiza a página.

Leia `references/pbix-mcp-operacoes.md` antes da primeira chamada ao pbix-mcp: ele traz a sequência de ferramentas, o formato do inventário e as armadilhas conhecidas, como coordenadas relativas em grupos. Leia `references/boas-praticas-layout.md` quando precisar justificar uma decisão de layout ou resolver um caso que as regras abaixo não cobrem.

Os arquivos de trabalho (`layout_antes.json`, `layout_proposto.json`, `layout_depois.json`, `antes_depois.html`) ficam numa pasta `layout_<nome_original>/` ao lado do .pbix, para não espalhar arquivos pela pasta do usuário.

## Fluxo de trabalho

### 1. Identificar o arquivo, proteger o original e ligar o guardião

Use o .pbix indicado no pedido. Se houver mais de um candidato e o pedido não disser qual, pergunte. O resultado vai para uma cópia chamada `<nome_original>_reorganizado.pbix`, na mesma pasta; o original só é sobrescrito se o usuário pedir isso expressamente. Siga da análise à aplicação sem pedir confirmação a cada etapa: o usuário pediu o trabalho inteiro, e decisões ambíguas ficam registradas no relatório final.

Crie o marcador `.pbi-layout-ativo` no diretório de trabalho (`touch .pbi-layout-ativo`). Enquanto ele existir, o hook guardião do plugin pede confirmação ao usuário antes de qualquer ferramenta do pbix-mcp que mude algo além da geometria. O hook também pede confirmação, sempre, antes de um `pbix_save` que sobrescreveria o arquivo original. Se o usuário recusar uma dessas confirmações, não insista: ajuste o plano.

### 2. Inventariar

Rode `uv run --no-project --quiet inventario_pbix.py <arquivo>.pbix --saida layout_<nome>/layout_antes.json`. Ele registra, por página, nome, tipo (normal, dica de ferramenta, detalhamento), largura e altura; por visual, o nome interno (`id`, estável entre original e cópia), tipo, título, campos, posição absoluta (filhos de grupo já convertidos), grupo, estado oculto e, em segmentadores, o modo (`Dropdown` ou `Basic`) e o campo.

Depois abra o arquivo no pbix-mcp (`pbix_open`) e confira o inventário com `pbix_get_pages` e `pbix_get_visual_positions`: as posições têm de bater. Se não baterem, o pbix-mcp manda; corrija o JSON. Para segmentadores em lista vertical, conte os itens que vão aparecer (`pbix_query_table` no campo) e grave em `items`: uma lista com seis itens precisa de altura que uma faixa de KPIs não oferece.

### 3. Classificar cada visual por função

O inventário vem com uma função sugerida (`role`, marcada com `role_sugerido: true`). Confira cada uma, porque a função decide a faixa da página que o visual ocupa. Classifique pelo que o arquivo mostra (tipo, título, campos), não pelo nome do arquivo ou por suposição:

| Função | Tipos internos comuns (confirme no arquivo) | Faixa |
|---|---|---|
| identidade | `image` (logotipo), `textbox` de título | canto superior esquerdo, compacta; um título que ocupa metade da largura ou mais vira faixa de cabeçalho na largura do grid, com data ou subtítulo à direita; uma faixa de borda a borda no topo é aceita como cabeçalho (`full_bleed: true`) |
| kpi | `card`, `cardVisual`, `multiRowCard`, `kpi`, `gauge` | faixa superior |
| filtro | `slicer`, `advancedSlicerVisual` | faixa superior, ou coluna de filtros se for lista vertical |
| tendencia | `lineChart`, `areaChart`, `stackedAreaChart`, combos de linha e coluna | meio |
| comparacao | `clusteredBarChart`, `clusteredColumnChart`, `barChart`, `columnChart` e variações | meio |
| detalhe | `tableEx` (tabela), `pivotTable` (matriz) | base |
| secundario | mapas, pizza, rosca, treemap, dispersão, funil, cascata, árvore de decomposição e demais | base |
| nota | `textbox` de fonte, metodologia ou rodapé | base, ou o fim da coluna de filtros |
| navegacao | `actionButton`, `pageNavigator`, `bookmarkNavigator` | posição fixa e idêntica em todas as páginas |
| container | `shape` ou `basicShape` usada como fundo de um bloco | acompanha o bloco que envolve |

Quando o papel de um visual não for evidente (uma rosca que é o principal indicador da página, uma tabela de três linhas que funciona como KPI), decida pela função que ele cumpre e registre a decisão. A tabela orienta, a função manda.

Em cada página, eleja o visual mais importante (`principal: true`) e declare o critério (por exemplo: o indicador que responde à pergunta central da página, ou o KPI de maior agregação). O inventário sugere o primeiro KPI na ordem de leitura; troque se outro cumprir melhor esse papel. Confirme também os empilhamentos sugeridos (`stack`): visuais com a mesma geometria exata costumam alternar por bookmark (`pbix_get_bookmarks` ajuda), mas pode ser sobreposição acidental.

Apague os campos `role_sugerido`, `principal_sugerido` e `stack_sugerido` depois de conferir, para que o JSON registre decisões, não palpites.

### 4. Diagnosticar a disposição atual

Rode `uv run --no-project --quiet layout_check.py check layout_antes.json` e `uv run --no-project --quiet layout_check.py score layout_antes.json`. Liste, por página, os problemas encontrados: bordas desalinhadas, sobreposições, espaçamentos irregulares, visuais encostados na borda, visuais da mesma função com tamanhos diferentes e desvios da hierarquia de leitura. O diagnóstico e a nota de partida vão para o relatório e justificam cada mudança.

### 5. Definir e declarar o grid

Antes de mover qualquer visual, declare um grid único para cada tamanho de página do relatório:

- unidade-base: margem, calha e dimensões são múltiplos dela, o que torna o alinhamento verificável por aritmética;
- margem externa igual nos quatro lados (o topo pode ser maior se houver faixa de identidade);
- calha constante entre visuais e entre blocos;
- colunas: 12 é o ponto de partida, porque divide em 2, 3, 4 e 6 blocos iguais.

O padrão do plugin, que os scripts usam quando margem, calha e unidade não são informadas:

| Página | Unidade-base | Margem | Calha | Largura da coluna (12 col.) |
|---|---|---|---|---|
| 1280×720 | 8 px | 24 px | 16 px | 88 px |
| 1920×1080 | 12 px | 36 px | 24 px | 132 px |
| 320×240 (dica) | 4 px | 12 px | 8 px | 17 px (sobra na margem direita) |

A segunda linha é a primeira escalada em 1,5, a mesma proporção entre os dois tamanhos de página. Para outros tamanhos, ou para conferir uma escolha diferente, rode `uv run --no-project --quiet layout_check.py grid --width W --height H [--margin M --gutter G --columns 12]`: ele devolve a borda de cada coluna, a largura de cada vão de n colunas e avisa quando a coluna não sai inteira (a sobra vai para a margem direita). Páginas de tamanhos diferentes recebem cada uma o seu grid, declarado. Se escolher valores diferentes do padrão, passe os mesmos `--margin --gutter --base` a todos os scripts.

### 6. Calcular a nova disposição com o motor e revisar

Rode `uv run --no-project --quiet propor_layout.py layout_antes.json --saida layout_proposto.json`. O motor aplica as regras abaixo de forma determinística e devolve a geometria nova de cada visual (com a original em `de`), o grid de cada página e as listas `decisoes` e `limitacoes`. Ele existe para que as contas de grid não sejam feitas de cabeça: a proposta já sai alinhada, com calhas e margens exatas.

A proposta é um ponto de partida, não uma ordem. Revise-a contra as regras abaixo e contra o que você sabe do relatório; quando um caso pedir outra solução (por exemplo, dois gráficos de mesma importância que o motor desigualou por área), edite `layout_proposto.json` à mão mantendo as bordas nas colunas do grid, e registre a decisão. Rode `layout_check.py check` na proposta antes de aplicar: ela precisa sair sem erros.

As regras que o motor aplica e que valem para qualquer ajuste manual:

**Estrutura e grid**
- Blocos: agrupe visuais afins em blocos retangulares (faixa de KPIs e filtros, bloco de tendência, bloco de detalhe). Proximidade e espaçamento comunicam quais visuais se relacionam.
- Alinhamento: toda borda de visual cai numa linha do grid; dentro de um bloco, os topos e as bases dos visuais de uma mesma linha coincidem.
- Respiro: margem e calha constantes. Nenhum visual encosta na borda da página nem em outro visual, inclusive porque o cabeçalho de um visual (ícones de foco, filtro, mais opções) se sobrepõe ao vizinho quando o espaço é curto.
- Tamanho proporcional: quanto mais importante o visual, maior a área. Visuais da mesma função e mesmo nível têm exatamente o mesmo tamanho (uma fileira de cartões, por exemplo); só o KPI principal pode ser um pouco maior, quando sobram colunas.

**Hierarquia de leitura, em Z**
- Quadrante superior esquerdo: a informação mais importante da página. Se houver logotipo ou título, ele ocupa o canto de forma compacta e o KPI principal vem logo à direita, como primeiro cartão da faixa, para que a primeira leitura seja de dado e não só de marca.
- Faixa superior: cartões de grandes números e segmentadores em lista suspensa, em linha. Ordem dentro da faixa: identidade, KPI principal, demais KPIs, segmentadores no fim da faixa. Quando não cabem todos com pelo menos duas colunas cada, os segmentadores vão para uma segunda linha estreita ainda dentro da faixa superior.
- Segmentador em lista vertical que cabe na altura da faixa superior (pelos itens em `items`, ou pela altura que o autor já deu a ele) fica na faixa, como os de lista suspensa. O que não cabe vai para a coluna de filtros à direita, com duas colunas do grid, que começa na faixa superior (o segundo ponto do Z) e desce até a base. Quando a coluna existe, os segmentadores em lista suspensa abrem a coluna no alto e a nota metodológica a fecha embaixo. Mudar o modo do segmentador para lista suspensa caberia na faixa, mas é formatação e está fora do escopo: registre essa alternativa no relatório para o usuário decidir.
- Filtros de mesmo campo ocupam a mesma posição e o mesmo tamanho em todas as páginas do mesmo tamanho, porque o usuário aprende onde eles ficam. Quando isso sobreporia outro visual, o motor registra a exceção.
- Meio: gráficos de tendência e comparações principais. O gráfico mais importante fica à esquerda e com mais área (8 de 12 colunas, com um gráfico de apoio nas 4 restantes); dois gráficos de mesma importância dividem a largura igualmente.
- Base: visuais secundários à esquerda e tabelas e matrizes à direita, com o dobro do peso, ou a largura toda quando sozinhas, porque precisam de colunas legíveis.
- Distribuição vertical de referência: faixa superior entre 15% e 22% da altura útil, meio com cerca de 55% do que sobra, base com o restante. Quando uma faixa não tem visuais, ela não fica vazia: as faixas seguintes sobem e ocupam o espaço. Se a base ficar abaixo do mínimo de legibilidade e o meio tiver folga, as duas se equilibram.

**Legibilidade mínima** (pontos de partida para 1280×720; escale proporcionalmente em telas maiores): cartões com pelo menos 80 px de altura; gráficos de linha e barra com pelo menos 200 px de altura; tabelas e matrizes com pelo menos 90 px de largura por coluna visível e títulos inteiros. Se a página não comportar todos os visuais com essas medidas, priorize a hierarquia e registre a limitação, em vez de espremer visuais até ficarem ilegíveis.

**Casos particulares**
- Grupos: o grupo se move como unidade, e os filhos acompanham na mesma disposição interna, escalada para a nova vaga. Coordenadas de filhos de grupo são relativas ao grupo: a proposta traz `rel_x` e `rel_y`, que são os valores a passar ao `pbix_move_visual` (ver `references/pbix-mcp-operacoes.md`).
- Visuais empilhados de propósito: dois ou mais visuais com o mesmo `stack` ocupam juntos uma única vaga e recebem exatamente a mesma posição e o mesmo tamanho, senão a alternância quebra.
- Formas de fundo: redimensionadas para envolver o bloco com folga de uma unidade-base de cada lado e mantidas atrás do conteúdo (`z_atras: true` na proposta).
- Navegação: botões e navegadores de página numa linha fixa no rodapé, à direita, na mesma posição em todas as páginas.
- Páginas de dica de ferramenta e de detalhamento: mantêm o tamanho próprio e recebem apenas encaixe na margem, na unidade-base e na calha, sem a hierarquia em faixas, que foi pensada para páginas de leitura completa.
- Densidade: acima de 8 vagas por página, o motor registra a observação; a skill não remove visuais.
- Layout para celular: fora do escopo; não é alterado.

### 7. Aplicar e salvar

Aplique a proposta visual por visual com `pbix_move_visual`, na mesma sessão aberta do passo 2. O `visual_index` é o da lista de `pbix_get_page_visuals`; ligue cada `id` da proposta ao índice pelo nome interno, que a própria lista mostra (`name=...`), e não pela ordem do JSON. Passe `-1` em `z`, exceto para formas de fundo com `z_atras`, que vão para trás do bloco.

Salve em `<nome_original>_reorganizado.pbix` com `overwrite=False`, sem sobrescrever arquivos existentes. Salvar com outro nome não limpa o estado de alterações pendentes do original aberto, então feche-o com `force=True` depois de confirmar que a cópia foi gravada.

### 8. Conferir com o auditor

Delegue a conferência ao subagente `auditor-layout` do plugin, passando o caminho do original, o da cópia e o de `layout_proposto.json`. Ele trabalha sem a memória desta sessão: lê a cópia direto do arquivo, roda `compare_pbix.py`, `layout_check.py check` e `score`, compara com a proposta e devolve um veredito. Se o subagente não estiver disponível, faça você mesmo os mesmos passos:

1. `uv run --no-project --quiet compare_pbix.py <original>.pbix <cópia>.pbix`: o resultado precisa ser `ok`, com as mudanças listadas apenas em `geometria`. Qualquer item em `outras_mudancas` viola o contrato da skill: refaça a partir do original. A ferramenta `pbix_diff` do pbix-mcp serve como checagem complementar do modelo e das medidas, mas ela não compara posições e responde "sem mudanças" mesmo depois de uma reorganização correta, então não basta sozinha.
2. `uv run --no-project --quiet inventario_pbix.py <cópia>.pbix --sem-sugestoes --saida layout_depois.json`, copie para ele as funções, `principal` e `stack` de `layout_proposto.json` (pelo `id`) e rode `uv run --no-project --quiet layout_check.py check layout_depois.json --before layout_antes.json`. Se houver formas de fundo, acrescente `--allow-gap` com os espaçamentos que a folga delas cria. Corrija o que o script apontar como erro (sobreposição, visual fora da página, visual perdido ou com tipo trocado, empilhamento quebrado); avisos podem ser aceitos com justificativa no relatório.
3. `uv run --no-project --quiet layout_check.py score layout_depois.json --before layout_antes.json` para a nota antes e depois.

Se o auditor apontar erros, corrija com `pbix_move_visual` a partir de uma nova abertura da cópia, salve como `_reorganizado_2.pbix` e confira de novo.

Por fim, gere o esquema com `uv run --no-project --quiet preview_layout.py layout_antes.json layout_proposto.json antes_depois.html`, entregue-o ao usuário e apague o marcador `.pbi-layout-ativo`.

## Relatório final

Encerre com um relatório curto, em português, nesta ordem:

1. **Grid adotado**: tamanho da página, unidade-base, margem, calha, colunas.
2. **Nota de layout**: geral e por página, antes → depois.
3. **Por página**: o visual mais importante e o critério, e os problemas da disposição original, em até três frases.
4. **Antes e depois**: por página, uma tabela com visual (tipo e título), posição e tamanho originais, posição e tamanho novos.
5. **Decisões em casos ambíguos**: uma linha cada, incluindo as `decisoes` do motor que importam para o usuário e os ajustes manuais feitos na proposta.
6. **Conferência**: veredito do auditor, resultado do `compare_pbix.py` e do `layout_check.py`, com a contagem de desvios antes e depois.
7. **Recomendações fora do escopo**: o que melhoraria o relatório mas exige mudar formatação ou configuração, como trocar o modo de um segmentador ou ajustar a ordem de tabulação para acompanhar a nova ordem de leitura. A skill não aplica, só registra. Inclua aqui as `limitacoes` do motor.
8. **Arquivos**: caminho completo da cópia salva e do `antes_depois.html`.

Lembre o usuário de abrir a cópia no Power BI Desktop para a conferência visual: o pbix-mcp trabalha com coordenadas e não renderiza a página, então detalhes como rótulos cortados só aparecem na tela.
