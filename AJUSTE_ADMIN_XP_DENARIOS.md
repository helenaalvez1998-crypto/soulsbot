# Ajuste administrativo de XP e Denários

A ferramenta fica dentro de `/adm` → **Economia** → **Ajustar XP / Denários de membro**.

## Fluxo

1. Selecione um membro do servidor.
2. Escolha **Adicionar** ou **Remover**.
3. Informe XP, Denários ou ambos; os campos podem ficar vazios individualmente.
4. Informe um motivo e envie.

## Regras e proteções

- A ferramenta é restrita aos administradores reconhecidos pelo controle de acesso do painel `/adm`.
- O ajuste é feito na tabela `users`, usando a mesma carteira e progressão já utilizadas pelo restante do bot.
- Os saldos nunca ficam negativos. Uma remoção maior que o saldo reduz o recurso somente até zero.
- O banco registra autor, membro, valores anteriores e posteriores, deltas efetivamente aplicados e motivo na tabela `logs`, na mesma transação da alteração.
- Quando o XP muda, o bot tenta sincronizar a patente/cargo do membro com o novo nível.
- Bots não podem ser selecionados como destinatários.
- O valor máximo por recurso e por operação é 1.000.000.000.

O projeto mantém apenas `/nara` e `/adm` como comandos slash publicados. Por isso, a operação foi adicionada como ferramenta administrativa dentro do painel existente, sem criar um terceiro comando slash que seria removido pelo filtro de inicialização.
