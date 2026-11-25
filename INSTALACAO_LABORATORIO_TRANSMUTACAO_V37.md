# Instalação — Laboratório de Transmutação V37

1. Faça backup do banco SQLite, da pasta de dados `cartas_geradas/` e da instalação atual.
2. Extraia o pacote preservando os diretórios.
3. Atualize `database.py`, `bot.py` e `sistemas/gwent.py`; mantenha os demais arquivos e migrações das versões anteriores.
4. Reinicie o bot/site e monitore os logs.
5. Em homologação, use duas contas:
   - A cria uma carta pessoal e a adiciona ao deck.
   - B enfrenta a carta em uma partida.
   - B tenta salvar o `card_id` da carta de A no próprio deck; a operação deve ser recusada.
   - Modifique em ambiente de teste `card_id`, `origin_type`, `is_sacrificable` e `user_id` do exemplar; a preparação deve falhar.
   - Confirme que cartas pessoais continuam excluídas de todos os fluxos de sacrifício.
6. Não considere a versão homologada em produção até concluir os testes com duas contas e banco real.

A V37 não adiciona migração de esquema. As consultas de exemplares passam a retornar campos de segurança já existentes na tabela.
