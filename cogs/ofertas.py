"""Jogos grátis e promoções com foco no Brasil.

Fontes (todas consultadas em região BR / preços em reais quando a loja informa):
  • Steam Brasil        – promoções e jogos temporariamente grátis      (sem chave)
  • Epic Games Store    – jogos grátis da semana                         (sem chave)
  • GOG                 – promoções e jogos grátis em BRL                (sem chave)
  • GamerPower          – giveaways de várias lojas                      (sem chave)
  • IsThereAnyDeal      – Nuuvem e outras lojas em BRL + giveaways       (ITAD_API_KEY, opcional)
  • CheapShark          – promoções de várias lojas em USD → BRL        (sem chave)
  • GG.deals            – comparação de preço da Steam em BRL            (GG_DEALS_API_KEY, opcional)

Cada oferta vira um cartão limpo: imagem grande, nome grande, preço original riscado
e preço de agora. Nenhuma fonte é obrigatória: se uma falhar, as outras continuam.
"""
import asyncio
import json
from email.utils import parsedate_to_datetime
import logging
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import (
    OFFERS_CHECK_MINUTES,
    MAX_OFFERS_PER_CHECK,
    MIN_PROMO_DISCOUNT,
    SEED_OFFERS_ON_FIRST_RUN,
    SENT_DB_PATH,
    GG_DEALS_API_KEY,
    ITAD_API_KEY,
    ITAD_SHOPS,
    OFFERS_GOG_ENABLED,
    OFFERS_SHOW_DESCRIPTION,
    BRAZIL_TZ,
)
from admin_config import GuildConfig
from utils import get_text_channel, erro_comando
from ia.provedores import gerar_texto_com_failover

log = logging.getLogger("ofertas")

# CheapShark: exige redução real, desconto >=50% e qualidade mínima.

HAS_LAYOUT_VIEW = hasattr(discord.ui, "LayoutView") and hasattr(discord.ui, "MediaGallery")

COR_GRATIS = 0x2ECC71
COR_PROMO = 0xF39C12
# Evita repostar o mesmo jogo grátis vindo de duas fontes diferentes (ex.: Epic + GamerPower).
JANELA_DUPLICADO_GRATIS = timedelta(days=14)

# ====================================================================== tradução
# Só é usada se OFFERS_SHOW_DESCRIPTION=true. Reaproveita a configuração Gemini da Nara.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
_translation_warned = False


_CACHE_DDL = """
    CREATE TABLE IF NOT EXISTS offer_translation_cache (
        source_text TEXT PRIMARY KEY,
        translated_text TEXT NOT NULL,
        translated_at TEXT NOT NULL
    )
"""


def _ler_cache_traducao(original: str) -> str | None:
    with sqlite3.connect(SENT_DB_PATH, timeout=3) as conn:
        conn.execute("PRAGMA busy_timeout=3000")
        conn.execute(_CACHE_DDL)
        row = conn.execute(
            "SELECT translated_text FROM offer_translation_cache WHERE source_text = ?",
            (original,),
        ).fetchone()
        return str(row[0]) if row and row[0] else None


