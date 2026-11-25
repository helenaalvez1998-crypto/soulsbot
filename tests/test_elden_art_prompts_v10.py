from sistemas.atelie_coliseu import gerar_prompt_carta
from sistemas.prompt_arte_criador import gerar_prompt_arte


def test_hoslow_catalog_prompt_uses_the_live_card_data_and_specific_scene():
    from sistemas.cartas import CARTAS_POR_ID

    prompt = gerar_prompt_carta(CARTAS_POR_ID["arma_lamina_peregrino"].para_dict())
    assert "Duelista da Casa Hoslow" in prompt
    assert "FACTION: Véu Carmesim" in prompt
    assert "TACTICAL ROW: melee" in prompt
    # A V18 revision changed this catalog card from 4 to 5 and removed its generic ability.
    assert "CURRENT POWER: 5" in prompt
    assert "RARITY/MODEL POWER CEILING: 5" in prompt
    assert "Nenhuma habilidade especial" in prompt
    assert "NO SPECIAL ABILITY — HARD VISUAL RESTRICTION" in prompt
    assert "Caminho do Maculado" in prompt
    assert "Batedor da Mansão Vulcânica" in prompt
    assert "polished silver plate" in prompt
    assert "pair of long, flexible thorned whips" in prompt
    assert "promise of blood" in prompt
    assert "no spellcasting" in prompt.lower()


def test_custom_card_prompt_decomposes_all_supplied_facts_without_inventing_magic():
    definition = {
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
    prompt = gerar_prompt_arte(definition, card_id="transmutacao_hoslow_test") ["prompt"]
    for required in (
        "Duelista da Casa Hoslow", "Véu Carmesim", "Destreza", "Comum",
        "CURRENT POWER: 4", "MAXIMUM POWER FOR THIS CARD/RARITY: 5",
        "melee", "Nenhuma habilidade especial", "Peregrino",
        "Batedor da Mansão Vulcânica", "promise of blood", "FACTION ART STANDARD — VÉU CARMESIM",
        "NO SPECIAL ABILITY — HARD CONSTRAINT", "no card frame",
        "landscape 5:4",
    ):
        assert required.casefold() in prompt.casefold(), required
    assert "Do not add spellcasting" in prompt
    assert "Do not add another character merely to illustrate synergy" in prompt


def test_custom_card_prompt_resolves_ability_name_and_mechanic():
    definition = {
        "nome": "Guardião Lunar",
        "descricao": "Protege um observatório antigo sob a lua.",
        "faccao": "Lua Negra",
        "tipo": "Magia",
        "raridade": "Épica",
        "poder": 6,
        "fileira": "siege",
        "funcao_tatica": "defesa",
        "habilidade": "sangue_frio",
        "afinidades": ["lua", "magia"],
        "afinidade_dominante": "lua",
    }
    prompt = gerar_prompt_arte(definition, card_id="transmutacao_lunar_test")["prompt"]
    # The gameplay ID sangue_frio is canonically named "Concentração" in cartas.py.
    assert "Concentração" in prompt
    assert "absolute composure" in prompt
    assert "Lua Negra" in prompt
    assert "cold lunar silver" in prompt


def test_custom_card_prompt_does_not_confuse_ingredients_with_the_subject_cast():
    definition = {
        "nome": "Sentinela das Cinzas",
        "descricao": "Permanece na passagem até o último viajante atravessar.",
        "faccao": "Ordem Áurea",
        "tipo": "Força",
        "raridade": "Rara",
        "poder": 5,
        "fileira": "melee",
        "funcao_tatica": "defesa",
        "habilidade": "",
        "ingredientes": [{"nome": "Cavaleiro de Leyndell"}, {"nome": "Lobo Solitário"}],
    }
    prompt = gerar_prompt_arte(definition, card_id="transmutacao_ash_test")["prompt"]
    assert "SOURCE INGREDIENTS" in prompt
    assert "Cavaleiro de Leyndell" in prompt
    assert "Do not portray the ingredients as a group" in prompt
    assert "FACTION ART STANDARD — ORDEM ÁUREA" in prompt


def test_unknown_internal_ability_key_does_not_authorize_invented_magic():
    definition = {
        "nome": "Vigia da Ponte Partida",
        "descricao": "Mantém a passagem sob vigilância durante a noite.",
        "faccao": "Ordem Áurea",
        "tipo": "Força",
        "raridade": "Comum",
        "poder": 2,
        "fileira": "melee",
        "habilidade": "ability_key_not_in_catalog",
    }
    prompt = gerar_prompt_arte(definition, card_id="transmutacao_unknown_ability") ["prompt"]
    assert "Nenhuma habilidade especial" in prompt
    assert "NO SPECIAL ABILITY — HARD CONSTRAINT" in prompt


def test_catalog_prompt_adds_lore_to_art_interpretation_layer():
    from sistemas.cartas import CARTAS_POR_ID

    prompt = gerar_prompt_carta(CARTAS_POR_ID["arma_lamina_peregrino"].para_dict())
    assert "LORE PHRASES → CONCRETE VISUAL DECISIONS" in prompt
    assert "PROMISE OF BLOOD" in prompt
    assert "HOUSE HOSLOW CANONICAL VISUAL CUES" in prompt
