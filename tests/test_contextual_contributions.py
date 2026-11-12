"""Regressões estáticas das ações contextuais por setor."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def test_runs_keep_suggestions_inside_central_and_empty_states():
    source = read("cogs/soulslike.py")
    assert '\"game_suggestion\", \"runs\", \"Sugerir jogo ausente\"' in source
    assert '\"challenge\", \"runs\", \"Propor desafio\"' in source
    assert "class VoltarCentralView" in source
    assert "Ainda não há jogos cadastrados. Você pode sugerir um jogo diretamente nesta tela" in source
    assert "Sugerir desafio** nesta mesma tela" in source

def test_catalogs_keep_submission_actions_available_during_search():
    source = read("cogs/catalogo_integrado.py")
    assert "Não encontrou? Enviar jogo" in source
    assert "Não encontrou? Enviar mod" in source
    # O botão do jogo fica fora do if de resultados: também aparece quando a busca
    # retorna resultados parecidos, mas não o título que a pessoa queria.
    build = source.split("class CatalogView", 1)[1].split("class ", 1)[0]
    assert 'if self.mode == "ver":' in build
    assert 'elif self.mode == "ver":' not in build
    mods = source.split("class ModsCatalogView", 1)[1].split("class ", 1)[0]
    assert 'if self.rows:' in mods and 'self.add_item(enviar)' in mods

def test_contextual_entry_points_exist_in_specialized_sectors():
    expected = {
        "cogs/platinas.py": ("platinas", "Sugerir melhoria em Platinas"),
        "cogs/zerados.py": ("zerados", "Sugerir melhoria em Zerados"),
        "cogs/loja.py": ("loja", "Sugerir item para a loja"),
        "cogs/santuario.py": ("santuario", "Sugerir melhoria"),
        "nara_help_panel.py": ("ajuda", "Sugerir pergunta ou resposta"),
        "cogs/comunidade.py": ("lore", "Publicar lore"),
    }
    for path, (sector, label) in expected.items():
        source = read(path)
        assert sector in source, path
        assert label in source, path
        assert "adicionar_botao_contribuicao_contextual" in source, path

def test_guides_have_their_own_panel_and_admin_publish_action():
    community = read("cogs/comunidade.py")
    admin = read("cogs/admin.py")
    assert "class CommunityGuidesView" in community
    assert "publicar_painel_guias" in community
    assert "community_guides_publish" in admin
    assert 'origin_sector="guias"' in community
    assert 'class CommunityArchiveView' in community
    assert "Publicar lore" in community and "Enviar guia" in community

def test_submission_remembers_origin_and_returns_direct_follow_up_actions():
    community = read("cogs/comunidade.py")
    database = read("database.py")
    assert "origin_sector=self.origin_sector" in community
    assert "origin_channel_id=interaction.channel_id" in community
    assert "class CommunitySubmissionReceiptView" in community
    assert "Acompanhar minha contribuição" in community
    assert "Enviar outra neste setor" in community
    assert '"origin_sector"' in database and "TEXT NOT NULL DEFAULT ''" in database
    assert '"origin_channel_id": "INTEGER"' in database

def test_admin_review_displays_origin_sector_and_channel():
    source = read("cogs/admin.py")
    assert "Setor de origem" in source
    assert "Canal de origem" in source
