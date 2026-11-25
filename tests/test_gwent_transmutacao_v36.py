from sistemas.gerador_cartas import gerar_carta_procedural
from sistemas.gwent import preparar_carta_pessoal, HABILIDADES_UNIDADE_IMPLEMENTADAS


def ingredients():
    return [
        {"exemplar_id": 101, "card_id": "chefe_maliketh_morte", "nome": "Maliketh", "categoria": "Unidade", "raridade": "Rara", "tipo": "Força", "is_sacrificable": 1},
        {"exemplar_id": 102, "card_id": "chefe_gurranq_bestial", "nome": "Gurranq", "categoria": "Unidade", "raridade": "Rara", "tipo": "Força", "is_sacrificable": 1},
        {"exemplar_id": 103, "card_id": "chefe_messmer_chama", "nome": "Messmer", "categoria": "Unidade", "raridade": "Rara", "tipo": "Magia", "is_sacrificable": 1},
    ]


def generated():
    return gerar_carta_procedural(
        ingredients(), seed="v36-test-seed", generated_id="transmutacao_test_card_0001"
    )["definition"]


def test_personal_card_is_prepared_for_standard_battle_engine():
    definition = generated()
    card = preparar_carta_pessoal(definition, {
        "id": 9001, "rarity": definition["raridade"], "power": definition["poder"]
    })
    assert card is not None
    assert card["personal_card"] is True
    assert card["card_id"] == definition["card_id"]
    assert card["id"] == f"{definition['card_id']}::9001"
    assert card["categoria"] == "Unidade"
    assert card["poder"] == definition["poder"]
    assert card["habilidade"] == definition["habilidade"]
    if card["habilidade"]:
        assert card["habilidade"] in HABILIDADES_UNIDADE_IMPLEMENTADAS


def test_personal_card_supports_individual_forge_progression():
    definition = generated()
    next_rarity = {"Comum": "Rara", "Rara": "Épica", "Épica": "Lendária", "Lendária": "Mítica"}
    rarity = next_rarity[definition["raridade"]]
    min_power, max_power = {"Comum": (3, 5), "Rara": (4, 6), "Épica": (5, 7), "Lendária": (6, 8), "Mítica": (8, 9)}[rarity]
    power = min_power
    card = preparar_carta_pessoal(definition, {"id": 9002, "rarity": rarity, "power": power})
    assert card is not None
    assert card["raridade"] == rarity
    assert card["poder"] == power


def test_personal_card_rejects_tampered_protection_and_out_of_range_power():
    definition = generated()
    tampered = dict(definition)
    tampered["is_sacrificable"] = True
    assert preparar_carta_pessoal(tampered, {"id": 9003, "rarity": definition["raridade"], "power": definition["poder"]}) is None
    assert preparar_carta_pessoal(definition, {"id": 9004, "rarity": definition["raridade"], "power": 99}) is None


def test_personal_card_rejects_missing_or_invalid_exemplar_identity():
    definition = generated()
    assert preparar_carta_pessoal(definition, {"id": 0, "rarity": definition["raridade"], "power": definition["poder"]}) is None
    assert preparar_carta_pessoal(definition, {"id": 9005, "rarity": "Primordial", "power": 9}) is None


def test_personal_card_rejects_exemplar_identity_and_protection_tampering():
    definition = generated()
    base = {"id": 9100, "card_id": definition["card_id"], "rarity": definition["raridade"],
            "power": definition["poder"], "origin_type": "transmutacao", "is_sacrificable": 0,
            "user_id": 777}
    assert preparar_carta_pessoal(definition, base, owner_id=777) is not None
    assert preparar_carta_pessoal(definition, {**base, "card_id": "transmutacao_other"}, owner_id=777) is None
    assert preparar_carta_pessoal(definition, {**base, "origin_type": "catalogo"}, owner_id=777) is None
    assert preparar_carta_pessoal(definition, {**base, "is_sacrificable": 1}, owner_id=777) is None
    assert preparar_carta_pessoal(definition, {**base, "user_id": 888}, owner_id=777) is None


def test_personal_card_requires_canonical_transmutation_id():
    definition = generated()
    tampered = dict(definition, card_id="catalog_card_001")
    assert preparar_carta_pessoal(tampered, {"id": 9200, "rarity": definition["raridade"],
                                             "power": definition["poder"]}) is None
