import sqlite3
import threading
from pathlib import Path

from sistemas.transmutacao_homologacao import verificar_banco_persistente


def _db(path):
    conn = sqlite3.connect(path)
    conn.executescript("""
      CREATE TABLE cartas_geradas(card_id TEXT PRIMARY KEY, owner_id INTEGER, rarity TEXT,
        art_path TEXT, art_status TEXT, status TEXT, exemplar_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE cartas_transmutacoes(id INTEGER PRIMARY KEY, tx_key TEXT UNIQUE, owner_id INTEGER,
        status TEXT, probability REAL, roll REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE cartas_exemplares(id INTEGER PRIMARY KEY, user_id INTEGER, card_id TEXT);
      CREATE TABLE cartas_materiais_transmutacao(user_id INTEGER, material_key TEXT, quantidade INTEGER);
      CREATE TABLE cartas_geradas_artes(generated_card_id TEXT, storage_path TEXT, content_hash TEXT);
      CREATE TABLE cartas_geradas_habilidades(generated_card_id TEXT, ability_id TEXT);
      CREATE TABLE cartas_colecao(user_id INTEGER, card_id TEXT, quantidade INTEGER);
    """)
    conn.commit(); conn.close()


def test_persistent_database_preflight_is_read_only_and_passes(tmp_path):
    path = tmp_path / "production-like.sqlite"
    _db(path)
    before = path.stat().st_size
    result = verificar_banco_persistente(path)
    assert result["status"] == "pass"
    assert result["integrity_check"] == "ok"
    assert result["missing_tables"] == []
    assert result["read_only"] is True
    assert path.stat().st_size == before


def test_preflight_blocks_missing_tables_without_creating_or_migrating(tmp_path):
    path = tmp_path / "partial.sqlite"
    conn = sqlite3.connect(path); conn.execute("CREATE TABLE unrelated(id INTEGER)"); conn.commit(); conn.close()
    result = verificar_banco_persistente(path)
    assert result["status"] == "blocked"
    assert "cartas_transmutacoes" in result["missing_tables"]


def test_preflight_does_not_create_missing_database(tmp_path):
    path = tmp_path / "missing.sqlite"
    result = verificar_banco_persistente(path)
    assert result["reason"] == "database_file_missing"
    assert not path.exists()


def test_file_backed_sqlite_serializes_duplicate_idempotency_key(tmp_path):
    path = tmp_path / "race.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE attempts(tx_key TEXT PRIMARY KEY, consumed INTEGER NOT NULL)")
    conn.commit(); conn.close()
    barrier = threading.Barrier(2)
    outcomes = []
    def worker():
        db = sqlite3.connect(path, timeout=5, isolation_level=None)
        try:
            barrier.wait()
            db.execute("BEGIN IMMEDIATE")
            found = db.execute("SELECT 1 FROM attempts WHERE tx_key='same-key'").fetchone()
            if found:
                outcomes.append("repeated")
            else:
                db.execute("INSERT INTO attempts VALUES ('same-key',1)")
                outcomes.append("consumed")
            db.commit()
        finally:
            db.close()
    threads = [threading.Thread(target=worker) for _ in range(2)]
    [t.start() for t in threads]; [t.join() for t in threads]
    check = sqlite3.connect(path)
    rows = check.execute("SELECT COUNT(*),SUM(consumed) FROM attempts").fetchone(); check.close()
    assert sorted(outcomes) == ["consumed", "repeated"]
    assert rows == (1, 1)


def test_file_backed_sqlite_rolls_back_consumption_on_technical_error(tmp_path):
    path = tmp_path / "rollback.sqlite"
    db = sqlite3.connect(path)
    db.executescript("CREATE TABLE inventory(qty INTEGER); INSERT INTO inventory VALUES(10);")
    db.commit()
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("UPDATE inventory SET qty=qty-3")
        raise OSError("simulated renderer failure")
    except OSError:
        db.rollback()
    assert db.execute("SELECT qty FROM inventory").fetchone()[0] == 10
    db.close()
