# Templates completos das cartas — guia

## O que muda

Cartas **com arte enviada pelo membro** passam a usar um **template completo por raridade**
(Comum, Rara, Épica, Lendária, Primordial): fundo, moldura e placas vazias já desenhados.
O bot cola a arte do membro *por trás* do template (ela aparece pela janela da arte) e escreve
nome, raridade, poder, tipo, categoria, custo e habilidade nos slots.

Cartas **sem arte enviada** continuam sendo desenhadas por código, exatamente como antes. Se uma raridade
ainda não tem template, as cartas dela com arte usam o layout antigo (janela + moldura).
O painel antigo de **Molduras fixas** continua valendo para as cartas sem arte enviada.

## Instalação

Copie os arquivos mantendo as pastas e reinicie o bot:

- `sistemas/templates_cartas.py` (novo)
- `sistemas/arte_cartas.py`
- `cogs/cartas_coliseu.py`
- `cogs/admin.py`
- `tests/test_templates_cartas.py` (novo, opcional)

## Enviar um template

1. Gere os 5 templates com os prompts de `dados/TEMPLATES_CARTAS_PROMPTS.md`, usando `dados/guia_template_carta_limpo.png` como referência.
2. `/adm` → **Jogos, Coliseu e runs** → **Templates das cartas (com arte)**.
3. Clique no botão da raridade; a Nara abre uma DM. Responda anexando **um** arquivo.
4. O bot valida, salva e devolve duas prévias: a carta de exemplo e outra com os slots contornados.

Requisitos: carta **completa e opaca**, retrato ~420:620 (recomendado 840 × 1240; até 6% de diferença é esticado), até 8 MB,
**sem texto**. A janela da arte (grande, no meio, ~5:4) deve estar transparente **ou** em magenta chapado `#FF00FF`
(o bot troca por transparência). PNG recomendado; JPG/WEBP só com o magenta bem chapado.

A janela é **detectada automaticamente** no arquivo enviado, então a arte sempre encaixa, mesmo que a IA erre alguns pixels.
Os arquivos ficam em `DATA_DIR/cartas_templates/` (na FadeHost, dentro do volume persistente).

## Layout dos textos (grade 840 × 1240)

| Campo | Posição |
|---|---|
| raridade | 600,44 → 784,96 |
| nome | 56,100 → 784,236 |
| arte | detectada no PNG (padrão 56,256 → 784,846) |
| poder | centro 144,986, raio 78 |
| tipo / categoria | 254,918 → 780,978 |
| custo | 254,992 → 780,1052 |
| habilidade | 56,1084 → 784,1176 |

Se a IA deslocar uma placa, ajuste só aquela raridade criando `DATA_DIR/cartas_templates/<raridade>.json`
(`comum`, `rara`, `epica`, `lendaria`, `primordial`) com apenas os campos que mudam; um `layout.json` na mesma pasta vale para todas:

```json
{
  "habilidade": [60, 1090, 780, 1180],
  "poder": {"centro": [150, 990], "raio": 70}
}
```

Campos inválidos são ignorados. Use a segunda prévia (slots contornados) para ler as coordenadas.

## Observações

- As cartas já enviadas no Discord não são editadas; valem as próximas renderizações.
- Somente o proprietário global do bot (`BOT_OWNER_ID`, `SOULS_USER_ID` ou dono da aplicação) altera templates.
- Fonte: o projeto só inclui `DejaVuSans.ttf` (regular). Para um título em negrito de verdade, adicione `DejaVuSans-Bold.ttf` em `fonts/`.
