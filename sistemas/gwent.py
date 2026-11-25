"""Motor estratégico Gwent do NARABOT: regras puras, sem dependência do Discord."""
from __future__ import annotations
from copy import deepcopy

ROWS = ("melee", "ranged", "siege")
AI_PLAYER_ID = -1  # Identidade técnica reservada à NARA; nunca recebe ranking/recompensas.
ROW_LABELS = {"melee": "Corpo a corpo", "ranged": "Longa distância", "siege": "Cerco"}
TYPE_ROW = {"Força": "melee", "Destreza": "ranged", "Magia": "siege"}
FACTIONS = {"Força": "Ordem Áurea", "Destreza": "Véu Carmesim", "Magia": "Lua Negra"}
FACTION_TYPES = {value: key for key, value in FACTIONS.items()}
LEGACY_FACTION_ALIASES = {"Casa Cariana": "Lua Negra", "Lua Sombria": "Lua Negra", "Dinastia Mohgwyn": "Véu Carmesim"}

def canonical_faction(value: str | None) -> str | None:
    """Converte nomes antigos de facção para os nomes atuais sem quebrar decks salvos."""
    if value is None:
        return None
    value = str(value)
    return LEGACY_FACTION_ALIASES.get(value, value)


def embaralhar_deck(deck: list[dict], rng=None) -> list[dict]:
    """Retorna uma cópia embaralhada; produção usa SystemRandom e testes podem injetar RNG."""
    from secrets import SystemRandom
    shuffled = deepcopy(deck)
    (rng or SystemRandom()).shuffle(shuffled)
    return shuffled


def contar_faccoes_deck(cards: list[dict]) -> dict[str, int]:
    """Conta facções das unidades; cartas especiais não definem a facção do deck."""
    counts = {faction: 0 for faction in FACTION_TYPES}
    for card in cards or []:
        if card.get("especial") or str(card.get("categoria", "")).casefold() == "especial":
            continue
        faction = canonical_faction(card.get("faccao"))
        if faction not in FACTION_TYPES:
            faction = FACTIONS.get(str(card.get("tipo", "")))
        if faction in counts:
            counts[faction] += 1
    return counts


def faccoes_predominantes(cards: list[dict]) -> set[str]:
    counts = contar_faccoes_deck(cards)
    highest = max(counts.values(), default=0)
    return {faction for faction, count in counts.items() if count == highest and highest > 0}


def validar_faccao_deck(cards: list[dict], faction: str) -> tuple[bool, dict[str, int]]:
    """A facção declarada deve estar entre as mais representadas nas unidades do deck."""
    normalized = canonical_faction(faction)
    counts = contar_faccoes_deck(cards)
    return normalized in faccoes_predominantes(cards), counts

# Contrato de cobertura: cada habilidade declarada no catálogo precisa estar ligada
# a um ramo do motor (unidade, Primordial ou carta tática especial).
HABILIDADES_UNIDADE_IMPLEMENTADAS = frozenset({
    "",  # Unidade de força pura: não ativa habilidade especial.
    "primeira_luz", "retaliacao", "impeto", "ultimo_folego", "contragolpe",
    "encadeamento", "adaptacao", "sangue_frio", "instinto", "precisao",
    "drenagem", "cacador_arcano", "quebra_ritmo", "lei_primeva",
    "decreto_soberano", "olho_tempestade", "fome_abismo", "paradoxo_eterno",
    "guardiao_fileira", "cacador_solitario", "estandarte", "resistencia_climatica",
    "eco_arcano", "dupla_fornalha", "irmandade_veu", "circulo_arcano",
    # Etapa 1: efeitos de ciclo de vida (escudo, queda, ressurreição, sobrevivência).
    "vinganca", "escudo_ferro", "ressurgir", "devorar", "sobrevivente", "espolios",
})
HABILIDADES_ESPECIAIS_IMPLEMENTADAS = frozenset({
    "gwent_nevoa", "gwent_geada", "gwent_chuva", "gwent_chifre", "gwent_medico",
    "gwent_queima", "gwent_purificar", "gwent_execucao", "gwent_vinculo",
    "gwent_batedor", "gwent_muralha",
    "gwent_egide", "gwent_requiem", "gwent_passo",
    "gwent_sangramento", "gwent_geada_cariana", "gwent_podrida", "gwent_loucura",
    "gwent_chama", "gwent_invocacao",
    "reliquia_godrick", "reliquia_renala", "reliquia_morte", "reliquia_noite_chama", "reliquia_lamina_negra", "reliquia_algemas",
})
FACTION_ARCHETYPES = {
    "Ordem Áurea": {"name": "Formação e Resistência", "description": "Proteção de fileira, fortalecimento de aliados e +1 na primeira unidade da Ordem Áurea jogada em cada rodada."},
    "Lua Negra": {"name": "Feitiçaria e Controle", "description": "Magia lunar, cosmos, gravidade, congelamento e +1 na primeira unidade da Lua Negra jogada em cada rodada."},
    "Véu Carmesim": {"name": "Sangue e Sacrifício", "description": "Sangramento, sacrifício, heresia e +1 na primeira unidade do Véu Carmesim jogada em cada rodada."},
}
LEADERS = {
    # Ordem Áurea — força régia, proteção e purificação.
    "comandante_fornalha": {"name": "Godfrey", "faction": "Ordem Áurea", "description": "Concede +2 de bônus a todas as suas unidades de Corpo a Corpo.", "effect": "godfrey_warlord"},
    "bastiao_ancestral": {"name": "Morgott", "faction": "Ordem Áurea", "description": "Na fileira escolhida, concede Escudo a até 2 aliados mais fortes e +1 de bônus a eles.", "effect": "morgott_omen"},
    "juiz_cerco": {"name": "Radagon", "faction": "Ordem Áurea", "description": "Remove Sangramento, Geada, Podridão e Loucura de todos os aliados; cada aliado purificado recebe +1 de bônus.", "effect": "radagon_purification"},
    # Véu Carmesim — hemorragia, sacrifício e devoção blasfema.
    "mestre_veu": {"name": "Mohg", "faction": "Véu Carmesim", "description": "Aplica uma marca de Sangramento aos 2 inimigos mais fortes da fileira escolhida; uma segunda marca causa Hemorragia (-2 de bônus).", "effect": "mohg_blood_rite"},
    "sombra_caminhante": {"name": "Rykard", "faction": "Véu Carmesim", "description": "Sacrifica seu aliado mais fraco na fileira escolhida; os demais aliados dessa fileira recebem +2 de bônus.", "effect": "rykard_devour"},
    "voz_caidos": {"name": "Esgar", "faction": "Véu Carmesim", "description": "Ressuscita do descarte a unidade mais forte de poder 5 ou menos na fileira escolhida, com +1 de bônus.", "effect": "esgar_blood_priest"},
    # Lua Negra — feitiçaria, gravidade e domínio astral.
    "arquimaga_eclipse": {"name": "Rennala", "faction": "Lua Negra", "description": "Remove Geada e Podridão dos aliados; cada aliado purificado em Cerco recebe +1 de bônus.", "effect": "rennala_full_moon"},
    "mestre_eclipse": {"name": "Astel", "faction": "Lua Negra", "description": "A gravidade atinge os inimigos da fileira escolhida: aplica uma marca de Geada a até 3 unidades mais fortes.", "effect": "astel_gravity"},
    "oraculo_tempestade": {"name": "Loretta", "faction": "Lua Negra", "description": "Concede +2 de bônus às 2 unidades aliadas mais fortes de Longa Distância.", "effect": "loretta_knight"},
}
# Arquétipos e combos nomeados. Os bônus são aplicados uma vez por combo/rodada.
CARD_SYNERGY_TAGS = {
    # Ordem Áurea: resistência, formação e sacrifício.
    "chefe_guardiao_cinzas": {"cinzas", "ordem_dourada"},
    "gwent_unidade_baluarte": {"fornalha", "ordem_dourada"},
    "gwent_unidade_mestre_forja": {"fornalha", "ordem_dourada"},
    "gwent_unidade_portaestandarte": {"fornalha", "estandarte", "ordem_dourada"},
    "covenant_irmandade_ferro": {"estandarte"},
    "chefe_rei_afogado": {"abismo", "sangue_mohgwyn"},
    "covenant_coroa_abismo": {"abismo", "sangue_mohgwyn"},
    "covenant_lobos_cinza": {"cinzas"},
    # Lua Negra: mobilidade, ataques encadeados e caça.
    "chefe_cervo_sombrio": {"veu_sombrio"},
    "chefe_aparicao_veio": {"veu_sombrio"},
    "gwent_unidade_cavaleira": {"veu_sombrio"},
    "gwent_unidade_dupla_veu": {"veu_sombrio", "duas_luas"},
    "arma_duas_luas": {"duas_luas", "lua_cariana"},
    "covenant_lua_velada": {"duas_luas", "lua_cariana"},
    "magia_nevoa_antiga": {"astral", "lua_cariana"},
    "arma_lamina_peregrino": {"peregrino"},
    "arma_arco_peregrino": {"peregrino"},
    "gwent_unidade_cartografa": {"duas_luas"},
    # Véu Carmesim: preparação, marcas e amplificação.
    "chefe_dama_vazio": {"vazio", "lua_cariana"},
    "arma_agulha_astro": {"astral", "lua_cariana"},
    "gwent_unidade_circulo": {"astral"},
    "gwent_unidade_invocador": {"astral"},
    "gwent_unidade_eco": {"astral", "eco"},
    "magia_orbe_eco": {"eco"},
    "magia_brasa_errante": {"chama"},
    "magia_chama_fria": {"chama"},
    # Etapa 2 — Ordem Áurea.
    "gwent_unidade_sentinela_rubra": {"muralha", "ordem_dourada"},
    "gwent_unidade_veterano_cercos": {"muralha"},
    "gwent_unidade_herdeiro_portao": {"muralha", "ordem_dourada"},
    "gwent_unidade_carniceiro_forja": {"banquete", "sangue_mohgwyn"},
    "gwent_unidade_intendente": {"banquete"},
    # Etapa 2 — Lua Negra.
    "gwent_unidade_cacadora_fantasma": {"fantasmas"},
    "gwent_unidade_cantora_lamentos": {"fantasmas"},
    "gwent_unidade_senhor_cacada": {"fantasmas"},
    "gwent_unidade_saqueadora_veu": {"caravana"},
    "gwent_unidade_contrabandista": {"caravana"},
    # Etapa 2 — Véu Carmesim.
    "gwent_unidade_guardiao_runas": {"runico"},
    "gwent_unidade_necromante": {"runico"},
    "gwent_unidade_detonador": {"runico"},
    "gwent_unidade_devorador_mana": {"eclipse_voraz", "sangue_mohgwyn"},
    "gwent_unidade_bibliotecaria": {"eclipse_voraz"},
    # Expansão V75 — duas metades de cada combo de facção.
    "gwent_v75_ordem_veterano_juramento": {"v75_erdtree_oath"},
    "gwent_v75_ordem_guardiao_crisol": {"v75_crucible_guard"},
    "gwent_v75_ordem_confessora_graca": {"v75_erdtree_oath"},
    "gwent_v75_ordem_arauto_estandarte": {"v75_crucible_guard"},
    "gwent_v75_veu_acolito_sangue": {"v75_blood_mark"},
    "gwent_v75_veu_devota_hemorragia": {"v75_blood_feast"},
    "gwent_v75_veu_carrasco_preco": {"v75_blood_feast"},
    "gwent_v75_veu_cacador_sangue": {"v75_blood_mark"},
    "gwent_v75_lua_oraculo_geada": {"v75_frost_lore"},
    "gwent_v75_lua_cartografo_lunar": {"v75_lunar_paths"},
    "gwent_v75_lua_graviturgista": {"v75_frost_lore"},
    "gwent_v75_lua_guardia": {"v75_lunar_paths"},
}
SYNERGY_COMBOS = {
    "cinzas_fornalha": {"name": "Aliança da Árvore Áurea", "tags": {"cinzas", "fornalha"}, "bonus": 2, "description": "Cavaleiro da Árvore Áurea ou Cavaleiros de Radahn e uma unidade da Fornalha coordenam a formação (+2)."},
    "veu_sombrio": {"name": "Caçada da Faca Negra", "tags": {"veu_sombrio"}, "minimum": 2, "bonus": 2, "description": "Duas unidades do Véu Sombrio entram em sintonia (+2)."},
    "vazio_astral": {"name": "Alinhamento Astral", "tags": {"vazio", "astral"}, "bonus": 2, "description": "Ranni e uma unidade Astral convergem (+2)."},
    "mare_abissal": {"name": "Maré Abissal", "tags": {"abismo"}, "minimum": 2, "bonus": 2, "description": "Godfrey e Cavaleiro Carmesim despertam a mesma força (+2)."},
    "juramento_estandarte": {"name": "Juramento de Leyndell", "tags": {"estandarte"}, "minimum": 2, "bonus": 1, "team_bonus": 1, "description": "Porta-estandarte e Guardas da Árvore Áurea fortalecem a formação (+1 para a carta que completa e +1 aos aliados na mesma fileira)."},
    "passos_duas_luas": {"name": "Dança da Lua Negra", "tags": {"duas_luas"}, "minimum": 2, "bonus": 2, "description": "Dançarina, Gêmea ou Cartógrafa sincronizam seus movimentos (+2)."},
    "eco_convergente": {"name": "Eco das Pedras Cintilantes", "tags": {"eco", "astral"}, "bonus": 2, "description": "O Erudito das Pedras Cintilantes e uma unidade Astral amplificam a mesma magia (+2)."},
    "chama_dupla": {"name": "Chamas do Monte Gelmir", "tags": {"chama"}, "minimum": 2, "bonus": 2, "description": "Piromante e Feiticeira da Lua Gélida equilibram suas chamas (+2)."},
    "muralha_inabalavel": {"name": "Defesa de Leyndell", "tags": {"muralha"}, "minimum": 2, "bonus": 2, "team_bonus": 1, "description": "Duas unidades da Muralha Rubra erguem a linha (+2 para a carta que completa e +1 aos aliados na fileira)."},
    "banquete_guerra": {"name": "Banquete de Sangue", "tags": {"banquete"}, "minimum": 2, "bonus": 3, "description": "Carniceiro da Forja e Intendente dividem o butim (+3)."},
    "procissao_fantasma": {"name": "Procissão dos que Vivem na Morte", "tags": {"fantasmas"}, "minimum": 2, "bonus": 2, "team_bonus": 1, "description": "Duas unidades fantasmas marcham juntas (+2 para a carta que completa e +1 aos aliados na fileira)."},
    "caravana_saqueadora": {"name": "Saque da Cidade Eterna", "tags": {"caravana"}, "minimum": 2, "bonus": 2, "description": "Saqueadora e Contrabandista fecham o negócio (+2)."},
    "ritual_runico": {"name": "Ritual das Runas", "tags": {"runico"}, "minimum": 2, "bonus": 2, "team_bonus": 1, "description": "Duas unidades rúnicas completam o círculo (+2 para a carta que completa e +1 aos aliados na fileira)."},
    "eclipse_voraz": {"name": "Eclipse Sanguíneo", "tags": {"eclipse_voraz"}, "minimum": 2, "bonus": 3, "description": "Cavaleiro de Sangue de Mohg e Bibliotecária eclipsam a mesma fonte (+3)."},
    "rota_peregrina": {"name": "Caminho do Maculado", "tags": {"peregrino"}, "minimum": 2, "bonus": 1, "description": "Duelista e Batedor da Mansão Vulcânica coordenam o avanço (+1)."},
    "juramento_erdtree": {"name": "Juramento da Árvore Áurea", "tags": {"ordem_dourada"}, "minimum": 2, "bonus": 2, "team_bonus": 1, "description": "Duas unidades da Ordem Áurea reforçam a formação: +2 para quem completa o combo e +1 aos aliados da mesma fileira."},
    "convergencia_lunar": {"name": "Convergência da Lua Negra", "tags": {"lua_cariana"}, "minimum": 2, "bonus": 2, "description": "Duas unidades ligadas à Lua Negra convergem e recebem +2."},
    "ritual_dinastia": {"name": "Ritual do Véu Carmesim", "tags": {"sangue_mohgwyn"}, "minimum": 2, "bonus": 2, "team_bonus": 1, "description": "Duas unidades do Véu Carmesim fortalecem a carta que completa o ritual (+2) e os aliados na fileira (+1)."},
    # Novos combos V75: exigem duas cartas e duas tags distintas; uma ativação por rodada.
    "v75_juramento_dois_crisol": {"name": "Juramento do Crisol e da Graça", "tags": {"v75_erdtree_oath", "v75_crucible_guard"}, "minimum": 2, "bonus": 2, "description": "Formação e proteção convergem: a carta que completa o juramento recebe +2."},
    "v75_banquete_hemorragia": {"name": "Banquete da Hemorragia", "tags": {"v75_blood_mark", "v75_blood_feast"}, "minimum": 2, "bonus": 2, "description": "Uma marca aberta alimenta o ritual: a carta que completa o combo recebe +2."},
    "v75_convergencia_gelida": {"name": "Convergência da Geada Lunar", "tags": {"v75_frost_lore", "v75_lunar_paths"}, "minimum": 2, "bonus": 2, "description": "Geada e leitura das fileiras entram em ressonância: a carta que completa o combo recebe +2."},
}


