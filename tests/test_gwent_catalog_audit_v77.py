import re

from sistemas.cartas import (
    CARTAS_POR_ID, CARTAS_PATENTE, CARTAS_PRIMORDIAIS, CARTAS_EXPANSAO_V75,
    CARTAS_SEM_EFEITO_IDS, _CARTAS_BASE, RARIDADES, FAIXA_PODER, HABILIDADES,
    FACCOES_IDENTIDADE_POR_CARTA, carta_jogo,
)
from sistemas.gwent import (
    CARD_IDENTITY_ABILITIES, FACTION_ARCHETYPES, _aplicar_habilidade_identidade,
    preparar_carta, novo_estado, aplicar_jogada, contar_faccoes_deck,
)

V75_IDENTITY_IDS = {
    "gwent_v75_ordem_veterano_juramento", "gwent_v75_ordem_confessora_graca",
    "gwent_v75_veu_acolito_sangue", "gwent_v75_veu_carrasco_preco",
    "gwent_v75_lua_oraculo_geada", "gwent_v75_lua_graviturgista",
}


def _all_cards():
    return [*_CARTAS_BASE, *CARTAS_PRIMORDIAIS, *CARTAS_PATENTE]


def test_complete_catalog_has_unique_ids_names_and_valid_stats():
    cards = _all_cards()
    assert len(cards) == 122
    assert len({card.id for card in cards}) == len(cards)
    assert len({card.nome for card in cards}) == len(cards)
    for card in cards:
        assert card.raridade in RARIDADES
        assert card.tipo in {"Força", "Destreza", "Magia"}
        assert card.para_dict()["faccao"] in FACTION_ARCHETYPES
        assert card.para_dict()["fileira"] in {"melee", "ranged", "siege"}
        if card.categoria.casefold() == "especial":
            assert card.poder == 0
        else:
            low, high = FAIXA_PODER[card.raridade]
            assert low <= card.poder <= high
        assert not card.habilidade or card.habilidade in HABILIDADES


def test_v75_has_six_identity_cards_and_six_combo_only_cards():
    assert len(CARTAS_EXPANSAO_V75) == 12
    for card in CARTAS_EXPANSAO_V75:
        prepared = preparar_carta(card.para_dict())
        if card.id in V75_IDENTITY_IDS:
            assert card.id in CARD_IDENTITY_ABILITIES
            assert prepared["habilidade_identidade"] is True
            assert prepared["habilidade_texto"] != "Sem habilidade especial."
            row = card.fileira or "melee"
            result = _aplicar_habilidade_identidade(
                {"board": [], "discard": []}, {"board": []},
                {"id": card.id, "bonus": 0, "poder": card.poder, "row": row},
                {"weather": {"melee": 0, "ranged": 0, "siege": 0}}, row,
            )
            assert result == CARD_IDENTITY_ABILITIES[card.id]["name"]
        else:
            assert card.id not in CARD_IDENTITY_ABILITIES
            assert prepared["habilidade_identidade"] is False
            assert "combo compatível" in prepared["habilidade_texto"].casefold()


def test_identity_cards_also_display_their_general_skill():
    card = CARTAS_POR_ID["chefe_guardiao_cinzas"]
    prepared = preparar_carta(card.para_dict())
    assert "Égide das Cinzas" in prepared["habilidade_nome"]
    assert "Ruptura de Postura" in prepared["habilidade_nome"]
    assert "Habilidade adicional:" in prepared["habilidade_texto"]
    assert "Ganha +1 de poder se o adversário jogou uma unidade na mesma fileira" in prepared["habilidade_texto"]


def test_balance_pass_cards_do_not_claim_effects_that_the_engine_removes():
    mechanical_claim = re.compile(
        r"\b(recebe|concede|fortalece|reduz|remove|aplica|marca|sacrifica|consome|"
        r"compra|traz|permanece|ignora|bloqueia|desvia|amplifica|coordena|"
        r"ataca melhor|luta melhor|cada vitória|quando cai|ao entrar|se houver|"
        r"se você|ao fim|pune)\b", re.IGNORECASE,
    )
    for card_id in CARTAS_SEM_EFEITO_IDS:
        card = CARTAS_POR_ID[card_id]
        assert not card.habilidade
        assert card_id not in CARD_IDENTITY_ABILITIES
        assert not mechanical_claim.search(card.descricao), (card_id, card.descricao)


