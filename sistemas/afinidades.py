"""Taxonomia e compatibilidade do Laboratório de Transmutação (V29).

Este módulo é determinístico: não sorteia, não consome recursos e não cria cartas.
Afinidades inferidas são etiquetas temáticas, não habilidades de combate.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any, Iterable

FACCOES = ("Ordem Áurea", "Véu Carmesim", "Lua Negra")
TIPO_PARA_FACCAO = {
    "Força": "Ordem Áurea",
    "Destreza": "Véu Carmesim",
    "Magia": "Lua Negra",
}
FACCAO_ALIASES = {
    "ordem aurea": "Ordem Áurea", "veu carmesim": "Véu Carmesim",
    "lua negra": "Lua Negra",
}
AFINIDADES = (
    "sagrado", "fogo", "sangue", "morte", "lua", "magia",
    "relampago", "gravidade", "gelo", "veneno", "ancestral", "bestial",
)
FUNCOES = ("ataque", "defesa", "controle", "suporte")
RARIDADES_GERADOR = ("Comum", "Rara", "Épica", "Lendária", "Mítica")
CATEGORIAS_EXCLUIDAS = {"especial", "lider", "líder"}

# Afinidades primárias por famílias temáticas explícitas do catálogo Elden Ring.
# Os termos são normalizados antes da comparação; mais de uma afinidade pode coexistir.
TERMOS_AFINIDADE = {
    "sagrado": ("aurea", "ouro", "ordem", "graca", "haligtree", "radagon", "marika", "sagrado"),
    "fogo": ("fogo", "chama", "fornalha", "messmer", "magma", "vulcao", "rykard"),
    "sangue": ("sangue", "mog", "mohg", "hemorragia", "dinastia", "carmesim"),
    "morte": ("morte", "maliketh", "runa da morte", "necrom", "morto", "destinado"),
    "lua": ("lua", "carian", "ranni", "nevoa", "noite", "estrelas"),
    "magia": ("magia", "feitico", "arcano", "runa", "arcan"),
    "relampago": ("relampago", "raio", "tempestade", "dragao", "placidusax", "trov"),
    "gravidade": ("gravidade", "radahn", "cosmico", "meteoro", "estrela"),
    "gelo": ("gelo", "frio", "nevasca", "congel"),
    "veneno": ("veneno", "podr", "tox", "putr"),
    "ancestral": ("ancestral", "primordial", "ancestrais", "espirito", "cervo"),
    "bestial": ("bestial", "gurranq", "fera", "garra", "caçador"),
}
FUNCAO_POR_PAPEL = {
    "vanguarda": "defesa", "guardiao runico": "defesa", "duelista": "ataque",
    "batedor": "ataque", "batedor de guerra": "ataque",
    "atirador de elite": "ataque", "artilheiro": "controle",
    "arcanista": "controle", "invocador": "suporte", "tatica": "suporte",
}
FUNCAO_POR_FILEIRA = {"melee": "ataque", "ranged": "ataque", "siege": "controle"}


def normalizar(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto.casefold()).strip()


def _texto_carta(carta: dict[str, Any]) -> str:
    return normalizar(" ".join(str(carta.get(k, "")) for k in
        ("id", "nome", "name", "descricao", "description", "jogo_origem", "origem", "lore")))


def classificar_carta(carta: dict[str, Any]) -> dict[str, Any]:
    """Extrai facção, origem, afinidades e função sem alterar o objeto de entrada."""
    tipo = str(carta.get("tipo", ""))
    faccao = str(carta.get("faccao") or TIPO_PARA_FACCAO.get(tipo, ""))
    if normalizar(faccao) in FACCAO_ALIASES:
        faccao = FACCAO_ALIASES[normalizar(faccao)]
    texto = _texto_carta(carta)
    afinidades = []
    for afinidade, termos in TERMOS_AFINIDADE.items():
        if any(normalizar(t) in texto for t in termos):
            afinidades.append(afinidade)
    # Rótulos explicitamente fornecidos têm precedência e são filtrados pela taxonomia.
    declaradas = carta.get("afinidades") or carta.get("affinities") or []
    for item in declaradas:
        chave = normalizar(item).replace(" ", "_")
        if chave in AFINIDADES and chave not in afinidades:
            afinidades.append(chave)
    origem = str(carta.get("origem_tipo") or carta.get("origin_type") or
                 carta.get("categoria_origem") or carta.get("categoria") or "catalogo")
    papel = str(carta.get("papel_gwent") or carta.get("role") or "")
    funcao = FUNCAO_POR_PAPEL.get(normalizar(papel))
    if not funcao:
        funcao = FUNCAO_POR_FILEIRA.get(str(carta.get("fileira", "")), "suporte")
    return {
        "faccao": faccao if faccao in FACCOES else "Indeterminada",
        "origem": origem,
        "afinidades": sorted(afinidades),
        "funcao": funcao,
        "raridade": str(carta.get("raridade") or carta.get("rarity") or "Comum"),
        "categoria": str(carta.get("categoria") or "Unidade"),
    }


def validar_ingredientes(ingredientes: Iterable[dict[str, Any]]) -> tuple[bool, str]:
    itens = list(ingredientes)
    if not 3 <= len(itens) <= 5:
        return False, "A transmutação exige de 3 a 5 exemplares."
    ids = [str(x.get("exemplar_id", x.get("id", ""))) for x in itens]
    if any(not x for x in ids) or len(set(ids)) != len(ids):
        return False, "Cada ingrediente precisa ser um exemplar distinto."
    for item in itens:
        dados = classificar_carta(item)
        if normalizar(dados["categoria"]) in CATEGORIAS_EXCLUIDAS:
            return False, "Cartas especiais e líderes não podem ser ingredientes."
        if dados["raridade"] not in RARIDADES_GERADOR:
            return False, "Primordiais e Singulares estão bloqueadas no gerador comum."
        if item.get("is_sacrificable") is False or item.get("is_sacrificable") == 0:
            return False, "Este exemplar é permanente e não pode ser sacrificado."
        if normalizar(item.get("origin_type")) == "transmutacao":
            return False, "Cartas geradas pelo Laboratório não podem ser sacrificadas."
    return True, "Ingredientes estruturalmente válidos."


def analisar_compatibilidade(ingredientes: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Pontua coerência temática sem converter o resultado em chance de sucesso."""
    itens = list(ingredientes)
    valido, motivo = validar_ingredientes(itens)
    if not valido:
        return {"valido": False, "motivo": motivo, "score": 0, "compatibilidade": "invalida",
                "faccao_dominante": "Indeterminada", "afinidades": [], "funcoes": []}
    classes = [classificar_carta(x) for x in itens]
    faccoes = Counter(x["faccao"] for x in classes if x["faccao"] in FACCOES)
    afinidades = Counter(a for x in classes for a in x["afinidades"])
    funcoes = Counter(x["funcao"] for x in classes)
    score = 0
    explicacoes = []
    if faccoes:
        n = faccoes.most_common(1)[0][1]
        score += round(30 * n / len(classes))
        explicacoes.append(f"Coesão de facção: {n}/{len(classes)}.")
    if afinidades:
        top, n = afinidades.most_common(1)[0]
        score += round(40 * n / len(classes))
        explicacoes.append(f"Afinidade predominante: {top} ({n}/{len(classes)}).")
    if funcoes:
        n = max(funcoes.values())
        score += round(20 * n / len(classes))
        explicacoes.append(f"Concentração funcional: {n}/{len(classes)}.")
    # Mistura de 2-3 funções recebe bônus por diversidade controlada.
    diversidade = len(funcoes)
    if diversidade >= 2:
        score += 10
        explicacoes.append("Composição tática diversificada.")
    score = min(100, score)
    nivel = "alta" if score >= 75 else "media" if score >= 50 else "baixa"
    dominante = faccoes.most_common(1)[0][0] if faccoes else "Indeterminada"
    return {
        "valido": True, "motivo": "Ingredientes compatíveis para análise.",
        "score": score, "compatibilidade": nivel,
        "faccao_dominante": dominante,
        "afinidades": [{"id": k, "peso": v} for k, v in afinidades.most_common()],
        "funcoes": [{"id": k, "quantidade": v} for k, v in funcoes.most_common()],
        "explicacoes": explicacoes,
    }
