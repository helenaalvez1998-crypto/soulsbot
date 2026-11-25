# Instalação — Molduras V12

1. Faça backup da instalação atual.
2. Extraia o conteúdo deste pacote sobre a pasta `narabot-main`.
3. Preserve o arquivo `.env`, o banco de dados e a pasta `data/`.
4. Reinicie o bot para que o renderizador e o cache em memória sejam recarregados.

A V12 altera somente a renderização visual das molduras. Não altera cartas, regras, IDs, decks, coleções, artes enviadas nem prompts de geração.

A chave de versão do renderizador foi atualizada para V12 e o fingerprint do código também muda automaticamente, invalidando as imagens antigas em cache persistente.
