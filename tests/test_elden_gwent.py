import unittest
from copy import deepcopy

from sistemas import cartas, gwent


class EldenGwentReworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = {c.id: c.para_dict() for c in cartas.CARTAS_POR_ID.values()}

    def make_state(self, special_id, enemy_id="chefe_guardiao_cinzas"):
        special = deepcopy(self.catalog[special_id])
        filler = [deepcopy(c) for cid, c in self.catalog.items()
                  if cid not in {special_id, enemy_id} and not c.get("especial")]
        deck_a = [special] + filler[:11]
        deck_b = filler[11:23]
        state = gwent.novo_estado(900, 100, 200, {"100": deck_a, "200": deck_b})
        state["phase"] = "battle"
        state["turn"] = "100"
        for player in state["players"].values():
            player["mulligan_done"] = True
        state["players"]["100"]["hand"] = [special, deepcopy(filler[0])]
        enemy = gwent.preparar_carta(deepcopy(self.catalog[enemy_id]))
        enemy["row"] = "melee"
        enemy["bonus"] = 0
        state["players"]["200"]["board"] = [enemy]
        return state, special

    def play_special(self, state, special, row="melee"):
        result = gwent.aplicar_jogada(state, 100, card_id=special["id"], action="play", row=row)
        self.assertNotIn("error", result, result.get("error"))
        return result["state"]

    def test_every_catalog_skill_has_an_engine_handler(self):
        skills = {c.habilidade for c in cartas.CARTAS_POR_ID.values()}
        implemented = set(gwent.HABILIDADES_UNIDADE_IMPLEMENTADAS) | set(gwent.HABILIDADES_ESPECIAIS_IMPLEMENTADAS)
        self.assertFalse(skills - implemented, skills - implemented)

    def test_all_base_powers_fit_rarity_ranges(self):
        for card in cartas.CARTAS_POR_ID.values():
            if card.categoria.casefold() == "especial":
                self.assertEqual(card.poder, 0, card.id)
                continue
            low, high = cartas.FAIXA_PODER[card.raridade]
            self.assertGreaterEqual(card.poder, low, card.id)
            self.assertLessEqual(card.poder, high, card.id)

    def test_factions_and_default_leaders_are_consistent(self):
        self.assertEqual(gwent.FACTIONS["Força"], "Ordem Áurea")
        self.assertEqual(gwent.FACTIONS["Magia"], "Lua Negra")
        self.assertEqual(gwent.FACTIONS["Destreza"], "Véu Carmesim")
        self.assertEqual(gwent.canonical_faction("Casa Cariana"), "Lua Negra")
        self.assertEqual(gwent.canonical_faction("Dinastia Mohgwyn"), "Véu Carmesim")
        for faction, leader_id in gwent.DEFAULT_LEADERS.items():
            self.assertEqual(gwent.LEADERS[leader_id]["faction"], faction)
        legacy_state = gwent.novo_estado(901, 101, 201, {"101": [deepcopy(c) for c in list(self.catalog.values())[:12]], "201": [deepcopy(c) for c in list(self.catalog.values())[12:24]]}, {"101": {"faction": "Casa Cariana"}})
        self.assertEqual(legacy_state["players"]["101"]["faction"], "Lua Negra")

    def test_blood_marks_trigger_on_second_application(self):
        state, special = self.make_state("elden_especial_sangramento")
        special["raridade"] = "Comum"
        state["players"]["100"]["hand"][0]["raridade"] = "Comum"
        state = self.play_special(state, special)
        enemy = state["players"]["200"]["board"][0]
        self.assertEqual(enemy["sangramento"], 1)
        enemy["bonus"] = 1
        state["players"]["100"]["hand"].append(deepcopy(special))
        state["turn"] = "100"
        state = self.play_special(state, special)
        enemy = state["players"]["200"]["board"][0]
        self.assertEqual(enemy["sangramento"], 0)
        self.assertEqual(enemy["bonus"], -1)

    def test_frost_rot_and_madness_reduce_effective_power(self):
        cases = [
            ("elden_especial_geada", "geada"),
            ("elden_especial_podrida", "podrida"),
            ("elden_especial_loucura", "loucura"),
        ]
        for card_id, key in cases:
            with self.subTest(card_id=card_id):
                state, special = self.make_state(card_id)
                special["raridade"] = "Comum"
                state["players"]["100"]["hand"][0]["raridade"] = "Comum"
                before = gwent.pontuacao(state["players"]["200"], state["weather"])
                state = self.play_special(state, special)
                enemy = state["players"]["200"]["board"][0]
                self.assertEqual(enemy[key], 1)
                after = gwent.pontuacao(state["players"]["200"], state["weather"])
                self.assertEqual(after, before - 1)

    def test_fire_cleanses_frost_and_grants_bonus(self):
        state, special = self.make_state("elden_especial_chama")
        ally = gwent.preparar_carta(deepcopy(self.catalog["chefe_guardiao_cinzas"]))
        ally.update({"row": "melee", "bonus": 0, "geada": 1})
        state["players"]["100"]["board"] = [ally]
        state = self.play_special(state, special)
        result = state["players"]["100"]["board"][0]
        self.assertEqual(result["geada"], 0)
        self.assertEqual(result["bonus"], 2)

    def test_spirit_summon_adds_three_power_unit(self):
        state, special = self.make_state("elden_especial_invocacao")
        state = self.play_special(state, special, row="ranged")
        summoned = state["players"]["100"]["board"][0]
        self.assertEqual(summoned["nome"], "Lobos Espirituais")
        self.assertEqual(summoned["poder"], 4)
        self.assertEqual(summoned["row"], "ranged")


    def test_erdtree_combo_applies_card_and_team_bonus(self):
        first = gwent.preparar_carta(deepcopy(self.catalog["chefe_guardiao_cinzas"]))
        second = gwent.preparar_carta(deepcopy(self.catalog["gwent_unidade_sentinela_rubra"]))
        first.update({"row": "melee", "bonus": 0})
        second.update({"row": "melee", "bonus": 0})
        player = {"board": [first], "synergy_used": {}}
        message = gwent._aplicar_combo_de_cartas(player, second)
        self.assertIn("Juramento da Árvore Áurea", message)
        self.assertEqual(second["bonus"], 2)
        self.assertEqual(first["bonus"], 1)

    def test_counterattack_is_distinct_from_retaliation(self):
        for card_id, expected_bonus in (("gwent_unidade_gigante", 3), ("covenant_irmandade_ferro", 1)):
            with self.subTest(card_id=card_id):
                unit = deepcopy(self.catalog[card_id])
                filler = [deepcopy(c) for cid, c in self.catalog.items()
                          if cid not in {card_id, "magia_sol_negro"} and not c.get("especial")]
                deck_a = [unit] + filler[:11]
                deck_b = [deepcopy(self.catalog["magia_sol_negro"])] + filler[11:22]
                state = gwent.novo_estado(901, 101, 201, {"101": deck_a, "201": deck_b})
                state["phase"] = "battle"; state["turn"] = "101"
                for player in state["players"].values():
                    player["mulligan_done"] = True
                state["players"]["101"]["hand"] = [unit, deepcopy(filler[0])]
                state["players"]["101"]["faction_boost_used"] = True
                enemy = gwent.preparar_carta(deepcopy(self.catalog["magia_sol_negro"]))
                enemy["row"] = "melee"; enemy["bonus"] = 0
                state["players"]["201"]["board"] = [enemy]
                result = gwent.aplicar_jogada(state, 101, card_id=card_id, action="play", row="melee")
                self.assertNotIn("error", result)
                played = next(c for c in result["state"]["players"]["101"]["board"] if c["id"] == card_id)
                self.assertEqual(played["bonus"], expected_bonus)


    def test_execution_respects_six_effective_power_limit(self):
        state, special = self.make_state("gwent_especial_execucao", enemy_id="primordial_origem")
        options = gwent.opcoes_de_alvo(state, 100)
        self.assertEqual(options[special["id"]]["opcoes"], [])
        result = gwent.aplicar_jogada(state, 100, card_id=special["id"], action="play", row="melee")
        self.assertIn("error", result)
        self.assertEqual(len(state["players"]["200"]["board"]), 1)

    def test_removed_unit_loses_temporary_statuses(self):
        unit = {"id": "target", "nome": "Alvo", "poder": 5, "bonus": 0, "row": "melee",
                "escudo": 0, "sangramento": 1, "geada": 1, "podrida": 1, "loucura": 1}
        side = {"board": [unit], "discard": [], "baixas": 0}
        gwent._remover_unidade(side, unit)
        self.assertEqual(len(side["discard"]), 1)
        self.assertTrue(all(side["discard"][0][key] == 0 for key in
                            ("sangramento", "geada", "podrida", "loucura")))

    def test_new_faction_combos_are_registered(self):
        self.assertIn("juramento_erdtree", gwent.SYNERGY_COMBOS)
        self.assertIn("convergencia_lunar", gwent.SYNERGY_COMBOS)
        self.assertIn("ritual_dinastia", gwent.SYNERGY_COMBOS)
        for combo_id in ("juramento_erdtree", "convergencia_lunar", "ritual_dinastia"):
            self.assertGreaterEqual(gwent.SYNERGY_COMBOS[combo_id]["bonus"], 2)

    def test_unit_must_use_its_assigned_row(self):
        card = deepcopy(self.catalog["arma_lamina_peregrino"])
        filler = [deepcopy(c) for cid, c in self.catalog.items() if cid != card["id"] and not c.get("especial")]
        state = gwent.novo_estado(902, 102, 202, {"102": [card] + filler[:11], "202": filler[11:23]})
        state["phase"] = "battle"; state["turn"] = "102"
        for player in state["players"].values(): player["mulligan_done"] = True
        state["players"]["102"]["hand"] = [card]
        rejected = gwent.aplicar_jogada(state, 102, card_id=card["id"], action="play", row="siege")
        self.assertIn("error", rejected)
        accepted = gwent.aplicar_jogada(state, 102, card_id=card["id"], action="play", row="melee")
        self.assertNotIn("error", accepted)

    def test_identity_skill_replaces_hidden_generic_skill(self):
        card = deepcopy(self.catalog["chefe_guardiao_cinzas"])
        filler = [deepcopy(c) for cid, c in self.catalog.items() if cid != card["id"] and not c.get("especial")]
        state = gwent.novo_estado(903, 103, 203, {"103": [card] + filler[:11], "203": filler[11:23]})
        state["phase"] = "battle"; state["turn"] = "103"
        for player in state["players"].values(): player["mulligan_done"] = True
        state["players"]["103"]["hand"] = [card]
        state["players"]["103"]["faction_boost_used"] = True
        state["players"]["203"]["last_row"] = "melee"
        result = gwent.aplicar_jogada(state, 103, card_id=card["id"], action="play", row="melee")
        self.assertNotIn("error", result)
        played = result["state"]["players"]["103"]["board"][0]
        # A identidade Égide das Cinzas não tem aliado para fortalecer; quebra_ritmo
        # não pode ser aplicado silenciosamente por baixo da descrição.
        self.assertEqual(played["bonus"], 0)

    def test_effective_power_includes_weather_for_execution(self):
        state, special = self.make_state("gwent_especial_execucao", enemy_id="primordial_origem")
        enemy = state["players"]["200"]["board"][0]
        enemy["row"] = "melee"
        state["weather"]["melee"] = 2
        options = gwent.opcoes_de_alvo(state, 100)
        self.assertEqual(len(options[special["id"]]["opcoes"]), 1)
        result = gwent.aplicar_jogada(state, 100, card_id=special["id"], action="play", row="melee")
        self.assertNotIn("error", result)

    def test_rot_and_madness_have_distinct_second_mark_effects(self):
        for card_id, status, initial_bonus, expected_bonus in (
            ("elden_especial_podrida", "podrida", 2, 0),
            ("elden_especial_loucura", "loucura", 2, -1),
        ):
            with self.subTest(card_id=card_id):
                state, special = self.make_state(card_id)
                enemy = state["players"]["200"]["board"][0]
                enemy["bonus"] = initial_bonus
                enemy[status] = 1
                state = self.play_special(state, special)
                updated = state["players"]["200"]["board"][0]
                self.assertEqual(updated[status], 2)
                self.assertEqual(updated["bonus"], expected_bonus)

    def test_faction_passive_is_equal_for_all_factions(self):
        self.assertEqual(set(gwent.FACTION_BOOST.values()), {1})

    def test_catalog_units_have_valid_assigned_rows(self):
        for card in self.catalog.values():
            if card.get("especial"):
                continue
            self.assertIn(card.get("fileira"), gwent.ROWS, card["id"])


    def test_rarity_increases_numeric_effect_without_changing_base_power(self):
        base = deepcopy(self.catalog["chefe_guardiao_cinzas"])
        common = gwent.preparar_carta({**base, "raridade": "Comum"})
        rare = gwent.preparar_carta({**base, "raridade": "Rara"})
        self.assertEqual(common["poder"], rare["poder"])
        self.assertEqual(common["potencia_raridade"], 0)
        self.assertEqual(rare["potencia_raridade"], 1)

        def play(card):
            state = gwent.novo_estado(901, 100, 200, {"100": [card] + [deepcopy(base)] * 11,
                                                       "200": [deepcopy(base)] * 12})
            state["phase"] = "battle"
            state["turn"] = "100"
            for side in state["players"].values():
                side["mulligan_done"] = True
            ally = gwent.preparar_carta(deepcopy(self.catalog["chefe_vigia_cinzento"]))
            ally.update({"row": "melee", "bonus": 0})
            side = state["players"]["100"]
            side["hand"] = [card]
            side["board"] = [ally]
            result = gwent.aplicar_jogada(state, 100, card_id=card["id"], action="play", row="melee")
            return result["state"]["players"]["100"]["board"]

        common_board = play(common)
        rare_board = play(rare)
        self.assertGreater(
            sum(int(u.get("bonus", 0)) for u in rare_board),
            sum(int(u.get("bonus", 0)) for u in common_board),
        )

    def test_rarity_bonus_is_bounded_and_visible_in_card_text(self):
        mythic = gwent.preparar_carta({**self.catalog["gwent_especial_chifre"], "raridade": "Mítica"})
        singular = gwent.preparar_carta({**self.catalog["gwent_especial_chifre"], "raridade": "Singular"})
        self.assertEqual(mythic["potencia_raridade"], 2)
        self.assertEqual(singular["potencia_raridade"], 3)
        values = [gwent.RARITY_EFFECT_BUDGET[r] for r in
                  ("Comum", "Rara", "Épica", "Lendária", "Mítica", "Primordial", "Singular")]
        self.assertEqual(values, [0, 1, 1, 2, 2, 3, 3])
        self.assertIn("Raridade Mítica", mythic["habilidade_texto"])


    def test_rarity_improves_status_and_weather_specials(self):
        state, blood = self.make_state("elden_especial_sangramento")
        state = self.play_special(state, blood)
        enemy = state["players"]["200"]["board"][0]
        self.assertEqual(enemy["sangramento"], 0)
        self.assertEqual(enemy["bonus"], -2)

        state, frost = self.make_state("elden_especial_geada")
        state = self.play_special(state, frost)
        enemy = state["players"]["200"]["board"][0]
        self.assertEqual(enemy["geada"], 2)

        state, mist = self.make_state("gwent_especial_nevoa")
        state = self.play_special(state, mist, row="melee")
        enemy = state["players"]["200"]["board"][0]
        self.assertEqual(enemy["podrida"], 1)
        self.assertEqual(state["weather"]["melee"], 0)

    def test_corrupted_blood_applies_bleed_in_siege_not_weather(self):
        state, special = self.make_state("gwent_especial_chuva")
        enemy = state["players"]["200"]["board"][0]
        enemy["row"] = "siege"
        state = self.play_special(state, special)
        enemy = state["players"]["200"]["board"][0]
        self.assertEqual(enemy["sangramento"], 1)
        self.assertEqual(state["weather"].get("siege", 0), 0)


if __name__ == "__main__":
    unittest.main()
