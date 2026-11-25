> Documento histórico. A V8 substitui este fluxo e consolida o Gwent como único jogo de cartas ativo. Consulte `CHANGELOG_GWENT_V8.md` e `INSTALACAO_GWENT_V8.md`.

# Instalação — Arena Gwent v2

## Antes de atualizar
1. Pare o processo do bot.
2. Faça uma cópia de segurança do banco SQLite usado em produção.
3. Guarde seu `.env` e quaisquer arquivos de configuração locais.

## Atualização
1. Extraia o conteúdo deste ZIP sobre a pasta atual do projeto, substituindo os arquivos.
2. Preserve o `.env` existente. O ZIP não deve substituir credenciais.
3. Instale dependências apenas se seu ambiente ainda não as tiver (`pip install -r requirements.txt`).
4. Inicie o bot normalmente. O `SCHEMA_CARTAS` cria as tabelas competitivas novas automaticamente.

## O que acontece com os dados existentes
- Coleção, Denários, Almas, conquistas e histórico clássico não são apagados.
- Decks Gwent antigos com 10 cartas continuam salvos; adicione duas cartas no construtor do site e salve o deck de 12.
- Partidas já em andamento continuam compatíveis com o motor atualizado.
- Ao abrir o painel de cartas no Discord, cada conta recebe uma única vez duas cartas especiais Gwent. A entrega tem tabela própria e também atende contas que já receberam o kit Gwent anterior.
- O ranking começa em 1000 MMR para quem ainda não tem registro.

## Regras competitivas
- Deck: 12 cartas únicas; mão inicial de 10 e reserva de 2.
- Mulligan: cada jogador pode trocar até duas cartas antes da batalha.
- Facções: Ordem de Ferro (Força), Errantes do Véu (Destreza) e Conclave Arcano (Magia). A primeira unidade da facção recebe +1 por rodada.
- Vitória: +25 MMR e 40 Denários.
- Derrota: -15 MMR e 15 Denários.
- Empate: MMR inalterado e 25 Denários para cada jogador.
- O registro de recompensa é idempotente por partida e jogador.

## Validação feita nesta entrega
- `py_compile` dos módulos Python alterados.
- `node --check site/app.js`.
- 9 testes unitários do motor Gwent.
- Execução do schema SQLite em banco temporário, confirmando as novas tabelas.
- Não foi possível executar um teste de integração contra o Discord e o banco real neste ambiente.
