# Revisão consolidada — Etapas 1 a 12

## O que esta rodada acrescenta

A rodada integrada 9–12 melhora a entrada na central da Nara, reduz cliques para duas tarefas recorrentes e padroniza a expiração de painéis privados e administrativos selecionados. As rotas existentes são reutilizadas, sem criar uma segunda implementação para registros ou preferências.

## Evidências de validação

| Verificação | Resultado |
|---|---:|
| Novos testes da etapa 9–12 | 9 aprovados |
| Testes direcionados combinados | 51 aprovados |
| Suíte completa | 258 aprovados / 16 falhas / 2 ignorados |
| Suíte completa da etapa 8 | 249 aprovados / 16 falhas / 2 ignorados |
| Regressões adicionais | 0 novas falhas |
| Compilação Python | Aprovada |

## Falhas preexistentes mantidas visíveis

A suíte completa continua com 16 falhas. Elas já apareciam no pacote da etapa 8 e não aumentaram nesta rodada. Os grupos de falhas observados incluem:

- expectativas de texto do módulo de relacionamento e personalidade;
- divergência entre os comandos slash esperados por testes antigos e os comandos efetivamente expostos;
- expectativas antigas de catálogo/Ports & Mods;
- texto esperado em FAQ de aprovação de zerados;
- expectativas de localização `.env.example` versus `env.example`;
- expectativas de integração de dashboard e de handlers administrativos de relacionamento.

Essas falhas não foram mascaradas, removidas ou reescritas. Precisam de triagem funcional separada para distinguir testes obsoletos de regressões reais.

## Riscos ainda não cobertos

- Interações reais no Discord, incluindo mobile e clientes com latência.
- Reinício do processo e persistência de Views públicas.
- Permissões efetivas configuradas no servidor/FadeHost.
- Testes concorrentes de transações SQLite do Coliseu e da economia.
- Revisão individual de todas as Views auxiliares do projeto.

## Recomendação operacional

Não substituir o bot de produção diretamente. Homologar primeiro em uma cópia, preservar `.env` e banco SQLite, validar os fluxos citados e só então promover o pacote.
