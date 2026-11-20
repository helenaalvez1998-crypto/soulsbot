# Relacionamento adaptativo da NARA

O relacionamento adaptativo mantém **afinidade**, **paciência** e eventos sociais resumidos para a pessoa escolhida no painel. A personalidade original da NARA continua sendo a base. Os indicadores afetam tanto a proximidade e o tom quanto a avaliação social que ela faz da pessoa: confiança, boa vontade, reserva e familiaridade devem refletir o histórico.

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

O servidor acompanha um membro por vez. Para administrar outro membro, o proprietário executa `/nara_relacionamento usuario:@outro_membro`. O perfil e os eventos do membro anterior ficam preservados no SQLite e deixam de ser atualizados enquanto ele não estiver selecionado. Ao selecioná-lo novamente, os valores anteriores voltam a ser usados.

A desativação apaga a configuração ativa, os indicadores e os eventos relacionais do membro selecionado. Não apaga o histórico de conversa que o próprio membro controla em `/nara_memoria`.

## Consentimento de memória

Configurar uma pessoa **não ativa a memória dela automaticamente**. O membro escolhido deve abrir `/nara_memoria` e selecionar **Ativar memória**. Até essa autorização, a NARA não atualiza indicadores/eventos automaticamente nem injeta o contexto relacional nas conversas. O proprietário pode consultar e ajustar os valores no painel, mas eles só influenciam a personalidade após a autorização do membro.

O membro continua podendo desativar ou apagar sua própria memória em `/nara_memoria`. O painel do membro não mostra pontuações, eventos ou controles do relacionamento; esses dados ficam reservados ao proprietário global do bot.

## Funcionamento

- **Afinidade** representa o vínculo duradouro, a confiança e a consideração conquistadas; muda lentamente e influencia a opinião geral da NARA sobre a pessoa.
- **Paciência** representa a tolerância momentânea e recupera-se mais rápido com o tempo; influencia sobretudo o quanto a NARA está disposta a tolerar naquele momento.
- Afinidade baixa exige reserva e ausência de simpatia presumida; afinidade alta permite familiaridade e consideração proporcionais ao histórico. A faixa neutra mantém avaliação equilibrada.
- A NARA não deve ser automaticamente boazinha nem automaticamente hostil. Ela avalia atitudes concretas, não discordâncias ou críticas legítimas. Os indicadores nunca alteram fatos, regras, justiça ou a qualidade da ajuda.
- A avaliação de mensagens é feita localmente em Python; não cria chamada adicional à API.
- A NARA recebe os indicadores na mesma chamada de IA que já seria realizada.
- Apenas eventos resumidos são registrados; o texto original da provocação não é duplicado no histórico relacional.
- Conversas neutras não geram penalidade. Sinais de sofrimento/pedido de ajuda não são pontuados.
- Eventos relacionais são limitados e expiram após 90 dias.
- Os ajustes manuais são persistidos no SQLite e reiniciam o relógio da recuperação passiva daquele perfil.

## Persistência

A configuração ativa fica em `nara_relacionamento_config`; os perfis individuais ficam em `nara_relacionamento_perfil`; os eventos resumidos ficam em `nara_relacionamento_eventos`. A seleção ativa é carregada do banco ao iniciar o cog, portanto não precisa ser refeita após cada reinicialização.
