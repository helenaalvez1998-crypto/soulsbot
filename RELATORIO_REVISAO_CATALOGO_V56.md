# Relatório de revisão do catálogo — V56

## Escopo desta entrega

A revisão desta versão cobre correções pontuais sustentadas pelo código-fonte e pelo motor de batalha. Não representa ainda uma validação completa de cânone de todas as 110 cartas, nem auditoria dos exemplares persistidos no SQLite.

## Correções realizadas

### 1. Identidade narrativa versus tipo mecânico

O serializador de cartas anteriormente derivava a facção exibida exclusivamente de `tipo`. Isso fazia com que alinhamentos temáticos conhecidos fossem apresentados de forma inadequada em casos específicos.

Foram adicionadas exceções explícitas:
- Blaidd, o Meio-Lobo: Lua Negra.
- Carrasco de Volcano Manor: Véu Carmesim.

O campo `tipo` permanece inalterado e continua servindo às regras de composição do deck. Portanto, não houve mudança silenciosa no balanceamento ou na seleção de facção do deck.

### 2. Nome duplicado

A Especial “Juramento do Crisol” e a Relíquia Singular compartilhavam o mesmo nome apesar de funções distintas. A Relíquia foi renomeada para “Juramento Primordial do Crisol”. Seu ID interno foi preservado para não quebrar referências.

### 3. Textos das Relíquias

As descrições agora refletem os handlers encontrados em `sistemas/gwent.py`:
- Grande Runa de Godrick: exige ao menos uma unidade aliada e concede +1 de bônus a todas.
- Grande Runa dos Não Nascidos: remove Geada e Podridão dos aliados afetados; cada purificado recebe +1.
- Runa da Morte: em cada fileira, seleciona o inimigo com maior bônus positivo e reduz esse bônus em até 2.
- Espada da Noite e da Chama: Noite aplica uma marca de Geada à fileira; Chama atinge o inimigo de maior poder efetivo, reduz 1 de poder-base e 2 de bônus; Escudo bloqueia.
- Lâmina Negra: reduz o bônus do alvo em 3; Escudo bloqueia sem consumir a Relíquia.
- Algemas de Margit: zera bônus positivo, preservando bônus negativo.

### 4. Prompts de arte

Foram criadas cenas dedicadas para as seis Relíquias, removendo a dependência de uma descrição visual genérica para esses itens.

## Testes

- Suíte completa: 60 testes aprovados.
- Incluídos testes para distinção entre tipo e facção narrativa, unicidade do nome do Crisol e fidelidade dos textos das Relíquias.
- Incluídas seis cenas de arte no teste de cobertura do catálogo.

## Limitações conhecidas

- O arquivo `colizeu.db` não está presente no pacote analisado. Cartas personalizadas, exemplares persistidos, decks e registros reais de usuários não foram auditados.
- As atribuições narrativas adicionadas são exceções explícitas e pontuais; o restante do catálogo ainda exige revisão individual de cânone e de alinhamento.
- A revisão completa de todos os textos mecânicos do catálogo ainda está pendente.
