# Nara — failover Gemini com três configurações

## Variáveis

Configure no `.env`/painel de hospedagem (não versione segredos):

```dotenv
GEMINI_API_KEY=CHAVE_PROJETO_A
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_BACKUP_API_KEY=CHAVE_PROJETO_B
GEMINI_BACKUP_MODEL=gemini-3.5-flash-lite
GEMINI_THIRD_API_KEY=CHAVE_PROJETO_C
GEMINI_THIRD_MODEL=gemini-3.5-flash-lite
```

Cooldowns opcionais:
- `GEMINI_QUOTA_COOLDOWN_SECONDS` / `GEMINI_BACKUP_QUOTA_COOLDOWN_SECONDS` / `GEMINI_THIRD_QUOTA_COOLDOWN_SECONDS`
- `*_RATE_LIMIT_COOLDOWN_SECONDS`, `*_UNAVAILABLE_COOLDOWN_SECONDS`, `*_AUTH_COOLDOWN_SECONDS`
- arquivos de circuito: `GEMINI_CIRCUIT_STATE_FILE`, `GEMINI_BACKUP_CIRCUIT_STATE_FILE`, `GEMINI_THIRD_CIRCUIT_STATE_FILE`

A terceira chave pode ser desativada deixando `GEMINI_THIRD_API_KEY` vazia. O mesmo vale para as demais. Reinicie o bot após alterar variáveis.

## Ordem e recuperação

Cada requisição tenta principal → reserva → terceira, ignorando circuitos ainda em cooldown. Quota, 429/rate limit, 401/403, timeout e indisponibilidade temporária abrem somente o circuito correspondente. Erros de validação/payload que não indicam indisponibilidade não provocam troca de chave. Os circuitos persistem em arquivos separados e voltam a permitir chamadas após o cooldown; portanto, uma chave recuperada é testada automaticamente na próxima solicitação elegível.

A conversa mantém prompt, pedido e contexto neutro constantes durante o failover. Ferramentas só são executadas pelo núcleo do agente depois que o modelo retorna chamadas válidas; a troca de provedor não repete a execução de ferramenta.

## Cotas Google

A quota é aplicada conforme o projeto/limites do Google, não pela quantidade de strings de chave cadastradas. Chaves diferentes do mesmo projeto normalmente compartilham limites e não constituem três cotas isoladas. Para redundância de quota, use chaves de projetos Google Cloud independentes, confirme no AI Studio/Google Cloud Console o projeto associado a cada chave e confira se cada projeto tem acesso ao modelo escolhido. Projetos independentes ainda podem estar sujeitos a limites organizacionais, modelo/região e políticas comuns do Google; não há garantia de três franquias idênticas.

## Segurança e operação

- Não inclua chaves no código, commits, issues, mensagens Discord ou logs.
- Restrinja acesso ao `.env` e à pasta `data/` (os arquivos de circuit breaker não contêm chaves).
- `/gemini_status` mostra os três estados locais; circuito liberado não prova que a quota remota esteja disponível.
- Quando os três falharem, a Nara responde pela contingência local; comandos/FAQ/SQLite continuam disponíveis.
- Este failover não substitui a Tavily na pesquisa web. Se a Tavily estiver indisponível, pesquisas que dependem de fontes web continuam suspensas, embora conversa e recursos locais permaneçam ativos.
