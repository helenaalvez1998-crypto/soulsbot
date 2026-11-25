from sistemas.gerador_cartas import (
    avaliar_balanceamento_cumulativo, gerar_carta_procedural,
    validar_definicao_gerada, validar_lote_gerado,
)


def make_trio():
    return [
        {"exemplar_id": 1, "card_id": "c1", "nome": "Maliketh Morte", "tipo": "Força", "categoria": "Unidade", "raridade": "Rara", "is_sacrificable": 1},
        {"exemplar_id": 2, "card_id": "c2", "nome": "Gurranq Bestial", "tipo": "Força", "categoria": "Unidade", "raridade": "Rara", "is_sacrificable": 1},
        {"exemplar_id": 3, "card_id": "c3", "nome": "Messmer Chama", "tipo": "Magia", "categoria": "Unidade", "raridade": "Rara", "is_sacrificable": 1},
    ]


def test_generated_card_is_valid_under_strict_validator():
    result = gerar_carta_procedural(make_trio(), seed="strict", generated_id="generated_4001")
    assert result["valido"]
    assert validar_definicao_gerada(result["definition"])[0]


def test_cumulative_balance_thresholds():
    assert avaliar_balanceamento_cumulativo(5, 5)["status"] == "amostra_insuficiente"
    assert avaliar_balanceamento_cumulativo(50, 50)["status"] == "dentro_da_meta"
    assert avaliar_balanceamento_cumulativo(80, 20)["alerta"] is True


def test_lot_validation_reports_duplicate_ids():
    a = gerar_carta_procedural(make_trio(), seed="a", generated_id="generated_4002")["definition"]
    report = validar_lote_gerado([a, dict(a)])
    assert report["valido"] is False
    assert report["ids_duplicados"] == ["generated_4002"]



def test_seed_sweep_generates_only_definitions_that_pass_strict_validation():
    ingredients = make_trio()
    for n in range(250):
        result = gerar_carta_procedural(
            ingredients, seed=f"validation-sweep-{n}",
            generated_id=f"sweep_card_{n:05}",
        )
        assert result["valido"], result
        assert validar_definicao_gerada(result["definition"])[0], result["definition"]
