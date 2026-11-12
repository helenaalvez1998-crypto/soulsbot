# NARA — Contribuições, interações e Coliseu Social

Este módulo acrescenta um fluxo comunitário moderado, um Arquivo de Mundos, interações nas publicações e ferramentas sociais para o Coliseu e os Santuários. O sistema foi integrado à base SQLite principal (`colizeu.db`) e preserva os módulos existentes.

## 1. Ativação pelo painel administrativo

1. Instale as dependências do projeto com `pip install -r requirements.txt`.
2. Faça um backup dos bancos SQLite antes de atualizar o código.
3. Inicie o bot. `Database.connect()` executa as migrações incrementais das novas tabelas e colunas.
4. Abra `/adm` → **Contribuições e Arquivo de Mundos** → **Configurar canais e XP**.
5. Configure os destinos:
   - **Canal do Arquivo de Mundos (Lore e Teorias)**: recebe o painel persistente e as publicações de lore, teorias, descobertas, cronologias e debates.
   - **Canal da Biblioteca de Guias e Tutoriais**: recebe guias, tutoriais e propostas de FAQ aprovadas.
   - **Canal geral de publicações comunitárias**: recebe ideias, correções e propostas que não têm destino especializado.
   - **Canal de runs Soulslike**: já existente; recebe novos jogos e desafios aprovados para Runs.
6. No mesmo painel, ajuste o XP padrão e o limite semanal de XP comunitário.
7. Use **Publicar painel do Arquivo de Mundos**. A publicação é atualizada no mesmo canal quando o ID salvo ainda existe.
8. Para revisar envios, abra `/adm` → **Central de moderação** → **Contribuições**. Para denúncias, selecione **Sinalizações**.

## 2. Jornada do membro

O painel do Arquivo de Mundos oferece:

- **Contribuir**: Lore, teoria, descoberta, cronologia, debate, guia, tutorial, FAQ, desafio, jogo para Runs, correção, item para Loja ou ideia.
- **Explorar Arquivo**: consulta publicações aprovadas.
- **Minhas contribuições**: consulta status e responde a pedidos de ajuste.
- **Favoritos**: consulta conteúdos salvos.
- **Mural de atividades**: acompanha publicações de runs, platinas, jogos zerados e contribuições.
- **Notificações**: configura quais atualizações de pessoas seguidas podem chegar por DM.

Todos podem enviar contribuições. A publicação oficial e o XP dependem de aprovação da equipe. Há limite anti-spam de cinco propostas pendentes e cinco envios por 24 horas por membro.

## 3. Revisão administrativa

A equipe pode:

- Aprovar e publicar;
- Ajustar o XP da aprovação (0–1000), respeitando o teto semanal configurado;
- Solicitar ajustes ao autor;
- Rejeitar com justificativa;
- Republicar uma proposta já aprovada quando a publicação falhar;
- Revisar sinalizações e ocultar uma publicação ou arquivar a denúncia sem ocultar o conteúdo.

A aprovação e o lançamento de XP são transacionais e idempotentes. Ocultar uma publicação não apaga o registro de auditoria nem altera os dados oficiais de platinas, runs ou jogos zerados. Conteúdos FAQ comunitários ocultados também deixam de ser usados nas respostas locais da NARA.

## 4. Regras especiais por tipo

### Jogos e desafios de Runs

- Sugestões de jogos aprovadas são materializadas no catálogo `sl_games`.
- Desafios aprovados são ligados ao jogo escolhido; desafios existentes sem `game_id` continuam globais.
- Desafios podem ser individuais ou coletivos. Para coletivos, informe no campo de formato `coletivo: 15` para estabelecer uma meta de 15 conclusões registradas.
- O participante precisa se inscrever antes de atualizar o progresso. Uma conclusão requer comprovante e é identificada como autodeclarada; não concede XP adicional nem altera ranking automaticamente.

### FAQ da comunidade

Uma FAQ aprovada é publicada na Biblioteca e registrada em uma tabela separada da FAQ editorial oficial. A NARA só consulta essas respostas em mensagens já dirigidas a ela ou em canal livre configurado e exige correspondência textual forte e inequívoca. A resposta informa que foi enviada por membro e aprovada pela equipe.

### Lore, teorias e descobertas

As publicações levam classificação de spoilers. O formulário aceita o prefixo `[SPOILER: nenhum]`, `[SPOILER: leve]`, `[SPOILER: avançado]` ou `[SPOILER: final]` no campo de fontes/referências. Teorias são interpretações da comunidade; não são tratadas como lore oficialmente confirmada.

## 5. Interações sociais

As publicações aprovadas de Runs, platinas, jogos zerados e contribuições podem oferecer:

- Reações sem pontuação competitiva;
- Discussão em thread;
- Favoritos;
- Acompanhamento de autor e notificações configuráveis;
- Honras no Santuário;
- Sinalização à equipe;
- Participação, progresso e lista de participantes em desafios.

As reações não alteram rankings nem concedem XP. Os rankings continuam usando apenas registros oficiais aprovados.

## 6. Coliseu e Santuários

O painel do Coliseu acrescenta ações para comparar gladiadores, abrir o Mural, consultar o Arquivo e explorar rankings. A comparação usa estatísticas aprovadas (platinas, jogos zerados, runs, recordes e XP).

O cartão do Santuário acrescenta acompanhamento, honras e Livro de Visitas. Visitantes podem deixar uma mensagem por 24 horas por Santuário; o proprietário pode consultar e apagar mensagens. Visitantes não podem personalizar o perfil.

## 7. Permissões do Discord

Para operação completa, o bot precisa nos canais de publicação:

- Ver canal;
- Enviar mensagens;
- Incorporar links;
- Ler histórico de mensagens;
- Criar threads públicas e enviar mensagens em threads.

Para ocultar publicações após revisão, precisa de **Gerenciar mensagens** nos canais em que publica. Os membros não precisam de permissões administrativas para contribuir ou interagir.

## 8. Compatibilidade e preservação

- As duas entradas principais permanecem `/nara` e `/adm`, conforme a arquitetura original do projeto.
- Os cogs existentes continuam na lista de extensões; os recursos novos aparecem nos painéis e nas views já existentes.
- O banco secundário do catálogo de jogos e mods não foi mesclado ao banco principal.
- Migrações são incrementais e mantêm os registros existentes. Ainda assim, faça backup antes de atualizar.

## 9. Limitações da primeira entrega

- A conclusão de um desafio comunitário é autodeclarada com evidência anexada; a equipe ainda precisa conferir a prova manualmente para qualquer reconhecimento oficial.
- Notificações por acompanhamento dependem de o membro aceitar DMs do bot.
- Se a mensagem de uma publicação for apagada manualmente ou o bot perder acesso ao canal original, a recuperação deve ser feita pela fila administrativa; o sistema evita publicar cópias silenciosas.
- Os campos dos canais precisam ser configurados por servidor antes da publicação do painel e das primeiras contribuições.
