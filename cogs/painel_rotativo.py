import logging

import discord
from discord.ext import commands, tasks

from cogs.platinas import PainelPublicoView
from cogs.zerados import ZeradosPublicoView

log = logging.getLogger("cogs.painel_rotativo")

INTERVALO_MINUTOS = 30

TEXTOS = {
    "platinas": (
        "🏆 **NARA — PLATINAS**\n"
        "Registre suas conquistas e consulte suas platinas.\n\n"
        "Clique no botão abaixo para abrir seu painel pessoal."
    ),
    "zerados": (
        "# ✅ Jogos Zerados\n\n"
        "Não curte platinar, mas zerou o jogo? Use o botão abaixo para **registrar**, ver sua lista "
        "e acompanhar o ranking de quem mais finalizou jogos.\n\n"
        "_Print é opcional. Se enviar, ele aparece no anúncio do canal._"
    ),
}


class PainelRotativo(commands.Cog):
    """Republica somente cópias rotativas; nunca altera nem apaga os painéis fixos."""

    def __init__(self, bot):
        self.bot = bot
        self.rotacionar.start()

    def cog_unload(self):
        self.rotacionar.cancel()

    @tasks.loop(minutes=INTERVALO_MINUTOS)
    async def rotacionar(self):
        for guild in self.bot.guilds:
            await self._rotacionar_guild(guild.id, "platinas")
            await self._rotacionar_guild(guild.id, "zerados")

    @rotacionar.before_loop
    async def antes_de_rotacionar(self):
        await self.bot.wait_until_ready()
        # A primeira cópia só aparece após 30 minutos, não imediatamente no boot.
        import asyncio
        await asyncio.sleep(INTERVALO_MINUTOS * 60)

    async def _rotacionar_guild(self, guild_id: int, tipo: str):
        channel_key = f"rotating:channel:{tipo}:{guild_id}"
        channel_id = await self.bot.db.get_kv(channel_key)
        if not channel_id:
            return

        try:
            channel = self.bot.get_channel(int(channel_id))
            if channel is None:
                channel = await self.bot.fetch_channel(int(channel_id))
        except (ValueError, discord.NotFound):
            log.warning("Canal configurado para painel rotativo não encontrado: tipo=%s guild=%s", tipo, guild_id)
            return
        except discord.Forbidden:
            log.warning("Sem permissão para acessar canal do painel rotativo: tipo=%s guild=%s", tipo, guild_id)
            return
        except discord.HTTPException:
            log.exception("Falha ao buscar canal do painel rotativo: tipo=%s guild=%s", tipo, guild_id)
            return

        if not hasattr(channel, "send"):
            log.warning("Canal do painel rotativo não aceita mensagens: tipo=%s guild=%s", tipo, guild_id)
            return

        cog_name = "Platinas" if tipo == "platinas" else "Zerados"
        cog = self.bot.get_cog(cog_name)
        if cog is None:
            log.warning("Cog %s indisponível; painel %s não foi rotacionado.", cog_name, tipo)
            return

        view = PainelPublicoView(cog) if tipo == "platinas" else ZeradosPublicoView(cog)
        rotating_key = f"rotating:message:{tipo}:{guild_id}:{channel.id}"
        fixed_key = f"panel:{tipo}:{guild_id}:{channel.id}"
        old_id = await self.bot.db.get_kv(rotating_key)
        fixed_id = await self.bot.db.get_kv(fixed_key)

        try:
            new_message = await channel.send(
                content=TEXTOS[tipo],
                view=view,
                allowed_mentions=discord.AllowedMentions.none(),
                silent=True,
            )
        except discord.Forbidden:
            log.warning("Sem permissão para publicar cópia rotativa: tipo=%s canal=%s", tipo, channel.id)
            return
        except discord.HTTPException:
            log.exception("Falha ao publicar cópia rotativa: tipo=%s canal=%s", tipo, channel.id)
            return

        # Persiste a nova mensagem antes de remover a anterior.
        await self.bot.db.set_kv(rotating_key, str(new_message.id))

        # Proteção explícita: a mensagem fixa nunca é removida pela rotação.
        if not old_id or str(old_id) == str(fixed_id) or str(old_id) == str(new_message.id):
            return

        try:
            old_message = await channel.fetch_message(int(old_id))
            if not old_message.pinned:
                await old_message.delete()
        except (ValueError, discord.NotFound):
            pass
        except discord.Forbidden:
            log.warning("Sem permissão para apagar cópia rotativa antiga: tipo=%s canal=%s", tipo, channel.id)
        except discord.HTTPException:
            log.exception("Falha ao apagar cópia rotativa antiga: tipo=%s canal=%s", tipo, channel.id)


async def setup(bot):
    await bot.add_cog(PainelRotativo(bot))
