
import hashlib
from pathlib import Path
from PIL import Image
import io
import pytest

from sistemas.arte_cartas_geradas import (
    validar_manifesto_arte, persistir_arte_com_manifesto
)
from sistemas.gerador_cartas import (
    ARQUETIPOS_POR_FUNCAO, EPITETOS_POR_AFINIDADE, LORE_POR_FUNCAO
)


def png():
    im = Image.new("RGB", (300, 450), (20, 30, 40))
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


def definition():
    return {
        "card_id": "v44_card_0001", "owner_id": 123,
        "nome": "Lunar Guardião", "faccao": "Lua Negra",
        "raridade": "Épica", "afinidade_dominante": "lua",
        "funcao_tatica": "defesa", "origem_tipo": "transmutacao",
        "is_sacrificable": False, "tipo": "Magia", "poder": 6,
        "fileira": "melee",
    }


def test_v44_manifest_binds_card_owner_and_hash():
    manifest = validar_manifesto_arte(definition(), png(), provider="external_art_provider",
                                      concept="guardião lunar")
    assert manifest["card_id"] == "v44_card_0001"
    assert manifest["owner_id"] == 123
    assert manifest["image_sha256"] == hashlib.sha256(png()).hexdigest()
    assert manifest["unique_asset_key"] == "123:v44_card_0001"


def test_v44_persists_immutable_asset_and_manifest(tmp_path):
    result = persistir_arte_com_manifesto(definition(), png(), base_dir=tmp_path)
    assert Path(result["storage_path"]).exists()
    assert Path(result["manifest_path"]).exists()
    again = persistir_arte_com_manifesto(definition(), png(), base_dir=tmp_path)
    assert again["content_hash"] == result["content_hash"]


def test_v44_rejects_invalid_faction():
    d = definition()
    d["faccao"] = "Facção inexistente"
    with pytest.raises(ValueError):
        validar_manifesto_arte(d, png())


def test_v45_identity_catalog_covers_all_tactical_functions():
    assert set(ARQUETIPOS_POR_FUNCAO) == {"ataque", "defesa", "controle", "suporte"}
    assert set(LORE_POR_FUNCAO) == set(ARQUETIPOS_POR_FUNCAO)
    assert set(EPITETOS_POR_AFINIDADE) >= {
        "sagrado", "fogo", "sangue", "morte", "lua", "magia",
        "relampago", "gravidade", "gelo", "veneno", "ancestral", "bestial"
    }
    assert all(len(v) >= 3 for v in ARQUETIPOS_POR_FUNCAO.values())
