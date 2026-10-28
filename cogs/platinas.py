import datetime as dt
import logging
import discord
from discord import app_commands
from discord.ext import commands

import config
from admin_config import GuildConfig
from levels import patente_por_nivel, nivel_por_xp, barra_progresso
from utils import get_text_channel, upsert_panel  # noqa: F401


async def eh_moderador(member: discord.Member, db=None) -> bool:
    if member.guild_permissions.manage_guild:
        return True
    if db and member.guild:
        mod_role_id = await GuildConfig.get(db, member.guild.id, "mod_role")
        if mod_role_id and any(r.id == mod_role_id for r in member.roles):
            return True
    if config.MOD_ROLE_ID and any(r.id == config.MOD_ROLE_ID for r in member.roles):
        return True
    return False


async def sincronizar_patente(guild: discord.Guild, member: discord.Member, nivel: int):
    """Dá o cargo da patente atual e remove as outras. Cria o cargo se não existir."""
    from levels import PATENTES

    from levels import nome_patente_exibicao, eh_cargo_patente
    alvo_nome = nome_patente_exibicao(patente_por_nivel(nivel))
    alvo = discord.utils.get(guild.roles, name=alvo_nome)
    if alvo is None:
        alvo = discord.utils.get(guild.roles, name=patente_por_nivel(nivel))
    try:
        if alvo is None:
            # Não cria cargo aqui; a inicialização só renomeia cargos existentes.
            return
        remover = [r for r in member.roles if eh_cargo_patente(r.name) and r != alvo]
        if remover:
            await member.remove_roles(*remover, reason="Colizeu: mudança de patente")
        if alvo not in member.roles:
            await member.add_roles(alvo, reason="Colizeu: nova patente")
    except discord.Forbidden:
        pass  # o cargo do bot precisa estar ACIMA dos cargos de patente


