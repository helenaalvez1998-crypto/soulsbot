# Gwent V76 — Consistência e leitura das cartas

## O que foi corrigido

- Cartas de recompensa geradas por jogos agora usam nomes e territórios coerentes com a própria facção.
- Cada recompensa recebe um selo curto de identidade no título. Isso evita que cartas de jogos diferentes pareçam ser a mesma carta quando possuem habilidades distintas.
- A descrição narrativa agora explica a identidade da carta e, quando existe habilidade, cita a habilidade correta. Cartas sem habilidade deixam isso explícito.
- A versão das artes foi atualizada para invalidar composições antigas e gerar novamente as imagens com os dados corrigidos.
- A inspeção de combate agora explica, em linguagem direta, a diferença entre poder-base, bônus e poder atual. Também deixa explícito que a potência da raridade não é somada ao poder.

## Como interpretar os números

- **Poder-base:** número impresso na carta.
- **Bônus:** pontos ganhos ou perdidos durante a partida.
- **Poder atual:** poder-base + bônus, respeitando o mínimo de 1.
- **Potência da raridade:** amplia efeitos de habilidade dentro dos limites da regra; não é poder de ataque.

## Arquivos alterados

- `sistemas/cartas.py`
- `site/app.js`
- `tests/test_gwent_reward_identity_v76.py`

## Compatibilidade

A alteração preserva o cálculo original de tipo, raridade, poder e habilidade das recompensas. Não muda o motor de combate nem recalcula partidas já encerradas. Ela corrige a geração de identidade/lore das recompensas e torna a leitura da inspeção mais clara.
