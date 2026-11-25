from sistemas.gerador_cartas import (
    calcular_distribuicao_50_50, avaliar_balanceamento_cumulativo,
    gerar_carta_procedural, validar_definicao_gerada, validar_lote_gerado,
)


def ingredient(i, card_id, name, rarity="Rara", tipo="Força", **extra):
    return {
        "exemplar_id": i, "card_id": card_id, "nome": name,
        "categoria": "Unidade", "raridade": rarity, "tipo": tipo,
        "is_sacrificable": 1, **extra,
    }


def trio():
    return [
        ingredient(11, "chefe_maliketh_morte", "Maliketh Morte", tipo="Força"),
        ingredient(12, "chefe_gurranq_bestial", "Gurranq Bestial", tipo="Força"),
        ingredient(13, "chefe_messmer_chama", "Messmer Chama", tipo="Magia"),
    ]


def test_generator_is_deterministic_for_same_seed_and_inputs():
    a = gerar_carta_procedural(trio(), seed="server-secret-seed", generated_id="generated_0001")
    b = gerar_carta_procedural(trio(), seed="server-secret-seed", generated_id="generated_0001")
    assert a == b
    assert a["valido"] is True
    assert a["status"] == "proposta_gerada"


def test_generated_definition_has_valid_faction_rarity_power_and_protection():
    result = gerar_carta_procedural(trio(), seed="seed-2", generated_id="generated_0002")
    definition = result["definition"]
    ok, errors = validar_definicao_gerada(definition)
    assert ok, errors
    assert definition["categoria"] == "Unidade"
    assert definition["raridade"] in {"Comum", "Rara", "Épica", "Lendária", "Mítica"}
    assert definition["is_sacrificable"] is False
    assert definition["origem_tipo"] == "transmutacao"
    assert definition["owner_scoped"] is True


def test_only_existing_approved_common_abilities_can_be_selected():
    result = gerar_carta_procedural(trio(), seed="seed-with-ability", generated_id="generated_0003")
    definition = result["definition"]
    if definition["habilidade"]:
        assert definition["habilidade"] in {
            "primeira_luz", "retaliacao", "impeto", "ultimo_folego", "contragolpe",
            "encadeamento", "adaptacao", "sangue_frio", "instinto", "precisao",
            "drenagem", "cacador_arcano", "quebra_ritmo",
        }
    assert validar_definicao_gerada(definition)[0]


def test_generator_rejects_invalid_inputs_and_never_consumes_resources():
    bad = trio()[:2]
    result = gerar_carta_procedural(bad, seed="seed", generated_id="generated_0004")
    assert result["valido"] is False
    good = gerar_carta_procedural(trio(), seed="seed", generated_id="generated_0005")
    assert good["consumo_executado"] is False
    assert good["persistencia_executada"] is False
    assert good["publicada"] is False


def test_primordial_and_singular_rarities_cannot_be_generated():
    ingredients = trio()
    ingredients[0]["raridade"] = "Primordial"
    assert not gerar_carta_procedural(ingredients, seed="s", generated_id="generated_0006")["valido"]
    ingredients = trio()
    ingredients[0]["raridade"] = "Singular"
    assert not gerar_carta_procedural(ingredients, seed="s", generated_id="generated_0007")["valido"]


def test_cumulative_50_50_monitor_does_not_force_individual_attempts():
    stats = calcular_distribuicao_50_50(60, 40)
    assert stats["total"] == 100
    assert stats["percentual_sem_habilidade"] == 60.0
    assert stats["percentual_com_habilidade"] == 40.0
    generated = gerar_carta_procedural(
        trio(), seed="seed", generated_id="generated_0008",
        balanceamento={"sem_habilidade": 60, "com_habilidade": 40},
    )
    assert generated["balanceamento_cumulativo"]["total"] == 101


def test_generated_id_must_be_server_style_unique_identifier():
    result = gerar_carta_procedural(trio(), seed="seed", generated_id="x")
    assert result["valido"] is False
    assert result["status"] == "id_invalido"


def test_function_compatibility_and_impact_power_budget_are_enforced():
    # Busca sementes até obter uma carta com habilidade, sem fixar o resultado aleatório.
    generated = None
    for n in range(100):
        result = gerar_carta_procedural(trio(), seed=f"ability-{n}", generated_id=f"generated_{1000+n}")
        if result.get("valido") and result["has_ability"]:
            generated = result["definition"]
            break
    assert generated is not None
    assert generated["habilidade"] in {
        "retaliacao", "impeto", "contragolpe", "encadeamento", "adaptacao",
        "instinto", "precisao", "cacador_arcano", "quebra_ritmo",
        "drenagem", "primeira_luz", "ultimo_folego", "sangue_frio",
    }
    assert validar_definicao_gerada(generated)[0]
    if generated["habilidade"] in {"contragolpe", "instinto", "drenagem"}:
        assert generated["poder"] < {"Comum": 5, "Rara": 6, "Épica": 7, "Lendária": 8, "Mítica": 9}[generated["raridade"]]


def test_strict_validator_rejects_tampered_fields_and_ability_mismatch():
    result = gerar_carta_procedural(trio(), seed="tamper", generated_id="generated_2001")
    definition = dict(result["definition"])
    definition["faccao"] = "Lua Negra"
    assert not validar_definicao_gerada(definition)[0]
    definition = dict(result["definition"])
    definition["is_sacrificable"] = True
    assert not validar_definicao_gerada(definition)[0]
    definition = dict(result["definition"])
    definition["raridade"] = "Primordial"
    assert not validar_definicao_gerada(definition)[0]


def test_cumulative_balance_monitor_uses_sample_threshold_and_alerts():
    small = avaliar_balanceamento_cumulativo(8, 2)
    assert small["status"] == "amostra_insuficiente"
    balanced = avaliar_balanceamento_cumulativo(50, 50)
    assert balanced["status"] == "dentro_da_meta"
    skewed = avaliar_balanceamento_cumulativo(80, 20)
    assert skewed["status"] == "revisao_de_balanceamento"
    assert skewed["alerta"] is True


def test_batch_validator_finds_duplicate_ids_and_invalid_cards():
    a = gerar_carta_procedural(trio(), seed="batch-a", generated_id="generated_3001")["definition"]
    b = gerar_carta_procedural(trio(), seed="batch-b", generated_id="generated_3002")["definition"]
    report = validar_lote_gerado([a, b])
    assert report["valido"] is True
    duplicate = validar_lote_gerado([a, dict(a)])
    assert duplicate["valido"] is False
    assert duplicate["ids_duplicados"] == ["generated_3001"]