# Habilidades de identidade: efeitos próprios de cartas-chave, além das habilidades
# gerais e dos combos de facção. Cada efeito é resolvido uma vez ao entrar em campo.
CARD_IDENTITY_ABILITIES = {
    "chefe_guardiao_cinzas": {"name": "Égide das Cinzas", "text": "Ao entrar em campo, dá +1 de bônus a um aliado da mesma fileira. Se já houver um aliado nessa fileira, esta carta também ganha +1.", "effect": "ash_guardian"},
    "chefe_dama_vazio": {"name": "Fenda do Vazio", "text": "Ao entrar em campo, tira 2 pontos de bônus da unidade inimiga mais forte. O bônus dela não pode ficar abaixo de -2.", "effect": "void_rend"},
    "chefe_cervo_sombrio": {"name": "Passagem Sombria", "text": "Ganha +1 para cada outra fileira que tenha um aliado seu, até +2.", "effect": "shadow_paths"},
    "chefe_rei_afogado": {"name": "Dízimo do Abismo", "text": "Ganha +2 se você tiver uma unidade no descarte. Se não tiver, ganha +1 caso o adversário tenha mais unidades em campo.", "effect": "abyss_tithe"},
    "chefe_oraculo_ruina": {"name": "Presságio da Ruína", "text": "Tira 1 ponto de bônus da unidade inimiga mais forte. Também ganha +1 se o adversário estiver vencendo.", "effect": "ruin_omen"},
    "chefe_cacador_sem_rosto": {"name": "Marca da Presa", "text": "Ganha +2 se o adversário tiver uma unidade com poder atual maior que o poder-base desta carta.", "effect": "faceless_hunt"},
    "chefe_vigia_cinzento": {"name": "Vigília Cinzenta", "text": "Dá +1 de bônus a todos os seus outros aliados na mesma fileira.", "effect": "grey_watch"},
    "chefe_aparicao_veio": {"name": "Deslocamento Espectral", "text": "Ganha +2 se sua unidade anterior foi jogada em outra fileira.", "effect": "veil_shift"},
    "arma_lamina_peregrino": {"name": "Duelo do Peregrino", "text": "Ganha +2 se o adversário jogou uma unidade na mesma fileira no turno anterior.", "effect": "pilgrim_duel"},
    "arma_martelo_fornalha": {"name": "Martelo de Cadência", "text": "Ganha +1 para cada aliado da Ordem Áurea na mesma fileira, até +2.", "effect": "forge_rhythm"},
    "arma_cajado_marulho": {"name": "Ressonância das Marés", "text": "Ganha +2 se o adversário tiver uma unidade do Véu Carmesim. Caso contrário, ganha +1 se ele tiver mais unidades em campo.", "effect": "tide_resonance"},
    "arma_duas_luas": {"name": "Dança Espelhada", "text": "Ganha +1 se você tiver outro aliado em uma fileira diferente.", "effect": "twin_dance"},
    "arma_grande_sino": {"name": "Sino do Último Bastião", "text": "Ganha +2 quando sua pontuação total for menor que a do adversário.", "effect": "last_bell"},
    "arma_agulha_astro": {"name": "Fio Astral", "text": "Marca o inimigo mais forte e tira 1 ponto de bônus dele. A próxima unidade Astral que você jogar ganha +1 nesta rodada.", "effect": "astral_thread"},
    "arma_lanca_fornalha": {"name": "Investida da Fornalha", "text": "Ganha +1 se já houver outra unidade da Ordem Áurea em campo.", "effect": "furnace_charge"},
    "arma_arco_peregrino": {"name": "Tiro de Cobertura", "text": "Dá +1 de bônus ao seu aliado mais fraco que esteja em outra fileira.", "effect": "covering_shot"},
    "magia_brasa_errante": {"name": "Brasa Persistente", "text": "Ganha +1 para cada fileira que tenha inimigos e esteja sob efeito climático, até +2.", "effect": "wandering_ember"},
    "magia_selo_vigilia": {"name": "Selo de Vigília", "text": "Reduz em 1 o dano do clima sofrido por esta carta e dá +1 de bônus a um aliado da mesma fileira.", "effect": "vigil_seal"},
    "magia_trovao_oco": {"name": "Descarga Oca", "text": "Tira 1 ponto de bônus de cada unidade inimiga na mesma fileira.", "effect": "hollow_thunder"},
    "magia_nevoa_antiga": {"name": "Névoa Ancestral", "text": "Ganha +2 se houver efeito climático em qualquer fileira.", "effect": "ancient_mist"},
    "magia_sol_negro": {"name": "Eclipse Devorador", "text": "Ganha +2 se algum inimigo tiver bônus acima de zero.", "effect": "devouring_eclipse"},
    "magia_fagulha": {"name": "Faísca Condutora", "text": "Ganha +1 se houver outra unidade da Lua Negra do seu lado do campo.", "effect": "conductive_spark"},
    "magia_orbe_eco": {"name": "Orbe Refrator", "text": "Ganha +1 para cada carta especial no seu descarte, até +2.", "effect": "echo_orb"},
    "magia_chama_fria": {"name": "Contrafogo", "text": "Tira 1 ponto de bônus de até dois inimigos na mesma fileira.", "effect": "counterflame"},
    "covenant_lua_velada": {"name": "Aliança Lunar", "text": "Esta carta ganha +1 e dá +1 de bônus a um aliado em outra fileira.", "effect": "veiled_moon"},
    "covenant_sentinelas": {"name": "Sentinela Compartilhada", "text": "Ganha +1 se você tiver pelo menos um aliado em cada uma das outras duas fileiras.", "effect": "shared_sentinel"},
    "covenant_ultimos": {"name": "Último Juramento", "text": "Ganha +2 se você tiver menos unidades em campo que o adversário.", "effect": "last_oath"},
    "covenant_filhos_brasa": {"name": "Herança da Brasa", "text": "Esta carta ganha +1 e dá +1 de bônus a um aliado da Ordem Áurea na mesma fileira.", "effect": "ember_kin"},
    "covenant_peregrinos_nevoa": {"name": "Rastro na Névoa", "text": "Ganha +1 se sua unidade anterior foi jogada em outra fileira.", "effect": "mist_trail"},
    "chefe_malenia_lamina_miquella": {"name": "Flor Escarlate", "text": "Ao entrar em campo, aplica Podridão Escarlate aos inimigos da fileira. Quem já estiver contaminado recebe uma segunda marca.", "effect": "scarlet_bloom"},
    "chefe_radahn_flagelo_estrelas": {"name": "Gravidade do Flagelo", "text": "Ao entrar em campo, move o inimigo mais forte para sua fileira e tira 2 pontos de bônus dele.", "effect": "star_gravity"},
    "chefe_maliketh_morte_destinada": {"name": "Morte Destinada", "text": "Ao entrar em campo, tira até 2 pontos de bônus do inimigo mais forte.", "effect": "destined_death"},
    "chefe_messmer_impalador": {"name": "Lança do Impalador", "text": "Ao entrar em campo, marca os inimigos da fileira com Sangramento. A segunda marca causa Hemorragia.", "effect": "impaling_spear"},
    "chefe_placidusax_lorde_dragao": {"name": "Tempestade do Tempo", "text": "Ao entrar em campo, aplica Geada aos inimigos da fileira e ganha +1 para cada inimigo atingido, até +3.", "effect": "time_storm"},
    # Expansão V75 — efeitos individuais das doze novas unidades.
    "gwent_v75_ordem_veterano_juramento": {"name": "Juramento Dourado", "text": "Ao entrar, recebe +1; se houver aliado na mesma fileira, o aliado mais fraco também recebe +1.", "effect": "v75_golden_vow"},
    "gwent_v75_ordem_confessora_graca": {"name": "Regressão Serena", "text": "Purifica até dois aliados da mesma fileira de estados negativos; cada aliado purificado recebe +1. Se ninguém precisar de purificação, fortalece o aliado mais fraco em +1.", "effect": "v75_grace_mender"},
    "gwent_v75_veu_acolito_sangue": {"name": "Marca da Dinastia", "text": "Aplica uma marca de Sangramento ao inimigo mais forte da fileira; a segunda marca provoca Hemorragia e reduz 2 de bônus.", "effect": "v75_blood_mark"},
    "gwent_v75_veu_carrasco_preco": {"name": "Preço em Sangue", "text": "Sacrifica o aliado mais fraco da mesma fileira e recebe bônus igual ao seu poder efetivo, até +3; sem aliado, recebe +1.", "effect": "v75_blood_price"},
    "gwent_v75_lua_oraculo_geada": {"name": "Presságio da Geada", "text": "Aplica uma marca de Geada ao inimigo mais forte da fileira; se já tinha uma marca, completa a segunda e recebe +1.", "effect": "v75_frost_oracle"},
    "gwent_v75_lua_graviturgista": {"name": "Cisalhamento Gravitacional", "text": "Reduz em 1 o bônus de até dois inimigos com bônus positivo na fileira; se atingir dois, recebe +1.", "effect": "v75_gravity_shear"},
}


# Cartas V18 de força pura não mantêm efeitos de identidade ocultos.
from sistemas.cartas import CARTAS_SEM_EFEITO_IDS as _CARTAS_SEM_EFEITO_IDS
CARD_IDENTITY_ABILITIES = {k: v for k, v in CARD_IDENTITY_ABILITIES.items() if k not in _CARTAS_SEM_EFEITO_IDS}

