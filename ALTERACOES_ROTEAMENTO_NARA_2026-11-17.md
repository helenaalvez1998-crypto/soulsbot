# Alterações de roteamento da NARA — 17/11/2026

## Regra de interação

- Menção real `@Nara` (ou resposta direta a uma mensagem da Nara): direciona a mensagem à IA. Quando uma intenção local/SQLite é reconhecida, o resultado do código é enviado como contexto factual para o modelo, que formula a resposta. O modelo não deve alterar valores nem estados.
- Nome `Nara` digitado no texto, sem menção real: usa somente respostas locais, incluindo FAQ, consultas SQLite, FAQ comunitária aprovada e fallback. Não chama Gemini.
- Sem menção nem chamada pelo nome: não inicia conversa generativa. Em `IA_CANAIS_LIVRES`, perguntas locais reconhecidas continuam podendo receber resposta local.
- Pedidos de ação e pesquisas com ferramentas mantêm suas rotas e proteções existentes.

## Correção do erro do log

Removido o `import config` local dentro de `_responder_local`. O módulo `config` já é importado no escopo global; o import interno fazia o Python tratar `config` como variável local e provocava `UnboundLocalError` na leitura de `config.SOULS_USER_ID`.

## Arquivos alterados

- `cogs/nara_ia.py`
- `nara_local.py`
- `nara_social.py`
- `tests/test_conversa.py`
- `README.md`
- `CONFIGURACAO_IA_NARA.md`
- `MAPA_FUNCIONAL_NARA.md`
- `INSTALACAO.md`
- `prompts/nara_manual.md`
- `GUIA_CONTRIBUICOES_INTERACOES_NARA.md`

## Validação

- `py_compile`: aprovado para os módulos e testes alterados.
- Testes direcionados (`test_conversa.py` + `test_faq_base.py`): 50 aprovados.
- Suite completa: 157 aprovados, 5 falhas e 2 ignorados. As mesmas 5 falhas ocorrem no ZIP de referência anterior, sem estas mudanças; nenhuma falha nova foi introduzida por este patch.
