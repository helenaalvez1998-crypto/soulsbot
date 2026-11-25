"""Rituais Ancestrais do Cartas do Coliseu.

Rituais de acesso especial consomem exemplares e Fragmentos. Não alteram o
balanceamento nem as regras de Primordiais ou Singulares.
"""
from __future__ import annotations

RITUAIS_ANCESTRAIS = {
    "coroa_do_haligtree": {
        "id": "coroa_do_haligtree",
        "nome": "Rito da Coroa do Haligtree",
        "lore": "A morte destinada, a chama da impalação e a sabedoria bestial são reunidas para despertar o Cavaleiro Consagrado.",
        "ingredientes": [
            {"card_id": "chefe_maliketh_morte_destinada", "rarity": "Lendária"},
            {"card_id": "chefe_messmer_impalador", "rarity": "Lendária"},
            {"card_id": "chefe_oraculo_ruina", "rarity": "Lendária"},
        ],
        "resultado": {"card_id": "gwent_mitica_coroa", "rarity": "Mítica"},
        "fragmentos": 250,
    },
}
