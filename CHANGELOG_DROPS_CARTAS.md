# Cartas do Coliseu — atualização acumulada de drops e exemplares

## Regras do sistema

- Toda recompensa de carta é um drop aleatório direto para a coleção; não há pacote para abrir.
- O sorteio usa o catálogo global, sem restringir a carta ao jogo ou à atividade que gerou a recompensa.
- O drop comum pode gerar Comum, Rara, Épica, Lendária ou Mítica.
- Primordial só entra no sorteio quando a aprovação está associada a um feito especial elegível da Central Soulslike.
- Singular não entra no sorteio comum; é concedida como drop especial ao validar um feito extraordinário elegível. Atualmente, os gatilhos são desafios cujo nome contém “Sem tomar dano”, “No-hit”, “Nível 1” ou “Todos os chefes”.
- Cada jogador pode possuir sua própria cópia de cada modelo Primordial e Singular. Não existe disputa por uma única cópia global.
- Platina concede um único drop; o zerado criado/vinculado automaticamente pela platina não gera outro drop.
- Aprovações de zerados, platinas, runs e contribuições comunitárias usam chaves de evento idempotentes.
- Reenvios, edições e reprocessamentos da mesma aprovação não duplicam a recompensa.

## Probabilidades dos drops comuns

| Raridade | Peso | Chance aproximada |
|---|---:|---:|
| Comum | 6.940 | 69,47% |
| Rara | 2.200 | 22,02% |
| Épica | 700 | 7,01% |
| Lendária | 100 | 1,00% |
| Mítica | 50 | 0,50% |
| Primordial | Fora do sorteio comum | 0% |
| Singular | Fora do sorteio comum | 0% |

Em drops especiais elegíveis, Primordial recebe peso 10 sobre o total 10.000 (0,1%). A Singular é uma recompensa especial condicionada a feito validado, não uma raridade sorteada em atividades comuns.

## Inventário individual

- Nova tabela `cartas_exemplares`: cada registro guarda `user_id`, `card_id`, raridade, poder, origem e data de obtenção.
- O mesmo modelo pode ser possuído em raridades diferentes; cada combinação modelo + raridade representa um exemplar distinto.
- Uma repetição do mesmo modelo na mesma raridade é duplicata e vira Almas ou fragmentos; um drop do mesmo modelo em outra raridade cria outro exemplar.
- `cartas_colecao` permanece como índice agregado de compatibilidade com módulos antigos e sua quantidade acompanha os exemplares distintos.
- O ledger `cartas_recompensas` guarda também `exemplar_id` e poder sorteado para auditoria da recompensa.
- Na inicialização, exemplares legados são criados automaticamente conforme a quantidade armazenada na coleção antiga. Nenhuma carta antiga é apagada.
- O construtor do deck lista cada exemplar individualmente, identifica-o pelo ID e permite escolher qual raridade/poder usar.
- O deck persiste os 12 `card_id` e os 12 `exemplar_id` correspondentes em `exemplar_ids_json`; decks antigos sem IDs migram selecionando o melhor exemplar disponível.
- Cada modelo possui um teto individual de poder calculado a partir do seu poder-base; o teto absoluto é 12.
- A raridade define a faixa inicial, limitada pelo teto do modelo.

## Duplicatas e evolução

Quando o jogador recebe um modelo que já possui:
- 50% de chance de converter a duplicata em Almas;
- 50% de chance de converter a duplicata em fragmentos.

| Raridade sorteada | Almas | Fragmentos |
|---|---:|---:|
| Comum | 5 | 1 |
| Rara | 15 | 2 |
| Épica | 40 | 4 |
| Lendária | 100 | 8 |
| Mítica | 180 | 10 |
| Primordial | 250 | 12 |

Evolução por fragmentos:

| De | Para | Custo |
|---|---|---:|
| Comum | Rara | 20 |
| Rara | Épica | 40 |
| Épica | Lendária | 80 |
| Lendária | Mítica | 160 |

Primordiais e Singulares não evoluem por fragmentos. A evolução atual aumenta o poder dentro da faixa da próxima raridade, respeitando o limite individual do modelo.

## Integrações de atividades

- Zerado aprovado: 1 drop.
- Platina aprovada: 1 drop, sem duplicar o marco automático de zerado.
- Run Soulslike aprovada: 1 drop; desafios especiais habilitam Primordial e Singular.
- Contribuição comunitária aprovada: 1 drop (lore, teoria, descoberta, cronologia, debate, guia, tutorial, FAQ, desafio, sugestão, correção e demais tipos que passam pelo fluxo de aprovação).
- Conta nova recebe 12 drops globais de boas-vindas com modelos distintos, para começar com um deck jogável. Contas antigas com qualquer marcador de kit preservam seu inventário e não recebem um segundo kit.
- Patentes liberadas por XP concedem drops globais idempotentes, não mais cartas fixas de patente. Cartas fixas de patente que já haviam sido entregues por versões anteriores são preservadas e marcadas como recompensa legada.
- Conquistas antigas aprovadas que ainda não possuem evento de recompensa são convertidas em drops globais na primeira sincronização; se a versão anterior já entregou a carta temática daquele marco, ela é preservada e o evento é marcado como legado pago, sem conceder uma segunda carta.
- XP permanece como recompensa adicional, sem ser substituído pelo drop.

## Interface e endpoints

