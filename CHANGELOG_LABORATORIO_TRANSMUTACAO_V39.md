# V39 — Telemetria agregada e integridade operacional

## Implementado
- `sistemas/transmutacao_telemetria.py`: relatório read-only por janela de até 365 dias.
- Agrega tentativas por status e cartas por raridade.
- Sinaliza probabilidade fora da política (0–90%), sorteio fora de [0,100), arte não validada/caminho ausente e carta sem exemplar.
- Não retorna `owner_id`, `tx_key`, IDs de ingredientes, snapshots ou definições pessoais.

## Validado
- Testes com dados simulados para alertas, janela máxima, ausência de dados e privacidade.
- Compilação Python do módulo e testes.

## Limitações
- A telemetria é um relatório sob demanda; não há dashboard, alertas em tempo real ou retenção/arquivamento automatizados.
- Não verifica hash dos arquivos de arte em lote; a integridade criptográfica individual continua no serviço de arte.
- A amostra não é prova de partidas reais nem de consistência em múltiplos processos.
- Não altera custos, chances, materiais ou regras de consumo.
