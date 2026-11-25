# V26 — Receitas de Linhagem

## Implementado
- Catálogo de três receitas determinísticas, com ingredientes por modelo e raridade, resultado definido e custo de Fragmentos.
- Tríade do Eclipse: três unidades Épicas temáticas da Lua Negra/Véu Carmin produz a unidade Lendária Apóstolo da Pele Divina.
- Juramento da Árvore Áurea: três exemplares temáticos de Crisol/forja/Leyndell produzem a Sentinela do Portão de Leyndell.
- Rito da Lâmina Negra: três exemplares ligados à morte produzem Maliketh, a Lâmina Negra.
- Listagem personalizada por jogador com quantidade de ingredientes disponíveis e IDs dos exemplares.
- Execução transacional: valida receita, propriedade, ingredientes, IDs distintos, deck ativo e saldo de Fragmentos.
- Resultado recebe poder mínimo da raridade; poder dos sacrificados não é transferido.
- Histórico gravado em `cartas_convergencias` e `cartas_movimentacoes`.
- Página `/linhagens` no site com seleção de exemplares, prévia/confirmação e execução autenticada.
- Link para as Receitas de Linhagem no painel `/jogo` do Discord.

## Regras preservadas
- Três exemplares distintos por receita.
- Nenhum exemplar equipado no deck ativo pode ser sacrificado.
- Cartas especiais não são ingredientes nem resultados.
- Primordiais e Singulares não participam destas receitas.
- Nenhum poder dos sacrificados é transferido; o resultado nasce no piso de sua raridade.
- A operação consome Fragmentos e é irreversível após confirmação.

## Validação executada
- `py_compile` dos arquivos Python alterados: aprovado.
- Testes de catálogo das receitas: incluídos nesta versão.
- Testes anteriores de gameplay/distribuição: executados separadamente.
- Não foi realizado teste visual no Discord nem teste contra banco de produção. A dependência `aiosqlite` não está instalada neste ambiente, então a execução transacional foi revisada estaticamente, mas não executada em banco local.
