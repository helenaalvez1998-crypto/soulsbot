# Configuração da IA da Nara

## Conversa normal (Gemini)
- `NARA_CONVERSA_ENABLED=true`: habilita conversa generativa.
- `GEMINI_API_KEY`: chave do projeto Gemini principal (necessária pelo menos uma chave).
- `GEMINI_BACKUP_API_KEY`: projeto Gemini de reserva.
- `GEMINI_THIRD_API_KEY`: terceiro projeto Gemini.
- `GEMINI_MODEL`, `GEMINI_BACKUP_MODEL`, `GEMINI_THIRD_MODEL`: modelos por projeto.
- O failover do roteador é Gemini principal -> reserva -> terceiro.

## Pesquisa web no chat
- `NARA_CHAT_IA_ENABLED=true`: habilita a rota de pesquisa factual com ferramentas.
- `TAVILY_API_KEY`: necessária para a pesquisa web. Sem ela, mantenha `NARA_CHAT_IA_ENABLED=false`.
- O configurador deixa a pesquisa ligada somente quando uma chave Tavily é informada.
- `IA_LIMITE_DIARIO`: teto diário de pesquisas avançadas por usuário.

## Canais e limites da conversa
- `IA_CANAIS_LIVRES`: IDs separados por vírgula dos canais em que a Nara pode responder perguntas locais reconhecidas sem menção; não inicia conversa Gemini.
- Menção real `@Nara` (ou resposta direta a ela): usa IA na conversa; quando existe resposta local/SQLite, ela é passada como contexto factual para o modelo.
- Nome “Nara” escrito sem menção real: usa somente FAQ/SQLite/fallback local, sem Gemini.
- Sem menção nem chamada pelo nome: não inicia conversa livre com IA; em canal configurado, apenas perguntas locais reconhecidas podem receber resposta.
- `NARA_CONVERSA_LIMITE_USUARIO`: limite diário por pessoa (0 = ilimitado).
- `NARA_CONVERSA_LIMITE_GLOBAL`: limite diário global (0 = ilimitado).
- `NARA_CONVERSA_COOLDOWN`: intervalo em segundos entre respostas da mesma pessoa.
- `NARA_CONVERSA_MAX_TOKENS`: limite de tokens por resposta.

## Importante
- `NARA_CHAT_IA_ENABLED` NÃO liga nem desliga a conversa normal; isso é feito por `NARA_CONVERSA_ENABLED`.
- O projeto usa até três configurações Gemini no roteador da Nara.
- A conversa normal exige pelo menos uma chave Gemini válida.
- A pesquisa web exige também uma chave Tavily válida.
- Não compartilhe `DISCORD_TOKEN`, chaves Gemini ou `TAVILY_API_KEY`.


## NARA AI 2.0 — memória e imagens
- O botão **Memória da Nara** dentro de `/nara` permite ao próprio membro ativar, desativar, consultar ou apagar sua memória.
- A memória é **opt-in**: começa desativada para cada membro e servidor.
- Quando ativada, guarda até 12 mensagens textuais recentes por membro/servidor, com expiração de 30 dias.
- Imagens/anexos não são armazenados no SQLite. Imagens PNG/JPEG/WEBP/GIF podem ser analisadas em conversa marcada, até 2 arquivos e 5 MiB por arquivo (8 MiB no total).
- Prints usados como comprovantes de platina/run nunca são aprovados pela IA; devem ser enviados pelos formulários de **Coliseu** dentro de `/nara`.
- O canal de conversa livre da Nara pode ser escolhido no `/adm` → **Canais** → **Canal de conversa livre da Nara**. Essa configuração é por servidor.
