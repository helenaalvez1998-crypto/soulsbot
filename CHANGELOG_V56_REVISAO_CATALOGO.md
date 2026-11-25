# NARABOT V56 — Revisão de identidade, relíquias e catálogo

## Alterações

- Separado o alinhamento narrativo individual da carta do tipo mecânico (`Força`, `Destreza`, `Magia`).
- Blaidd, o Meio-Lobo, passa a exibir Lua Negra como alinhamento narrativo, preservando `Destreza` como tipo mecânico.
- Carrasco de Volcano Manor passa a exibir Véu Carmesim como alinhamento narrativo, preservando `Força` como tipo mecânico.
- O cálculo da facção predominante do deck permanece baseado no tipo das unidades, conforme as regras atuais.
- Renomeada a Relíquia Singular `gwent_singular_primeiro` para “Juramento Primordial do Crisol”, eliminando a colisão visual com a Especial “Juramento do Crisol”; o ID interno foi preservado.
- Reescritas as descrições das seis Relíquias para explicitar condição, alvo, magnitude e bloqueios de acordo com os handlers do motor.
- Adicionadas seis cenas de arte específicas para as Relíquias que não tinham prompt dedicado.

## Arquivos alterados

- `sistemas/cartas.py`
- `sistemas/atelie_coliseu.py`
- `tests/test_elden_art_prompts.py`
- `tests/test_card_catalog_quality.py` (novo)

## Compatibilidade

- IDs internos das cartas preservados.
- Tipos mecânicos, poderes, raridades, custos e habilidades não foram alterados.
- Nenhuma regra de batalha foi modificada.
- As facções de composição do deck continuam calculadas pelo tipo predominante; os dois alinhamentos individuais são metadados narrativos exibidos na carta.

## Validação

`python -m unittest discover -s tests -v`

Resultado: **60 testes aprovados**.
