"""API do hub do site: estatísticas do servidor, perfil, ranking, atividade e Nara.

Tudo aqui usa só dados locais (SQLite + cache do Discord + FAQ local da Nara),
sem chamar Gemini, para não gastar cota de API.
"""
from __future__ import annotations

import os
import re
import time

from aiohttp import web

import levels

_RANKINGS = {
    "xp": ("ranking_xp", "XP"),
    "platinas": ("ranking_platinas", "Platinas"),
    "zerados": ("ranking_zerados", "Zerados"),
}
_nara_ultimo: dict[int, float] = {}
TEMAS = {"cinzas", "fogueira", "abismo", "veneno", "sangue", "ametista"}
EMBLEMAS = ["⚔", "🛡", "🔥", "💀", "🐉", "🌙", "👑", "🗡", "🏹", "☠", "🦅", "⚜"]
_PADRAO = {"tema": "cinzas", "cor": "", "frase": "", "emblema": "⚔"}
_tabela_ok = False


async def _tabela(bot) -> None:
    global _tabela_ok
    if _tabela_ok:
        return
    await bot.db.conn.execute(
        "CREATE TABLE IF NOT EXISTS site_perfil ("
        "user_id INTEGER PRIMARY KEY, tema TEXT NOT NULL DEFAULT 'cinzas', "
        "cor TEXT NOT NULL DEFAULT '', frase TEXT NOT NULL DEFAULT '', "
        "emblema TEXT NOT NULL DEFAULT '⚔')")
    await bot.db.conn.commit()
    _tabela_ok = True


async def _prefs(bot, uid: int) -> dict:
    await _tabela(bot)
    r = await bot.db._one("SELECT tema, cor, frase, emblema FROM site_perfil WHERE user_id=?", (uid,))
    return dict(r) if r else dict(_PADRAO)


