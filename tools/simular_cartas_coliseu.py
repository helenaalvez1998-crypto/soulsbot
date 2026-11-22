"""Simula confrontos aleatórios para detectar cartas fora da faixa de equilíbrio.

Uso: python tools/simular_cartas_coliseu.py [quantidade_de_duelos]
O simulador não acessa Discord, IA, rede ou banco de produção.
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sistemas.cartas import (  # noqa: E402
    CARTAS_PATENTE,
    CARTAS_PACOTE,
    carta_jogo,
    cards_em_deck_validos,
    poder_total_deck,
    resolver_duelo,
    resolver_rodada,
)

SEED = 20261122
FAIXA_ALVO = (0.45, 0.55)


def montar_pool():
    pool = {c.id: c.para_dict() for c in [*CARTAS_PACOTE, *CARTAS_PATENTE]}
    for i in range(100):
        nome = f"Jogo de Simulação {i + 1}"
        for marco in ("zerado", "platina"):
            carta = carta_jogo(nome, marco)
            pool[carta.id] = carta.para_dict()
    return list(pool.values())


def sortear_deck(rng: random.Random, pool: list[dict]) -> list[dict]:
    for _ in range(2000):
        deck = rng.sample(pool, 5)
        if cards_em_deck_validos(deck)[0]:
            return deck
    raise RuntimeError("Não foi possível montar um deck válido com o catálogo atual.")


def sortear_par_compativel(rng: random.Random, pool: list[dict], diferenca_maxima: int = 4):
    """Sorteia dois decks dentro do limite de pareamento usado em produção."""
    deck_a = sortear_deck(rng, pool)
    poder_a = poder_total_deck(deck_a)
    for tentativas in range(1, 10_001):
        deck_b = sortear_deck(rng, pool)
        if abs(poder_a - poder_total_deck(deck_b)) <= diferenca_maxima:
            return deck_a, deck_b, tentativas
    raise RuntimeError("Não foi possível encontrar decks compatíveis após 10.000 tentativas.")


def simular(duelos: int = 100_000) -> dict:
    rng = random.Random(SEED)
    pool = montar_pool()
    aparicoes = defaultdict(int)
    pontos = defaultdict(float)
    vitorias_duelo = 0
    empates_duelo = 0
    tentativas_pareamento = 0
    cartas_por_id = {c["id"]: c for c in pool}

    for _ in range(int(duelos)):
        deck_a, deck_b, tentativas = sortear_par_compativel(rng, pool)
        tentativas_pareamento += tentativas
        rng.shuffle(deck_a)
        rng.shuffle(deck_b)
        rounds = []
        anterior_a = anterior_b = None
        for n in range(5):
            a, b = deck_a[n], deck_b[n]
            resultado = resolver_rodada(a, b, n + 1, anterior_a, anterior_b)
            rounds.append(resultado)
            aparicoes[a["id"]] += 1
            aparicoes[b["id"]] += 1
            if resultado["winner"] == "a":
                pontos[a["id"]] += 1.0
                anterior_a, anterior_b = "venceu", "perdeu"
            elif resultado["winner"] == "b":
                pontos[b["id"]] += 1.0
                anterior_a, anterior_b = "perdeu", "venceu"
            else:
                pontos[a["id"]] += 0.5
                pontos[b["id"]] += 0.5
                anterior_a = anterior_b = None
        vencedor = resolver_duelo(rounds)
        if vencedor == "a":
            vitorias_duelo += 1
        elif vencedor == "empate":
            empates_duelo += 1

    # Segunda medição: cada carta enfrenta somente cartas da mesma raridade.
    # Isso separa desequilíbrios internos de uma raridade da força bruta esperada
    # entre Comum/Rara/Épica/Lendária.
    comparacoes_por_carta = 1_000
    espelho_aparicoes = defaultdict(int)
    espelho_pontos = defaultdict(float)
    por_raridade_cartas = defaultdict(list)
    for carta in pool:
        por_raridade_cartas[carta["raridade"]].append(carta)
    estados_anteriores = (None, "venceu", "perdeu")
    for carta in pool:
        adversarios = [c for c in por_raridade_cartas[carta["raridade"]] if c["id"] != carta["id"]]
        if not adversarios:
            continue
        for _ in range(comparacoes_por_carta):
            adversaria = rng.choice(adversarios)
            resultado = resolver_rodada(
                carta, adversaria, rng.randint(1, 5),
                rng.choice(estados_anteriores), rng.choice(estados_anteriores),
            )
            espelho_aparicoes[carta["id"]] += 1
            if resultado["winner"] == "a":
                espelho_pontos[carta["id"]] += 1.0
            elif resultado["winner"] == "empate":
                espelho_pontos[carta["id"]] += 0.5

    metricas = []
    fora = []
    for carta in pool:
        card_id = carta["id"]
        total = aparicoes[card_id]
        taxa_contexto = pontos[card_id] / total if total else 0.0
        total_espelho = espelho_aparicoes[card_id]
        taxa_espelho = espelho_pontos[card_id] / total_espelho if total_espelho else 0.0
        item = {
            "id": card_id,
            "nome": carta["nome"],
            "raridade": carta["raridade"],
            "aparicoes_em_decks": total,
            "taxa_vitoria_em_decks_aleatorios": round(taxa_contexto, 4),
            "comparacoes_mesma_raridade": total_espelho,
            "taxa_vitoria_mesma_raridade": round(taxa_espelho, 4),
        }
        metricas.append(item)
        if total_espelho >= 500 and not (FAIXA_ALVO[0] <= taxa_espelho <= FAIXA_ALVO[1]):
            fora.append(item)

    metricas.sort(key=lambda x: x["taxa_vitoria_mesma_raridade"], reverse=True)
    por_raridade = {}
    por_raridade_contexto = {}
    for raridade in {c["raridade"] for c in pool}:
        grupo = [m["taxa_vitoria_mesma_raridade"] for m in metricas if m["raridade"] == raridade]
        contexto = [m["taxa_vitoria_em_decks_aleatorios"] for m in metricas if m["raridade"] == raridade]
        if grupo:
            ordenado = sorted(grupo)
            por_raridade[raridade] = {
                "cartas": len(grupo),
                "media": round(sum(grupo) / len(grupo), 4),
                "mediana": round(ordenado[len(ordenado) // 2], 4),
                "minimo": round(ordenado[0], 4),
                "maximo": round(ordenado[-1], 4),
            }
            por_raridade_contexto[raridade] = round(sum(contexto) / len(contexto), 4)
    taxa_a = vitorias_duelo / max(1, int(duelos))
    taxa_empate = empates_duelo / max(1, int(duelos))
    taxa_b = max(0.0, 1.0 - taxa_a - taxa_empate)
    return {
        "duelos": int(duelos),
        "seed": SEED,
        "pool_cartas": len(pool),
        "diferenca_maxima_poder_deck": 4,
        "media_tentativas_pareamento": round(tentativas_pareamento / max(1, int(duelos)), 2),
        "taxa_vitoria_lado_a": round(taxa_a, 4),
        "taxa_vitoria_lado_b": round(taxa_b, 4),
        "taxa_empate": round(taxa_empate, 4),
        "comparacoes_mesma_raridade_por_carta": comparacoes_por_carta,
        "resumo_por_raridade_mesma_raridade": por_raridade,
        "media_vitoria_por_raridade_em_decks_aleatorios": por_raridade_contexto,
        "cartas_fora_45_55_em_comparacao_mesma_raridade": len(fora),
        "fora_da_faixa": fora,
        "top_5": metricas[:5],
        "bottom_5": metricas[-5:],
        "nota_balanceamento": (
            "Os pares respeitam a diferença máxima de 4 pontos no poder base total dos decks. "
            "O pool de cartas é amostrado uniformemente e não reproduz a distribuição de cartas dos jogadores. "
            "O campo taxa_vitoria_mesma_raridade compara cada carta contra o mesmo nível de raridade e é mais adequado "
            "para rastrear cartas fora da faixa 45–55%. A taxa em decks aleatórios mistura raridades e mostra também "
            "a vantagem bruta esperada de raridades superiores. Não aplique nerf automático sem revisar os confrontos."
        ),
    }


if __name__ == "__main__":
    quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    resultado = simular(quantidade)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
