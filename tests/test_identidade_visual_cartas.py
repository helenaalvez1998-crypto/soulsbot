import unittest

from sistemas.identidade_visual_cartas import (
    FACCOES, RARIDADES, listar_combinacoes, normalizar_faccao,
    resolver_identidade_visual,
)


class IdentidadeVisualCartasTests(unittest.TestCase):
    def test_todas_as_faccoes_tem_identidade_independente(self):
        self.assertEqual(set(FACCOES), {"Ordem Áurea", "Véu Carmesim", "Lua Negra"})
        brasoes = {v["brasao"] for v in FACCOES.values()}
        self.assertEqual(len(brasoes), len(FACCOES))

    def test_todas_as_raridades_tem_medalhao_proprio(self):
        self.assertEqual(len(RARIDADES), 7)
        formas = {v["forma"] for v in RARIDADES.values()}
        gemas = {v["gema"] for v in RARIDADES.values()}
        self.assertEqual(len(formas), 7)
        self.assertEqual(len(gemas), 7)

    def test_aliases_legados(self):
        self.assertEqual(normalizar_faccao("Mohgwyn"), "Véu Carmesim")
        self.assertEqual(normalizar_faccao("Carian"), "Lua Negra")
        self.assertEqual(normalizar_faccao("Golden Order"), "Ordem Áurea")

    def test_resolver_nao_modifica_catalogo(self):
        a = resolver_identidade_visual("Lua Negra", "Mítica")
        a["tema_faccao"]["paleta"] = None
        b = resolver_identidade_visual("Lua Negra", "Mítica")
        self.assertIsNotNone(b["tema_faccao"]["paleta"])
        self.assertEqual(b["tema_raridade"]["forma"], "estrela_radiante")

    def test_matriz_facção_raridade_completa(self):
        combinacoes = listar_combinacoes()
        self.assertEqual(len(combinacoes), 21)
        for item in combinacoes:
            ficha = resolver_identidade_visual(item["faccao"], item["raridade"])
            self.assertEqual(ficha["faccao"], item["faccao"])
            self.assertEqual(ficha["raridade"], item["raridade"])


if __name__ == "__main__":
    unittest.main()
