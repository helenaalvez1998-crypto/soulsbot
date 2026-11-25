# Auditoria integral do catálogo — NARABOT V57

## Escopo e limites

- Foram inspecionados os **110 modelos estáticos** definidos no código: 95 cartas do catálogo base, 5 Primordiais e 10 recompensas de Patente.
- O banco `colizeu.db` não foi fornecido; cartas personalizadas/transmutadas e exemplares persistidos em coleções não entram nesta contagem.
- Cartas de recompensa por jogos (`carta_jogo`) são geradas a partir de dados do usuário e não fazem parte dos 110 modelos fixos.
- A facção exibida no NARABOT é uma classificação estratégica própria do jogo. Não deve ser interpretada automaticamente como filiação canônica do personagem em Elden Ring. O tipo mecânico continua separado da facção narrativa.
- Para personagens e itens canônicos, o texto foi redigido como resumo curto; personagens e arquétipos sem identidade oficial são tratados como criações/inspirações do NARABOT, não como personagens oficiais.

## Correções aplicadas nesta versão

1. Preenchidas as **21 descrições narrativas vazias** do catálogo fixo, sem usar lore como substituto do texto mecânico.
2. Corrigidas as descrições de Malenia, Radahn, Maliketh, Messmer e Placidusax, que continham textos mecânicos antigos incompatíveis com as habilidades de identidade atualmente executadas.
3. Separadas descrições narrativas dos textos de efeito das cartas Especiais, Relíquias e Primordiais. O efeito mecânico permanece na habilidade.
4. Restaurados os seis textos mecânicos das Relíquias no dicionário `HABILIDADES`, para que o detalhe da carta e a arte não caiam em “Sem habilidade especial”.
5. Corrigidos os textos de Névoa de Sellia e Lua Gélida: o motor aplica marcas de Podridão/Geada, não clima de fileira.
6. Corrigida a arte de carta para consumir o mesmo texto de habilidade preparado pelo motor, inclusive habilidades de identidade e escalonamento por raridade.
7. Removida a alegação genérica de escalonamento de raridade para Chama Negra e Lei da Regressão, cujos handlers não alteram bônus.
8. Incrementada a versão de artes para invalidar imagens em cache produzidas com os textos antigos.

## Inventário individual

Cada registro abaixo mostra identidade, classificação usada pelo jogo, atributos e os dois textos separados. “Facção do jogo” é uma convenção estratégica; não equivale a facção canônica de Elden Ring.

### 001. Cavaleiro da Árvore Áurea
- **ID:** `chefe_guardiao_cinzas` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Égide das Cinzas (`quebra_ritmo`)
- **Efeito mecânico:** Ao entrar, concede +1 a um aliado da mesma fileira. Se já houver um aliado ali, recebe +1. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Um sentinela montado patrulha os caminhos que conduzem à Árvore Áurea, impondo a autoridade da capital.

### 002. Ranni, Bruxa da Lua
- **ID:** `chefe_dama_vazio` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 6 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Fenda do Vazio (`ultimo_folego`)
- **Efeito mecânico:** Ao entrar, reduz em 2 o bônus da unidade inimiga mais forte (mínimo -2). Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** A princesa lunar rompeu com os Dois Dedos e busca um destino independente da Vontade Maior.

### 003. Cavaleiro do Cão de Caça
- **ID:** `chefe_cervo_sombrio` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Um cavaleiro errante segue a trilha de presas pelas florestas enevoadas das Terras Intermédias.

### 004. Godfrey, Primeiro Lorde Prístino
- **ID:** `chefe_rei_afogado` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 7 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Dízimo do Abismo (`primeira_luz`)
- **Efeito mecânico:** Recebe +2 se houver unidade no seu descarte; caso contrário, +1 se o rival controlar mais unidades. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Primeiro Lorde Prístino e consorte de Marika, Godfrey liderou os guerreiros que conquistaram as Terras Intermédias.

### 005. Gurranq, Clérigo Bestial
- **ID:** `chefe_oraculo_ruina` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Corpo a corpo
- **Poder-base:** 7 · **Raridade:** Lendária · **Custo cadastrado:** 4
- **Habilidade:** Presságio da Ruína (`impeto`)
- **Efeito mecânico:** Reduz em 1 o bônus da unidade inimiga mais forte e recebe +1 se o rival estiver à frente. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** O clérigo bestial consome Raiz da Morte e guarda um segredo ligado à própria Runa da Morte.

### 006. Assassino da Faca Negra
- **ID:** `chefe_cacador_sem_rosto` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Um assassino Numen envolto em segredo, ligado à Noite das Facas Negras e ao fragmento da Runa da Morte.

### 007. Cavaleiro de Leyndell
- **ID:** `chefe_vigia_cinzento` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Um soldado da capital mantém a vigília entre as muralhas erguidas em nome da Ordem Áurea.

### 008. Lâmina Negra Errante
- **ID:** `chefe_aparicao_veio` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 4 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Uma figura encapuzada atravessa as sombras, deixando apenas o rumor de uma lâmina silenciosa.

### 009. Malenia, Lâmina de Miquella
- **ID:** `chefe_malenia_lamina_miquella` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 9 · **Raridade:** Primordial · **Custo cadastrado:** 4
- **Habilidade:** Flor Escarlate (`drenagem`)
- **Efeito mecânico:** Ao entrar, aplica Podridão Escarlate às unidades inimigas da fileira; alvos já contaminados sofrem uma segunda marca. Potência Primordial: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 5 dessas alterações por ativação.
- **Descrição narrativa:** Espadachim lendária e irmã gêmea de Miquella, luta enquanto a Podridão Escarlate consome seu corpo.

