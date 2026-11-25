from sistemas.rituais_ancestrais import RITUAIS_ANCESTRAIS
from sistemas.cartas import get_carta, faixa_poder_exemplar


def test_ritual_ancestral_uses_three_distinct_legendary_units():
    ritual = RITUAIS_ANCESTRAIS["coroa_do_haligtree"]
    assert len(ritual["ingredientes"]) == 3
    assert len({x["card_id"] for x in ritual["ingredientes"]}) == 3
    assert all(x["rarity"] == "Lendária" for x in ritual["ingredientes"])
    assert ritual["fragmentos"] == 250


def test_ritual_result_is_existing_mythic_unit():
    ritual = RITUAIS_ANCESTRAIS["coroa_do_haligtree"]
    result = get_carta(ritual["resultado"]["card_id"])
    assert result is not None
    assert result.categoria.casefold() != "especial"
    assert result.raridade == "Mítica"
    assert ritual["resultado"]["rarity"] == "Mítica"
    low, high = faixa_poder_exemplar(result, "Mítica")
    assert low <= high


def test_ritual_does_not_reference_primordial_or_singular():
    ritual = RITUAIS_ANCESTRAIS["coroa_do_haligtree"]
    assert all(x["rarity"] not in {"Primordial", "Singular"} for x in ritual["ingredientes"])
    assert ritual["resultado"]["rarity"] not in {"Primordial", "Singular"}
