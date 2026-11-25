# V80 — Revisão completa do catálogo e clareza das cartas

## Objetivo

Fazer a ficha de cada carta corresponder ao efeito realmente executado pelo motor e separar claramente:

1. **O que a carta faz** — condição, alvo, quantidade e resultado do efeito.
2. **Bônus da raridade** — somente o que a raridade realmente altera, em seção própria.
3. **História (lore)** — contexto narrativo, sem instruções de combate.
4. **Combos possíveis** — efeitos que dependem de composição, separados da habilidade individual.

## Escopo conferido

- 122 registros estáticos: 95 cartas do catálogo principal, 12 cartas da expansão V75, 5 cartas Primordiais e 10 recompensas de patente.
- 60 exemplos dinâmicos de recompensas geradas (30 nomes × marcos `zerado` e `platina`), além das recompensas de patente.
- Textos de habilidade efetiva, bônus de raridade, lore, facção, fileira, poder-base, raridade, custo e combos.
- Textos e símbolos usados pelo renderizador de artes e pelos painéis de detalhes.

## Correções relevantes

- A ficha não mostra mais uma habilidade genérica que o motor substitui por uma habilidade de identidade.
- Cartas de combo sem efeito individual são identificadas como cartas que só funcionam em combo; seus combos aparecem em seção própria.
- O texto de Estandarte foi alinhado ao efeito real: concede bônus aos aliados que já estão na fileira, não à própria carta que está entrando.
- Condições descritas como “turno anterior” foram corrigidas quando o motor verifica a última unidade jogada pelo inimigo na rodada atual.
- A apresentação da raridade foi separada do efeito principal e personalizada para os efeitos que usam limites específicos: marcas, recuperação, compra, invocação, escudos e movimento.
- Chamado dos Mortos explicita o retorno à mesma fileira e a perda de bônus e escudo.
- A arte passou a usar o ID e o texto da habilidade efetivamente executada, não um efeito genérico oculto.
- Textos da arte foram testados para caber no espaço previsto.
- Versão das artes e cache do navegador atualizada para 33.
- Corrigidos alvos próprios indevidos em Caçador Solitário e Devorar.

## Integridade do jogo

IDs, raridades, poder-base, custos, efeitos de combate e limites de balanceamento foram preservados, exceto correções de bugs em que a própria execução contrariava a regra esperada ou o texto divulgado. Não foi criada uma mecânica nova.

## Testes

- `83 passed`
- `61 subtests passed`
- `node --check site/app.js` aprovado.
- `py_compile` de `sistemas/cartas.py`, `sistemas/gwent.py` e `sistemas/arte_cartas.py` aprovado.

A suíte completa do repositório não foi executada; foram executadas as suítes direcionadas de catálogo, efeitos, expansão, competitividade, arte e separação entre lore e habilidade.

## Limite da auditoria

Os 122 registros estáticos foram inventariados individualmente. As 60 recompensas dinâmicas são amostras do gerador, que aceita títulos arbitrários. A auditoria confirma a separação entre narrativa e mecânica e a correspondência dos textos com o código do jogo; não equivale a uma checagem documental independente de cada frase de lore contra todas as fontes canônicas de Elden Ring.

## Ajustes de execução necessários para coerência

Foram corrigidos casos em que o motor contava a própria carta como se fosse um aliado já presente: Guardião de Fileira, Caçador Solitário, Devorar e verificações de aliados das habilidades de identidade. Isso corrige alvos e condições impossíveis ou autodestrutivas; não cria uma habilidade nova.

## Observação de empacotamento

Os arquivos binários de fonte não estão incluídos no ZIP. O renderizador tenta usar fontes DejaVu instaladas no ambiente do servidor como alternativa; confirme que elas existem no ambiente de implantação para manter a mesma tipografia das prévias.
