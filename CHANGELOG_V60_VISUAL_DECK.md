# NARABOT V60 — Correção visual do Deck e Coleção

## Problemas observados na captura
- Painel do deck e coleção com proporções desequilibradas.
- Cartas comprimidas, com textos e botões estreitos.
- Configuração de líder e relíquia disputando espaço na mesma área.
- Mensagem de erro de resposta JSON pouco informativa.

## Alterações
- Reequilíbrio da grade principal do Deck e Coleção.
- Cartas com largura mínima maior e grade adaptável ao espaço disponível.
- Configuração do deck organizada em coluna única.
- Ajustes de filtros, títulos, nomes e botões para evitar quebras ruins.
- Em telas menores, o painel passa para uma coluna e a coleção usa duas colunas.
- Leitura das respostas da API do deck com parser que exibe status HTTP e trecho da resposta inválida, em vez do erro genérico do JSON.parse.

## Validação
- `node --check site/app.js`: aprovado.
- Não foi possível validar a resposta real de `/api/gwent/deck` sem executar o site conectado ao servidor e à sessão Discord.
- Se a API continuar devolvendo HTML, a mensagem agora deverá mostrar o status e o início da resposta para identificar rota ausente, redirecionamento ou erro do servidor.
