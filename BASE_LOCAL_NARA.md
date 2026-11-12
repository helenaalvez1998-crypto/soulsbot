# Base local de respostas da NARA

## Arquivos
- `dados/nara_faq.json`: perguntas reconhecidas, respostas finais e marcação de conteúdo exclusivo da equipe.
- `faq_base.py`: normalização, reconhecimento de perguntas e entrega das respostas.
- `nara_local.py`: regras locais, roteamento e respostas de contingência.
- `nara_help_panel.py`: Central de Ajuda e índice de comandos do Discord.

## Conteúdo atual
- 134 intenções cadastradas.
- 1.546 exemplos de perguntas e variações.
- 118 respostas prontas revisadas para o membro.
- 16 consultas dinâmicas que usam informações atuais do servidor.
- 30 itens marcados como `staff_only`, ocultos da Central de Ajuda dos jogadores.

## Padrão editorial das respostas
As respostas são escritas para quem está usando o servidor, não para quem mantém o código:
1. Começar pela resposta ou ação que resolve a dúvida.
2. Explicar somente o que o membro precisa fazer ou saber.
3. Usar nomes de comandos e botões que aparecem no Discord.
4. Evitar variáveis de ambiente, nomes de APIs, SQLite, Gemini, handlers, cache e detalhes internos.
5. Preservar números, prazos, limites e avisos que mudam a decisão do membro.
6. Usar a personalidade da NARA — debochada, sarcástica e carismática — em pequenas doses. A piada nunca pode esconder a instrução.
7. Em privacidade, recompensas, aprovação e ações irreversíveis, priorizar clareza em vez de humor.

## Conteúdo exclusivo da equipe
Itens com `staff_only: true` não aparecem na `/central_ajuda` dos membros. Eles continuam na base para que a NARA possa responder dúvidas diretas com uma orientação curta, sem expor configurações internas. O índice `/comandos` mantém suas seções administrativas identificadas como MOD/ADMIN.

## Reconhecimento
1. Normaliza maiúsculas, acentos, pontuação e URLs.
2. Prioriza correspondência exata com exemplos cadastrados.
3. Para paráfrases, calcula similaridade lexical por cobertura de termos, Jaccard e similaridade de sequência.
4. Exige confiança mínima e margem sobre a segunda intenção; perguntas ambíguas não são adivinhadas.
5. Se não reconhecer uma FAQ, o roteador geral decide se a mensagem é uma conversa social ou assunto permitido da comunidade.

O classificador é determinístico e local. Não usa Gemini, embeddings, APIs ou bibliotecas externas. Para melhorar uma intenção, acrescente frases reais em `examples` e rode `pytest -q`.

## Como adicionar uma resposta
Edite a intenção correspondente em `dados/nara_faq.json`. Use `answer` para uma mensagem final completa. Use `handler` para consultas que dependem de dados atuais, permissões ou estado do servidor. Marque `staff_only: true` para conteúdo operacional que não deve aparecer na Central de Ajuda dos membros.

**Não coloque prompts de IA nesse arquivo.** O campo `answer` é o texto final que a NARA envia ao membro.
