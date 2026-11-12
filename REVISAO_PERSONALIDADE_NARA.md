# Revisão de personalidade e comunicação — NARA v5

## Objetivo editorial

Aplicar a identidade definida para a NARA às interações em que a assistente fala com os membros, sem transformar toda a interface em uma sequência de piadas. A personalidade é contextual: provocadora em conversas leves, teatral em situações de jogo, precisa em suporte técnico e estritamente factual em moderação, privacidade e falhas.

## Superfícies revisadas

Foi feita uma varredura estática dos módulos Python e dos pontos de envio/edição de mensagens, respostas e embeds dos Cogs. O inventário encontrou aproximadamente 697 chamadas relevantes distribuídas por 20 Cogs. A revisão editorial concentrou as alterações nos textos que representam a voz da NARA, sem reescrever automaticamente rótulos ou dados apresentados pela aplicação.

Módulos e superfícies com alterações nesta rodada:

- `prompts/nara_personalidade_runtime.md`, `prompts/nara_conversa.md` e `prompts/nara_pesquisa.md`: identidade canônica, seis modos adaptativos, leitura social, limites de humor e regras de veracidade.
- `nara_local.py` e `cogs/nara_ia.py`: fallback local, falas determinísticas, respostas de consultas e enquadramento textual de saldo, perfil, platinas, zerados, runs, inventário e ranking.
- `nara_voz.py`: camada determinística pequena para introduções contextuais. Ela preserva integralmente o corpo da resposta e não altera valores, permissões ou estado.
- `nara_conhecimento.py`, `nara_help_panel.py` e `cogs/painel_membros.py`: ajuda, apresentação dos sistemas, instruções de navegação e central do membro.
- `cogs/admin.py`, `cogs/cargos.py` e `cogs/transmissoes.py`: textos introdutórios de administração, moderação e configuração.
- `cogs/platinas.py`, `cogs/zerados.py`, `cogs/soulslike.py`, `cogs/santuario.py`, `cogs/loja.py`, `cogs/catalogo_integrado.py`, `cogs/perfil.py`, `cogs/progressao.py`, `cogs/ranking.py` e `cogs/colizeu.py`: descrições de painéis, consultas, rankings e notificações de progresso.
- `cogs/youtube.py`, `cogs/game_news.py`, `cogs/ofertas.py` e `cogs/painel_rotativo.py`: avisos e textos associados às integrações e aos painéis públicos.

## Decisões de consistência

- Novatos recebem cordialidade e ironia discreta; membros conhecidos podem receber humor moderado; vínculos próximos permitem provocações afetuosas. Familiaridade não é presumida.
- O humor não aparece automaticamente em cada resposta. A informação, o estado real do sistema e o próximo passo vêm primeiro.
- Moderação, permissões, privacidade, falhas de integração e validações mantêm linguagem objetiva. Isso é intencional, não uma falha de personalidade.
- Botões, opções, placeholders, nomes de comandos, valores, preços, recompensas, datas, estados e instruções operacionais continuam claros e não são alterados para criar efeito cômico.
- A NARA não promete uma ação antes de o fluxo confirmar sucesso e não afirma disponibilidade de funcionalidades com base apenas em sugestões.

## Personalização por membro e privacidade

A estrutura social já existente foi preservada. O perfil social é separado por servidor e membro e só é lido/atualizado quando a memória pessoal está ativa por opção do próprio usuário. A relação influencia a escolha de tom, não permissões, recompensas, regras ou acesso a dados. A exclusão da memória continua removendo também o perfil social associado. Nenhum mecanismo paralelo de memória foi criado nesta revisão.

## Integridade funcional

As alterações são editoriais. Não foram intencionalmente modificados comandos, condições de autorização, valores de economia, fórmulas de XP, regras de aprovação, persistência, prazos ou destinos de notificações. O helper `nara_voz.enquadrar()` apenas acrescenta uma abertura curta a respostas locais selecionadas e preserva o texto e os valores originais.

## Verificações executadas

- `python -m compileall -q .`
- `pytest -q`
- Testes específicos da camada de voz em `tests/test_nara_voz.py`.
- Verificação do tamanho de `conv.carregar_prompt()`: 5.948 caracteres, abaixo do limite de 6.000 definido pelo projeto.

As mensagens de interface que devem ser neutras foram mantidas assim deliberadamente. O objetivo é uma NARA reconhecível e consistente, não uma interface que prejudica a leitura ou transforma toda validação em sarcasmo.
