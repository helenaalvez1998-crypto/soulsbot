# V25 — Forja das Terras Intermédias: acesso pelo Discord

## Implementado nesta etapa
- Novo botão **Forja** no painel `/jogo`.
- Seleção de exemplar individual e prévia de raridade, poder atual, poder máximo e custos.
- Ação **Lapidar +1** conectada a `coliseu_aprimorar_exemplar`.
- Ação **Ascender** conectada a `coliseu_evoluir_exemplar`.
- Botões ficam indisponíveis quando a operação não se aplica ao exemplar selecionado.
- Retorno explícito de sucesso ou dos principais motivos de falha, sem consumir recursos quando a operação é rejeitada pelo banco.
- Restrição da interface ao proprietário do painel; a validação de propriedade e saldo continua no banco.

## Regras preservadas
- Lapidação: +1 poder por operação, consumindo Almas e respeitando o teto do modelo/raridade.
- Ascensão: consome Fragmentos, preserva o poder existente e ajusta apenas até o piso da nova raridade quando necessário.
- Exemplares duplicados continuam independentes.
- Cartas especiais não entram na progressão.
- Primordiais e Singulares continuam fora da ascensão comum; nenhum balanceamento dessas raridades foi alterado.

## Validação executada
- `python -m py_compile cogs/painel_jogo.py`: aprovado.
- `python -m pytest -q tests/test_elden_gwent.py tests/test_v18_card_distribution.py`: 24 testes aprovados e 12 subtests aprovados.
- Importação/runtime do Cog e teste visual no Discord não foram executados porque a dependência `discord.py` não está instalada neste ambiente.
- A suíte completa foi iniciada, mas excedeu o limite de execução disponível; não é declarada como aprovada.

## Limites conhecidos
- O seletor do Discord mostra até 25 exemplares por vez; paginação fica para a próxima iteração.
- O fluxo web já permite lapidação/ascensão no construtor de deck; esta etapa adiciona um ponto de entrada dedicado no Discord, não uma nova tela web independente.
- Não houve teste contra banco de produção nem teste de interação real no Discord.
