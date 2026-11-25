import json
from sistemas.transmutacao_catalogo import filtrar_catalogo, resumo_catalogo
from sistemas.transmutacao_balanceamento import analisar_balanceamento


def cards():
    return [
      {"card_id":"card_alpha_01","name":"Lunar Guardião","rarity":"Épica","faction":"Lua Negra","power":6,
       "art_path":"/private/a.png","art_status":"validated",
       "definition_json":json.dumps({"afinidades":["lua","magia"],"funcao_tatica":"defesa","descricao":"Guardião da lua","habilidade":"sangue_frio"})},
      {"card_id":"card_beta_02","name":"Áureo Carrasco","rarity":"Rara","faction":"Ordem Áurea","power":5,
       "art_path":"","art_status":"pending",
       "definition_json":json.dumps({"afinidades":["sagrado"],"funcao_tatica":"ataque","descricao":"Executor","habilidade":""})},
      {"card_id":"card_gamma_03","name":"Carmesim Oráculo","rarity":"Lendária","faction":"Véu Carmesim","power":7,
       "art_path":"/private/c.png","art_status":"stored",
       "definition_json":json.dumps({"afinidades":["sangue"],"funcao_tatica":"suporte","descricao":"Oráculo","habilidade":"drenagem"})},
    ]


def test_v46_filters_and_paginates_by_affinity_and_role():
    result=filtrar_catalogo(cards(), affinity="lua", role="defesa", page=1, page_size=1)
    assert result["total"]==1 and result["items"][0]["card_id"]=="card_alpha_01"


def test_v46_searches_description_and_returns_art_status():
    result=filtrar_catalogo(cards(), query="guardião")
    assert result["total"]==1 and result["items"][0]["art_ready"] is True


def test_v46_summary_counts_rarity_faction_and_art():
    result=resumo_catalogo(cards())
    assert result["total"]==3 and result["artes_prontas"]==2 and result["artes_pendentes"]==1


def test_v47_reports_50_50_and_power_by_rarity():
    result=analisar_balanceamento(cards(), min_sample=3)
    assert result["total"]==3
    assert result["com_habilidade"]==2 and result["sem_habilidade"]==1
    assert result["distribuicao_raridade"]["Épica"]==1
    assert result["poder_por_raridade"]["Épica"]["mean"]==6


def test_v47_warns_small_sample_and_duplicate_names():
    sample=cards()[:1]+cards()[:1]
    result=analisar_balanceamento(sample,min_sample=20)
    assert "amostra_insuficiente" in result["alertas"]
    assert "nomes_repetidos" in result["alertas"]


def test_v47_reports_50_50_deviation_over_five_points():
    sample=cards()
    sample.extend([{"card_id":f"c{i:08}","name":f"Name {i}","rarity":"Comum","faction":"Lua Negra","power":3,
      "definition_json":json.dumps({"habilidade":"instinto","funcao_tatica":"ataque"})} for i in range(20)])
    result=analisar_balanceamento(sample,min_sample=20)
    assert "distribuicao_50_50_fora_da_tolerancia" in result["alertas"]
