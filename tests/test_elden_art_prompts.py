import unittest

from sistemas.atelie_coliseu import gerar_prompt_carta


class EldenRingArtPromptTests(unittest.TestCase):
    def make_card(self, faction, name, description, card_id="card_test"):
        return {
            "id": card_id,
            "nome": name,
            "categoria": "Unidade",
            "habilidade": "drenagem",
            "raridade": "Comum",
            "tipo": "Força",
            "faccao": faction,
            "fileira": "melee",
            "poder": 4,
            "descricao": description,
        }

    def test_golden_order_prompt_uses_leyndell_world(self):
        prompt = gerar_prompt_carta(self.make_card(
            "Ordem Áurea", "Cavaleiro de Leyndell", "Defende os portões da capital dourada.",
            "chefe_vigia_cinzento",
        ))
        self.assertIn("ORDEM ÁUREA (LIGHT, LAW AND FAITH)", prompt)
        self.assertIn("SETTING CUES — LEYNDELL / ALTUS", prompt)
        self.assertIn("Elden Ring — Terras Intermédias", prompt)
        self.assertNotIn("A massive watchman in battered grey iron", prompt)

    def test_crimson_veil_prompt_uses_mohgwyn_only_when_card_supports_it(self):
        prompt = gerar_prompt_carta(self.make_card(
            "Véu Carmesim", "Cavaleiro da Dinastia Mohgwyn", "Serve ao ritual do palácio de Mohgwyn.",
            "covenant_coroa_abismo",
        ))
        self.assertIn("VÉU CARMESIM (BLOOD, SACRIFICE AND HERESY)", prompt)
        self.assertIn("SETTING CUES — MOHGWYN", prompt)
        self.assertIn("not a claim that every card subject is an official member", prompt)

    def test_dark_moon_prompt_uses_carian_world(self):
        prompt = gerar_prompt_carta(self.make_card(
            "Lua Negra", "Ranni, Bruxa da Lua", "Contempla a Lua Negra sobre Liurnia.",
            "chefe_dama_vazio",
        ))
        self.assertIn("LUA NEGRA (MAGIC, COSMOS AND SECRETS)", prompt)
        self.assertIn("SETTING CUES — LIURNIA / CARIAN LANDS", prompt)
        self.assertNotIn("CONCLAVE ARCANO", prompt)

    def test_prompt_does_not_include_removed_card_cost_or_card_ui(self):
        prompt = gerar_prompt_carta(self.make_card(
            "Ordem Áurea", "Cavaleiro de Leyndell", "Guarda a estrada de Altus."
        ))
        self.assertNotIn("COST:", prompt)
        self.assertIn("CARD ART ONLY", prompt)
        self.assertIn("no card frame", prompt.lower())


    def test_all_catalog_cards_receive_specific_elden_scenes(self):
        from sistemas import cartas
        from sistemas.atelie_coliseu import CENAS_ELDEN_POR_ID

        catalog = cartas.CARTAS_POR_ID
        self.assertEqual(len(CENAS_ELDEN_POR_ID), 107)
        for card_id, card in catalog.items():
            with self.subTest(card_id=card_id):
                prompt = gerar_prompt_carta(card.para_dict())
                self.assertIn("CARD-SPECIFIC VISUAL SCENE", prompt)
                self.assertNotIn("No fixed scene exists", prompt)
                self.assertNotIn("CARD-SPECIFIC CHARACTER CASTING", prompt)
                self.assertNotIn("the randomized appearance profile is only a fallback", prompt.lower())

    def test_canonical_characters_keep_their_actual_elden_ring_identity(self):
        from sistemas import cartas
        samples = {
            "chefe_dama_vazio": ("four arms", "Ranni's Rise", "Dark Moon"),
            "chefe_rei_afogado": ("Godfrey", "Serosh", "greataxe"),
            "gwent_unidade_herdeiro_portao": ("Prince of Death", "Deeproot Depths", "not as a living"),
            "gwent_unidade_senhor_cacada": ("Blaidd", "Half-Wolf", "greatsword"),
            "primordial_eternidade": ("Maliketh", "Destined Death", "Crumbling Farum Azula"),
        }
        for card_id, phrases in samples.items():
            with self.subTest(card_id=card_id):
                prompt = gerar_prompt_carta(cartas.CARTAS_POR_ID[card_id].para_dict())
                for phrase in phrases:
                    self.assertIn(phrase.casefold(), prompt.casefold())

    def test_faction_alignment_never_overwrites_canonical_character_design(self):
        from sistemas import cartas
        prompt = gerar_prompt_carta(cartas.CARTAS_POR_ID["chefe_dama_vazio"].para_dict())
        self.assertIn("the three narabot factions are custom deck allegiances", prompt.lower())
        self.assertIn("do not randomize face, age, gender, species", prompt.lower())

    def test_all_narabot_art_is_locked_to_elden_ring_even_if_origin_metadata_differs(self):
        card = self.make_card("", "Cavaleiro Errante", "Viaja por uma floresta antiga.")
        card["jogo_origem"] = "Universo Original"
        prompt = gerar_prompt_carta(card)
        self.assertIn("Mandatory universe: Elden Ring", prompt)
        self.assertIn("Mandatory 5:4 aspect ratio, horizontal composition.", prompt)
        self.assertIn("Do not mix franchises", prompt)


if __name__ == "__main__":
    unittest.main()
