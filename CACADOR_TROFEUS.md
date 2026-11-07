# Caçador de Troféus — identificação, pesquisa e catálogo

O Caçador mantém um catálogo separado da loja cosmética e salva o progresso de cada jogador. A IA identifica jogos e prepara rascunhos de colecionáveis/troféus, mas **não publica dados automaticamente**.

## Como o jogador pesquisa um jogo

1. Abra `/cacador` ou o botão **Caçador de Troféus** no `/coliseu`.
2. Use **Solicitar cadastro** e escreva o nome como lembrar: título original/traduzido, abreviação ou erro de digitação.
3. O sistema procura primeiro um título/alias já catalogado. Se não encontrar, pesquisa fontes com Tavily Free e usa Gemini principal para analisar os resultados; outro projeto Gemini assume se o primeiro falhar.
4. Se o principal atingir quota, rate limit ou ficar indisponível, o mesmo pedido é tentado pelo segundo projeto Gemini configurado.
5. O jogador confere ano, estúdio, escopo e fontes e confirma o jogo correto. Depois da confirmação começa a pesquisa detalhada do catálogo.
6. O resultado fica em revisão administrativa. Falhas de API, JSON, fonte ou banco não publicam catálogo.

O mapa local de aliases de `God of War (2018)` é apenas um atalho de identificação; não é fonte de troféus e não dispensa pesquisa/revisão.

## Como o administrador revisa e publica

- `/catalogo_admin`: abre o painel administrativo.
- `/catalogo_fila`: mostra solicitações e erros técnicos.
- `/catalogo_auditar slug:<slug>`: mostra itens, troféus, fontes e estado de validação.
- `/catalogo_validar slug:<slug>`: registra revisão humana.
- `/catalogo_publicar slug:<slug>`: publica somente se a auditoria transacional encontrar itens/troféus, fontes HTTPS, pelo menos dois domínios distintos e validação humana.
- `/catalogo_importar arquivo:<arquivo.json>`: importa para revisão; os dados começam não verificados.

O painel de jogadores lista somente jogos em `ready`. A IA não transforma uma solicitação em catálogo público sozinha.

## Configuração Gemini

```dotenv
GEMINI_API_KEY=sua_chave_do_projeto_principal
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_BACKUP_API_KEY=sua_chave_de_outro_projeto_google
GEMINI_BACKUP_MODEL=gemini-3.5-flash-lite
TAVILY_API_KEY=sua_chave_do_plano_free
TAVILY_MAX_QUERIES_PER_JOB=4
```

A Tavily Free faz as consultas web; o Gemini principal analisa os resultados e o outro projeto Gemini assume em caso de quota/rate limit/indisponibilidade. As duas chaves devem pertencer a projetos Google diferentes para que os circuit breakers e as quotas por projeto sejam independentes. Duas chaves do mesmo projeto compartilham quota. Não é necessário ativar billing; sem billing, ao atingir os limites gratuitos o pedido falha de forma controlada.

A busca externa usa somente Tavily Free/Search Basic (1.000 créditos mensais publicados no plano gratuito; até 4 consultas por tarefa neste bot). Os modelos Gemini recebem as fontes como texto e não ativam Google Search grounding. Não vincule faturamento no Google nem habilite Pay-as-you-go/upgrade na Tavily; quando os créditos gratuitos terminarem, a pesquisa pausa sem cobrança.

Referências oficiais:
- https://docs.tavily.com/documentation/api-reference/endpoint/search
- https://tavily.com/pricing
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://ai.google.dev/gemini-api/docs/pricing

## Limitações importantes

- Não existe API única com cobertura completa de colecionáveis e troféus para todos os jogos.
- Se a busca não retornar fontes HTTPS verificáveis, o sistema falha fechado.
- URL mencionada apenas no texto do modelo não é aceita como evidência; os registros precisam usar URLs retornadas pela Tavily nesta pesquisa.
- Títulos, aliases, DLC, NG+, itens perdíveis, locais e requisitos precisam de revisão humana.
- Duas fontes/domínios são um bloqueio mínimo; não provam completude.
- Reimportações preservam o progresso de jogadores. Registros ausentes no novo rascunho não são apagados automaticamente.

## Atualização

Faça backup de `data/colizeu.db` antes de substituir o código. Não substitua o `.env` nem apague o banco. `/gemini_status` exibe os dois circuit breakers de IA.
