"""Gerador procedural V30: produz definições, sem persistir nem consumir recursos.

A função é pura em relação ao banco. O chamador fornece seed/id gerados no servidor,
valida a definição e só em versões posteriores poderá persistir/publicar a carta.
"""
from __future__ import annotations

import hashlib
import random
import re
import unicodedata
from collections import Counter
from typing import Any, Iterable

from sistemas.afinidades import (
    FACCOES, RARIDADES_GERADOR, analisar_compatibilidade,
    classificar_carta, validar_ingredientes,
)
from sistemas.cartas import FAIXA_PODER, HABILIDADES, HABILIDADES_COMUNS

TIPO_POR_FACCAO = {
    "Ordem Áurea": "Força",
    "Véu Carmesim": "Destreza",
    "Lua Negra": "Magia",
}
FILEIRA_POR_FUNCAO = {
    "ataque": "melee", "defesa": "melee",
    "controle": "siege", "suporte": "ranged",
}
PREFIXO_AFINIDADE = {
    "sagrado": "Áureo", "fogo": "Ígneo", "sangue": "Carmesim",
    "morte": "Funesto", "lua": "Lunar", "magia": "Arcano",
    "relampago": "Tempestuoso", "gravidade": "Estelar",
    "gelo": "Glacial", "veneno": "Pútrido",
    "ancestral": "Ancestral", "bestial": "Feral",
}
SUFIXO_FUNCAO = {
    "ataque": "Executor", "defesa": "Sentinela",
    "controle": "Arauto", "suporte": "Oráculo",
}
DESCRICOES = {
    "ataque": "Uma presença ofensiva moldada pela convergência dos ingredientes sacrificados.",
    "defesa": "Um guardião cuja forma nasceu da resistência compartilhada pelos ingredientes.",
    "controle": "Uma entidade que dobra o ritmo do campo por meio de forças convergentes.",
    "suporte": "Uma presença de apoio que manifesta a afinidade dominante da transmutação.",
}


# Compatibilidade inicial revisada por função tática. Apenas habilidades comuns já
# presentes no motor podem entrar no gerador; efeitos de controle de tabuleiro mais
# amplos permanecem fora até revisão específica de balanceamento.
HABILIDADES_POR_FUNCAO = {
    "ataque": {
        "retaliacao", "impeto", "contragolpe", "encadeamento", "adaptacao",
        "instinto", "precisao", "cacador_arcano", "quebra_ritmo",
    },
    "defesa": {
        "primeira_luz", "ultimo_folego", "sangue_frio", "instinto",
    },
    "controle": {
        "drenagem", "precisao", "quebra_ritmo", "cacador_arcano",
    },
    "suporte": {
        "primeira_luz", "ultimo_folego", "sangue_frio", "adaptacao",
    },
}
PESO_HABILIDADE = {
    "primeira_luz": 1, "retaliacao": 1, "impeto": 1, "ultimo_folego": 1,
    "encadeamento": 1, "adaptacao": 1, "sangue_frio": 1, "precisao": 1,
    "cacador_arcano": 1, "quebra_ritmo": 1, "contragolpe": 2,
    "instinto": 2, "drenagem": 2,
}

# V45 — camadas de identidade procedural. Mantém as mesmas facções, raridades,
# faixas de poder e habilidades aprovadas; a variedade é narrativa/tática, não
# uma licença para introduzir efeitos ainda não implementados.
ARQUETIPOS_POR_FUNCAO = {
    "ataque": ("Carrasco", "Duelista", "Caçador", "Lâmina Errante", "Executor"),
    "defesa": ("Bastião", "Guardião", "Sentinela", "Portador do Escudo", "Vigia"),
    "controle": ("Arauto", "Condutor", "Oráculo", "Teurgo", "Tecelão"),
    "suporte": ("Prelado", "Invocador", "Custódio", "Vidente", "Portador da Chama"),
}
EPITETOS_POR_AFINIDADE = {
    "sagrado": ("da Graça Velada", "do Juramento Áureo", "da Última Bênção"),
    "fogo": ("da Brasa Eterna", "da Chama Impura", "do Forno Rubro"),
    "sangue": ("do Pacto Carmesim", "da Linhagem Escarlate", "do Véu Sangrento"),
    "morte": ("do Fim Destinado", "da Cinza Sepulcral", "do Véu Fúnebre"),
    "lua": ("do Eclipse Cariano", "da Lua Silente", "do Firmamento Velado"),
    "magia": ("da Runa Partida", "do Verbo Arcano", "do Selo Antigo"),
    "relampago": ("da Tempestade Antiga", "do Raio Dracônico", "do Céu Partido"),
    "gravidade": ("do Abismo Estelar", "do Peso das Estrelas", "do Céu Caído"),
    "gelo": ("da Geada Profunda", "do Inverno Imóvel", "da Nevasca Pálida"),
    "veneno": ("do Pântano Corrompido", "da Seiva Pútrida", "do Último Esporo"),
    "ancestral": ("das Raízes Primevas", "do Espírito Antigo", "da Memória Verde"),
    "bestial": ("da Garra Primeva", "do Instinto Feral", "da Presa Dourada"),
}
LORE_POR_FUNCAO = {
    "ataque": "Forjado para romper a linha inimiga, carrega a memória agressiva dos ingredientes que o originaram.",
    "defesa": "Sua forma nasceu da resistência dos ingredientes; permanece onde outros recuam.",
    "controle": "Interpreta os sinais do campo e desorganiza o avanço adversário por meio de forças convergentes.",
    "suporte": "Canaliza a afinidade dominante para sustentar aliados e alterar o curso do confronto.",
}

