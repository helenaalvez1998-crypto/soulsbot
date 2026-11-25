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
            "Lua Sombria", "Ranni, Bruxa da Lua", "Contempla a Lua Negra sobre Liurnia.",
            "chefe_dama_vazio",
        ))
        self.assertIn("LUA SOMBRIA (MAGIC, COSMOS AND SECRETS)", prompt)
        self.assertIn("SETTING CUES — LIURNIA / CARIAN LANDS", prompt)
        self.assertNotIn("CONCLAVE ARCANO", prompt)

    def test_prompt_does_not_include_removed_card_cost_or_card_ui(self):
        prompt = gerar_prompt_carta(self.make_card(
            "Ordem Áurea", "Cavaleiro de Leyndell", "Guarda a estrada de Altus."
        ))
        self.assertNotIn("COST:", prompt)
        self.assertIn("CARD ART ONLY", prompt)
        self.assertIn("no card frame", prompt.lower())

    def test_non_elden_origin_does_not_receive_lands_between_setting(self):
        card = self.make_card("", "Cavaleiro Errante", "Viaja por uma floresta antiga.")
        card["jogo_origem"] = "Universo Original"
        prompt = gerar_prompt_carta(card)
        self.assertNotIn("ELDEN RING WORLD", prompt)
        self.assertIn("Universo Original", prompt)


if __name__ == "__main__":
    unittest.main()
