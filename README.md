# Soulsbot

Comece por [`LEIA-ME-PRIMEIRO.txt`](LEIA-ME-PRIMEIRO.txt), [`INSTALACAO_E_ATUALIZACAO.md`](INSTALACAO_E_ATUALIZACAO.md) e [`ESTRUTURA_DO_PROJETO.md`](ESTRUTURA_DO_PROJETO.md).

# Nara — Bot de Discord

Bot de Discord (discord.py) com perfis, XP, patentes, registro/aprovação de platinas e rankings.

## Requisitos
- Python **3.10 ou superior**.
- Bot criado no Discord Developer Portal com as intents necessárias habilitadas.
- `DISCORD_TOKEN` para inicialização; `DEEPSEEK_API_KEY` e/ou `GEMINI_API_KEY` são usadas para pesquisa externa; DeepSeek é principal e Gemini reserva por padrão.

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
- `cogs/nara_ia.py` – roteamento local, consultas de perfil e pesquisa avançada da Nara
- `nara_local.py` – FAQ, classificador local, detecção de pesquisa necessária e bloqueio de imagens
- `ia_nucleo.py`, `ia_ferramentas.py`, `ia_gemini.py`, `ia_deepseek.py`, `ia_multi.py`, `ia_provedores.py`, `ia_confirmacao.py` – agente multi-provedor, ferramentas e segurança
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

## Nara econômica: respostas locais primeiro, IA só quando necessária

A Nara não envia toda conversa aos modelos externos. `cogs/nara_ia.py` consulta primeiro `nara_local.py`, que classifica saudações, ajuda, regras, perguntas frequentes e consultas de dados. Essas respostas não fazem chamadas HTTP nem consomem quota de modelo.

- **Respostas locais:** saudação, identidade, capacidades, comandos, XP, patentes, Denários, loja, Coliseu, registros, comprovantes, rankings e dúvidas frequentes.
- **Consultas SQLite:** perfil, XP/nível, saldo privado, platinas aprovadas, zerados, runs, inventário e rankings. A Nara lê somente os dados do próprio membro, exceto rankings públicos.
- **Pesquisa de catálogo:** pedidos sobre listas de troféus, platinas, conquistas, DLCs e colecionáveis são encaminhados para `/jogo_buscar`. O comando consulta primeiro aliases/catálogos locais; se não encontrar, usa DeepSeek Search + DeepSeek Flash e alterna para Gemini + Google Search grounding se DeepSeek atingir quota/saldo, rate limit ou ficar indisponível. O usuário confirma o título e o resultado fica em revisão administrativa.
- **Pesquisa conversacional:** desligada por padrão (`NARA_CHAT_IA_ENABLED=false`). Mesmo pesquisas explícitas de guias no chat não acionam IA. Isso preserva quota; a pesquisa de catálogos é feita por `/jogo_buscar`. Se ativada, o agente usa DeepSeek primeiro e Gemini como reserva.
- **Canal `IA_CANAIS_LIVRES`:** responde dúvidas que tenham uma intenção local reconhecida. Não envia conversa aleatória ao modelo; para pesquisa de jogo, pede que o usuário marque a Nara ou use `/jogo_buscar`.
- **Fallback:** mensagens marcadas que não correspondam ao FAQ recebem orientação local; não são enviadas automaticamente a nenhum modelo.

### Imagens e prints

A Nara de conversa é **somente texto**. O código não baixa, abre, salva ou envia imagens/anexos visuais a nenhum provedor de IA. Prints enviados em conversa recebem uma orientação para usar o formulário de `/coliseu`. Os módulos específicos de registro de platina/run continuam aceitando comprovantes para a revisão da moderação; esses arquivos não são encaminhados à Nara.

### Quando a IA externa é utilizada

Com `NARA_CHAT_IA_ENABLED=false` e `OFFERS_SHOW_DESCRIPTION=false`, o único fluxo regular que usa IA externa é o Caçador de Troféus quando `/jogo_buscar` não encontra o jogo/alias/catálogo local. DeepSeek Search + `deepseek-flash` é o principal; quando Search, geração, saldo, quota ou serviço DeepSeek falha, o bot usa Gemini + Google Search grounding como reserva. Os circuit breakers são independentes e persistidos em `data/deepseek_circuit.json` e `data/gemini_circuit.json`. Administradores consultam ambos com `/gemini_status`.

`DEEPSEEK_API_KEY` + `DEEPSEEK_MODEL=deepseek-flash` habilitam o principal. `GEMINI_API_KEY` + `GEMINI_MODEL` habilitam o reserva. Recomenda-se configurar as duas chaves. O histórico neutro e os prompts são compartilhados no agente conversacional; as permissões e validações continuam no código, não no prompt. Consulte `INSTALACAO_E_ATUALIZACAO.md` para as variáveis e `CACADOR_TROFEUS.md` para o fluxo de pesquisa.
## Zerados (`cogs/zerados.py`)
Versão leve das platinas para quem quer registrar os jogos que finalizou, sem precisar platinar.
- **`/zerados`** abre o painel (registrar, lista, ranking total/mensal). Também há o botão **Zerados** dentro do `/coliseu`.
- O registro **não passa pela moderação**: jogo, plataforma, data, comentário e print são (print e comentário opcionais).
- Dá XP/Denários (`XP_ZERADO`, `DENARIOS_ZERADO`), até `ZERADOS_XP_LIMITE_DIARIO` por 24h. Acima disso o registro entra sem XP.
- Se `ZERADOS_CHANNEL_ID` estiver definido, cada registro é anunciado lá (com o print, se houver).
- **`/remover_zerado <número>`**: o dono remove o próprio registro; moderadores removem qualquer um. A recompensa é devolvida.
- Moderadores: **`/postar_painel_zerados`** publica o botão fixo no canal.
- O perfil mostra a contagem de ✅ Zerados ao lado das platinas.


### Caçador de Troféus — pesquisa assistida por IA

Veja `CACADOR_TROFEUS.md`. Configure `DEEPSEEK_API_KEY` (principal) e `GEMINI_API_KEY` (reserva), depois use `/jogo_buscar` para identificar o título oficial, confirmar o candidato e gerar um catálogo em revisão. A publicação exige auditoria e validação administrativa.


## Caçador de Troféus e pesquisa de jogos

O comando `/jogo_buscar` reconhece títulos/aliases existentes sem consumir modelo ou usa DeepSeek Search + Flash, com failover para Gemini Search grounding, para sugerir candidatos, inclusive quando há abreviações ou erros de digitação. A pesquisa aprofundada do catálogo só começa após confirmação do título e fica em revisão administrativa; não existe publicação automática pela IA. Consulte [`CACADOR_TROFEUS.md`](CACADOR_TROFEUS.md) para o fluxo e [`AUDITORIA_TECNICA.md`](AUDITORIA_TECNICA.md) para as correções, testes, limites e checklist de atualização. Para ativar a pesquisa, configure `DEEPSEEK_API_KEY` e `GEMINI_API_KEY`; DeepSeek usa `deepseek-flash` por padrão e Gemini é a reserva. Se a hospedagem definir `GEMINI_MODEL` nas variáveis do serviço, esse valor prevalece sobre o `.env`; confira o painel para não continuar executando um modelo antigo. Em erro de quota ou `429`, consulte `/gemini_status`: o comando mostra os dois circuit breakers e qual provedor está pausado; confira os painéis de saldo/quota do fornecedor correspondente.
