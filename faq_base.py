"""Base local de FAQ da Nara: reconhecimento aproximado e respostas finais.

Não chama IA, rede ou serviços externos. As respostas em JSON são mensagens finais
prontas para Discord; intenções com `handler` consultam código/SQLite já existente.
"""
from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent / "dados" / "nara_faq.json"
STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "da", "do", "das", "dos",
    "em", "no", "na", "nos", "nas", "por", "para", "pra", "com", "sem", "e", "ou", "que",
    "como", "qual", "quais", "quando", "onde", "quem", "me", "minha", "meu", "minhas", "meus",
    "eu", "voce", "voces", "aqui", "isso", "esse", "essa", "faz", "fazer", "tem", "ter",
    "posso", "consigo", "quero", "queria", "gostaria", "mostra", "mostrar", "diga", "dizer",
    "fala", "falar", "sobre", "bot", "servidor",
}


@lru_cache(maxsize=16384)
def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or "").casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"https?://\S+", " ", texto)
    texto = re.sub(r"[^a-z0-9 ]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


@lru_cache(maxsize=16384)
def _tokens_normalizados(texto_normalizado: str) -> frozenset[str]:
    return frozenset(t for t in texto_normalizado.split() if len(t) > 1 and t not in STOPWORDS)


def _tokens(texto: str) -> frozenset[str]:
    return _tokens_normalizados(normalizar(texto))


@lru_cache(maxsize=1)
def carregar_base() -> dict:
    with BASE_PATH.open("r", encoding="utf-8") as arquivo:
        data = json.load(arquivo)
    if not isinstance(data.get("intents"), list):
        raise ValueError("Base FAQ inválida: campo 'intents' ausente")
    return data


@lru_cache(maxsize=32768)
def _token_ratio(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if min(len(a), len(b)) < 4 or abs(len(a) - len(b)) > 2:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


@lru_cache(maxsize=1)
def _corpus_preparado():
    """Pré-processa FAQ uma vez; não normaliza os mesmos exemplos a cada mensagem."""
    base = carregar_base()
    preparados = []
    exatos = {}
    for item in base["intents"]:
        intent = item.get("intent")
        exemplos = list(item.get("examples", []))
        exemplos.extend([item.get("title", ""), " ".join(item.get("keywords", []))])
        linhas = []
        vocabulario = set()
        for exemplo in exemplos:
            if not exemplo:
                continue
            norm = normalizar(str(exemplo))
            tokens = _tokens_normalizados(norm)
            if not norm:
                continue
            linhas.append((norm, tokens))
            vocabulario.update(tokens)
        for exemplo in item.get("examples", []):
            norm = normalizar(str(exemplo))
            if norm:
                exatos.setdefault(norm, intent)
        preparados.append((intent, tuple(linhas), frozenset(vocabulario)))
    return tuple(preparados), exatos


def _score_preparado(qnorm: str, qt: frozenset[str], exemplo: str,
                     et: frozenset[str], fuzzy_threshold: float) -> float:
    if qnorm == exemplo:
        return 1.0
    if not qt or not et:
        return 0.0

    comuns_exatos = qt & et
    correspondencias = 0
    # Se já existem duas palavras exatas em comum, não precisamos pagar por
    # comparação fuzzy de todos os tokens desta frase.
    if len(comuns_exatos) < 2:
        usados = set()
        for token in qt - et:
            candidato = None
            melhor = 0.0
            for outro in et - usados:
                ratio = _token_ratio(token, outro)
                if ratio >= fuzzy_threshold and ratio > melhor:
                    melhor = ratio
                    candidato = outro
            if candidato is not None:
                usados.add(candidato)
                correspondencias += 1

        # Sem palavra compartilhada (nem por similaridade), a comparação da
        # frase inteira não pode ser um sinal confiável: elimina este exemplo.
        if not comuns_exatos and not correspondencias:
            return 0.0

    inter = len(comuns_exatos) + correspondencias
    cobertura = inter / max(1, min(len(qt), len(et)))
    jaccard = inter / max(1, len(qt | et))
    sequencia = SequenceMatcher(None, qnorm, exemplo).ratio()
    return min(1.0, 0.58 * cobertura + 0.17 * jaccard + 0.25 * sequencia)


def classificar(pergunta: str, *, min_score: float | None = None,
                min_margin: float | None = None) -> tuple[str | None, float]:
    """Classifica paráfrases locais com corpus pré-processado e margem antichute."""
    base = carregar_base()
    cfg = base.get("matching", {})
    threshold = float(min_score if min_score is not None else cfg.get("min_score", 0.54))
    margin = float(min_margin if min_margin is not None else cfg.get("min_margin", 0.09))
    fuzzy_threshold = float(cfg.get("fuzzy_token_threshold", 0.88))
    min_shared = int(cfg.get("minimum_shared_tokens", 2))

    qnorm = normalizar(str(pergunta or ""))
    if not qnorm:
        return None, 0.0

    corpus, exatos = _corpus_preparado()
    intent_exato = exatos.get(qnorm)
    if intent_exato:
        return intent_exato, 1.0

    qt = _tokens_normalizados(qnorm)
    if not qt:
        return None, 0.0

    melhores_por_intent = []
    for intent, exemplos, vocabulario in corpus:
        melhor = 0.0
        for exemplo, et in exemplos:
            score = _score_preparado(qnorm, qt, exemplo, et, fuzzy_threshold)
            if score > melhor:
                melhor = score
                if melhor >= 0.999:
                    break

        compartilhados = len(qt & vocabulario)
        if compartilhados < min_shared:
            faltantes = qt - vocabulario
            extras = sum(
                any(_token_ratio(token, outro) >= fuzzy_threshold for outro in vocabulario)
                for token in faltantes
            )
            compartilhados += extras
        melhores_por_intent.append((intent, melhor, compartilhados))

    melhores_por_intent.sort(key=lambda x: x[1], reverse=True)
    if not melhores_por_intent:
        return None, 0.0
    primeiro, score, compartilhados = melhores_por_intent[0]
    segundo_score = melhores_por_intent[1][1] if len(melhores_por_intent) > 1 else 0.0
    if (score < threshold or compartilhados < min_shared or (score - segundo_score) < margin):
        return None, score
    return primeiro, score


def resposta_pronta(intent: str) -> str | None:
    """Retorna a mensagem final escrita para o membro, sem prefixos repetitivos."""
    for item in carregar_base()["intents"]:
        if item.get("intent") == intent:
            answer = str(item.get("answer") or "").strip()
            return answer or None
    return None


def estatisticas() -> dict[str, int]:
    intents = carregar_base()["intents"]
    return {
        "intencoes": len(intents),
        "exemplos": sum(len(i.get("examples", [])) for i in intents),
        "respostas_prontas": sum(bool(i.get("answer")) for i in intents),
        "handlers_dinamicos": sum(bool(i.get("handler")) for i in intents),
    }
