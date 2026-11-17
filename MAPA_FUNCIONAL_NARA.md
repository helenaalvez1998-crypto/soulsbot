# Mapa funcional auditado do NARA e da Nara local

**Base analisada:** pacote final do NARA/Nara, com as funções e o FAQ local auditados; o recurso removido do tutorial antigo permanece ausente nesta versão.  
**Regra da base:** cada resposta FAQ foi comparada com a implementação indicada em `verified_sources` no `dados/nara_faq.json`. Respostas que dependem de dados pessoais são handlers dinâmicos, não valores fixos.

## 1. Inventário do conhecimento local

- **134 intenções** distintas.
- **1.546 formulações** de perguntas, incluindo sinônimos, variações de frase e perguntas operacionais.
- **118 respostas estáticas**.
- **16 handlers dinâmicos** para dados de perfil, saldo, inventário, rankings, comandos/canais, sistemas ativos e recompensas por servidor.
- **12 categorias** no painel de perguntas.
- A base não contém prompts de IA: são respostas finais e instruções de roteamento local.

### Categorias da Central de Ajuda

1. Platinas e conquistas
2. Jogos zerados
3. Runs e desafios
5. XP e patentes
6. Perfis e rankings
7. Perfis e Santuários
8. Loja e Denários
9. Servidor, cargos e painéis
10. YouTube e ofertas
11. Administração e Nara
12. IA e funcionamento

O `/central_ajuda` abre a central de forma privada. A ordem foi ajustada para seguir a jornada comum do membro: primeiro os sistemas de jogo e progressão; depois perfil/economia; por fim, servidor, integrações e IA. As perguntas de cada categoria ficam ordenadas por título. Cada categoria contém perguntas estáticas e consultas dinâmicas. Uma consulta dinâmica chama o mesmo handler SQLite/runtime usado pela Nara no chat; portanto, o saldo/inventário não fica congelado numa resposta antiga.

O `/comandos` abre um índice privado com **nove áreas**, cobrindo os **43 comandos e subcomandos** cadastrados no pacote. Ele separa comandos do jogador de publicação, administração, catálogo, runs e diagnósticos. Os comandos existentes não foram renomeados; `/coliseu` é o painel do jogador e `/colizeu` é a atualização administrativa do canal. O Discord controla a ordenação da busca nativa de slash commands; o índice do NARA organiza a navegação sem quebrar chamadas atuais.

## 2. XP, nível e patentes

### XP por mensagem
- Mensagem válida concede valor aleatório entre **10 e 20 XP**.
- Há intervalo de **60 segundos por pessoa** entre concessões por mensagem.
- Mensagens de bots, mensagens sem texto nem anexo e o canal de moderação não contam. Mensagens com anexo podem contar mesmo sem texto.

### XP por voz
- **5 XP a cada 5 minutos**.
- Exige ao menos **duas pessoas humanas** no canal.
- Bots não contam; membros ensurdecidos por si mesmos ou pelo servidor não recebem o ganho.

### Fórmula de nível
XP mínimo acumulado para o nível \(n\): `100 × (n − 1)²`.  
O `/nivel` mostra nível, XP atual, barra e quanto falta para o próximo nível.

### Patentes
| Nível mínimo | Patente |
|---:|---|
| 1 | Cinzas Novatas |
| 5 | Guerreiro Caído |
| 10 | Caçador de Almas |
| 15 | Cavaleiro do Abismo |
| 20 | Guardião das Cinzas |
| 30 | Arauto da Ruína |
| 40 | Executor Sombrio |
| 50 | Senhor das Almas |
| 75 | Lenda do Coliseu |
| 100 | Sentinela Imortal |

Quando o nível muda, o bot tenta sincronizar o cargo da patente. Os cargos precisam existir e a hierarquia/permissões do bot precisam permitir a atribuição. O bot não cria automaticamente os cargos ausentes.

## 3. Platinas

