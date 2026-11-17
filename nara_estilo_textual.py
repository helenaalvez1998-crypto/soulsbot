"""Princípios e pequenos formatadores de estilo textual usados pelas respostas locais da Nara.

A camada textual é determinística: não altera dados, permissões ou regras de negócio. Ela
apenas dá enquadramento textual às consultas que, sem IA, poderiam soar genéricas.
Textos críticos (moderação, privacidade, falhas e confirmações) permanecem objetivos.
"""
from __future__ import annotations

from typing import Final

_ENQUADRAMENTOS: Final[dict[str, str]] = {
    "saldo": "Hm. O saldo não mente. Vamos aos números:",
    "perfil": "Seu retrato no servidor. Sem filtro e sem desculpa:",
    "platinas": "Olha só sua coleção de platinas:",
    "zerados": "Backlog diminuindo. Vamos ver o que vc concluiu:",
    "runs": "Suas runs aprovadas. Agora os tempos têm a palavra:",
    "inventario": "Seu arsenal cosmético. Abrindo:",
    "ranking": "A arena tá assim. Não reclame comigo; reclame com seu desempenho:",
    "ajuda": "Tá, vamos ao mapa. Sem caça ao tesouro:",
    "sistemas": "Estes são os módulos que o sistema confirma como ativos:",
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

