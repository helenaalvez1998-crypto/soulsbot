"""Política econômica e simulador do Laboratório de Transmutação — V33.

Esta camada calcula custos e probabilidades; não consome recursos, não executa
rituais e não publica cartas. O commit transacional pertence à integração V34+.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Iterable

RARITIES = ("Comum", "Rara", "Épica", "Lendária", "Mítica")

# Proposta V33: probabilidades base herdadas da proposta anterior, explicitadas
# como parâmetros versionados e sujeitas a telemetria antes do lançamento.
BASE_CHANCE = {
    "Comum": 80.0,
    "Rara": 65.0,
    "Épica": 45.0,
    "Lendária": 25.0,
    "Mítica": 10.0,
}

# Custos por tentativa. Ingredientes (3–5 cartas) são sacrificados à parte.
# Material "vestigio_primordial" permanece reservado e não habilita Primordial/Singular.
COSTS = {
    "Comum": {"essencia_vida": 5, "fragmento_ancestral": 0, "nucleo_convergencia": 0},
    "Rara": {"essencia_vida": 10, "fragmento_ancestral": 2, "nucleo_convergencia": 0},
    "Épica": {"essencia_vida": 15, "fragmento_ancestral": 5, "nucleo_convergencia": 0},
    "Lendária": {"essencia_vida": 20, "fragmento_ancestral": 10, "nucleo_convergencia": 1},
    "Mítica": {"essencia_vida": 30, "fragmento_ancestral": 20, "nucleo_convergencia": 2},
}

MATERIALS = {
    "essencia_vida": {"name": "Essência de Vida", "description": "Material-base para estabilizar a transmutação."},
    "fragmento_ancestral": {"name": "Fragmento Ancestral", "description": "Material de maior densidade para raridades elevadas."},
    "nucleo_convergencia": {"name": "Núcleo de Convergência", "description": "Catalisador de estabilidade para Lendárias e Míticas."},
    "vestigio_primordial": {"name": "Vestígio Primordial", "description": "Reservado; não libera raridades Primordial ou Singular."},
    "cinza_da_graca": {"name": "Cinza da Graça", "description": "Catalisador de estabilidade; bônus de chance limitado."},
    "residuo_cariano": {"name": "Resíduo Cariano", "description": "Catalisador compatível com afinidade lunar."},
    "brasa_messmerica": {"name": "Brasa Messmeriana", "description": "Catalisador compatível com afinidade de fogo."},
    "nucleo_sanguineo": {"name": "Núcleo Sanguíneo", "description": "Catalisador compatível com afinidade de sangue."},
}

MAX_CHANCE = 90.0
COMPATIBILITY_BONUS_MAX = 10.0
FACTION_BONUS = 5.0
CATALYST_BONUS = 5.0
MAX_TOTAL_BONUS = 20.0
MIN_INGREDIENTS = 3
MAX_INGREDIENTS = 5
POLICY_VERSION = "v33.1"


@dataclass(frozen=True)
class Quote:
    rarity: str
    base_chance: float
    compatibility_bonus: float
    faction_bonus: float
    catalyst_bonus: float
    final_chance: float
    costs: dict[str, int]
    ingredients_required: int


def calcular_orcamento(rarity: str, compatibility_score: int,
                       same_faction: bool, catalyst_active: bool = False,
                       catalyst_key: str | None = None) -> Quote:
    if rarity not in RARITIES:
        raise ValueError("Raridade não elegível no Laboratório comum.")
    if not isinstance(compatibility_score, int) or not 0 <= compatibility_score <= 100:
        raise ValueError("Compatibilidade deve ser um inteiro entre 0 e 100.")
    # Score 0–100 traduzido linearmente em até +10 p.p.; score não é chance.
    from sistemas.catalisadores import obter_efeito
    effect = obter_efeito(catalyst_key, legacy_active=catalyst_active)
    effective_score = min(100, compatibility_score + effect.bonus_compatibilidade)
    compat = round(COMPATIBILITY_BONUS_MAX * effective_score / 100.0, 2)
    faction = FACTION_BONUS if same_faction else 0.0
    catalyst = effect.bonus_chance
    bonus = min(MAX_TOTAL_BONUS, compat + faction + catalyst)
    chance = min(MAX_CHANCE, BASE_CHANCE[rarity] + bonus)
    costs = dict(COSTS[rarity])
    if effect.custo:
        for key, amount in effect.custo.items():
            costs[key] = costs.get(key, 0) + amount
    return Quote(
        rarity=rarity, base_chance=BASE_CHANCE[rarity],
        compatibility_bonus=compat, faction_bonus=faction,
        catalyst_bonus=catalyst, final_chance=round(chance, 2),
        costs=costs, ingredients_required=MIN_INGREDIENTS,
    )


def validar_saldo(costs: dict[str, int], balances: dict[str, int]) -> list[dict[str, Any]]:
    """Retorna faltas explícitas sem alterar saldo."""
    missing = []
    for key, amount in costs.items():
        have = max(0, int(balances.get(key, 0)))
        if have < amount:
            missing.append({"material": key, "required": amount, "available": have,
                            "missing": amount - have})
    return missing


def simular_economia(rarity: str, compatibility_score: int = 50,
                     same_faction: bool = False, catalyst_active: bool = False,
                     attempts: int = 100_000, seed: int = 3301) -> dict[str, Any]:
    """Monte Carlo reprodutível: mostra sucessos, falhas e consumo esperado."""
    if not 1 <= int(attempts) <= 2_000_000:
        raise ValueError("A simulação aceita de 1 a 2.000.000 tentativas.")
    quote = calcular_orcamento(rarity, compatibility_score, same_faction, catalyst_active)
    rng = random.Random(int(seed))
    successes = sum(1 for _ in range(int(attempts)) if rng.random() * 100 < quote.final_chance)
    failures = int(attempts) - successes
    cost = dict(quote.costs)
    return {
        "policy_version": POLICY_VERSION, "rarity": rarity,
        "attempts": int(attempts), "successes": successes, "failures": failures,
        "success_rate_observed": round(successes / int(attempts) * 100, 3),
        "success_rate_expected": quote.final_chance,
        "expected_attempts_per_success": round(100 / quote.final_chance, 3),
        "expected_failures_before_success": round((100 / quote.final_chance) - 1, 3),
        "cost_per_attempt": cost,
        "total_materials_consumed": {k: v * int(attempts) for k, v in cost.items()},
        "expected_materials_per_success": {
            k: round(v * 100 / quote.final_chance, 2) for k, v in cost.items()
        },
        "ingredient_cards_consumed_per_attempt": f"{MIN_INGREDIENTS}-{MAX_INGREDIENTS}",
        "expected_ingredient_cards_per_success": (
            f"{round(MIN_INGREDIENTS*100/quote.final_chance,2)}-"
            f"{round(MAX_INGREDIENTS*100/quote.final_chance,2)}"
        ),
        "bonus": {
            "compatibility": quote.compatibility_bonus,
            "faction": quote.faction_bonus,
            "catalyst": quote.catalyst_bonus,
            "total_applied": round(quote.final_chance - quote.base_chance, 2),
        },
    }


def gerar_relatorio_simulacao(attempts: int = 100_000) -> list[dict[str, Any]]:
    """Compara todas as raridades em cenário neutro e cenário favorável."""
    report = []
    for rarity in RARITIES:
        for label, score, faction, catalyst in (
            ("neutro", 0, False, False),
            ("favoravel", 100, True, True),
        ):
            result = simular_economia(rarity, score, faction, catalyst, attempts, 3301)
            result["scenario"] = label
            report.append(result)
    return report


def descrever_regra_de_consumo() -> dict[str, str]:
    return {
        "success": "Consome todos os ingredientes e materiais comprometidos; cria uma carta pessoal.",
        "legitimate_failure": "Consome todos os ingredientes e materiais comprometidos; não cria carta.",
        "technical_error": "Não consome ingredientes nem materiais; a tentativa não é registrada como falha.",
        "primordial_singular": "Bloqueadas no gerador comum; Vestígio Primordial não altera essa regra.",
    }
