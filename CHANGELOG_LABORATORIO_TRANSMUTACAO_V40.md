# V40 — Homologação com SQLite persistente

## Implementado
- `sistemas/transmutacao_homologacao.py`: preflight read-only de arquivo SQLite persistente, `quick_check`, tabelas essenciais e modo de journal.
- Testes com arquivo SQLite real e conexões independentes para serialização de chave idempotente, rollback e persistência.

## Validado
- Os testes não usam `:memory:` para os cenários de concorrência e rollback.
- Preflight abre o banco em `mode=ro` e ativa `query_only`; não cria arquivo nem executa migrações.

## Limitações
- Os testes de concorrência validam a semântica SQLite/BEGIN IMMEDIATE, não executam duas instâncias do serviço web/Discord.
- Não houve homologação com duas contas reais, nem teste com a classe Database de produção, pois `aiosqlite` não está disponível neste ambiente.
- Backup/restore, permissões do diretório de arte e partidas reais continuam pendentes.
