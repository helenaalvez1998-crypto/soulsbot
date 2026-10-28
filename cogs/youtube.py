import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import (
    YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, YOUTUBE_FEED_URL, ATOM, YT,
    VIDEO_CHANNEL_ID, LIVE_CHANNEL_ID, ROLE_VIDEO, ROLE_LIVE,
    YOUTUBE_VIDEO_CHECK_SECONDS, YOUTUBE_LIVE_CHECK_MINUTES,
    LIVE_START_HOUR, LIVE_END_HOUR, BRAZIL_TZ,
)
from admin_config import GuildConfig
from utils import get_text_channel, erro_comando

log = logging.getLogger("youtube")

# Marcador: o YouTube respondeu normalmente, mas o canal ainda não tem nenhum vídeo.
SEM_VIDEOS = {"id": "__sem_videos__", "title": "", "url": ""}


def com_mencao(channel, nome_cargo: str, texto: str) -> tuple[str, discord.AllowedMentions]:
    """Põe a menção do cargo na frente do texto (se o cargo existir) e libera só essa menção."""
    guild = getattr(channel, "guild", None)
    cargo = discord.utils.get(guild.roles, name=nome_cargo) if guild else None
    if cargo is None:
        return texto, discord.AllowedMentions.none()
    return f"{cargo.mention} {texto}", discord.AllowedMentions(roles=[cargo])



