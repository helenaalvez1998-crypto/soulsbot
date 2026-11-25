import pytest

from sistemas.economia_transmutacao import (
    BASE_CHANCE, COSTS, MAX_CHANCE, calcular_orcamento, validar_saldo,
    simular_economia, gerar_relatorio_simulacao, descrever_regra_de_consumo,
)


def test_base_chances_and_rarity_costs_are_explicit_and_monotonic():
    assert [BASE_CHANCE[r] for r in ("Comum", "Rara", "Épica", "Lendária", "Mítica")] == [80, 65, 45, 25, 10]
    essence = [COSTS[r]["essencia_vida"] for r in COSTS]
    assert essence == sorted(essence)
    assert COSTS["Lendária"]["nucleo_convergencia"] == 1
    assert COSTS["Mítica"]["nucleo_convergencia"] == 2


def test_probability_bonus_is_bounded_and_compatibility_is_not_probability():
    quote = calcular_orcamento("Comum", 100, True, True)
    assert quote.final_chance == MAX_CHANCE == 90
    assert quote.compatibility_bonus == 10
    assert quote.faction_bonus == 5
    assert quote.catalyst_bonus == 5
    assert quote.costs["nucleo_convergencia"] == 1


def test_rarity_probability_schedule():
    values = [calcular_orcamento(r, 0, False).final_chance
              for r in ("Comum", "Rara", "Épica", "Lendária", "Mítica")]
    assert values == [80, 65, 45, 25, 10]


def test_invalid_rarity_and_compatibility_rejected():
    with pytest.raises(ValueError):
        calcular_orcamento("Primordial", 50, False)
    with pytest.raises(ValueError):
        calcular_orcamento("Mítica", 101, False)


def test_balance_validation_does_not_mutate_inventory():
    balances = {"essencia_vida": 3}
    missing = validar_saldo({"essencia_vida": 5, "fragmento_ancestral": 2}, balances)
    assert missing == [
        {"material": "essencia_vida", "required": 5, "available": 3, "missing": 2},
        {"material": "fragmento_ancestral", "required": 2, "available": 0, "missing": 2},
    ]
    assert balances == {"essencia_vida": 3}


def test_simulation_is_reproducible_and_reports_expected_consumption():
    a = simular_economia("Mítica", attempts=10000, seed=123)
    b = simular_economia("Mítica", attempts=10000, seed=123)
    assert a == b
    assert a["attempts"] == 10000
    assert a["successes"] + a["failures"] == 10000
    assert a["expected_attempts_per_success"] == 6.667
    assert a["expected_materials_per_success"]["essencia_vida"] == 200


def test_favorable_case_never_exceeds_probability_cap():
    for rarity in BASE_CHANCE:
        q = calcular_orcamento(rarity, 100, True, True)
        assert q.final_chance <= 90


def test_rules_separate_failure_from_technical_error():
    rules = descrever_regra_de_consumo()
    assert "Consome todos" in rules["legitimate_failure"]
    assert "Não consome" in rules["technical_error"]
    assert "não altera" not in rules["technical_error"]


def test_simulation_report_covers_all_rarities_and_scenarios():
    report = gerar_relatorio_simulacao(1000)
    assert len(report) == 10
    assert {x["scenario"] for x in report} == {"neutro", "favoravel"}