LIMITE_DESVIO_50_50_PP = 5.0
MINIMO_AMOSTRA_BALANCEAMENTO = 20


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _seed_int(seed: str | int | bytes) -> int:
    raw = seed if isinstance(seed, bytes) else str(seed).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest(), "big")


def _majority(values: Iterable[str], fallback: str) -> str:
    counts = Counter(v for v in values if v)
    if not counts:
        return fallback
    # Desempate estável e independente da ordem dos ingredientes.
    highest = max(counts.values())
    return sorted(k for k, n in counts.items() if n == highest)[0]


def _rarity(ingredients: list[dict[str, Any]]) -> str:
    order = list(RARIDADES_GERADOR)
    ranks = sorted(order.index(classificar_carta(x)["raridade"]) for x in ingredients)
    # Mediana inferior: uma combinação mista não escala automaticamente ao ingrediente mais raro.
    return order[ranks[(len(ranks) - 1) // 2]]


def calcular_distribuicao_50_50(total_sem_habilidade: int, total_com_habilidade: int) -> dict[str, Any]:
    """Mede a distribuição cumulativa; não altera nem força a próxima geração."""
    sem = max(0, int(total_sem_habilidade))
    com = max(0, int(total_com_habilidade))
    total = sem + com
    return {
        "total": total,
        "sem_habilidade": sem,
        "com_habilidade": com,
        "percentual_sem_habilidade": round(100 * sem / total, 2) if total else 0.0,
        "percentual_com_habilidade": round(100 * com / total, 2) if total else 0.0,
        "meta": "50/50 cumulativo",
        "desvio_pontos_percentuais": round(abs(50 - (100 * com / total)), 2) if total else 0.0,
    }


def gerar_carta_procedural(
    ingredientes: Iterable[dict[str, Any]],
    *,
    seed: str | int | bytes,
    generated_id: str,
    balanceamento: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Gera uma proposta procedural determinística; não grava nem consome ingredientes."""
    itens = [dict(x) for x in ingredientes]
    valido, motivo = validar_ingredientes(itens)
    if not valido:
        return {"valido": False, "status": "ingredientes_invalidos", "motivo": motivo}
    if not generated_id or not re.fullmatch(r"[a-zA-Z0-9_-]{8,100}", str(generated_id)):
        return {"valido": False, "status": "id_invalido", "motivo": "ID permanente do servidor inválido."}

    compat = analisar_compatibilidade(itens)
    classes = [classificar_carta(x) for x in itens]
    faccao = _majority((x["faccao"] for x in classes if x["faccao"] in FACCOES), "Ordem Áurea")
    funcao = _majority((x["funcao"] for x in classes), "ataque")
    raridade = _rarity(itens)
    afinidades = Counter(a for x in classes for a in x["afinidades"])
    afinidade = sorted(afinidades, key=lambda a: (-afinidades[a], a))[0] if afinidades else "ancestral"

    rng = random.Random(_seed_int(seed))
    minimo, maximo = FAIXA_PODER[raridade]
    # Efeitos mais disruptivos têm menor poder-base; não excede a faixa da raridade.
    pool_habilidades = sorted(HABILIDADES_POR_FUNCAO.get(funcao, set()) & set(HABILIDADES_COMUNS) & set(HABILIDADES))
    if not pool_habilidades:
        return {"valido": False, "status": "sem_habilidade_compativel",
                "motivo": "Não existe habilidade aprovada para esta função tática."}
    habilidade_id = rng.choice(pool_habilidades) if rng.random() < 0.5 else ""
    poder = rng.randint(minimo, maximo)
    # Habilidades de maior impacto recebem orçamento de poder menor.
    if habilidade_id and PESO_HABILIDADE.get(habilidade_id, 1) >= 2:
        poder = max(minimo, poder - 1)

    arquetipo = rng.choice(ARQUETIPOS_POR_FUNCAO[funcao])
    epiteto = rng.choice(EPITETOS_POR_AFINIDADE[afinidade])
    nome = f"{PREFIXO_AFINIDADE[afinidade]} {arquetipo} {epiteto}"
    if habilidade_id:
        habilidade = {
            "id": habilidade_id,
            "nome": HABILIDADES[habilidade_id]["nome"],
            "descricao": HABILIDADES[habilidade_id]["texto"],
        }
    else:
        habilidade = None

    snapshot = [
        {
            "exemplar_id": str(x.get("exemplar_id", x.get("id"))),
            "card_id": str(x.get("card_id", x.get("id", ""))),
            "nome": str(x.get("nome", x.get("name", ""))),
            "raridade": classificar_carta(x)["raridade"],
            "faccao": classificar_carta(x)["faccao"],
        }
        for x in itens
    ]
    definition = {
        "card_id": str(generated_id),
        "nome": nome,
        "categoria": "Unidade",
        "tipo": TIPO_POR_FACCAO[faccao],
        "faccao": faccao,
        "raridade": raridade,
        "poder": poder,
        "custo": 0,
        "habilidade": habilidade_id,
        "habilidades": [habilidade] if habilidade else [],
        "descricao": LORE_POR_FUNCAO[funcao], 
        "arquetipo": arquetipo,
        "epiteto": epiteto,
        "identidade_procedural": {
            "versao": "v45",
            "afinidade": afinidade,
            "funcao": funcao,
            "semente_identidade": hashlib.sha256((str(seed) + ":identity").encode("utf-8")).hexdigest(),
        },
        "afinidades": sorted(afinidades) or [afinidade],
        "afinidade_dominante": afinidade,
        "funcao_tatica": funcao,
        "fileira": FILEIRA_POR_FUNCAO[funcao],
        "origem_tipo": "transmutacao",
        "owner_scoped": True,
        "is_sacrificable": False,
        "ingredientes": snapshot,
        "compatibilidade": {
            "score": compat["score"],
            "nivel": compat["compatibilidade"],
        },
        "generator_version": "v45",
    }
    # Defesa adicional: nenhuma habilidade fora do conjunto já implementado.
    if habilidade_id and (habilidade_id not in HABILIDADES_COMUNS or habilidade_id not in HABILIDADES):
        return {"valido": False, "status": "habilidade_nao_aprovada"}
    monitor = None
    if balanceamento is not None:
        monitor = avaliar_balanceamento_cumulativo(
            balanceamento.get("sem_habilidade", 0) + (0 if habilidade_id else 1),
            balanceamento.get("com_habilidade", 0) + (1 if habilidade_id else 0),
        )
    return {
        "valido": True,
        "status": "proposta_gerada",
        "definition": definition,
        "has_ability": bool(habilidade_id),
        "compatibilidade": compat,
        "balanceamento_cumulativo": monitor,
        "seed_hash": hashlib.sha256(str(seed).encode("utf-8")).hexdigest(),
        "consumo_executado": False,
        "persistencia_executada": False,
        "publicada": False,
    }


def avaliar_balanceamento_cumulativo(
    total_sem_habilidade: int,
    total_com_habilidade: int,
    *,
    minimo_amostra: int = MINIMO_AMOSTRA_BALANCEAMENTO,
    limite_desvio_pp: float = LIMITE_DESVIO_50_50_PP,
) -> dict[str, Any]:
    """Classifica a distribuição acumulada sem manipular a geração individual."""
    dados = calcular_distribuicao_50_50(total_sem_habilidade, total_com_habilidade)
    desvio = float(dados["desvio_pontos_percentuais"])
    if dados["total"] < max(1, int(minimo_amostra)):
        status = "amostra_insuficiente"
        alerta = False
    elif desvio <= float(limite_desvio_pp):
        status = "dentro_da_meta"
        alerta = False
    else:
        status = "revisao_de_balanceamento"
        alerta = True
    dados.update({
        "status": status,
        "alerta": alerta,
        "limite_desvio_pp": float(limite_desvio_pp),
        "minimo_amostra": int(minimo_amostra),
        "acao": "monitorar" if not alerta else "revisar parâmetros; não alterar retroativamente cartas",
    })
    return dados


def validar_definicao_gerada(definition: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validação estrita da definição; não substitui playtests competitivos."""
    erros: list[str] = []
    if not isinstance(definition, dict):
        return False, ["A definição precisa ser um objeto."]
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,100}", str(definition.get("card_id", ""))):
        erros.append("ID permanente inválido.")
    if not str(definition.get("nome", "")).strip() or len(str(definition.get("nome", ""))) > 80:
        erros.append("Nome ausente ou acima de 80 caracteres.")
    if definition.get("categoria") != "Unidade":
        erros.append("Apenas unidades podem ser geradas.")
    if definition.get("raridade") not in RARIDADES_GERADOR:
        erros.append("Raridade bloqueada ou inválida.")
    faixa = FAIXA_PODER.get(str(definition.get("raridade")))
    poder = definition.get("poder")
    if not faixa or isinstance(poder, bool) or not isinstance(poder, int) or not faixa[0] <= poder <= faixa[1]:
        erros.append("Poder fora da faixa permitida.")
    if definition.get("faccao") not in FACCOES:
        erros.append("Facção inválida.")
    if definition.get("tipo") != TIPO_POR_FACCAO.get(definition.get("faccao")):
        erros.append("Tipo legado não corresponde à facção.")
    if definition.get("origem_tipo") != "transmutacao" or definition.get("is_sacrificable") is not False:
        erros.append("Proteção de carta pessoal ausente.")
    if definition.get("owner_scoped") is not True:
        erros.append("A carta precisa ser exclusiva do proprietário.")
    funcao = definition.get("funcao_tatica")
    if funcao not in FILEIRA_POR_FUNCAO or definition.get("fileira") != FILEIRA_POR_FUNCAO.get(funcao):
        erros.append("Função tática e fileira incompatíveis.")
    afinidades = definition.get("afinidades")
    if not isinstance(afinidades, list) or not afinidades or definition.get("afinidade_dominante") not in afinidades:
        erros.append("Afinidades ausentes ou afinidade dominante inconsistente.")
    habilidade = str(definition.get("habilidade") or "")
    habilidades = definition.get("habilidades")
    if not isinstance(habilidades, list) or len(habilidades) > 1:
        erros.append("A V31 permite no máximo uma habilidade.")
    if habilidade:
        if habilidade not in HABILIDADES_COMUNS or habilidade not in HABILIDADES:
            erros.append("Habilidade não aprovada.")
        if habilidade not in HABILIDADES_POR_FUNCAO.get(str(funcao), set()):
            erros.append("Habilidade incompatível com a função tática.")
        if not habilidades or habilidades[0].get("id") != habilidade:
            erros.append("Lista de habilidades não corresponde ao identificador principal.")
        elif habilidades[0].get("nome") != HABILIDADES[habilidade]["nome"] or habilidades[0].get("descricao") != HABILIDADES[habilidade]["texto"]:
            erros.append("Texto da habilidade diverge do efeito implementado no motor.")
        if PESO_HABILIDADE.get(habilidade, 1) >= 2 and poder == faixa[1]:
            erros.append("Habilidade de maior impacto não pode usar o teto de poder da raridade.")
    elif habilidades:
        erros.append("Carta sem habilidade contém efeitos na lista.")
    if definition.get("custo") != 0:
        erros.append("Custo de unidade gerada deve permanecer neutro na V31.")
    ingredientes = definition.get("ingredientes")
    if not isinstance(ingredientes, list) or not 3 <= len(ingredientes) <= 5:
        erros.append("Snapshot deve conter de 3 a 5 ingredientes.")
    else:
        ids = [str(x.get("exemplar_id", "")) for x in ingredientes]
        if any(not x for x in ids) or len(set(ids)) != len(ids):
            erros.append("Snapshot contém ingredientes ausentes ou repetidos.")
    return not erros, erros


def validar_lote_gerado(definitions: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Audita um lote em busca de erros estruturais e colisões de identidade."""
    itens = list(definitions)
    erros_por_carta = []
    ids: Counter[str] = Counter()
    nomes: Counter[str] = Counter()
    for index, definition in enumerate(itens):
        ok, erros = validar_definicao_gerada(definition)
        card_id = str(definition.get("card_id", f"index_{index}"))
        ids[card_id] += 1
        nomes[_norm(definition.get("nome", ""))] += 1
        if not ok:
            erros_por_carta.append({"card_id": card_id, "erros": erros})
    ids_duplicados = sorted(k for k, n in ids.items() if n > 1)
    nomes_duplicados = sorted(k for k, n in nomes.items() if k and n > 1)
    return {
        "valido": not erros_por_carta and not ids_duplicados,
        "total": len(itens),
        "erros": erros_por_carta,
        "ids_duplicados": ids_duplicados,
        "nomes_repetidos": nomes_duplicados,
        "observacao": "Nomes repetidos são alertas de revisão; IDs repetidos invalidam o lote.",
    }
