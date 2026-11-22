"""Catálogo e regras puras do Cartas do Coliseu.

Todas as artes usam símbolos e geometria original; nenhum recurso visual de jogos
proprietários é incorporado ao catálogo.
"""
from __future__ import annotations

import hashlib
import re
import secrets
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from levels import PATENTES

VERSAO_ARTES = 1

TIPOS = ("Destreza", "Força", "Magia")
EMOJIS_TIPO = {"Destreza": "🌀", "Força": "⚔️", "Magia": "🔮"}
CICLO_TIPOS = {"Destreza": "Força", "Força": "Magia", "Magia": "Destreza"}

RARIDADES = ("Comum", "Rara", "Épica", "Lendária")
PESOS_RARIDADE = {"Comum": 70, "Rara": 22, "Épica": 7, "Lendária": 1}
CUSTO_RARIDADE = {"Comum": 1, "Rara": 2, "Épica": 3, "Lendária": 4}
FAIXA_PODER = {
    "Comum": (3, 5),
    "Rara": (4, 6),
    "Épica": (5, 7),
    "Lendária": (6, 8),
}
ALMAS_DUPLICATA = {"Comum": 5, "Rara": 15, "Épica": 40, "Lendária": 100}
CUSTO_FORJA = {"Comum": 40, "Rara": 120, "Épica": 320, "Lendária": 800}
PRECO_PACOTE_FOGUEIRA = 120
CARTAS_POR_PACOTE = 3
PITY_CARTAS = 10

HABILIDADES: dict[str, dict[str, str]] = {
    "primeira_luz": {"nome": "Primeira Luz", "texto": "+1 de poder na primeira rodada."},
    "retaliacao": {"nome": "Retaliação", "texto": "+1 de poder se perdeu a rodada anterior."},
    "impeto": {"nome": "Ímpeto", "texto": "+1 de poder se venceu a rodada anterior."},
    "ultimo_folego": {"nome": "Último Fôlego", "texto": "+1 de poder na quinta rodada."},
    "contragolpe": {"nome": "Contragolpe", "texto": "+1 de poder se estiver em desvantagem de tipo."},
}


@dataclass(frozen=True, slots=True)
class Carta:
    id: str
    nome: str
    categoria: str
    tipo: str
    poder: int
    raridade: str
    custo: int
    habilidade: str
    descricao: str = ""
    jogo_origem: str = ""

    def para_dict(self) -> dict[str, Any]:
        return asdict(self)


