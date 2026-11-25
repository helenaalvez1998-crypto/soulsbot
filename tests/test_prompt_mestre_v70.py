from PIL import Image
import io

from sistemas.atelie_coliseu import (
    ARTE_ALTURA,
    ARTE_LARGURA,
    gerar_prompt_carta_estruturado,
    normalizar_imagem_carta,
)
from sistemas.arte_upload_criador import normalizar_upload_arte
from sistemas.cartas import CARTAS_POR_ID
from sistemas.prompt_arte_criador import gerar_prompt_arte


def test_catalog_prompt_uses_three_sections_exact_5_4_and_canonical_hoslow_identity():
    package = gerar_prompt_carta_estruturado(CARTAS_POR_ID["arma_lamina_peregrino"].para_dict())
    assert package["analysis"]
    assert "Duelista da Casa Hoslow" in package["analysis"]
    assert "FACTION ART STANDARD" in package["prompt"]
    assert "House Hoslow" in package["prompt"]
    assert "Mandatory 5:4 aspect ratio, horizontal composition." in package["prompt"]
    assert "16. NEGATIVE PROMPT" in package["prompt"]
    assert "ordinary sword" in package["negative_prompt"]
    assert package["recommended_aspect_ratio"] == "5:4"
    assert (package["recommended_width"], package["recommended_height"]) == (1200, 960)


def test_custom_card_prompt_obeys_master_and_returns_analysis_prompt_and_negative():
    card = {
        "nome": "Duelista da Casa Hoslow",
        "descricao": "Herdeiro de uma casa de duelistas, transforma a elegância do aço em uma promessa de sangue.",
        "categoria": "Unidade",
        "faccao": "Véu Carmesim",
        "tipo": "Destreza",
        "raridade": "Comum",
        "poder": 4,
        "poder_maximo": 5,
        "funcao_tatica": "ataque",
        "fileira": "melee",
        "habilidade": "",
        "sinergias": ["Peregrino", "Batedor da Mansão Vulcânica"],
    }
    package = gerar_prompt_arte(card, card_id="transmutacao_hoslow_v70")
    prompt = package["prompt"]
    assert "Duelista da Casa Hoslow" in package["analysis"]
    assert "Véu Carmesim" in package["analysis"]
    assert "Mandatory 5:4 aspect ratio, horizontal composition." in prompt
    assert "paired long flexible thorned whips" in prompt
    assert "do not add another character" in prompt.lower()
    assert "no special ability" in prompt.lower()
    assert "ordinary sword" in package["negative_prompt"]
    assert package["recommended_aspect_ratio"] == "5:4"
    assert (package["recommended_width"], package["recommended_height"]) == (1200, 960)


def test_catalog_atelier_normalizer_outputs_exact_5_4():
    raw = io.BytesIO()
    Image.new("RGB", (1024, 819), (50, 50, 50)).save(raw, format="PNG")
    result = normalizar_imagem_carta(raw.getvalue())
    assert (result.largura, result.altura) == (ARTE_LARGURA, ARTE_ALTURA)
    assert result.largura * 4 == result.altura * 5


def test_creator_upload_normalizer_outputs_exact_5_4():
    raw = io.BytesIO()
    Image.new("RGB", (1100, 900), (80, 80, 80)).save(raw, format="PNG")
    result = normalizar_upload_arte(raw.getvalue())
    assert result["width"] * 4 == result["height"] * 5
    assert (result["width"], result["height"]) == (1200, 960)


def test_faction_is_resolved_only_from_the_faccao_field():
    from sistemas.direcao_arte_prompts import normalizar_faccao, direcao_faccao

    assert normalizar_faccao("Ordem Áurea") == "Ordem Áurea"
    assert normalizar_faccao("Véu Carmesim") == "Véu Carmesim"
    assert normalizar_faccao("Lua Negra") == "Lua Negra"
    assert normalizar_faccao("Lua Sombria") == ""
    assert "exactly three" in direcao_faccao("Lua Sombria").casefold()

    card = {
        "nome": "Guardião Lunar",
        "descricao": "Serve a Ordem Áurea e mantém uma sinergia com magos da Lua Negra.",
        "faccao": "Véu Carmesim",
        "sinergias": ["Lua Negra"],
    }
    from sistemas.direcao_arte_prompts import montar_prompt_mestre
    prompt = montar_prompt_mestre(card=card, detail_prompt="", has_ability=False)
    assert "The supplied value is: Véu Carmesim" in prompt
    assert "FACTION ART STANDARD — VÉU CARMESIM" in prompt
    assert "FACTION ART STANDARD — ORDEM ÁUREA" not in prompt
    assert "FACTION ART STANDARD — LUA NEGRA" not in prompt


def test_canonical_character_matching_does_not_match_partial_names():
    from sistemas.direcao_arte_prompts import canonical_reference

    reference = canonical_reference({
        "nome": "Cavaleiro da Dinastia Mohgwyn",
        "descricao": "Serve no palácio subterrâneo de Mohgwyn.",
    })
    assert "CANONICAL IDENTITY CHECK" in reference
    assert "Mohg, Lord of Blood" not in reference


def test_prompt_contains_explicit_visual_authority_hierarchy():
    from sistemas.direcao_arte_prompts import montar_prompt_mestre

    prompt = montar_prompt_mestre(
        card={"nome": "Ranni", "faccao": "Lua Negra", "descricao": "A bruxa contempla a lua."},
        detail_prompt="",
        has_ability=False,
    )
    assert "VISUAL AUTHORITY HIERARCHY" in prompt
    assert "canonical armor, clothing, skin, hair, weapons or signature equipment" in prompt
    assert "Mandatory 5:4 aspect ratio, horizontal composition." in prompt
