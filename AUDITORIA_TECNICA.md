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


### Failover automático DeepSeek ↔ Gemini (revisão atual)

- Adicionado `ia_deepseek.py`: adaptador DeepSeek Flash com chamadas de ferramentas no formato Chat Completions e histórico neutro, sem entrada multimodal.
- Adicionado `ia_multi.py`: roteador conversacional. DeepSeek é principal por padrão; Gemini assume se o principal atingir quota/saldo, rate limit, chave inválida ou indisponibilidade. O provedor que falhou não é reconsultado no mesmo turno; numa nova solicitação volta a ser tentado quando o circuito expirar.
- Adicionado `deepseek_resilience.py`: classifica HTTP 402 (saldo), 429 (rate limit), 401/403 (credencial/permissão) e 5xx/timeout, com circuit breaker e estado persistente independentes de Gemini.
- Adicionado `ia_provedores.py`: Catálogo usa DeepSeek Search + DeepSeek Flash, validando URLs retornadas pelo Search; em erro do Search/modelo ou ausência de fontes, alterna para Gemini + Google Search grounding. Não aceita URLs inventadas pelo modelo.
- Tradução opcional de ofertas também utiliza DeepSeek primeiro e Gemini como reserva; permanece desligada por padrão para economia.
- `/gemini_status` agora apresenta os estados dos dois fornecedores e informa as chaves/modelos configurados sem revelar credenciais.
- O histórico do agente foi normalizado em `MensagemAgente`, permitindo que uma conversa com tool calling mude de provedor sem perder o vínculo entre a chamada da ferramenta e sua resposta. Permissões, argumentos, confirmação e auditoria continuam no núcleo Python.
- Adicionadas variáveis `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL=deepseek-flash`, `DEEPSEEK_BASE_URL`, circuit breakers e `AI_PRIMARY_PROVIDER`. Configure ambas as chaves para failover completo.
- Testes simulam DeepSeek principal, erro 402/429/503, fallback para Gemini, fallback inverso quando Gemini é principal, ausência de fontes, persistência dos circuit breakers e correlação de IDs em tool calls.

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

- `python -m compileall -q .`: compilou todos os arquivos Python sem erros nesta versão.
- `pytest -q`: **128 testes passaram** nesta rodada, incluindo roteamento local, separação de pesquisas de catálogo, política de quota, filtros de pesquisa e proteção de imagens. `python -m unittest discover -s tests -q`: **21 testes passaram**.
- Varredura AST: sem erros de sintaxe ou métodos duplicados em classes/módulos.
- Auditoria de comandos: **37 comandos** com nomes explícitos, sem duplicatas e dentro do limite de 32 caracteres.
- Testes SQLite simulam falha no crédito de XP e confirmam rollback da aprovação da run.
- Testes do catálogo simulam falha de inserção e rejeição de publicação sem evidências/validação suficientes.

## O que não foi possível validar aqui

Este ambiente não tem as dependências de runtime do bot (`discord.py`, `aiosqlite`, `google-genai`) instaladas e não contém token Discord nem chaves Gemini e DeepSeek. Portanto, **não foi possível iniciar o bot em um servidor real, fazer chamadas reais ao Discord/Gemini, validar intents/permissões de um servidor, confirmar o formato de respostas da API em produção nem medir latência/custos reais**. Os testes de SQLite usam SQLite real por um adaptador de teste; não substituem um teste de integração com `aiosqlite`.

## Checklist de implantação

1. Fazer backup do SQLite atual.
2. Substituir os arquivos de código/documentação sem sobrescrever `.env` e `data/`.
3. Instalar dependências de `requirements.txt` em ambiente virtual limpo.
4. Configurar `DISCORD_TOKEN`, `DEEPSEEK_API_KEY` e `GEMINI_API_KEY`. Para failover completo, as duas chaves precisam pertencer a projetos ativos e com saldo/quota. `DEEPSEEK_MODEL=deepseek-flash` e `GEMINI_MODEL` podem ficar nos padrões documentados.
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


## Economia de quota e bloqueio de imagens da Nara

