"""Serviços do Caçador de Troféus.

O catálogo é separado do inventário cosmético da loja. O progresso dos itens é
armazenado uma única vez e pode alimentar várias conquistas relacionadas.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone


def nome_exibicao(name_pt: str, name_original: str = "") -> str:
    pt = (name_pt or "").strip()
    original = (name_original or "").strip()
    if original and original.casefold() != pt.casefold():
        return f"{pt} ({original})" if pt else original
    return pt or original or "Item sem nome"


def _slug(valor: str) -> str:
    valor = valor.strip().lower()
    valor = re.sub(r"[^a-z0-9]+", "-", valor).strip("-")
    if not valor:
        raise ValueError("O jogo precisa ter um identificador (slug) válido.")
    return valor[:100]


def _bool_value(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y", "sim", "s"}
    return False


async def listar_jogos(db, apenas_prontos: bool = True):
    if apenas_prontos:
        return await db._all(
            "SELECT * FROM games_catalog WHERE status='ready' ORDER BY name COLLATE NOCASE"
        )
    return await db._all("SELECT * FROM games_catalog ORDER BY name COLLATE NOCASE")


async def buscar_jogo(db, game_id: int):
    return await db._one("SELECT * FROM games_catalog WHERE id=?", (game_id,))


async def registrar_acesso(db, user_id: int, game_id: int):
    await db.conn.execute(
        """INSERT INTO user_game_progress(user_id, game_id, last_viewed)
           VALUES (?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(user_id, game_id) DO UPDATE SET last_viewed=CURRENT_TIMESTAMP""",
        (user_id, game_id),
    )
    await db.conn.commit()


async def ultimo_jogo(db, user_id: int):
    return await db._one(
        """SELECT g.*, p.last_viewed FROM user_game_progress p
           JOIN games_catalog g ON g.id=p.game_id
           WHERE p.user_id=? AND g.status='ready'
           ORDER BY p.last_viewed DESC LIMIT 1""",
        (user_id,),
    )


async def categorias_do_jogo(db, game_id: int):
    return await db._all(
        """SELECT category, COUNT(*) AS total
           FROM game_items WHERE game_id=?
           GROUP BY category ORDER BY category COLLATE NOCASE""",
        (game_id,),
    )


async def listar_itens(db, game_id: int, category: str, user_id: int, limit: int = 25, offset: int = 0):
    return await db._all(
        """SELECT i.*, COALESCE(u.obtained, 0) AS obtained
           FROM game_items i
           LEFT JOIN user_collected_items u ON u.item_id=i.id AND u.user_id=?
           WHERE i.game_id=? AND i.category=?
           ORDER BY i.name_pt COLLATE NOCASE LIMIT ? OFFSET ?""",
        (user_id, game_id, category, limit, offset),
    )


async def contar_itens(db, game_id: int, category: str):
    row = await db._one(
        "SELECT COUNT(*) AS total FROM game_items WHERE game_id=? AND category=?",
        (game_id, category),
    )
    return int(row["total"] or 0)


async def progresso_categoria(db, game_id: int, category: str, user_id: int):
    row = await db._one(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN COALESCE(u.obtained,0)=1 THEN 1 ELSE 0 END) AS obtidos
           FROM game_items i
           LEFT JOIN user_collected_items u ON u.item_id=i.id AND u.user_id=?
           WHERE i.game_id=? AND i.category=?""",
        (user_id, game_id, category),
    )
    return int(row["obtidos"] or 0), int(row["total"] or 0)


