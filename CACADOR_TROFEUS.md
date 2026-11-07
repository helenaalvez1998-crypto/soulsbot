# Caçador de Troféus — identificação, pesquisa e catálogo

O Caçador mantém um catálogo separado da loja cosmética e salva o progresso de cada jogador. A IA ajuda a identificar jogos e preparar rascunhos de colecionáveis/troféus, mas **não publica dados automaticamente**.

## Como o jogador pesquisa um jogo

1. Abra `/cacador` ou o botão **Caçador de Troféus** no `/coliseu`.
2. Use **Solicitar cadastro** e escreva o nome como lembrar: título original/traduzido, abreviação ou erro de digitação.
3. O sistema procura primeiro um título/alias já catalogado. Se não houver correspondência, usa DeepSeek Search + DeepSeek Flash para sugerir até cinco candidatos; se o principal atingir quota/saldo, rate limit ou indisponibilidade, alterna automaticamente para Gemini com Google Search grounding.
4. O jogador confere ano, estúdio, escopo e fontes e confirma o jogo correto. Quando houver ambiguidade, precisa selecionar o candidato.
5. Só depois da confirmação o agente pesquisa o catálogo e cria um rascunho em revisão. Uma falha de API, JSON, fonte ou banco deve deixar o job com erro e não publicar o catálogo.

O mapa local de aliases de `God of War (2018)` é apenas um atalho de identificação. Ele não é fonte de dados de troféus e não dispensa a pesquisa nem a revisão.

## Como o administrador revisa e publica

- `/catalogo_admin`: abre o painel administrativo com os atalhos da fila e a explicação do processo.
- `/catalogo_fila`: mostra os pedidos pendentes e detalhes/erros técnicos.
- `/catalogo_auditar slug:<slug>`: mostra contagem de itens/troféus, evidências, domínios e estado de validação.
- `/catalogo_validar slug:<slug>`: inicia a confirmação de revisão humana. Isso marca os registros como revisados; não é uma garantia automática de que cada requisito esteja correto.
- `/catalogo_publicar slug:<slug>`: publica apenas se a auditoria transacional encontrar itens e troféus, todos os registros ligados a fontes HTTPS cadastradas, no mínimo dois domínios distintos e validação humana.
- `/catalogo_importar arquivo:<arquivo.json>`: importa catálogo manual em estado de revisão; os dados continuam não verificados.

O painel de jogadores lista somente jogos em `ready`. A IA nunca transforma sozinha uma solicitação em catálogo público.

## Configuração de IA

No `.env`:

```dotenv
DEEPSEEK_API_KEY=sua_chave_deepseek
DEEPSEEK_MODEL=deepseek-flash
GEMINI_API_KEY=sua_chave_google
GEMINI_MODEL=gemini-3.8-flash
AI_PRIMARY_PROVIDER=deepseek
```

Configure `DEEPSEEK_API_KEY` (principal) e `GEMINI_API_KEY` (reserva). `DEEPSEEK_MODEL` usa `deepseek-flash`; Search e Chat são chamadas separadas. `GEMINI_MODEL` deve ser um modelo disponível no projeto e compatível com Google Search grounding. O modelo atualmente documentado pelo Google para grounding é compatível com esse fluxo; confira a documentação e preços antes de aumentar o volume:

- https://ai.google.dev/gemini-api/docs/google-search
- https://ai.google.dev/gemini-api/docs/models

O Caçador limita cada usuário a três identificações a cada dez minutos. A pesquisa de catálogo é iniciada somente após confirmação, mas consome pesquisas DeepSeek Search + tokens do modelo; se houver failover, pode usar Google Search grounding e tokens Gemini. Ambos podem gerar cobrança/consumo de quota.

## Limitações importantes

- Não existe uma API única com cobertura completa de colecionáveis e troféus para todos os jogos.
- A pesquisa depende de páginas públicas acessíveis e do grounding devolvido pelo Google. Se o modelo não encontrar fontes, o sistema falha fechado e solicita revisão manual.
- URL citada apenas em texto pelo modelo não é aceita como evidência; cada item/troféu precisa apontar para uma URL devolvida no grounding e cadastrada no catálogo.
- Títulos, aliases, nomes, DLC, NG+, itens perdíveis, locais e requisitos precisam ser conferidos antes da validação administrativa.
- Duas fontes/domínios não provam completude; são um bloqueio mínimo para reduzir dados sem sustentação.
- Reimportações preservam o progresso dos jogadores. Registros antigos que deixaram de aparecer no novo rascunho não são apagados automaticamente, para evitar perda de histórico; compare as versões manualmente.
- O mapa local de títulos conhecidos é intencionalmente pequeno. Para outros jogos, a identificação depende de um provedor configurado (DeepSeek principal ou Gemini reserva) e de fontes de pesquisa.

## Atualização

Faça backup de `data/colizeu.db` antes de substituir o código. Não substitua seu `.env` nem o banco de dados. As tabelas novas e índices são criados/migrados ao iniciar o bot.


Se DeepSeek ou Gemini atingir quota/saldo, rate limit ou indisponibilidade, o roteador tenta automaticamente o outro provedor. Cada API tem circuit breaker e estado persistente independentes. `/gemini_status` mostra os dois estados. Confirme saldo DeepSeek no painel DeepSeek e limites/billing Gemini no Google AI Studio.
