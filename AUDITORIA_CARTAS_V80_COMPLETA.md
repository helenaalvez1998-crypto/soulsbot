# Auditoria completa de cartas — V80

## Escopo e método

Foram conferidos **122 registros estáticos** do catálogo: 95 cartas principais, 12 cartas da expansão V75, 5 cartas Primordiais e 10 recompensas de patente.

Para cada carta, a ficha efetiva foi obtida por `preparar_carta`, a mesma camada usada pelo jogo e pelo gerador de arte. Assim, o texto registrado abaixo não mostra uma habilidade genérica escondida quando uma habilidade de identidade a substitui.

Os campos foram mantidos separados: **efeito de combate**, **bônus de raridade**, **história/lore** e **combos compatíveis**. A história não serve como instrução de jogo; as regras ficam no campo de efeito.

Foram ainda exercitados **60 exemplos de recompensas dinâmicas** (30 nomes de jogos × marcos `zerado` e `platina`) para verificar a separação entre descrição narrativa e habilidade gerada. Isso é uma amostra do gerador, não uma enumeração de todos os títulos possíveis.

## Como ler as fichas

- **Poder-base** é o valor inicial impresso na carta; não é somado pela raridade.
- **Bônus da raridade** é mostrado em campo separado e descreve o que o código realmente reforça ou limita para aquela carta.
- **Sem habilidade individual** significa que a carta não executa um efeito sozinha; ela pode funcionar em um dos combos listados.
- **Sem habilidade especial** significa que não há efeito de combate individual nem combo listado para a carta.

---

## Cartas do catálogo principal

### 1. Cavaleiro da Árvore Áurea

- **ID:** `chefe_guardiao_cinzas`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Rara / 2
- **Habilidade:** Égide das Cinzas
- **O que faz:** Ao entrar, esta carta e o primeiro aliado da mesma fileira ganham +1 de bônus. Sem aliado, ela não ganha bônus.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um sentinela montado patrulha os caminhos que conduzem à Árvore Áurea, impondo a autoridade da capital.
- **Combos possíveis:**
  - **Aliança da Árvore Áurea** — Cavaleiro da Árvore Áurea ou Cavaleiros de Radahn e uma unidade da Fornalha coordenam a formação (+2).
  - **Juramento da Árvore Áurea** — Duas unidades da Ordem Áurea reforçam a formação: +2 para quem completa o combo e +1 aos aliados da mesma fileira.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 2. Ranni, Bruxa da Lua

- **ID:** `chefe_dama_vazio`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 6 / Épica / 3
- **Habilidade:** Fenda do Vazio
- **O que faz:** Ao entrar, tira 2 pontos do bônus do inimigo mais forte do campo. O bônus dele não pode ficar abaixo de -2.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** A princesa lunar rompeu com os Dois Dedos e busca um destino independente da Vontade Maior.
- **Combos possíveis:**
  - **Alinhamento Astral** — Ranni e uma unidade Astral convergem (+2).
  - **Convergência da Lua Negra** — Duas unidades ligadas à Lua Negra convergem e recebem +2.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 3. Cavaleiro do Cão de Caça

