"""Pesquisa multi-provedor e geração de rascunhos de catálogos.

DeepSeek Search + Flash é principal; Gemini + Google Search grounding é reserva.
A IA identifica e pesquisa; o código valida as URLs e mantém tudo em revisão.
Nenhum dado gerado pela IA é publicado automaticamente.
"""
from __future__ import annotations

import json
import logging
import re

from ia_provedores import gerar_pesquisa_com_failover

log = logging.getLogger("nara.trofeus.ai")


def _json_from_text(text: str) -> dict:
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("A IA não retornou JSON válido.")
    data = json.loads(raw[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("A resposta da IA não é um objeto JSON.")
    return data



async def _generate(prompt: str, search_queries: list[str] | None = None) -> tuple[str, list[dict]]:
    """Pesquisa DeepSeek primeiro e alterna para Gemini + grounding se necessário."""
    queries = search_queries or [
        "video game official title developer publisher release date platforms " + prompt[:60]
    ]
    text, sources, provider = await gerar_pesquisa_com_failover(prompt, queries)
    log.info("Pesquisa de catálogo concluída pelo provedor %s; fontes HTTPS=%d", provider, len(sources))
    # Fonte é sempre URL HTTPS devolvida pelo mecanismo de pesquisa, nunca URL inventada pelo modelo.
    return text, sources


async def identificar_jogo(consulta: str) -> dict:
    """Resolve abreviações/erros para títulos oficiais, sem assumir edição."""
    consulta = " ".join((consulta or "").split())[:120]
    if len(consulta) < 2:
        raise ValueError("Digite pelo menos dois caracteres.")
    import unicodedata
    normalized = unicodedata.normalize("NFKD", consulta).encode("ascii", "ignore").decode().casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    known = {
        "god of war 2018", "god of war 18", "god of war ps4", "god of war 4",
        "god of war iv", "gow 2018", "gow4", "gow 4"
    }
    if normalized in known:
        return {
            "input": consulta,
            "candidates": [{
                "canonical_title": "God of War",
                "original_title": "God of War",
                "release_year": 2018,
                "developer": "Santa Monica Studio",
                "publisher": "Sony Interactive Entertainment",
                "platforms": ["PlayStation 4", "PC"],
                "edition_scope": "Jogo base de 2018; DLC e conteúdo adicional devem ser confirmados separadamente.",
                "aliases": sorted(known),
                "confidence": 1.0,
                "identity_evidence": "Correspondência canônica local para God of War (2018), distinto do jogo original de 2005 e de Ragnarök (2022)."
            }],
            "needs_clarification": False,
            "notes": "Título reconhecido pela regra local. A pesquisa de catálogo e suas fontes ainda precisam ser executadas e revisadas.",
            "sources": []
        }
    prompt = f"""
Você é um catalogador de videogames. Identifique o jogo que o usuário quis dizer.
Entrada literal (pode conter erro, abreviação, tradução ou edição): {consulta!r}

Pesquise na web. Priorize fontes oficiais (site do estúdio/editora, Steam, PlayStation,
Xbox, Nintendo) para identidade, e bases reconhecidas para desambiguação.
NÃO transforme o texto digitado em nome oficial sem verificar. NÃO invente jogos.
Diferencie jogo-base, remake/remaster, edição/versão, DLC e sequência.
Se a entrada for ambígua, retorne vários candidatos em ordem de confiança.
Retorne SOMENTE JSON neste formato:
{{
 "input": "...",
 "candidates": [
  {{"canonical_title":"título oficial","original_title":"título no idioma original",
   "release_year":2022,"developer":"estúdio","publisher":"editora",
   "platforms":["PC","PS5"],"edition_scope":"jogo base; DLC X opcional",
   "aliases":["abreviações e erros comuns"],"confidence":0.0,
   "identity_evidence":"por que é este jogo"}}
 ],
 "needs_clarification": true,
 "notes":"limitações e diferenças relevantes"
}}
No máximo 5 candidatos. Confidence entre 0 e 1. Se não houver correspondência confiável, candidates deve ser [].
"""
    text, sources = await _generate(
        prompt, [f'"{consulta}" video game official title release year developer publisher platforms']
    )
    if not sources:
        return {
            "input": consulta, "candidates": [], "needs_clarification": True,
            "notes": "A pesquisa não retornou referências verificáveis em fontes HTTPS de nenhum provedor. Nenhuma identificação foi aceita.",
            "sources": [],
        }
    data = _json_from_text(text)
    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    clean = []
    for c in candidates[:5]:
        if not isinstance(c, dict) or not str(c.get("canonical_title", "")).strip():
            continue
        try:
            confidence = max(0.0, min(1.0, float(c.get("confidence", 0))))
        except (TypeError, ValueError):
            confidence = 0.0
        clean.append({
            "canonical_title": str(c["canonical_title"]).strip()[:120],
            "original_title": str(c.get("original_title") or c["canonical_title"]).strip()[:120],
            "release_year": int(c["release_year"]) if str(c.get("release_year", "")).isdigit() and 1970 <= int(c["release_year"]) <= 2100 else None,
            "developer": str(c.get("developer", ""))[:120],
            "publisher": str(c.get("publisher", ""))[:120],
            "platforms": [str(x)[:40] for x in c.get("platforms", [])[:12]] if isinstance(c.get("platforms"), list) else [],
            "edition_scope": str(c.get("edition_scope", ""))[:500],
            "aliases": [str(x)[:100] for x in c.get("aliases", [])[:30]] if isinstance(c.get("aliases"), list) else [],
            "confidence": confidence,
            "identity_evidence": str(c.get("identity_evidence", ""))[:700],
        })
    return {
        "input": consulta, "candidates": clean,
        "needs_clarification": bool(data.get("needs_clarification", len(clean) != 1)),
        "notes": str(data.get("notes", ""))[:1000],
        "sources": sources,
    }


async def pesquisar_catalogo(candidato: dict, incluir_dlc: bool = True) -> dict:
    """Cria rascunho estruturado com fontes. O resultado sempre entra em revisão."""
    title = str(candidato.get("canonical_title", "")).strip()
    scope = str(candidato.get("edition_scope", "jogo base"))
    prompt = f"""
Você é um pesquisador de guias de videogame. Monte um RASCUNHO verificável de catálogo
para o jogo oficialmente identificado abaixo. Pesquise fontes atuais na web.
Jogo: {title}
Título original: {candidato.get('original_title', title)}
Escopo informado: {scope}
Incluir DLC: {"sim" if incluir_dlc else "não"}
Plataformas: {", ".join(candidato.get("platforms", []))}

OBJETIVO: checklist que conecte colecionáveis a troféus/conquistas sem duplicar itens.
Priorize wiki especializada do jogo, guias reconhecidos e fontes oficiais para troféus.
Não copie conteúdo extenso. Parafraseie em português. Não invente localização, requisitos,
nomes oficiais ou troféus. Se não tiver evidência suficiente, omita o registro.
Inclua armas, armaduras, anéis/acessórios, magias/habilidades, gestos e outros tipos
relevantes ao jogo, mas só os que conseguir fundamentar.
Para troféus, use a lista completa APENAS se encontrar uma fonte confiável de cobertura completa.
Se não puder assegurar completude, declare isso em coverage_notes e retorne apenas os registros
que conseguiu verificar. Não invente que o catálogo é completo.

Retorne SOMENTE JSON neste formato:
{{
 "name":"título oficial","name_original":"título original","slug":"slug-kebab-case",
 "platforms":["..."],"coverage_notes":"o que está coberto e o que falta",
 "sources":[{{"title":"...","url":"https://...","kind":"wiki|official|guide|database"}}],
 "items":[
  {{"category":"Armas","name_pt":"...","name_original":"...","description_pt":"...",
   "location_pt":"...","acquisition_pt":"...","dlc":"...","ng_cycle":"...",
   "missable":false,"source_url":"https://fonte-exata"}}
 ],
 "trophies":[
  {{"name_pt":"...","name_original":"...","description_pt":"...","grade":"Bronze|Prata|Ouro|Platina",
   "is_platinum":false,"source_url":"https://fonte-exata",
   "requirements":[{{"item_name_original":"nome exato de um item do array items",
    "description_pt":"...","quantity":1}}]}}
 ]
}}
REGRAS:
- Cada item e troféu precisa de source_url válido que apareça em sources ou seja fonte direta encontrada.
- Só conecte requirement a item que exista no array items. Não invente relações.
- Para requisitos que não sejam colecionáveis, descreva-os como texto em requirements, sem item_name_original.
- Não inclua campos verified; o sistema inicia tudo como não verificado.
- Não invente URL. Se não encontrar fonte específica, não inclua o registro.
- Respeite o escopo do jogo base/DLC informado.
"""
    search_queries = [
        f'"{title}" official trophy achievement list base game DLC',
        f'"{title}" complete collectibles weapons armor accessories spells locations guide',
        f'"{title}" missable trophies collectibles requirements guide',
        f'"{title}" all trophies achievements platinum requirements walkthrough',
    ]
    text, grounding = await _generate(prompt, search_queries)
    if not grounding:
        raise RuntimeError("Nenhum dos provedores de pesquisa retornou fontes HTTPS verificáveis para o catálogo.")
    data = _json_from_text(text)
    # O título foi confirmado pelo usuário; o modelo não pode renomear o jogo.
    data["name"] = title
    year = candidato.get("release_year")
    slug_base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    # Ano na chave evita colidir remakes/sequências com nomes canônicos iguais.
    data["slug"] = f"{slug_base}-{int(year)}" if isinstance(year, int) and 1970 <= year <= 2100 else slug_base
    # A lista do modelo não é prova. Só URLs retornadas pelo Search/Grounding usado
    # nesta execução são aceitas como evidência de pesquisa.
    merged = {}
    for src in grounding:
        if not isinstance(src, dict):
            continue
        url = str(src.get("url", "")).strip()
        if url.startswith("https://"):
            merged[url] = {"title": str(src.get("title", ""))[:180], "url": url,
                           "kind": str(src.get("kind") or "grounded_web")[:40]}
    data["sources"] = list(merged.values())[:30]
    valid_urls = set(merged)
    # Fail closed: reject malformed records and URLs that were not surfaced as sources.
    items = []
    for item in data.get("items", []) if isinstance(data.get("items"), list) else []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("source_url", "")).strip()
        if not item.get("name_pt") or not item.get("category") or url not in valid_urls:
            continue
        item["verified"] = False
        items.append(item)
    trophies = []
    for trophy in data.get("trophies", []) if isinstance(data.get("trophies"), list) else []:
        if not isinstance(trophy, dict):
            continue
        url = str(trophy.get("source_url", "")).strip()
        if not trophy.get("name_pt") or url not in valid_urls:
            continue
        trophy["verified"] = False
        reqs = []
        for req in trophy.get("requirements", []) if isinstance(trophy.get("requirements"), list) else []:
            if isinstance(req, dict):
                reqs.append(req)
        trophy["requirements"] = reqs
        trophies.append(trophy)
    data["items"], data["trophies"] = items[:10000], trophies[:2000]
    if not data["items"] or not data["trophies"]:
        raise RuntimeError(
            "As fontes encontradas não sustentaram pelo menos um item e um troféu. "
            "O catálogo não será salvo como se estivesse completo."
        )
    data["status"] = "review"
    data["research_sources"] = len(valid_urls)
    data["coverage_notes"] = str(data.get("coverage_notes", ""))[:1500]
    return data
