"""Regressões da Central de Aprovação unificada, sem exigir discord.py no ambiente de teste."""
from __future__ import annotations

import ast
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"Atribuição {name} não encontrada em {path}")


def test_migracao_preserva_zerados_antigos_como_aprovados():
    schema = _assignment(ROOT / "database.py", "SCHEMA")
    migrations = _assignment(ROOT / "database.py", "MIGRACOES_COLUNAS")
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE zerados (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            game TEXT NOT NULL, platform TEXT NOT NULL, finished_at TEXT NOT NULL,
            comment TEXT NOT NULL DEFAULT '', xp_awarded INTEGER NOT NULL DEFAULT 0,
            denarios_awarded INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    db.execute(
        "INSERT INTO zerados(user_id,game,platform,finished_at) VALUES (1,'Elden Ring','PC','2026-10-01')"
    )
    db.executescript(schema)
    for column, ddl in migrations["zerados"].items():
        if column not in {r["name"] for r in db.execute("PRAGMA table_info(zerados)")}:
            db.execute(f"ALTER TABLE zerados ADD COLUMN {column} {ddl}")
    db.execute("UPDATE zerados SET approved_at=created_at WHERE status='approved' AND approved_at IS NULL")
    row = db.execute("SELECT status, approved_at, created_at FROM zerados WHERE id=1").fetchone()
    assert row["status"] == "approved"
    assert row["approved_at"] == row["created_at"]


def test_pedidos_pendentes_nao_entram_no_perfil_ou_ranking():
    schema = _assignment(ROOT / "database.py", "SCHEMA")
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(schema)
    db.execute("INSERT INTO zerados(user_id,game,platform,finished_at,status) VALUES (1,'Dark Souls','PC','2026-11-01','pending')")
    db.execute("INSERT INTO zerados(user_id,game,platform,finished_at,status) VALUES (2,'Elden Ring','PC','2026-11-02','approved')")
    assert db.execute("SELECT COUNT(*) FROM zerados WHERE user_id=1 AND status='approved'").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM zerados WHERE user_id=2 AND status='approved'").fetchone()[0] == 1
    assert db.execute("SELECT user_id FROM zerados WHERE status='approved' GROUP BY user_id").fetchall()[0][0] == 2


def test_os_tres_fluxos_usam_o_mesmo_canal_central():
    platinas = (ROOT / "cogs" / "platinas.py").read_text(encoding="utf-8")
    runs = (ROOT / "cogs" / "soulslike.py").read_text(encoding="utf-8")
    zerados = (ROOT / "cogs" / "zerados.py").read_text(encoding="utf-8")
    assert '"mod_channel"' in platinas
    assert '"mod_channel"' in runs
    assert '"mod_channel"' in zerados
    assert "criar_zerado_pendente" in zerados
    assert "registrar_zerado_com_recompensa" not in zerados
    assert 'custom_id="zer:approve"' in zerados
    assert 'custom_id="zer:reject"' in zerados
    assert "self.bot.add_view(ZeradoRevisaoView(self))" in zerados


def test_faq_explica_que_zerados_passam_pela_aprovacao():
    faq = json.loads((ROOT / "dados" / "nara_faq.json").read_text(encoding="utf-8"))
    answers = {item.get("intent"): item.get("answer", "") for item in faq["intents"]}
    assert "Central de Aprovação" in answers["como_registrar_zerado"]
    assert "só depois de aprovado" in answers["zerado_sem_aprovacao"]
    assert "jogos zerados" in answers["como_funciona_aprovacao"]



def test_migracao_zerados_adiciona_vinculo_unico_com_platina():
    migrations = _assignment(ROOT / "database.py", "MIGRACOES_COLUNAS")
    assert migrations["zerados"]["source_platina_id"] == "INTEGER"
    database_source = (ROOT / "database.py").read_text(encoding="utf-8")
    assert "idx_zerados_source_platina_unique" in database_source
    assert "ON zerados(source_platina_id) WHERE source_platina_id IS NOT NULL" in database_source


def test_aprovacao_de_platina_cria_zerado_na_mesma_transacao():
    database_source = (ROOT / "database.py").read_text(encoding="utf-8")
    start = database_source.index("async def aprovar_platina_com_recompensa")
    end = database_source.index("async def platinas_do_usuario", start)
    method = database_source[start:end]
    assert "Registro automático pela aprovação da platina." in method
    assert "status='approved'" in method
    assert "source_platina_id" in method
    assert "lower(game)=lower(?)" in method
    assert "limite_zerados" in method
    assert "xp_awarded=?, denarios_awarded=?" in method
    assert "async with self.transaction() as tx:" in method
