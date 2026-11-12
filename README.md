# NARA — Inteligência da Comunidade


> **Identidade oficial:** o nome do bot e do projeto é **NARA**. “Soulslike” continua sendo usado apenas para identificar o gênero/jogos da comunidade. Os nomes dos comandos slash e o arquivo de banco `colizeu.db` foram preservados para não quebrar instalações existentes.
Comece por [`INSTALACAO.md`](INSTALACAO.md) e [`ESTRUTURA_DO_PROJETO.md`](ESTRUTURA_DO_PROJETO.md).

# Nara — Bot de Discord

Bot de Discord (discord.py) com perfis, XP, patentes, registro/aprovação de platinas e rankings.

## Requisitos
- Python **3.11 ou superior** (Python 3.13 recomendado para novas implantações).
- Bot criado no Discord Developer Portal com as intents necessárias habilitadas.

## Rodar localmente
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python configurar_bot.py
python bot.py
```

## Produção e FadeHost

O projeto está preparado para iniciar com `python bot.py`. Na FadeHost, configure Python 3.13, `DATA_DIR=/data` e `DB_PATH=/data/colizeu.db`; cadastre tokens, chaves e IDs no painel de variáveis de ambiente. Consulte [`DEPLOY_FADEHOST.md`](DEPLOY_FADEHOST.md) antes do primeiro deploy. Não é necessário `keep_alive` nem servidor HTTP.

## Experiência visual e navegação

- Perfis, cartões de jogador e santuários continuam em **embeds**, preservando avatares, imagens e galerias.
- Painéis de entrada, ranking em texto, guias, avisos de ofertas e anúncios de conquistas usam **Markdown** quando isso mantém a funcionalidade.
- Botões, filtros, seletores e paginação atualizam a mensagem em que o usuário está navegando; confirmações e erros privados continuam efêmeros quando fazem sentido.
- Os comandos de publicação reutilizam o painel existente no canal, evitando duplicatas ao executá-los novamente.
- Os cartões do pódio do Coliseu mostram um catálogo visual das platinas aprovadas, com capa, plataforma e data. O catálogo é montado a partir dos comprovantes; imagens inacessíveis são ignoradas sem bloquear o restante do painel.

## Comandos e navegação

- Os antigos comandos individuais dos membros foram retirados da lista slash e passaram a ser acessados pelos botões do `/nara`; seus fluxos originais e regras de permissão foram preservados.
- `/colizeu` (com **Z**) é administrativo: atualiza a mensagem informativa e os rankings do canal do Colizeu.

A central `/nara` organiza os recursos de membro em botões. A lista de comandos administrativos continua separada e é acessada conforme as permissões do servidor. Consulte também [`GUIA_DE_COMANDOS_NARA.md`](GUIA_DE_COMANDOS_NARA.md) para a sequência completa de configuração.

## Loja de Denários
O botão **Loja** no `/nara` abre a loja privada do membro. Moderadores podem usar `/painel_loja` para publicar um painel fixo no canal atual; o botão **Abrir loja** continua funcionando após reinícios e abre a loja individual de quem clicou. A publicação atualiza o painel existente no mesmo canal em vez de duplicá-lo. Itens são cosméticos e ficam guardados no banco SQLite.


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
- `ia_nucleo.py`, `ia_ferramentas.py`, `ia_gemini.py`, `ia_multi.py`, `ia_provedores.py`, `ia_confirmacao.py` – agente Gemini multi-projeto, ferramentas e segurança
- `tests/` – testes do agente

## Santuários (perfil em thread privada)
Cada membro pode ter um **santuário**: uma thread privada dentro do canal `PERFIS_CHANNEL_ID`, com um cartão
(banner, bio, patente, XP, redes, galeria de platinas e, se o módulo Soulslike estiver ativo, os melhores tempos).
- `Meu santuário` (no painel `/nara` ou no painel do canal) cria/abre o seu; os botões **Personalizar**, **Redes** e **Atualizar** ficam dentro dele.
- `Visitar santuário` adiciona a pessoa à thread. Para sair, ela usa *Sair do tópico* e a thread some da lista dela.
- O conteúdo do tópico é dedicado ao perfil do proprietário: cartão, biografia, plataformas, runs e galeria. Visitantes não podem editar o Santuário.
- Ao abrir ou visitar, o bot tenta remover avisos automáticos de entrada/saída do Discord. A limpeza é restrita a mensagens de sistema; mensagens e conteúdo dos membros nunca são apagados por essa rotina.
- `/painel_santuarios` (moderadores) posta no canal de perfis os botões "Meu Santuário" e "Visitar um Santuário".
- A galeria atualiza sozinha quando uma platina é aprovada.

**Permissões do canal de perfis** (crie um canal de texto, ex. `#santuarios`):
- `@everyone`: Ver canal e Ler histórico **ligados**; Enviar mensagens, Enviar mensagens em tópicos e Criar tópicos **desligados** (visitantes só leem).
- Bot: Ver canal, Ler histórico de mensagens, Enviar mensagens em tópicos, **Criar tópicos privados**, **Gerenciar tópicos**, **Gerenciar mensagens**, Inserir links, Anexar arquivos, Fixar mensagens. `Gerenciar mensagens` permite limpar os avisos automáticos de entrada/saída; sem essa permissão, o Santuário continua funcionando, mas alguns avisos podem permanecer.

