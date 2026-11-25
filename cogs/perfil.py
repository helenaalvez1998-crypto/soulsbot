import datetime as dt
import discord
from discord.ext import commands

import config
from levels import nivel_por_xp, patente_por_nivel, barra_progresso


class Perfil(commands.Cog):
    """Sem comandos próprios: o painel de Coliseu dentro de /nara usa estes métodos."""

    def __init__(self, bot):
        self.bot = bot

    async def embed_perfil(self, membro: discord.Member) -> discord.Embed:
        db = self.bot.db
        user = await db.get_user(membro.id)
        nivel = nivel_por_xp(user["xp"])
        qtd = await db.contar_platinas(membro.id)
        zerados = await db.contar_zerados(membro.id)
        runs = await db.stats_runs(membro.id)
        analytics = await db.estatisticas_gamer(membro.id)
        pendentes = await db.registros_pendentes_usuario(membro.id)

        embed = discord.Embed(title=f"🏛️ {membro.display_name}", color=config.COR_OURO)
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="Patente", value=patente_por_nivel(nivel), inline=True)
        embed.add_field(name="Nível", value=str(nivel), inline=True)
        embed.add_field(name="Denários", value=f"🪙 {user['denarios']}", inline=True)
        embed.add_field(name="XP", value=barra_progresso(user["xp"]), inline=False)
        embed.add_field(name="🏆 Platinas", value=str(qtd), inline=True)
        embed.add_field(name="✅ Zerados", value=str(zerados), inline=True)
        embed.add_field(name="⚔️ Runs", value=str(runs["runs"]), inline=True)
        embed.add_field(name="Rank XP", value=f"#{await db.posicao_xp(user['xp'])}", inline=True)
        embed.add_field(name="Rank Platinas", value=f"#{await db.posicao_platinas(qtd)}", inline=True)
        if analytics["media_nota"] is not None:
            embed.add_field(
                name="⭐ Avaliação média",
                value=f"**{analytics['media_nota']:.1f}/10** · {analytics['qtd_notas']} avaliações",
                inline=True,
            )
        if analytics["media_dificuldade"] is not None:
            rotulos = {1: "Muito fácil", 2: "Fácil", 3: "Moderada", 4: "Difícil", 5: "Muito difícil"}
            media = analytics["media_dificuldade"]
            arredondada = max(1, min(5, int(round(media))))
            embed.add_field(
                name="🎯 Dificuldade percebida",
                value=f"{media:.1f}/5 · {rotulos[arredondada]} ({analytics['qtd_dificuldades']} respostas)",
                inline=True,
            )
        if analytics["plataformas"]:
            plataformas = " · ".join(f"{r['platform']}: {r['total']}" for r in analytics["plataformas"])
            embed.add_field(name="🎮 Plataformas mais usadas", value=plataformas[:1024], inline=False)
        if analytics["melhores"]:
            linhas = [f"⭐ **{r['titulo']}** — {int(r['rating'])}/10 ({r['tipo']})" for r in analytics["melhores"]]
            embed.add_field(name="🏅 Jogos mais bem avaliados", value="\n".join(linhas)[:1024], inline=False)
        if analytics["recentes"]:
            linhas = [f"{r['tipo']}: **{r['titulo']}** · {r['data']}" for r in analytics["recentes"]]
            embed.add_field(name="🕓 Conquistas recentes", value="\n".join(linhas)[:1024], inline=False)
        if pendentes:
            embed.add_field(name="📬 Em análise", value=f"{pendentes} registro(s) aguardando moderação", inline=False)
        embed.set_footer(text="Estatísticas baseadas somente em conquistas e avaliações aprovadas.")
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
            "Vamos ao que interessa: o caminho de cada recurso, sem caça ao tesouro no menu.\n\n"
            "**`/nara`** abre o painel de conquistas e jornadas.\n\n"
            "🏆 **Registrar platina** — informe o jogo, a plataforma, a data e os comprovantes; "
            "a moderação revisará o registro.\n"
            "👤 **Perfil** — consulta patente, nível, XP e posições no ranking.\n"
            "📜 **Platinas** — lista suas conquistas aprovadas.\n"
            "🏛️ **Santuário** — personalize sua apresentação, galeria e plataformas.\n"
            "✅ **Zerados** — registre os jogos que você finalizou, sem precisar platinar.\n"
            "⚔️ **Runs e desafios** — registre tempos e acompanhe recordes.\n\n"
            "_Use os botões de voltar para navegar sem criar mensagens adicionais._"
        )


async def setup(bot):
    await bot.add_cog(Perfil(bot))
