# Remoção definitiva do jogo antigo (duelo de 5 cartas)

Removido do código (o Gwent do Coliseu é o único jogo):

- `database.py`: tabelas `cartas_decks`, `cartas_deck_itens`, `cartas_duelos`, `cartas_duelo_deck`,
  `cartas_duelo_jogadas`, `cartas_duelo_rounds`, `cartas_duelo_participacoes`, `cartas_missoes_recompensas`
  (schema e migração), coluna `duel_id` de `cartas_transacoes` (só no schema de instalações novas),
  e os métodos de convite/duelo/rodada/ranking/missões/prazos/deck antigo e `coliseu_forjar_carta`.
- `sistemas/cartas.py`: regras do duelo (`resolver_rodada`, tipos/tríade, narração, validação de deck de 5),
  `carta_dict`, `CICLO_TIPOS`, `EMOJIS_TIPO`.
- `sistemas/arte_cartas.py`: tabuleiro de duelo, GIF de revelação, dashboard da arena, deck preview.
- `bot.py`: rota e handler `/api/gwent/store/forge` (forja desativada) e `forge_cards`.

Bancos existentes: nenhuma tabela é apagada (sem DROP); as tabelas históricas ficam intactas, só não são mais usadas.
