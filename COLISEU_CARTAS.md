# Cartas do Coliseu — SoulsBot

## O que foi adicionado

O módulo `cogs.cartas_coliseu` adiciona à Nara uma central privada de cartas com coleção persistente, pacote Fogueira, Forja de Almas, montagem de deck, duelos com apostas e Hall da Fama.

A integração aparece no painel **Meu Progresso** como **Coliseu de cartas**. O módulo é separado do perfil/Coliseu social que já existia em `cogs/colizeu.py`.

## Regras de lançamento

- Cada jogo gera duas cartas diferentes por jogador: `Alma Desperta` ao aprovar o zerado e `Eco da Platina` ao aprovar a platina.
- A platina aprovada também libera a carta de zerado, mesmo quando não houve um registro manual de zerado.
- Cartas de conquistas anteriores são sincronizadas na primeira abertura do painel.
- Patentes dão cartas próprias ao atingir o nível correspondente.
- Um kit inicial gratuito de cinco cartas comuns permite montar o primeiro deck sem gastar Denários.
- O pacote Fogueira custa 120 Denários e entrega três cartas. Probabilidades por carta: 70% Comum, 22% Rara, 7% Épica e 1% Lendária.
- Após dez cartas Comuns consecutivas, a próxima carta aberta é garantidamente Rara ou melhor.
- Duplicatas de cartas de pacote convertem-se em Almas. A Forja permite fabricar cartas comuns, raras, épicas e lendárias do catálogo de pacote. Cartas de jogos e patentes permanecem exclusivas dos respectivos marcos.
- O catálogo inicial de pacotes tem 33 cartas: 15 Comuns, 8 Raras, 6 Épicas e 4 Lendárias. Entre as Comuns, há cartas dos três tipos (6 Destreza, 5 Magia e 4 Força), ampliando a variedade nos primeiros pacotes. O deck possui cinco cartas, limite de 12 pontos de custo e no máximo uma Lendária. Uma carta não pode ser repetida no mesmo deck.
- O pareamento de apostas compara a soma do poder base dos cinco cards. A diferença máxima inicial é de 4 pontos; o banco valida isso ao criar o convite e novamente antes de travar as apostas. O convite mostra o poder dos dois decks. É uma proteção inicial contra confrontos muito desiguais, não uma garantia matemática de equilíbrio, pois tipo e habilidades também alteram o poder em cada rodada.
- O lançamento oferece apenas duelos com aposta: 10 a 500 Denários por jogador, nível mínimo 5, até cinco duelos aceitos por dia, no máximo dois confrontos entre o mesmo par em 24 horas, limite diário de 1.500 Denários apostados por membro e cooldown de 60 segundos. A compra de pacotes também tem limite de três por janela móvel de 24 horas (360 Denários/dia ao preço atual de 120 por pacote).
- A aposta só é debitada de ambos quando o convite é aceito. O vencedor recebe 90% do pote; 10% é removido da economia. Empate devolve as duas apostas. Inatividade de três minutos durante uma partida também devolve as duas apostas.
- O convite expira em dois minutos e não movimenta Denários se não for aceito. Depois de um duelo concluído, qualquer um dos participantes pode solicitar uma revanche em um clique; o convite usa a aposta anterior como sugestão e o adversário ainda precisa aceitar. A revanche respeita saldo, nível, disponibilidade, limites diários, limite de confrontos e compatibilidade dos decks.
- Cada uma das cinco rodadas tem até 30 segundos para as duas escolhas secretas e simultâneas. Se não houver as duas escolhas dentro do prazo, a partida é encerrada e as duas apostas são devolvidas. Jogadores que escolhem rapidamente normalmente concluem o duelo em cerca de 2–4 minutos.
- Cada duelo concluído concede +8 XP aos dois participantes, independentemente do vencedor, limitado a três duelos recompensados por membro em uma janela móvel de 24 horas. O XP não depende do valor apostado; partidas expiradas ou canceladas não geram XP.
- Há três missões semanais opcionais: concluir 1 duelo (+2 Almas), concluir 3 duelos (+4 Almas) e vencer 2 duelos (+6 Almas). O progresso e as recompensas são individuais, creditados automaticamente e reiniciados por semana ISO no fuso de São Paulo. Não há sequência diária ou penalidade por ausência.
- O pacote Fogueira é revelado carta por carta, com a opção de revelar todas ou abrir um resumo visual. A compra e o crédito das três cartas acontecem de forma atômica antes da animação; sair da mensagem não remove as cartas já adquiridas.
- A habilidade Encadeamento concede +2 de poder se o jogador venceu a rodada anterior e repetir o tipo de carta. Ela foi adicionada sem alterar os atributos determinísticos das cartas de jogo e patente que já haviam sido entregues.
- O histórico de rivalidade exibe o placar completo entre dois membros e os cinco confrontos mais recentes.
- A escolha de cartas é privada e simultânea. O servidor valida os participantes, o deck travado, o uso único das cartas e todos os cálculos.

