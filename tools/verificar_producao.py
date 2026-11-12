"""Pré-verificação offline, sem conexão com Discord nem acesso a credenciais.

Uso: python tools/verificar_producao.py
Retorna 0 quando as verificações offline passam; não equivale à homologação.
"""
from __future__ import annotations

import ast
import importlib.util
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validar_schema():
    tree = ast.parse((ROOT / "database.py").read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"SCHEMA", "INDICES_POS_MIGRACAO"}:
                    values[target.id] = ast.literal_eval(node.value)
    with sqlite3.connect(":memory:") as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(values["SCHEMA"])
        for table, columns in {
            "zerados": {"source_platina_id": "INTEGER"},
        }.items():
            for column, definition in columns.items():
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        conn.executescript(values["INDICES_POS_MIGRACAO"])
        required = {"users", "platinas", "sl_runs", "zerados", "logs", "catalog_import_jobs"}
        found = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert required <= found, f"Tabelas ausentes: {required-found}"
        conn.execute("INSERT INTO users(user_id,xp) VALUES(1,10)")
        conn.execute("UPDATE users SET xp=xp+5 WHERE user_id=1")
        assert conn.execute("SELECT xp FROM users WHERE user_id=1").fetchone()[0] == 15
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    return len(found)


def main():
    failures = []
    files = list(ROOT.rglob("*.py"))
    for file in files:
        try:
            compile(file.read_bytes(), str(file), "exec")
        except (SyntaxError, UnicodeError) as exc:
            failures.append(f"Compilação: {file.relative_to(ROOT)}: {exc}")
    try:
        tables = validar_schema()
        print(f"OK: schema SQLite, {tables} tabelas, integridade e operação básica")
    except Exception as exc:
        failures.append(f"Schema SQLite: {exc}")
    for package in ("discord", "aiosqlite"):
        if importlib.util.find_spec(package) is None:
            print(f"PENDENTE: dependência {package} não instalada; integração não executada")
        else:
            print(f"DISPONÍVEL: {package} (testes de integração ainda necessários)")
    print(f"OK: {len(files)} arquivos Python verificados" if not failures else "FALHA: verificação")
    for error in failures:
        print(error, file=sys.stderr)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
