# Narabot V72 — Manutenção de artes e deck

## Ateliê: remover todas as artes aplicadas
- Adicionada ação em lote visível somente para a equipe administradora do Ateliê.
- A ação arquiva todas as submissões comunitárias com status `approved`, retirando essas ilustrações das cartas e restaurando a arte-base.
- Os arquivos de imagem, créditos dos artistas e registros históricos permanecem no banco de dados; submissões pendentes e rejeitadas não são alteradas.
- A versão do sistema de artes foi incrementada para invalidar URLs/cache antigos das imagens das cartas.

## Construtor de deck: redefinir
- Adicionado botão `Redefinir deck` no painel do deck.
- A ação limpa as cartas selecionadas, os exemplares, a relíquia e a configuração do deck salvo; volta à facção padrão Ordem Áurea e seu líder padrão.
- A coleção, os exemplares possuídos e partidas já iniciadas não são alterados.
- A nova rota opera somente sobre o usuário autenticado e valida a origem da requisição.
- Ambas as ações destrutivas solicitam confirmação no navegador.

## Arquivos alterados
- `bot.py`
- `database.py`
- `sistemas/cartas.py`
- `site/index.html`
- `site/app.js`
- `site/style.css`

## Validação
- Compilação Python dos módulos alterados.
- Verificação sintática de `site/app.js` com Node.js.
- Validação das instruções SQL em SQLite: deck redefinido; submissões aprovadas arquivadas; pendentes preservadas.