def _aplicar_habilidade_identidade(player: dict, other: dict, card: dict, state: dict, row: str) -> str | None:
    data = CARD_IDENTITY_ABILITIES.get(str(card.get("id", "")))
    if not data:
        return None
    effect = data["effect"]
    allies, enemies = player.get("board", []), other.get("board", [])
    same_row = [unit for unit in allies if unit.get("row") == row]
    enemy_row = [unit for unit in enemies if unit.get("row") == row]
    weather = state.get("weather", {})
    strongest = max(enemies, key=lambda unit: _poder_efetivo(unit, weather), default=None)
    weakest_other_row = min((u for u in allies if u.get("row") != row), key=lambda u: _poder_efetivo(u, weather), default=None)
    if effect == "ash_guardian":
        if same_row:
            same_row[0]["bonus"] = int(same_row[0].get("bonus", 0)) + 1
            card["bonus"] += 1
    elif effect == "void_rend" and strongest:
        strongest["bonus"] = max(-2, int(strongest.get("bonus", 0)) - 2)
    elif effect == "shadow_paths":
        card["bonus"] += min(2, len({u.get("row") for u in allies if u.get("row") != row}))
    elif effect == "abyss_tithe":
        card["bonus"] += 2 if player.get("discard") else (1 if len(enemies) > len(allies) else 0)
    elif effect == "ruin_omen":
        if strongest:
            strongest["bonus"] = max(-2, int(strongest.get("bonus", 0)) - 1)
        if pontuacao(player, state.get("weather")) < pontuacao(other, state.get("weather")):
            card["bonus"] += 1
    elif effect == "faceless_hunt":
        if any(_poder_efetivo(u, weather) > int(card.get("poder", 0)) for u in enemies): card["bonus"] += 2
    elif effect == "grey_watch":
        for unit in same_row: unit["bonus"] = int(unit.get("bonus", 0)) + 1
    elif effect == "veil_shift":
        if player.get("last_row") is not None and player.get("last_row") != row: card["bonus"] += 2
    elif effect == "pilgrim_duel":
        if other.get("last_row") == row: card["bonus"] += 2
    elif effect == "forge_rhythm":
        card["bonus"] += min(2, sum(1 for u in allies if canonical_faction(u.get("faccao") or FACTIONS.get(str(u.get("tipo", "")))) == "Ordem Áurea" and u.get("row") == row))
    elif effect == "tide_resonance":
        if any(canonical_faction(u.get("faccao") or FACTIONS.get(str(u.get("tipo", "")))) == "Véu Carmesim" for u in enemies):
            card["bonus"] += 2
        elif len(enemies) > len(allies):  # Etapa 3: alternativa contra facções que não são o Conclave.
            card["bonus"] += 1
    elif effect == "twin_dance":
        if any(u.get("row") != row for u in allies): card["bonus"] += 1
    elif effect == "last_bell":
        if pontuacao(player, state.get("weather")) < pontuacao(other, state.get("weather")): card["bonus"] += 2
    elif effect == "astral_thread":
        if strongest: strongest["bonus"] = max(-2, int(strongest.get("bonus", 0)) - 1)
        player["astral_thread_ready"] = True
    elif effect == "furnace_charge":
        if any(canonical_faction(u.get("faccao") or FACTIONS.get(str(u.get("tipo", "")))) == "Ordem Áurea" for u in allies): card["bonus"] += 1
    elif effect == "covering_shot" and weakest_other_row:
        weakest_other_row["bonus"] = int(weakest_other_row.get("bonus", 0)) + 1
    elif effect == "wandering_ember":
        card["bonus"] += min(2, sum(1 for r in ROWS if int(weather.get(r, 0)) > 0 and any(u.get("row") == r for u in enemies)))
    elif effect == "vigil_seal":
        card["weather_resist"] = 1
        if same_row: same_row[0]["bonus"] = int(same_row[0].get("bonus", 0)) + 1
    elif effect == "hollow_thunder":
        for unit in enemy_row: unit["bonus"] = max(-2, int(unit.get("bonus", 0)) - 1)
    elif effect == "ancient_mist":
        if any(int(v or 0) > 0 for v in state.get("weather", {}).values()): card["bonus"] += 2
    elif effect == "devouring_eclipse":
        if any(int(u.get("bonus", 0)) > 0 for u in enemies): card["bonus"] += 2
    elif effect == "conductive_spark":
        if any(canonical_faction(u.get("faccao") or FACTIONS.get(str(u.get("tipo", "")))) == "Lua Negra" for u in allies): card["bonus"] += 1
    elif effect == "echo_orb":
        card["bonus"] += min(2, sum(1 for c in player.get("discard", []) if c.get("especial")))
    elif effect == "counterflame":
        for unit in sorted(enemy_row, key=lambda u: int(u.get("bonus", 0)), reverse=True)[:2]:
            unit["bonus"] = max(-2, int(unit.get("bonus", 0)) - 1)
    elif effect == "veiled_moon":
        card["bonus"] += 1
        if weakest_other_row: weakest_other_row["bonus"] = int(weakest_other_row.get("bonus", 0)) + 1
    elif effect == "shared_sentinel":
        occupied = {u.get("row") for u in allies}
        if all(r == row or r in occupied for r in ROWS): card["bonus"] += 1
    elif effect == "last_oath":
        if len(allies) < len(enemies): card["bonus"] += 2
    elif effect == "ember_kin":
        card["bonus"] += 1
        ally = next((u for u in same_row if canonical_faction(u.get("faccao") or FACTIONS.get(str(u.get("tipo", "")))) == "Ordem Áurea"), None)
        if ally: ally["bonus"] = int(ally.get("bonus", 0)) + 1
    elif effect == "mist_trail":
        if player.get("last_row") is not None and player.get("last_row") != row: card["bonus"] += 1
    elif effect == "scarlet_bloom":
        for unit in enemy_row:
            marks = int(unit.get("podrida", 0))
            unit["podrida"] = min(2, marks + (2 if marks else 1))
            if unit["podrida"] >= 2 and int(unit.get("bonus", 0)) > 0:
                unit["bonus"] = max(0, int(unit.get("bonus", 0)) - 1)
    elif effect == "star_gravity" and strongest:
        strongest["row"] = row
        strongest["bonus"] = max(-2, int(strongest.get("bonus", 0)) - 2)
    elif effect == "destined_death" and strongest:
        strongest["bonus"] = max(-2, int(strongest.get("bonus", 0)) - 2)
    elif effect == "impaling_spear":
        for unit in enemy_row:
            unit["sangramento"] = int(unit.get("sangramento", 0)) + 1
            if unit["sangramento"] >= 2:
                unit["bonus"] = max(-2, int(unit.get("bonus", 0)) - 2)
                unit["sangramento"] = 0
    elif effect == "time_storm":
        atingidos = 0
        for unit in enemy_row:
            unit["geada"] = min(2, int(unit.get("geada", 0)) + 1)
            atingidos += 1
        card["bonus"] += min(3, atingidos)
    elif effect == "v75_golden_vow":
        card["bonus"] += 1
        ally = min(same_row, key=lambda u: _poder_efetivo(u, weather), default=None)
        if ally:
            ally["bonus"] = int(ally.get("bonus", 0)) + 1
    elif effect == "v75_crucible_guard":
        target = min((u for u in same_row if int(u.get("escudo", 0)) <= 0),
                     key=lambda u: _poder_efetivo(u, weather), default=None)
        if target is not None:
            target["escudo"] = 1
        else:
            card["escudo"] = 1
    elif effect == "v75_grace_mender":
        status_keys = ("sangramento", "geada", "podrida", "loucura")
        targets = sorted((u for u in same_row if any(int(u.get(k, 0)) > 0 for k in status_keys)),
                         key=lambda u: _poder_efetivo(u, weather))[:2]
        for target in targets:
            for key in status_keys:
                target[key] = 0
            target["bonus"] = int(target.get("bonus", 0)) + 1
        if not targets:
            target = min(same_row, key=lambda u: _poder_efetivo(u, weather), default=None)
            if target:
                target["bonus"] = int(target.get("bonus", 0)) + 1
            else:
                card["bonus"] += 1
    elif effect == "v75_golden_standard":
        occupied_rows = {u.get("row") for u in allies}
        if len(occupied_rows | {row}) >= 2:
            card["bonus"] += 1
            for target in same_row[:2]:
                target["bonus"] = int(target.get("bonus", 0)) + 1
    elif effect == "v75_blood_mark":
        target = max(enemy_row, key=lambda u: _poder_efetivo(u, weather), default=None)
        if target:
            marks = int(target.get("sangramento", 0)) + 1
            if marks >= 2:
                target["sangramento"] = 0
                target["bonus"] = max(-2, int(target.get("bonus", 0)) - 2)
                card["bonus"] += 1
            else:
                target["sangramento"] = marks
    elif effect == "v75_blood_feast":
        card["bonus"] += min(2, sum(1 for u in enemies if int(u.get("sangramento", 0)) > 0))
    elif effect == "v75_blood_price":
        victim = min(same_row, key=lambda u: _poder_efetivo(u, weather), default=None)
        if victim is not None:
            gain = min(3, max(1, _poder_efetivo(victim, weather)))
            _remover_unidade(player, victim, "sacrificio")
            card["bonus"] += gain
        else:
            card["bonus"] += 1
    elif effect == "v75_blood_pursuit":
        target = max((u for u in enemy_row if int(u.get("sangramento", 0)) > 0),
                     key=lambda u: _poder_efetivo(u, weather), default=None)
        if target:
            target["bonus"] = max(-2, int(target.get("bonus", 0)) - 1)
            card["bonus"] += 1
    elif effect == "v75_frost_oracle":
        target = max(enemy_row, key=lambda u: _poder_efetivo(u, weather), default=None)
        if target:
            old_marks = int(target.get("geada", 0))
            target["geada"] = min(2, old_marks + 1)
            if old_marks >= 1:
                card["bonus"] += 1
    elif effect == "v75_lunar_cartography":
        occupied = {u.get("row") for u in allies if u.get("row") != row}
        card["bonus"] += min(2, len(occupied))
    elif effect == "v75_gravity_shear":
        targets = sorted((u for u in enemy_row if int(u.get("bonus", 0)) > 0),
                         key=lambda u: int(u.get("bonus", 0)), reverse=True)[:2]
        for target in targets:
            target["bonus"] = max(-2, int(target.get("bonus", 0)) - 1)
        if len(targets) == 2:
            card["bonus"] += 1
    elif effect == "v75_moon_ward":
        target = min((u for u in allies if u.get("row") != row and int(u.get("escudo", 0)) <= 0),
                     key=lambda u: _poder_efetivo(u, weather), default=None)
        if target is not None:
            target["escudo"] = 1
        else:
            card["escudo"] = 1
        if any(int(u.get("geada", 0)) > 0 for u in enemy_row):
            card["bonus"] += 1
    return str(data["name"])


# Passiva de facção: a primeira unidade da própria facção recebe +1 por rodada.
FACTION_BOOST = {"Ordem Áurea": 1, "Lua Negra": 1, "Véu Carmesim": 1}

DEFAULT_LEADERS = {
    "Ordem Áurea": "comandante_fornalha",
    "Lua Negra": "arquimaga_eclipse",
    "Véu Carmesim": "mestre_veu",  # Etapa 3: padrão mais forte; quem já escolheu um líder não é afetado.
}


# Potência adicional por raridade. O bônus é um orçamento por ativação:
# é distribuído entre os alvos que a habilidade já afetou, sem criar alvos novos.
RARITY_EFFECT_BUDGET = {
    # Curva com retornos decrescentes: raridade já eleva poder-base.
    # O teto de 3 evita que raridades altas dupliquem a vantagem em efeitos.
    # Estes pontos ampliam habilidades; nunca são somados ao poder-base.
    "Comum": 0, "Rara": 1, "Épica": 1, "Lendária": 2,
    "Mítica": 2, "Primordial": 3, "Singular": 3,
}


def _aplicar_potencia_raridade(card: dict, player: dict, other: dict,
                                bonus_antes: dict[int, int],
                                bonus_card_antes: int = 0) -> int:
    """Amplia buffs/debuffs numéricos já produzidos pela habilidade, com teto por carta.

    Não aumenta poder-base, não cria alvos e não altera custos, duração, compra,
    invocação, escudos ou condições. O orçamento segue o nível exclusivo
    da raridade e respeita o teto individual de cada alvo/efeito.
    """
    budget = int(RARITY_EFFECT_BUDGET.get(str(card.get("raridade", "Comum")), 0))
    if budget <= 0:
        return 0
    changes: list[tuple[dict, int]] = []
    card_delta = int(card.get("bonus", 0)) - int(bonus_card_antes)
    if card_delta:
        changes.append((card, card_delta))
    for side in (player, other):
        for unit in side.get("board", []):
            old = bonus_antes.get(id(unit))
            if old is None:
                continue
            delta = int(unit.get("bonus", 0)) - int(old)
            if delta:
                changes.append((unit, delta))
    applied = 0
    for target, delta in changes:
        if applied >= budget:
            break
        if delta > 0:
            target["bonus"] = int(target.get("bonus", 0)) + 1
        else:
            target["bonus"] = max(-2, int(target.get("bonus", 0)) - 1)
        applied += 1
    return applied


