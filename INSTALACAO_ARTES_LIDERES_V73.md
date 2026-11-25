# Instalação — Narabot V73

1. Faça backup da pasta atual do bot e do banco SQLite persistente.
2. Substitua os arquivos pelo conteúdo deste pacote, preservando os segredos e variáveis de ambiente já configurados.
3. Reinicie o bot.
4. A tabela `cartas_gwent_lideres_artes` será criada automaticamente pelo schema no início do banco. Não execute SQL manual nem apague o banco.
5. Entre no site com uma conta autorizada no Ateliê e abra a aba **Ateliê**.
6. Em **Ferramentas administrativas do Ateliê → Aplicar arte nas cartas de líder**, selecione um dos nove líderes, escolha a imagem e clique em **Aplicar arte ao líder**.

## Requisitos da imagem
- PNG, JPG ou WEBP estático.
- Pelo menos 512 × 512 pixels; máximo de 8 MB e 18 megapixels.
- A imagem é recortada/ajustada e normalizada para 1200 × 960 pixels (5:4 horizontal).
- O crédito do artista é opcional.

A arte fica armazenada no banco e passa a aparecer para todos os jogadores no preview da carta de comando do construtor de deck. Para voltar ao retrato original, selecione o mesmo líder e clique em **Restaurar arte padrão**.

Os endpoints de alteração são exclusivos dos administradores já autorizados pelo Ateliê (`COLISEUM_ART_REVIEWER_IDS`, proprietário do bot e criador configurado). Não é necessário conceder permissão adicional a usuários comuns.
