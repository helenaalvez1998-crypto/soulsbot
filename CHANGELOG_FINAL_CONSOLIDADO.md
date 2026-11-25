# NARA — consolidação de entrega

## Comandos e navegação
- Superfície slash limitada a `/nara`, `/jogo` e `/adm`.
- `/jogo` abre a central do Coliseu no Discord; partidas, construtor de deck e Ateliê ficam no site.

## Mercado do Coliseu
- Reativada compra de pacote com 3 cartas por 120 Denários, limitada a 3 pacotes em 24 horas.
- Compra, cobrança, recompensas e pity executam na mesma transação SQLite.
- Drops de pacotes usam o mesmo inventário de exemplares/raridades dos drops de atividades.
- Duplicatas geram Almas ou fragmentos; Primordiais podem sair com chance de 0,1% por carta.
- Após 10 cartas Comuns consecutivas, a próxima recebe proteção de raridade (Rara ou superior).
- Forja direta por Almas permanece desativada; Almas continuam usadas para lapidar exemplares e fragmentos para evolução.

## Site
- Mercado com saldo, limite diário, confirmação de compra e resultado das três cartas.
- Atualização do inventário, saldo e histórico após abertura.

## Validação
- Suíte automatizada e compilação Python executadas na consolidação.
- Verificação sintática JavaScript executada quando Node.js está disponível.
- Teste real com duas contas Discord, OAuth de produção e partida online ainda depende do servidor configurado pelo proprietário.