def preparar_carta(card: dict) -> dict:
    special = str(card.get("categoria", "")).casefold() == "especial"
    skill = str(card.get("habilidade", ""))
    try:
        from sistemas.cartas import HABILIDADES
        skill_data = HABILIDADES.get(skill, {})
    except Exception:
        skill_data = {}
    row = str(card.get("fileira") or TYPE_ROW.get(str(card.get("tipo", "")), "melee"))
    if row not in ROWS:
        row = TYPE_ROW.get(str(card.get("tipo", "")), "melee")
    kind = str(card.get("tipo", "Força"))
    faction = str(card.get("faccao") or FACTIONS.get(kind, "Ordem Áurea"))
    category = "Especial" if special else "Unidade"
    identity = CARD_IDENTITY_ABILITIES.get(str(card["id"]), {})
    raridade = str(card.get("raridade", "Comum"))
    # Sem habilidade, só recebe orçamento se puder completar um combo registrado.
    has_synergy = bool(CARD_SYNERGY_TAGS.get(str(card.get("id", "")), set()))
    # Relíquias possuem potência fixa no próprio texto do item; a raridade não
    # acrescenta modificadores ocultos como ocorre com cartas especiais comuns.
    budget = (0 if skill.startswith("reliquia_") else
              int(RARITY_EFFECT_BUDGET.get(raridade, 0)) if (skill or identity or has_synergy) else 0)
    # Lore (descricao) nunca deve ser usada como fallback de regra mecânica.
    # Isso evita que frases narrativas sejam exibidas como se fossem efeitos de combate.
    textos_habilidade = []
    if identity.get("text"):
        textos_habilidade.append(str(identity["text"]))
    if skill_data.get("texto") and identity:
        textos_habilidade.append(f"Habilidade adicional: {skill_data['texto']}")
    elif not identity and card.get("habilidade_texto"):
        textos_habilidade.append(str(card["habilidade_texto"]))
    elif not identity and skill_data.get("texto"):
        textos_habilidade.append(str(skill_data["texto"]))
    texto_habilidade = str(" ".join(textos_habilidade) or "Sem habilidade especial.")[:420]
    if budget:
        quantidade_alteracoes = "alteração" if budget == 1 else "alterações"
        upgrades = {
            "gwent_nevoa": f" Raridade {raridade}: pode aplicar uma segunda marca de Podridão Escarlate.",
            "gwent_chuva": " Aplica Sangramento às unidades inimigas da fileira de Cerco; a segunda marca provoca Hemorragia.",
            "gwent_geada": f" Raridade {raridade}: pode aplicar uma segunda marca de Geada.",
            "gwent_medico": f" Raridade {raridade}: recupera unidade com poder-base até {min(8, 4 + budget)}.",
            "gwent_execucao": f" Raridade {raridade}: alcança poder efetivo até {min(6, 6 + budget)}.",
            "gwent_requiem": f" Raridade {raridade}: recupera unidade com poder-base até {min(10, 6 + budget)}.",
            "gwent_batedor": f" Raridade {raridade}: compra até {min(2, 1 + budget)} cartas.",
            "gwent_invocacao": f" Raridade {raridade}: invoca lobos com {min(6, 3 + budget)} de poder.",
            "gwent_egide": f" Raridade {raridade}: protege até {min(3, 1 + budget)} unidades.",
            "gwent_passo": f" Raridade {raridade}: move até {min(3, 1 + budget)} unidades.",
            "gwent_sangramento": f" Raridade {raridade}: aplica uma marca extra a até {min(3, budget)} alvo(s), podendo ativar hemorragia imediatamente.",
            "gwent_geada_cariana": f" Raridade {raridade}: aplica uma segunda marca a até {min(3, budget)} alvo(s).",
            "gwent_queima": "",
            "gwent_purificar": "",
            "gwent_podrida": f" Raridade {raridade}: pode aplicar a segunda marca imediatamente a até {min(3, budget)} alvo(s).",
            "gwent_loucura": f" Raridade {raridade}: pode aplicar a segunda marca imediatamente a até {min(3, budget)} alvo(s).",
        }
        if skill in {"gwent_nevoa", "gwent_geada"}:
            # Esses dois efeitos globais só aplicam a segunda marca a partir
            # do orçamento 2 (Lendária+), não em Rara/Épica.
            if budget >= 2:
                label = "Podridão Escarlate" if skill == "gwent_nevoa" else "Geada"
                texto_habilidade = (texto_habilidade + f" Raridade {raridade}: aplica a segunda marca de {label} a todas as unidades elegíveis da fileira/campo afetado.").strip()
        elif skill in upgrades:
            texto_habilidade = (texto_habilidade + upgrades[skill]).strip()
        elif skill:
            texto_habilidade = (texto_habilidade + f" Raridade {raridade}: reforça até {budget} bônus já alterados pela habilidade: +1 nos positivos ou -1 nos negativos. Não muda o poder inicial nem os escudos.").strip()
        elif identity:
            texto_habilidade = (texto_habilidade + f" Raridade {raridade}: reforça até {budget} bônus já alterados pela habilidade: +1 nos positivos ou -1 nos negativos. Não muda o poder inicial nem os escudos.").strip()
        elif has_synergy:
            texto_habilidade = (texto_habilidade + f" Raridade {raridade}: ao completar combo compatível, reforça até {budget} bônus já alterados: +1 nos positivos ou -1 nos negativos.").strip()
    return {
        "id": str(card["id"]), "nome": str(card.get("nome", "Carta")),
        "categoria": category,
        "papel_gwent": str(card.get("papel_gwent", "Tática" if special else ROW_LABELS[row])),
        "especial": special,
        "poder": 0 if special else max(1, min(15, int(card.get("poder", 1)))),
        "raridade": raridade, "potencia_raridade": budget, "tipo": kind,
        "faccao": faction,
        "arquetipo_faccao": FACTION_ARCHETYPES.get(faction, {}).get("name", "Estratégia Geral"),
        "arquetipo_descricao": FACTION_ARCHETYPES.get(faction, {}).get("description", ""),
        "fileira": row,
        "row": row, "row_label": ROW_LABELS[row], "habilidade": skill,
        "habilidade_nome": str(
            f"{identity['name']} + {skill_data['nome']}" if identity and skill_data.get("nome")
            else identity.get("name", card.get("habilidade_nome", skill_data.get("nome", skill.replace("_", " ").title())))
        ),
        "habilidade_texto": texto_habilidade,
        "habilidade_identidade": bool(identity),
        "sinergias": sorted(CARD_SYNERGY_TAGS.get(str(card["id"]), set())),
        "combos_compativeis": [
            {"id": combo_id, "nome": combo["name"], "descricao": combo["description"]}
            for combo_id, combo in SYNERGY_COMBOS.items()
            if CARD_SYNERGY_TAGS.get(str(card["id"]), set()) & set(combo["tags"])
        ],
        "descricao": str(card.get("descricao", ""))[:240],
        "image_url": f"/api/gwent/cards/{card['id']}/image",
    }



def preparar_carta_pessoal(definition: dict, exemplar: dict, *, owner_id: int | None = None) -> dict | None:
    """Prepara uma carta publicada pelo Laboratório para o mesmo motor de batalha.

    A autorização do proprietário é responsabilidade da camada de persistência;
    esta função valida apenas a definição e o exemplar já resolvidos pelo servidor.
    """
    if not isinstance(definition, dict) or not isinstance(exemplar, dict):
        return None
    card_id = str(definition.get("card_id") or "")
    if (not card_id.startswith("transmutacao_") or len(card_id) > 120
            or definition.get("origem_tipo") != "transmutacao"
            or definition.get("owner_scoped") is not True
            or definition.get("is_sacrificable") is not False
            or definition.get("categoria") != "Unidade"):
        return None
    # Quando a camada de persistência fornece os metadados do exemplar,
    # revalidamos a identidade e a proteção também no limite do motor.
    if exemplar.get("card_id") not in (None, "", card_id):
        return None
    if exemplar.get("origin_type") not in (None, "", "transmutacao"):
        return None
    if exemplar.get("is_sacrificable") not in (None, 0, False):
        return None
    if owner_id is not None:
        try:
            if int(exemplar.get("user_id", -1)) != int(owner_id):
                return None
        except (TypeError, ValueError):
            return None
    from sistemas.gerador_cartas import validar_definicao_gerada
    from sistemas.cartas import FAIXA_PODER
    valid, _errors = validar_definicao_gerada(definition)
    if not valid:
        return None
    rarity = str(exemplar.get("rarity") or definition.get("raridade") or "Comum")
    try:
        power = int(exemplar.get("power") or definition.get("poder") or 0)
        exemplar_id = int(exemplar.get("id") or 0)
    except (TypeError, ValueError):
        return None
    allowed_range = FAIXA_PODER.get(rarity)
    if rarity in {"Primordial", "Singular"} or not allowed_range or not int(allowed_range[0]) <= power <= int(allowed_range[1]) or exemplar_id <= 0:
        return None
    payload = dict(definition)
    payload.update({
        "id": str(definition["card_id"]), "nome": str(definition["nome"]),
        "categoria": "Unidade", "raridade": rarity, "poder": power,
        "tipo": str(definition["tipo"]), "faccao": str(definition["faccao"]),
        "fileira": str(definition["fileira"]),
        "habilidade": str(definition.get("habilidade") or ""),
        "descricao": str(definition.get("descricao") or ""), "custo": 0,
    })
    card = preparar_carta(payload)
    card["card_id"] = str(definition["card_id"])
    card["exemplar_id"] = exemplar_id
    card["id"] = f"{definition['card_id']}::{exemplar_id}"
    card["personal_card"] = True
    return card


def _faction(cards):
    counts = contar_faccoes_deck(cards)
    return max(counts, key=lambda faction: (counts[faction], faction))


def novo_estado(match_id: int, creator_id: int, opponent_id: int, decks: dict[str, list[dict]], deck_configs: dict[str, dict] | None = None) -> dict:
    players = {}
    deck_configs = deck_configs or {}
    for uid in (str(creator_id), str(opponent_id)):
        deck = deepcopy(decks[uid])
        config = deck_configs.get(uid, {})
        requested_faction = canonical_faction(config.get("faction"))
        # Decks antigos preservam a facção salva; decks novos são validados no endpoint de gravação.
        faction = requested_faction if requested_faction in FACTION_TYPES else _faction(deck)
        leader_id = config.get("leader_id") or DEFAULT_LEADERS[faction]
        if leader_id not in LEADERS or LEADERS[leader_id]["faction"] != faction:
            leader_id = DEFAULT_LEADERS[faction]
        players[uid] = {
            "hand": deck[:10], "draw_pile": deck[10:], "discard": [], "board": [],
            "passed": False, "leader_used": False, "weather_used": False,
            "faction": faction, "leader_id": leader_id, "leader_name": LEADERS[leader_id]["name"],
            "equipped_relic_id": str(config.get("relic_id") or ""), "relic_used": False, "faction_boost_used": False,
            "mulligan_done": False, "last_row": None, "synergy_used": {}, "baixas": 0,
        }
    return {
        "match_id": int(match_id), "status": "active", "phase": "mulligan", "round": 1,
        "players": players, "turn": str(creator_id), "round_starter": str(creator_id),
        "weather": {row: 0 for row in ROWS},
        "crowns": {str(creator_id): 0, str(opponent_id): 0},
        "rounds": [], "winner_id": None,
        "last_event": "Preparação: cada jogador pode trocar até duas cartas.",
        "event_log": ["Partida criada. Preparação: cada jogador pode trocar até duas cartas."],
    }


def _registrar_evento(state: dict) -> dict:
    """Acrescenta o último evento ao histórico persistido da partida."""
    history = state.setdefault("event_log", [])
    event = str(state.get("last_event", "")).strip()
    if event and (not history or history[-1] != event):
        history.append(event[:500])
    state["event_log"] = history[-20:]
    return {"state": state}


def _aplicar_combo_de_cartas(player: dict, card: dict) -> str | None:
    """Resolve uma combinação temática uma única vez por jogador e rodada."""
    tags_novas = set(CARD_SYNERGY_TAGS.get(str(card.get("id", "")), set()))
    if not tags_novas:
        return None
    usados = player.setdefault("synergy_used", {})
    tags_campo = set()
    for unit in player.get("board", []):
        tags_campo.update(CARD_SYNERGY_TAGS.get(str(unit.get("id", "")), set()))
    tags_total = tags_campo | tags_novas
    for combo_id, combo in SYNERGY_COMBOS.items():
        if usados.get(combo_id):
            continue
        required = set(combo["tags"])
        if not required.issubset(tags_total):
            continue
        participantes = [*player.get("board", []), card]
        if "minimum" in combo:
            quantidade = sum(bool(CARD_SYNERGY_TAGS.get(str(unit.get("id", "")), set()) & required) for unit in participantes)
            if quantidade < int(combo["minimum"]):
                continue
        card["bonus"] = int(card.get("bonus", 0)) + int(combo.get("bonus", 0))
        team_bonus = int(combo.get("team_bonus", 0))
        if team_bonus:
            for ally in player.get("board", []):
                if ally.get("row") == card.get("row"):
                    ally["bonus"] = int(ally.get("bonus", 0)) + team_bonus
        card["combo_ativado"] = combo_id
        usados[combo_id] = True
        return str(combo["name"])
    return None


def _poder_efetivo(unit: dict, weather: dict | None = None) -> int:
    """Poder real da unidade, com bônus, clima e estados negativos aplicados."""
    weather = weather or {}
    clima = max(0, int(weather.get(unit.get("row"), 0) or 0) - int(unit.get("weather_resist", 0)))
    estados = min(3, int(unit.get("geada", 0)) + int(unit.get("podrida", 0)) + int(unit.get("loucura", 0)))
    return max(1, int(unit.get("poder", 0)) + int(unit.get("bonus", 0)) - clima - estados)


def _remover_unidade(side: dict, unit: dict, causa: str = "remocao") -> str:
    """Remove uma unidade do campo respeitando escudo e disparando Vingança.

    Ponto único de remoção: qualquer efeito que destrua, sacrifique ou execute
    uma unidade deve passar por aqui para que escudo, contagem de baixas e
    habilidades de queda funcionem de forma consistente.
    Retorna um texto curto para o histórico da partida.
    """
    if unit not in side.get("board", []):
        return ""
    if causa != "sacrificio" and int(unit.get("escudo", 0)) > 0:
        unit["escudo"] = int(unit["escudo"]) - 1
        return f"{unit['nome']} resistiu graças ao escudo."
    side["board"].remove(unit)
    unit.pop("escudo", None)
    for status_key in ("sangramento", "geada", "podrida", "loucura"):
        unit[status_key] = 0
    side.setdefault("discard", []).append(unit)
    side["baixas"] = int(side.get("baixas", 0)) + 1
    texto = f"{unit['nome']} caiu."
    if unit.get("habilidade") == "vinganca":
        aliados = [u for u in side["board"] if u.get("row") == unit.get("row")]
        for aliado in aliados:
            aliado["bonus"] = int(aliado.get("bonus", 0)) + 1
        if aliados:
            texto += f" Vingança: +1 para {len(aliados)} aliado(s)."
    return texto


def pontuacao(player: dict, weather: dict | None = None) -> int:
    weather = weather or {}
    total = 0
    for c in player["board"]:
        total += _poder_efetivo(c, weather)
    return total


def _resumo_alvo(unit: dict) -> dict:
    return {
        "id": str(unit["id"]), "nome": unit.get("nome", ""), "poder": int(unit.get("poder", 0)),
        "bonus": int(unit.get("bonus", 0)), "row": unit.get("row", ""), "escudo": int(unit.get("escudo", 0)),
        "sangramento": int(unit.get("sangramento", 0)), "geada": int(unit.get("geada", 0)),
        "podrida": int(unit.get("podrida", 0)), "loucura": int(unit.get("loucura", 0)),
    }


