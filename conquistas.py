"""Conquistas (badges) do perfil.

Todas são DERIVADAS de dados que o bot já tem (platinas, zerados, runs, XP, tempo no servidor).
Nada é inventado nem guardado à parte: se o dado muda, a conquista muda junto.
Sem dependência do discord.py.
"""
from dataclasses import dataclass

# raridade -> (rótulo, emoji)
RARIDADES = {
    "comum": ("Comum", "⚪"),
    "rara": ("Rara", "🔵"),
    "epica": ("Épica", "🟣"),
    "lendaria": ("Lendária", "🟡"),
}


@dataclass(frozen=True)
class Conquista:
    chave: str
    nome: str
    descricao: str
    raridade: str
    emoji: str


@dataclass
class Stats:
    """Números que alimentam as conquistas (montados pelo cog de perfil)."""
    nivel: int = 1
    xp: int = 0
    platinas: int = 0
    zerados: int = 0
    runs: int = 0
    recordes: int = 0
    pos_xp: int | None = None
    pos_platinas: int | None = None
    dias_no_servidor: int | None = None


def _escada(chave, emoji, nome_fmt, desc_fmt, marcos):
    """Gera uma 'escada' de conquistas (1ª, 5, 10...) onde só o MAIOR marco atingido é mostrado."""
    return [(chave, emoji, nome_fmt.format(n=n), desc_fmt.format(n=n), n, raridade) for n, raridade in marcos]


PLATINAS = _escada("platina", "🏆", "{n} platinas", "Teve {n} platinas aprovadas pela moderação.",
                   [(1, "comum"), (5, "comum"), (10, "rara"), (25, "epica"), (50, "lendaria")])
ZERADOS = _escada("zerado", "✅", "{n} zerados", "Registrou {n} jogos finalizados.",
                  [(1, "comum"), (10, "comum"), (25, "rara"), (50, "epica"), (100, "lendaria")])
RUNS = _escada("run", "⚔️", "{n} runs", "Teve {n} runs Soulslike aprovadas.",
               [(1, "comum"), (5, "rara"), (20, "epica")])

NOME_PRIMEIRA_PLATINA = "Primeira platina"
NOME_PRIMEIRO_ZERADO = "Primeiro zerado"
NOME_PRIMEIRA_RUN = "Primeira run"


def _maior_marco(escada, valor):
    atingidos = [m for m in escada if valor >= m[4]]
    return atingidos[-1] if atingidos else None


def calcular(stats: Stats) -> list[Conquista]:
    """Lista de conquistas do jogador, das mais raras para as mais comuns."""
    lista: list[Conquista] = []

    for escada, valor in ((PLATINAS, stats.platinas), (ZERADOS, stats.zerados), (RUNS, stats.runs)):
        marco = _maior_marco(escada, valor)
        if marco:
            chave, emoji, nome, desc, n, raridade = marco
            if n == 1:
                nome = {"platina": NOME_PRIMEIRA_PLATINA, "zerado": NOME_PRIMEIRO_ZERADO, "run": NOME_PRIMEIRA_RUN}[chave]
                desc = {"platina": "Teve a primeira platina aprovada.",
                        "zerado": "Registrou o primeiro jogo finalizado.",
                        "run": "Teve a primeira run Soulslike aprovada."}[chave]
            lista.append(Conquista(f"{chave}_{n}", nome, desc, raridade, emoji))

    if stats.recordes >= 1:
        lista.append(Conquista(
            "recordista", "Recordista",
            f"Detém o melhor tempo em {stats.recordes} categoria{'s' if stats.recordes != 1 else ''} do Hall da Fama.",
            "lendaria" if stats.recordes >= 3 else "epica", "👑"))

    if stats.pos_xp is not None and stats.xp > 0 and stats.pos_xp <= 3:
        lista.append(Conquista("podio_xp", "Pódio de XP", f"Está em #{stats.pos_xp} no ranking de XP.", "epica", "🥇"))
    if stats.pos_platinas is not None and stats.platinas > 0 and stats.pos_platinas <= 3:
        lista.append(Conquista("podio_platinas", "Pódio de platinas",
                               f"Está em #{stats.pos_platinas} no ranking de platinas.", "epica", "🏛️"))

    if stats.nivel >= 50:
        lista.append(Conquista("veterano_nivel", "Veterano das cinzas", "Alcançou o nível 50.", "lendaria", "🌑"))
    elif stats.nivel >= 20:
        lista.append(Conquista("experiente", "Experiente", "Alcançou o nível 20.", "rara", "🛡️"))

    if stats.dias_no_servidor is not None and stats.dias_no_servidor >= 365:
        lista.append(Conquista("um_ano", "Um ano de arena", "Está no servidor há mais de um ano.", "rara", "📅"))

    ordem = {"lendaria": 0, "epica": 1, "rara": 2, "comum": 3}
    return sorted(lista, key=lambda c: (ordem[c.raridade], c.nome))


def linha_resumo(conquistas: list[Conquista], limite: int = 6) -> str:
    """Emojis das conquistas mais raras, para caber em um campo do embed."""
    if not conquistas:
        return "*Nenhuma conquista ainda.*"
    ver = conquistas[:limite]
    texto = " ".join(c.emoji for c in ver)
    resto = len(conquistas) - len(ver)
    return texto + (f" **+{resto}**" if resto > 0 else "")


def texto_detalhado(conquistas: list[Conquista]) -> str:
    if not conquistas:
        return "Ainda não há conquistas. Registre platinas, zerados ou runs para desbloquear as primeiras."
    linhas = []
    for c in conquistas:
        rotulo, bolinha = RARIDADES[c.raridade]
        linhas.append(f"{c.emoji} **{c.nome}** · {bolinha} {rotulo}\n　{c.descricao}")
    return "\n".join(linhas)
