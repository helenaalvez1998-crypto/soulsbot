from nara_voz import enquadrar


def test_enquadrar_adiciona_abertura_contextual_sem_alterar_o_conteudo():
    corpo = "Você tem **120 Denários**."
    assert enquadrar(corpo, "saldo") == "Hm. Vamos aos números:\n" + corpo


def test_enquadrar_preserva_texto_desconhecido_ou_vazio():
    assert enquadrar("Texto original", "contexto-inexistente") == "Texto original"
    assert enquadrar("   ", "saldo") == ""


def test_enquadrar_nao_duplica_abertura():
    texto = "Hm. Vamos aos números:\nVocê tem **120 Denários**."
    assert enquadrar(texto, "saldo") == texto


def test_enquadrar_nao_modifica_valores_e_resultados():
    corpo = "**Top 3:**\n1. <@123> — 47 platinas\n2. <@456> — 31 platinas"
    saida = enquadrar(corpo, "ranking")
    assert corpo in saida
    assert "47 platinas" in saida
    assert "31 platinas" in saida
