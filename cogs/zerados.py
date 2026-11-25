import datetime as dt
import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
from admin_config import GuildConfig
from cogs.platinas import eh_moderador, sincronizar_patente, hoje
from cogs.comum import NotaJogoView, formatar_dificuldade
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

    def painel_view(self, user, callback_voltar=None) -> "ZeradosPainelView":
        return ZeradosPainelView(self, user, callback_voltar=callback_voltar)

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
            "Não curte platinar, mas terminou o jogo? A jornada também conta. Use o botão abaixo para **enviar seu registro**, "
            "ver sua lista aprovada e acompanhar o ranking de quem mais finalizou jogos.\n\n"
            "_Os registros passam pela Central de Aprovação. XP/Denários e publicação só são liberados após a aprovação. Print é opcional; não precisa transformar cada final em um dossiê._"
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
        if isinstance(removido, dict) and removido.get("erro"):
            return await interaction.response.send_message(removido["erro"], ephemeral=True)
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
        if removido.get("recompensa_drop_revertida"):
            extra += " O drop de carta/recursos desse registro também foi revertido."
        await interaction.response.send_message(f"🗑️ Registro #{registro} (**{z['game']}**) removido.{extra}", ephemeral=True)

    async def cog_app_command_error(self, interaction, error):
        await erro_comando(interaction, error)

    # ------------------------------------------------------------ registro
    async def registrar_zerado(self, interaction: discord.Interaction, jogo: str, plataforma: str,
                               data: str, comentario: str, capturas, nota: int | None = None,
                               dificuldade: int | None = None):
        try:
            d = dt.datetime.strptime(data.strip(), "%d/%m/%Y").date()
        except ValueError:
            return await interaction.response.send_message("Data inválida. Use DD/MM/AAAA.", ephemeral=True)
        if d > hoje():
            return await interaction.response.send_message("A data não pode estar no futuro.", ephemeral=True)

        jogo, plataforma = jogo.strip()[:100], plataforma.strip()[:30]
        comentario = (comentario or "").strip()[:500]
        if nota is not None and (type(nota) is not int or not 1 <= nota <= 10):
            return await interaction.response.send_message("Escolha uma nota entre 1 e 10.", ephemeral=True)
        if dificuldade is not None and (type(dificuldade) is not int or not 1 <= dificuldade <= 5):
            return await interaction.response.send_message("Escolha uma dificuldade entre 1 e 5.", ephemeral=True)
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
            linhas = await self.gravar_zerado(
                interaction.guild, interaction.user, d, jogo, plataforma, comentario, capturas, nota, dificuldade
            )
            await db.set_ultima_plataforma(interaction.user.id, plataforma)
        except ValueError as exc:
            return await interaction.edit_original_response(content=str(exc))
        await interaction.edit_original_response(content="\n".join(linhas))

    async def gravar_zerado(self, guild, user, d, jogo, plataforma, comentario, capturas,
                            nota: int | None = None, dificuldade: int | None = None) -> list[str]:
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
            user.id, jogo, plataforma, d.isoformat(), comentario, nota, dificuldade
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
            if nota is not None:
                embed.add_field(name="Nota do jogo", value=f"⭐ {nota}/10", inline=True)
            if dificuldade is not None:
                embed.add_field(name="Dificuldade percebida", value=formatar_dificuldade(dificuldade), inline=True)
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
            if registro.get("rating") is not None:
                embed.add_field(name="Nota do jogo", value=f"⭐ {int(registro['rating'])}/10", inline=True)
            if registro.get("difficulty") is not None:
                embed.add_field(name="Dificuldade percebida", value=formatar_dificuldade(registro["difficulty"]), inline=True)
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
            mensagem_publica = await canal.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            comunidade = self.bot.get_cog("Comunidade")
            if comunidade:
                try:
                    await comunidade.registrar_publicacao_social(
                        interaction.guild, canal, mensagem_publica, "zerado", int(registro["id"]), int(registro["user_id"])
                    )
                except Exception:
                    log.exception("Zerado #%s publicado, mas as interações sociais não foram anexadas", registro.get("id"))
            return True
        except Exception:
            log.exception("Falha ao anunciar zerado aprovado #%s", registro.get("id"))
            return False

    # ------------------------------------------------------------ textos
    async def texto_lista(self, membro) -> str:
        rows = await self.bot.db.zerados_do_usuario(membro.id)
        cabecalho = f"## ✅ Zerados de {membro.display_name}\n\n"
        if not rows:
            return cabecalho + "Ainda não há jogos zerados registrados. Sua lista está limpa — por enquanto."
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
            return f"## ✅ {titulo}\n\nAinda não há dados suficientes nesse ranking. A disputa continua aberta."
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

    async def _processar(
        self, interaction: discord.Interaction, aprovar: bool, motivo: str = "",
        source_message: discord.Message | None = None,
    ):
        mensagem_revisao = source_message or interaction.message
        if not mensagem_revisao or not mensagem_revisao.embeds:
            return await interaction.response.send_message("Cartão de revisão inválido.", ephemeral=True)
        footer = mensagem_revisao.embeds[0].footer.text or ""
        import re
        match = re.search(r"\bZeradoID:(\d+)\b", footer)
        if not match:
            return await interaction.response.send_message("Não consegui localizar o ID deste zerado.", ephemeral=True)

        zerado_id = int(match.group(1))
        db = self.cog.bot.db
        # Reconhece o clique antes de qualquer consulta/transação potencialmente lenta.
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not await eh_moderador(interaction.user, db):
            return await interaction.followup.send("Apenas moderadores podem revisar este registro.", ephemeral=True)
        pendente = await db.get_zerado(zerado_id)
        if pendente is None or pendente["status"] != "pending":
            return await interaction.followup.send("Este registro já foi processado ou removido.", ephemeral=True)
        if int(pendente["user_id"]) == interaction.user.id:
            return await interaction.followup.send("Você não pode aprovar ou rejeitar o próprio registro.", ephemeral=True)

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
                return await interaction.followup.send("Outro moderador já processou este registro.", ephemeral=True)

            # Confirma a presença da carta após o commit e repara conquistas antigas.
            carta_confirmada = False
            try:
                await db.coliseu_sincronizar_conquistas(int(resultado["user_id"]))
                carta_presente = await db._one(
                    "SELECT 1 FROM cartas_colecao WHERE user_id=? AND card_id=?",
                    (int(resultado["user_id"]), str(resultado["card_id"])),
                )
                carta_confirmada = carta_presente is not None
                if not carta_confirmada:
                    raise RuntimeError(
                        f"Carta não encontrada após sincronização: zerado={zerado_id} card={resultado['card_id']}"
                    )
            except Exception:
                log.exception(
                    "Zerado #%s aprovado, mas houve falha ao confirmar a carta %s para user=%s",
                    zerado_id, resultado.get("card_id"), resultado.get("user_id"),
                )
                await interaction.followup.send(
                    "O zerado foi aprovado, mas não consegui confirmar a carta na coleção. "
                    "A equipe foi avisada pelo log; não envie o registro novamente.", ephemeral=True,
                )

            from cogs.comum import sincronizar_cartao
            await sincronizar_cartao(
                self.cog.bot, interaction.guild_id, "zerados", zerado_id, "approved", interaction.user.id
            )
            recompensa = f"+{resultado['xp']} XP · +{resultado['denarios']} Denários"
            if resultado["daily_limit_reached"]:
                recompensa = "Sem recompensa: limite diário atingido"
            embed = discord.Embed.from_dict(mensagem_revisao.embeds[0].to_dict())
            embed.color = discord.Color.green()
            embed.set_footer(text=f"ZeradoID:{zerado_id} · APROVADO")
            outcome = resultado.get("card_outcome")
            if outcome == "carta":
                status_carta = f"🃏 **Drop recebido:** {resultado['card_name']} · {resultado['card_rarity']}"
            elif outcome == "almas":
                status_carta = f"✨ **Duplicata convertida:** +{resultado.get('card_almas', 0)} Almas"
            elif outcome == "fragmentos":
                status_carta = f"🧩 **Duplicata convertida:** +{resultado.get('card_fragmentos', 0)} fragmentos de evolução"
            else:
                status_carta = f"🃏 **Recompensa:** {resultado.get('card_name', 'Carta')} · {resultado.get('card_rarity', '')}"
            embed.add_field(
                name="Resultado",
                value=(
                    f"✅ Aprovado por {interaction.user.mention}\n"
                    f"**Recompensa:** {recompensa}\n{status_carta}"
                ),
                inline=False,
            )
            cartao_atualizado = True
            try:
                await mensagem_revisao.edit(
                    content=f"✅ Solicitação `#{zerado_id}` aprovada por {interaction.user.mention}.",
                    embed=embed, view=None,
                )
            except discord.HTTPException:
                cartao_atualizado = False
                log.exception("Zerado #%s aprovado, mas o cartão de revisão não foi atualizado", zerado_id)
                await interaction.followup.send(
                    "A aprovação foi salva e as recompensas foram aplicadas, mas não consegui atualizar o cartão. Não clique novamente.",
                    ephemeral=True,
                )

            membro = interaction.guild.get_member(int(resultado["user_id"])) if interaction.guild else None
            subiu = resultado["new_level"] > resultado["old_level"]
            if membro and subiu:
                await sincronizar_patente(interaction.guild, membro, int(resultado["new_level"]))
            await self.cog._anunciar_aprovado(
                interaction, resultado, int(resultado["new_level"]) if subiu else None
            )
            try:
                await db.log(
                    interaction.user.id, "zerado_aprovado",
                    f"id={zerado_id} user={resultado['user_id']} card={resultado.get('card_id')} "
                    f"card_added={bool(resultado.get('card_added'))} card_confirmed={carta_confirmada}",
                )
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
            from utils import notificar_usuario
            aviso_carta = (
                f"🃏 Você recebeu **{resultado['card_name']}** ({resultado['card_rarity']})!"
                if outcome == "carta" else
                f"✨ Sua duplicata virou **{resultado.get('card_almas', 0)} Almas**."
                if outcome == "almas" else
                f"🧩 Sua duplicata virou **{resultado.get('card_fragmentos', 0)} fragmentos de evolução**."
                if outcome == "fragmentos" else
                "⚠️ A recompensa foi registrada; consulte sua coleção."
            )
            await notificar_usuario(
                self.cog.bot, interaction.guild_id, int(resultado["user_id"]), "approvals",
                f"✅ Seu zerado de **{pendente['game']}** foi aprovado e registrado no Coliseu.\n"
                f"{aviso_carta}\nAbra `/nara` → Coliseu → Minha coleção para conferir."
            )
            if cartao_atualizado:
                detalhe_entrega = (
                    ("carta entregue" if resultado.get("card_added") else "carta já estava na coleção")
                    if carta_confirmada else "entrega da carta requer verificação"
                )
                await interaction.followup.send(
                    f"Zerado #{zerado_id} aprovado; {detalhe_entrega}: **{resultado['card_name']}**.",
                    ephemeral=True,
                )
            return

        alterado = await db.rejeitar_zerado(zerado_id, interaction.user.id, motivo)
        if not alterado:
            return await interaction.followup.send("Outro moderador já processou este registro.", ephemeral=True)
        embed = discord.Embed.from_dict(mensagem_revisao.embeds[0].to_dict())
        embed.color = discord.Color.red()
        embed.set_footer(text=f"ZeradoID:{zerado_id} · REJEITADO")
        resultado_texto = f"❌ Rejeitado por {interaction.user.mention}"
        if motivo:
            resultado_texto += f"\n**Motivo:** {discord.utils.escape_markdown(motivo[:300])}"
        embed.add_field(name="Resultado", value=resultado_texto, inline=False)
        cartao_atualizado = True
        try:
            await mensagem_revisao.edit(
                content=f"❌ Solicitação `#{zerado_id}` rejeitada por {interaction.user.mention}.",
                embed=embed, view=None,
            )
        except discord.HTTPException:
            cartao_atualizado = False
            log.exception("Zerado #%s rejeitado, mas o cartão de revisão não foi atualizado", zerado_id)
            await interaction.followup.send(
                "A rejeição foi salva, mas não consegui atualizar o cartão. Não clique novamente.",
                ephemeral=True,
            )
        try:
            await db.log(interaction.user.id, "zerado_rejeitado", f"id={zerado_id} user={pendente['user_id']}")
        except Exception:
            log.exception("Zerado #%s rejeitado, mas falhou o log de auditoria", zerado_id)
        from cogs.comum import sincronizar_cartao
        await sincronizar_cartao(
            self.cog.bot, interaction.guild_id, "zerados", zerado_id, "rejected", interaction.user.id, motivo
        )
        from utils import notificar_usuario
        texto_motivo = f"\nMotivo: {motivo}" if motivo else ""
        await notificar_usuario(
            self.cog.bot, interaction.guild_id, int(pendente["user_id"]), "rejections",
            f"❌ Seu registro de zerado **{pendente['game']}** foi rejeitado.{texto_motivo}\n"
            "Você pode corrigir os dados e enviar novamente pelo painel de Zerados."
        )
        if cartao_atualizado:
            await interaction.followup.send(f"Zerado #{zerado_id} rejeitado.", ephemeral=True)

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, emoji="✅", custom_id="zer:approve")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._processar(interaction, True)

    @discord.ui.button(label="Rejeitar", style=discord.ButtonStyle.danger, emoji="❌", custom_id="zer:reject")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # A autorização é validada novamente no envio do modal; abrir o modal não altera dados.
        import re
        footer = interaction.message.embeds[0].footer.text or "" if interaction.message and interaction.message.embeds else ""
        match = re.search(r"\bZeradoID:(\d+)\b", footer)
        if not match:
            return await interaction.response.send_message("Não foi possível identificar o registro.", ephemeral=True)
        from cogs.comum import MotivoDecisaoModal
        mensagem_revisao = interaction.message
        async def decidir(inter, motivo):
            await self._processar(inter, False, motivo, source_message=mensagem_revisao)
        await interaction.response.send_modal(MotivoDecisaoModal(self.cog.bot, "zerado", int(match.group(1)), decidir))


