# V17 — Retratos dos líderes

## O que mudou
- A carta de comando dos líderes agora usa arte individual para Godfrey, Morgott, Radagon, Mohg, Rykard, Esgar, Rennala, Astel e Loretta.
- Os nove retratos ficam em `site/assets/leaders/` no formato WebP.
- A moldura e a paleta continuam associadas à facção: Ordem Áurea (dourado), Véu Carmesim (vermelho) e Lua Negra (azul).
- Nome, facção, descrição do efeito e identificação de carta de comando continuam sendo renderizados pela interface, não dependem do texto embutido na imagem.
- Líderes permanecem sem poder e custo numéricos; seus efeitos mecânicos não foram alterados.

## Origem da arte
Os retratos foram recortados de uma prancha 3×3 gerada para esta versão. São imagens de referência integradas à interface; não são renders individuais de alta resolução.

## Validação
- `node --check site/app.js`: aprovado.
- `python -m compileall -q .`: aprovado.
- `pytest`: iniciou e avançou por 44 testes, mas excedeu o limite de execução do ambiente em duas tentativas; não declarar a suíte completa como aprovada nesta versão.
