from pathlib import Path
import unittest
from PIL import Image
from sistemas.renderizador_cartas_premium import TEMPLATE_POR_FACCAO, compor_carta_premium

class PremiumRendererTests(unittest.TestCase):
    def test_template_ordem_aurea_exists_and_has_transparent_art_window(self):
        path = Path(__file__).resolve().parents[1] / "assets" / "cartas" / "premium" / TEMPLATE_POR_FACCAO["Ordem Áurea"]
        self.assertTrue(path.is_file())
        image = Image.open(path).convert("RGBA")
        self.assertEqual(image.size, (1024, 1536))
        self.assertEqual(image.getpixel((500, 500))[3], 0)
        self.assertEqual(image.getpixel((10, 10))[3], 255)

    def test_other_factions_use_safe_legacy_fallback(self):
        self.assertNotIn("Véu Carmesim", TEMPLATE_POR_FACCAO)
        self.assertNotIn("Lua Negra", TEMPLATE_POR_FACCAO)

    def test_seven_distinct_rarity_badges_are_installed(self):
        from sistemas.renderizador_cartas_premium import ASSET_RARIDADE
        root = Path(__file__).resolve().parents[1] / "assets" / "cartas" / "premium" / "raridades"
        self.assertEqual(len(ASSET_RARIDADE), 7)
        for filename in ASSET_RARIDADE.values():
            self.assertTrue((root / filename).is_file(), filename)

    def test_premium_composition_returns_expected_size(self):
        from sistemas.renderizador_cartas_premium import compor_carta_premium
        base = Image.new("RGB", (420, 620), (30, 30, 30))
        card = {"faccao": "Ordem Áurea", "raridade": "Rara", "nome": "Carta de Teste",
                "categoria": "Unidade", "poder": 5, "fileira": "melee", "tipo": "Força",
                "descricao": "Texto de lore de teste."}
        result = compor_carta_premium(card, base, 420, 620)
        self.assertIsNotNone(result)
        self.assertEqual(result.size, (420, 620))

if __name__ == "__main__":
    unittest.main()