class YouTube(commands.Cog):
    """Avisos de vídeos e lives do canal oQuasepro."""

    def __init__(self, bot):
        self.bot = bot
        self.http_session: aiohttp.ClientSession | None = None
        self.latest_video_id: str | None = None
        self.current_live_video_id: str | None = None
        self.live_state_initialized = False

    async def cog_load(self):
        self.http_session = aiohttp.ClientSession(headers={"User-Agent": "oQuaseproYouTubeNotifications/1.0"})
        self.video_loop.start()
        self.live_loop.start()

    async def cog_unload(self):
        self.video_loop.cancel()
        self.live_loop.cancel()
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    async def fetch_latest_video(self) -> dict[str, str] | None:
        """Tenta o feed RSS (grátis). Se o YouTube recusar, usa a API (1 unidade de cota por consulta)."""
        video = await self._latest_via_rss()
        if video:
            return video
        return await self._latest_via_api()

    async def _latest_via_api(self) -> dict[str, str] | None:
        if not self.http_session or not YOUTUBE_API_KEY or not YOUTUBE_CHANNEL_ID.startswith("UC"):
            return None
        params = {
            "part": "snippet",
            "playlistId": "UU" + YOUTUBE_CHANNEL_ID[2:],  # playlist de uploads do canal
            "maxResults": "1",
            "key": YOUTUBE_API_KEY,
        }
        try:
            async with self.http_session.get(
                "https://www.googleapis.com/youtube/v3/playlistItems",
                params=params,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    erros = payload.get("error", {}).get("errors", [])
                    if response.status == 404 and any(e.get("reason") == "playlistNotFound" for e in erros):
                        # Canal sem nenhum upload: o YouTube nem cria a playlist de uploads.
                        log.info("O YouTube não tem vídeos para o canal %s (canal sem uploads).", YOUTUBE_CHANNEL_ID)
                        return SEM_VIDEOS
                    log.error(
                        "YouTube API (playlistItems) retornou HTTP %s: %s. "
                        "Confira se YOUTUBE_CHANNEL_ID é o ID do canal no YouTube (começa com UC).",
                        response.status,
                        payload.get("error", {}).get("message", "erro sem detalhes"),
                    )
                    return None
            items = payload.get("items", [])
            if not items:
                return SEM_VIDEOS
            snippet = items[0].get("snippet", {})
            video_id = snippet.get("resourceId", {}).get("videoId")
            if not video_id:
                return None
            return {
                "id": video_id,
                "title": snippet.get("title") or "Vídeo novo",
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            log.exception("Falha ao consultar a API de uploads do YouTube.")
            return None

    async def _latest_via_rss(self) -> dict[str, str] | None:
        if not self.http_session:
            return None
        try:
            async with self.http_session.get(
                YOUTUBE_FEED_URL,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                response.raise_for_status()
                xml_text = await response.text()
            root = ET.fromstring(xml_text)
            entry = root.find(f"{ATOM}entry")
            if entry is None:
                return SEM_VIDEOS
            video_id = entry.findtext(f"{YT}videoId")
            title = entry.findtext(f"{ATOM}title") or "Vídeo novo"
            link_el = entry.find(f"{ATOM}link")
            url = link_el.attrib.get("href") if link_el is not None else None
            if not video_id:
                return None
            return {
                "id": video_id,
                "title": title,
                "url": url or f"https://www.youtube.com/watch?v={video_id}",
            }
        except aiohttp.ClientResponseError as e:
            log.warning("Feed RSS do YouTube recusou (HTTP %s). Tentando pela API.", e.status)
            return None
        except (aiohttp.ClientError, asyncio.TimeoutError, ET.ParseError):
            log.warning("Falha ao consultar o feed RSS do YouTube. Tentando pela API.")
            return None

    async def fetch_video_kind(self, video_id: str) -> str:
        """Diz se uma entrada do feed é 'video' comum ou 'live' (ao vivo, agendada ou
        gravação de live). Custa 1 unidade de cota. Sem chave da API, assume 'video'."""
        if not self.http_session or not YOUTUBE_API_KEY:
            return "video"
        params = {
            "part": "snippet,liveStreamingDetails",
            "id": video_id,
            "key": YOUTUBE_API_KEY,
        }
        try:
            async with self.http_session.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params=params,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    log.error(
                        "YouTube API (videos) retornou HTTP %s: %s",
                        response.status,
                        payload.get("error", {}).get("message", "erro sem detalhes"),
                    )
                    return "video"
            items = payload.get("items", [])
            if not items:
                return "video"
            item = items[0]
            estado = item.get("snippet", {}).get("liveBroadcastContent", "none")
            if estado in ("live", "upcoming") or item.get("liveStreamingDetails"):
                return "live"
            return "video"
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            log.exception("Falha ao classificar o vídeo %s.", video_id)
            return "video"

    async def fetch_live_stream(self) -> dict[str, str] | None:
        """Procura uma live ativa neste canal. Exige chave da YouTube Data API."""
        if not self.http_session or not YOUTUBE_API_KEY:
            log.error("Defina YOUTUBE_API_KEY nas variáveis de ambiente.")
            return None

        params = {
            "part": "snippet",
            "channelId": YOUTUBE_CHANNEL_ID,
            "eventType": "live",
            "type": "video",
            "maxResults": "1",
            "key": YOUTUBE_API_KEY,
        }
        try:
            async with self.http_session.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    log.error(
                        "YouTube API retornou HTTP %s: %s",
                        response.status,
                        payload.get("error", {}).get("message", "erro sem detalhes"),
                    )
                    return None
            items = payload.get("items", [])
            if not items:
                return None
            item = items[0]
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                return None
            return {
                "id": video_id,
                "title": item.get("snippet", {}).get("title", "Estou ao vivo!"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": item.get("snippet", {}).get("thumbnails", {}).get("high", {}).get("url", ""),
            }
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            log.exception("Falha ao consultar lives do YouTube.")
            return None

    # -------------------------------------------------------------- vídeos

    @tasks.loop(seconds=YOUTUBE_VIDEO_CHECK_SECONDS)
    async def video_loop(self):
        latest = await self.fetch_latest_video()
        if not latest:
            return

        # A primeira consulta só marca a referência, para não anunciar vídeos antigos.
        if self.latest_video_id is None:
            self.latest_video_id = latest["id"]
            if latest["id"] == SEM_VIDEOS["id"]:
                log.info("Canal ainda sem vídeos. O primeiro vídeo publicado será anunciado.")
            else:
                log.info("Feed de vídeos inicializado.")
            return

        if latest["id"] == self.latest_video_id:
            return

        self.latest_video_id = latest["id"]

        # Lives (e gravações de lives) também aparecem no feed. Elas têm aviso próprio.
        if await self.fetch_video_kind(latest["id"]) == "live":
            log.info("Entrada do feed ignorada (é uma live): %s", latest["id"])
            return

        video_ch_id = await GuildConfig.get(self.bot.db, self.guild_id, "video_channel") or VIDEO_CHANNEL_ID
        channel = await get_text_channel(self.bot, video_ch_id)
        if channel is None:
            return

        embed = discord.Embed(
            title=latest["title"][:250],
            url=latest["url"],
            description=f"Um vídeo novo foi publicado no canal **oQuasepro**.\n\n[Assistir agora]({latest['url']})",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_author(name="oQuasepro", url="https://www.youtube.com/@oQuasepro")
        embed.set_image(url=f"https://i.ytimg.com/vi/{latest['id']}/hqdefault.jpg")
        embed.set_footer(text="Notificação automática do YouTube")
        role_video_name = None
        role_video_id = await GuildConfig.get(self.bot.db, self.guild_id, "role_video") or ROLE_VIDEO
        if role_video_id:
            role_obj = channel.guild.get_role(role_video_id) if channel.guild else None
            role_video_name = role_obj.name if role_obj else None
        content, mentions = com_mencao(channel, role_video_name or "", "📺 **Vídeo novo no YouTube!**")
        try:
            await channel.send(content=content, embed=embed, allowed_mentions=mentions)
            log.info("Aviso de vídeo enviado: %s", latest["id"])
        except discord.HTTPException:
            log.exception("Não foi possível enviar o aviso de vídeo.")

    @video_loop.before_loop
    async def before_video_loop(self):
        await self.bot.wait_until_ready()

    # --------------------------------------------------------------- lives

    @tasks.loop(minutes=YOUTUBE_LIVE_CHECK_MINUTES)
    async def live_loop(self):
        # Só consulta no horário habitual de live (horário de Brasília).
        now_local = datetime.now(BRAZIL_TZ)
        if not (LIVE_START_HOUR <= now_local.hour < LIVE_END_HOUR):
            return

        if not YOUTUBE_API_KEY:
            log.error("Defina YOUTUBE_API_KEY nas variáveis de ambiente.")
            return

        live = await self.fetch_live_stream()

        # Primeira consulta: só registra o estado atual. Se já estiver ao vivo nesse
        # momento, não manda um aviso atrasado.
        if not self.live_state_initialized:
            self.live_state_initialized = True
            self.current_live_video_id = live["id"] if live else None
            log.info("Estado inicial de live registrado.")
            return

        # Sem live: zera o estado, para a próxima live ser anunciada.
        if live is None:
            self.current_live_video_id = None
            return

        if self.current_live_video_id is None:
            self.current_live_video_id = live["id"]
        elif live["id"] == self.current_live_video_id:
            return
        else:
            self.current_live_video_id = live["id"]

        live_ch_id = await GuildConfig.get(self.bot.db, self.guild_id, "live_channel") or LIVE_CHANNEL_ID
        channel = await get_text_channel(self.bot, live_ch_id)
        if channel is None:
            return

        embed = discord.Embed(
            title="oQuasepro está AO VIVO no YouTube!",
            url=live["url"],
            description=f"**{live['title']}**\n\n[Assistir à live agora]({live['url']})",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_author(name="oQuasepro", url="https://www.youtube.com/@oQuasepro")
        thumbnail = live.get("thumbnail")
        if thumbnail:
            embed.set_image(url=thumbnail)
        embed.set_footer(text="Notificação automática do YouTube")
        role_live_name = None
        role_live_id = await GuildConfig.get(self.bot.db, self.guild_id, "role_live") or ROLE_LIVE
        if role_live_id:
            role_obj = channel.guild.get_role(role_live_id) if channel.guild else None
            role_live_name = role_obj.name if role_obj else None
        content, mentions = com_mencao(channel, role_live_name or "", "🔴 **A live começou no YouTube!**")
        try:
            await channel.send(content=content, embed=embed, allowed_mentions=mentions)
            log.info("Aviso de live enviado: %s", live["id"])
        except discord.HTTPException:
            log.exception("Não foi possível enviar o aviso de live.")

    @live_loop.before_loop
    async def before_live_loop(self):
        await self.bot.wait_until_ready()


    @app_commands.command(name="teste_video", description="[MOD] Envia um teste para verificar os avisos de novos vídeos do YouTube.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def teste_video(self, interaction: discord.Interaction):
        video_ch = await GuildConfig.get(self.bot.db, interaction.guild_id, "video_channel") or VIDEO_CHANNEL_ID
        await interaction.response.send_message(f"Canal de vídeos configurado: <#{video_ch}>.", ephemeral=True)

    @app_commands.command(name="teste_live", description="[MOD] Envia um teste para verificar os avisos de transmissões ao vivo.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def teste_live(self, interaction: discord.Interaction):
        live_ch = await GuildConfig.get(self.bot.db, interaction.guild_id, "live_channel") or LIVE_CHANNEL_ID
        await interaction.response.send_message(
            f"Canal de lives configurado: <#{live_ch}>. "
            "A detecção consulta a YouTube Data API periodicamente.",
            ephemeral=True,
        )

    @app_commands.command(name="status_youtube", description="[MOD] Mostra se os avisos do YouTube estão configurados corretamente.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status_youtube(self, interaction: discord.Interaction):
        key_status = "configurada" if YOUTUBE_API_KEY else "FALTANDO"
        video_ch = await GuildConfig.get(self.bot.db, interaction.guild_id, "video_channel") or VIDEO_CHANNEL_ID
        live_ch = await GuildConfig.get(self.bot.db, interaction.guild_id, "live_channel") or LIVE_CHANNEL_ID
        await interaction.response.send_message(
            f"**Canal YouTube:** `{YOUTUBE_CHANNEL_ID}`\n"
            f"**Vídeos:** <#{video_ch}>\n"
            f"**Lives:** <#{live_ch}>\n"
            f"**Chave da API:** {key_status}\n"
            f"**Verificação de vídeos:** a cada {YOUTUBE_VIDEO_CHECK_SECONDS} segundos\n"
            f"**Verificação de lives:** a cada {YOUTUBE_LIVE_CHECK_MINUTES} minutos, "
            f"entre {LIVE_START_HOUR}h e {LIVE_END_HOUR % 24}h (horário de Brasília)",
            ephemeral=True,
        )

    async def cog_app_command_error(self, interaction, error):
        await erro_comando(interaction, error)


async def setup(bot):
    await bot.add_cog(YouTube(bot))
