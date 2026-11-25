import ast
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _schema_value(name):
    tree = ast.parse((ROOT / "database.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} não encontrado")


def _db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_schema_value("SCHEMA"))
    conn.executescript(_schema_value("SCHEMA_CARTAS"))
    conn.execute("ALTER TABLE cartas_exemplares ADD COLUMN origin_type TEXT NOT NULL DEFAULT 'catalogo'")
    conn.execute("ALTER TABLE cartas_exemplares ADD COLUMN origin_card_id TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE cartas_exemplares ADD COLUMN is_sacrificable INTEGER NOT NULL DEFAULT 1")
    conn.executescript(_schema_value("TRIGGERS_POS_MIGRACAO"))
    conn.execute("INSERT INTO users(user_id) VALUES (101)")
    conn.commit()
    return conn


def test_transmutation_tables_exist_and_are_owner_scoped():
    conn = _db()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert {"cartas_geradas", "cartas_transmutacoes",
            "cartas_geradas_habilidades", "cartas_geradas_artes"} <= names
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cartas_geradas)")}
    assert {"card_id", "owner_id", "exemplar_id", "definition_json", "art_path"} <= cols


def test_generated_exemplar_must_be_marked_non_sacrificable():
    conn = _db()
    conn.execute(
        """INSERT INTO cartas_exemplares
           (user_id,card_id,rarity,power,source,origin_type,is_sacrificable)
           VALUES (101,'tr_101','Épica',6,'transmutacao','transmutacao',0)"""
    )
    row = conn.execute(
        "SELECT origin_type,is_sacrificable FROM cartas_exemplares WHERE card_id='tr_101'"
    ).fetchone()
    assert row == ("transmutacao", 0)


def test_generated_exemplar_cannot_be_reclassified_or_unlocked():
    conn = _db()
    conn.execute(
        """INSERT INTO cartas_exemplares
           (user_id,card_id,rarity,power,source,origin_type,is_sacrificable)
           VALUES (101,'tr_102','Épica',6,'transmutacao','transmutacao',0)"""
    )
    for sql in [
        "UPDATE cartas_exemplares SET is_sacrificable=1 WHERE card_id='tr_102'",
        "UPDATE cartas_exemplares SET origin_type='catalogo' WHERE card_id='tr_102'",
        "UPDATE cartas_exemplares SET source='drop' WHERE card_id='tr_102'",
    ]:
        try:
            conn.execute(sql)
            assert False, "A proteção deveria rejeitar esta alteração."
        except sqlite3.IntegrityError:
            pass


def test_regular_exemplars_remain_sacrificable_by_default():
    conn = _db()
    conn.execute(
        """INSERT INTO cartas_exemplares
           (user_id,card_id,rarity,power,source)
           VALUES (101,'catalog_1','Comum',3,'drop')"""
    )
    row = conn.execute(
        "SELECT origin_type,is_sacrificable FROM cartas_exemplares WHERE card_id='catalog_1'"
    ).fetchone()
    assert row == ("catalogo", 1)
