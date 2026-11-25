# V9 — Direção de arte específica de Elden Ring

## Escopo

Atualiza exclusivamente os prompts do Ateliê que orientam a criação ou regeneração da ilustração. Mantém intactos o renderizador Python/Pillow, molduras, ícones, painel de habilidade, dimensões, recorte, upload e substituição manual de arte, regras do Gwent e banco de dados.

## Problema corrigido

A V7 ainda dependia de uma direção de arte de fantasia medieval genérica, com referências de regiões adicionadas como camada. Além disso, o fluxo descartava storyboards antigos sem substituí-los por cenas realmente específicas e aplicava perfis aleatórios de rosto/cabelo/idade a personagens que deveriam manter aparência canônica.

## Alterações

- Direção visual principal agora é Elden Ring: Terras Intermédias e Reino das Sombras, sem usar castelos medievais genéricos ou estética de fantasia intercambiável.
- Adicionadas 89 cenas específicas por ID do catálogo: personagem/entidade, silhueta, roupa/armadura, arma ou relíquia, ação, cenário, materiais, iluminação e enquadramento.
- As 10 cartas dinâmicas de patente recebem briefing próprio com estágio de progressão, facção/tipo, equipamento e região coerentes com o nome gerado.
- Personagens canônicos como Ranni, Godfrey, Gurranq, Blaidd, Fia, Godwyn, Maliketh, Placidusax, Marika e o Gigante de Fogo recebem travas de identidade e detalhes reconhecíveis.
- Entidades não humanas, espíritos, relíquias e efeitos especiais não recebem corpo humano aleatório.
- Perfis aleatórios de rosto, idade, cabelo, gênero e físico foram removidos dos prompts Elden Ring.
- As facções do NARABOT continuam sendo alinhamentos de deck: não alteram a filiação, o equipamento ou a história canônica dos personagens.
- Raridade controla grandiosidade/composição, sem inventar poderes ou redesenhar a identidade do personagem.
- A área da arte permanece uma imagem isolada 5:4, sem moldura, texto, custo, números ou UI.

## Cobertura e validação

- 89 cenas específicas para cartas fixas.
- 10 briefings dinâmicos para cartas de patente.
- 99 cartas do catálogo verificadas sem fallback genérico.
- Testes de identidade canônica, facções, cenas, custo/UI e compatibilidade de cartas de outra origem.
- Suíte completa: 33 testes aprovados.

## Arquivos

- `sistemas/atelie_coliseu.py`
- `tests/test_elden_art_prompts.py`
- `CHANGELOG_PROMPTS_ARTE_ELDEN_V9.md`
- `INSTALACAO_PROMPTS_ELDEN_V9.md`
