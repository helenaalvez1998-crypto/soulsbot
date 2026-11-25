> Documento histórico. A V8 substitui este fluxo e consolida o Gwent como único jogo de cartas ativo. Consulte `CHANGELOG_GWENT_V8.md` e `INSTALACAO_GWENT_V8.md`.

# Instalação — Coliseu / Arena Gwent v3

## Antes de atualizar
1. Pare o bot.
2. Faça backup do banco SQLite e da pasta `data`.
3. Preserve o `.env` e configurações locais.

## Atualização
1. Extraia o ZIP sobre a pasta atual do projeto, substituindo os arquivos.
2. Não substitua o `.env`.
3. Instale dependências somente se necessário: `pip install -r requirements.txt`.
4. Reinicie o bot.

## Conteúdo
- 8 novas unidades e 5 novas cartas especiais.
- 5 novas habilidades de unidade e 5 novos efeitos especiais.
- Líderes com efeito específico por facção.
- Deck Gwent com 12 cartas únicas: mínimo de 8 unidades e máximo de 4 especiais.
- Novas cartas incluídas no catálogo de pacotes do Discord.

## Dados existentes
A atualização não apaga coleções, saldos, conquistas, patentes, decks clássicos, históricos ou partidas persistidas. Nenhuma migração destrutiva foi adicionada.

## Validação desta entrega
- 16 testes unitários do motor Gwent aprovados.
- `py_compile` aprovado nos módulos Python alterados.
- `node --check site/app.js` aprovado.
- Catálogo carregado: 52 cartas de pacote, das quais 11 são especiais.
- Integração completa Discord/site em produção não foi executada neste ambiente.