def opcoes_de_alvo(state: dict, user_id) -> dict:
    """Alvos escolhíveis para cada carta especial da mão de `user_id`.

    As regras de elegibilidade ficam aqui, ao lado de aplicar_jogada, para o site apenas
    exibir as opções (mesmos limites de poder que o motor valida). `filtro_fileira` diz como
    o site deve filtrar pela fileira escolhida: "mesma" (alvo na fileira) ou "diferente".
    """
    player = state.get("players", {}).get(str(user_id))
    if not player or state.get("status") != "active" or state.get("phase", "battle") != "battle":
        return {}
    other = next((p for uid, p in state["players"].items() if uid != str(user_id)), {"board": []})
    resultado: dict[str, dict] = {}
    for card in player.get("hand", []):
        if not (card.get("especial") or str(card.get("categoria", "")).casefold() == "especial"):
            continue
        skill = card.get("habilidade", "")
        if skill == "gwent_execucao":
            info = {"rotulo": f"Escolha a unidade inimiga a eliminar (poder efetivo {min(6, 6 + int(RARITY_EFFECT_BUDGET.get(str(card.get('raridade', 'Comum')), 0)))} ou menos)",
                    "filtro_fileira": "mesma",
                    "opcoes": [u for u in other.get("board", []) if _poder_efetivo(u, state.get("weather")) <= min(6, 6 + int(RARITY_EFFECT_BUDGET.get(str(card.get("raridade", "Comum")), 0)))]}
        elif skill == "gwent_medico":
            info = {"rotulo": f"Escolha a unidade (poder {min(8, 4 + int(RARITY_EFFECT_BUDGET.get(str(card.get('raridade', 'Comum')), 0)))} ou menos) que volta para a sua mão",
                    "filtro_fileira": None,
                    "opcoes": [c for c in player.get("discard", []) if not c.get("especial") and int(c["poder"]) <= min(8, 4 + int(RARITY_EFFECT_BUDGET.get(str(card.get("raridade", "Comum")), 0)))]}
        elif skill == "gwent_requiem":
            info = {"rotulo": f"Escolha a unidade (poder {min(10, 6 + int(RARITY_EFFECT_BUDGET.get(str(card.get('raridade', 'Comum')), 0)))} ou menos) que retorna ao campo",
                    "filtro_fileira": None,
                    "opcoes": [c for c in player.get("discard", []) if not c.get("especial") and int(c["poder"]) <= min(10, 6 + int(RARITY_EFFECT_BUDGET.get(str(card.get("raridade", "Comum")), 0)))]}
        elif skill == "gwent_egide":
            info = {"rotulo": "Escolha a unidade que receberá o escudo", "filtro_fileira": None,
                    "opcoes": [u for u in player.get("board", []) if int(u.get("escudo", 0)) <= 0]}
        elif skill == "gwent_passo":
            info = {"rotulo": "Escolha a unidade que será movida para a fileira de destino",
                    "filtro_fileira": "diferente", "opcoes": list(player.get("board", []))}
        else:
            continue
        info["opcoes"] = [_resumo_alvo(u) for u in info["opcoes"]]
        resultado[str(card["id"])] = info
    return resultado


def opcoes_de_reliquia(state: dict, user_id) -> dict:
    """Descreve escolhas de alvo da Relíquia equipada para a interface e para a IA."""
    player = state.get("players", {}).get(str(user_id))
    if not player:
        return {}
    relic_id = str(player.get("equipped_relic_id") or "")
    other = next((p for uid, p in state.get("players", {}).items() if uid != str(user_id)), {})
    rows = {}
    if relic_id in {"reliquia_noite_chama", "reliquia_lamina_negra", "reliquia_algemas_margit"}:
        for row in ROWS:
            targets = [u for u in other.get("board", []) if u.get("row") == row]
            rows[row] = [_resumo_alvo(u) for u in targets]
    return {
        "relic_id": relic_id,
        "requires_row": relic_id in {"reliquia_noite_chama", "reliquia_lamina_negra", "reliquia_algemas_margit"},
        "requires_target": relic_id in {"reliquia_lamina_negra", "reliquia_algemas_margit"},
        "supports_modes": relic_id == "reliquia_noite_chama",
        "rows": rows,
    }


def placar(state: dict) -> dict:
    return {uid: {
        "score": pontuacao(player, state.get("weather")),
        "passed": player["passed"], "hand": len(player["hand"]),
        "crowns": state["crowns"][uid], "board": deepcopy(player["board"]),
        "faction": canonical_faction(player.get("faction", "")) or "",
        "baixas": int(player.get("baixas", 0)),
    } for uid, player in state["players"].items()}


def _resolve_round(state: dict) -> None:
    ids = list(state["players"])
    a, b = ids
    sa = pontuacao(state["players"][a], state.get("weather"))
    sb = pontuacao(state["players"][b], state.get("weather"))
    winner = a if sa > sb else b if sb > sa else None
    if winner:
        state["crowns"][winner] += 1
        state["last_event"] = f"Rodada {state['round']} vencida por {winner} ({sa} × {sb})."
    else:
        state["last_event"] = f"Rodada {state['round']} empatada ({sa} × {sb})."
    state["rounds"].append({"round": state["round"], "score_a": sa, "score_b": sb, "winner_id": winner})
    if max(state["crowns"].values()) >= 2 or state["round"] >= 3:
        ca, cb = state["crowns"][a], state["crowns"][b]
        state["status"] = "finished"
        state["phase"] = "finished"
        state["winner_id"] = a if ca > cb else b if cb > ca else None
        state["last_event"] += " Partida encerrada."
        return
    state["round"] += 1
    previous_weather = deepcopy(state.get("weather", {}))
    extras = []
    for pid, player in state["players"].items():
        board = player.get("board", [])
        # Espólios: quem vence a rodada com a unidade em campo compra uma carta.
        if pid == winner and any(u.get("habilidade") == "espolios" for u in board) and player.get("draw_pile"):
            player["hand"].append(player["draw_pile"].pop(0))
            extras.append("Espólios de guerra: o vencedor comprou uma carta.")
        # Sobrevivente: a mais forte permanece no campo para a próxima rodada.
        keepers = [u for u in board if u.get("habilidade") == "sobrevivente"]
        keeper = max(keepers, key=lambda u: _poder_efetivo(u, previous_weather), default=None)
        # Unidades sobrevivem à rodada no descarte: isso habilita recuperação
        # por Lágrima Sagrada e mantém o histórico completo da partida.
        for fallen in board:
            if fallen is keeper:
                continue
            archived = deepcopy(fallen)
            # Bônus, escudos e estados são temporários: não podem reaparecer ao
            # recuperar uma unidade do descarte em uma rodada posterior.
            archived["bonus"] = 0
            archived["escudo"] = 0
            for status_key in ("sangramento", "geada", "podrida", "loucura"):
                archived[status_key] = 0
            archived.pop("combo_ativado", None)
            player.setdefault("discard", []).append(archived)
        player["board"] = []
        if keeper is not None:
            kept = deepcopy(keeper)
            kept["bonus"] = 0
            kept["escudo"] = 0
            # Estados temporários são encerrados ao fim da rodada, inclusive em Sobreviventes.
            for status_key in ("sangramento", "geada", "podrida", "loucura"):
                kept[status_key] = 0
            kept.pop("combo_ativado", None)
            player["board"].append(kept)
            extras.append(f"{kept['nome']} sobreviveu à rodada.")
        player["passed"] = False
        player["faction_boost_used"] = False
        player["last_row"] = None
        player["synergy_used"] = {}
        player.pop("astral_thread_ready", None)
    state["weather"] = {row: 0 for row in ROWS}
    # Iniciativa alternada: a pessoa que abriu a rodada anterior cede a abertura
    # da próxima, independentemente do vencedor. Isso evita snowball de iniciativa.
    previous_starter = str(state.get("round_starter") or a)
    next_starter = b if previous_starter == a else a
    state["round_starter"] = next_starter
    state["turn"] = next_starter
    state["last_event"] += " " + " ".join(extras) if extras else ""
    state["last_event"] += f" Nova rodada: {next_starter} começa (iniciativa alternada); as cartas restantes continuam na mão."



def _auto_pass_empty_hands(state: dict) -> None:
    """Marca automaticamente como passados os jogadores sem cartas na mão.

    Se ambos ficarem sem cartas (ou já tiverem passado), resolve a rodada.
    Também avança o turno para o único jogador que ainda pode jogar.
    """
    while state.get("status") == "active" and state.get("phase", "battle") == "battle":
        players = state.get("players", {})
        if not players:
            return

        newly_passed = []
        for uid, side in players.items():
            if not side.get("hand") and not side.get("passed", False):
                side["passed"] = True
                newly_passed.append(str(uid))

        if newly_passed:
            message = "Sem cartas na mão: passagem automática de " + ", ".join(
                f"jogador {uid}" for uid in newly_passed
            ) + "."
            state["last_event"] = message
            history = state.setdefault("event_log", [])
            if not history or history[-1] != message:
                history.append(message[:500])
                state["event_log"] = history[-20:]

        if all(side.get("passed", False) for side in players.values()):
            _resolve_round(state)
            if state.get("status") != "active":
                return
            # Uma nova rodada pode começar com a mão vazia; nesse caso
            # o passe também é automático, sem exigir uma ação inexistente.
            continue

        active_id = next((uid for uid, side in players.items() if not side.get("passed", False)), None)
        turn_id = str(state.get("turn") or "")
        if active_id is not None and (turn_id not in players or players[turn_id].get("passed", False)):
            state["turn"] = active_id
        return

