"""Conhecimento dinâmico limitado ao runtime e às permissões do membro."""
from __future__ import annotations

from types import SimpleNamespace
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import nara_conhecimento  # noqa: E402


class Perms:
    def __init__(self, **values):
        self.__dict__.update(values)
        self.value = sum((1 << i) for i, k in enumerate(values) if values[k])

    def is_superset(self, other):
        return all(not bool(v) or bool(getattr(self, k, False)) for k, v in other.__dict__.items() if k != "value")


def test_lista_comandos_reflete_arvore_real_e_oculta_comando_restrito():
    publico = SimpleNamespace(name="nivel", description="Mostra seu nível", default_permissions=None)
    restrito = SimpleNamespace(name="config", description="Configura o servidor",
                               default_permissions=Perms(manage_guild=True))
    tree = SimpleNamespace(get_commands=lambda: [publico, restrito])
    bot = SimpleNamespace(tree=tree, cogs={"Perfil": object(), "NaraIA": object()})
    membro = SimpleNamespace(guild_permissions=Perms(manage_guild=False))
    comandos = nara_conhecimento.comandos_visiveis(bot, membro)
    assert [c.caminho for c in comandos] == ["/nivel"]
    ajuda = nara_conhecimento.formatar_ajuda(bot, membro)
    assert "/nivel" in ajuda and "/config" not in ajuda


def test_grupo_de_comandos_e_flattenado_com_caminho():
    sub = SimpleNamespace(name="listar", description="Lista registros", default_permissions=None)
    grupo = SimpleNamespace(name="coliseu", description="", default_permissions=None, commands=[sub])
    bot = SimpleNamespace(tree=SimpleNamespace(get_commands=lambda: [grupo]), cogs={})
    assert nara_conhecimento.comandos_visiveis(bot)[0].caminho == "/coliseu listar"


def test_contexto_nao_contem_dados_privados_do_banco():
    bot = SimpleNamespace(tree=SimpleNamespace(get_commands=lambda: []), cogs={"Loja": object()})
    contexto = nara_conhecimento.inventario_runtime(bot)
    assert "Loja" in contexto
    assert "saldo" not in contexto.lower()
    assert "999999" not in contexto


def test_comando_com_check_customizado_e_omitido_sem_prova_de_acesso():
    publico = SimpleNamespace(name="ajuda", description="Ajuda", default_permissions=None, checks=[])
    protegido = SimpleNamespace(name="admin", description="Admin", default_permissions=None,
                                checks=[object()])
    bot = SimpleNamespace(tree=SimpleNamespace(get_commands=lambda: [publico, protegido]), cogs={})
    comandos = nara_conhecimento.comandos_visiveis(bot, SimpleNamespace(guild_permissions=Perms()))
    assert [c.caminho for c in comandos] == ["/ajuda"]


def test_ajuda_organiza_comandos_por_fluxo_e_nao_em_ordem_alfabetica():
    comandos = [
        SimpleNamespace(name="nara", description="Central interativa dos membros", default_permissions=None),
        SimpleNamespace(name="ranking-xp", description="Ranking de XP", default_permissions=None),
        SimpleNamespace(name="zerados", description="Jogos concluídos", default_permissions=None),
        SimpleNamespace(name="coliseu", description="Painel principal", default_permissions=None),
        SimpleNamespace(name="central_ajuda", description="Ajuda", default_permissions=None),
        SimpleNamespace(name="nivel", description="Nível", default_permissions=None),
    ]
    bot = SimpleNamespace(tree=SimpleNamespace(get_commands=lambda: comandos), cogs={})
    texto = nara_conhecimento.formatar_ajuda(bot)
    assert texto.index("**Comece por aqui**") < texto.index("**Perfil e progressão**")
    assert texto.index("**Perfil e progressão**") < texto.index("**Jogos e conquistas**")
    assert texto.index("`/nara`") < texto.index("`/nivel`") < texto.index("`/zerados`")
    assert "`/nara`" in texto


def test_inventario_da_ia_usa_a_mesma_organizacao_por_area():
    comandos = [
        SimpleNamespace(name="zerados", description="Jogos concluídos", default_permissions=None),
        SimpleNamespace(name="central_ajuda", description="Ajuda", default_permissions=None),
        SimpleNamespace(name="coliseu", description="Painel principal", default_permissions=None),
    ]
    bot = SimpleNamespace(tree=SimpleNamespace(get_commands=lambda: comandos), cogs={})
    texto = nara_conhecimento.inventario_runtime(bot)
    assert texto.index("[Comece por aqui]") < texto.index("[Perfil e progressão]")
    assert texto.index("[Perfil e progressão]") < texto.index("[Jogos e conquistas]")
