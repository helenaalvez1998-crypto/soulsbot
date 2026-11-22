# Correções dos templates de cartas — SoulsBot Coliseum

## Arquivos e geometria

Os cinco templates padrão foram reconstruídos a partir das artes fornecidas, preservando a identidade visual de cada raridade e reposicionando as placas para obedecer ao `guia_template_carta_840x1240.png`.

- Canvas: 840 × 1240 px, PNG RGBA.
- Janela única da ilustração: `(56, 256) → (784, 846)`, 728 × 590 px.
- Alpha da janela: 0 em todos os pixels.
- Alpha fora da janela: 255 em todos os pixels.
- Raridade: `(600,44) → (784,96)`.
- Nome: `(56,100) → (784,236)`.
- Poder: centro `(144,986)`, raio `78`.
- Tipo: `(254,918) → (780,978)`.
- Custo: `(254,992) → (780,1052)`.
- Habilidade: `(56,1084) → (784,1176)`.

## Ajustes visuais nos cinco arquivos

- As placas de raridade, nome, poder, tipo, custo e habilidade foram movidas e redimensionadas para os slots do guia.
- As superfícies internas foram escurecidas seletivamente para manter contraste com a tipografia do Pillow, sem apagar as bordas e ornamentos específicos de cada raridade.
- A abertura de ilustração foi refeita como um retângulo limpo; ornamentos da Legendary foram mantidos fora da área de arte.
- O selo superior da Epic foi reconstruído para não colidir com o cristal decorativo.
- A franja de transparência e qualquer preenchimento dentro da janela foram removidos.
- Todas as cinco imagens foram exportadas no mesmo tamanho e com a mesma geometria.

## Ajustes no código

- `sistemas/templates_cartas.py`: layout fixo pelo guia; validação de proporção mais estrita; validação da janela e da opacidade; arquivos JSON antigos de coordenadas ignorados; fallback automático para o template padrão se um upload persistente antigo estiver inválido.
- `sistemas/arte_cartas.py`: prévias administrativas usam uma ilustração de demonstração sem duplicar a etiqueta antiga de tipo/categoria.
- `sistemas/cartas.py`: versão visual/cache atualizada para 5.
- `cogs/cartas_coliseu.py`: painel administrativo informa quando um upload antigo inválido foi ignorado e o padrão está ativo.
- `dados/TEMPLATES_CARTAS_PROMPTS.md`: prompts corrigidos para exigir exatamente uma janela transparente e superfícies opacas no restante da carta.
- `tests/test_templates_cartas_quality.py`: testes de geometria, alpha, uploads inválidos, fallback, proporção e prévias de todas as raridades.

## Validação executada

- 21 testes específicos dos templates: aprovados.
- Compilação dos módulos alterados: aprovada.
- Testes de dimensão, modo RGBA e alpha dos cinco PNGs: aprovados.
- A suíte completa foi comparada com o ZIP original: as mesmas 18 falhas preexistentes aparecem em ambos os projetos. A versão corrigida acrescenta os testes novos dos templates; não introduziu novas falhas na suíte existente.
