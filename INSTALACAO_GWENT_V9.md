# Instalação — Gwent V9

1. Faça backup do banco SQLite e da pasta `data/`.
2. Desligue o bot.
3. Extraia o pacote completo ou aplique os arquivos alterados mantendo os caminhos.
4. Não apague `data/`, `.env` ou o banco de dados.
5. Reinicie o bot.
6. Atualize o site com Ctrl+F5.

A versão de artes foi incrementada para 10. Isso faz o renderizador gerar novas imagens e deixar de servir as imagens de cartas armazenadas sob a chave antiga. Os arquivos antigos de cache podem permanecer no disco sem serem utilizados.

Os IDs e as quantidades de cartas dos jogadores são preservados. Os snapshots de decks antigos são reconstruídos quando carregados, usando o catálogo canônico atualizado.