### 010. Radahn, Flagelo das Estrelas
- **ID:** `chefe_radahn_flagelo_estrelas` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 9 · **Raridade:** Primordial · **Custo cadastrado:** 4
- **Habilidade:** Gravidade do Flagelo (`quebra_ritmo`)
- **Efeito mecânico:** Ao entrar, desloca a unidade inimiga mais forte para sua fileira e reduz seu bônus em 2. Potência Primordial: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 5 dessas alterações por ativação.
- **Descrição narrativa:** General temido da Fragmentação, dominou a gravidade para deter o curso das estrelas e permaneceu em Caelid após a Podridão.

### 011. Maliketh, Lâmina Negra
- **ID:** `chefe_maliketh_morte_destinada` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 8 · **Raridade:** Lendária · **Custo cadastrado:** 4
- **Habilidade:** Morte Destinada (`cacador_arcano`)
- **Efeito mecânico:** Ao entrar, remove até 2 pontos de bônus da unidade inimiga mais forte. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** Sombra leal de Marika e guardião da Runa da Morte, carrega a Morte Destinada selada em sua lâmina.

### 012. Messmer, o Empalador
- **ID:** `chefe_messmer_impalador` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 8 · **Raridade:** Lendária · **Custo cadastrado:** 4
- **Habilidade:** Lança do Impalador (`quebra_ritmo`)
- **Efeito mecânico:** Ao entrar, aplica Sangramento às unidades inimigas da fileira; uma segunda marca provoca Hemorragia. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** Filho de Marika e senhor da chama impura, comandou a purga que devastou o Reino das Sombras.

### 013. Placidusax, Lorde Dragão
- **ID:** `chefe_placidusax_lorde_dragao` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 9 · **Raridade:** Primordial · **Custo cadastrado:** 4
- **Habilidade:** Tempestade do Tempo (`olho_tempestade`)
- **Efeito mecânico:** Ao entrar, aplica Geada às unidades inimigas da fileira e recebe +1 por inimigo atingido, até +3. Potência Primordial: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 5 dessas alterações por ativação.
- **Descrição narrativa:** Lorde Dragão ancestral que aguarda, em Farum Azula, o retorno de seu deus desaparecido.

### 014. Duelista da Casa Hoslow
- **ID:** `arma_lamina_peregrino` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Herdeiro de uma casa de duelistas, transforma a elegância do aço em uma promessa de sangue.

### 015. Ferreiro de Volcano Manor
- **ID:** `arma_martelo_fornalha` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Entre fornalhas e juramentos de traição, um artesão molda armas para os recusantes do Monte Gelmir.

### 016. Feiticeiro Cariano
- **ID:** `arma_cajado_marulho` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Longa distância
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Discípulo da realeza cariana, conjura feitiçarias de pedra cintilante sob a proteção da lua.

### 017. Espadachim da Lua Negra
- **ID:** `arma_duas_luas` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 7 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Dança Espelhada (`precisao`)
- **Efeito mecânico:** Recebe +1 se houver outra unidade aliada em fileira diferente. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Um duelista das tradições carianas conduz a lâmina sob a luz fria da Lua Negra.

### 018. Sentinela do Portão de Leyndell
- **ID:** `arma_grande_sino` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 8 · **Raridade:** Lendária · **Custo cadastrado:** 4
- **Habilidade:** Sino do Último Bastião (`instinto`)
- **Efeito mecânico:** Recebe +2 quando sua pontuação estiver abaixo da rival. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** Um guardião de elite protege os acessos da capital e enfrenta qualquer ameaça à ordem dourada.

### 019. Leitora de Estrelas de Sellia
- **ID:** `arma_agulha_astro` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Longa distância
- **Poder-base:** 4 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Uma estudiosa de Sellia observa os astros e procura caminhos ocultos na feitiçaria noturna.

### 020. Lanceiro da Árvore Áurea
- **ID:** `arma_lanca_fornalha` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Treinado para defender os domínios da Árvore Áurea, avança com lança e disciplina militar.

### 021. Batedor da Mansão Vulcânica
- **ID:** `arma_arco_peregrino` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Um recusante percorre os caminhos do Monte Gelmir, atento às rotas e aos movimentos dos inimigos.

### 022. Monge do Fogo
- **ID:** `magia_brasa_errante` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Corpo a corpo
- **Poder-base:** 4 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Devoto do fogo dos gigantes, preserva ritos antigos nas encostas geladas dos Picos dos Gigantes.

### 023. Confessora da Ordem Áurea
- **ID:** `magia_selo_vigilia` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Selo de Vigília (`adaptacao`)
- **Efeito mecânico:** Concede resistência climática 1 a si e +1 a um aliado na mesma fileira. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Treinada para agir discretamente, a Confessora combina devoção, infiltração e combate próximo.

### 024. Dragoeiro Ancião
- **ID:** `magia_trovao_oco` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Longa distância
- **Poder-base:** 6 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Descarga Oca (`drenagem`)
- **Efeito mecânico:** Reduz em 1 o bônus de todas as unidades inimigas na sua fileira. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Um guerreiro ligado aos antigos dragões canaliza relâmpagos ancestrais em meio à batalha.

### 025. Astróloga de Liurnia
- **ID:** `magia_nevoa_antiga` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 7 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Névoa Ancestral (`encadeamento`)
- **Efeito mecânico:** Recebe +2 se qualquer fileira estiver sob clima. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Sob os céus de Liurnia, uma astróloga procura nas estrelas sinais de destinos ainda ocultos.

