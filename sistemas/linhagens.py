"""Receitas determinísticas de Linhagem do Cartas do Coliseu.

Cada receita consome três exemplares específicos e Fragmentos. Os resultados são
unidades já existentes no catálogo; esta etapa não cria habilidades nem Primordiais.
"""
from __future__ import annotations

RECEITAS_LINHAGEM = {
    "trindade_lunar": {
        "id": "trindade_lunar",
        "nome": "Tríade do Eclipse",
        "lore": "Três juramentos carianos convergem em uma lâmina tocada pela noite.",
        "ingredientes": [
            {"card_id": "covenant_lua_velada", "rarity": "Épica"},
            {"card_id": "arma_duas_luas", "rarity": "Épica"},
            {"card_id": "magia_nevoa_antiga", "rarity": "Épica"},
        ],
        "resultado": {"card_id": "magia_sol_negro", "rarity": "Lendária"},
        "fragmentos": 80,
    },
    "forja_dourada": {
        "id": "forja_dourada",
        "nome": "Juramento da Árvore Áurea",
        "lore": "A disciplina do Crisol, o fogo da forja e a guarda de Leyndell moldam um grande sino de guerra.",
        "ingredientes": [
            {"card_id": "gwent_unidade_baluarte", "rarity": "Rara"},
            {"card_id": "arma_martelo_fornalha", "rarity": "Rara"},
            {"card_id": "covenant_irmandade_ferro", "rarity": "Comum"},
        ],
        "resultado": {"card_id": "arma_grande_sino", "rarity": "Lendária"},
        "fragmentos": 80,
    },
    "rito_da_morte": {
        "id": "rito_da_morte",
        "nome": "Rito da Lâmina Negra",
        "lore": "A sombra dos assassinos e os servos da morte apontam para o arauto da Runa da Morte.",
        "ingredientes": [
            {"card_id": "chefe_aparicao_veio", "rarity": "Comum"},
            {"card_id": "chefe_cacador_sem_rosto", "rarity": "Rara"},
            {"card_id": "gwent_unidade_necromante", "rarity": "Rara"},
        ],
        "resultado": {"card_id": "chefe_oraculo_ruina", "rarity": "Lendária"},
        "fragmentos": 80,
    },
}
