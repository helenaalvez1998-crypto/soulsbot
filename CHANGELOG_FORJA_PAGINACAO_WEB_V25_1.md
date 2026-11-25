# V25.1 — Forja completa: paginação e interface web

## Implementado
- Paginação do seletor de exemplares no Discord, com 25 opções por página.
- Controles anterior/próxima, estado de página e reset da seleção ao trocar de página.
- Botão direto para abrir a Forja no site pelo painel `/jogo`.
- Nova página independente `/forja`, com busca, filtro por raridade, ordenação e paginação.
- API autenticada para listar exemplares elegíveis e executar lapidação/ascensão.
- Confirmação explícita antes de operações irreversíveis e atualização da coleção após sucesso.
- Validação de autenticação, origem das requisições de escrita, ID do exemplar e ação permitida.

## Regras preservadas
- Lapidação: +1 poder por operação, limitada pelo teto do modelo/raridade.
- Ascensão: consome Fragmentos, preserva poder e ajusta apenas até o mínimo da nova raridade quando necessário.
- Progressão individual por exemplar; duplicatas não compartilham progresso.
- Cartas especiais não entram na Forja.
- Primordiais e Singulares continuam fora da ascensão comum.
- Nenhum balanceamento de Primordiais foi realizado.

## Validação executada
- `py_compile` em `cogs/painel_jogo.py` e `site_hub.py`: aprovado.
- `tests/test_elden_gwent.py` e `tests/test_v18_card_distribution.py`: 24 testes aprovados e 12 subtests aprovados.
- Integridade do ZIP verificada.
- Não foi possível executar teste visual real no Discord nem autenticação/banco de produção neste ambiente.