## Experiência visual dos duelos

- A Arena abre um painel gráfico pessoal com vitórias, derrotas, empates, aproveitamento, saldo líquido, partidas ativas e resultados recentes. O menu de partidas permite abrir a ficha de qualquer confronto salvo.
- Ao iniciar um desafio, o convite já mostra o tabuleiro da partida, os dois duelistas, o poder dos decks e o valor em jogo. Ao aceitar, o mesmo tabuleiro passa ao estado de confronto ativo.
- A escolha privada mostra todas as cartas restantes em uma única imagem horizontal, numeradas de 1 a 5. O jogador toca no botão que corresponde ao número da carta; não precisa abrir um menu suspenso nem confirmar uma segunda vez.
- Depois da escolha, o participante recebe a imagem da própria carta com o selo **CARTA TRAVADA**. A escolha continua secreta para o adversário.
- O tabuleiro público acompanha o placar, o progresso das cinco rodadas e a quantidade de escolhas recebidas. Cada rodada resolvida revela as duas cartas lado a lado, seus poderes, o vencedor da rodada e a narração. Rodadas futuras permanecem com cartas fechadas.
- Ao encerrar, a ficha individual destaca o campeão, o placar final, o prêmio creditado, o lucro líquido e o valor removido da economia. Empates e partidas canceladas também têm desfecho visual próprio. Cada confronto mantém seu próprio registro.
- Quando os dois jogadores confirmam, a rodada recém-resolvida recebe uma revelação curta em GIF: cartas, vencedor, bônus de combo e destaque visual. O quadro final permanece legível depois da animação.
- A trilha e a ficha mostram o bônus de tipo e o bônus de habilidade que contribuíram para o poder final de cada carta. A revelação destaca a habilidade ativada e a virada de liderança; a mão privada indica se a habilidade de cada opção já pode ativar ou se depende da carta rival.
- A Tríade Elemental concede +2 de poder uma única vez por jogador e por duelo quando a escolha completa Destreza, Força e Magia. O bônus é calculado pelo servidor, salvo na rodada e exibido na mão, na revelação e no resultado.
- As habilidades existentes continuam a recompensar sequências: Encadeamento considera vitória anterior e repetição de tipo; Adaptação recompensa trocar de tipo; Retaliação, Ímpeto, Sangue-frio e outras habilidades reagem ao resultado anterior ou à situação da rodada. A mão privada mostra a sequência pessoal, o progresso da Tríade e uma prévia honesta das habilidades ativáveis antes da escolha.
- A partida pode terminar antes da quinta rodada somente quando a diferença de vitórias já é maior que o número de rodadas restantes. Nesse caso, o vencedor está matematicamente definido; a liquidação da aposta, a recompensa e o histórico seguem o mesmo fluxo normal. Se ainda existir possibilidade de empate em vitórias ou virada, as rodadas continuam.
- As imagens são compostas localmente por Pillow a partir das artes das cartas; não dependem de serviços externos. No Discord, as áreas da imagem não aceitam cliques, então a seleção usa botões numerados imediatamente abaixo da mão ilustrada.

## Persistência e arquivos

- As tabelas de coleção, decks, Almas, pity, duelos, rodadas, transações, participações, missões semanais e XP de duelos são criadas automaticamente pela inicialização de `Database.connect()`.
- Os dados permanentes ficam no SQLite já usado pelo SoulsBot. Preserve `data/` e o banco de produção durante a atualização.
- As cartas são definidas em `sistemas/cartas.py`.
- As artes são geradas localmente por `sistemas/arte_cartas.py` com Pillow. O cache fica em `data/cartas_cache/` e pode ser apagado sem perder coleções.
- Não são incorporadas imagens oficiais de jogos. A arte atual usa formas, símbolos e tipografia original.

