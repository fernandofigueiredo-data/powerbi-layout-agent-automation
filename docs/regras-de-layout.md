# O que o plugin faz com o seu arquivo Power BI

Este documento lista, para quem vai rodar o plugin, tudo o que acontece com um
`.pbix` durante a reorganização: o que pode mudar, o que nunca muda e as regras
que decidem onde cada visual vai parar.

A versão usada pelo motor de layout, com os detalhes de cálculo, está em
[regras-de-layout.md](../plugins/powerbi-layout-agent-automation/skills/reorganizar-layout-power-bi/references/regras-de-layout.md).
As fontes de cada regra estão em
[boas-praticas-layout.md](../plugins/powerbi-layout-agent-automation/skills/reorganizar-layout-power-bi/references/boas-praticas-layout.md).

## Índice

1. [O que muda e o que nunca muda](#1-o-que-muda-e-o-que-nunca-muda)
2. [Como cada visual é classificado](#2-como-cada-visual-é-classificado)
3. [Grid](#3-grid)
4. [Alinhamento, espaçamento e tamanho](#4-alinhamento-espaçamento-e-tamanho)
5. [Ordem de leitura em Z](#5-ordem-de-leitura-em-z)
6. [Faixa superior: identidade, KPIs e filtros](#6-faixa-superior-identidade-kpis-e-filtros)
7. [Filtros em lista e coluna de filtros](#7-filtros-em-lista-e-coluna-de-filtros)
8. [Meio e base da página](#8-meio-e-base-da-página)
9. [Altura das faixas](#9-altura-das-faixas)
10. [Tamanho mínimo para continuar legível](#10-tamanho-mínimo-para-continuar-legível)
11. [Casos especiais](#11-casos-especiais)
12. [O que fica fora do escopo](#12-o-que-fica-fora-do-escopo)
13. [Como a nota de layout é calculada](#13-como-a-nota-de-layout-é-calculada)
14. [Como você confere o resultado](#14-como-você-confere-o-resultado)

## 1. O que muda e o que nunca muda

A reorganização é um trabalho de diagramação. O conteúdo do relatório já foi
aprovado por quem o construiu, então só a geometria dos visuais muda.

| Pode mudar | Nunca muda |
|---|---|
| Posição (x, y) de visuais e grupos | Dados, tabelas, relacionamentos e consultas |
| Largura e altura de visuais e grupos | Medidas, campos e agregações |
| Ordem de camada, **só** de formas usadas como fundo de um bloco | Filtros e segmentadores (seleções e configuração) |
| | Tipo de cada visual |
| | Formatação, cores, fontes, títulos e tema |
| | Interações entre visuais e bookmarks |
| | Tamanho e tipo das páginas |
| | Layout para celular |

Nenhum visual é criado, removido ou ocultado.

- **O original não é tocado.** O resultado vai para uma cópia
  `<nome>_reorganizado.pbix` na mesma pasta. Se essa cópia já existir, o
  plugin grava `<nome>_reorganizado_2.pbix`.
- **Há uma trava contra acidentes.** Um hook pede a sua confirmação antes de
  qualquer gravação que sobrescreveria o arquivo original e, durante a
  reorganização, antes de qualquer ferramenta que mude algo além da geometria.
- **Há uma prova no fim.** O script `compare_pbix.py` compara original e
  cópia arquivo por arquivo e só aprova se a única diferença for de posição e
  tamanho.

## 2. Como cada visual é classificado

Antes de mover qualquer coisa, cada visual recebe uma função. É a função, não o
tipo do visual, que decide em que parte da página ele vai ficar. O plugin
sugere a função pelo tipo, e o Claude confere pelo título e pelos campos.

| Função | Exemplos | Onde fica |
|---|---|---|
| Identidade | Logotipo, caixa de texto com o título | Canto superior esquerdo, compacta |
| KPI | Cartão, cartão de várias linhas, KPI, medidor | Faixa superior |
| Filtro | Segmentadores de qualquer tipo | Faixa superior ou coluna de filtros |
| Tendência | Linha, área, faixa, combinação de linha e coluna | Meio |
| Comparação | Barras e colunas | Meio |
| Detalhe | Tabela e matriz | Base |
| Secundário | Mapa, pizza, rosca, treemap, dispersão, funil, cascata | Base |
| Nota | Caixa de texto com fonte, metodologia ou rodapé | Base, ou o fim da coluna de filtros |
| Navegação | Botões, navegador de páginas e de bookmarks | Linha fixa no rodapé |
| Fundo | Forma usada como fundo de um bloco | Acompanha o bloco que envolve |

Em cada página, um visual é eleito o **principal**: o indicador que responde à
pergunta central da página. Ele recebe a posição e a área de maior destaque.
Quando a função de um visual não é óbvia, por exemplo uma rosca que é o
principal indicador da página, vale a função que ele cumpre, e a decisão
aparece no relatório final.

## 3. Grid

- Toda página recebe um grid de **12 colunas**. Doze colunas se dividem em 2,
  3, 4 e 6 blocos iguais, o que permite metades, terços e quartos exatos.
- Margens, calha (o espaço entre visuais) e dimensões são múltiplos de uma
  **unidade-base**. A calha vale 2 unidades e as margens de cima e de baixo, 3.
- A largura de cada coluna é sempre múltipla da unidade. A sobra da largura da
  página vai para as margens laterais, dividida igualmente.

| Página | Unidade | Margens (cima/baixo, laterais) | Calha | Coluna |
|---|---|---|---|---|
| 1280×720 | 8 px | 24 px, 24 px | 16 px | 88 px |
| 1920×1080 | 12 px | 36 px, 36 px | 24 px | 132 px |
| 1024×768 (4:3) | 8 px | 24 px, 40 px | 16 px | 64 px |
| 320×240 (dica) | 4 px | 12 px, 20 px | 8 px | 16 px |

Para qualquer outro tamanho, o comando
`/powerbi-layout-agent-automation:grid LxA` calcula o grid.

## 4. Alinhamento, espaçamento e tamanho

- **Toda borda de visual cai numa linha do grid.** Na mesma linha, os topos e
  as bases dos visuais coincidem.
- **Margem e calha são constantes.** Nenhum visual encosta na borda da página
  nem em outro visual. Isso também evita que os ícones do cabeçalho de um
  visual (foco, filtro, mais opções) fiquem por cima do vizinho.
- **Visuais afins formam blocos.** A faixa de KPIs e filtros, o bloco de
  tendência e o bloco de detalhe ficam agrupados, e a distância entre eles
  mostra o que se relaciona com o quê.
- **Nenhuma sobreposição**, exceto a de visuais empilhados de propósito
  (seção 11).
- **O tamanho acompanha a importância.** Quanto mais importante o visual,
  maior a área.
- **Mesma função, mesmo tamanho.** Uma fileira de cartões tem cartões
  idênticos. Só o KPI principal pode ficar maior, com as colunas que sobrarem.

## 5. Ordem de leitura em Z

O olho percorre a página em Z: da esquerda para a direita no alto, desce na
diagonal e volta a ler da esquerda para a direita embaixo. As faixas seguem
essa ordem:

1. **Topo**: identidade, KPIs e filtros. O panorama.
2. **Meio**: tendências e comparações. A explicação.
3. **Base**: tabelas, matrizes e visuais secundários. O detalhe.

Regras do topo:

- O **canto superior esquerdo** recebe a informação mais importante. Um
  logotipo ou título pequeno ocupa o canto de forma compacta, e o KPI
  principal vem logo à direita, para que a primeira leitura seja de dado e não
  só de marca.
- Um **título largo** (metade da largura da página ou mais) vira uma faixa de
  cabeçalho na largura do grid. O KPI principal abre a linha logo abaixo dele.
- Uma **faixa de borda a borda** que já existia como cabeçalho continua de
  borda a borda, e o conteúdo começa uma calha abaixo dela.

## 6. Faixa superior: identidade, KPIs e filtros

- **Ordem na linha**: identidade, KPI principal, demais KPIs e, no fim, os
  segmentadores.
- **Largura**: cada KPI ocupa pelo menos 2 colunas. Quando a linha também tem
  filtros ou identidade, um KPI ocupa no máximo um terço das colunas e um
  filtro, no máximo 3. A sobra que não se divide igualmente vai para o KPI
  principal.
- **KPIs demais para uma linha** quebram em linhas equilibradas (7 KPIs viram
  4 + 3), alinhadas ao primeiro KPI.
- **KPIs que não cabem ao lado da coluna de filtros** ocupam as 12 colunas, e
  a coluna de filtros começa logo abaixo deles.
- **Filtros que não cabem na linha dos KPIs** vão para uma segunda linha
  estreita, ainda no topo, ou para a coluna de filtros, quando ela existe.

## 7. Filtros em lista e coluna de filtros

- Um segmentador em **lista vertical que cabe no topo** (pela quantidade de
  itens ou pela altura que o autor já deu a ele) fica no topo, como os de
  lista suspensa.
- Uma **lista vertical que não cabe** vai para a **coluna de filtros**: duas
  colunas do grid à direita, a partir do topo. A lista fica com a altura dos
  seus itens, mais uma folga, e não estica até a base.
- A **nota metodológica** fecha a coluna embaixo só se o texto couber na
  largura dela. Uma nota longa fica numa linha no fim da área principal.
- Um segmentador em **lista suspensa** numa página com coluna de filtros fica
  no topo ao lado dos KPIs, se couber. Se a página não tiver KPI ou não houver
  colunas sobrando, vai para o alto da coluna.
- **Mesmo campo, mesma posição em todas as páginas.** Um filtro de Ano que
  está na coluna de filtros numa página está na coluna em todas as páginas que
  a têm, com a mesma posição e o mesmo tamanho entre páginas do mesmo tamanho.
  Quando repetir a posição sobreporia outro visual, a exceção aparece no
  relatório.

## 8. Meio e base da página

- **Meio**: o gráfico mais importante fica à esquerda com 2/3 da largura, e o
  de apoio, à direita. Conta como mais importante o visual eleito principal
  ou o que tinha área original pelo menos 30% maior. Dois gráficos de
  importância parecida dividem a largura igualmente. Mais de quatro visuais no
  meio viram duas linhas.
- **Base**: visuais secundários à esquerda e tabelas e matrizes à direita, com
  o dobro da largura, porque precisam de colunas legíveis. Uma tabela sozinha
  na base ocupa a largura toda.
- **Tabela que ficaria estreita** para os campos ao dividir a base: os
  visuais secundários sobem para o meio, ao lado dos gráficos, e a tabela fica
  com a largura toda.
- **Nenhuma faixa fica vazia.** Sem tendência nem comparação, a base sobe e
  ocupa o meio. Sem nada no topo, o meio sobe.

## 9. Altura das faixas

- **Topo**: cerca de 18% da altura útil, entre 15% e 22%, e nunca menos que a
  altura mínima de um cartão.
- **Meio**: cerca de 55% do que sobra.
- **Base**: o restante. Se ela ficar baixa demais para ser legível e o meio
  tiver folga, as duas se equilibram.
- **Nota** (sem coluna de filtros, ou longa demais para ela): linha estreita no
  fim da área principal.
- **Navegação**: linha fixa no rodapé, à direita.

## 10. Tamanho mínimo para continuar legível

Valores de referência para páginas de 1280×720. Em páginas maiores, o plugin
escala na mesma proporção:

| Visual | Mínimo |
|---|---|
| Cartão | 80 px de altura |
| Gráfico de linha ou de barra | 200 px de altura |
| Tabela ou matriz | 90 px de largura por campo exibido |

Se a página não comportar todos os visuais com essas medidas, o plugin
prioriza a ordem de leitura e registra a limitação no relatório, em vez de
espremer visuais até ficarem ilegíveis.

Um gráfico ou tabela que perde mais de 10% da menor dimensão também vira
limitação, para você conferir no Power BI Desktop. No teste real com o painel
IFData, uma rosca que encolheu cortou o rótulo central, e uma dispersão mais
baixa perdeu marcas do eixo.

## 11. Casos especiais

- **Grupos** se movem como uma unidade. Se o tamanho do grupo muda, os visuais
  de dentro acompanham na mesma disposição, em escala.
- **Visuais empilhados de propósito** (os que se alternam por bookmark)
  continuam empilhados: recebem exatamente a mesma posição e o mesmo tamanho,
  para a alternância não quebrar.
- **Formas de fundo** são redimensionadas para continuar envolvendo o bloco
  que já envolviam, com uma unidade de folga de cada lado, e ficam atrás do
  conteúdo. É o único caso em que a ordem de camada muda.
- **Botões de navegação** ficam numa linha no rodapé, à direita, na ordem em
  que o autor os colocou, e na mesma posição em todas as páginas do mesmo
  tamanho.
- **Páginas de dica de ferramenta e de detalhamento** mantêm o tamanho próprio
  e só são encaixadas na margem, na unidade e na calha. Elas não recebem as
  faixas, que foram pensadas para páginas de leitura completa.
- **Páginas densas** (mais de 8 visuais) ganham uma observação no relatório.
  Nenhum visual é removido.

## 12. O que fica fora do escopo

Algumas melhorias exigiriam mudar formatação ou configuração. O plugin não as
aplica, só as registra em "Recomendações fora do escopo" no relatório final:

- trocar um segmentador de lista vertical por lista suspensa para ele caber no
  topo;
- ajustar a ordem de tabulação à nova ordem de leitura;
- reorganizar o layout para celular;
- reduzir o número de visuais de uma página densa.

O plugin trabalha com coordenadas e não renderiza a página. Rótulos cortados e
títulos que quebram em duas linhas só aparecem no Power BI Desktop: abra a
cópia lá para a conferência visual final.

## 13. Como a nota de layout é calculada

Cada página recebe uma nota de 0 a 100, antes e depois da reorganização, pela
soma de cinco critérios:

| Critério | Peso | O que confere |
|---|---|---|
| Alinhamento | 25 | Bordas na unidade-base e nas linhas das colunas do grid |
| Espaço | 20 | Margem respeitada e espaçamentos iguais à calha |
| Integridade | 20 | Nenhuma sobreposição, nenhum visual fora da página, empilhados intactos |
| Hierarquia | 20 | Faixas em Z na ordem certa, identidade ou KPI no canto, principal no alto |
| Proporção | 15 | Mesma função com o mesmo tamanho, área que cresce com a importância |

O comando `/powerbi-layout-agent-automation:diagnosticar` mostra a nota atual e
a nota que a reorganização alcançaria, sem gravar nada.

## 14. Como você confere o resultado

Ao terminar, o plugin entrega um relatório com:

1. o grid adotado em cada tamanho de página;
2. a nota de layout antes → depois, geral e por página;
3. o visual principal de cada página e os problemas da disposição original;
4. uma tabela com a posição e o tamanho de cada visual, antes e depois;
5. as decisões tomadas em casos ambíguos;
6. o resultado da conferência: o auditor independente, a comparação entre
   original e cópia e a checagem do layout;
7. as recomendações fora do escopo e as limitações encontradas;
8. o caminho da cópia salva e de um esquema HTML com o antes e depois de cada
   página.
