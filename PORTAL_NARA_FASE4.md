# NARA Portal — Fase 4: cargos selecionáveis e painéis Discord

## Entregas

### Cargos selecionáveis pelos membros
- Novo cog `cogs.portal_role_panel`, carregado pelo `bot.py`.
- Painel Discord persistente com menu de seleção de até 25 cargos.
- O membro pode adicionar/remover cargos configurados sem abrir ticket.
- A seleção é validada contra a lista configurada para o servidor.
- O portal lista cargos do servidor e permite salvar até 25 opções.
- O backend rejeita cargos inexistentes, gerenciados, @everyone e cargos acima/iguais ao maior cargo do bot.

### Publicação e atualização de painéis
- Nova API administrativa `GET/POST /api/portal/admin/panels`.
- Publicação/atualização do painel de cargos selecionáveis.
- Publicação/atualização dos painéis públicos de Platinas e Jogos Zerados.
- O ID da mensagem publicada é persistido em KV por servidor/canal/tipo. Uma nova publicação no mesmo canal atualiza a mensagem registrada, quando ela ainda existe.
- A página de Administração ganhou formulários para escolher cargos e publicar os painéis.

## Rotas novas
- `GET/POST /api/portal/admin/roles`
- `GET/POST /api/portal/admin/panels`

As duas rotas exigem login Discord, origem de API autorizada e permissão de moderação/administrador.

## Requisitos operacionais
- Bot com `Gerenciar Cargos` e hierarquia acima de todos os cargos selecionáveis.
- Bot com `Enviar Mensagens` e `Inserir Links` no canal de publicação.
- Intents e permissões do Discord configuradas conforme o README.
- O cog de Platinas e o cog de Zerados precisam estar carregados para publicar seus painéis.

## Validação e limites
- `py_compile` passou em `bot.py`, `site_portal.py` e `cogs/portal_role_panel.py`.
- `node --check` passou em `site/app.js`.
- HTML passou pelo parser.
- Registro das rotas do portal passou: 40 rotas registradas, incluindo as duas novas APIs.
- Este ambiente não tem `discord.py` instalado; portanto não foi possível instanciar a View/Cog nem executar teste real contra a API do Discord.
- Não houve teste conectado ao servidor de produção. Testar em servidor de homologação antes de publicar.
- A publicação web nesta fase cobre cargos selecionáveis, Platinas e Jogos Zerados; não é um editor universal de todos os painéis internos do Discord.
