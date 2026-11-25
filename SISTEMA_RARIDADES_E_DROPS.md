# Especificação — Raridades, drops e evolução do Cartas do Coliseu

## Princípios

1. Toda atividade recompensável concede XP e pode conceder um drop de carta adicional.
2. A carta vem do catálogo global, não necessariamente do jogo registrado.
3. O drop é entregue diretamente à coleção.
4. A raridade pertence ao exemplar, não apenas ao modelo. Um mesmo modelo pode existir na coleção do jogador em várias raridades ao mesmo tempo. Um novo drop do mesmo modelo em raridade diferente cria um exemplar; a repetição do mesmo modelo na mesma raridade é duplicata e gera Almas ou fragmentos.
5. Primordial é individual por jogador e depende de condição especial de obtenção.
6. Singular é individual por jogador e depende de feito extraordinário validado.
7. Duplicatas são convertidas em Almas ou fragmentos; fragmentos evoluem exemplares existentes.

A concessão de Singular está atualmente vinculada a desafios com os termos “Sem tomar dano”, “No-hit”, “Nível 1” ou “Todos os chefes” no nome. Cada categoria entrega um modelo Singular próprio; outros desafios extraordinários elegíveis entregam O Primeiro Juramento. Esses gatilhos podem ser refinados para uma configuração explícita de desafio em uma próxima etapa.

## Raridades

Comum, Rara, Épica, Lendária, Mítica, Primordial e Singular.

## Fluxo de recompensa

`atividade submetida -> análise/moderação -> aprovação -> XP + drop -> registro idempotente -> coleção/exemplar ou recurso de duplicata`

Registros pendentes e rejeitados não geram drop. Uma aprovação só pode ser processada uma vez por chave de evento.

## Drops de entrada e progressão

- Contas novas recebem 12 drops globais de boas-vindas, com modelos distintos, para começar com um deck jogável.
- Patentes liberadas por XP concedem drops globais, sem selecionar carta fixa; cartas de patente já entregues por versões anteriores são preservadas e não geram drop retroativo adicional.
- Conquistas aprovadas antigas sem evento de recompensa são convertidas em drops globais na sincronização inicial; cartas temáticas que já haviam sido entregues por versões anteriores são preservadas e não geram uma segunda recompensa.
- Kits fixos e cartas de patente já entregues por versões antigas são preservados; a migração não os remove.

## Atividades cobertas

- Registro de jogo zerado aprovado.
- Registro de platina aprovado.
- Run Soulslike aprovada.
- Contribuições comunitárias aprovadas, incluindo lore, teoria, descoberta, cronologia, debate, guia, tutorial, FAQ e desafios.

## Probabilidades

Drops comuns: Comum 69,47%; Rara 22,02%; Épica 7,01%; Lendária 1,00%; Mítica 0,50%. Primordial fica fora da tabela comum e recebe 0,1% apenas em drops de feitos especiais elegíveis. Singular é recompensa especial condicionada ao feito validado.

## Exemplares e atributos

Cada exemplar persiste raridade, poder, origem e data. O poder é sorteado na faixa da raridade e limitado pelo teto do modelo. O teto individual é derivado do poder-base do modelo e não ultrapassa 12.

## Duplicatas

A duplicata converte-se em Almas ou fragmentos, com probabilidade de 50% para cada resultado. O valor depende da raridade do drop.

## Evolução

Comum -> Rara: 20 fragmentos.
Rara -> Épica: 40 fragmentos.
Épica -> Lendária: 80 fragmentos.
Lendária -> Mítica: 160 fragmentos.

Primordial e Singular não evoluem por fragmentos. Almas lapidam exemplares em +1 poder dentro da faixa da raridade e do teto do modelo. Custos: Comum 10, Rara 20, Épica 40, Lendária 80, Mítica 150 e Primordial 250 Almas. Singulares e cartas especiais não podem ser lapidadas.

## Persistência e migração

A tabela legada `cartas_colecao` continua preservada. A tabela `cartas_exemplares` é criada automaticamente e recebe uma migração dos exemplares legados, sem apagar coleção, XP, moedas, decks ou histórico. O deck persiste a escolha do `exemplar_id` de cada modelo em `exemplar_ids_json`, com fallback para o melhor exemplar em decks antigos.

## Configuração administrativa de desafios Soulslike

A tabela `sl_challenges` possui `coliseu_primordial_drop` (-1 = automático por nome; 0 = desativado; 1 = chance de 0,1%) e `coliseu_singular_card_id` (ID de uma Singular ou `none`). A administração consulta IDs com `/sl_admin recompensas_listar` e configura cada desafio com `/sl_admin recompensa_desafio`.

Desafios antigos continuam reconhecendo automaticamente “Sem tomar dano”/“No-hit”, “Nível 1” e “Todos os chefes” até que a administração defina explicitamente a configuração. A configuração Singular `none` desativa a concessão automática para aquele desafio.

## Seleção de exemplares no deck

O construtor lista cada exemplar separadamente e o jogador escolhe qual exemplar de cada modelo será usado. O deck exige 12 modelos diferentes e persiste a lista alinhada de IDs de modelo e exemplar. O servidor valida propriedade e correspondência antes de salvar; snapshots de partidas carregam raridade e poder do exemplar escolhido.

## Auditoria da economia e histórico

O ledger `cartas_recompensas` registra a origem de cada drop, além da raridade, poder, exemplar e conversão de duplicata. A tabela `cartas_movimentacoes` registra evolução e lapidação com estado anterior/posterior e recurso consumido. O histórico exibido no site combina drops, duplicatas, evoluções e lapidações. A migração cria as estruturas sem remover os registros antigos.


## Recompensas do próprio Coliseu (atualização v11)

- Vitória em partida Gwent concede um drop global adicional ao vencedor.
- O drop normal de vitória tem limite de 3 por jogador a cada janela móvel de 24 horas; XP, Denários e MMR continuam sendo calculados normalmente.
- Empates e derrotas mantêm as recompensas de participação já existentes (XP/Denários/MMR), mas não concedem drop de vitória.
- Marcos cumulativos de 5, 10, 25, 50 e 100 vitórias concedem um drop adicional único por conta, registrado com chave de evento própria.
- A concessão do drop ocorre na mesma transação que finaliza a partida e registra as recompensas; retries não duplicam cartas.
- O histórico da arena mostra raridade, modelo, exemplar ou conversão de duplicata recebida.
- `cartas_gwent_rewards` agora armazena `reward_xp`, `drop_event_key` e `milestone_drop_event_key`; a migração adiciona as colunas também em bancos existentes.

## Cobertura das habilidades

O motor mantém conjuntos de cobertura para habilidades de unidade/Primordial e cartas táticas especiais. O teste de regressão compara esses conjuntos com o catálogo `HABILIDADES` para impedir que uma habilidade seja cadastrada sem ramo correspondente no motor de batalha.
