# Direção artística híbrida do Coliseu

## Identidade

A nova direção mistura fantasia sombria monumental e pictórica com energia visual de anime épico. O objetivo é obter ambientes antigos, grandiosos e trágicos, materiais convincentes e luz cinematográfica, combinados com personagens de silhueta clara, poses expressivas, movimentos dinâmicos e efeitos sobrenaturais legíveis.

A referência a jogos como Elden Ring é usada somente como referência ampla de atmosfera, escala mitológica, arquitetura e tom. O prompt proíbe reproduzir personagens, locais exatos, key art, roupas icônicas, logos ou composições protegidas. O resultado deve ser uma interpretação original do universo de cada jogo.

## Personalização por carta

O botão **Gerar prompt de arte** agora monta instruções a partir de:

- jogo de origem e sua identidade temática ampla;
- categoria (chefe, arma, magia, covenant, jogo, patente ou relíquia);
- raridade, que ajusta a escala e a intensidade visual sem alterar a moldura oficial;
- tipo (Destreza, Força ou Magia), que define acentos de cor e movimento;
- habilidade, que fornece uma metáfora visual específica;
- nome e descrição/lore da carta.

## Regras de composição

- Arte horizontal 5:4, para encaixar na janela atual do renderizador.
- Um foco visual dominante e uma cena com narrativa própria.
- Primeiro plano, plano do sujeito e fundo para dar profundidade.
- Silhueta legível em tamanho pequeno.
- Luz motivada, efeitos com interação física no cenário e partículas controladas.
- Sem moldura, borda, texto, números, atributos, logo, marca d'água ou interface. O SoulsBot aplica a moldura fixa e os dados oficiais separadamente.

## Instalação

Substitua os arquivos mantendo os caminhos originais:

- `sistemas/atelie_coliseu.py`
- `cogs/cartas_coliseu.py`

O arquivo `tests/test_atelie_coliseu.py` contém testes de regressão para a montagem dos prompts.