### 026. Apóstolo da Pele Divina
- **ID:** `magia_sol_negro` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Corpo a corpo
- **Poder-base:** 8 · **Raridade:** Lendária · **Custo cadastrado:** 4
- **Habilidade:** Eclipse Devorador (`quebra_ritmo`)
- **Efeito mecânico:** Recebe +2 se houver uma unidade inimiga com bônus positivo. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** Devoto da antiga ordem da Pele Divina, empunha a chama negra associada à morte dos deuses.

### 027. Aprendiz de Feitiçaria Cariana
- **ID:** `magia_fagulha` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Um aprendiz da tradição cariana começa a dominar os projéteis de pedra cintilante.

### 028. Erudito da Academia
- **ID:** `magia_orbe_eco` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Longa distância
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Pesquisador de Raya Lucaria, dedica a vida ao estudo dos segredos das pedras cintilantes.

### 029. Feiticeira da Lua Gélida
- **ID:** `magia_chama_fria` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Longa distância
- **Poder-base:** 4 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Uma feiticeira errante combina o frio das antigas artes lunares com chamas de origem desconhecida.

### 030. Cavaleiros de Radahn
- **ID:** `covenant_lobos_cinza` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Veteranos da hoste do Flagelo das Estrelas, marcham sob o estandarte do general de Caelid.

### 031. Juramentada de Ranni
- **ID:** `covenant_lua_velada` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 6 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Aliança Lunar (`primeira_luz`)
- **Efeito mecânico:** Recebe +1 e concede +1 a uma unidade aliada em outra fileira. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Uma aliada juramentada à princesa lunar acompanha sua busca por um caminho além da Ordem Áurea.

### 032. Guardiões de Sellia
- **ID:** `covenant_sentinelas` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Vigias da cidade oculta de Sellia protegem seus segredos e as passagens de feitiçaria.

### 033. Cavaleiro da Dinastia Mohgwyn
- **ID:** `covenant_coroa_abismo` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 7 · **Raridade:** Lendária · **Custo cadastrado:** 4
- **Habilidade:** Selo Enfraquecedor (`drenagem`)
- **Efeito mecânico:** Reduz em 1 o bônus de todas as unidades inimigas, até o limite de -2. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** Um guerreiro jurado à dinastia sanguínea guarda os domínios ocultos de Mohg.

### 034. Cavaleiros de sangue juramentados
- **ID:** `covenant_ultimos` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Combatentes unidos por juramentos de sangue permanecem ao lado de seu senhor até o último fôlego.

### 035. Discípulos do Monge do Fogo
- **ID:** `covenant_filhos_brasa` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Seguidores dos antigos monges preservam a chama dos gigantes e seus rituais esquecidos.

### 036. Peregrinos da Cidade Eterna
- **ID:** `covenant_peregrinos_nevoa` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Viajantes das cidades subterrâneas cruzam a escuridão em busca de uma nova estrela.

### 037. Guardas da Árvore Áurea
- **ID:** `covenant_irmandade_ferro` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 4 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:** Retaliação dos Semideuses (`retaliacao`)
- **Efeito mecânico:** Recebe +1 de poder quando sua pontuação está abaixo da rival.
- **Descrição narrativa:** Defensores juramentados protegem os caminhos e santuários consagrados à Árvore Áurea.

### 038. Miasma da Podridão
- **ID:** `gwent_especial_nevoa` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Névoa de Sellia (`gwent_nevoa`)
- **Efeito mecânico:** Aplica 1 marca de Podridão Escarlate a todas as unidades inimigas da fileira escolhida; raridades Épica ou superiores aplicam uma segunda marca. Raridade Rara: pode aplicar uma segunda marca de Podridão Escarlate.
- **Descrição narrativa:** Uma nuvem pútrida se espalha pelo campo, lembrando os pântanos corrompidos de Caelid.

### 039. Geada dos Picos dos Gigantes
- **ID:** `gwent_especial_geada` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Lua Gélida (`gwent_geada`)
- **Efeito mecânico:** Aplica 1 marca de Geada a todas as unidades inimigas em campo; raridades Épica ou superiores aplicam uma segunda marca. Raridade Rara: pode aplicar uma segunda marca de Geada.
- **Descrição narrativa:** O frio dos Picos dos Gigantes avança sobre o campo e silencia o vigor dos combatentes.

### 040. Sangue Corrompido
- **ID:** `gwent_especial_chuva` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 0 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:** Chuva de Estrelas (`gwent_chuva`)
- **Efeito mecânico:** Aplica clima -2 à fileira de cerco: todas as unidades nela perdem 2 de poder efetivo até o fim da rodada.
- **Descrição narrativa:** Um rito sanguíneo mancha o campo de batalha com a promessa de uma dívida ainda não paga.

### 041. Rugido de Godfrey
- **ID:** `gwent_especial_chifre` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 0 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Rugido de Godfrey (`gwent_chifre`)
- **Efeito mecânico:** Concede +2 às suas unidades na fileira escolhida até o fim da rodada. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** O rugido do Primeiro Lorde Prístino ecoa entre as fileiras e reacende a coragem dos guerreiros.

### 042. Lágrima Sagrada
- **ID:** `gwent_especial_medico` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Lágrima Sagrada (`gwent_medico`)
- **Efeito mecânico:** Devolve à sua mão uma unidade do seu descarte com poder-base 4 ou menos; você pode escolher o alvo. Raridade Rara: recupera unidade com poder-base até 5.
- **Descrição narrativa:** Uma lágrima consagrada guarda a memória dos que tombaram e ainda podem retornar à jornada.

