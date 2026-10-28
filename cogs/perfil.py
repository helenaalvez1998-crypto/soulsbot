import datetime as dt
import discord
from discord.ext import commands

import config
from levels import nivel_por_xp, patente_por_nivel, barra_progresso


class Perfil(commands.Cog):
    """Sem comandos próprios: o painel /coliseu usa estes métodos."""

    def __init__(self, bot):
        self.bot = bot

    async def embed_perfil(self, membro: discord.Member) -> discord.Embed:
        db = self.bot.db
        user = await db.get_user(membro.id)
        nivel = nivel_por_xp(user["xp"])
        qtd = await db.contar_platinas(membro.id)

        embed = discord.Embed(title=f"🏛️ {membro.display_name}", color=config.COR_OURO)
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="Patente", value=patente_por_nivel(nivel), inline=True)
        embed.add_field(name="Nível", value=str(nivel), inline=True)
        embed.add_field(name="Denários", value=f"🪙 {user['denarios']}", inline=True)
        embed.add_field(name="XP", value=barra_progresso(user["xp"]), inline=False)
        embed.add_field(name="🏆 Platinas", value=str(qtd), inline=True)
        embed.add_field(name="✅ Zerados", value=str(await db.contar_zerados(membro.id)), inline=True)
        embed.add_field(name="Rank XP", value=f"#{await db.posicao_xp(user['xp'])}", inline=True)
        embed.add_field(name="Rank Platinas", value=f"#{await db.posicao_platinas(qtd)}", inline=True)
        return embed

    async def embed_platinas(self, membro: discord.Member) -> discord.Embed | None:
        rows = await self.bot.db.platinas_do_usuario(membro.id)
        if not rows:
            return None
        linhas = [f"🏆 **{r['game']}** — {r['platform']} ({r['earned_at']})" for r in rows[:25]]
        embed = discord.Embed(
            title=f"Platinas de {membro.display_name}",
            description="\n".join(linhas),
            color=config.COR_PRATA,
        )
        if len(rows) > 25:
            embed.set_footer(text=f"Mostrando 25 de {len(rows)}")
        return embed

    async def texto_platinas(self, membro: discord.Member) -> str | None:
        rows = await self.bot.db.platinas_do_usuario(membro.id)
        if not rows:
            return None
        def data_legivel(valor):
            try:
                return dt.date.fromisoformat(str(valor)).strftime("%d/%m/%Y")
            except (ValueError, TypeError):
                return str(valor)
        cabecalho = f"## 📜 Platinas de {membro.display_name}\n\n"
        linhas = []
        for r in rows[:25]:
            linha = f"🏆 **{r['game']}** · `{r['platform']}` · {data_legivel(r['earned_at'])}"
            candidato = cabecalho + "\n".join(linhas + [linha])
            if len(candidato) > 1850:
                break
            linhas.append(linha)
        texto = cabecalho + ("\n".join(linhas) or "Nenhuma conquista cabe na lista atual.")
        if len(rows) > len(linhas):
            texto += f"\n\n_Mostrando {len(linhas)} de {len(rows)} conquistas. O perfil continua com a coleção completa._"
        return texto[:1990]

    def texto_ajuda(self) -> str:
        return (
            "## ⚔️ Colizeu — Guia rápido\n\n"
            "**`/coliseu`** abre o painel de conquistas e jornadas.\n\n"
            "🏆 **Registrar platina** — informe o jogo, a plataforma, a data e os comprovantes; "
            "a moderação revisará o registro.\n"
            "👤 **Perfil** — consulta patente, nível, XP e posições no ranking.\n"
            "📜 **Platinas** — lista suas conquistas aprovadas.\n"
            "🏛️ **Santuário** — personalize sua apresentação, galeria e plataformas.\n"
            "✅ **Zerados** — registre os jogos que você finalizou, sem precisar platinar.\n"
            "⚔️ **Runs e desafios** — registre tempos e acompanhe recordes.\n\n"
            "_Use os botões de voltar para navegar sem criar mensagens adicionais._"
        )

    def embed_ajuda(self) -> discord.Embed:
        embed = discord.Embed(title="⚔️ Nara — Como usar", color=config.COR_OURO)
        embed.description = (
            "Use **`/coliseu`** para abrir o painel. Nele você pode:\n\n"
            "📤 **Registrar platina** — informe jogo, plataforma, data e anexe o print. "
            "A moderação aprova ou rejeita.\n"
            "👤 **Perfil** — patente, nível, XP e ranking.\n"
            "📜 **Platinas** — lista de jogos platinados.\n"
            "🏆 **Ranking** — platinas, XP e platinas do mês.\n"
            "🔎 O menu de membros deixa você consultar o perfil de outra pessoa.\n"
            "🏛️ **Meu santuário** — seu espaço pessoal com platinas, prints e redes.\n"
            "🚪 **Visitar santuário** — entre no santuário do membro escolhido no menu. "
            "Para sair, use *Sair do tópico* e ele some da sua lista."
        )
        return embed


async def setup(bot):
    await bot.add_cog(Perfil(bot))
