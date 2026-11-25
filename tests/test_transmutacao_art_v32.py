import hashlib
from pathlib import Path

import pytest

from sistemas.arte_cartas_geradas import (
    gerar_arte_original, persistir_arte_original, verificar_arte,
)


def definition(card_id="generated_art_0001", owner_id=701):
    return {
        "card_id": card_id, "owner_id": owner_id,
        "nome": "Lunar Sentinela", "categoria": "Unidade",
        "tipo": "Magia", "faccao": "Lua Negra",
        "raridade": "Épica", "poder": 6, "custo": 0,
        "habilidade": "primeira_luz", "descricao": "Uma sentinela moldada pela lua.",
        "fileira": "melee", "afinidades": ["lua", "magia"],
        "afinidade_dominante": "lua", "funcao_tatica": "defesa",
        "origem_tipo": "transmutacao", "is_sacrificable": False,
    }


def test_art_is_original_deterministic_png_for_each_card_identity():
    first = gerar_arte_original(definition())
    again = gerar_arte_original(definition())
    other = gerar_arte_original(definition("generated_art_0002"))
    assert first[:8] == bytes([137, 80, 78, 71, 13, 10, 26, 10])
    assert first == again
    assert hashlib.sha256(first).hexdigest() != hashlib.sha256(other).hexdigest()


def test_art_persistence_is_owner_scoped_and_integrity_checked(tmp_path):
    card = definition()
    image = gerar_arte_original(card)
    stored = persistir_arte_original(card, image, base_dir=tmp_path)
    path = Path(stored["storage_path"])
    assert path.exists()
    assert path.parent.name == str(card["owner_id"])
    assert stored["content_hash"] == hashlib.sha256(image).hexdigest()
    assert verificar_arte(path, stored["content_hash"])
    again = persistir_arte_original(card, image, base_dir=tmp_path)
    assert again["idempotent"] is True


def test_art_is_immutable_for_a_card_id(tmp_path):
    card = definition()
    first = gerar_arte_original(card)
    persistir_arte_original(card, first, base_dir=tmp_path)
    altered = first + b"tamper"
    with pytest.raises(FileExistsError):
        persistir_arte_original(card, altered, base_dir=tmp_path)


def test_invalid_personal_identity_is_rejected():
    card = definition("../escape")
    with pytest.raises(ValueError):
        gerar_arte_original(card)
    card = definition()
    card["is_sacrificable"] = True
    with pytest.raises(ValueError):
        gerar_arte_original(card)


def test_art_hash_tampering_is_detected(tmp_path):
    card = definition()
    image = gerar_arte_original(card)
    stored = persistir_arte_original(card, image, base_dir=tmp_path)
    path = Path(stored["storage_path"])
    path.write_bytes(b"not an image")
    assert not verificar_arte(path, stored["content_hash"])