### 043. Chama Negra
- **ID:** `gwent_especial_queima` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Chama Negra (`gwent_queima`)
- **Efeito mecânico:** Tenta remover a unidade de maior poder efetivo de cada lado; um escudo pode bloquear cada remoção.
- **Descrição narrativa:** A chama negra, temida até pelos deuses, consome tudo o que toca.

### 044. Lei da Regressão
- **ID:** `gwent_especial_purificar` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Lei da Regressão (`gwent_purificar`)
- **Efeito mecânico:** Remove todos os efeitos climáticos.
- **Descrição narrativa:** A Lei da Regressão revela a verdade por trás das ilusões e desfaz os véus que encobrem o mundo.

### 045. Lâmina da Morte Destinada
- **ID:** `gwent_especial_execucao` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 0 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Lâmina da Morte Destinada (`gwent_execucao`)
- **Efeito mecânico:** Remove uma unidade inimiga escolhida da fileira selecionada se ela tiver poder efetivo 6 ou menos; um escudo pode bloquear a remoção. Raridade Épica: alcança poder efetivo até 6.
- **Descrição narrativa:** A lâmina da Morte Destinada carrega o fragmento de um poder que deveria permanecer selado.

### 046. Juramento do Crisol
- **ID:** `gwent_especial_vinculo` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Juramento do Crisol (`gwent_vinculo`)
- **Efeito mecânico:** Se houver ao menos duas unidades aliadas na fileira escolhida, concede +2 a todas elas até o fim da rodada. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Um juramento ancestral une os guerreiros às formas primordiais que precederam a Erdtree.

### 047. Passo do Cão de Caça
- **ID:** `gwent_especial_batedor` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Passo do Cão de Caça (`gwent_batedor`)
- **Efeito mecânico:** Compra uma carta da reserva, se disponível. Raridade Rara: compra até 2 cartas.
- **Descrição narrativa:** O passo do cão de caça atravessa o campo antes que o inimigo perceba sua aproximação.

### 048. Bastião de Leyndell
- **ID:** `gwent_especial_muralha` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 0 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:** Bastião de Leyndell (`gwent_muralha`)
- **Efeito mecânico:** Concede +1 às suas unidades na fileira escolhida até o fim da rodada.
- **Descrição narrativa:** As muralhas douradas de Leyndell erguem-se como símbolo da resistência da capital.

### 049. Ritual de Sangue
- **ID:** `elden_especial_sangramento` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Sangramento (`gwent_sangramento`)
- **Efeito mecânico:** Marca as unidades inimigas da fileira; a segunda marca reduz o bônus em 2 (mínimo -2) e consome as marcas. Marcas expiram no fim da rodada. Raridade Rara: aplica uma marca extra a até 1 alvo(s), podendo ativar hemorragia imediatamente.
- **Descrição narrativa:** O ritual desperta o poder do sangue e transforma cada ferida em um presságio de ruína.

### 050. Lua Cheia de Rennala
- **ID:** `elden_especial_geada` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Geada Cariana (`gwent_geada_cariana`)
- **Efeito mecânico:** Aplica até duas marcas às unidades inimigas da fileira escolhida; cada marca reduz 1 de poder efetivo até o fim da rodada. Raridade Rara: aplica uma segunda marca a até 1 alvo(s).
- **Descrição narrativa:** A lua cheia de Rennala ilumina o campo com a frieza ancestral da realeza cariana.

### 051. Flor da Podridão Escarlate
- **ID:** `elden_especial_podrida` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Podridão Escarlate (`gwent_podrida`)
- **Efeito mecânico:** Cada marca reduz 1 de poder efetivo; a segunda também corrói 1 ponto de bônus positivo, se houver. Marcas expiram no fim da rodada. Raridade Épica: pode aplicar a segunda marca imediatamente a até 2 alvo(s).
- **Descrição narrativa:** A flor escarlate floresce onde a podridão encontra carne, pedra e memória.

### 052. Chama Frenética
- **ID:** `elden_especial_loucura` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Loucura Frenética (`gwent_loucura`)
- **Efeito mecânico:** Cada marca reduz 1 de poder efetivo; a segunda remove todos os bônus positivos da unidade. Marcas expiram no fim da rodada. Raridade Épica: pode aplicar a segunda marca imediatamente a até 2 alvo(s).
- **Descrição narrativa:** A chama frenética consome razão e identidade, deixando apenas o caos da Chama Frenética.

### 053. Chama do Gigante
- **ID:** `elden_especial_chama` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Chama do Gigante (`gwent_chama`)
- **Efeito mecânico:** Remove Geada de todas as suas unidades; cada unidade purificada recebe +1 de poder até o fim da rodada. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** A chama dos gigantes arde contra o frio que tenta aprisionar os vivos.

### 054. Cinzas dos Lobos Solitários
- **ID:** `elden_especial_invocacao` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Cinzas dos Lobos Solitários (`gwent_invocacao`)
- **Efeito mecânico:** Invoca Lobos Espirituais com 3 de poder na fileira escolhida. Raridade Rara: invoca lobos com 4 de poder.
- **Descrição narrativa:** Cinzas antigas despertam os espíritos de lobos que outrora caçaram ao lado de seus mestres.

### 055. Grande Runa de Godrick
- **ID:** `reliquia_grande_runa_godrick` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 0 · **Raridade:** Lendária · **Custo cadastrado:** 3
- **Habilidade:** Grande Runa de Godrick (`reliquia_godrick`)
- **Efeito mecânico:** Exige ao menos uma unidade aliada em campo. Concede +1 de bônus a todas as unidades aliadas. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** Fragmento da ordem dourada reivindicado por Godrick, o Enxertado, em sua busca desesperada por grandeza.

