from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
BOT_SOURCE = (ROOT / "bot.py").read_text(encoding="utf-8")


def test_only_nara_and_adm_are_allowed_primary_slash_commands():
    tree = ast.parse(BOT_SOURCE)
    assignment = next(
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "COMANDOS_PRINCIPAIS" for t in node.targets)
    )
    assert isinstance(assignment.value, ast.Call)
    allowed = ast.literal_eval(assignment.value.args[0])
    assert set(allowed) == {"nara", "adm"}


def test_startup_filters_commands_before_remote_sync():
    assert BOT_SOURCE.index("_manter_apenas_comandos_principais(self.tree)") < BOT_SOURCE.index("async def on_ready")
    assert "self.tree.copy_global_to(guild=guild)" in BOT_SOURCE
    assert "self.tree.clear_commands(guild=None)" in BOT_SOURCE
    assert "self.tree.sync(guild=guild)" in BOT_SOURCE


def test_legacy_commands_are_not_individually_synced_by_startup():
    # A árvore é filtrada após carregar todos os Cogs e antes da sincronização.
    setup = BOT_SOURCE.split("async def setup_hook", 1)[1].split("async def on_ready", 1)[0]
    assert "_manter_apenas_comandos_principais(self.tree)" in setup
