# Operações no pbix-mcp para reorganizar layout

Sequência de ferramentas e armadilhas conhecidas. Os nomes abaixo são os do servidor pbix-mcp; o prefixo que o cliente acrescenta varia conforme a instalação: `mcp__plugin_power-bi_layout_with_pbix-mcp_pbix-mcp__` para o servidor que o plugin traz, `mcp__pbix-mcp__` para um pbix-mcp configurado à parte. Escolha um e use só ele na reorganização inteira, porque cada servidor tem os seus próprios arquivos abertos.

O inventário sai de `scripts/inventario_pbix.py`, que lê o .pbix como zip sem passar pelo pbix-mcp; as ferramentas de leitura abaixo servem para conferi-lo e para o que o arquivo não mostra sozinho (itens de um segmentador, bookmarks).

## Sequência

| Etapa | Ferramenta | Observação |
|---|---|---|
| Abrir | `pbix_open(file_path, alias)` | Use um alias curto, como `orig`. Se não abrir, rode `pbix_doctor(alias)` e relate o diagnóstico. |
| Listar páginas | `pbix_get_pages(alias)` | Dá as páginas, a contagem de visuais e o tamanho (por exemplo `1920x1080`). A lista de componentes devolvida por `pbix_open` mostra o formato do relatório: `Report/definition/...` é PBIR; `Report/Layout` é o formato legado. |
| Listar visuais | `pbix_get_page_visuals(alias, page_index)` | O `visual_index` desta lista é o que `pbix_move_visual` usa. A lista mostra o nome interno de cada visual (`name=...`), que é o `id` do inventário: ligue índice e `id` por ele, não pela ordem do JSON. |
| Posições absolutas | `pbix_get_visual_positions(alias, page_index)` | Resolve o deslocamento de grupos para coordenadas absolutas da página. Use estas coordenadas no inventário. |
| Detalhe de um visual | `pbix_get_visual_detail(alias, page_index, visual_index)` | Para título, campos, modo do segmentador (`Dropdown` ou `Basic`) e estado oculto. |
| Itens de um segmentador | `pbix_query_table(alias, table_name, columns="Campo", max_rows=5000)` | Para contar os valores distintos que uma lista vertical vai exibir e estimar a altura que ela pede. |
| Bookmarks | `pbix_get_bookmarks(alias)` | Ajuda a detectar visuais empilhados que se alternam. |
| Mover e redimensionar | `pbix_move_visual(alias, page, visual_index, x, y, width, height, z)` | `page` aceita índice ou nome de exibição. `-1` deixa o valor inalterado. A posição fica no container do visual; `pbix_set_visual_property` não a alcança. |
| Salvar | `pbix_save(alias, output_path, overwrite=False, backup=True)` | Passe `output_path` com o nome da cópia. Com `output_path` vazio, o arquivo original é sobrescrito. |
| Comparar modelo | `pbix_diff(alias_a, alias_b)` | Confirma que tabelas, medidas, relacionamentos, páginas, visuais e tema não mudaram. Não compara posições: depois de uma reorganização correta, responde "sem mudanças" em todas as seções. A prova de que só a geometria mudou vem de `scripts/compare_pbix.py`. |
| Fechar | `pbix_close(alias, force)` | Recusa fechar arquivo com alterações não salvas. Salvar com `output_path` diferente não limpa esse estado, então, depois de confirmar que a cópia foi gravada, feche o original com `force=True`. |

## Armadilhas

**Coordenadas em grupos.** Para visuais dentro de um grupo, o x e o y gravados são relativos ao grupo. `pbix_get_visual_positions` converte para absoluto na leitura, mas, ao escrever com `pbix_move_visual` num filho de grupo, passe coordenadas relativas ao grupo (absoluta menos o deslocamento do grupo). O caminho mais seguro é mover o container do grupo e deixar os filhos intactos. Depois de mover filhos, releia as posições para confirmar onde eles foram parar.

**Índices estáveis.** Faça o inventário e a aplicação na mesma sessão aberta, sem adicionar nem remover visuais, para que os índices continuem apontando para os mesmos visuais. Se reabrir o arquivo, liste os visuais de novo antes de mover.

**Ordem de camada.** Só altere `z` de formas de fundo, para garantir que fiquem atrás do bloco. Mudar a camada de outros visuais pode esconder um visual atrás de outro em layouts com sobreposição intencional.

**Sem renderização.** O pbix-mcp opera sobre a definição do relatório e não desenha a página. Legibilidade de rótulos, quebras de título e barras de rolagem em tabelas só podem ser conferidas no Power BI Desktop. Por isso os mínimos de tamanho da skill são conservadores.

**Salvar com segurança.** `overwrite=False` faz o salvamento falhar se a cópia já existir. Nesse caso, acrescente um sufixo numérico (`_reorganizado_2.pbix`) em vez de forçar a sobrescrita.

**O que o salvamento altera além da geometria.** Observado em teste com relatório PBIR (pbix-mcp 0.9.153): o arquivo `SecurityBindings` é descartado, os `page.json` e o `pages.json` são regravados com outra indentação, sem mudança de conteúdo, e a ordem dos arquivos dentro do zip muda. `compare_pbix.py` classifica esses três casos como informação, não como violação. Peça ao usuário que confirme que a cópia abre no Power BI Desktop.

**Ordem de tabulação.** No PBIR, `tabOrder` fica no mesmo bloco `position` que x, y e z, e `pbix_move_visual` não o altera. Depois da reorganização, a ordem de tabulação continua a original, o que pode não acompanhar a nova ordem de leitura. Registre isso como recomendação, sem alterar.

## Formato do inventário (`layout_antes.json` e `layout_depois.json`)

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

- `type` de página: `normal`, `tooltip` ou `drillthrough`.
- `role`: `identidade`, `kpi`, `filtro`, `tendencia`, `comparacao`, `detalhe`, `secundario`, `nota`, `navegacao` ou `container`.
- `id`: o nome interno do visual (por exemplo `7c162bc9717fa0da53f2`), que é estável. É o que liga o antes ao depois; não use o índice, que pode mudar.
- `full_bleed`: opcional, `true` para uma faixa de título de borda a borda no topo; o script deixa de cobrar a margem dela.
- `title`: opcional, rótulo curto usado no esquema visual.
- `principal`: opcional, marca o visual mais importante da página.
- `stack`: opcional, mesmo valor para visuais empilhados de propósito; o script aceita a sobreposição entre eles.
- `slicer_mode`: em segmentadores, `Dropdown` (lista suspensa) ou `Basic` (lista vertical). Lista vertical vai para a coluna de filtros.
- `items`: opcional, quantos itens a lista vertical exibe; pesa na altura que ela recebe na coluna.
- `field`: em segmentadores, o campo filtrado (`Tabela.Coluna`); filtros do mesmo campo ficam na mesma posição entre páginas.
- `is_group`: `true` para o container de um grupo; `parent`: nos filhos, o `id` do grupo. `rel_x` e `rel_y` são as coordenadas relativas ao grupo, as que `pbix_move_visual` espera para um filho.
- `hidden`: visual oculto no arquivo (costuma alternar por bookmark).
- `role_sugerido`, `principal_sugerido`, `stack_sugerido`: marcas do inventário automático; apague depois de conferir.
- Na proposta (`propor_layout.py`): `de` com a geometria original de cada visual que mudou, `z_atras` nas formas de fundo, `grid` em cada página e, no topo do documento, `decisoes` e `limitacoes`.
- Coordenadas sempre absolutas, em pixels da página.
