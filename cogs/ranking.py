import datetime as dt
import discord
from discord.ext import commands

import config

MEDALHAS = ["🥇", "🥈", "🥉"]
TIPOS = {
    "platinas": "Platinas (total)",
    "xp": "XP",
    "mensal": "Platinas do mês",
    "zerados": "Jogos zerados",
    "zerados_mensal": "Zerados do mês",
    "runs": "Runs aprovadas",
    "recordes": "Recordes de Runs",
}


class Ranking(commands.Cog):
    """Sem comandos próprios: o painel de Coliseu dentro de /nara usa embed_ranking."""

    def __init__(self, bot):
        self.bot = bot

    async def texto_ranking(self, tipo: str) -> str:
        db = self.bot.db
        mes = dt.datetime.now(config.BRAZIL_TZ).strftime("%Y-%m")
        if tipo == "platinas":
            rows, titulo, unidade = await db.ranking_platinas(), "Ranking de Platinas", "platinas"
        elif tipo == "xp":
            rows, titulo, unidade = await db.ranking_xp(), "Ranking de XP", "XP"
        elif tipo == "mensal":
            rows, titulo, unidade = await db.ranking_mensal(mes), f"Platinas de {mes}", "platinas"
        elif tipo == "zerados":
            rows, titulo, unidade = await db.ranking_zerados(), "Ranking de Jogos Zerados", "jogos"
        elif tipo == "zerados_mensal":
            rows, titulo, unidade = await db.ranking_zerados_mensal(mes), f"Jogos Zerados de {mes}", "jogos"
        elif tipo == "runs":
            rows, titulo, unidade = await db.ranking_runs(), "Ranking de Runs Aprovadas", "runs"
        elif tipo == "recordes":
            rows, titulo, unidade = await db.ranking_recordes_runs(), "Ranking de Recordes de Runs", "recordes"
        else:
            return "## 🏛️ Ranking não reconhecido."
        if not rows:
            return f"## 🏛️ {titulo}\n\nAinda não há dados nesse ranking."
        linhas = []
        for i, row in enumerate(rows):
            posicao = MEDALHAS[i] if i < 3 else f"`{i + 1:>2}.`"
            linhas.append(f"{posicao} <@{row['user_id']}> — **{row['valor']}** {unidade}")
        return f"## 🏛️ {titulo}\n\n" + "\n".join(linhas) + "\n\n_Atualizado ao consultar._"

    async def embed_ranking(self, tipo: str) -> discord.Embed:
        db = self.bot.db
        mes = dt.datetime.now(config.BRAZIL_TZ).strftime("%Y-%m")
        if tipo == "platinas":
            rows, titulo, unidade = await db.ranking_platinas(), "Ranking de Platinas", "🏆"
        elif tipo == "xp":
            rows, titulo, unidade = await db.ranking_xp(), "Ranking de XP", "XP"
        elif tipo == "mensal":
            rows, titulo, unidade = await db.ranking_mensal(mes), f"Platinas de {mes}", "🏆"
        elif tipo == "zerados":
            rows, titulo, unidade = await db.ranking_zerados(), "Ranking de Jogos Zerados", "✅"
        elif tipo == "zerados_mensal":
            rows, titulo, unidade = await db.ranking_zerados_mensal(mes), f"Jogos Zerados de {mes}", "✅"
        elif tipo == "runs":
            rows, titulo, unidade = await db.ranking_runs(), "Ranking de Runs Aprovadas", "⚔️"
        elif tipo == "recordes":
            rows, titulo, unidade = await db.ranking_recordes_runs(), "Ranking de Recordes de Runs", "👑"
        else:
            return discord.Embed(title="Ranking não reconhecido", color=config.COR_OURO)

        if not rows:
            return discord.Embed(title=f"🏛️ {titulo}", description="Ainda não há registros suficientes para montar este ranking. A arena aguarda os primeiros resultados.", color=config.COR_OURO)

        linhas = []
        for i, r in enumerate(rows):
            pos = MEDALHAS[i] if i < 3 else f"`{i + 1}.`"
            linhas.append(f"{pos} <@{r['user_id']}> — **{r['valor']}** {unidade}")
        return discord.Embed(title=f"🏛️ {titulo}", description="\n".join(linhas), color=config.COR_OURO)


async def setup(bot):
    await bot.add_cog(Ranking(bot))
