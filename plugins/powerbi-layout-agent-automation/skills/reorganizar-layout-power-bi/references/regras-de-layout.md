# Regras de layout

As regras que o motor (`scripts/propor_layout.py`) aplica e que valem para qualquer ajuste manual na proposta. Consultar ao revisar `layout_proposto.json` ou ao decidir um caso que o motor não resolve bem. Os fundamentos e as fontes de cada regra estão em `boas-praticas-layout.md`.

## Índice

1. Grid
2. Estrutura
3. Hierarquia de leitura em Z
4. Faixa superior e KPIs
5. Filtros
6. Meio e base
7. Distribuição vertical
8. Legibilidade mínima
9. Casos particulares

## 1. Grid

- 12 colunas, calha de 2 unidades-base, margem de cima e de baixo de 3 unidades.
- A largura da coluna é sempre múltipla da unidade-base, para que toda borda de visual caia nela. A sobra da largura vai para as margens laterais, dividida entre esquerda e direita em unidades inteiras (pelo menos 3 de cada lado).
- Em 1280×720 e 1920×1080 não há sobra (margens de 24 e 36 px, colunas de 88 e 132 px). Em 1024×768 (4:3), colunas de 64 px e margens laterais de 40 px. Para qualquer outro tamanho, `layout_check.py grid --width W --height H` mostra o resultado.
- Margem, calha ou unidade informadas à mão valem como dadas; aí a coluna é a maior largura inteira que cabe, e a sobra vai para a margem direita.

## 2. Estrutura

- **Blocos**: agrupar visuais afins em blocos retangulares (faixa de KPIs e filtros, bloco de tendência, bloco de detalhe). Proximidade e espaçamento comunicam quais visuais se relacionam.
- **Alinhamento**: toda borda de visual cai numa linha do grid; dentro de um bloco, os topos e as bases dos visuais de uma mesma linha coincidem.
- **Respiro**: margem e calha constantes. Nenhum visual encosta na borda da página nem em outro visual, inclusive porque o cabeçalho de um visual (ícones de foco, filtro, mais opções) se sobrepõe ao vizinho quando o espaço é curto.
- **Tamanho proporcional**: quanto mais importante o visual, maior a área. Visuais da mesma função e do mesmo nível têm exatamente o mesmo tamanho (uma fileira de cartões, por exemplo); só o KPI principal pode ficar maior, com as colunas que sobram.

## 3. Hierarquia de leitura em Z

- **Quadrante superior esquerdo**: a informação mais importante da página. Logotipo ou título pequeno ocupa o canto de forma compacta, e o KPI principal vem logo à direita, como primeiro cartão da faixa, para que a primeira leitura seja de dado e não só de marca.
- **Título largo** (metade da largura da página ou mais): vira uma faixa de cabeçalho na largura do grid, com data, subtítulo ou logotipo pequeno à direita. O KPI principal abre a faixa superior logo abaixo dele, no canto esquerdo.
- **Faixa de borda a borda** (`full_bleed: true`): mantida como cabeçalho, de x=0 até a largura da página; o conteúdo começa uma calha abaixo dela.

## 4. Faixa superior e KPIs

- **Ordem**: identidade, KPI principal, demais KPIs, segmentadores no fim da linha.
- **Largura dos KPIs**: pelo menos 2 colunas cada. Com filtros ou identidade na mesma linha, um KPI ocupa no máximo um terço das colunas, e um filtro, no máximo 3 colunas. A sobra que não se divide igualmente vai para o KPI principal.
- **KPIs que não cabem ao lado da coluna de filtros**: quando os KPIs só cabem com 2 colunas cada usando as 12 colunas, a faixa de KPIs ocupa a largura toda e a coluna de filtros começa logo abaixo dela.
- **KPIs que não cabem numa linha**: quebram em linhas equilibradas (por exemplo, 7 KPIs viram 4 + 3), alinhadas ao primeiro KPI; o motor registra a limitação.
- **Filtros que não cabem na linha dos KPIs** vão para uma segunda linha estreita, ainda na faixa superior, ou para a coluna de filtros, quando ela existe.

## 5. Filtros