- O membro abre `/coliseu` e escolhe Platinas, ou usa o painel público correspondente.
- Formulário: jogo, plataforma, data `DD/MM/AAAA` e pelo menos um comprovante.
- Plataformas listadas no formulário: PS5, PS4, PS3, PC, Xbox Series, Xbox One, Switch e Outra.
- Data futura é recusada.
- Aceita imagens e vídeos: máximo **10 arquivos**, **20 MB por arquivo** e **40 MB no total**.
- Uma pessoa não pode cadastrar a mesma platina para o mesmo jogo/plataforma enquanto já houver registro pendente ou aprovado.
- A solicitação é enviada ao canal de moderação e fica pendente.
- A aprovação credita a recompensa configurada para o servidor, atualiza perfil/painel/galeria e pode sincronizar a patente. A rejeição não concede recompensa e o bot tenta avisar por DM.
- Só platinas aprovadas aparecem em coleção, ranking e galeria do Santuário.

**Valores padrão globais no código:** 200 XP e 50 Denários por platina aprovada. O `/adm` permite sobrescrever os valores por servidor. A resposta dinâmica da Nara consulta o valor efetivo do servidor.

## 4. Jogos zerados

- `/zerados` abre o painel privado; a moderação pode publicar o painel público com `/postar_painel_zerados`.
- Formulário: jogo, plataforma, data `DD/MM/AAAA`, comentário opcional e até 5 comprovantes opcionais.
- Plataformas: PS5, PS4, PS3, PC, Xbox Series, Xbox One, Switch, Mobile e Outra.
- Data futura é recusada; duplicidade é bloqueada por pessoa + jogo + plataforma.
- Imagens/vídeos: **20 MB por arquivo**, **40 MB no total**.
- Todo envio é encaminhado ao mesmo canal central de aprovação usado por platinas e runs. O pedido só entra no perfil/ranking e só recebe recompensa após aprovação.
- Por padrão, até **3 registros aprovados nas últimas 24 horas** recebem recompensa. Pedidos pendentes não contam para o limite; se o limite já foi atingido no momento da aprovação, o registro entra sem XP/Denários. O limite e os valores podem ser configurados no `/adm`.
- `/remover_zerado <registro>` permite cancelar o próprio pedido pendente ou remover o próprio registro aprovado; moderadores podem remover registros de qualquer membro. O sistema também estorna o XP/Denários que aquele registro tinha concedido.
- O painel tem lista, ranking e seleção para consultar outro membro.

**Valores padrão globais no código:** 50 XP e 10 Denários por registro elegível. A Nara consulta as configurações efetivas do servidor quando explica recompensas.

## Central de Aprovação

- `MOD_CHANNEL_ID` (ou **Canal central de aprovação/moderação** em `/adm`) é o destino único dos cartões de revisão de platinas, runs Soulslike e jogos zerados.
- Aprovar/rejeitar acontece nos botões do próprio cartão; os canais públicos de anúncio continuam separados e só recebem itens aprovados.
- Jogos zerados novos ficam pendentes, fora do perfil e do ranking e sem recompensa até a aprovação. Registros antigos são preservados como aprovados na migração do banco.

## 5. Runs e desafios Soulslike

- A Central Soulslike permite registrar run, consultar Livro dos Desafios, Hall da Fama e Meu Perfil.
- Formatos de tempo aceitos incluem `1:30:45`, `90:15`, `1h30m45s`, `1h30` e `45m12s`.
- O formulário seleciona jogo/desafio, tempo e build opcional.
- O bot pede o comprovante por DM: imagem ou vídeo até **20 MB**, enviado em até **10 minutos**. Depois apresenta resumo e pede confirmação.
- Runs submetidas ficam pendentes até revisão da moderação. O histórico mostra até 10 registros recentes e seus estados; uma run pendente pode ser cancelada no painel do jogador.
- Somente runs aprovadas entram no ranking. O ranking usa o melhor tempo individual por jogo/desafio e mostra repetições.
- Aprovação concede **100 XP**; novo recorde global para aquela combinação jogo/desafio concede mais **100 XP** (200 XP total). O código não concede Denários por run.
- Administradores podem cadastrar jogos/desafios e suas regras pela família `/soulslike`. Uma run aprovada pode ser invalidada por `/soulslike invalidar`, saindo do ranking e mantendo registro de auditoria.



