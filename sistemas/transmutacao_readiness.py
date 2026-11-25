"""Preflight operacional read-only do Laboratório — V38.

Não declara produção pronta. Verifica arquivos, configuração, dependências e
contratos mínimos antes da homologação; não abre nem modifica banco de produção.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Iterable

REQUIRED_FILES = (
    "database.py", "bot.py", "site_hub.py", "site/transmutacao.html",
    "sistemas/transmutacao.py", "sistemas/gerador_cartas.py",
    "sistemas/afinidades.py", "sistemas/economia_transmutacao.py",
    "sistemas/arte_cartas_geradas.py",
)
REQUIRED_TABLES = (
    "cartas_exemplares", "cartas_geradas", "cartas_transmutacoes",
    "cartas_materiais_transmutacao", "cartas_geradas_habilidades",
    "cartas_geradas_artes", "cartas_geracao_balanceamento",
)
REQUIRED_ENV = ("DISCORD_TOKEN",)


def avaliar_arquivos(root: str | Path) -> list[dict[str, str]]:
    base = Path(root)
    return [{"check": f"file:{name}", "status": "ok" if (base / name).is_file() else "fail"}
            for name in REQUIRED_FILES]


def avaliar_dependencias(installed: Iterable[str]) -> list[dict[str, str]]:
    names = {str(x).lower().replace("_", "-").split("==")[0] for x in installed}
    required = {"aiosqlite", "aiohttp", "pillow"}
    return [{"check": f"dependency:{name}", "status": "ok" if name in names else "fail"}
            for name in sorted(required)]


def avaliar_ambiente(env: Mapping[str, str]) -> list[dict[str, str]]:
    checks = []
    for name in REQUIRED_ENV:
        checks.append({"check": f"env:{name}", "status": "ok" if str(env.get(name, "")).strip() else "fail"})
    # Credenciais nunca são devolvidas nem incluídas no relatório.
    data_dir = str(env.get("DATA_DIR", "")).strip()
    checks.append({"check": "env:DATA_DIR", "status": "ok" if data_dir else "warn"})
    return checks


def avaliar_schema(conn) -> list[dict[str, str]]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    existing = {str(row[0]) for row in rows}
    return [{"check": f"table:{name}", "status": "ok" if name in existing else "fail"}
            for name in REQUIRED_TABLES]


def consolidar_preflight(*groups: list[dict[str, str]]) -> dict:
    checks = [item for group in groups for item in group]
    failed = sum(x["status"] == "fail" for x in checks)
    warnings = sum(x["status"] == "warn" for x in checks)
    return {"checks": checks, "total": len(checks), "failed": failed,
            "warnings": warnings, "status": "blocked" if failed else ("conditional" if warnings else "pass"),
            "production_approved": False,
            "note": "Preflight não substitui homologação com duas contas, banco persistente e ambiente real."}
