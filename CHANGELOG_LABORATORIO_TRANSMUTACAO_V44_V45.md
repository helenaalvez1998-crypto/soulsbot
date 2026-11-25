# Laboratório de Transmutação — V44 e V45

## V44 — Identidade, manifesto e persistência de arte por carta
- Adicionado manifesto individual com card_id, owner_id, facção, raridade, afinidade, função tática, provedor, conceito e SHA-256.
- Validação estrita de facção/raridade, imagem PNG, tamanho e identidade da carta.
- Persistência de manifesto JSON imutável ao lado do PNG, com gravação atômica e proteção contra sobrescrita.
- Adaptador aceita bytes de um provedor externo de ilustração original.
- O renderer local existente continua sendo uma composição gráfica procedural; não é uma pintura original gerada por IA.

## V45 — Variedade de identidade procedural
- Expandido o catálogo de arquétipos por função tática.
- Adicionados epítetos temáticos por afinidade.
- Descrições de lore específicas por função.
- Identidade procedural determinística vinculada à seed e registrada na definição.
- Mantidas facções, raridades, faixas de poder, habilidades já aprovadas e monitoramento cumulativo 50/50.
- Nenhuma habilidade nova foi introduzida no motor.

## Validação executada
- `compileall` para módulos `sistemas`, `database.py` e `site_hub.py`: aprovado.
- Testes V44/V45 e regressões V30/V31/V32/V42/V43: 33 passed.

## Limitações
- A integração com um serviço real de geração de ilustrações originais ainda depende de credenciais, provedor e testes externos; este pacote entrega contrato de validação/persistência, não uma biblioteca completa de pinturas originais.
- Não houve teste visual no navegador nem homologação em banco de produção.
- O catálogo de arquétipos amplia variedade narrativa, mas ainda exige avaliação em partidas para medir diversidade competitiva.