- Adicionado `nara_local.py`: classifica saudações, identidade, ajuda, comandos, regras do servidor, XP, patentes, Denários, loja, registros, comprovantes, rankings e consultas frequentes sem modelo ou rede.
- Perfil, saldo privado, platinas, zerados, runs, inventário e rankings são lidos diretamente do SQLite. Consultas locais não incrementam o contador de uso Gemini.
- `decidir_rota` permite testar a decisão: mensagens básicas vão para resposta local; bate-papo no canal livre que não é dirigido à Nara é ignorado; pesquisa de jogo precisa ser explícita; mensagem de pesquisa em canal livre pede menção; apenas pesquisa explícita e marcada pode ir à rota multi-provedor DeepSeek/Gemini, se o chat estiver habilitado.
- A Nara não baixa nem interpreta imagens. `ia_nucleo.rodar_agente` e `GeminiAdaptador.conteudo_usuario` agora aceitam apenas texto; não existe envio de `Part.from_bytes` pelo caminho conversacional.
- Anexos de imagem são identificados apenas por MIME/nome do arquivo, sem chamar `read`, `save` ou acessar URL. Os formulários especializados de comprovante continuam independentes e não enviam as imagens à Nara.
- Adicionados testes de conversas simuladas, pesquisa intencional, conversa no canal livre, print vazio, texto acompanhado de print e fallback sem chamada externa. A política de economia também é testada: pesquisa conversacional não passa ao Gemini sem opt-in explícito.
- As chaves dos provedores deixaram de ser necessárias para a Nara responder perguntas básicas. Para failover completo nas pesquisas do Caçador, configure `DEEPSEEK_API_KEY` e `GEMINI_API_KEY`; com apenas uma chave, o sistema usa somente esse fornecedor.

Limitação mantida: os testes de roteamento/funções puras não substituem homologação com `discord.py`, `aiosqlite`, token Discord e chaves Gemini e DeepSeek reais.


## Revisão adicional: economia máxima e pesquisa segura (rodada atual)

- Expandida a FAQ local para cumprimentos, identidade, ajuda/comandos, privacidade, XP, recompensas, Denários, patentes, loja, Coliseu, Santuário, YouTube, ofertas, registros, comprovantes e consultas SQLite.
- Consultas pessoais usam somente o ID de quem falou; saldo/inventário não são incluídos em respostas de outros membros. Rankings são públicos.
- Pesquisa conversacional Gemini desativada por padrão (`NARA_CHAT_IA_ENABLED=false`); só pode ser habilitada manualmente. Se ativada, o limite é três pesquisas por usuário/dia (`IA_LIMITE_DIARIO=3`). O comando `/jogo_buscar` mantém o limitador persistente próprio (3 identificações por 10 minutos por usuário).
- Perguntas sobre troféus/platinas/DLCs/colecionáveis de qualquer jogo são roteadas para `/jogo_buscar`; o chat não chama uma fonte de Elden Ring para tentar responder outro jogo. Se o catálogo já existir, a consulta fica local e não chama o Gemini.
- Pesquisa conversacional por chat passou a ser desligada por padrão, inclusive para Elden Ring. Assim, com `OFFERS_SHOW_DESCRIPTION=false`, a rota conversacional multi-provedor não é inicializada e as quotas ficam reservadas ao `/jogo_buscar` quando necessário, com DeepSeek principal e Gemini como reserva.
- Prompt específico de pesquisa fica em `prompts/nara_pesquisa.md`; recebe apenas o texto digitado e não recebe histórico, perfil, saldo, inventário, menções a terceiros, imagens ou anexos.
- `ia_nucleo.py` e `ia_gemini.py` mantêm interface somente textual. A ferramenta de leitura de páginas valida `Content-Type` e rejeita imagens, PDFs, vídeo e binários antes de ler o corpo da resposta.
- Prints em conversa são detectados por metadados do anexo (MIME/extensão) sem download, leitura ou OCR. Formulários de comprovante continuam separados e servem à revisão humana, não à IA.
- Removidos do roteamento da Nara os prompts/contextos grandes e funções antigas que não eram usados; reduzido o prompt de pesquisa para baixar tokens nas poucas chamadas externas.


## Failover DeepSeek/Gemini — testes de integração simulada

- DeepSeek é o principal do pipeline de pesquisa de catálogos; Gemini é a reserva via Google Search grounding. A conversa avançada da Nara, se habilitada, usa o mesmo roteador e pode inverter a ordem com `AI_PRIMARY_PROVIDER`.
- Os circuit breakers são independentes e persistidos. DeepSeek classifica saldo insuficiente (HTTP 402), rate limit (429), erros de autenticação/configuração e indisponibilidade. Gemini classifica os erros de quota/rate limit/serviço com o adaptador já existente.
- Quando o provedor principal falha no meio de uma sequência de tool calls, o histórico neutro preserva a chamada e a resposta da ferramenta para que a reserva continue a tarefa sem repetir a ação.
- Última execução: `compileall` sem erros; `pytest -q`: **128 aprovados**; `unittest`: **21 aprovados**. Estes são testes automatizados/simulados, não chamadas reais às APIs.
- Para failover efetivo entre serviços, configure ambas as chaves. Com ambas indisponíveis, respostas locais/SQLite permanecem ativas e pesquisas externas falham de forma segura.
