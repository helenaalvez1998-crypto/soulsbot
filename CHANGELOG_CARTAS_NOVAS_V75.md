# Narabot V75 — Expansão de 12 cartas

## Resumo
- Adicionadas 12 unidades permanentes ao catálogo: quatro para cada facção.
- Distribuição: 6 cartas Raras e 6 Épicas; cada facção recebe duas de cada raridade.
- Preservada a regra de distribuição do catálogo: 6 das novas unidades são peças sem habilidade individual e 6 possuem habilidade de identidade.
- As 12 cartas entram em `CARTAS_PACOTE`, `CARTAS_POR_ID` e `CARTAS_PACOTE_POR_RARIDADE`; ficam disponíveis nos fluxos normais de obtenção.
- Criadas 12 cenas individuais em `CENAS_ELDEN_POR_ID`, com direção visual correspondente ao universo e à facção.
- `VERSAO_ARTES` e `CARD_IMAGE_VERSION` atualizadas de 27 para 28.

## Novas cartas

### Ordem Áurea
| Carta | Poder | Raridade | Fileira | Efeito |
|---|---:|---|---|---|
| Veterano do Juramento Dourado | 4 | Rara | Corpo a corpo | +1 para si; se houver aliado na fileira, +1 ao aliado mais fraco. |
| Guardião do Crisol Menor | 4 | Rara | Corpo a corpo | Peça de combo, sem habilidade individual. |
| Confessora da Graça Serena | 5 | Épica | Cerco | Purifica até dois aliados da fileira e concede +1 a cada um; sem alvo afetado, fortalece o aliado mais fraco em +1. |
| Arauto do Estandarte Áureo | 5 | Épica | Longa distância | Peça de combo, sem habilidade individual. |

Combo **Juramento do Crisol e da Graça**: requer duas cartas com as duas tags complementares; a carta que completa recebe +2.

### Véu Carmesim
| Carta | Poder | Raridade | Fileira | Efeito |
|---|---:|---|---|---|
| Acólito da Dinastia Sanguínea | 4 | Rara | Longa distância | Aplica Sangramento ao inimigo mais forte da fileira; a segunda marca causa Hemorragia e -2 de bônus. |
| Devota da Hemorragia | 4 | Rara | Cerco | Peça de combo, sem habilidade individual. |
| Carrasco da Procissão Carmesim | 5 | Épica | Corpo a corpo | Sacrifica o aliado mais fraco da fileira e recebe bônus igual ao poder efetivo dele, limitado a +3; sem aliado, recebe +1. |
| Caçador das Catacumbas de Mohgwyn | 5 | Épica | Longa distância | Peça de combo, sem habilidade individual. |

Combo **Banquete da Hemorragia**: requer as duas tags complementares; a carta que completa recebe +2.

### Lua Negra
| Carta | Poder | Raridade | Fileira | Efeito |
|---|---:|---|---|---|
| Oráculo Gélido de Sellia | 4 | Rara | Cerco | Aplica Geada ao inimigo mais forte da fileira; se já tinha uma marca, completa a segunda e recebe +1. |
| Cartógrafo das Cidades Eternas | 4 | Rara | Longa distância | Peça de combo, sem habilidade individual. |
| Graviturgista de Nokron | 5 | Épica | Cerco | Reduz em 1 o bônus de até dois inimigos com bônus positivo na fileira; se atingir dois, recebe +1. |
| Guardiã do Juramento Lunar | 5 | Épica | Corpo a corpo | Peça de combo, sem habilidade individual. |

Combo **Convergência da Geada Lunar**: requer as duas tags complementares; a carta que completa recebe +2.

## Limites de balanceamento
- Cada combo novo exige duas cartas e duas tags distintas.
- Cada combo pode ativar uma vez por jogador por rodada.
- O combo concede +2-base somente à unidade que o completa; não concede bônus global à fileira. O orçamento de raridade existente pode acrescentar +1 a uma alteração numérica elegível, respeitando o limite de uma amplificação por carta/ativação.
- Efeitos de alvo são limitados à mesma fileira e, quando aplicável, a no máximo dois alvos.
- Sacrifício do Carrasco tem ganho máximo de +3 e remove efetivamente a unidade sacrificada.
- As seis peças sem habilidade individual preservam a proporção de metade das unidades de força pura no catálogo.
- A amplificação numérica por raridade continua obedecendo ao orçamento já existente no motor; nenhuma regra global foi aumentada.

## Compatibilidade
- Nenhuma migração de banco de dados.
- As cartas novas passam a integrar o pool de obtenção; jogadores não recebem cópias retroativamente.
- Decks salvos e partidas em andamento não são reescritos.