async def progresso_jogo(db, game_id: int, user_id: int):
    row = await db._one(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN COALESCE(u.obtained,0)=1 THEN 1 ELSE 0 END) AS obtidos
           FROM game_items i
           LEFT JOIN user_collected_items u ON u.item_id=i.id AND u.user_id=?
           WHERE i.game_id=?""",
        (user_id, game_id),
    )
    return int(row["obtidos"] or 0), int(row["total"] or 0)


async def definir_item_obtido(db, user_id: int, item_id: int, obtido: bool):
    await db.conn.execute(
        """INSERT INTO user_collected_items(user_id,item_id,obtained,updated_at)
           VALUES (?,?,?,CURRENT_TIMESTAMP)
           ON CONFLICT(user_id,item_id) DO UPDATE SET
             obtained=excluded.obtained, updated_at=CURRENT_TIMESTAMP""",
        (user_id, item_id, 1 if obtido else 0),
    )
    await db.conn.commit()


async def listar_trofeus(db, game_id: int):
    return await db._all(
        "SELECT * FROM game_trophies WHERE game_id=? ORDER BY is_platinum DESC, name_pt COLLATE NOCASE",
        (game_id,),
    )


async def requisitos_trofeu(db, trophy_id: int, user_id: int):
    return await db._all(
        """SELECT r.*, i.name_pt, i.name_original, i.category,
                  COALESCE(u.obtained,0) AS obtained
           FROM trophy_requirements r
           LEFT JOIN game_items i ON i.id=r.item_id
           LEFT JOIN user_collected_items u ON u.item_id=i.id AND u.user_id=?
           WHERE r.trophy_id=? ORDER BY i.category, i.name_pt""",
        (user_id, trophy_id),
    )


async def progresso_trofeu(db, trophy_id: int, user_id: int):
    reqs = await requisitos_trofeu(db, trophy_id, user_id)
    row = await db._one(
        "SELECT completed FROM user_trophy_progress WHERE user_id=? AND trophy_id=?",
        (user_id, trophy_id),
    )
    if row and row["completed"]:
        return 1, 1, reqs
    linked = [r for r in reqs if r["item_id"] is not None]
    # Troféus sem itens vinculados dependem de confirmação manual.
    if not linked:
        return 0, 1, reqs
    total = len(linked)
    feitos = sum(1 for r in linked if r["obtained"])
    return feitos, total, reqs


async def definir_trofeu_concluido(db, user_id: int, trophy_id: int, concluido: bool):
    await db.conn.execute(
        """INSERT INTO user_trophy_progress(user_id,trophy_id,completed,updated_at)
           VALUES (?,?,?,CURRENT_TIMESTAMP)
           ON CONFLICT(user_id,trophy_id) DO UPDATE SET
             completed=excluded.completed,updated_at=CURRENT_TIMESTAMP""",
        (user_id, trophy_id, 1 if concluido else 0),
    )
    await db.conn.commit()


async def importar_catalogo(db, payload: dict, publicar: bool = False):
    """Importa catálogo como rascunho, atomicamente e sempre sem verificação humana."""
    from urllib.parse import urlparse

    if not isinstance(payload, dict):
        raise ValueError("O arquivo precisa conter um objeto JSON.")
    if publicar:
        raise ValueError("Publicação direta está bloqueada. Use /catalogo_validar e /catalogo_publicar.")

    nome = str(payload.get("name", "")).strip()[:120]
    if not nome:
        raise ValueError("Campo obrigatório ausente: name.")
    slug = _slug(str(payload.get("slug") or nome))
    itens = payload.get("items", [])
    trofeus = payload.get("trophies", [])
    sources_raw = payload.get("sources", [])
    platforms_raw = payload.get("platforms", [])
    if not isinstance(itens, list) or not isinstance(trofeus, list):
        raise ValueError("'items' e 'trophies' precisam ser listas.")
    if not isinstance(sources_raw, list) or not isinstance(platforms_raw, list):
        raise ValueError("'sources' e 'platforms' precisam ser listas.")
    if len(itens) > 10000 or len(trofeus) > 2000 or len(sources_raw) > 100:
        raise ValueError("O catálogo excede o limite de segurança de importação.")

    sources, valid_urls = [], set()
    for src in sources_raw:
        if not isinstance(src, dict):
            continue
        url = str(src.get("url", "")).strip()
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            continue
        if url not in valid_urls:
            valid_urls.add(url)
            sources.append({"title": str(src.get("title", "")).strip()[:180], "url": url,
                            "kind": str(src.get("kind", "source")).strip()[:40]})
    if not valid_urls:
        raise ValueError("Nenhuma fonte HTTPS válida foi fornecida. O catálogo não foi importado.")

    platforms = list(dict.fromkeys(str(x).strip()[:50] for x in platforms_raw
                                   if isinstance(x, (str, int)) and str(x).strip()))[:20]
    prepared_items = []
    seen_items = set()
    for item in itens:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "")).strip()[:80]
        name_pt = str(item.get("name_pt") or item.get("name") or "").strip()[:160]
        name_original = str(item.get("name_original") or item.get("name_en") or name_pt).strip()[:160]
        source_url = str(item.get("source_url", "")).strip()
        if not category or not name_pt or source_url not in valid_urls:
            continue
        key = (category.casefold(), name_original.casefold())
        if key in seen_items:
            continue
        seen_items.add(key)
        prepared_items.append({
            "category": category, "name_pt": name_pt, "name_original": name_original,
            "description_pt": str(item.get("description_pt", ""))[:1200],
            "location_pt": str(item.get("location_pt", ""))[:1200],
            "acquisition_pt": str(item.get("acquisition_pt", ""))[:1200],
            "dlc": str(item.get("dlc", ""))[:120], "ng_cycle": str(item.get("ng_cycle", ""))[:80],
            "missable": 1 if _bool_value(item.get("missable")) else 0, "source_url": source_url,
        })

    prepared_trophies = []
    seen_trophies = set()
    for trophy in trofeus:
        if not isinstance(trophy, dict):
            continue
        name_pt = str(trophy.get("name_pt") or trophy.get("name") or "").strip()[:160]
        name_original = str(trophy.get("name_original") or trophy.get("name_en") or name_pt).strip()[:160]
        source_url = str(trophy.get("source_url", "")).strip()
        if not name_pt or source_url not in valid_urls:
            continue
        if name_original.casefold() in seen_trophies:
            continue
        seen_trophies.add(name_original.casefold())
        raw_requirements = trophy.get("requirements", [])
        if not isinstance(raw_requirements, list):
            raw_requirements = []
        requirements = []
        for req in raw_requirements[:100]:
            if not isinstance(req, dict):
                continue
            try:
                quantity = int(req.get("quantity", 1))
            except (TypeError, ValueError):
                quantity = 1
            requirements.append({
                "item_name_original": str(req.get("item_name_original") or req.get("item_name_en") or "").strip()[:160],
                "description_pt": str(req.get("description_pt", "")).strip()[:1000],
                "quantity": max(1, min(999, quantity)),
            })
        prepared_trophies.append({
            "name_pt": name_pt, "name_original": name_original,
            "description_pt": str(trophy.get("description_pt", ""))[:1200],
            "grade": str(trophy.get("grade", ""))[:20],
            "is_platinum": 1 if _bool_value(trophy.get("is_platinum")) else 0,
            "source_url": source_url, "requirements": requirements,
        })

    if not prepared_items or not prepared_trophies:
        raise ValueError(
            "A pesquisa não produziu ao menos um item e um troféu com fonte HTTPS correspondente. "
            "Nada foi gravado; refine a pesquisa ou revise as fontes."
        )

    cover_url = str(payload.get("cover_url", "")).strip()
    cover = urlparse(cover_url)
    if cover.scheme != "https" or not cover.netloc:
        cover_url = ""

    # Conexão transacional separada: uma falha em qualquer item desfaz todo o lote.
    async with db.transaction() as tx:
        await tx.conn.execute(
            """INSERT INTO games_catalog(slug,name,name_original,status,platforms_json,cover_url,sources_json,updated_at)
               VALUES (?,?,?,'review',?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(slug) DO UPDATE SET
                 name=excluded.name, name_original=excluded.name_original, status='review',
                 platforms_json=excluded.platforms_json, cover_url=excluded.cover_url,
                 sources_json=excluded.sources_json, updated_at=CURRENT_TIMESTAMP""",
            (slug, nome, str(payload.get("name_original", ""))[:120],
             json.dumps(platforms, ensure_ascii=False), cover_url,
             json.dumps(sources, ensure_ascii=False)),
        )
        game = await tx._one("SELECT id FROM games_catalog WHERE slug=?", (slug,))
        game_id = int(game["id"])

        for item in prepared_items:
            await tx.conn.execute(
                """INSERT INTO game_items(
                     game_id,category,name_pt,name_original,description_pt,location_pt,
                     acquisition_pt,dlc,ng_cycle,missable,source_url,verified,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,0,CURRENT_TIMESTAMP)
                   ON CONFLICT(game_id,category,name_original) DO UPDATE SET
                     name_pt=excluded.name_pt, description_pt=excluded.description_pt,
                     location_pt=excluded.location_pt, acquisition_pt=excluded.acquisition_pt,
                     dlc=excluded.dlc, ng_cycle=excluded.ng_cycle, missable=excluded.missable,
                     source_url=excluded.source_url, verified=0, updated_at=CURRENT_TIMESTAMP""",
                (game_id, item["category"], item["name_pt"], item["name_original"],
                 item["description_pt"], item["location_pt"], item["acquisition_pt"],
                 item["dlc"], item["ng_cycle"], item["missable"], item["source_url"]),
            )

        for trophy in prepared_trophies:
            await tx.conn.execute(
                """INSERT INTO game_trophies(
                     game_id,name_pt,name_original,description_pt,grade,is_platinum,source_url,verified,updated_at)
                   VALUES (?,?,?,?,?,?,?,0,CURRENT_TIMESTAMP)
                   ON CONFLICT(game_id,name_original) DO UPDATE SET
                     name_pt=excluded.name_pt, description_pt=excluded.description_pt,
                     grade=excluded.grade, is_platinum=excluded.is_platinum,
                     source_url=excluded.source_url, verified=0, updated_at=CURRENT_TIMESTAMP""",
                (game_id, trophy["name_pt"], trophy["name_original"], trophy["description_pt"],
                 trophy["grade"], trophy["is_platinum"], trophy["source_url"]),
            )
            tr = await tx._one(
                "SELECT id FROM game_trophies WHERE game_id=? AND name_original=?",
                (game_id, trophy["name_original"]),
            )
            if not tr:
                raise RuntimeError(f"Falha ao recuperar troféu importado: {trophy['name_original']}")
            trophy_id = int(tr["id"])
            # Reimportação substitui relações antigas, sem apagar o progresso do usuário.
            await tx.conn.execute("DELETE FROM trophy_requirements WHERE trophy_id=?", (trophy_id,))
            for req in trophy["requirements"]:
                item_id = None
                if req["item_name_original"]:
                    matches = await tx._all(
                        "SELECT id FROM game_items WHERE game_id=? AND name_original=? ORDER BY id LIMIT 2",
                        (game_id, req["item_name_original"]),
                    )
                    if len(matches) != 1:
                        raise ValueError(
                            f"Requisito referencia o item '{req['item_name_original']}', "
                            "mas não existe uma correspondência única no catálogo. Corrija o nome "
                            "ou deixe item_name_original vazio para um requisito sem colecionável."
                        )
                    item_id = int(matches[0]["id"])
                await tx.conn.execute(
                    "INSERT INTO trophy_requirements(trophy_id,item_id,description_pt,quantity) VALUES (?,?,?,?)",
                    (trophy_id, item_id, req["description_pt"], req["quantity"]),
                )

    return {
        "game_id": game_id, "slug": slug, "name": nome, "status": "review",
        "items_received": len(prepared_items), "trophies_received": len(prepared_trophies),
        "sources_received": len(sources),
    }


async def salvar_aliases(db, game_id: int, aliases: list[str], source: str = "ai_research"):
    """Persiste aliases apenas quando não apontam para outro título canônico."""
    import unicodedata
    values = set()
    for alias in aliases or []:
        raw = " ".join(str(alias).split()).strip()[:120]
        if len(raw) < 2:
            continue
        norm = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode().casefold()
        norm = re.sub(r"[^a-z0-9]+", " ", norm).strip()
        if norm:
            values.add((raw, norm))
    async with db.transaction() as tx:
        for raw, norm in values:
            owners = await tx._all("SELECT DISTINCT game_id FROM game_aliases WHERE alias_norm=?", (norm,))
            if any(int(row["game_id"]) != int(game_id) for row in owners):
                continue
            await tx.conn.execute(
                "INSERT OR IGNORE INTO game_aliases(game_id,alias,alias_norm,source) VALUES (?,?,?,?)",
                (game_id, raw, norm, source),
            )


async def auditar_catalogo(db, game_id: int) -> dict:
    game = await buscar_jogo(db, game_id)
    if not game:
        raise ValueError("Jogo não encontrado.")
    items = await db._all("SELECT source_url,verified,name_pt FROM game_items WHERE game_id=?", (game_id,))
    trophies = await db._all("SELECT source_url,verified,name_pt FROM game_trophies WHERE game_id=?", (game_id,))
    try:
        sources = json.loads(game["sources_json"] or "[]")
    except (TypeError, json.JSONDecodeError):
        sources = []
    if not isinstance(sources, list):
        sources = []
    domains = set()
    for source in sources:
        try:
            from urllib.parse import urlparse
            host = urlparse(source.get("url", "")).netloc.lower()
            if host:
                domains.add(host.removeprefix("www."))
        except Exception:
            pass
    all_rows = list(items) + list(trophies)
    approved_urls = {str(s.get("url", "")).strip() for s in sources if isinstance(s, dict)}
    sourced = sum(1 for r in all_rows if (r["source_url"] or "") in approved_urls
                  and (r["source_url"] or "").startswith("https://"))
    verified = sum(1 for r in all_rows if r["verified"])
    return {
        "game": game, "items": len(items), "trophies": len(trophies),
        "sourced": sourced, "total": len(all_rows), "verified": verified,
        "domains": sorted(domains), "sources": sources,
        "ready": bool(items and trophies and len(domains) >= 2 and all_rows and sourced == len(all_rows) and verified == len(all_rows)),
    }


async def validar_catalogo(db, game_id: int) -> dict:
    """Marca os registros existentes como revisados numa única transação."""
    async with db.transaction() as tx:
        game = await tx._one("SELECT id,name FROM games_catalog WHERE id=?", (game_id,))
        if not game:
            raise ValueError("Jogo não encontrado.")
        items = await tx._one("SELECT COUNT(*) AS total FROM game_items WHERE game_id=?", (game_id,))
        trophies = await tx._one("SELECT COUNT(*) AS total FROM game_trophies WHERE game_id=?", (game_id,))
        if not int(items["total"] or 0) or not int(trophies["total"] or 0):
            raise ValueError("O catálogo precisa conter itens e troféus antes da validação.")
        await tx.conn.execute("UPDATE game_items SET verified=1 WHERE game_id=?", (game_id,))
        await tx.conn.execute("UPDATE game_trophies SET verified=1 WHERE game_id=?", (game_id,))
        return {"name": game["name"], "items": int(items["total"]), "trophies": int(trophies["total"])}


async def publicar_catalogo(db, game_id: int) -> dict:
    """Audita e publica sob BEGIN IMMEDIATE, evitando corrida com reimportações."""
    from urllib.parse import urlparse

    async with db.transaction() as tx:
        game = await tx._one("SELECT * FROM games_catalog WHERE id=?", (game_id,))
        if not game:
            raise ValueError("Jogo não encontrado.")
        items = await tx._all("SELECT source_url,verified FROM game_items WHERE game_id=?", (game_id,))
        trophies = await tx._all("SELECT source_url,verified FROM game_trophies WHERE game_id=?", (game_id,))
        try:
            sources = json.loads(game["sources_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            sources = []
        approved_urls = set()
        domains = set()
        for source in sources if isinstance(sources, list) else []:
            if not isinstance(source, dict):
                continue
            url = str(source.get("url", "")).strip()
            parsed = urlparse(url)
            if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
                approved_urls.add(url)
                domains.add(parsed.hostname.lower().removeprefix("www."))
        rows = list(items) + list(trophies)
        sourced = sum(1 for row in rows if str(row["source_url"] or "") in approved_urls)
        verified = sum(1 for row in rows if int(row["verified"] or 0) == 1)
        audit = {
            "name": game["name"], "items": len(items), "trophies": len(trophies),
            "total": len(rows), "sourced": sourced, "verified": verified,
            "domains": sorted(domains),
        }
        if not items or not trophies or len(domains) < 2 or not rows or sourced != len(rows) or verified != len(rows):
            raise ValueError(
                f"Auditoria reprovada: itens {len(items)}, troféus {len(trophies)}, "
                f"fontes válidas {sourced}/{len(rows)}, revisados {verified}/{len(rows)}, "
                f"domínios independentes {len(domains)} (mínimo 2)."
            )
        await tx.conn.execute(
            "UPDATE games_catalog SET status='ready', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (game_id,),
        )
        return audit


async def buscar_jogo_por_nome_ou_alias(db, consulta: str):
    """Resolve título canônico/alias já cadastrado antes de chamar o modelo."""
    import unicodedata
    raw = " ".join(str(consulta or "").split()).strip()
    norm = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode().casefold()
    norm = re.sub(r"[^a-z0-9]+", " ", norm).strip()
    if not norm:
        return None
    row = await db._one(
        """SELECT g.* FROM game_aliases a JOIN games_catalog g ON g.id=a.game_id
           WHERE a.alias_norm=? AND g.status='ready'
             AND (SELECT COUNT(DISTINCT x.game_id) FROM game_aliases x WHERE x.alias_norm=a.alias_norm)=1
           LIMIT 1""", (norm,)
    )
    if row:
        return row
    return await db._one(
        """SELECT * FROM games_catalog g WHERE g.status='ready'
           AND (lower(g.name)=lower(?) OR (lower(g.name_original)=lower(?) AND
             (SELECT COUNT(*) FROM games_catalog x WHERE x.status='ready'
              AND lower(x.name_original)=lower(?))=1)) LIMIT 1""",
        (raw, raw, raw),
    )
