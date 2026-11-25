from sistemas.cartas import carta_jogo


def test_game_reward_title_epithet_matches_its_faction():
    for game_name in ("Jogo da Ordem", "Jogo do Sangue", "Jogo das Estrelas"):
        card = carta_jogo(game_name, "zerado")
        if card.tipo == "Força":
            assert any(token in card.nome for token in ("Graça Dourada", "Leyndell", "Árvore Áurea", "Crisol", "Capital Dourada"))
            assert "Mohgwyn" not in card.nome
            assert "Lua Negra" not in card.nome
            assert "Ordem Áurea" in card.descricao
        elif card.tipo == "Destreza":
            assert any(token in card.nome for token in ("Mohgwyn", "Véu Carmesim", "Dinastia Sanguínea", "Procissão Carmesim", "Catacumbas"))
            assert "Ordem Áurea" not in card.descricao
            assert "Véu Carmesim" in card.descricao
        else:
            assert any(token in card.nome for token in ("Lua Negra", "Sellia", "Nokron", "Cariana", "Cidades Eternas"))
            assert "Lua Negra" in card.descricao


def test_different_game_rewards_have_distinguishable_card_names():
    first = carta_jogo("Jogo A", "zerado")
    second = carta_jogo("Jogo B", "zerado")
    assert first.id != second.id
    assert first.nome != second.nome


def test_game_reward_lore_explains_the_card_instead_of_using_generic_lore():
    card = carta_jogo("Elden Challenge", "platina")
    assert "Recompensa de domínio: guerreiro de elite" not in card.descricao
    assert 100 < len(card.descricao) <= 240
    assert card.descricao.endswith(".")
    if card.habilidade:
        ability_name = __import__("sistemas.cartas", fromlist=["HABILIDADES"]).HABILIDADES[card.habilidade]["nome"]
        assert ability_name in card.descricao
    else:
        assert "Não possui habilidade especial" in card.descricao