def test_patent_rewards_use_faction_consistent_titles():
    expected = {
        "Força": ("Leyndell", "Áurea"),
        "Destreza": ("Sanguíneo", "Mohgwyn"),
        "Magia": ("Cariano", "Raya Lucaria"),
    }
    for card in CARTAS_PATENTE:
        assert any(token in card.nome for token in expected[card.tipo]), (card.id, card.nome)


def test_game_rewards_keep_name_region_and_faction_in_the_same_archetype():
    expected = {
        "Força": ("Leyndell", "Áurea", "Crisol"),
        "Destreza": ("Sanguíneo", "Mohgwyn", "Volcano Manor", "Ravenmount"),
        "Magia": ("Cariano", "Liurnia", "Raya Lucaria"),
    }
    rewards = [carta_jogo(f"Jogo de Auditoria {i}", milestone)
               for i in range(30) for milestone in ("zerado", "platina")]
    for card in rewards:
        assert any(token in card.nome for token in expected[card.tipo]), (card.id, card.nome)
        assert card.descricao.endswith(".")
        assert len(card.descricao) <= 240


def test_explicit_faction_overrides_are_applied_to_card_payloads():
    expected = {
        "chefe_oraculo_ruina": "Ordem Áurea",
        "primordial_tempestade": "Lua Negra",
        "arma_martelo_fornalha": "Véu Carmesim",
        "arma_duas_luas": "Lua Negra",
        "magia_selo_vigilia": "Ordem Áurea",
        "magia_sol_negro": "Véu Carmesim",
        "covenant_lua_velada": "Lua Negra",
        "covenant_coroa_abismo": "Véu Carmesim",
        "gwent_unidade_cavaleira": "Lua Negra",
        "gwent_unidade_cartografa": "Lua Negra",
        "gwent_unidade_mestre_forja": "Véu Carmesim",
        "gwent_unidade_devorador_mana": "Véu Carmesim",
    }
    for card_id, faction in expected.items():
        assert FACCOES_IDENTIDADE_POR_CARTA[card_id] == faction
        assert CARTAS_POR_ID[card_id].para_dict()["faccao"] == faction


def test_identity_registry_has_no_orphan_cards_or_unimplemented_effects():
    ids = {card.id for card in _all_cards()}
    assert set(CARD_IDENTITY_ABILITIES).issubset(ids)
    source = open(__file__.replace("tests/test_gwent_catalog_audit_v77.py", "sistemas/gwent.py"), encoding="utf-8").read()
    dispatched = set(re.findall(r'effect\s*==\s*"([^"]+)"', source))
    registered = {item["effect"] for item in CARD_IDENTITY_ABILITIES.values()}
    assert registered <= dispatched
    assert max(len(preparar_carta(card.para_dict())["habilidade_texto"]) for card in _all_cards()) <= 420


def test_faction_override_controls_deck_count_and_round_passive():
    model = CARTAS_POR_ID["covenant_lua_velada"]
    payload = preparar_carta(model.para_dict())
    assert payload["tipo"] == "Destreza"
    assert payload["faccao"] == "Lua Negra"
    counts = contar_faccoes_deck([payload])
    assert counts["Lua Negra"] == 1
    assert counts["Véu Carmesim"] == 0

    filler_a = [preparar_carta(model.para_dict()) for _ in range(12)]
    filler_b = [preparar_carta(model.para_dict()) for _ in range(12)]
    state = novo_estado(1777, 1, 2, {"1": filler_a, "2": filler_b}, {
        "1": {"faction": "Lua Negra"}, "2": {"faction": "Lua Negra"}
    })
    player = state["players"]["1"]
    player["hand"] = [payload, preparar_carta(CARTAS_POR_ID["chefe_guardiao_cinzas"].para_dict())]
    player["draw_pile"] = []
    player["mulligan_done"] = True
    player["faction_boost_used"] = False
    state["players"]["2"]["mulligan_done"] = True
    state["players"]["2"]["passed"] = True
    state["phase"] = "battle"
    state["round"] = 2
    state["turn"] = "1"

    result = aplicar_jogada(state, 1, card_id=payload["id"], action="play", row=payload["row"])
    assert "error" not in result
    played = next(unit for unit in result["state"]["players"]["1"]["board"] if unit["id"] == payload["id"])
    # Aliança Lunar gives +1, Épica potency adds +1, and the faction passive adds +1.
    assert played["bonus"] == 3
