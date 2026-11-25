# NARABOT V61 — Catálogo limpo e ficha de carta

## Catálogo / Deck e Coleção
- Removidos nome, facção, raridade, fileira, poder, potência e botões da grade externa de cartas.
- Cada posição da coleção e do deck mostra somente a arte completa da carta, com uma indicação discreta de interação.
- Clique/toque na carta abre uma ficha de detalhes.
- Os filtros continuam pesquisando também habilidade, efeito e descrição.

## Ficha ao abrir uma carta
- Layout reorganizado em arte, identificação, atributos, efeito de combate, lore e sinergias.
- Ações de adicionar/remover do deck, evoluir e lapidar foram movidas para a ficha.
- Restrições existentes de 12 cartas, 8 unidades, máximo de 4 especiais e modelos únicos continuam validadas.
- Fechamento pelo botão, clique no fundo e tecla Escape.

## Texto dos efeitos na própria arte
- A arte oficial continua sendo gerada com `preparar_carta`, que prioriza efeitos de identidade e o texto mecânico efetivo do motor.
- Aumentada a versão de cache da imagem no cliente para solicitar novamente as artes atualizadas.
- Não se usa descrição narrativa como fallback de efeito mecânico.

## Validação
- `node --check site/app.js`: aprovado.
- `python -m compileall -q site_portal.py sistemas bot.py`: aprovado.
- `python -m unittest tests.test_elden_gwent tests.test_gwent_transmutacao_v36`: 22 testes aprovados.
- Não foi executada validação visual em navegador nesta sessão.
