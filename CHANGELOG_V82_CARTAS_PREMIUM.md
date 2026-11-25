# V82 — Primeiro template premium integrado

- Criado template ornamental rasterizado de alta qualidade para Ordem Áurea.
- Separada a janela da ilustração por transparência; moldura, medalhões, faixa e painel inferior permanecem como asset fixo.
- Criado `renderizador_cartas_premium.py`, que recebe a arte já produzida pelo renderizador atual e insere textos do catálogo/motor.
- Habilidade, explicação de raridade (quando o motor fornece uma mudança efetiva) e lore são renderizados em áreas separadas.
- O pipeline premium é usado somente quando existe template homologado para a facção. Véu Carmesim e Lua Negra permanecem no renderer legado até receberem seus assets próprios; não se usa brasão errado como fallback.
- Cache persistente existente é preservado; fingerprint passa a incluir o novo módulo e o asset.
- Nenhuma mecânica, atributo ou ID foi alterado.
