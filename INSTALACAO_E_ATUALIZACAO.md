# Instalação e atualização — Soulsbot

## Requisitos

- Python 3.11 ou superior.
- Um bot criado no Discord Developer Portal.
- Respostas básicas da Nara não exigem chave de IA. Para análise com failover gratuito, configure duas chaves Gemini de projetos Google diferentes e uma chave do plano gratuito Tavily para busca web.
- Armazenamento persistente para `data/` (recomendado).

## Instalação inicial

1. Extraia o ZIP inteiro para uma pasta. Não execute o `bot.py` de dentro do ZIP.
2. Crie um ambiente virtual: `python -m venv .venv`.
3. Ative o ambiente e instale: `pip install -r requirements.txt`.
4. Copie `.env.example` para `.env` (ou `env.example` para `.env`).
5. Preencha `DISCORD_TOKEN`, IDs, as chaves Gemini principal/reserva e `TAVILY_API_KEY` gratuita.
6. Mantenha `NARA_CHAT_IA_ENABLED=false` e `OFFERS_SHOW_DESCRIPTION=false` para máxima economia.
7. No Discord Developer Portal, habilite **Message Content Intent**, **Server Members Intent** e **Voice States**, conforme os recursos usados.
8. Execute `python bot.py` e confira os logs.

## Atualização de uma instalação existente

1. Pare o bot.
2. Faça backup de `data/` e do `.env`.
3. Extraia os arquivos do ZIP atualizado sobre o projeto.
4. Preserve o `.env` existente e não apague `data/colizeu.db`.
5. Instale dependências com `pip install -r requirements.txt`.
6. No painel da hospedagem, remova variáveis antigas de provedores que não serão mais usados e configure `GEMINI_API_KEY`, `GEMINI_BACKUP_API_KEY` e `TAVILY_API_KEY`.
7. Reinicie o bot e leia os logs.

## Como criar as chaves sem contratar planos pagos

1. No [Google AI Studio](https://aistudio.google.com/), abra/crie o projeto principal e gere uma API key para `GEMINI_API_KEY`.
2. Crie ou selecione um segundo projeto Google diferente e gere outra key para `GEMINI_BACKUP_API_KEY`. Não basta criar duas chaves dentro do mesmo projeto: elas compartilham a quota.
3. Não vincule faturamento/conta de billing a nenhum dos projetos. Use apenas o Free Tier de geração de texto.
4. Na [Tavily Pricing](https://www.tavily.com/pricing), cadastre-se no plano **Researcher Free** (1.000 créditos mensais, sem cartão de crédito) e copie a API key para `TAVILY_API_KEY`.
5. No painel Tavily, permaneça no plano gratuito. Não selecione Pay-as-you-go, upgrade ou compra de créditos.

A busca Tavily usa Search Basic, que consome 1 crédito por consulta. Este bot limita a até quatro consultas na etapa de pesquisa do catálogo; a identificação inicial normalmente utiliza uma consulta. Assim, uma identificação + pesquisa completa usa até cinco créditos quando todas as consultas são executadas. Os créditos gratuitos são renovados no primeiro dia do mês; se acabarem, as chamadas param até a renovação ou upgrade — este bot não tenta fazer upgrade.

## Configuração dos dois projetos Gemini

As variáveis no painel da hospedagem têm precedência sobre o `.env`.

- `GEMINI_API_KEY`: chave do projeto principal.
- `GEMINI_MODEL`: modelo habilitado no projeto principal.
- `GEMINI_BACKUP_API_KEY`: chave do segundo projeto Google, usada automaticamente quando o principal falhar.
- `GEMINI_BACKUP_MODEL`: modelo do projeto reserva; por padrão, usa o mesmo modelo.
- `GEMINI_QUOTA_COOLDOWN_SECONDS=21600`: pausa do projeto principal após quota esgotada.
- `GEMINI_BACKUP_QUOTA_COOLDOWN_SECONDS=21600`: pausa independente do reserva.
- `GEMINI_CIRCUIT_STATE_FILE=data/gemini_circuit.json`: estado persistente do principal.
- `GEMINI_BACKUP_CIRCUIT_STATE_FILE=data/gemini_backup_circuit.json`: estado persistente do reserva.
- `TAVILY_API_KEY`: chave da pesquisa web gratuita.
- `TAVILY_MAX_QUERIES_PER_JOB=4`: no máximo quatro consultas Basic por tarefa.
- `TAVILY_CIRCUIT_STATE_FILE=data/tavily_circuit.json`: pausa persistente quando a quota free terminar.

**Atenção à quota:** o Google aplica limites por projeto, não por chave. Duas chaves criadas dentro do mesmo projeto compartilham a mesma quota e não oferecem reserva de quota. Para isolamento, as duas chaves devem pertencer a projetos diferentes. Isso não garante que o Google conceda a cada projeto o mesmo nível de acesso gratuito nem autoriza contornar limites da plataforma.

**Sem pagamento:** não vincule contas de faturamento aos projetos Google e não habilite Pay-as-you-go/upgrade na Tavily. A Tavily Free/Researcher publica 1.000 créditos mensais; o bot usa somente Search Basic, com limite de até quatro consultas por tarefa. Quando os créditos gratuitos terminarem, a pesquisa pausa até a renovação, sem compra automática. Confirme o plano gratuito no painel Tavily antes de criar a chave.

A pesquisa é feita pela Tavily Free; os dois Gemini recebem apenas texto + trechos/URLs recuperados, sem Google Search grounding. Isso evita usar grounding que não está disponível gratuitamente no modelo `gemini-3.5-flash-lite`. Gemini principal e reserva precisam estar em projetos Google distintos para terem circuit breakers e quotas por projeto independentes; duas chaves no mesmo projeto compartilham quota. Projetos separados não garantem franquias ou disponibilidade idênticas, e não devem ser usados para contornar regras do Google.

O comando `/gemini_status` mostra os dois circuit breakers Gemini e o estado local da Tavily. “Circuito liberado” não confirma a quota real restante em nenhum fornecedor.

## Economia da Nara e anexos visuais

`nara_local.py` responde perguntas frequentes e consulta SQLite sem API. `NARA_CHAT_IA_ENABLED=false` mantém o chat de IA desligado; o Gemini fica reservado a `/jogo_buscar`. `OFFERS_SHOW_DESCRIPTION=false` evita chamadas para tradução de ofertas. O agente recebe apenas texto: prints/imagens não são baixados, lidos ou enviados aos modelos. Comprovantes dos formulários continuam disponíveis para revisão humana nos módulos próprios.

## Testes locais

```bash
python -m compileall -q .
pytest -q
python -m unittest discover -s tests -v
```

## Diagnóstico no Discord

- `/gemini_status`: mostra estado dos circuit breakers principal e reserva.
- `/catalogo_fila`: mostra pedidos e erros técnicos.
- `/catalogo_admin`: abre a administração do Caçador.

## Segurança

Nunca envie `.env`, token Discord, chaves Google, banco SQLite ou backups de membros em canais públicos. O ZIP não contém credenciais nem banco local.
