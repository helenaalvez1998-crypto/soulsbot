# SoulsBot — melhorias de experiência do usuário

Este pacote contém somente os arquivos alterados para aplicar as melhorias de UX.

## O que foi atualizado

- **Central `/nara`:** painel inicial com nível, patente, barra de progresso, platinas, zerados, runs, Denários, média de avaliações e registros pendentes.
- **Meus registros:** histórico privado com filtros por situação, contagem completa, motivo de rejeição e reenvio de registros rejeitados com os dados anteriores preenchidos. O membro ainda precisa revisar os dados e anexar novamente os comprovantes.
- **Formulários de jogos:** plataforma recente pré-selecionada, aviso de títulos semelhantes, revisão antes do envio, nota de 1 a 10, dificuldade percebida de 1 a 5 e comentário opcional.
- **Perfil:** média de avaliação, dificuldade percebida, plataformas mais usadas, jogos mais bem avaliados e conquistas recentes.
- **Rankings:** novos rankings de jogos mais bem avaliados e jogos mais difíceis segundo as avaliações aprovadas da comunidade, exigindo pelo menos três avaliações por título.
- **Progressão XP:** filtros para comandos, bots, webhooks, mensagens curtas e canais de moderação; deduplicação de conteúdo repetido por sete dias e limite de até 20 mensagens elegíveis por dia.
- **Notificações:** preferências individuais para aprovações, rejeições, níveis, respostas/atualizações e desafios; o envio por DM respeita essas preferências.
- **Desafios:** atualização do resumo público de inscritos, participantes em andamento e conclusões autodeclaradas.
- **Banco de dados:** novas tabelas e migrações aditivas; os dados existentes são preservados.

## Arquivos incluídos

- `database.py`
- `notificacoes.py` (novo)
- `cogs/avaliacao_jogo.py`
- `cogs/comunidade.py`
- `cogs/painel_membros.py`
- `cogs/perfil.py`
- `cogs/platinas.py`
- `cogs/progressao.py`
- `cogs/ranking.py`
- `cogs/soulslike.py`
- `cogs/zerados.py`

## Instalação

1. Faça backup do banco de dados de produção (`data/jogos.db`) e das configurações (`.env`).
2. Extraia o ZIP diretamente na pasta raiz do projeto SoulsBot, preservando a estrutura `cogs/`.
3. Substitua somente os arquivos listados no pacote.
4. Inicie o bot normalmente. As migrações adicionam as novas colunas/tabelas sem apagar os registros existentes.
5. Não substitua o banco de produção pelo `data/jogos.db` de outro pacote ou ambiente.

## Validação realizada

- Compilação de 87 arquivos Python: sem erros de sintaxe.
- Testes direcionados: 14 passaram; 1 foi ignorado.
- Migrações SQLite, persistência e consultas dos rankings de jogos: verificadas com banco de teste.
- Limitação: `discord.py` e `aiosqlite` não estavam instalados no ambiente de edição; não foi possível validar interações reais com o Discord nesta execução.
