# Design das cartas V5 — Facção + raridade

## Objetivo

Atualizar o renderizador Pillow para que a moldura comunique a raridade e os emblemas/painéis comuniquem a facção, sem exibir custo de carta.

## Alterações

- A moldura metálica agora usa uma escala visual consistente por raridade:
  - Comum: aço/prata.
  - Rara: azul.
  - Épica: violeta.
  - Lendária: ouro.
  - Mítica: carmesim.
  - Primordial: marfim celestial.
  - Singular: obsidiana iridescente.
- Os emblemas continuam identificando a facção com glifos próprios: Térvore (Ordem Áurea), sangue (Véu Carmesim) e lua (Lua Negra).
- A cor da facção permanece nos detalhes do painel e nos acentos, sem substituir a cor principal da raridade.
- A gema de tipo e o ícone de fileira continuam separados do emblema da facção, evitando confusão entre categoria, posição e facção.
- Nenhum custo é desenhado na carta padrão. O espaço inferior é usado pela habilidade e sua descrição.
- `VERSAO_ARTES` foi incrementada para invalidar as cartas antigas no cache e forçar a regeneração visual.

## Compatibilidade

- Não altera regras, poder, raridade, facção, coleção, decks ou banco de dados.
- Mantém o fluxo de arte enviada pelo jogador e os templates completos configurados pelo Ateliê.
- Templates personalizados antigos podem continuar exibindo elementos que já estejam desenhados na própria imagem (por exemplo, um custo impresso). Para removê-los, substitua o template por um sem esse elemento.

## Validação

- Compilação Python: aprovada.
- Testes automatizados existentes: 21 aprovados.
- Pré-renderização das sete raridades: aprovada.
