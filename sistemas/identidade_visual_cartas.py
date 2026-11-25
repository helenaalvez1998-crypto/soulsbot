"""Sistema central de identidade visual das cartas do Narabot.

Camada de configuração, sem imagens e sem dependências pesadas. Define a identidade
independente da facção e o acabamento independente da raridade. O renderizador consome
esta ficha; assets rasterizados poderão substituir os elementos vetoriais sem alterar
as regras, o catálogo ou os pontos de integração.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

VERSAO_IDENTIDADE_VISUAL = 1

FACCOES: dict[str, dict[str, Any]] = {
    "Ordem Áurea": {
        "id": "ordem_aurea",
        "paleta": ((39, 31, 17), (91, 69, 31), (224, 183, 82), (245, 230, 180)),
        "metal": (242, 218, 153),
        "brasao": "erdtree",
        "estandarte": "estandarte_erdtree",
        "cenario": "leyndell_dourada",
        "ornamento": "raizes_douradas",
    },
    "Véu Carmesim": {
        "id": "veu_carmesim",
        "paleta": ((43, 13, 18), (83, 23, 31), (177, 49, 62), (238, 178, 177)),
        "metal": (205, 139, 125),
        "brasao": "tridente_carmesim",
        "estandarte": "estandarte_sangue",
        "cenario": "palacio_mohgwyn",
        "ornamento": "espinhos_sangue",
    },
    "Lua Negra": {
        "id": "lua_negra",
        "paleta": ((18, 15, 39), (39, 29, 76), (139, 112, 214), (224, 215, 255)),
        "metal": (191, 202, 224),
        "brasao": "lua_estelar",
        "estandarte": "estandarte_lunar",
        "cenario": "carian_noturna",
        "ornamento": "filigrana_lunar",
    },
}

# Perfis semânticos de raridade. Cada raridade tem uma linguagem material e um
# emblema próprios; não é apenas uma troca de cor no mesmo selo.
RARIDADES: dict[str, dict[str, Any]] = {
    "Comum": {"id": "comum", "gema": "losango_prata", "material": "ferro_prateado", "forma": "escudo_simples", "ornamento": 1, "brilho": 0},
    "Rara": {"id": "rara", "gema": "safira", "material": "prata_azulada", "forma": "cristal_angular", "ornamento": 2, "brilho": 1},
    "Épica": {"id": "epica", "gema": "ametista", "material": "prata_violeta", "forma": "cristal_coronado", "ornamento": 3, "brilho": 2},
    "Lendária": {"id": "lendaria", "gema": "rubi_dourado", "material": "ouro_real", "forma": "coroa_heraldica", "ornamento": 4, "brilho": 3},
    "Mítica": {"id": "mitica", "gema": "estrela_arcana", "material": "metal_celestial", "forma": "estrela_radiante", "ornamento": 5, "brilho": 4},
    "Primordial": {"id": "primordial", "gema": "runa_ancestral", "material": "ouro_ancestral", "forma": "selo_ancestral", "ornamento": 6, "brilho": 5},
    "Singular": {"id": "singular", "gema": "nucleo_unico", "material": "metal_transcendente", "forma": "brasao_exclusivo", "ornamento": 7, "brilho": 6},
}

CORES_RARIDADE = {
    "Comum": ((23, 29, 37), (166, 181, 194)),
    "Rara": ((9, 29, 48), (77, 180, 226)),
    "Épica": ((28, 15, 50), (183, 126, 239)),
    "Lendária": ((39, 25, 10), (239, 185, 75)),
    "Mítica": ((38, 10, 18), (205, 61, 75)),
    "Primordial": ((34, 32, 25), (239, 224, 174)),
    "Singular": ((9, 12, 24), (151, 143, 206)),
}

ALIASES_FACCAO = {
    "ordem aurea": "Ordem Áurea", "golden order": "Ordem Áurea",
    "veu carmesim": "Véu Carmesim", "dinastia mohgwyn": "Véu Carmesim",
    "mohgwyn": "Véu Carmesim", "blood dynasty": "Véu Carmesim",
    "lua negra": "Lua Negra", "lua sombria": "Lua Negra",
    "casa cariana": "Lua Negra", "cariana": "Lua Negra", "carian": "Lua Negra",
}


def normalizar_faccao(valor: Any) -> str:
    import unicodedata
    bruto = str(valor or "").strip()
    chave = unicodedata.normalize("NFKD", bruto).encode("ascii", "ignore").decode("ascii").casefold()
    return ALIASES_FACCAO.get(chave, bruto if bruto in FACCOES else "Ordem Áurea")


def resolver_identidade_visual(faccao: Any, raridade: Any) -> dict[str, Any]:
    """Ficha imutável por chamada para o renderizador; não altera dados do jogo."""
    fac = normalizar_faccao(faccao)
    rar = str(raridade or "Comum")
    if rar not in RARIDADES:
        rar = "Comum"
    return {
        "faccao": fac,
        "tema_faccao": deepcopy(FACCOES[fac]),
        "raridade": rar,
        "tema_raridade": deepcopy(RARIDADES[rar]),
        "cores_raridade": deepcopy(CORES_RARIDADE[rar]),
        "versao": VERSAO_IDENTIDADE_VISUAL,
    }


def listar_combinacoes() -> list[dict[str, str]]:
    return [
        {"faccao": fac, "raridade": rar}
        for fac in FACCOES
        for rar in RARIDADES
    ]
