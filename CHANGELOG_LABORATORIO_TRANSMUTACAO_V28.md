# V28 — Fundação do Laboratório de Transmutação

## Implementado nesta versão
- Estrutura de persistência para cartas procedurais pessoais e tentativas de transmutação.
- Campos de origem e proteção em `cartas_exemplares`: `origin_type`, `origin_card_id`, `is_sacrificable`.
- Tabelas `cartas_geradas`, `cartas_transmutacoes`, `cartas_geradas_habilidades` e `cartas_geradas_artes`.
- Índices por proprietário e histórico.
- Migração incremental compatível com exemplares existentes.
- Triggers SQLite impedem reclassificar uma carta transmutada ou habilitar seu sacrifício.
- Métodos de consulta de cartas geradas sempre filtrados pelo proprietário.
- Convergência comum, Linhagens, Rituais Ancestrais e remoção automática de recompensas rejeitam exemplares pessoais protegidos.

## Regras preservadas
- Cartas transmutadas são exclusivas do criador.
- Não podem ser sacrificadas, transferidas ou compartilhadas.
- Exemplares tradicionais permanecem sacrificáveis conforme regras atuais.
- Nenhuma carta é gerada nesta versão.
- Nenhuma mudança de balanceamento de Primordiais ou Singulares.

## Ainda não implementado
- Gerador procedural, receitas, probabilidades e materiais.
- Criação e armazenamento de arte original.
- Interface do Laboratório.
- Integração de cartas geradas com Forja, deckbuilding e motor de batalha.

## Validação
- Testes SQLite de schema e triggers.
- Testes automatizados de regressão.
- Compilação Python.
- Não houve teste com `aiosqlite`/banco de produção nem teste visual.
