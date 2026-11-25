# V41 — Correção de idempotência entre proprietários

## Implementado
- Chave idempotente persistida passa a ser derivada de `owner_id + tx_key` por SHA-256 (`owner_v1_...`).
- Repetições do mesmo pedido pelo mesmo proprietário continuam retornando o resultado anterior sem novo consumo.
- Duas contas que enviam a mesma chave de cliente não colidem nem recebem o identificador da carta uma da outra.
- A chave original continua sendo retornada ao chamador; a chave persistida não revela o ID do proprietário.

## Validado
- Regressão de sucesso, falha legítima, rollback técnico, saldo, deck, propriedade e idempotência.
- Novo teste com dois proprietários usando a mesma chave de cliente.
- Testes V40 de SQLite persistente, `BEGIN IMMEDIATE`, rollback e preflight read-only.

## Migração e compatibilidade
- Não exige alteração de schema: a coluna `tx_key` continua única e armazena o digest escopado.
- Registros históricos com chave em texto simples continuam no banco; novas chamadas usam o formato escopado. Não há migração automática nem tentativa de reinterpretar chaves antigas.
- Uma repetição de chamada antiga após atualização poderá não localizar seu registro histórico e deve ser tratada operacionalmente antes de atualizar uma instalação com transações pendentes.

## Limitações
- Não substitui homologação com duas contas reais e servidor implantado.
- Não valida integração com PostgreSQL ou outro banco; o projeto atual usa SQLite.