### 056. Grande Runa dos Não Nascidos
- **ID:** `reliquia_runa_nao_nascidos` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Lendária · **Custo cadastrado:** 3
- **Habilidade:** Grande Runa dos Não Nascidos (`reliquia_renala`)
- **Efeito mecânico:** Remove Geada e Podridão das unidades aliadas afetadas; cada unidade purificada recebe +1 de bônus. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** A Grande Runa guardada por Rennala conserva o poder do renascimento e da perfeição inacabada.

### 057. Runa da Morte
- **ID:** `reliquia_runa_morte` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 0 · **Raridade:** Mítica · **Custo cadastrado:** 4
- **Habilidade:** Runa da Morte (`reliquia_morte`)
- **Efeito mecânico:** Em cada fileira, reduz em até 2 o bônus positivo da unidade inimiga que tiver o maior bônus naquela fileira. Potência Mítica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 4 dessas alterações por ativação.
- **Descrição narrativa:** O fragmento da Morte Destinada recorda o poder que Maliketh recebeu para manter selado.

### 058. Espada da Noite e da Chama
- **ID:** `reliquia_noite_chama` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Lendária · **Custo cadastrado:** 3
- **Habilidade:** Espada da Noite e da Chama (`reliquia_noite_chama`)
- **Efeito mecânico:** Na postura da Noite, aplica Geada a todas as unidades inimigas da fileira escolhida. Na postura da Chama, atinge a unidade de maior poder efetivo: reduz 1 de poder-base e 2 de bônus; Escudo bloqueia o golpe. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** Arma lendária que reúne a feitiçaria da noite e a chama dourada em duas posturas distintas.

### 059. Lâmina Negra
- **ID:** `reliquia_lamina_negra` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 0 · **Raridade:** Mítica · **Custo cadastrado:** 4
- **Habilidade:** Lâmina Negra (`reliquia_lamina_negra`)
- **Efeito mecânico:** Na fileira escolhida, reduz em 3 o bônus de uma unidade inimiga (a escolhida ou a de maior poder efetivo). Escudo bloqueia o efeito sem consumir a Relíquia. Potência Mítica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 4 dessas alterações por ativação.
- **Descrição narrativa:** Uma lâmina marcada pela Morte Destinada, associada aos assassinos que mudaram o destino dos semideuses.

### 060. Algemas de Margit
- **ID:** `reliquia_algemas_margit` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 0 · **Raridade:** Épica · **Custo cadastrado:** 2
- **Habilidade:** Algemas de Margit (`reliquia_algemas`)
- **Efeito mecânico:** Na fileira escolhida, zera o bônus positivo de uma unidade inimiga (a escolhida ou a de maior bônus); bônus negativos permanecem inalterados. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Correntes forjadas para conter o Agouro caído, capazes de subjugar até mesmo um inimigo temível.

### 061. Cavaleiro do Crisol
- **ID:** `gwent_unidade_baluarte` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Quanto maior a formação aliada, mais difícil é derrubá-lo.

### 062. Caçador de Dedos
- **ID:** `gwent_unidade_lamina_sem_juramento` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Ataca melhor quando opera sem apoio na fileira.

### 063. Porta-estandarte de Leyndell
- **ID:** `gwent_unidade_portaestandarte` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Fortalece as demais unidades aliadas na mesma fileira.

### 064. Profeta de Liurnia
- **ID:** `gwent_unidade_oraculo_clima` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Sua visão atravessa tempestades e geadas.

### 065. Erudito das Pedras Cintilantes
- **ID:** `gwent_unidade_eco` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Canaliza o poder das cartas especiais já utilizadas.

### 066. Cavaleira Cariana
- **ID:** `gwent_unidade_cavaleira` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Uma duelista que pune movimentos previsíveis.

### 067. Gigante de Fogo
- **ID:** `gwent_unidade_gigante` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 7 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Instinto de Caçador (`instinto`)
- **Efeito mecânico:** Recebe +2 quando sua pontuação está abaixo da rival. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Uma presença colossal na linha de frente.

### 068. Exploradora da Cidade Eterna
- **ID:** `gwent_unidade_cartografa` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Encontra rotas onde os outros veem obstáculos.

### 069. Apóstolo da Pele Divina Errante
- **ID:** `gwent_unidade_invocador` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 7 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Caçador de Feitiços (`cacador_arcano`)
- **Efeito mecânico:** Recebe +1 se o adversário controlar uma unidade da Lua Negra ou qualquer unidade com bônus positivo. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Converte conhecimento arcano em força de combate.

### 070. Mestre Ferreiro de Volcano Manor
- **ID:** `gwent_unidade_mestre_forja` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Luta melhor ao lado de outra unidade da Ordem Áurea.

### 071. Gêmeas da Cidade Eterna
- **ID:** `gwent_unidade_dupla_veu` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Coordena ataques com aliados posicionados em outra fileira.

### 072. Discípulo da Academia
- **ID:** `gwent_unidade_circulo` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Amplifica a magia quando encontra aliados ou resíduos arcanos.

### 073. Cavaleiro de Radahn
- **ID:** `gwent_unidade_sentinela_rubra` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Primeira a receber o golpe, última a recuar.

### 074. Cavaleiro Draconiano
- **ID:** `gwent_unidade_veterano_cercos` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Já viu mais muralhas caírem do que rostos conhecidos.

### 075. Godwyn, o Dourado
- **ID:** `gwent_unidade_herdeiro_portao` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Vingança (`vinganca`)
- **Efeito mecânico:** Ao cair, concede +1 às unidades aliadas da mesma fileira. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Quando cai, a formação inteira jura vingá-lo.

