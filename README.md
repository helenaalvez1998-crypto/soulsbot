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
O módulo `cogs/ofertas.py` publica jogos grátis e promoções com foco no Brasil, em cartões limpos: **imagem grande, nome grande, preço original riscado e preço de agora**, com um botão para a loja.

| Fonte | Chave | O que traz |
|---|---|---|
| Steam Brasil | não | promoções e jogos temporariamente grátis, em R$ |
| Epic Games Store (BR) | não | jogos grátis da semana |
| GOG (catálogo público, BRL) | não | promoções e jogos grátis, em R$ |
| GamerPower | não | giveaways de várias lojas (valor original em US$, marcado como tal) |
| IsThereAnyDeal (`ITAD_API_KEY`) | grátis | **Nuuvem** e outras lojas em R$ + giveaways |
| GG.deals (`GG_DEALS_API_KEY`) | opcional | comparação de preço da Steam em R$ |

Nenhuma fonte é obrigatória: se uma falhar, as outras continuam. Valores só aparecem como "R$" quando a API informa BRL; nada é convertido em silêncio.

**Layout.** Usa Components V2 (discord.py >= 2.6): a imagem fica no topo, em largura total, seguida de nome, preço e botão. Jogo grátis = barra verde e botão "Resgatar grátis"; promoção = barra laranja e botão "Ver oferta". Se o discord.py for mais antigo, cai automaticamente para um embed.

**Sem repetição.** O mesmo jogo grátis vindo de duas fontes (ex.: Epic + GamerPower) é postado uma vez só. Fontes novas são registradas em silêncio na primeira consulta, sem inundar o canal.

**Ativando a Nuuvem (ITAD).** Crie uma conta em isthereanydeal.com, abra *Apps > Register App*, copie a **API key** (não o OAuth Client ID) e defina `ITAD_API_KEY`. `ITAD_SHOPS` define as lojas (padrão `50` = Nuuvem; a lista de IDs está na seção *Shops* de https://docs.isthereanydeal.com). Os links e preços da ITAD são exibidos como recebidos, com atribuição "via IsThereAnyDeal".

**GG.deals.** Gere uma chave em https://gg.deals/api/ e defina `GG_DEALS_API_KEY`. Só aparece quando a API devolve BRL.

Moderadores: `/status_ofertas` mostra o que está ativo; `/previa_oferta` exibe, só para você, como um cartão fica no canal.

Variáveis opcionais: `OFFERS_CHECK_MINUTES` (30), `MAX_OFFERS_PER_CHECK` (8), `MIN_PROMO_DISCOUNT` (50), `OFFERS_GOG_ENABLED`, `OFFERS_SHOW_DESCRIPTION`.

## Estrutura
- `bot.py` – inicialização e sincronização dos comandos
- `config.py` – variáveis de ambiente e constantes (XP, cores)
- `levels.py` – fórmula de nível e patentes
- `database.py` – SQLite (usuários, platinas, logs)
- `cogs/` – perfil, platinas (registro + aprovação por botões), ranking

## Módulos (cogs)
- `cogs/youtube.py` – avisos de vídeo (RSS) e live (YouTube Data API)
- `cogs/ofertas.py` – jogos grátis e promoções com foco no Brasil (Steam BR, Epic, GOG, GamerPower, Nuuvem via ITAD) em cartões com imagem grande
- `cogs/cargos.py` – botão Verificar-me e botões de cargos (custom_id mantidos da instalação anterior)
- `cogs/colizeu.py` – painel de ranking do canal #colizeu
- `cogs/loja.py` e `loja.py` – painel público da loja, loja privada, catálogo cosmético e compras com Denários
- `cogs/progressao.py` – níveis, XP e patentes exibidos como funções da Nara
- `cogs/nara_ia.py` – IA da Nara (Gemini), com regras em `prompts/nara.md`
- `ia_nucleo.py`, `ia_ferramentas.py`, `ia_gemini.py`, `ia_confirmacao.py` – agente: ferramentas, segurança, Gemini e botões
- `tests/` – testes do agente

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
`/status_ofertas`, `/previa_oferta`, `/teste_video`, `/teste_live`, `/status_youtube`) só aparecem para quem tem **Gerenciar servidor**.
Para liberar a um cargo específico: Configurações do servidor → Integrações → o bot → escolha o comando → adicione o cargo.


## Nara — XP e patentes

O sistema integrado concede XP por mensagens válidas (10–20 XP, com intervalo de 60 s por usuário), participação em canal de voz (5 XP a cada 5 min quando há pelo menos duas pessoas não bots) e eventos aprovados. Platinas continuam usando a recompensa existente `XP_PLATINA` (200 XP); runs aprovadas concedem 100 XP e um novo recorde concede mais 100 XP. O XP é compartilhado com o nível e as patentes.

