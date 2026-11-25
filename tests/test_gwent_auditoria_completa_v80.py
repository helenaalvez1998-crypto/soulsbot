from sistemas.cartas import (
    CARTAS_POR_ID, CARTAS_PATENTE, CARTAS_PRIMORDIAIS, _CARTAS_BASE, HABILIDADES,
    VERSAO_ARTES, carta_jogo,
)
from sistemas.gwent import CARD_IDENTITY_ABILITIES, CARD_SYNERGY_TAGS, RARITY_EFFECT_BUDGET, preparar_carta
from sistemas.arte_cartas import _dados_habilidade_visual, _id_habilidade_visual


def test_all_122_cards_keep_effect_rarity_and_story_separate():
    assert len(CARTAS_POR_ID) == 122
    for card in CARTAS_POR_ID.values():
        prepared = preparar_carta(card.para_dict())
        assert prepared["habilidade_texto"]
        assert "Raridade " not in prepared["habilidade_texto"]
        assert prepared["descricao"] != prepared["habilidade_texto"]
        if prepared["habilidade_identidade"]:
            identity = CARD_IDENTITY_ABILITIES[card.id]
            assert prepared["habilidade"] == ""
            assert prepared["habilidade_nome"] == identity["name"]
            assert prepared["habilidade_texto"] == identity["text"]
        elif not prepared["habilidade"] and CARD_SYNERGY_TAGS.get(card.id):
            assert "combo compatível" in prepared["habilidade_texto"].casefold()
        elif not prepared["habilidade"]:
            assert "não possui uma habilidade de combate própria" in prepared["habilidade_texto"]
        assert len(prepared["habilidade_texto"]) <= 420


def test_rarity_messages_describe_the_real_limit_for_each_special_card():
    def text(card_id, rarity=None):
        data = CARTAS_POR_ID[card_id].para_dict()
        if rarity:
            data["raridade"] = rarity
        return preparar_carta(data)["raridade_texto"]

    assert "1 marca" in text("gwent_especial_nevoa", "Rara")
    assert "2 marcas" in text("gwent_especial_nevoa", "Lendária")
    assert "até 5" in text("gwent_especial_medico", "Rara")
    assert "até 7" in text("gwent_especial_requiem", "Épica")
    assert "até 2 cartas" in text("gwent_especial_batedor", "Rara")
    assert "até 2 aliados" in text("gwent_especial_egide", "Rara")
    assert "até 2 aliados" in text("gwent_especial_passo", "Rara")
    assert "4 de poder-base" in text("elden_especial_invocacao", "Rara")
    assert "primeiro inimigo" in text("elden_especial_sangramento", "Rara")
    assert "continua limitado a 6 de poder atual" in text("gwent_especial_execucao", "Épica")


def test_rarity_budget_matches_the_existing_game_rules():
    assert RARITY_EFFECT_BUDGET == {
        "Comum": 0, "Rara": 1, "Épica": 1, "Lendária": 2,
        "Mítica": 2, "Primordial": 3, "Singular": 3,
    }


def test_card_art_uses_the_effective_mechanical_text_not_lore_or_hidden_skill():
    for card_id in CARTAS_POR_ID:
        card = CARTAS_POR_ID[card_id].para_dict()
        prepared = preparar_carta(card)
        art_name, art_text = _dados_habilidade_visual(card)
        assert art_name == prepared["habilidade_nome"]
        assert art_text == prepared["habilidade_texto"]
        assert art_text != prepared["descricao"]


def test_dynamic_game_rewards_keep_lore_out_of_the_effect_description():
    for i in range(30):
        for milestone in ("zerado", "platina"):
            card = carta_jogo(f"Auditoria v80 {i}", milestone).para_dict()
            prepared = preparar_carta(card)
            assert prepared["descricao"]
            assert prepared["habilidade_texto"]
            assert prepared["descricao"] != prepared["habilidade_texto"]
            assert "Habilidade:" not in prepared["descricao"]
            lore = prepared["descricao"].casefold()
            assert "ganha +" not in lore and "reduz em" not in lore and "aplica " not in lore

    from sistemas.cartas import CARTAS_PATENTE
    for patent in CARTAS_PATENTE:
        lore = patent.descricao.casefold()
        assert "ganha +" not in lore and "reduz em" not in lore and "aplica " not in lore


def test_art_version_was_bumped_to_refresh_existing_card_images():
    assert VERSAO_ARTES == 33
    app = __import__("pathlib").Path("site/app.js").read_text(encoding="utf-8")
    index = __import__("pathlib").Path("site/index.html").read_text(encoding="utf-8")
    assert "const CARD_IMAGE_VERSION = 33" in app
    assert "searchParams.set('v','21')" not in index


