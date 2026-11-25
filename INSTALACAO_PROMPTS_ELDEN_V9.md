# Instalação — Prompts de arte Elden Ring V9

Esta atualização altera somente os textos de instrução usados pelo Ateliê para gerar as ilustrações.

## Instalação

1. Faça backup da pasta atual do bot.
2. Pare o bot.
3. Extraia o ZIP e copie a pasta `narabot-main` sobre a instalação atual, substituindo os arquivos.
4. Preserve `.env`, banco de dados, pasta `data/` e artes já enviadas pelos jogadores.
5. Reinicie o bot.
6. Abra o Ateliê e gere novamente o prompt de cada carta cuja arte deseja refazer.

## O que permanece igual

- Moldura e renderizador Python/Pillow.
- Símbolos, cores, raridade, poder e painel de habilidade.
- Proporção 5:4 e recorte da área de arte.
- Upload e substituição manual de imagens.
- Regras, decks, coleção e banco de dados.

Artes já existentes não são alteradas automaticamente. A nova direção de arte é aplicada quando um novo prompt é gerado e uma nova imagem é criada/substituída.

Não há migração de banco de dados.
