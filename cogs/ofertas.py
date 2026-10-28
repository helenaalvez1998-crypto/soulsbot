import asyncio
import logging
import json
import sqlite3
import os
from io import BytesIO
from datetime import datetime, timezone
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import (
    GAMES_CHANNEL_ID, PROMOS_CHANNEL_ID, OFFERS_CHECK_MINUTES, MAX_OFFERS_PER_CHECK,
    MIN_PROMO_DISCOUNT, SEED_OFFERS_ON_FIRST_RUN, SENT_DB_PATH, GG_DEALS_API_KEY,
)
from admin_config import GuildConfig
from utils import get_text_channel, erro_comando

log = logging.getLogger("ofertas")

# Tradução das descrições de jogos e ofertas para português brasileiro.
# Reutiliza as variáveis Gemini da Nara e mantém fallback para o texto original.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip()
_translation_warned = False


def _translate_game_description_sync(text: str) -> str:
    """Chamada síncrona isolada; executada em thread para não bloquear o loop do Discord."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = (
        "Traduza a descrição abaixo para português brasileiro natural (pt-BR). "
        "Retorne somente a descrição traduzida, sem introdução, aspas ou comentários. "
        "Preserve o sentido e todos os fatos. Não traduza nomes oficiais de jogos, "
        "personagens, estúdios, plataformas, marcas, URLs, códigos, comandos, "
        "identificadores, datas, valores ou moedas. Não invente informações nem "
        "adicione detalhes. Se o texto já estiver em português brasileiro, devolva-o "
        "com mudanças mínimas.\\n\\nDESCRIÇÃO:\\n" + text
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    result = (getattr(response, "text", None) or "").strip()
    return result or text


async def traduzir_descricao_oferta(texto: str) -> str:
    """Traduz descrições externas e mantém cache SQLite para reduzir custo e latência."""
    global _translation_warned
    original = (texto or "").strip()
    if not original:
        return original
    if not GEMINI_API_KEY or not GEMINI_MODEL:
        if not _translation_warned:
            log.warning(
                "Tradução de descrições de jogos/ofertas desativada: "
                "configure GEMINI_API_KEY e GEMINI_MODEL no ambiente."
            )
            _translation_warned = True
        return original

    try:
        with sqlite3.connect(SENT_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS offer_translation_cache (
                    source_text TEXT PRIMARY KEY,
                    translated_text TEXT NOT NULL,
                    translated_at TEXT NOT NULL
                )
            """)
            row = conn.execute(
                "SELECT translated_text FROM offer_translation_cache WHERE source_text = ?",
                (original,),
            ).fetchone()
            if row and row[0]:
                return str(row[0])
    except sqlite3.Error:
        log.exception("Não foi possível ler o cache de traduções; tentando traduzir sem cache.")

    try:
        translated = await asyncio.to_thread(_translate_game_description_sync, original)
        translated = translated.strip() or original
    except Exception:
        log.exception("Falha traduzindo descrição de jogo/oferta; será usado o texto original.")
        return original

    try:
        with sqlite3.connect(SENT_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS offer_translation_cache (
                    source_text TEXT PRIMARY KEY,
                    translated_text TEXT NOT NULL,
                    translated_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "INSERT OR REPLACE INTO offer_translation_cache "
                "(source_text, translated_text, translated_at) VALUES (?, ?, ?)",
                (original, translated, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
    except sqlite3.Error:
        log.exception("Não foi possível salvar a tradução no cache; tradução ainda será usada.")

    return translated


# ---------------------------------------------------------------- banco local

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


def mark_offer_sent(item_key: str) -> None:
    with sqlite3.connect(SENT_DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sent_items(item_key, sent_at) VALUES (?, ?)",
            (item_key, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def count_sent_items() -> int:
    with sqlite3.connect(SENT_DB_PATH) as conn:
        return conn.execute("SELECT COUNT(*) FROM sent_items").fetchone()[0]


# ------------------------------------------------------------------- ofertas

def money_brl(cents: Any) -> str | None:
    try:
        return f"R$ {int(cents) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return None


async def fetch_gamerpower(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    try:
        async with session.get(
            "https://www.gamerpower.com/api/giveaways",
            params={"type": "game"},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status == 429:
                log.warning("GamerPower limitou requisições.")
                return []
            resp.raise_for_status()
            data = await resp.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        log.exception("Falha consultando GamerPower.")
        return []
    if not isinstance(data, list):
        return []
    items = []
    for g in data:
        title = g.get("title")
        url = g.get("open_giveaway_url") or g.get("gamerpower_url")
        if not title or not url:
            continue
        end_date = str(g.get("end_date") or "").strip()
        if not end_date or end_date.upper() == "N/A":
            end_date = "Sem data informada"
        raw_platforms = str(g.get("platforms") or "Plataforma não informada")
        platform_names = {
            "PC": "PC", "Steam": "Steam", "Epic Games Store": "Epic Games Store",
            "GOG": "GOG", "itch.io": "itch.io", "PlayStation": "PlayStation",
            "Xbox One": "Xbox One", "Xbox Series X|S": "Xbox Series X|S",
            "Nintendo Switch": "Nintendo Switch", "Android": "Android", "iOS": "iOS",
            "Origin": "EA app", "Ubisoft Connect": "Ubisoft Connect",
        }
        translated_platforms = [platform_names.get(part.strip(), part.strip()) for part in raw_platforms.split(",")]
        description = (g.get("description") or "Jogo gratuito por tempo limitado. Confira as condições e a data de encerramento na página da oferta.").strip()
        # A API não oferece uma descrição localizada de forma consistente; não traduzimos
        # automaticamente textos arbitrários para evitar publicar traduções inventadas.
        items.append({
            "key": f"gamerpower:{g.get('id') or title}",
            "title": title,
            "url": url,
            "image": g.get("thumbnail"),
            "description": description,
            "category": "JOGO GRÁTIS / GIVEAWAY",
            "platform": ", ".join(translated_platforms),
            "price": "Grátis",
            "source": "GamerPower",
            "end_date": end_date,
            "kind": "game",
        })
    return items


async def fetch_steam_offers(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    try:
        async with session.get(
            "https://store.steampowered.com/api/featuredcategories/",
            params={"cc": "br", "l": "brazilian"},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status == 429:
                log.warning("Steam Store limitou requisições.")
                return []
            resp.raise_for_status()
            data = await resp.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        log.exception("Falha consultando Steam Store.")
        return []
    if not isinstance(data, dict):
        return []
    items = []
    for section_name in ("freegames", "specials"):
        section = data.get(section_name) or {}
        for game in section.get("items", []) if isinstance(section, dict) else []:
            app_id = game.get("id")
            title = game.get("name")
            if not app_id or not title:
                continue
            discount = int(game.get("discount_percent") or 0)
            final_cents = game.get("final_price")
            initial_cents = game.get("original_price")
            actually_free = bool(game.get("is_free")) or final_cents == 0
            if not actually_free and (final_cents is None or discount <= 0):
                continue
            final_price = "Grátis" if actually_free else money_brl(final_cents)
            original_price = None if actually_free else money_brl(initial_cents)
            if not final_price:
                continue
            items.append({
                "key": f"steam:{app_id}:{discount}:{final_cents}",
                "steam_app_id": int(app_id),
                "title": title,
                "url": f"https://store.steampowered.com/app/{app_id}/?cc=br",
                "image": game.get("header_image"),
                "description": "Oferta regional da Steam. Confira a página da loja para condições e validade.",
                "category": "JOGO GRÁTIS NA STEAM" if actually_free else f"PROMOÇÃO STEAM • {discount}% OFF",
                "platform": "Steam",
                "price": final_price,
                "original_price": original_price,
                "discount": discount,
                "source": "Steam Store Brasil",
                "end_date": "Consulte a página da loja",
                "kind": "game" if actually_free else "promo",
            })
    return items



async def fetch_epic_free_games(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Consulta a listagem pública de jogos promocionalmente grátis da Epic em pt-BR.

    O endpoint é o backend público usado pela loja web; não é uma API oficial
    com SLA, portanto falhas são toleradas e não interrompem as outras fontes.
    """
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    try:
        async with session.get(
            url,
            params={"locale": "pt-BR", "country": "BR", "allowCountries": "BR"},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status == 429:
                log.warning("Epic Games Store limitou requisições.")
                return []
            resp.raise_for_status()
            payload = await resp.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        log.exception("Falha consultando jogos grátis da Epic Games Store.")
        return []

    elements = (((payload or {}).get("data") or {}).get("Catalog") or {}).get("searchStore", {}).get("elements", [])
    items: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for game in elements if isinstance(elements, list) else []:
        promotions = game.get("promotions") or {}
        promotional_offers = promotions.get("promotionalOffers") or []
        if not promotional_offers:
            continue
        active_offers = []
        for group in promotional_offers:
            for offer in group.get("promotionalOffers") or []:
                end_raw = offer.get("endDate")
                try:
                    end_dt = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00")) if end_raw else None
                    if end_dt is not None and end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    end_dt = None
                if end_dt is None or end_dt > now:
                    active_offers.append(offer)
        if not active_offers:
            continue
        price_data = ((game.get("price") or {}).get("totalPrice") or {})
        discount_price = price_data.get("discountPrice")
        original_price = price_data.get("originalPrice")
        try:
            discount_is_zero = float(discount_price) == 0
            original_is_positive = original_price is None or float(original_price) > 0
        except (TypeError, ValueError):
            continue
        if not discount_is_zero or not original_is_positive:
            continue
        slug = game.get("productSlug") or game.get("urlSlug")
        product_id = game.get("id")
        title = game.get("title")
        if not title or not product_id:
            continue
        if slug:
            game_url = f"https://store.epicgames.com/pt-BR/p/{slug}"
        else:
            game_url = f"https://store.epicgames.com/pt-BR/"
        images = game.get("keyImages") or []
        image_url = next((im.get("url") for im in images if im.get("type") in {"OfferImageWide", "DieselGameBoxWide", "Thumbnail"} and im.get("url")), None)
        end_dates = [str(o.get("endDate")) for o in active_offers if o.get("endDate")]
        end_date = min(end_dates) if end_dates else "Consulte a loja"
        items.append({
            "key": f"epic:{product_id}:{end_date}",
            "title": title,
            "url": game_url,
            "image": image_url,
            "description": "Jogo gratuito por tempo limitado na Epic Games Store. Confira a página da loja para confirmar a disponibilidade e o prazo.",
            "category": "JOGO GRÁTIS POR TEMPO LIMITADO",
            "platform": "Epic Games Store (PC)",
            "price": "Grátis",
            "source": "Epic Games Store — região Brasil",
            "end_date": end_date.replace("T", " ").replace("Z", " UTC"),
            "kind": "game",
        })
    return items


async def enrich_with_gg_deals_prices(session: aiohttp.ClientSession, items: list[dict[str, Any]]) -> None:
    """Acrescenta comparação GG.deals em BRL sem substituir o preço regional da Steam."""
    if not GG_DEALS_API_KEY:
        return
    app_ids = sorted({int(item["steam_app_id"]) for item in items if item.get("steam_app_id")})
    if not app_ids:
        return
    # GG.deals permite até 100 IDs por consulta; as ofertas da Steam normalmente cabem em um lote.
    for start in range(0, len(app_ids), 100):
        batch = app_ids[start:start + 100]
        try:
            async with session.get(
                "https://api.gg.deals/v1/prices/by-steam-app-id/",
                params={"key": GG_DEALS_API_KEY, "ids": ",".join(map(str, batch)), "region": "br"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                # Ler o corpo antes de tratar erros: a API costuma informar no JSON
                # a causa exata de um HTTP 400. Nunca registrar a URL completa, pois
                # ela contém a chave de API como parâmetro.
                body = await resp.text()
                if resp.status == 429:
                    log.warning("GG.deals atingiu o limite da API; preços complementares ignorados neste ciclo.")
                    return
                if resp.status >= 400:
                    detail = body[:500].replace("\n", " ").strip() or "sem detalhes no corpo da resposta"
                    try:
                        error_payload = json.loads(body)
                        if isinstance(error_payload, dict):
                            error_data = error_payload.get("data")
                            if isinstance(error_data, dict):
                                detail = str(error_data.get("message") or error_data.get("name") or detail)[:500]
                    except (ValueError, TypeError):
                        pass
                    log.warning(
                        "GG.deals respondeu HTTP %s (região br, %s IDs). Detalhe: %s. "
                        "Preços complementares ignorados neste ciclo; confira chave, plano e parâmetros.",
                        resp.status, len(batch), detail,
                    )
                    return
                try:
                    payload = json.loads(body)
                except (ValueError, TypeError):
                    log.warning("GG.deals retornou uma resposta que não é JSON válido; preços ignorados neste ciclo.")
                    return
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            log.exception("Falha de rede consultando preços regionais do GG.deals.")
            return
        if isinstance(payload, dict) and payload.get("success") is False:
            error_data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            log.warning(
                "GG.deals informou falha: %s. Preços complementares ignorados neste ciclo.",
                str(error_data.get("message") or error_data.get("name") or "erro sem detalhes")[:500],
            )
            return
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        for item in items:
            app_id = item.get("steam_app_id")
            if app_id is None or str(app_id) not in data:
                continue
            game = data.get(str(app_id))
            if not isinstance(game, dict):
                continue
            prices = game.get("prices") or {}
            currency = str(prices.get("currency") or "").upper()
            # Nunca mostrar valor estrangeiro como se fosse BRL.
            if currency not in {"BRL", "R$"}:
                continue
            retail = prices.get("currentRetail")
            keyshop = prices.get("currentKeyshops")
            item["gg_deals_url"] = game.get("url") or "https://gg.deals/"
            item["gg_deals_retail"] = money_decimal_brl(retail)
            item["gg_deals_keyshops"] = money_decimal_brl(keyshop)
            item["gg_deals_currency"] = currency


def money_decimal_brl(value: Any) -> str | None:
    try:
        amount = float(str(value).replace(",", "."))
        return "R$ " + f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return None

def make_offer_embed(item: dict[str, Any]) -> discord.Embed:
    """Cartão compacto e visual: título, descrição, preço e imagem dentro do embed."""
    titulo = str(item.get("title") or "Jogo / oferta")[:250]
    descricao = str(item.get("description") or "Confira os detalhes na página da oferta.")[:1800]
    plataforma = str(item.get("platform", "Plataforma não informada"))[:250]
    preco = str(item.get("price", "Consulte a loja"))
    original = item.get("original_price")
    desconto = item.get("discount")
    url = str(item.get("url", ""))
    fonte = str(item.get("source", "Loja"))
    validade = str(item.get("end_date") or "").strip()

    cor = discord.Color.green() if item.get("kind") == "game" else discord.Color.orange()
    embed = discord.Embed(title=titulo, url=url or None, description=descricao, color=cor)

    if item.get("kind") == "promo" and original and original != preco:
        atual = f"**{preco}**"
        if desconto:
            atual += f"  ·  **-{desconto}%**"
        embed.add_field(name="Agora", value=atual[:1024], inline=True)
        embed.add_field(name="Preço normal", value=str(original)[:1024], inline=True)
    else:
        embed.add_field(name="Preço", value=f"**{preco}**"[:1024], inline=True)

    # Metadados discretos, sem campo redundante de categoria/tipo.
    meta = [plataforma]
    if validade and validade.lower() not in {"consulte a loja", "sem data informada", "n/a"}:
        meta.append(f"Até {validade}")
    embed.add_field(name=" ", value=" · ".join(meta)[:1024], inline=False)

    gg_url = item.get("gg_deals_url")
    gg_retail = item.get("gg_deals_retail")
    gg_keyshops = item.get("gg_deals_keyshops")
    if gg_url and (gg_retail or gg_keyshops):
        comparison = []
        if gg_retail:
            comparison.append(f"Lojas oficiais: **{gg_retail}**")
        if gg_keyshops:
            comparison.append(f"Keyshops: **{gg_keyshops}**")
        comparison.append(f"[Comparar preços]({gg_url})")
        embed.add_field(name="GG.deals", value=" · ".join(comparison), inline=False)

    embed.set_footer(text=f"Fonte: {fonte}")
    image_url = str(item.get("image") or "")
    if image_url.startswith("https://"):
        embed.set_image(url=image_url)
    return embed


class OfertaView(discord.ui.View):
    """Botão simples de acesso à página da oferta."""
    def __init__(self, url: str):
        super().__init__(timeout=None)
        if url.startswith(("https://", "http://")):
            self.add_item(discord.ui.Button(label="Ver oferta", style=discord.ButtonStyle.link, url=url))


async def preparar_imagem_oferta(
    session: aiohttp.ClientSession, item: dict[str, Any]
) -> discord.File | None:
    """Baixa a arte do jogo para enviá-la como imagem destacada fora do embed."""
    image_url = str(item.get("image") or "")
    if not image_url.startswith("https://"):
        return None
    try:
        async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None
            content_type = resp.headers.get("Content-Type", "").lower()
            if not content_type.startswith("image/"):
                return None
            data = await resp.read()
            if not data or len(data) > 8 * 1024 * 1024:
                return None
        # Discord reconhece a extensão pelo nome; o nome genérico cobre PNG/JPEG/WebP.
        ext = ".png" if "png" in content_type else ".webp" if "webp" in content_type else ".jpg"
        return discord.File(BytesIO(data), filename=f"jogo{ext}")
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        log.debug("Não foi possível baixar a imagem da oferta %s.", item.get("key"))
        return None


class Ofertas(commands.Cog):
    """Jogos grátis (GamerPower/Epic/Steam) e promoções Steam com comparação GG.deals opcional."""

    def __init__(self, bot):
        self.bot = bot
        self.http_session: aiohttp.ClientSession | None = None

    async def cog_load(self):
        self.http_session = aiohttp.ClientSession(headers={"User-Agent": "NaraBot/1.0"})
        init_offers_db()
        self.offers_loop.start()

    async def cog_unload(self):
        self.offers_loop.cancel()
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    @tasks.loop(minutes=OFFERS_CHECK_MINUTES)
    async def offers_loop(self):
        if not self.http_session:
            return
        try:
            offers = await asyncio.gather(
                fetch_gamerpower(self.http_session),
                fetch_steam_offers(self.http_session),
                fetch_epic_free_games(self.http_session),
                return_exceptions=True,
            )
            items = []
            for result in offers:
                if isinstance(result, list):
                    items.extend(result)
                elif isinstance(result, Exception):
                    log.error("Erro consultando uma fonte de ofertas: %r", result)

            unique = {item["key"]: item for item in items}
            # GG.deals é complementar: não é necessário para o bot continuar funcionando.
            await enrich_with_gg_deals_prices(self.http_session, list(unique.values()))

            # Primeira execução: só registra o que já existe, sem postar.
            if SEED_OFFERS_ON_FIRST_RUN and unique and count_sent_items() == 0:
                for item in unique.values():
                    mark_offer_sent(item["key"])
                log.info("Primeira execução: %s ofertas registradas sem postar.", len(unique))
                return

            sent_this_cycle = 0
            for item in unique.values():
                if offer_already_sent(item["key"]):
                    continue
                if item["kind"] == "promo" and item.get("discount", 0) < MIN_PROMO_DISCOUNT:
                    continue
                # As tarefas de loop não têm interaction; usa o primeiro guild disponível.
                guild_id = self.bot.guilds[0].id if self.bot.guilds else 0
                if item["kind"] == "game":
                    target_id = await GuildConfig.get(self.bot.db, guild_id, "games_channel") or GAMES_CHANNEL_ID
                else:
                    target_id = await GuildConfig.get(self.bot.db, guild_id, "promos_channel") or PROMOS_CHANNEL_ID
                if not target_id:
                    log.warning("Defina os canais de jogos/promoções via /adm ou config.py para ativar os avisos de ofertas.")
                    return
                channel = await get_text_channel(self.bot, target_id)
                if channel is None:
                    continue
                try:
                    # Traduz a descrição da oferta antes de publicar. O cache evita
                    # chamadas repetidas para descrições idênticas.
                    item["description"] = await traduzir_descricao_oferta(
                        str(item.get("description") or "")
                    )
                    # Enviar a arte como anexo separado costuma dar mais destaque visual
                    # do que a imagem embutida no cartão, respeitando o limite do Discord.
                    # Use a URL original dentro do embed. Enviar o arquivo anexado
                    # junto com attachment:// fez alguns clientes mostrarem a imagem
                    # separada do cartão, quebrando o layout minimalista.
                    await channel.send(
                        embed=make_offer_embed(item),
                        view=OfertaView(str(item.get("url", ""))),
                    )
                    mark_offer_sent(item["key"])
                    sent_this_cycle += 1
                    await asyncio.sleep(1.2)
                    if sent_this_cycle >= MAX_OFFERS_PER_CHECK:
                        break
                except discord.HTTPException:
                    log.exception("Falha publicando oferta: %s", item.get("title"))
            log.info("Ofertas verificadas: %s; novas publicadas: %s", len(unique), sent_this_cycle)
        except Exception:
            log.exception("Erro na rotina de ofertas.")

    @offers_loop.before_loop
    async def before_offers_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="status_ofertas", description="Mostra se o monitoramento de ofertas está configurado e funcionando.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status_ofertas(self, interaction: discord.Interaction):
        games_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "games_channel") or GAMES_CHANNEL_ID
        promos_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "promos_channel") or PROMOS_CHANNEL_ID
        games = f"<#{games_id}>" if games_id else "Não configurado"
        promos = f"<#{promos_id}>" if promos_id else "Não configurado"
        await interaction.response.send_message(
            f"**Jogos grátis:** {games}\n**Promoções:** {promos}\n"
            f"**Verificação:** a cada {OFFERS_CHECK_MINUTES} minutos.\n"
            f"**Desconto mínimo para promoções:** {MIN_PROMO_DISCOUNT}%\n"
            f"**Fontes:** Steam Brasil, GamerPower e Epic Games Store\n"
            f"**Comparação GG.deals:** {'Ativa (região Brasil)' if GG_DEALS_API_KEY else 'Desativada — configure GG_DEALS_API_KEY no .env'}",
            ephemeral=True,
        )

    async def cog_app_command_error(self, interaction, error):
        await erro_comando(interaction, error)


async def setup(bot):
    await bot.add_cog(Ofertas(bot))
