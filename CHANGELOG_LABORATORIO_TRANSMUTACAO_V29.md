# V29 — Afinidades e Compatibilidade

## Implementado
- Taxonomia canônica das três facções existentes: Ordem Áurea, Véu Carmesim e Lua Negra.
- Taxonomia de afinidades temáticas: sagrado, fogo, sangue, morte, lua, magia, relâmpago, gravidade, gelo, veneno, ancestral e bestial.
- Taxonomia funcional: ataque, defesa, controle e suporte.
- Classificador determinístico que lê identidade, nome, descrição, facção/tipo, raridade, origem, papel e fileira.
- Validação estrutural de 3 a 5 ingredientes distintos.
- Bloqueio de especiais, líderes, Primordiais, Singulares e cartas pessoais não sacrificáveis.
- Análise de compatibilidade com score explicável de 0 a 100, facção dominante, afinidades e distribuição funcional.

## Interpretação do score
O score é um índice interno de coerência temática e tática. Não é probabilidade de sucesso, não consome materiais e não determina raridade ou poder da carta resultante.

## Limites desta versão
- Afinidades inferidas por palavras-chave são classificação temática inicial; não equivalem a tags canônicas revisadas carta por carta.
- Nenhum ingrediente é consumido.
- Nenhuma chance de sucesso ou economia foi definida.
- Nenhuma carta é gerada.
- Não foram adicionadas habilidades novas nem alterado o motor de batalha.
- A taxonomia de afinidades é uma proposta de sistema para revisão; balanceamento e pesos econômicos continuam pendentes.

## Próxima etapa
V30 — gerador procedural restrito a atributos e efeitos já existentes e aprovados.
