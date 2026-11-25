import unittest

from sistemas.cartas import CARTAS_POR_ID, _CARTAS_BASE, CARTAS_PRIMORDIAIS, CARTAS_PATENTE
from sistemas.gwent import CARD_IDENTITY_ABILITIES, preparar_carta


class CardCatalogQualityTests(unittest.TestCase):
    def test_identity_faction_is_independent_from_mechanical_type(self):
        blaidd = CARTAS_POR_ID["gwent_unidade_senhor_cacada"].para_dict()
        carrasco = CARTAS_POR_ID["gwent_unidade_carniceiro_forja"].para_dict()
        self.assertEqual(blaidd["tipo"], "Destreza")
        self.assertEqual(blaidd["faccao"], "Lua Negra")
        self.assertEqual(carrasco["tipo"], "Força")
        self.assertEqual(carrasco["faccao"], "Véu Carmesim")

    def test_crisol_card_names_are_unique(self):
        names = [card.nome for card in CARTAS_POR_ID.values()]
        self.assertEqual(names.count("Juramento do Crisol"), 1)
        self.assertIn("Juramento Primordial do Crisol", names)

    def test_relic_texts_explain_actual_mechanical_conditions(self):
        expected = {
            "reliquia_grande_runa_godrick": ("ao menos uma unidade aliada", "+1"),
            "reliquia_runa_nao_nascidos": ("geada e podridão", "purificada"),
            "reliquia_runa_morte": ("cada fileira", "bônus positivo"),
            "reliquia_noite_chama": ("aplica geada", "escudo"),
            "reliquia_lamina_negra": ("reduz em 3", "escudo"),
            "reliquia_algemas_margit": ("bônus negativos", "zera o bônus positivo"),
        }
        for card_id, fragments in expected.items():
            text = preparar_carta(CARTAS_POR_ID[card_id].para_dict())["habilidade_texto"].casefold()
            with self.subTest(card_id=card_id):
                for fragment in fragments:
                    self.assertIn(fragment, text)

    def test_all_122_catalog_cards_have_narrative_description(self):
        cards = [*_CARTAS_BASE, *CARTAS_PRIMORDIAIS, *CARTAS_PATENTE]
        self.assertEqual(len(cards), 122)
        missing = [card.id for card in cards if not card.descricao.strip()]
        self.assertEqual(missing, [])

    def test_identity_cards_show_effective_identity_text_in_game_and_art(self):
        from sistemas.arte_cartas import _dados_habilidade_visual
        for card_id, identity in CARD_IDENTITY_ABILITIES.items():
            card = CARTAS_POR_ID[card_id]
            prepared = preparar_carta(card.para_dict())
            with self.subTest(card_id=card_id):
                self.assertEqual(prepared["habilidade_nome"], identity["name"])
                self.assertTrue(prepared["habilidade_texto"].startswith(identity["text"]))
                self.assertEqual(_dados_habilidade_visual(card.para_dict()), (prepared["habilidade_nome"], prepared["habilidade_texto"]))

    def test_status_specials_describe_the_actual_status_handlers(self):
        expected = {
            "gwent_especial_nevoa": ("podridão escarlate", "fileira escolhida"),
            "gwent_especial_geada": ("geada", "unidades inimigas em campo"),
        }
        for card_id, fragments in expected.items():
            prepared = preparar_carta(CARTAS_POR_ID[card_id].para_dict())
            text = prepared["habilidade_texto"].casefold()
            with self.subTest(card_id=card_id):
                for fragment in fragments:
                    self.assertIn(fragment, text)

    def test_non_scaling_specials_do_not_claim_rarity_scaling(self):
        for card_id in ("gwent_especial_queima", "gwent_especial_purificar"):
            text = preparar_carta(CARTAS_POR_ID[card_id].para_dict())["habilidade_texto"].casefold()
            with self.subTest(card_id=card_id):
                self.assertNotIn("potência", text)

    def test_identity_cards_do_not_keep_old_mechanical_text_as_lore(self):
        for card_id in CARD_IDENTITY_ABILITIES:
            card = CARTAS_POR_ID[card_id]
            with self.subTest(card_id=card_id):
                self.assertTrue(card.descricao.strip())
                self.assertNotIn("recebe +", card.descricao.casefold())
                self.assertNotIn("reduz em ", card.descricao.casefold())

    def test_units_without_skill_do_not_advertise_rarity_power(self):
        card = CARTAS_POR_ID["chefe_cervo_sombrio"].para_dict()
        prepared = preparar_carta(card)
        self.assertEqual(prepared["potencia_raridade"], 0)
        self.assertNotIn("potência", prepared["habilidade_texto"].casefold())

    def test_corrupted_blood_text_matches_siege_bleed_handler(self):
        card = preparar_carta(CARTAS_POR_ID["gwent_especial_chuva"].para_dict())
        text = card["habilidade_texto"].casefold()
        self.assertIn("sangramento", text)
        self.assertIn("cerco", text)
        self.assertNotIn("clima", text)


if __name__ == "__main__":
    unittest.main()
