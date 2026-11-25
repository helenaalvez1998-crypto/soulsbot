# V10 — Molduras retangulares de cantos retos

## Objetivo

Manter a carta no formato vertical colecionável (420 × 620), mas substituir contornos recortados/angulares por uma moldura retangular com quatro cantos retos de 90 graus.

## Alterações

- A silhueta externa agora é um retângulo vertical com cantos retos e espessura uniforme.
- A geometria externa deixou de variar por facção; nenhuma facção altera o formato de carta.
- A identidade de facção aparece em gravações internas do aro:
  - Ordem Áurea: ramos da Térvore, folhas e cantoneiras arquitetônicas de Leyndell.
  - Véu Carmesim: espinhos, gotas e marcas rituais inspiradas em Mohgwyn.
  - Lua Negra: arcos lunares, órbitas e estrelas inspiradas na tradição cariana.
- A raridade continua definindo metal, cor, brilho e acabamento.
- As 21 combinações (3 facções × 7 raridades) continuam distintas no overlay.
- Janela da ilustração, proporção da carta, placas, textos, poder, ícones, regras e substituição de arte foram preservados.
- Versão do cache do renderizador atualizada para V10, invalidando automaticamente imagens antigas.

## Validação

- `python -m compileall -q .`
- `python -m unittest discover -s tests -v`
- 34 testes aprovados.
- Verificação de cantos retos, formato vertical, aliases antigos e diferenças visuais entre as 21 combinações.
