# V81 — Fundação do sistema visual modular de cartas

## Objetivo
Evoluir o renderizador de cartas existente, sem criar um segundo pipeline e sem adicionar geração de imagens por IA ao runtime do bot.

## O que entrou nesta etapa

- Novo módulo `sistemas/identidade_visual_cartas.py` centraliza a identidade visual das três facções e das sete raridades.
- Cada facção possui identificadores semânticos independentes para brasão, estandarte, cenário e ornamento, além da paleta.
- Cada raridade possui identificadores próprios de gema, material, formato do medalhão, nível de ornamento e brilho. Portanto, a definição não é apenas uma troca de cor.
- `sistemas/arte_cartas.py` passa a consultar o registro central para resolver paleta de facção e acabamento de raridade.
- O fingerprint do renderizador inclui o novo módulo; alterações futuras na identidade invalidam automaticamente as imagens persistidas antigas.
- O módulo é leve: apenas biblioteca padrão, sem carregar imagens, chamar IA, fazer rede ou acessar banco de dados.
- A ficha visual é copiada por chamada para impedir que uma renderização altere a configuração global.

## Arquitetura-alvo

1. **Template-base da composição:** cabeçalho, moldura, placa de nome, coluna de poder/combate, faixa inferior e painel de habilidade/lore.
2. **Tema de facção:** brasão, estandartes, cenário e ornamentos específicos.
3. **Tema de raridade:** medalhão completo e acabamento próprios para cada raridade.
4. **Arte da carta:** imagem independente, recortada e encaixada na janela central.
5. **Dados do catálogo:** nome, poder, categoria, fileira, habilidade, bônus e lore; nenhuma regra é inferida pela camada visual.
6. **Cache persistente:** compor apenas em cache miss; servir PNG/WebP pronto nas visualizações seguintes.

## Peso e desempenho

- Não executar geração por IA no processo do bot.
- Não baixar assets em cada renderização.
- Manter assets estáticos locais, compartilhados entre cartas.
- Compor uma carta somente quando a chave de conteúdo mudar.
- Usar WebP para miniaturas e PNG para a carta de alta qualidade/transparência quando necessário.
- Manter o limite de concorrência e o cache já implementados na V80.

## Testes

- `python -m unittest tests.test_identidade_visual_cartas -v`: 5 testes aprovados.
- `python -m py_compile sistemas/arte_cartas.py sistemas/identidade_visual_cartas.py tests/test_identidade_visual_cartas.py`: aprovado.
- `node --check site/app.js`: aprovado.
- A suíte completa não foi executada nesta etapa. Um teste preexistente de renderização das 21 combinações excedeu o limite de tempo do ambiente durante a execução; isso não foi contado como aprovado.

## Limite desta entrega

Esta etapa implementa a fundação modular e a resolução de identidade, mas ainda não substitui o acabamento procedural atual por todos os assets ornamentais finais aprovados nas referências. A próxima etapa é produzir os templates gráficos reutilizáveis e integrar cada camada no renderizador, começando por uma carta piloto de cada facção e raridade. Nenhuma mecânica, ID ou atributo do catálogo foi alterado.