def test_rarity_copy_is_direct_and_does_not_promise_effects_that_are_not_executed():
    by_id = lambda card_id, rarity=None: preparar_carta({**CARTAS_POR_ID[card_id].para_dict(), **({"raridade": rarity} if rarity else {})})
    mythic = by_id("chefe_guardiao_cinzas", "Mítica")["raridade_texto"]
    assert "até 2 unidades" in mythic
    assert "+1" in mythic and "poder-base" in mythic and "escudos" in mythic
    purificar = by_id("gwent_especial_purificar", "Mítica")["raridade_texto"]
    assert "não altera o efeito desta carta" in purificar
    necromante = by_id("gwent_unidade_necromante", "Rara")["raridade_texto"]
    assert "não muda o efeito próprio" in necromante and "combo" in necromante

def test_card_details_keep_combo_text_separate_and_power_math_matches_engine():
    from pathlib import Path
    app = Path("site/app.js").read_text(encoding="utf-8")
    index = Path("site/index.html").read_text(encoding="utf-8")
    assert "gwentEffectivePower(card, weatherValue)" in app
    assert "PODER-BASE" in app and "COMBOS POSSÍVEIS" in app
    assert "Combos possíveis" in index
    assert "String(s).replaceAll('_',' ')" not in index


def test_ability_copy_matches_known_edge_conditions():
    def ability(card_id):
        return preparar_carta(CARTAS_POR_ID[card_id].para_dict())["habilidade_texto"]
    assert "Sacrifícios ignoram o escudo" in HABILIDADES["escudo_ferro"]["texto"]
    assert "a ordem em que aparecem no campo" in preparar_carta(CARTAS_POR_ID["gwent_especial_passo"].para_dict())["habilidade_texto"]
    relic_text = preparar_carta(CARTAS_POR_ID["reliquia_noite_chama"].para_dict())["habilidade_texto"]
    assert "Relíquia é consumida" in relic_text

def test_rarity_for_marks_does_not_claim_a_false_negative_floor():
    for card_id in ("elden_especial_podrida", "elden_especial_loucura"):
        text = preparar_carta(CARTAS_POR_ID[card_id].para_dict())["raridade_texto"]
        if text:
            assert "até -2" not in text


def test_solo_and_sacrifice_cards_do_not_treat_themselves_as_allies():
    from copy import deepcopy
    from sistemas import cartas, gwent

    catalog = {card.id: card.para_dict() for card in cartas.CARTAS_POR_ID.values()}

    def state_with_card(card_id):
        card = deepcopy(catalog[card_id])
        filler = [deepcopy(data) for cid, data in catalog.items()
                  if cid not in {card_id, "chefe_guardiao_cinzas"} and not data.get("especial")]
        state = gwent.novo_estado(980, 180, 280, {
            "180": [card] + filler[:11],
            "280": filler[11:23],
        })
        state["phase"] = "battle"
        state["turn"] = "180"
        for player in state["players"].values():
            player["mulligan_done"] = True
        state["players"]["180"]["hand"] = [card, deepcopy(filler[0])]
        state["players"]["180"]["board"] = []
        state["players"]["280"]["board"] = [
            gwent.preparar_carta(deepcopy(catalog["chefe_guardiao_cinzas"])) | {"row": "melee", "bonus": 0}
        ]
        return state, card

    # O bônus do Caçador Solitário só deve entrar quando não há outro aliado na fileira.
    state, solo = state_with_card("gwent_singular_primeiro")
    result = gwent.aplicar_jogada(state, 180, card_id=solo["id"], action="play", row="melee")
    assert "error" not in result
    played = next(unit for unit in result["state"]["players"]["180"]["board"] if unit["id"] == solo["id"])
    assert played["bonus"] >= 2

    # Devorar não pode sacrificar a própria carta quando não há outro aliado.
    state, devour = state_with_card("gwent_unidade_carniceiro_forja")
    result = gwent.aplicar_jogada(state, 180, card_id=devour["id"], action="play", row="melee")
    assert "error" not in result
    assert any(unit["id"] == devour["id"] for unit in result["state"]["players"]["180"]["board"])


def test_identity_effects_target_other_allies_not_the_card_that_just_entered():
    from sistemas.gwent import _aplicar_habilidade_identidade

    card = {"id": "chefe_guardiao_cinzas", "row": "melee", "bonus": 0, "poder": 5}
    player = {"board": [card], "discard": []}
    other = {"board": []}
    state = {"weather": {}}
    _aplicar_habilidade_identidade(player, other, card, state, "melee")
    assert card["bonus"] == 0  # Sem aliado anterior, a Égide das Cinzas não dá bônus.

    ally = {"id": "ally", "row": "melee", "bonus": 0, "poder": 4}
    card = {"id": "chefe_guardiao_cinzas", "row": "melee", "bonus": 0, "poder": 5}
    player = {"board": [ally, card], "discard": []}
    _aplicar_habilidade_identidade(player, other, card, state, "melee")
    assert ally["bonus"] == 1
    assert card["bonus"] == 1


def test_v75_blood_price_does_not_sacrifice_itself_when_no_other_ally_exists():
    from sistemas.gwent import _aplicar_habilidade_identidade

    card = {"id": "gwent_v75_veu_carrasco_preco", "row": "melee", "bonus": 0, "poder": 5}
    player = {"board": [card], "discard": []}
    _aplicar_habilidade_identidade(player, {"board": []}, card, {"weather": {}}, "melee")
    assert card in player["board"]
    assert card["bonus"] == 1


