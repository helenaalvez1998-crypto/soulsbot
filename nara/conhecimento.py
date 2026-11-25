"""Inventário de capacidades reais obtido do runtime do NARA.

Não varre arquivos nem infere funcionalidades por nomes de arquivos: usa apenas
cogs carregados e comandos registrados na árvore ativa do discord.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ComandoVisivel:
    caminho: str
    descricao: str


def _permissao_suficiente(member: Any, command: Any) -> bool:
    # Checks customizados podem consultar banco/contexto/permissões do Discord em runtime.
    # Não os executamos para montar ajuda; omitimos o comando quando não é possível provar acesso.
    if getattr(command, "checks", None):
        return False
    required = getattr(command, "default_permissions", None)
    if required is None:
        return True
    if member is None:
        return False
    actual = getattr(member, "guild_permissions", None)
    if actual is None:
        return False
    try:
        return bool(actual.is_superset(required))
    except (AttributeError, TypeError):
        try:
            req = int(required.value)
            got = int(actual.value)
            return (got & req) == req
        except (AttributeError, TypeError, ValueError):
            return False


def _flatten_command(command: Any, prefix: str, member: Any, out: list[ComandoVisivel]) -> None:
    name = str(getattr(command, "name", "")).strip()
    if not name or not _permissao_suficiente(member, command):
        return
    path = f"{prefix} {name}".strip()
    children = getattr(command, "commands", None)
    if children:
        for child in children:
            _flatten_command(child, path, member, out)
        return
    desc = str(getattr(command, "description", "") or "").strip()
    out.append(ComandoVisivel("/" + path.replace(" ", " "), desc[:180]))


def comandos_visiveis(bot: Any, member: Any = None) -> list[ComandoVisivel]:
    """Comandos reais registrados e autorizados para o membro atual."""
    tree = getattr(bot, "tree", None)
    getter = getattr(tree, "get_commands", None)
    if not callable(getter):
        return []
    saida: list[ComandoVisivel] = []
    try:
        commands = getter()
    except Exception:
        return []
    for command in commands or ():
        _flatten_command(command, "", member, saida)
    return sorted(saida, key=lambda c: c.caminho.casefold())


def cogs_carregados(bot: Any) -> list[str]:
    cogs = getattr(bot, "cogs", {}) or {}
    try:
        nomes = [str(nome) for nome in cogs.keys()]
    except AttributeError:
        return []
    return sorted(nomes, key=str.casefold)


def inventario_runtime(bot: Any, member: Any = None, *, limite: int = 45) -> str:
    """Resumo curto para a Nara; não inclui membros, saldos, canais privados ou segredos."""
    cogs = cogs_carregados(bot)
    comandos = comandos_visiveis(bot, member)
    ordenados = sorted(comandos, key=lambda c: (_grupo_ajuda(c.caminho)[0], c.caminho.casefold()))
    linhas = ["INVENTÁRIO REAL DO NARABOT (runtime; não presumir recursos ausentes):"]
    linhas.append("Cogs atualmente carregados: " + (", ".join(cogs) if cogs else "nenhum identificado"))
    if ordenados:
        linhas.append("Comandos slash disponíveis para este usuário, agrupados por função:")
        grupo_atual = None
        for comando in ordenados[:limite]:
            _, grupo = _grupo_ajuda(comando.caminho)
            if grupo != grupo_atual:
                grupo_atual = grupo
                linhas.append(f"[{grupo}]")
            linha = f"{comando.caminho} — {comando.descricao}" if comando.descricao else comando.caminho
            linhas.append(linha)
    else:
        linhas.append("A árvore atual não retornou comandos slash visíveis para este usuário.")
    if len(ordenados) > limite:
        linhas.append(f"Mais {len(ordenados) - limite} comandos omitidos por limite de contexto. O índice por área é `/nara`.")
    linhas.append("Não afirme que pode configurar ou administrar algo apenas por existir um cog; exija ferramenta executável correspondente.")
    return "\n".join(linhas)


def _grupo_ajuda(caminho: str) -> tuple[int, str]:
    """Agrupa comandos por tarefa, em vez de despejar uma lista alfabética."""
    caminho = caminho.casefold().strip()
    if caminho in {"/nara", "/comandos", "/central_ajuda"}:
        return 0, "Comece por aqui"
    if caminho in {"/coliseu", "/nivel", "/ranking-xp"}:
        return 1, "Perfil e progressão"
    if caminho in {"/zerados", "/remover_zerado"}:
        return 2, "Jogos e conquistas"
    if caminho == "/loja":
        return 3, "Economia"
    if caminho.startswith("/sl_admin"):
        return 5, "Runs e desafios · moderação"
    if (
        caminho == "/adm" or caminho == "/colizeu" or caminho.startswith("/painel")
        or caminho.startswith("/postar_painel") or caminho.startswith("/cargo_painel")
    ):
        return 6, "Painéis e administração"
    if caminho in {
        "/status_ofertas", "/previa_oferta", "/teste_video", "/teste_live",
        "/status_youtube", "/gemini_status",
    }:
        return 7, "Integrações e diagnósticos"
    return 8, "Outros comandos"


def canais_visiveis(guild: Any, member: Any) -> list[str]:
    """Canais que o próprio usuário pode ver; canais ocultos nunca são listados."""
    saida = []
    for canal in getattr(guild, "channels", ()) or ():
        try:
            permissoes = canal.permissions_for(member)
            if not getattr(permissoes, "view_channel", False):
                continue
            categoria = getattr(getattr(canal, "category", None), "name", None)
            prefixo = f"{categoria} / " if categoria else ""
            saida.append(prefixo + str(getattr(canal, "name", "canal")))
        except Exception:
            continue
    return sorted(set(saida), key=str.casefold)


def formatar_sistemas(bot: Any) -> str:
    nomes = cogs_carregados(bot)
    if not nomes:
        return "Não consegui identificar os módulos ativos neste momento. Prefiro admitir a limitação a desfilar sistemas fantasmas como se fossem reais."
    return "**Relatório confirmado: estes são os módulos ativos agora:**\n" + "\n".join(f"• {nome}" for nome in nomes)
