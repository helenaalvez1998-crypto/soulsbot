# V11 — Heráldica exclusiva por facção

## Objetivo

Dar às três facções uma linguagem ornamental claramente diferente sem modificar o formato externo da carta nem a composição do layout.

## O que mudou

- **Ordem Áurea:** arcadas inspiradas em Leyndell, brotos/folhas da Térvore, cartuchos ovais e rosácea solar.
- **Véu Carmesim:** ferragens de tridente, espinhos, gotas rituais, medalhões de sangue e corrente cerimonial.
- **Lua Negra:** astrolábios, constelações, crescentes, órbitas e estrela polar.
- Os ornamentos foram reforçados nas faixas laterais e nos cantos superior/inferior para continuarem reconhecíveis em miniaturas.
- A raridade continua definindo metal, cor, brilho e acabamento; a facção define a heráldica.

## O que foi preservado

- Silhueta externa retangular vertical, com quatro cantos de 90 graus.
- Dimensão-base de 420 × 620.
- Janela e recorte da ilustração.
- Placas, medalhão de poder, emblema, fileira, raridade e painel de habilidade.
- Sistema de geração e substituição de artes.
- Regras, cartas, coleções, decks e banco de dados.

## Validação

- `python -m compileall -q .`
- `python -m unittest discover -s tests -v`
- Teste específico compara as gravações laterais das três facções.
- Teste de silhueta confirma que as três facções usam exatamente a mesma geometria externa.
