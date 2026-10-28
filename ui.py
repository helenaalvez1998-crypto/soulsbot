"""Identidade visual do Colizeu: cores, símbolos e pequenos auxiliares compartilhados.

A ideia é que todo sistema (perfil, Coliseu, Galeria, runs) fale a mesma língua visual:
preto/dourado/prata, a patente definindo a cor do jogador e rodapés no mesmo formato.
Sem dependência do discord.py: dá para testar sem o Discord.
"""
import datetime as dt

import config
from levels import PATENTES, SIMBOLOS_PATENTES, nivel_por_xp, patente_por_nivel

# Cor de destaque por patente: quanto mais alta a patente, mais "nobre" o tom.
# Isso diferencia novatos, ativos e veteranos sem precisar de texto extra.
COR_PATENTE = {
    "Cinzas Novatas": 0x7A736B,
    "Guerreiro Caído": 0x8C6D4F,
    "Caçador de Almas": 0x5F7F8C,
    "Cavaleiro do Abismo": 0x3F6FA8,
    "Guardião das Cinzas": 0x5E5A8C,
    "Arauto da Ruína": 0x8B2E3C,
    "Executor Sombrio": 0x6D1F2B,
    "Senhor das Almas": 0xB8862B,
    "Lenda do Coliseu": 0xD4AF37,
    "Sentinela Imortal": 0xF1D77A,
}

LINHA = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
MARCA = "⚔️ Colizeu"


def cor_da_patente(nivel: int) -> int:
    return COR_PATENTE.get(patente_por_nivel(nivel), config.COR_OURO)


def patente_com_simbolo(nivel: int) -> str:
    nome = patente_por_nivel(nivel)
    return f"{SIMBOLOS_PATENTES.get(nome, '🔥')} {nome}"


def rodape(secao: str | None = None) -> str:
    """Rodapé padrão: 'Colizeu · Seção'."""
    return f"{MARCA} · {secao}" if secao else MARCA


def barra(fracao: float, tamanho: int = 12) -> str:
    fracao = max(0.0, min(1.0, fracao))
    cheio = int(round(fracao * tamanho))
    return "▰" * cheio + "▱" * (tamanho - cheio)


def progresso_nivel(xp: int) -> tuple[int, int, int, float]:
    """(nível, xp no nível, xp necessário no nível, fração 0-1)."""
    from levels import xp_para_nivel
    nivel = nivel_por_xp(xp)
    base, topo = xp_para_nivel(nivel), xp_para_nivel(nivel + 1)
    return nivel, xp - base, topo - base, (xp - base) / (topo - base)


def proxima_patente(nivel: int):
    """(nível mínimo, nome) da próxima patente, ou None se já está na última."""
    for minimo, nome in PATENTES:
        if minimo > nivel:
            return minimo, nome
    return None


def fmt_data(valor) -> str:
    try:
        return dt.date.fromisoformat(str(valor)).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(valor)


def fmt_tempo(seg: int) -> str:
    h, resto = divmod(int(seg), 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}"
