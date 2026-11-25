# V35 — Interface Web do Laboratório de Transmutação

## Implementado
- Página autenticada por APIs em `/transmutacao`, com seleção de 3–5 exemplares, busca, filtro por raridade e paginação.
- Prévia sem consumo de recursos, com compatibilidade, carta estimada, chance e orçamento calculados no servidor.
- Inventário individual de materiais e histórico das últimas 20 tentativas.
- Confirmação explícita antes da execução e aviso destacado sobre consumo irreversível em falha legítima.
- API `GET /api/gwent/transmutacao`.
- API `POST /api/gwent/transmutacao/preview`.
- API `POST /api/gwent/transmutacao/execute`, que chama exclusivamente `Database.coliseu_executar_transmutacao`.
- APIs de cartas pessoais: `GET /api/gwent/cartas-geradas` e `GET /api/gwent/cartas-geradas/{card_id}`, sempre filtradas pelo proprietário autenticado.
- Proprietário obtido da sessão (`_api_user_id`), nunca do corpo enviado pelo navegador.
- Validação de origem para POST, chave idempotente com escopo por proprietário e limitação de execução em memória a uma tentativa por usuário a cada cinco segundos.
- Links de navegação adicionados à Forja, Linhagens e Rituais Ancestrais.

## Regras preservadas
- Prévia não consome ingredientes nem materiais e não cria arte.
- Execução usa o serviço transacional V34; não duplica a lógica de consumo no endpoint.
- Cartas pessoais, especiais, líderes, Primordiais/Singulares e exemplares equipados não aparecem como ingredientes elegíveis; a validação definitiva continua no serviço transacional.
- Sem catalisador na interface V35.
- Sem alterações na política econômica V33, probabilidades, custos ou regras de raridade.

## Detalhe importante da prévia
Para os mesmos ingredientes, a raridade e o orçamento econômico são estáveis. Nome, poder e habilidade são gerados novamente na execução e podem diferir da prévia. O navegador informa essa distinção.

## Validação executada
- `py_compile` nos módulos Python do projeto: aprovado.
- `node --check` no JavaScript da página: aprovado.
- Testes focados V28–V34 e V35: **48 passed**.
- Testes V35 verificam registro da página, autenticação obrigatória nas APIs privadas e avisos/fluxo de confirmação.
- Suíte completa iniciada, mas excedeu o limite de execução do ambiente durante a coleta/execução; não há resultado completo para declarar aprovação global.

## Limitações e não validações
- Não houve teste visual em navegador real nem teste no Discord.
- Não houve teste com banco de produção, múltiplos processos ou implantação.
- O rate limit V35 é em memória por processo; não substitui rate limit distribuído em implantação com múltiplos workers.
- A política de materiais e probabilidades V33 permanece proposta; aquisição/escassez não foi implementada.
- A prévia não reserva materiais. O serviço V34 revalida saldo, propriedade, deck e ingredientes no commit.
- Falhas técnicas continuam sendo exceções/rollback do serviço V34; a interface não as converte em falha legítima.
