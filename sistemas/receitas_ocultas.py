"""Receitas ocultas e descoberta individual (V42).

A descoberta é persistida por jogador. A assinatura ignora ordem dos ingredientes,
mas exige a combinação exata de IDs canônicos e raridades declaradas. O módulo
não consome cartas: a descoberta ocorre em uma ação de pesquisa separada e só
registra a receita quando o jogador possui todos os ingredientes elegíveis.
"""
from __future__ import annotations
import hashlib, json
from typing import Any
from sistemas.afinidades import classificar_carta, validar_ingredientes

RECEITAS_OCULTAS: dict[str, dict[str, Any]] = {
    "trindade_lunar_oculta": {
        "nome": "Trindade da Lua Velada", "pista": "Três vestígios da noite cariana convergem sob a mesma lua.",
        "ingredientes": {"covenant_lua_velada": "Épica", "arma_duas_luas": "Épica", "magia_nevoa_antiga": "Épica"},
        "afinidades": ["lua", "magia"], "faccao": "Lua Negra", "raridade_resultado": "Lendária",
        "descricao": "Uma linhagem lunar esquecida, revelada pela combinação de pacto, lâmina e névoa.",
    },
    "forja_dourada_oculta": {
        "nome": "Forja Dourada Perdida", "pista": "O peso do sino responde ao juramento de ferro e à guarda fiel.",
        "ingredientes": {"gwent_unidade_baluarte": "Rara", "arma_martelo_fornalha": "Rara", "covenant_irmandade_ferro": "Comum"},
        "afinidades": ["sagrado", "fogo"], "faccao": "Ordem Áurea", "raridade_resultado": "Lendária",
        "descricao": "Uma tradição de forja que une proteção, juramento e fogo antigo.",
    },
    "rito_da_morte_oculto": {
        "nome": "Rito do Veio Morto", "pista": "A aparição, o caçador e o necromante apontam para um mesmo oráculo.",
        "ingredientes": {"chefe_aparicao_veio": "Comum", "chefe_cacador_sem_rosto": "Rara", "gwent_unidade_necromante": "Rara"},
        "afinidades": ["morte", "bestial"], "faccao": "Véu Carmesim", "raridade_resultado": "Lendária",
        "descricao": "Um rito funerário que revela uma rota ancestral de transmutação.",
    },
}


def assinatura_ingredientes(ingredients: list[dict[str, Any]]) -> str:
    payload = sorted((str(x.get("card_id") or x.get("id")), str(x.get("raridade") or x.get("rarity"))) for x in ingredients)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def descobrir_receitas(ingredients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok, reason = validar_ingredientes(ingredients)
    if not ok:
        return []
    actual = sorted((str(x.get("card_id") or x.get("id")), str(x.get("raridade") or x.get("rarity"))) for x in ingredients)
    found = []
    for recipe_id, recipe in RECEITAS_OCULTAS.items():
        expected = sorted((card_id, rarity) for card_id, rarity in recipe["ingredientes"].items())
        if actual == expected:
            found.append({"recipe_id": recipe_id, **recipe})
    return found


def avaliar_descoberta(ingredients: list[dict[str, Any]]) -> dict[str, Any]:
    if not 3 <= len(ingredients) <= 5:
        return {"valid": False, "reason": "A descoberta exige de 3 a 5 exemplares distintos.", "discoveries": []}
    ids = [int(x.get("exemplar_id", x.get("id", 0)) or 0) for x in ingredients]
    if any(x <= 0 for x in ids) or len(ids) != len(set(ids)):
        return {"valid": False, "reason": "Cada ingrediente precisa ser um exemplar distinto.", "discoveries": []}
    ok, reason = validar_ingredientes(ingredients)
    if not ok:
        return {"valid": False, "reason": reason, "discoveries": []}
    discoveries = descobrir_receitas(ingredients)
    return {"valid": True, "reason": "Combinação analisada; nenhum ingrediente foi consumido.",
            "signature": assinatura_ingredientes(ingredients),
            "discoveries": [{"recipe_id": x["recipe_id"], "name": x["nome"],
                             "description": x["descricao"], "rarity": x["raridade_resultado"]}
                            for x in discoveries]}
