import logging
import re
import io
import datetime as dt
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from admin_config import GuildConfig
from cogs.platinas import eh_moderador
from levels import nivel_por_xp, patente_por_nivel
from utils import get_text_channel

PODIO = [("🥇", config.COR_OURO), ("🥈", config.COR_PRATA), ("🥉", 0xCD7F32)]


class BotaoPerfilGladiador(discord.ui.DynamicItem[discord.ui.Button], template=r"colizeu:perfil:(?P<uid>[0-9]+)"):
    """Lupa persistente que abre o santuário do gladiador. O ID vai no custom_id,
    então continua funcionando após reiniciar o bot."""

    def __init__(self, user_id: int, nome: str = "Perfil", row: int | None = None):
        super().__init__(
            discord.ui.Button(
                label=nome[:80],
                emoji="🔎",
                style=discord.ButtonStyle.secondary,
                custom_id=f"colizeu:perfil:{user_id}",
                row=row,
            )
        )
        self.user_id = user_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        return cls(int(match["uid"]), item.label or "Perfil")

    async def callback(self, interaction: discord.Interaction):
        # O Santuario.visitar já faz o defer, libera a thread e responde com o link.
        santuario = interaction.client.get_cog("Santuario")
        if santuario is None:
            return await interaction.response.send_message("Os santuários estão indisponíveis no momento.", ephemeral=True)
        # self.user_id vem do custom_id do botão clicado (dono do card), nunca de quem clicou.
        logging.info("Colizeu: %s abriu a lupa do santuário de %s", interaction.user.id, self.user_id)
        await santuario.visitar(interaction, self.user_id)


def _view_podio(nomes: list[tuple[int, str]]) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for linha, (uid, nome) in enumerate(nomes):  # um botão por linha, na ordem dos cards
        view.add_item(BotaoPerfilGladiador(uid, nome, row=linha))
    return view


