"""Cobertura das respostas determinísticas com a voz social da NARA."""
from __future__ import annotations

import nara_respostas


def test_saudacao_automatica_usa_tom_coloquial_e_nao_resposta_generica():
    texto = nara_respostas.resposta_social("saudacao", cumprimento="Boa tarde")
    assert texto
    texto_normalizado = texto.casefold()
    assert any(marca in texto_normalizado for marca in ("vc", "td", "tô"))
    assert "por aqui tudo em ordem" not in texto_normalizado


def test_criador_e_chamado_de_souls_por_identidade_estavel():
    texto = nara_respostas.resposta_social("saudacao", nome="Souls")
    assert "Souls" in texto


def test_respostas_sociais_automaticas_tem_abreviacoes_naturais(monkeypatch):
    casos = {
        "como_esta": ("vc", "obg", "tô", "td"),
        "agradecimento": ("pfv", "obg", "tbm", "dps"),
        "despedida": ("dps", "pfv"),
        "motivacao": ("hj", "vc", "msm", "dnv"),
    }
    monkeypatch.setattr(nara_respostas.random, "choice", lambda opcoes: opcoes[0])
    for intent, marcas in casos.items():
        texto = nara_respostas.resposta_social(intent).casefold()
        assert any(marca in texto for marca in marcas), (intent, texto)


def test_todas_as_intencoes_sociais_têm_resposta_local():
    for intent in nara_respostas.INTENCOES_SOCIAIS:
        texto = nara_respostas.resposta_social(intent, nome="Souls")
        assert isinstance(texto, str) and texto.strip(), intent


def test_novas_respostas_estão_integradas_ao_roteador_local_do_cog():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "cogs" / "nara_ia.py").read_text(encoding="utf-8")
    assert "import nara_respostas" in source
    assert 'resposta_social("saudacao"' in source
    assert "if intent in nara_respostas.INTENCOES_SOCIAIS" in source
