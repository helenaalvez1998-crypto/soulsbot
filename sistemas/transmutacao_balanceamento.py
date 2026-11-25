"""V47 — métricas de equilíbrio do Laboratório; diagnóstico, não ajuste automático."""
from __future__ import annotations
from collections import Counter
from typing import Any


def analisar_balanceamento(cards: list[Any], *, min_sample: int = 20) -> dict[str, Any]:
    rarities, factions, abilities, roles = Counter(), Counter(), Counter(), Counter()
    powers_by_rarity: dict[str, list[int]] = {}
    total = len(cards)
    with_ability = 0
    names = Counter()
    for raw in cards:
        c = dict(raw)
        rarity = str(c.get("rarity") or "Desconhecida")
        faction = str(c.get("faction") or "Desconhecida")
        rarities[rarity] += 1; factions[faction] += 1
        names[str(c.get("name") or c.get("card_id") or "")] += 1
        try: definition = c.get("definition") or __import__("json").loads(c.get("definition_json") or "{}")
        except Exception: definition = {}
        power = int(c.get("power") or definition.get("poder") or 0)
        powers_by_rarity.setdefault(rarity, []).append(power)
        role = str(definition.get("funcao_tatica") or "não definida")
        roles[role] += 1
        ability = definition.get("habilidade") or ""
        if ability:
            with_ability += 1
            abilities[str(ability)] += 1
    without = total - with_ability
    pct_ability = 100 * with_ability / total if total else 0.0
    deviation = abs(50.0 - pct_ability) if total else 0.0
    power_stats = {
        k: {"count": len(v), "min": min(v), "max": max(v),
            "mean": round(sum(v)/len(v), 2)}
        for k, v in powers_by_rarity.items() if v
    }
    duplicate_names = {k:v for k,v in names.items() if v > 1}
    warnings = []
    if total < int(min_sample): warnings.append("amostra_insuficiente")
    elif deviation > 5: warnings.append("distribuicao_50_50_fora_da_tolerancia")
    if duplicate_names: warnings.append("nomes_repetidos")
    if any(not x for x in [c.get("art_path") for c in map(dict,cards)]):
        warnings.append("cartas_sem_arte_associada")
    return {
        "total": total, "com_habilidade": with_ability, "sem_habilidade": without,
        "percentual_com_habilidade": round(pct_ability,2),
        "percentual_sem_habilidade": round(100-pct_ability,2) if total else 0.0,
        "desvio_meta_50_50_pp": round(deviation,2), "amostra_minima": int(min_sample),
        "amostra_suficiente": total >= int(min_sample),
        "distribuicao_raridade": dict(rarities), "distribuicao_faccao": dict(factions),
        "distribuicao_funcao": dict(roles), "frequencia_habilidades": dict(abilities),
        "poder_por_raridade": power_stats, "nomes_repetidos": duplicate_names,
        "alertas": warnings, "status": "diagnostico" if warnings else "sem_alertas_detectados",
        "nota": "Métricas agregadas não substituem partidas competitivas e análise de taxa de vitória."
    }
