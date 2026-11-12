# Central de Aprovação — NARA / Nara

## Objetivo

O canal central é a caixa de entrada da equipe para revisar registros enviados pelos membros. Os três fluxos principais usam o mesmo destino: **platinas, runs Soulslike e jogos zerados**. Cada solicitação aparece como um cartão com os dados do membro e os botões de decisão.

## 1. Criar e configurar o canal

1. Crie um canal privado no Discord, por exemplo `#central-de-aprovacao`.
2. Dê acesso ao cargo da equipe de moderação e ao próprio bot.
3. No bot, abra `/adm` → **Canais** e configure **Canal central de aprovação/moderação**. A mesma configuração também aparece na seção **Coliseu**.
4. Confirme que o bot tem, nesse canal: **Ver canal**, **Enviar mensagens**, **Incorporar links**, **Anexar arquivos** e **Ler histórico de mensagens**.
5. Confira em `/adm` o **Cargo de moderador**. Além desse cargo, membros com a permissão Discord **Gerenciar servidor** também podem revisar.

A configuração é salva por servidor no banco de dados. Ela tem prioridade sobre `MOD_CHANNEL_ID` do `.env`.

## 2. O que chega nesse canal

- **Platina:** o membro envia jogo, plataforma, data e comprovante; o cartão de revisão já era encaminhado ao canal de moderação.
- **Run Soulslike:** o membro envia jogo, desafio, tempo, build e comprovante; o cartão usa o mesmo canal.
- **Jogo zerado:** agora também cria uma solicitação pendente e envia o cartão para esse canal. O comprovante é opcional, mas a equipe ainda decide se o registro deve ser aceito.

A equipe usa **Aprovar** ou **Rejeitar** no próprio cartão. O estado e o moderador responsável são registrados no banco. Os botões são persistentes e continuam disponíveis depois que o bot reinicia, desde que a mensagem do cartão permaneça no Discord.

## 3. O que acontece após a decisão

**Ao aprovar um jogo zerado:** ele passa a aparecer no perfil, na lista e nos rankings; a recompensa é calculada naquele momento, respeitando os valores e o limite diário configurados em `/adm`; e, se configurado, é anunciado no canal público de zerados.

**Ao rejeitar um jogo zerado:** ele não entra no perfil nem no ranking, não recebe XP/Denários e o autor recebe uma mensagem privada quando aceita DMs. Uma solicitação rejeitada pode ser reenviada, desde que o membro corrija os dados.

Platinas e runs mantêm seus próprios efeitos após aprovação, mas continuam chegando ao mesmo canal de revisão.

## 4. Canais públicos continuam separados

O canal central é interno; não é o canal de exposição das conquistas. Configure separadamente, caso queira anúncios públicos:

- `PLATINAS_CHANNEL_ID`: anúncios de platinas aprovadas.
- `SOULSLIKE_CHANNEL_ID`: anúncios de runs e recordes aprovados.
- `ZERADOS_CHANNEL_ID`: anúncios de jogos zerados aprovados.

Se um canal público não estiver configurado, a aprovação é mantida no banco, mas não haverá publicação pública daquele tipo.

## 5. Compatibilidade com o banco existente

Na primeira inicialização desta versão, o banco recebe uma migração automática. **Todos os registros de jogos zerados que já existiam são preservados como aprovados**; eles não são enviados retroativamente para a fila. Somente os novos envios entram como pendentes. Não apague nem substitua `data/colizeu.db` durante a atualização.

## 6. Teste recomendado antes de liberar

1. Faça um envio de teste de platina, run e jogo zerado em um servidor/canal de teste.
2. Confirme que os cartões de platina, run e zerado aparecem no mesmo canal privado; ao terminar uma pesquisa de catálogo, confirme que o aviso também chega ali.
3. Aprove um teste e confirme o crédito de recompensa e a publicação pública correspondente.
4. Rejeite outro teste e confirme que ele não aparece no perfil/ranking nem credita recompensa.
5. Reinicie o bot e confirme que os botões dos cartões ainda respondem.

Use permissões de teste e não aprove/rejeite registros reais durante a validação.

## Escopo

A Central de Aprovação unifica os principais avisos e decisões de moderação. Platinas, runs e zerados usam cartões com botões de aprovar/rejeitar. Configurações gerais (`/adm`) e a manutenção editorial continuam sendo executadas pelos comandos administrativos correspondentes.


## 7. Central unificada no painel `/adm`

O painel administrativo inclui **Central de Moderação**, com filtros para Todas as categorias, Platinas, Runs/Desafios e Jogos zerados. A fila combina os registros pendentes por ordem de chegada e permite selecionar uma solicitação para abrir o cartão original no canal central.

A decisão continua sendo feita no cartão original, pelos botões **Aprovar** e **Rejeitar**. Isso mantém um único fluxo de decisão por tipo, preserva os comprovantes e evita duplicar regras de recompensa. Ao decidir no cartão, a mensagem original é atualizada e os botões são removidos; o painel pode ser atualizado para retirar a solicitação da fila.

A fila usa os IDs das mensagens vinculadas aos registros no banco. Se uma mensagem tiver sido apagada manualmente ou não estiver vinculada, a solicitação continuará aparecendo no painel, mas o link para o cartão poderá não funcionar.
