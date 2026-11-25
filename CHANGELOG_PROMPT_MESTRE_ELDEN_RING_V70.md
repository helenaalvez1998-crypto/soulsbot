# Narabot V70 — Direção de arte e prompts Elden Ring

## Objetivo

Aplicar o Prompt-Mestre de Direção de Arte aos dois fluxos de prompts de ilustração: Ateliê do catálogo e criação/transmutação de cartas personalizadas.

## Mudanças

- Padronizada a composição dos prompts em 14 camadas: identificação; referência canônica de Elden Ring; aparência; armadura e vestimentas; armas e postura; expressão; cena narrativa; ambiente; iluminação; paleta; composição; proporção; acabamento; restrições.
- Adicionada análise artística em português, prompt profissional em inglês e negative prompt específico por carta.
- Reforçadas as instruções de fidelidade aos modelos, armaduras, silhuetas e equipamentos reconhecíveis de Elden Ring; quando a identidade canônica não puder ser determinada, o texto evita inventar detalhes como fatos canônicos.
- Adicionadas travas de identidade para personagens e conjuntos reconhecíveis, incluindo Ranni, Malenia, Radahn, Godfrey, Maliketh, Messmer e a Casa Hoslow.
- Sinergias são tratadas como contexto complementar; não adicionam automaticamente personagens secundários.
- Habilidades e efeitos só são representados quando existem na ficha; cartas sem habilidade recebem restrições contra magia ou efeitos artificiais não justificados.
- Aplicada a exigência global de universo Elden Ring, sem mistura com outras franquias.
- Fixada a proporção horizontal 5:4, com saída normalizada em 1200 × 960 px nos fluxos de arte do catálogo e de upload/criação.
- Atualizadas as telas do Ateliê para exibir e copiar separadamente a análise, o prompt e o negative prompt, além de copiar o pacote completo.
- Atualizada a API do Ateliê para retornar as três seções e os metadados da proporção.

## Compatibilidade

- Mantida a função pública `gerar_prompt_carta(carta)` como retorno textual do prompt positivo, para não quebrar consumidores existentes.
- Adicionada `gerar_prompt_carta_estruturado(carta)` para consumidores que precisam das três seções.
- Sem alteração intencional de regras de combate ou migração de banco de dados.

## Validação executada

- `py_compile` dos módulos Python alterados: aprovado.
- `node --check site/app.js`: aprovado.
- Verificação de sintaxe do JavaScript inline de `site/atelie-arte.html`: aprovada.
- Testes focados de direção de arte, Ateliê, laboratório e normalização: 25 testes aprovados e 115 subtestes aprovados.
- A suíte completa possui uma falha identificada em `tests/test_auditoria_efeitos_v50.py::test_efeitos_especiais_sem_texto_ficam_explicitos`, relacionada ao relatório de relíquias/efeitos especiais (`reliquia_godrick` ausente da lista esperada). O teste está fora dos módulos de geração de prompts e não foi alterado nesta entrega. Uma execução completa adicional excedeu o limite de tempo disponível.

## Observação de uso

O sistema monta os prompts; não chama automaticamente um serviço externo para gerar a imagem. O prompt positivo e o negative prompt devem ser enviados ao gerador de imagens utilizado pelo operador. A saída de arte normalizada pelo projeto é 1200 × 960 px (5:4).