async def _prefs_map(bot, ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    await _tabela(bot)
    marcas = ",".join("?" * len(ids))
    rows = await bot.db._all(
        f"SELECT user_id, cor, emblema FROM site_perfil WHERE user_id IN ({marcas})", tuple(ids))
    return {int(r["user_id"]): dict(r) for r in rows}


def _guild(bot):
    import config
    try:
        gid = int(getattr(config, "GUILD_ID", 0) or 0)
    except (TypeError, ValueError):
        gid = 0
    return bot.get_guild(gid) if gid else None


def _nome(guild, user_id: int) -> str:
    membro = guild.get_member(int(user_id)) if guild else None
    return membro.display_name if membro else f"Jogador {str(user_id)[-4:]}"


def _avatar(guild, user_id: int) -> str | None:
    membro = guild.get_member(int(user_id)) if guild else None
    if membro is None:
        return None
    try:
        return str(membro.display_avatar.replace(size=64, format="png").url)
    except Exception:
        return None


async def _ranking(bot, guild, tipo: str, limite: int) -> list[dict]:
    metodo, _ = _RANKINGS[tipo]
    linhas = await getattr(bot.db, metodo)(limite)
    pm = await _prefs_map(bot, [int(r["user_id"]) for r in linhas])
    return [
        {
            "pos": i, "id": str(r["user_id"]), "name": _nome(guild, r["user_id"]),
            "avatar": _avatar(guild, r["user_id"]), "valor": int(r["valor"] or 0),
            "emblema": pm.get(int(r["user_id"]), {}).get("emblema") or "",
            "cor": pm.get(int(r["user_id"]), {}).get("cor") or "",
        }
        for i, r in enumerate(linhas, 1)
    ]


async def _atividade(bot, guild, limite: int = 10) -> list[dict]:
    plat = await bot.db._all(
        "SELECT user_id, game, created_at AS quando FROM platinas "
        "WHERE status='approved' ORDER BY id DESC LIMIT ?", (limite,))
    zer = await bot.db._all(
        "SELECT user_id, game, COALESCE(approved_at, finished_at) AS quando FROM zerados "
        "WHERE status='approved' AND source_platina_id IS NULL ORDER BY id DESC LIMIT ?", (limite,))
    itens = [("platina", r) for r in plat] + [("zerado", r) for r in zer]
    itens.sort(key=lambda t: str(t[1]["quando"] or ""), reverse=True)
    return [
        {"tipo": t, "user": _nome(guild, r["user_id"]), "game": r["game"], "quando": str(r["quando"] or "")}
        for t, r in itens[:limite]
    ]


async def _perfil(bot, user_id: int) -> dict:
    r = await bot.db.resumo_painel_nara(user_id)
    xp = r["xp"]
    nivel = levels.nivel_por_xp(xp)
    base, prox = levels.xp_para_nivel(nivel), levels.xp_para_nivel(nivel + 1)
    r.update({
        "nivel": nivel, "patente": levels.patente_por_nivel(nivel),
        "xp_nivel_atual": xp - base, "xp_nivel_total": prox - base,
        "posicao": await bot.db.posicao_xp(xp),
    })
    return r


def registrar_rotas(bot, app: web.Application) -> None:
    def auth(request):
        return bot._api_user_id(request)

    async def overview(request: web.Request) -> web.Response:
        guild = _guild(bot)
        if guild is None:
            return web.json_response({"error": "Servidor indisponível."}, status=503)
        agora = time.time()
        no_site = sum(1 for t in bot._web_presence.values() if agora - t <= 75)
        humanos = [m for m in guild.members if not m.bot]
        data = {
            "server": {
                "name": guild.name,
                "icon": str(guild.icon.replace(size=128).url) if guild.icon else None,
                "members": len(humanos),
                "online": sum(1 for m in humanos if str(m.status) != "offline"),
                "on_site": no_site,
                "invite": os.getenv("DISCORD_INVITE_URL", "").strip() or None,
            },
            "authenticated": False,
        }
        uid = auth(request)
        if uid is not None:
            data["authenticated"] = True
            data["me"] = await _perfil(bot, uid)
            data["me"]["name"] = _nome(guild, uid)
            data["me"]["avatar"] = _avatar(guild, uid)
            data["me"]["prefs"] = await _prefs(bot, uid)
            data["top"] = {k: await _ranking(bot, guild, k, 5) for k in _RANKINGS}
            data["recent"] = await _atividade(bot, guild)
        return web.json_response(data, headers={"Cache-Control": "no-store"})

    async def ranking(request: web.Request) -> web.Response:
        if auth(request) is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        tipo = request.query.get("tipo", "xp")
        if tipo not in _RANKINGS:
            return web.json_response({"error": "Ranking inválido."}, status=400)
        try:
            limite = max(1, min(50, int(request.query.get("limite", "20"))))
        except ValueError:
            limite = 20
        return web.json_response({
            "tipo": tipo, "label": _RANKINGS[tipo][1],
            "rows": await _ranking(bot, _guild(bot), tipo, limite),
        }, headers={"Cache-Control": "no-store"})

    async def nara(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not bot._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        agora = time.time()
        if agora - _nara_ultimo.get(uid, 0) < 1.5:
            return web.json_response({"error": "Calma, guerreiro. Uma pergunta por vez."}, status=429)
        _nara_ultimo[uid] = agora
        try:
            corpo = await request.json()
        except Exception:
            return web.json_response({"error": "Requisição inválida."}, status=400)
        pergunta = str(corpo.get("message", "")).strip()[:300]
        if not pergunta:
            return web.json_response({"error": "Escreva algo."}, status=400)
        from nara import faq
        intent, _score = faq.classificar(pergunta)
        resposta = faq.resposta_pronta(intent) if intent else None
        if not resposta:
            exemplos = {i.get("intent"): (i.get("examples") or [""])[0]
                        for i in faq.carregar_base()["intents"]}
            sugestoes = [exemplos.get(it, "") for it, _a, _s in faq.buscar_relacionadas(pergunta, 3)]
            sugestoes = [q for q in sugestoes if q]
            return web.json_response({
                "reply": "Não captei essa. Para conversa livre, me chame no Discord. Talvez você quis dizer:",
                "suggestions": sugestoes,
            })
        return web.json_response({"reply": resposta, "suggestions": []})

    async def prefs_get(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        return web.json_response(await _prefs(bot, uid), headers={"Cache-Control": "no-store"})

    async def prefs_set(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not bot._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            c = await request.json()
        except Exception:
            return web.json_response({"error": "Requisição inválida."}, status=400)
        tema = str(c.get("tema", "cinzas"))
        cor = str(c.get("cor", "") or "")
        emblema = str(c.get("emblema", "⚔"))
        frase = re.sub(r"[\x00-\x1f\x7f]", " ", str(c.get("frase", "") or "")).strip()[:80]
        if tema not in TEMAS or emblema not in EMBLEMAS or (cor and not re.fullmatch(r"#[0-9a-fA-F]{6}", cor)):
            return web.json_response({"error": "Valores inválidos."}, status=400)
        await _tabela(bot)
        await bot.db.conn.execute(
            "INSERT INTO site_perfil(user_id, tema, cor, frase, emblema) VALUES (?,?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET tema=excluded.tema, cor=excluded.cor, "
            "frase=excluded.frase, emblema=excluded.emblema", (uid, tema, cor, frase, emblema))
        await bot.db.conn.commit()
        return web.json_response({"ok": True, "tema": tema, "cor": cor, "frase": frase, "emblema": emblema})

    app.router.add_get("/api/hub/prefs", prefs_get)
    app.router.add_post("/api/hub/prefs", prefs_set)
    app.router.add_get("/api/hub/overview", overview)
    app.router.add_get("/api/hub/ranking", ranking)
    app.router.add_post("/api/hub/nara", nara)