- A API da coleção devolve raridade, poder e ID do exemplar selecionado.
- A API `/api/gwent/exemplars` lista os exemplares individuais.
- A API `/api/gwent/drops/history` expõe os últimos drops, duplicatas e recompensas especiais; o site mostra o histórico pessoal.
- A API `POST /api/gwent/evolve` evolui um exemplar autenticado após validar saldo e propriedade.
- A API `POST /api/gwent/upgrade` lapida um exemplar em +1 poder usando Almas, com validação do limite do modelo.
- O site exibe saldo de fragmentos e ação de evolução no construtor de deck.
- Compra de pacotes e forja direta permanecem desativadas nos endpoints da loja (HTTP 410).

## Compatibilidade e limites conhecidos

- O deck continua exigindo 12 modelos diferentes; o jogador escolhe manualmente qual exemplar de cada modelo vai usar.
- Drops do mesmo modelo em raridades diferentes criam exemplares adicionais; drops repetidos do mesmo modelo na mesma raridade são convertidos em recursos.
- Kits fixos e cartas de patente concedidos por versões antigas permanecem na coleção dos membros; não são removidos durante a migração.
- Os gatilhos de Singular continuam baseados no nome do desafio (“Sem tomar dano”, “No-hit”, “Nível 1” ou “Todos os chefes”). Novos gatilhos devem ser cadastrados explicitamente.
- Almas agora têm uso próprio na lapidação de poder; não podem comprar cartas.
- A validação com Discord, aiosqlite e banco de produção depende do ambiente de execução do bot. O banco existente deve ser copiado antes da implantação.

## Continuação — seleção de exemplares e configuração de feitos

- O mesmo modelo agora pode existir em Comum, Rara, Épica etc. no inventário do mesmo jogador. Só a repetição do mesmo modelo na mesma raridade é tratada como duplicata e convertida em recurso.
- A quantidade agregada em `cartas_colecao` é incrementada quando um drop concede outra raridade do mesmo modelo; `cartas_exemplares` guarda cada exemplar de forma independente.
- O construtor do site mostra cada exemplar separadamente (`Exemplar #ID`) e permite escolher a cópia exata que entra no deck.
- Decks persistem `exemplar_ids_json`, alinhado com `card_ids_json`. O servidor valida que cada exemplar pertence ao jogador e ao modelo informado.
- O snapshot de uma partida usa raridade e poder do exemplar escolhido, em vez de substituir automaticamente pelo exemplar mais forte.
- Novos campos em `sl_challenges` permitem configurar chance Primordial (0,1%) e carta Singular de cada desafio.
- Comandos administrativos: `/sl_admin recompensas_listar` mostra IDs e regras; `/sl_admin recompensa_desafio` configura Primordial e Singular. Desafios antigos continuam com detecção automática pelo nome até serem configurados explicitamente.
- Testes de regressão cobrem modelo em duas raridades e duplicata na mesma raridade.
- Remover um zerado agora tenta reverter também o drop: exemplar não utilizado é retirado; Almas/fragmentos são debitados se o saldo comportar a devolução. A remoção é bloqueada se a carta estiver no deck, tiver sido evoluída/lapidada ou se os recursos da duplicata já tiverem sido gastos.
- O FAQ e o manual da NARA foram atualizados para explicar drops, raridades, evolução, seleção de exemplares e limites de reversão.

- Aprovações de envios públicos de ports e mods também concedem drop global ao autor; cadastros diretos feitos pela equipe não geram drop. A aprovação verifica status pendente e usa chave idempotente por envio.
- As molduras renderizadas localmente agora diferenciam visualmente Mítica (constelações), Primordial (selos solares) e Singular (assinatura assimétrica), além das molduras das raridades inferiores.


## Continuação — auditoria da economia e histórico de progressão

- Criada a tabela `cartas_movimentacoes`, com histórico auditável de lapidação e evolução: exemplar, raridade anterior/posterior, poder anterior/posterior, recurso consumido, quantidade e origem.
- Evolução e lapidação agora registram a movimentação na mesma transação que debita o recurso e atualiza o exemplar.
- A API de histórico retorna também movimentações econômicas; o site reúne drops, duplicatas, evoluções e lapidações em uma única linha do tempo.
- Corrigida a interface para permitir lapidação de exemplares Míticos (150 Almas) e Primordiais (250 Almas), de acordo com as regras já aceitas pelo servidor. Singulares continuam sem lapidação.
- Mantidos os tetos individuais dos modelos e o limite absoluto de 12 de poder.
- O ledger de recompensas agora persiste a origem do drop (zerado, platina, run, contribuição, port, mod, patente, boas-vindas ou feito especial); o histórico da coleção mostra essa origem ao membro.
- A tela de histórico atualiza imediatamente após lapidação e identifica a origem do drop (por exemplo, jogo zerado, platina, run Soulslike, comunidade, port/mod e boas-vindas).
- Adicionado teste de partida simulada com duas instâncias do mesmo modelo em raridades diferentes: o motor mantém o poder e a raridade selecionados ao entrar na partida.


## Consolidação posterior — Mercado de pacotes reativado

- Compra de pacotes voltou a ficar disponível conforme a decisão do projeto: 3 cartas por 120 Denários, até 3 pacotes em 24 horas.
- A compra e as três recompensas são processadas na mesma transação do banco.
- Pacotes usam o mesmo inventário de exemplares, raridades e duplicatas dos drops globais.
- Primordial mantém 0,1% por carta; após 10 cartas Comuns consecutivas, a próxima recebe raridade garantida de Rara ou superior.
- Forja direta permanece desativada; evolução por fragmentos e lapidação por Almas continuam disponíveis.
