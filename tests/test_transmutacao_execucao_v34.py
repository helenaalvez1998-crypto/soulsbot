import ast
import asyncio
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from sistemas import transmutacao as service


ROOT = Path(__file__).resolve().parents[1]


def _schema(name):
    tree = ast.parse((ROOT / "database.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(name)


class AsyncCursor:
    def __init__(self, cursor):
        self.cursor = cursor
        self.rowcount = cursor.rowcount
        self.lastrowid = cursor.lastrowid

    async def fetchone(self):
        return self.cursor.fetchone()

    async def fetchall(self):
        return self.cursor.fetchall()


class AsyncConn:
    def __init__(self, conn):
        self.raw = conn

    async def execute(self, sql, args=()):
        return AsyncCursor(self.raw.execute(sql, args))


class FakeTx:
    def __init__(self, conn):
        self.conn = AsyncConn(conn)
        self.raw = conn

    async def _one(self, sql, args=()):
        return self.raw.execute(sql, args).fetchone()

    async def _all(self, sql, args=()):
        return self.raw.execute(sql, args).fetchall()


class FakeDB:
    def __init__(self):
        self.raw = sqlite3.connect(":memory:")
        self.raw.row_factory = sqlite3.Row
        self.raw.execute("PRAGMA foreign_keys=ON")
        self.raw.executescript(_schema("SCHEMA"))
        self.raw.executescript(_schema("SCHEMA_CARTAS"))
        cols = {r[1] for r in self.raw.execute("PRAGMA table_info(cartas_exemplares)")}
        for name, declaration in (
            ("origin_type", "TEXT NOT NULL DEFAULT 'catalogo'"),
            ("origin_card_id", "TEXT NOT NULL DEFAULT ''"),
            ("is_sacrificable", "INTEGER NOT NULL DEFAULT 1"),
        ):
            if name not in cols:
                self.raw.execute(f"ALTER TABLE cartas_exemplares ADD COLUMN {name} {declaration}")
        self.raw.executescript(_schema("TRIGGERS_POS_MIGRACAO"))
        self.raw.execute("INSERT INTO users(user_id) VALUES (777)")
        for material, amount in (
            ("essencia_vida", 1000), ("fragmento_ancestral", 1000),
            ("nucleo_convergencia", 1000),
        ):
            self.raw.execute(
                "INSERT INTO cartas_materiais_transmutacao(user_id,material_key,quantidade) VALUES (777,?,?)",
                (material, amount),
            )
        ingredients = [
            "gwent_unidade_baluarte",
            "gwent_unidade_portaestandarte",
            "gwent_unidade_mestre_forja",
        ]
        for card_id in ingredients:
            self.raw.execute(
                """INSERT INTO cartas_exemplares
                   (user_id,card_id,rarity,power,source,origin_type,origin_card_id,is_sacrificable)
                   VALUES (777,?, 'Rara', 5, 'drop', 'catalogo', '', 1)""",
                (card_id,),
            )
        self.raw.commit()

    @asynccontextmanager
    async def transaction(self):
        self.raw.execute("BEGIN IMMEDIATE")
        try:
            yield FakeTx(self.raw)
            self.raw.commit()
        except BaseException:
            self.raw.rollback()
            raise


@pytest.fixture
def db():
    return FakeDB()


def _ids(db):
    return [r[0] for r in db.raw.execute(
        "SELECT id FROM cartas_exemplares WHERE user_id=777 ORDER BY id"
    )]


def _patch_art(monkeypatch, tmp_path):
    original = service.persistir_arte_original
    monkeypatch.setattr(
        service, "persistir_arte_original",
        lambda definition, data: original(definition, data, base_dir=tmp_path),
    )


def test_success_consumes_ingredients_and_materials_and_publishes_personal_card(db, monkeypatch, tmp_path):
    _patch_art(monkeypatch, tmp_path)
    monkeypatch.setattr(service.secrets, "randbelow", lambda n: 0)
    result = asyncio.run(service.executar_transmutacao(
        db, 777, _ids(db), tx_key="v34-success-0001"
    ))
    assert result["status"] == "sucesso"
    assert result["consumo_executado"] is True
    assert db.raw.execute("SELECT COUNT(*) FROM cartas_exemplares WHERE user_id=777").fetchone()[0] == 1
    generated = db.raw.execute(
        "SELECT card_id,owner_id,art_status,status FROM cartas_geradas"
    ).fetchone()
    assert generated["owner_id"] == 777
    assert generated["art_status"] == "validated"
    assert generated["status"] == "published"
    assert db.raw.execute(
        "SELECT COUNT(*) FROM cartas_colecao WHERE user_id=777 AND card_id=?",
        (generated["card_id"],),
    ).fetchone()[0] == 1
    exemplar = db.raw.execute(
        "SELECT origin_type,is_sacrificable FROM cartas_exemplares WHERE card_id=?",
        (generated["card_id"],),
    ).fetchone()
    assert tuple(exemplar) == ("transmutacao", 0)
    persisted = service._scoped_tx_key(777, "v34-success-0001")
    assert db.raw.execute(
        "SELECT COUNT(*) FROM cartas_transmutacoes WHERE tx_key=? AND status='success'", (persisted,)
    ).fetchone()[0] == 1


def test_legitimate_failure_consumes_all_committed_resources_but_creates_no_card(db, monkeypatch):
    monkeypatch.setattr(service.secrets, "randbelow", lambda n: 9999)
    before = db.raw.execute(
        "SELECT material_key,quantidade FROM cartas_materiais_transmutacao ORDER BY material_key"
    ).fetchall()
    result = asyncio.run(service.executar_transmutacao(
        db, 777, _ids(db), tx_key="v34-failure-0001"
    ))
    after = db.raw.execute(
        "SELECT material_key,quantidade FROM cartas_materiais_transmutacao ORDER BY material_key"
    ).fetchall()
    assert result["status"] == "falha"
    assert result["consumo_executado"] is True
    assert [r[1] for r in after] != [r[1] for r in before]
    assert db.raw.execute("SELECT COUNT(*) FROM cartas_geradas").fetchone()[0] == 0
    assert db.raw.execute("SELECT COUNT(*) FROM cartas_exemplares WHERE user_id=777").fetchone()[0] == 0


def test_active_deck_ingredients_are_not_consumed(db):
    ids = _ids(db)
    db.raw.execute(
        "INSERT INTO cartas_gwent_decks(user_id,card_ids_json,exemplar_ids_json) VALUES (777,'[]',?)",
        ('[' + str(ids[0]) + ']',),
    )
    db.raw.commit()
    before = db.raw.execute("SELECT COUNT(*) FROM cartas_exemplares WHERE user_id=777").fetchone()[0]
    result = asyncio.run(service.executar_transmutacao(db, 777, ids, tx_key="v34-deck-0001"))
    after = db.raw.execute("SELECT COUNT(*) FROM cartas_exemplares WHERE user_id=777").fetchone()[0]
    assert result["status"] == "ingrediente_equipado_no_deck"
    assert result["consumo_executado"] is False
    assert before == after


def test_insufficient_materials_do_not_consume_ingredients(db):
    db.raw.execute(
        "UPDATE cartas_materiais_transmutacao SET quantidade=0 WHERE user_id=777"
    )
    db.raw.commit()
    before = _ids(db)
    result = asyncio.run(service.executar_transmutacao(
        db, 777, before, tx_key="v34-no-materials-0001"
    ))
    assert result["status"] == "materiais_insuficientes"
    assert result["consumo_executado"] is False
    assert _ids(db) == before


def test_idempotency_key_prevents_double_consumption(db, monkeypatch, tmp_path):
    _patch_art(monkeypatch, tmp_path)
    monkeypatch.setattr(service.secrets, "randbelow", lambda n: 0)
    ids = _ids(db)
    first = asyncio.run(service.executar_transmutacao(db, 777, ids, tx_key="v34-idempotent-0001"))
    second = asyncio.run(service.executar_transmutacao(db, 777, ids, tx_key="v34-idempotent-0001"))
    assert first["status"] == "sucesso"
    assert second["status"] == "repetida"
    assert db.raw.execute("SELECT COUNT(*) FROM cartas_transmutacoes").fetchone()[0] == 1


def test_technical_art_failure_rolls_back_everything(db, monkeypatch):
    before_ids = _ids(db)
    before_materials = [tuple(r) for r in db.raw.execute(
        "SELECT material_key,quantidade FROM cartas_materiais_transmutacao ORDER BY material_key"
    )]
    monkeypatch.setattr(service.secrets, "randbelow", lambda n: 0)
    def fail_art(*args, **kwargs):
        raise OSError("renderer unavailable")
    monkeypatch.setattr(service, "gerar_arte_original", fail_art)
    with pytest.raises(OSError):
        asyncio.run(service.executar_transmutacao(
            db, 777, before_ids, tx_key="v34-technical-error-0001"
        ))
    assert _ids(db) == before_ids
    after_materials = [tuple(r) for r in db.raw.execute(
        "SELECT material_key,quantidade FROM cartas_materiais_transmutacao ORDER BY material_key"
    )]
    assert after_materials == before_materials
    assert db.raw.execute("SELECT COUNT(*) FROM cartas_transmutacoes").fetchone()[0] == 0


def test_other_owner_cannot_use_someone_elses_exemplars(db):
    ids = _ids(db)
    result = asyncio.run(service.executar_transmutacao(db, 888, ids, tx_key="v34-owner-0001"))
    assert result["status"] == "ingredientes_nao_encontrados_ou_sem_propriedade"
    assert result["consumo_executado"] is False


def test_same_client_tx_key_is_isolated_between_owners(db, monkeypatch, tmp_path):
    _patch_art(monkeypatch, tmp_path)
    monkeypatch.setattr(service.secrets, "randbelow", lambda n: 0)
    db.raw.execute("INSERT INTO users(user_id) VALUES (888)")
    for material, amount in (("essencia_vida", 1000), ("fragmento_ancestral", 1000), ("nucleo_convergencia", 1000)):
        db.raw.execute("INSERT INTO cartas_materiais_transmutacao(user_id,material_key,quantidade) VALUES (888,?,?)", (material, amount))
    for card_id in ("gwent_unidade_baluarte", "gwent_unidade_portaestandarte", "gwent_unidade_mestre_forja"):
        db.raw.execute("INSERT INTO cartas_exemplares(user_id,card_id,rarity,power,source,origin_type,origin_card_id,is_sacrificable) VALUES (888,?,'Rara',5,'drop','catalogo','',1)", (card_id,))
    db.raw.commit()
    first = asyncio.run(service.executar_transmutacao(db, 777, _ids(db), tx_key="same-client-key"))
    ids_888 = [r[0] for r in db.raw.execute("SELECT id FROM cartas_exemplares WHERE user_id=888 ORDER BY id")]
    second = asyncio.run(service.executar_transmutacao(db, 888, ids_888, tx_key="same-client-key"))
    assert first["status"] == "sucesso"
    assert second["status"] == "sucesso"
    assert first["generated_card_id"] != second["generated_card_id"]
    assert db.raw.execute("SELECT COUNT(*) FROM cartas_transmutacoes").fetchone()[0] == 2
    assert service._scoped_tx_key(777, "same-client-key") != service._scoped_tx_key(888, "same-client-key")
