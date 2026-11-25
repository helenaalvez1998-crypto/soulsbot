# V30 — Gerador Procedural

## Implementado
- `sistemas/gerador_cartas.py`, motor determinístico baseado em seed fornecida pelo servidor.
- Geração de identidade estrutural: nome, descrição, facção, afinidade, função, fileira, raridade, poder e habilidade.
- Raridade resultante baseada na mediana inferior das raridades dos ingredientes, limitada a Comum–Mítica.
- Poder escolhido dentro da faixa já definida para a raridade.
- Facção, afinidades e função derivadas pela taxonomia V29.
- Habilidade opcional (50% por tentativa) escolhida exclusivamente entre `HABILIDADES_COMUNS` já presentes no motor.
- Validador estrutural de definição.
- Monitor cumulativo 50/50 que mede a distribuição observada sem forçar cada tentativa individual.
- ID de carta gerada validado como identificador emitido pelo servidor.

## Segurança e limites
- O módulo não persiste dados, não consome ingredientes/materiais e não publica cartas.
- Seed e ID devem ser emitidos pelo servidor; a API ainda não foi conectada.
- O hash de seed retornado é um marcador de auditoria, não prova criptográfica de que a seed foi mantida secreta.
- A geração de arte não está incluída.
- Habilidades Primordiais e habilidades de cartas especiais não são elegíveis.
- A distribuição de 50/50 é monitorada cumulativamente; a V30 não força a proporção em uma amostra pequena.
- Não foi validado equilíbrio competitivo; o gerador apenas respeita faixas e limites estruturais.

## Próxima etapa
V31 — validação aprofundada, controle cumulativo 50/50, revisão de combinações e proteção contra resultados inválidos.