class Colizeu(commands.Cog):
    """Mantém uma mensagem-painel sempre atualizada no canal #colizeu."""

    def __init__(self, bot):
        self.bot = bot
        # Cacheia cada catálogo até a lista de platinas aprovadas mudar.
        self._catalogos_cache: dict[int, tuple[tuple, bytes]] = {}

    async def cog_load(self):
        self.bot.add_dynamic_items(BotaoPerfilGladiador)
        self.loop_atualizar.start()

    async def cog_unload(self):
        self.bot.remove_dynamic_items(BotaoPerfilGladiador)
        self.loop_atualizar.cancel()

    @tasks.loop(minutes=10)
    async def loop_atualizar(self):
        try:
            await self.atualizar()
        except Exception:
            logging.exception("Falha ao atualizar o painel do Colizeu")

    @loop_atualizar.before_loop
    async def _antes(self):
        await self.bot.wait_until_ready()

    async def _membro(self, guild: discord.Guild, user_id: int):
        m = guild.get_member(user_id)
        if m:
            return m
        try:
            return await guild.fetch_member(user_id)
        except discord.HTTPException:
            return None

    async def _foto_platina(self, guild: discord.Guild, platina) -> str | None:
        """Busca a mensagem original para obter um link de imagem válido (links do Discord expiram)."""
        mod_ch_id = await GuildConfig.get(self.bot.db, guild.id, "mod_channel") or config.MOD_CHANNEL_ID
        if not mod_ch_id:
            return None
        canal = await get_text_channel(self.bot, mod_ch_id)
        if canal and platina["proof_msg_id"]:
            try:
                msg = await canal.fetch_message(platina["proof_msg_id"])
                if msg.embeds and msg.embeds[0].image:
                    return msg.embeds[0].image.url
                if msg.attachments:
                    return msg.attachments[0].url
            except discord.HTTPException:
                pass
        return platina.get("proof_url")

    async def _catalogo_platinas(self, guild: discord.Guild, platinas) -> discord.File | None:
        """Gera uma folha visual com uma miniatura por jogo platinado."""
        if not platinas:
            return None
        signature = tuple((p["id"], p["proof_msg_id"], p["proof_url"]) for p in platinas)
        user_id = int(platinas[0]["user_id"])
        cached = self._catalogos_cache.get(user_id)
        filename = f"catalogo_platinas_{user_id}.jpg"
        if cached and cached[0] == signature:
            return discord.File(io.BytesIO(cached[1]), filename=filename)

        try:
            from PIL import Image, ImageDraw, ImageFont, ImageOps
        except ImportError:
            logging.warning("Pillow não está instalado; catálogo visual desativado temporariamente.")
            return None

        mod_ch_id = await GuildConfig.get(self.bot.db, guild.id, "mod_channel") or config.MOD_CHANNEL_ID
        if not mod_ch_id:
            return None
        canal = await get_text_channel(self.bot, mod_ch_id)
        if canal is None:
            return None
        thumbs = []
        timeout = aiohttp.ClientTimeout(total=12, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for platina in platinas:
                url = None
                try:
                    msg_id = platina["proof_msg_id"]
                    if msg_id:
                        msg = await canal.fetch_message(msg_id)
                        candidates = [a for a in msg.attachments if
                                      (a.content_type or "").startswith("image/") or
                                      a.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))]
                        if candidates:
                            url = candidates[0].url
                        elif msg.embeds and msg.embeds[0].image:
                            url = msg.embeds[0].image.url
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass
                if not url:
                    url = platina["proof_url"]
                if not url:
                    continue
                try:
                    async with session.get(url) as response:
                        if response.status != 200:
                            continue
                        dados = await response.read()
                    imagem = Image.open(io.BytesIO(dados)).convert("RGB")
                    # Miniaturas de proporção consistente valorizam o catálogo e reduzem o peso.
                    imagem = ImageOps.fit(imagem, (204, 104), method=Image.Resampling.LANCZOS, centering=(0.5, 0.45))
                    try:
                        data_legivel = dt.date.fromisoformat(str(platina["earned_at"])).strftime("%d/%m/%Y")
                    except (ValueError, TypeError):
                        data_legivel = str(platina["earned_at"])
                    thumbs.append((str(platina["game"]), str(platina["platform"]), data_legivel, imagem))
                except Exception:
                    continue

        if not thumbs:
            return None

        cols, card_w, card_h = 3, 224, 170
        rows = (len(thumbs) + cols - 1) // cols
        canvas = Image.new("RGB", (cols * card_w, rows * card_h), (28, 30, 34))
        draw = ImageDraw.Draw(canvas)
        try:
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 13)
            detail_font = ImageFont.truetype("DejaVuSans.ttf", 10)
        except OSError:
            title_font = detail_font = ImageFont.load_default()
        for i, (game, platform, data_legivel, image) in enumerate(thumbs):
            x, y = (i % cols) * card_w, (i // cols) * card_h
            canvas.paste(image, (x + 10, y + 8))
            draw.rectangle((x, y, x + card_w - 1, y + card_h - 1), outline=(184, 146, 51), width=1)
            title = game if len(game) <= 28 else game[:25] + "..."
            detail = platform if len(platform) <= 30 else platform[:27] + "..."
            draw.text((x + 10, y + 118), title, font=title_font, fill=(245, 241, 226))
            draw.text((x + 10, y + 136), detail, font=detail_font, fill=(185, 188, 194))
            draw.text((x + 10, y + 153), data_legivel, font=detail_font, fill=(145, 150, 158))
        buffer = io.BytesIO()
        canvas.save(buffer, format="JPEG", quality=82, optimize=True, progressive=True)
        data = buffer.getvalue()
        # Guarda apenas em cache local; o arquivo é recriado para cada envio/edição.
        self._catalogos_cache[user_id] = (signature, data)
        return discord.File(io.BytesIO(data), filename=filename)

    async def montar_painel(self, guild: discord.Guild) -> tuple[str, list[discord.Embed], discord.ui.View, list[discord.File]]:
        db = self.bot.db
        top = await db.ranking_completo(10)
        agora = int(discord.utils.utcnow().timestamp())
        cabecalho = (
            "# 🏛️ COLIZEU — Hall dos Gladiadores\n\n"
            "Os maiores caçadores de platinas da arena.\n"
            f"_Atualizado <t:{agora}:R>._"
        )
        if not top:
            return (
                cabecalho + "\n\n**A arena ainda está vazia.** Nenhuma platina aprovada foi registrada. Use `/coliseu` para começar.",
                [], discord.ui.View(timeout=None), [],
            )

        embeds: list[discord.Embed] = []
        arquivos: list[discord.File] = []
        podio_botoes: list[tuple[int, str]] = []
        for i, row in enumerate(top[:3]):
            medalha, cor = PODIO[i]
            membro = await self._membro(guild, row["user_id"])
            nome = membro.display_name if membro else f"<@{row['user_id']}>"
            nivel = nivel_por_xp(row["xp"])
            ultimas = await db.ultimas_platinas(row["user_id"], 3)
            jogos = "\n".join(
                f"🏆 {discord.utils.escape_markdown(str(p['game']))} ({discord.utils.escape_markdown(str(p['platform']))})"
                for p in ultimas
            ) or "Nenhuma conquista recente."

            podio_botoes.append((row["user_id"], f"{medalha} {membro.display_name if membro else 'Perfil'}"))
            e = discord.Embed(title=f"{medalha} {nome}", color=cor)
            e.description = (
                f"**{row['platinas']}** platinas • **{patente_por_nivel(nivel)}** • Nível {nivel} • {row['xp']} XP\n\n"
                f"**Últimas conquistas**\n{jogos}"
            )
            if membro:
                e.set_thumbnail(url=membro.display_avatar.url)
            todas_platinas = await db.platinas_do_usuario(row["user_id"])
            catalogo = await self._catalogo_platinas(guild, todas_platinas)
            if catalogo:
                e.description += f"\n\n**📚 Catálogo completo:** {len(todas_platinas)} jogos"
                e.set_image(url=f"attachment://{catalogo.filename}")
                arquivos.append(catalogo)
            elif ultimas:
                # Fallback quando nenhum comprovante está acessível para montar o catálogo.
                foto = await self._foto_platina(guild, ultimas[0])
                if foto:
                    e.set_image(url=foto)
            embeds.append(e)

        partes = [cabecalho]
        if len(top) > 3:
            linhas = ["\n**⚔️ Demais gladiadores**"]
            for i, row in enumerate(top[3:], start=4):
                membro = await self._membro(guild, row["user_id"])
                nome = discord.utils.escape_markdown(membro.display_name) if membro else f"<@{row['user_id']}>"
                patente = patente_por_nivel(nivel_por_xp(row["xp"]))
                linhas.append(f"`{i:>2}.` **{nome}** — 🏆 {row['platinas']} • {patente}")
            partes.append("\n".join(linhas))
        return "\n".join(partes)[:1990], embeds, _view_podio(podio_botoes), arquivos

    async def _publicar_no_canal(self, canal, chave_msg_id: str) -> bool:
        """Publica ou atualiza o painel no canal indicado sem criar duplicatas."""
        content, embeds, view, arquivos = await self.montar_painel(canal.guild)

        msg_id = await self.bot.db.get_kv(chave_msg_id)
        msg = None
        if msg_id:
            try:
                msg = await canal.fetch_message(int(msg_id))
            except (discord.NotFound, ValueError, TypeError):
                msg = None  # ID antigo/inválido; tenta localizar uma publicação existente.
            except discord.HTTPException:
                logging.exception("Não foi possível buscar a mensagem salva do painel do Colizeu")
                return False

        if msg is None:
            try:
                async for antiga in canal.history(limit=50):
                    antigo_titulo = any(e.title == "🏛️ COLIZEU — Hall dos Gladiadores" for e in antiga.embeds)
                    if antigo_titulo or antiga.content.startswith("# 🏛️ COLIZEU — Hall dos Gladiadores"):
                        msg = antiga
                        break
            except (discord.Forbidden, discord.HTTPException, AttributeError):
                logging.debug("Não foi possível procurar uma publicação antiga do Colizeu", exc_info=True)

        if msg is not None:
            await msg.edit(content=content, embeds=embeds, view=view, attachments=arquivos)
        else:
            msg = await canal.send(content=content, embeds=embeds, view=view, files=arquivos)
        await self.bot.db.set_kv(chave_msg_id, str(msg.id))
        return True

    async def atualizar(self) -> bool:
        """Atualiza o painel automático no canal definido em COLIZEU_CHANNEL_ID."""
        if not config.COLIZEU_CHANNEL_ID:
            return False
        canal = self.bot.get_channel(config.COLIZEU_CHANNEL_ID)
        if canal is None:
            try:
                canal = await self.bot.fetch_channel(config.COLIZEU_CHANNEL_ID)
            except discord.HTTPException:
                logging.exception("Não foi possível acessar o canal do Colizeu")
                return False
        if not hasattr(canal, "guild") or not hasattr(canal, "send"):
            logging.error("COLIZEU_CHANNEL_ID não aponta para um canal de mensagens válido")
            return False
        return await self._publicar_no_canal(canal, "colizeu_msg_id")

    @app_commands.command(
        name="painel_colizeu",
        description="[MOD] Publica o painel principal com platinas, perfil, runs e desafios.",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def painel_colizeu(self, interaction: discord.Interaction):
        """Atalho de publicação do painel principal da Nara."""
        platinas = self.bot.get_cog("Platinas")
        if platinas is None:
            return await interaction.response.send_message("O painel principal ainda não está carregado.", ephemeral=True)
        await platinas.publicar_painel_principal(interaction)

    @app_commands.command(name="colizeu", description="[MOD] Atualiza a mensagem de informações e rankings do canal do Colizeu.")
    @app_commands.default_permissions(manage_guild=True)
    async def colizeu(self, interaction: discord.Interaction):
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        ok = await self.atualizar()
        await interaction.followup.send(
            "✅ Painel atualizado!" if ok else "Não achei o canal. Confira COLIZEU_CHANNEL_ID e as permissões do bot.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Colizeu(bot))
