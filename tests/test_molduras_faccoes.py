import unittest
from PIL import ImageChops

from sistemas import molduras_cartas as molduras


class MoldurasPorFaccaoTests(unittest.TestCase):
    def test_aliases_antigos_sao_normalizados(self):
        self.assertEqual(molduras.normalizar_faccao("Casa Cariana"), "Lua Sombria")
        self.assertEqual(molduras.normalizar_faccao("Dinastia Mohgwyn"), "Véu Carmesim")
        self.assertEqual(molduras.normalizar_faccao("Ordem Aurea"), "Ordem Áurea")

    def test_as_tres_faccoes_tem_silhuetas_diferentes(self):
        mascaras = [
            molduras._forma_moldura("Comum", molduras.ESTILOS["Comum"], faccao)
            for faccao in molduras.FACCOES
        ]
        self.assertIsNotNone(ImageChops.difference(mascaras[0], mascaras[1]).getbbox())
        self.assertIsNotNone(ImageChops.difference(mascaras[1], mascaras[2]).getbbox())
        self.assertIsNotNone(ImageChops.difference(mascaras[0], mascaras[2]).getbbox())

    def test_21_combinacoes_faccao_raridade_renderizam(self):
        for faccao in molduras.FACCOES:
            for raridade in molduras.ESTILOS:
                with self.subTest(faccao=faccao, raridade=raridade):
                    overlay = molduras.construir_overlay(
                        raridade=raridade, faccao=faccao, tipo="Força",
                        fileira="melee", especial=False,
                    )
                    self.assertEqual(overlay.size, (molduras.BASE_W * molduras.S, molduras.BASE_H * molduras.S))
                    self.assertIsNotNone(overlay.getbbox())

    def test_nomes_legados_usam_emblema_e_arquitetura_corretos(self):
        antigo = molduras.construir_overlay(
            raridade="Lendária", faccao="Casa Cariana", tipo="Magia",
            fileira="siege", especial=False,
        )
        atual = molduras.construir_overlay(
            raridade="Lendária", faccao="Lua Sombria", tipo="Magia",
            fileira="siege", especial=False,
        )
        self.assertEqual(ImageChops.difference(antigo, atual).getbbox(), None)


if __name__ == "__main__":
    unittest.main()
