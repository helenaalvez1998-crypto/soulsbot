# Instalação — Design das Cartas V5

1. Faça backup da pasta de dados e do banco de dados atual.
2. Pare o bot.
3. Extraia o conteúdo deste pacote sobre a pasta atual do projeto.
4. Preserve o arquivo `.env`, o banco de dados e o diretório de dados persistentes.
5. Reinicie o bot normalmente.

A versão visual das artes foi incrementada. As cartas serão regeneradas automaticamente quando forem solicitadas; não é necessário apagar a coleção nem recriar os decks.

## Observação sobre templates enviados pelo Discord

O novo design é aplicado ao renderizador padrão do Pillow. Se houver um template completo personalizado cadastrado no Ateliê para uma raridade, esse template continua tendo prioridade. Um custo que esteja desenhado dentro de um template antigo não pode ser removido automaticamente pelo renderizador: envie um template atualizado sem o custo ou remova o template personalizado para usar o padrão.

Esta atualização é visual e não exige migração do banco de dados.
