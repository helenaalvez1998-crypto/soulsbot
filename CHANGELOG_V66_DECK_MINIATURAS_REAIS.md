# NARABOT V66 — Miniaturas reais no deck montado

## Correção estrutural
A V65 ainda reutilizava o mesmo componente de carta da coleção (`gwent-card-tile`) para o deck selecionado. Isso deixava a aparência do deck dependente das regras genéricas da galeria e das cascatas antigas do CSS.

Na V66, o renderizador JavaScript cria uma classe exclusiva `gwent-deck-mini` para cada carta que já está no deck. O CSS passa a controlar diretamente esse componente dedicado.

## Resultado pretendido
- Desktop: grade de 3 colunas no painel do deck.
- Arte limitada a 106 px de altura por miniatura.
- Nome curto da carta em uma linha.
- Clique continua abrindo a ficha completa (`data-gwent-inspect` preservado).
- Coleção continua usando o componente e dimensões normais.
- Tablet/celular: grade de 4 colunas e miniaturas de 94 px.

## Cache
- Atualizados os parâmetros de versão do `app.js` e do CSS para `v66`.

## Segurança da alteração
- Não altera IDs das cartas, dados, APIs, banco, seleção, validação ou salvamento do deck.
- Preservar `colizeu.db`.
- Validação estática do template e seletores; confirmar renderização no navegador.
