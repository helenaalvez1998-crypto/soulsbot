# V53 — Progressão exclusiva de potência por raridade

## Alteração

A escala de potência de raridade agora é estritamente crescente e não possui valores repetidos:

| Raridade | Potência |
|---|---:|
| Comum | 0 |
| Rara | 1 |
| Épica | 2 |
| Lendária | 3 |
| Mítica | 4 |
| Primordial | 5 |
| Singular | 6 |

## Comportamento

- `potencia_raridade` continua sendo um orçamento de ampliação de habilidades, não poder-base nem ataque direto.
- A ampliação continua limitada pela lógica e pelos tetos individuais de cada efeito.
- Os textos de cartas preparados pelo motor recebem o novo valor e as descrições derivadas da raridade.
- A execução que elimina unidades mantém seu teto explícito de 6 de poder efetivo; o aumento da raridade não remove esse limite.
- Não foram alterados custos, faixas de poder-base, probabilidades de obtenção, regras de líderes ou Relíquias.

## Validação

- `tests/test_elden_gwent.py`: 21 passed, 7 subtests passed.
- A suíte completa foi iniciada, mas não concluiu dentro do limite de execução desta sessão; portanto, não é declarada como aprovada.
