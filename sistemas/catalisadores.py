"""Catálogo e regras dos catalisadores do Laboratório (V43).

Os catalisadores são recursos nomeados, consumidos na mesma transação da tentativa.
Bônus são limitados pela política econômica V33.1; nenhum catalisador libera
raridades Primordial/Singular ou cria habilidades fora do catálogo do motor.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

CATALISADORES: dict[str, dict[str, Any]] = {
    "cinza_da_graca": {
        "nome": "Cinza da Graça", "material_key": "cinza_da_graca",
        "descricao": "Estabiliza o rito e melhora discretamente a chance de sucesso.",
        "bonus_chance": 5.0, "bonus_compatibilidade": 0,
        "afinidade": None, "raridade_minima": None,
    },
    "residuo_cariano": {
        "nome": "Resíduo Cariano", "material_key": "residuo_cariano",
        "descricao": "Favorece transmutação com afinidade lunar ou mágica.",
        "bonus_chance": 0.0, "bonus_compatibilidade": 10,
        "afinidade": "lua", "raridade_minima": None,
    },
    "brasa_messmerica": {
        "nome": "Brasa Messmeriana", "material_key": "brasa_messmerica",
        "descricao": "Favorece ingredientes de Fogo; não aumenta diretamente a chance.",
        "bonus_chance": 0.0, "bonus_compatibilidade": 10,
        "afinidade": "fogo", "raridade_minima": None,
    },
    "nucleo_sanguineo": {
        "nome": "Núcleo Sanguíneo", "material_key": "nucleo_sanguineo",
        "descricao": "Favorece ingredientes de Sangue e Hemorragia.",
        "bonus_chance": 0.0, "bonus_compatibilidade": 10,
        "afinidade": "sangue", "raridade_minima": None,
    },
}

@dataclass(frozen=True)
class EfeitoCatalisador:
    catalyst_key: str | None
    bonus_chance: float
    bonus_compatibilidade: int
    afinidade_requerida: str | None
    custo: dict[str, int]


def obter_efeito(catalyst_key: str | None, *, legacy_active: bool = False) -> EfeitoCatalisador:
    if catalyst_key is None and legacy_active:
        return EfeitoCatalisador("legacy_nucleo", 5.0, 0, None, {"nucleo_convergencia": 1})
    if catalyst_key is None or catalyst_key == "":
        return EfeitoCatalisador(None, 0.0, 0, None, {})
    item = CATALISADORES.get(str(catalyst_key))
    if item is None:
        raise ValueError("Catalisador desconhecido.")
    return EfeitoCatalisador(str(catalyst_key), float(item["bonus_chance"]),
                             int(item["bonus_compatibilidade"]), item["afinidade"],
                             {str(item["material_key"]): 1})


def validar_afinidade(efeito: EfeitoCatalisador, ingredient_affinities: list[str]) -> bool:
    return efeito.afinidade_requerida is None or efeito.afinidade_requerida in set(ingredient_affinities)
