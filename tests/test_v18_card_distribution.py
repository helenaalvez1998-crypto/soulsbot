import unittest
from copy import deepcopy
from sistemas import cartas, gwent

class CardDistributionV18Tests(unittest.TestCase):
    def test_unit_collection_is_exactly_half_vanilla(self):
        units = [c for c in cartas.CARTAS_POR_ID.values() if c.categoria.casefold() != "especial"]
        vanilla = [c for c in units if not c.habilidade]
        self.assertEqual(len(vanilla), len(units) // 2)
        self.assertTrue(all(c.poder <= cartas.FAIXA_PODER[c.raridade][1] for c in vanilla))

    def test_high_rarity_bosses_have_unique_identity_effects(self):
        ids = ["chefe_malenia_lamina_miquella", "chefe_radahn_flagelo_estrelas",
               "chefe_maliketh_morte_destinada", "chefe_messmer_impalador",
               "chefe_placidusax_lorde_dragao"]
        for card_id in ids:
            with self.subTest(card_id=card_id):
                self.assertIn(card_id, gwent.CARD_IDENTITY_ABILITIES)

    def test_malenia_applies_scarlet_rot(self):
        card = cartas.get_carta("chefe_malenia_lamina_miquella").para_dict()
        enemy = cartas.get_carta("chefe_guardiao_cinzas").para_dict()
        state = gwent.novo_estado(990, 100, 200, {"100": [card] * 12, "200": [enemy] * 12})
        state["phase"] = "battle"; state["turn"] = "100"
        for side in state["players"].values(): side["mulligan_done"] = True
        state["players"]["100"]["hand"] = [card]
        target = gwent.preparar_carta(deepcopy(enemy)); target.update({"row": "ranged", "bonus": 0})
        state["players"]["200"]["board"] = [target]
        result = gwent.aplicar_jogada(state, 100, card_id=card["id"], action="play", row="ranged")
        self.assertNotIn("error", result)
        self.assertEqual(result["state"]["players"]["200"]["board"][0]["podrida"], 1)
