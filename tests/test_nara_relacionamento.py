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


    def test_contexto_define_afinidade_como_opiniao_e_confianca(self):
        contexto = rel.formatar_contexto(3.1, 5.0, [])
        self.assertIn("afinidade determina consideração", contexto)
        self.assertIn("faixa 2,5–3,9 representa pouca simpatia, não neutralidade", contexto)
        self.assertIn("aja conforme a faixa, não narre a faixa", contexto)
        self.assertIn("Não diga repetidamente que a relação é distante", contexto)
        contexto_alto = rel.formatar_contexto(9.0, 5.0, [])
        self.assertIn("carinho, confiança e consideração podem aparecer naturalmente", contexto_alto)

    def test_contexto_nao_autoriza_revelar_pontuacoes_ou_eventos(self):
        contexto = rel.formatar_contexto(2.5, 3.0, [{"summary": "Desrespeito explícito"}])
        self.assertIn("Não revele notas nem eventos privados", contexto)
        self.assertIn("Não humilhe, ameace ou ataque atributos pessoais sensíveis", contexto)


    def test_opiniao_sobre_alvo_configurado(self):
        self.assertTrue(rel.detectar_consulta_opiniao(
            "qual sua opiniao sobre davis95?", ["davisg95"]
        ))

    def test_pergunta_generica_nao_puxa_relacionamento_do_alvo(self):
        self.assertFalse(rel.detectar_consulta_opiniao(
            "qual sua opiniao sobre esse jogo?", ["davisg95"]
        ))

    def test_mencao_discord_identifica_alvo_sem_nome_no_texto(self):
        self.assertTrue(rel.detectar_consulta_opiniao(
            "o que acha dele?", [], mencionado=True
        ))


    def test_opiniao_com_erro_de_digitacao_opniao(self):
        self.assertTrue(rel.detectar_consulta_opiniao(
            "qual sua opnião sobre davisg95?", ["davisg95"]
        ))

    def test_opiniao_com_mencao_real_do_discord(self):
        self.assertTrue(rel.detectar_consulta_opiniao(
            "qual sua opnião sobre <@337010644186300446>?",
            [], mencionado=True
        ))


    def test_opniao_com_erro_de_digitacao_e_detectada(self):
        self.assertTrue(rel.eh_consulta_opiniao("qual sua opnião sobre @davisg95?"))
        self.assertTrue(rel.eh_consulta_opiniao("qual sua opinião sobre Davis?"))

    def test_mencao_isolada_nao_e_pergunta_de_opiniao(self):
        self.assertFalse(rel.eh_consulta_opiniao("bom dia @davisg95"))
        self.assertFalse(rel.detectar_consulta_opiniao("bom dia", [], mencionado=True))

    def test_faixas_de_afinidade_tem_semantica_deterministica(self):
        self.assertEqual(rel.faixa_afinidade(1.0), "antipatia_clara")
        self.assertEqual(rel.faixa_afinidade(3.1), "baixa")
        self.assertEqual(rel.faixa_afinidade(4.5), "reservada")
        self.assertEqual(rel.faixa_afinidade(5.5), "neutra")
        self.assertEqual(rel.faixa_afinidade(7.0), "boa")
        self.assertEqual(rel.faixa_afinidade(9.5), "alta")

    def test_validador_rejeita_elogio_compensatorio_da_resposta_real(self):
        resposta = (
            "o davis testa a paciência da moderação, mas pelo menos movimenta o servidor. "
            "o caos dele já faz parte da mobília daqui."
        )
        self.assertEqual(
            rel.motivo_resposta_incoerente(resposta, 3.1),
            "elogio_ou_afeto_compensatorio",
        )

    def test_validador_nao_rejeita_negacao_de_afeto(self):
        resposta = "não tenho carinho nem sinto falta dele; prefiro manter distância."
        self.assertIsNone(rel.motivo_resposta_incoerente(resposta, 3.1))

    def test_validador_nao_aplica_regra_de_baixa_afinidade_a_nota_alta(self):
        resposta = "gosto dele e é bom ter por perto."
        self.assertIsNone(rel.motivo_resposta_incoerente(resposta, 9.0))

    def test_resposta_de_contingencia_para_afinidade_3_1_nao_recita_categoria(self):
        resposta = rel.resposta_padrao_opiniao("davisg95", 3.1)
        self.assertNotIn("relação", resposta)
        self.assertNotIn("distante", resposta)
        self.assertNotIn("neutra", resposta)
        self.assertNotIn("afinidade", resposta)
        self.assertNotIn("movimenta", resposta)

    def test_resposta_quase_igual_a_anterior_e_detectada(self):
        atual = "o davis testa a paciência da moderação, mas movimenta o servidor de vez em quando."
        anterior = "o davis testa a paciencia da moderacao mas movimenta o servidor de vez em quando"
        self.assertTrue(rel.resposta_repetida(atual, [anterior]))


    def test_resposta_sem_marcador_de_distancia_e_aceita(self):
        # A nota orienta a atitude; a resposta não precisa declarar a categoria do vínculo.
        self.assertIsNone(
            rel.motivo_resposta_incoerente(
                "davis? não é alguém que me ganhe facilmente. fico na cordialidade e pronto.", 3.1
            )
        )

    def test_opiniao_fria_sem_rotulo_relacional_e_aceita(self):
        resposta = "davis? não vou fingir entusiasmo. trato normal e sigo o baile."
        self.assertIsNone(rel.motivo_resposta_incoerente(resposta, 3.1))

    def test_resposta_padrao_baixa_afinidade_varia_sem_anunciar_distancia(self):
        primeira = rel.resposta_padrao_opiniao("davisg95", 3.1)
        segunda = rel.resposta_padrao_opiniao("davisg95", 3.1, [primeira])
        self.assertNotEqual(primeira, segunda)
        for resposta in (primeira, segunda):
            self.assertNotIn("relação distante", resposta)
            self.assertNotIn("relação neutra", resposta)

    def test_resposta_padrao_varia_quando_a_anterior_ja_foi_usada(self):
        primeira = rel.resposta_padrao_opiniao("davisg95", 3.1)
        segunda = rel.resposta_padrao_opiniao("davisg95", 3.1, [primeira])
        self.assertNotEqual(primeira, segunda)
        self.assertIsNone(rel.motivo_resposta_incoerente(segunda, 3.1))


if __name__ == "__main__":
    unittest.main()
