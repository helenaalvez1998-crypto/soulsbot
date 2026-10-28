# Nara — Bot de Discord

Bot de Discord (discord.py) com perfis, XP, patentes, registro/aprovação de platinas e rankings.

## Rodar localmente
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env    # preencha os valores
python bot.py
```

## Experiência visual e navegação

- Perfis, cartões de jogador e santuários continuam em **embeds**, preservando avatares, imagens e galerias.
- Painéis de entrada, ranking em texto, guias, avisos de ofertas e anúncios de conquistas usam **Markdown** quando isso mantém a funcionalidade.
- Botões, filtros, seletores e paginação atualizam a mensagem em que o usuário está navegando; confirmações e erros privados continuam efêmeros quando fazem sentido.
- Os comandos de publicação reutilizam o painel existente no canal, evitando duplicatas ao executá-los novamente.
- Os cartões do pódio do Coliseu mostram um catálogo visual das platinas aprovadas, com capa, plataforma e data. O catálogo é montado a partir dos comprovantes; imagens inacessíveis são ignoradas sem bloquear o restante do painel.

## Comandos
**`/coliseu`** abre um painel privado com as áreas **Platinas**, **Zerados** e **Runs e desafios**. Dentro de **Platinas**, você encontra Registrar platina, Perfil, Platinas, Ranking, Ajuda e os atalhos para santuários; os menus permitem consultar outros membros.


Moderadores: `/postar_painel` (posta o botão "Abrir painel" no canal) · `/painel_colizeu` (publica/atualiza o painel do Colizeu no canal atual) · `/colizeu` (atualiza o painel no canal configurado) · `/painel_loja` (publica/atualiza o painel público da loja no canal atual) · `/painel_verificacao` · `/painel_cargos`

## Loja de Denários
`/loja` abre a loja privada do membro. Moderadores podem usar `/painel_loja` para publicar um painel fixo no canal atual; o botão **Abrir loja** continua funcionando após reinícios e abre a loja individual de quem clicou. A publicação atualiza o painel existente no mesmo canal em vez de duplicá-lo. Itens são cosméticos e ficam guardados no banco SQLite.


## Ofertas e jogos grátis
O módulo `cogs/ofertas.py` consulta Steam Brasil (preços regionais e textos localizados quando disponíveis), GamerPower e a listagem pública de jogos promocionalmente grátis da Epic Games Store em `pt-BR`. A consulta da Epic é um endpoint público da loja, não uma API com SLA; se falhar, as outras fontes continuam funcionando.

Para ativar a comparação de preços do GG.deals, gere uma chave em https://gg.deals/api/ e defina `GG_DEALS_API_KEY` no `.env`. O bot consulta a região `br` e só exibe os valores quando a API identifica a moeda como BRL, sem converter silenciosamente preços estrangeiros. A comparação complementa ofertas Steam existentes; a API pública do GG.deals não oferece um endpoint geral para listar todas as promoções de todas as lojas. Os embeds incluem link para o GG.deals conforme os termos de atribuição.

Os nomes oficiais dos jogos são preservados (não devem ser traduzidos); textos genéricos do bot ficam em português brasileiro. As descrições fornecidas por terceiros podem continuar no idioma original quando a fonte não disponibiliza tradução PT-BR.

## Estrutura
- `bot.py` – inicialização e sincronização dos comandos
- `config.py` – variáveis de ambiente e constantes (XP, cores)
- `levels.py` – fórmula de nível e patentes
- `database.py` – SQLite (usuários, platinas, logs)
- `cogs/` – perfil, platinas (registro + aprovação por botões), ranking

## Módulos (cogs)
- `cogs/youtube.py` – avisos de vídeo (RSS) e live (YouTube Data API)
- `cogs/ofertas.py` – jogos grátis (GamerPower, Epic Games Store e Steam), promoções da Steam e comparação opcional de preços via GG.deals
- `cogs/cargos.py` – botão Verificar-me e botões de cargos (custom_id mantidos da instalação anterior)
- `cogs/colizeu.py` – painel de ranking do canal #colizeu
- `cogs/loja.py` e `loja.py` – painel público da loja, loja privada, catálogo cosmético e compras com Denários
- `cogs/progressao.py` – níveis, XP e patentes exibidos como funções da Nara
- `cogs/nara_ia.py` – IA da Nara (Gemini), com regras em `prompts/nara.md`

## Santuários (perfil em thread privada)
Cada membro pode ter um **santuário**: uma thread privada dentro do canal `PERFIS_CHANNEL_ID`, com um cartão
(banner, bio, patente, XP, redes, galeria de platinas e, se o módulo Soulslike estiver ativo, os melhores tempos).
- `Meu santuário` (no painel `/coliseu` ou no painel do canal) cria/abre o seu; os botões **Personalizar**, **Redes** e **Atualizar** ficam dentro dele.
- `Visitar santuário` adiciona a pessoa à thread. Para sair, ela usa *Sair do tópico* e a thread some da lista dela.
- `/painel_santuarios` (moderadores) posta no canal de perfis os botões "Meu santuário" e "Visitar um santuário".
- A galeria atualiza sozinha quando uma platina é aprovada.

**Permissões do canal de perfis** (crie um canal de texto, ex. `#santuarios`):
- `@everyone`: Ver canal e Ler histórico **ligados**; Enviar mensagens, Enviar mensagens em tópicos e Criar tópicos **desligados** (visitantes só leem).
- Bot: Ver canal, Enviar mensagens em tópicos, **Criar tópicos privados**, **Gerenciar tópicos**, Inserir links, Anexar arquivos, Fixar mensagens.

