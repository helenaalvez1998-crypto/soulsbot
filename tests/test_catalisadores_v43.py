import pytest
from sistemas.catalisadores import CATALISADORES, obter_efeito, validar_afinidade
from sistemas.economia_transmutacao import calcular_orcamento


def test_catalog_has_named_material_costs_and_distinct_effects():
    assert len(CATALISADORES) >= 4
    for key in CATALISADORES:
        effect = obter_efeito(key)
        assert effect.custo


def test_grace_ash_adds_five_percentage_points_and_consumable():
    quote = calcular_orcamento("Épica", 0, False, catalyst_key="cinza_da_graca")
    assert quote.final_chance == 50
    assert quote.costs["cinza_da_graca"] == 1


def test_affinity_catalysts_require_matching_ingredients():
    effect = obter_efeito("residuo_cariano")
    assert validar_afinidade(effect, ["lua", "magia"])
    assert not validar_afinidade(effect, ["fogo", "sangue"])


def test_unknown_catalyst_is_rejected():
    with pytest.raises(ValueError):
        obter_efeito("catalisador_inventado")


def test_chance_cap_remains_ninety_percent():
    quote = calcular_orcamento("Comum", 100, True, catalyst_key="cinza_da_graca")
    assert quote.final_chance == 90
