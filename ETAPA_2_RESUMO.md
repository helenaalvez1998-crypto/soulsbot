# Etapa 2 — Central da Nara

## Alterações desta entrega
- A central /nara mantém a prévia visual do deck ao entrar e agora resume quantidade de cartas, custo, poder-base e raridades presentes.
- As telas principais da Nara e os subpainéis montados diretamente por ela têm botão Fechar painel.
- O fechamento encerra apenas a interface efêmera; não remove registros nem cancela ações já salvas.
- O timeout da tela inicial e das categorias não apaga a mensagem: desativa os controles e informa como reabrir `/nara`.
- Retornos à central/categoria preservam a referência da mensagem para o comportamento de timeout.
- O menu principal do Coliseu também oferece Fechar painel.
- O detalhe da carta identifica claramente o retorno como “Voltar à coleção”.
- Nenhuma ação de negócio ou comando foi removido.

## Arquivos alterados
- `cogs/painel_membros.py`
- `cogs/cartas_coliseu.py`
- `tests/test_ux_navigation.py`
- `PLANO_REFORMULACAO_SOULSBOT.md`

## Validação local
- 38 testes direcionados passaram.
- `py_compile` dos módulos alterados passou.
- `compileall` do projeto passou.
- Não foi possível executar interação real no Discord/FadeHost neste ambiente, pois `discord.py` não está instalado.

## Instalação
Extraia o ZIP na raiz do projeto, preservando as pastas. Faça backup antes. Não substitua `.env` nem o banco de produção. A pasta `tests/` e os documentos não são necessários para a execução do bot, mas ficam no pacote para auditoria e regressão.
