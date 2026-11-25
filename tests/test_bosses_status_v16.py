import unittest
from sistemas.cartas import CARTAS_POR_ID
from sistemas import gwent


class BossesAndStatusesV16Tests(unittest.TestCase):
    def test_five_canonical_bosses_are_in_catalogue(self):
        ids = set(CARTAS_POR_ID)
        expected = {
            "chefe_malenia_lamina_miquella", "chefe_radahn_flagelo_estrelas",
            "chefe_maliketh_morte_destinada", "chefe_messmer_impalador",
            "chefe_placidusax_lorde_dragao",
        }
        self.assertTrue(expected.issubset(ids))

    def test_weather_specials_are_renamed_as_statuses(self):
        from sistemas.cartas import CARTAS_POR_ID
        by_id = CARTAS_POR_ID
        self.assertEqual(by_id["gwent_especial_nevoa"].nome, "Miasma da Podridão")
        self.assertEqual(by_id["gwent_especial_geada"].nome, "Geada dos Picos dos Gigantes")
        self.assertEqual(by_id["gwent_especial_chuva"].nome, "Sangue Corrompido")

    def test_leaders_are_visual_only_contract(self):
        for leader in gwent.LEADERS.values():
            self.assertIn("name", leader)
            self.assertIn("description", leader)
            self.assertNotIn("power", leader)
            self.assertNotIn("cost", leader)


if __name__ == "__main__":
    unittest.main()
