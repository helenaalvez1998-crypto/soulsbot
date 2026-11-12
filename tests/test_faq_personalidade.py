"""Garantias editoriais da base de respostas da NARA."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _base():
    return json.loads((ROOT / "dados" / "nara_faq.json").read_text(encoding="utf-8"))


def test_base_tem_108_respostas_textuais_e_17_intencoes_dinamicas():
    base = _base()
    intents = base["intents"]
    respostas = [item for item in intents if str(item.get("answer") or "").strip()]
    dinamicas = [item for item in intents if item.get("handler")]
    assert len(intents) == 125
    assert len(respostas) == 108
    assert len(dinamicas) == 17
    assert all(item.get("verified_sources", {}).get("files") for item in intents)


def test_faq_descreve_nara_como_presenca_exclusivamente_textual():
    descricao = _base()["description"].casefold()
    assert "responde por texto" in descricao
    assert "não fala nem envia áudio" in descricao


def test_respostas_nao_descrevem_a_nara_como_agente_de_voz():
    textos = [str(item.get("answer") or "").casefold() for item in _base()["intents"]]
    textos = [texto for texto in textos if texto]
    proibidos = ("estou ouvindo", "minha voz", "vou falar com você", "envie um áudio para mim")
    for texto in textos:
        assert not any(termo in texto for termo in proibidos), texto


def test_respostas_preservam_dados_operacionais_criticos():
    respostas = {item["intent"]: item.get("answer", "") for item in _base()["intents"]}
    assert "10 e 20 XP" in respostas["xp_por_mensagem"]
    assert "60 segundos" in respostas["xp_por_mensagem"]
    assert "5 XP a cada 5 minutos" in respostas["xp_por_voz"]
    assert "20 MB por arquivo" in respostas["regras_comprovante_platina"]
    assert "40 MB no total" in respostas["regras_comprovante_platina"]
    assert "3 jogos zerados aprovados" in respostas["limite_recompensa_zerados"]
    assert "100 XP" in respostas["recompensa_run_recorde"]
    assert "200 XP no total" in respostas["recompensa_run_recorde"]
    assert "Eterno Renascido" in respostas["loja_catalogo_precos"]


def test_respostas_de_staff_continuam_separadas_da_ajuda_publica():
    itens = _base()["intents"]
    restritas = [item for item in itens if item.get("staff_only")]
    assert restritas
    assert all(item.get("answer") or item.get("handler") for item in restritas)
