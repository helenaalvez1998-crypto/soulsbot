import asyncio
from pathlib import Path

import pytest
from sistemas.gwent import LEADERS


def test_leader_art_db_upsert_list_and_restore_default():
    pytest.importorskip("aiosqlite")
    from database import Database

    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            assert await db.coliseu_gwent_lideres_artes_listar() == []
            saved = await db.coliseu_gwent_lider_arte_salvar(
                "comandante_fornalha", b"jpeg-test-bytes", "image/jpeg", "Artista", 1300117955236991046
            )
            assert saved["leader_id"] == "comandante_fornalha"
            assert bytes(saved["image_data"]) == b"jpeg-test-bytes"
            rows = await db.coliseu_gwent_lideres_artes_listar()
            assert len(rows) == 1 and rows[0]["leader_id"] == "comandante_fornalha"

            updated = await db.coliseu_gwent_lider_arte_salvar(
                "comandante_fornalha", b"new-jpeg", "image/jpeg", "Outro artista", 42
            )
            assert bytes(updated["image_data"]) == b"new-jpeg"
            assert updated["artist_name"] == "Outro artista"
            assert len(await db.coliseu_gwent_lideres_artes_listar()) == 1

            assert await db.coliseu_gwent_lider_arte_remover("comandante_fornalha") is True
            assert await db.coliseu_gwent_lider_arte_obter("comandante_fornalha") is None
            assert await db.coliseu_gwent_lider_arte_remover("comandante_fornalha") is False
        finally:
            await db.close()
    asyncio.run(scenario())


def test_all_registered_leaders_have_builtin_art_fallbacks_and_admin_api_routes():
    root = Path(__file__).resolve().parents[1]
    bot_source = (root / "bot.py").read_text(encoding="utf-8")
    app_source = (root / "site" / "app.js").read_text(encoding="utf-8")
    index_source = (root / "site" / "index.html").read_text(encoding="utf-8")
    asset_ids = {
        "comandante_fornalha", "bastiao_ancestral", "juiz_cerco", "mestre_veu",
        "sombra_caminhante", "voz_caidos", "arquimaga_eclipse", "mestre_eclipse",
        "oraculo_tempestade",
    }
    assert set(LEADERS) == asset_ids
    assert 'app.router.add_post("/api/gwent/atelier/leaders/{leader_id}/art"' in bot_source
    assert 'app.router.add_delete("/api/gwent/atelier/leaders/{leader_id}/art"' in bot_source
    assert 'app.router.add_get("/api/gwent/leaders/{leader_id}/art"' in bot_source
    assert "_atelier_is_admin(user_id)" in bot_source
    assert "loadAtelierLeaderArtAdmin" in app_source
    assert "uploadAtelierLeaderArt" in app_source
    assert "removeAtelierLeaderArt" in app_source
    assert "atelier-leader-art-select" in index_source


def test_leader_art_schema_is_persistent_and_has_content_revision():
    import ast
    import sqlite3

    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "database.py").read_text(encoding="utf-8"))
    schemas = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"SCHEMA", "SCHEMA_CARTAS"}:
                    schemas[target.id] = ast.literal_eval(node.value)
    connection = sqlite3.connect(":memory:")
    connection.executescript(schemas["SCHEMA"])
    connection.executescript(schemas["SCHEMA_CARTAS"])
    columns = {row[1] for row in connection.execute("PRAGMA table_info(cartas_gwent_lideres_artes)")}
    assert {"leader_id", "image_data", "mime_type", "artist_name", "uploaded_by", "revision"} <= columns
    connection.execute(
        "INSERT INTO cartas_gwent_lideres_artes(leader_id,image_data,mime_type,artist_name,uploaded_by,revision) VALUES(?,?,?,?,?,?)",
        ("comandante_fornalha", b"jpeg", "image/jpeg", "artist", 1, "hash-v1"),
    )
    connection.execute(
        "UPDATE cartas_gwent_lideres_artes SET image_data=?,revision=? WHERE leader_id=?",
        (b"replacement", "hash-v2", "comandante_fornalha"),
    )
    assert connection.execute(
        "SELECT image_data,revision FROM cartas_gwent_lideres_artes WHERE leader_id=?",
        ("comandante_fornalha",),
    ).fetchone() == (b"replacement", "hash-v2")
    connection.close()


def test_every_builtin_leader_image_exists():
    root = Path(__file__).resolve().parents[1]
    fallback_names = {
        "godfrey", "morgott", "radagon", "mohg", "rykard", "esgar",
        "rennala", "astel", "loretta",
    }
    for name in fallback_names:
        assert (root / "site" / "assets" / "leaders" / f"{name}.webp").is_file()
