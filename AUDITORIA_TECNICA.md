# Auditoria técnica — Nara / Soulsbot

## Escopo revisado

Revisão estática e testes de serviços para inicialização, configuração, SQLite, economia, progressão, platinas, runs Soulslike, agente de IA, ferramentas, fontes externas, pesquisa de jogos, importação/publicação de catálogos, ofertas e cogs do Discord.

## Correções aplicadas

### Banco e integridade

- Liga `PRAGMA foreign_keys=ON` e define `busy_timeout` em conexões SQLite; usa WAL para banco persistente.
- Adiciona transações `BEGIN IMMEDIATE` em fluxos que precisam ser indivisíveis.
- Protege compras, equipagem, recompensas, aprovação de platinas, registros de jogos zerados e aprovação de runs contra cliques concorrentes e crédito duplicado.
- Aprovação de run, XP base e bônus por recorde agora são uma única transação. Se o crédito falhar, a aprovação também sofre rollback.
- Importação de catálogo é validada e transacional. Falha de uma inserção não deixa jogo ou parte do catálogo persistidos; requisito que aponta para item inexistente/ambíguo rejeita o lote em vez de criar vínculo quebrado silenciosamente.
- Publicação revalida evidências e validação humana dentro da transação que muda o jogo para `ready`.
- Alias conflitante não pode resolver para jogo arbitrário; índice único global evita aliases duplicados.

### Pesquisa e IA

- Identificação não aceita candidato sem retorno de fontes de Google Search grounding, exceto correspondências locais curadas e explícitas.
- O título digitado pelo membro não é usado automaticamente como título canônico.
- Dados gerados começam como não verificados; URLs precisam estar presentes no grounding e cada item/troféu precisa apontar a uma fonte cadastrada.
- Limite persistente de três identificações por pessoa em dez minutos.
- Tempo limite de rede, execução do SDK fora do event loop e fechamento explícito de clientes Gemini.
- Novo módulo `gemini_resilience.py`: classifica `429` de quota/billing versus rate limit transitório e `5xx`, aplica circuit breaker compartilhado entre Nara, Caçador e tradução de ofertas, respeita `retryDelay` quando disponível e persiste o bloqueio em `data/gemini_circuit.json`.
- Não duplica a política de retries do SDK oficial. Depois que o SDK esgota as tentativas transitórias, o bot abre o circuit breaker; em quota/billing, não insiste em chamadas inúteis.
- Novo comando administrativo `/gemini_status` para consultar o bloqueio local sem expor chave ou credenciais.
- A leitura de páginas externas exige HTTPS, domínio permitido, redirecionamento ainda em domínio permitido e limite de tamanho; cache com limite de 256 páginas.
- Ação do agente continua sujeita a validação em código e confirmação do usuário; permissões de moderação são revalidadas no fluxo de confirmação.

### Discord, callbacks e recuperação

- Corrigida duplicidade de `cog_load` no Caçador, que fazia uma definição sobrescrever a outra.
- Jobs de pesquisa marcados como `researching` só são considerados interrompidos se estiverem parados há mais de cinco minutos, evitando falso positivo em recarga rápida de extensão. A fila administrativa também reconcilia jobs abandonados após esse prazo.
- Operações após `defer` que podiam falhar antes de responder foram incluídas em tratamento de erro.
- Falhas em logs, notificações, atualização de patente e publicação secundária não devem desfazer nem mascarar uma compra, platina ou run já confirmada no banco.
- Rejeição de run revalida a permissão de moderador no envio do modal e impede que o próprio jogador modere sua run. Solicitações de comprovante por DM expiram em dez minutos e não bloqueiam indefinidamente novos registros.
- Arquivos de comprovante têm limites de tamanho/quantidade, conversão protegida e limpeza compensatória para reduzir mensagens órfãs e registros incompletos.
- Configurações numéricas inválidas deixam de derrubar a importação do bot; o código usa padrão seguro e registra aviso.

### Higiene do projeto

