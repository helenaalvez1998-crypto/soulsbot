from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_exemplar_queries_return_security_metadata_for_engine_validation():
    source = (ROOT / "database.py").read_text(encoding="utf-8")
    start = source.index("async def coliseu_listar_exemplares")
    end = source.index("async def coliseu_evoluir_exemplar", start)
    body = source[start:end]
    for field in ("user_id", "origin_type", "origin_card_id", "is_sacrificable"):
        assert field in body
    assert "WHERE user_id=?" in body


def test_personal_card_resolution_is_owner_scoped_and_engine_rechecks_owner():
    source = (ROOT / "bot.py").read_text(encoding="utf-8")
    start = source.index("async def _gwent_generated_card_payload")
    end = source.index("async def _api_gwent_deck", start)
    body = source[start:end]
    assert "WHERE owner_id=? AND card_id=?" in body
    assert "preparar_carta_pessoal(definition, exemplar, owner_id=int(user_id))" in body


def test_battle_snapshot_resolves_personal_cards_through_owner_scoped_helper():
    source = (ROOT / "bot.py").read_text(encoding="utf-8")
    start = source.index("async def _gwent_deck_snapshots")
    end = source.index("async def ", start + 20)
    body = source[start:end]
    assert "_gwent_generated_card_payload(user_id, str(card_id), record)" in body