# ------------------------------------------------------------------ painel do usuário
class ZeradosPainelView(discord.ui.View):
    def __init__(self, cog: Zerados, user, callback_voltar=None):
        super().__init__(timeout=900)
        self.cog, self.user = cog, user
        self.callback_voltar = callback_voltar
        # Este painel já tem botão Voltar próprio; a central da Nara não deve
        # acrescentar um segundo botão de retorno.
        self._nara_has_return = callback_voltar is not None
        self.alvo = None  # membro consultado (padrão: você)
        self.sel_membro = discord.ui.UserSelect(placeholder="🔎 Consultar outro membro (opcional)", row=0)
        self.sel_membro.callback = self.trocar_membro
        self.add_item(self.sel_membro)
        from cogs.comunidade import adicionar_botao_contribuicao_contextual
        adicionar_botao_contribuicao_contextual(
            self, "correction", "zerados", "Sugerir melhoria em Zerados", "💡", row=3,
        )

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
        plataforma_padrao = await self.cog.bot.db.get_ultima_plataforma(interaction.user.id)
        await interaction.response.send_modal(ZeradoModal(self.cog, plataforma_padrao))

    @discord.ui.button(label="Lista", style=discord.ButtonStyle.primary, emoji="📜", row=1)
    async def lista(self, interaction: discord.Interaction, button: discord.ui.Button):
        membro = self._membro()
        texto = await self.cog.texto_lista(membro)
        await interaction.response.edit_message(content=texto, embeds=[], view=VoltarZeradosView(self.cog, self.user, self.alvo, self.callback_voltar))

    @discord.ui.button(label="Galeria", style=discord.ButtonStyle.primary, emoji="🖼️", row=2)
    async def galeria_zerados(self, interaction: discord.Interaction, button: discord.ui.Button):
        membro = self._membro()
        rows = await self.cog.bot.db.zerados_do_usuario(membro.id)
        view = GaleriaZeradosView(self.cog, self.user, membro, rows, callback_voltar=self.callback_voltar)
        await interaction.response.edit_message(content=None, embeds=await view.embeds(), view=view)

    @discord.ui.button(label="Ranking", style=discord.ButtonStyle.secondary, emoji="🏆", row=1)
    async def ranking(self, interaction: discord.Interaction, button: discord.ui.Button):
        texto = await self.cog.texto_ranking("total")
        await interaction.response.edit_message(content=texto, embeds=[], view=RankingZeradosView(self.cog, self.user, self.alvo, self.callback_voltar))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="↩️", row=2)
    async def voltar_coliseu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.callback_voltar is not None:
            return await self.callback_voltar(interaction)
        from cogs.platinas import ColiseuView
        platinas = self.cog.bot.get_cog("Platinas")
        if platinas is None:
            return await interaction.response.send_message("O Coliseu não está disponível.", ephemeral=True)
        view = ColiseuView(platinas, interaction.user)
        await interaction.response.edit_message(content=view.texto(), embeds=[], view=view)


