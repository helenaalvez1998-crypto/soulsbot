# Instalação — Gwent V8

1. Desligue o bot.
2. Faça backup do banco SQLite, da pasta `data/` e da versão atual do projeto.
3. Extraia o ZIP V8 sobre a pasta `narabot-main`, substituindo os arquivos do código.
4. Preserve `.env`, o banco `data/colizeu.db` (ou o caminho definido por `DATA_DIR`) e arquivos personalizados que não façam parte do pacote.
5. Confirme que `cogs/cartas_coliseu.py` foi removido; o Gwent é o único jogo de cartas ativo.
6. Inicie com `python bot.py`.
7. Confira os logs de inicialização e abra o site com `Ctrl + F5`.
8. Faça login com uma conta Discord e confirme que a coleção recebe o kit inicial apenas uma vez.
9. Teste o mercado com saldo suficiente e depois uma partida entre duas contas com decks válidos.

## Compatibilidade e dados

- Não apague nem substitua o banco existente.
- Os IDs e quantidades da coleção são preservados.
- Em bancos existentes, tabelas antigas de deck/duelo permanecem intactas como histórico; instalações novas não as criam e o runtime não as acessa.
- O primeiro acesso ao site entrega os kits iniciais de forma idempotente.
- Pacotes custam 120 Denários e o limite é três a cada 24 horas.
- A forja usa Almas; Primordiais não podem ser forjadas.

## Verificação

O pacote inclui testes locais do motor, catálogo e renderização. A validação em produção exige duas contas Discord reais para testar desafios, turnos, reconexão, recompensas e permissões.
