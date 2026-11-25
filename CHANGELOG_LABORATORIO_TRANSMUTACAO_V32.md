# V32 — Arte Original de Cartas Pessoais

## Implementado
- Módulo `sistemas/arte_cartas_geradas.py`.
- Renderização procedural individual com o motor Pillow já existente no projeto.
- Identidade visual derivada de ID, nome, facção, raridade, afinidades, função e fileira.
- Moldura e ornamentos respeitam a raridade usando o renderer atual.
- PNG original gerado localmente, sem depender de imagens externas ou serviços remotos.
- Persistência em `DATA_DIR/cartas_geradas/{owner_id}/{card_id}.png`.
- Gravação temporária, validação, SHA-256 e publicação atômica sem sobrescrita.
- Verificação de integridade por hash e formato PNG.
- Método de banco `coliseu_registrar_arte_carta_gerada`, condicionado ao proprietário, para registrar hash, dimensões e caminho.
- O estado da carta não é publicado automaticamente; a arte fica marcada como validada.

## Natureza da arte
A arte desta versão é ilustração procedural original produzida por formas, camadas, cenário e composição do renderer local. Não é pintura generativa por modelo de imagem nem ilustração manual. A arquitetura permite substituir o fornecedor visual no futuro sem alterar a identidade persistente da carta.

## Segurança
- IDs são validados antes de formar caminhos.
- Caminho é isolado por proprietário.
- Arquivo já existente para o mesmo ID não pode ser substituído por conteúdo diferente.
- PNG é validado antes e depois da gravação.
- O registro no banco exige `owner_id` e `card_id` correspondentes.

## Não implementado
- Integração com API/UX do Laboratório.
- Publicação automática da carta.
- Revisão visual humana ou classificação semântica da arte.
- Geração por serviço externo de imagens.
- Teste transacional com `aiosqlite`/banco de produção.
