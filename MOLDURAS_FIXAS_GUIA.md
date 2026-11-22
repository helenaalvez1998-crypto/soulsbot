# Molduras fixas das cartas — instalação e uso

## O que muda

O renderizador passa a aceitar uma camada PNG independente para cada raridade: Comum, Rara, Épica, Lendária e Primordial. Quando existe um PNG personalizado, ele substitui a moldura vetorial antiga. O bot continua desenhando a ilustração, nome, raridade, tipo, poder, custo e habilidade; esses elementos não são substituídos pelo upload.

## Instalação

Substitua os arquivos do pacote mantendo exatamente as pastas:

- `cogs/admin.py`
- `cogs/cartas_coliseu.py`
- `sistemas/arte_cartas.py`
- `sistemas/cartas.py`
- `prompts/MOLDURAS_FIXAS_CARTAS.md`

Reinicie o bot para carregar a nova opção do painel administrativo.

## Enviar uma borda pelo Discord

1. Abra `/adm`.
2. Entre em **Jogos, Coliseu e runs**.
3. Clique em **Molduras fixas das cartas**.
4. Clique no botão da raridade que deseja configurar.
5. A Nara enviará uma DM privada. Responda anexando um único PNG.
6. O bot valida formato, canal alfa, proporção, resolução e transparência do centro. Se aceitar, salva o arquivo e devolve uma prévia da carta.
7. Use **Atualizar status** no painel para conferir quais raridades estão personalizadas.

O painel também oferece um seletor para restaurar a moldura original do bot para uma raridade específica.

## Requisitos do arquivo

- PNG com transparência real (RGBA/canal alfa), não um quadriculado desenhado.
- Canvas recomendado: **840 × 1240 px**. Mínimo aceito: 420 × 620 px.
- Proporção 420:620.
- Até 8 MB e 20 milhões de pixels.
- Somente a moldura deve ter pixels visíveis. O centro precisa ser transparente.

Os cinco prompts completos e específicos de cada raridade estão em `prompts/MOLDURAS_FIXAS_CARTAS.md`.

## Persistência e cache

Os PNGs são salvos em `DATA_DIR/cartas_molduras/` (na FadeHost, normalmente dentro do volume persistente `/data`). Não coloque as molduras em diretórios temporários do processo. A assinatura do arquivo entra na chave do cache, então substituir uma borda invalida as próximas renderizações em cache.

As cartas antigas que já foram enviadas como anexos no Discord não são editadas retroativamente. As próximas renderizações e novos envios usam a borda atualizada.

## Permissão

Como as cinco molduras são globais e afetam todas as cartas do bot, a alteração é restrita ao proprietário global (`BOT_OWNER_ID`, `SOULS_USER_ID` ou proprietário da aplicação). Administradores comuns do servidor não conseguem substituir esses arquivos.
