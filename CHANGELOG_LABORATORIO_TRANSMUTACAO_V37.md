# V37 — Auditoria de Segurança e Integridade do Laboratório

## Base e inspeção
- Base utilizada: pacote V36, ZIP validado antes da extração.
- Revisados os fluxos de resolução de cartas pessoais, coleção, salvamento de deck, snapshots de partida, proteção de exemplares e serviço transacional.

## Endurecimentos implementados
- Consultas de exemplares agora retornam `user_id`, `origin_type`, `origin_card_id` e `is_sacrificable`, além dos campos de jogo.
- `preparar_carta_pessoal` rejeita IDs fora do namespace `transmutacao_`, divergência entre `card_id` da definição e do exemplar, origem adulterada e exemplares marcados como sacrificáveis.
- A resolução de carta pessoal no servidor passa o proprietário autenticado à camada do motor, que confere `exemplar.user_id` com a sessão quando esse metadado está disponível.
- Mantida a resolução da definição no banco por `owner_id + card_id`; snapshots de partida continuam congelando a definição já validada.
- Nenhuma regra de economia, chance, raridade, sacrifício ou balanceamento foi alterada.

## Testes executados
- `py_compile` de todos os arquivos Python: aprovado.
- Testes focados V28–V37, incluindo transmutação, V34, V35, V36 e Gwent: **78 passed, 7 subtests passed**.
- ZIP: integridade verificada com `unzip -t`.

## Limitações / não homologado
- Não houve teste end-to-end com duas contas reais, partida PvP real ou banco de produção.
- Não houve teste de concorrência multi-processo em ambiente de produção.
- A suíte completa do repositório não foi usada como critério de aprovação desta versão; o resultado declarado refere-se aos testes direcionados listados acima.
- O motor valida metadados de proprietário quando fornecidos pela camada de persistência; a consulta SQL owner-scoped permanece a barreira principal de autorização.
