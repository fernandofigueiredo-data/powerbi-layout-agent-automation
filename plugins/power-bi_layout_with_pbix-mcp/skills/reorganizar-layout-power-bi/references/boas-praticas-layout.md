# Boas práticas de layout em relatórios Power BI

Fundamentos que sustentam as regras da skill, com a fonte de cada um. Consultar ao justificar uma decisão ou ao resolver um caso não previsto. Onde as fontes divergem, a divergência está registrada, com a escolha da skill e o motivo.

## Índice

1. Espaço: margens e espaçamento
2. Alinhamento e seções
3. Tamanho
4. Fluxo de leitura e hierarquia
5. Densidade
6. Tamanhos de página
7. Acessibilidade e ordem de leitura
8. Divergências entre fontes
9. Fontes

## 1. Espaço: margens e espaçamento

- O Power BI não tem propriedade de margem de página; a margem existe apenas se os visuais forem dispostos de modo a deixá-la. As margens laterais devem ser iguais; topo e base podem variar para acomodar identidade, títulos ou segmentadores. [Microsoft Learn, *Design visually appealing reports*]
- Espaçamento suficiente entre visuais evita que o cabeçalho de um visual se sobreponha ao vizinho e dificulte o uso dos ícones. [Microsoft Learn, *Design visually appealing reports*]
- Espaços de profundidades diferentes podem separar seções, mas excesso de espaço desequilibra a página. O objetivo é espaçamento uniforme e equilibrado. [Microsoft Learn, *Design visually appealing reports*]
- Incrementos de 8, 16 e 24 px como base de um grid consistente. [awesome-copilot, *Power BI report design best practices*] Esta é uma convenção de comunidade, não uma norma da Microsoft; a skill a adota porque torna o alinhamento verificável por aritmética.

## 2. Alinhamento e seções

- As bordas dos visuais devem estar alinhadas e o espaço entre eles deve ser constante. [Microsoft Learn, *Design visually appealing reports*]
- Seções podem ser implícitas (visuais próximos, separados dos demais por espaço) ou explícitas (formas coloridas de fundo sob visuais alinhados). [Microsoft Learn, *Design visually appealing reports*] A skill usa seções implícitas por padrão e respeita as explícitas que já existirem, redimensionando as formas para envolver o bloco.
- O Power BI Desktop oferece linhas de grade, ajuste à grade, guias inteligentes e comandos de alinhar e distribuir; a ordem de camada é gerida no painel Seleção. [Microsoft Learn, *Use gridlines and snap-to-grid*]
- Alinhar os elementos e ser consistente na posição e na formatação estão entre as regras de design de dashboard da SQLBI. [SQLBI, *Dashboard design rules*]

## 3. Tamanho

- Quanto mais importante o visual, maior ele deve ser; visuais semelhantes, como uma série de cartões, devem ter o mesmo tamanho. [Microsoft Learn, *Design visually appealing reports*]
- Visuais respondem ao tamanho: um gráfico de linha pequeno vira quase uma sparkline, com poucos rótulos de eixo. O visual precisa comunicar seus dados no tamanho real da página, sem depender do modo foco. [Microsoft Learn, *Design visually appealing reports*]
- Se texto e visuais tiverem todos o mesmo tamanho, o leitor não sabe onde focar; cartões são uma boa forma de destacar o número importante. [Microsoft Learn, *Tips and tricks for creating reports*]

## 4. Fluxo de leitura e hierarquia

- A maioria das pessoas lê de cima para baixo: o dado de mais alto nível vai no canto superior esquerdo, e o detalhe cresce no sentido de leitura do público (esquerda para direita, cima para baixo). [Microsoft Learn, *Tips for designing a great Power BI dashboard*]
- Regra 3-30-300: cerca de 3 segundos para a visão geral, 30 para filtrar e aproximar, 300 para o detalhe sob demanda, adaptação do mantra de busca visual de Ben Shneiderman (1996). Na prática: visuais simples (cartões, linhas) no alto à esquerda; barras por hierarquia e interação no meio; matriz de detalhe por último, embaixo à direita. [Kurt Buhler, SQLBI, *Introducing the 3-30-300 rule for better reports*, 2024]
- Padrão em Z: útil em interfaces visuais e de monitoramento, em que se busca a visão de conjunto; o padrão em F descreve melhor páginas com muito texto. [Medium, UXD Critical Software] Os dois padrões são heurísticas de varredura com respaldo de estudos de rastreamento ocular em páginas web, não leis da percepção; servem como ponto de partida e não substituem o conhecimento de como o público usa o relatório.

## 5. Densidade