def aplicar_jogada(state: dict, user_id: int, card_id: str | None = None,
                    action: str = "play", row: str | None = None,
                    card_ids: list[str] | None = None,
                    target_id: str | None = None) -> dict:
    state = deepcopy(state)
    # Compatibilidade com partidas iniciadas na versão anterior do motor.
    state.setdefault("phase", "battle")
    state.setdefault("weather", {row: 0 for row in ROWS})
    state.setdefault("event_log", [])
    for legacy_player in state.get("players", {}).values():
        legacy_player.setdefault("discard", [])
        legacy_player.setdefault("draw_pile", [])
        legacy_player["faction"] = canonical_faction(legacy_player.get("faction")) or _faction(legacy_player.get("hand", []))
        legacy_player.setdefault("faction_boost_used", False)
        legacy_player.setdefault("mulligan_done", True)
        legacy_player.setdefault("leader_used", False)
        legacy_player.setdefault("relic_used", False)
        legacy_player.setdefault("weather_used", False)
        legacy_player.setdefault("last_row", None)
        legacy_player.setdefault("synergy_used", {})
        legacy_player.setdefault("baixas", 0)
    uid = str(user_id)
    if state["status"] != "active":
        return {"error": "A partida já terminou."}
    if uid not in state["players"]:
        return {"error": "Você não participa desta partida."}
    player = state["players"][uid]

    # Relíquia equipada é uma carta tática adicional, separada das 12 cartas do deck.
    # A ação "relic" converte a escolha equipada em uma carta temporária e usa o
    # mesmo resolvedor de especiais, preservando validações e o limite de uma ativação.
    if action == "relic":
        relic_id = str(player.get("equipped_relic_id") or "")
        if not relic_id:
            return {"error": "Você não equipou uma Relíquia para esta partida."}
        if player.get("relic_used"):
            return {"error": "Sua Relíquia já foi ativada nesta partida."}
        relic_cards = {
            "reliquia_grande_runa_godrick", "reliquia_runa_nao_nascidos",
            "reliquia_runa_morte", "reliquia_noite_chama",
            "reliquia_lamina_negra", "reliquia_algemas_margit",
        }
        if relic_id not in relic_cards:
            return {"error": "A Relíquia equipada não é válida."}
        from sistemas.cartas import get_carta
        relic_model = get_carta(relic_id)
        if relic_model is None:
            return {"error": "A carta da Relíquia não está disponível no catálogo."}
        relic_payload = preparar_carta(relic_model.para_dict())
        relic_payload["id"] = relic_id
        relic_payload["especial"] = True
        player["hand"].append(relic_payload)
        action = "play"
        card_id = relic_id

    # Rendição pode ser declarada mesmo fora do turno; todas as outras ações
    # continuam protegidas pela validação de turno abaixo.
    if action == "surrender":
        opponent_id = next(x for x in state["players"] if x != uid)
        state["status"] = "finished"
        state["phase"] = "finished"
        state["winner_id"] = opponent_id
        state["surrendered_by"] = uid
        state["last_event"] = f"Jogador {uid} se rendeu. Vitória de {opponent_id}."
        return _registrar_evento(state)

    # A preparação inicial é simultânea: cada jogador deve poder escolher
    # suas trocas independentemente de quem inicia a batalha.
    if state.get("phase") != "mulligan" and state["turn"] != uid:
        return {"error": "Aguarde a jogada do adversário."}

    if state.get("phase") == "mulligan":
        if player["mulligan_done"]:
            return {"error": "Você já concluiu sua preparação."}
        if action not in {"mulligan", "keep"}:
            return {"error": "Escolha trocar até duas cartas ou manter sua mão."}
        if action == "mulligan":
            chosen = [str(x) for x in (card_ids or [])]
            if len(chosen) > 2 or len(set(chosen)) != len(chosen):
                return {"error": "Você pode trocar no máximo duas cartas diferentes."}
            for cid in chosen:
                old = next((c for c in player["hand"] if c["id"] == cid), None)
                if old is None:
                    return {"error": "Carta selecionada não está na sua mão."}
                player["hand"].remove(old)
                player["discard"].append(old)
                if player["draw_pile"]:
                    player["hand"].append(player["draw_pile"].pop(0))
        player["mulligan_done"] = True
        other = next(x for x in state["players"] if x != uid)
        if state["players"][other]["mulligan_done"]:
            state["phase"] = "battle"
            state["turn"] = list(state["players"])[0]
            state["last_event"] = "Preparação concluída. A batalha começou."
            _auto_pass_empty_hands(state)
        else:
            state["turn"] = other
            state["last_event"] = "Preparação concluída por um jogador. Aguardando o adversário."
        return _registrar_evento(state)

    if player["passed"]:
        return {"error": "Você já passou nesta rodada."}
    other_id = next(x for x in state["players"] if x != uid)
    other = state["players"][other_id]

    # Compatibilidade com partidas salvas antes da regra de passe automático.
    if not player.get("hand") and action != "pass":
        state["turn"] = other_id
        state["last_event"] = "Você está sem cartas na mão e passou automaticamente."
        _auto_pass_empty_hands(state)
        return _registrar_evento(state)

    if action == "pass":
        player["passed"] = True
        state["turn"] = other_id
        state["last_event"] = "Jogador passou. O adversário ainda pode jogar."
        _auto_pass_empty_hands(state)
        return _registrar_evento(state)

    if action == "leader":
        if player["leader_used"]:
            return {"error": "A habilidade de líder já foi usada."}
        if row not in ROWS:
            return {"error": "Fileira inválida."}
        leader_id = player.get("leader_id") or DEFAULT_LEADERS.get(player.get("faction"), "comandante_fornalha")
        leader = LEADERS.get(leader_id)
        if not leader or leader["faction"] != player.get("faction"):
            return {"error": "Líder incompatível com a facção deste deck."}
        effect = leader["effect"]
        enemy = other
        if effect == "godfrey_warlord":
            targets = [u for u in player["board"] if u.get("row") == "melee"]
            if not targets:
                return {"error": "Godfrey precisa de ao menos um aliado em Corpo a Corpo."}
            for unit in targets:
                unit["bonus"] = int(unit.get("bonus", 0)) + 2
        elif effect == "morgott_omen":
            targets = sorted(
                (u for u in player["board"] if u.get("row") == row and int(u.get("escudo", 0)) <= 0),
                key=lambda u: _poder_efetivo(u, state.get("weather")), reverse=True
            )[:2]
            if not targets:
                return {"error": "Não há aliados sem Escudo na fileira escolhida."}
            for unit in targets:
                unit["escudo"] = 1
                unit["bonus"] = int(unit.get("bonus", 0)) + 1
        elif effect == "radagon_purification":
            status_keys = ("sangramento", "geada", "podrida", "loucura")
            purified = []
            for unit in player["board"]:
                if any(int(unit.get(key, 0)) > 0 for key in status_keys):
                    for key in status_keys:
                        unit[key] = 0
                    unit["bonus"] = int(unit.get("bonus", 0)) + 1
                    purified.append(unit)
            if not purified:
                return {"error": "Nenhum aliado possui um efeito negativo para Radagon purificar."}
        elif effect == "mohg_blood_rite":
            targets = sorted(
                enemy["board"], key=lambda u: _poder_efetivo(u, state.get("weather")), reverse=True
            )
            targets = [u for u in targets if u.get("row") == row][:2]
            if not targets:
                return {"error": "Não há inimigos na fileira escolhida para o ritual de sangue."}
            for unit in targets:
                unit["sangramento"] = int(unit.get("sangramento", 0)) + 1
                if unit["sangramento"] >= 2:
                    unit["bonus"] = max(-2, int(unit.get("bonus", 0)) - 2)
                    unit["sangramento"] = 0
        elif effect == "rykard_devour":
            allies = [u for u in player["board"] if u.get("row") == row]
            if len(allies) < 2:
                return {"error": "Rykard precisa de ao menos 2 aliados na fileira para realizar o sacrifício."}
            victim = min(allies, key=lambda u: _poder_efetivo(u, state.get("weather")))
            victim_name = victim.get("nome", "Aliado")
            _remover_unidade(player, victim, "sacrificio")
            for unit in player["board"]:
                if unit.get("row") == row:
                    unit["bonus"] = int(unit.get("bonus", 0)) + 2
        elif effect == "esgar_blood_priest":
            pool = [c for c in player["discard"] if not c.get("especial") and int(c.get("poder", 99)) <= 5]
            if not pool:
                return {"error": "Não há unidade de poder 5 ou menos no descarte para Esgar ressuscitar."}
            revived = deepcopy(max(pool, key=lambda c: int(c.get("poder", 0))))
            player["discard"] = [c for c in player["discard"] if c.get("id") != revived.get("id")]
            revived["row"] = row
            revived["bonus"] = int(revived.get("bonus", 0)) + 1
            revived.pop("escudo", None)
            for key in ("sangramento", "geada", "podrida", "loucura"):
                revived[key] = 0
            player["board"].append(revived)
        elif effect == "rennala_full_moon":
            affected = [u for u in player["board"] if int(u.get("geada", 0)) > 0 or int(u.get("podrida", 0)) > 0]
            if not affected:
                return {"error": "Rennala precisa de aliados afetados por Geada ou Podridão."}
            for unit in affected:
                unit["geada"] = 0
                unit["podrida"] = 0
                if unit.get("row") == "siege":
                    unit["bonus"] = int(unit.get("bonus", 0)) + 1
        elif effect == "astel_gravity":
            targets = sorted(
                (u for u in enemy["board"] if u.get("row") == row),
                key=lambda u: _poder_efetivo(u, state.get("weather")), reverse=True
            )[:3]
            if not targets:
                return {"error": "Não há inimigos na fileira escolhida para Astel atingir."}
            for unit in targets:
                unit["geada"] = min(2, int(unit.get("geada", 0)) + 1)
        elif effect == "loretta_knight":
            if row != "ranged":
                return {"error": "Loretta só pode ser ativada escolhendo a fileira de Longa Distância."}
            targets = sorted(
                (u for u in player["board"] if u.get("row") == "ranged"),
                key=lambda u: _poder_efetivo(u, state.get("weather")), reverse=True
            )[:2]
            if not targets:
                return {"error": "Loretta precisa de ao menos uma unidade aliada em Longa Distância."}
            for unit in targets:
                unit["bonus"] = int(unit.get("bonus", 0)) + 2
        else:
            return {"error": "Habilidade de líder não reconhecida."}
        player["leader_used"] = True
        state["last_event"] = f"Líder {leader['name']} ativou: {leader['description']}"
    elif action == "weather":
        if player["weather_used"]:
            return {"error": "Seu efeito climático já foi usado nesta partida."}
        if row not in ROWS:
            return {"error": "Fileira inválida."}
        player["weather_used"] = True
        state["weather"][row] = max(1, int(state["weather"].get(row, 0)))
        state["last_event"] = f"Clima severo na fileira {ROW_LABELS[row]}."
    elif action == "play":
        found = next((c for c in player["hand"] if c["id"] == str(card_id)), None)
        if not found:
            return {"error": "Essa carta não está na sua mão."}
        card = deepcopy(found)
        bonus_antes = {id(unit): int(unit.get("bonus", 0))
                       for side in (player, other) for unit in side.get("board", [])}
        bonus_card_antes = int(card.get("bonus", 0))
        # Cartas com habilidade de identidade substituem a habilidade genérica do
        # campo `habilidade`; executar ambas criava efeitos ocultos não descritos.
        skill = "" if str(card.get("id", "")) in CARD_IDENTITY_ABILITIES else card.get("habilidade", "")
        eventos_especial: list[str] = []
        potencia_raridade = int(RARITY_EFFECT_BUDGET.get(str(card.get("raridade", "Comum")), 0))
        if card.get("especial") or str(card.get("categoria", "")).casefold() == "especial":
            if skill.startswith("reliquia_") and player.get("relic_used"):
                return {"error": "Você já ativou uma Relíquia nesta partida."}
            if skill == "reliquia_godrick":
                if not player["board"]: return {"error": "A Grande Runa de Godrick exige uma unidade aliada em campo."}
                for unit in player["board"]: unit["bonus"] = int(unit.get("bonus", 0)) + 1
                player["relic_used"] = True
                eventos_especial.append("Grande Runa de Godrick concedeu +1 a todas as unidades aliadas.")
            elif skill == "reliquia_renala":
                purificados = 0
                for unit in player["board"]:
                    if unit.get("geada", 0) or unit.get("podrida", 0):
                        unit["geada"] = 0; unit["podrida"] = 0; unit["bonus"] = int(unit.get("bonus", 0)) + 1; purificados += 1
                if not purificados: return {"error": "Não há aliados com Geada ou Podridão para purificar."}
                player["relic_used"] = True
                eventos_especial.append(f"Grande Runa dos Não Nascidos purificou {purificados} aliado(s) e concedeu +1.")
            elif skill == "reliquia_morte":
                alvos=[]
                for fileira in ROWS:
                    candidatos=[u for u in other["board"] if u.get("row")==fileira and int(u.get("bonus",0))>0]
                    if candidatos:
                        alvo=max(candidatos,key=lambda u:int(u.get("bonus",0))); alvo["bonus"]=max(0,int(alvo.get("bonus",0))-2); alvos.append(alvo["nome"])
                if not alvos: return {"error": "A Runa da Morte só afeta unidades inimigas com bônus positivo."}
                player["relic_used"]=True; eventos_especial.append("Runa da Morte corroeu bônus de: "+", ".join(alvos)+".")
            elif skill == "reliquia_noite_chama":
                if row not in ROWS: return {"error": "Escolha uma fileira inimiga."}
                alvos=[u for u in other["board"] if u.get("row")==row]
                if not alvos: return {"error": "Não há inimigos na fileira escolhida."}
                if target_id == "noite":
                    for unit in alvos: unit["geada"]=min(2,int(unit.get("geada",0))+1)
                    eventos_especial.append("A postura da Noite aplicou Geada à fileira.")
                else:
                    alvo=max(alvos,key=lambda u:_poder_efetivo(u,state.get("weather")))
                    if int(alvo.get("escudo",0))>0: alvo["escudo"]-=1; eventos_especial.append(f"O Escudo de {alvo['nome']} bloqueou a Chama.")
                    else: alvo["poder"]=max(1,int(alvo.get("poder",1))-1); alvo["bonus"]=int(alvo.get("bonus",0))-2; eventos_especial.append(f"A Chama atingiu {alvo['nome']}.")
                player["relic_used"]=True
            elif skill == "reliquia_lamina_negra":
                if row not in ROWS: return {"error": "Escolha a fileira do alvo."}
                alvos=[u for u in other["board"] if u.get("row")==row]
                alvo=next((u for u in alvos if u.get("id")==str(target_id)),None) if target_id else (max(alvos,key=lambda u:_poder_efetivo(u,state.get("weather"))) if alvos else None)
                if not alvo: return {"error": "Alvo não encontrado."}
                if int(alvo.get("escudo",0))>0:
                    alvo["escudo"]-=1
                    eventos_especial.append(f"O Escudo de {alvo['nome']} bloqueou a Lâmina Negra; a Relíquia não foi consumida.")
                else:
                    alvo["bonus"]=int(alvo.get("bonus",0))-3
                    player["relic_used"]=True
                    eventos_especial.append(f"Lâmina Negra reduziu o bônus de {alvo['nome']} em 3.")
            elif skill == "reliquia_algemas":
                if row not in ROWS: return {"error": "Escolha a fileira do alvo."}
                alvos=[u for u in other["board"] if u.get("row")==row]
                alvo=next((u for u in alvos if u.get("id")==str(target_id)),None) if target_id else (max(alvos,key=lambda u:int(u.get("bonus",0))) if alvos else None)
                if not alvo: return {"error": "Não há alvo na fileira escolhida."}
                alvo["bonus"]=min(0,int(alvo.get("bonus",0))); player["relic_used"]=True; eventos_especial.append(f"Algemas de Margit anularam os bônus de {alvo['nome']}.")
            elif skill == "gwent_nevoa":
                if row not in ROWS:
                    return {"error": "Escolha uma fileira válida."}
                targets = [u for u in other["board"] if u.get("row") == row]
                if not targets:
                    return {"error": "Não há inimigos na fileira escolhida para receber Podridão Escarlate."}
                for unit in targets:
                    unit["podrida"] = min(2, int(unit.get("podrida", 0)) + 1 + (1 if potencia_raridade >= 2 else 0))
            elif skill == "gwent_chuva":
                targets = [u for u in other["board"] if u.get("row") == "siege"]
                if not targets:
                    return {"error": "Não há inimigos em Cerco para receber Sangue Corrompido."}
                for unit in targets:
                    unit["sangramento"] = min(2, int(unit.get("sangramento", 0)) + 1)
                    if unit["sangramento"] >= 2:
                        unit["bonus"] = max(-2, int(unit.get("bonus", 0)) - 2)
                        unit["sangramento"] = 0
            elif skill == "gwent_geada":
                targets = list(other["board"])
                if not targets:
                    return {"error": "Não há inimigos para receber Geada."}
                for unit in targets:
                    unit["geada"] = min(2, int(unit.get("geada", 0)) + 1 + (1 if potencia_raridade >= 2 else 0))
            elif skill == "gwent_chifre":
                if row not in ROWS:
                    return {"error": "Escolha uma fileira válida."}
                for unit in player["board"]:
                    if unit["row"] == row:
                        unit["bonus"] = int(unit.get("bonus", 0)) + 2
            elif skill == "gwent_medico":
                candidates = [c for c in player["discard"] if not c.get("especial") and int(c["poder"]) <= min(8, 4 + potencia_raridade)]
                if not candidates:
                    return {"error": "Não há unidade elegível no descarte."}
                if target_id:
                    revived = next((c for c in candidates if c["id"] == str(target_id)), None)
                    if revived is None:
                        return {"error": "Essa unidade não pode ser recuperada (poder 4 ou menos, no seu descarte)."}
                else:
                    revived = candidates[-1]
                player["discard"].remove(revived)
                player["hand"].append(revived)
            elif skill == "gwent_queima":
                for side in (player, other):
                    if side["board"]:
                        strongest = max(side["board"], key=lambda u: _poder_efetivo(u, state.get("weather")))
                        eventos_especial.append(_remover_unidade(side, strongest))
            elif skill == "gwent_purificar":
                state["weather"] = {r: 0 for r in ROWS}
            elif skill == "gwent_execucao":
                if row not in ROWS:
                    return {"error": "Escolha uma fileira válida."}
                targets = [c for c in other["board"] if c["row"] == row]
                if not targets:
                    return {"error": "Não há unidade inimiga nessa fileira."}
                elegiveis = [c for c in targets if _poder_efetivo(c, state.get("weather")) <= min(6, 6 + potencia_raridade)]
                if not elegiveis:
                    return {"error": f"A Lâmina da Morte Destinada só alcança unidades com poder efetivo {min(6, 6 + potencia_raridade)} ou menos."}
                if target_id:
                    victim = next((c for c in elegiveis if c["id"] == str(target_id)), None)
                    if victim is None:
                        return {"error": "O alvo escolhido não está nessa fileira ou excede poder efetivo 6."}
                else:
                    victim = min(elegiveis, key=lambda u: _poder_efetivo(u, state.get("weather")))
                eventos_especial.append(_remover_unidade(other, victim, "execucao"))
            elif skill == "gwent_vinculo":
                if row not in ROWS:
                    return {"error": "Escolha uma fileira válida."}
                allies = [c for c in player["board"] if c["row"] == row]
                if len(allies) < 2:
                    return {"error": "O Juramento exige pelo menos duas unidades na fileira."}
                for unit in allies:
                    unit["bonus"] = int(unit.get("bonus", 0)) + 2
            elif skill == "gwent_batedor":
                quantidade = min(2, 1 + potencia_raridade, len(player["draw_pile"]))
                if quantidade <= 0:
                    return {"error": "Sua reserva de compra está vazia."}
                for _ in range(quantidade):
                    player["hand"].append(player["draw_pile"].pop(0))
                eventos_especial.append(f"Passo do Cão de Caça comprou {quantidade} carta(s).")
            elif skill == "gwent_muralha":
                if row not in ROWS:
                    return {"error": "Escolha uma fileira válida."}
                for unit in player["board"]:
                    if unit["row"] == row:
                        unit["bonus"] = int(unit.get("bonus", 0)) + 1
            elif skill == "gwent_chama":
                purificados = 0
                for unit in player["board"]:
                    marcas = int(unit.get("geada", 0))
                    if marcas:
                        unit["geada"] = 0
                        unit["bonus"] = int(unit.get("bonus", 0)) + 1
                        purificados += 1
                eventos_especial.append(f"Chama removeu Geada de {purificados} unidade(s) aliada(s); cada uma recebeu +1.")
            elif skill == "gwent_invocacao":
                if row not in ROWS:
                    return {"error": "Escolha a fileira para a invocação."}
                summoned = {
                    "id": f"espiritos_lobos_{uid}_{state['round']}_{len(player['board'])}",
                    "nome": "Lobos Espirituais", "categoria": "Unidade", "especial": False,
                    "poder": min(6, 3 + potencia_raridade), "bonus": 0, "tipo": "Magia", "faccao": "Lua Negra",
                    "habilidade": "", "row": row, "fileira": row, "weather_resist": 0, "escudo": 0,
                }
                player["board"].append(summoned)
                eventos_especial.append(f"Lobos Espirituais invocados na fileira {ROW_LABELS[row]} ({min(6, 3 + potencia_raridade)} de poder).")
            elif skill == "gwent_sangramento":
                if row not in ROWS:
                    return {"error": "Escolha uma fileira válida."}
                targets = [u for u in other["board"] if u["row"] == row]
                if not targets:
                    return {"error": "Não há unidades inimigas nessa fileira."}
                for index, unit in enumerate(targets):
                    marcas_antes = int(unit.get("sangramento", 0))
                    marcas_aplicar = 1 + (1 if index < potencia_raridade and marcas_antes == 0 else 0)
                    for _ in range(marcas_aplicar):
                        unit["sangramento"] = int(unit.get("sangramento", 0)) + 1
                        if unit["sangramento"] >= 2:
                            unit["bonus"] = max(-2, int(unit.get("bonus", 0)) - 2)
                            unit["sangramento"] = 0
                            eventos_especial.append(f"{unit['nome']} sofreu hemorragia (-2).")
                        else:
                            eventos_especial.append(f"{unit['nome']} recebeu uma marca de Sangramento.")
            elif skill == "gwent_geada_cariana":
                if row not in ROWS:
                    return {"error": "Escolha uma fileira válida."}
                targets = [u for u in other["board"] if u["row"] == row]
                if not targets:
                    return {"error": "Não há unidades inimigas nessa fileira."}
                afetadas = 0
                for index, unit in enumerate(targets):
                    marcas_antes = int(unit.get("geada", 0))
                    if marcas_antes >= 2:
                        continue
                    extra = 1 if index < potencia_raridade and marcas_antes == 0 else 0
                    unit["geada"] = min(2, marcas_antes + 1 + extra)
                    afetadas += 1
                eventos_especial.append(f"Geada aplicada a {afetadas} unidade(s); cada marca reduz 1 de poder efetivo, até duas.")
            elif skill == "gwent_podrida":
                if row not in ROWS:
                    return {"error": "Escolha uma fileira válida."}
                targets = [u for u in other["board"] if u["row"] == row]
                if not targets:
                    return {"error": "Não há unidades inimigas nessa fileira."}
                afetadas = 0
                for index, unit in enumerate(targets):
                    marcas_antes = int(unit.get("podrida", 0))
                    if marcas_antes >= 2:
                        continue
                    extra = 1 if index < potencia_raridade and marcas_antes == 0 else 0
                    unit["podrida"] = min(2, marcas_antes + 1 + extra)
                    afetadas += 1
                    if unit["podrida"] == 2 and int(unit.get("bonus", 0)) > 0:
                        unit["bonus"] = max(0, int(unit.get("bonus", 0)) - 1)
                eventos_especial.append(f"Podridão Escarlate aplicada a {afetadas} unidade(s); a segunda marca corrói 1 ponto de bônus positivo.")
            elif skill == "gwent_loucura":
                if row not in ROWS:
                    return {"error": "Escolha uma fileira válida."}
                targets = [u for u in other["board"] if u["row"] == row]
                if not targets:
                    return {"error": "Não há unidades inimigas nessa fileira."}
                afetadas = 0
                para_calar = 0
                for index, unit in enumerate(targets):
                    marcas_antes = int(unit.get("loucura", 0))
                    if marcas_antes >= 2:
                        continue
                    extra = 1 if index < potencia_raridade and marcas_antes == 0 else 0
                    unit["loucura"] = min(2, marcas_antes + 1 + extra)
                    afetadas += 1
                    if unit["loucura"] == 2 and int(unit.get("bonus", 0)) > 0:
                        unit["bonus"] = 0
                        para_calar += 1
                eventos_especial.append(f"Loucura aplicada a {afetadas} unidade(s); {para_calar} bônus positivo(s) foram anulados pela segunda marca.")
            elif skill == "gwent_egide":
                protegiveis = [u for u in player["board"] if int(u.get("escudo", 0)) <= 0]
                if not protegiveis:
                    return {"error": "Você não tem unidade sem escudo em campo."}
                if target_id:
                    alvo = next((u for u in protegiveis if u["id"] == str(target_id)), None)
                    if alvo is None:
                        return {"error": "Escolha uma unidade sua que ainda não tenha escudo."}
                else:
                    alvo = max(protegiveis, key=lambda u: _poder_efetivo(u, state.get("weather")))
                escolhidos = [alvo] + [u for u in sorted(protegiveis, key=lambda u: _poder_efetivo(u, state.get("weather")), reverse=True) if u is not alvo]
                for protegida in escolhidos[:min(3, 1 + potencia_raridade)]:
                    protegida["escudo"] = 1
                eventos_especial.append(f"{len(escolhidos[:min(3, 1 + potencia_raridade)])} unidade(s) receberam escudo.")
            elif skill == "gwent_requiem":
                elegiveis = [c for c in player["discard"] if not c.get("especial") and int(c["poder"]) <= min(10, 6 + potencia_raridade)]
                if not elegiveis:
                    return {"error": "Não há unidade elegível (poder 6 ou menos) no descarte."}
                if target_id:
                    revivida = next((c for c in elegiveis if c["id"] == str(target_id)), None)
                    if revivida is None:
                        return {"error": "Essa unidade não pode ser trazida de volta pelo Réquiem."}
                else:
                    revivida = max(elegiveis, key=lambda c: int(c["poder"]))
                player["discard"].remove(revivida)
                revivida = deepcopy(revivida)
                revivida["bonus"] = 0
                revivida.pop("escudo", None)
                if revivida.get("row") not in ROWS:
                    revivida["row"] = row if row in ROWS else "melee"
                player["board"].append(revivida)
                eventos_especial.append(f"{revivida['nome']} retornou ao campo.")
            elif skill == "gwent_passo":
                if row not in ROWS:
                    return {"error": "Escolha a fileira de destino."}
                moviveis = [u for u in player["board"] if u["row"] != row]
                if not moviveis:
                    return {"error": "Você não tem unidade fora dessa fileira para mover."}
                if target_id:
                    alvo = next((u for u in moviveis if u["id"] == str(target_id)), None)
                    if alvo is None:
                        return {"error": "Escolha uma unidade sua que não esteja na fileira de destino."}
                else:
                    alvo = min(moviveis, key=lambda u: _poder_efetivo(u, state.get("weather")))
                moviveis_ordenados = [alvo] + [u for u in moviveis if u is not alvo]
                movidos = []
                for unidade in moviveis_ordenados[:min(3, 1 + potencia_raridade)]:
                    origem = unidade["row"]
                    unidade["row"] = row
                    movidos.append(unidade["nome"])
                eventos_especial.append(f"{', '.join(movidos)} moveram-se para {ROW_LABELS[row]}.")
            else:
                return {"error": "Efeito especial desconhecido."}
            # Relíquias têm efeitos fixos descritos no catálogo; sua raridade não
            # altera números nem cria uma segunda camada oculta de potência.
            potencia_aplicada = (0 if str(skill).startswith("reliquia_") else
                _aplicar_potencia_raridade(card, player, other, bonus_antes, bonus_card_antes))
            if potencia_aplicada:
                eventos_especial.append(
                    f"A raridade {card.get('raridade', 'Comum')} ampliou o efeito em {potencia_aplicada} ponto(s)."
                )
            player["hand"].remove(found)
            player["discard"].append(card)
            state["last_event"] = f"Carta especial {card['nome']} utilizada."
            detalhes = [d for d in eventos_especial if d]
            if detalhes:
                state["last_event"] += " " + " ".join(detalhes)
        else:
            fileira_obrigatoria = str(card.get("row") or card.get("fileira") or TYPE_ROW.get(str(card.get("tipo", "")), "melee"))
            if row not in ROWS:
                row = fileira_obrigatoria
            if row != fileira_obrigatoria:
                return {"error": f"{card['nome']} só pode ser posicionada na fileira {ROW_LABELS[fileira_obrigatoria]}. Use uma habilidade de movimentação para reposicioná-la."}
            card["row"] = fileira_obrigatoria
            card["bonus"] = 0
            own_score = pontuacao(player, state.get("weather"))
            enemy_score = pontuacao(other, state.get("weather"))
            last_row = player.get("last_row")
            enemy_last_row = other.get("last_row")
            extras_entrada: list[str] = []
            unidade_revivida = None
            if skill == "primeira_luz" and state["round"] == 1: card["bonus"] += 1
            elif skill == "lei_primeva" and state["round"] == 1: card["bonus"] += 2
            elif skill == "ultimo_folego" and state["round"] == 3: card["bonus"] += 1
            elif skill == "paradoxo_eterno" and state["round"] == 3 and state["rounds"] and state["rounds"][-1]["winner_id"] not in (None, uid): card["bonus"] += 2
            elif skill == "precisao" and row == "ranged": card["bonus"] += 1
            elif skill in {"instinto", "fome_abismo"} and own_score < enemy_score: card["bonus"] += 2
            elif skill == "retaliacao" and own_score < enemy_score: card["bonus"] += 1
            elif skill == "contragolpe" and own_score < enemy_score: card["bonus"] += 2
            elif skill == "impeto" and own_score > enemy_score: card["bonus"] += 1
            elif skill == "sangue_frio" and own_score == enemy_score: card["bonus"] += 2
            elif skill == "encadeamento" and last_row == row: card["bonus"] += 2
            elif skill == "adaptacao" and last_row is not None and last_row != row: card["bonus"] += 1
            elif skill == "cacador_arcano":
                # Etapa 3: também caça unidades fortalecidas, para funcionar contra qualquer facção.
                if any(canonical_faction(c.get("faccao") or FACTIONS.get(str(c.get("tipo", "")))) == "Lua Negra" for c in other["board"]) or any(int(c.get("bonus", 0)) > 0 for c in other["board"]):
                    card["bonus"] += 1
            elif skill == "quebra_ritmo" and enemy_last_row == row: card["bonus"] += 1
            elif skill == "olho_tempestade" and state.get("weather", {}).get(row): card["bonus"] += 2
            elif skill == "drenagem":
                for enemy in other["board"]:
                    enemy["bonus"] = max(-2, int(enemy.get("bonus", 0)) - 1)
            elif skill == "decreto_soberano":
                for enemy in other["board"]:
                    enemy["bonus"] = max(-2, int(enemy.get("bonus", 0)) - 2)
            elif skill == "guardiao_fileira":
                card["bonus"] += min(3, sum(1 for ally in player["board"] if ally["row"] == row))
            elif skill == "cacador_solitario":
                if not any(ally["row"] == row for ally in player["board"]):
                    card["bonus"] += 2
            elif skill == "estandarte":
                for ally in player["board"]:
                    if ally["row"] == row:
                        ally["bonus"] = int(ally.get("bonus", 0)) + 1
            elif skill == "resistencia_climatica":
                card["weather_resist"] = 2
                if not any(int(v or 0) > 0 for v in state["weather"].values()):
                    card["bonus"] += 1  # Etapa 3: sem clima ativo a resistência vira vigor.
            elif skill == "eco_arcano":
                if any(c.get("especial") for c in player["discard"]):
                    card["bonus"] += 2
            elif skill == "escudo_ferro":
                card["escudo"] = 1
            elif skill == "devorar":
                presas = [a for a in player["board"] if a["row"] == row]
                if presas:
                    presa = min(presas, key=lambda u: _poder_efetivo(u, state.get("weather")))
                    ganho = min(4, max(1, _poder_efetivo(presa, state.get("weather"))))
                    _remover_unidade(player, presa, "sacrificio")
                    card["bonus"] += ganho
                    extras_entrada.append(f"Devorou {presa['nome']} (+{ganho}).")
            elif skill == "ressurgir":
                pool = [c for c in player["discard"] if not c.get("especial") and int(c["poder"]) <= 5]
                if pool:
                    revivida = max(pool, key=lambda c: int(c["poder"]))
                    player["discard"].remove(revivida)
                    revivida = deepcopy(revivida)
                    revivida["bonus"] = 0
                    revivida.pop("escudo", None)
                    revivida["row"] = revivida.get("row") if revivida.get("row") in ROWS else row
                    unidade_revivida = revivida
                    extras_entrada.append(f"Ressurgiu {revivida['nome']} do descarte.")
            # Sinergias de cartas: recompensam composições e posicionamento coordenado.
            if skill == "dupla_fornalha" and any(c.get("tipo") == "Força" and c.get("row") == row for c in player["board"]):
                card["bonus"] += 2
            elif skill == "irmandade_veu" and any(c.get("tipo") == "Destreza" and c.get("row") != row for c in player["board"]):
                card["bonus"] += 2
            elif skill == "circulo_arcano" and (
                any(c.get("tipo") == "Magia" and c.get("row") == row for c in player["board"])
                or any(c.get("especial") for c in player["discard"])
            ):
                card["bonus"] += 2
            # Habilidade exclusiva da carta, depois das habilidades gerais e antes dos combos.
            identidade_ativada = _aplicar_habilidade_identidade(player, other, card, state, row)
            if player.pop("astral_thread_ready", False) and "astral" in CARD_SYNERGY_TAGS.get(str(card.get("id", "")), set()):
                card["bonus"] += 1
                state["last_event"] += " O Fio Astral foi consumido (+1)."
            # Combos temáticos entre cartas específicas, além das sinergias de fileira acima.
            combo_ativado = _aplicar_combo_de_cartas(player, card)
            # A raridade amplifica apenas os efeitos da carta e combos; não multiplica
            # a passiva fixa da facção, evitando bônus oculto por composição do deck.
            potencia_aplicada = _aplicar_potencia_raridade(
                card, player, other, bonus_antes, bonus_card_antes
            )
            if potencia_aplicada:
                extras_entrada.append(
                    f"A raridade {card.get('raridade', 'Comum')} ampliou a habilidade em {potencia_aplicada} ponto(s)."
                )
            # Passiva visível: a primeira unidade da facção do deck recebe +1 nesta rodada.
            card_faction = canonical_faction(card.get("faccao") or FACTIONS.get(str(card.get("tipo", ""))))
            if card_faction == player["faction"] and not player["faction_boost_used"]:
                card["bonus"] += FACTION_BOOST.get(player["faction"], 1)
                player["faction_boost_used"] = True
            player["hand"].remove(found)
            player["board"].append(card)
            if unidade_revivida is not None:
                player["board"].append(unidade_revivida)
            player["last_row"] = row
            state["last_event"] = f"{card['nome']} entrou na fileira {ROW_LABELS[row]}."
            for texto_extra in extras_entrada:
                state["last_event"] += f" {texto_extra}"
            if identidade_ativada:
                state["last_event"] += f" Habilidade ativada: {identidade_ativada}."
            if combo_ativado:
                state["last_event"] += f" Combo ativado: {combo_ativado}."
    else:
        return {"error": "Ação desconhecida."}

    if state["status"] == "active" and not other["passed"]:
        state["turn"] = other_id
    elif state["status"] == "active" and other["passed"]:
        state["turn"] = uid
    if state["status"] == "active":
        _auto_pass_empty_hands(state)
    return _registrar_evento(state)



