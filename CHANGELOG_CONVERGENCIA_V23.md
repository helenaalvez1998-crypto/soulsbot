# V23 — Ritual de Convergência

## Implementado
- Convergência determinística de três exemplares do mesmo modelo e raridade.
- Resultado conhecido: um exemplar do mesmo modelo na raridade seguinte.
- O novo exemplar começa no piso de poder da nova raridade; poder e lapidação dos sacrificados não são transferidos.
- Registro de cada sacrifício em `cartas_convergencias.sacrificios_json`.
- Histórico consultável por `coliseu_listar_convergencias`.
- Cartas especiais não podem ser fundidas.
- Primordiais e Singulares exigem ritual especial e não entram na receita comum.

## Limites desta versão
- A receita comum está implementada na camada de banco de dados; interface visual de seleção/preview e receitas de linhagem/ancestrais ainda não foram conectadas.
- Antes de expor o comando na interface, integrar validação de cartas equipadas nos decks e confirmação explícita dos três exemplares.
