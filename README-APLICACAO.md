# Patch inicial da API HTTP do SoulsBot

O pacote contém somente `bot.py` atualizado e este guia.

## O que muda
- Inicia um servidor HTTP no mesmo processo do bot Discord.
- Usa `PORT` fornecida pela FadeHost (fallback local: 8080).
- Escuta em `0.0.0.0`.
- Disponibiliza `GET /` e `GET /api/status`.
- Encerra o servidor HTTP junto com o bot.
- Não altera regras, tabelas SQLite, contas, cartas ou Denários.

## Como aplicar
1. Faça backup do repositório atual e do banco persistente na FadeHost.
2. No repositório GitHub conectado à FadeHost, substitua o `bot.py` da raiz por este arquivo.
3. Faça commit e push para a branch acompanhada pela FadeHost.
4. Acompanhe o deploy e procure nos logs por `API HTTP iniciada em 0.0.0.0:8080`.
5. Após o deploy, abra `https://soulsbot.fadehost.app/api/status`.

Resposta esperada:
```json
{
  "service": "soulsbot-api",
  "status": "online",
  "discord_connected": true,
  "database": "connected"
}
```

Durante a inicialização, `discord_connected` pode aparecer como `false`; atualize a página depois que o bot conectar.

## Escopo e segurança
Este é apenas um endpoint público de diagnóstico. Não expõe dados dos jogadores nem permite executar ações no jogo. Login Discord, autenticação e endpoints de coleção/deck/duelo ainda não foram implementados.

Se o deploy falhar, não faça outras alterações. Envie os logs da FadeHost para análise, ocultando tokens, senhas e segredos.