- **ID:** `chefe_cervo_sombrio`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Um cavaleiro errante segue a trilha de presas pelas florestas enevoadas das Terras Intermédias.
- **Combos possíveis:**
  - **Caçada da Faca Negra** — Duas unidades do Véu Sombrio entram em sintonia (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 4. Godfrey, Primeiro Lorde Prístino

- **ID:** `chefe_rei_afogado`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 7 / Épica / 3
- **Habilidade:** Dízimo do Abismo
- **O que faz:** Se houver uma unidade no seu descarte, ganha +2 de bônus. Se o descarte estiver vazio, ganha +1 apenas se o inimigo tiver mais unidades em campo.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Primeiro Lorde Prístino e consorte de Marika, Godfrey liderou os guerreiros que conquistaram as Terras Intermédias.
- **Combos possíveis:**
  - **Maré Abissal** — Godfrey e Cavaleiro Carmesim despertam a mesma força (+2).
  - **Ritual do Véu Carmesim** — Duas unidades do Véu Carmesim fortalecem a carta que completa o ritual (+2) e os aliados na fileira (+1).
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 5. Gurranq, Clérigo Bestial

- **ID:** `chefe_oraculo_ruina`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 7 / Lendária / 4
- **Habilidade:** Presságio da Ruína
- **O que faz:** Tira 1 ponto do bônus do inimigo mais forte. Se sua equipe estiver perdendo, esta carta também ganha +1 de bônus.
- **Bônus da raridade:** Raridade Lendária: pode reforçar o bônus de até 2 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** O clérigo bestial consome Raiz da Morte e guarda um segredo ligado à própria Runa da Morte.
- **Combos possíveis:** nenhum combo cadastrado.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 6. Assassina da Faca Negra

- **ID:** `chefe_cacador_sem_rosto`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Uma assassina Numen ligada à Noite das Facas Negras, quando um fragmento da Runa da Morte foi usado para matar Godwyn.
- **Combos possíveis:** nenhum combo cadastrado.

### 7. Cavaleiro de Leyndell

- **ID:** `chefe_vigia_cinzento`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Um soldado da capital mantém a vigília entre as muralhas erguidas em nome da Ordem Áurea.
- **Combos possíveis:** nenhum combo cadastrado.

### 8. Lâmina Negra Errante

- **ID:** `chefe_aparicao_veio`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 4 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Uma figura encapuzada atravessa as sombras, deixando apenas o rumor de uma lâmina silenciosa.
- **Combos possíveis:**
  - **Caçada da Faca Negra** — Duas unidades do Véu Sombrio entram em sintonia (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 9. Malenia, Lâmina de Miquella

- **ID:** `chefe_malenia_lamina_miquella`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 9 / Primordial / 4
- **Habilidade:** Flor Escarlate
- **O que faz:** Aplica Podridão Escarlate a todos os inimigos desta fileira. Cada marca reduz o poder atual em 1. Com 2 marcas, também tira 1 ponto do bônus positivo. As marcas somem no fim da rodada.
- **Bônus da raridade:** Raridade Primordial: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Espadachim lendária e irmã gêmea de Miquella, luta enquanto a Podridão Escarlate consome seu corpo.
- **Combos possíveis:** nenhum combo cadastrado.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 10. Radahn, Flagelo das Estrelas

- **ID:** `chefe_radahn_flagelo_estrelas`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 9 / Primordial / 4
- **Habilidade:** Gravidade do Flagelo
- **O que faz:** Ao entrar, move o inimigo mais forte para esta fileira e tira 2 pontos do bônus dele (até -2).
- **Bônus da raridade:** Raridade Primordial: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** General temido da Fragmentação, dominou a gravidade para deter o curso das estrelas e permaneceu em Caelid após a Podridão.
- **Combos possíveis:** nenhum combo cadastrado.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 11. Maliketh, Lâmina Negra

- **ID:** `chefe_maliketh_morte_destinada`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 8 / Lendária / 4
- **Habilidade:** Morte Destinada
- **O que faz:** Ao entrar, tira 2 pontos do bônus do inimigo mais forte do campo. O bônus dele não pode ficar abaixo de -2.
- **Bônus da raridade:** Raridade Lendária: pode reforçar o bônus de até 2 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Sombra leal de Marika e guardião da Runa da Morte, carrega a Morte Destinada selada em sua lâmina.
- **Combos possíveis:** nenhum combo cadastrado.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 12. Messmer, o Empalador

- **ID:** `chefe_messmer_impalador`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 8 / Lendária / 4
- **Habilidade:** Lança do Impalador
- **O que faz:** Aplica Sangramento a todos os inimigos desta fileira. A segunda marca causa Hemorragia: tira 2 pontos do bônus (até -2) e apaga as marcas. As marcas restantes somem no fim da rodada.
- **Bônus da raridade:** Raridade Lendária: pode reforçar o bônus de até 2 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Filho de Marika e senhor da chama impura, comandou a purga que devastou o Reino das Sombras.
- **Combos possíveis:** nenhum combo cadastrado.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 13. Placidusax, Lorde Dragão

- **ID:** `chefe_placidusax_lorde_dragao`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 9 / Primordial / 4
- **Habilidade:** Tempestade do Tempo
- **O que faz:** Aplica Geada a todos os inimigos desta fileira. Cada marca reduz o poder atual em 1 nesta rodada. Esta carta ganha +1 de bônus por inimigo atingido, até +3.
- **Bônus da raridade:** Raridade Primordial: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Lorde Dragão ancestral que aguarda, em Farum Azula, o retorno de seu deus desaparecido.
- **Combos possíveis:** nenhum combo cadastrado.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 14. Duelista da Casa Hoslow

- **ID:** `arma_lamina_peregrino`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Herdeiro de uma casa de duelistas, transforma a elegância do aço em uma promessa de sangue.
- **Combos possíveis:**
  - **Caminho do Maculado** — Duelista e Batedor da Mansão Vulcânica coordenam o avanço (+1).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 15. Ferreiro de Volcano Manor

- **ID:** `arma_martelo_fornalha`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Entre fornalhas e juramentos de traição, um artesão molda armas para os recusantes do Monte Gelmir.
- **Combos possíveis:** nenhum combo cadastrado.

### 16. Feiticeiro Cariano

- **ID:** `arma_cajado_marulho`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Longa distância
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Discípulo da realeza cariana, conjura feitiçarias de pedra cintilante sob a proteção da lua.
- **Combos possíveis:** nenhum combo cadastrado.

### 17. Espadachim da Lua Negra

- **ID:** `arma_duas_luas`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Lua Negra / Corpo a corpo
- **Poder-base / raridade / custo:** 7 / Épica / 3
- **Habilidade:** Dança Espelhada
- **O que faz:** Ganha +1 de bônus se já houver outro aliado seu em uma fileira diferente.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um duelista das tradições carianas conduz a lâmina sob a luz fria da Lua Negra.
- **Combos possíveis:**
  - **Dança da Lua Negra** — Dançarina, Gêmea ou Cartógrafa sincronizam seus movimentos (+2).
  - **Convergência da Lua Negra** — Duas unidades ligadas à Lua Negra convergem e recebem +2.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 18. Sentinela do Portão de Leyndell

- **ID:** `arma_grande_sino`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 8 / Lendária / 4
- **Habilidade:** Sino do Último Bastião
- **O que faz:** Ganha +2 de bônus se sua equipe estiver perdendo quando esta carta entrar.
- **Bônus da raridade:** Raridade Lendária: pode reforçar o bônus de até 2 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um guardião de elite protege os acessos da capital e enfrenta qualquer ameaça à ordem dourada.
- **Combos possíveis:** nenhum combo cadastrado.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 19. Leitora de Estrelas de Sellia

- **ID:** `arma_agulha_astro`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Longa distância
- **Poder-base / raridade / custo:** 4 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Uma estudiosa de Sellia observa os astros e procura caminhos ocultos na feitiçaria noturna.
- **Combos possíveis:**
  - **Alinhamento Astral** — Ranni e uma unidade Astral convergem (+2).
  - **Eco das Pedras Cintilantes** — O Erudito das Pedras Cintilantes e uma unidade Astral amplificam a mesma magia (+2).
  - **Convergência da Lua Negra** — Duas unidades ligadas à Lua Negra convergem e recebem +2.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 20. Lanceiro da Árvore Áurea

- **ID:** `arma_lanca_fornalha`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Treinado para defender os domínios da Árvore Áurea, avança com lança e disciplina militar.
- **Combos possíveis:** nenhum combo cadastrado.

### 21. Batedor da Mansão Vulcânica

- **ID:** `arma_arco_peregrino`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Um recusante percorre os caminhos do Monte Gelmir, atento às rotas e aos movimentos dos inimigos.
- **Combos possíveis:**
  - **Caminho do Maculado** — Duelista e Batedor da Mansão Vulcânica coordenam o avanço (+1).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 22. Monge do Fogo

- **ID:** `magia_brasa_errante`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Corpo a corpo
- **Poder-base / raridade / custo:** 4 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Devoto do fogo dos gigantes, preserva ritos antigos nas encostas geladas dos Picos dos Gigantes.
- **Combos possíveis:**
  - **Chamas do Monte Gelmir** — Piromante e Feiticeira da Lua Gélida equilibram suas chamas (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 23. Confessora da Ordem Áurea

- **ID:** `magia_selo_vigilia`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Rara / 2
- **Habilidade:** Selo de Vigília
- **O que faz:** O clima tira 1 ponto a menos desta carta. O primeiro aliado que já esteja na mesma fileira também ganha +1 de bônus.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Treinada para agir discretamente, a Confessora combina devoção, infiltração e combate próximo.
- **Combos possíveis:** nenhum combo cadastrado.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 24. Dragoeiro Ancião

- **ID:** `magia_trovao_oco`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Longa distância
- **Poder-base / raridade / custo:** 6 / Épica / 3
- **Habilidade:** Descarga Oca
- **O que faz:** Tira 1 ponto do bônus de cada inimigo nesta fileira. Nenhum bônus pode ficar abaixo de -2.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um guerreiro ligado aos antigos dragões canaliza relâmpagos ancestrais em meio à batalha.
- **Combos possíveis:** nenhum combo cadastrado.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 25. Astróloga de Liurnia

- **ID:** `magia_nevoa_antiga`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 7 / Épica / 3
- **Habilidade:** Névoa Ancestral
- **O que faz:** Ganha +2 de bônus se houver clima ativo em qualquer fileira.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Sob os céus de Liurnia, uma astróloga procura nas estrelas sinais de destinos ainda ocultos.
- **Combos possíveis:**
  - **Alinhamento Astral** — Ranni e uma unidade Astral convergem (+2).
  - **Eco das Pedras Cintilantes** — O Erudito das Pedras Cintilantes e uma unidade Astral amplificam a mesma magia (+2).
  - **Convergência da Lua Negra** — Duas unidades ligadas à Lua Negra convergem e recebem +2.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 26. Apóstolo da Pele Divina

- **ID:** `magia_sol_negro`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 8 / Lendária / 4
- **Habilidade:** Eclipse Devorador
- **O que faz:** Ganha +2 de bônus se pelo menos um inimigo tiver bônus acima de 0.
- **Bônus da raridade:** Raridade Lendária: pode reforçar o bônus de até 2 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Devoto da antiga ordem da Pele Divina, empunha a chama negra associada à morte dos deuses.
- **Combos possíveis:** nenhum combo cadastrado.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 27. Aprendiz de Feitiçaria Cariana

- **ID:** `magia_fagulha`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Lua Negra / Longa distância
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Um aprendiz da tradição cariana começa a dominar os projéteis de pedra cintilante.
- **Combos possíveis:** nenhum combo cadastrado.

### 28. Erudito da Academia

- **ID:** `magia_orbe_eco`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Longa distância
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Pesquisador de Raya Lucaria, dedica a vida ao estudo dos segredos das pedras cintilantes.
- **Combos possíveis:**
  - **Eco das Pedras Cintilantes** — O Erudito das Pedras Cintilantes e uma unidade Astral amplificam a mesma magia (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 29. Feiticeira da Lua Gélida

- **ID:** `magia_chama_fria`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Longa distância
- **Poder-base / raridade / custo:** 4 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Uma feiticeira errante combina o frio das antigas artes lunares com chamas de origem desconhecida.
- **Combos possíveis:**
  - **Chamas do Monte Gelmir** — Piromante e Feiticeira da Lua Gélida equilibram suas chamas (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 30. Cavaleiros de Radahn

- **ID:** `covenant_lobos_cinza`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Veteranos da hoste do Flagelo das Estrelas, marcham sob o estandarte do general de Caelid.
- **Combos possíveis:**
  - **Aliança da Árvore Áurea** — Cavaleiro da Árvore Áurea ou Cavaleiros de Radahn e uma unidade da Fornalha coordenam a formação (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 31. Juramentada de Ranni

- **ID:** `covenant_lua_velada`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Lua Negra / Longa distância
- **Poder-base / raridade / custo:** 6 / Épica / 3
- **Habilidade:** Aliança Lunar
- **O que faz:** Esta carta sempre ganha +1 de bônus. O aliado mais fraco em outra fileira também ganha +1, se houver.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Uma aliada juramentada à princesa lunar acompanha sua busca por um caminho além da Ordem Áurea.
- **Combos possíveis:**
  - **Dança da Lua Negra** — Dançarina, Gêmea ou Cartógrafa sincronizam seus movimentos (+2).
  - **Convergência da Lua Negra** — Duas unidades ligadas à Lua Negra convergem e recebem +2.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 32. Guardiões de Sellia

- **ID:** `covenant_sentinelas`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Vigias da cidade oculta de Sellia protegem seus segredos e as passagens de feitiçaria.
- **Combos possíveis:** nenhum combo cadastrado.

### 33. Cavaleiro da Dinastia Mohgwyn

- **ID:** `covenant_coroa_abismo`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 7 / Lendária / 4
- **Habilidade:** Selo Enfraquecedor
- **O que faz:** Ao entrar, tira 1 ponto do bônus de cada inimigo. O bônus não pode ficar abaixo de -2.
- **Bônus da raridade:** Raridade Lendária: pode reforçar o bônus de até 2 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um guerreiro jurado à dinastia sanguínea guarda os domínios ocultos de Mohg.
- **Combos possíveis:**
  - **Maré Abissal** — Godfrey e Cavaleiro Carmesim despertam a mesma força (+2).
  - **Ritual do Véu Carmesim** — Duas unidades do Véu Carmesim fortalecem a carta que completa o ritual (+2) e os aliados na fileira (+1).

### 34. Cavaleiros de sangue juramentados

- **ID:** `covenant_ultimos`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Combatentes unidos por juramentos de sangue permanecem ao lado de seu senhor até o último fôlego.
- **Combos possíveis:** nenhum combo cadastrado.

### 35. Discípulos do Monge do Fogo

- **ID:** `covenant_filhos_brasa`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Seguidores dos antigos monges preservam a chama dos gigantes e seus rituais esquecidos.
- **Combos possíveis:** nenhum combo cadastrado.

### 36. Peregrinos da Cidade Eterna

- **ID:** `covenant_peregrinos_nevoa`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Lua Negra / Longa distância
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Viajantes das cidades subterrâneas cruzam a escuridão em busca de uma nova estrela.
- **Combos possíveis:** nenhum combo cadastrado.

### 37. Guardas da Árvore Áurea

- **ID:** `covenant_irmandade_ferro`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 4 / Comum / 1
- **Habilidade:** Retaliação dos Semideuses
- **O que faz:** Se sua equipe estiver perdendo quando esta carta entrar, ganha +1 de bônus.
- **Bônus da raridade:** Raridade Comum: não reforça os efeitos de bônus desta carta.
- **História (lore):** Defensores juramentados protegem os caminhos e santuários consagrados à Árvore Áurea.
- **Combos possíveis:**
  - **Juramento de Leyndell** — Porta-estandarte e Guardas da Árvore Áurea fortalecem a formação (+1 para a carta que completa e +1 aos aliados na mesma fileira).

### 38. Miasma da Podridão

- **ID:** `gwent_especial_nevoa`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Névoa de Sellia
- **O que faz:** Escolha a fileira desejada. Todos os inimigos da fileira escolhida recebem Podridão Escarlate. Cada marca reduz o poder atual em 1 até o fim da rodada.
- **Bônus da raridade:** Raridade Rara: cada inimigo atingido recebe 1 marca de Podridão Escarlate. A partir da Lendária, recebe até 2.
- **História (lore):** Uma nuvem pútrida se espalha pelo campo, lembrando os pântanos corrompidos de Caelid.
- **Combos possíveis:** nenhum combo cadastrado.

### 39. Geada dos Picos dos Gigantes

- **ID:** `gwent_especial_geada`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Lua Gélida
- **O que faz:** Todos os inimigos em campo recebem 1 marca de Geada. Cada marca reduz o poder atual em 1 até o fim da rodada.
- **Bônus da raridade:** Raridade Rara: cada inimigo atingido recebe 1 marca de Geada. A partir da Lendária, recebe até 2.
- **História (lore):** O frio dos Picos dos Gigantes avança sobre o campo e silencia o vigor dos combatentes.
- **Combos possíveis:** nenhum combo cadastrado.

### 40. Sangue Corrompido

- **ID:** `gwent_especial_chuva`
- **Categoria / tipo:** Especial / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 0 / Comum / 1
- **Habilidade:** Sangue Corrompido
- **O que faz:** Todos os inimigos em Cerco recebem Sangramento. A segunda marca causa Hemorragia: tira 2 pontos do bônus (até -2) e apaga as marcas. As marcas restantes somem no fim da rodada.
- **Bônus da raridade:** Raridade Comum: não reforça os efeitos de bônus desta carta.
- **História (lore):** Um rito sanguíneo mancha o campo de batalha com a promessa de uma dívida ainda não paga.
- **Combos possíveis:** nenhum combo cadastrado.

### 41. Rugido de Godfrey

- **ID:** `gwent_especial_chifre`
- **Categoria / tipo:** Especial / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 0 / Épica / 3
- **Habilidade:** Rugido de Godfrey
- **O que faz:** Escolha uma fileira. Todos os seus aliados nela ganham +2 de bônus nesta rodada.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** O rugido do Primeiro Lorde Prístino ecoa entre as fileiras e reacende a coragem dos guerreiros.
- **Combos possíveis:** nenhum combo cadastrado.

### 42. Lágrima Sagrada

- **ID:** `gwent_especial_medico`
- **Categoria / tipo:** Especial / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Lágrima Sagrada
- **O que faz:** Escolha uma unidade do seu descarte para colocá-la na sua mão.
- **Bônus da raridade:** Raridade Rara: permite recuperar unidades com poder-base de até 5.
- **História (lore):** Uma lágrima consagrada guarda a memória dos que tombaram e ainda podem retornar à jornada.
- **Combos possíveis:** nenhum combo cadastrado.

### 43. Chama Negra

- **ID:** `gwent_especial_queima`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Épica / 3
- **Habilidade:** Chama Negra
- **O que faz:** Remove a unidade mais forte de cada lado do campo. Se ela tiver escudo, perde o escudo e continua em campo.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** A chama negra, temida até pelos deuses, consome tudo o que toca.
- **Combos possíveis:** nenhum combo cadastrado.

### 44. Lei da Regressão

- **ID:** `gwent_especial_purificar`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Lei da Regressão
- **O que faz:** Acaba com o clima nas três fileiras. Não remove as marcas de Geada, Sangramento, Podridão ou Loucura das unidades.
- **Bônus da raridade:** Raridade Rara: não altera o efeito desta carta.
- **História (lore):** A Lei da Regressão revela a verdade por trás das ilusões e desfaz os véus que encobrem o mundo.
- **Combos possíveis:** nenhum combo cadastrado.

### 45. Lâmina da Morte Destinada

- **ID:** `gwent_especial_execucao`
- **Categoria / tipo:** Especial / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 0 / Épica / 3
- **Habilidade:** Lâmina da Morte Destinada
- **O que faz:** Escolha uma fileira e remova 1 inimigo com poder atual de até 6. Se ele tiver escudo, perde o escudo e continua em campo.
- **Bônus da raridade:** Raridade Épica: o alvo continua limitado a 6 de poder atual. Se a unidade removida ativar Vingança, a raridade também pode reforçar até 1 bônus dessa reação.
- **História (lore):** A lâmina da Morte Destinada carrega o fragmento de um poder que deveria permanecer selado.
- **Combos possíveis:** nenhum combo cadastrado.

### 46. Juramento do Crisol

- **ID:** `gwent_especial_vinculo`
- **Categoria / tipo:** Especial / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Juramento do Crisol
- **O que faz:** Escolha uma fileira com pelo menos 2 aliados. Todos os seus aliados nela ganham +2 de bônus nesta rodada.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um juramento ancestral une os guerreiros às formas primordiais que precederam a Erdtree.
- **Combos possíveis:** nenhum combo cadastrado.

### 47. Passo do Cão de Caça

- **ID:** `gwent_especial_batedor`
- **Categoria / tipo:** Especial / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Passo do Cão de Caça
- **O que faz:** Compra cartas do topo da sua reserva. A quantidade depende da raridade.
- **Bônus da raridade:** Raridade Rara: compra até 2 cartas do topo da sua reserva.
- **História (lore):** O passo do cão de caça atravessa o campo antes que o inimigo perceba sua aproximação.
- **Combos possíveis:** nenhum combo cadastrado.

### 48. Bastião de Leyndell

- **ID:** `gwent_especial_muralha`
- **Categoria / tipo:** Especial / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 0 / Comum / 1
- **Habilidade:** Bastião de Leyndell
- **O que faz:** Escolha uma fileira. Todos os seus aliados nela ganham +1 de bônus nesta rodada.
- **Bônus da raridade:** Raridade Comum: não reforça os efeitos de bônus desta carta.
- **História (lore):** As muralhas douradas de Leyndell erguem-se como símbolo da resistência da capital.
- **Combos possíveis:** nenhum combo cadastrado.

### 49. Ritual de Sangue

- **ID:** `elden_especial_sangramento`
- **Categoria / tipo:** Especial / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Sangramento
- **O que faz:** Escolha uma fileira. Todos os inimigos nela recebem Sangramento. A segunda marca causa Hemorragia: tira 2 pontos do bônus (até -2) e apaga as marcas. As marcas restantes somem no fim da rodada.
- **Bônus da raridade:** Raridade Rara: além da marca normal, pode aplicar outra marca no primeiro inimigo da fileira, se ele ainda não tiver Sangramento. A segunda marca causa Hemorragia, reduz o bônus em 2 e apaga as marcas; a raridade pode reduzir mais 1 (até -2).
- **História (lore):** O ritual desperta o poder do sangue e transforma cada ferida em um presságio de ruína.
- **Combos possíveis:** nenhum combo cadastrado.

### 50. Lua Cheia de Rennala

- **ID:** `elden_especial_geada`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Geada Cariana
- **O que faz:** Escolha uma fileira. Todos os inimigos nela recebem Geada. Cada marca reduz o poder atual em 1; cada inimigo pode ter até 2 marcas. Elas somem no fim da rodada.
- **Bônus da raridade:** Raridade Rara: além da marca normal, pode aplicar outra marca no primeiro inimigo da fileira, se ele ainda não tiver Geada.
- **História (lore):** A lua cheia de Rennala ilumina o campo com a frieza ancestral da realeza cariana.
- **Combos possíveis:** nenhum combo cadastrado.

### 51. Flor da Podridão Escarlate

- **ID:** `elden_especial_podrida`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Épica / 3
- **Habilidade:** Podridão Escarlate
- **O que faz:** Escolha uma fileira. Todos os inimigos nela recebem Podridão Escarlate. Cada marca reduz o poder atual em 1; a segunda também tira 1 ponto do bônus positivo. As marcas somem no fim da rodada.
- **Bônus da raridade:** Raridade Épica: além da marca normal, pode aplicar outra marca no primeiro inimigo da fileira, se ele ainda não tiver Podridão Escarlate. A segunda marca reduz em 1 o bônus positivo; a raridade pode tirar mais 1 ponto.
- **História (lore):** A flor escarlate floresce onde a podridão encontra carne, pedra e memória.
- **Combos possíveis:** nenhum combo cadastrado.

### 52. Chama Frenética

- **ID:** `elden_especial_loucura`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Épica / 3
- **Habilidade:** Loucura Frenética
- **O que faz:** Escolha uma fileira. Todos os inimigos nela recebem Loucura. Cada marca reduz o poder atual em 1; a segunda zera o bônus positivo. As marcas somem no fim da rodada.
- **Bônus da raridade:** Raridade Épica: além da marca normal, pode aplicar outra marca no primeiro inimigo da fileira, se ele ainda não tiver Loucura. A segunda marca zera o bônus positivo; a raridade pode tirar mais 1 ponto.
- **História (lore):** A chama frenética consome razão e identidade, deixando apenas o caos da Chama Frenética.
- **Combos possíveis:** nenhum combo cadastrado.

### 53. Chama do Gigante

- **ID:** `elden_especial_chama`
- **Categoria / tipo:** Especial / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Chama do Gigante
- **O que faz:** Remove Geada de todos os aliados que tenham essa marca. Cada aliado purificado ganha +1 de bônus nesta rodada.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** A chama dos gigantes arde contra o frio que tenta aprisionar os vivos.
- **Combos possíveis:** nenhum combo cadastrado.

### 54. Cinzas dos Lobos Solitários

- **ID:** `elden_especial_invocacao`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Cinzas dos Lobos Solitários
- **O que faz:** Invoca a unidade Lobos Espirituais na fileira escolhida.
- **Bônus da raridade:** Raridade Rara: a unidade Lobos Espirituais entra com 4 de poder-base.
- **História (lore):** Cinzas antigas despertam os espíritos de lobos que outrora caçaram ao lado de seus mestres.
- **Combos possíveis:** nenhum combo cadastrado.

### 55. Grande Runa de Godrick

- **ID:** `reliquia_grande_runa_godrick`
- **Categoria / tipo:** Especial / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 0 / Lendária / 3
- **Habilidade:** Grande Runa de Godrick
- **O que faz:** Uma vez por partida: se você tiver ao menos 1 aliado em campo, todos os seus aliados recebem +1 de bônus.
- **Bônus da raridade:** A raridade não muda o efeito desta Relíquia.
- **História (lore):** Fragmento do Anel Prístino reivindicado por Godrick, o Enxertado, que buscava poder por meio do enxerto.
- **Combos possíveis:** nenhum combo cadastrado.

### 56. Grande Runa dos Não Nascidos

- **ID:** `reliquia_runa_nao_nascidos`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Lendária / 3
- **Habilidade:** Grande Runa dos Não Nascidos
- **O que faz:** Uma vez por partida: remove Geada e Podridão de todos os aliados afetados. Cada aliado purificado recebe +1 de bônus.
- **Bônus da raridade:** A raridade não muda o efeito desta Relíquia.
- **História (lore):** A Grande Runa guardada por Rennala conserva o poder do renascimento e da perfeição inacabada.
- **Combos possíveis:** nenhum combo cadastrado.

### 57. Runa da Morte

- **ID:** `reliquia_runa_morte`
- **Categoria / tipo:** Especial / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 0 / Mítica / 4
- **Habilidade:** Runa da Morte
- **O que faz:** Uma vez por partida: em cada fileira, encontra o inimigo com maior bônus positivo e reduz esse bônus em 2, sem deixá-lo abaixo de 0.
- **Bônus da raridade:** A raridade não muda o efeito desta Relíquia.
- **História (lore):** O fragmento da Morte Destinada recorda o poder que Maliketh recebeu para manter selado.
- **Combos possíveis:** nenhum combo cadastrado.

### 58. Espada da Noite e da Chama

- **ID:** `reliquia_noite_chama`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Lendária / 3
- **Habilidade:** Espada da Noite e da Chama
- **O que faz:** Uma vez por partida, escolha fileira e postura. Noite: aplica 1 marca de Geada a todos os inimigos da fileira (-1 de poder atual até o fim da rodada). Chama: tira 1 do poder-base (mín. 1) e 2 do bônus do inimigo mais forte. Escudo bloqueia Chama, mas a Relíquia é consumida.
- **Bônus da raridade:** A raridade não muda o efeito desta Relíquia.
- **História (lore):** Arma lendária da Mansão Cariana. Sua postura especial libera um ataque mágico ou uma onda de fogo.
- **Combos possíveis:** nenhum combo cadastrado.

### 59. Lâmina Negra

- **ID:** `reliquia_lamina_negra`
- **Categoria / tipo:** Especial / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 0 / Mítica / 4
- **Habilidade:** Lâmina Negra
- **O que faz:** Uma vez por partida, escolha um inimigo da fileira: o bônus dele cai em 3. Sem alvo escolhido, atinge o mais forte da fileira. Se houver escudo, ele é gasto e a Relíquia não é consumida.
- **Bônus da raridade:** A raridade não muda o efeito desta Relíquia.
- **História (lore):** A arma de Maliketh, que guarda a Morte Destinada selada em sua lâmina. Não é uma das adagas usadas pelas Assassinas da Faca Negra.
- **Combos possíveis:** nenhum combo cadastrado.

### 60. Algemas de Margit

- **ID:** `reliquia_algemas_margit`
- **Categoria / tipo:** Especial / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 0 / Épica / 2
- **Habilidade:** Algemas de Margit
- **O que faz:** Uma vez por partida, escolha um inimigo da fileira. Se o bônus for positivo, cai para 0; bônus negativos não mudam. Sem alvo escolhido, atinge quem tem o maior bônus na fileira.
- **Bônus da raridade:** A raridade não muda o efeito desta Relíquia.
- **História (lore):** Correntes forjadas para conter o Agouro caído, capazes de subjugar até mesmo um inimigo temível.
- **Combos possíveis:** nenhum combo cadastrado.

### 61. Cavaleiro do Crisol

- **ID:** `gwent_unidade_baluarte`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um cavaleiro do Crisol, marcado pelas antigas formas que antecederam a Árvore Áurea, guarda a formação com disciplina.
- **Combos possíveis:**
  - **Aliança da Árvore Áurea** — Cavaleiro da Árvore Áurea ou Cavaleiros de Radahn e uma unidade da Fornalha coordenam a formação (+2).
  - **Juramento da Árvore Áurea** — Duas unidades da Ordem Áurea reforçam a formação: +2 para quem completa o combo e +1 aos aliados da mesma fileira.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 62. Caçador de Dedos

- **ID:** `gwent_unidade_lamina_sem_juramento`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Caçador de Dedos, um duelista errante que prefere trilhas solitárias e confrontos sem testemunhas.
- **Combos possíveis:** nenhum combo cadastrado.

### 63. Porta-estandarte de Leyndell

- **ID:** `gwent_unidade_portaestandarte`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** O estandarte de Leyndell reúne soldados dispersos sob o símbolo dourado da capital.
- **Combos possíveis:**
  - **Aliança da Árvore Áurea** — Cavaleiro da Árvore Áurea ou Cavaleiros de Radahn e uma unidade da Fornalha coordenam a formação (+2).
  - **Juramento de Leyndell** — Porta-estandarte e Guardas da Árvore Áurea fortalecem a formação (+1 para a carta que completa e +1 aos aliados na mesma fileira).
  - **Juramento da Árvore Áurea** — Duas unidades da Ordem Áurea reforçam a formação: +2 para quem completa o combo e +1 aos aliados da mesma fileira.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 64. Profeta de Liurnia

- **ID:** `gwent_unidade_oraculo_clima`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** O profeta de Liurnia observa as mudanças do céu e interpreta os sinais trazidos por tempestades e geadas.
- **Combos possíveis:** nenhum combo cadastrado.

### 65. Erudito das Pedras Cintilantes

- **ID:** `gwent_unidade_eco`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um estudioso das pedras cintilantes investiga as ressonâncias deixadas por feitiçarias antigas.
- **Combos possíveis:**
  - **Alinhamento Astral** — Ranni e uma unidade Astral convergem (+2).
  - **Eco das Pedras Cintilantes** — O Erudito das Pedras Cintilantes e uma unidade Astral amplificam a mesma magia (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 66. Cavaleira Cariana

- **ID:** `gwent_unidade_cavaleira`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Lua Negra / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Uma duelista cariana, treinada nas tradições de combate da realeza lunar.
- **Combos possíveis:**
  - **Caçada da Faca Negra** — Duas unidades do Véu Sombrio entram em sintonia (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 67. Gigante de Fogo

- **ID:** `gwent_unidade_gigante`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 7 / Épica / 3
- **Habilidade:** Instinto de Caçador
- **O que faz:** Se sua equipe estiver perdendo quando esta carta entrar, ganha +2 de bônus.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Uma presença colossal na linha de frente.
- **Combos possíveis:** nenhum combo cadastrado.

### 68. Exploradora da Cidade Eterna

- **ID:** `gwent_unidade_cartografa`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Lua Negra / Longa distância
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Encontra rotas onde os outros veem obstáculos.
- **Combos possíveis:**
  - **Dança da Lua Negra** — Dançarina, Gêmea ou Cartógrafa sincronizam seus movimentos (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 69. Apóstolo da Pele Divina Errante

- **ID:** `gwent_unidade_invocador`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Véu Carmesim / Cerco
- **Poder-base / raridade / custo:** 7 / Épica / 3
- **Habilidade:** Caçador de Feitiços
- **O que faz:** Ganha +1 de bônus se o inimigo tiver uma unidade da Lua Negra ou qualquer unidade com bônus acima de 0.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Converte conhecimento arcano em força de combate.
- **Combos possíveis:**
  - **Alinhamento Astral** — Ranni e uma unidade Astral convergem (+2).
  - **Eco das Pedras Cintilantes** — O Erudito das Pedras Cintilantes e uma unidade Astral amplificam a mesma magia (+2).

### 70. Mestre Ferreiro de Volcano Manor

- **ID:** `gwent_unidade_mestre_forja`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um mestre ferreiro de Volcano Manor trabalha entre brasas, aço e os juramentos dos recusantes.
- **Combos possíveis:**
  - **Aliança da Árvore Áurea** — Cavaleiro da Árvore Áurea ou Cavaleiros de Radahn e uma unidade da Fornalha coordenam a formação (+2).
  - **Juramento da Árvore Áurea** — Duas unidades da Ordem Áurea reforçam a formação: +2 para quem completa o combo e +1 aos aliados da mesma fileira.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 71. Gêmeas da Cidade Eterna

- **ID:** `gwent_unidade_dupla_veu`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Lua Negra / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Duas irmãs das Cidades Eternas percorrem caminhos subterrâneos que raramente aparecem nos mapas.
- **Combos possíveis:**
  - **Caçada da Faca Negra** — Duas unidades do Véu Sombrio entram em sintonia (+2).
  - **Dança da Lua Negra** — Dançarina, Gêmea ou Cartógrafa sincronizam seus movimentos (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 72. Discípulo da Academia

- **ID:** `gwent_unidade_circulo`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Discípulo de Raya Lucaria, dedica-se ao estudo dos círculos arcanos e dos resíduos de feitiçaria.
- **Combos possíveis:**
  - **Alinhamento Astral** — Ranni e uma unidade Astral convergem (+2).
  - **Eco das Pedras Cintilantes** — O Erudito das Pedras Cintilantes e uma unidade Astral amplificam a mesma magia (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 73. Cavaleiro de Radahn

- **ID:** `gwent_unidade_sentinela_rubra`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Um cavaleiro da hoste de Radahn mantém sua posição sob o estandarte vermelho de Caelid.
- **Combos possíveis:**
  - **Defesa de Leyndell** — Duas unidades da Muralha Rubra erguem a linha (+2 para a carta que completa e +1 aos aliados na fileira).
  - **Juramento da Árvore Áurea** — Duas unidades da Ordem Áurea reforçam a formação: +2 para quem completa o combo e +1 aos aliados da mesma fileira.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 74. Cavaleiro Draconiano

- **ID:** `gwent_unidade_veterano_cercos`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Já viu mais muralhas caírem do que rostos conhecidos.
- **Combos possíveis:**
  - **Defesa de Leyndell** — Duas unidades da Muralha Rubra erguem a linha (+2 para a carta que completa e +1 aos aliados na fileira).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 75. Godwyn, o Dourado

- **ID:** `gwent_unidade_herdeiro_portao`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Épica / 3
- **Habilidade:** Vingança
- **O que faz:** Quando esta unidade sair do campo, cada aliado que continuar na mesma fileira ganha +1 de bônus.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Godwyn, herdeiro da linhagem dourada, carrega o peso de uma antiga promessa ligada à capital.
- **Combos possíveis:**
  - **Defesa de Leyndell** — Duas unidades da Muralha Rubra erguem a linha (+2 para a carta que completa e +1 aos aliados na fileira).
  - **Juramento da Árvore Áurea** — Duas unidades da Ordem Áurea reforçam a formação: +2 para quem completa o combo e +1 aos aliados da mesma fileira.

### 76. Carrasco de Volcano Manor

- **ID:** `gwent_unidade_carniceiro_forja`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 4 / Rara / 2
- **Habilidade:** Devorar
- **O que faz:** Ao entrar, sacrifica o aliado mais fraco da mesma fileira e ganha bônus igual à força atual dele, até +4. O escudo não impede o sacrifício. Sem aliado, não ganha bônus.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um carrasco de Volcano Manor cumpre ordens entre as fornalhas e os juramentos dos recusantes.
- **Combos possíveis:**
  - **Banquete de Sangue** — Carniceiro da Forja e Intendente dividem o butim (+3).
  - **Ritual do Véu Carmesim** — Duas unidades do Véu Carmesim fortalecem a carta que completa o ritual (+2) e os aliados na fileira (+1).

### 77. Mercador Nômade

- **ID:** `gwent_unidade_intendente`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Longa distância
- **Poder-base / raridade / custo:** 4 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Um mercador nômade percorre as Terras Intermédias levando provisões e notícias entre assentamentos.
- **Combos possíveis:**
  - **Banquete de Sangue** — Carniceiro da Forja e Intendente dividem o butim (+3).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 78. Assassina de Ravenmount

- **ID:** `gwent_unidade_cacadora_fantasma`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Uma assassina de Ravenmount atravessa a névoa sem deixar rastros fáceis de seguir.
- **Combos possíveis:**
  - **Procissão dos que Vivem na Morte** — Duas unidades fantasmas marcham juntas (+2 para a carta que completa e +1 aos aliados na fileira).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 79. Fia, Companheira do Leito de Morte

- **ID:** `gwent_unidade_cantora_lamentos`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 5 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Fia, Companheira do Leito de Morte, entoa lamentos pelos que encontraram repouso entre os mortos.
- **Combos possíveis:**
  - **Procissão dos que Vivem na Morte** — Duas unidades fantasmas marcham juntas (+2 para a carta que completa e +1 aos aliados na fileira).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 80. Blaidd, o Meio-Lobo

- **ID:** `gwent_unidade_senhor_cacada`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Lua Negra / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Épica / 3
- **Habilidade:** Vingança
- **O que faz:** Quando esta unidade sair do campo, cada aliado que continuar na mesma fileira ganha +1 de bônus.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Blaidd, o Meio-Lobo, é um guerreiro ligado a Ranni e à antiga linhagem dos lobos das Terras Intermédias.
- **Combos possíveis:**
  - **Procissão dos que Vivem na Morte** — Duas unidades fantasmas marcham juntas (+2 para a carta que completa e +1 aos aliados na fileira).

### 81. Ladina da Cidade Eterna

- **ID:** `gwent_unidade_saqueadora_veu`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Lua Negra / Longa distância
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Nenhuma rota é cara demais para quem leva o butim.
- **Combos possíveis:**
  - **Saque da Cidade Eterna** — Saqueadora e Contrabandista fecham o negócio (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 82. Recusante da Mansão Vulcânica

- **ID:** `gwent_unidade_contrabandista`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Um recusante de Volcano Manor, acostumado a negociar favores e segredos nas encostas do Monte Gelmir.
- **Combos possíveis:**
  - **Saque da Cidade Eterna** — Saqueadora e Contrabandista fecham o negócio (+2).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 83. Guardião da Ordem Áurea

- **ID:** `gwent_unidade_guardiao_runas`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** Um guardião da Ordem Áurea carrega inscrições rúnicas ligadas aos ensinamentos da capital.
- **Combos possíveis:**
  - **Ritual das Runas** — Duas unidades rúnicas completam o círculo (+2 para a carta que completa e +1 aos aliados na fileira).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 84. Servo dos que Vivem na Morte

- **ID:** `gwent_unidade_necromante`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 4 / Rara / 2
- **Habilidade:** Ressurgir
- **O que faz:** Ao entrar, se houver uma unidade no seu descarte com poder-base até 5, traz de volta a mais forte entre elas. Ela retorna à fileira original.
- **Bônus da raridade:** Raridade Rara: não muda o efeito próprio desta carta. Se ela completar um combo, pode reforçar o bônus de 1 unidade afetada por ele.
- **História (lore):** Um servo dos que Vivem na Morte segue os ritos que desafiam a ordem natural da morte.
- **Combos possíveis:**
  - **Ritual das Runas** — Duas unidades rúnicas completam o círculo (+2 para a carta que completa e +1 aos aliados na fileira).

### 85. Guerreiro da Chama Frenética

- **ID:** `gwent_unidade_detonador`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Épica / 3
- **Habilidade:** Vingança
- **O que faz:** Quando esta unidade sair do campo, cada aliado que continuar na mesma fileira ganha +1 de bônus.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um guerreiro marcado pela Chama Frenética percorre as Terras Intermédias em busca de novos devotos.
- **Combos possíveis:**
  - **Ritual das Runas** — Duas unidades rúnicas completam o círculo (+2 para a carta que completa e +1 aos aliados na fileira).

### 86. Cavaleiro de Sangue de Mohg

- **ID:** `gwent_unidade_devorador_mana`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um cavaleiro ligado ao sangue de Mohg participa dos rituais sombrios da dinastia subterrânea.
- **Combos possíveis:**
  - **Eclipse Sanguíneo** — Cavaleiro de Sangue de Mohg e Bibliotecária eclipsam a mesma fonte (+3).
  - **Ritual do Véu Carmesim** — Duas unidades do Véu Carmesim fortalecem a carta que completa o ritual (+2) e os aliados na fileira (+1).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 87. Bibliotecária de Raya Lucaria

- **ID:** `gwent_unidade_bibliotecaria`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 5 / Comum / 1
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Comum: não reforça os bônus gerados pelo combo desta carta.
- **História (lore):** O conhecimento reunido na guerra vale mais que ouro.
- **Combos possíveis:**
  - **Eclipse Sanguíneo** — Cavaleiro de Sangue de Mohg e Bibliotecária eclipsam a mesma fonte (+3).
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 88. Bênção da Árvore Áurea

- **ID:** `gwent_especial_egide`
- **Categoria / tipo:** Especial / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Bênção da Árvore Áurea
- **O que faz:** Dá escudo a aliados que ainda não tenham um. Você escolhe o primeiro; depois, os mais fortes são protegidos.
- **Bônus da raridade:** Raridade Rara: pode dar escudo a até 2 aliados sem escudo.
- **História (lore):** Uma bênção da Árvore Áurea, invocada pelos guerreiros que buscam a proteção da capital.
- **Combos possíveis:** nenhum combo cadastrado.

### 89. Chamado dos Mortos

- **ID:** `gwent_especial_requiem`
- **Categoria / tipo:** Especial / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 0 / Épica / 3
- **Habilidade:** Chamado dos Mortos
- **O que faz:** Escolha uma unidade do seu descarte para voltar ao campo, na mesma fileira em que estava antes de sair. Ela retorna sem bônus e sem escudo.
- **Bônus da raridade:** Raridade Épica: permite trazer de volta unidades com poder-base de até 7.
- **História (lore):** Um chamado antigo ecoa entre os mortos e convida os guerreiros caídos a retornarem à batalha.
- **Combos possíveis:** nenhum combo cadastrado.

### 90. Passo do Lobo

- **ID:** `gwent_especial_passo`
- **Categoria / tipo:** Especial / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 0 / Rara / 2
- **Habilidade:** Passo do Lobo
- **O que faz:** Move aliados de outras fileiras para a escolhida. Você pode escolher quem vai primeiro; os demais seguem a ordem em que aparecem no campo. Sem escolha, o mais fraco vai primeiro.
- **Bônus da raridade:** Raridade Rara: pode mover até 2 aliados para a fileira escolhida.
- **História (lore):** O Passo do Lobo representa a velocidade e a precisão dos caçadores que cruzam as Terras Intermédias.
- **Combos possíveis:** nenhum combo cadastrado.

### 91. Cavaleiro Consagrado do Haligtree

- **ID:** `gwent_mitica_coroa`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 8 / Mítica / 5
- **Habilidade:** Estandarte
- **O que faz:** Ao entrar, dá +1 de bônus a cada aliado que já esteja na mesma fileira.
- **Bônus da raridade:** Raridade Mítica: pode reforçar o bônus de até 2 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Um cavaleiro consagrado guarda os caminhos do Haligtree e permanece fiel à promessa de Miquella.
- **Combos possíveis:** nenhum combo cadastrado.

### 92. Juramento Primordial do Crisol

- **ID:** `gwent_singular_primeiro`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 10 / Singular / 0
- **Habilidade:** Caçador Solitário
- **O que faz:** Ganha +2 de bônus se não houver outro aliado nesta fileira quando entrar.
- **Bônus da raridade:** Raridade Singular: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Exemplar singular conquistado por um feito extraordinário.
- **Combos possíveis:** nenhum combo cadastrado.

### 93. Adaga da Faca Negra

- **ID:** `gwent_singular_intocavel`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 9 / Singular / 0
- **Habilidade:** Mira Cariana
- **O que faz:** Ao entrar na fileira de Longa Distância, ganha +1 de bônus.
- **Bônus da raridade:** Raridade Singular: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Conquistada ao concluir um desafio sem sofrer dano.
- **Combos possíveis:** nenhum combo cadastrado.

### 94. Vontade de Marika

- **ID:** `gwent_singular_nivel1`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 10 / Singular / 0
- **Habilidade:** Último Suspiro
- **O que faz:** Na terceira rodada, ganha +1 de bônus ao entrar em campo.
- **Bônus da raridade:** Raridade Singular: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Conquistada ao vencer um desafio no nível um.
- **Combos possíveis:** nenhum combo cadastrado.

### 95. Coroa do Lorde Prístino

- **ID:** `gwent_singular_cacador_chefes`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Corpo a corpo
- **Poder-base / raridade / custo:** 9 / Singular / 0
- **Habilidade:** Paradoxo Eterno
- **O que faz:** Na terceira rodada, ganha +2 de bônus se o inimigo venceu a segunda rodada.
- **Bônus da raridade:** Raridade Singular: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Conquistada ao derrotar todos os chefes de um desafio.
- **Combos possíveis:** nenhum combo cadastrado.

## Expansão V75

### 96. Veterano do Juramento Dourado

- **ID:** `gwent_v75_ordem_veterano_juramento`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 4 / Rara / 2
- **Habilidade:** Juramento Dourado
- **O que faz:** Ao entrar, esta carta ganha +1 de bônus. O aliado mais fraco da mesma fileira também ganha +1, se houver.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Veterano de Leyndell, endurecido pelas campanhas da capital e fiel à Árvore Áurea.
- **Combos possíveis:**
  - **Juramento do Crisol e da Graça** — Formação e proteção convergem: a carta que completa o juramento recebe +2.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 97. Guardião do Crisol Menor

- **ID:** `gwent_v75_ordem_guardiao_crisol`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 4 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Guardião treinado nos antigos rituais do Crisol, mantém a disciplina entre os guerreiros de Leyndell.
- **Combos possíveis:**
  - **Juramento do Crisol e da Graça** — Formação e proteção convergem: a carta que completa o juramento recebe +2.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 98. Confessora da Graça Serena

- **ID:** `gwent_v75_ordem_confessora_graca`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Cerco
- **Poder-base / raridade / custo:** 5 / Épica / 3
- **Habilidade:** Regressão Serena
- **O que faz:** Remove Sangramento, Geada, Podridão e Loucura de até 2 aliados desta fileira. Cada um ganha +1 de bônus. Se nenhum aliado tiver marcas, o mais fraco ganha +1. Se não houver outro aliado na fileira, esta carta ganha +1.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Confessora da Ordem Áurea, estuda a Lei da Regressão e protege os ritos de purificação da capital.
- **Combos possíveis:**
  - **Juramento do Crisol e da Graça** — Formação e proteção convergem: a carta que completa o juramento recebe +2.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 99. Arauto do Estandarte Áureo

- **ID:** `gwent_v75_ordem_arauto_estandarte`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Longa distância
- **Poder-base / raridade / custo:** 5 / Épica / 3
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Arauto de Leyndell, carrega o estandarte dourado que reúne os soldados da capital.
- **Combos possíveis:**
  - **Juramento do Crisol e da Graça** — Formação e proteção convergem: a carta que completa o juramento recebe +2.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 100. Acólito da Dinastia Sanguínea

- **ID:** `gwent_v75_veu_acolito_sangue`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 4 / Rara / 2
- **Habilidade:** Marca da Dinastia
- **O que faz:** Aplica Sangramento ao inimigo mais forte desta fileira. Se ele já tiver uma marca, causa Hemorragia: tira 2 pontos do bônus (até -2), apaga as marcas e esta carta ganha +1.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Servo do Palácio de Mohgwyn, participa dos rituais de sangue dedicados ao Senhor do Sangue.
- **Combos possíveis:**
  - **Banquete da Hemorragia** — Uma marca aberta alimenta o ritual: a carta que completa o combo recebe +2.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 101. Devota da Hemorragia

- **ID:** `gwent_v75_veu_devota_hemorragia`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Cerco
- **Poder-base / raridade / custo:** 4 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Devota da Hemorragia, oferece preces ao Senhor do Sangue nos salões subterrâneos de Mohgwyn.
- **Combos possíveis:**
  - **Banquete da Hemorragia** — Uma marca aberta alimenta o ritual: a carta que completa o combo recebe +2.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 102. Carrasco da Procissão Carmesim

- **ID:** `gwent_v75_veu_carrasco_preco`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Épica / 3
- **Habilidade:** Preço em Sangue
- **O que faz:** Sacrifica o aliado mais fraco desta fileira e ganha bônus igual à força atual dele, até +3. Se não houver aliado, ganha +1. O escudo não impede o sacrifício.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Carrasco da Procissão Carmesim, executa sentenças em nome da dinastia sanguínea.
- **Combos possíveis:**
  - **Banquete da Hemorragia** — Uma marca aberta alimenta o ritual: a carta que completa o combo recebe +2.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 103. Caçador das Catacumbas de Mohgwyn

- **ID:** `gwent_v75_veu_cacador_sangue`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 5 / Épica / 3
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Caçador das Catacumbas de Mohgwyn, persegue aqueles que tentam escapar dos rituais da dinastia.
- **Combos possíveis:**
  - **Banquete da Hemorragia** — Uma marca aberta alimenta o ritual: a carta que completa o combo recebe +2.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 104. Oráculo Gélido de Sellia

- **ID:** `gwent_v75_lua_oraculo_geada`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 4 / Rara / 2
- **Habilidade:** Presságio da Geada
- **O que faz:** Aplica Geada ao inimigo mais forte desta fileira. Se ele já tiver Geada, esta carta ganha +1 de bônus.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Astróloga de Sellia, estuda as correntes de frio associadas às antigas artes lunares.
- **Combos possíveis:**
  - **Convergência da Geada Lunar** — Geada e leitura das fileiras entram em ressonância: a carta que completa o combo recebe +2.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 105. Cartógrafo das Cidades Eternas

- **ID:** `gwent_v75_lua_cartografo_lunar`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Longa distância
- **Poder-base / raridade / custo:** 4 / Rara / 2
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Cartógrafo das Cidades Eternas, registra passagens subterrâneas e caminhos sob as estrelas.
- **Combos possíveis:**
  - **Convergência da Geada Lunar** — Geada e leitura das fileiras entram em ressonância: a carta que completa o combo recebe +2.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

### 106. Graviturgista de Nokron

- **ID:** `gwent_v75_lua_graviturgista`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 5 / Épica / 3
- **Habilidade:** Cisalhamento Gravitacional
- **O que faz:** Tira 1 ponto do bônus de até 2 inimigos com bônus positivo nesta fileira. Se atingir 2 inimigos, esta carta ganha +1.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Graviturgista de Nokron, pesquisa forças capazes de curvar o movimento dos corpos celestes.
- **Combos possíveis:**
  - **Convergência da Geada Lunar** — Geada e leitura das fileiras entram em ressonância: a carta que completa o combo recebe +2.
- **Regra de apresentação:** habilidade de identidade; a habilidade genérica do campo de catálogo não é executada e não aparece na ficha.

### 107. Guardiã do Juramento Lunar

- **ID:** `gwent_v75_lua_guardia`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Épica / 3
- **Habilidade:** Sem habilidade individual
- **O que faz:** Esta carta não tem efeito sozinha. Ela só funciona em um combo compatível; veja os combos compatíveis desta carta.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Guardiã juramentada à Lua Negra, protege os caminhos lunares e as alianças das Cidades Eternas.
- **Combos possíveis:**
  - **Convergência da Geada Lunar** — Geada e leitura das fileiras entram em ressonância: a carta que completa o combo recebe +2.
- **Regra de apresentação:** carta de combo; não anuncia efeito individual.

## Cartas Primordiais

### 108. Besta Prístina, Arauto da Vontade Maior

- **ID:** `primordial_origem`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Cerco
- **Poder-base / raridade / custo:** 8 / Primordial / 4
- **Habilidade:** Lei Primeva
- **O que faz:** Na primeira rodada, ganha +2 de bônus ao entrar em campo.
- **Bônus da raridade:** Raridade Primordial: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** A Besta Prístina manifesta a vontade que veio além das estrelas e deu forma à ordem dourada.
- **Combos possíveis:** nenhum combo cadastrado.

### 109. Marika, Rainha Eterna

- **ID:** `primordial_trono`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 8 / Primordial / 4
- **Habilidade:** Decreto Soberano
- **O que faz:** Ao entrar, tira 2 pontos do bônus de cada inimigo. Nenhum bônus pode ficar abaixo de -2.
- **Bônus da raridade:** Raridade Primordial: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Marika, a Rainha Eterna, ergueu a ordem dourada e rompeu o Anel Prístino, mudando para sempre as Terras Intermédias.
- **Combos possíveis:** nenhum combo cadastrado.

### 110. Placidusax, Senhor Dragão

- **ID:** `primordial_tempestade`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 8 / Primordial / 4
- **Habilidade:** Olho da Tempestade
- **O que faz:** Se houver clima na fileira escolhida, ganha +2 de bônus ao entrar.
- **Bônus da raridade:** Raridade Primordial: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Placidusax, antigo lorde dos dragões, permanece suspenso no tempo em Farum Azula.
- **Combos possíveis:** nenhum combo cadastrado.

### 111. Mãe Sem Forma

- **ID:** `primordial_abismo`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Cerco
- **Poder-base / raridade / custo:** 8 / Primordial / 4
- **Habilidade:** Fome do Abismo
- **O que faz:** Se sua equipe estiver perdendo quando esta carta entrar, ganha +2 de bônus.
- **Bônus da raridade:** Raridade Primordial: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** A Mãe Sem Forma é venerada pelos seguidores de Mohg como origem do poder sanguíneo.
- **Combos possíveis:** nenhum combo cadastrado.

### 112. Maliketh, Guardião da Morte Destinada

- **ID:** `primordial_eternidade`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 8 / Primordial / 4
- **Habilidade:** Paradoxo Eterno
- **O que faz:** Na terceira rodada, ganha +2 de bônus se o inimigo venceu a segunda rodada.
- **Bônus da raridade:** Raridade Primordial: pode reforçar o bônus de até 3 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Maliketh guarda a Morte Destinada, o poder cuja ausência sustenta a ordem sem morte de Marika.
- **Combos possíveis:** nenhum combo cadastrado.

## Recompensas de patente

### 113. Novato de Raya Lucaria · Selo AF8F

- **ID:** `patente_1`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 3 / Comum / 1
- **Habilidade:** Caçador de Feitiços
- **O que faz:** Ganha +1 de bônus se o inimigo tiver uma unidade da Lua Negra ou qualquer unidade com bônus acima de 0.
- **Bônus da raridade:** Raridade Comum: não reforça os efeitos de bônus desta carta.
- **História (lore):** Recompensa de patente concedida ao alcançar o nível 1. Um estudioso da Lua Negra, dedicado às artes arcanas.
- **Combos possíveis:** nenhum combo cadastrado.

### 114. Novato de Raya Lucaria · Selo 52B7

- **ID:** `patente_2`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 3 / Comum / 1
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Recompensa de patente concedida ao alcançar o nível 5. Um estudioso da Lua Negra, dedicado às artes arcanas.
- **Combos possíveis:** nenhum combo cadastrado.

### 115. Aprendiz Cariano · Selo 068B

- **ID:** `patente_3`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Recompensa de patente concedida ao alcançar o nível 10. Um estudioso da Lua Negra, dedicado às artes arcanas.
- **Combos possíveis:** nenhum combo cadastrado.

### 116. Escudeiro da Árvore Áurea · Selo 4B40

- **ID:** `patente_4`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Rara / 2
- **Habilidade:** Sem habilidade especial
- **O que faz:** Esta carta não possui uma habilidade de combate própria.
- **Bônus da raridade:** Não há reforço de habilidade exibido para esta carta.
- **História (lore):** Recompensa de patente concedida ao alcançar o nível 15. Um combatente de Leyndell, treinado para servir à Árvore Áurea.
- **Combos possíveis:** nenhum combo cadastrado.

### 117. Acólito Sanguíneo · Selo 8644

- **ID:** `patente_5`
- **Categoria / tipo:** Unidade / Destreza
- **Facção / fileira:** Véu Carmesim / Longa distância
- **Poder-base / raridade / custo:** 6 / Rara / 2
- **Habilidade:** Postura Encadeada
- **O que faz:** Ganha +2 de bônus se sua última unidade foi jogada nesta mesma fileira.
- **Bônus da raridade:** Raridade Rara: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Recompensa de patente concedida ao alcançar o nível 20. Um guerreiro do Véu Carmesim, ligado aos caminhos de Mohgwyn.
- **Combos possíveis:** nenhum combo cadastrado.

### 118. Veterano de Leyndell · Selo D17A

- **ID:** `patente_6`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Épica / 3
- **Habilidade:** Retaliação dos Semideuses
- **O que faz:** Se sua equipe estiver perdendo quando esta carta entrar, ganha +1 de bônus.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Recompensa de patente concedida ao alcançar o nível 30. Um combatente de Leyndell, treinado para servir à Árvore Áurea.
- **Combos possíveis:** nenhum combo cadastrado.

### 119. Feiticeiro Cariano · Selo C7CC

- **ID:** `patente_7`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 7 / Épica / 3
- **Habilidade:** Caçador de Feitiços
- **O que faz:** Ganha +1 de bônus se o inimigo tiver uma unidade da Lua Negra ou qualquer unidade com bônus acima de 0.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Recompensa de patente concedida ao alcançar o nível 40. Um estudioso da Lua Negra, dedicado às artes arcanas.
- **Combos possíveis:** nenhum combo cadastrado.

### 120. Veterano de Leyndell · Selo 5241

- **ID:** `patente_8`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 5 / Épica / 3
- **Habilidade:** Retaliação dos Semideuses
- **O que faz:** Se sua equipe estiver perdendo quando esta carta entrar, ganha +1 de bônus.
- **Bônus da raridade:** Raridade Épica: pode reforçar o bônus de 1 unidade afetada por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Recompensa de patente concedida ao alcançar o nível 50. Um combatente de Leyndell, treinado para servir à Árvore Áurea.
- **Combos possíveis:** nenhum combo cadastrado.

### 121. Lorde de Leyndell · Selo 192C

- **ID:** `patente_9`
- **Categoria / tipo:** Unidade / Força
- **Facção / fileira:** Ordem Áurea / Corpo a corpo
- **Poder-base / raridade / custo:** 8 / Lendária / 4
- **Habilidade:** Ímpeto do Lorde
- **O que faz:** Se sua equipe estiver vencendo quando esta carta entrar, ganha +1 de bônus.
- **Bônus da raridade:** Raridade Lendária: pode reforçar o bônus de até 2 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Recompensa de patente concedida ao alcançar o nível 75. Um combatente de Leyndell, treinado para servir à Árvore Áurea.
- **Combos possíveis:** nenhum combo cadastrado.

### 122. Mestre Cariano · Selo E9EF

- **ID:** `patente_10`
- **Categoria / tipo:** Unidade / Magia
- **Facção / fileira:** Lua Negra / Cerco
- **Poder-base / raridade / custo:** 6 / Lendária / 4
- **Habilidade:** Ruptura de Postura
- **O que faz:** Ganha +1 de bônus se a última unidade jogada pelo inimigo nesta rodada entrou nesta fileira.
- **Bônus da raridade:** Raridade Lendária: pode reforçar o bônus de até 2 unidades afetadas por esta carta ou por seu combo. Quem ganhar bônus recebe +1 extra; quem perder bônus perde mais 1 ponto (até -2). Não muda o poder-base nem os escudos.
- **História (lore):** Recompensa de patente concedida ao alcançar o nível 100. Um estudioso da Lua Negra, dedicado às artes arcanas.
- **Combos possíveis:** nenhum combo cadastrado.

---

## Correções e verificações aplicadas na V80

1. A ficha mostra somente a habilidade efetivamente executada. Quando há habilidade de identidade ativa, o texto genérico substituído não aparece como se também fosse aplicado.
2. Cartas que só funcionam por combo são identificadas como tal. Os nomes e textos dos combos aparecem em seção própria; tags internas não são exibidas como se fossem instruções para o jogador.
3. A história/lore permanece em campo separado do efeito. Não foi usado texto narrativo para explicar regras de combate.
4. O texto de **Estandarte** foi corrigido: o código concede +1 aos aliados que já estavam na fileira; a própria carta que entra não recebe esse +1 do Estandarte.
5. Textos que diziam 'turno anterior' foram ajustados quando a condição real é a última unidade jogada pelo inimigo **na rodada atual**.
6. A habilidade **Devorar** não pode sacrificar a própria carta quando não existe outro aliado. **Caçador Solitário** verifica a ausência de outro aliado na fileira.
7. Efeitos de identidade que se referem a aliados existentes não contam a própria carta que está entrando como se fosse um aliado anterior.
8. **Chamado dos Mortos** informa que a unidade volta à mesma fileira e retorna sem bônus e sem escudo; a faixa de poder-base é explicada no bônus de raridade.
9. Bônus de raridade com efeitos especiais (marcas, compra, recuperação, invocação, escudos e movimento) são explicados separadamente, usando os limites calculados pelo motor.
10. O texto da **Espada da Noite e da Chama** foi encurtado sem retirar as condições importantes para caber na área de texto da arte.
11. A inspeção de layout confirma que os textos efetivos das 122 cartas cabem no painel de habilidade da arte em até quatro linhas no tamanho mínimo previsto pelo renderizador. Os símbolos de habilidade também usam o efeito realmente executado, nunca uma habilidade genérica que foi substituída.
12. A versão das artes/cache foi atualizada para 33; a arte usa o mesmo texto efetivo retornado pelo sistema de preparação da carta.

## Limites desta auditoria

- Os 122 registros estáticos foram inventariados individualmente. As recompensas geradas a partir de nomes de jogos foram testadas por amostragem (60 combinações), pois o gerador aceita títulos arbitrários.
- A validação de lore neste relatório prioriza separação entre narrativa e mecânica e coerência dos campos da carta. Não representa uma nova checagem documental independente de cada frase de todo o cânone de Elden Ring.
- Os testes apresentados no pacote são testes direcionados de catálogo, habilidades, combos, raridade, artes e regressões. A suíte completa do repositório não foi executada.