def test_requiem_explains_that_the_returned_unit_loses_bonus_and_shield():
    text = preparar_carta(CARTAS_POR_ID["gwent_especial_requiem"].para_dict())["habilidade_texto"]
    assert "sem bônus e sem escudo" in text
    assert "mesma fileira em que estava antes de sair" in text


def test_all_122_card_ability_texts_fit_the_card_art_panel_without_clipping():
    from PIL import Image, ImageDraw
    from sistemas.arte_cartas import _wrap, _font
    draw = ImageDraw.Draw(Image.new("RGB", (420, 620)))
    for card in CARTAS_POR_ID.values():
        prepared = preparar_carta(card.para_dict())
        text = prepared["habilidade_texto"]
        fits = any(len(_wrap(draw, text, _font(size), 342)) <= 3 for size in (12, 11, 10, 9))
        if not fits:
            fits = len(_wrap(draw, text, _font(9), 342)) <= 4
        assert fits, f"Texto da carta {card.id} ultrapassa o painel da arte: {text}"


def test_banner_description_matches_that_only_existing_allies_get_the_bonus():
    from copy import deepcopy
    from sistemas import cartas, gwent
    catalog = {card.id: card.para_dict() for card in cartas.CARTAS_POR_ID.values()}
    card = deepcopy(catalog["gwent_mitica_coroa"])
    fillers = [deepcopy(data) for cid, data in catalog.items()
               if cid not in {card["id"], "chefe_guardiao_cinzas"} and not data.get("especial")]
    state = gwent.novo_estado(980, 180, 280, {"180": [card] + fillers[:11], "280": fillers[11:23]})
    state["phase"] = "battle"
    state["turn"] = "180"
    for player in state["players"].values():
        player["mulligan_done"] = True
    own = state["players"]["180"]
    own["hand"] = [card]
    own["board"] = []
    own["faction_boost_used"] = True  # Isola o Estandarte da passiva de facção.
    state["players"]["280"]["board"] = [
        gwent.preparar_carta(deepcopy(catalog["chefe_guardiao_cinzas"])) | {"row": "melee", "bonus": 0}
    ]
    result = gwent.aplicar_jogada(state, 180, card_id=card["id"], action="play", row="melee")
    assert "error" not in result
    board = result["state"]["players"]["180"]["board"]
    banner = next(unit for unit in board if unit["id"] == card["id"])
    assert banner["bonus"] == 0  # A carta que entra não recebe o +1 do Estandarte.

    # Com um aliado já na fileira, só ele recebe o efeito; a raridade reforça esse +1.
    card = deepcopy(catalog["gwent_mitica_coroa"])
    ally = deepcopy(catalog["gwent_unidade_baluarte"])
    state = gwent.novo_estado(981, 180, 280, {"180": [card, ally] + fillers[:10], "280": fillers[11:23]})
    state["phase"] = "battle"
    state["turn"] = "180"
    for player in state["players"].values():
        player["mulligan_done"] = True
    own = state["players"]["180"]
    own["hand"] = [card]
    own["board"] = [gwent.preparar_carta(deepcopy(ally)) | {"row": "melee", "bonus": 0}]
    own["faction_boost_used"] = True
    state["players"]["280"]["board"] = [
        gwent.preparar_carta(deepcopy(catalog["chefe_guardiao_cinzas"])) | {"row": "melee", "bonus": 0}
    ]
    result = gwent.aplicar_jogada(state, 180, card_id=card["id"], action="play", row="melee")
    assert "error" not in result
    board = result["state"]["players"]["180"]["board"]
    banner = next(unit for unit in board if unit["id"] == card["id"])
    existing_ally = next(unit for unit in board if unit["id"] == ally["id"])
    assert banner["bonus"] == 0
    assert existing_ally["bonus"] == 2


def test_last_enemy_played_row_is_described_as_current_round_not_previous_turn():
    from sistemas.cartas import HABILIDADES
    assert "nesta rodada" in HABILIDADES["quebra_ritmo"]["texto"]
    assert "turno anterior" not in HABILIDADES["quebra_ritmo"]["texto"]


def test_card_art_symbols_use_the_effective_skill_not_a_hidden_catalog_skill():
    identity = CARTAS_POR_ID["chefe_guardiao_cinzas"].para_dict()
    assert identity["habilidade"]  # O catálogo antigo ainda guarda um efeito genérico.
    assert _id_habilidade_visual(identity) == ""  # A identidade substitui esse efeito no motor.

    combo_only = CARTAS_POR_ID["arma_lamina_peregrino"].para_dict()
    assert _id_habilidade_visual(combo_only) == ""

    active = CARTAS_POR_ID["reliquia_noite_chama"].para_dict()
    assert _id_habilidade_visual(active) == "reliquia_noite_chama"
