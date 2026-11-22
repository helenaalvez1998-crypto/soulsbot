# SoulsBot — Etapa 3: reformulação do painel `/adm`

## Objetivo
Reorganizar a entrada administrativa e os caminhos de navegação sem remover handlers ou comandos existentes.

## Alterações
- Organização do painel em oito categorias: Servidor e acesso; Moderação e auditoria; Jogos, Coliseu e runs; Comunidade e contribuições; Economia e progressão; Publicações e integrações; Catálogos de Ports & Mods; Diagnóstico e NARA IA.
- Atalho por seletor para fila de aprovação, resumo operacional, auditoria, configuração de canais, gerenciador de painéis e diagnóstico.
- Ações de publicação no canal atual foram mantidas separadas do gerenciador que permite escolher outro canal. Isso evita esconder os caminhos originais que têm comportamentos diferentes.
- Indicadores iniciais de configuração e solicitações pendentes, com tratamento de falha para que um indicador indisponível não impeça a abertura do painel.
- Ajuste de autorização para que Administrador, dono do servidor, quem possui Gerenciar Servidor, proprietário global do bot e moderadores (nas áreas permitidas) tenham acesso coerente com seus níveis.
- Retorno à categoria preservado em dashboard, histórico, telas de configuração e confirmação de restauração.
- Correção do retorno de categoria para calcular corretamente o nível de acesso do usuário, sem depender de variável inexistente.
- O gerenciador de publicação agora aceita também administradores com permissão Gerenciar Servidor.

## Compatibilidade
- Os IDs de ações administrativas existentes foram preservados nas categorias.
- Os handlers de negócio continuam sendo chamados; o painel reorganiza o acesso, não reimplementa os comandos.
- Nenhuma migração de banco de dados é necessária para esta etapa.
- Não contém `.env`, tokens, credenciais ou banco de produção.

## Validação executada
Comandos:
- `python -m py_compile cogs/admin.py tests/test_admin_panel_ux.py`
- `python -m pytest -q tests/test_admin_panel_ux.py tests/test_admin_config_mapping.py tests/test_ux_navigation.py`

Resultado: **25 testes aprovados**.

## Pendência identificada fora do escopo desta etapa
O teste amplo `tests/test_cobertura_comandos.py` ainda aponta duas pendências do painel de membros: o comando `publicar_luatools` não está mapeado em um botão e a ação `zerados` não aparece em `MEMBROS_CATEGORIAS`. O arquivo `cogs/painel_membros.py` não foi alterado nesta etapa; essas pendências devem ser tratadas na etapa de subpainéis dos membros.

## Instalação
1. Faça backup do projeto e do banco de dados.
2. Extraia o ZIP na raiz do projeto, preservando as pastas.
3. Reinicie o bot.
4. Teste `/adm` com uma conta Administrador/Gerenciar Servidor e com uma conta de moderador para confirmar os níveis de acesso.

O ambiente de edição não tinha as dependências de runtime do Discord instaladas; portanto, não foi possível executar uma sessão real de interação no Discord/FadeHost.
