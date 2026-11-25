# Validação da atualização de drops

## Verificações executadas neste ambiente

- `python -m compileall -q .`: todos os arquivos Python compilam.
- `node --check site/app.js`: sintaxe JavaScript válida.
- Execução dos schemas SQLite em memória: tabelas e índices criados.
- Inicialização/migração simulada do banco legado do ZIP anterior: colunas novas do ledger adicionadas e inventário antigo convertido em exemplares, sem apagar registros existentes.
- Conta nova: 12 drops globais de boas-vindas, modelos distintos e entrega idempotente.
- Patentes: cada marco gera drop global uma única vez.
- Conquistas históricas aprovadas: viram drops globais uma única vez.
- Evolução: fragmentos debitados somente após validar posse, modelo, categoria, faixa de poder e saldo.
- Lapidação: Almas debitadas somente após validar posse, modelo, categoria, teto de poder e saldo.
- Drops de atividade: ledger registra exemplar/poder e impede duplicação pelo mesmo `event_key`.
- Feito especial Soulslike: fluxo de aprovação concede chance Primordial configurável e recompensa Singular individual configurável por desafio, mantendo a detecção automática dos nomes legados.
- Histórico pessoal: consulta de recompensas recentes e duplicatas registrada no ledger.
- Port e mod: aprovação de envios públicos concede drop ao autor com chave idempotente; cadastros diretos da equipe não são premiados.
- Pacotes e forja: desativados também na camada de persistência, não apenas na interface HTTP.

## Limites da validação

- O ambiente de trabalho não contém `aiosqlite` nem `discord.py` instalados. A migração e as transações foram exercitadas com um adaptador de compatibilidade sobre SQLite; a compilação Python foi executada normalmente.
- Não foi possível conectar ao Discord nem executar uma partida real com duas contas.
- O ambiente não possui `discord.py` nem `aiosqlite`; comandos administrativos e integração HTTP não puderam ser executados contra as bibliotecas reais neste ambiente.
- O construtor de deck lista e permite escolher manualmente o exemplar de cada modelo. O deck mantém 12 modelos diferentes e persiste os IDs dos exemplares selecionados.
- A remoção de zerado reverte o drop se o exemplar ainda estiver intacto e fora do deck, ou se o saldo de recursos for suficiente. Se a recompensa foi usada/evoluída ou está em um deck, a remoção automática é bloqueada para revisão.

Antes de produção, instalar `requirements.txt`, fazer backup de `data/` e testar o bot com duas contas em um servidor de teste.

## Validação adicional — exemplares e deck

- Testes de regressão `python -m unittest discover -v`: aprovam variantes de raridade por modelo, duplicatas, idempotência, Primordiais e Singulares individuais, migração de colunas e reversão segura de drops ao remover zerados.
- `cartas_gwent_decks.exemplar_ids_json` é adicionada por migração de coluna, sem apagar decks anteriores.
- A API de coleção entrega cada exemplar com `card_id` e `exemplar_id`; o salvamento valida a propriedade do exemplar e a correspondência com o modelo.
- Partidas usam snapshot do exemplar escolhido, não o exemplar mais forte automaticamente.
- Schema novo e migração simulada também validam `exemplar_ids_json`, `coliseu_primordial_drop` e `coliseu_singular_card_id`.
- Configuração administrativa de feitos foi adicionada em `/adm` → **Jogos, Coliseu e runs** → **Configurar drops especiais dos desafios**, além dos comandos administrativos do módulo Soulslike.
- Renderização de uma carta de teste nas sete raridades: todas as molduras foram geradas com dimensão correta.


## Validação adicional — economia e histórico

- Tabela de movimentações criada no schema novo e disponível para bancos antigos via `CREATE TABLE IF NOT EXISTS`.
- Teste de lapidação confirma débito de Almas, incremento de poder e registro de auditoria.
- Teste de evolução confirma débito de fragmentos, transição de raridade e registro de auditoria.
- Testes percorrem as faixas de poder das sete raridades para todos os modelos do catálogo, validando teto individual e limite absoluto de 12.
- Interface verificada para disponibilizar lapidação Mítica e Primordial conforme os custos do backend.
- Teste de regressão confirma que a origem da recompensa é gravada e recuperável para auditoria.
- Teste de batalha simulado confirma que o motor Gwent mantém raridade e poder do exemplar selecionado no deck; a instância Mítica conserva poder maior que a instância Comum do mesmo modelo.
- Suíte atual: 15 testes automatizados aprovados, além de compilação Python e verificação sintática do JavaScript.
