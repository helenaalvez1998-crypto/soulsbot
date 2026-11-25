# V50 — Auditoria de fidelidade dos efeitos

- Criado `sistemas/auditoria_efeitos.py`, que compara o catálogo `HABILIDADES` com os contratos de cobertura do motor.
- Separa habilidades gerais, habilidades especiais, efeitos de identidade por carta e unidades sem habilidade.
- Expõe lacunas e efeitos especiais registrados no motor sem texto no catálogo, sem inventar descrições.
- Inclui testes de contrato para impedir que novas habilidades sejam adicionadas ao catálogo sem classificação no motor.
- Limite: o relatório comprova cobertura estrutural por identificador, não comprova execução correta de cada efeito em partidas reais. A homologação funcional continua necessária.

## Resultado do catálogo V49 auditado

- 52 identificadores de habilidade no catálogo.
- 0 habilidades sem cobertura estrutural declarada no motor.
- 16 efeitos de identidade de cartas separados das habilidades genéricas.
- 39 modelos de unidade listados como sem habilidade especial.
- 6 identificadores de Relíquias presentes no contrato de especiais do motor, mas ausentes do dicionário genérico `HABILIDADES`; isso é esperado porque as Relíquias possuem catálogo próprio na interface e não devem ser misturadas às cartas especiais comuns.

A contagem de 39 refere-se a modelos de carta sem habilidade, não à proporção atual de exemplares gerados. A regra de distribuição 50/50 deve ser medida na amostra de transmutação, não inferida desse total.
