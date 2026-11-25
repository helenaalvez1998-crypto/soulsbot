# V69 — Prompts de arte específicos por carta

## Objetivo

Aprimorar os prompts usados na geração de ilustrações do Ateliê do Coliseu e na criação/transmutação de cartas. O prompt agora parte dos dados efetivos de cada carta e os converte em uma direção de arte concreta, mantendo uma identidade visual coerente com o mundo de *Elden Ring* e com a facção correspondente.

## Alterações

- Atualizado `sistemas/atelie_coliseu.py`, usado pelo Ateliê das cartas do catálogo.
- Atualizado `sistemas/prompt_arte_criador.py`, usado pelas cartas geradas/transmutadas.
- Os dois caminhos agora usam a mesma camada de interpretação de lore para converter identidade, papel, objetos, localidade e atmosfera em decisões visuais rastreáveis aos dados da carta.
- O briefing considera nome, lore, facção, tipo, raridade, poder atual e teto de poder, função tática, fileira, arquétipo, epíteto, afinidades, habilidade e regra canônica, sinergias e ingredientes de transmutação quando esses dados existem.
- Separação explícita entre fatos canônicos da carta e escolhas de encenação artística. Pose, câmera, clima e iluminação comunicam os fatos, mas não criam nova biografia, equipamento ou poder.
- Padrões cromáticos e materiais mais consistentes para Ordem Áurea, Véu Carmesim e Lua Negra, sem impor o mesmo uniforme a todos os personagens nem sobrescrever identidades canônicas de *Elden Ring*.
- Sinergias são contexto estratégico. Não obrigam a inclusão de outros personagens na ilustração.
- Habilidades são traduzidas em ações visíveis somente quando há nome/regra canônica resolvida. Uma chave interna desconhecida, sozinha, não autoriza efeitos mágicos.
- Cartas sem habilidade especial recebem uma restrição explícita contra magia, aura, runas flutuantes, trilhas de energia e poderes artificiais.
- Reforçadas as regras de ilustração isolada: sem moldura, texto, título, números, ícones, interface, logotipo ou marca d'água.
- Corrigida a identificação textual da facção Lua Negra no prompt do catálogo.

## Exemplo verificado: Duelista da Casa Hoslow

O prompt agora orienta uma cena individual coerente com a identidade da Casa Hoslow: armadura prateada ajustada com gravações florais, luvas articuladas, capa vermelho-escura, par de chicotes longos e flexíveis com espinhos, postura técnica de duelo e pátio de pedra vulcânica da Mansão Vulcânica. A promessa de sangue é tratada como voto sombrio e tensão aristocrática, não como gore ou magia. A sinergia com o Batedor da Mansão Vulcânica é apenas contexto e não exige um segundo personagem.

**Atenção aos dados atuais:** no catálogo que acompanha esta versão, a carta está com poder **5**, teto **5**, raridade **Comum** e **sem habilidade especial**. O tutorial de referência cita poder 4; o prompt do catálogo preserva os dados ativos do jogo e não altera as regras da carta.

## Escopo e compatibilidade

- Nenhuma regra de combate, estatística, raridade, sinergia ou dado de carta foi alterado.
- Nenhuma imagem existente é regenerada automaticamente. As novas instruções são usadas na próxima solicitação de geração de prompt; artes já salvas permanecem intactas.
- Não há migração de banco de dados.