# Catálogo inicial. As cartas de jogos e patentes são geradas deterministicamente.
_CARTAS_BASE = [
    # Chefes
    Carta("chefe_guardiao_cinzas", "Guardião das Cinzas", "Chefe", "Força", 5, "Rara", 2, "retaliacao"),
    Carta("chefe_dama_vazio", "Dama do Vazio", "Chefe", "Magia", 6, "Épica", 3, "ultimo_folego"),
    Carta("chefe_cervo_sombrio", "Cervo Sombrio", "Chefe", "Destreza", 4, "Comum", 1, "contragolpe"),
    Carta("chefe_rei_afogado", "Rei Afogado", "Chefe", "Força", 7, "Épica", 3, "primeira_luz"),
    Carta("chefe_oraculo_ruina", "Oráculo da Ruína", "Chefe", "Magia", 7, "Lendária", 4, "impeto"),
    Carta("chefe_cacador_sem_rosto", "Caçador sem Rosto", "Chefe", "Destreza", 5, "Rara", 2, "retaliacao"),
    Carta("chefe_vigia_cinzento", "Vigia Cinzento", "Chefe", "Força", 4, "Comum", 1, "retaliacao"),
    Carta("chefe_aparicao_veio", "Aparição do Véu", "Chefe", "Destreza", 3, "Comum", 1, "contragolpe"),
    # Armas
    Carta("arma_lamina_peregrino", "Lâmina do Peregrino", "Arma", "Destreza", 4, "Comum", 1, "primeira_luz"),
    Carta("arma_martelo_fornalha", "Martelo da Fornalha", "Arma", "Força", 6, "Rara", 2, "ultimo_folego"),
    Carta("arma_cajado_marulho", "Cajado do Marulho", "Arma", "Magia", 5, "Rara", 2, "contragolpe"),
    Carta("arma_duas_luas", "Lâminas das Duas Luas", "Arma", "Destreza", 7, "Épica", 3, "impeto"),
    Carta("arma_grande_sino", "Grande Sino de Ferro", "Arma", "Força", 8, "Lendária", 4, "retaliacao"),
    Carta("arma_agulha_astro", "Agulha Astral", "Arma", "Magia", 3, "Comum", 1, "primeira_luz"),
    Carta("arma_lanca_fornalha", "Lança da Fornalha", "Arma", "Força", 4, "Comum", 1, "primeira_luz"),
    Carta("arma_arco_peregrino", "Arco do Peregrino", "Arma", "Destreza", 5, "Comum", 1, "impeto"),
    # Magias
    Carta("magia_brasa_errante", "Brasa Errante", "Magia", "Magia", 3, "Comum", 1, "primeira_luz"),
    Carta("magia_selo_vigilia", "Selo da Vigília", "Magia", "Destreza", 5, "Rara", 2, "contragolpe"),
    Carta("magia_trovao_oco", "Trovão Oco", "Magia", "Força", 6, "Épica", 3, "retaliacao"),
    Carta("magia_nevoa_antiga", "Névoa Antiga", "Magia", "Magia", 7, "Épica", 3, "impeto"),
    Carta("magia_sol_negro", "Sol Negro", "Magia", "Magia", 8, "Lendária", 4, "ultimo_folego"),
    Carta("magia_fagulha", "Fagulha", "Magia", "Destreza", 4, "Comum", 1, "contragolpe"),
    Carta("magia_orbe_eco", "Orbe do Eco", "Magia", "Magia", 4, "Comum", 1, "ultimo_folego"),
    Carta("magia_chama_fria", "Chama Fria", "Magia", "Magia", 3, "Comum", 1, "retaliacao"),
    # Covenants / juramentos
    Carta("covenant_lobos_cinza", "Lobos da Cinza", "Covenant", "Força", 5, "Rara", 2, "impeto"),
    Carta("covenant_lua_velada", "Lua Velada", "Covenant", "Destreza", 6, "Épica", 3, "primeira_luz"),
    Carta("covenant_sentinelas", "Sentinelas do Véu", "Covenant", "Magia", 4, "Comum", 1, "retaliacao"),
    Carta("covenant_coroa_abismo", "Coroa do Abismo", "Covenant", "Força", 7, "Lendária", 4, "contragolpe"),
    Carta("covenant_ultimos", "Os Últimos Juramentados", "Covenant", "Destreza", 5, "Rara", 2, "ultimo_folego"),
    Carta("covenant_filhos_brasa", "Filhos da Brasa", "Covenant", "Força", 5, "Comum", 1, "contragolpe"),
    Carta("covenant_peregrinos_nevoa", "Peregrinos da Névoa", "Covenant", "Destreza", 4, "Comum", 1, "primeira_luz"),
    Carta("covenant_irmandade_ferro", "Irmandade de Ferro", "Covenant", "Força", 4, "Comum", 1, "retaliacao"),
]

CARTAS_POR_ID: dict[str, Carta] = {c.id: c for c in _CARTAS_BASE}


def slug_jogo(nome: str) -> str:
    normalizado = unicodedata.normalize("NFKD", str(nome or ""))
    ascii_nome = "".join(ch for ch in normalizado if not unicodedata.combining(ch)).lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_nome).strip("_") or "jogo_sem_nome"
    # Sufixo estável evita colisões entre títulos que normalizam para o mesmo slug.
    suffix = hashlib.sha256(str(nome or "").casefold().encode("utf-8")).hexdigest()[:6]
    return f"{slug[:62]}_{suffix}"


def _hash_int(valor: str) -> int:
    return int.from_bytes(hashlib.sha256(valor.encode("utf-8")).digest()[:8], "big")


