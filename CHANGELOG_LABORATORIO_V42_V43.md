# Laboratório de Transmutação — V42 e V43

## V42 — Receitas ocultas e descoberta individual
- Criadas três receitas ocultas temáticas: Trindade da Lua Velada, Forja Dourada Perdida e Rito do Veio Morto.
- Descoberta compara IDs canônicos e raridades exatas, sem depender da ordem dos ingredientes.
- Pesquisa exige 3–5 exemplares distintos, próprios, elegíveis e fora do deck ativo.
- Pesquisa não consome cartas nem materiais.
- Descobertas são persistidas por jogador em `cartas_receitas_ocultas_descobertas`, com assinatura e timestamp; `INSERT OR IGNORE` torna o registro idempotente.
- API: `POST /api/gwent/transmutacao/discover`; listagem em `GET /api/gwent/transmutacao`.
- UI do Laboratório ganhou ação de pesquisa e lista de receitas descobertas.

## V43 — Catalisadores nomeados
- Catálogo: Cinza da Graça, Resíduo Cariano, Brasa Messmeriana e Núcleo Sanguíneo.
- Cinza da Graça adiciona +5 pontos percentuais, sujeito ao teto global de 90%, e custa uma unidade.
- Catalisadores Cariano, Messmeriano e Sanguíneo exigem afinidade correspondente e aumentam a pontuação de compatibilidade em até 10 pontos antes do cálculo do bônus de compatibilidade.
- Cada catalisador exige uma unidade do respectivo material; o débito ocorre dentro da transação de transmutação já existente.
- Mantida compatibilidade retroativa com o sinalizador legado `catalyst_active`.
- UI ganhou seletor de catalisador e exibição dos saldos.

## Validação executada
- `compileall` para `database.py`, `site_hub.py`, `sistemas` e `tests`: aprovado.
- `node --check` no JavaScript da página `/transmutacao`: aprovado.
- Testes direcionados V42, V43, economia V33, execução V34 e validação V31: 30 passaram.
- Suíte ampla sem `tests/test_elden_art_prompts.py` excedeu o limite de execução desta sessão.
- Suíte completa confirmou falhas preexistentes de prompt de arte em 6 Relíquias (`No fixed scene exists`); execução interrompida pelo limite de falhas configurado.

## Limitações ainda abertas
- O ambiente não possui `aiosqlite`; a migração e o débito transacional não foram exercitados em banco real nesta sessão.
- A origem de aquisição/distribuição dos novos materiais catalisadores ainda não foi integrada a recompensas ou drops; o sistema reconhece, exige e consome os materiais quando presentes no inventário.
- A UI foi atualizada, mas não houve teste visual em navegador nem teste de ponta a ponta com duas contas.
- As receitas ocultas são descobertas por combinações exatas pré-configuradas; pistas dinâmicas, cadeia de investigação e receitas adicionais permanecem expansão futura.
