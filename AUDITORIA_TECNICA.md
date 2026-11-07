# Auditoria técnica — Soulsbot (versão com dois projetos Gemini e pesquisa gratuita)

## Escopo

Revisão estática e testes automatizados de inicialização, configuração, SQLite, economia, progressão, platinas, runs Soulslike, agente, permissões, pesquisa de jogos, importação/publicação de catálogos, ofertas e cogs Discord.

## Arquitetura atual de IA (dois projetos Gemini + busca gratuita)

- O bot usa dois projetos Gemini: `GEMINI_API_KEY` é o principal e `GEMINI_BACKUP_API_KEY` é a reserva. Cada projeto tem modelo, circuit breaker e arquivo de estado próprios.
- As quotas Google são aplicadas por projeto, não por chave. Duas chaves do mesmo projeto compartilham a mesma quota; projetos diferentes permitem isolamento de estado/quota, mas não garantem franquias iguais nem autorizam contornar regras do fornecedor.
- O mecanismo de pesquisa web do Caçador é Tavily Free/Search Basic. O código limita a quantidade de consultas por tarefa, valida URLs HTTPS e armazena somente os resultados necessários.
- Os dois Gemini recebem texto e evidências recuperadas pela Tavily. O código não ativa Google Search grounding para o modelo `gemini-3.5-flash-lite`.
- O bot não habilita billing, não compra créditos e não ativa Pay-as-you-go/upgrade. A administração deve manter os projetos Google sem faturamento vinculado e a Tavily no plano gratuito. Quando a franquia gratuita de pesquisa terminar, o circuito Tavily pausa até a renovação; nenhuma cobrança ou upgrade é acionado.
- A busca e os modelos têm quotas distintas. Se Tavily acabar, dois projetos Gemini não conseguem substituir a busca web; a pesquisa é interrompida com segurança. Se Tavily estiver disponível e o Gemini principal falhar, o Gemini reserva analisa as mesmas fontes sem repetir as consultas.
- Dados recuperados de páginas são tratados como entrada não confiável. O modelo é instruído a ignorar comandos presentes nas páginas, não inventar dados/URLs e usar exclusivamente URLs recebidas.
- A publicação do catálogo exige revisão/auditoria humana; resultados começam não verificados e URLs não retornadas pelo mecanismo de busca são rejeitadas.
- `NARA_CHAT_IA_ENABLED=false` mantém conversas básicas locais/SQLite. Imagens e prints não são baixados, lidos, submetidos a OCR ou enviados à IA.

## Integridade de dados e economia

- SQLite com foreign keys, `busy_timeout` e WAL para banco persistente.
- Transações `BEGIN IMMEDIATE` em operações que precisam ser indivisíveis.
- Proteções contra compras, equipagem, recompensas e aprovações duplicadas em cliques/ações concorrentes.
- Aprovação de run e concessão de XP/bônus na mesma transação.
- Importação de catálogo atômica e publicação revalidada dentro da transação.
- Consultas de perfil, saldo, platinas, zerados, runs, inventário e ranking atendidas por SQLite sem consumo de quota Gemini.
- Respostas locais para saudações, ajuda, identidade, regras, comandos, perguntas frequentes e sistemas do bot.

## Failover e tratamento de erros

- Circuit breakers independentes para Gemini principal, Gemini reserva e Tavily Free.
- Gemini principal é chamado primeiro; em quota, rate limit, credencial/permissão inválida ou indisponibilidade, o segundo projeto recebe o mesmo prompt e evidências.
- Se o primeiro Gemini falhar após uma ferramenta já ter sido executada no fluxo conversacional, o histórico neutro preserva a chamada e o resultado para que a reserva continue sem repetir a ação.
- Erros de quota Tavily (HTTP 432/433 ou mensagens de créditos esgotados) pausam a pesquisa até o próximo mês UTC; HTTP 429 usa pausa temporária; erros de autenticação não são repetidos continuamente.
- `/gemini_status` mostra os estados locais dos dois circuit breakers Gemini e da Tavily. Estado liberado não garante que a quota real do fornecedor esteja disponível.
- Se os serviços de pesquisa/modelo estiverem indisponíveis, nenhuma publicação parcial acontece; recursos locais continuam disponíveis.

## Outras correções incluídas

- Corrigida duplicidade de `cog_load` no Caçador, evitando sobrescrita do hook de recuperação de pesquisas interrompidas.
- Operações após `defer` tratadas para reduzir interações Discord sem resposta.
- Falhas em notificações/logs secundários não mascaram compras, platinas ou runs já confirmadas.
- Arquivos de comprovante têm limites de tamanho/quantidade, conversão protegida e limpeza compensatória.
- Leitura de páginas exige HTTPS, valida Content-Type e rejeita imagens, PDFs, vídeo e binários.
- Configurações numéricas inválidas usam padrão seguro em vez de derrubar a importação dos cogs.

## Configuração necessária

```dotenv
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_BACKUP_API_KEY=...
GEMINI_BACKUP_MODEL=gemini-3.5-flash-lite
TAVILY_API_KEY=...
TAVILY_MAX_QUERIES_PER_JOB=4
NARA_CHAT_IA_ENABLED=false
OFFERS_SHOW_DESCRIPTION=false
```

Não vincule faturamento às contas Google nem habilite Pay-as-you-go na Tavily se a exigência for custo zero. Verifique os painéis de uso antes de executar pesquisas em volume.

## Limitações de validação

- Última suíte: `pytest -q` **129 aprovados**; `unittest discover` **21 aprovados**; compilação dos **48 arquivos Python** sem erros de sintaxe; 37 decorators de comandos nomeados sem nomes duplicados.

- Os testes deste pacote são automatizados e simulam erros/alternância; não são homologação com tokens/contas reais.
- Este ambiente não dispõe das chaves Google, chave Tavily, token Discord ou dependências de produção para executar uma pesquisa real.
- Cobertura de colecionáveis/troféus varia por jogo, edição, plataforma e DLC. A revisão humana das fontes continua obrigatória.
- A Tavily Free tem limite mensal; depois de consumido, a pesquisa web fica pausada até renovação. Gemini backup não substitui o mecanismo de busca.
- Duas chaves Gemini do mesmo projeto não fornecem uma quota reserva separada.

## Correção adicional — componentes Discord UI (07/11/2026)

- Corrigida colisão com `discord.ui.Item.parent`, propriedade interna gerenciada pelo `discord.py` e sem setter público.
- Os componentes customizados do Caçador de Troféus agora guardam a referência à view em `self.owner_view`, sem sobrescrever `self.parent`.
- A correção abrange seletores e botões de categorias, itens, troféus e confirmação de pesquisa de jogos.
- Adicionado teste AST de regressão para impedir atribuições futuras a `self.parent` em `cogs/trofeus.py`.
- Validação após correção: 132 testes `pytest` aprovados; compilação Python executada separadamente.