## Simulação de equilíbrio

Execute na raiz do projeto:

```bash
python tools/simular_cartas_coliseu.py 100000
```

O script usa seed fixa e constrói um pool de teste com as cartas estáticas, patentes e cartas sintéticas de jogos. Ele gera pares de decks legais com diferença máxima de 4 pontos de poder base, conforme o pareamento em produção, e mede paridade agregada dos lados e taxa individual por carta/raridade. O pool de teste é uniforme; não representa a distribuição real de coleção nem as probabilidades de pacote.

Na validação desta atualização, 10.000 duelos filtrados com a seed `20261122` tiveram 48,25% de vitórias para o lado A, 49,67% para o lado B e 2,08% de empates; a média foi 1,23 tentativa para encontrar um par compatível. A comparação simulada entre cartas da mesma raridade apontou 193 de 243 cartas fora da faixa individual de 45–55%, apesar das médias agregadas por raridade ficarem próximas de 50%. Em decks aleatórios, a taxa média de vitória foi 31,93% para Comum, 46,71% para Rara, 60,82% para Épica e 73,15% para Lendária. Isso evidencia que o balanceamento individual ainda não está pronto para competição pública de alto risco. O Coliseu deve continuar em alpha, com apostas pequenas e limites conservadores. Execute novamente o script após alterações nas cartas. A simulação usa um pool uniforme/sintético e não representa a distribuição real das coleções nem escolhas estratégicas dos jogadores. Não se deve enfraquecer uma carta automaticamente por uma taxa isolada: compare cenários equivalentes e monitore partidas reais.

## Instalação

1. Faça backup do banco SQLite e da pasta `data/`.
2. Extraia o patch preservando os caminhos e substitua os arquivos correspondentes.
3. Mantenha `fonts/DejaVuSans.ttf`, usada pelo renderizador (a versão em negrito usa fallback para essa mesma fonte se não existir).
4. Reinicie o bot. A migração das tabelas do Coliseu ocorre na inicialização.
5. Faça um teste no Discord com duas contas de teste antes de liberar apostas para todos.

O módulo exige as dependências normais do projeto, incluindo `discord.py`, `aiosqlite` e Pillow, já declaradas em `requirements.txt`.

## Seleção de adversários conectados

- O botão **Desafiar jogador** abre uma lista privada dos membros conectados do servidor, em vez de pedir que o desafiante digite uma menção ou ID.
- A lista inclui estados Online, Ausente e Não perturbe; bots e o próprio desafiante são omitidos. Só aparecem membros que já tenham nível mínimo 5, pelo menos 10 Denários e um deck válido de cinco cartas.
- A lista pode ser atualizada e é paginada em grupos de até 25 opções. Depois da seleção, o desafiante informa o valor da aposta; as validações financeiras e de equilíbrio continuam sendo refeitas pelo banco ao criar/aceitar o convite.
- Para ler status de presença, `bot.py` ativa `intents.presences`. Também é obrigatório ativar **Presence Intent** no Discord Developer Portal: abra a aplicação → **Bot** → **Privileged Gateway Intents** → ative **Presence Intent**. O código e o painel precisam estar habilitados; sem isso, o Discord não entrega status de presença ao bot.

## Variação visual das cartas

- As imagens são geradas em Pillow, de forma determinística, sem depender de APIs externas ou de arte oficial de jogos.
- A categoria define a composição (chefe, arma, magia, covenant, jogo ou patente); o tipo define acentos e ícone vetorial; raridade define paleta e acabamento da moldura.
- Cada carta tem detalhes de fundo gerados a partir do seu ID/dados, mantendo a mesma aparência em renderizações futuras.
- `VERSAO_ARTES` foi incrementada para invalidar o cache antigo. As novas artes são regeneradas automaticamente; a pasta `data/cartas_cache/` pode ser apagada sem perder coleções.

## Ateliê de artes personalizadas

