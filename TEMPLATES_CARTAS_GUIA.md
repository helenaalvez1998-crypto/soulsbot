# Templates completos das cartas — guia oficial do SoulsBot Coliseum

## Como funciona

As cartas **com arte personalizada aprovada** usam um template completo por raridade. O template contém fundo, placas vazias e acabamento; somente a janela da ilustração é transparente. O bot encaixa a arte atrás do template e escreve nome, raridade, poder, tipo/categoria, custo e habilidade nas placas.

As cartas **sem arte personalizada** continuam usando o renderizador procedural original. Os templates não alteram regras, atributos, coleção, duelo ou economia. Cada raridade tem seu próprio material e ornamentos, mas todas compartilham exatamente as mesmas coordenadas de placas e janela.

## Templates padrão incluídos

Os cinco templates corrigidos estão distribuídos em `assets/cartas_templates/`:

- `comum.png`
- `rara.png`
- `epica.png`
- `lendaria.png`
- `primordial.png`

Eles são carregados automaticamente, inclusive quando `DATA_DIR` aponta para um volume persistente separado. Um upload feito no painel administrativo substitui o padrão sem modificar os assets do projeto. A opção **Restaurar template padrão** remove a substituição e reativa o arquivo incluído.

## Geometria obrigatória

Canvas: **840 × 1240 px**, PNG RGBA. A única região transparente deve ser exatamente o retângulo da arte:

- Janela da arte: `(56, 256) → (784, 846)` — **728 × 590 px**.
- Os pixels da janela devem ter alpha 0.
- Todo o restante do template deve ser opaco (alpha 255).
- Não pode haver texto rasterizado no template; os textos são escritos pelo Pillow.

### Slots na grade 840 × 1240

| Campo | Posição |
|---|---|
| Raridade | `600,44 → 784,96` |
| Nome | `56,100 → 784,236` |
| Arte | `56,256 → 784,846` |
| Poder | centro `144,986`, raio `78` |
| Tipo / categoria | `254,918 → 780,978` |
| Custo | `254,992 → 780,1052` |
| Habilidade | `56,1084 → 784,1176` |

A geometria é compartilhada pelas cinco raridades. Não crie JSON de coordenadas por raridade para compensar placas desalinhadas: corrija o PNG para respeitar este guia. Arquivos JSON antigos de layout são ignorados pelo renderizador; as coordenadas deste guia são a única fonte de verdade.

## Substituir um template pelo Discord

1. Abra `/adm`.
2. Entre em **Jogos, Coliseu e runs**.
3. Abra **Templates completos das cartas**.
4. Selecione a raridade e envie um PNG como anexo na DM da Nara.
5. O bot valida dimensão, proporção, transparência e posição exata da janela, salva a substituição no volume persistente e gera uma prévia.

Somente o proprietário global do bot pode alterar templates globais. Os uploads ficam em `DATA_DIR/cartas_templates/`.

## Regras de validação

- Canvas recomendado e padrão: exatamente 840 × 1240 px; 420 × 620 px é o mínimo aceito antes da normalização. A proporção tem tolerância de apenas 0,5% para não deformar as placas.
- PNG RGBA recomendado; JPEG/WEBP podem ser enviados somente quando a janela usa magenta chapado `#FF00FF`.
- A janela deve coincidir com `(56,256) → (784,846)`, com tolerância máxima de 3 px após normalização. O renderizador usa o retângulo detectado, mas rejeita qualquer desvio maior.
- Pelo menos 99,5% dos pixels da janela devem ter alpha 0.
- Pelo menos 99,5% dos pixels fora da janela devem ter alpha 255; os templates oficiais têm opacidade total fora da janela.
- Se um upload antigo no volume persistente estiver inválido, o bot ignora esse arquivo e usa o template padrão incluído no projeto.
- Arquivo de até 8 MB e 20 milhões de pixels.

## Observações

- O arquivo de arte é ajustado para 728 × 590 px; o sistema não deve mudar a posição dos slots para acomodar templates fora do guia.
- O cache de cartas usa a versão visual 5 para impedir que imagens antigas persistam após a atualização dos templates.
- Cartas já enviadas no Discord não são editadas retroativamente.
- A prévia de calibração do painel mostra os slots oficiais sobre a carta renderizada.
