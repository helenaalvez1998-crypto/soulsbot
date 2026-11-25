# Laboratório de Transmutação — V46 e V47

## V46 — Catálogo pessoal
- Página autenticada `/cartas-geradas`.
- API `/api/gwent/cartas-geradas` com busca textual, filtros por facção, raridade, afinidade e função tática.
- Paginação com tamanho controlado (1–100) e resumo de coleção.
- Detalhes de afinidades, função, lore e estado da arte no catálogo.
- Mantém a consulta sempre escopada ao proprietário autenticado; não cria catálogo público nem permite transferência.

## V47 — Diagnóstico de equilíbrio
- Módulo de métricas para proporção com/sem habilidade, raridade, facção, função, frequência de habilidades, poder por raridade, nomes repetidos e cartas sem arte.
- API agregada autenticada `/api/gwent/transmutacao/balanceamento`.
- Painel de diagnóstico dentro do catálogo pessoal.
- Não altera cartas automaticamente e não declara equilíbrio competitivo apenas por métricas estáticas.

## Validação
- 19 testes V42–V47 e regressões V44/V45 aprovados.
- `py_compile` dos módulos e `site_hub.py` aprovado.
- Teste de sintaxe JS executado separadamente quando Node disponível.

## Limitações
- O endpoint de diagnóstico usa até 5.000 cartas recentes do banco, não o histórico ilimitado.
- Não há métricas de taxa de vitória, partidas reais ou desempenho por matchup no esquema atualmente disponível.
- A homologação final de banco de produção, duas contas e partidas reais permanece pendente.
- A geração de pinturas originais por IA segue dependendo de um provedor externo configurado; V44 fornece validação e persistência, não geração artística externa.