- **Lista vertical que cabe na faixa superior** (pelos itens em `items`, cerca de 24 px por item mais 40 px de cabeçalho em 1280×720, ou pela altura que o autor já deu a ela) fica na faixa, como os de lista suspensa.
- **Lista vertical que não cabe** vai para a coluna de filtros: duas colunas do grid à direita, começando na faixa superior (o segundo ponto do Z). A lista recebe a altura dos seus itens com 20% de folga (pelos `items`), não a coluna inteira; sem `items`, divide a altura disponível.
- **Nota na coluna de filtros só se couber**: a nota metodológica fecha a coluna embaixo quando o texto cabe na largura dela (estimativa de 6 px por caractere e 16 px por linha, em 1280×720, até 12 unidades de altura). Nota longa, ou sem texto no inventário e que no original era mais larga que duas colunas de filtros, fica numa linha no fim da área principal.
- **Lista suspensa com coluna de filtros na página**: fica na faixa ao lado dos KPIs se couber; vai para o alto da coluna quando a página não tem KPI ou quando não há colunas sobrando na faixa.
- **Mesmo campo, mesma posição**: um campo de filtro que vai para a coluna numa página vai para a coluna em todas as páginas que a têm, e filtros do mesmo campo e do mesmo modo repetem posição e tamanho entre páginas do mesmo tamanho. Quando repetir sobreporia outro visual, o motor registra a exceção em `decisoes`.
- **Fora do escopo**: trocar uma lista vertical por lista suspensa caberia na faixa, mas é formatação. Registrar a alternativa em "Recomendações fora do escopo".

## 6. Meio e base

- **Meio**: gráficos de tendência e de comparação. O mais importante (o `principal`, ou o de área original pelo menos 30% maior) fica à esquerda com 2/3 da largura, e o de apoio, à direita. Dois gráficos de importância parecida dividem a largura igualmente. Mais de quatro visuais viram duas linhas.
- **Base**: visuais secundários à esquerda e tabelas e matrizes à direita, com o dobro do peso, ou a largura toda quando sozinhas, porque precisam de colunas legíveis.
- **Tabela que ficaria estreita para os campos** dividindo a base (menos de 90 px por campo): os secundários sobem para o meio, ao lado dos gráficos, se o meio tiver uma linha só e couberem nela; senão, a tabela ganha uma linha só dela na base. Só vale quando a largura toda basta para a tabela.
- **Faixa vazia não fica vazia**: sem tendência nem comparação, a base sobe e ocupa o meio; sem faixa superior, o meio sobe para o topo.

## 7. Distribuição vertical

- Faixa superior com cerca de 18% da altura útil (entre 15% e 22%), nunca abaixo da altura mínima de um cartão.
- Meio com cerca de 55% do que sobra; base com o restante.
- Se a base ficar abaixo do mínimo de legibilidade e o meio tiver folga, as duas se equilibram.
- Nota sem coluna de filtros, ou longa demais para ela: linha estreita no fim da área principal. Navegação: linha fixa no rodapé, à direita.

## 8. Legibilidade mínima

Pontos de partida para 1280×720; o motor escala proporcionalmente em telas maiores e registra em `limitacoes` o que não couber:

- cartões com pelo menos 80 px de altura;
- gráficos de linha e de barra com pelo menos 200 px de altura;
- tabelas e matrizes com pelo menos 90 px de largura por campo exibido (contado em `fields`);
- gráfico ou tabela que perde mais de 10% da menor dimensão (largura ou altura) gera uma limitação para conferir no Desktop: num teste real, uma rosca que perdeu 14% da altura cortou o rótulo central, e uma dispersão mais baixa perdeu marcas do eixo.

Títulos inteiros e rótulos sem corte só podem ser conferidos no Power BI Desktop. Se a página não comportar todos os visuais com essas medidas, priorizar a hierarquia e registrar a limitação, em vez de espremer visuais até ficarem ilegíveis.

## 9. Casos particulares

- **Grupos**: o grupo se move como unidade. Se o tamanho dele muda, os filhos acompanham na mesma disposição interna, escalada para a nova vaga, e a proposta marca `aplicar_filho: true` com `rel_x`, `rel_y`, `width` e `height` a aplicar. Se só a posição muda, mover o container basta (`aplicar_filho: false`). Ver `pbix-mcp-operacoes.md`.
- **Visuais empilhados de propósito**: dois ou mais visuais com o mesmo `stack` ocupam juntos uma única vaga e recebem exatamente a mesma posição e o mesmo tamanho, senão a alternância por bookmark quebra.
- **Formas de fundo**: redimensionadas para envolver o bloco que já envolviam, com folga de uma unidade-base de cada lado, e mantidas atrás do conteúdo (`z_atras: true`). A folga cria espaçamentos diferentes da calha: passá-los em `--allow-gap` ao `layout_check.py` e ao `preview_layout.py`.
- **Navegação**: botões e navegadores de página numa linha fixa no rodapé, à direita, na ordem em que o autor os dispôs, na mesma posição em todas as páginas do mesmo tamanho.
- **Páginas de dica de ferramenta e de detalhamento**: mantêm o tamanho próprio e recebem só encaixe na margem, na unidade-base e na calha, sem as faixas, que foram pensadas para páginas de leitura completa.
- **Densidade**: acima de 8 vagas por página, o motor registra a observação; a skill não remove visuais.
- **Layout para celular**: fora do escopo; não é alterado.