- Corrigido `.gitignore` que estava com nome de arquivo incorreto.
- Removidos arquivos residuais de um byte e caches de execução/teste.
- Documentação do Caçador atualizada para refletir a pesquisa automática e seus controles reais.

## Testes executados nesta revisão

- `python -m compileall -q .`: compilou os **40 arquivos Python** sem erros.
- `pytest -q`: **48 testes passaram**, incluindo os oito novos cenários de resiliência Gemini.
- `python -m unittest discover -s tests -q`: **21 testes passaram**.
- Varredura AST: sem erros de sintaxe ou métodos duplicados em classes/módulos.
- Auditoria de comandos: **37 comandos** com nomes explícitos, sem duplicatas e dentro do limite de 32 caracteres.
- Testes SQLite simulam falha no crédito de XP e confirmam rollback da aprovação da run.
- Testes do catálogo simulam falha de inserção e rejeição de publicação sem evidências/validação suficientes.

## O que não foi possível validar aqui

Este ambiente não tem as dependências de runtime do bot (`discord.py`, `aiosqlite`, `google-genai`) instaladas e não contém token Discord nem chave Gemini. Portanto, **não foi possível iniciar o bot em um servidor real, fazer chamadas reais ao Discord/Gemini, validar intents/permissões de um servidor, confirmar o formato de respostas da API em produção nem medir latência/custos reais**. Os testes de SQLite usam SQLite real por um adaptador de teste; não substituem um teste de integração com `aiosqlite`.

## Checklist de implantação

1. Fazer backup do SQLite atual.
2. Substituir os arquivos de código/documentação sem sobrescrever `.env` e `data/`.
3. Instalar dependências de `requirements.txt` em ambiente virtual limpo.
4. Configurar `DISCORD_TOKEN` e, para funções de IA, `GEMINI_API_KEY`. `GEMINI_MODEL` pode ficar no padrão documentado.
5. Conferir intents **Message Content**, **Server Members** e **Voice States**, permissões de canais e hierarquia de cargos.
6. Iniciar e conferir os logs do processo e o `/status_ofertas`.
7. Testar `/jogo_buscar god of war 2018`, confirmar o candidato e abrir `/catalogo_admin` e `/catalogo_fila`.
8. Validar primeiro um único catálogo pequeno; abrir todas as fontes, conferir DLC/requisitos e só então usar `/catalogo_validar` e `/catalogo_publicar`.

## Riscos que continuam exigindo operação responsável

- IA de pesquisa não garante completude nem precisão semântica. Revisão humana das fontes continua obrigatória.
- O Google Search grounding e o modelo podem mudar; acompanhe os avisos e a documentação do provedor.
- O SQLite atende bem a um bot de porte pequeno/médio em um único processo. Para múltiplos processos concorrentes, alta taxa de escrita ou alta disponibilidade, migrar para PostgreSQL é a evolução correta.
- O sistema ainda não tem migração de catálogo versionada/arquivamento de itens obsoletos. Reimportar preserva registros e progresso existente; mudanças de escopo precisam de revisão administrativa.
- Backups do banco devem ser feitos com o bot parado ou usando a API de backup do SQLite; copiar apenas o arquivo principal enquanto WAL está ativo pode não incluir as transações mais recentes.

### Testes adicionais da correção Gemini 429

- Testes unitários simulam `429 RESOURCE_EXHAUSTED` com quota/billing, rate limit transitório com `retryDelay`, `503`, bloqueio de chamadas subsequentes, persistência do bloqueio, preservação de erros locais e concorrência entre chamadas.
- A Nara, o Caçador de Troféus e a tradução das ofertas compartilham o mesmo circuit breaker. Uma falha de quota em uma função impede as outras de continuar gastando chamadas até o fim da pausa.
- O SDK oficial já aplica retries para falhas temporárias; o bot não adiciona uma segunda sequência automática de retries. Depois que o SDK devolve a falha final, o circuito pausa novas chamadas.
- A classificação usa os detalhes/mensagem do erro final. Um `429` isolado não identifica a quota específica; o diagnóstico definitivo continua no painel de quota/billing e de Search grounding do Google.