### 076. Carrasco de Volcano Manor
- **ID:** `gwent_unidade_carniceiro_forja` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 4 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Devorar (`devorar`)
- **Efeito mecânico:** Ao entrar, consome a unidade aliada de menor poder efetivo na mesma fileira e recebe bônus igual ao poder dela, até +4. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Consome os restos da batalha para ampliar a própria força.

### 077. Mercador Nômade
- **ID:** `gwent_unidade_intendente` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Longa distância
- **Poder-base:** 4 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Cada vitória enche os depósitos da Ordem.

### 078. Assassina de Ravenmount
- **ID:** `gwent_unidade_cacadora_fantasma` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Some na névoa e reaparece quando a próxima rodada começa.

### 079. Fia, Companheira do Leito de Morte
- **ID:** `gwent_unidade_cantora_lamentos` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 5 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Seu canto arrasta os caídos de volta ao campo.

### 080. Blaidd, o Meio-Lobo
- **ID:** `gwent_unidade_senhor_cacada` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Lua Negra · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Vingança (`vinganca`)
- **Efeito mecânico:** Ao cair, concede +1 às unidades aliadas da mesma fileira. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** A presa que o derruba desperta a matilha inteira.

### 081. Ladina da Cidade Eterna
- **ID:** `gwent_unidade_saqueadora_veu` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Nenhuma rota é cara demais para quem leva o butim.

### 082. Recusante da Mansão Vulcânica
- **ID:** `gwent_unidade_contrabandista` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Sempre tem um truque guardado para a primeira emboscada.

### 083. Guardião da Ordem Áurea
- **ID:** `gwent_unidade_guardiao_runas` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Runas gravadas na pele desviam o primeiro feitiço.

### 084. Servo dos que Vivem na Morte
- **ID:** `gwent_unidade_necromante` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 4 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Ressurgir (`ressurgir`)
- **Efeito mecânico:** Se houver uma unidade elegível, traz do descarte a mais forte com poder base 5 ou menos diretamente ao campo. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Desperta no campo os que o descarte ainda guarda.

### 085. Guerreiro da Chama Frenética
- **ID:** `gwent_unidade_detonador` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Vingança (`vinganca`)
- **Efeito mecânico:** Ao cair, concede +1 às unidades aliadas da mesma fileira. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Sua queda libera a energia que ele guardava.

### 086. Cavaleiro de Sangue de Mohg
- **ID:** `gwent_unidade_devorador_mana` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Corpo a corpo
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Consome aliados menores para alimentar o ritual de sangue.

### 087. Bibliotecária de Raya Lucaria
- **ID:** `gwent_unidade_bibliotecaria` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 5 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** O conhecimento reunido na guerra vale mais que ouro.

### 088. Bênção da Árvore Áurea
- **ID:** `gwent_especial_egide` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Bênção da Árvore Áurea (`gwent_egide`)
- **Efeito mecânico:** Concede escudo a uma unidade sua. Raridade Rara: protege até 2 unidades.
- **Descrição narrativa:** Concede escudo a uma unidade sua (a escolhida, ou a mais forte sem escudo).

### 089. Chamado dos Mortos
- **ID:** `gwent_especial_requiem` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 0 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Chamado dos Mortos (`gwent_requiem`)
- **Efeito mecânico:** Traz do descarte diretamente ao campo uma unidade com poder base 6 ou menos. Raridade Épica: recupera unidade com poder-base até 8.
- **Descrição narrativa:** Traz direto ao campo uma unidade com poder base 6 ou menos do seu descarte (a escolhida, ou a mais forte).

### 090. Passo do Lobo
- **ID:** `gwent_especial_passo` · **Origem:** Catálogo fixo
- **Categoria:** Especial · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 0 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Passo do Lobo (`gwent_passo`)
- **Efeito mecânico:** Move uma unidade sua para a fileira escolhida. Raridade Rara: move até 2 unidades.
- **Descrição narrativa:** Move uma unidade sua para a fileira escolhida (a escolhida, ou a mais fraca fora dela).

### 091. Cavaleiro Consagrado do Haligtree
- **ID:** `gwent_mitica_coroa` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 8 · **Raridade:** Mítica · **Custo cadastrado:** 5
- **Habilidade:** Estandarte (`estandarte`)
- **Efeito mecânico:** Concede +1 às outras unidades aliadas da mesma fileira. Potência Mítica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 4 dessas alterações por ativação.
- **Descrição narrativa:** Uma presença mítica que fortalece a formação aliada.

### 092. Juramento Primordial do Crisol
- **ID:** `gwent_singular_primeiro` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 10 · **Raridade:** Singular · **Custo cadastrado:** 0
- **Habilidade:** Caçador Solitário (`cacador_solitario`)
- **Efeito mecânico:** +2 se não houver outra unidade sua na fileira. Potência Singular: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 6 dessas alterações por ativação.
- **Descrição narrativa:** Exemplar singular conquistado por um feito extraordinário.

### 093. Adaga da Faca Negra
- **ID:** `gwent_singular_intocavel` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Corpo a corpo
- **Poder-base:** 9 · **Raridade:** Singular · **Custo cadastrado:** 0
- **Habilidade:** Mira Cariana (`precisao`)
- **Efeito mecânico:** Recebe +1 ao entrar na fileira de longa distância. Potência Singular: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 6 dessas alterações por ativação.
- **Descrição narrativa:** Conquistada ao concluir um desafio sem sofrer dano.