class RevisaoView(discord.ui.View):
    """Botões persistentes: continuam funcionando após reiniciar o bot."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def _processar(self, interaction: discord.Interaction, aprovar: bool):
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)

        db = self.bot.db
        platina_id = int(interaction.message.embeds[0].footer.text.split(":")[1])
        p = await db.get_platina(platina_id)
        if p is None or p["status"] != "pending":
            return await interaction.response.send_message("Este registro já foi processado.", ephemeral=True)

        novo_status = "approved" if aprovar else "rejected"
        await db.set_status(platina_id, novo_status, interaction.user.id)
        await db.log(interaction.user.id, f"platina_{novo_status}", f"id={platina_id} user={p['user_id']}")

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green() if aprovar else discord.Color.red()
        embed.add_field(
            name="Resultado",
            value=f"{'✅ Aprovada' if aprovar else '❌ Rejeitada'} por {interaction.user.mention}",
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=None)

        membro = interaction.guild.get_member(p["user_id"])
        if aprovar:
            xp_plat = await GuildConfig.get(db, interaction.guild_id, "xp_platina") or config.XP_PLATINA
            den_plat = await GuildConfig.get(db, interaction.guild_id, "denarios_platina") or config.DENARIOS_PLATINA
            antigo, novo, _ = await db.add_reward(p["user_id"], xp_plat, den_plat)
            if membro:
                await sincronizar_patente(interaction.guild, membro, novo)
            plat_ch_id = await GuildConfig.get(db, interaction.guild_id, "platinas_channel")
            canal = await get_text_channel(self.bot, plat_ch_id) if plat_ch_id else None
            if canal:
                linhas = [
                    "# 🏆 Nova platina no Coliseu!",
                    f"<@{p['user_id']}> conquistou **{p['game']}** na plataforma **{p['platform']}**.",
                    f"[📸 Ver comprovante]({p['proof_url']})",
                    f"**Recompensa:** +{xp_plat} XP · +{den_plat} Denários",
                ]
                if novo > antigo:
                    linhas.extend(["", f"⬆️ **Novo nível:** {novo} — {patente_por_nivel(novo)}"])
                await canal.send("\n".join(linhas))
            painel = self.bot.get_cog("Colizeu")
            if painel:
                try:
                    await painel.atualizar()
                except Exception:
                    pass
            santuario = self.bot.get_cog("Santuario")
            if santuario:
                try:
                    await santuario.atualizar(p["user_id"])
                except Exception:
                    logging.getLogger("colizeu").exception("Falha ao atualizar o santuário")
        elif membro:
            try:
                await membro.send(f"Sua platina de **{p['game']}** foi rejeitada. Fale com a moderação se tiver dúvidas.")
            except discord.Forbidden:
                pass

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, custom_id="plat:approve")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._processar(interaction, True)

    @discord.ui.button(label="Rejeitar", style=discord.ButtonStyle.danger, custom_id="plat:reject")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._processar(interaction, False)


class ColiseuView(discord.ui.View):
    """Painel principal do Coliseu. Pode ser público e persistente ou privado por usuário."""
    def __init__(self, platinas_cog, user=None):
        # Sem usuário definido, é o painel público postado pela moderação e precisa
        # continuar funcionando após reinicializações. Com usuário, é a versão privada.
        super().__init__(timeout=None if user is None else 300)
        self.platinas_cog = platinas_cog
        self.user_id = user.id if user is not None else None

    def texto(self):
        return (
            "# 🏛️ NARA — COLISEU\n"
            "Sua central de conquistas e jornadas.\n\n"
            "**🏆 Platinas** — registrar conquistas, consultar perfil e ranking.\n"
            "**✅ Zerados** — registrar jogos finalizados, sem precisar de platina.\n"
            "**⚔️ Runs e desafios** — registrar tempos, conferir regras e recordes.\n\n"
            "_Escolha uma área abaixo. A navegação acontece nesta mesma mensagem._"
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user_id is not None and interaction.user.id != self.user_id:
            await interaction.response.send_message("Abra /coliseu para acessar seu próprio painel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Platinas", emoji="🏆", style=discord.ButtonStyle.primary, custom_id="nara:coliseu:platinas", row=0)
    async def abrir_platinas(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PainelView(self.platinas_cog, interaction.user)
        if self.user_id is None:
            # No painel público, cada pessoa recebe a navegação em uma resposta privada.
            await interaction.response.send_message(embed=await view.embed(), view=view, ephemeral=True)
        else:
            await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)

    @discord.ui.button(label="Zerados", emoji="✅", style=discord.ButtonStyle.success, custom_id="nara:coliseu:zerados", row=0)
    async def abrir_zerados(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.platinas_cog.bot.get_cog("Zerados")
        if cog is None:
            return await interaction.response.send_message("O painel de zerados não está disponível. Avise a moderação.", ephemeral=True)
        view = cog.painel_view(interaction.user)
        if self.user_id is None:
            await interaction.response.send_message(embed=await view.embed(), view=view, ephemeral=True)
        else:
            await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)

    @discord.ui.button(label="Runs e desafios", emoji="⚔️", style=discord.ButtonStyle.danger, custom_id="nara:coliseu:runs", row=0)
    async def abrir_runs(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.platinas_cog.bot.get_cog("Soulslike")
        if cog is None:
            return await interaction.response.send_message("O painel de runs não está disponível. Avise a moderação.", ephemeral=True)
        from cogs.soulslike import CentralView
        if self.user_id is None:
            await interaction.response.send_message(content=cog.texto_central(), view=CentralView(cog), ephemeral=True)
        else:
            await interaction.response.edit_message(content=cog.texto_central(), embeds=[], view=CentralView(cog))


PLATAFORMAS = ["PS5", "PS4", "PS3", "PC", "Xbox Series", "Xbox One", "Switch", "Outra"]


def hoje() -> dt.date:
    return dt.datetime.now(config.BRAZIL_TZ).date()


class Platinas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(RevisaoView(self.bot))
        self.bot.add_view(PainelPublicoView(self))
        self.bot.add_view(PainelPrincipalPublicoView(self))
        self.bot.add_view(ColiseuView(self))

    # -------------------------------------------------------- comando público único
    @app_commands.command(name="coliseu", description="Abre o painel principal com platinas, runs, desafios, rankings e perfil.")
    @app_commands.guild_only()
    async def coliseu(self, interaction: discord.Interaction):
        view = ColiseuView(self, interaction.user)
        await interaction.response.send_message(content=view.texto(), view=view, ephemeral=True)

    async def abrir_painel(self, interaction: discord.Interaction):
        view = PainelView(self, interaction.user)
        await interaction.response.send_message(embed=await view.embed(), view=view, ephemeral=True)

    async def publicar_painel_principal(self, interaction: discord.Interaction):
        """Publica o painel principal interativo (platinas, perfil, runs e desafios)."""
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        canal = interaction.channel
        if interaction.guild is None or canal is None or not isinstance(canal, (discord.TextChannel, discord.Thread)):
            return await interaction.response.send_message("Use este comando em um canal de texto do servidor.", ephemeral=True)
        view = ColiseuView(self)
        texto = view.texto()
        key = f"panel:principal:{interaction.guild_id}:{canal.id}"
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await upsert_panel(
                self.bot, canal, key, marker="nara:painel:principal*",
                content=texto, embeds=[], view=view,
            )
        except discord.Forbidden:
            return await interaction.followup.send("Não tenho permissão para publicar ou atualizar o painel neste canal.", ephemeral=True)
        except discord.HTTPException:
            return await interaction.followup.send("O Discord recusou a publicação do painel. Confira as permissões e tente novamente.", ephemeral=True)
        await interaction.followup.send("✅ Painel principal da Nara publicado/atualizado neste canal.", ephemeral=True)

    @app_commands.command(name="painel_principal", description="[MOD] Publica o painel principal com platinas, perfil, runs e desafios.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def painel_principal(self, interaction: discord.Interaction):
        await self.publicar_painel_principal(interaction)

    @app_commands.command(name="postar_painel", description="[MOD] Publica o painel principal da Nara neste canal.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def postar_painel(self, interaction: discord.Interaction):
        await self.publicar_painel_principal(interaction)

    @app_commands.command(name="painel_platinas", description="[MOD] Publica neste canal o painel público de platinas.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def painel_platinas(self, interaction: discord.Interaction):
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores podem publicar o painel de platinas.", ephemeral=True)
        canal = interaction.channel
        if interaction.guild is None or canal is None or not isinstance(canal, (discord.TextChannel, discord.Thread)):
            return await interaction.response.send_message("Use este comando em um canal de texto do servidor.", ephemeral=True)
        view = PainelPublicoView(self)
        texto = "🏆 **NARA — PLATINAS**\nRegistre suas conquistas e consulte suas platinas.\n\nClique no botão abaixo para abrir seu painel pessoal."
        key = f"panel:platinas:{interaction.guild_id}:{canal.id}"
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await upsert_panel(
                self.bot, canal, key, marker="plat:painel",
                content=texto, view=view,
            )
        except discord.Forbidden:
            return await interaction.followup.send("Não tenho permissão para publicar ou atualizar o painel neste canal.", ephemeral=True)
        except discord.HTTPException:
            return await interaction.followup.send("O Discord recusou a publicação. Confira as permissões e tente novamente.", ephemeral=True)
        await interaction.followup.send("✅ Painel de platinas publicado/atualizado neste canal.", ephemeral=True)

    # -------------------------------------------------------- registro
    async def registrar_platina(self, interaction: discord.Interaction, jogo: str, plataforma: str,
                                data: str, capturas):
        try:
            d = dt.datetime.strptime(data.strip(), "%d/%m/%Y").date()
        except ValueError:
            return await interaction.response.send_message("Data inválida. Use DD/MM/AAAA.", ephemeral=True)
        if d > hoje():
            return await interaction.response.send_message("A data não pode estar no futuro.", ephemeral=True)
        if not isinstance(capturas, (list, tuple)):
            capturas = [capturas]
        capturas = list(capturas)
        if not capturas:
            return await interaction.response.send_message("Anexe pelo menos um comprovante.", ephemeral=True)
        if len(capturas) > 10:
            return await interaction.response.send_message("Envie no máximo 10 comprovantes por registro.", ephemeral=True)
        for arquivo_anexo in capturas:
            tipo = (arquivo_anexo.content_type or "").lower()
            nome = arquivo_anexo.filename.lower()
            eh_imagem_ou_video = tipo.startswith(("image/", "video/")) or nome.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".webm"))
            if not eh_imagem_ou_video:
                return await interaction.response.send_message(
                    f"Arquivo não suportado: {arquivo_anexo.filename}. Envie imagens ou vídeos.", ephemeral=True
                )

        jogo, plataforma = jogo.strip()[:100], plataforma.strip()[:30]
        if not jogo:
            return await interaction.response.send_message("Informe o nome do jogo.", ephemeral=True)
        db = self.bot.db
        if await db.platina_duplicada(interaction.user.id, jogo, plataforma):
            return await interaction.response.send_message(
                "Você já registrou essa platina (pendente ou aprovada).", ephemeral=True
            )

        mod_ch_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "mod_channel")
        canal = await get_text_channel(self.bot, mod_ch_id) if mod_ch_id else None
        if canal is None:
            return await interaction.response.send_message(
                "Canal de moderação não configurado. Avise um administrador.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        arquivos = [await anexo.to_file() for anexo in capturas]
        embed = discord.Embed(title="🏆 Platina aguardando aprovação", color=config.COR_PRATA)
        embed.add_field(name="Membro", value=interaction.user.mention)
        embed.add_field(name="Jogo", value=jogo)
        embed.add_field(name="Plataforma", value=plataforma)
        embed.add_field(name="Data", value=d.strftime("%d/%m/%Y"))
        embed.add_field(name="Comprovantes", value=f"{len(capturas)} arquivo(s) anexado(s)", inline=False)
        primeiro_tipo = (capturas[0].content_type or "").lower()
        if primeiro_tipo.startswith("image/") or capturas[0].filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            embed.set_image(url=f"attachment://{arquivos[0].filename}")
        if len(capturas) > 1:
            embed.add_field(name="Arquivos adicionais", value="\n".join(
                f"{i}. {discord.utils.escape_markdown(a.filename)}" for i, a in enumerate(capturas[1:], start=2)
            )[:1024], inline=False)

        msg = await canal.send(embed=embed, files=arquivos, view=RevisaoView(self.bot))
        urls = [(att.url, att.content_type) for att in msg.attachments]
        url = urls[0][0] if urls else capturas[0].url
        platina_id = await db.criar_platina(interaction.user.id, jogo, plataforma, d.isoformat(), url, msg.id)
        await db.adicionar_comprovantes(platina_id, urls or [(a.url, a.content_type) for a in capturas])
        embed.set_footer(text=f"ID:{platina_id}")
        await msg.edit(embed=embed)
        await db.log(interaction.user.id, "platina_registrada", f"id={platina_id} jogo={jogo}")
        await interaction.edit_original_response(content="✅ Registro enviado para a moderação!")


# ------------------------------------------------------------------ painel do usuário
class PainelView(discord.ui.View):
    def __init__(self, cog, user):
        super().__init__(timeout=900)
        self.cog, self.user = cog, user
        self.alvo: discord.Member | None = None  # membro consultado (padrão: você)
        self.sel_membro = discord.ui.UserSelect(placeholder="🔎 Consultar outro membro (opcional)", row=0)
        self.sel_membro.callback = self.trocar_membro
        self.add_item(self.sel_membro)

    def _membro(self):
        return self.alvo or self.user

    async def embed(self) -> discord.Embed:
        membro = self._membro()
        db = self.cog.bot.db
        user = await db.get_user(membro.id)
        nivel = nivel_por_xp(user["xp"])
        qtd = await db.contar_platinas(membro.id)
        e = discord.Embed(
            title="🏛️ Painel do Colizeu",
            description="Use os botões abaixo para registrar platinas, ver perfis e rankings.",
            color=config.COR_OURO,
        )
        e.set_thumbnail(url=membro.display_avatar.url)
        e.add_field(name="Consultando", value=f"**{membro.display_name}**" + (" (você)" if membro == self.user else ""), inline=False)
        e.add_field(name="Patente", value=patente_por_nivel(nivel))
        e.add_field(name="Nível", value=str(nivel))
        e.add_field(name="🏆 Platinas", value=str(qtd))
        e.add_field(name="XP", value=barra_progresso(user["xp"]), inline=False)
        return e

    async def trocar_membro(self, interaction: discord.Interaction):
        escolhido = self.sel_membro.values[0]
        if getattr(escolhido, "bot", False):
            return await interaction.response.send_message("Bots não têm perfil.", ephemeral=True)
        self.alvo = escolhido if isinstance(escolhido, discord.Member) else interaction.guild.get_member(escolhido.id)
        await interaction.response.edit_message(embed=await self.embed(), view=self)

    @discord.ui.button(label="Registrar platina", style=discord.ButtonStyle.success, emoji="📤", row=1)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PlatinaModal(self.cog))

    @discord.ui.button(label="Perfil", style=discord.ButtonStyle.primary, emoji="👤", row=1)
    async def perfil(self, interaction: discord.Interaction, button: discord.ui.Button):
        e = await self.cog.bot.get_cog("Perfil").embed_perfil(self._membro())
        await interaction.response.edit_message(content=None, embed=e, view=VoltarPainelView(self.cog, self.user, self.alvo))

    @discord.ui.button(label="Platinas", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def platinas(self, interaction: discord.Interaction, button: discord.ui.Button):
        membro = self._membro()
        texto = await self.cog.bot.get_cog("Perfil").texto_platinas(membro)
        if texto is None:
            texto = f"## 📜 Coleção de {membro.display_name}\n\nAinda não há platinas aprovadas para exibir."
        await interaction.response.edit_message(content=texto, embeds=[], view=VoltarPainelView(self.cog, self.user, membro))

    @discord.ui.button(label="Ranking", style=discord.ButtonStyle.secondary, emoji="🏆", row=1)
    async def ranking(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RankingView(self.cog, "platinas", self.user, self._membro())
        texto = await self.cog.bot.get_cog("Ranking").texto_ranking("platinas")
        await interaction.response.edit_message(content=texto, embeds=[], view=view)

    @discord.ui.button(label="Ajuda", style=discord.ButtonStyle.secondary, emoji="❓", row=1)
    async def ajuda(self, interaction: discord.Interaction, button: discord.ui.Button):
        texto = self.cog.bot.get_cog("Perfil").texto_ajuda()
        await interaction.response.edit_message(content=texto, embeds=[], view=VoltarPainelView(self.cog, self.user, self.alvo))

    @discord.ui.button(label="Meu santuário", style=discord.ButtonStyle.success, emoji="🏛️", row=2)
    async def meu_santuario(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.bot.get_cog("Santuario").abrir_meu(interaction)

    @discord.ui.button(label="Visitar santuário", style=discord.ButtonStyle.primary, emoji="🚪", row=2)
    async def visitar_santuario(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.alvo is None:
            return await interaction.response.edit_message(
                content="🔎 **Antes de visitar:** selecione um membro no menu superior e tente novamente.",
                embed=await self.embed(), view=self,
            )
        await self.cog.bot.get_cog("Santuario").visitar(interaction, self.alvo.id)


class VoltarPainelView(discord.ui.View):
    """Retorna à tela de perfil sem publicar uma nova mensagem."""
    def __init__(self, cog, owner, alvo=None):
        super().__init__(timeout=900)
        self.cog, self.owner_id = cog, owner.id
        self.owner, self.alvo = owner, alvo

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Este painel pertence a outra pessoa.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Voltar ao painel", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PainelView(self.cog, self.owner)
        view.alvo = self.alvo
        await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)


class RankingView(discord.ui.View):
    def __init__(self, cog, tipo: str, owner=None, alvo=None):
        super().__init__(timeout=900)
        from cogs.ranking import TIPOS
        self.cog = cog
        self.owner = owner
        self.alvo = alvo
        self.sel = discord.ui.Select(
            placeholder="Filtrar ranking",
            options=[discord.SelectOption(label=nome, value=k, default=k == tipo) for k, nome in TIPOS.items()],
            row=0,
        )
        self.sel.callback = self.trocar
        self.add_item(self.sel)

    async def trocar(self, interaction: discord.Interaction):
        tipo = self.sel.values[0]
        for o in self.sel.options:
            o.default = o.value == tipo
        texto = await self.cog.bot.get_cog("Ranking").texto_ranking(tipo)
        await interaction.response.edit_message(content=texto, embeds=[], view=self)

    @discord.ui.button(label="Voltar ao painel", style=discord.ButtonStyle.secondary, emoji="↩️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        owner = self.owner or interaction.user
        view = PainelView(self.cog, owner)
        view.alvo = self.alvo
        await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)


class PlatinaModal(discord.ui.Modal):
    """Formulário com o campo para anexar o print (precisa de discord.py >= 2.6)."""

    def __init__(self, cog):
        super().__init__(title="Registrar platina")
        self.cog = cog
        self.jogo = discord.ui.TextInput(placeholder="Ex.: Elden Ring", max_length=100)
        self.plataforma = discord.ui.Select(
            placeholder="Escolha a plataforma",
            options=[discord.SelectOption(label=p, value=p) for p in PLATAFORMAS],
        )
        self.data = discord.ui.TextInput(default=hoje().strftime("%d/%m/%Y"), placeholder="DD/MM/AAAA", max_length=10)
        self.prova = discord.ui.FileUpload(required=True, min_values=1, max_values=10)
        self.add_item(discord.ui.Label(text="Jogo", component=self.jogo))
        self.add_item(discord.ui.Label(text="Plataforma", component=self.plataforma))
        self.add_item(discord.ui.Label(text="Data da conquista", component=self.data))
        self.add_item(discord.ui.Label(text="Print da platina (comprovante)", component=self.prova))

    async def on_submit(self, interaction: discord.Interaction):
        if not self.prova.values or not self.plataforma.values:
            return await interaction.response.send_message("Preencha a plataforma e anexe pelo menos um comprovante.", ephemeral=True)
        await self.cog.registrar_platina(
            interaction, self.jogo.value, self.plataforma.values[0], self.data.value, list(self.prova.values)
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        logging.getLogger("colizeu").exception("Erro no formulário de platina", exc_info=error)
        if not interaction.response.is_done():
            await interaction.response.send_message("Algo deu errado ao enviar. Tente de novo.", ephemeral=True)


class PainelPrincipalPublicoView(discord.ui.View):
    """Painel público persistente; cada botão abre uma interface privada por membro."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Platinas", style=discord.ButtonStyle.success, emoji="🏆", custom_id="nara:painel:principal:platinas", row=0)
    async def platinas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.abrir_painel(interaction)

    @discord.ui.button(label="Perfil", style=discord.ButtonStyle.primary, emoji="👤", custom_id="nara:painel:principal:perfil", row=0)
    async def perfil(self, interaction: discord.Interaction, button: discord.ui.Button):
        perfil_cog = self.cog.bot.get_cog("Perfil")
        if perfil_cog is None:
            return await interaction.response.send_message("O perfil está indisponível no momento.", ephemeral=True)
        embed = await perfil_cog.embed_perfil(interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Runs", style=discord.ButtonStyle.danger, emoji="⚔️", custom_id="nara:painel:principal:runs", row=1)
    async def runs(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.cog.bot.get_cog("Soulslike")
        if cog is None:
            return await interaction.response.send_message("O sistema de runs está indisponível no momento.", ephemeral=True)
        from cogs.soulslike import CentralView
        await interaction.response.send_message(embed=cog.embed_central(), view=CentralView(cog), ephemeral=True)

    @discord.ui.button(label="Desafios", style=discord.ButtonStyle.secondary, emoji="📜", custom_id="nara:painel:principal:desafios", row=1)
    async def desafios(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.cog.bot.get_cog("Soulslike")
        if cog is None:
            return await interaction.response.send_message("O sistema de desafios está indisponível no momento.", ephemeral=True)
        await cog.mostrar_desafios(interaction)


class PainelPublicoView(discord.ui.View):
    """Botão fixo da mensagem postada por /painel_platinas (continua funcionando após reiniciar o bot)."""

    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Abrir painel", style=discord.ButtonStyle.success, emoji="🏛️", custom_id="plat:painel")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.abrir_painel(interaction)


async def setup(bot):
    await bot.add_cog(Platinas(bot))
