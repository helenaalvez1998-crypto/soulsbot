"""Relatórios agregados e read-only do Laboratório — V39.

Não expõe IDs de jogador, chaves idempotentes, snapshots de ingredientes ou
conteúdo de cartas. Os dados são agregados para revisão operacional.
"""
from __future__ import annotations
from collections import Counter
from typing import Any

VALID_STATUSES = {"sucesso", "falha", "repetida", "erro", "failed", "success"}


def _dict_rows(rows: Any) -> list[dict]:
    return [dict(row) for row in (rows or [])]


async def gerar_relatorio_telemetria(db: Any, *, dias: int = 30) -> dict:
    """Retorna contagens agregadas; não altera banco nem identifica jogadores."""
    days = max(1, min(int(dias), 365))
    attempts = _dict_rows(await db._all(
        """SELECT status,probability,roll,failure_reason,created_at
           FROM cartas_transmutacoes
           WHERE created_at >= datetime('now', ?)""", (f"-{days} days",)))
    cards = _dict_rows(await db._all(
        """SELECT rarity,art_status,status,
                  CASE WHEN exemplar_id IS NULL THEN 0 ELSE 1 END AS has_exemplar,
                  CASE WHEN art_path<>'' THEN 1 ELSE 0 END AS has_art_path
           FROM cartas_geradas
           WHERE created_at >= datetime('now', ?)""", (f"-{days} days",)))
    status_counts = Counter(str(x.get("status") or "unknown") for x in attempts)
    rarity_counts = Counter(str(x.get("rarity") or "unknown") for x in cards)
    invalid_probability = sum(
        1 for x in attempts
        if x.get("probability") is None or not 0 <= float(x["probability"]) <= 90
    )
    invalid_roll = sum(
        1 for x in attempts
        if x.get("roll") is not None and not 0 <= float(x["roll"]) < 100
    )
    missing_art = sum(1 for x in cards if x.get("art_status") != "validated" or not x.get("has_art_path"))
    missing_exemplar = sum(1 for x in cards if not x.get("has_exemplar"))
    return {
        "window_days": days,
        "attempts_total": len(attempts),
        "attempts_by_status": dict(sorted(status_counts.items())),
        "generated_cards_total": len(cards),
        "generated_cards_by_rarity": dict(sorted(rarity_counts.items())),
        "integrity_checks": {
            "invalid_probability_records": invalid_probability,
            "invalid_roll_records": invalid_roll,
            "cards_without_validated_art": missing_art,
            "cards_without_exemplar": missing_exemplar,
        },
        "alerts": [
            name for name, count in (
                ("probability_out_of_policy", invalid_probability),
                ("roll_out_of_range", invalid_roll),
                ("generated_card_art_incomplete", missing_art),
                ("generated_card_without_exemplar", missing_exemplar),
            ) if count
        ],
        "privacy": "aggregate_only; no owner IDs, tx keys, ingredient IDs or card definitions",
        "read_only": True,
    }
