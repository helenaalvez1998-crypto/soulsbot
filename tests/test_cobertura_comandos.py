"""Garante que todo comando continua acessível por botão em /nara (membros) ou /adm (admin).

Os comandos principais publicados são /nara, /adm e /nara_relacionamento. Os demais comandos existem nos cogs, mas só
podem ser usados se houver um botão/ação em algum painel. Se este teste falhar após você
adicionar um comando, inclua-o em COBERTURA apontando para a ação do painel que o abre.
"""
import ast
from pathlib import Path

from tests.test_ux_navigation import _category_actions

ROOT = Path(__file__).resolve().parents[1]

PUBLICADOS = {"nara", "adm", "nara_relacionamento"}

# comando -> (painel, ação). Painel "membros" = /nara; "admin" = /adm.
COBERTURA = {
    # ---- membros (/nara)
    "coliseu": ("membros", "coliseu"),
    "zerados": ("membros", "zerados"),
    "remover_zerado": ("membros", "remover_zerado"),
    "loja": ("membros", "loja"),
    "nivel": ("membros", "nivel"),
    "ranking-xp": ("membros", "ranking_xp"),
    "nara_memoria": ("membros", "memoria"),
    "central_ajuda": ("membros", "ajuda"),
    "comandos": ("ajuda", "Ver índice de comandos"),
    # ---- admin (/adm)
    "cargo_painel": ("admin", "cargos_opcoes"),
    "editar_painel_cargos": ("admin", "cargos_texto"),
    "painel_verificacao": ("admin", "post_verificacao"),
    "painel_cargos": ("admin", "post_cargos"),
    "colizeu": ("admin", "colizeu_atualizar"),
    "painel_colizeu": ("admin", "post_coliseu"),
    "painel_loja": ("admin", "post_loja"),
    "painel_santuarios": ("admin", "post_santuario"),
    "painel_ajuda_nara": ("admin", "post_ajuda"),
    "painel_principal": ("admin", "publicar_paineis"),
    "postar_painel": ("admin", "publicar_paineis"),
    "painel_platinas": ("admin", "publicar_paineis"),
    "postar_painel_zerados": ("admin", "publicar_paineis"),
    "configurar_video_transmissao": ("admin", "transmissao_video"),
    "gemini_status": ("admin", "ia_provedores"),
    "nara_relatorio": ("admin", "ia_relatorio"),
    "status_youtube": ("admin", "youtube_status"),
    "teste_video": ("admin", "youtube_test_video"),
    "teste_live": ("admin", "youtube_test_live"),
    "status_ofertas": ("admin", "ofertas_status"),
    "previa_oferta": ("admin", "ofertas_preview"),
    "noticias_canal": ("admin", "radar_games"),
    "noticias_adicionar_feed": ("admin", "radar_games"),
    "noticias_listar_feeds": ("admin", "radar_games"),
    "noticias_remover_feed": ("admin", "radar_games"),
    "noticias_status": ("admin", "radar_games"),
    "noticias_testar": ("admin", "radar_games"),
    "sl_admin publicar_central": ("admin", "sl_central"),
    "sl_admin jogo_adicionar": ("admin", "sl_jogo"),
    "sl_admin desafio_adicionar": ("admin", "sl_desafio"),
    "sl_admin invalidar": ("admin", "sl_invalidar"),
}


def _comandos_do_codigo() -> set[str]:
    encontrados: set[str] = set()
    for arquivo in (ROOT / "cogs").glob("*.py"):
        tree = ast.parse(arquivo.read_text(encoding="utf-8"))
        grupos = {}
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and getattr(node.value.func, "attr", "") == "Group"
            ):
                nome = next((k.value.value for k in node.value.keywords if k.arg == "name"), None)
                for alvo in node.targets:
                    if isinstance(alvo, ast.Name):
                        grupos[alvo.id] = nome
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if isinstance(deco, ast.Call) and getattr(deco.func, "attr", "") == "command":
                    nome = next(
                        (k.value.value for k in deco.keywords if k.arg == "name"), node.name
                    )
                    base = deco.func.value
                    prefixo = grupos.get(base.id) if isinstance(base, ast.Name) else None
                    encontrados.add(f"{prefixo} {nome}" if prefixo else nome)
    return encontrados - PUBLICADOS


def test_todo_comando_tem_botao_mapeado():
    sem_mapa = _comandos_do_codigo() - set(COBERTURA)
    assert not sem_mapa, f"Comandos sem botão mapeado em algum painel: {sorted(sem_mapa)}"


def test_mapa_nao_aponta_para_comando_inexistente():
    obsoletos = set(COBERTURA) - _comandos_do_codigo()
    assert not obsoletos, f"Entradas do mapa sem comando correspondente: {sorted(obsoletos)}"


def test_cada_acao_mapeada_existe_no_painel_correto():
    admin = (ROOT / "cogs" / "admin.py").read_text(encoding="utf-8")
    membros = (ROOT / "cogs" / "painel_membros.py").read_text(encoding="utf-8")
    ajuda = (ROOT / "nara_help_panel.py").read_text(encoding="utf-8")
    acoes_admin = {a for v in _category_actions(admin, "ADMIN_CATEGORIAS").values() for a in v}
    # precisa existir um BOTÃO na categoria (ter só o handler não basta)
    acoes_membros = {a for v in _category_actions(membros, "MEMBROS_CATEGORIAS").values() for a in v}
    for comando, (painel, acao) in COBERTURA.items():
        if painel == "admin":
            assert acao in acoes_admin, f"/{comando}: ação '{acao}' não está em ADMIN_CATEGORIAS"
        elif painel == "membros":
            assert acao in acoes_membros, f"/{comando}: ação '{acao}' sem botão em MEMBROS_CATEGORIAS"
        else:
            assert acao in ajuda, f"/{comando}: botão '{acao}' não encontrado na central de ajuda"
