from sistemas.afinidades import (
    AFINIDADES, FACCOES, analisar_compatibilidade, classificar_carta,
    validar_ingredientes,
)


def unit(exemplar_id, card_id, nome, tipo="Força", **extra):
    return {
        "exemplar_id": exemplar_id, "id": card_id, "card_id": card_id,
        "nome": nome, "tipo": tipo, "categoria": "Unidade",
        "raridade": "Rara", "is_sacrificable": 1, **extra,
    }


def test_factions_map_to_existing_three_factions():
    assert classificar_carta({"tipo": "Força"})["faccao"] == "Ordem Áurea"
    assert classificar_carta({"tipo": "Destreza"})["faccao"] == "Véu Carmesim"
    assert classificar_carta({"tipo": "Magia"})["faccao"] == "Lua Negra"
    assert len(FACCOES) == 3


def test_affinity_classifier_can_return_multiple_thematic_tags():
    result = classificar_carta({
        "id": "chefe_maliketh_morte_destinada",
        "nome": "Maliketh, Morte Destinada",
        "tipo": "Força",
    })
    assert "morte" in result["afinidades"]
    assert set(result["afinidades"]) <= set(AFINIDADES)


def test_ingredient_count_and_unique_ids_are_enforced():
    trio = [unit(i, f"unit_{i}", "Cavaleiro") for i in (1, 2, 3)]
    assert validar_ingredientes(trio)[0] is True
    assert validar_ingredientes(trio[:2])[0] is False
    assert validar_ingredientes([trio[0], trio[1], trio[0]])[0] is False
    assert validar_ingredientes(trio + [unit(4, "u4", "Cavaleiro")] * 3)[0] is False


def test_special_primordial_singular_and_personal_cards_are_rejected():
    trio = [unit(i, f"unit_{i}", "Cavaleiro") for i in (1, 2, 3)]
    special = [dict(x) for x in trio]
    special[0]["categoria"] = "Especial"
    assert not validar_ingredientes(special)[0]
    primordial = [dict(x) for x in trio]
    primordial[0]["raridade"] = "Primordial"
    assert not validar_ingredientes(primordial)[0]
    singular = [dict(x) for x in trio]
    singular[0]["raridade"] = "Singular"
    assert not validar_ingredientes(singular)[0]
    personal = [dict(x) for x in trio]
    personal[0]["origin_type"] = "transmutacao"
    personal[0]["is_sacrificable"] = 0
    assert not validar_ingredientes(personal)[0]


def test_compatibility_is_deterministic_and_not_a_probability():
    trio = [
        unit(1, "chefe_maliketh_morte", "Maliketh Morte", tipo="Força"),
        unit(2, "chefe_gurranq_bestial", "Gurranq Bestial", tipo="Força"),
        unit(3, "chefe_messmer_chama", "Messmer Chama", tipo="Magia"),
    ]
    a = analisar_compatibilidade(trio)
    b = analisar_compatibilidade(trio)
    assert a == b
    assert a["valido"] is True
    assert 0 <= a["score"] <= 100
    assert "probabilidade" not in a
    assert {x["id"] for x in a["afinidades"]} >= {"morte", "bestial", "fogo"}
