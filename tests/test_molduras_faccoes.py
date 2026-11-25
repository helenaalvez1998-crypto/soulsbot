import unittest
from PIL import ImageChops

from sistemas import molduras_cartas as molduras


class MoldurasPorFaccaoTests(unittest.TestCase):
    def test_aliases_antigos_sao_normalizados(self):
        self.assertEqual(molduras.normalizar_faccao("Casa Cariana"), "Lua Negra")
        self.assertEqual(molduras.normalizar_faccao("Dinastia Mohgwyn"), "Véu Carmesim")
        self.assertEqual(molduras.normalizar_faccao("Ordem Aurea"), "Ordem Áurea")

    def test_todas_as_faccoes_preservam_silhueta_retangular_vertical(self):
        mascaras = [
            molduras._forma_moldura("Comum", molduras.ESTILOS["Comum"], faccao)
            for faccao in molduras.FACCOES
        ]
        # A moldura tem cantos retos de 90 graus e mantém o formato vertical de carta.
        for mascara in mascaras:
            self.assertEqual(mascara.getpixel((3*molduras.S, 3*molduras.S)), 255)
            self.assertEqual(mascara.getpixel((416*molduras.S, 3*molduras.S)), 255)
            self.assertEqual(mascara.getpixel((3*molduras.S, 616*molduras.S)), 255)
            self.assertEqual(mascara.getpixel((416*molduras.S, 616*molduras.S)), 255)
        # A geometria externa é comum: facção aparece nas gravações, não deformando a carta.
        self.assertIsNone(ImageChops.difference(mascaras[0], mascaras[1]).getbbox())
        self.assertIsNone(ImageChops.difference(mascaras[1], mascaras[2]).getbbox())

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

    def test_21_combinacoes_tem_acabamentos_visuais_distintos(self):
        overlays = {}
        for faccao in molduras.FACCOES:
            for raridade in molduras.ESTILOS:
                overlays[(faccao, raridade)] = molduras.construir_overlay(
                    raridade=raridade, faccao=faccao, tipo="Força",
                    fileira="melee", especial=False,
                )
        # Mesma raridade em facções diferentes deve mudar a heráldica.
        for raridade in molduras.ESTILOS:
            a = overlays[("Ordem Áurea", raridade)]
            b = overlays[("Véu Carmesim", raridade)]
            c = overlays[("Lua Negra", raridade)]
            self.assertIsNotNone(ImageChops.difference(a, b).getbbox())
            self.assertIsNotNone(ImageChops.difference(b, c).getbbox())
        # Mesma facção em raridades diferentes deve mudar o acabamento.
        for faccao in molduras.FACCOES:
            a = overlays[(faccao, "Comum")]
            b = overlays[(faccao, "Lendária")]
            self.assertIsNotNone(ImageChops.difference(a, b).getbbox())

    def test_heraldica_lateral_e_unica_sem_alterar_a_silhueta(self):
        overlays = {
            faccao: molduras.construir_overlay(
                raridade="Comum", faccao=faccao, tipo="Força",
                fileira="melee", especial=False,
            )
            for faccao in molduras.FACCOES
        }
        # A comparação isola as duas faixas laterais decoradas, sem considerar
        # o emblema circular da facção no HUD.
        regioes = ((8*molduras.S, 185*molduras.S, 18*molduras.S, 395*molduras.S),
                   (402*molduras.S, 185*molduras.S, 412*molduras.S, 395*molduras.S))
        for box in regioes:
            recortes = {f: img.crop(box) for f, img in overlays.items()}
            self.assertIsNotNone(ImageChops.difference(recortes["Ordem Áurea"], recortes["Véu Carmesim"]).getbbox())
            self.assertIsNotNone(ImageChops.difference(recortes["Véu Carmesim"], recortes["Lua Negra"]).getbbox())

    def test_nomes_legados_usam_emblema_e_arquitetura_corretos(self):
        antigo = molduras.construir_overlay(
            raridade="Lendária", faccao="Casa Cariana", tipo="Magia",
            fileira="siege", especial=False,
        )
        atual = molduras.construir_overlay(
            raridade="Lendária", faccao="Lua Negra", tipo="Magia",
            fileira="siege", especial=False,
        )
        self.assertEqual(ImageChops.difference(antigo, atual).getbbox(), None)


if __name__ == "__main__":
    unittest.main()
