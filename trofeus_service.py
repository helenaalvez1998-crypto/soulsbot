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
    if not reqs:
        row = await db._one(
            "SELECT completed FROM user_trophy_progress WHERE user_id=? AND trophy_id=?",
            (user_id, trophy_id),
        )
        return (1 if row and row["completed"] else 0), 1, []
    total = len(reqs)
    feitos = sum(1 for r in reqs if r["item_id"] is not None and r["obtained"])
    return feitos, total, reqs


async def importar_catalogo(db, payload: dict, publicar: bool = False):
    """Importa JSON validado. Não faz scraping; recebe dados de fontes autorizadas."""
    if not isinstance(payload, dict):
        raise ValueError("O arquivo precisa conter um objeto JSON.")
    nome = str(payload.get("name", "")).strip()
    if not nome:
        raise ValueError("Campo obrigatório ausente: name.")
    slug = _slug(str(payload.get("slug") or nome))
    itens = payload.get("items", [])
    trofeus = payload.get("trophies", [])
    if not isinstance(itens, list) or not isinstance(trofeus, list):
        raise ValueError("'items' e 'trophies' precisam ser listas.")
    if len(itens) > 10000 or len(trofeus) > 2000:
        raise ValueError("O catálogo excede o limite de segurança de importação.")
    if publicar and (not itens or not trofeus):
        raise ValueError("Para publicar, o catálogo precisa ter itens e troféus cadastrados.")
    status = "ready" if publicar else "review"
    sources = payload.get("sources", [])
    platforms = payload.get("platforms", [])
    cur = await db.conn.execute(
        """INSERT INTO games_catalog(slug,name,name_original,status,platforms_json,cover_url,sources_json,updated_at)
           VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
           ON CONFLICT(slug) DO UPDATE SET
             name=excluded.name, name_original=excluded.name_original, status=excluded.status,
             platforms_json=excluded.platforms_json, cover_url=excluded.cover_url,
             sources_json=excluded.sources_json, updated_at=CURRENT_TIMESTAMP""",
        (slug, nome, str(payload.get("name_original", "")), status,
         json.dumps(platforms, ensure_ascii=False), str(payload.get("cover_url", "")),
         json.dumps(sources, ensure_ascii=False)),
    )
    await db.conn.commit()
    game = await db._one("SELECT id FROM games_catalog WHERE slug=?", (slug,))
    game_id = int(game["id"])

    # Importação incremental: atualiza os mesmos registros, sem apagar progresso do usuário.
    for item in itens:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "")).strip()
        name_pt = str(item.get("name_pt") or item.get("name") or "").strip()
        name_original = str(item.get("name_original") or item.get("name_en") or name_pt).strip()
        if not category or not name_pt:
            continue
        await db.conn.execute(
            """INSERT INTO game_items(
                 game_id,category,name_pt,name_original,description_pt,location_pt,
                 acquisition_pt,dlc,ng_cycle,missable,source_url,verified,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(game_id,category,name_original) DO UPDATE SET
                 name_pt=excluded.name_pt, description_pt=excluded.description_pt,
                 location_pt=excluded.location_pt, acquisition_pt=excluded.acquisition_pt,
                 dlc=excluded.dlc, ng_cycle=excluded.ng_cycle, missable=excluded.missable,
                 source_url=excluded.source_url, verified=excluded.verified,
                 updated_at=CURRENT_TIMESTAMP""",
            (game_id, category, name_pt, name_original,
             str(item.get("description_pt", "")), str(item.get("location_pt", "")),
             str(item.get("acquisition_pt", "")), str(item.get("dlc", "")),
             str(item.get("ng_cycle", "")), 1 if item.get("missable") else 0,
             str(item.get("source_url", "")), 1 if item.get("verified") else 0),
        )

    for trophy in trofeus:
        if not isinstance(trophy, dict):
            continue
        name_pt = str(trophy.get("name_pt") or trophy.get("name") or "").strip()
        name_original = str(trophy.get("name_original") or trophy.get("name_en") or name_pt).strip()
        if not name_pt:
            continue
        await db.conn.execute(
            """INSERT INTO game_trophies(
                 game_id,name_pt,name_original,description_pt,grade,is_platinum,source_url,verified,updated_at)
               VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(game_id,name_original) DO UPDATE SET
                 name_pt=excluded.name_pt, description_pt=excluded.description_pt,
                 grade=excluded.grade, is_platinum=excluded.is_platinum,
                 source_url=excluded.source_url, verified=excluded.verified,
                 updated_at=CURRENT_TIMESTAMP""",
            (game_id, name_pt, name_original, str(trophy.get("description_pt", "")),
             str(trophy.get("grade", "")), 1 if trophy.get("is_platinum") else 0,
             str(trophy.get("source_url", "")), 1 if trophy.get("verified") else 0),
        )

    # Relaciona requisitos por slug/nome original do item, evitando duplicar itens.
    for trophy in trofeus:
        if not isinstance(trophy, dict):
            continue
        trophy_original = str(trophy.get("name_original") or trophy.get("name_en") or trophy.get("name_pt") or trophy.get("name") or "").strip()
        tr = await db._one(
            "SELECT id FROM game_trophies WHERE game_id=? AND name_original=?",
            (game_id, trophy_original),
        )
        if not tr:
            continue
        for req in trophy.get("requirements", []) if isinstance(trophy.get("requirements", []), list) else []:
            if not isinstance(req, dict):
                continue
            item_original = str(req.get("item_name_original") or req.get("item_name_en") or "").strip()
            item_id = None
            if item_original:
                ir = await db._one(
                    "SELECT id FROM game_items WHERE game_id=? AND name_original=? LIMIT 1",
                    (game_id, item_original),
                )
                item_id = int(ir["id"]) if ir else None
            await db.conn.execute(
                """INSERT INTO trophy_requirements(trophy_id,item_id,description_pt,quantity)
                   SELECT ?,?,?,? WHERE NOT EXISTS (
                     SELECT 1 FROM trophy_requirements WHERE trophy_id=? AND
                     COALESCE(item_id,0)=COALESCE(?,0) AND description_pt=?
                   )""",
                (int(tr["id"]), item_id, str(req.get("description_pt", "")),
                 max(1, int(req.get("quantity", 1))), int(tr["id"]), item_id,
                 str(req.get("description_pt", ""))),
            )
    await db.conn.commit()
    return {
        "game_id": game_id, "slug": slug, "name": nome, "status": status,
        "items_received": len(itens), "trophies_received": len(trofeus),
    }
