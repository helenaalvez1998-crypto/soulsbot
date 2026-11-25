# Instalação — Prompts de arte Elden Ring V7

Esta versão atualiza somente o briefing usado pelo Ateliê para gerar a ilustração da carta.

## O que muda

- O prompt passa a considerar a identidade da carta, a facção e a região do mundo de Elden Ring sugerida pelo nome/descrição.
- A arte continua sendo uma imagem independente, gerada/substituída pelo fluxo atual do Ateliê.
- O renderizador Python/Pillow, a moldura, o painel de texto, os ícones, as dimensões e o recorte não foram redesenhados.
- O upload e a substituição manual de arte continuam funcionando como antes.
- O campo de custo não é enviado ao prompt da imagem.
- Cartas de outra origem não recebem automaticamente cenário das Terras Intermédias.

## Instalação

1. Faça backup da pasta atual do bot.
2. Pare o bot.
3. Extraia o ZIP e copie os arquivos para a pasta do projeto, substituindo os correspondentes.
4. Preserve `.env`, banco de dados, pasta `data/` e imagens já enviadas pelos jogadores.
5. Reinicie o bot.
6. No Ateliê, gere novamente o prompt da carta para criar uma nova ilustração. Artes já enviadas não são alteradas automaticamente.

## Arquivos alterados/adicionados

- `sistemas/atelie_coliseu.py` — diretrizes das facções, contexto de mundo e prompt sem custo.
- `tests/test_elden_art_prompts.py` — testes do novo prompt.
- `CHANGELOG_PROMPTS_ARTE_ELDEN_V7.md` — registro técnico.

Não há migração de banco de dados.
