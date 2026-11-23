# SoulsBot — integração dos duelos com o site (Etapa 1)

## O que esta etapa altera

- O site lista os convites e duelos associados à conta Discord autenticada.
- O participante convidado pode aceitar o convite pelo site; a aceitação usa `coliseu_decidir_convite` no banco compartilhado.
- A sala web mostra o placar, as rodadas resolvidas e somente as cartas ainda disponíveis do próprio participante.
- As jogadas do site usam `coliseu_registrar_jogada` e a resolução original `ColiseuCartas.resolver_rodada`; não foi criado um segundo motor.
- O Discord continua publicando convites e exibindo o painel da partida, mas a ação de jogar direciona para o site.
- O login OAuth preserva o link profundo `/?duel=ID`, inclusive quando o usuário precisa autenticar antes de entrar na sala.

## Arquivos alterados

- `bot.py`
- `cogs/cartas_coliseu.py`
- `site/index.html`
- `site/app.js`
- `site/style.css`

## Configuração

Opcionalmente, configure `SOULSBOT_PUBLIC_URL=https://narabot.sbs` no ambiente do serviço. O código usa esse domínio como padrão se a variável não existir.

Mantenha as variáveis OAuth e o segredo de sessão já configurados. Não compartilhe tokens nem segredos.

## Validações executadas

- `python -m py_compile bot.py database.py cogs/cartas_coliseu.py`
- `node --check site/app.js`

Essas verificações confirmam sintaxe; ainda é necessário validar o fluxo real no ambiente hospedado com duas contas Discord.

## Limites desta etapa

- A criação de convites continua sendo feita pelo fluxo existente do Discord. A criação de desafios pelo site e a presença unificada Discord/site ficam para a próxima etapa.
- Não há ainda atualização em tempo real por WebSocket; a tela pode ser atualizada manualmente. A atualização automática será tratada após validar o fluxo de partida.
- Faça o deploy quando não houver partida ativa em andamento. A partir desta versão, partidas ativas usam o site para registrar novas jogadas.
