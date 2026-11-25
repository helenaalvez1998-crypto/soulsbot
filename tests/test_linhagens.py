import importlib.util
import unittest
from pathlib import Path

from sistemas import cartas

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("linhagens_catalogo_test", ROOT / "sistemas" / "linhagens.py")
linhagens = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(linhagens)


class LinhagensCatalogTests(unittest.TestCase):
    def test_recipe_ids_are_unique_and_have_three_distinct_ingredients(self):
        self.assertEqual(len(linhagens.RECEITAS_LINHAGEM), len(set(linhagens.RECEITAS_LINHAGEM)))
        for recipe_id, recipe in linhagens.RECEITAS_LINHAGEM.items():
            with self.subTest(recipe=recipe_id):
                ids = [x["card_id"] for x in recipe["ingredientes"]]
                self.assertEqual(len(ids), 3)
                self.assertEqual(len(set(ids)), 3)

    def test_all_ingredients_and_outputs_match_catalog_rarity(self):
        for recipe_id, recipe in linhagens.RECEITAS_LINHAGEM.items():
            with self.subTest(recipe=recipe_id):
                for ingredient in recipe["ingredientes"]:
                    card = cartas.get_carta(ingredient["card_id"])
                    self.assertIsNotNone(card, ingredient["card_id"])
                    self.assertNotEqual(card.categoria.casefold(), "especial")
                    self.assertEqual(card.raridade, ingredient["rarity"])
                    self.assertNotIn(card.raridade, ("Primordial", "Singular"))
                result = cartas.get_carta(recipe["resultado"]["card_id"])
                self.assertIsNotNone(result, recipe["resultado"]["card_id"])
                self.assertNotEqual(result.categoria.casefold(), "especial")
                self.assertEqual(result.raridade, recipe["resultado"]["rarity"])
                self.assertNotIn(result.raridade, ("Primordial", "Singular"))
                self.assertGreater(recipe["fragmentos"], 0)


if __name__ == "__main__":
    unittest.main()
