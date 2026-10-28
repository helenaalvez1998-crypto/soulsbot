import logging
import random
import time
import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from admin_config import GuildConfig
from levels import nivel_por_xp, xp_para_nivel, patente_por_nivel, barra_progresso
from cogs.platinas import sincronizar_patente

# XP de participação; valores ajustáveis aqui.
XP_MENSAGEM_MIN = 10
XP_MENSAGEM_MAX = 20
INTERVALO_MENSAGEM = 60
XP_VOZ_POR_INTERVALO = 5
INTERVALO_VOZ_SEGUNDOS = 300
XP_RUN_APROVADA = 100
XP_NOVO_RECORDE = 100

class ProgressaoXP(commands.Cog):
    """Progressão única por mensagens, voz, platinas e runs aprovadas."""
    def __init__(self, bot):
        self.bot = bot
        self.ultimo_xp_msg = {}
        self.voz.start()

    def cog_unload(self):
        self.voz.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        # Renomeia cargos existentes; não cria cargos novos nem duplica.
        from levels import PATENTES, nome_patente_exibicao
        for guild in self.bot.guilds:
            for _, nome_original in PATENTES:
                nome_novo = nome_patente_exibicao(nome_original)
                cargo = discord.utils.get(guild.roles, name=nome_original)
                if cargo is None:
                    cargo = discord.utils.get(guild.roles, name=nome_novo)
                if cargo is None:
                    logging.warning(
                        "Nara — progressão: cargo '%s' não encontrado em '%s'; nenhum cargo foi criado.",
                        nome_original, guild.name,
                    )
                    continue
                if cargo.name == nome_novo:
                    continue
                try:
                    await cargo.edit(
                        name=nome_novo,
                        reason="Nara: adicionar símbolo visual à patente existente",
                    )
                    logging.info(
                        "Nara — progressão: cargo renomeado '%s' -> '%s' em '%s'",
                        nome_original, nome_novo, guild.name,
                    )
                except discord.Forbidden:
                    logging.error(
                        "Nara não pode renomear cargos em '%s'. Verifique Gerenciar Cargos "
                        "e se o cargo do bot está acima das patentes.",
                        guild.name,
                    )
                    break
                except discord.HTTPException as exc:
                    logging.error("Falha ao renomear cargo '%s' em '%s': %s", nome_original, guild.name, exc)

    async def conceder_xp(self, guild, user_id: int, quantidade: int, motivo: str):
        if quantidade <= 0:
            return
        antigo_xp_row = await self.bot.db.get_user(user_id)
        xp_antigo = int(antigo_xp_row['xp'])
        antigo_nivel = nivel_por_xp(xp_antigo)
        _, novo_nivel, total = await self.bot.db.add_reward(user_id, quantidade, 0)
        membro = guild.get_member(user_id) if guild else None
        if membro and novo_nivel > antigo_nivel:
            await sincronizar_patente(guild, membro, novo_nivel)
            try:
                await membro.send(f"⚔️ Você alcançou o nível **{novo_nivel} — {patente_por_nivel(novo_nivel)}** no sistema de progressão da Nara! (+{quantidade} XP por {motivo})")
            except (discord.Forbidden, discord.HTTPException):
                pass
        return total

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return
        # Ignora mensagens vazias, comandos e canais de moderação.
        if not message.content.strip() and not message.attachments:
            return
        mod_ch_id = await GuildConfig.get(self.bot.db, message.guild.id, "mod_channel") or config.MOD_CHANNEL_ID
        if mod_ch_id and message.channel.id == mod_ch_id:
            return
        agora = time.monotonic()
        chave = (message.guild.id, message.author.id)
        if agora - self.ultimo_xp_msg.get(chave, 0) < INTERVALO_MENSAGEM:
            return
        self.ultimo_xp_msg[chave] = agora
        await self.conceder_xp(message.guild, message.author.id, random.randint(XP_MENSAGEM_MIN, XP_MENSAGEM_MAX), "interação no Discord")

    @tasks.loop(seconds=INTERVALO_VOZ_SEGUNDOS)
    async def voz(self):
        for guild in self.bot.guilds:
            for canal in getattr(guild, 'voice_channels', []):
                membros = [m for m in canal.members if not m.bot and not m.voice.self_deaf and not m.voice.deaf]
                # Requer ao menos dois humanos; evita XP por ficar sozinho em voz.
                if len(membros) < 2:
                    continue
                for membro in membros:
                    await self.conceder_xp(guild, membro.id, XP_VOZ_POR_INTERVALO, "participação em voz")

    @voz.before_loop
    async def antes_voz(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="nivel", description="Veja seu nível, XP e progresso da Nara.")
    async def nivel(self, interaction: discord.Interaction, membro: discord.Member = None):
        alvo = membro or interaction.user
        user = await self.bot.db.get_user(alvo.id)
        xp = int(user['xp'])
        nivel = nivel_por_xp(xp)
        embed = discord.Embed(title=f"🛡️ Nara — {alvo.display_name}", color=config.COR_OURO)
        embed.set_thumbnail(url=alvo.display_avatar.url)
        embed.add_field(name="Patente", value=patente_por_nivel(nivel), inline=True)
        embed.add_field(name="Nível", value=str(nivel), inline=True)
        embed.add_field(name="XP total", value=f"{xp:,}", inline=True)
        embed.add_field(name="Progresso", value=barra_progresso(xp), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=(membro is None))

    @app_commands.command(name="ranking-xp", description="Veja os maiores níveis da Nara.")
    async def ranking_xp(self, interaction: discord.Interaction):
        rows = await self.bot.db.ranking_xp(10)
        if not rows:
            return await interaction.response.send_message("Ainda não há XP registrado.", ephemeral=True)
        linhas = []
        for i, row in enumerate(rows, 1):
            nivel = nivel_por_xp(int(row['valor']))
            linhas.append(f"`{i:>2}.` <@{row['user_id']}> — **Nível {nivel}** · {patente_por_nivel(nivel)} · {row['valor']} XP")
        texto = "## 🏆 Ranking de XP da Nara\n\n" + "\n".join(linhas)
        await interaction.response.send_message(content=texto)


async def setup(bot):
    await bot.add_cog(ProgressaoXP(bot))
