import logging
import discord
from discord.ext import commands

import config
from database import Database

logging.basicConfig(level=logging.INFO)

EXTENSOES = ("cogs.admin", "cogs.perfil", "cogs.platinas", "cogs.loja", "cogs.ranking", "cogs.colizeu",
            "cogs.cargos", "cogs.progressao", "cogs.youtube", "cogs.ofertas", "cogs.zerados", "cogs.santuario", "cogs.soulslike", "cogs.nara_ia")


class NaraBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.db = Database(config.DB_PATH)

    async def setup_hook(self):
        await self.db.connect()
        for ext in EXTENSOES:
            await self.load_extension(ext)
        if config.GUILD_ID:  # sincroniza instantâneo no seu servidor
            guild = discord.Object(config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            # remove comandos GLOBAIS antigos (do bot anterior) para não aparecerem duplicados
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
        else:  # global pode levar até 1h para aparecer
            await self.tree.sync()

    async def on_ready(self):
        logging.info("Nara online como %s", self.user)


if __name__ == "__main__":
    if not config.TOKEN:
        raise SystemExit("Defina DISCORD_TOKEN nas variáveis de ambiente.")
    NaraBot().run(config.TOKEN)