## Comandos de moderação ficam escondidos
Os comandos de moderador (`/postar_painel`, `/painel_santuarios`, `/painel_colizeu`, `/colizeu`, `/painel_loja`, `/painel_verificacao`, `/painel_cargos`,
`/status_ofertas`, `/teste_video`, `/teste_live`, `/status_youtube`) só aparecem para quem tem **Gerenciar servidor**.
Para liberar a um cargo específico: Configurações do servidor → Integrações → o bot → escolha o comando → adicione o cargo.


## Nara — XP e patentes

O sistema integrado concede XP por mensagens válidas (10–20 XP, com intervalo de 60 s por usuário), participação em canal de voz (5 XP a cada 5 min quando há pelo menos duas pessoas não bots) e eventos aprovados. Platinas continuam usando a recompensa existente `XP_PLATINA` (200 XP); runs aprovadas concedem 100 XP e um novo recorde concede mais 100 XP. O XP é compartilhado com o nível e as patentes.

Comandos: `/nivel`, `/ranking-xp`. O bot precisa das intents **Message Content**, **Server Members** e **Voice States** habilitadas no Developer Portal, além de permissão para gerenciar cargos. O cargo mais alto do bot deve ficar acima dos cargos de patente.

As patentes são criadas automaticamente quando necessárias: Cinzas Novatas, Guerreiro Caído, Combatente Sombrio, Cavaleiro Errante, Gladiador do Abismo, Guardião das Cinzas, Executor da Ruína, Lenda do Coliseu, Arauto das Almas e Sentinela Imortal.

## IA da Nara (Gemini)
`cogs/nara_ia.py` adiciona uma IA com a personalidade definida em `prompts/nara.md`. A IA conhece as funções da Nara
(guia embutido) e lê, só para consulta, o perfil de quem perguntou e os rankings públicos. Ela não executa ações.

- **Marcada** (menção ou resposta a uma mensagem do bot): responde qualquer coisa e pode pesquisar nas wikis.
- **Canal de dúvidas** (`IA_CANAIS_LIVRES`): responde a toda mensagem enviada no canal configurado, mesmo sem `@Nara`,
  sem exigir ponto de interrogação e sem intervalo entre respostas. Outros canais não são afetados. Mensagens de bots
  são ignoradas para evitar ciclos. O modo livre usa o guia e os dados do bot, sem pesquisa na web.

No arquivo `.env`, defina `IA_CANAIS_LIVRES=ID_DO_CANAL_DE_DUVIDAS` (ative o Modo Desenvolvedor no Discord e copie o ID do canal).
Para responder sem limites internos, configure `IA_LIMITE_DIARIO=0` e `IA_TETO_ESPONTANEO=0`; use `IA_COOLDOWN_CANAL=0`.
As respostas ainda dependem da disponibilidade/cota da API Gemini. Variáveis obrigatórias: `GEMINI_API_KEY` e `GEMINI_MODEL`.
Sem elas, o módulo fica desativado.

## Zerados (`cogs/zerados.py`)
Versão leve das platinas para quem quer registrar os jogos que finalizou, sem precisar platinar.
- **`/zerados`** abre o painel (registrar, lista, ranking total/mensal). Também há o botão **Zerados** dentro do `/coliseu`.
- O registro **não passa pela moderação**: jogo, plataforma, data, comentário e print são (print e comentário opcionais).
- Dá XP/Denários (`XP_ZERADO`, `DENARIOS_ZERADO`), até `ZERADOS_XP_LIMITE_DIARIO` por 24h. Acima disso o registro entra sem XP.
- Se `ZERADOS_CHANNEL_ID` estiver definido, cada registro é anunciado lá (com o print, se houver).
- **`/remover_zerado <número>`**: o dono remove o próprio registro; moderadores removem qualquer um. A recompensa é devolvida.
- Moderadores: **`/postar_painel_zerados`** publica o botão fixo no canal.
- O perfil mostra a contagem de ✅ Zerados ao lado das platinas.
