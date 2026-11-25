"""V46 — catálogo pessoal das cartas do Laboratório."""
from __future__ import annotations
import json
from typing import Any


def filtrar_catalogo(rows: list[Any], *, query: str = "", faction: str = "",
                    rarity: str = "", affinity: str = "", role: str = "",
                    page: int = 1, page_size: int = 24) -> dict[str, Any]:
    q = str(query or "").strip().casefold()
    faction, rarity = str(faction or "").strip().casefold(), str(rarity or "").strip().casefold()
    affinity, role = str(affinity or "").strip().casefold(), str(role or "").strip().casefold()
    normalized = []
    for raw in rows:
        item = dict(raw)
        try:
            definition = json.loads(item.get("definition_json") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            definition = {}
        item["definition"] = definition
        item["affinities"] = list(definition.get("afinidades") or [])
        item["role"] = str(definition.get("funcao_tatica") or "")
        item["art_ready"] = bool(item.get("art_path")) and str(item.get("art_status")) in {"validated", "stored"}
        haystack = " ".join([
            str(item.get("name") or ""), str(item.get("card_id") or ""),
            str(item.get("faction") or ""), str(item.get("rarity") or ""),
            " ".join(map(str, item["affinities"])), item["role"],
            str(definition.get("descricao") or ""),
        ]).casefold()
        if q and q not in haystack: continue
        if faction and faction not in str(item.get("faction") or "").casefold(): continue
        if rarity and rarity != str(item.get("rarity") or "").casefold(): continue
        if affinity and affinity not in [str(x).casefold() for x in item["affinities"]]: continue
        if role and role != item["role"].casefold(): continue
        normalized.append(item)
    page_size = max(1, min(int(page_size), 100))
    page = max(1, int(page))
    total = len(normalized)
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, pages)
    start = (page - 1) * page_size
    return {"items": normalized[start:start+page_size], "total": total,
            "page": page, "page_size": page_size, "pages": pages}


def resumo_catalogo(rows: list[Any]) -> dict[str, Any]:
    from collections import Counter
    rarity, faction = Counter(), Counter()
    ready = 0
    for raw in rows:
        item = dict(raw)
        rarity[str(item.get("rarity") or "Desconhecida")] += 1
        faction[str(item.get("faction") or "Desconhecida")] += 1
        if item.get("art_path") and item.get("art_status") in {"validated", "stored"}: ready += 1
    return {"total": len(rows), "por_raridade": dict(rarity),
            "por_faccao": dict(faction), "artes_prontas": ready,
            "artes_pendentes": max(0, len(rows)-ready)}
