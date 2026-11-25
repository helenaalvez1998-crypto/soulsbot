# V33 — Economia, Materiais e Probabilidades

## Implementado
- `sistemas/economia_transmutacao.py`: política econômica versionada `v33.1`.
- Inventário dedicado `cartas_materiais_transmutacao`, separado de Almas e Fragmentos da Forja.
- Consulta do inventário por proprietário: `coliseu_listar_materiais_transmutacao`.
- Orçamento de tentativa por raridade, compatibilidade, facção e catalisador.
- Validação de saldo sem mutação de inventário.
- Simulador Monte Carlo reprodutível, com sucessos, falhas e consumo esperado.
- Relatório comparativo para cinco raridades e dois cenários.
- Regras de consumo documentadas e explicitamente separadas entre falha legítima e erro técnico.

## Política econômica proposta (não lançamento definitivo)

### Probabilidade base
| Raridade | Chance base |
|---|---:|
| Comum | 80% |
| Rara | 65% |
| Épica | 45% |
| Lendária | 25% |
| Mítica | 10% |

Bônus: compatibilidade V29 até +10 pontos percentuais (score 0–100 convertido linearmente); facção dominante compartilhada +5 p.p.; catalisador +5 p.p. Bônus total limitado a +20 p.p. e chance final limitada a 90%.

O score de compatibilidade continua sendo coerência temática/tática, não probabilidade. A conversão econômica é uma regra separada e explícita. No cenário neutro da simulação, score 0, sem facção compartilhada e sem catalisador; no cenário favorável, score 100, facção compartilhada e catalisador.

### Materiais por tentativa
| Raridade | Essência de Vida | Fragmento Ancestral | Núcleo de Convergência |
|---|---:|---:|---:|
| Comum | 5 | 0 | 0 |
| Rara | 10 | 2 | 0 |
| Épica | 15 | 5 | 0 |
| Lendária | 20 | 10 | 1 |
| Mítica | 30 | 20 | 2 |

Catalisador consome +1 Núcleo de Convergência e concede +5 p.p. Vestígio Primordial fica reservado e não libera Primordial/Singular. Ingredientes são 3–5 cartas elegíveis, consumidas integralmente.

## Leitura da simulação
A simulação calcula o número esperado de tentativas por sucesso como `100 / chance`. Todo fracasso legítimo consome os materiais e ingredientes da tentativa. Portanto, o custo esperado por sucesso cresce inversamente à probabilidade. A simulação não representa inflação, taxa de aquisição, mercado, frequência de drops ou comportamento real dos jogadores; esses dados ainda não existem.

## Regras invioláveis
- Sucesso: consome ingredientes e materiais comprometidos e cria carta pessoal.
- Falha legítima: consome ingredientes e materiais comprometidos e não cria carta.
- Erro técnico: não consome ingredientes nem materiais e não conta como falha.
- A geração/validação de definição e arte ocorre antes do commit de consumo.
- Primordial e Singular continuam bloqueadas no gerador comum.
- Não há ajuste de Primordiais, nem transferência de poder dos ingredientes.

## Limites desta versão
- Custos e probabilidades são parâmetros propostos para revisão, não economia definitiva de lançamento.
- Não existe ainda fonte de aquisição/recompensa dos novos materiais.
- Catalisador é contabilizado como Núcleo extra, mas a UX/obtenção ainda não existe.
- Não há execução de transmutação nem consumo de materiais nesta versão.
- Não há integração de preview/API/UI do Laboratório.
- Não houve teste com `aiosqlite` nem banco de produção.
- A simulação é matemática/Monte Carlo, não teste de economia ao vivo.

## Validação
- Testes unitários da política, limites, saldo, repetibilidade e relatório.
