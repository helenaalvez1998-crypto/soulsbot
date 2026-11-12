"""Tutorial de transmissões e configuração administrativa do vídeo da NARA."""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("nara.transmissoes")


class VideoTransmissaoView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Assistir ao vídeo tutorial", style=discord.ButtonStyle.link, url=url, emoji="▶️"))


class Transmissoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await self.bot.db.conn.execute(
            """CREATE TABLE IF NOT EXISTS nara_video_transmissao (
                guild_id INTEGER PRIMARY KEY,
                url TEXT NOT NULL,
                updated_by INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )"""
        )
        await self.bot.db.conn.commit()

    async def obter_video(self, guild_id: int) -> str | None:
        row = await self.bot.db._one(
            "SELECT url FROM nara_video_transmissao WHERE guild_id=?", (guild_id,)
        )
        return str(row["url"]) if row and row["url"] else None

    @app_commands.command(
        name="configurar_video_transmissao",
        description="[MOD] Cadastra ou atualiza o vídeo tutorial de transmissões no Discord.",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(link="Link do vídeo publicado no YouTube")
    async def configurar_video_transmissao(self, interaction: discord.Interaction, link: str):
        if interaction.guild_id is None:
            return await interaction.response.send_message(
                "Esse comando só pode ser usado dentro de um servidor.", ephemeral=True
            )
        parsed = urlparse(link.strip())
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}:
            return await interaction.response.send_message(
                "Informe um link HTTPS válido do YouTube (youtube.com ou youtu.be).", ephemeral=True
            )
        import time
        await self.bot.db.conn.execute(
            """INSERT INTO nara_video_transmissao(guild_id,url,updated_by,updated_at)
               VALUES(?,?,?,?) ON CONFLICT(guild_id) DO UPDATE SET
               url=excluded.url, updated_by=excluded.updated_by, updated_at=excluded.updated_at""",
            (interaction.guild_id, link.strip(), interaction.user.id, int(time.time())),
        )
        await self.bot.db.conn.commit()
        await interaction.response.send_message(
            "Vídeo tutorial salvo. Quando alguém perguntar como voltar a transmitir, vou apresentar o tutorial e o botão para assistir ao vídeo.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Transmissoes(bot))