## 6. Perfil e Santuário

- Perfil do jogador mostra nível, patente, XP, progresso, Denários, estatísticas de platinas/zerados e posições nos rankings.
- Santuário é um tópico privado criado no canal de perfis configurado. O banner exibido vem do banner da conta Discord; o formulário Personalizar não oferece upload de banner. Exige que o bot possa criar/gerenciar tópicos privados.
- Dono pode personalizar frase (100 caracteres), bio (500), jogo favorito (60) e tema: Ouro, Prata, Sangue, Safira, Esmeralda ou Violeta.
- Dono pode cadastrar/remover contas de Steam, Epic, GOG, EA, Ubisoft, Battle.net, itch.io, PlayStation, Xbox, Twitch, YouTube, Instagram, TikTok e X, usando URL de domínio permitido ou `@` quando suportado. **Limitação de exibição:** plataformas de jogos aparecem em todos os Santuários; Twitch, YouTube, Instagram, TikTok e X só são renderizados publicamente no Santuário do proprietário configurado do bot nesta versão.
- Outro membro pode visitar se for adicionado à thread pelo fluxo de visita; depois pode sair pelo menu de tópicos do Discord.
- Galeria mostra platinas aprovadas, até 10 por página; a lista e a captura ampliada são abertas em resposta efêmera para quem clicou. O comprovante pode ficar indisponível caso a mensagem/arquivo original deixe de estar acessível.
- O painel `/coliseu` é privado para quem o abriu, mas permite selecionar outro membro e ver a tela Perfil, que inclui Denários. O cartão do Santuário também exibe Denários a quem tem acesso ao tópico privado. A consulta de perfil pelo agente da Nara não devolve Denários para terceiros, e a ferramenta de inventário é limitada ao próprio usuário; portanto, a visibilidade depende do fluxo utilizado.

## 7. Loja e Denários

- `/loja` abre a loja privada. `/painel_loja` (moderação) publica o catálogo público.
- Cores Brasa, Névoa, Hera e Crepúsculo: **100 Denários** cada.
- Títulos Caçador de Chefes, Mestre das Rolagens e Persistente: **150 Denários** cada.
- Eterno Renascido: **300 Denários** e exige nível 20.
- A compra é única por item. O membro pode equipar/desequipar o item já comprado.
- É cosmético: não aumenta XP, nível, patente ou ranking. Itens equipados aparecem no perfil.
- Saldo e inventário são mostrados na interface privada do membro.

## 8. Cargos, verificação e painéis

- `/painel_verificacao` publica o botão Verificar-me; ele tenta conceder o cargo de servidor simplificado. O cargo precisa existir, e o bot precisa de Gerenciar Cargos e hierarquia suficiente.
- `/painel_cargos` publica botões de cargos configuráveis; clicar alterna adicionar/remover. `/cargo_painel` edita até 25 opções; `/editar_painel_cargos` altera título e mensagem. A moderação usa `/cargo_painel` para adicionar/editar/remover opções (limite de 25) e `/editar_painel_cargos` para editar título/mensagem. O código sugere oito cargos iniciais (Avisos de Vídeo, Avisos de Live, Elden Ring, Dark Souls, Bloodborne, Sekiro, Outros Soulslikes e Procurando Co-op), mas não cria esses cargos no servidor.
- `/adm` exige a permissão Discord **Administrador** (não apenas Gerenciar servidor). Configura por servidor canais de moderação, platinas, vídeos, lives, zerados, perfis, jogos grátis e promoções; cargos de moderação e avisos; XP/Denários por platina/zerado e limite diário de recompensa de zerados. Mostra o que está personalizado, o que usa padrão e o que está sem valor.
- Restaurar configurações remove somente overrides administrativos daquele servidor e volta aos padrões de `config.py`; não apaga dados de usuários. A seção Personalização global ainda não oferece troca de cores/prefixo pelo painel.
- `/coliseu` (grafia com S) abre o painel do membro. `/colizeu` (com Z) é a ação administrativa que atualiza o painel Hall dos Gladiadores no canal configurado. O painel de ranking atualiza a cada 10 minutos quando configurado.
- Painéis públicos de platinas/zerados podem ter cópias rotativas a cada 30 minutos; a rotação protege a mensagem fixa/pinada.

