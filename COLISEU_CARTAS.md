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
- O catálogo inicial de pacotes tem 32 cartas: 15 Comuns, 7 Raras, 6 Épicas e 4 Lendárias. Entre as Comuns, há cartas dos três tipos (6 Destreza, 5 Magia e 4 Força), ampliando a variedade nos primeiros pacotes. O deck possui cinco cartas, limite de 12 pontos de custo e no máximo uma Lendária. Uma carta não pode ser repetida no mesmo deck.
- O pareamento de apostas compara a soma do poder base dos cinco cards. A diferença máxima inicial é de 4 pontos; o banco valida isso ao criar o convite e novamente antes de travar as apostas. O convite mostra o poder dos dois decks. É uma proteção inicial contra confrontos muito desiguais, não uma garantia matemática de equilíbrio, pois tipo e habilidades também alteram o poder em cada rodada.
- O lançamento oferece apenas duelos com aposta: 10 a 500 Denários por jogador, nível mínimo 5, até cinco duelos aceitos por dia, no máximo dois confrontos entre o mesmo par em 24 horas, limite diário de 1.500 Denários apostados por membro e cooldown de 60 segundos.
- A aposta só é debitada de ambos quando o convite é aceito. O vencedor recebe 90% do pote; 10% é removido da economia. Empate devolve as duas apostas. Inatividade de três minutos durante uma partida também devolve as duas apostas.
- O convite expira em dois minutos e não movimenta Denários se não for aceito.
- A escolha de cartas é privada e simultânea. O servidor valida os participantes, o deck travado, o uso único das cartas e todos os cálculos.

## Persistência e arquivos

- As tabelas de coleção, decks, Almas, pity, duelos, rodadas e transações são criadas automaticamente pela inicialização de `Database.connect()`.
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

Com a seed atual (`20261122`), 100.000 duelos filtrados tiveram 48,95% de vitórias para o lado A, 49,08% para o lado B e 1,97% de empates; a média foi 1,22 tentativa para encontrar um par compatível. A média agregada por raridade em comparações controladas ficou próxima de 50%, mas 188 de 242 cartas ficaram fora da faixa individual de 45–55%. Em decks aleatórios, a taxa média por raridade foi Comum 32,56%, Rara 46,90%, Épica 60,45% e Lendária 76,00%. Isso evidencia diferenças grandes de poder entre raridades e cartas; o pareamento pelo poder-base total não resolve sozinho o balanceamento. Portanto, esta versão deve ser tratada como alpha fechado, com apostas pequenas e monitoramento, não como ambiente competitivo já equilibrado. Execute novamente o script após alterações nas cartas. A simulação usa um pool uniforme/sintético e não representa a distribuição real das coleções nem escolhas estratégicas de jogadores. Não se deve enfraquecer uma carta automaticamente por uma taxa isolada: compare cenários equivalentes e monitore partidas reais.

## Instalação

1. Faça backup do banco SQLite e da pasta `data/`.
2. Extraia o patch preservando os caminhos e substitua os arquivos correspondentes.
3. Mantenha `fonts/DejaVuSans.ttf`, usada pelo renderizador (a versão em negrito usa fallback para essa mesma fonte se não existir).
4. Reinicie o bot. A migração das tabelas do Coliseu ocorre na inicialização.
5. Faça um teste no Discord com duas contas de teste antes de liberar apostas para todos.

O módulo exige as dependências normais do projeto, incluindo `discord.py`, `aiosqlite` e Pillow, já declaradas em `requirements.txt`.
