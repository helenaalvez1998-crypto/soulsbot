import unittest
from copy import deepcopy

from sistemas import gwent


class LeaderAbilityV15Tests(unittest.TestCase):
    def make_state(self, leader_id, faction, own_units=None, enemy_units=None, discard=None, weather=None):
        own_units = own_units or []
        enemy_units = enemy_units or []
        deck = [
            {"id": "dummy_a", "nome": "Dummy A", "poder": 3, "bonus": 0, "row": "melee", "especial": False},
            {"id": "dummy_b", "nome": "Dummy B", "poder": 4, "bonus": 0, "row": "ranged", "especial": False},
        ]
        state = {
            "status": "active", "phase": "battle", "turn": "1", "round": 1,
            "players": {
                "1": {"hand": [deepcopy(deck[0])], "draw_pile": [], "discard": deepcopy(discard or []),
                      "board": deepcopy(own_units), "passed": False, "leader_used": False,
                      "weather_used": False, "faction": faction, "leader_id": leader_id,
                      "leader_name": gwent.LEADERS[leader_id]["name"], "faction_boost_used": False,
                      "mulligan_done": True, "last_row": None, "synergy_used": {}, "baixas": 0},
                "2": {"hand": [deepcopy(deck[1])], "draw_pile": [], "discard": [], "board": deepcopy(enemy_units),
                      "passed": False, "leader_used": False, "weather_used": False,
                      "faction": "Ordem Áurea", "leader_id": "comandante_fornalha",
                      "leader_name": "Godfrey", "faction_boost_used": False,
                      "mulligan_done": True, "last_row": None, "synergy_used": {}, "baixas": 0},
            },
            "weather": deepcopy(weather or {"melee": 0, "ranged": 0, "siege": 0}),
            "crowns": {"1": 0, "2": 0}, "rounds": [], "winner_id": None,
        }
        return state

    def unit(self, name, row="melee", power=4, **extra):
        return {"id": name.lower().replace(" ", "_"), "nome": name, "poder": power,
                "bonus": 0, "row": row, "especial": False, "escudo": 0,
                "sangramento": 0, "geada": 0, "podrida": 0, "loucura": 0, **extra}

    def activate(self, state, row="melee"):
        result = gwent.aplicar_jogada(state, 1, action="leader", row=row)
        self.assertNotIn("error", result, result.get("error"))
        return result["state"]

    def test_leader_roster_is_three_unique_bosses_per_faction(self):
        expected = {
            "Ordem Áurea": {"Godfrey", "Morgott", "Radagon"},
            "Véu Carmesim": {"Mohg", "Rykard", "Esgar"},
            "Lua Negra": {"Rennala", "Astel", "Loretta"},
        }
        for faction, names in expected.items():
            self.assertEqual({v["name"] for v in gwent.LEADERS.values() if v["faction"] == faction}, names)
        self.assertEqual(len({v["effect"] for v in gwent.LEADERS.values()}), 9)

    def test_godfrey_strengthens_melee_only(self):
        own = [self.unit("Soldier", "melee"), self.unit("Archer", "ranged")]
        s = self.activate(self.make_state("comandante_fornalha", "Ordem Áurea", own))
        self.assertEqual(s["players"]["1"]["board"][0]["bonus"], 2)
        self.assertEqual(s["players"]["1"]["board"][1]["bonus"], 0)

    def test_morgott_shields_and_bolsters_two_in_selected_row(self):
        own = [self.unit("A", "ranged", 5), self.unit("B", "ranged", 4), self.unit("C", "ranged", 3)]
        s = self.activate(self.make_state("bastiao_ancestral", "Ordem Áurea", own), "ranged")
        board = s["players"]["1"]["board"]
        self.assertEqual([u["escudo"] for u in board], [1, 1, 0])
        self.assertEqual([u["bonus"] for u in board], [1, 1, 0])

    def test_radagon_purifies_and_rewards_only_affected_allies(self):
        own = [self.unit("Cursed", "melee", sangramento=1), self.unit("Clean", "ranged")]
        s = self.activate(self.make_state("juiz_cerco", "Ordem Áurea", own))
        board = s["players"]["1"]["board"]
        self.assertEqual(board[0]["sangramento"], 0)
        self.assertEqual(board[0]["bonus"], 1)
        self.assertEqual(board[1]["bonus"], 0)

    def test_mohg_applies_bleed_and_triggers_second_mark(self):
        enemy = [self.unit("Marked", "melee", sangramento=1), self.unit("Fresh", "melee")]
        s = self.activate(self.make_state("mestre_veu", "Véu Carmesim", enemy_units=enemy))
        board = s["players"]["2"]["board"]
        self.assertEqual(board[0]["bonus"], -2)
        self.assertEqual(board[0]["sangramento"], 0)
        self.assertEqual(board[1]["sangramento"], 1)

    def test_rykard_sacrifices_weakest_and_buffs_survivors(self):
        own = [self.unit("Offering", "melee", 2), self.unit("Devotee", "melee", 5)]
        s = self.activate(self.make_state("sombra_caminhante", "Véu Carmesim", own))
        board = s["players"]["1"]["board"]
        self.assertEqual([u["nome"] for u in board], ["Devotee"])
        self.assertEqual(board[0]["bonus"], 2)
        self.assertEqual(s["players"]["1"]["discard"][0]["nome"], "Offering")

    def test_esgar_revives_best_eligible_unit_into_selected_row(self):
        fallen = [{"id": "fallen", "nome": "Fallen Knight", "poder": 5, "bonus": 0, "row": "melee", "especial": False}]
        s = self.activate(self.make_state("voz_caidos", "Véu Carmesim", discard=fallen), "ranged")
        revived = s["players"]["1"]["board"][0]
        self.assertEqual(revived["row"], "ranged")
        self.assertEqual(revived["bonus"], 1)

    def test_rennala_clears_weather_and_buffs_siege(self):
        own = [self.unit("Mage", "siege", geada=1)]
        s = self.activate(self.make_state("arquimaga_eclipse", "Lua Negra", own, weather={"melee": 2, "ranged": 0, "siege": 1}))
        self.assertEqual(set(s["weather"].values()), {2, 0, 1})
        self.assertEqual(s["players"]["1"]["board"][0]["geada"], 0)
        self.assertEqual(s["players"]["1"]["board"][0]["bonus"], 1)

    def test_astel_applies_gravity_geada_to_three_strongest_in_row(self):
        enemy = [self.unit("A", "melee", 6), self.unit("B", "melee", 5), self.unit("C", "melee", 4), self.unit("D", "melee", 3)]
        s = self.activate(self.make_state("mestre_eclipse", "Lua Negra", enemy_units=enemy))
        board = s["players"]["2"]["board"]
        self.assertEqual([u["geada"] for u in board], [1, 1, 1, 0])

    def test_loretta_buffs_two_strongest_ranged_allies(self):
        own = [self.unit("A", "ranged", 6), self.unit("B", "ranged", 5), self.unit("C", "ranged", 4)]
        s = self.activate(self.make_state("oraculo_tempestade", "Lua Negra", own), "ranged")
        self.assertEqual([u["bonus"] for u in s["players"]["1"]["board"]], [2, 2, 0])

    def test_failed_leader_activation_does_not_consume_leader(self):
        own = [self.unit("Only", "melee")]
        state = self.make_state("sombra_caminhante", "Véu Carmesim", own)
        result = gwent.aplicar_jogada(state, 1, action="leader", row="melee")
        self.assertIn("error", result)
        self.assertFalse(state["players"]["1"]["leader_used"])


if __name__ == "__main__":
    unittest.main()
