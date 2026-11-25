# V34 — Execução Transacional da Transmutação

## Implementado
- Serviço `sistemas/transmutacao.py` e ponto de entrada `Database.coliseu_executar_transmutacao`.
- Chave idempotente `tx_key`; repetição da mesma chave retorna o resultado anterior sem novo consumo.
- Validação de 3–5 exemplares distintos, propriedade, elegibilidade, proteção de cartas pessoais e ausência no deck ativo.
- Compatibilidade e raridade calculadas com os módulos V29–V31.
- Custos e chances calculados com a política V33, incluindo custo adicional do catalisador.
- Validação de saldo no inventário individual `cartas_materiais_transmutacao`.
- Sorteio de servidor com `secrets.randbelow`; não recebe seed nem probabilidade do cliente.
- Preparação e validação da definição e da arte antes do débito.
- `BEGIN IMMEDIATE` revalida e executa consumo, remoção dos exemplares, registro do histórico e criação da carta dentro da mesma transação.
- Sucesso cria carta individual com exemplar `origin_type='transmutacao'`, `source='transmutacao'` e `is_sacrificable=0`.
- Sucesso grava arte validada e habilidade no banco, e atualiza telemetria cumulativa 50/50.
- Falha legítima consome os ingredientes e materiais e registra tentativa sem criar carta.
- Erro técnico lança exceção e provoca rollback; arte criada durante a tentativa é removida se o commit falhar.
- Tabela global `cartas_geracao_balanceamento` para contagem cumulativa de unidades geradas com/sem habilidade.

## Segurança transacional
- IDs e propriedade são verificados no servidor.
- Deck ativo é consultado dentro da transação.
- Materiais são debitados com condição `quantidade >= custo` e verificação de `rowcount`.
- Exemplares são removidos com condição de proprietário e verificação de `rowcount`.
- O SQLite serializa escritores com `BEGIN IMMEDIATE`; uma chave idempotente impede repetição da mesma operação.
- A criação da carta e o registro do resultado são parte do mesmo commit.

## Limites desta versão
- Não há ainda página web, endpoint HTTP, comando Discord ou tela de prévia.
- Não há fluxo de aquisição/recompensa dos novos materiais.
- Não há gestão de catalisadores na interface.
- O serviço não deve ser exposto diretamente a clientes até existir autenticação/CSRF/rate limit no endpoint que o chamar.
- `aiosqlite` não está instalado neste ambiente; a execução foi testada com adaptador assíncrono de teste sobre SQLite real, mas não com a conexão `Database` de produção.
- Não houve teste de concorrência multi-processo em banco de produção.
- A arte procedural permanece no nível visual definido na V32; não é pintura generativa de modelo de imagem.
- A política econômica V33 continua proposta e precisa de validação de aquisição/escassez de materiais antes de lançamento.

## Validação
- Compilação Python dos arquivos alterados.
- Testes de sucesso, falha legítima, erro técnico, rollback, propriedade, deck ativo, saldo insuficiente e idempotência.
- Testes de regressão das versões V28–V33 e dos sistemas de Linhagens, Rituais e Gwent.
