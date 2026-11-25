# Auditoria de clareza das cartas — V79

## Escopo

Revisão das explicações exibidas nas cartas, usando o catálogo e o motor de combate do próprio projeto como fonte. Esta versão dá continuidade à V78 e concentra-se em tornar curto e direto o texto do bônus de raridade.

## Alteração de linguagem

Para cartas cujo bônus de raridade reforça alterações numéricas já feitas pela habilidade, o texto passou a seguir este padrão:

> Raridade Mítica: reforça até 2 bônus já alterados pela habilidade: +1 nos positivos ou -1 nos negativos. Não muda o poder inicial nem os escudos.

Para cartas que recebem o reforço por sinergia, o texto informa que ele ocorre ao completar um combo compatível.

As cartas com efeitos específicos de raridade — por exemplo, segunda marca, compra, proteção, movimento ou recuperação — mantêm explicações próprias, porque a raridade modifica esses efeitos de forma diferente. Não seria correto aplicar a elas uma descrição genérica.

## Mecânica confirmada no código

A potência por raridade continua sendo um limite por ativação, aplicado somente a alterações numéricas de bônus que a habilidade já produziu. Para cada alteração selecionada, o motor soma 1 ao bônus positivo ou reduz em 1 o bônus negativo, respeitando os limites existentes. Não cria alvos nem aumenta poder-base ou escudos.

Limites preservados: Comum 0; Rara 1; Épica 1; Lendária 2; Mítica 2; Primordial 3; Singular 3.

## Integridade

Nenhuma mecânica, valor de balanceamento, habilidade, ID, custo, poder-base, raridade, condição, alvo ou duração foi alterada nesta revisão. Foram modificados apenas os textos explicativos do bônus genérico de raridade.

## Testes

Executados:
- `tests/test_gwent_catalog_audit_v77.py`
- `tests/test_gwent_expansao_v75.py`
- `tests/test_gwent_competitivo_v74.py`
- `tests/test_elden_gwent.py`

Resultado: **53 testes aprovados e 7 subtestes aprovados**. A suíte completa do projeto não foi executada.
