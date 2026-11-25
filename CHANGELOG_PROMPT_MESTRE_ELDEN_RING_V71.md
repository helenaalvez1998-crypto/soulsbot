# Narabot V71 — Prompt-Mestre por facção e fidelidade canônica

## Implementação

- Implementado o texto de referência fornecido como regra comum nos dois fluxos: Ateliê do catálogo e criação/transmutação de cartas.
- Unificada a direção das três facções em `sistemas/direcao_arte_prompts.py`: Ordem Áurea, Véu Carmesim e Lua Negra.
- A facção é lida exclusivamente do campo `faccao`; lore, sinergias, afinidades, nome, aparência, tipo e habilidade não podem atribuir facção.
- Nenhuma quarta facção é criada. Campo ausente ou inválido gera direção neutra e sinalização explícita, sem inferência.
- A facção orienta principalmente iluminação, atmosfera, cenário e acentos ambientais. Design, cores, armadura, roupas, anatomia, armas e equipamentos canônicos têm prioridade absoluta.
- Reorganizadas as camadas do prompt em 16 seções sequenciais: identificação; Elden Ring/cânone; campo de facção; direção da facção; aparência; armadura/equipamento; armas/postura; expressão; cena; ambiente; iluminação; paleta; composição; formato 5:4; qualidade; negative prompt.
- Unificadas as direções que antes estavam duplicadas e divergiam entre o Ateliê e o criador de cartas.
- Mantidas as três saídas: análise artística em português, prompt profissional em inglês e negative prompt específico em inglês.
- Mantida a proporção horizontal 5:4 e normalização 1200 × 960.

## Compatibilidade

- Mantidas as funções públicas de geração já utilizadas pela API e pelo site.
- Sem alteração intencional de regras de combate ou migração do banco de dados.

## Validação

- Testes específicos dos dois fluxos de prompts e das três facções adicionados na V71.
