# Auditoria de linguagem das cartas — V78

## Escopo

Revisão baseada no catálogo e no motor de combate existentes. O objetivo foi tornar as informações exibidas ao jogador mais diretas, sem criar habilidades, alterar valores ou mudar as condições de ativação.

## O que foi alterado

- Simplificadas as explicações das habilidades gerais em `sistemas/cartas.py`.
- Simplificadas as explicações das habilidades de identidade em `sistemas/gwent.py`, preservando gatilhos, alvos, quantidades, limites e duração descritos pelo motor.
- Corrigidas descrições das seis cartas V75 que não têm habilidade individual: agora informam que dependem de combos, em vez de sugerir um efeito próprio.
- As cartas de recompensa por jogo e por patente agora apresentam informação de habilidade coerente com a habilidade efetivamente atribuída; cartas sem habilidade informam isso claramente.
- A explicação do bônus de raridade foi reescrita para linguagem direta. Ela informa que, em cada ativação, a raridade pode reforçar um número limitado de alterações de bônus já feitas pela habilidade: soma +1 às alterações positivas ou -1 às negativas. Não altera poder inicial nem escudos.

## Mecânicas preservadas

- Nenhum valor de `RARITY_EFFECT_BUDGET` foi alterado: Comum 0; Rara 1; Épica 1; Lendária 2; Mítica 2; Primordial 3; Singular 3.
- Não foram alterados poderes-base, custos, raridades, IDs, condições, alvos, duração, efeitos de combate, combos ou regras de aplicação da raridade.
- A potência continua sendo um orçamento por ativação, distribuído entre alterações numéricas de bônus que a habilidade já produziu. Não cria alvos nem efeitos novos.

## Validação

Testes direcionados executados:

- `tests/test_gwent_catalog_audit_v77.py`
- `tests/test_gwent_expansao_v75.py`
- `tests/test_gwent_competitivo_v74.py`
- `tests/test_elden_gwent.py`

Resultado: **53 testes passaram e 7 subtestes passaram**.

A suíte completa do projeto não foi executada nesta revisão.
