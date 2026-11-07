# Instalação e atualização — Soulsbot

## Requisitos

- Python 3.11 ou superior.
- Um bot criado no Discord Developer Portal.
- As respostas básicas não usam IA externa. Para failover automático, configure `DEEPSEEK_API_KEY` (principal) e `GEMINI_API_KEY` (reserva). Com apenas uma chave, o bot usa apenas esse provedor e não terá reserva quando ele falhar.
- Ambiente com armazenamento persistente para `data/` (recomendado).

## Instalação inicial

1. Extraia o ZIP inteiro para uma pasta do projeto. Não execute o `bot.py` de dentro do ZIP.
2. Crie um ambiente virtual: `python -m venv .venv`.
3. Ative o ambiente e instale as dependências: `pip install -r requirements.txt`.
4. Copie `.env.example` para `.env` (ou `env.example` para `.env`).
5. Preencha `DISCORD_TOKEN` e os IDs dos canais/cargos. Configure `DEEPSEEK_API_KEY` e `GEMINI_API_KEY` para failover automático nas pesquisas de jogos/catálogos.
6. Confira `DEEPSEEK_MODEL=deepseek-flash` e `GEMINI_MODEL`. DeepSeek Flash usa Search + Chat API; Gemini é reserva via Google Search grounding.
7. No Discord Developer Portal, habilite **Message Content Intent**, **Server Members Intent** e **Presence/Voice States** conforme os recursos usados.
8. Execute `python bot.py` e confira se a inicialização termina sem traceback.

## Atualização de uma instalação existente

1. Pare o processo do bot.
2. Faça backup de `data/` e do arquivo `.env`.
3. Extraia os arquivos do ZIP atualizado sobre o diretório do projeto.
4. **Não substitua** o `.env` existente e **não apague** `data/colizeu.db`.
5. Instale dependências atualizadas com `pip install -r requirements.txt`.
6. Reinicie o processo e leia os logs.
7. Confirme que os comandos aparecem no Discord. Se `GUILD_ID` estiver configurado, a sincronização é por servidor; se estiver vazio, comandos globais podem demorar a propagar.

## Variáveis dos provedores e precedência

As variáveis definidas no painel da hospedagem/processo têm precedência sobre o `.env`. As respostas locais da Nara não dependem de nenhuma chave. Para o Caçador de Troféus, configure as duas APIs para que a alternância automática funcione:

- `DEEPSEEK_API_KEY`: chave da plataforma DeepSeek.
- `DEEPSEEK_MODEL=deepseek-flash`: modelo principal oficial atual.
- `DEEPSEEK_BASE_URL=https://api.deepseek.com`: endpoint oficial.
- `GEMINI_API_KEY`: chave Google AI Studio usada como reserva automática quando DeepSeek falhar ou não retornar fontes verificáveis.
- `GEMINI_MODEL`: modelo Google disponível no projeto e compatível com Search grounding.
- `AI_PRIMARY_PROVIDER=deepseek`: provedor preferido nas conversas com IA (quando habilitadas).
- `DEEPSEEK_QUOTA_COOLDOWN_SECONDS=21600`: pausa padrão após saldo insuficiente.
- `DEEPSEEK_RATE_LIMIT_COOLDOWN_SECONDS=60`: pausa após HTTP 429.
- `DEEPSEEK_UNAVAILABLE_COOLDOWN_SECONDS=45`: pausa após timeout/5xx.
- `DEEPSEEK_AUTH_COOLDOWN_SECONDS=3600`: pausa após chave inválida (401).
- `DEEPSEEK_CIRCUIT_STATE_FILE=data/deepseek_circuit.json`: estado persistente.
- `GEMINI_QUOTA_COOLDOWN_SECONDS=21600`: pausa padrão após quota/billing esgotado.
- `GEMINI_RATE_LIMIT_COOLDOWN_SECONDS=60`: pausa para 429 transitório.
- `GEMINI_UNAVAILABLE_COOLDOWN_SECONDS=45`: pausa para 5xx.
- `GEMINI_CIRCUIT_STATE_FILE=data/gemini_circuit.json`: estado persistente.

O comando `/gemini_status` agora mostra os estados dos dois provedores. Circuit breakers independentes evitam insistir no provedor indisponível; o outro é acionado para a solicitação atual. Quando o bloqueio expira, o provedor principal volta a ser testado automaticamente em uma nova solicitação. Um erro de autenticação, saldo ou quota não altera prompts, dados do servidor ou o outro provedor.
## Economia da Nara e anexos visuais

`nara_local.py` resolve perguntas frequentes e consultas ao SQLite sem chamar IA externa. Por padrão, `NARA_CHAT_IA_ENABLED=false` desativa chamadas aos provedores pelo chat da Nara; as APIs ficam reservadas ao `/jogo_buscar`, quando o catálogo local não resolve a pesquisa. `OFFERS_SHOW_DESCRIPTION=false` também evita tradução de descrições de ofertas via IA. Em uma instalação existente, confira essas variáveis no `.env` e no painel da hospedagem, porque o `.env` antigo não é substituído automaticamente. A pesquisa conversacional pode ser habilitada explicitamente (`NARA_CHAT_IA_ENABLED=true`), mas isso consome quota e fica limitada por `IA_LIMITE_DIARIO=3` por membro/dia. O agente de conversa recebe somente texto: a Nara não baixa, abre ou envia imagens/prints ao provedor. Os comprovantes enviados pelos formulários de platina/run/zerados continuam disponíveis para revisão humana nos respectivos módulos. Consulte `NARA_ECONOMIA.md` para simulações e regras.

## Testes locais

```bash
python -m compileall -q .
pytest -q
python -m unittest discover -s tests -v
```

## Diagnóstico no Discord

- `/gemini_status`: mostra aos administradores se o circuito local está pausado.
- `/catalogo_fila`: mostra solicitações e a razão técnica guardada para a equipe.
- `/catalogo_admin`: abre a administração do Caçador de Troféus.

`/gemini_status` sem bloqueio local não garante que o projeto tenha quota disponível no Google; o comando só mostra o estado conhecido pelo processo do bot.

## Segurança

Nunca envie `.env`, token do Discord, chaves Gemini/DeepSeek, banco SQLite ou backup com dados de membros para chats públicos. O ZIP de distribuição não contém esses arquivos.