def carta_jogo(nome_jogo: str, marco: str) -> Carta:
    """Gera carta fixa por jogo/marco: zerado e platina nunca compartilham ID."""
    marco = "platina" if str(marco).lower() == "platina" else "zerado"
    slug = slug_jogo(nome_jogo)
    seed = f"{slug}:{marco}:soulsbot-card-v1"
    n = _hash_int(seed)
    tipo = TIPOS[n % len(TIPOS)]
    habilidade = tuple(HABILIDADES)[(n // 7) % len(HABILIDADES)]
    if marco == "zerado":
        raridade = "Rara"
        minimo, maximo = FAIXA_PODER[raridade]
        poder = minimo + ((n // 11) % (maximo - minimo + 1))
        sufixo = "Alma Desperta"
    else:
        raridade = "Épica"
        minimo, maximo = FAIXA_PODER[raridade]
        poder = minimo + ((n // 13) % (maximo - minimo + 1))
        sufixo = "Eco da Platina"
    titulo = str(nome_jogo or "Jogo")[:62]
    return Carta(
        id=f"jogo_{slug}_{marco}",
        nome=f"{titulo} — {sufixo}"[:95],
        categoria="Jogo",
        tipo=tipo,
        poder=int(poder),
        raridade=raridade,
        custo=CUSTO_RARIDADE[raridade],
        habilidade=habilidade,
        descricao=f"Carta exclusiva por {('zerar' if marco == 'zerado' else 'platinar')} {titulo}.",
        jogo_origem=titulo,
    )


def carta_patente(indice: int, nivel_minimo: int, nome_patente: str) -> Carta:
    seed = f"patente:{indice}:{nome_patente}:soulsbot-card-v1"
    n = _hash_int(seed)
    if nivel_minimo >= 75:
        raridade = "Lendária"
    elif nivel_minimo >= 30:
        raridade = "Épica"
    elif nivel_minimo >= 10:
        raridade = "Rara"
    else:
        raridade = "Comum"
    minimo, maximo = FAIXA_PODER[raridade]
    poder = minimo + (n % (maximo - minimo + 1))
    tipo = TIPOS[(n // 9) % len(TIPOS)]
    habilidade = tuple(HABILIDADES)[(n // 17) % len(HABILIDADES)]
    card_id = f"patente_{indice + 1}"
    return Carta(
        id=card_id,
        nome=f"Patente: {nome_patente}"[:95],
        categoria="Patente",
        tipo=tipo,
        poder=int(poder),
        raridade=raridade,
        custo=CUSTO_RARIDADE[raridade],
        habilidade=habilidade,
        descricao=f"Desbloqueada ao alcançar o nível {nivel_minimo}.",
    )


CARTAS_PATENTE = [carta_patente(i, nivel, nome) for i, (nivel, nome) in enumerate(PATENTES)]
CARTAS_POR_ID.update({c.id: c for c in CARTAS_PATENTE})

# Pacotes não entregam cartas de patente ou de jogos: essas são recompensas de marcos.
CARTAS_PACOTE = [c for c in _CARTAS_BASE]
CARTAS_PACOTE_POR_RARIDADE = {
    raridade: [c for c in CARTAS_PACOTE if c.raridade == raridade]
    for raridade in RARIDADES
}


def get_carta(card_id: str) -> Carta | None:
    if card_id in CARTAS_POR_ID:
        return CARTAS_POR_ID[card_id]
    if str(card_id).startswith("jogo_"):
        m = re.fullmatch(r"jogo_(.+)_(zerado|platina)", str(card_id))
        if m:
            slug, marco = m.groups()
            # O slug não é reversível em nome original; a função é usada após
            # carregar o snapshot persistido ou com o nome de jogo do registro.
            return None
    return None


def carta_de_jogo_por_id(card_id: str, nome_jogo: str) -> Carta:
    carta = carta_jogo(nome_jogo, "platina" if str(card_id).endswith("_platina") else "zerado")
    if carta.id != card_id:
        raise ValueError("ID de carta de jogo não corresponde ao título armazenado.")
    return carta


def catalogo_estatico_dicts() -> list[dict[str, Any]]:
    return [c.para_dict() for c in [*_CARTAS_BASE, *CARTAS_PATENTE]]


def sortear_carta(pity_atual: int) -> tuple[Carta, int, bool]:
    """Retorna (carta, novo_pity, pity_ativado) com probabilidades públicas por carta."""
    ativado = int(pity_atual) >= PITY_CARTAS
    if ativado:
        # Mantém a proporção relativa das chances Rara/Épica/Lendária.
        raridade = secrets.choice(
            ["Rara"] * 22 + ["Épica"] * 7 + ["Lendária"] * 1
        )
    else:
        rolagem = secrets.randbelow(100)
        if rolagem < 70:
            raridade = "Comum"
        elif rolagem < 92:
            raridade = "Rara"
        elif rolagem < 99:
            raridade = "Épica"
        else:
            raridade = "Lendária"
    candidatos = CARTAS_PACOTE_POR_RARIDADE[raridade]
    if not candidatos:
        # Não deveria acontecer com o catálogo declarado; evita falha ao abrir pack.
        raridade = "Rara" if ativado else "Comum"
        candidatos = CARTAS_PACOTE_POR_RARIDADE[raridade]
    carta = secrets.choice(candidatos)
    novo_pity = 0 if raridade != "Comum" else (0 if ativado else int(pity_atual) + 1)
    return carta, novo_pity, ativado


def carta_dict(card_id: str, nome_jogo: str | None = None) -> dict[str, Any] | None:
    carta = get_carta(card_id)
    if carta is None and card_id.startswith("jogo_") and nome_jogo:
        try:
            carta = carta_de_jogo_por_id(card_id, nome_jogo)
        except ValueError:
            return None
    return carta.para_dict() if carta else None


def vantagem_tipo(tipo_a: str, tipo_b: str) -> int:
    """Retorna +3 se A vence B, -3 se B vence A, ou 0."""
    if CICLO_TIPOS.get(tipo_a) == tipo_b:
        return 3
    if CICLO_TIPOS.get(tipo_b) == tipo_a:
        return -3
    return 0


def bonus_habilidade(carta: dict[str, Any], round_no: int, resultado_anterior: str | None,
                     tem_desvantagem: bool) -> int:
    habilidade = carta.get("habilidade")
    if habilidade == "primeira_luz" and round_no == 1:
        return 1
    if habilidade == "retaliacao" and resultado_anterior == "perdeu":
        return 1
    if habilidade == "impeto" and resultado_anterior == "venceu":
        return 1
    if habilidade == "ultimo_folego" and round_no == 5:
        return 1
    if habilidade == "contragolpe" and tem_desvantagem:
        return 1
    return 0


def resolver_rodada(carta_a: dict[str, Any], carta_b: dict[str, Any], round_no: int,
                     resultado_a_anterior: str | None, resultado_b_anterior: str | None) -> dict[str, Any]:
    vantagem_a = vantagem_tipo(carta_a["tipo"], carta_b["tipo"])
    tipo_a = max(0, vantagem_a)
    tipo_b = max(0, -vantagem_a)
    habilidade_a = bonus_habilidade(carta_a, round_no, resultado_a_anterior, vantagem_a < 0)
    habilidade_b = bonus_habilidade(carta_b, round_no, resultado_b_anterior, vantagem_a > 0)
    poder_a = int(carta_a["poder"]) + tipo_a + habilidade_a
    poder_b = int(carta_b["poder"]) + tipo_b + habilidade_b
    vencedor = "a" if poder_a > poder_b else "b" if poder_b > poder_a else "empate"
    return {
        "power_a": poder_a,
        "power_b": poder_b,
        "type_bonus_a": tipo_a,
        "type_bonus_b": tipo_b,
        "skill_bonus_a": habilidade_a,
        "skill_bonus_b": habilidade_b,
        "winner": vencedor,
    }


def narrar_rodada(round_no: int, carta_a: dict[str, Any], carta_b: dict[str, Any], resultado: dict[str, Any]) -> str:
    """Narração local determinística e curta; não chama IA nem serviços externos."""
    nomes = [
        "As lâminas se cruzam e a arena prende a respiração.",
        "A fogueira estala enquanto os poderes colidem.",
        "Um movimento calculado muda o ritmo do confronto.",
        "A arquibancada sente que a decisão se aproxima.",
        "Última rodada. Não há espaço para hesitação.",
    ]
    texto = nomes[min(max(round_no - 1, 0), 4)]
    if resultado["winner"] == "a":
        decisao = f"**{carta_a['nome']}** supera **{carta_b['nome']}**."
    elif resultado["winner"] == "b":
        decisao = f"**{carta_b['nome']}** supera **{carta_a['nome']}**."
    else:
        decisao = f"**{carta_a['nome']}** e **{carta_b['nome']}** empatam."
    return f"{texto}\n{decisao}"


def resolver_duelo(rounds: list[dict[str, Any]]) -> str:
    wins_a = sum(1 for r in rounds if r.get("winner") == "a")
    wins_b = sum(1 for r in rounds if r.get("winner") == "b")
    if wins_a > wins_b:
        return "a"
    if wins_b > wins_a:
        return "b"
    # Desempate pela soma do poder efetivo nas rodadas vencidas.
    total_a = sum(int(r["power_a"]) for r in rounds if r.get("winner") == "a")
    total_b = sum(int(r["power_b"]) for r in rounds if r.get("winner") == "b")
    if total_a > total_b:
        return "a"
    if total_b > total_a:
        return "b"
    return "empate"


def poder_total_deck(cards: list[dict[str, Any]]) -> int:
    """Soma o poder base das cinco cartas para pareamento de força aproximada."""
    return sum(int(c.get("poder", 0)) for c in cards)


def cards_em_deck_validos(cards: list[dict[str, Any]]) -> tuple[bool, str]:
    if len(cards) != 5:
        return False, "O deck precisa ter exatamente cinco cartas."
    ids = [c["id"] for c in cards]
    if len(set(ids)) != 5:
        return False, "Não é permitido repetir uma carta no mesmo deck."
    custo = sum(int(c["custo"]) for c in cards)
    if custo > 12:
        return False, f"Seu deck custa {custo} pontos; o limite é 12."
    lendarias = sum(1 for c in cards if c["raridade"] == "Lendária")
    if lendarias > 1:
        return False, "O deck pode conter no máximo uma carta Lendária."
    return True, "Deck válido."
