# Relatório de design e balanceamento — expansão V75

A expansão adiciona 12 unidades sem elevar os limites globais do motor. Cada facção recebe quatro cartas com curva de poder 4/4/5/5, duas Raras e duas Épicas.

## Filosofia
- Ordem Áurea: reforço pontual, purificação e formação.
- Véu Carmesim: preparação de Sangramento, Hemorragia e sacrifício com custo real.
- Lua Negra: Geada, controle de bônus e posicionamento entre fileiras.

Cada facção recebe duas cartas com habilidade individual e duas peças de combo sem habilidade individual. Isso mantém a regra de distribuição de 50% de unidades sem habilidade especial, evitando que toda carta nova gere valor adicional por si só.

## Combos
Os três combos requerem duas tags distintas presentes em pelo menos duas unidades no campo. São registrados em `synergy_used`, portanto cada combo pode disparar uma vez por jogador por rodada. O bônus-base de +2 vai somente para a carta que completa o combo; não há bônus de equipe. A regra global de raridade pode acrescentar +1 a uma alteração numérica elegível (uma amplificação por ativação), por isso uma peça Rara/Épica sem habilidade individual pode chegar a +3 no próprio bônus ao completar o combo.

## Avaliação dos efeitos
- Veterano: valor próprio moderado e um reforço de +1 em aliado; exige presença prévia na fileira para o segundo valor.
- Confessora: purificação limitada a dois alvos; a alternativa sem estados negativos é apenas +1 em um aliado.
- Acólito: uma marca por entrada; a Hemorragia só acontece se o alvo já tiver Sangramento.
- Carrasco: remove permanentemente o aliado mais fraco da fileira e limita o ganho a +3; não é um buff sem custo.
- Oráculo: Geada em um único alvo; o bônus pessoal só aparece ao completar a segunda marca.
- Graviturgista: só afeta bônus positivos, no máximo dois inimigos, e só ganha +1 quando alcança ambos.

## Testes
- 191 testes passaram, 1 foi ignorado e 199 subtestes passaram na suíte ampla, excluindo o módulo de renderização de molduras e o módulo de execução de transmutação com teste de integração demorado.
- No módulo de molduras, 4 testes adicionais passaram; 2 testes visuais demorados foram separados.
- No módulo de transmutação, 7 testes adicionais passaram; 1 teste de execução longa foi separado.
- 81 testes focados de catálogo, prompt, motor, distribuição de raridade e expansão passaram com 193 subtestes.
- Python e JavaScript passaram na checagem de sintaxe.

Esses resultados verificam os contratos e efeitos unitários. Não substituem uma simulação competitiva de milhares de partidas completas; o balanceamento final ainda deve ser observado em partidas reais.
