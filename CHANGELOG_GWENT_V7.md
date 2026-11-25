> Documento histórico. A V8 substitui este fluxo e consolida o Gwent como único jogo de cartas ativo. Consulte `CHANGELOG_GWENT_V8.md` e `INSTALACAO_GWENT_V8.md`.

# Gwent V7 — conversão integral do catálogo

## O que mudou

- O catálogo que antes continha categorias de outro modo (`Chefe`, `Arma`, `Magia`, `Covenant`, `Jogo`, `Patente` e `Relíquia`) agora é apresentado ao Gwent como `Unidade` ou `Especial`.
- Cada carta possui facção, fileira e papel tático derivados de seu tipo e identidade.
- As cartas de armas e feitiços que funcionavam como itens abstratos receberam nomes de combatentes/personagens, preservando seus IDs históricos.
- Cartas de conquistas e patentes agora são apresentadas como Campeões e Veteranos do Gwent.
- As cinco Primordiais receberam identidade de personagens/entidades e continuam únicas.
- As descrições das habilidades foram revisadas para refletir os efeitos que o motor Gwent realmente executa.
- A arte mantém a composição temática de origem, mas a identificação exibida passa a ser `Unidade`/`Especial`; isso evita quebrar artes personalizadas existentes.
- Coleções, quantidades, IDs, decks salvos, recompensas e histórico não são apagados. Os IDs antigos são a chave de migração para preservar a posse dos jogadores.

## Compatibilidade

A conversão é feita na camada de catálogo/API, sem reescrever registros de inventário. Decks salvos continuam apontando para os mesmos IDs, agora serializados com os metadados do Gwent. Partidas já em andamento preservam seus snapshots antigos até serem concluídas.

## Validação

- Testes do motor Gwent e da conversão do catálogo.
- Verificação de sintaxe Python e JavaScript.
- Renderização de cartas com categoria visual de origem e rótulo atual do Gwent.
