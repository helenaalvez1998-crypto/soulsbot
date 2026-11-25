# Gwent do Coliseu — edição Elden Ring

## Objetivo da edição

A edição substitui a identidade fictícia anterior por uma ambientação inspirada nas Terras Intermédias. O motor continua sendo um jogo de cartas estratégico no formato de Gwent: três fileiras, gestão de mão, melhor de três rodadas, clima, líderes, descarte e combos.

Os IDs internos das cartas existentes foram preservados para não quebrar inventários, exemplares, decks salvos, histórico de partidas ou referências de artes. O catálogo ganhou seis cartas táticas novas.

## Facções

| Facção | Tipo de unidade | Identidade estratégica |
|---|---|---|
| Ordem Áurea | Força | Luz, Lei e Fé; formação, escudos, resistência e proteção dos juramentados |
| Véu Carmesim | Destreza | Sangue, Sacrifício e Heresia; sangramento, rituais e pressão crescente |
| Lua Negra | Magia | Magia, Cosmos e Segredos; feitiçaria lunar, gravidade, geada e controle |

A facção do deck é determinada pelo tipo predominante das unidades. Cartas especiais não contam para a maioria. Em caso de empate, o motor mantém o critério determinístico anterior. A primeira unidade da facção escolhida jogada em cada rodada recebe +1 de poder; o bônus é igual para as três facções.

### Líderes

- **Ordem Áurea:** Godfrey, Sentinela Áurea e Guardião de Leyndell.
- **Véu Carmesim:** Mohg, Cavaleiro Carmesim e Nobre Sanguíneo.
- **Lua Negra:** Ranni, Rennala e Mestra Cariana.

O líder continua sendo escolhido no deck e pode ser ativado uma vez por partida. Cada líder permanece vinculado à facção e seu efeito é resolvido pelo servidor.

## Regras principais da partida

1. Cada jogador usa um deck de 12 cartas únicas: 10 começam na mão e 2 ficam na reserva.
2. Na preparação, cada jogador pode trocar até duas cartas.
3. A partida é melhor de três: vence quem conquistar duas coroas.
4. Cada unidade possui uma fileira obrigatória definida pelo seu papel tático: corpo a corpo, longa distância ou cerco. A facção não determina sozinha a fileira; unidades da mesma facção podem ocupar fileiras diferentes.
5. O servidor rejeita uma unidade jogada em fileira diferente da indicada na carta. Cartas especiais que movem unidades são exceções explícitas: a unidade pode ser reposicionada pelo efeito, não por escolha livre ao ser jogada. Invocações criadas por efeitos usam a fileira escolhida pelo próprio efeito.
6. Cartas especiais que exigem uma fileira exibem essa escolha; táticas sem alvo de fileira não solicitam uma escolha inútil.
7. O clima afeta o poder efetivo das unidades na fileira atingida. Resistência climática reduz a penalidade.
8. Cartas especiais resolvem seus efeitos e vão para o descarte; não ocupam uma fileira como unidade.
9. O jogador pode passar. Depois de passar, não pode voltar a jogar naquela rodada. A rodada termina quando ambos passam ou ficam sem cartas.
10. Ao fim da rodada, as unidades comuns vão para o descarte. A habilidade Sobrevivente mantém a unidade elegível mais forte em campo; seus bônus temporários e estados negativos são limpos.
11. O servidor valida mão, turno, fileira permitida, alvos, efeitos, pontuação e resultado. O navegador não decide o resultado da partida. A interface mostra poder efetivo, penalidade climática, resistência e marcadores de estado usando a mesma fórmula do servidor.

### Passiva de facção

A primeira unidade da facção principal do deck jogada em cada rodada recebe +1 de poder. O bônus é idêntico para Ordem Áurea, Lua Negra e Véu Carmesim. Ele é aplicado uma única vez por jogador a cada rodada.

## Estados negativos

Os estados são aplicados por cartas táticas. Cada um altera poder efetivo ou bônus conforme sua regra; a pontuação de uma unidade nunca fica abaixo de 1.

| Estado | Regra do motor | Contrajogo |
|---|---|---|
| Sangramento | A primeira aplicação marca a unidade. Na segunda, reduz seu bônus em 2 (mínimo -2) e remove as marcas | Reaplicar a mesma tática é necessário para disparar a hemorragia |
| Geada | Cada marca reduz 1 de poder efetivo, até 2 | Chama do Gigante remove Geada das suas unidades e concede +1 a cada unidade purificada |
| Podridão Escarlate | Cada marca reduz 1 de poder efetivo; a segunda também corrói 1 ponto de bônus positivo, se houver | Limpeza de estados por efeitos específicos ou fim da rodada |
| Loucura | Cada marca reduz 1 de poder efetivo; a segunda remove todos os bônus positivos | Limpeza de estados por efeitos específicos ou fim da rodada |

O total combinado de Geada, Podridão e Loucura não pode impor mais de 3 pontos de penalidade por unidade. Estados temporários são encerrados quando a unidade deixa o campo ou no fim da rodada, inclusive em unidades com Sobrevivente.

