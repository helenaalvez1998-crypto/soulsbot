# SoulsBot — Etapa 5: subpainéis administrativos

## Alteração desta entrega
- O histórico de auditoria ganhou um botão **Atualizar**.
- Atualizar preserva filtro, termo de pesquisa e página, recarregando os dados atuais.
- O botão é reconstruído junto com os demais controles após paginação/filtragem.
- A navegação contextual de retorno à categoria foi preservada.

## Preservação
- Não foram removidos comandos, categorias, ações administrativas, permissões ou handlers.
- O patch altera somente `cogs/admin.py`; os testes incluídos são opcionais para produção.

## Instalação
1. Faça backup do projeto.
2. Extraia o ZIP na raiz, substituindo `cogs/admin.py`.
3. Reinicie o bot.

## Validação
- Testes estruturais incluídos em `tests/`.
- A execução em Discord real depende de validar com a aplicação e permissões do servidor.
