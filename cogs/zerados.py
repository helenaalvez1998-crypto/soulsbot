import datetime as dt
import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
from admin_config import GuildConfig
from cogs.platinas import eh_moderador, sincronizar_patente, hoje
from levels import nivel_por_xp, patente_por_nivel
from utils import get_text_channel, upsert_panel, erro_comando

log = logging.getLogger("zerados")

MEDALHAS = ["🥇", "🥈", "🥉"]
PLATAFORMAS = ["PS5", "PS4", "PS3", "PC", "Xbox Series", "Xbox One", "Switch", "Mobile", "Outra"]
EXT_IMAGEM = (".png", ".jpg", ".jpeg", ".webp", ".gif")
EXT_VIDEO = (".mp4", ".mov", ".webm")


def data_legivel(valor) -> str:
    try:
        return dt.date.fromisoformat(str(valor)).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(valor)


def eh_imagem(anexo: discord.Attachment) -> bool:
    return (anexo.content_type or "").lower().startswith("image/") or anexo.filename.lower().endswith(EXT_IMAGEM)


def eh_midia(anexo: discord.Attachment) -> bool:
    tipo = (anexo.content_type or "").lower()
    return tipo.startswith(("image/", "video/")) or anexo.filename.lower().endswith(EXT_IMAGEM + EXT_VIDEO)


