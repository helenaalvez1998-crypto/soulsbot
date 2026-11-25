> Documento histórico. A V8 substitui este fluxo e consolida o Gwent como único jogo de cartas ativo. Consulte `CHANGELOG_GWENT_V8.md` e `INSTALACAO_GWENT_V8.md`.

# Gwent do Coliseu — V6

## Remoção do jogo antigo
- Removido o carregamento do cog `cogs.cartas_coliseu`.
- Removidos os endpoints HTTP do deck antigo de 5 cartas, duelos antigos e WebSocket antigo.
- Removidos os atalhos do painel de membros e da administração que abriam o jogo antigo.
- Removidas as páginas antigas de coleção, deck e duelos do site; o Gwent é a única interface de jogo.
- Removido o cog antigo do pacote.
- As rotas de cartas e imagens foram migradas para `/api/gwent/cards`.

## Dados preservados
As tabelas e registros históricos do banco não são apagados nesta atualização. O Gwent continua usando a coleção de cartas já existente como fonte de propriedade, mas não chama o motor antigo de duelos. Isso evita perda irreversível de inventário ou histórico.
