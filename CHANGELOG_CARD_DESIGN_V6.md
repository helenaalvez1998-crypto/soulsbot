# Narabot — Design de cartas V6: heráldica de Elden Ring

## O que mudou

- **Ordem Áurea:** selo redesenhado como Térvore dentro do círculo do Elden; ornamentos laterais em forma de ramos e folhas douradas.
- **Véu Carmesim:** selo ritual com tridente, gota de sangue e espinhos; ornamentos laterais inspirados em espinhos e marcas de sangue.
- **Lua Negra:** crescente lunar com órbita e estrelas; ornamentos laterais com arcos orbitais e estrelas.
- Os ornamentos de facção são aplicados no overlay da carta, mantendo a arte central, o poder, a raridade, a fileira e a descrição legíveis.
- A raridade continua definindo o metal e a geometria da moldura; a facção define os símbolos e os detalhes heráldicos. As duas informações não competem entre si.
- Versão do renderizador alterada para V6. A impressão digital do código invalida automaticamente o cache visual antigo.
- Não há alteração de regras, cartas, banco de dados, coleções ou decks.

## Instalação

Substitua os arquivos do projeto pelos do pacote V6, preservando `.env` e o banco de dados. O cache antigo não precisa ser apagado manualmente; a versão do renderizador força a regeneração das cartas.
