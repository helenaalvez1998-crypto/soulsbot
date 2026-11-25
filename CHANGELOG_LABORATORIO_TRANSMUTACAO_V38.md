# V38 — Preflight de lançamento controlado

## Implementado
- `sistemas/transmutacao_readiness.py`: verificações read-only de arquivos críticos, dependências, variáveis de ambiente e tabelas mínimas.
- Relatório agregado com estados `pass`, `conditional` e `blocked`.
- Segredos não são retornados no relatório.
- `production_approved` permanece sempre `false`: preflight não equivale a homologação.

## Validado
- Testes unitários para arquivos ausentes/presentes, dependências, segredo de ambiente e schema SQLite.
- Não abre banco de produção, não executa migrações e não altera dados.

## Pendências antes de produção
- Homologar com duas contas reais e banco persistente.
- Confirmar backup/restore, permissões do diretório de arte e política de retenção.
- Configurar `DATA_DIR` em volume persistente.
- Resolver rate limit distribuído para múltiplos workers (o limitador atual em memória não é distribuído).
- Validar CSRF/origem e autenticação no ambiente implantado.
