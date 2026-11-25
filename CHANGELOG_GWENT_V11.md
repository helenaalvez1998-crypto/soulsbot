# Gwent V11 — recompensas de vitória, progressão e cobertura

- Vitória concede um drop global ao vencedor, com limite de 3 drops normais por janela móvel de 24 horas.
- Marcos de 5, 10, 25, 50 e 100 vitórias concedem drops adicionais únicos.
- Drops são registrados na mesma transação da finalização da partida, com chaves idempotentes.
- Arena apresenta XP, Denários, MMR e drops recebidos após a partida.
- Corrigida a ausência da coluna `reward_xp` no schema de `cartas_gwent_rewards`, que era consultada e gravada pelo fluxo de partidas.
- Migração compatível adiciona `reward_xp`, `drop_event_key` e `milestone_drop_event_key` a bancos existentes.
- Adicionado contrato de cobertura para impedir habilidades do catálogo sem implementação no motor.

## Validação

- Testes unitários de raridades, inventário, migração, marcos e cobertura de habilidades.
- Verificação de sintaxe Python e JavaScript.
- Ainda requer teste de integração em ambiente Discord com dependências reais e banco de produção clonado.
