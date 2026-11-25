# V55 — Redesign premium das cartas

## Escopo
Reformulação visual da representação das cartas na coleção/construtor de decks. A alteração não modifica regras, balanceamento, poderes, raridades, habilidades ou resolução de combate.

## Alterações
- Novo componente visual `cardFaceMarkup`, com arte em tela cheia, vinheta, moldura interna, cantoneiras, cabeçalho de facção/raridade, selo de poder, título e faixa de efeito.
- Tratamento visual individual para as facções Ordem Áurea, Véu Carmesim e Lua Negra.
- Acabamentos por raridade: Comum, Rara, Épica, Lendária, Mítica, Primordial e Singular.
- Cartas especiais mantêm distinção de categoria e usam hierarquia visual própria.
- Exemplar e ações de deck/Forja ficam fora da face da carta para não competir com a arte.
- Layout responsivo para desktop e mobile, com suporte a `prefers-reduced-motion`.
- Mantida a origem de arte já existente via `cardImageMarkup` e API de imagens.

## Validação executada
- `node --check site/app.js`: aprovado.
- `python -m pytest -q tests/test_elden_gwent.py tests/test_auditoria_efeitos_v50.py`: 24 passed, 7 subtests passed.
- Não foi executado teste visual em navegador real nem homologação em ambiente de produção.

## Observação
A nova composição melhora moldura, hierarquia, contraste e leitura, mas não cria novas ilustrações de personagens. A arte exibida continua vindo do pipeline de imagens já existente.