## 9. YouTube e ofertas

### YouTube
- Feed RSS para vídeos novos: padrão de 120 segundos. Se o RSS falhar, pode recorrer à API. O primeiro ciclo após iniciar apenas memoriza o vídeo mais recente; não anuncia conteúdo antigo.
- Detecção de lives exige `YOUTUBE_API_KEY`, padrão de 10 minutos entre 19h e 24h (horário de Brasília). A primeira consulta também memoriza o estado atual sem mandar aviso atrasado.
- `/status_youtube` mostra ID do canal monitorado, canais de vídeo/live, presença da chave e intervalos.
- `/teste_video` e `/teste_live` apenas mostram os canais configurados em resposta privada; apesar do nome, não publicam notificação de teste no canal.

### Ofertas
- Fontes incluem Steam, Epic, GOG, GamerPower e integrações opcionais ITAD/Nuuvem e GG.deals.
- Jogo temporariamente gratuito e promoção com desconto são fluxos/canais distintos; free-to-play permanente não é tratado como oferta grátis.
- Padrões: verificação a cada 30 minutos, até 8 ofertas por ciclo e desconto mínimo de 50% para promoções. O sistema deduplica anúncios e evita repostar a mesma oferta.
- `/status_ofertas` mostra canais, intervalo, desconto mínimo, layout e fontes opcionais. `/previa_oferta` mostra um cartão de exemplo apenas para quem executou o comando.
- Se `OFFERS_SHOW_DESCRIPTION=true`, o bot tenta traduzir descrições para pt-BR usando Gemini e mantém cache SQLite; se a chave não estiver disponível ou a tradução falhar, usa o texto original.

## 10. Comandos e entradas principais

### Membros
`/comandos`, `/central_ajuda`, `/coliseu`, `/zerados`, `/remover_zerado`, `/nivel`, `/ranking-xp`, `/loja`.

### Moderação/administradores
`/adm`, `/painel_verificacao`, `/painel_cargos`, `/editar_painel_cargos`, `/cargo_painel`, `/painel_principal`, `/postar_painel`, `/painel_platinas`, `/postar_painel_zerados`, `/painel_santuarios`, `/painel_loja`, `/painel_colizeu`, `/colizeu`, `/sl_admin publicar_central`, `/sl_admin jogo_adicionar`, `/sl_admin desafio_adicionar`, `/sl_admin invalidar`, `/status_youtube`, `/teste_video`, `/teste_live`, `/status_ofertas`, `/previa_oferta`, `/gemini_status`.

## 11. Conversa Gemini, pesquisa e contexto

