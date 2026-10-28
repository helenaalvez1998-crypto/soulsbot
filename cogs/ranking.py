import datetime as dt
import discord
from discord.ext import commands

import config

MEDALHAS = ["🥇", "🥈", "🥉"]
TIPOS = {"platinas": "Platinas (total)", "xp": "XP", "mensal": "Platinas do mês"}


class Ranking(commands.Cog):
    """Sem comandos próprios: o painel /coliseu usa embed_ranking."""

    def __init__(self, bot):
        self.bot = bot

    async def texto_ranking(self, tipo: str) -> str:
        db = self.bot.db
        if tipo == "platinas":
            rows, titulo, unidade = await db.ranking_platinas(), "Ranking de Platinas", "platinas"
        elif tipo == "xp":
            rows, titulo, unidade = await db.ranking_xp(), "Ranking de XP", "XP"
        else:
            mes = dt.datetime.now(config.BRAZIL_TZ).strftime("%Y-%m")
            rows, titulo, unidade = await db.ranking_mensal(mes), f"Platinas de {mes}", "platinas"
        if not rows:
            return f"## 🏛️ {titulo}\n\nAinda não há dados nesse ranking."
        linhas = []
        for i, row in enumerate(rows):
            posicao = MEDALHAS[i] if i < 3 else f"`{i + 1:>2}.`"
            linhas.append(f"{posicao} <@{row['user_id']}> — **{row['valor']}** {unidade}")
        return f"## 🏛️ {titulo}\n\n" + "\n".join(linhas) + "\n\n_Atualizado ao consultar._"

    async def embed_ranking(self, tipo: str) -> discord.Embed:
        db = self.bot.db
        if tipo == "platinas":
            rows, titulo, unidade = await db.ranking_platinas(), "Ranking de Platinas", "🏆"
        elif tipo == "xp":
            rows, titulo, unidade = await db.ranking_xp(), "Ranking de XP", "XP"
        else:
            mes = dt.datetime.now(config.BRAZIL_TZ).strftime("%Y-%m")
            rows, titulo, unidade = await db.ranking_mensal(mes), f"Platinas de {mes}", "🏆"

        if not rows:
            return discord.Embed(title=f"🏛️ {titulo}", description="Ainda não há dados nesse ranking.", color=config.COR_OURO)

        linhas = []
        for i, r in enumerate(rows):
            pos = MEDALHAS[i] if i < 3 else f"`{i + 1}.`"
            linhas.append(f"{pos} <@{r['user_id']}> — **{r['valor']}** {unidade}")
        return discord.Embed(title=f"🏛️ {titulo}", description="\n".join(linhas), color=config.COR_OURO)


async def setup(bot):
    await bot.add_cog(Ranking(bot))
