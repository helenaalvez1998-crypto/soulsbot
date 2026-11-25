# V54 — Potência da raridade na interface

- A coleção e o construtor exibem a potência da raridade nas cartas, inclusive especiais.
- O detalhe da carta explica que potência de raridade amplia habilidades, não é poder-base nem ataque direto.
- A inspeção de coleção usa `potencia_raridade` fornecida pelo servidor, com fallback para a escala canônica.
- A Forja exibe potência da raridade separada do poder-base e do limite de lapidação.
- A API de coleção e a API da Forja explicitam `potencia_raridade` usando `RARITY_EFFECT_BUDGET`.
- Nenhuma regra de batalha, custo, poder-base, raridade ou limite de habilidade foi alterada.

## Validação

Validações executadas:

- `PYTHONPATH=. pytest -q tests/test_elden_gwent.py tests/test_auditoria_efeitos_v50.py`: 24 passed, 7 subtests passed.
- `node --check site/app.js`: aprovado.
- 7 scripts inline de `site/index.html`: sintaxe aprovada com Node.js.
- `python -m py_compile bot.py site_hub.py`: aprovado.

Não foi executado teste visual em navegador real nem teste de integração autenticado contra banco de produção.
