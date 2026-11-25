# V24 — Interface do Ritual de Convergência

## Implementado
- Botão **Ritual de Convergência** no painel `/jogo`.
- Seletor de três exemplares e validação de modelo/raridade iguais.
- Prévia explícita do resultado, custo e perda irreversível antes da confirmação.
- Confirmação separada e opção de cancelar sem consumir exemplares.
- Bloqueio no banco de dados para impedir o sacrifício de exemplares presentes no deck ativo.
- A validação de deck ocorre dentro da mesma transação que consome os exemplares, reduzindo risco de corrida entre a prévia e a confirmação.
- Tratamento de falhas de validação sem consumir cartas.

## Regras preservadas
- Três exemplares do mesmo modelo e raridade geram um exemplar do mesmo modelo na raridade seguinte.
- O resultado começa no poder mínimo da nova raridade; não recebe poder/lapidação dos sacrificados.
- Cartas especiais não participam da convergência comum.
- Primordiais e Singulares exigem ritual especial.
- Histórico dos sacrifícios permanece registrado.

## Validação
- 66 arquivos Python compilados sem erro.
- `tests/test_elden_gwent.py` e `tests/test_v18_card_distribution.py`: 24 testes aprovados e 12 subtestes aprovados.

## Limites conhecidos
- O seletor do Discord exibe até 25 exemplares elegíveis por vez; paginação da seleção ainda não foi implementada.
- A interface foi adicionada ao painel Discord `/jogo`. O fluxo web de deckbuilding/Forja não foi alterado.
- A validação de exemplares equipados consulta `exemplar_ids_json` do deck ativo; não há validação de decks salvos em outros slots porque o esquema atual mantém um deck por jogador.
- Não foi executado teste de integração contra um banco de produção nem teste visual dentro de uma instância Discord.
