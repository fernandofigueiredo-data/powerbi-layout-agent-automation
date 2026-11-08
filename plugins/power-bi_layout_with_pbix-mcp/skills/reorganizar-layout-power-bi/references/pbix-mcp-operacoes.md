# Operações no pbix-mcp para reorganizar layout

Sequência de ferramentas, armadilhas conhecidas e formato dos JSONs de layout. Os nomes abaixo são os do servidor pbix-mcp; o prefixo que o cliente acrescenta varia conforme a instalação: `mcp__plugin_power-bi-layout-with-pbix-mcp_pbix-mcp__` para o servidor que o plugin traz, `mcp__pbix-mcp__` para um pbix-mcp configurado à parte. Escolher um e usar só ele na reorganização inteira, porque cada servidor tem os seus próprios arquivos abertos.

O inventário sai de `scripts/inventario_pbix.py`, que lê o .pbix como zip sem passar pelo pbix-mcp; as ferramentas de leitura abaixo servem para conferi-lo e para o que o arquivo não mostra sozinho (itens de um segmentador, bookmarks).

## Sequência

| Etapa | Ferramenta | Observação |
|---|---|---|
| Abrir | `pbix_open(file_path, alias)` | Alias curto, como `orig`. Se não abrir, rodar `pbix_doctor(alias)` e relatar o diagnóstico. |
| Listar páginas | `pbix_get_pages(alias)` | Páginas, contagem de visuais e tamanho (por exemplo `1920x1080`). A lista de componentes de `pbix_open` mostra o formato: `Report/definition/...` é PBIR; `Report/Layout` é o formato legado. |
| Listar visuais | `pbix_get_page_visuals(alias, page_index)` | O `visual_index` desta lista é o que `pbix_move_visual` usa. A lista mostra o nome interno de cada visual (`name=...`), que é o `id` do inventário: ligar índice e `id` por ele, nunca pela ordem do JSON. |
| Posições absolutas | `pbix_get_visual_positions(alias, page_index)` | Resolve o deslocamento de grupos para coordenadas absolutas da página; marca os filhos com `[child of group]`. Serve para conferir o inventário e, depois de aplicar, a cópia. |
| Detalhe de um visual | `pbix_get_visual_detail(alias, page_index, visual_index)` | Título, campos, modo do segmentador (`Dropdown` ou `Basic`) e estado oculto. |
| Itens de um segmentador | `pbix_query_table(alias, table_name, columns="Campo", max_rows=5000)` | Contar os valores distintos que uma lista vertical vai exibir, para gravar em `items`. |
| Bookmarks | `pbix_get_bookmarks(alias)` | Confirmar visuais empilhados que se alternam. |
| Mover e redimensionar | `pbix_move_visual(alias, page, visual_index, x, y, width, height, z)` | `page` aceita índice ou nome de exibição; `-1` deixa o valor inalterado. A posição fica no container do visual; `pbix_set_visual_property` não a alcança. |
| Salvar | `pbix_save(alias, output_path, overwrite=False, backup=True)` | `output_path` com o nome da cópia. Com `output_path` vazio, o arquivo original é sobrescrito (o guardião do plugin pede confirmação). |
| Diagnosticar a cópia | `pbix_doctor(alias)` | Depois de salvar, abrir a cópia com outro alias e rodar: confere zip, layout, modelo de dados e nomes. |
| Comparar modelo | `pbix_diff(alias_a, alias_b)` | Confirma que tabelas, medidas, relacionamentos, páginas, visuais e tema não mudaram. Não compara posições: depois de uma reorganização correta, responde "sem mudanças". A prova de que só a geometria mudou vem de `scripts/compare_pbix.py`. |
| Fechar | `pbix_close(alias, force)` | Recusa fechar arquivo com alterações não salvas. Salvar com `output_path` diferente não limpa esse estado: depois de confirmar que a cópia foi gravada, fechar o original com `force=True`. |

## Armadilhas

**Grupos.** Para visuais dentro de um grupo, o x e o y gravados são relativos ao grupo; `pbix_get_visual_positions` converte para absoluto na leitura. A proposta do motor diz o que aplicar:

- Grupo só movido (mesmo tamanho): os filhos vêm com `aplicar_filho: false`. Mover só o container do grupo; os filhos acompanham, porque a posição relativa não muda.
- Grupo redimensionado: os filhos vêm com `aplicar_filho: true`. Mover o container e depois cada filho com `x = rel_x`, `y = rel_y`, `width` e `height` da proposta (coordenadas relativas ao grupo, não absolutas).

Depois de aplicar, reler com `pbix_get_visual_positions`: as posições absolutas dos filhos têm de bater com as da proposta. Verificado em teste com grupo de dois gráficos redimensionado (pbix-mcp 0.9.153, formato legado).

**Índices estáveis.** Fazer a conferência do inventário e a aplicação na mesma sessão aberta, sem adicionar nem remover visuais, para que os índices continuem apontando para os mesmos visuais. Ao reabrir o arquivo, listar os visuais de novo antes de mover.

