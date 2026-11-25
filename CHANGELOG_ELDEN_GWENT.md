# Changelog — Edição Elden Ring do Gwent

## Alterações
- Tema do catálogo e da interface migrado para Elden Ring.
- Facções renomeadas para Ordem Áurea, Casa Cariana e Dinastia Mohgwyn, com mapeamento ajustado aos tipos Força, Magia e Destreza.
- Líderes e nomes das cartas atualizados preservando os IDs existentes.
- Paletas das cartas atualizadas para ouro, azul lunar e vermelho-sangue.
- Adicionados estados de Sangramento, Geada, Podridão Escarlate e Loucura.
- Adicionado contrajogo de fogo: Chama do Gigante remove Geada das unidades aliadas e concede +1.
- Adicionada invocação espiritual: Lobos Espirituais, 3 de poder, colocados na fileira escolhida.
- Adicionados combos da Árvore Áurea, Lua Cariana e Dinastia de Sangue.
- Cada unidade recebeu uma fileira tática fixa, independente da facção; o servidor rejeita posicionamento em fileira diferente. Movimentação continua permitida somente por efeitos específicos.
- A interface de jogada bloqueia a escolha de fileira para unidades e só solicita fileira às táticas que realmente precisam dela.
- Habilidades de identidade substituem habilidades genéricas ocultas, eliminando bônus duplos não descritos.
- O poder efetivo agora inclui clima em todas as verificações de alvo e seleção de unidades.
- Podridão Escarlate e Loucura ganharam efeitos distintos na segunda marca.
- Passiva de facção equalizada: primeira unidade da facção recebe +1 por rodada.
- Textos de habilidades gerais e táticas revisados para declarar alvo, limite, duração e efeito secundário sem divergência com o motor.
- Versão das artes elevada para 22 para renovar o cache após a revisão das fileiras e descrições.
- Ajustado Contragolpe para +2 quando o jogador está atrás, diferenciando-o de Retaliação (+1).
- Corrigidos textos de cartas especiais para explicitar poder-base versus poder efetivo e restrições de alvo.
- Corrigida a exibição do poder efetivo na arena: clima, resistência e estados agora usam a mesma fórmula do servidor; marcadores visuais exibem estados ativos.
- Versão das artes incrementada para regenerar o cache com as novas facções e paletas.

## Compatibilidade
IDs antigos de cartas foram mantidos. Não há migração destrutiva de inventário, exemplares, decks ou histórico.

## Testes
`python -m unittest discover -s tests -v` — 18 testes aprovados após a revisão de coerência das regras e efeitos.
