# Gwent V9 — conversão visual e semântica do catálogo

## Correções
- Removida a serialização de categorias de origem (Chefe, Arma, Magia, Covenant, Jogo e Patente) para os dados exibidos no Gwent.
- Cartas passam a expor apenas Unidade/Especial, facção, fileira e papel tático do Gwent.
- Renderizador redesenhado para compor unidades por facção e fileira, sem reutilizar os símbolos de armas/magias/covenants do catálogo antigo.
- Nas cartas, Destreza/Força/Magia deixam de ser rótulos visíveis: a identidade exibida é a facção e a fileira.
- Recompensas de jogos externos mantêm IDs históricos, mas recebem nomes, descrições e identidade visual do universo Gwent; o título externo não aparece na carta.
- Cartas de patente recebem nomes e descrições de progressão do Gwent, sem carimbar a patente antiga na arte.
- Prompts do Ateliê agora usam facção e fileira e proíbem referência visual/textual a franquias externas.
- Snapshots de decks são reconstruídos integralmente do catálogo canônico, preservando IDs e slots.
- Versão de artes elevada para 10 para invalidar o cache antigo sem apagar dados dos jogadores.

## Compatibilidade e dados
- IDs das cartas e quantidades nas coleções permanecem inalterados.
- Nenhuma tabela ou inventário é apagado.
- O cache antigo não é removido; novos arquivos são gerados sob uma chave de cache nova.
