# Revisão da base de respostas locais da NARA

## Escopo desta revisão

A base `dados/nara_faq.json` contém 125 intenções:

- **108 respostas estáticas** (`answer`): revisadas para refletir a personalidade da NARA no Discord e incorporar abreviações brasileiras naturais. 106 textos foram modificados nesta rodada; 2 já estavam alinhados ao padrão.
- **17 respostas dinâmicas** (`handler`): continuam sendo montadas pelos handlers do código, com dados do servidor e do usuário. Esta revisão preserva seus identificadores e fluxos; a redação dinâmica deve ser validada em execução no Discord.

## Critérios editoriais

1. Abreviações como `vc`, `tb`, `pra`, `tá`, `dps`, `agr`, `msm`, `mto`, `qnd` e `msg` aparecem com moderação, sem transformar cada frase em uma sequência de siglas.
2. A personalidade é confiante, espontânea e levemente provocadora quando o contexto permite.
3. Privacidade, moderação, segurança, falhas e instruções técnicas mantêm clareza e objetividade.
4. Comandos, nomes de painéis, requisitos, valores, prazos, limites e condições de aprovação foram preservados.
5. A NARA responde por texto no Discord; não deve afirmar que ouviu áudio ou analisou imagens que não consegue processar.

## Arquivos atualizados

- `dados/nara_faq.json` — revisão das respostas estáticas.
- `prompts/nara_conversa.md` — reforço das regras de conversa e do tratamento de prints como não oficiais.

Os módulos de roteamento e os handlers dinâmicos foram mantidos para não alterar a lógica de negócio nesta rodada.

## Validação

- JSON da FAQ: válido.
- Compilação Python (`compileall`): aprovada.
- Testes focados de FAQ, base, estilo textual, conversa e conhecimento: **61 aprovados**.
- Suíte completa: **149 aprovados, 2 ignorados e 4 falhas preexistentes/fora do escopo textual**, relacionadas a mapeamento de comandos, ausência de `.env.example` e uma expectativa de teste de prompt. Essas falhas precisam ser corrigidas separadamente antes de considerar a suíte integralmente verde.

A revisão textual não altera consultas SQL, permissões, critérios de classificação, recompensas ou confirmações. Ainda é necessária validação manual no servidor Discord/Fatehost.


## Segunda passada de personalidade

As respostas estáticas receberam uma camada adicional de voz contextual, inspirada no perfil canônico da NARA: provocação inteligente, teatralidade em jogos, competitividade e primeira pessoa quando natural. Mensagens sensíveis e operacionais permanecem objetivas. Foram acrescentadas falas específicas por intenção, evitando um bordão único repetido.
