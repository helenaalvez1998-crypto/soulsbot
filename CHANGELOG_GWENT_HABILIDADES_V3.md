# Gwent do Coliseu — Habilidades individuais V3

## Escopo
Esta versão adiciona habilidades de identidade para 28 cartas nomeadas, sem remover as habilidades gerais, as sinergias de fileira/facção ou os nove combos específicos existentes.

## Princípios
- Habilidades de identidade são resolvidas quando a unidade entra em campo.
- Cada habilidade possui texto próprio exposto pelo objeto preparado da carta (`habilidade_nome`, `habilidade_texto`, `habilidade_identidade`).
- Efeitos de suporte afetam aliados; controle afeta bônus inimigos; condições de pontuação concedem bônus limitados.
- As cartas sem habilidade de identidade continuam usando suas habilidades gerais atuais.
- As cartas Primordiais mantêm suas habilidades especiais existentes.
- Cartas especiais mantêm seus efeitos de ação existentes.

## Habilidades individuais

| Carta | Habilidade | Efeito resumido |
|---|---|---|
| Guardião das Cinzas | Égide das Cinzas | Protege aliado da fileira e recebe bônus ao entrar acompanhado |
| Dama do Vazio | Fenda do Vazio | Reduz o bônus do inimigo mais forte |
| Cervo Sombrio | Passagem Sombria | Cresce conforme aliados ocupam outras fileiras |
| Rei Afogado | Dízimo do Abismo | Aproveita descarte ou desvantagem numérica |
| Oráculo da Ruína | Presságio da Ruína | Enfraquece a maior ameaça e reage à pontuação inferior |
| Caçador sem Rosto | Marca da Presa | Ganha força contra inimigos mais poderosos |
| Vigia Cinzento | Vigília Cinzenta | Fortalece aliados na mesma fileira |
| Aparição do Véu | Deslocamento Espectral | Recompensa alternância de fileira |
| Duelista do Peregrino | Duelo do Peregrino | Reage à fileira usada pelo rival |
| Ferreiro de Guerra da Fornalha | Martelo de Cadência | Escala com aliados da Ordem de Ferro na fileira |
| Oráculo do Marulho | Ressonância das Marés | Reage à presença do Conclave inimigo |
| Dançarina das Duas Luas | Dança Espelhada | Recompensa distribuição entre fileiras |
| Guardião do Sino de Ferro | Sino do Último Bastião | Ganha força quando está atrás |
| Tecelã da Agulha Astral | Fio Astral | Enfraquece ameaça e prepara bônus para próxima unidade Astral |
| Lanceiro da Fornalha | Investida da Fornalha | Recompensa presença aliada da Ordem de Ferro |
| Batedor do Peregrino | Tiro de Cobertura | Fortalece aliado mais fraco em outra fileira |
| Piromante da Brasa Errante | Brasa Persistente | Cresce com fileiras inimigas sob clima |
| Guardiã do Selo da Vigília | Selo de Vigília | Proteção climática e suporte local |
| Evocador do Trovão Oco | Descarga Oca | Enfraquece unidades inimigas na fileira |
| Oráculo da Névoa Antiga | Névoa Ancestral | Cresce sob clima ativo |
| Arauto do Sol Negro | Eclipse Devorador | Reage a inimigos com bônus positivo |
| Acólita da Fagulha | Faísca Condutora | Reage à presença de aliados arcanos |
| Guardião do Orbe do Eco | Orbe Refrator | Cresce com especiais no descarte |
| Feiticeira da Chama Fria | Contrafogo | Enfraquece até duas ameaças na fileira |
| Lua Velada | Aliança Lunar | Fortalece a si e um aliado em outra fileira |
| Sentinelas do Véu | Sentinela Compartilhada | Recompensa cobertura das três fileiras |
| Os Últimos Juramentados | Último Juramento | Reage à desvantagem numérica |
| Filhos da Brasa | Herança da Brasa | Fortalece a si e um aliado da Ordem de Ferro |
| Peregrinos da Névoa | Rastro na Névoa | Recompensa alternância de fileira |

## Validação
- Testes unitários dos nove combos existentes.
- Teste de exposição de texto e metadados das 28 habilidades individuais.
- Testes de resolução de efeitos do Guardião das Cinzas e da Dama do Vazio.
- Testes automatizados executados: `python -m unittest discover -s tests -v`.

## Observações
Os efeitos são aplicados no motor do Gwent quando a unidade entra em campo. O equilíbrio competitivo ainda exige partidas de teste com diferentes decks e não deve ser considerado fechado apenas pela aprovação dos testes unitários.