## Permissões dos comandos administrativos

Os comandos administrativos ficam separados da central de membros `/nara` e protegidos pelas permissões declaradas no Discord e pelas verificações internas do bot. `/adm` exige **Administrador**. A maior parte dos comandos de publicação, diagnóstico e catálogo exige **Gerenciar servidor**; alguns fluxos também verificam o papel de moderação configurado no NARA. Para ajustar a visibilidade por cargo, use Configurações do servidor → Integrações → NARA → permissões de comandos. Não remova os checks internos do bot ao alterar a visibilidade.


## Nara — XP e patentes

O sistema integrado concede XP por mensagens válidas (10–20 XP, com intervalo de 60 s por usuário), participação em canal de voz (5 XP a cada 5 min quando há pelo menos duas pessoas não bots) e eventos aprovados. Platinas continuam usando a recompensa existente `XP_PLATINA` (200 XP); runs aprovadas concedem 100 XP e um novo recorde concede mais 100 XP. O XP é compartilhado com o nível e as patentes.

Comandos de membro: **Meu nível** e **Ranking XP** dentro do `/nara`. O bot precisa das intents **Message Content**, **Server Members** e **Voice States** habilitadas no Developer Portal, além de permissão para gerenciar cargos. O cargo mais alto do bot deve ficar acima dos cargos de patente.

As patentes são calculadas pelo XP e o bot tenta atribuir o cargo correspondente quando o membro sobe de nível. **Os cargos precisam ser criados previamente no Discord** com estes nomes: Cinzas Novatas, Guerreiro Caído, Caçador de Almas, Cavaleiro do Abismo, Guardião das Cinzas, Arauto da Ruína, Executor Sombrio, Senhor das Almas, Lenda do Coliseu e Sentinela Imortal. O bot não cria cargos ausentes; precisa de Gerenciar Cargos e deve ficar acima deles na hierarquia.


## Inicialização rápida da Nara conversável

1. Instale Python 3.11 ou superior e extraia o projeto.
2. Instale as dependências: `python -m pip install -r requirements.txt`.
3. Execute `python configurar_bot.py` e informe, sem compartilhá-los, o token do bot Discord e uma chave Gemini.
4. No Discord Developer Portal, habilite **Message Content Intent**, **Server Members Intent** e **Voice States**.
5. Execute `python bot.py` (ou use `INICIAR_WINDOWS.bat` / `iniciar_linux.sh`).


### Ordem de decisão

1. **Respostas locais/SQLite:** saudações, FAQ, comandos, sistemas ativos, perfil e consultas do próprio membro.
2. **Ferramentas do NARA:** pedidos imperativos compatíveis com ferramentas registradas em `ia_ferramentas.py`. As validações de parâmetros, permissões, risco e confirmação continuam em `ia_nucleo.py` e `ia_confirmacao.py`.
3. **Gemini:** conversa livre, quando `NARA_CONVERSA_ENABLED=true`, e pesquisa factual com ferramentas compatíveis, quando `NARA_CHAT_IA_ENABLED=true`.
4. **Resposta transparente:** quando a função não existe, o provedor não está configurado ou a informação não pode ser confirmada.

### O que a Nara consulta localmente