- Nos detalhes de cada carta da coleção, o proprietário encontra **Gerar prompt de arte**. A Nara monta um prompt específico com o nome, categoria, tipo, contexto e jogo de origem da carta. Para cartas conquistadas ao zerar/platinar, o prompt também representa de forma distinta o encerramento da jornada ou a conclusão de todos os desafios.
- O prompt aplica uma direção artística fixa do SoulsBot: fantasia sombria pintada, materiais antigos, atmosfera gótica e composição horizontal 5:4 com sujeito central. O jogo de origem define o tema amplo; o SoulsBot define como a ilustração deve ser representada. A raridade não entra no prompt e nunca muda a composição da arte. A moldura, título, atributos e habilidade continuam sendo desenhados pelo Pillow.
- O prompt é mostrado em uma mensagem privada/efêmera em bloco de texto para facilitar a cópia. O bot não gera a imagem; o membro utiliza o gerador de imagens que preferir.
- Depois de gerar a imagem, o membro clica em **Enviar minha arte**. A Nara abre uma sessão por DM válida por 30 minutos. O membro responde à DM com uma única imagem estática PNG/JPG/WEBP de até 8 MB e pelo menos 512 × 512 pixels. O arquivo é reprocessado em memória, perde metadados/EXIF e é normalizado para 1234 × 1000 pixels. O limite é de três artes por membro aguardando avaliação ao mesmo tempo.
- Existe somente um canal privado de arquivo e revisão: `#biblioteca-coliseu`. Configure o ID em `COLISEU_ART_CHANNEL_ID` no `.env`. Oculte o canal de `@everyone` e libere acesso ao bot e à moderação. O bot precisa de `View Channel`, `Send Messages`, `Attach Files`, `Embed Links` e `Read Message History`. A configuração fica desativada por padrão; sem o ID, o botão de prompt funciona, mas o envio informa que a biblioteca ainda não foi configurada.
- As imagens aguardando análise e as aprovadas permanecem como anexos de mensagens nesse mesmo canal. A moderação aprova ou rejeita pelos botões da mensagem; ao rejeitar, informa o motivo. Somente quem tem `Manage Messages`, `Manage Server`, `Administrator` ou o cargo indicado por `MOD_ROLE_ID` pode decidir.
- O SQLite guarda apenas dono, carta, jogo, status e IDs do canal/mensagem/anexo. Quando a carta é aberta, o bot recupera o anexo do Discord e monta a carta completa em memória. Não é criada cópia permanente da arte do membro na pasta `data/` nem no cache de cartas.
- A arte é individual: somente a carta daquele proprietário usa a ilustração personalizada. Outros membros continuam vendo a arte-base. Uma carta pode ter uma arte personalizada ativa; outra aprovada substitui a anterior, mantendo o histórico. O proprietário pode voltar à arte original. Arte personalizada não altera poder, raridade, habilidade, custo ou qualquer regra competitiva.
- Se a mensagem/anexo do arquivo for apagado ou ficar inacessível, o bot volta a exibir a ilustração-base. Por isso, não apague mensagens do canal e inclua a biblioteca no backup do servidor/Discord. O bot não mantém cópia local permanente.
- A galeria pública separada e os pacotes temáticos compráveis por jogo não fazem parte desta primeira versão. O prompt já aproveita `jogo_origem` das cartas de conquista e está preparado para usar a mesma informação quando cartas de pacotes temáticos forem implementadas.

### Configuração do Ateliê

1. Crie um único canal de texto privado chamado `#biblioteca-coliseu`.
2. Oculte o canal de `@everyone`; libere acesso ao bot e aos moderadores.
3. Conceda ao bot `View Channel`, `Send Messages`, `Attach Files`, `Embed Links` e `Read Message History`.
4. Ative mensagens diretas entre membros e o bot (o jogador precisa responder à Nara por DM).
5. Copie o ID do canal com o Modo Desenvolvedor do Discord e configure `COLISEU_ART_CHANNEL_ID=ID_DO_CANAL` no `.env`.
6. Reinicie o bot. O botão **Gerar prompt de arte** pode ser usado sem esse canal, mas **Enviar minha arte** exige a configuração.

As novas tabelas `cartas_atelie_sessoes` e `cartas_atelie_artes` são criadas automaticamente pelo `SCHEMA_CARTAS`; não substitua o banco de produção.
