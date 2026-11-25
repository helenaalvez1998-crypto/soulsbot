# Relatório de auditoria inicial — Cartas do Coliseu / Elden Ring

**Base analisada:** pacote `narabot-elden-ring-v54-potencia-raridade-ui(1).zip`  
**Escopo desta etapa:** catálogo Python, regras do Gwent, preparação/serialização das cartas, textos exibidos pelo site e testes de regressão.  
**Limite:** o ZIP não contém banco de dados SQLite; portanto, cartas/exemplares personalizados persistidos não foram auditados.

## Resultado executivo

- Catálogo carregado: **110 modelos**.
- Categorias: 26 Especiais, 21 Chefes, 16 Covenants, 15 Magias, 12 Armas, 10 Relíquias e 10 cartas de Patente.
- Raridades: 28 Comuns, 35 Raras, 21 Épicas, 11 Lendárias, 3 Míticas, 8 Primordiais e 4 Singulares.
- Testes executados: `PYTHONPATH=. pytest -q tests/test_elden_gwent.py tests/test_auditoria_efeitos_v50.py` — **24 passaram; 7 subtestes passaram**.

Os testes validam aspectos importantes do motor, mas não detectam todas as inconsistências semânticas e de apresentação descritas abaixo.

## Achados prioritários

### P0 — Facção está acoplada ao atributo Tipo

Em `sistemas/cartas.py`, `Carta.para_dict()` deriva a facção exclusivamente de `tipo`:

- Força → Ordem Áurea
- Destreza → Véu Carmesim
- Magia → Lua Negra

O motor repete o mesmo mapeamento em `sistemas/gwent.py` (`FACTIONS`). Isso produz divergências explícitas com a própria organização temática documentada nos comentários do catálogo:

- O bloco comentado como **Lua Negra** contém Assassina de Ravenmount, Fia, Blaidd, Ladina da Cidade Eterna e Recusante da Mansão Vulcânica, todas cadastradas como Destreza e, portanto, exibidas como Véu Carmesim.
- O bloco comentado como **Véu Carmesim** contém Guardião da Ordem Áurea, Servo dos que Vivem na Morte, Guerreiro da Chama Frenética, Cavaleiro de Sangue de Mohg e Bibliotecária de Raya Lucaria, todos cadastrados como Magia e, portanto, exibidos como Lua Negra.
- Blaidd, em particular, é apresentado no grupo Lua Negra, mas a regra automática o classifica no Véu Carmesim.

**Recomendação:** separar `faccao` de `tipo` no modelo de carta. `tipo` deve continuar representando o atributo mecânico (Força/Destreza/Magia); `faccao` deve ser um campo canônico explícito, com migração/fallback para cartas antigas. Atualizar serialização, preparação de cartas, validação de deck, passiva de facção, combos, líderes, APIs e testes em conjunto. Não corrigir apenas o texto visual: a facção também participa das regras.

### P0 — Descrição narrativa pode ser apresentada como efeito mecânico

`preparar_carta()` em `sistemas/gwent.py` preenche `habilidade_texto` nesta ordem: texto de identidade, texto de habilidade, `habilidade_texto` legado e, por fim, `descricao`.

Quando uma unidade não tem habilidade mecânica, a descrição narrativa pode virar o texto apresentado como habilidade. Exemplo: **Gigante de Fogo** tem habilidade `instinto`, mas sua descrição é apenas “Uma presença colossal na linha de frente.”; **Apóstolo da Pele Divina Errante** descreve uma ideia narrativa, enquanto o efeito real de `cacador_arcano` é condicional e numérico.

**Recomendação:** separar os campos `descricao_lore` e `habilidade_texto`. Para carta sem habilidade, exibir “Sem habilidade especial” (ou equivalente) e manter o texto de ambientação em área própria. Nunca usar texto de lore como fallback de efeito.

### P1 — Descrições de unidades não explicam seus efeitos

Há exemplos em que o campo `descricao` é flavor text, enquanto a habilidade ativa tem regra objetiva diferente:

- Godwyn, o Dourado: descrição narrativa; habilidade real `vinganca` concede +1 às unidades aliadas da mesma fileira ao cair.
- Carrasco de Volcano Manor: descrição narrativa; habilidade `devorar` consome a unidade aliada de menor poder efetivo na mesma fileira e ganha bônus até +4.
- Blaidd: descrição narrativa; habilidade `vinganca` concede +1 aos aliados da mesma fileira ao cair.
- Servo dos que Vivem na Morte: descrição narrativa; `ressurgir` traz do descarte a unidade elegível mais forte com poder-base 5 ou menos.

**Recomendação:** cada carta deve ter texto mecânico completo e conciso, derivado do efeito implementado; lore deve ficar em campo separado.

### P1 — Nome duplicado em cartas com funções diferentes

“Juramento do Crisol” é usado por `gwent_especial_vinculo` (carta Especial) e `gwent_singular_primeiro` (Relíquia Singular). Isso pode confundir busca, coleção, deck e leitura de recompensas.

**Recomendação:** manter o nome temático em uma delas e renomear a outra com distinção funcional clara, preservando os IDs internos.

### P1 — Descrições de Relíquias precisam explicitar condições e escolhas

As seis Relíquias têm handlers próprios no motor, fora do dicionário comum `HABILIDADES`, portanto não são habilidades desconhecidas. Contudo, alguns textos são incompletos:

- Espada da Noite e da Chama: exige fileira inimiga; a postura Noite aplica Geada, enquanto Chama reduz 1 do poder-base e 2 de bônus do alvo mais forte, salvo bloqueio por escudo. O texto atual não informa valores nem seleção de fileira.
- Runa da Morte: afeta a unidade com bônus positivo mais alto em cada fileira, removendo até 2 de bônus; a descrição não esclarece a seleção por fileira.
- Grande Runa dos Não Nascidos: só tem efeito se aliados possuírem Geada ou Podridão; cada purificado recebe +1.
- Algemas de Margit: anula bônus positivos de um alvo na fileira escolhida; não remove penalidades.

**Recomendação:** descrever alvo, condição, magnitude, duração e bloqueios quando aplicável.

### P2 — Texto do catálogo e texto do motor não são uma única fonte

O catálogo mantém textos em `HABILIDADES`, descrições individuais em `Carta.descricao` e textos de identidade em `CARD_IDENTITY_ABILITIES`. `preparar_carta()` escolhe entre essas fontes por precedência. Isso cria risco de divergência e torna a auditoria manual mais difícil.

**Recomendação:** centralizar o texto mecânico em uma definição canônica por habilidade/identidade e gerar o texto apresentado pela mesma definição que orienta o efeito. Textos específicos por carta devem substituir o genérico apenas quando houver regra realmente diferente.

## Plano recomendado de execução

1. **Modelo semântico:** separar facção, tipo mecânico, lore e efeito.
2. **Auditoria carta a carta:** validar nome, facção, raridade, poder-base, fileira, habilidade, condições, alvo, magnitude e duração contra o motor.
3. **Correção de textos:** produzir descrições mecânicas padronizadas e textos de lore independentes.
4. **Interface:** mostrar nome, facção, raridade, poder-base, fileira, habilidade e lore em hierarquia consistente; diferenciar poder-base, potência de raridade e bônus temporários.
5. **Regressão:** adicionar testes para garantir que o texto exibido corresponde à habilidade e que facção não é inferida indevidamente do tipo.
6. **Banco de dados:** auditar exemplares, cartas personalizadas e valores persistidos após receber o arquivo SQLite atual.

## Arquivos principais para a próxima etapa

- `sistemas/cartas.py`
- `sistemas/gwent.py`
- `site/app.js`
- `site/index.html`
- `site/style.css`
- `database.py`

## Não alterado nesta etapa

Nenhuma regra de batalha, custo, drop, raridade, poder ou persistência foi modificada. Este arquivo registra achados da auditoria estática para orientar correções controladas.
