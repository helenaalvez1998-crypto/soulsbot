"""Loja de Denários: catálogo pequeno e só cosmético (nada afeta XP, ranking ou recompensas).

Referência de preço: uma platina rende 50 Denários e um zerado 10, então 100 Denários = 2 platinas.
Sem dependência do discord.py.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    id: str
    tipo: str          # "cor" ou "titulo"
    nome: str
    preco: int
    emoji: str
    valor: int | None = None   # cor 0xRRGGBB (só para tipo "cor")
    nivel_min: int = 1
    descricao: str = ""


ITENS = [
    Item("cor_brasa", "cor", "Brasa", 100, "🔥", 0xE25822, descricao="Cor de brasa para o seu perfil."),
    Item("cor_nevoa", "cor", "Névoa", 100, "🌫️", 0x9FB4C7, descricao="Um azul pálido de neblina."),
    Item("cor_hera", "cor", "Hera", 100, "🌿", 0x4C9F70, descricao="Verde de musgo e ruína."),
    Item("cor_crepusculo", "cor", "Crepúsculo", 100, "🌆", 0xC2185B, descricao="Rosa-escuro do fim de tarde."),
    Item("tit_cacador", "titulo", "Caçador de Chefes", 150, "🗡️", descricao="Aparece abaixo do seu nome."),
    Item("tit_rolagens", "titulo", "Mestre das Rolagens", 150, "🌀", descricao="Aparece abaixo do seu nome."),
    Item("tit_persistente", "titulo", "Persistente", 150, "🪨", descricao="Aparece abaixo do seu nome."),
    Item("tit_renascido", "titulo", "Eterno Renascido", 300, "♾️", nivel_min=20,
         descricao="Exige nível 20. Aparece abaixo do seu nome."),
]
POR_ID = {i.id: i for i in ITENS}
ROTULO_TIPO = {"cor": "Cor de perfil", "titulo": "Título"}


def linha_item(item: Item, possui: bool, equipado: bool, nivel: int) -> str:
    if equipado:
        estado = "✅ equipado"
    elif possui:
        estado = "🎒 seu"
    elif nivel < item.nivel_min:
        estado = f"🔒 nível {item.nivel_min}"
    else:
        estado = f"🪙 {item.preco}"
    return f"{item.emoji} **{item.nome}** — {estado}"
