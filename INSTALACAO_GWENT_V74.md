# Instalação — Narabot V74

1. Faça backup da pasta atual do Narabot e do banco de dados.
2. Extraia o conteúdo deste pacote e substitua os arquivos da instalação.
3. Preserve seu `.env` e as credenciais existentes. Não substitua configurações privadas pelas de exemplo.
4. Reinicie o processo do bot/servidor.
5. Abra o site e atualize com `Ctrl + F5` para carregar `app.js` e `style.css` da V74.
6. Entre no construtor, confira a composição da facção e salve novamente o deck caso ele não corresponda à facção predominante.
7. Em uma partida de teste, confirme a seleção de alvo/modo da relíquia e a alternância de iniciativa na segunda rodada.

## Regras importantes da V74

- A facção salva deve ser uma das mais representadas entre as unidades do deck. Cartas especiais não contam. Se houver empate na maior contagem, qualquer facção empatada é válida.
- A relíquia equipada ocupa um slot separado e não pode ser incluída entre as 12 cartas do deck.
- O primeiro jogador da partida é o criador do desafio. A iniciativa alterna na abertura de cada rodada subsequente.
- Relíquias são efeitos fixos: a raridade do item não amplifica seus números.

Não há migração de banco de dados. Decks e coleções existentes são preservados.
