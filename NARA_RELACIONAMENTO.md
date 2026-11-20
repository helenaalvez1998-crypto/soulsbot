# Relacionamento adaptativo da NARA

O relacionamento adaptativo mantém **afinidade**, **paciência** e eventos sociais resumidos por membro com memória autorizada. O painel escolhe um perfil para ajuste manual; perguntas de opinião podem consultar qualquer membro mencionado que tenha histórico autorizado. A personalidade original da NARA continua sendo a base. Os indicadores afetam tanto a proximidade e o tom quanto a avaliação social que ela faz da pessoa: confiança, boa vontade, reserva e familiaridade devem refletir o histórico.

## Acesso e privacidade administrativa

Não é necessário editar o `.env` para escolher o membro nem ajustar os indicadores.

- O comando `/nara_relacionamento` tem permissão padrão `administrator` no Discord, portanto membros e moderadores comuns não o veem por padrão.
- O código também exige o **proprietário global do bot** (`BOT_OWNER_ID` ou `bot.is_owner`). Ser administrador ou moderador do servidor não concede acesso aos dados nem aos botões.
- Se um administrador alterar a visibilidade do comando nas configurações do Discord, outras pessoas ainda serão bloqueadas pelo controle interno; nenhuma pontuação ou evento é enviado a elas.
- O painel é efêmero, privado e expira após cinco minutos. Cada clique revalida o proprietário, o servidor e o membro selecionado.

Para usar, o proprietário do bot precisa conseguir invocar comandos de administrador no servidor:

- `/nara_relacionamento usuario:@membro` — escolhe o membro monitorado e abre o painel.
- `/nara_relacionamento` — reabre o painel do membro atualmente selecionado.

No painel, os botões ajustam separadamente **Afinidade +0,5**, **Afinidade −0,5**, **Paciência +0,5** e **Paciência −0,5**. Também há **Atualizar** e **Desativar relacionamento**. Os valores são limitados ao intervalo de 1 a 10.

O painel administrativo exibe e ajusta um membro por vez, mas os perfis individuais são armazenados por `guild_id` e `user_id`. A conversa atualiza o relacionamento do próprio membro que interage com a Nara quando a memória está ativa. Em perguntas de opinião, uma menção explícita identifica o alvo e carrega o perfil dele; sem menção, o membro selecionado no painel é usado como fallback quando a pergunta for claramente uma consulta de opinião.

A desativação apaga a configuração ativa, os indicadores e os eventos relacionais do membro selecionado. Não apaga o histórico de conversa que o próprio membro controla em `/nara_memoria`.

## Consentimento de memória

Configurar uma pessoa **não ativa a memória dela automaticamente**. O membro escolhido deve abrir `/nara_memoria` e selecionar **Ativar memória**. Até essa autorização, a NARA não atualiza indicadores/eventos automaticamente nem injeta o contexto relacional nas conversas. O proprietário pode consultar e ajustar os valores no painel, mas eles só influenciam a personalidade após a autorização do membro.

O membro continua podendo desativar ou apagar sua própria memória em `/nara_memoria`. O painel do membro não mostra pontuações, eventos ou controles do relacionamento; esses dados ficam reservados ao proprietário global do bot.

## Funcionamento

- **Afinidade** representa o vínculo duradouro, a confiança e a consideração conquistadas; muda lentamente e influencia a opinião geral da NARA sobre a pessoa.
- **Paciência** representa a tolerância momentânea e recupera-se mais rápido com o tempo; influencia sobretudo o quanto a NARA está disposta a tolerar naquele momento.
- Afinidade baixa exige reserva real, pouca simpatia e ausência de elogios compensatórios; afinidade alta permite familiaridade e consideração proporcionais ao histórico. A faixa neutra mantém avaliação equilibrada. A nota é traduzida em faixas semânticas determinísticas de 1–2,4, 2,5–3,9, 4–4,9, 5–6,4, 6,5–8,4 e 8,5–10.
- A NARA não deve ser automaticamente boazinha nem automaticamente hostil. Ela avalia atitudes concretas, não discordâncias ou críticas legítimas. Se a afinidade for baixa e não houver eventos concretos, pode demonstrar pouca sintonia ou simpatia sem inventar acusações. O estado relacional é uma orientação interna de comportamento: ela não deve anunciar repetidamente que a relação é distante, neutra ou reservada. Respostas de opinião passam por validador determinístico que bloqueia elogios/afetos compensatórios incompatíveis com a faixa e repetição quase literal; o validador não exige palavras específicas para provar que a NARA está usando a nota. Os indicadores nunca alteram fatos, regras, justiça ou a qualidade da ajuda.
- A avaliação de mensagens é feita localmente em Python; não cria chamada adicional à API.
- A NARA recebe os indicadores na mesma chamada de IA que já seria realizada. Perguntas de opinião não recebem memória, relação social ou respostas recentes de quem perguntou; somente o estado relacional do alvo é anexado.
- Apenas eventos resumidos são registrados; o texto original da provocação não é duplicado no histórico relacional.
- Conversas neutras não geram penalidade. Sinais de sofrimento/pedido de ajuda não são pontuados.
- Eventos relacionais são limitados e expiram após 90 dias.
- Os ajustes manuais são persistidos no SQLite e reiniciam o relógio da recuperação passiva daquele perfil.

## Persistência

A configuração ativa fica em `nara_relacionamento_config`; os perfis individuais ficam em `nara_relacionamento_perfil`; os eventos resumidos ficam em `nara_relacionamento_eventos`. A seleção ativa é carregada do banco ao iniciar o cog, portanto não precisa ser refeita após cada reinicialização.


## Validação final da opinião

Perguntas explícitas de opinião são processadas em uma rota própria. O código resolve o alvo por menção real, nome em cache ou membro selecionado no painel; ignora o histórico e as notas de quem perguntou. Nessas consultas, não injeta respostas recentes do canal, memória do autor, perfil social do autor, FAQ ou manual operacional.

A personalidade de runtime usa uma versão compacta para evitar instruções duplicadas e conflitos com o documento de referência extenso. A faixa relacional deve aparecer naturalmente na atitude, no grau de calor, na intimidade, na paciência e na escolha de palavras; não deve ser narrada em toda resposta. Depois da resposta do Gemini, um validador rejeita elogios ou demonstrações de afeto incompatíveis com afinidade baixa e detecta repetição quase literal. Ele não exige que a NARA diga que a relação é distante, fria ou neutra. Quando a resposta precisa ser substituída, as alternativas de contingência usam construções variadas e coloquiais, sem humilhação ou ataques pessoais. O log registra se a resposta foi aceita ou substituída e o motivo, sem armazenar o texto da conversa.
