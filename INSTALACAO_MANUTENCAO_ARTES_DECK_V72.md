# Instalação — Narabot V72

1. Faça backup do projeto e do banco de dados SQLite.
2. Substitua os arquivos do projeto pelos arquivos desta versão.
3. Reinicie o processo do bot/site.
4. Atualize o navegador com `Ctrl + F5` para carregar o JavaScript e CSS novos.

## Onde aparecem os botões
- `Deck e Coleção`: botão `Redefinir deck`, dentro do painel do deck. O jogador limpa somente o próprio deck salvo e pode montar outro com as cartas que já possui.
- `Ateliê`: dentro do painel administrativo da fila de aprovação aparece `Remover todas as artes aplicadas`. O botão é restrito à equipe configurada em `COLISEUM_ART_REVIEWER_IDS` e aos administradores já definidos no bot.

## O que a remoção em massa faz
Arquiva as artes comunitárias atualmente aprovadas. As cartas voltam à arte-base. Os arquivos enviados, créditos e histórico continuam preservados no banco. Pedidos pendentes não são removidos.

## O que o reset do deck faz
Apaga as 12 seleções e o loadout de facção/líder/relíquia do deck do usuário autenticado. Não apaga cartas da coleção nem modifica partidas já iniciadas.

Não há migração de banco de dados nesta versão.
