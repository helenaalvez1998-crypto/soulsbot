# V31 — Validação e Balanceamento

## Implementado
- Validador estrito para IDs, nomes, facção/tipo, função/fileira, afinidades, raridade, poder, custo, origem e proteção.
- Habilidades limitadas ao conjunto comum já existente no motor.
- Matriz de compatibilidade entre habilidades e função tática.
- Orçamento de poder: habilidades classificadas como impacto maior não podem usar o teto da raridade e sofrem redução de 1 no sorteio.
- Auditoria de lote para detectar definições inválidas e IDs duplicados; nomes repetidos geram alerta.
- Monitor cumulativo 50/50 com amostra mínima de 20 e alerta quando o desvio da proporção de unidades com habilidade ultrapassa 5 pontos percentuais.
- Monitoramento não altera cartas anteriores nem força uma carta individual a compensar a distribuição.

## Política de balanceamento
- 50/50 é métrica cumulativa sobre unidades geradas, não garantia estatística em amostras pequenas.
- A matriz de habilidade/função é uma primeira política de elegibilidade, sujeita a playtests.
- O redutor de poder é uma salvaguarda estrutural, não evidência de equilíbrio competitivo.
- O validador não substitui partidas simuladas, telemetria ou revisão humana.

## Não implementado
- Persistência de telemetria cumulativa no banco.
- Interface de revisão/moderação.
- Testes reais de batalha com cartas geradas.
- Geração de arte e publicação.
- Execução transacional de transmutação.
