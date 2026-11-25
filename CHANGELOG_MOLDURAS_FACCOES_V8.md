# V8 — Molduras com arquitetura própria por facção

## Escopo

Atualiza exclusivamente o renderizador visual das molduras. A janela da ilustração, o sistema de geração/substituição de arte, textos, poder, raridade, fileira, habilidade e regras do jogo permanecem no mesmo fluxo.

## Alterações

- A silhueta estrutural da moldura agora depende da facção, além dos ornamentos e cores já existentes:
  - **Ordem Áurea:** perfil de arquitetura sagrada, ombros chanfrados e coroamento central inspirado em Leyndell/Térvore.
  - **Véu Carmesim:** perfil mais agressivo, com recortes e espinhos laterais inspirados nos ritos de Mohgwyn.
  - **Lua Negra:** perfil ogival e astral, com arcos e coroamento pontiagudo inspirado na arquitetura cariana.
- A raridade continua determinando o acabamento metálico, espessura, brilho e ornamentos próprios.
- Filete interno recebe a cor heráldica da facção para reforçar a leitura sem substituir a cor da raridade.
- Normalização centralizada dos nomes de facção, inclusive aliases legados `Casa Cariana` e `Dinastia Mohgwyn`, evitando fallback visual incorreto para Ordem Áurea.
- Normalização aplicada também ao renderizador principal e ao caminho de renderização com template.
- Versão do renderizador atualizada para invalidar o cache persistente antigo automaticamente.
- Janela da arte e fluxo de substituição da ilustração não foram alterados.

## Validação

- Compilação Python de `sistemas/molduras_cartas.py` e `sistemas/arte_cartas.py`.
- Testes das 21 combinações (3 facções × 7 raridades).
- Testes de silhuetas distintas e aliases legados.
- Suíte geral do projeto: ver resultado de execução na entrega.
