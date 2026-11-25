> Documento histórico. A V8 substitui este fluxo e consolida o Gwent como único jogo de cartas ativo. Consulte `CHANGELOG_GWENT_V8.md` e `INSTALACAO_GWENT_V8.md`.

# Atualização — Arena Gwent

## Implementado
- Novo motor isolado em `sistemas/gwent.py`.
- Deck Gwent independente de 10 cartas, sem alterar o deck clássico de 5.
- Três fileiras: Força, Destreza e Magia mapeadas para corpo a corpo, longa distância e cerco.
- Turnos alternados, cartas persistentes no campo, passar rodada e melhor de três.
- Habilidade de líder e clima por fileira, cada uma limitada por partida.
- Efeitos táticos para as habilidades já existentes no catálogo de cartas.
- Persistência de decks e partidas em novas tabelas SQLite.
- Interface no site com construção de deck, seleção de adversário, arena, placar e atualização automática.
- Aviso por DM no Discord ao adversário quando uma partida é criada.
- Recompensa única de cinco cartas comuns adicionais entregue ao abrir o painel de cartas no Discord.
- Economia, coleção, pacotes, forja, recompensas e duelos clássicos mantidos separados.

## Validação executada
- `py_compile` nos módulos Python alterados.
- `node --check site/app.js`.
- Testes unitários do motor Gwent (6 testes).
- Execução do schema SQLite em banco temporário.

## Limites desta entrega
- Não foi possível executar um teste de integração do bot completo neste ambiente porque as dependências de runtime do projeto (incluindo `aiosqlite` e `discord.py`) não estão instaladas.
- As partidas Gwent são iniciadas diretamente pelo site; o oponente recebe aviso por DM. A aceitação formal de convite, ranking Gwent, matchmaking e recompensas pós-partida ainda não fazem parte desta versão.
- A coleção atual não contém cartas de clima/especiais como cartas individuais; clima e líder entram como ações táticas limitadas por partida.


## Atualização competitiva — versão 2
- Deck Gwent ampliado para 12 cartas: 10 na mão inicial e 2 reservas.
- Troca inicial (mulligan) de até duas cartas por jogador, antes do primeiro turno de batalha.
- Três facções determinadas pela composição de unidades do deck: Ordem de Ferro (Força), Errantes do Véu (Destreza) e Conclave Arcano (Magia). A primeira unidade da facção recebe +1 por rodada.
- Seis cartas especiais disponíveis na coleção: Névoa de Guerra, Geada Implacável, Chuva de Ferro, Chifre de Batalha, Médico de Campanha e Queima Estratégica.
- Kit de duas cartas especiais entregue uma única vez também a contas antigas, sem apagar a recompensa inicial anterior.
- Cartas especiais são aceitas em decks Gwent e bloqueadas nos decks clássicos de cinco cartas.
- Ranking individual MMR com patentes Bronze, Prata, Ouro e Diamante.
- Resultado final concede Denários e atualiza MMR com gravação idempotente por partida/jogador.
- Recompensas: vitória +40 Denários e +25 MMR; derrota +15 Denários e -15 MMR; empate +25 Denários e sem alteração de MMR.
- Migração aditiva: novas tabelas são criadas sem remover coleções, saldos ou históricos existentes.
- Testes do motor ampliados para 8 casos, incluindo mulligan, facções e cartas especiais.


## Atualização — Sinergias e combos entre cartas
- Adicionado sistema de arquétipos por carta com metadados de sinergia expostos ao cliente.
- Novos combos nomeados: Pacto das Cinzas (Guardião das Cinzas + unidade da Fornalha), Caçada do Véu (duas unidades do Véu Sombrio) e Convergência Astral (Dama do Vazio + unidade Astral).
- Cada combo concede +2 de poder à carta que completa a combinação e só pode ativar uma vez por jogador por rodada.
- Estado dos combos é reiniciado no início de cada rodada e possui compatibilidade com partidas persistidas de versões anteriores.
- A interface de montagem de deck, mão e campo exibe as afinidades disponíveis; o registro da partida anuncia o combo ativado.
- Mantidas as sinergias existentes de fileira, facção e cartas especiais.
- Validação: compilação Python e cinco verificações direcionadas de combos e metadados.


## Atualização — Arquétipos e combos ampliados
- Ampliado o mapa de afinidades de cartas existentes sem criar modelos duplicados.
- Novos combos: Maré Abissal, Juramento do Estandarte, Passos das Duas Luas, Eco Convergente, Chama em Contraponto e Rota do Peregrino.
- Juramento do Estandarte fortalece também aliados na mesma fileira; demais combos aplicam bônus direto à carta que conclui a combinação.
- Todos os combos são limitados a uma ativação por jogador por rodada e reiniciam na transição de rodada.
- Cartas agora expõem combos compatíveis e arquétipo da facção para interfaces de coleção, mão e deck.
- Identidade estratégica das facções: Ordem de Ferro (formação/resistência), Errantes do Véu (mobilidade/encadeamento) e Conclave Arcano (preparação/amplificação).
- Mantidas as habilidades individuais, cartas especiais, líderes, progressão, economia e persistência existentes.
- Validação: compilação Python, sintaxe JavaScript e nove testes direcionados de combos.

## Habilidades individuais V3
- Adicionadas habilidades de identidade para 28 cartas nomeadas.
- As descrições individuais são expostas pela preparação de cartas usada pelo bot/site.
- Efeitos incluem proteção, enfraquecimento, suporte, reação a clima, descarte, pontuação e posicionamento.
- Mantidos os nove combos específicos e as habilidades gerais existentes.
- Testes unitários ampliados para validar metadados e resolução de efeitos.