`nara_conhecimento.py` constrói um inventário a partir dos comandos efetivamente registrados em `bot.tree` e dos cogs atualmente carregados. Comandos com `default_permissions` incompatíveis são omitidos; comandos com checks customizados que o inventário não consegue avaliar com segurança também são omitidos. A consulta de canais usa `permissions_for(member)` e lista somente canais que o próprio usuário pode visualizar; a consulta de cargos lista apenas os cargos do próprio membro. Isso não equivale a um inventário de todas as configurações administrativas do servidor nem libera leitura de canais privados, saldos ou dados de terceiros.

As consultas de perfil/platinas/zerados/inventário continuam usando as funções SQLite existentes. O inventário de runtime é contexto de apoio e não prova, por si só, que uma ação esteja implementada: a Nara só anuncia execução quando existe ferramenta concreta e seu retorno confirma o resultado.

### Configuração independente das rotas de IA

- `NARA_CONVERSA_ENABLED=true`: habilita o papo livre curto, sem ferramentas, sujeito a cooldown e limites diários. Portanto, pode chamar Gemini mesmo que a opção abaixo esteja desligada.
- Para a conversa realmente gerar respostas, configure `GEMINI_API_KEY` (ou `GEMINI_BACKUP_API_KEY`). Sem uma chave válida, a Nara permanece online para funções locais, mas o papo livre só retorna frases de contingência.
- `NARA_CHAT_IA_ENABLED=false`: desliga a pesquisa factual no chat com ferramentas; **não** desliga o papo livre acima.
- `IA_ACOES_MODERACAO=false`: mantém bloqueada a ação de moderação `conceder_xp` via agente. As demais ferramentas continuam sujeitas aos seus próprios níveis de risco, validações e confirmação. Pedidos de ação precisam de `GEMINI_API_KEY` ou `GEMINI_BACKUP_API_KEY`; continuam disponíveis mesmo que conversa livre e pesquisa factual estejam desligadas.


**Limite atual:** o listener da Nara não abre nem interpreta imagens/anexos. Não envie prints com chaves, nem arquivos `.conf`; a rota avisa para descrever a tela em texto. O projeto não implementa OCR nem leitura visual na Nara.

### Validação e pontos de configuração

Para ativar/desativar as rotas, use as variáveis listadas acima; nenhuma nova chave de serviço foi adicionada.

## Zerados (`cogs/zerados.py`)
Versão leve das platinas para quem quer registrar os jogos que finalizou, sem precisar platinar.
- O botão **Jogos zerados** no `/nara` abre o painel (registrar, lista, ranking total/mensal).
- Todo envio vira um **pedido pendente na Central de Aprovação** (`MOD_CHANNEL_ID`), junto com os comprovantes opcionais. A equipe aprova/rejeita no próprio cartão. O pedido só entra no perfil/ranking após aprovado.
- Após aprovação, dá XP/Denários (`XP_ZERADO`, `DENARIOS_ZERADO`), até `ZERADOS_XP_LIMITE_DIARIO` registros aprovados nas últimas 24h. Se o limite já foi atingido, o registro é aprovado sem recompensa.
- Se `ZERADOS_CHANNEL_ID` estiver definido, só os registros **aprovados** são anunciados lá (com links para os comprovantes, se houver).
- **Remover zerado** no `/nara`:  o dono pode cancelar um pedido pendente ou remover o próprio registro aprovado; moderadores podem remover registros de qualquer membro. Recompensas concedidas são devolvidas.
- Moderadores: **`/postar_painel_zerados`** publica o botão fixo no canal.
- O perfil mostra a contagem de ✅ Zerados ao lado das platinas.


Se o primeiro projeto Gemini falhar, a Nara tenta o segundo. Configure `GEMINI_API_KEY` e `GEMINI_BACKUP_API_KEY` de projetos distintos e, para a pesquisa web, `TAVILY_API_KEY` do plano gratuito. Os modelos são definidos por `GEMINI_MODEL` e `GEMINI_BACKUP_MODEL`. Em erro de quota ou `429`, consulte `/gemini_status` para ver o estado dos dois circuit breakers.

## Base local de perguntas e respostas da Nara

