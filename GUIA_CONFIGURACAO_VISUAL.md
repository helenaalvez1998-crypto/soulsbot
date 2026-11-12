# Configuração visual do NARA pelo Discord

O painel `/adm` é o centro de configuração por servidor. As alterações são salvas no SQLite e não exigem editar `.env` para escolher canais.

## Instalação inicial em um clique

1. Convide o bot com as permissões **Gerenciar Canais**, **Ver Canais**, **Enviar Mensagens**, **Incorporar Links**, **Anexar Arquivos**, **Ler Histórico de Mensagens** e **Gerenciar Cargos** (para atribuir permissões aos cargos).
2. Execute `/adm` como administrador.
3. Clique em **Configuração Automática**.
4. O bot cria a categoria `SOULSBOT • CANAIS OFICIAIS`, cria os canais que faltarem e salva cada destino no servidor atual.
5. Em `/adm` > **Cargos**, escolha o cargo da equipe. O painel concede a esse cargo acesso à Central privada de Aprovação.

A configuração automática não apaga, renomeia ou move canais existentes. Se o processo for interrompido, execute novamente: canais já criados dentro da categoria serão reutilizados.

## Canais gerados e finalidade

| Canal | Finalidade |
|---|---|
| `central-aprovacoes` | Fila privada de platinas, runs e jogos zerados aguardando equipe |
| `anuncios-platinas` | Publicações de platinas aprovadas |
| `anuncios-zerados` | Publicações de jogos zerados aprovados |
| `runs-soulslike` | Runs e recordes Soulslike aprovados |
| `santuario-perfis` | Threads e perfis dos membros |
| `youtube-videos` | Avisos de novos vídeos |
| `youtube-lives` | Avisos de transmissões ao vivo |
| `jogos-gratis` | Jogos gratuitos encontrados |
| `promocoes` | Promoções e descontos de jogos |
| `painel-colizeu` | Painel principal e rankings do Colizeu |

## Escolher ou trocar canais individualmente

1. Execute `/adm`.
2. Abra **Canais**.
3. Selecione **Configurar** na finalidade desejada.
4. Escolha o canal no seletor nativo do Discord.
5. O bot salva imediatamente a escolha para aquele servidor.

Também há atalhos por sistema em **Coliseu**, **Galeria** e **Jogos**. As escolhas são independentes por servidor, permitindo que uma instalação do bot atenda várias comunidades com canais diferentes.

## Segurança da Central de Aprovação

A `central-aprovacoes` é privada por padrão: `@everyone` não consegue visualizá-la. Administradores continuam com acesso pelo privilégio de administrador do Discord. Ao escolher o cargo em `/adm` > **Cargos** > **Cargo de moderador**, o bot concede acesso a esse cargo. Se o cargo ou o canal for trocado depois, o painel tenta atualizar as permissões correspondentes.

Não conceda o cargo de moderador a membros que não devam ver comprovantes e solicitações privadas.

## O que ainda exige credenciais externas

A criação de canais e a gravação dos destinos são automáticas. O administrador ainda precisa cadastrar, no ambiente seguro da FadeHost, as credenciais que só ele pode emitir ou controlar: `DISCORD_TOKEN`, chave Gemini, chave YouTube e chave Tavily (se usar pesquisa web). O painel não pede nem exibe tokens secretos.

## Nara AI 2.0
- A configuração automática cria também `#nara-conversa` e vincula esse canal à Nara no servidor.
- O administrador pode trocar o destino em `/adm` → **Canais** → **Canal de conversa livre da Nara**.
- Cada membro controla sua própria memória pelo painel privado de botões aberto em `/nara_memoria`.
