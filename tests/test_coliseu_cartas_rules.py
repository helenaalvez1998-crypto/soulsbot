from sistemas.cartas import (
    CARTAS_PACOTE,
    HABILIDADES,
    carta_jogo,
    cards_em_deck_validos,
    poder_total_deck,
    resolver_duelo,
    resolver_rodada,
    vantagem_tipo,
)


def test_triangulo_de_tipos_tem_bonus_de_tres():
    assert vantagem_tipo("Destreza", "Força") == 3
    assert vantagem_tipo("Força", "Magia") == 3
    assert vantagem_tipo("Magia", "Destreza") == 3
    assert vantagem_tipo("Força", "Destreza") == -3
    assert vantagem_tipo("Magia", "Magia") == 0


def test_cartas_de_zerado_e_platina_sao_diferentes_e_deterministicas():
    zerado = carta_jogo("Elden Ring", "zerado")
    platina = carta_jogo("Elden Ring", "platina")
    assert zerado.id != platina.id
    assert zerado.raridade == "Rara"
    assert platina.raridade == "Épica"
    assert zerado == carta_jogo("Elden Ring", "zerado")


def test_deck_respeita_tamanho_custo_e_limite_de_lendaria():
    comuns = [c.para_dict() for c in CARTAS_PACOTE if c.raridade == "Comum"]
    assert cards_em_deck_validos(comuns[:5])[0]
    assert not cards_em_deck_validos(comuns[:4])[0]
    lendarias = [c.para_dict() for c in CARTAS_PACOTE if c.raridade == "Lendária"]
    epicas = [c.para_dict() for c in CARTAS_PACOTE if c.raridade == "Épica"]
    deck = [lendarias[0], *epicas[:4]]
    assert not cards_em_deck_validos(deck)[0]


def test_bonus_de_tipo_e_habilidade_entram_no_calculo_servidor():
    a = {"id": "a", "nome": "A", "tipo": "Destreza", "poder": 4, "habilidade": "primeira_luz"}
    b = {"id": "b", "nome": "B", "tipo": "Força", "poder": 5, "habilidade": "retaliacao"}
    resultado = resolver_rodada(a, b, 1, None, None)
    assert resultado["power_a"] == 8  # 4 base +3 tipo +1 habilidade
    assert resultado["power_b"] == 5
    assert resultado["winner"] == "a"


def test_empate_de_duelo_usa_poder_das_rodadas_vencidas():
    rounds = [
        {"winner": "a", "power_a": 8, "power_b": 3},
        {"winner": "b", "power_a": 4, "power_b": 6},
        {"winner": "a", "power_a": 6, "power_b": 2},
        {"winner": "b", "power_a": 4, "power_b": 6},
        {"winner": "empate", "power_a": 6, "power_b": 6},
    ]
    assert resolver_duelo(rounds) == "a"


def test_habilidades_catalogadas_sao_concisas_e_distintas():
    assert set(HABILIDADES) == {"primeira_luz", "retaliacao", "impeto", "ultimo_folego", "contragolpe"}
    assert len({x["nome"] for x in HABILIDADES.values()}) == len(HABILIDADES)


def test_poder_total_deck_soma_apenas_poder_base():
    cartas = [
        {"id": "a", "poder": 4},
        {"id": "b", "poder": 5},
        {"id": "c", "poder": 3},
        {"id": "d", "poder": 4},
        {"id": "e", "poder": 4},
    ]
    assert poder_total_deck(cartas) == 20
