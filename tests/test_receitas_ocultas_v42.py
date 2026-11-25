from sistemas.receitas_ocultas import RECEITAS_OCULTAS, avaliar_descoberta, descobrir_receitas


def make_items(recipe_id):
    recipe = RECEITAS_OCULTAS[recipe_id]
    return [{"exemplar_id": i + 1, "card_id": card_id, "raridade": rarity,
             "categoria": "Unidade", "is_sacrificable": True}
            for i, (card_id, rarity) in enumerate(recipe["ingredientes"].items())]


def test_all_hidden_recipes_discover_exact_ingredient_sets():
    for recipe_id in RECEITAS_OCULTAS:
        items = make_items(recipe_id)
        result = avaliar_descoberta(items)
        assert result["valid"] is True
        assert [x["recipe_id"] for x in descobrir_receitas(items)] == [recipe_id]


def test_recipe_discovery_is_order_independent():
    items = make_items("trindade_lunar_oculta")
    assert descobrir_receitas(items) == descobrir_receitas(list(reversed(items)))


def test_near_match_does_not_unlock_recipe():
    items = make_items("trindade_lunar_oculta")
    items[0]["raridade"] = "Rara"
    assert descobrir_receitas(items) == []


def test_invalid_and_duplicate_exemplars_are_rejected():
    items = make_items("trindade_lunar_oculta")
    items[1]["exemplar_id"] = items[0]["exemplar_id"]
    result = avaliar_descoberta(items)
    assert result["valid"] is False