- `NARA_CONVERSA_ENABLED` controla o papo normal com Gemini; por padrão está ligado no código. Padrões: 20 respostas por pessoa/dia, 250 por servidor/dia, cooldown de 6 segundos e 320 tokens por resposta. `0` remove cada teto numérico correspondente.
- `NARA_CHAT_IA_ENABLED` controla pesquisa factual com ferramentas/fontes; não desliga a conversa normal. A pesquisa de chat usa `IA_LIMITE_DIARIO` (padrão 3 por usuário/dia) e cooldown de 8 segundos entre pesquisas externas.
- O roteador de conversa tenta Gemini principal, depois reserva e depois terceira configuração. `/gemini_status` (administrador) mostra o estado local dos circuitos, não a quota real restante no Google.
- `IA_CANAIS_LIVRES` lista IDs de canais onde perguntas locais reconhecidas podem ser respondidas sem menção; essa rota não chama Gemini.
- Menção real `@Nara` (ou resposta direta à Nara) direciona conversa para IA. Respostas locais/SQLite são usadas como contexto factual para que o modelo não invente dados.
- Escrever “Nara” no texto sem menção real direciona somente para respostas locais, inclusive FAQ comunitária aprovada quando houver correspondência.
- Mensagens sem menção e sem chamada pelo nome não iniciam conversa generativa.
- Ao ser mencionada com pedido explícito de ação, a Nara pode abrir atalhos para `/coliseu`, Platinas, Zerados, Runs, Loja e Santuário; consultar perfil/platinas/zerados/rankings/Hall da Fama/loja; equipar/desequipar itens próprios; e preparar compra, registro de zerado, edição do Santuário ou gestão de redes para confirmação do autor. O agente não confirma sucesso antes do resultado da ferramenta.
- A concessão de XP pela IA é ferramenta opcional, controlada por `IA_ACOES_MODERACAO=false` por padrão; quando habilitada, exige moderador e confirmação, aceita 1–500 XP e registra o motivo. Não há ferramenta geral de banir/expulsar/silenciar.
- A pesquisa com ferramentas do chat está limitada a páginas textuais de Elden Ring em domínios permitidos; não é pesquisa irrestrita de qualquer jogo nem leitura de PDF/imagens.
- O pedido de conversa não leva o histórico inteiro do canal. Quando a pessoa responde diretamente à Nara, pode incluir até 240 caracteres da resposta anterior. O cache temporário para perguntas repetidas não é memória completa de conversas.

## 12. O que a Nara faz quando não entende

- Em canal configurado em `IA_CANAIS_LIVRES`, uma pergunta reconhecida recebe resposta local sem menção e sem consumo Gemini.
- Se não reconhecer em canal livre, ela pede para repetir a pergunta mencionando `@Nara` e mostra botão para abrir a Central de Ajuda.
- Ao receber menção real `@Nara` (ou resposta direta a ela), pergunta aberta segue para Gemini quando `NARA_CONVERSA_ENABLED=true`; intenções locais podem fornecer dados verificados ao modelo.
- Chamar “Nara” apenas pelo texto, sem `@`, mantém o fluxo local: FAQ, dados SQLite e fallback determinístico, sem IA generativa.
- Fora de canal livre, mensagens sem menção e sem chamada textual pelo nome são ignoradas.
- A classificação local usa normalização, exemplos e semelhança por tokens com limite/margem. Ela reduz falhas de formulação, mas não interpreta literalmente qualquer pergunta imaginável; quando houver dúvida, não deve inventar.

## 13. Itens removidos na limpeza do projeto

Foram removidos por não terem uso no fluxo ativo: `conquistas.py`, `perfil_card.py`, o adaptador DeepSeek (`ia_deepseek.py` e `deepseek_resilience.py`) e o Caçador de Troféus (`cogs/trofeus.py`, `trofeus_service.py`, `cacador_fila.py` e `catalogo_ia.py`). A conversa principal usa o roteador Gemini descrito em `ia_multi.py`. A FAQ não promete conquistas/badges integrados ao perfil, DeepSeek nem pesquisa de catálogo de troféus.

## 14. Validação desta edição

- Sintaxe Python: compilação de todos os arquivos `.py` sem erro.
- Reconhecimento: todas as **1.546 formulações** cadastradas retornam a intenção correspondente.
- Testes automatizados: **77 testes aprovados**.
- Não foi possível executar um teste de UI/Discord real neste ambiente porque `discord.py` não está instalado aqui. A API declarada pelo projeto em `requirements.txt` é `discord.py>=2.6`; sincronização de comandos, permissões e renderização de Select/Button devem ser confirmadas na hospedagem/servidor depois do deploy.
