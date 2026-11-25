# Narabot V74 — Integridade competitiva do Gwent

## Alterações

### Distribuição inicial
- O embaralhamento agora ocorre no servidor com `secrets.SystemRandom` ao iniciar partidas PvP (após aceitar o convite) e Solo.
- Os dois lados recebem baralhos embaralhados independentemente; a ordem salva no construtor não determina a mão inicial.
- O modo Solo espelha também a relíquia equipada do jogador para a NARA.

### Relíquias
- A API da partida expõe os dados da relíquia equipada e opções de alvo.
- A interface agora solicita fileira, postura ou alvo para Espada da Noite e da Chama, Lâmina Negra e Algemas de Margit.
- A Lâmina Negra consome o escudo e a ação, mas não consome a relíquia quando o golpe é bloqueado; a ação é registrada sem retornar erro e perder a alteração do escudo.
- Efeitos de relíquias são fixos e não recebem amplificação oculta da raridade.
- A mesma relíquia não pode ocupar simultaneamente uma posição do deck e o slot de equipamento.
- A IA avalia o uso de sua relíquia através do mesmo motor de regras e considera alvos/modos válidos.

### Facção do deck
- A facção escolhida precisa ser a mais representada entre as unidades do deck.
- Cartas especiais não entram na contagem; empates entre facções predominantes são permitidos.
- A regra é validada no backend e refletida no construtor. Aliases legados são normalizados.
- Decks antigos já salvos mantêm a facção configurada para preservar compatibilidade; a validação é aplicada ao salvar novamente.

### Descrições e ciclo de rodada
- Textos de Geada e Névoa agora especificam Lendária ou superior para a segunda marca global, conforme o limiar efetivo do motor.
- A descrição dinâmica deixa de anunciar esse efeito em Rara/Épica.
- Ao fim da rodada, bônus, escudos, estados negativos, marcas de combo e preparação do Fio Astral são removidos de unidades descartadas e sobreviventes.
- A escolha do Sobrevivente considera o clima vigente antes de o clima ser limpo.
- A iniciativa alterna entre os jogadores a cada nova rodada, independentemente de quem venceu a rodada anterior.

## Compatibilidade
- Nenhuma migração de banco de dados.
- Partidas em andamento preservam seu estado; estados antigos sem `round_starter` usam o primeiro jogador registrado como referência inicial da alternância.
- Decks salvos não são apagados.
