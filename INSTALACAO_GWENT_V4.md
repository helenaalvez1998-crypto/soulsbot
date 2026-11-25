> Documento histórico. A V8 substitui este fluxo e consolida o Gwent como único jogo de cartas ativo. Consulte `CHANGELOG_GWENT_V8.md` e `INSTALACAO_GWENT_V8.md`.

# Coliseu Gwent V4 — Facções, líderes e sinergias

## Arquivos
Este pacote é incremental: extraia os arquivos mantendo a estrutura `narabot-main/` e substitua somente os arquivos incluídos.

## Instalação
1. Faça backup do banco SQLite e dos arquivos atuais.
2. Pare o bot.
3. Extraia este pacote sobre a versão Coliseu V3.
4. Preserve `.env`, o banco de dados e os demais arquivos que não estão neste pacote.
5. Reinicie o bot. A migração adiciona `faction` e `leader_id` à tabela `cartas_gwent_decks`; os decks existentes são preservados.
6. No site, abra Arena Gwent, escolha uma facção e um líder, e salve novamente o deck.

## Regras da versão
- Facções: Ordem de Ferro, Errantes do Véu e Conclave Arcano.
- Cada facção oferece dois líderes selecionáveis.
- A facção e o líder são salvos com o deck e congelados na criação de cada partida.
- Decks legados sem facção salva continuam jogáveis; a facção é inferida pela composição do deck.
- Três novas unidades com sinergias específicas entram no catálogo e podem ser obtidas pelo sistema de cartas existente.
- O deck clássico de cinco cartas e suas regras não são alterados.

## Validação
Testes do motor Gwent: 21 aprovados. Sintaxe Python e JavaScript verificadas. A integração com Discord/site em produção ainda deve ser validada no servidor.
