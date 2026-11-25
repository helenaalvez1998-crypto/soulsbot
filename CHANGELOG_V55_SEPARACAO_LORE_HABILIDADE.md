# V55 — Separação entre lore e habilidade mecânica

## Alterações

- `sistemas/gwent.py`: `preparar_carta()` não usa mais `descricao` como fallback de `habilidade_texto`.
- Quando não existe texto mecânico cadastrado, a carta exibe explicitamente `Sem habilidade especial.`
- O texto narrativo continua no campo `descricao`, sem ser misturado ao efeito de combate.
- `site/app.js`: o selo de habilidade usa o nome legível da habilidade, em vez do identificador interno sempre que disponível.
- Cartas especiais passam a exibir o texto mecânico real no selo, em vez de expor a chave interna do efeito.
- As inspeções de carta em campo e de preparação de jogada exibem blocos separados para `HABILIDADE` e `DESCRIÇÃO`.
- `site/style.css`: a descrição narrativa recebe tratamento visual secundário para não competir com a regra mecânica.
- Adicionados testes de regressão para impedir que lore seja apresentado como habilidade.

## Escopo preservado

Nenhum valor de poder, raridade, custo, potência, facção, fileira, alvo, duração ou resolução de batalha foi alterado nesta etapa.

## Validação

- `PYTHONPATH=. pytest -q tests/test_separacao_lore_habilidade.py tests/test_elden_gwent.py tests/test_auditoria_efeitos_v50.py`: 26 aprovados e 7 subtestes aprovados.
- `node --check site/app.js`: aprovado.
- A suíte integral foi iniciada, mas excedeu o limite de execução desta sessão; não é declarada como aprovada.
