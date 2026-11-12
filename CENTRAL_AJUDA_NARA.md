# Base local auditada e ampliada da Nara

A base de conhecimento fica em `dados/nara_faq.json`.

- Cada entrada possui `intent`, `title`, `category`, `examples`, `keywords` e `answer` ou `handler`.
- `answer` é uma resposta final fixa, sem chamada de IA.
- `handler` chama um fluxo local que consulta SQLite ou runtime (por exemplo, saldo, perfil, inventário, rankings ou comandos).
- `examples` contém mais de 1.500 maneiras naturais diferentes de perguntar a mesma coisa. Acrescente frases completas, sinônimos, gírias, abreviações e variações de ordem.
- `verified_sources.files` informa quais módulos foram usados para conferir a resposta.
- Não crie afirmações de recurso só porque existe um arquivo isolado: confirme que o módulo está carregado e integrado ao fluxo.

## Como ampliar com segurança

1. Primeiro encontre a implementação no cog/serviço/banco e confirme validações, limites, permissões e efeitos.
2. Escreva a resposta com o limite correto: diga quando algo depende da configuração do servidor ou de permissão.
3. Adicione pelo menos 5–10 formulações naturais por pergunta.
4. Evite frases curtas ambíguas; uma palavra isolada como “platina” pode apontar para várias intenções.
5. Rode `python -m unittest discover -s tests -v`.
6. Verifique que cada exemplo aponta para a intenção esperada e que perguntas desconhecidas continuam sem classificação.

A Central `/central_ajuda` inclui perguntas sobre os sistemas do bot, respostas fixas e 16 tipos de consultas dinâmicas. As categorias seguem a jornada de uso (jogos/conquistas e progressão primeiro; configuração, integrações e IA depois). Dentro de cada categoria, as perguntas são ordenadas pelo título. As dinâmicas usam o mesmo handler local da conversa e não devem ser convertidas em respostas fixas, pois podem conter dados privados ou configurações por servidor.

O comando `/comandos` é um índice separado, privado e interativo, com nove áreas. Ele agrupa os comandos por tarefa e mostra a sequência recomendada de execução. Os nomes e permissões existentes foram mantidos para não quebrar comandos já utilizados. A lista nativa de slash commands é ordenada pelo Discord; o índice do NARA fornece a navegação por categoria.


## Estado da versão auditada
- 134 intenções.
- 1.546 formulações de perguntas.
- 118 respostas estáticas.
- 16 handlers dinâmicos.
- 12 categorias de FAQ no painel; nenhuma ultrapassa 25 opções, limite do seletor do Discord.
- 9 áreas no índice `/comandos`, cobrindo os 43 comandos e subcomandos registrados no pacote.
- O corpus é pré-processado e armazenado em cache no processo. Depois de editar `dados/nara_faq.json`, reinicie o bot para recarregar a base.