A base `dados/nara_faq.json` contém intenções, exemplos de paráfrases, palavras-chave e mensagens finais prontas para Discord. O classificador `faq_base.py` funciona localmente, sem Gemini, rede ou dependências externas; usa normalização de texto, similaridade lexical e limiar/margem de confiança para não chutar perguntas ambíguas. Consultas pessoais e rankings continuam usando handlers que consultam o SQLite em tempo real. Para ampliar o FAQ, adicione exemplos e, quando aplicável, um campo `answer` (mensagem final) ou `handler` (consulta dinâmica já implementada). Não coloque prompts de IA nesse arquivo.


## Central de Ajuda interativa da Nara

O botão **Central de ajuda** no `/nara` abre o painel privado com 12 categorias, 134 intenções e mais de 1.500 formulações de perguntas. As categorias seguem uma ordem de uso, e as perguntas de cada categoria ficam organizadas pelo título. A pessoa escolhe a categoria e depois a pergunta pronta. Respostas fixas vêm de `dados/nara_faq.json`; perguntas pessoais e rankings são consultados por handlers locais no SQLite/runtime. Essa navegação não chama Gemini. Para acessar as funções dos membros, use `/nara`. Para alterar a base, edite o JSON e reinicie o bot; as intenções devem continuar vinculadas aos fluxos reais do código.


## Central de Aprovação



## Contribuições da comunidade, Arquivo de Mundos e Coliseu Social

O projeto inclui um fluxo moderado de contribuições, publicações de lore e teorias, guias, FAQ comunitária, interações em Runs/platinas/zerados, comparação de gladiadores e Livro de Visitas dos Santuários. Consulte **[GUIA_CONTRIBUICOES_INTERACOES_NARA.md](GUIA_CONTRIBUICOES_INTERACOES_NARA.md)** para ativar canais, configurar XP, publicar o painel e revisar contribuições.

## Configuração visual por servidor

Use `/adm` no Discord. O botão **Configuração Automática** cria a categoria e os canais oficiais do NARA, vincula cada destino ao sistema correspondente e preserva canais existentes. Depois, em **Canais**, cada destino pode ser trocado individualmente com um seletor nativo do Discord. Em **Cargos**, escolha o cargo da equipe para conceder acesso à Central privada de Aprovação. Consulte `GUIA_CONFIGURACAO_VISUAL.md` para detalhes e permissões.

## Escopo e personalidade da Nara
A Nara tem escopo exclusivo da comunidade, personalidade debochada, vínculos sociais individuais com opt-in e o relatório operacional `/nara_relatorio` para a equipe. Os prompts ficam em `prompts/` e a configuração das rotas de IA em `CONFIGURACAO_IA_NARA.md`.


## Limpeza automática do canal de dúvidas da Nara

Configure `IA_CANAIS_LIVRES` com os IDs dos canais em que a Nara responde sem ser mencionada, separados por vírgula. Por padrão, esses canais são limpos a cada 30 minutos (`NARA_DUVIDAS_LIMPEZA_INTERVALO_MINUTOS=30`). A limpeza começa somente após o primeiro intervalo completo depois que o bot fica pronto. Mensagens fixadas são preservadas. Para desligar, use `NARA_DUVIDAS_LIMPEZA_ENABLED=false`.

O bot precisa de `Ver canal`, `Ler histórico de mensagens` e `Gerenciar mensagens` em cada canal. A limpeza remove mensagens não fixadas, inclusive perguntas e respostas antigas, portanto fixe qualquer aviso ou painel que deva permanecer.


## Integração automática: platina também conta como jogo zerado

Quando uma platina é aprovada pela moderação, a NARA registra automaticamente o mesmo jogo em **Jogos Zerados**, usando o membro, título, plataforma e data da conquista.

- O membro não precisa enviar um segundo formulário.
- Se já existir um zerado aprovado para o mesmo jogo/plataforma, nenhum registro ou prêmio de zerado duplicado é criado.
- Se existir um pedido manual de zerado pendente para essa combinação, ele é convertido em aprovado pela validação da platina.
- A recompensa da platina e a recompensa do zerado seguem suas configurações próprias. O limite diário de recompensas de zerados continua valendo.
- O vínculo entre o registro de zerado e a platina é armazenado em `source_platina_id`, com índice único para impedir associação duplicada.
- A migração é incremental: bancos existentes recebem a nova coluna sem apagar os registros atuais.

A aprovação da platina e a sincronização do zerado, incluindo as recompensas, acontecem na mesma transação do banco de dados.