def _ai_hand_strength(player: dict) -> float:
    """Valor aproximado dos recursos ainda na mão, usado para conservar cartas fortes."""
    total = 0.0
    for card in player.get("hand", []):
        if card.get("especial") or str(card.get("categoria", "")).casefold() == "especial":
            total += 4.0
        else:
            total += max(1, int(card.get("poder", 1)))
    return total


def _ai_candidate_value(before: dict, after: dict, ai_uid: str, human_uid: str,
                        action: str, card: dict | None = None) -> float:
    """Avalia uma jogada com base no efeito real calculado pelo motor de regras."""
    before_score = placar(before)
    after_score = placar(after)
    before_ai = before_score.get(ai_uid, {})
    after_ai = after_score.get(ai_uid, {})
    before_human = before_score.get(human_uid, {})
    after_human = after_score.get(human_uid, {})

    ai_gain = int(after_ai.get("score", 0)) - int(before_ai.get("score", 0))
    human_loss = int(before_human.get("score", 0)) - int(after_human.get("score", 0))
    value = float(ai_gain) + 1.20 * float(human_loss)

    ai_before = before.get("players", {}).get(ai_uid, {})
    ai_after = after.get("players", {}).get(ai_uid, {})
    human_before = before.get("players", {}).get(human_uid, {})
    human_after = after.get("players", {}).get(human_uid, {})

    # Cartas não gastas continuam sendo recursos para as próximas rodadas.
    value += 0.18 * (_ai_hand_strength(ai_after) - _ai_hand_strength(ai_before))
    # Escudos têm valor defensivo, mesmo quando ainda não alteram a pontuação.
    ai_shields_before = sum(int(unit.get("escudo", 0)) for unit in ai_before.get("board", []))
    ai_shields_after = sum(int(unit.get("escudo", 0)) for unit in ai_after.get("board", []))
    human_shields_before = sum(int(unit.get("escudo", 0)) for unit in human_before.get("board", []))
    human_shields_after = sum(int(unit.get("escudo", 0)) for unit in human_after.get("board", []))
    value += 0.8 * ((ai_shields_after - ai_shields_before) - (human_shields_after - human_shields_before))

    # Valoriza encerrar uma rodada favorável e penaliza entregar uma coroa.
    ai_crowns_before = int(before.get("crowns", {}).get(ai_uid, 0))
    ai_crowns_after = int(after.get("crowns", {}).get(ai_uid, 0))
    human_crowns_before = int(before.get("crowns", {}).get(human_uid, 0))
    human_crowns_after = int(after.get("crowns", {}).get(human_uid, 0))
    value += 12.0 * ((ai_crowns_after - ai_crowns_before) - (human_crowns_after - human_crowns_before))

    if action == "play" and card:
        # O desconto de recurso favorece usar primeiro cartas de menor poder quando
        # duas opções produzem resultado de campo semelhante.
        cost = 0.18 if (card.get("especial") or str(card.get("categoria", "")).casefold() == "especial") else 0.08 * max(1, int(card.get("poder", 1)))
        value -= cost
    return value