**Ordem de camada.** Só alterar `z` de formas de fundo (`z_atras` na proposta), para garantir que fiquem atrás do bloco. Mudar a camada de outros visuais pode esconder um visual atrás de outro. O `compare_pbix.py` lista em `camada` todo visual cujo `z` mudou: cada item precisa ser uma forma de fundo.

**Sem renderização.** O pbix-mcp opera sobre a definição do relatório e não desenha a página. Legibilidade de rótulos, quebras de título e barras de rolagem em tabelas só podem ser conferidas no Power BI Desktop. Por isso os mínimos de tamanho são conservadores.

**Salvar com segurança.** `overwrite=False` faz o salvamento falhar se a cópia já existir. Nesse caso, acrescentar um sufixo numérico (`_reorganizado_2.pbix`) em vez de forçar a sobrescrita.

**O que o salvamento altera além da geometria.** Observado em teste com relatório PBIR (pbix-mcp 0.9.153): o arquivo `SecurityBindings` é descartado, os `page.json` e o `pages.json` são regravados com outra indentação, sem mudança de conteúdo, e a ordem dos arquivos dentro do zip muda. `compare_pbix.py` classifica esses casos como informação, não como violação. Pedir ao usuário que confirme que a cópia abre no Power BI Desktop.

**Ordem de tabulação.** No PBIR, `tabOrder` fica no mesmo bloco `position` que x, y e z, e `pbix_move_visual` não o altera. Depois da reorganização, a ordem de tabulação continua a original, o que pode não acompanhar a nova ordem de leitura. Registrar isso como recomendação, sem alterar.

## Formato dos JSONs de layout

`layout_antes.json` (inventário), `layout_proposto.json` (proposta do motor) e `layout_depois.json` (inventário da cópia com `--herdar`) usam o mesmo formato. Exemplos completos em `examples/`.

```json
{
  "pages": [
    {
      "name": "Visão geral",
      "type": "normal",
      "width": 1280,
      "height": 720,
      "visuals": [
        {"id": "3", "type": "card", "title": "Faturamento", "role": "kpi", "principal": true,
         "x": 120, "y": 16, "width": 200, "height": 96},
        {"id": "7", "type": "shape", "role": "container", "x": 8, "y": 8, "width": 1264, "height": 112},
        {"id": "9", "type": "lineChart", "role": "tendencia", "stack": "alternancia-1",
         "x": 16, "y": 136, "width": 824, "height": 304}
      ]
    }
  ]
}
```

Campos de página:
- `type`: `normal`, `tooltip` ou `drillthrough`.
- `grid` (só na proposta): `base`, `margem` (de cima e de baixo), `margem_esquerda`, `margem_direita`, `calha`, `colunas` e `largura_coluna` usados no cálculo.

Campos de visual:
- `id`: o nome interno do visual (por exemplo `7c162bc9717fa0da53f2`), estável entre original e cópia. É o que liga o antes ao depois; o índice pode mudar.
- `role`: `identidade`, `kpi`, `filtro`, `tendencia`, `comparacao`, `detalhe`, `secundario`, `nota`, `navegacao` ou `container`.
- `title`: rótulo curto usado nas mensagens e no esquema visual.
- `principal`: marca o visual mais importante da página.
- `stack`: mesmo valor para visuais empilhados de propósito; a conferência aceita a sobreposição entre eles e exige geometria idêntica.
- `full_bleed`: `true` para uma faixa de título de borda a borda no topo; a conferência deixa de cobrar a margem dela.
- `fields`: campos exibidos; em tabelas e matrizes, a quantidade decide a largura mínima.
- `slicer_mode`: em segmentadores, `Dropdown` (lista suspensa) ou `Basic` (lista vertical).
- `items`: quantos itens a lista vertical exibe; decide se ela cabe na faixa superior e pesa na altura que recebe na coluna.
- `field`: em segmentadores, o campo filtrado (`Tabela.Coluna`); filtros do mesmo campo ficam na mesma posição entre páginas.
- `is_group`: `true` para o container de um grupo. `parent`: nos filhos, o `id` do grupo. `rel_x` e `rel_y`: coordenadas relativas ao grupo.
- `hidden`: visual oculto no arquivo (costuma alternar por bookmark).
- `role_sugerido`, `principal_sugerido`, `stack_sugerido`: marcas do inventário automático. Não precisam ser apagadas à mão: a proposta e o `--herdar` as removem.
- Só na proposta: `de` (geometria original de cada visual que mudou), `z_atras` (formas de fundo), `aplicar_filho` (filhos de grupo que precisam ser movidos) e, no topo do documento, `decisoes` e `limitacoes`.
- Só no inventário com `--herdar`: `sem_correspondencia`, a lista de `id` da cópia que não existem na proposta (precisa vir vazia).
- Coordenadas sempre absolutas, em pixels da página.
