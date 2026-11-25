# NARABOT V65 — Correção efetiva das miniaturas do deck

## Causa identificada
As versões anteriores alteravam `narabot-visual-v59.css`, mas o `index.html` continuava requisitando o mesmo URL com `?v=59`. O navegador podia reutilizar a folha antiga em cache, fazendo parecer que as correções não funcionavam.

## Correção
- Atualizado o URL da folha para `narabot-visual-v59.css?v=65` para invalidar o cache.
- Conferido o HTML real: o deck selecionado é `#gwent-deck-selected.gwent-deck-selected` e cada item é `button.gwent-card-tile`.
- Forçada grade de 3 colunas no painel desktop.
- Limitada a área da arte e a imagem a 104 px de altura no desktop.
- Ocultado o rótulo repetitivo sob cada miniatura.
- Grade compacta de 4 colunas em telas menores.
- Preservados os eventos de clique, IDs, dados, endpoints e regras do jogo.

## Validação
- Verificação estática dos seletores contra o HTML e o gerador JavaScript.
- A renderização deve ser conferida no navegador após instalar a V65.
- Preservar `colizeu.db`.
