# Revisão completa da base de respostas da NARA

## Escopo revisado

A base `dados/nara_faq.json` contém 125 intenções:

- **108 respostas estáticas** (`answer`): todas foram reescritas nesta revisão. A comparação com a versão textual anterior confirma que as 108 respostas preenchidas foram alteradas.
- **17 respostas dinâmicas** (`handler`): permanecem sem texto estático no JSON por desenho. O conteúdo é montado em tempo real pelo código a partir de configurações do servidor, consultas ao banco, comandos disponíveis e dados do membro. Os textos desses caminhos também foram revisados.

As respostas restritas (`staff_only`) continuam marcadas como restritas. Os exemplos de perguntas, palavras-chave, categorias, fontes verificadas, identificadores de intenção e parâmetros de correspondência foram preservados.

## Critérios editoriais

1. A NARA se comunica por texto no Discord. Ela lê mensagens e responde por mensagens; não possui fala, voz ou envio de áudio.
2. A personalidade aparece na escolha das palavras, na autoconfiança, na ironia contextual e em comentários teatrais pontuais.
3. O sarcasmo não é aplicado mecanicamente. Dúvidas legítimas recebem instruções claras; privacidade, permissões, falhas técnicas e moderação mantêm tom objetivo.
4. Nenhum texto deve prometer uma ação que dependa de ferramenta, permissão, confirmação ou aprovação ainda não concluída.
5. Comandos, nomes de painéis, requisitos, valores, prazos, limites, condições de aprovação e regras foram mantidos conforme a base e as implementações citadas em `verified_sources`.

## Caminhos dinâmicos também revisados

Os handlers cobertos incluem XP, Denários, recompensas configuráveis, saldo, perfil, platinas, jogos zerados, runs, inventário, rankings, ajuda, canais visíveis, cargos, sistemas ativos e tutorial de transmissão no Discord.

Os dados variáveis continuam sendo obtidos pelo fluxo original. A revisão alterou a redação, não as consultas SQL, os critérios de classificação, as permissões, a lógica de confirmação ou as fórmulas de economia.

## Arquivos alterados

- `dados/nara_faq.json` — reescrita das 108 respostas fixas e atualização da descrição da base.
- `cogs/nara_ia.py` — redação das respostas dinâmicas e mensagens locais relacionadas.
- `nara_estilo_textual.py` — aberturas contextuais das consultas pessoais e rankings.
- `nara_conhecimento.py` — texto de ajuda, canais e sistemas ativos.
- `nara_local.py` — fallback textual.
- `tests/test_nara_estilo_textual.py` — expectativas atualizadas para a nova redação.
- `tests/test_faq_personalidade.py` — verificações de cobertura, textualidade e preservação de dados operacionais.

## Validação

- JSON válido: aprovado.
- Compilação Python: aprovada.
- Suíte automatizada: **143 testes aprovados**.
- Intenções: 125.
- Respostas estáticas reescritas: 108 de 108.
- Caminhos dinâmicos: 17 de 17 mantidos e revisados.

A revisão não altera a lógica de negócio do bot. Os testes automatizados não substituem uma validação manual em um servidor Discord real, especialmente para permissões e integrações externas.
