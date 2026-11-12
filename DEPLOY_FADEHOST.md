# Implantação do NARA na FadeHost

Este guia considera o repositório com `bot.py`, `requirements.txt` e `config.py` na raiz.

## 1. Antes do primeiro deploy

1. Faça backup do banco SQLite atual e da pasta `data/`.
2. Envie o conteúdo da pasta `NARA/` para a raiz de um repositório GitHub (público ou privado).
3. Confira que `.env`, bancos SQLite, logs e arquivos locais não foram versionados. O `.gitignore` já os exclui; `.env.example` contém apenas nomes e valores de exemplo.
4. No Discord Developer Portal, habilite **Message Content Intent**, **Server Members Intent** e **Guild Voice States**. O projeto usa os três intents.
5. Convide o bot com os escopos `bot` e `applications.commands`, concedendo apenas as permissões necessárias aos módulos ativados. Para a configuração completa, normalmente são necessários Ver canais, Enviar mensagens, Ler histórico, Inserir links, Anexar arquivos, Gerenciar mensagens, Gerenciar cargos e gerenciar/criar tópicos conforme os painéis usados. Mantenha o cargo do bot acima dos cargos que ele atribui.

## 2. Criar o bot na FadeHost

1. Abra **Bots → Host a bot** e selecione Discord.
2. Escolha **Your own repository** e informe a URL do GitHub.
3. Deixe a linguagem como **Auto-detect** (o `requirements.txt` identifica Python).
4. Em **Build & start**, escolha Python **3.13** e configure o comando de inicialização:

   ```bash
   python bot.py
   ```

5. Cole o token no campo próprio **Discord bot token** (a FadeHost o injeta como `DISCORD_TOKEN`).
6. Cadastre as demais variáveis na área **Environment variables**. Não coloque chaves no GitHub nem em mensagens de Discord.
7. Faça Deploy e acompanhe o console até aparecer `NARA conectado`.

## 3. Variáveis essenciais

Cadastre apenas os valores dos recursos que serão usados. IDs do Discord são números, sem `<#...>` ou menções.

```dotenv
GUILD_ID=ID_DO_SERVIDOR
MOD_CHANNEL_ID=ID_DO_CANAL_DE_APROVACAO
MOD_ROLE_ID=ID_DO_CARGO_DE_MODERACAO
PLATINAS_CHANNEL_ID=ID_DO_CANAL_DE_PLATINAS
SOULSLIKE_CHANNEL_ID=ID_DO_CANAL_DE_RUNS
COLIZEU_CHANNEL_ID=ID_DO_CANAL_DO_COLISEU
PERFIS_CHANNEL_ID=ID_DO_CANAL_DE_SANTUARIOS
ZERADOS_CHANNEL_ID=ID_DO_CANAL_DE_ZERADOS
CREATOR_VIDEO_CHANNEL_ID=ID_DO_CANAL_DE_VIDEOS
CREATOR_LIVE_CHANNEL_ID=ID_DO_CANAL_DE_LIVES
GAMES_CHANNEL_ID=ID_DO_CANAL_DE_JOGOS
PROMOS_CHANNEL_ID=ID_DO_CANAL_DE_OFERTAS
DATA_DIR=/data
DB_PATH=/data/colizeu.db
# Opcional: deixe os circuit breakers sem override; eles herdam DATA_DIR.
LOG_LEVEL=INFO
CLEAR_GLOBAL_COMMANDS_ON_GUILD_SYNC=false
```

Para IA e pesquisa, cadastre opcionalmente `GEMINI_API_KEY`, `GEMINI_BACKUP_API_KEY`, `GEMINI_THIRD_API_KEY` e `TAVILY_API_KEY`. Cada chave deve vir do painel do respectivo fornecedor. O sistema local do bot continua funcionando sem essas chaves, mas as funções que dependem desses provedores ficam desativadas ou limitadas.

Consulte `.env.example` para os demais controles de economia, limites, horários e integrações.

## 4. Persistência e backups

- **Obrigatório na FadeHost:** sobrescreva `DATA_DIR=/data` e `DB_PATH=/data/colizeu.db`. Os arquivos dos circuit breakers herdam `DATA_DIR` por padrão. Esse volume é destinado aos dados que precisam sobreviver a novos deploys.
- Nunca guarde o banco em `./data` no contêiner de código: diretórios do repositório podem ser substituídos durante deploys.
- Faça backup periódico de `/data/colizeu.db`, `/data/sent_offers.sqlite3` e dos JSONs de estado (`gemini_circuit.json`, `gemini_backup_circuit.json`, `gemini_third_circuit.json` e `tavily_circuit.json`). Antes de atualizar código que altera esquema, pare o bot e faça backup.
- Não rode duas instâncias do NARA apontando para o mesmo SQLite ao mesmo tempo. O banco local é apropriado para uma única instância; para escalar horizontalmente, migre primeiro para um banco servidor.

## 5. Comandos antigos e sincronização

- Com `GUILD_ID` preenchido, os comandos são sincronizados no servidor indicado e ficam disponíveis mais rapidamente.
- `CLEAR_GLOBAL_COMMANDS_ON_GUILD_SYNC=false` é o padrão seguro. A opção `true` apaga o conjunto de comandos globais do bot durante a sincronização; isso afeta todos os servidores em que ele está instalado. Só habilite deliberadamente para limpar registros globais antigos e volte para `false` depois.
- Sem `GUILD_ID`, a sincronização é global e a publicação dos comandos pode demorar.

## 6. Operação e diagnóstico

O processo grava logs no console da FadeHost. Procure por:

- `SQLite conectado`: banco aberto;
- `Extensão carregada`: módulo/cog ativo;
- `Comandos sincronizados`: sincronização concluída;
- `NARA conectado`: Gateway conectado;
- `extensões falharam`: inicialização parcial que exige correção.

Não configure servidor HTTP nem `keep_alive` para manter o bot ligado. A hospedagem de bots mantém o processo ativo; endpoints HTTP são opcionais e não são necessários para o Gateway do Discord.

O plano gratuito anunciado pela FadeHost tem 256 MB de RAM. Este projeto agrega diversos cogs, SQLite, Pillow e integrações de IA; monitore o uso após o primeiro deploy. Se houver encerramentos por memória, reduza módulos não usados ou aumente a memória do bot antes de atribuir o problema ao Discord.

CONFIGURAÇÃO VISUAL PELO DISCORD
1. Convide o bot com permissões de Gerenciar Canais, Gerenciar Cargos, Ver Canais, Enviar Mensagens, Incorporar Links, Anexar Arquivos e Ler Histórico.
2. Execute /adm no servidor.
3. Clique em “Configuração Automática” para criar a categoria e os canais oficiais do NARA.
4. Em /adm > Cargos, selecione o cargo da equipe de moderação. O bot concederá acesso desse cargo à Central privada de Aprovação.
5. Use /adm > Canais para trocar individualmente qualquer destino. As escolhas ficam salvas por servidor no SQLite.

A configuração automática não cria cargos, não publica mensagens de teste e não altera/apaga canais existentes. Chaves externas (Discord, Gemini, YouTube, Tavily etc.) continuam precisando ser fornecidas pelo administrador no ambiente seguro da hospedagem.
