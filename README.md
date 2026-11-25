# NARA — bot de Discord da comunidade Soulslike

Perfis, XP e patentes, platinas/zerados/runs com aprovação, Gwent do Coliseu como jogo principal no site,
catálogo de ports/mods, ofertas de jogos, YouTube e a assistente **Nara** (respostas locais + Gemini opcional).

## Rodar
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env        # preencha pelo menos DISCORD_TOKEN, GUILD_ID, MOD_CHANNEL_ID
python bot.py
```
Python 3.11+. Na FadeHost: Python 3.13, `DATA_DIR=/data`, start command `python bot.py`, variáveis no painel.
Intents necessárias no Developer Portal: Server Members, Message Content e Presence.

## Estrutura
```
bot.py            entrada: carrega cogs, API/site HTTP, tratamento de erros e interações
config.py         variáveis de ambiente, constantes e caminhos de dados
database.py       SQLite (aiosqlite): schema, migrações e consultas
admin_config.py   configuração por servidor (painel /adm), com fallback para config.py
levels.py loja.py utils.py   patentes/XP, itens da loja, utilitários e navegação de painéis
cogs/             funcionalidades Discord (um arquivo por área; comum.py = peças compartilhadas)
sistemas/         cartas do Coliseu: regras, arte, templates e Ateliê
ia/               Gemini com failover entre até 3 chaves, ferramentas e confirmação de ações
nara/             respostas locais, FAQ, personalidade e Central de Ajuda
prompts/ dados/   prompts da Nara e base de FAQ (lidos em runtime)
fonts/           fonte usada nas imagens
site/             portal NARA + Gwent (login Discord, biblioteca, comunidade, administração e arena)
```

## Comandos
São publicados exatamente três slash commands: **`/nara`** (central dos membros), **`/jogo`** (painel de Cartas do Coliseu) e **`/adm`** (painel administrativo). O nome do jogo continua sendo Coliseu; `/jogo` é somente a entrada do Discord. Os demais comandos slash dos cogs são filtrados antes da sincronização.

## Dados
Banco em `DATA_DIR/colizeu.db` (nome mantido). Faça backup de `data/` antes de atualizar e nunca
substitua `.env` nem `data/` ao copiar o código novo.

## Gwent do Coliseu — edição Elden Ring

A edição temática Elden Ring usa as facções Ordem Áurea, Véu Carmesim e Lua Negra. Consulte `REGRAS_ELDEN_GWENT.md` para o novo livro de regras, estados negativos, invocação espiritual e combos.


O Gwent é o único jogo de cartas ativo no bot e no site. O motor antigo de duelo de cinco cartas foi retirado do runtime: o cog legado e suas rotinas de deck/duelo não são carregados nem distribuídos. As tabelas históricas que já existirem no SQLite são preservadas sem DROP; instalações novas não criam as tabelas antigas. Elas não possuem rotas ou comandos ativos.

### Regras da partida

- Deck com 12 cartas únicas: 10 na mão inicial e 2 na reserva.
- Preparação inicial: cada jogador pode trocar até duas cartas.
- Melhor de três rodadas; duas coroas vencem a partida.
- Três fileiras: corpo a corpo, longa distância e cerco.
- Clima reduz o poder efetivo das unidades na fileira afetada; resistência climática é aplicada no servidor.
- Líderes são vinculados à facção e podem ser ativados uma vez por partida.
- Passar encerra as jogadas do jogador na rodada; quando ambos passam, a rodada é resolvida.
- Unidades que permanecem no campo ao fim da rodada são movidas ao descarte.
- O servidor valida turnos, cartas na mão, efeitos, pontuação e resultado; o navegador só envia ações.

### Cartas, coleção e progressão

- A coleção histórica é convertida na camada Gwent sem alterar os IDs, quantidades ou posse dos jogadores.
- No primeiro acesso autenticado ao site, contas novas recebem 12 drops globais de boas-vindas com modelos distintos. Conquistas antigas sem recompensa registrada e novas patentes liberadas por XP também são convertidas em drops globais.
- Cartas podem ser obtidas por drops de atividades e compradas no Mercado do Coliseu: pacote com 3 cartas por 120 Denários, até 3 pacotes em 24 horas. Cada carta é sorteada no catálogo global; Primordial tem chance de 0,1% por carta, e após 10 cartas Comuns consecutivas a próxima recebe proteção de raridade (Rara ou superior).
- Há sete raridades: Comum, Rara, Épica, Lendária, Mítica, Primordial e Singular. Primordiais e Singulares são individuais por jogador e dependem de condições especiais.
- Cada exemplar guarda sua própria raridade e poder. O mesmo modelo pode existir em raridades diferentes ao mesmo tempo; a repetição do mesmo modelo na mesma raridade é duplicata. A migração cria exemplares para as cartas antigas sem apagar o inventário legado.
- Duplicatas geram Almas ou fragmentos. Fragmentos evoluem exemplares de Comum até Mítica, desde que o jogador ainda não possua aquele modelo na raridade de destino; Almas lapidam o poder em +1, sempre respeitando o limite individual do modelo.
- Aprovações de zerados, platinas, runs Soulslike, contribuições comunitárias e envios públicos de ports/mods concedem XP quando previsto e drop adicional, com proteção contra recompensas duplicadas. A administração configura chance Primordial e Singular por desafio em `/adm` → **Jogos, Coliseu e runs** → **Configurar drops especiais dos desafios**. Contas novas recebem 12 drops globais de boas-vindas; marcos de patente e conquistas históricas pendentes também usam drops.
- Vitórias, derrotas e empates atualizam ranking, MMR Elo, Denários e XP; XP de partidas tem limite de 30 por jogador a cada 24 horas, e marcos de patente liberam drops globais.
- O ranking e o histórico de partidas são exibidos no site.

### Apresentação visual

- Cartas usam moldura por raridade, paleta por facção, selo de poder, classe, fileira e painel de habilidade.
- O construtor tem busca e filtros por facção e raridade, além de prévia ampliada.
- Cada exemplar aparece separadamente no construtor, com seu ID, raridade e poder. O deck persiste o exemplar escolhido; partidas usam exatamente essa cópia.
- A coleção exibe raridade e poder do exemplar; o construtor permite evoluir com fragmentos e lapidar poder com Almas.
- A arena apresenta pontuação por jogador e fileira, cartas no campo, mão privada, líder, clima, histórico recente e opção de concessão.
- As artes são geradas localmente e de forma determinística. Não dependem de imagens externas.

### Ateliê de Cartas (site)

- O Ateliê fica dentro do site do Coliseu; não cria um quarto comando slash.
- O jogador escolhe um modelo que possui, gera um prompt individual com identidade visual, facção, raridade, habilidade e papel tático, e envia uma imagem PNG/JPG/WEBP.
- Uploads são normalizados para JPEG 1234 × 1000, limitados a 8 MB e 18 megapixels; imagens animadas são recusadas.
- Cada conta pode manter até três submissões pendentes, com no máximo uma pendente por modelo e artista.
- A aprovação publica uma arte oficial compartilhada por modelo; uma nova aprovação arquiva a versão oficial anterior sem apagar o histórico. O nome do artista fica associado à versão publicada.
- A fila de revisão é restrita ao `BOT_OWNER_ID` e aos IDs listados em `COLISEUM_ART_REVIEWER_IDS` (separados por vírgula). Configure os revisores no ambiente de produção antes de abrir o Ateliê à comunidade.
- A arte aprovada substitui a arte-base na rota de imagem do Gwent.

Rotas adicionais: `GET /api/gwent/atelier/prompt`, `POST /api/gwent/atelier/submit`, `GET /api/gwent/atelier/history`, `GET /api/gwent/atelier/review`, `POST /api/gwent/atelier/review/{submission_id}`, `GET /api/gwent/atelier/official/{card_id}` e `GET /api/gwent/atelier/art/{card_id}`.

### API do Gwent

- `GET /api/gwent/cards`
- `GET /api/gwent/cards/{card_id}/image`
- `GET /api/gwent/deck` e `POST /api/gwent/deck`
- `GET /api/gwent/store` (saldo, preço e limite diário)
- `POST /api/gwent/store/pack` (compra atômica de 3 cartas por 120 Denários)
- `POST /api/gwent/store/forge` (HTTP 410; forja direta permanece desativada)
- `GET /api/gwent/exemplars`
- `GET /api/gwent/drops/history`
- `POST /api/gwent/evolve`
- `POST /api/gwent/upgrade`
- `GET /api/gwent/matches` e `POST /api/gwent/matches`
- `GET /api/gwent/matches/{match_id}`
- `POST /api/gwent/matches/{match_id}/action`

### Atualização

Faça backup de `data/` e do banco antes de atualizar. Desligue o bot, extraia o pacote sobre a pasta `narabot-main`, preserve `.env`, banco de dados e dados existentes, e reinicie com `python bot.py`. O pacote não executa migrações destrutivas. Depois, atualize o navegador com `Ctrl + F5`.

A validação desta atualização cobre compilação Python, sintaxe JavaScript, schema SQLite, migração de inventário legado, drops idempotentes, variantes do mesmo modelo por raridade, seleção persistente de exemplares no deck, evolução por fragmentos e concessão individual de Singular/Primordial. Os testes automatizados ficam em `tests/` e rodam com `python -m unittest discover -v`. A validação final em produção ainda depende de executar o bot com as dependências instaladas no seu servidor Discord e testar duas contas reais simultaneamente.
\n\n## Portal NARA — administração web\n\nA área Administração permite gerir fila, configurações e Radar RSS. Na Fase 4 também permite configurar até 25 cargos selecionáveis e publicar/atualizar os painéis de cargos, Platinas e Jogos Zerados. Para cargos selecionáveis, o bot precisa de `Gerenciar Cargos` e deve estar acima dos cargos configurados. Consulte `PORTAL_NARA_FASE4.md` para detalhes e limites.\n

## Líderes V15

O Coliseu possui nove líderes com habilidades exclusivas. Consulte `REGRAS_LIDERES_V15.md` e `CHANGELOG_LIDERES_EXCLUSIVOS_V15.md` para a descrição dos efeitos e limites.
