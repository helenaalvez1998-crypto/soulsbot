# Auditoria do catálogo de cartas — revisão V77

## Escopo verificado

Foram revisadas as definições estáticas e os geradores dinâmicos do catálogo:

- 107 cartas da coleção principal, incluindo as 12 unidades da expansão V75;
- 5 cartas Primordiais;
- 10 recompensas de patente;
- gerador de recompensas por jogos concluídos e platinados;
- preparação de cartas para o motor de combate;
- habilidades gerais, habilidades de identidade, bônus de raridade, sinergias e passivas de facção.

Total estático conferido: **122 cartas**. As recompensas por jogos são geradas dinamicamente e foram verificadas com dezenas de combinações de origem e marco.

## Correções realizadas

### 1. Habilidades e descrições

- A tela de inspeção agora mostra a habilidade de identidade e também a habilidade geral quando uma carta possui as duas. Antes, a habilidade de identidade escondia a habilidade geral, embora o motor executasse ambas.
- As cartas selecionadas pelo balanceamento V18 para não possuir habilidade ativa tiveram suas descrições ajustadas para não prometer efeitos que o motor remove.
- As 12 cartas V75 foram conferidas conforme o desenho existente: seis possuem habilidade de identidade e seis são peças de combo. Esse desenho foi preservado.
- A explicação de potência da raridade agora diferencia cartas com habilidade própria de cartas que dependem de combo. Também esclarece que a potência não aumenta poder-base nem escudos.

### 2. Facções e passivas

- Foram adicionadas correções de facção para personagens e grupos cuja identidade narrativa não corresponde ao tipo de combate padrão.
- O cálculo da passiva de facção agora consulta a facção real da carta, em vez de inferi-la apenas de Força, Destreza ou Magia.
- Habilidades que verificam a facção do adversário ou dos aliados agora usam o campo de facção resolvido quando a regra fala de Ordem Áurea, Lua Negra ou Véu Carmesim.
- Placidusax recebeu a mesma facção narrativa nas duas cartas que representam o personagem.

### 3. Recompensas dinâmicas

- Títulos de recompensas por jogos agora combinam personagem e epíteto do mesmo arquétipo, evitando misturas como um recusante de Volcano Manor com um título específico da Dinastia Mohgwyn.
- Recompensas de patente usam nomes compatíveis com o tipo/facção e um selo determinístico para manter títulos únicos.
- Os cálculos originais de raridade, poder, habilidade e identificador das recompensas foram preservados.

### 4. Correções de lore

- A Assassina da Faca Negra agora está no feminino; as Assassinas da Faca Negra são descritas no lore como mulheres Numen ligadas a Marika.
- A Grande Runa de Godrick é descrita como fragmento do Anel Prístino, não como fragmento da Ordem Áurea.
- A Lâmina Negra foi separada textualmente das adagas das Assassinas da Faca Negra: a Lâmina Negra é a arma de Maliketh.
- A Espada da Noite e da Chama agora é descrita com seus dois ataques corretos: magia e fogo, sem atribuir à arma uma chama dourada.

## Regras preservadas

- Não foram alteradas as faixas de poder por raridade.
- Não foram alterados os valores-base de poder das cartas estáticas.
- Não foram alterados os requisitos dos combos V75.
- As seis cartas V75 de combo continuam sem habilidade de identidade individual.
- Os identificadores das cartas existentes foram preservados.
- Nenhum dado do banco de dados foi migrado ou apagado.

## Validação

A suíte direcionada executada nesta revisão passou:

- **53 testes aprovados**;
- **7 subtestes aprovados**;
- sintaxe JavaScript validada com `node --check`;
- módulos Python compilados com `py_compile`.

A suíte completa do projeto não foi declarada como aprovada; a validação registrada aqui cobre os testes de catálogo, expansão V75, Gwent competitivo e integração de combate Elden/Gwent.

## Referências externas de lore consultadas

- [Assassinas da Faca Negra](https://eldenring.wiki.gg/wiki/Black_Knife_Assassin) — grupo formado por mulheres Numen ligadas a Marika.
- [Noite das Facas Negras](https://eldenring.wiki.gg/wiki/Night_of_Black_Knives) — Ranni roubou o fragmento da Runa da Morte e o usou para imbuir as armas das assassinas.
- [Maliketh](https://eldenring.wiki.gg/wiki/Maliketh) — guardião da Runa da Morte, selada em sua lâmina; Gurranq consome Raiz da Morte.
- [Grande Runa de Godrick](https://eldenring.wiki.gg/wiki/Godrick%27s_Great_Rune) — fragmento do Anel Prístino, também chamado de anel-âncora.
- [Espada da Noite e da Chama](https://eldenring.wiki.gg/wiki/Sword_of_Night_and_Flame) — arma da Mansão Cariana com ataques de magia e fogo.
- [Placidusax](https://eldenring.wiki.gg/wiki/Dragonlord_Placidusax) — antigo Lorde Prístino que aguarda o retorno do deus que o abandonou.
