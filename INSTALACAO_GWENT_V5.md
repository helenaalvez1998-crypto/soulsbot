> Documento histórico. A V8 substitui este fluxo e consolida o Gwent como único jogo de cartas ativo. Consulte `CHANGELOG_GWENT_V8.md` e `INSTALACAO_GWENT_V8.md`.

# Coliseu Gwent V5 — Gwent como jogo principal

## O que muda
- O site abre diretamente no Gwent do Coliseu.
- A navegação mostra somente o novo jogo Gwent.
- As telas antigas de visão geral, coleção clássica, deck de cinco cartas e duelos clássicos ficam ocultas no site.
- O backend antigo e os dados já existentes são preservados; nada é apagado do banco.
- Mantém as facções, líderes e sinergias da V4.

## Instalação
1. Faça backup do banco SQLite e dos arquivos atuais.
2. Pare o bot.
3. Extraia o pacote sobre a pasta `narabot-main`, preservando a estrutura.
4. Preserve `.env`, o banco e arquivos que não estejam no pacote.
5. Reinicie o bot e atualize o site com recarga forçada do navegador (Ctrl+F5).

## Importante sobre as cartas
O construtor de deck Gwent continua usando as cartas que cada jogador já possui na coleção compartilhada, incluindo cartas antigas compatíveis e as cartas novas adicionadas na V4. Esta atualização troca o jogo principal e a interface; ela não apaga nem substitui automaticamente o inventário dos jogadores.

## Validação
- JavaScript: `node --check site/app.js` aprovado.
- Python: compilação dos módulos alterados aprovada.
- Testes do motor Gwent: 21 aprovados.
- A instalação no servidor/produção não foi executada por este pacote.