### 094. Vontade de Marika
- **ID:** `gwent_singular_nivel1` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 10 · **Raridade:** Singular · **Custo cadastrado:** 0
- **Habilidade:** Último Suspiro (`ultimo_folego`)
- **Efeito mecânico:** Recebe +1 de poder na terceira rodada. Potência Singular: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 6 dessas alterações por ativação.
- **Descrição narrativa:** Conquistada ao vencer um desafio no nível um.

### 095. Coroa do Lorde Prístino
- **ID:** `gwent_singular_cacador_chefes` · **Origem:** Catálogo fixo
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Corpo a corpo
- **Poder-base:** 9 · **Raridade:** Singular · **Custo cadastrado:** 0
- **Habilidade:** Paradoxo Eterno (`paradoxo_eterno`)
- **Efeito mecânico:** Recebe +2 na terceira rodada se o adversário venceu a segunda. Potência Singular: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 6 dessas alterações por ativação.
- **Descrição narrativa:** Conquistada ao derrotar todos os chefes de um desafio.

### 096. Besta Prístina, Arauto da Vontade Maior
- **ID:** `primordial_origem` · **Origem:** Carta primordial
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Cerco
- **Poder-base:** 8 · **Raridade:** Primordial · **Custo cadastrado:** 4
- **Habilidade:** Lei Primeva (`lei_primeva`)
- **Efeito mecânico:** Recebe +2 de poder ao entrar na primeira rodada. Potência Primordial: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 5 dessas alterações por ativação.
- **Descrição narrativa:** A Besta Prístina manifesta a vontade que veio além das estrelas e deu forma à ordem dourada.

### 097. Marika, Rainha Eterna
- **ID:** `primordial_trono` · **Origem:** Carta primordial
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 8 · **Raridade:** Primordial · **Custo cadastrado:** 4
- **Habilidade:** Decreto Soberano (`decreto_soberano`)
- **Efeito mecânico:** Reduz em 2 o bônus de todas as unidades inimigas, até o limite de -2. Potência Primordial: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 5 dessas alterações por ativação.
- **Descrição narrativa:** Marika, a Rainha Eterna, ergueu a ordem dourada e rompeu o Anel Prístino, mudando para sempre as Terras Intermédias.

### 098. Placidusax, Senhor Dragão
- **ID:** `primordial_tempestade` · **Origem:** Carta primordial
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Cerco
- **Poder-base:** 8 · **Raridade:** Primordial · **Custo cadastrado:** 4
- **Habilidade:** Olho da Tempestade (`olho_tempestade`)
- **Efeito mecânico:** Recebe +2 quando sua fileira estiver sob efeito climático. Potência Primordial: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 5 dessas alterações por ativação.
- **Descrição narrativa:** Placidusax, antigo lorde dos dragões, permanece suspenso no tempo em Farum Azula.

### 099. Mãe Sem Forma
- **ID:** `primordial_abismo` · **Origem:** Carta primordial
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Cerco
- **Poder-base:** 8 · **Raridade:** Primordial · **Custo cadastrado:** 4
- **Habilidade:** Fome do Abismo (`fome_abismo`)
- **Efeito mecânico:** Recebe +2 quando sua pontuação está abaixo da rival. Potência Primordial: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 5 dessas alterações por ativação.
- **Descrição narrativa:** A Mãe Sem Forma é venerada pelos seguidores de Mohg como origem do poder sanguíneo.

### 100. Maliketh, Guardião da Morte Destinada
- **ID:** `primordial_eternidade` · **Origem:** Carta primordial
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 8 · **Raridade:** Primordial · **Custo cadastrado:** 4
- **Habilidade:** Paradoxo Eterno (`paradoxo_eterno`)
- **Efeito mecânico:** Recebe +2 na terceira rodada se o adversário venceu a segunda. Potência Primordial: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 5 dessas alterações por ativação.
- **Descrição narrativa:** Maliketh guarda a Morte Destinada, o poder cuja ausência sustenta a ordem sem morte de Marika.

### 101. Novato de Raya Lucaria da Graça Perdida
- **ID:** `patente_1` · **Origem:** Patente gerada deterministicamente
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 3 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:** Caçador de Feitiços (`cacador_arcano`)
- **Efeito mecânico:** Recebe +1 se o adversário controlar uma unidade da Lua Negra ou qualquer unidade com bônus positivo.
- **Descrição narrativa:** Recompensa de progressão nas Terras Intermédias — nível 1.

### 102. Novato de Raya Lucaria do Palácio de Mohgwyn
- **ID:** `patente_2` · **Origem:** Patente gerada deterministicamente
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 3 · **Raridade:** Comum · **Custo cadastrado:** 1
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial.
- **Descrição narrativa:** Recompensa de progressão nas Terras Intermédias — nível 5.

### 103. Aprendiz Cariano das Ruínas de Farum Azula
- **ID:** `patente_3` · **Origem:** Patente gerada deterministicamente
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Recompensa de progressão nas Terras Intermédias — nível 10.

### 104. Escudeiro de Leyndell da Graça Perdida
- **ID:** `patente_4` · **Origem:** Patente gerada deterministicamente
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:**  (`sem habilidade`)
- **Efeito mecânico:** Sem habilidade especial. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Recompensa de progressão nas Terras Intermédias — nível 15.

### 105. Acólito Sanguíneo da Noite dos Punhais
- **ID:** `patente_5` · **Origem:** Patente gerada deterministicamente
- **Categoria:** Unidade · **Tipo mecânico:** Destreza · **Facção do jogo:** Véu Carmesim · **Fileira:** Longa distância
- **Poder-base:** 6 · **Raridade:** Rara · **Custo cadastrado:** 2
- **Habilidade:** Postura Encadeada (`encadeamento`)
- **Efeito mecânico:** Recebe +2 ao jogar na mesma fileira da sua unidade anterior. Potência Rara: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 1 dessas alterações por ativação.
- **Descrição narrativa:** Recompensa de progressão nas Terras Intermédias — nível 20.

