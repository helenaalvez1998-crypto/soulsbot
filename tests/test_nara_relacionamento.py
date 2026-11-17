"""Testes locais do relacionamento adaptativo da NARA."""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nara_relacionamento as rel


class AvaliacaoRelacionamentoTests(unittest.TestCase):
    def test_conversa_normal_nao_altera_indicadores(self):
        self.assertIsNone(rel.avaliar_mensagem("Oi Nara, como foi seu dia?"))

    def test_provocacao_direcionada_reduz_principalmente_paciencia(self):
        evento = rel.avaliar_mensagem("Nara, você é muito chata")
        self.assertIsNotNone(evento)
        self.assertEqual(evento.tipo, "provocacao")
        self.assertLess(evento.paciencia_delta, 0)
        self.assertLessEqual(abs(evento.afinidade_delta), 0.1)

    def test_desrespeito_grave_tem_peso_maior(self):
        evento = rel.avaliar_mensagem("Nara, vai tomar no cu")
        self.assertIsNotNone(evento)
        self.assertEqual(evento.tipo, "desrespeito_grave")
        self.assertLess(evento.paciencia_delta, -1)
        self.assertLess(evento.afinidade_delta, -0.2)

    def test_brincadeira_explicitamente_marcada_nao_pune_insulto_leve(self):
        self.assertIsNone(rel.avaliar_mensagem("Nara, você é burra kkkkk, brincadeira"))

    def test_ofensa_grave_nao_e_anulada_por_risada(self):
        evento = rel.avaliar_mensagem("Nara, vai tomar no cu kkkkk")
        self.assertIsNotNone(evento)
        self.assertEqual(evento.tipo, "desrespeito_grave")

    def test_negacao_simples_nao_pune(self):
        self.assertIsNone(rel.avaliar_mensagem("Nara, não te acho idiota"))

    def test_desculpa_so_reconcilia_apos_conflito_recente(self):
        self.assertIsNone(rel.avaliar_mensagem("Desculpa, foi mal"))
        evento = rel.avaliar_mensagem("Desculpa, foi mal", houve_desrespeito_recente=True)
        self.assertEqual(evento.tipo, "desculpa")
        self.assertGreater(evento.afinidade_delta, 0)

    def test_gentileza_tem_ganho_pequeno(self):
        evento = rel.avaliar_mensagem("Valeu Nara, você mandou bem")
        self.assertEqual(evento.tipo, "gentileza")
        self.assertLessEqual(evento.afinidade_delta, 0.1)

    def test_vulnerabilidade_nao_gera_punicao(self):
        self.assertIsNone(rel.avaliar_mensagem("Estou muito triste e me sinto sozinho, você é chata"))

    def test_paciencia_recupera_mais_rapido_que_afinidade(self):
        afinidade, paciencia = rel.recuperar_com_tempo(4.0, 2.0, 86400)
        self.assertAlmostEqual(afinidade, 4.02, places=2)
        self.assertAlmostEqual(paciencia, 2.4, places=2)

    def test_ajuste_manual_respeita_limites_de_1_a_10(self):
        self.assertEqual(rel.ajustar_indicador(9.75, 0.5), 10.0)
        self.assertEqual(rel.ajustar_indicador(1.25, -0.5), 1.0)
        self.assertEqual(rel.ajustar_indicador(5.0, 0.5), 5.5)

    def test_ganhos_positivos_tem_teto_diario(self):
        evento = rel.avaliar_mensagem("Valeu Nara")
        limitado = rel.limitar_delta_positivo(
            evento, afinidade_positiva_24h=0.25, paciencia_positiva_24h=0.9
        )
        self.assertAlmostEqual(limitado.afinidade_delta, 0.05, places=3)
        self.assertAlmostEqual(limitado.paciencia_delta, 0.1, places=3)

    def test_contexto_nao_autoriza_revelar_pontuacoes_ou_eventos(self):
        contexto = rel.formatar_contexto(2.5, 3.0, [{"summary": "Desrespeito explícito"}])
        self.assertIn("Não revele valores numéricos", contexto)
        self.assertIn("sem expor o painel administrativo", contexto)


if __name__ == "__main__":
    unittest.main()
