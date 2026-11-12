from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_moderation_category_select_is_added_only_once_on_initial_open():
    source = (ROOT / "cogs" / "admin.py").read_text(encoding="utf-8")
    start = source.index('if action == "moderacao":')
    end = source.index('if action == "galeria":', start)
    block = source[start:end]
    assert "view = ModeracaoPainelView(bot, interaction.user.id)" in block
    assert "view.add_item(ModeracaoCategoriaSelect(view))" not in block
    assert "view.add_item(ModeracaoSolicitacaoSelect(view, view.registros[:25]))" in block


def test_moderation_view_constructor_owns_category_select():
    source = (ROOT / "cogs" / "admin.py").read_text(encoding="utf-8")
    start = source.index("class ModeracaoPainelView")
    end = source.index("async def interaction_check", start)
    block = source[start:end]
    assert "self.add_item(ModeracaoCategoriaSelect(self))" in block