### 106. Veterano de Leyndell das Ruínas de Farum Azula
- **ID:** `patente_6` · **Origem:** Patente gerada deterministicamente
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Retaliação dos Semideuses (`retaliacao`)
- **Efeito mecânico:** Recebe +1 de poder quando sua pontuação está abaixo da rival. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Recompensa de progressão nas Terras Intermédias — nível 30.

### 107. Feiticeiro Cariano do Palácio de Mohgwyn
- **ID:** `patente_7` · **Origem:** Patente gerada deterministicamente
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 7 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Caçador de Feitiços (`cacador_arcano`)
- **Efeito mecânico:** Recebe +1 se o adversário controlar uma unidade da Lua Negra ou qualquer unidade com bônus positivo. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Recompensa de progressão nas Terras Intermédias — nível 40.

### 108. Veterano de Leyndell do Palácio de Mohgwyn
- **ID:** `patente_8` · **Origem:** Patente gerada deterministicamente
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 5 · **Raridade:** Épica · **Custo cadastrado:** 3
- **Habilidade:** Retaliação dos Semideuses (`retaliacao`)
- **Efeito mecânico:** Recebe +1 de poder quando sua pontuação está abaixo da rival. Potência Épica: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 2 dessas alterações por ativação.
- **Descrição narrativa:** Recompensa de progressão nas Terras Intermédias — nível 50.

### 109. Lorde de Leyndell da Lua Negra
- **ID:** `patente_9` · **Origem:** Patente gerada deterministicamente
- **Categoria:** Unidade · **Tipo mecânico:** Força · **Facção do jogo:** Ordem Áurea · **Fileira:** Corpo a corpo
- **Poder-base:** 8 · **Raridade:** Lendária · **Custo cadastrado:** 4
- **Habilidade:** Ímpeto do Lorde (`impeto`)
- **Efeito mecânico:** Recebe +1 de poder quando sua pontuação está acima da rival. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** Recompensa de progressão nas Terras Intermédias — nível 75.

### 110. Mestre Cariano da Graça Perdida
- **ID:** `patente_10` · **Origem:** Patente gerada deterministicamente
- **Categoria:** Unidade · **Tipo mecânico:** Magia · **Facção do jogo:** Lua Negra · **Fileira:** Cerco
- **Poder-base:** 6 · **Raridade:** Lendária · **Custo cadastrado:** 4
- **Habilidade:** Ruptura de Postura (`quebra_ritmo`)
- **Efeito mecânico:** Recebe +1 se o adversário jogou na mesma fileira em seu último turno. Potência Lendária: quando esta habilidade altera bônus, amplia em 1 ponto cada uma de até 3 dessas alterações por ativação.
- **Descrição narrativa:** Recompensa de progressão nas Terras Intermédias — nível 100.

## Observações de cânone e autoria

- Ranni e Blaidd foram descritos dentro da relação de princesa lunar e sombra/vassalo; Godwyn foi associado à Noite das Facas Negras e à condição de Príncipe da Morte; Godfrey à posição de Primeiro Lorde Prístino; Gurranq à Raiz da Morte e ao segredo de Maliketh; Malenia à Podridão Escarlate; Radahn ao domínio da gravidade; Maliketh à guarda da Runa da Morte; Messmer à purga do Reino das Sombras; Placidusax à espera em Farum Azula.
- O material oficial de Bandai Namco confirma o vínculo de Messmer com a purga do Reino das Sombras e sua chama. Os demais resumos de lore foram conferidos com páginas de referência da Eldenpedia (wiki comunitária, não fonte oficial).
- Cartas como “Duelista da Casa Hoslow”, “Espadachim da Lua Negra”, “Lâmina Negra Errante”, “Dragoeiro Ancião” e diversos Covenants são arquétipos ou adaptações internas. A descrição foi escrita como ambientação autoral, sem afirmar que sejam NPCs oficiais.
- A classificação de facção é uma camada de balanceamento e identidade visual do NARABOT. Não foi alterada em massa porque isso poderia mudar a leitura estratégica de decks e não há uma regra canônica de três facções equivalente no jogo original.

## Fontes de referência

- [Eldenpedia — Lore](https://eldenring.wiki.gg/wiki/Lore)
- [Eldenpedia — Characters](https://eldenring.wiki.gg/wiki/Characters)
- [Eldenpedia — Ranni the Witch](https://eldenring.wiki.gg/wiki/Ranni_the_Witch)
- [Eldenpedia — Godwyn the Golden](https://eldenring.wiki.gg/wiki/Godwyn)
- [Bandai Namco — Shadow of the Erdtree product information](https://www.bandainamcoent.co.jp/pdfs/20240627_EN.pdf)

## Validação

- 8 testes focados de qualidade do catálogo passaram.
- 59 testes no total passaram ao executar a suíte excluindo o módulo de renderização pesada de molduras (os 8 testes focados estão incluídos nesses 59).
- A suíte integral não terminou dentro do limite de execução porque o módulo `test_molduras_faccoes` ficou em execução; por isso não declaro 100% da suíte integral aprovada.
- Os testes confirmam 110/110 descrições narrativas não vazias, texto de habilidade exclusivo correto em jogo e arte, texto de Relíquias recuperado e descrições de Névoa/Geada coerentes com os handlers.
