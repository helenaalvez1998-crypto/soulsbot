# Caçador de Troféus — primeira etapa

Esta versão adiciona a fundação do sistema ao Soulsbot:

- Botão **Caçador de Troféus** no painel existente do Coliseu.
- Comando `/cacador` como atalho.
- Catálogo separado do inventário cosmético da loja.
- Progresso individual por usuário.
- Navegação por jogo, categoria, itens e troféus.
- Nomes exibidos como `Nome em português (Original em inglês)`.
- Solicitação de jogos ausentes pelo próprio jogador, diretamente no Discord.\n- Fila administrativa para acompanhar solicitações.\n- Importação administrativa de catálogos JSON para revisão.
- Publicação administrativa após validação básica.

## Comandos administrativos

- `/catalogo_importar arquivo:<arquivo.json>`: importa para revisão; não publica automaticamente.
- `/catalogo_publicar slug:<slug>`: publica se houver pelo menos um item e um troféu.

## Formato de importação

Veja `catalogo_exemplo.json`. O arquivo é apenas um exemplo de estrutura: seus dados são fictícios e marcados como não verificados. Não publique esse exemplo como catálogo real.

## Limites desta etapa

Esta entrega registra solicitações de jogos ausentes, mas **não** implementa ainda a pesquisa autônoma na web nem conectores de fontes externas. A camada de importação e o modelo de dados estão preparados para receber os conectores autorizados na próxima etapa. Também não inclui um catálogo real completo de Dark Souls III.

## Atualização

Faça backup do SQLite antes de atualizar. As novas tabelas são criadas automaticamente na inicialização e não alteram as tabelas antigas.
