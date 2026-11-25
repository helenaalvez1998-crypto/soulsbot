# Instalação — Prompts de arte V69

1. Faça backup da pasta atual do Narabot.
2. Substitua o projeto pela pasta `narabot_v52_work` deste pacote, ou aplique os arquivos atualizados preservando as configurações locais:
   - `sistemas/atelie_coliseu.py`
   - `sistemas/prompt_arte_criador.py`
3. Reinicie o processo do bot/servidor para recarregar os módulos Python.
4. Abra o Ateliê ou a área de criação de cartas e solicite um prompt novo. Prompts já copiados anteriormente não são atualizados retroativamente.
5. Gere a nova ilustração usando o prompt retornado e envie/substitua a arte pelo fluxo normal do site.

Não é necessário executar migração SQL. O pacote mantém as demais funcionalidades e os dados do jogo da versão V68.

## Validação desta atualização

Os módulos Python foram compilados com `py_compile`. Os testes específicos dos prompts e do Ateliê passaram. A suíte global contém uma falha em um teste de auditoria de efeitos especiais (`test_efeitos_especiais_sem_texto_ficam_explicitos`), fora dos dois geradores de prompt; por isso, não foi declarado que toda a suíte esteja verde.
