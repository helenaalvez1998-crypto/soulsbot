from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_and_news_modules_are_loaded_by_nara():
    source = (ROOT / "bot.py").read_text(encoding="utf-8")
    assert '"cogs.catalogo_integrado"' in source
    assert '"cogs.game_news"' in source
    assert "COMANDOS_PRINCIPAIS = frozenset({\"nara\", \"adm\"})" in source


def test_catalog_module_does_not_create_or_run_a_second_bot():
    source = (ROOT / "cogs" / "catalogo_integrado.py").read_text(encoding="utf-8")
    assert "class CatalogoIntegrado(commands.Cog)" in source
    assert "commands.Bot(" not in source
    assert ".run(" not in source
    assert "class MainView" in source
    assert "class AdminView" in source


def test_news_module_uses_catalog_database_and_no_second_bot():
    source = (ROOT / "cogs" / "game_news.py").read_text(encoding="utf-8")
    assert "from cogs.catalogo_integrado import DB_PATH" in source
    assert "class GameNewsCog(commands.Cog)" in source
    assert "commands.Bot(" not in source
    assert ".run(" not in source


def test_member_and_admin_panels_expose_integrated_features():
    member = (ROOT / "cogs" / "painel_membros.py").read_text(encoding="utf-8")
    admin = (ROOT / "cogs" / "admin.py").read_text(encoding="utf-8")
    assert '"catalogos": {' in member
    assert '("catalogos", "Catálogos", "📚")' in member
    assert '"catalogos": {' in admin
    assert '"radar": {' in admin
    assert 'if action == "radar_games":' in admin
    assert 'if action in ("catalogo_jogos", "catalogo_mods"):' in admin


def test_catalog_public_view_has_no_separate_admin_entry():
    source = (ROOT / "cogs" / "catalogo_integrado.py").read_text(encoding="utf-8")
    main_view = source.split("class MainView", 1)[1].split("# ------------------------------------------------------------------ catálogo separado de mods", 1)[0]
    assert 'custom_id="catalogo:admin"' not in main_view



def test_public_catalog_panel_can_be_published_from_admin_panel():
    source = (ROOT / "cogs" / "catalogo_integrado.py").read_text(encoding="utf-8")
    assert "async def publicar_painel_publico" in source
    assert 'value="publish_panel"' in source
    assert "CatalogoPublicarChannelView" in source
