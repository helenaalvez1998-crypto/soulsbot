"""Princípios e pequenos formatadores de voz usados pelas respostas locais da Nara.

A camada é determinística: não altera dados, permissões ou regras de negócio. Ela
apenas dá enquadramento textual às consultas que, sem IA, poderiam soar genéricas.
Textos críticos (moderação, privacidade, falhas e confirmações) permanecem objetivos.
"""
from __future__ import annotations

from typing import Final

_ENQUADRAMENTOS: Final[dict[str, str]] = {
    "saldo": "Hm. Vamos aos números:",
    "perfil": "Seu retrato atual na comunidade:",
    "platinas": "Sua coleção de platinas até agora:",
    "zerados": "Seus jogos concluídos:",
    "runs": "Suas runs aprovadas:",
    "inventario": "Vamos abrir esse inventário cosmético:",
    "ranking": "A arena está assim:",
    "ajuda": "Certo. Aqui está o caminho, sem labirinto desnecessário:",
    "sistemas": "Estes são os módulos que estão realmente ativos agora:",
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

