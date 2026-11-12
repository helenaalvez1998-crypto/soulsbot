"""Regressões do diretório e da navegação organizada da Nara."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _literal_assignment(path: Path, variable: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == variable for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"Atribuição {variable} não encontrada em {path}")


def _comandos_do_codigo() -> set[str]:
    saida = set()
    for path in (ROOT / "cogs").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                nome_decorator = ast.unparse(decorator.func)
                comando = node.name
                for keyword in decorator.keywords:
                    if keyword.arg == "name":
                        comando = ast.literal_eval(keyword.value)
                if nome_decorator.endswith("app_commands.command") or nome_decorator == "app_commands.command":
                    saida.add("/" + comando)
                elif nome_decorator.endswith("sl_admin.command"):
                    saida.add("/sl_admin " + comando)
    return saida


def test_diretorio_tem_areas_unicas_e_respeita_limites_do_discord():
    secoes = _literal_assignment(ROOT / "nara_help_panel.py", "COMANDOS_SECOES")
    assert len(secoes) == 9
    assert len({secao["key"] for secao in secoes}) == len(secoes)
    assert len({secao["label"] for secao in secoes}) == len(secoes)
    for secao in secoes:
        assert len(secao["label"]) <= 100
        assert len(secao["description"]) <= 100
        total_embed = len(secao["intro"])
        for titulo, conteudo in secao["fields"]:
            assert len(titulo) <= 256
            assert len(conteudo) <= 1024
            total_embed += len(titulo) + len(conteudo)
        assert total_embed <= 6000


def test_diretorio_reflete_apenas_os_dois_comandos_publicos():
    secoes = _literal_assignment(ROOT / "nara_help_panel.py", "COMANDOS_SECOES")
    conteudo = "\\n".join(
        secao["intro"] + "\\n" + "\\n".join(titulo + "\\n" + texto for titulo, texto in secao["fields"])
        for secao in secoes
    )
    indexados = set(re.findall(r"`(/[^`\\s]+(?:\\s+[^`\\s]+)?)`", conteudo))
    assert indexados == {"/nara", "/adm"}


def test_ordem_da_faq_contem_as_categorias_reais_sem_perdas():
    ordem = _literal_assignment(ROOT / "nara_help_panel.py", "FAQ_CATEGORIA_ORDEM")
    base = json.loads((ROOT / "dados" / "nara_faq.json").read_text(encoding="utf-8"))
    existentes = {
        item.get("category", "Outros") for item in base["intents"]
        if item.get("answer") or item.get("handler")
    }
    assert set(ordem) == existentes
    assert len(ordem) == len(set(ordem))


def test_comando_comandos_esta_registrado_no_cog_da_nara():
    tree = ast.parse((ROOT / "cogs" / "nara_ia.py").read_text(encoding="utf-8"))
    encontrado = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "comandos_command":
            encontrado = any(
                isinstance(decorator, ast.Call)
                and "app_commands.command" in ast.unparse(decorator.func)
                and any(k.arg == "name" and isinstance(k.value, ast.Constant) and k.value.value == "comandos"
                        for k in decorator.keywords)
                for decorator in node.decorator_list
            )
    assert encontrado
