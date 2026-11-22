# Auditoria de painéis do SoulsBot — Etapa 1

## Escopo e base analisada

Esta auditoria foi feita sobre o pacote completo `soulsbot-main (3)(1).zip` enviado anteriormente nesta conversa. O pacote tem estrutura de projeto datada de 20/11/2026. Ele serve como base para mapear a arquitetura, mas não comprova sozinho que contém todos os patches incrementais entregues depois (Coliseu, Ateliê e outras atualizações). Antes de alterar a interface em produção, a etapa de implementação deverá partir da cópia completa atualmente instalada no FadeHost ou de uma cópia consolidada equivalente.

## Inventário encontrado

- 139 classes `View`/`Modal` no projeto, distribuídas por diversos módulos.
- 43 declarações de comandos slash no código analisado; há nomes duplicados em módulos e comandos removidos da árvore de comandos por `cog_load`, portanto esse número não equivale ao número de comandos visíveis no Discord.
- `/nara`: 6 categorias principais e 18 ações configuradas, além de 2 atalhos diretos (perfil e santuário) e um seletor de guias.
- `/adm`: 12 categorias administrativas e 43 ações declaradas nas categorias.
- Existe um utilitário compartilhado de navegação (`painel_navegacao.py`) para adicionar botão de retorno, mas a integração não é uniforme em todos os fluxos.

## Achados prioritários — Nara

1. **Caminhos duplicados:** o seletor “Não sabe por onde começar?” repete entradas já existentes na central; a categoria Comunidade também inclui Perfil, Santuário e Ajuda, que já aparecem em outros lugares.
2. **Atalhos distribuídos:** Perfil e Santuário ficam fora da grade principal, enquanto outras áreas ficam dentro de categorias. É uma hierarquia inconsistente.
3. **Ações de manutenção misturadas ao uso normal:** “Remover zerado” aparece como ação separada da biblioteca, quando seria mais intuitivo gerenciar/remover um registro dentro do próprio painel de Zerados.
4. **Retorno inconsistente:** alguns fluxos recebem callback de volta, mas outros chamam diretamente handlers de módulos (por exemplo, memória, santuário, arquivo/minhas contribuições e catálogo). Esses handlers podem abrir outra mensagem ou painel sem restaurar a origem da navegação.
5. **Timeout que apaga a mensagem:** `PainelMembrosView` e `MembrosCategoriaView` tentam apagar a mensagem quando expiram. Isso pode fazer o usuário perder o contexto em vez de receber uma indicação clara de que deve reabrir `/nara`.
6. **Informação inicial repetida:** a descrição de boas-vindas é escrita em mais de um ponto, com versões ligeiramente diferentes. Uma única função de renderização evitaria divergência.
7. **Apresentação das áreas:** a central atual descreve várias funções em texto longo. É possível substituí-lo por um resumo de estado pessoal e ações primárias, deixando guias/contexto dentro de cada área.

## Achados prioritários — ADM

1. **12 categorias na tela inicial:** a quantidade é alta para um menu principal e aumenta a carga de escolha. A proposta é agrupar em 5–6 áreas de trabalho, sem remover nenhuma das 43 ações.
2. **Sobreposição entre rotas:** “Moderação” e “Comunidade → Revisar contribuições pendentes” abrem a mesma ação; “Gerenciador de painéis” convive com atalhos individuais de publicação; “Configurar canais” e “Configuração guiada” têm escopos próximos. A interface pode oferecer uma rota primária e manter atalhos contextuais, em vez de expor caminhos duplicados com o mesmo peso.
3. **Diagnóstico fragmentado:** Dashboard operacional, Histórico de auditoria e Status/configurações estão separados, embora façam parte de uma mesma área de saúde e diagnóstico.
4. **Configuração sem orientação progressiva:** o ADM mostra o estado de valores personalizados/padrão, mas ainda exige que o administrador conheça o objetivo de cada configuração. É possível adicionar recomendações de próximo passo e estado de conclusão sem alterar as regras de configuração.
5. **Acesso e permissões:** há separação entre moderador e administrador; essa lógica deve ser preservada e centralizada para evitar que reorganizar categorias exponha ferramentas administrativas.
6. **Confirmações críticas:** o reset já tem confirmação explícita. A reforma deve preservar e padronizar esse padrão para ações destrutivas ou financeiras.

## Painéis e módulos que entram na auditoria completa

- Nara e navegação principal (`cogs/painel_membros.py`).
- ADM, moderação, diagnóstico, configuração e publicação (`cogs/admin.py`).
- Platinas, Coliseu e biblioteca de conquistas (`cogs/platinas.py`, `cogs/colizeu.py`).
- Zerados e galeria (`cogs/zerados.py`).
- Runs e desafios (`cogs/soulslike.py`).
- Comunidade e contribuições (`cogs/comunidade.py`).
- Ports & Mods (`cogs/catalogo_integrado.py`).
- Santuários (`santuario.py` e `cogs/santuario.py`).
- Loja, perfil, progressão e rankings (`cogs/loja.py`, `cogs/perfil.py`, `cogs/progressao.py`, `cogs/ranking.py`).
- Cargos/verificação, ajuda, notícias, ofertas e YouTube.

## Plano de execução por etapas

### Etapa 1 — Inventário e auditoria (concluída)
Mapear comandos, painéis, subpainéis, ações, permissões, rotas repetidas e pontos sem retorno. Nenhum código funcional é alterado nesta etapa.

### Etapa 2 — Navegação central da Nara
Unificar cabeçalhos/rodapés, garantir Voltar à central e Cancelar, preservar estado ao voltar, revisar timeouts e reduzir duplicações no `/nara`. Manter os dois comandos principais e todas as ações existentes.

### Etapa 3 — Navegação do ADM
Reorganizar as 12 categorias em grupos menores, resolver rotas repetidas, melhorar status e próximos passos, preservando todas as ações e as restrições de acesso.

### Etapa 4 — Subpainéis de membro
Padronizar navegação, paginação, confirmação, erros, estados vazios e retorno nos painéis de jogos, platinas, zerados, runs, comunidade, catálogo, santuário, loja e perfil.

### Etapa 5 — Subpainéis administrativos
Padronizar moderação, configurações, cargos, publicações, catálogos, notícias/ofertas, YouTube, auditoria e diagnóstico.

### Etapa 6 — Testes de regressão e entrega
Conferir cobertura de ações, permissões, callbacks, persistência de views, timeouts, banco e fluxos principais. Entregar patches incrementais e uma matriz “função existente → caminho no novo painel”.

## Regras de segurança da reformulação

- Nenhuma ação será removida para simplificar menus.
- Ações duplicadas podem apontar para uma rota principal única, mantendo atalhos quando forem úteis.
- Permissões serão revalidadas no callback, não apenas escondidas visualmente.
- Não alterar regras de negócio, economia, XP, aprovações ou dados sem necessidade explícita.
- Cada etapa será testada e entregue separadamente antes da próxima.