### Novas cartas táticas

- **Ritual de Sangue** — aplica uma marca de Sangramento a todas as unidades inimigas da fileira escolhida; a segunda aplicação dispara a hemorragia.
- **Lua Cheia de Rennala** — aplica uma marca de Geada às unidades inimigas da fileira escolhida.
- **Flor da Podridão Escarlate** — aplica até duas marcas de Podridão às unidades inimigas da fileira escolhida.
- **Chama Frenética** — aplica até duas marcas de Loucura às unidades inimigas da fileira escolhida.
- **Chama do Gigante** — remove Geada de todas as unidades aliadas e concede +1 a cada unidade purificada.
- **Cinzas dos Lobos Solitários** — invoca Lobos Espirituais com 3 de poder na fileira escolhida, sem consumir uma carta normal da mão.

## Combos de facção adicionados

Os combos são disparados quando a carta que completa a combinação entra em campo. Cada combo é aplicado uma vez por jogador por rodada.

- **Juramento da Árvore Áurea:** duas unidades marcadas como Ordem Áurea; +2 para a carta que completa o combo e +1 às unidades aliadas da mesma fileira.
- **Convergência da Lua Negra:** duas unidades ligadas à Lua Negra; +2 para a carta que completa o combo.
- **Ritual do Véu Carmesim:** duas unidades do Véu Carmesim; +2 para a carta que completa o combo e +1 às unidades aliadas da mesma fileira.

Os combos anteriores continuam ativos. As cartas preservam seus IDs, portanto a alteração de nomes não apaga as sinergias já vinculadas ao catálogo.

## Poder, raridade e coerência

- Unidades comuns: poder-base 3–5.
- Raras: 4–6.
- Épicas: 5–7.
- Lendárias: 6–8.
- Míticas e Primordiais: 8–9.
- Singulares: 8–10.
- Cartas especiais têm poder-base 0 porque seu valor vem do efeito, não de presença no campo.

O poder-base é separado do bônus de habilidade. O poder exibido no catálogo não deve ser confundido com o poder efetivo depois de bônus, clima e estados negativos. O mesmo cálculo de poder efetivo é usado na pontuação, na seleção de alvos e na escolha de unidades mais fortes ou mais fracas.

Cartas com habilidade de identidade usam essa habilidade no lugar da habilidade genérica cadastrada no campo técnico. Não recebem as duas ao mesmo tempo; isso evita efeitos ocultos que não aparecem no texto exibido. O teste automatizado verifica que todas as cartas respeitam a faixa de poder de sua raridade e que toda habilidade do catálogo possui um ramo implementado no motor.

## Arquivos alterados

- `sistemas/cartas.py` — nomes, facções, textos de habilidade e seis novas cartas.
- `sistemas/gwent.py` — facções, líderes, combos, estados negativos, invocação e limpeza de estados no fim da rodada.
- `sistemas/arte_cartas.py` e `sistemas/molduras_cartas.py` — paletas visuais dourada, azul lunar e vermelho-sangue; versão das artes atualizada para renovar o cache.
- `site/app.js` e `site/index.html` — seleção de facções e apresentação dos líderes.
- `bot.py` e `sistemas/atelie_coliseu.py` — rótulos e contexto temático.
- `tests/test_elden_gwent.py` — testes de catálogo, facções, estados, invocação e combos.

## Validação

Execute na raiz do projeto:

```bash
python -m unittest discover -s tests -v
```

A validação desta edição cobre a coerência estrutural do catálogo, as fileiras obrigatórias, o uso de poder efetivo com clima, a substituição de habilidades genéricas por habilidades de identidade e os efeitos de estados negativos. O equilíbrio competitivo ainda exige partidas reais com decks variados; números de bônus e custos devem ser ajustados após telemetria de partidas, não apenas por inspeção de código.


## Potência dos efeitos por raridade — curva competitiva V58

A raridade pode ampliar habilidades, mas com retornos decrescentes porque também está associada a poder-base superior. O orçamento por ativação é: Comum 0; Rara 1; Épica 1; Lendária 2; Mítica 2; Primordial 3; Singular 3. O reforço é aplicado apenas a cartas com habilidade efetiva, nunca a unidades sem habilidade. Para efeitos numéricos, amplia em 1 ponto cada alteração elegível, até o orçamento, sem ultrapassar os limites absolutos do efeito. Para táticas com regras específicas, o orçamento controla apenas os parâmetros explicitamente previstos no respectivo handler. Não cria alvos, não altera poder-base, não multiplica a passiva fixa da facção e não remove condições de ativação. A raridade nunca ignora escudos, não cria alvos e não remove condições de ativação.

A curva é uma calibração inicial conservadora, não uma alegação de equilíbrio comprovado. A validação competitiva exige telemetria de partidas reais: taxa de vitória por facção, frequência de inclusão por carta, taxa de vitória quando a carta é jogada, resultado por raridade e desempenho por rodada. Até haver amostra suficiente, alterações adicionais em poder-base ou habilidades específicas devem ser tratadas como hipóteses, não como correções definitivas.