class Zerados(commands.Cog):
    """Registro de jogos zerados: versão leve das platinas, sem aprovação da moderação."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(ZeradosPublicoView(self))

    def painel_view(self, user) -> "ZeradosPainelView":
        return ZeradosPainelView(self, user)

    # ------------------------------------------------------------ comandos
    @app_commands.command(name="zerados", description="Abre seu painel de jogos zerados.")
    @app_commands.guild_only()
    async def zerados(self, interaction: discord.Interaction):
        await self.abrir_painel(interaction)

    async def abrir_painel(self, interaction: discord.Interaction):
        view = self.painel_view(interaction.user)
        await interaction.response.send_message(embed=await view.embed(), view=view, ephemeral=True)

    @app_commands.command(name="postar_painel_zerados", description="[MOD] Publica neste canal o botão para abrir o painel de zerados.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def postar_painel_zerados(self, interaction: discord.Interaction):
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        texto = (
            "# ✅ Jogos Zerados\n\n"
            "Não curte platinar, mas zerou o jogo? Use o botão abaixo para **registrar**, ver sua lista "
            "e acompanhar o ranking de quem mais finalizou jogos.\n\n"
            "_Print é opcional. Se enviar, ele aparece no anúncio do canal._"
        )
        key = f"panel:zerados:{interaction.guild_id}:{interaction.channel_id}"
        await upsert_panel(
            self.bot, interaction.channel, key, marker="zer:painel",
            content=texto, embeds=[], view=ZeradosPublicoView(self),
        )
        await interaction.response.send_message("✅ Painel de zerados atualizado neste canal.", ephemeral=True)

    @app_commands.command(name="remover_zerado", description="Remove um registro de jogo zerado (o seu, ou qualquer um se for moderador).")
    @app_commands.describe(registro="Número do registro, mostrado na lista (ex.: 12)")
    @app_commands.guild_only()
    async def remover_zerado(self, interaction: discord.Interaction, registro: int):
        db = self.bot.db
        z = await db.get_zerado(registro)
        if z is None:
            return await interaction.response.send_message("Registro não encontrado.", ephemeral=True)
        if z["user_id"] != interaction.user.id and not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Você só pode remover os seus próprios registros.", ephemeral=True)

        await db.apagar_zerado(registro)
        await db.log(interaction.user.id, "zerado_removido", f"id={registro} user={z['user_id']} jogo={z['game']}")

        extra = ""
        if z["xp_awarded"] or z["denarios_awarded"]:
            _, novo, _ = await db.add_reward(z["user_id"], -z["xp_awarded"], -z["denarios_awarded"])
            membro = interaction.guild.get_member(z["user_id"])
            if membro:
                await sincronizar_patente(interaction.guild, membro, novo)
            extra = f" A recompensa (−{z['xp_awarded']} XP, −{z['denarios_awarded']} Denários) foi devolvida."
        await interaction.response.send_message(f"🗑️ Registro #{registro} (**{z['game']}**) removido.{extra}", ephemeral=True)

    async def cog_app_command_error(self, interaction, error):
        await erro_comando(interaction, error)

    # ------------------------------------------------------------ registro
    async def registrar_zerado(self, interaction: discord.Interaction, jogo: str, plataforma: str,
                               data: str, comentario: str, capturas):
        try:
            d = dt.datetime.strptime(data.strip(), "%d/%m/%Y").date()
        except ValueError:
            return await interaction.response.send_message("Data inválida. Use DD/MM/AAAA.", ephemeral=True)
        if d > hoje():
            return await interaction.response.send_message("A data não pode estar no futuro.", ephemeral=True)

        jogo, plataforma = jogo.strip()[:100], plataforma.strip()[:30]
        comentario = (comentario or "").strip()[:300]
        if not jogo:
            return await interaction.response.send_message("Informe o nome do jogo.", ephemeral=True)

        capturas = list(capturas or [])
        for anexo in capturas:
            if not eh_midia(anexo):
                return await interaction.response.send_message(
                    f"Arquivo não suportado: {anexo.filename}. Envie imagens ou vídeos.", ephemeral=True
                )

        db = self.bot.db
        if await db.zerado_duplicado(interaction.user.id, jogo, plataforma):
            return await interaction.response.send_message(
                "Você já registrou esse jogo nessa plataforma. Para refazer, remova o registro antigo com `/remover_zerado`.",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        # Recompensa (com limite por 24h para evitar farm de XP)
        xp = dinheiro = 0
        xp_zerado = await GuildConfig.get(db, interaction.guild_id, "xp_zerado") or config.XP_ZERADO
        den_zerado = await GuildConfig.get(db, interaction.guild_id, "denarios_zerado") or config.DENARIOS_ZERADO
        limite = await GuildConfig.get(db, interaction.guild_id, "zerados_xp_limite") or config.ZERADOS_XP_LIMITE_DIARIO
        if xp_zerado > 0 or den_zerado > 0:
            if limite <= 0 or await db.contar_zerados_recentes(interaction.user.id) < limite:
                xp, dinheiro = xp_zerado, den_zerado

        zerado_id = await db.criar_zerado(
            interaction.user.id, jogo, plataforma, d.isoformat(), comentario, xp, dinheiro
        )
        await db.log(interaction.user.id, "zerado_registrado", f"id={zerado_id} jogo={jogo}")

        subiu = False
        novo_nivel = None
        if xp or dinheiro:
            antigo, novo_nivel, _ = await db.add_reward(interaction.user.id, xp, dinheiro)
            subiu = novo_nivel > antigo
            if subiu and isinstance(interaction.user, discord.Member):
                await sincronizar_patente(interaction.guild, interaction.user, novo_nivel)

        anunciado = await self._anunciar(interaction, zerado_id, jogo, plataforma, d, comentario, capturas, xp, dinheiro, novo_nivel if subiu else None)

        linhas = [f"✅ **{jogo}** registrado como zerado! (registro #{zerado_id})"]
        if xp or dinheiro:
            linhas.append(f"**Recompensa:** +{xp} XP · +{dinheiro} Denários")
        elif xp_zerado > 0:
            linhas.append(f"_Você já atingiu o limite de {limite} zerados com recompensa nas últimas 24h; este registro entrou sem XP._")
        if subiu:
            linhas.append(f"⬆️ **Novo nível:** {novo_nivel} — {patente_por_nivel(novo_nivel)}")
        if capturas and not anunciado:
            linhas.append("_Os prints só são guardados quando existe um canal de anúncios de zerados configurado._")
        await interaction.edit_original_response(content="\n".join(linhas))

    async def _anunciar(self, interaction, zerado_id, jogo, plataforma, data, comentario, capturas, xp, dinheiro, novo_nivel) -> bool:
        zerados_ch_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "zerados_channel")
        if not zerados_ch_id:
            return False
        canal = await get_text_channel(self.bot, zerados_ch_id)
        if canal is None:
            return False
        try:
            arquivos = [await a.to_file() for a in capturas]
            embed = discord.Embed(
                title="✅ Jogo zerado!",
                description=f"{interaction.user.mention} zerou **{jogo}**",
                color=discord.Color.green(),
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name="Plataforma", value=plataforma, inline=True)
            embed.add_field(name="Data", value=data.strftime("%d/%m/%Y"), inline=True)
            if comentario:
                embed.add_field(name="Comentário", value=comentario, inline=False)
            if novo_nivel:
                embed.add_field(name="⬆️ Novo nível", value=f"{novo_nivel} — {patente_por_nivel(novo_nivel)}", inline=False)
            rodape = f"Registro #{zerado_id}"
            if xp or dinheiro:
                rodape += f" · +{xp} XP · +{dinheiro} Denários"
            embed.set_footer(text=rodape)
            for anexo, arquivo in zip(capturas, arquivos):
                if eh_imagem(anexo):
                    embed.set_image(url=f"attachment://{arquivo.filename}")
                    break
            await canal.send(embed=embed, files=arquivos or discord.utils.MISSING)
            return True
        except discord.HTTPException:
            log.exception("Falha ao anunciar zerado #%s", zerado_id)
            return False

    # ------------------------------------------------------------ textos
    async def texto_lista(self, membro) -> str:
        rows = await self.bot.db.zerados_do_usuario(membro.id)
        cabecalho = f"## ✅ Zerados de {membro.display_name}\n\n"
        if not rows:
            return cabecalho + "Ainda não há jogos zerados registrados."
        linhas = []
        for r in rows[:30]:
            linha = f"✅ **{r['game']}** · `{r['platform']}` · {data_legivel(r['finished_at'])} · `#{r['id']}`"
            if len(cabecalho + "\n".join(linhas + [linha])) > 1800:
                break
            linhas.append(linha)
        texto = cabecalho + "\n".join(linhas)
        if len(rows) > len(linhas):
            texto += f"\n\n_Mostrando {len(linhas)} de {len(rows)} jogos._"
        return texto

    async def texto_ranking(self, tipo: str) -> str:
        db = self.bot.db
        if tipo == "mensal":
            mes = dt.datetime.now(config.BRAZIL_TZ).strftime("%Y-%m")
            rows, titulo = await db.ranking_zerados_mensal(mes), f"Zerados de {mes}"
        else:
            rows, titulo = await db.ranking_zerados(), "Ranking de Zerados"
        if not rows:
            return f"## ✅ {titulo}\n\nAinda não há dados nesse ranking."
        linhas = []
        for i, r in enumerate(rows):
            pos = MEDALHAS[i] if i < 3 else f"`{i + 1:>2}.`"
            linhas.append(f"{pos} <@{r['user_id']}> — **{r['valor']}** zerados")
        return f"## ✅ {titulo}\n\n" + "\n".join(linhas) + "\n\n_Atualizado ao consultar._"


# ------------------------------------------------------------------ painel do usuário
class ZeradosPainelView(discord.ui.View):
    def __init__(self, cog: Zerados, user):
        super().__init__(timeout=900)
        self.cog, self.user = cog, user
        self.alvo = None  # membro consultado (padrão: você)
        self.sel_membro = discord.ui.UserSelect(placeholder="🔎 Consultar outro membro (opcional)", row=0)
        self.sel_membro.callback = self.trocar_membro
        self.add_item(self.sel_membro)

    def _membro(self):
        return self.alvo or self.user

    async def embed(self) -> discord.Embed:
        membro = self._membro()
        db = self.cog.bot.db
        qtd = await db.contar_zerados(membro.id)
        user = await db.get_user(membro.id)
        nivel = nivel_por_xp(user["xp"])
        e = discord.Embed(
            title="✅ Painel de Zerados",
            description="Registre os jogos que você finalizou, veja sua lista e o ranking.",
            color=discord.Color.green(),
        )
        e.set_thumbnail(url=membro.display_avatar.url)
        e.add_field(name="Consultando", value=f"**{membro.display_name}**" + (" (você)" if membro == self.user else ""), inline=False)
        e.add_field(name="✅ Zerados", value=str(qtd))
        e.add_field(name="Rank Zerados", value=f"#{await db.posicao_zerados(qtd)}" if qtd else "—")
        e.add_field(name="Nível", value=f"{nivel} — {patente_por_nivel(nivel)}")
        return e

    async def trocar_membro(self, interaction: discord.Interaction):
        escolhido = self.sel_membro.values[0]
        if getattr(escolhido, "bot", False):
            return await interaction.response.send_message("Bots não têm perfil.", ephemeral=True)
        self.alvo = escolhido if isinstance(escolhido, discord.Member) else interaction.guild.get_member(escolhido.id)
        await interaction.response.edit_message(embed=await self.embed(), view=self)

    @discord.ui.button(label="Registrar zerado", style=discord.ButtonStyle.success, emoji="📤", row=1)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ZeradoModal(self.cog))

    @discord.ui.button(label="Lista", style=discord.ButtonStyle.primary, emoji="📜", row=1)
    async def lista(self, interaction: discord.Interaction, button: discord.ui.Button):
        membro = self._membro()
        texto = await self.cog.texto_lista(membro)
        await interaction.response.edit_message(content=texto, embeds=[], view=VoltarZeradosView(self.cog, self.user, self.alvo))

    @discord.ui.button(label="Ranking", style=discord.ButtonStyle.secondary, emoji="🏆", row=1)
    async def ranking(self, interaction: discord.Interaction, button: discord.ui.Button):
        texto = await self.cog.texto_ranking("total")
        await interaction.response.edit_message(content=texto, embeds=[], view=RankingZeradosView(self.cog, self.user, self.alvo))

    @discord.ui.button(label="Voltar ao Coliseu", style=discord.ButtonStyle.secondary, emoji="↩️", row=2)
    async def voltar_coliseu(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.platinas import ColiseuView
        platinas = self.cog.bot.get_cog("Platinas")
        if platinas is None:
            return await interaction.response.send_message("O Coliseu não está disponível.", ephemeral=True)
        view = ColiseuView(platinas, interaction.user)
        await interaction.response.edit_message(content=view.texto(), embeds=[], view=view)


class VoltarZeradosView(discord.ui.View):
    """Volta ao painel sem criar uma nova mensagem."""

    def __init__(self, cog: Zerados, owner, alvo=None):
        super().__init__(timeout=900)
        self.cog, self.owner, self.alvo = cog, owner, alvo

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("Este painel pertence a outra pessoa.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Voltar ao painel", style=discord.ButtonStyle.secondary, emoji="↩️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ZeradosPainelView(self.cog, self.owner)
        view.alvo = self.alvo
        await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)


class RankingZeradosView(VoltarZeradosView):
    def __init__(self, cog: Zerados, owner, alvo=None):
        super().__init__(cog, owner, alvo)
        self.sel = discord.ui.Select(
            placeholder="Filtrar ranking",
            options=[
                discord.SelectOption(label="Zerados (total)", value="total", default=True),
                discord.SelectOption(label="Zerados do mês", value="mensal"),
            ],
            row=0,
        )
        self.sel.callback = self.trocar
        self.add_item(self.sel)

    async def trocar(self, interaction: discord.Interaction):
        tipo = self.sel.values[0]
        for o in self.sel.options:
            o.default = o.value == tipo
        texto = await self.cog.texto_ranking(tipo)
        await interaction.response.edit_message(content=texto, embeds=[], view=self)


class ZeradoModal(discord.ui.Modal):
    """Formulário de registro (anexo é opcional). Precisa de discord.py >= 2.6."""

    def __init__(self, cog: Zerados):
        super().__init__(title="Registrar jogo zerado")
        self.cog = cog
        self.jogo = discord.ui.TextInput(placeholder="Ex.: Hollow Knight", max_length=100)
        self.plataforma = discord.ui.Select(
            placeholder="Escolha a plataforma",
            options=[discord.SelectOption(label=p, value=p) for p in PLATAFORMAS],
        )
        self.data = discord.ui.TextInput(default=hoje().strftime("%d/%m/%Y"), placeholder="DD/MM/AAAA", max_length=10)
        self.comentario = discord.ui.TextInput(
            style=discord.TextStyle.paragraph, required=False, max_length=300,
            placeholder="O que achou? Nota, final, dificuldade... (opcional)",
        )
        self.prova = discord.ui.FileUpload(required=False, min_values=0, max_values=4)
        self.add_item(discord.ui.Label(text="Jogo", component=self.jogo))
        self.add_item(discord.ui.Label(text="Plataforma", component=self.plataforma))
        self.add_item(discord.ui.Label(text="Data em que zerou", component=self.data))
        self.add_item(discord.ui.Label(text="Comentário (opcional)", component=self.comentario))
        self.add_item(discord.ui.Label(text="Print dos créditos (opcional)", component=self.prova))

    async def on_submit(self, interaction: discord.Interaction):
        if not self.plataforma.values:
            return await interaction.response.send_message("Escolha a plataforma.", ephemeral=True)
        await self.cog.registrar_zerado(
            interaction, self.jogo.value, self.plataforma.values[0], self.data.value,
            self.comentario.value, list(self.prova.values),
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        log.exception("Erro no formulário de zerado", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send("Algo deu errado ao registrar. Tente de novo.", ephemeral=True)
        else:
            await interaction.response.send_message("Algo deu errado ao registrar. Tente de novo.", ephemeral=True)


class ZeradosPublicoView(discord.ui.View):
    """Botão fixo do painel postado no canal (continua funcionando após reiniciar o bot)."""

    def __init__(self, cog: Zerados):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Abrir painel de zerados", style=discord.ButtonStyle.success, emoji="✅", custom_id="zer:painel")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.abrir_painel(interaction)


async def setup(bot):
    await bot.add_cog(Zerados(bot))
