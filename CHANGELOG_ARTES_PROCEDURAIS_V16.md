# NaraBot — Artes procedurais V16

## Diversidade visual
- Adicionadas 12 famílias de cenário (floresta, muralha/catedral, costa inundada, vulcão/forja, necrópole/pântano e geleira/campo de batalha, entre outras variações).
- Adicionados 5 tratamentos climáticos determinísticos: névoa, chuva, cinzas/faíscas, neve e partículas arcanas.
- Adicionados 10 objetos narrativos de cenário (monólito, árvore caída, altar, estandarte, relíquia, portal, coluna, cristal, engrenagem e fogueira).
- A seleção usa o conteúdo/identidade da carta com hash estável, para manter a mesma arte entre renderizações e ampliar a combinação de elementos sem depender apenas da paleta.
- A camada de cenário fica atrás do motivo/personagem principal.
- Artes personalizadas enviadas pelo Ateliê continuam substituindo a arte automática sem receber os elementos procedurais por cima.
- Versão de arte/cache elevada para 16 para invalidar imagens antigas.

## Validação
- `py_compile` executado em `sistemas/arte_cartas.py` e `sistemas/cartas.py`.
- Renderização de teste executada para unidade, especial e arma.

## Limitação
A arte continua sendo vetorial/procedural feita em Pillow. A ampliação reduz repetição visual, mas não equivale a uma ilustração pintada manualmente ou gerada por IA para cada carta.
