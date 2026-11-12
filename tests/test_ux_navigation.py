"""Regressões de navegação dos painéis /nara e /adm."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def _category_actions(source: str, variable: str):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == variable
            for target in node.targets
        ):
            result = {}
            for key_node, value_node in zip(node.value.keys, node.value.values):
                if not isinstance(key_node, ast.Constant):
                    continue
                category = key_node.value
                actions = next(
                    value
                    for key, value in zip(value_node.keys, value_node.values)
                    if isinstance(key, ast.Constant) and key.value == "acoes"
                )
                result[category] = [
                    entry.elts[0].value
                    for entry in actions.elts
                    if isinstance(entry, ast.Tuple)
                    and isinstance(entry.elts[0], ast.Constant)
                ]
            return result
    raise AssertionError(f"{variable} não encontrado")


def _dispatch_actions(source: str, function_name: str):
    tree = ast.parse(source)
    function = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    actions = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Compare):
            if (
                isinstance(node.left, ast.Name)
                and node.left.id == "action"
            ):
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                        actions.add(comparator.value)
                    elif isinstance(comparator, ast.Tuple):
                        actions.update(
                            item.value for item in comparator.elts
                            if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        )
    return actions


def test_todas_as_acoes_dos_membros_tem_handler():
    source = (ROOT / "cogs" / "painel_membros.py").read_text(encoding="utf-8")
    actions = {
        action
        for category_actions in _category_actions(source, "MEMBROS_CATEGORIAS").values()
        for action in category_actions
    }
    dispatched = _dispatch_actions(source, "_executar_acao_membro")
    assert actions <= dispatched
    assert {"perfil", "santuario"} <= dispatched


def test_todas_as_acoes_administrativas_tem_handler():
    source = (ROOT / "cogs" / "admin.py").read_text(encoding="utf-8")
    actions = {
        action
        for category_actions in _category_actions(source, "ADMIN_CATEGORIAS").values()
        for action in category_actions
    }
    assert actions == _dispatch_actions(source, "_executar_acao_admin")


def test_paineis_estao_divididos_em_categorias():
    members = (ROOT / "cogs" / "painel_membros.py").read_text(encoding="utf-8")
    admin = (ROOT / "cogs" / "admin.py").read_text(encoding="utf-8")
    assert "class MembrosCategoriaView" in members
    assert "class PainelMembrosView" in members
    assert "class AdminCategoriaView" in admin
    assert "class AdminMainView" in admin
    assert 'custom_id=f"adm:categoria:{categoria}"' in admin


def test_paineis_pessoais_verificam_usuario():
    members = (ROOT / "cogs" / "painel_membros.py").read_text(encoding="utf-8")
    admin = (ROOT / "cogs" / "admin.py").read_text(encoding="utf-8")
    assert "interaction.user.id != self.user_id" in members
    assert "interaction.user.id != self.user_id" in admin



def test_acessos_diretos_de_perfil_e_santuario_tem_handler():
    source = (ROOT / "cogs" / "painel_membros.py").read_text(encoding="utf-8")
    assert 'MembrosAcessoDiretoButton(self, "perfil"' in source
    assert 'MembrosAcessoDiretoButton(self, "santuario"' in source
    actions = _dispatch_actions(source, "_executar_acao_membro")
    assert {"perfil", "santuario"} <= actions


def test_coliseu_explica_modulos_existentes_sem_criar_novos():
    source = (ROOT / "cogs" / "painel_membros.py").read_text(encoding="utf-8")
    for name in ("Platinas", "Zerados", "Runs e desafios"):
        assert name in source
