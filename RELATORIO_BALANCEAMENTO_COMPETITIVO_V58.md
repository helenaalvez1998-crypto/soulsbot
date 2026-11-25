# Relatório de Balanceamento Competitivo — V58

## Escopo e limite da análise

Esta revisão usa o catálogo auditado V57 (`docs/AUDITORIA_CATALOGO_V57.json`), as regras em `REGRAS_ELDEN_GWENT.md` e os handlers de `sistemas/gwent.py`. O banco `colizeu.db` e o histórico de partidas não foram fornecidos. Portanto, este documento é uma auditoria estática de regras e catálogo, não uma medição de win rate.

## Retrato do catálogo

- 110 entradas no inventário auditado.
- 84 unidades e 26 cartas especiais.
- 42 entradas sem `habilidade_id`.
- Distribuição de raridade do inventário: Comum 28; Rara 35; Épica 21; Lendária 11; Mítica 3; Primordial 8; Singular 4.

### Poder-base médio por facção

| Facção | Unidades | Média bruta |
|---|---:|---:|
| Ordem Áurea | 31 | 6,42 |
| Véu Carmesim | 26 | 6,00 |
| Lua Negra | 27 | 5,78 |

A média bruta não basta para declarar uma facção mais forte: as proporções de raridade são diferentes. Comparando dentro de raridades, as amostras de Épica/Lendária/Mítica/Primordial/Singular são pequenas e incompletas para algumas facções. Não foi aplicado nerf arbitrário de facção.

### Poder-base por raridade (unidades)

| Raridade | Quantidade | Faixa | Média |
|---|---:|---:|---:|
| Comum | 26 | 3–5 | 4.62 |
| Rara | 23 | 4–6 | 5.65 |
| Épica | 14 | 5–7 | 6.29 |
| Lendária | 8 | 6–8 | 7.50 |
| Mítica | 1 | 8–8 | 8.00 |
| Primordial | 8 | 8–9 | 8.38 |
| Singular | 4 | 9–10 | 9.50 |

## Problemas encontrados e correções aplicadas

### 1. Dupla vantagem da raridade

A raridade já eleva a faixa de poder-base. Além disso, a regra anterior atribuía um orçamento linear de potência de 0 a 6 pontos por ativação. Em uma partida sem recurso de energia/custo de jogada, isso cria uma vantagem cumulativa relevante para cartas de raridade alta.

**Correção V58:** curva com retornos decrescentes:

| Raridade | Antes | V58 |
|---|---:|---:|
| Comum | 0 | 0 |
| Rara | 1 | 1 |
| Épica | 2 | 1 |
| Lendária | 3 | 2 |
| Mítica | 4 | 2 |
| Primordial | 5 | 3 |
| Singular | 6 | 3 |

O teto de potência adicional passou a ser 3. A potência não altera o poder-base. Unidades sem habilidade não exibem potência fictícia; unidades sem habilidade, mas com combo compatível, descrevem a ampliação do combo.

### 2. Sangue Corrompido: texto incompatível com o motor

A descrição antiga dizia que a carta aplicava clima -2 em Cerco. O handler real aplicava Sangramento às unidades inimigas na fileira de Cerco e disparava Hemorragia na segunda marca. O texto foi corrigido; o efeito de combate foi mantido para não alterar a regra sem decisão de design.

### 3. Unidades sem habilidade

A preparação de cartas podia anexar um texto genérico de potência mesmo quando a unidade não possuía habilidade. A apresentação agora só anuncia ampliação quando existe habilidade mecânica ou sinergia compatível.

## Riscos de design que ainda exigem decisão

1. **Sem custo de energia durante a partida:** como o deck tem 12 cartas únicas e não há custo de recurso documentado para jogar unidades, uma carta de raridade alta não paga um custo tático adicional no momento de uso. A raridade pode virar vantagem direta, especialmente se as cartas altas forem acessíveis por progressão/pagamento.
2. **Limites de raridade no deck:** não há limite documentado de Primordiais/Singulares por deck. Recomendo testar uma regra de construção (por exemplo, no máximo 1 Singular e 1 Primordial por deck) em ambiente de teste antes de ativar em produção.
3. **Amostra por raridade/facção:** a distribuição de Lendárias, Míticas, Primordiais e Singulares não permite comparar todas as facções com confiança.
4. **Líderes e combos:** passiva de facção é simétrica (+1), mas combos podem gerar bônus de equipe. Precisam de telemetria por deck e por combinação, não apenas teste unitário.

## Métricas necessárias para o balanceamento real

Registrar por partida: facção, líder, deck, cartas jogadas, ordem de jogo, habilidade ativada, alvo, poder efetivo antes/depois, rodada vencida, resultado final e abandono. Com isso, calcular:

- taxa de vitória por facção e líder;
- taxa de inclusão por carta e taxa de vitória quando a carta é jogada;
- diferença entre poder esperado e poder real gerado por habilidade;
- desempenho por raridade, fileira e matchup;
- frequência e taxa de vitória de cada combo;
- partidas encerradas por execução/remoção/controle de estado.

Evitar nerfar carta só por ter taxa de vitória alta com amostra pequena. Como regra inicial, exigir ao menos 100 partidas relevantes por segmento antes de ajustes específicos, e usar intervalo de confiança para evitar reagir a ruído.

## Validação

- 31 testes direcionados de catálogo e motor passaram na validação V58.
- Testes de regressão cobrem textos de cartas, handlers, raridade, estados, combos, fileiras e poder efetivo.
- A suíte completa não foi declarada aprovada nesta entrega; a execução anterior excedeu o limite de tempo em um teste de renderização de molduras.

## Arquivos alterados

- `sistemas/gwent.py` — curva de potência por raridade e apresentação coerente de potência.
- `sistemas/cartas.py` — texto mecânico correto de Sangue Corrompido.
- `tests/test_elden_gwent.py` — expectativas da nova curva.
- `tests/test_card_catalog_quality.py` — regressões para unidades sem habilidade e Sangue Corrompido.
- `REGRAS_ELDEN_GWENT.md` — regra de potência V58 e limite da validação competitiva.
- `docs/RELATORIO_BALANCEAMENTO_COMPETITIVO_V58.json` — dados estruturados da auditoria.
