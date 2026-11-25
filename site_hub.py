"""API do hub do site: estatísticas do servidor, perfil, ranking, atividade e Nara.

Tudo aqui usa só dados locais (SQLite + cache do Discord + FAQ local da Nara),
sem chamar Gemini, para não gastar cota de API.
"""
from __future__ import annotations

import os
import re
import time
import json
import hashlib
import secrets
from pathlib import Path

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
_transmutacao_last_exec: dict[int, float] = {}


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

    async def linhagens_page(request: web.Request) -> web.Response:
        page = Path(__file__).resolve().parent / "site" / "linhagens.html"
        if not page.is_file():
            return web.Response(text="Página de Linhagens indisponível.", status=503)
        return web.FileResponse(page)

    async def linhagens_list(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        return web.json_response({"recipes": await bot.db.coliseu_listar_receitas_linhagem(uid)},
                                 headers={"Cache-Control": "no-store"})

    async def linhagens_execute(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not bot._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            body = await request.json()
            recipe_id = str(body.get("recipe_id", ""))
            exemplar_ids = [int(x) for x in body.get("exemplar_ids", [])]
        except (ValueError, TypeError, AttributeError):
            return web.json_response({"error": "Dados inválidos."}, status=400)
        result = await bot.db.coliseu_executar_receita_linhagem(uid, recipe_id, exemplar_ids)
        return web.json_response(result, headers={"Cache-Control": "no-store"})

    async def rituais_page(request: web.Request) -> web.Response:
        page = Path(__file__).resolve().parent / "site" / "rituais_ancestrais.html"
        if not page.is_file():
            return web.Response(text="Página de Rituais Ancestrais indisponível.", status=503)
        return web.FileResponse(page)

    async def rituais_list(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        return web.json_response({"recipes": await bot.db.coliseu_listar_rituais_ancestrais(uid)},
                                 headers={"Cache-Control": "no-store"})

    async def rituais_execute(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not bot._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            body = await request.json()
            recipe_id = str(body.get("recipe_id", ""))
            exemplar_ids = [int(x) for x in body.get("exemplar_ids", [])]
        except (ValueError, TypeError, AttributeError):
            return web.json_response({"error": "Dados inválidos."}, status=400)
        result = await bot.db.coliseu_executar_ritual_ancestral(uid, recipe_id, exemplar_ids)
        return web.json_response(result, headers={"Cache-Control": "no-store"})

    async def transmutacao_page(request: web.Request) -> web.Response:
        page = Path(__file__).resolve().parent / "site" / "transmutacao.html"
        if not page.is_file():
            return web.Response(text="Laboratório de Transmutação indisponível.", status=503)
        return web.FileResponse(page)

    async def transmutacao_list(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        rows = await bot.db._all(
            """SELECT e.id,e.card_id,e.rarity,e.power,e.source,e.origin_type,
                      e.is_sacrificable,e.obtained_at
               FROM cartas_exemplares e WHERE e.user_id=?
               ORDER BY e.obtained_at DESC,e.id DESC""", (int(uid),))
        from sistemas.cartas import get_carta
        from sistemas.afinidades import classificar_carta, validar_ingredientes
        from sistemas.transmutacao import _snapshot_ingrediente
        deck = await bot.db._one(
            "SELECT exemplar_ids_json FROM cartas_gwent_decks WHERE user_id=?", (int(uid),))
        try:
            equipped = {int(x) for x in json.loads(deck["exemplar_ids_json"] or "[]")} if deck else set()
        except (TypeError, ValueError, json.JSONDecodeError):
            equipped = set()
        items = []
        for row in rows:
            item = dict(row)
            card = get_carta(str(item["card_id"]))
            if card is None:
                continue
            snap = _snapshot_ingrediente(item)
            classification = classificar_carta(snap)
            eligible = (item.get("is_sacrificable", 1) not in (0, False)
                        and str(item.get("origin_type") or "").casefold() != "transmutacao"
                        and classification["categoria"].casefold() not in ("especial", "líder", "lider")
                        and classification["raridade"] in ("Comum", "Rara", "Épica", "Lendária", "Mítica")
                        and int(item["id"]) not in equipped)
            if eligible:
                items.append({"id": int(item["id"]), "card_id": str(item["card_id"]),
                              "name": str(getattr(card, "nome", None) or item["card_id"]),
                              "rarity": str(item["rarity"]), "power": int(item["power"] or 0),
                              "faction": classification["faccao"], "eligible": True})
        materials = await bot.db.coliseu_listar_materiais_transmutacao(uid)
        history = await bot.db._all(
            """SELECT tx_key,status,ingredient_ids_json,probability,generated_card_id,
                      failure_reason,created_at,completed_at FROM cartas_transmutacoes
               WHERE owner_id=? ORDER BY id DESC LIMIT 20""", (int(uid),))
        history_items = []
        for raw in history:
            h = dict(raw)
            try:
                h["ingredient_ids"] = json.loads(h.pop("ingredient_ids_json") or "[]")
            except (TypeError, ValueError, json.JSONDecodeError):
                h["ingredient_ids"] = []
            history_items.append(h)
        from sistemas.catalisadores import CATALISADORES
        discovered = await bot.db.coliseu_listar_receitas_ocultas(uid)
        return web.json_response({"items": items, "materials": [dict(x) for x in materials],
                                  "catalysts": CATALISADORES, "discovered_recipes": [dict(x) for x in discovered],
                                  "history": history_items},
                                 headers={"Cache-Control": "no-store"})

    async def transmutacao_preview(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not bot._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            body = await request.json()
            ids = [int(x) for x in body.get("exemplar_ids", [])]
            catalyst_key = str(body.get("catalyst_key") or "") or None
        except (ValueError, TypeError, AttributeError):
            return web.json_response({"error": "Dados inválidos."}, status=400)
        if not 3 <= len(ids) <= 5 or len(set(ids)) != len(ids) or any(x <= 0 for x in ids):
            return web.json_response({"error": "Selecione de 3 a 5 exemplares distintos."}, status=400)
        marks = ",".join("?" for _ in ids)
        rows = await bot.db._all(
            f"""SELECT id,user_id,card_id,rarity,power,source,origin_type,origin_card_id,is_sacrificable
                FROM cartas_exemplares WHERE user_id=? AND id IN ({marks})""", (int(uid), *ids))
        if len(rows) != len(ids):
            return web.json_response({"error": "Um ou mais exemplares não pertencem à sua coleção."}, status=400)
        by_id = {int(x["id"]): x for x in rows}
        rows = [by_id[x] for x in ids]
        deck = await bot.db._one("SELECT exemplar_ids_json FROM cartas_gwent_decks WHERE user_id=?", (int(uid),))
        try:
            equipped = {int(x) for x in json.loads(deck["exemplar_ids_json"] or "[]")} if deck else set()
        except (TypeError, ValueError, json.JSONDecodeError):
            return web.json_response({"error": "Deck ativo inválido; operação bloqueada."}, status=409)
        if equipped.intersection(ids):
            return web.json_response({"error": "Remova do deck ativo os exemplares selecionados."}, status=409)
        from sistemas.transmutacao import _snapshot_ingrediente
        from sistemas.afinidades import analisar_compatibilidade, classificar_carta, validar_ingredientes
        from sistemas.gerador_cartas import gerar_carta_procedural, validar_definicao_gerada
        from sistemas.economia_transmutacao import calcular_orcamento, validar_saldo
        ingredients = [_snapshot_ingrediente(x) for x in rows]
        valid, reason = validar_ingredientes(ingredients)
        if not valid:
            return web.json_response({"error": reason}, status=400)
        compatibility = analisar_compatibilidade(ingredients)
        stable = hashlib.sha256((str(uid) + ":" + ",".join(map(str, sorted(ids)))).encode()).hexdigest()
        proposal = gerar_carta_procedural(ingredients, seed=stable, generated_id="preview_" + stable[:20])
        if not proposal.get("valido"):
            return web.json_response({"error": proposal.get("motivo", "Não foi possível gerar prévia.")}, status=422)
        definition = proposal["definition"]
        ok, errors = validar_definicao_gerada(definition)
        if not ok:
            return web.json_response({"error": "Prévia reprovada: " + "; ".join(errors)}, status=422)
        from collections import Counter
        factions = Counter(classificar_carta(x)["faccao"] for x in ingredients)
        same_faction = bool(factions and factions.most_common(1)[0][1] == len(ingredients))
        from sistemas.catalisadores import obter_efeito, validar_afinidade
        try:
            catalyst_effect = obter_efeito(catalyst_key)
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        all_affinities = sorted({a for item in ingredients for a in classificar_carta(item)["afinidades"]})
        if not validar_afinidade(catalyst_effect, all_affinities):
            return web.json_response({"error": "Catalisador incompatível com as afinidades selecionadas."}, status=400)
        quote = calcular_orcamento(definition["raridade"], int(compatibility["score"]), same_faction, False, catalyst_key=catalyst_key)
        balances_rows = await bot.db.coliseu_listar_materiais_transmutacao(uid)
        balances = {str(x["material_key"]): int(x["quantidade"]) for x in balances_rows}
        missing = validar_saldo(quote.costs, balances)
        return web.json_response({
            "preview": {"name": definition["nome"], "rarity": definition["raridade"],
                        "power": definition["poder"], "faction": definition["faccao"],
                        "function": definition["funcao_tatica"], "affinities": definition["afinidades"],
                        "ability": definition.get("habilidade") or None,
                        "description": definition["descricao"]},
            "compatibility": compatibility, "quote": quote.__dict__,
            "balances": balances, "missing": missing,
            "notice": "Estimativa determinística. Para os mesmos ingredientes, raridade, custo e chance são estáveis; nome, poder e habilidade podem variar na geração final."
        }, headers={"Cache-Control": "no-store"})

    async def transmutacao_execute(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not bot._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            body = await request.json()
            ids = [int(x) for x in body.get("exemplar_ids", [])]
            tx_key = str(body.get("tx_key", ""))
            catalyst_key = str(body.get("catalyst_key") or "") or None
            confirmed = body.get("confirmed") is True
        except (ValueError, TypeError, AttributeError):
            return web.json_response({"error": "Dados inválidos."}, status=400)
        if not confirmed:
            return web.json_response({"error": "Confirmação explícita obrigatória."}, status=400)
        if not re.fullmatch(r"[a-f0-9]{32,64}", tx_key):
            return web.json_response({"error": "Chave de operação inválida."}, status=400)
        now = time.monotonic()
        previous = _transmutacao_last_exec.get(int(uid), 0.0)
        if now - previous < 5.0:
            return web.json_response({"error": "Aguarde alguns segundos antes de iniciar outra tentativa."}, status=429)
        if not 3 <= len(ids) <= 5 or len(set(ids)) != len(ids) or any(x <= 0 for x in ids):
            return web.json_response({"error": "Selecione de 3 a 5 exemplares distintos."}, status=400)
        _transmutacao_last_exec[int(uid)] = now
        # Escopo por proprietário: uma chave escolhida por outra conta não colide com esta.
        scoped_tx_key = hashlib.sha256(f"{int(uid)}:{tx_key}".encode()).hexdigest()
        result = await bot.db.coliseu_executar_transmutacao(int(uid), ids, catalyst_active=False, catalyst_key=catalyst_key, tx_key=scoped_tx_key)
        return web.json_response(result, headers={"Cache-Control": "no-store"})

    async def transmutacao_discover(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not bot._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            body = await request.json()
            ids = [int(x) for x in body.get("exemplar_ids", [])]
        except (ValueError, TypeError, AttributeError):
            return web.json_response({"error": "Dados inválidos."}, status=400)
        if not 3 <= len(ids) <= 5 or len(set(ids)) != len(ids) or any(x <= 0 for x in ids):
            return web.json_response({"error": "Selecione de 3 a 5 exemplares distintos."}, status=400)
        marks = ",".join("?" for _ in ids)
        rows = await bot.db._all(
            f"SELECT id,user_id,card_id,rarity,power,source,origin_type,origin_card_id,is_sacrificable FROM cartas_exemplares WHERE user_id=? AND id IN ({marks})",
            (int(uid), *ids))
        if len(rows) != len(ids):
            return web.json_response({"error": "Ingredientes não pertencem à sua coleção."}, status=403)
        deck = await bot.db._one("SELECT exemplar_ids_json FROM cartas_gwent_decks WHERE user_id=?", (int(uid),))
        try:
            equipped = {int(x) for x in json.loads(deck["exemplar_ids_json"] or "[]")} if deck else set()
        except (TypeError, ValueError, json.JSONDecodeError):
            return web.json_response({"error": "Deck ativo inválido; operação bloqueada."}, status=409)
        if equipped.intersection(ids):
            return web.json_response({"error": "Remova os exemplares do deck ativo antes de pesquisar."}, status=409)
        from sistemas.transmutacao import _snapshot_ingrediente
        from sistemas.receitas_ocultas import avaliar_descoberta, descobrir_receitas
        by_id = {int(x["id"]): x for x in rows}
        ingredients = [_snapshot_ingrediente(by_id[x]) for x in ids]
        result = avaliar_descoberta(ingredients)
        if not result["valid"]:
            return web.json_response({"error": result["reason"]}, status=400)
        found = descobrir_receitas(ingredients)
        registered = []
        for recipe in found:
            saved = await bot.db.coliseu_registrar_descoberta_receita(uid, recipe["recipe_id"], result["signature"])
            registered.append({"recipe_id": recipe["recipe_id"], "name": recipe["nome"],
                               "description": recipe["descricao"], "rarity": recipe["raridade_resultado"],
                               "status": saved["status"]})
        return web.json_response({"valid": True, "discoveries": registered,
                                  "message": "Pesquisa concluída sem consumir ingredientes." if not found else "Receita oculta descoberta e registrada para esta conta."},
                                 headers={"Cache-Control": "no-store"})

    async def generated_cards(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        from sistemas.transmutacao_catalogo import filtrar_catalogo, resumo_catalogo
        rows = await bot.db.coliseu_listar_cartas_geradas(uid, 200)
        result = filtrar_catalogo(
            rows, query=request.query.get("q", ""),
            faction=request.query.get("faction", ""),
            rarity=request.query.get("rarity", ""),
            affinity=request.query.get("affinity", ""),
            role=request.query.get("role", ""),
            page=int(request.query.get("page", "1")),
            page_size=int(request.query.get("page_size", "24")),
        )
        result["summary"] = resumo_catalogo(rows)
        return web.json_response(result, headers={"Cache-Control": "no-store"})

    async def generated_cards_page(request: web.Request) -> web.Response:
        page = Path(__file__).resolve().parent / "site" / "cartas-geradas.html"
        if not page.is_file():
            return web.Response(text="Catálogo pessoal indisponível.", status=503)
        return web.FileResponse(page)

    async def transmutacao_balance_report(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        # O relatório usa dados agregados globais; não expõe definições ou proprietários.
        rows = await bot.db._all(
            """SELECT card_id,name,rarity,faction,power,definition_json,art_path,art_status
               FROM cartas_geradas ORDER BY id DESC LIMIT 5000"""
        )
        from sistemas.transmutacao_balanceamento import analisar_balanceamento
        return web.json_response(analisar_balanceamento([dict(x) for x in rows]),
                                 headers={"Cache-Control": "no-store"})

    async def generated_card_detail(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        row = await bot.db.coliseu_obter_carta_gerada(uid, request.match_info["card_id"])
        if not row:
            return web.json_response({"error": "Carta não encontrada."}, status=404)
        data = dict(row)
        try:
            data["definition"] = json.loads(data.pop("definition_json") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            data["definition"] = {}
        return web.json_response(data, headers={"Cache-Control": "no-store"})

    async def atelier_page(request: web.Request) -> web.Response:
        page = Path(__file__).resolve().parent / "site" / "atelie-arte.html"
        if not page.is_file():
            return web.Response(text="Ateliê de Arte indisponível.", status=503)
        return web.FileResponse(page)

    async def generated_card_prompt(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        card_id = str(request.match_info["card_id"])
        row = await bot.db.coliseu_obter_carta_gerada(uid, card_id)
        if not row:
            return web.json_response({"error": "Carta não encontrada para esta conta."}, status=404)
        try:
            definition = json.loads(row["definition_json"] or "{}")
            from sistemas.prompt_arte_criador import gerar_prompt_arte
            result = gerar_prompt_arte(definition, card_id=card_id)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return web.json_response({"error": str(exc)}, status=422)
        return web.json_response(result, headers={"Cache-Control": "no-store"})

    async def generated_card_art_upload(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not bot._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        card_id = str(request.match_info["card_id"])
        row = await bot.db.coliseu_obter_carta_gerada(uid, card_id)
        if not row:
            return web.json_response({"error": "Carta não encontrada para esta conta."}, status=404)
        replace_existing = request.query.get("replace") == "1"
        if str(row["art_status"] or "") in {"validated", "stored"} and not replace_existing:
            return web.json_response({"error": "Esta carta já possui arte. Use a opção explícita de substituir."}, status=409)
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field is None or field.name != "image":
                return web.json_response({"error": "Envie o arquivo no campo image."}, status=400)
            chunks = []
            total_bytes = 0
            while True:
                chunk = await field.read_chunk(size=64 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > 12 * 1024 * 1024:
                    return web.json_response({"error": "Arquivo acima de 12 MB."}, status=413)
                chunks.append(chunk)
            raw = b"".join(chunks)
            if not raw:
                return web.json_response({"error": "Arquivo vazio."}, status=400)
            import hashlib
            from config import get_data_dir
            from sistemas.arte_upload_criador import normalizar_upload_arte
            try:
                normalized = normalizar_upload_arte(raw)
            except ValueError as exc:
                return web.json_response({"error": str(exc)}, status=422)
            image_bytes = normalized["image_bytes"]
            width, height = normalized["width"], normalized["height"]
            fmt = normalized["source_format"]
            digest = hashlib.sha256(image_bytes).hexdigest()
            base = Path(get_data_dir()) / "cartas_geradas_uploads" / str(int(uid)) / card_id
            base.mkdir(parents=True, exist_ok=True)
            target = base / f"{digest}.png"
            if not target.exists():
                temp = base / f".{digest}.tmp"
                temp.write_bytes(image_bytes)
                try:
                    os.link(temp, target)
                except FileExistsError:
                    pass
                finally:
                    temp.unlink(missing_ok=True)
            definition = json.loads(row["definition_json"] or "{}")
            manifest = {
                "version": "v48", "card_id": card_id, "owner_id": int(uid),
                "sha256": digest, "width": width, "height": height,
                "format": "PNG", "source_format": fmt,
                "source": "creator_upload", "status": "validated",
                "faction": str(definition.get("faccao") or row["faction"]),
                "rarity": str(definition.get("raridade") or row["rarity"]),
            }
            manifest_path = target.with_suffix(".manifest.json")
            manifest_tmp = manifest_path.with_suffix(".manifest.tmp")
            manifest_tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                os.replace(manifest_tmp, manifest_path)
            finally:
                manifest_tmp.unlink(missing_ok=True)
            result = await bot.db.coliseu_registrar_arte_carta_gerada(
                int(uid), card_id, str(target), digest, width, height,
                replace_existing=replace_existing,
            )
            if result.get("status") != "arte_registrada":
                return web.json_response({"error": "Não foi possível registrar a arte.", "detail": result}, status=409)
            return web.json_response({"status": "arte_registrada", "card_id": card_id,
                                      "width": width, "height": height,
                                      "sha256": digest, "art_url": f"/api/gwent/cartas-geradas/{card_id}/arte"},
                                     headers={"Cache-Control": "no-store"})
        except Exception:
            # Erro técnico não deve ser convertido em rejeição de conteúdo nem consumir recursos.
            return web.json_response({"error": "Falha técnica ao processar a imagem. Nenhum material foi consumido."}, status=500)

    async def generated_card_art(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        row = await bot.db.coliseu_obter_carta_gerada(uid, str(request.match_info["card_id"]))
        if not row or not row["art_path"]:
            return web.json_response({"error": "Arte não encontrada."}, status=404)
        path = Path(str(row["art_path"])).resolve()
        # Só serve arquivos dentro do diretório privado do proprietário.
        try:
            from config import get_data_dir
            allowed = (Path(get_data_dir()) / "cartas_geradas_uploads" / str(int(uid))).resolve()
            path.relative_to(allowed)
            if not path.is_file():
                raise FileNotFoundError
        except (ValueError, OSError, FileNotFoundError):
            return web.json_response({"error": "Arquivo de arte indisponível."}, status=404)
        return web.FileResponse(path, headers={"Cache-Control": "private, no-store"})

    async def forja_page(request: web.Request) -> web.Response:
        page = Path(__file__).resolve().parent / "site" / "forja.html"
        if not page.is_file():
            return web.Response(text="Página da Forja indisponível.", status=503)
        return web.FileResponse(page)

    async def forja_list(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        rows = await bot.db.coliseu_listar_exemplares(uid)
        from sistemas.cartas import (
            CUSTO_APRIMORAMENTO_ALMAS, BONUS_EVOLUCAO_FRAGMENTOS,
            RARIDADES, get_carta, faixa_poder_exemplar,
        )
        from sistemas.gwent import RARITY_EFFECT_BUDGET
        items = []
        for row in rows:
            card = get_carta(str(row["card_id"]))
            if card is None or str(card.categoria).casefold() == "especial":
                continue
            rarity = str(row["rarity"])
            power = int(row["power"] or 0)
            try:
                _minimum, maximum = faixa_poder_exemplar(card, rarity)
            except (ValueError, KeyError):
                continue
            idx = RARIDADES.index(rarity) if rarity in RARIDADES else -1
            next_rarity = RARIDADES[idx + 1] if 0 <= idx < len(RARIDADES) - 1 else None
            if next_rarity in ("Primordial", "Singular"):
                next_rarity = None
            items.append({
                "id": int(row["id"]), "card_id": str(row["card_id"]),
                "name": str(getattr(card, "nome", None) or getattr(card, "name", None) or row["card_id"]),
                "rarity": rarity, "power": power, "max_power": int(maximum),
                "potencia_raridade": int(RARITY_EFFECT_BUDGET.get(rarity, 0)),
                "lap_cost": CUSTO_APRIMORAMENTO_ALMAS.get(rarity),
                "next_rarity": next_rarity,
                "evo_cost": BONUS_EVOLUCAO_FRAGMENTOS.get(rarity) if next_rarity else None,
            })
        return web.json_response({"items": items}, headers={"Cache-Control": "no-store"})

    async def forja_action(request: web.Request) -> web.Response:
        uid = auth(request)
        if uid is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not bot._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            body = await request.json()
            exemplar_id = int(body.get("exemplar_id"))
            action = str(body.get("action", ""))
        except (ValueError, TypeError, AttributeError):
            return web.json_response({"error": "Dados inválidos."}, status=400)
        if exemplar_id <= 0 or action not in ("lapidar", "ascender"):
            return web.json_response({"error": "Operação inválida."}, status=400)
        if action == "lapidar":
            result = await bot.db.coliseu_aprimorar_exemplar(uid, exemplar_id)
        else:
            result = await bot.db.coliseu_evoluir_exemplar(uid, exemplar_id)
        return web.json_response(result, headers={"Cache-Control": "no-store"})

    app.router.add_get("/api/hub/prefs", prefs_get)
    app.router.add_post("/api/hub/prefs", prefs_set)
    app.router.add_get("/api/hub/overview", overview)
    app.router.add_get("/api/hub/ranking", ranking)
    app.router.add_post("/api/hub/nara", nara)

    app.router.add_get("/forja", forja_page)
    app.router.add_get("/transmutacao", transmutacao_page)
    app.router.add_get("/api/gwent/transmutacao", transmutacao_list)
    app.router.add_post("/api/gwent/transmutacao/preview", transmutacao_preview)
    app.router.add_post("/api/gwent/transmutacao/execute", transmutacao_execute)
    app.router.add_post("/api/gwent/transmutacao/discover", transmutacao_discover)
    app.router.add_get("/cartas-geradas", generated_cards_page)
    app.router.add_get("/api/gwent/transmutacao/balanceamento", transmutacao_balance_report)
    app.router.add_get("/api/gwent/cartas-geradas", generated_cards)
    app.router.add_get("/api/gwent/cartas-geradas/{card_id}", generated_card_detail)
    app.router.add_get("/atelie-arte", atelier_page)
    app.router.add_get("/api/gwent/cartas-geradas/{card_id}/prompt", generated_card_prompt)
    app.router.add_post("/api/gwent/cartas-geradas/{card_id}/arte", generated_card_art_upload)
    app.router.add_get("/api/gwent/cartas-geradas/{card_id}/arte", generated_card_art)

    app.router.add_get("/api/gwent/forja", forja_list)
    app.router.add_post("/api/gwent/forja", forja_action)

    app.router.add_get("/rituais-ancestrais", rituais_page)
    app.router.add_get("/api/gwent/rituais-ancestrais", rituais_list)
    app.router.add_post("/api/gwent/rituais-ancestrais", rituais_execute)

    app.router.add_get("/linhagens", linhagens_page)
    app.router.add_get("/api/gwent/linhagens", linhagens_list)
    app.router.add_post("/api/gwent/linhagens", linhagens_execute)
