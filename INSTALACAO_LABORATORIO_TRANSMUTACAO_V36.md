# Instalação — Laboratório de Transmutação V36

1. Faça backup do banco SQLite, da pasta de dados `cartas_geradas/` e da instalação atual.
2. Extraia o pacote preservando a estrutura de diretórios.
3. Atualize `bot.py`, `sistemas/gwent.py` e os testes/documentos da V36.
4. Mantenha as versões V28–V35 e as migrações já aplicadas. A V36 não adiciona tabelas nem exige migração de banco.
5. Reinicie o bot/site.
6. Em homologação, com duas contas diferentes:
   - crie uma carta pessoal na conta A;
   - confirme que ela aparece no construtor e na coleção da conta A;
   - salve-a em um deck da conta A e inicie uma partida contra a conta B;
   - confirme que B consegue enfrentar a carta e ver sua arte;
   - confirme que B não consegue adicionar o `card_id` ao próprio deck;
   - confirme que a carta continua indisponível para sacrifício em todos os rituais.
7. Teste também cartas pessoais após lapidação e ascensão na Forja.

A V36 não deve ser considerada homologada em produção até esses testes com duas contas serem concluídos.