class GaleriaZeradosView(discord.ui.View):
    """Galeria paginada de jogos concluídos, usando comprovante real quando disponível."""
    PAGE_SIZE = 5

    def __init__(self, cog, owner, alvo, rows, page=0, callback_voltar=None):
        super().__init__(timeout=900)
        self.cog, self.owner, self.alvo = cog, owner, alvo
        self.callback_voltar = callback_voltar
        self.rows = list(rows)
        self.page = max(0, min(page, max(0, (len(self.rows) - 1) // self.PAGE_SIZE)))
        self._sync()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("Esta galeria pertence a outra pessoa.", ephemeral=True)
            return False
        return True

    async def embeds(self):
        inicio = self.page * self.PAGE_SIZE
        fatia = self.rows[inicio:inicio + self.PAGE_SIZE]
        total_paginas = max(1, (len(self.rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        cards = []
        mod_ch_id = await GuildConfig.get(self.cog.bot.db, self.alvo.guild.id, "mod_channel") if getattr(self.alvo, "guild", None) else None
        canal = await get_text_channel(self.cog.bot, mod_ch_id) if mod_ch_id else None
        for row in fatia:
            e = discord.Embed(
                title=f"✅ {row['game']}",
                description=f"**Plataforma:** {row['platform']}\\n**Concluído em:** {data_legivel(row['finished_at'])}\\n**Registro:** `#{row['id']}`",
                color=discord.Color.green(),
            )
            comentario = str(row["comment"] or "").strip()
            if row["rating"] is not None:
                e.add_field(name="Nota do jogo", value=f"⭐ {int(row['rating'])}/10", inline=True)
            if row["difficulty"] is not None:
                e.add_field(name="Dificuldade percebida", value=formatar_dificuldade(row["difficulty"]), inline=True)
            if comentario:
                e.add_field(name="Comentário", value=comentario[:900], inline=False)
            # O cartão original da moderação pode conter um comprovante anexado.
            if canal and row["proof_msg_id"]:
                try:
                    mensagem = await canal.fetch_message(int(row["proof_msg_id"]))
                    anexo = next((a for a in mensagem.attachments if (a.content_type or "").startswith("image/")), None)
                    if anexo:
                        e.set_image(url=anexo.url)
                        e.set_footer(text="Comprovante enviado pelo jogador")
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass
            if not e.footer.text:
                e.set_footer(text="Imagem de capa não cadastrada")
            cards.append(e)
        if not cards:
            cards.append(discord.Embed(
                title=f"✅ Jogos zerados de {self.alvo.display_name}",
                description="Ainda não há jogos concluídos aprovados para exibir.",
                color=discord.Color.green(),
            ))
        cards[0].description = (
            f"**Coleção de {self.alvo.display_name}**\\n"
            f"Página {self.page + 1}/{total_paginas} · {len(self.rows)} jogo(s)\\n\\n"
            + (cards[0].description or "")
        )
        return cards

    def _sync(self):
        self.clear_items()
        total_paginas = max(1, (len(self.rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        botoes = [
            discord.ui.Button(label="Anterior", emoji="⬅️", style=discord.ButtonStyle.secondary,
                              disabled=self.page <= 0, row=0, custom_id=f"zer:galeria:prev:{self.page}"),
            discord.ui.Button(label="Próxima", emoji="➡️", style=discord.ButtonStyle.secondary,
                              disabled=self.page >= total_paginas - 1, row=0,
                              custom_id=f"zer:galeria:next:{self.page}"),
            discord.ui.Button(label="Lista por nome", emoji="📜", style=discord.ButtonStyle.primary,
                              row=1, custom_id=f"zer:galeria:lista:{self.page}"),
            discord.ui.Button(label="Voltar ao painel", emoji="↩️", style=discord.ButtonStyle.secondary,
                              row=1, custom_id=f"zer:galeria:voltar:{self.page}"),
        ]
        for b, cb in zip(botoes, (self.anterior, self.proxima, self.lista, self.voltar)):
            b.callback = cb
            self.add_item(b)

    async def anterior(self, interaction):
        self.page = max(0, self.page - 1)
        self._sync()
        await interaction.response.edit_message(embeds=await self.embeds(), view=self)

    async def proxima(self, interaction):
        self.page = min(max(0, (len(self.rows) - 1) // self.PAGE_SIZE), self.page + 1)
        self._sync()
        await interaction.response.edit_message(embeds=await self.embeds(), view=self)

    async def lista(self, interaction):
        texto = await self.cog.texto_lista(self.alvo)
        await interaction.response.edit_message(content=texto, embeds=[], view=VoltarZeradosView(self.cog, self.owner, self.alvo, self.callback_voltar))

    async def voltar(self, interaction):
        view = ZeradosPainelView(self.cog, self.owner, callback_voltar=self.callback_voltar)
        view.alvo = self.alvo if self.alvo.id != self.owner.id else None
        await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)


class VoltarZeradosView(discord.ui.View):
    """Volta ao painel sem criar uma nova mensagem."""

    def __init__(self, cog: Zerados, owner, alvo=None, callback_voltar=None):
        super().__init__(timeout=900)
        self.cog, self.owner, self.alvo = cog, owner, alvo
        self.callback_voltar = callback_voltar
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar ao Coliseu", emoji="🏠")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("Este painel pertence a outra pessoa.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Voltar ao painel", style=discord.ButtonStyle.secondary, emoji="↩️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ZeradosPainelView(self.cog, self.owner, callback_voltar=self.callback_voltar)
        view.alvo = self.alvo
        await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)


class RankingZeradosView(VoltarZeradosView):
    def __init__(self, cog: Zerados, owner, alvo=None, callback_voltar=None):
        super().__init__(cog, owner, alvo, callback_voltar)
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
    """Dados do registro; a nota e o comentário são solicitados em duas etapas seguintes."""

    def __init__(
        self, cog: Zerados, plataforma_padrao: str | None = None,
        jogo_padrao: str | None = None, data_padrao: str | None = None,
        motivo_rejeicao: str | None = None,
    ):
        super().__init__(title="Corrigir zerado rejeitado" if jogo_padrao else "Registrar jogo zerado")
        self.cog = cog
        self.jogo = discord.ui.TextInput(
            placeholder="Ex.: Hollow Knight", max_length=100,
            default=(str(jogo_padrao)[:100] if jogo_padrao else None),
        )
        self.plataforma = discord.ui.Select(
            placeholder="Escolha a plataforma",
            options=[discord.SelectOption(label=p, value=p, default=(p == plataforma_padrao)) for p in PLATAFORMAS],
        )
        self.data = discord.ui.TextInput(
            default=(str(data_padrao)[:10] if data_padrao else hoje().strftime("%d/%m/%Y")),
            placeholder="DD/MM/AAAA", max_length=10,
        )
        self.motivo_rejeicao = str(motivo_rejeicao or "").strip()[:180]
        self.prova = discord.ui.FileUpload(required=False, min_values=0, max_values=5)
        self.add_item(discord.ui.Label(text="Jogo", component=self.jogo))
        self.add_item(discord.ui.Label(text="Plataforma", component=self.plataforma))
        self.add_item(discord.ui.Label(text="Data em que zerou", component=self.data))
        self.add_item(discord.ui.Label(text="Print dos créditos (opcional)", component=self.prova))

    async def on_submit(self, interaction: discord.Interaction):
        if not self.plataforma.values:
            return await interaction.response.send_message("Escolha a plataforma.", ephemeral=True)
        jogo = str(self.jogo.value).strip()
        plataforma = self.plataforma.values[0]
        data = str(self.data.value).strip()
        capturas = list(self.prova.values)
        semelhantes = await self.cog.bot.db.titulos_semelhantes(jogo)
        aviso_titulo = (
            "\n\n**Confira o nome:** encontrei títulos parecidos no catálogo: "
            + ", ".join(f"**{discord.utils.escape_markdown(t)}**" for t in semelhantes)
            + ". Confirme se está registrando a edição correta."
            if semelhantes else ""
        )

        async def concluir(avaliacao_interaction, nota, dificuldade, comentario):
            await self.cog.registrar_zerado(
                avaliacao_interaction, jogo, plataforma, data, comentario, capturas, nota, dificuldade,
            )

        await interaction.response.send_message(
            "**Avaliação — 1/3: Nota do jogo**\nQuanto você gostou deste jogo? Escolha uma nota de 1 a 10." + aviso_titulo,
            view=NotaJogoView(
                concluir, "Na sua experiência, qual foi a dificuldade para zerar este jogo?",
                contexto=(f"Jogo: **{discord.utils.escape_markdown(jogo)}**\n"
                          f"Plataforma: **{plataforma}** · Data: **{data}**\n"
                          f"Comprovantes: **{len(capturas)} arquivo(s)**"
                          + (f"\n**Motivo da rejeição anterior:** {discord.utils.escape_markdown(self.motivo_rejeicao)}" if self.motivo_rejeicao else "")),
            ), ephemeral=True,
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