def _salvar_cache_traducao(original: str, translated: str) -> None:
    with sqlite3.connect(SENT_DB_PATH, timeout=3) as conn:
        conn.execute("PRAGMA busy_timeout=3000")
        conn.execute(_CACHE_DDL)
        conn.execute(
            "INSERT OR REPLACE INTO offer_translation_cache "
            "(source_text, translated_text, translated_at) VALUES (?, ?, ?)",
            (original, translated, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


async def traduzir_descricao_oferta(texto: str) -> str:
    """Traduz descrições externas e mantém cache SQLite para reduzir custo e latência."""
    global _translation_warned
    original = (texto or "").strip()
    if not original:
        return original
    if not (GEMINI_API_KEY or os.getenv("GEMINI_BACKUP_API_KEY", "").strip()):
        if not _translation_warned:
            log.warning("Tradução de descrições desativada: configure GEMINI_API_KEY e/ou GEMINI_BACKUP_API_KEY.")
            _translation_warned = True
        return original

    try:
        cached = await asyncio.to_thread(_ler_cache_traducao, original)
        if cached:
            return cached
    except sqlite3.Error:
        log.exception("Não foi possível ler o cache de traduções.")

    try:
        prompt = (
            "Traduza a descrição abaixo para português brasileiro natural (pt-BR). "
            "Retorne somente a descrição traduzida, sem introdução, aspas ou comentários. "
            "Preserve o sentido e todos os fatos. Não traduza nomes oficiais de jogos, "
            "personagens, estúdios, plataformas, marcas, URLs, códigos, comandos, "
            "identificadores, datas, valores ou moedas. Não invente informações nem "
            "adicione detalhes. Se o texto já estiver em português brasileiro, devolva-o "
            "com mudanças mínimas.\n\nDESCRIÇÃO:\n" + original
        )
        translated = await gerar_texto_com_failover(
            prompt, system="Você é tradutor pt-BR, fiel ao texto e sem acrescentar informações.", temperature=0.1
        )
        translated = translated.strip() or original
    except Exception:
        log.exception("Falha traduzindo descrição; será usado o texto original.")
        return original

    try:
        await asyncio.to_thread(_salvar_cache_traducao, original, translated)
    except sqlite3.Error:
        log.exception("Não foi possível salvar a tradução no cache.")
    return translated


# ================================================================== banco local

def init_offers_db() -> None:
    with sqlite3.connect(SENT_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_items (
                item_key TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL
            )
        """)
        conn.commit()


def offer_already_sent(item_key: str) -> bool:
    with sqlite3.connect(SENT_DB_PATH) as conn:
        return conn.execute(
            "SELECT 1 FROM sent_items WHERE item_key = ?", (item_key,)
        ).fetchone() is not None


def mark_offer_sent(item_key: str, *, refresh: bool = False) -> None:
    verb = "INSERT OR REPLACE" if refresh else "INSERT OR IGNORE"
    with sqlite3.connect(SENT_DB_PATH) as conn:
        conn.execute(
            f"{verb} INTO sent_items(item_key, sent_at) VALUES (?, ?)",
            (item_key, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def count_sent_items() -> int:
    with sqlite3.connect(SENT_DB_PATH) as conn:
        return conn.execute("SELECT COUNT(*) FROM sent_items").fetchone()[0]


def free_title_recently_sent(norm: str) -> bool:
    """True se um jogo grátis com esse título já foi publicado (de qualquer fonte) na janela."""
    if not norm:
        return False
    cutoff = (datetime.now(timezone.utc) - JANELA_DUPLICADO_GRATIS).isoformat()
    with sqlite3.connect(SENT_DB_PATH) as conn:
        return conn.execute(
            "SELECT 1 FROM sent_items WHERE item_key = ? AND sent_at > ?",
            (f"free:{norm}", cutoff),
        ).fetchone() is not None


def mark_free_title(norm: str) -> None:
    if norm:
        mark_offer_sent(f"free:{norm}", refresh=True)


def migrate_legacy_seeds() -> None:
    """Instalações antigas já tinham Steam/GamerPower/Epic registradas: não reseedar nem inundar.

    Roda uma única vez. Fontes novas (GOG, ITAD) são "semeadas" em silêncio na primeira
    consulta, para o canal não receber dezenas de ofertas antigas de uma vez.
    """
    if offer_already_sent("seed:__migrated__"):
        return
    if count_sent_items() > 0:
        for src in ("steam", "gamerpower", "epic"):
            mark_offer_sent(f"seed:{src}")
    mark_offer_sent("seed:__migrated__")


# ===================================================================== utilidades

def fmt_brl(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def money_brl(cents: Any) -> str | None:
    try:
        return fmt_brl(int(cents) / 100)
    except (TypeError, ValueError):
        return None


def money_decimal_brl(value: Any) -> str | None:
    try:
        return fmt_brl(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return None


def parse_dt(raw: Any) -> datetime | None:
    """Aceita ISO-8601, 'YYYY-MM-DD HH:MM:SS' (GamerPower) ou timestamp Unix. Sempre devolve UTC."""
    if raw in (None, "", 0):
        return None
    if isinstance(raw, datetime):
        return (raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(raw, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    s = str(raw).strip()
    if not s or s.upper() == "N/A":
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            d = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def fmt_prazo(raw: Any, so_data: bool = False) -> str | None:
    """'10/11 às 15:00' no horário de Brasília. Com so_data=True mostra só '10/11'
    (para fontes que não informam o fuso horário, como a GamerPower)."""
    d = parse_dt(raw)
    if d is None:
        return None
    if so_data:
        return d.strftime("%d/%m")
    return d.astimezone(BRAZIL_TZ).strftime("%d/%m às %H:%M")


def norm_title(title: str) -> str:
    t = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"\b(giveaway|free|key|dlc)\b", " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()


_LOJAS_NO_TITULO = (
    r"Steam|Epic Games(?: Store)?|GOG|itch\.io|Ubisoft(?: Connect)?|EA(?: app)?|Origin|"
    r"Prime Gaming|Amazon Prime|Xbox|PlayStation|PS[45]|Switch|Android|iOS|DRM-Free"
)


def limpar_titulo_gamerpower(title: str) -> str:
    """'Hades (Steam) Giveaway' -> 'Hades'."""
    t = re.sub(rf"\s*\((?:{_LOJAS_NO_TITULO})[^)]*\)", "", title, flags=re.I)
    t = re.sub(r"\s*\bGiveaway\b\s*$", "", t, flags=re.I)
    return t.strip(" -–:") or title


def _brl_only(currency: Any) -> bool:
    return str(currency or "").upper() in {"BRL", "R$"}


# =============================================================== requisição segura

# Respeita o Retry-After para não insistir enquanto a API mantém o bloqueio.
_REQUEST_COOLDOWNS: dict[str, datetime] = {}


async def _request_json(session: aiohttp.ClientSession, method: str, url: str,
                        nome: str, **kwargs) -> Any | None:
    """Faz a requisição e devolve JSON ou None. Nunca registra URL/headers (podem ter chave)."""
    cooldown_until = _REQUEST_COOLDOWNS.get(nome)
    now = datetime.now(timezone.utc)
    if cooldown_until and now < cooldown_until:
        remaining = int((cooldown_until - now).total_seconds())
        log.info("%s em pausa por limite da API; nova tentativa em aproximadamente %s s.", nome, remaining)
        return None

    try:
        async with session.request(
            method, url, timeout=aiohttp.ClientTimeout(total=20), **kwargs
        ) as resp:
            if resp.status == 429:
                retry_after = (resp.headers.get("Retry-After") or "").strip()
                retry_seconds = 0
                if retry_after:
                    try:
                        retry_seconds = max(0, int(float(retry_after)))
                    except ValueError:
                        try:
                            retry_dt = parsedate_to_datetime(retry_after)
                            if retry_dt.tzinfo is None:
                                retry_dt = retry_dt.replace(tzinfo=timezone.utc)
                            retry_seconds = max(0, int((retry_dt - now).total_seconds()))
                        except (TypeError, ValueError, OverflowError):
                            retry_seconds = 0
                if retry_seconds > 0:
                    _REQUEST_COOLDOWNS[nome] = now + timedelta(seconds=retry_seconds)
                    log.warning(
                        "%s respondeu HTTP 429; respeitando Retry-After de %s s.",
                        nome, retry_seconds,
                    )
                else:
                    _REQUEST_COOLDOWNS[nome] = now + timedelta(minutes=30)
                    log.warning(
                        "%s respondeu HTTP 429 sem Retry-After válido; pausa preventiva de 30 minutos.",
                        nome,
                    )
                return None
            if resp.status in (401, 403):
                log.warning("%s recusou o acesso (HTTP %s). Confira a chave/plano.", nome, resp.status)
                return None
            if resp.status >= 400:
                log.warning("%s respondeu HTTP %s.", nome, resp.status)
                return None
            return await resp.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        log.exception("Falha consultando %s.", nome)
        return None


# ===================================================================== fontes

async def fetch_steam_offers(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    data = await _request_json(
        session, "GET", "https://store.steampowered.com/api/featuredcategories/",
        "Steam Store", params={"cc": "br", "l": "brazilian"},
    )
    if not isinstance(data, dict):
        return []
    items = []
    for section_name in ("freegames", "specials"):
        section = data.get(section_name) or {}
        for game in section.get("items", []) if isinstance(section, dict) else []:
            app_id, title = game.get("id"), game.get("name")
            if not app_id or not title:
                continue
            currency = game.get("currency")
            if currency and not _brl_only(currency):
                continue
            discount = int(game.get("discount_percent") or 0)
            final_cents = game.get("final_price")
            initial_cents = game.get("original_price")
            # "Grátis" só quando era pago e ficou 0 — jogos free-to-play permanentes não são oferta.
            is_free = final_cents == 0 and (initial_cents or 0) > 0
            if not is_free and (final_cents is None or final_cents == 0 or discount <= 0):
                continue
            price = "Grátis" if is_free else money_brl(final_cents)
            if not price:
                continue
            # large_capsule_image (616x353) é bem maior que header_image (460x215).
            image = game.get("large_capsule_image") or game.get("header_image")
            items.append({
                "key": f"steam:{app_id}:{discount}:{final_cents}",
                "source_id": "steam",
                "steam_app_id": int(app_id),
                "title": title,
                "url": f"https://store.steampowered.com/app/{app_id}/?cc=br",
                "image": image,
                "store": "Steam",
                "platform": "PC",
                "price": price,
                "original_price": money_brl(initial_cents) if initial_cents else None,
                "discount": 100 if is_free else discount,
                "end": game.get("discount_expiration"),
                "kind": "game" if is_free else "promo",
            })
    return items


async def fetch_epic_free_games(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Listagem pública de jogos promocionalmente grátis da Epic (pt-BR / BR).

    É o backend público da loja web, sem SLA: se falhar, as outras fontes seguem.
    """
    payload = await _request_json(
        session, "GET",
        "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions",
        "Epic Games Store",
        params={"locale": "pt-BR", "country": "BR", "allowCountries": "BR"},
    )
    elements = (((payload or {}).get("data") or {}).get("Catalog") or {}).get("searchStore", {}).get("elements", [])
    items: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    prefer = ("OfferImageWide", "DieselStoreFrontWide", "DieselGameBoxWide", "Thumbnail")
    for game in elements if isinstance(elements, list) else []:
        promotions = game.get("promotions") or {}
        active_offers = []
        for group in promotions.get("promotionalOffers") or []:
            for offer in group.get("promotionalOffers") or []:
                end_dt = parse_dt(offer.get("endDate"))
                if end_dt is None or end_dt > now:
                    active_offers.append(offer)
        if not active_offers:
            continue
        price_data = ((game.get("price") or {}).get("totalPrice") or {})
        try:
            discount_is_zero = float(price_data.get("discountPrice")) == 0
            original_raw = price_data.get("originalPrice")
            original_is_positive = original_raw is None or float(original_raw) > 0
        except (TypeError, ValueError):
            continue
        if not discount_is_zero or not original_is_positive:
            continue
        title, product_id = game.get("title"), game.get("id")
        if not title or not product_id:
            continue
        slug = game.get("productSlug") or game.get("urlSlug")
        url = f"https://store.epicgames.com/pt-BR/p/{slug}" if slug else "https://store.epicgames.com/pt-BR/free-games"
        by_type = {im.get("type"): im.get("url") for im in (game.get("keyImages") or []) if im.get("url")}
        image = next((by_type[t] for t in prefer if t in by_type), None)
        original_text = None
        if _brl_only(price_data.get("currencyCode")) and original_raw:
            decimals = int((price_data.get("currencyInfo") or {}).get("decimals") or 2)
            original_text = fmt_brl(float(original_raw) / (10 ** decimals))
        end_dates = [o.get("endDate") for o in active_offers if o.get("endDate")]
        end = min(end_dates) if end_dates else None
        items.append({
            "key": f"epic:{product_id}:{end}",
            "source_id": "epic",
            "title": title,
            "url": url,
            "image": image,
            "store": "Epic Games Store",
            "platform": "PC",
            "price": "Grátis",
            "original_price": original_text,
            "discount": 100,
            "end": end,
            "kind": "game",
        })
    return items


def _gog_amount(money: Any) -> float | None:
    """finalMoney/baseMoney -> float. Só aceita BRL."""
    if not isinstance(money, dict) or not _brl_only(money.get("currency")):
        return None
    try:
        return float(str(money.get("amount")).replace(",", "."))
    except (TypeError, ValueError):
        return None


async def fetch_gog_offers(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Catálogo público da GOG, região BR, preços em BRL (sem chave)."""
    if not OFFERS_GOG_ENABLED:
        return []
    data = await _request_json(
        session, "GET", "https://catalog.gog.com/v1/catalog", "GOG",
        params={
            "limit": 48, "order": "desc:trending", "discounted": "eq:true",
            "productType": "in:game,pack", "page": 1,
            "countryCode": "BR", "locale": "pt-BR", "currencyCode": "BRL",
        },
    )
    products = data.get("products") if isinstance(data, dict) else None
    items: list[dict[str, Any]] = []
    for p in products if isinstance(products, list) else []:
        title, pid = p.get("title"), p.get("id")
        price = p.get("price") or {}
        final, base = _gog_amount(price.get("finalMoney")), _gog_amount(price.get("baseMoney"))
        if not title or not pid or final is None or base is None or base <= 0 or final >= base:
            continue
        discount = round((1 - final / base) * 100)
        is_free = final == 0
        slug = p.get("slug")
        url = p.get("storeLink") or (f"https://www.gog.com/pt/game/{slug}" if slug else "https://www.gog.com/pt/")
        items.append({
            "key": f"gog:{pid}:{int(round(final * 100))}",
            "source_id": "gog",
            "title": title,
            "url": url,
            "image": p.get("coverHorizontal") or p.get("coverVertical"),
            "store": "GOG",
            "platform": "PC",
            "price": "Grátis" if is_free else fmt_brl(final),
            "original_price": fmt_brl(base),
            "discount": 100 if is_free else discount,
            "end": None,
            "kind": "game" if is_free else "promo",
        })
    return items


async def fetch_gamerpower(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    data = await _request_json(
        session, "GET", "https://www.gamerpower.com/api/giveaways",
        "GamerPower", params={"type": "game"},
    )
    if not isinstance(data, list):
        return []
    platform_names = {"Origin": "EA app", "Xbox Series X|S": "Xbox Series X|S"}
    pc_stores = {"PC", "Steam", "Epic Games Store", "GOG", "itch.io", "EA app", "Ubisoft Connect",
                 "Prime Gaming", "Battle.net", "DRM-Free"}
    items = []
    for g in data:
        title = g.get("title")
        url = g.get("open_giveaway_url") or g.get("gamerpower_url")
        if not title or not url:
            continue
        if str(g.get("status") or "Active").lower() != "active":
            continue
        parts = [platform_names.get(p.strip(), p.strip()) for p in str(g.get("platforms") or "").split(",") if p.strip()]
        store = next((p for p in parts if p not in {"PC", "DRM-Free"}), parts[0] if parts else "Giveaway")
        plat = "PC" if any(p in pc_stores for p in parts) else ", ".join(p for p in parts if p != store)[:60]
        worth = str(g.get("worth") or "").strip()
        m = re.match(r"^\$\s*([\d.,]+)$", worth)
        # A GamerPower só informa o valor em dólar; fica claramente marcado como US$.
        original = f"US$ {m.group(1).replace('.', ',')}" if m and float(m.group(1).replace(',', '.') or 0) > 0 else None
        desc = (g.get("description") or "").strip() or None
        items.append({
            "key": f"gamerpower:{g.get('id') or title}",
            "source_id": "gamerpower",
            "title": limpar_titulo_gamerpower(title),
            "url": url,
            # "image" é maior que "thumbnail".
            "image": g.get("image") or g.get("thumbnail"),
            "store": store,
            "platform": plat or None,
            "price": "Grátis",
            "original_price": original,
            "discount": 100,
            "end": g.get("end_date"),
            "end_so_data": True,  # a API não informa o fuso: mostramos só o dia
            "description": desc,
            "kind": "game",
        })
    return items


# ---- IsThereAnyDeal -------------------------------------------------------------
ITAD_ATTRIBUTION = "[IsThereAnyDeal](https://isthereanydeal.com)"


def _itad_plataformas(plats: list[dict[str, Any]] | None) -> str | None:
    nomes = [p.get("name") for p in (plats or []) if p.get("name")]
    if not nomes:
        return None
    return "PC" if "Windows" in nomes else ", ".join(nomes[:3])


def _itad_image(game: dict[str, Any]) -> str | None:
    assets = game.get("assets") or {}
    for k in ("banner600", "banner400", "banner300", "boxart", "banner145"):
        if assets.get(k):
            return assets[k]
    return None


async def fetch_itad_deals(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Promoções em BRL (Nuuvem etc.). Requer ITAD_API_KEY; a ITAD exige manter URLs/preços como vieram."""
    if not ITAD_API_KEY:
        return []
    body = {
        "country": "BR", "limit": 60, "sort": "-cut", "shops": ITAD_SHOPS,
        "filter": {"cut": {"min": max(1, MIN_PROMO_DISCOUNT)}},
    }
    data = await _request_json(
        session, "POST", "https://api.isthereanydeal.com/deals/v2", "IsThereAnyDeal",
        json=body, headers={"ITAD-API-Key": ITAD_API_KEY},
    )
    rows = data.get("list") if isinstance(data, dict) else None
    now = datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []
    for g in rows if isinstance(rows, list) else []:
        deal = g.get("deal") or {}
        price, regular = deal.get("price") or {}, deal.get("regular") or {}
        # Só jogos base (sem DLC/pacotes sem tipo) e só valores realmente em reais.
        if g.get("type") != "game" or not _brl_only(price.get("currency")):
            continue
        expiry = parse_dt(deal.get("expiry"))
        if expiry is not None and expiry <= now:
            continue
        try:
            amount, reg_amount = float(price["amount"]), float(regular.get("amount") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        shop = deal.get("shop") or {}
        url = deal.get("url")
        if not g.get("title") or not url:
            continue
        is_free = amount == 0
        items.append({
            "key": f"itad:{shop.get('id')}:{g.get('id')}:{price.get('amountInt', int(amount * 100))}",
            "source_id": "itad",
            "title": g["title"],
            "url": url,
            "image": _itad_image(g),
            "store": shop.get("name") or "Loja",
            "platform": _itad_plataformas(deal.get("platforms")),
            "price": "Grátis" if is_free else fmt_brl(amount),
            "original_price": fmt_brl(reg_amount) if reg_amount > amount else None,
            "discount": 100 if is_free else int(deal.get("cut") or 0),
            "end": deal.get("expiry"),
            "kind": "game" if is_free else "promo",
            "via": ITAD_ATTRIBUTION,
        })
    return items


async def fetch_itad_giveaways(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Giveaways ativos (GOG, Prime Gaming, etc.) pela ITAD. Requer ITAD_API_KEY."""
    if not ITAD_API_KEY:
        return []
    data = await _request_json(
        session, "GET", "https://api.isthereanydeal.com/giveaways/v1", "IsThereAnyDeal (giveaways)",
        params={"limit": 20}, headers={"ITAD-API-Key": ITAD_API_KEY},
    )
    now = datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []
    for gw in data if isinstance(data, list) else []:
        url = gw.get("url")
        expiry = parse_dt(gw.get("expiry"))
        if not url or (expiry is not None and expiry <= now):
            continue
        games = [x for x in (gw.get("games") or []) if x.get("type") in (None, "game")]
        if not games:
            continue
        # Pacote com vários jogos: usa o nome da promoção; senão, o nome do jogo.
        title = games[0].get("title") if len(games) == 1 else gw.get("title")
        if not title:
            continue
        shop = gw.get("shop") or {}
        items.append({
            "key": f"itad_give:{gw.get('id')}",
            "source_id": "itad_give",
            "title": title,
            "url": url,
            "image": _itad_image(games[0]),
            "store": shop.get("name") or "Loja",
            "platform": _itad_plataformas(games[0].get("platforms")),
            "price": "Grátis",
            "original_price": None,
            "discount": 100,
            "end": gw.get("expiry"),
            "kind": "game",
            "via": ITAD_ATTRIBUTION,
        })
    return items



# ---- CheapShark (promoções de várias lojas) -------------------------------------
CHEAPSHARK_DEALS_URL = "https://www.cheapshark.com/api/1.0/deals"
CHEAPSHARK_STORES_URL = "https://www.cheapshark.com/api/1.0/stores"
USD_BRL_URL = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
USD_BRL_CACHE_SECONDS = 6 * 60 * 60


async def fetch_usd_brl_rate(session: aiohttp.ClientSession) -> float | None:
    """Obtém USD/BRL com cache e duas fontes; evita consultar câmbio a cada ciclo."""
    now = datetime.now(timezone.utc).timestamp()
    cached_rate = getattr(fetch_usd_brl_rate, "_rate", None)
    cached_at = getattr(fetch_usd_brl_rate, "_at", 0.0)
    if cached_rate and now - cached_at < USD_BRL_CACHE_SECONDS:
        return float(cached_rate)

    # Frankfurter é a fonte principal: não exige chave e não publica quotas diárias/mensais.
    # A AwesomeAPI fica como fallback caso a primeira esteja indisponível.
    providers = (
        (
            "Frankfurter",
            "https://api.frankfurter.dev/v2/rate/usd/brl",
            lambda data: float(data["rate"]) if isinstance(data, dict) else 0.0,
        ),
        (
            "AwesomeAPI",
            USD_BRL_URL,
            lambda data: float(data["USDBRL"]["bid"]) if isinstance(data, dict) else 0.0,
        ),
    )

    for provider_name, url, extract_rate in providers:
        try:
            data = await _request_json(session, "GET", url, f"cotação USD/BRL ({provider_name})")
            rate = extract_rate(data)
            if rate > 0:
                fetch_usd_brl_rate._rate = rate
                fetch_usd_brl_rate._at = now
                fetch_usd_brl_rate._provider = provider_name
                log.info("Cotação USD/BRL obtida via %s: %.4f", provider_name, rate)
                return rate
        except Exception as exc:
            log.warning("Falha na cotação USD/BRL via %s: %s", provider_name, exc)

    # Se todas as fontes falharem, usa a última taxa válida em memória.
    if cached_rate:
        log.warning("Fontes de câmbio indisponíveis; usando última cotação válida em cache.")
        return float(cached_rate)

    return None


async def fetch_cheapshark_stores(session: aiohttp.ClientSession) -> dict[str, str]:
    """Obtém os nomes das lojas monitoradas pelo CheapShark."""
    data = await _request_json(session, "GET", CHEAPSHARK_STORES_URL, "CheapShark (lojas)")
    if not isinstance(data, list):
        return {}
    return {
        str(store.get("storeID")): str(store.get("storeName") or "Loja")
        for store in data
        if isinstance(store, dict) and store.get("storeID") is not None
        and str(store.get("isActive", "1")) == "1"
    }


async def fetch_cheapshark_offers(
    session: aiohttp.ClientSession,
    store_names: dict[str, str],
    usd_brl: float | None,
) -> list[dict[str, Any]]:
    """Busca até 300 promoções CheapShark, filtra qualidade e desconto mínimo."""
    if not usd_brl or usd_brl <= 0:
        log.warning("CheapShark pausado: cotação USD/BRL indisponível; não serão exibidos preços incorretos.")
        return []

    # Cinco páginas sequenciais de até 60 resultados (limite documentado por página).
    all_deals: list[dict[str, Any]] = []
    for page_number in range(5):
        page_data = await _request_json(
            session, "GET", CHEAPSHARK_DEALS_URL, "CheapShark",
            params={
                "pageNumber": page_number,
                "pageSize": 60,
                "sortBy": "DealRating",
                "onSale": 1,
            },
            headers={"User-Agent": "NARABOT/1.0 (Discord game deals monitor)"},
        )
        if not isinstance(page_data, list):
            log.warning(
                "CheapShark página %s não retornou uma lista (tipo=%s); interrompendo paginação.",
                page_number + 1, type(page_data).__name__,
            )
            break
        all_deals.extend(page_data)
        log.info(
            "CheapShark página %s/5: %s registros recebidos.",
            page_number + 1, len(page_data),
        )
        if len(page_data) < 60:
            break

    if not all_deals:
        log.warning("CheapShark não retornou registros nas páginas consultadas.")
        return []

    log.info("CheapShark API respondeu com %s registros brutos em até 5 páginas.", len(all_deals))
    candidates: dict[str, dict[str, Any]] = {}
    rejected_not_flagged = 0
    rejected_not_on_sale = 0
    rejected_discount = 0
    rejected_low_quality = 0
    duplicate_game_deals = 0

    for deal in all_deals:
        try:
            title = str(deal.get("title") or "").strip()
            deal_id = str(deal.get("dealID") or "").strip()
            sale_usd = float(deal.get("salePrice"))
            normal_usd = float(deal.get("normalPrice"))
            if not title or not deal_id or sale_usd < 0 or normal_usd <= 0:
                continue

            if str(deal.get("isOnSale", "0")).strip() != "1":
                rejected_not_flagged += 1
                continue
            if sale_usd >= normal_usd:
                rejected_not_on_sale += 1
                continue

            discount = round(((normal_usd - sale_usd) / normal_usd) * 100)
            if discount < 50:
                rejected_discount += 1
                continue

            steam_rating = int(float(deal.get("steamRatingPercent") or 0))
            steam_review_count = int(float(deal.get("steamRatingCount") or 0))
            metacritic = int(float(deal.get("metacriticScore") or 0))

            # Qualidade: Steam >=75% com >=300 avaliações OU Metacritic >=70.
            steam_quality = steam_rating >= 75 and steam_review_count >= 300
            metacritic_quality = metacritic >= 70
            if not (steam_quality or metacritic_quality):
                rejected_low_quality += 1
                continue

            deal_rating = float(deal.get("dealRating") or 0)
        except (TypeError, ValueError):
            continue

        store_id = str(deal.get("storeID") or "")
        store = store_names.get(store_id, f"Loja {store_id}" if store_id else "Loja")
        url = f"https://www.cheapshark.com/redirect?dealID={deal_id}"
        sale_brl = sale_usd * usd_brl
        normal_brl = normal_usd * usd_brl
        thumb = deal.get("thumb")
        steam_app_id = str(deal.get("steamAppID") or "").strip()
        # Preferir header art Steam em resolução maior; o MediaGallery usa toda a largura do painel.
        image = (
            f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{steam_app_id}/header.jpg"
            if steam_app_id
            else thumb if isinstance(thumb, str) and thumb.startswith("https://") else None
        )
        game_id = str(deal.get("gameID") or "").strip()
        dedupe_id = f"cheapshark-game:{game_id}" if game_id else f"cheapshark-deal:{deal_id}"
        candidate = {
            "key": dedupe_id,
            "source_id": "cheapshark",
            "title": title,
            "url": url,
            "image": image,
            "store": store,
            "platform": "PC",
            "price": fmt_brl(sale_brl),
            "original_price": fmt_brl(normal_brl),
            "discount": discount,
            "end": None,
            "kind": "promo",
            "via": f"CheapShark · conversão estimada (US$ 1 = {fmt_brl(usd_brl)})",
            "relevance_rank": (
                steam_rating + min(steam_review_count, 10000) / 100 + metacritic
            ),
            "_deal_rating": deal_rating,
        }

        # Um cartão por jogo; mantém a oferta com melhor DealRating e depois maior desconto.
        existing = candidates.get(dedupe_id)
        if existing:
            duplicate_game_deals += 1
            if (candidate["_deal_rating"], candidate["discount"]) <= (
                existing["_deal_rating"], existing["discount"]
            ):
                continue
        candidates[dedupe_id] = candidate

    items = []
    for candidate in candidates.values():
        candidate.pop("_deal_rating", None)
        items.append(candidate)

    log.info(
        "CheapShark qualidade: brutos=%s | sem isOnSale=%s | sem redução=%s | "
        "desconto abaixo de 50%%=%s | reprovados por avaliações/Metacritic=%s | "
        "duplicados do mesmo jogo=%s | aprovados únicos=%s",
        len(all_deals), rejected_not_flagged, rejected_not_on_sale,
        rejected_discount, rejected_low_quality, duplicate_game_deals, len(items),
    )
    return items


# ---- GG.deals (comparação opcional, só Steam) -----------------------------------
async def enrich_with_gg_deals_prices(session: aiohttp.ClientSession, items: list[dict[str, Any]]) -> None:
    """Acrescenta comparação GG.deals em BRL sem substituir o preço regional da Steam."""
    if not GG_DEALS_API_KEY:
        return
    app_ids = sorted({int(item["steam_app_id"]) for item in items if item.get("steam_app_id")})
    for start in range(0, len(app_ids), 100):
        batch = app_ids[start:start + 100]
        try:
            async with session.get(
                "https://api.gg.deals/v1/prices/by-steam-app-id/",
                params={"key": GG_DEALS_API_KEY, "ids": ",".join(map(str, batch)), "region": "br"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                # Nunca registrar a URL completa: ela contém a chave de API.
                body = await resp.text()
                if resp.status == 429:
                    log.warning("GG.deals atingiu o limite da API; preços complementares ignorados neste ciclo.")
                    return
                if resp.status >= 400:
                    detail = body[:500].replace("\n", " ").strip() or "sem detalhes"
                    try:
                        err = json.loads(body)
                        if isinstance(err, dict) and isinstance(err.get("data"), dict):
                            detail = str(err["data"].get("message") or err["data"].get("name") or detail)[:500]
                    except (ValueError, TypeError):
                        pass
                    log.warning("GG.deals respondeu HTTP %s (%s IDs). Detalhe: %s", resp.status, len(batch), detail)
                    return
                try:
                    payload = json.loads(body)
                except (ValueError, TypeError):
                    log.warning("GG.deals retornou uma resposta que não é JSON válido.")
                    return
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            log.exception("Falha de rede consultando o GG.deals.")
            return
        if isinstance(payload, dict) and payload.get("success") is False:
            err = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            log.warning("GG.deals informou falha: %s", str(err.get("message") or err.get("name") or "erro sem detalhes")[:500])
            return
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        for item in items:
            app_id = item.get("steam_app_id")
            game = data.get(str(app_id)) if app_id is not None else None
            if not isinstance(game, dict):
                continue
            prices = game.get("prices") or {}
            if not _brl_only(prices.get("currency")):  # nunca mostrar valor estrangeiro como BRL
                continue
            item["gg_deals_url"] = game.get("url") or "https://gg.deals/"
            item["gg_deals_retail"] = money_decimal_brl(prices.get("currentRetail"))
            item["gg_deals_keyshops"] = money_decimal_brl(prices.get("currentKeyshops"))


# ===================================================================== cartão

def _esc(texto: str) -> str:
    return discord.utils.escape_markdown(str(texto))


def preco_linha(item: dict[str, Any]) -> str:
    """'~~R$ 199,90~~ ➜ **R$ 49,90** · **-75%**' (ou GRÁTIS)."""
    preco = str(item.get("price") or "Consulte a loja")
    original = item.get("original_price")
    desconto = item.get("discount")
    gratis = preco.lower() in {"grátis", "gratis"}
    atual = "**GRÁTIS**" if gratis else f"**{preco}**"
    if original and original != preco:
        linha = f"~~{original}~~  ➜  {atual}"
    else:
        linha = atual
    if not gratis and desconto:
        linha += f"  ·  **-{int(desconto)}%**"
    return linha


def cartao_texto(item: dict[str, Any]) -> str:
    """Texto do cartão: pouca coisa escrita, nome grande, preços em destaque."""
    gratis = item.get("kind") == "game"
    rotulo = "🎁 JOGO GRÁTIS" if gratis else "🔥 PROMOÇÃO"
    store = str(item.get("store") or "").strip()
    linhas = [
        f"**{rotulo}**" + (f"  ·  **{_esc(store)}**" if store else ""),
        f"# {_esc(str(item.get('title') or 'Jogo'))[:240]}",
        f"## {preco_linha(item)}",
    ]
    meta = []
    plat = str(item.get("platform") or "").strip()
    if plat and plat != store:
        meta.append(_esc(plat))
    prazo = fmt_prazo(item.get("end"), bool(item.get("end_so_data")))
    if prazo:
        meta.append(f"até {prazo}")
    if item.get("via"):
        meta.append(f"via {item['via']}")
    if meta:
        linhas.append("  ·  ".join(meta))

    gg_url, gg_retail, gg_keys = item.get("gg_deals_url"), item.get("gg_deals_retail"), item.get("gg_deals_keyshops")
    if gg_url and (gg_retail or gg_keys):
        partes = []
        if gg_retail:
            partes.append(f"lojas oficiais {gg_retail}")
        if gg_keys:
            partes.append(f"keyshops {gg_keys}")
        linhas.append(f"**GG.deals:** {' · '.join(partes)} · [comparar]({gg_url})")

    if OFFERS_SHOW_DESCRIPTION and item.get("description"):
        linhas.append(str(item["description"])[:300].rstrip() + ("…" if len(str(item["description"])) > 300 else ""))
    return "\n".join(linhas)[:3900]


def _cor(item: dict[str, Any]) -> int:
    return COR_GRATIS if item.get("kind") == "game" else COR_PROMO


def _botao_label(item: dict[str, Any]) -> str:
    return "Resgatar grátis" if item.get("kind") == "game" else "Ver oferta"


def _url_valida(url: Any) -> bool:
    return isinstance(url, str) and url.startswith(("https://", "http://"))


def make_offer_view(item: dict[str, Any]):
    """Cartão Components V2: imagem grande em cima, nome grande, preço e um botão."""
    container_items: list[Any] = []
    image = str(item.get("image") or "")
    if image.startswith("https://"):
        container_items.append(discord.ui.MediaGallery(discord.MediaGalleryItem(image)))
    container_items.append(discord.ui.TextDisplay(cartao_texto(item)))
    url = item.get("url")
    if _url_valida(url):
        container_items.append(discord.ui.ActionRow(
            discord.ui.Button(label=_botao_label(item), style=discord.ButtonStyle.link, url=url)
        ))
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(discord.ui.Container(*container_items, accent_colour=_cor(item)))
    return view


class OfertaView(discord.ui.View):
    """Reserva para servidores sem Components V2: só o botão de acesso."""
    def __init__(self, item: dict[str, Any]):
        super().__init__(timeout=None)
        if _url_valida(item.get("url")):
            self.add_item(discord.ui.Button(label=_botao_label(item), style=discord.ButtonStyle.link, url=item["url"]))


def make_offer_embed(item: dict[str, Any]) -> discord.Embed:
    """Reserva (discord.py antigo): embed enxuto com a imagem grande."""
    texto = cartao_texto(item).split("\n", 2)
    embed = discord.Embed(
        title=str(item.get("title") or "Jogo")[:250],
        url=item.get("url") if _url_valida(item.get("url")) else None,
        description=texto[2] if len(texto) > 2 else None,
        color=_cor(item),
    )
    if str(item.get("image") or "").startswith("https://"):
        embed.set_image(url=item["image"])
    return embed


async def enviar_oferta(channel, item: dict[str, Any]) -> None:
    sem_mencoes = discord.AllowedMentions.none()
    if HAS_LAYOUT_VIEW:
        try:
            await channel.send(view=make_offer_view(item), allowed_mentions=sem_mencoes)
            return
        except (TypeError, AttributeError):
            log.exception("Components V2 indisponível; usando embed de reserva.")
    await channel.send(embed=make_offer_embed(item), view=OfertaView(item), allowed_mentions=sem_mencoes)


AMOSTRA = {
    "key": "amostra", "source_id": "amostra", "title": "ELDEN RING",
    "url": "https://store.steampowered.com/app/1245620/ELDEN_RING/?cc=br",
    "image": "https://cdn.cloudflare.steamstatic.com/steam/apps/1245620/header.jpg",
    "store": "Steam", "platform": "PC", "price": "R$ 149,99", "original_price": "R$ 249,90",
    "discount": 40, "end": datetime.now(timezone.utc) + timedelta(days=3), "kind": "promo",
}


# ===================================================================== cog

class Ofertas(commands.Cog):
    """Jogos grátis e promoções (Steam, Epic, GOG, CheapShark, GamerPower e ITAD/Nuuvem)."""

    def __init__(self, bot):
        self.bot = bot
        self.http_session: aiohttp.ClientSession | None = None
        self.cheapshark_stores: dict[str, str] = {}

    async def cog_load(self):
        self.http_session = aiohttp.ClientSession(headers={
            "User-Agent": "NARABOT/1.0 (Discord game deals monitor)"
        })
        self.cheapshark_stores = await fetch_cheapshark_stores(self.http_session)
        await asyncio.to_thread(init_offers_db)
        await asyncio.to_thread(migrate_legacy_seeds)
        self.offers_loop.start()

    async def cog_unload(self):
        self.offers_loop.cancel()
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    # -- coleta ---------------------------------------------------------------
    async def coletar(self) -> list[dict[str, Any]]:
        # Ordem importa na deduplicação de grátis: fontes mais completas primeiro,
        # GamerPower (agregador) por último.
        fontes = (
            fetch_epic_free_games, fetch_steam_offers, fetch_gog_offers,
            fetch_itad_giveaways, fetch_itad_deals, fetch_gamerpower,
        )
        results = await asyncio.gather(*(f(self.http_session) for f in fontes), return_exceptions=True)
        items: list[dict[str, Any]] = []
        for fonte, result in zip(fontes, results):
            if isinstance(result, list):
                items.extend(result)
            elif isinstance(result, Exception):
                log.error("Erro na fonte %s: %r", fonte.__name__, result)

        try:
            usd_brl = await fetch_usd_brl_rate(self.http_session)
            cheapshark = await fetch_cheapshark_offers(
                self.http_session, self.cheapshark_stores, usd_brl
            )
            cheapshark_eligible = len(cheapshark)
            log.info(
                "CheapShark: lojas=%s | ofertas recebidas=%s | "
                "promoções válidas=%s (desconto mínimo interno: 50%%)",
                len(self.cheapshark_stores),
                len(cheapshark),
                cheapshark_eligible,
            )
            items.extend(cheapshark)
        except Exception:
            log.exception("Erro na fonte CheapShark.")
        return items

    @tasks.loop(minutes=OFFERS_CHECK_MINUTES)
    async def offers_loop(self):
        if not self.http_session:
            return
        try:
            items = await self.coletar()

            unique: dict[str, dict[str, Any]] = {}
            gratis_vistos: set[str] = set()
            for item in items:
                if item["key"] in unique:
                    continue
                if item["kind"] == "game":
                    norm = norm_title(item["title"])
                    if norm and norm in gratis_vistos:
                        continue  # mesmo jogo grátis vindo de outra fonte
                    gratis_vistos.add(norm)
                    item["norm"] = norm
                unique[item["key"]] = item

            await enrich_with_gg_deals_prices(self.http_session, list(unique.values()))

            # Fonte vista pela primeira vez: registra o que já existe sem postar (evita inundar o canal).
            fontes_presentes = {i["source_id"] for i in unique.values()}
            if SEED_OFFERS_ON_FIRST_RUN:
                for src in fontes_presentes:
                    # CheapShark deve publicar ofertas já encontradas na primeira coleta.
                    # As fontes antigas continuam protegidas contra inundação inicial.
                    if src == "cheapshark":
                        continue
                    if await asyncio.to_thread(offer_already_sent, f"seed:{src}"):
                        continue
                    seeded = 0
                    for item in unique.values():
                        if item["source_id"] == src:
                            await asyncio.to_thread(mark_offer_sent, item["key"])
                            if item["kind"] == "game":
                                await asyncio.to_thread(mark_free_title, item.get("norm", ""))
                            seeded += 1
                    await asyncio.to_thread(mark_offer_sent, f"seed:{src}")
                    log.info("Fonte '%s' registrada pela primeira vez: %s ofertas marcadas sem postar.", src, seeded)

            # A leitura da base de deduplicação pode esperar por lock; não bloqueie o event loop.
            novos = []
            for item in unique.values():
                if await asyncio.to_thread(offer_already_sent, item["key"]):
                    continue
                if item["kind"] == "game" and await asyncio.to_thread(free_title_recently_sent, item.get("norm", "")):
                    continue
                if (
                    item["kind"] == "promo"
                    and item.get("source_id") != "cheapshark"
                    and (item.get("discount") or 0) < MIN_PROMO_DISCOUNT
                ):
                    continue
                novos.append(item)
            # Jogos grátis primeiro; depois CheapShark por relevância e, em seguida, desconto.
            novos.sort(key=lambda i: (
                i["kind"] != "game",
                -float(i.get("relevance_rank") or 0),
                -(i.get("discount") or 0),
            ))

            cheapshark_total = sum(1 for i in unique.values() if i.get("source_id") == "cheapshark")
            cheapshark_new = sum(1 for i in novos if i.get("source_id") == "cheapshark")
            log.info(
                "CheapShark pipeline: coletadas=%s | novas após deduplicação/filtros=%s",
                cheapshark_total,
                cheapshark_new,
            )

            sent_this_cycle = 0
            cheapshark_sent_this_cycle = 0
            guild_id = self.bot.guilds[0].id if self.bot.guilds else 0
            for item in novos:
                if item["kind"] == "game":
                    target_id = await GuildConfig.get(self.bot.db, guild_id, "games_channel")
                else:
                    target_id = await GuildConfig.get(self.bot.db, guild_id, "promos_channel")
                if not target_id:
                    log.warning("Defina os canais de jogos/promoções via /adm ou config.py para ativar os avisos de ofertas.")
                    return
                channel = await get_text_channel(self.bot, target_id)
                if channel is None:
                    continue
                try:
                    if OFFERS_SHOW_DESCRIPTION and item.get("description"):
                        item["description"] = await traduzir_descricao_oferta(str(item["description"]))
                    await enviar_oferta(channel, item)
                    await asyncio.to_thread(mark_offer_sent, item["key"])
                    if item["kind"] == "game":
                        await asyncio.to_thread(mark_free_title, item.get("norm", ""))
                    sent_this_cycle += 1
                    if item.get("source_id") == "cheapshark":
                        cheapshark_sent_this_cycle += 1
                    await asyncio.sleep(1.2)
                    if sent_this_cycle >= MAX_OFFERS_PER_CHECK:
                        break
                except discord.HTTPException:
                    log.exception("Falha publicando oferta: %s", item.get("title"))
            log.info(
                "Ofertas verificadas: %s; novas publicadas: %s | "
                "CheapShark publicadas nesta coleta: %s",
                len(unique), sent_this_cycle, cheapshark_sent_this_cycle,
            )
        except Exception:
            log.exception("Erro na rotina de ofertas.")

    @offers_loop.before_loop
    async def before_offers_loop(self):
        await self.bot.wait_until_ready()

    # -- comandos de moderação --------------------------------------------------
    @app_commands.command(name="status_ofertas", description="Mostra se o monitoramento de ofertas está configurado e funcionando.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status_ofertas(self, interaction: discord.Interaction):
        games_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "games_channel")
        promos_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "promos_channel")
        games = f"<#{games_id}>" if games_id else "Não configurado"
        promos = f"<#{promos_id}>" if promos_id else "Não configurado"
        gog = "✅ GOG (BRL)" if OFFERS_GOG_ENABLED else "⚪ GOG desligada (OFFERS_GOG_ENABLED)"
        if ITAD_API_KEY:
            itad = f"✅ IsThereAnyDeal — lojas {', '.join(map(str, ITAD_SHOPS))} (50 = Nuuvem)"
        else:
            itad = "⚪ IsThereAnyDeal — defina ITAD_API_KEY para ativar a Nuuvem"
        gg = "✅ GG.deals (comparação de preços)" if GG_DEALS_API_KEY else "⚪ GG.deals — defina GG_DEALS_API_KEY (opcional)"
        layout = "Components V2 (imagem grande)" if HAS_LAYOUT_VIEW else "embed (atualize o discord.py para >= 2.6)"
        await interaction.response.send_message(
            f"**Jogos grátis:** {games}\n**Promoções:** {promos}\n"
            f"**Verificação:** a cada {OFFERS_CHECK_MINUTES} minutos · desconto mínimo {MIN_PROMO_DISCOUNT}%\n"
            f"**Layout:** {layout}\n\n"
            "**Fontes**\n✅ Steam Brasil\n✅ Epic Games Store (BR)\n✅ GamerPower\n"
            f"✅ CheapShark ({len(self.cheapshark_stores)} lojas cadastradas; USD → BRL)\n"
            f"{gog}\n{itad}\n{gg}",
            ephemeral=True,
        )

    @app_commands.command(name="previa_oferta", description="Mostra só para você como um cartão de oferta fica no canal.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def previa_oferta(self, interaction: discord.Interaction):
        amostra = dict(AMOSTRA)
        if HAS_LAYOUT_VIEW:
            await interaction.response.send_message(view=make_offer_view(amostra), ephemeral=True)
        else:
            await interaction.response.send_message(embed=make_offer_embed(amostra), view=OfertaView(amostra), ephemeral=True)

    async def cog_app_command_error(self, interaction, error):
        await erro_comando(interaction, error)


async def setup(bot):
    await bot.add_cog(Ofertas(bot))
