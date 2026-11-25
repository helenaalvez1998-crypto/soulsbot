# Narabot V19 — Sistema de Relíquias

## Conteúdo
- Grande Runa de Godrick: +1 de bônus a todas as unidades aliadas em campo.
- Grande Runa dos Não Nascidos: purifica Geada e Podridão dos aliados afetados e concede +1 a cada purificado.
- Runa da Morte: remove até 2 pontos de bônus da unidade inimiga com bônus positivo mais forte em cada fileira.
- Espada da Noite e da Chama: escolha Chama (reduz poder e bônus do inimigo mais forte na fileira) ou Noite (aplica Geada à fileira).
- Lâmina Negra: reduz em 3 o bônus de um inimigo; Escudo bloqueia.
- Algemas de Margit: anula bônus positivos de uma unidade inimiga.

## Regra de uso
Cada jogador pode ativar somente uma carta de Relíquia por partida. As Relíquias são cartas especiais jogadas da mão e não ocupam uma posição de unidade no tabuleiro. O motor mantém `relic_used` por jogador e rejeita uma segunda ativação.

## Observações
- A escolha Noite da Espada da Noite e da Chama é enviada como `target_id="noite"`; a postura Chama é o padrão.
- Para selecionar alvo específico na Lâmina Negra ou nas Algemas de Margit, enviar `target_id` com o ID da unidade; sem isso, o motor escolhe automaticamente um alvo válido.
- O balanceamento fino das Primordiais permanece fora do escopo desta versão.
