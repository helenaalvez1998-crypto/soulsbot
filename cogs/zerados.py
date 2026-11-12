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
    """Registros de jogos zerados enviados à Central de Aprovação da moderação."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(ZeradosPublicoView(self))
        self.bot.add_view(ZeradoRevisaoView(self))

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
            "Não curte platinar, mas zerou o jogo? Use o botão abaixo para **enviar seu registro**, "
            "ver sua lista aprovada e acompanhar o ranking de quem mais finalizou jogos.\n\n"
            "_Os registros passam pela Central de Aprovação. XP/Denários e publicação são liberados após a aprovação. Print é opcional._"
        )
        key = f"panel:zerados:{interaction.guild_id}:{interaction.channel_id}"
        await upsert_panel(
            self.bot, interaction.channel, key, marker="zer:painel",
            content=texto, embeds=[], view=ZeradosPublicoView(self),
        )
        await self.bot.db.set_kv(
            f"rotating:channel:zerados:{interaction.guild_id}", str(interaction.channel_id)
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

        removido = await db.remover_zerado_com_recompensa(registro)
        if removido is None:
            return await interaction.response.send_message("Este registro já foi removido por outra ação.", ephemeral=True)
        if removido["status"] == "pending" and removido["proof_msg_id"]:
            try:
                mod_ch_id = await GuildConfig.get(db, interaction.guild_id, "mod_channel")
                canal_mod = await get_text_channel(self.bot, mod_ch_id) if mod_ch_id else None
                if canal_mod:
                    mensagem = await canal_mod.fetch_message(int(removido["proof_msg_id"]))
                    if mensagem.embeds:
                        embed_cancelado = mensagem.embeds[0]
                        embed_cancelado.color = discord.Color.dark_grey()
                        embed_cancelado.set_footer(text=f"ZeradoID:{registro} · CANCELADO")
                        embed_cancelado.add_field(name="Resultado", value=f"Cancelado por {interaction.user.mention}", inline=False)
                        await mensagem.edit(content=f"🗑️ Solicitação `#{registro}` cancelada.", embed=embed_cancelado, view=None)
            except discord.HTTPException:
                log.exception("Falha ao marcar cartão do zerado #%s como cancelado", registro)
        try:
            await db.log(interaction.user.id, "zerado_removido", f"id={registro} user={z['user_id']} jogo={z['game']}")
        except Exception:
            log.exception("Zerado #%s removido, mas falhou o log de auditoria", registro)

        extra = ""
        if z["xp_awarded"] or z["denarios_awarded"]:
            novo = nivel_por_xp(int(removido["new_xp"]))
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
        if len(capturas) > 5:
            return await interaction.response.send_message("Envie no máximo 5 comprovantes por registro.", ephemeral=True)
        total_bytes = 0
        for anexo in capturas:
            if not eh_midia(anexo):
                return await interaction.response.send_message(
                    f"Arquivo não suportado: {anexo.filename}. Envie imagens ou vídeos.", ephemeral=True
                )
            tamanho = int(getattr(anexo, "size", 0) or 0)
            if tamanho > 20 * 1024 * 1024:
                return await interaction.response.send_message(
                    f"O arquivo {anexo.filename} excede o limite de 20 MB.", ephemeral=True
                )
            total_bytes += tamanho
        if total_bytes > 40 * 1024 * 1024:
            return await interaction.response.send_message(
                "O total dos comprovantes não pode ultrapassar 40 MB por registro.", ephemeral=True
            )

        db = self.bot.db
        if await db.zerado_duplicado(interaction.user.id, jogo, plataforma):
            return await interaction.response.send_message(
                "Você já tem um pedido pendente ou um registro aprovado desse jogo nessa plataforma. Aguarde a análise ou use **Remover zerado** no `/nara` para corrigir.",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            linhas = await self.gravar_zerado(interaction.guild, interaction.user, d, jogo, plataforma, comentario, capturas)
        except ValueError as exc:
            return await interaction.edit_original_response(content=str(exc))
        await interaction.edit_original_response(content="\n".join(linhas))

    async def gravar_zerado(self, guild, user, d, jogo, plataforma, comentario, capturas) -> list[str]:
        """Cria uma solicitação pendente e envia o cartão com comprovantes ao canal central."""
        db = self.bot.db
        mod_ch_id = await GuildConfig.get(db, guild.id, "mod_channel")
        if not mod_ch_id:
            raise ValueError(
                "A Central de Aprovação ainda não está configurada. Peça à administração para definir "
                "o **Canal de Moderação** em `/adm` antes de enviar um zerado."
            )
        canal = await get_text_channel(self.bot, mod_ch_id)
        if canal is None:
            raise ValueError(
                "Não consegui acessar a Central de Aprovação. Confira se o canal configurado existe "
                "e se o bot pode visualizar e enviar mensagens nele."
            )

        zerado_id = await db.criar_zerado_pendente(
            user.id, jogo, plataforma, d.isoformat(), comentario
        )
        if zerado_id is None:
            raise ValueError(
                "Você já possui um registro pendente ou aprovado desse jogo nessa plataforma. "
                "Aguarde a revisão ou use **Remover zerado** no `/nara` para corrigir um registro aprovado."
            )

        arquivos = []
        mensagem = None
        try:
            arquivos = [await anexo.to_file() for anexo in capturas]
            embed = discord.Embed(
                title="📥 NOVO REGISTRO — JOGO ZERADO",
                description=f"**Solicitante:** {user.mention}\n**Jogo:** {jogo}",
                color=config.COR_PRATA,
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Plataforma", value=plataforma, inline=True)
            embed.add_field(name="Data em que zerou", value=d.strftime("%d/%m/%Y"), inline=True)
            if comentario:
                embed.add_field(name="Comentário", value=comentario, inline=False)
            if capturas:
                embed.add_field(name="Comprovantes", value=f"{len(capturas)} arquivo(s) anexado(s)", inline=False)
                for anexo, arquivo in zip(capturas, arquivos):
                    if eh_imagem(anexo):
                        embed.set_image(url=f"attachment://{arquivo.filename}")
                        break
            else:
                embed.add_field(name="Comprovantes", value="Não enviados (opcional)", inline=False)
            embed.set_footer(text=f"ZeradoID:{zerado_id} · PENDENTE DE APROVAÇÃO")
            mensagem = await canal.send(
                content=f"📥 Registro de {user.mention} aguardando análise.",
                embed=embed,
                files=arquivos or discord.utils.MISSING,
                view=ZeradoRevisaoView(self),
            )
            vinculada = await db.definir_mensagem_revisao_zerado(zerado_id, mensagem.id)
            if not vinculada:
                raise RuntimeError("Não consegui vincular o cartão ao registro pendente.")
            try:
                await db.log(user.id, "zerado_enviado_revisao", f"id={zerado_id} jogo={jogo}")
            except Exception:
                log.exception("Zerado #%s enviado para revisão, mas falhou o log de auditoria", zerado_id)
        except Exception as exc:
            log.exception("Falha ao encaminhar zerado #%s para a moderação", zerado_id)
            if mensagem is not None:
                try:
                    await mensagem.delete()
                except discord.HTTPException:
                    log.exception("Falha ao remover cartão órfão do zerado #%s", zerado_id)
            try:
                await db.apagar_zerado(zerado_id)
            except Exception:
                log.exception("Falha ao limpar registro pendente incompleto #%s", zerado_id)
            raise ValueError(
                "Não consegui encaminhar seu registro à Central de Aprovação. "
                "Nenhum registro foi mantido; confira as permissões do bot e tente novamente."
            ) from exc

        return [
            f"📨 **{jogo}** enviado para análise da moderação (solicitação `#{zerado_id}`).",
            "O registro só aparecerá no perfil/ranking e só concederá XP/Denários depois da aprovação.",
        ]

    async def _anunciar_aprovado(self, interaction: discord.Interaction, registro: dict, novo_nivel=None) -> bool:
        """Publica o zerado aprovado no canal de anúncios, separado da fila administrativa."""
        try:
            zerados_ch_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "zerados_channel")
            if not zerados_ch_id:
                return False
            canal = await get_text_channel(self.bot, zerados_ch_id)
            if canal is None:
                return False
            membro = interaction.guild.get_member(int(registro["user_id"])) if interaction.guild else None
            mencao = membro.mention if membro else f"<@{registro['user_id']}>"
            embed = discord.Embed(
                title="✅ Jogo zerado aprovado!",
                description=f"{mencao} zerou **{registro['game']}**",
                color=discord.Color.green(),
            )
            if membro:
                embed.set_thumbnail(url=membro.display_avatar.url)
            embed.add_field(name="Plataforma", value=registro["platform"], inline=True)
            embed.add_field(name="Data", value=data_legivel(registro["finished_at"]), inline=True)
            if registro.get("comment"):
                embed.add_field(name="Comentário", value=registro["comment"], inline=False)
            anexos = list(getattr(interaction.message, "attachments", []) or [])
            if anexos:
                links = [f"[Comprovante {i}]({anexo.url})" for i, anexo in enumerate(anexos, start=1)]
                embed.add_field(name="Comprovantes", value=" · ".join(links), inline=False)
                primeira_imagem = next((a for a in anexos if (a.content_type or "").startswith("image/")), None)
                if primeira_imagem:
                    embed.set_image(url=primeira_imagem.url)
            recompensas = f"+{registro['xp']} XP · +{registro['denarios']} Denários"
            if registro["daily_limit_reached"]:
                recompensas = "Sem recompensa: limite diário de registros premiados atingido"
            embed.add_field(name="Recompensa", value=recompensas, inline=False)
            if novo_nivel:
                embed.add_field(name="⬆️ Novo nível", value=f"{novo_nivel} — {patente_por_nivel(novo_nivel)}", inline=False)
            embed.set_footer(text=f"Registro #{registro['id']} · aprovado pela moderação")
            await canal.send(embed=embed)
            return True
        except Exception:
            log.exception("Falha ao anunciar zerado aprovado #%s", registro.get("id"))
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


class ZeradoRevisaoView(discord.ui.View):
    """Aprovação/rejeição persistente dos registros de jogos zerados."""

    def __init__(self, cog: Zerados):
        super().__init__(timeout=None)
        self.cog = cog

    async def _processar(self, interaction: discord.Interaction, aprovar: bool):
        if not await eh_moderador(interaction.user, self.cog.bot.db):
            return await interaction.response.send_message("Apenas moderadores podem revisar este registro.", ephemeral=True)
        if not interaction.message or not interaction.message.embeds:
            return await interaction.response.send_message("Cartão de revisão inválido.", ephemeral=True)
        footer = interaction.message.embeds[0].footer.text or ""
        import re
        match = re.search(r"\bZeradoID:(\d+)\b", footer)
        if not match:
            return await interaction.response.send_message("Não consegui localizar o ID deste zerado.", ephemeral=True)
        zerado_id = int(match.group(1))
        db = self.cog.bot.db
        pendente = await db.get_zerado(zerado_id)
        if pendente is None or pendente["status"] != "pending":
            return await interaction.response.send_message("Este registro já foi processado ou removido.", ephemeral=True)
        if int(pendente["user_id"]) == interaction.user.id:
            return await interaction.response.send_message("Você não pode aprovar ou rejeitar o próprio registro.", ephemeral=True)

        if aprovar:
            xp = await GuildConfig.get(db, interaction.guild_id, "xp_zerado")
            denarios = await GuildConfig.get(db, interaction.guild_id, "denarios_zerado")
            limite = await GuildConfig.get(db, interaction.guild_id, "zerados_xp_limite")
            if xp is None:
                xp = config.XP_ZERADO
            if denarios is None:
                denarios = config.DENARIOS_ZERADO
            if limite is None:
                limite = config.ZERADOS_XP_LIMITE_DIARIO
            resultado = await db.aprovar_zerado_com_recompensa(
                zerado_id, interaction.user.id, int(xp), int(denarios), int(limite)
            )
            if resultado is None:
                return await interaction.response.send_message("Outro moderador já processou este registro.", ephemeral=True)
            from cogs.moderacao_utils import sincronizar_cartao
            await sincronizar_cartao(self.cog.bot, interaction.guild_id, "zerados", zerado_id, "approved", interaction.user.id)
            status_texto = "✅ Aprovado"
            cor = discord.Color.green()
            recompensa = f"+{resultado['xp']} XP · +{resultado['denarios']} Denários"
            if resultado["daily_limit_reached"]:
                recompensa = "Sem recompensa: limite diário atingido"
            embed = interaction.message.embeds[0]
            embed.color = cor
            embed.set_footer(text=f"ZeradoID:{zerado_id} · APROVADO")
            embed.add_field(
                name="Resultado",
                value=f"{status_texto} por {interaction.user.mention}\n**Recompensa:** {recompensa}",
                inline=False,
            )
            try:
                await interaction.response.edit_message(
                    content=f"✅ Solicitação `#{zerado_id}` aprovada por {interaction.user.mention}.",
                    embed=embed, view=None,
                )
            except discord.HTTPException:
                log.exception("Zerado #%s aprovado, mas o cartão não foi atualizado", zerado_id)
                if not interaction.response.is_done():
                    await interaction.response.send_message("A aprovação foi salva, mas não consegui atualizar o cartão.", ephemeral=True)
                else:
                    await interaction.followup.send("A aprovação foi salva, mas não consegui atualizar o cartão.", ephemeral=True)

            membro = interaction.guild.get_member(int(resultado["user_id"])) if interaction.guild else None
            subiu = resultado["new_level"] > resultado["old_level"]
            if membro and subiu:
                await sincronizar_patente(interaction.guild, membro, int(resultado["new_level"]))
            await self.cog._anunciar_aprovado(
                interaction, resultado, int(resultado["new_level"]) if subiu else None
            )
            try:
                await db.log(interaction.user.id, "zerado_aprovado", f"id={zerado_id} user={resultado['user_id']}")
            except Exception:
                log.exception("Zerado #%s aprovado, mas falhou o log de auditoria", zerado_id)
            painel = self.cog.bot.get_cog("Colizeu")
            if painel:
                try:
                    await painel.atualizar()
                except Exception:
                    log.exception("Falha ao atualizar painel do Coliseu após aprovação do zerado #%s", zerado_id)
            santuario = self.cog.bot.get_cog("Santuario")
            if santuario:
                try:
                    await santuario.atualizar(int(resultado["user_id"]))
                except Exception:
                    log.exception("Falha ao atualizar santuário após aprovação do zerado #%s", zerado_id)
            return

        alterado = await db.rejeitar_zerado(zerado_id, interaction.user.id)
        if not alterado:
            return await interaction.response.send_message("Outro moderador já processou este registro.", ephemeral=True)
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_footer(text=f"ZeradoID:{zerado_id} · REJEITADO")
        embed.add_field(name="Resultado", value=f"❌ Rejeitado por {interaction.user.mention}", inline=False)
        try:
            await interaction.response.edit_message(
                content=f"❌ Solicitação `#{zerado_id}` rejeitada por {interaction.user.mention}.",
                embed=embed, view=None,
            )
        except discord.HTTPException:
            log.exception("Zerado #%s rejeitado, mas o cartão não foi atualizado", zerado_id)
            if not interaction.response.is_done():
                await interaction.response.send_message("A rejeição foi salva, mas não consegui atualizar o cartão.", ephemeral=True)
            else:
                await interaction.followup.send("A rejeição foi salva, mas não consegui atualizar o cartão.", ephemeral=True)
        try:
            await db.log(interaction.user.id, "zerado_rejeitado", f"id={zerado_id} user={pendente['user_id']}")
        except Exception:
            log.exception("Zerado #%s rejeitado, mas falhou o log de auditoria", zerado_id)
        membro = interaction.guild.get_member(int(pendente["user_id"])) if interaction.guild else None
        if membro:
            try:
                await membro.send(
                    f"Seu registro de jogo zerado **{pendente['game']}** foi rejeitado pela moderação. "
                    "Você pode conferir os dados e falar com a equipe se precisar de esclarecimentos."
                )
            except discord.Forbidden:
                pass

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, emoji="✅", custom_id="zer:approve")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._processar(interaction, True)

    @discord.ui.button(label="Rejeitar", style=discord.ButtonStyle.danger, emoji="❌", custom_id="zer:reject")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await eh_moderador(interaction.user, self.cog.bot.db):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        import re
        footer = interaction.message.embeds[0].footer.text or "" if interaction.message and interaction.message.embeds else ""
        match = re.search(r"\bZeradoID:(\d+)\b", footer)
        if not match:
            return await interaction.response.send_message("Não foi possível identificar o registro.", ephemeral=True)
        from cogs.moderacao_utils import MotivoDecisaoModal
        async def decidir(inter, motivo):
            await self._processar(inter, False)
            from cogs.moderacao_utils import sincronizar_cartao
            await sincronizar_cartao(self.cog.bot, inter.guild_id, "zerados", int(match.group(1)), "rejected", inter.user.id, motivo)
        await interaction.response.send_modal(MotivoDecisaoModal(self.cog.bot, "zerado", int(match.group(1)), decidir))


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
        self.prova = discord.ui.FileUpload(required=False, min_values=0, max_values=5)
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
