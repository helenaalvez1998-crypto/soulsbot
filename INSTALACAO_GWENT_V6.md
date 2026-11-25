> Documento histórico. A V8 substitui este fluxo e consolida o Gwent como único jogo de cartas ativo. Consulte `CHANGELOG_GWENT_V8.md` e `INSTALACAO_GWENT_V8.md`.

# Instalação — Gwent V6

1. Faça backup do banco de dados e dos arquivos de configuração.
2. Pare o bot.
3. Extraia o pacote completo sobre a pasta `narabot-main`, substituindo os arquivos.
4. Preserve `.env`, `config.py` específico do servidor e o banco de dados atual.
5. Confirme que `cogs/cartas_coliseu.py` foi removido do deploy; a V6 já não o carrega.
6. Reinicie o bot e atualize o navegador com `Ctrl + F5`.

A V6 não apaga tabelas históricas do jogo antigo. Ela remove seus pontos de entrada, rotas e interfaces. O inventário existente permanece disponível para formar decks Gwent.
