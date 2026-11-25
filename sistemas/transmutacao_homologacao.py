"""Ferramentas de homologação do Laboratório — V40.

Executa verificações somente leitura em banco persistente e não altera schema,
recursos, cartas ou resultados de transmutação.
"""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import Any

REQUIRED_TABLES = {
    "cartas_geradas", "cartas_transmutacoes", "cartas_exemplares",
    "cartas_materiais_transmutacao", "cartas_geradas_artes",
    "cartas_geradas_habilidades", "cartas_colecao",
}


def verificar_banco_persistente(database_path: str | os.PathLike[str]) -> dict[str, Any]:
    """Inspeciona um SQLite existente sem criar arquivo nem executar migrações."""
    path = Path(database_path)
    if not path.is_file():
        return {"status": "blocked", "reason": "database_file_missing", "read_only": True}
    if path.stat().st_size == 0:
        return {"status": "blocked", "reason": "database_file_empty", "read_only": True}
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=2)
        try:
            conn.execute("PRAGMA query_only=ON")
            integrity = str(conn.execute("PRAGMA quick_check").fetchone()[0])
            tables = {str(row[0]) for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            missing = sorted(REQUIRED_TABLES - tables)
            journal = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"status": "blocked", "reason": "database_unreadable", "error_type": type(exc).__name__, "read_only": True}
    status = "pass" if integrity == "ok" and not missing else "blocked"
    return {"status": status, "integrity_check": integrity,
            "missing_tables": missing, "journal_mode": journal,
            "database_bytes": path.stat().st_size, "read_only": True}