def executar_turno_ia(state: dict, ai_user_id: int = AI_PLAYER_ID) -> dict:
    """Executa as ações da NARA enquanto ela conservar o turno.

    A IA usa o mesmo motor `aplicar_jogada` das pessoas. Assim, validações,
    habilidades, clima, líderes, pontuação e resolução de rodada são idênticos.
    O deck da IA é preparado pelo endpoint de criação da partida.
    """
    current = deepcopy(state)
    ai_uid = str(ai_user_id)
    if current.get("status") != "active" or ai_uid not in current.get("players", {}):
        return current

    # Limite defensivo: no máximo 13 jogadas por chamada (12 cartas + líder/clima/passe).
    for _ in range(16):
        if current.get("status") != "active" or str(current.get("turn")) != ai_uid:
            break
        players = current.get("players", {})
        ai = players.get(ai_uid, {})
        human_uid = next((uid for uid in players if uid != ai_uid), None)
        if human_uid is None:
            break

        if current.get("phase") == "mulligan":
            if ai.get("mulligan_done", False):
                break
            result = aplicar_jogada(current, ai_user_id, action="keep")
            if "error" in result:
                break
            current = result["state"]
            continue

        if current.get("phase", "battle") != "battle" or ai.get("passed", False):
            break
        human = players.get(human_uid, {})
        if not ai.get("hand"):
            result = aplicar_jogada(current, ai_user_id, action="pass")
            if "error" in result:
                break
            current = result["state"]
            continue

        scores = placar(current)
        ai_score = int(scores.get(ai_uid, {}).get("score", 0))
        human_score = int(scores.get(human_uid, {}).get("score", 0))
        margin = ai_score - human_score
        human_potential = sum(
            (6 if c.get("especial") or str(c.get("categoria", "")).casefold() == "especial"
             else max(1, int(c.get("poder", 1))))
            for c in human.get("hand", [])
        )

        # Se o adversário já passou e a NARA está na frente, fecha a rodada.
        # Se a vantagem supera o potencial restante da mão humana, conserva recursos.
        should_pass = bool(human.get("passed") and margin > 0)
        should_pass = should_pass or (margin > human_potential + 1)
        if should_pass:
            result = aplicar_jogada(current, ai_user_id, action="pass")
            if "error" in result:
                break
            current = result["state"]
            continue

        candidates: list[tuple[float, dict]] = []

        def consider(action: str, row: str | None = None, card: dict | None = None,
                     target_id: str | None = None) -> None:
            result = aplicar_jogada(
                current, ai_user_id,
                card_id=str(card.get("id", "")) if card else "",
                action=action, row=row, target_id=target_id,
            )
            if "error" in result or not isinstance(result.get("state"), dict):
                return
            after = result["state"]
            score = _ai_candidate_value(current, after, ai_uid, human_uid, action, card)
            candidates.append((score, {"state": after, "action": action, "row": row, "card": card}))

        # Unidades têm fileira fixa; cartas especiais podem escolher uma fileira quando o efeito pede.
        for card in list(ai.get("hand", [])):
            is_special = bool(card.get("especial") or str(card.get("categoria", "")).casefold() == "especial")
            legal_rows = ROWS if is_special else (str(card.get("row") or card.get("fileira") or TYPE_ROW.get(str(card.get("tipo", "")), "melee")),)
            for row in legal_rows:
                consider("play", row, card)

        # Líder e clima não consomem carta: a IA só os usa quando há ganho concreto.
        if not ai.get("leader_used", False):
            for row in ROWS:
                consider("leader", row)
        if not ai.get("weather_used", False):
            for row in ROWS:
                consider("weather", row)

        # A Relíquia é avaliada pelo mesmo motor que valida as ações humanas.
        if ai.get("equipped_relic_id") and not ai.get("relic_used", False):
            relic_id = str(ai.get("equipped_relic_id"))
            if relic_id in {"reliquia_grande_runa_godrick", "reliquia_runa_nao_nascidos", "reliquia_runa_morte"}:
                consider("relic")
            elif relic_id == "reliquia_noite_chama":
                for row in ROWS:
                    if any(u.get("row") == row for u in human.get("board", [])):
                        consider("relic", row, target_id="noite")
                        consider("relic", row, target_id="chama")
            elif relic_id in {"reliquia_lamina_negra", "reliquia_algemas_margit"}:
                for row in ROWS:
                    for target in human.get("board", []):
                        if target.get("row") == row:
                            consider("relic", row, target_id=str(target.get("id", "")))

        best = max(candidates, key=lambda item: item[0], default=None)
        if best is None or best[0] <= 0.05:
            result = aplicar_jogada(current, ai_user_id, action="pass")
            if "error" in result:
                break
            current = result["state"]
            continue

        current = best[1]["state"]
        # Se a outra pessoa ainda não passou, a vez volta para ela.
        # Se ela já passou, a IA mantém a vez e reavalia sua próxima ação.
        if current.get("status") != "active" or str(current.get("turn")) != ai_uid:
            break

    # Fail-safe: a IA não pode deixar a partida presa no próprio turno por
    # atingir o limite defensivo do loop.
    if current.get("status") == "active" and str(current.get("turn")) == ai_uid:
        fallback = aplicar_jogada(current, ai_user_id, action="pass")
        if "error" not in fallback:
            current = fallback["state"]
    return current

def calcular_delta_mmr(rating_a: int, rating_b: int, resultado_a: float, k_factor: int = 32) -> int:
    """Calcula a variação Elo do jogador A; o jogador B recebe o valor oposto."""
    rating_a = max(0, int(rating_a))
    rating_b = max(0, int(rating_b))
    resultado = float(resultado_a)
    if resultado not in (0.0, 0.5, 1.0):
        raise ValueError("resultado_a deve ser 0.0, 0.5 ou 1.0")
    k = max(1, int(k_factor))
    esperado_a = 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
    return int(round(k * (resultado - esperado_a)))


def calcular_xp_partida(outcome: str, xp_recente: int = 0, limite_diario: int = 30) -> int:
    """Retorna XP da partida, respeitando o teto diário informado pelo chamador."""
    recompensas = {"win": 30, "draw": 20, "loss": 10}
    chave = str(outcome or "").strip().lower()
    if chave not in recompensas:
        raise ValueError("outcome deve ser 'win', 'draw' ou 'loss'")
    limite = max(0, int(limite_diario))
    acumulado = max(0, int(xp_recente))
    restante = max(0, limite - acumulado)
    return min(recompensas[chave], restante)
