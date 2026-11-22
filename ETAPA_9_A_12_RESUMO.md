# Etapas 9 a 12 — UX integrada, consistência e confiabilidade

## Objetivo

Executar em uma rodada integrada melhorias de experiência na central da Nara e no `/adm`, priorizando tarefas frequentes, previsibilidade de navegação e tratamento correto de sessões expiradas. As regras de negócio e os handlers existentes foram preservados.

## Etapa 9 — Central principal da Nara

- Incluídos atalhos diretos para **Meus registros** e **Notificações** na tela inicial.
- Mantidos os acessos existentes a Meu deck, Meu perfil, Santuário e categorias.
- Adicionada orientação curta na tela inicial para explicar o propósito dos atalhos.
- Os atalhos reutilizam `_executar_acao_membro`; não duplicam consultas, regras de permissão ou lógica dos módulos.
- Os cinco botões de acesso direto ocupam uma única linha válida do Discord; o seletor de guia e o botão Fechar continuam em linhas próprias.

## Etapa 10 — Consistência administrativa

- Categorias administrativas temporárias passam a desativar os controles ao expirar e mantêm a mensagem com orientação para reabrir `/adm`.
- O painel recebe referência à mensagem original para que a expiração consiga atualizá-la.
- A checagem de identidade, papel de administrador/moderador e acesso por categoria foi preservada.

## Etapa 11 — Registros, notificações e ferramentas operacionais

- **Meus registros** e **Notificações** agora encerram a sessão de forma explícita: desativam controles e informam como reabrir a central.
- Dashboard operacional e Histórico de auditoria também desativam controles na expiração e preservam a mensagem com instrução de reabertura.
- A atualização do Histórico continua mantendo filtro, termo de pesquisa e página conforme a implementação anterior.

## Etapa 12 — Revisão e regressão

- Criados nove testes de regressão para os novos atalhos, dispatch, proteção por proprietário e expiração de painéis.
- `python -m py_compile cogs/*.py *.py`: aprovado.
- Testes direcionados de UX/navegação/ownership/admin: **51 aprovados**.
- Suíte completa: **258 aprovados, 16 falhas e 2 ignorados**.
- A suíte anterior (etapa 8) tinha 249 aprovados, as mesmas 16 falhas e 2 ignorados. As nove novas verificações passaram e não houve aumento das falhas.

## Limites e pendências da revisão

- As 16 falhas já existiam na etapa 8. Estão relacionadas a expectativas antigas ou divergentes sobre personalidade/relacionamento, comandos slash, catálogo, texto do FAQ, localização do arquivo `.env.example` e integração do dashboard. Não foram alteradas automaticamente porque exigem decisão funcional e revisão de compatibilidade, não simples ajuste para satisfazer testes textuais.
- O teste local não substitui teste de interação real no Discord/FadeHost.
- A revisão desta rodada cobriu diretamente os painéis principais, registros, notificações, dashboard, histórico e suas rotas de acesso. Não declara que todas as 104 classes `View` do projeto foram individualmente testadas em runtime.
- Nenhum banco de dados, `.env` ou credencial foi incluído no pacote.

## Arquivos de código alterados

- `cogs/painel_membros.py`
- `cogs/admin.py`
- `tests/test_stage9_12_integrated_ux.py`

## Instalação

1. Faça backup do código e do banco SQLite atual.
2. Extraia o pacote completo sobre uma cópia de homologação do projeto.
3. Preserve `.env`, variáveis do FadeHost e o banco de produção.
4. Instale dependências conforme `requirements.txt`.
5. Execute a suíte de testes e valide `/nara`, `/adm`, Meus registros, Notificações, Dashboard e Histórico em um servidor de teste.
6. Só depois promova para produção.
