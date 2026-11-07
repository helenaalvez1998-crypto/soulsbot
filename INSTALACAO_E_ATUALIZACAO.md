# Instalação e atualização — Soulsbot

## Requisitos

- Python 3.11 ou superior.
- Um bot criado no Discord Developer Portal.
- Uma chave Gemini somente para os recursos de IA.
- Ambiente com armazenamento persistente para `data/` (recomendado).

## Instalação inicial

1. Extraia o ZIP inteiro para uma pasta do projeto. Não execute o `bot.py` de dentro do ZIP.
2. Crie um ambiente virtual: `python -m venv .venv`.
3. Ative o ambiente e instale as dependências: `pip install -r requirements.txt`.
4. Copie `.env.example` para `.env` (ou `env.example` para `.env`).
5. Preencha `DISCORD_TOKEN`, IDs dos canais/cargos e `GEMINI_API_KEY`.
6. Confira `GEMINI_MODEL`. O padrão do pacote é `gemini-3.8-flash`; `gemini-3.5-flash-lite` também é compatível com Google Search grounding segundo a documentação atual do Google.
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

## Variáveis Gemini e precedência

As variáveis definidas no painel da hospedagem/processo têm precedência sobre os valores do `.env`. O bot registra no log o `GEMINI_MODEL` efetivamente recebido. Portanto, se o painel ainda contém `gemini-3.5-flash-lite`, mudar apenas o `.env` não altera o modelo carregado.

- `GEMINI_API_KEY`: chave do projeto Google AI Studio.
- `GEMINI_MODEL`: modelo habilitado no projeto.
- `GEMINI_QUOTA_COOLDOWN_SECONDS=21600`: pausa padrão de seis horas quando o erro indica quota/billing esgotado.
- `GEMINI_RATE_LIMIT_COOLDOWN_SECONDS=60`: pausa padrão para 429 transitório sem indicação de quota permanente.
- `GEMINI_UNAVAILABLE_COOLDOWN_SECONDS=45`: pausa padrão para 5xx/serviço indisponível.
- `GEMINI_CIRCUIT_STATE_FILE=data/gemini_circuit.json`: estado persistente do bloqueio.

A pausa evita chamadas repetidas enquanto a API está recusando solicitações; ela **não aumenta a quota** nem corrige billing. Se o erro disser que a quota atual foi excedida ou pedir para verificar plano/faturamento, consulte o projeto certo em [AI Studio Rate Limits](https://ai.dev/rate-limit) e no painel de faturamento. Depois que você confirmar que a quota foi restaurada, pode remover somente `data/gemini_circuit.json` com o bot parado e reiniciá-lo para liberar a pausa antes do prazo. Não remova `data/colizeu.db`.

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

Nunca envie `.env`, token do Discord, chave Gemini, banco SQLite ou backup com dados de membros para chats públicos. O ZIP de distribuição não contém esses arquivos.
