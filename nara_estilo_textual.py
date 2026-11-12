"""Princípios e pequenos formatadores de estilo textual usados pelas respostas locais da Nara.

A camada textual é determinística: não altera dados, permissões ou regras de negócio. Ela
apenas dá enquadramento textual às consultas que, sem IA, poderiam soar genéricas.
Textos críticos (moderação, privacidade, falhas e confirmações) permanecem objetivos.
"""
from __future__ import annotations

from typing import Final

_ENQUADRAMENTOS: Final[dict[str, str]] = {
    "saldo": "Hm. Vamos aos números — sem ilusões:",
    "perfil": "Seu retrato atual na comunidade. A realidade, sem filtros:",
    "platinas": "Sua coleção de platinas até agora. Vamos conferir:",
    "zerados": "Jogos concluídos. O backlog está perdendo terreno:",
    "runs": "Suas runs aprovadas. Que os tempos falem:",
    "inventario": "Abrindo seu inventário cosmético:",
    "ranking": "A arena está assim. Observe os nomes:",
    "ajuda": "Certo. Aqui está o mapa, sem caça ao tesouro:",
    "sistemas": "Módulos que o sistema confirma como ativos agora:",
}


def enquadrar(texto: str, contexto: str) -> str:
    """Acrescenta uma abertura curta e contextual, preservando o conteúdo original."""
    corpo = (texto or "").strip()
    abertura = _ENQUADRAMENTOS.get(str(contexto or "").casefold())
    if not corpo or not abertura:
        return corpo
    # Evita duplicar o enquadramento caso uma camada chame esta função duas vezes.
    if corpo.startswith(abertura):
        return corpo
    return f"{abertura}\n{corpo}"

