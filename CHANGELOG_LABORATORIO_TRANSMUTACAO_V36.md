# V36 — Integração das cartas pessoais ao motor Gwent

## Implementado

- Cartas publicadas pelo Laboratório são resolvidas por `owner_id + card_id` no servidor; uma conta não pode carregar a definição pessoal de outra conta para seu próprio deck.
- O construtor de deck (`GET/POST /api/gwent/deck`) reconhece cartas `transmutacao_*` publicadas e exige um exemplar pertencente ao jogador autenticado.
- O endpoint de coleção (`GET /api/gwent/cards`) inclui cartas pessoais do proprietário.
- Snapshots de deck usados para criar partidas PvP e treino contra a NARA incluem a definição pessoal validada. O snapshot fica congelado no estado da partida, permitindo que o adversário enfrente a carta sem receber sua propriedade.
- `preparar_carta_pessoal` valida a definição procedural e o exemplar, converte a carta para o contrato comum do motor e preserva as habilidades comuns aprovadas.
- Cartas pessoais continuam unidades, não especiais; Primordial e Singular seguem bloqueadas no Laboratório.
- A preparação aceita raridade/poder do exemplar após progressão individual pela Forja, desde que permaneçam dentro das faixas permitidas.
- Endpoint de imagem serve o PNG individual validado a jogadores autenticados, verificando contenção do caminho e SHA-256 antes de servir.

## Testes

- Testes direcionados V34/V35/Gwent + novos testes V36: 35 aprovados, 7 subtests aprovados.
- `py_compile` de `bot.py` e `sistemas/gwent.py`: aprovado.
- Suíte completa: iniciou, mas excedeu o limite de execução desta sessão; não classificada como aprovada.

## Limitações

- Não foi possível importar/executar o bot completo no ambiente de validação porque o pacote `discord.py` não está instalado.
- Não houve teste end-to-end de partidas com banco de produção, duas contas reais, nem validação visual do navegador.
- O motor de batalha recebe o snapshot da definição pessoal; o histórico mantém a definição congelada no JSON da partida. Não foi criada sincronização retroativa de cartas em partidas já iniciadas.
- A V36 não altera custos, probabilidades, balanceamento de Primordiais/Singulares nem as regras de sacrifício.

## Instalação

Consulte `INSTALACAO_LABORATORIO_TRANSMUTACAO_V36.md`. Faça backup do banco e dos arquivos de dados antes de atualizar. Homologue com duas contas distintas antes de produção.
