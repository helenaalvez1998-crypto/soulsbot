# V51 — Sistema visual semântico das cartas

## Implementado
- Insígnias vetoriais locais para facções, fileiras, raridade, categoria e famílias de efeitos.
- Cartas do construtor de deck e da coleção de seleção agora recebem faixa de facção/raridade e faixa de fileira/habilidade.
- Cartas sem habilidade exibem explicitamente “Força pura”; isso é apresentação, não efeito novo.
- Inspeção de carta em combate ganhou tags com símbolos semânticos.
- CSS responsivo dedicado ao novo sistema de cartas, sem remover a arte original nem alterar a proporção 420:620.
- Nenhuma dependência externa de ícones foi adicionada.

## Preservação
- Nenhuma regra de batalha, poder, custo, habilidade, drop ou balanceamento foi alterada.
- As unidades sem habilidade continuam sem habilidade.
- O motor continua sendo a fonte de verdade para o efeito executado.

## Validação
- `node --check site/app.js`: aprovado.
- Testes de regressão direcionados: 35 passed, 7 subtests passed.
- Não foi realizado teste visual automatizado em navegador nesta etapa.
