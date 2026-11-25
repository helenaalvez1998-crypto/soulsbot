# V7 — Prompts de ilustração contextualizados para Elden Ring

## Escopo

Esta revisão altera somente a geração do briefing textual usado pelo Ateliê para criar/substituir a ilustração da carta. Não altera a moldura Python/Pillow, os ícones, o painel de texto, o recorte da arte, o fluxo de upload/substituição, as regras do Gwent ou o banco de dados.

## Alterações

- Atualizadas as diretrizes visuais das três facções: Ordem Áurea, Véu Carmesim e Lua Negra.
- Adicionadas referências ambientais condicionais para Leyndell/Altus, Mohgwyn, Liurnia/Cariana, Haligtree, Caelid, Farum Azula, Cidades Eternas, Gelmir/Volcano Manor, Limgrave/Stormveil, Montanhas dos Gigantes e Reino das Sombras.
- A localização só é sugerida quando nome, descrição, habilidade ou cena da carta dão suporte; o prompt evita misturar regiões sem relação.
- Reforçada a preservação da aparência, silhueta, equipamento e identidade canônica de personagens nomeados de Elden Ring.
- As três facções são descritas como alinhamentos próprios do NARABOT, sem reescrever a filiação oficial dos personagens.
- Storyboards antigos do cenário genérico deixam de sobrepor as informações canônicas das cartas Elden Ring.
- Removido o campo de custo do briefing de imagem; o jogo não exibe custo na carta.
- Mantidas a saída de ilustração isolada em paisagem 5:4 e a substituição manual da arte pelo Ateliê.

## Arquivos

- `sistemas/atelie_coliseu.py`
- `tests/test_elden_art_prompts.py`

## Validação

Testes unitários específicos verificam as três facções, contexto de regiões, ausência do custo e ausência de cenário Elden Ring em cartas de outra origem.