Comandos: `/nivel`, `/ranking-xp`. O bot precisa das intents **Message Content**, **Server Members** e **Voice States** habilitadas no Developer Portal, além de permissão para gerenciar cargos. O cargo mais alto do bot deve ficar acima dos cargos de patente.

As patentes são criadas automaticamente quando necessárias: Cinzas Novatas, Guerreiro Caído, Combatente Sombrio, Cavaleiro Errante, Gladiador do Abismo, Guardião das Cinzas, Executor da Ruína, Lenda do Coliseu, Arauto das Almas e Sentinela Imortal.

## IA da Nara (Gemini): o cérebro do bot
`cogs/nara_ia.py` recebe toda mensagem dirigida à Nara e entrega à IA, que interpreta o pedido e decide: responder,
consultar dados ou agir usando as funções do bot. A personalidade está em `prompts/nara.md`.
Os comandos de barra e os botões continuam existindo e funcionando como antes (são rápidos e não gastam cota).

- **Marcada** (menção ou resposta a uma mensagem do bot): conversa, consulta, age e pode pesquisar nas wikis.
- **Canal de dúvidas** (`IA_CANAIS_LIVRES`): responde a toda mensagem do canal, sem pesquisa na web, e também pode agir.

### O que a IA consegue fazer (`ia_ferramentas.py`)
| Nível | Ferramentas | Como acontece |
|---|---|---|
| Consulta | perfil, platinas, zerados, rankings, Hall da Fama, loja, buscar membro, wiki | direto |
| Própria e reversível | equipar / desequipar item | direto |
| Com confirmação | comprar item, editar santuário, adicionar/remover rede, registrar zerado | a IA prepara; o membro toca em **Confirmar** |
| Atalho | abrir painéis (platina e run exigem comprovante, então a IA entrega o botão certo) | botão |
| Moderação | conceder XP (desligada por padrão: `IA_ACOES_MODERACAO=true`) | só moderador + confirmação |

### Segurança (`ia_nucleo.py`)
- A IA só escolhe a ferramenta. Permissão, validação, limites e confirmação são checados em **código**.
- Quem age é sempre quem escreveu a mensagem; nenhuma ferramenta aceita "agir por outro membro".
- O resumo mostrado junto aos botões vem do código, não do modelo.
- Cada ação é registrada na tabela `logs` (`ia_acao`, `ia_negado`, `loja_compra`...).
- `IA_ACOES=false` volta ao modo só consulta. Reutiliza `gravar_zerado` (novo, extraído de `registrar_zerado`), então o
  painel e a IA seguem as mesmas regras de recompensa.
- Para adicionar uma ferramenta nova: crie uma função em `criar_registro` com `add(...)`, escolha o `Risco` e, se gastar
  algo, escreva um `preparar` que valide e devolva o texto do botão.

### Configuração
No arquivo `.env`, defina `IA_CANAIS_LIVRES=ID_DO_CANAL_DE_DUVIDAS` (ative o Modo Desenvolvedor no Discord e copie o ID do canal).
Para responder sem limites internos, configure `IA_LIMITE_DIARIO=0` e `IA_TETO_ESPONTANEO=0`; use `IA_COOLDOWN_CANAL=0`.
As respostas ainda dependem da disponibilidade/cota da API Gemini. Variáveis obrigatórias: `GEMINI_API_KEY` e `GEMINI_MODEL`.
Sem elas, o módulo fica desativado. Testes do agente: `python -m unittest discover -s tests -v`.

## Zerados (`cogs/zerados.py`)
Versão leve das platinas para quem quer registrar os jogos que finalizou, sem precisar platinar.
- **`/zerados`** abre o painel (registrar, lista, ranking total/mensal). Também há o botão **Zerados** dentro do `/coliseu`.
- O registro **não passa pela moderação**: jogo, plataforma, data, comentário e print são (print e comentário opcionais).
- Dá XP/Denários (`XP_ZERADO`, `DENARIOS_ZERADO`), até `ZERADOS_XP_LIMITE_DIARIO` por 24h. Acima disso o registro entra sem XP.
- Se `ZERADOS_CHANNEL_ID` estiver definido, cada registro é anunciado lá (com o print, se houver).
- **`/remover_zerado <número>`**: o dono remove o próprio registro; moderadores removem qualquer um. A recompensa é devolvida.
- Moderadores: **`/postar_painel_zerados`** publica o botão fixo no canal.
- O perfil mostra a contagem de ✅ Zerados ao lado das platinas.