- Contar uma história por tela, sem barras de rolagem e sem excesso de elementos. [Microsoft Learn, *Tips and tricks for creating reports*; SQLBI, *Dashboard design rules*]
- Referência de comunidade: de 6 a 8 visuais por página de dashboard, levando o detalhe para páginas de drill-through. [awesome-copilot] A skill não remove visuais, então, se a página estiver acima disso, ela apenas registra a densidade no relatório como observação.

## 6. Tamanhos de página

- Tipos de tela no Power BI: 16:9 (padrão), 4:3, Carta, Dica de ferramenta e Personalizado. Tamanhos 16:9 disponíveis: 1280×720, 1920×1080, 2560×1440 e 3840×2160. [Microsoft Learn, *Apply page size and settings*]
- Páginas de dica de ferramenta: tamanho embutido de 320×240 px; devem ficar ocultas. [Microsoft Learn, *Report page tooltips*]
- Páginas muito grandes e cheias de visuais demoram a renderizar, e os visuais podem não aparecer de cima para baixo. [Microsoft Learn, *Design visually appealing reports*]

## 7. Acessibilidade e ordem de leitura

- A ordem de tabulação deve acompanhar a ordem visual de leitura, e formas e imagens decorativas devem sair dela. [Microsoft Learn, *Design Power BI reports for accessibility*] A skill não altera a ordem de tabulação, porque ela está fora da geometria; quando a nova disposição divergir muito da ordem de tabulação existente, registrar isso no relatório como recomendação.

## 8. Divergências entre fontes

| Ponto | Posição A | Posição B | Escolha da skill |
|---|---|---|---|
| Canto superior esquerdo | Logotipo ou principal KPI (preferência do autor da skill) | Manter logotipos, botões e segmentadores fora da área de visão geral (SQLBI, 3-30-300) | Identidade compacta no canto, KPI principal logo à direita, como primeiro cartão: preserva a preferência do autor e entrega a primeira leitura a um dado. |
| Segmentadores | Faixa superior, ao lado dos KPIs (preferência do autor da skill) | Barra lateral ou rodapé (awesome-copilot); painel lateral (SQLBI) | Faixa superior, no fim da linha, depois dos KPIs. Com muitos segmentadores em lista suspensa, segunda linha estreita ainda na faixa superior. Lista vertical que não cabe na faixa vai para uma coluna de filtros à direita, que começa na faixa superior; a solução foi validada em teste com um painel real de dois tamanhos de página. |
| Tabelas | Base da tela (preferência do autor da skill) | Embaixo à direita, como último ponto de leitura (SQLBI) | Base; à direita quando dividem a linha com outro visual, largura toda quando sozinhas. |

## 9. Fontes

- Microsoft Learn. *Design visually appealing reports* (módulo de treinamento Power BI effective reports). https://learn.microsoft.com/training/modules/power-bi-effective-reports/3-design-reports
- Microsoft Learn. *Tips for designing a great Power BI dashboard*. https://learn.microsoft.com/power-bi/create-reports/service-dashboards-design-tips
- Microsoft Learn. *Tips and tricks for creating reports in Power BI Desktop*. https://learn.microsoft.com/power-bi/create-reports/desktop-tips-and-tricks-for-creating-reports
- Microsoft Learn. *Use gridlines and snap-to-grid in Power BI reports*. https://learn.microsoft.com/power-bi/create-reports/desktop-gridlines-snap-to-grid
- Microsoft Learn. *Apply page size and settings in a Power BI report*. https://learn.microsoft.com/power-bi/create-reports/power-bi-report-display-settings
- Microsoft Learn. *Report page tooltips* (guidance). https://learn.microsoft.com/power-bi/guidance/report-page-tooltips
- Microsoft Learn. *Design Power BI reports for accessibility*. https://learn.microsoft.com/power-bi/create-reports/desktop-accessibility-creating-reports
- Kurt Buhler, SQLBI. *Introducing the 3-30-300 rule for better reports*, 2024. https://www.sqlbi.com/articles/introducing-the-3-30-300-rule-for-better-reports/
- SQLBI. *Dashboard design rules* (pôster). https://www.sqlbi.com/wp-content/uploads/videotrainings/dashboarddesign/rules-bw-A3.pdf
- awesome-copilot. *Power BI report design best practices* (instruções de comunidade). https://awesome-copilot.github.com/instruction/power-bi-report-design-best-practices/
- UXD Critical Software. *Understanding the F-shaped and Z-shaped reading patterns*. https://medium.com/uxd-critical-software/understanding-the-f-shaped-and-z-shaped-reading-patterns-for-optimal-usability-in-complex-systems-e96668839abd

Fontes consultadas em novembro de 2026.
