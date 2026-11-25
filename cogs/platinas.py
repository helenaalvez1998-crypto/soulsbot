import datetime as dt
import logging
import discord
from discord import app_commands
from discord.ext import commands

import config
from admin_config import GuildConfig
from levels import patente_por_nivel, nivel_por_xp, barra_progresso
from utils import get_text_channel, upsert_panel  # noqa: F401
from cogs.comum import NotaJogoView, formatar_dificuldade

log = logging.getLogger("cogs.platinas")


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
        log.warning("Sem permissão para sincronizar patente de %s; confira a hierarquia de cargos.", member.id)
    except discord.HTTPException:
        log.exception("Falha HTTP ao sincronizar patente de %s", member.id)
    except Exception:
        log.exception("Falha inesperada ao sincronizar patente de %s", member.id)


class RevisaoView(discord.ui.View):
    """Botões persistentes: continuam funcionando após reiniciar o bot."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def _processar(
        self, interaction: discord.Interaction, aprovar: bool, motivo: str = "",
        source_message: discord.Message | None = None,
    ):
        mensagem_revisao = source_message or interaction.message
        if not mensagem_revisao or not mensagem_revisao.embeds:
            return await interaction.response.send_message("Mensagem de revisão inválida.", ephemeral=True)

        footer = mensagem_revisao.embeds[0].footer.text or ""
        match = __import__("re").search(r"\bID:(\d+)\b", footer)
        if not match:
            return await interaction.response.send_message("Não foi possível localizar o ID desta platina.", ephemeral=True)
        platina_id = int(match.group(1))
        db = self.bot.db
        # Reconhece o clique antes das consultas e transações de aprovação.
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not await eh_moderador(interaction.user, db):
            return await interaction.followup.send("Apenas moderadores.", ephemeral=True)
        p = await db.get_platina(platina_id)
        if p is None or p["status"] != "pending":
            return await interaction.followup.send("Este registro já foi processado.", ephemeral=True)

        novo_status = "approved" if aprovar else "rejected"
        if aprovar:
            xp_plat = await GuildConfig.get(db, interaction.guild_id, "xp_platina")
            den_plat = await GuildConfig.get(db, interaction.guild_id, "denarios_platina")
            if xp_plat is None:
                xp_plat = config.XP_PLATINA
            if den_plat is None:
                den_plat = config.DENARIOS_PLATINA
            xp_zerado = await GuildConfig.get(db, interaction.guild_id, "xp_zerado")
            den_zerado = await GuildConfig.get(db, interaction.guild_id, "denarios_zerado")
            limite_zerados = await GuildConfig.get(db, interaction.guild_id, "zerados_xp_limite")
            if xp_zerado is None:
                xp_zerado = config.XP_ZERADO
            if den_zerado is None:
                den_zerado = config.DENARIOS_ZERADO
            if limite_zerados is None:
                limite_zerados = config.ZERADOS_XP_LIMITE_DIARIO

            decision = await db.aprovar_platina_com_recompensa(
                platina_id, interaction.user.id, int(xp_plat), int(den_plat),
                int(xp_zerado), int(den_zerado), int(limite_zerados),
            )
            if decision is None:
                return await interaction.followup.send("Outro moderador já processou esta platina.", ephemeral=True)
            antigo, novo = decision["old_level"], decision["new_level"]
            user_id = decision["user_id"]
        else:
            changed = await db.decidir_platina(platina_id, "rejected", interaction.user.id, motivo)
            if not changed:
                return await interaction.followup.send("Outro moderador já processou esta platina.", ephemeral=True)
            antigo = novo = None
            user_id = int(p["user_id"])

        try:
            await db.log(interaction.user.id, f"platina_{novo_status}", f"id={platina_id} user={user_id}")
        except Exception:
            # A decisão e a recompensa já foram confirmadas pela transação principal.
            # Uma falha secundária no log não pode deixar os botões parecendo pendentes.
            log.exception("Decisão da platina #%s salva, mas falhou o registro de auditoria", platina_id)
        try:
            from cogs.comum import sincronizar_cartao
            await sincronizar_cartao(
                self.bot, interaction.guild_id, "platinas", platina_id,
                novo_status, interaction.user.id, motivo if not aprovar else None,
            )
        except Exception:
            log.exception("Falha ao sincronizar cartão original da platina #%s", platina_id)
        embed = discord.Embed.from_dict(mensagem_revisao.embeds[0].to_dict())
        embed.color = discord.Color.green() if aprovar else discord.Color.red()
        texto_resultado = f"{'✅ Aprovada' if aprovar else '❌ Rejeitada'} por {interaction.user.mention}"
        if not aprovar and motivo:
            texto_resultado += f"\n**Motivo:** {discord.utils.escape_markdown(motivo[:300])}"
        embed.add_field(name="Resultado", value=texto_resultado, inline=False)
        cartao_atualizado = True
        try:
            await mensagem_revisao.edit(embed=embed, view=None)
        except discord.HTTPException:
            cartao_atualizado = False
            log.exception("Decisão da platina #%s foi salva, mas a mensagem não pôde ser atualizada", platina_id)
            await interaction.followup.send(
                "A decisão foi salva no banco, mas não consegui atualizar a mensagem. Não clique novamente; a platina já foi processada.",
                ephemeral=True,
            )

        membro = interaction.guild.get_member(user_id) if interaction.guild else None
        if aprovar:
            if membro and novo > antigo:
                await sincronizar_patente(interaction.guild, membro, novo)
            try:
                plat_ch_id = await GuildConfig.get(db, interaction.guild_id, "platinas_channel")
                canal = await get_text_channel(self.bot, plat_ch_id) if plat_ch_id else None
                if canal:
                    linhas = [
                        "# 🏆 Nova platina no Coliseu!",
                        f"<@{user_id}> conquistou **{p['game']}** na plataforma **{p['platform']}**.",
                        "✅ Esta conquista também foi registrada automaticamente em Jogos Zerados.",
                        f"[📸 Ver comprovante]({p['proof_url']})",
                        f"**Recompensa:** +{int(xp_plat)} XP · +{int(den_plat)} Denários",
                    ]
                    if decision.get("card_outcome") == "carta":
                        linhas.append(f"🃏 **Drop:** {decision.get('card_name')} · {decision.get('card_rarity')}")
                    elif decision.get("card_outcome") == "almas":
                        linhas.append("✨ **Duplicata:** convertida em Almas.")
                    elif decision.get("card_outcome") == "fragmentos":
                        linhas.append("🧩 **Duplicata:** convertida em fragmentos de evolução.")
                    if p["rating"] is not None:
                        linhas.insert(3, f"**Nota do jogo:** ⭐ {int(p['rating'])}/10")
                    if p["difficulty"] is not None:
                        pos_dificuldade = 4 if p["rating"] is not None else 3
                        linhas.insert(pos_dificuldade, f"**Dificuldade percebida:** {formatar_dificuldade(p['difficulty'])}")
                    if str(p["comment"] or "").strip():
                        pos_comentario = 3 + int(p["rating"] is not None) + int(p["difficulty"] is not None)
                        linhas.insert(pos_comentario,
                                      f"**Comentário:** {str(p['comment']).strip()}")
                    if novo > antigo:
                        linhas.extend(["", f"⬆️ **Novo nível:** {novo} — {patente_por_nivel(novo)}"])
                    mensagem_publica = await canal.send("\n".join(linhas), allowed_mentions=discord.AllowedMentions.none())
                    comunidade = self.bot.get_cog("Comunidade")
                    if comunidade:
                        try:
                            await comunidade.registrar_publicacao_social(
                                interaction.guild, canal, mensagem_publica, "platina", int(platina_id), int(user_id)
                            )
                        except Exception:
                            log.exception("Platina #%s publicada, mas as interações sociais não foram anexadas", platina_id)
            except Exception:
                logging.getLogger("colizeu").exception(
                    "Platina #%s aprovada, mas falhou a configuração/publicação do anúncio", platina_id
                )
            # A aprovação da platina também conclui o jogo no sistema de zerados.
            # Se já existia um zerado aprovado, o banco não cria outro nem paga novamente.
            if not decision["zerado_preexisting"]:
                try:
                    await db.log(
                        user_id, "zerado_automatico_platina",
                        f"zerado_id={decision['zerado_id']} platina_id={platina_id} "
                        f"convertido={decision['zerado_converted']} xp={decision['zerado_xp']} "
                        f"denarios={decision['zerado_denarios']}",
                    )
                except Exception:
                    log.exception("Falha ao registrar auditoria do zerado automático da platina #%s", platina_id)
                zerados_cog = self.bot.get_cog("Zerados")
                if zerados_cog:
                    registro_auto = {
                        "id": decision["zerado_id"], "user_id": user_id,
                        "game": p["game"], "platform": p["platform"],
                        "finished_at": p["earned_at"],
                        "comment": str(p["comment"] or "Registrado automaticamente pela platina aprovada."),
                        "rating": p["rating"],
                        "difficulty": p["difficulty"],
                        "xp": decision["zerado_xp"],
                        "denarios": decision["zerado_denarios"],
                        "daily_limit_reached": decision["zerado_daily_limit_reached"],
                    }
                    try:
                        await zerados_cog._anunciar_aprovado(
                            interaction, registro_auto,
                            novo_nivel=(decision["new_level"] if decision["new_level"] > decision["old_level"] else None),
                        )
                    except Exception:
                        log.exception("Platina #%s aprovada, mas falhou o anúncio automático do zerado", platina_id)

                # Se a pessoa já tinha enviado um zerado pendente, atualiza o cartão antigo.
                if decision["zerado_converted"] and decision["zerado_proof_msg_id"]:
                    try:
                        mod_ch_id = await GuildConfig.get(db, interaction.guild_id, "mod_channel")
                        mod_channel = await get_text_channel(self.bot, mod_ch_id) if mod_ch_id else None
                        if mod_channel:
                            old_card = await mod_channel.fetch_message(int(decision["zerado_proof_msg_id"]))
                            if old_card.embeds:
                                old_embed = old_card.embeds[0]
                                old_embed.color = discord.Color.green()
                                old_embed.add_field(
                                    name="Resultado",
                                    value="✅ Aprovado automaticamente: a platina correspondente foi validada.",
                                    inline=False,
                                )
                                old_embed.set_footer(text=f"ZeradoID:{decision['zerado_id']} · APROVADO")
                                await old_card.edit(content="🏆 Este jogo também foi reconhecido como zerado pela platina aprovada.", embed=old_embed, view=None)
                    except discord.HTTPException:
                        log.exception("Falha ao atualizar cartão do zerado convertido #%s", decision["zerado_id"])

            painel = self.bot.get_cog("Colizeu")
            if painel:
                try:
                    await painel.atualizar()
                except Exception:
                    logging.getLogger("colizeu").exception("Falha ao atualizar o painel após aprovação")
            santuario = self.bot.get_cog("Santuario")
            if santuario:
                try:
                    await santuario.atualizar(user_id)
                except Exception:
                    logging.getLogger("colizeu").exception("Falha ao atualizar o santuário")
            from utils import notificar_usuario
            await notificar_usuario(
                self.bot, interaction.guild_id, user_id, "approvals",
                f"✅ Sua platina de **{p['game']}** foi aprovada e publicada no Coliseu. "
                "Ela também foi reconhecida em Jogos Zerados. "
                + (f"Você recebeu **{decision.get('card_name')}** ({decision.get('card_rarity')})."
                   if decision.get("card_outcome") == "carta" else
                   f"Sua duplicata virou {decision.get('card_almas', 0)} Almas."
                   if decision.get("card_outcome") == "almas" else
                   f"Sua duplicata virou {decision.get('card_fragmentos', 0)} fragmentos."
                   if decision.get("card_outcome") == "fragmentos" else "")
            )
        else:
            from utils import notificar_usuario
            texto_motivo = f"\nMotivo: {motivo}" if motivo else ""
            await notificar_usuario(
                self.bot, interaction.guild_id, user_id, "rejections",
                f"❌ Sua platina de **{p['game']}** foi rejeitada.{texto_motivo}\n"
                "Você pode corrigir os dados e enviar novamente pelo Coliseu."
            )

        if cartao_atualizado:
            await interaction.followup.send(
                f"Platina #{platina_id} {'aprovada' if aprovar else 'rejeitada'}.",
                ephemeral=True,
            )

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, custom_id="plat:approve")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._processar(interaction, True)

    @discord.ui.button(label="Rejeitar", style=discord.ButtonStyle.danger, custom_id="plat:reject")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # A autorização é validada novamente no envio do modal; abrir o modal não altera dados.
        import re
        footer = interaction.message.embeds[0].footer.text or "" if interaction.message and interaction.message.embeds else ""
        match = re.search(r"\bID:(\d+)\b", footer)
        if not match:
            return await interaction.response.send_message("Não foi possível identificar a platina.", ephemeral=True)
        from cogs.comum import MotivoDecisaoModal
        mensagem_revisao = interaction.message
        async def decidir(inter, motivo):
            await self._processar(inter, False, motivo, source_message=mensagem_revisao)
        await interaction.response.send_modal(MotivoDecisaoModal(self.bot, "platina", int(match.group(1)), decidir))


class ColiseuView(discord.ui.View):
    """Painel principal do Coliseu. Pode ser público e persistente ou privado por usuário."""
    def __init__(self, platinas_cog, user=None, back_callback=None):
        # Sem usuário definido, é o painel público postado pela moderação e precisa
        # continuar funcionando após reinicializações. Com usuário, é a versão privada.
        super().__init__(timeout=None if user is None else 300)
        self.platinas_cog = platinas_cog
        self.user_id = user.id if user is not None else None
        self.back_callback = back_callback
        from cogs.comunidade import adicionar_botao_contribuicao_contextual
        adicionar_botao_contribuicao_contextual(
            self, "idea", "coliseu", "Sugerir competição", "💡", row=1,
        )

    async def _voltar_coliseu(self, interaction: discord.Interaction):
        if self.back_callback is not None:
            await self.back_callback(interaction)
            return
        await interaction.response.edit_message(content=self.texto(), embed=None, view=ColiseuView(self.platinas_cog, interaction.user))

    def texto(self):
        return (
            "# 🏛️ NARA — COLISEU\n"
            "Sua central de conquistas e jornadas. Aqui, cada registro tem seu lugar — e cada prova passa pela revisão correta.\n\n"
            "**🏆 Platinas** — registrar conquistas, consultar perfil e ranking.\n"
            "**✅ Zerados** — registrar jogos finalizados, sem precisar de platina.\n"
            "**⚔️ Runs e desafios** — registrar tempos, conferir regras e recordes.\n"
            "_Escolha uma área abaixo. Eu cuido da navegação; você cuida das conquistas. Tudo acontece nesta mesma mensagem._"
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user_id is not None and interaction.user.id != self.user_id:
            await interaction.response.send_message("Abra /nara para acessar seu próprio painel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Platinas", emoji="🏆", style=discord.ButtonStyle.primary, custom_id="nara:coliseu:platinas", row=0)
    async def abrir_platinas(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PainelView(self.platinas_cog, interaction.user, callback_voltar=self._voltar_coliseu if self.back_callback is not None else None)
        if self.user_id is not None and self.back_callback is not None:
            view.callback_voltar = self._voltar_coliseu
        if self.user_id is None:
            # No painel público, cada pessoa recebe a navegação em uma resposta privada.
            await interaction.response.send_message(embed=await view.embed(), view=view, ephemeral=True)
        else:
            await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)

    @discord.ui.button(label="Zerados", emoji="✅", style=discord.ButtonStyle.success, custom_id="nara:coliseu:zerados", row=0)
    async def abrir_zerados(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.platinas_cog.bot.get_cog("Zerados")
        if cog is None:
            return await interaction.response.send_message("O painel de zerados não está disponível agora. Avise a moderação; não vou abrir uma porta que não existe.", ephemeral=True)
        view = cog.painel_view(
            interaction.user,
            callback_voltar=self._voltar_coliseu if self.user_id is not None and self.back_callback is not None else None,
        )
        if self.user_id is not None and self.back_callback is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(view, self._voltar_coliseu)
        if self.user_id is None:
            await interaction.response.send_message(embed=await view.embed(), view=view, ephemeral=True)
        else:
            await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)

    @discord.ui.button(label="Runs e desafios", emoji="⚔️", style=discord.ButtonStyle.danger, custom_id="nara:coliseu:runs", row=0)
    async def abrir_runs(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.platinas_cog.bot.get_cog("Soulslike")
        if cog is None:
            return await interaction.response.send_message("O painel de runs não está disponível agora. Avise a moderação para verificar o módulo.", ephemeral=True)
        from cogs.soulslike import CentralView
        if self.user_id is None:
            await interaction.response.send_message(content=cog.texto_central(), view=CentralView(cog), ephemeral=True)
        else:
            callback = self._voltar_coliseu if self.back_callback is not None else None
            view = CentralView(cog, callback_voltar=callback, user_id=interaction.user.id if callback else None)
            await interaction.response.edit_message(content=cog.texto_central(), embeds=[], view=view)


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
            await self.bot.db.set_kv(
                f"rotating:channel:platinas:{interaction.guild_id}", str(canal.id)
            )
        except discord.Forbidden:
            return await interaction.followup.send("Não tenho permissão para publicar ou atualizar o painel neste canal.", ephemeral=True)
        except discord.HTTPException:
            return await interaction.followup.send("O Discord recusou a publicação. Confira as permissões e tente novamente.", ephemeral=True)
        await interaction.followup.send("✅ Painel de platinas publicado/atualizado neste canal.", ephemeral=True)

    # -------------------------------------------------------- registro
    async def registrar_platina(self, interaction: discord.Interaction, jogo: str, plataforma: str,
                                data: str, capturas, nota: int | None = None, comentario: str = "",
                                dificuldade: int | None = None):
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
        total_bytes = 0
        for arquivo_anexo in capturas:
            tipo = (arquivo_anexo.content_type or "").lower()
            nome = arquivo_anexo.filename.lower()
            eh_imagem_ou_video = tipo.startswith(("image/", "video/")) or nome.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".webm"))
            if not eh_imagem_ou_video:
                return await interaction.response.send_message(
                    f"Arquivo não suportado: {arquivo_anexo.filename}. Envie imagens ou vídeos.", ephemeral=True
                )
            tamanho = int(getattr(arquivo_anexo, "size", 0) or 0)
            if tamanho > 20 * 1024 * 1024:
                return await interaction.response.send_message(
                    f"O arquivo {arquivo_anexo.filename} excede o limite de 20 MB.", ephemeral=True
                )
            total_bytes += tamanho
        if total_bytes > 40 * 1024 * 1024:
            return await interaction.response.send_message(
                "O total dos comprovantes não pode ultrapassar 40 MB por registro.", ephemeral=True
            )

        jogo, plataforma = jogo.strip()[:100], plataforma.strip()[:30]
        comentario = str(comentario or "").strip()[:500]
        if nota is not None and (type(nota) is not int or not 1 <= nota <= 10):
            return await interaction.response.send_message("Escolha uma nota entre 1 e 10.", ephemeral=True)
        if dificuldade is not None and (type(dificuldade) is not int or not 1 <= dificuldade <= 5):
            return await interaction.response.send_message("Escolha uma dificuldade entre 1 e 5.", ephemeral=True)
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
        msg = None
        platina_id = None
        try:
            # Conversão de anexos também precisa estar protegida: Discord já recebeu defer.
            arquivos = [await anexo.to_file() for anexo in capturas]
            embed = discord.Embed(title="🏆 Platina aguardando aprovação", color=config.COR_PRATA)
            embed.add_field(name="Membro", value=interaction.user.mention)
            embed.add_field(name="Jogo", value=jogo)
            embed.add_field(name="Plataforma", value=plataforma)
            embed.add_field(name="Data", value=d.strftime("%d/%m/%Y"))
            if nota is not None:
                embed.add_field(name="Nota do jogo", value=f"⭐ {nota}/10")
            if dificuldade is not None:
                embed.add_field(name="Dificuldade percebida", value=formatar_dificuldade(dificuldade))
            if comentario:
                embed.add_field(name="Comentário", value=comentario, inline=False)
            embed.add_field(name="Comprovantes", value=f"{len(capturas)} arquivo(s) anexado(s)", inline=False)
            primeiro_tipo = (capturas[0].content_type or "").lower()
            if primeiro_tipo.startswith("image/") or capturas[0].filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                embed.set_image(url=f"attachment://{arquivos[0].filename}")
            if len(capturas) > 1:
                embed.add_field(name="Arquivos adicionais", value="\n".join(
                    f"{i}. {discord.utils.escape_markdown(a.filename)}" for i, a in enumerate(capturas[1:], start=2)
                )[:1024], inline=False)
            msg = await canal.send(embed=embed, files=arquivos)
            urls = [(att.url, att.content_type) for att in msg.attachments]
            url = urls[0][0] if urls else capturas[0].url
            platina_id = await db.criar_platina_unica(
                interaction.user.id, jogo, plataforma, d.isoformat(), url, msg.id, nota, comentario, dificuldade
            )
            if platina_id is None:
                try:
                    await msg.delete()
                except discord.HTTPException:
                    log.exception("Não foi possível apagar mensagem duplicada de platina")
                return await interaction.edit_original_response(
                    content="Você já registrou essa platina (pendente ou aprovada). A solicitação duplicada foi descartada."
                )
            await db.adicionar_comprovantes(platina_id, urls or [(a.url, a.content_type) for a in capturas])
            embed.set_footer(text=f"ID:{platina_id}")
            await msg.edit(embed=embed, view=RevisaoView(self.bot))
        except Exception:
            log.exception("Falha ao finalizar registro de platina para user=%s game=%s", interaction.user.id, jogo)
            if platina_id is not None:
                try:
                    await db.excluir_platina_pendente(platina_id)
                except Exception:
                    log.exception("Falha ao remover registro incompleto de platina #%s", platina_id)
            if msg is not None:
                try:
                    await msg.delete()
                except discord.HTTPException:
                    log.exception("Falha ao apagar mensagem de moderação órfã de platina")
            return await interaction.edit_original_response(
                content="Não consegui concluir o registro. Nenhuma platina pendente foi mantida; tente novamente."
            )
        try:
            await db.set_ultima_plataforma(interaction.user.id, plataforma)
        except Exception:
            log.exception("Platina #%s registrada, mas não foi possível salvar a plataforma preferida", platina_id)
        try:
            await db.log(interaction.user.id, "platina_registrada", f"id={platina_id} jogo={jogo}")
        except Exception:
            log.exception("Platina #%s registrada, mas falhou o log de auditoria", platina_id)
        await interaction.edit_original_response(content="✅ Registro enviado para a moderação!")


# ------------------------------------------------------------------ painel do usuário
class PainelView(discord.ui.View):
    def __init__(self, cog, user, callback_voltar=None):
        super().__init__(timeout=900)
        self.cog, self.user = cog, user
        self.callback_voltar = callback_voltar
        self.alvo: discord.Member | None = None  # membro consultado (padrão: você)
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar", emoji="↩️")
        self.sel_membro = discord.ui.UserSelect(placeholder="🔎 Consultar outro membro (opcional)", row=4 if callback_voltar is not None else 0)
        self.sel_membro.callback = self.trocar_membro
        self.add_item(self.sel_membro)
        from cogs.comunidade import adicionar_botao_contribuicao_contextual
        adicionar_botao_contribuicao_contextual(
            self, "correction", "platinas", "Sugerir melhoria em Platinas", "💡", row=3,
        )

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
        plataforma_padrao = await self.cog.bot.db.get_ultima_plataforma(interaction.user.id)
        await interaction.response.send_modal(PlatinaModal(self.cog, plataforma_padrao))

    @discord.ui.button(label="Perfil", style=discord.ButtonStyle.primary, emoji="👤", row=1)
    async def perfil(self, interaction: discord.Interaction, button: discord.ui.Button):
        e = await self.cog.bot.get_cog("Perfil").embed_perfil(self._membro())
        await interaction.response.edit_message(content=None, embed=e, view=VoltarPainelView(self.cog, self.user, self.alvo, self.callback_voltar))

    @discord.ui.button(label="Platinas", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def platinas(self, interaction: discord.Interaction, button: discord.ui.Button):
        membro = self._membro()
        texto = await self.cog.bot.get_cog("Perfil").texto_platinas(membro)
        if texto is None:
            texto = f"## 📜 Coleção de {membro.display_name}\n\nAinda não há platinas aprovadas para exibir."
        await interaction.response.edit_message(content=texto, embeds=[], view=VoltarPainelView(self.cog, self.user, membro, self.callback_voltar))

    @discord.ui.button(label="Galeria", style=discord.ButtonStyle.primary, emoji="🖼️", row=2)
    async def galeria_platinas(self, interaction: discord.Interaction, button: discord.ui.Button):
        membro = self._membro()
        rows = await self.cog.bot.db.platinas_do_usuario(membro.id)
        view = GaleriaPlatinasView(self.cog, self.user, membro, rows, callback_voltar=self.callback_voltar)
        await interaction.response.edit_message(content=None, embeds=view.embeds(), view=view)

    @discord.ui.button(label="Ranking", style=discord.ButtonStyle.secondary, emoji="🏆", row=1)
    async def ranking(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RankingView(self.cog, "platinas", self.user, self._membro(), callback_voltar=self.callback_voltar)
        texto = await self.cog.bot.get_cog("Ranking").texto_ranking("platinas")
        await interaction.response.edit_message(content=texto, embeds=[], view=view)

    @discord.ui.button(label="Ajuda", style=discord.ButtonStyle.secondary, emoji="❓", row=1)
    async def ajuda(self, interaction: discord.Interaction, button: discord.ui.Button):
        texto = self.cog.bot.get_cog("Perfil").texto_ajuda()
        await interaction.response.edit_message(content=texto, embeds=[], view=VoltarPainelView(self.cog, self.user, self.alvo, self.callback_voltar))

    @discord.ui.button(label="Meu santuário", style=discord.ButtonStyle.success, emoji="🏛️", row=2)
    async def meu_santuario(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.bot.get_cog("Santuario").abrir_meu(interaction, callback_voltar=self.callback_voltar)

    @discord.ui.button(label="Visitar santuário", style=discord.ButtonStyle.primary, emoji="🚪", row=2)
    async def visitar_santuario(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.alvo is None:
            return await interaction.response.edit_message(
                content="🔎 **Antes de visitar:** selecione um membro no menu superior e tente novamente.",
                embed=await self.embed(), view=self,
            )
        await self.cog.bot.get_cog("Santuario").visitar(interaction, self.alvo.id, callback_voltar=self.callback_voltar)


class GaleriaPlatinasView(discord.ui.View):
    """Galeria paginada de platinas aprovadas; mantém a lista textual como alternativa."""
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

    def embeds(self):
        inicio = self.page * self.PAGE_SIZE
        fatia = self.rows[inicio:inicio + self.PAGE_SIZE]
        total_paginas = max(1, (len(self.rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        cards = []
        for idx, row in enumerate(fatia, start=inicio + 1):
            e = discord.Embed(
                title=f"🏆 {row['game']}",
                description=f"**Plataforma:** {row['platform']}\\n**Conquistada em:** {row['earned_at']}\\n**Registro:** `#{row['id']}`",
                color=config.COR_OURO,
            )
            # proof_url é o comprovante fornecido no registro, não uma capa oficial.
            url = str(row["proof_url"] or "").strip()
            if url.startswith(("https://", "http://")):
                e.set_image(url=url)
                e.set_footer(text="Comprovante enviado pelo jogador")
            else:
                e.set_footer(text="Capa/comprovante visual não disponível")
            cards.append(e)
        if not cards:
            cards.append(discord.Embed(
                title=f"🏆 Platinas de {self.alvo.display_name}",
                description="Ainda não há platinas aprovadas para exibir.",
                color=config.COR_OURO,
            ))
        cards[0].description = (
            f"**Coleção de {self.alvo.display_name}**\\n"
            f"Página {self.page + 1}/{total_paginas} · {len(self.rows)} conquista(s)\\n\\n"
            + (cards[0].description or "")
        )
        return cards

    def _sync(self):
        self.clear_items()
        total_paginas = max(1, (len(self.rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.add_item(discord.ui.Button(label="Anterior", emoji="⬅️", style=discord.ButtonStyle.secondary,
                                        disabled=self.page <= 0, row=0, custom_id=f"plat:galeria:prev:{self.page}"))
        self.add_item(discord.ui.Button(label="Próxima", emoji="➡️", style=discord.ButtonStyle.secondary,
                                        disabled=self.page >= total_paginas - 1, row=0,
                                        custom_id=f"plat:galeria:next:{self.page}"))
        self.add_item(discord.ui.Button(label="Lista por nome", emoji="📜", style=discord.ButtonStyle.primary,
                                        row=1, custom_id=f"plat:galeria:lista:{self.page}"))
        self.add_item(discord.ui.Button(label="Voltar ao painel", emoji="↩️", style=discord.ButtonStyle.secondary,
                                        row=1, custom_id=f"plat:galeria:voltar:{self.page}"))
        self.children[0].callback = self.anterior
        self.children[1].callback = self.proxima
        self.children[2].callback = self.lista
        self.children[3].callback = self.voltar

    async def anterior(self, interaction):
        self.page = max(0, self.page - 1)
        self._sync()
        await interaction.response.edit_message(embeds=self.embeds(), view=self)

    async def proxima(self, interaction):
        self.page = min(max(0, (len(self.rows) - 1) // self.PAGE_SIZE), self.page + 1)
        self._sync()
        await interaction.response.edit_message(embeds=self.embeds(), view=self)

    async def lista(self, interaction):
        texto = await self.cog.bot.get_cog("Perfil").texto_platinas(self.alvo)
        await interaction.response.edit_message(content=texto or "Ainda não há platinas aprovadas.",
                                                embeds=[], view=VoltarPainelView(self.cog, self.owner, self.alvo, self.callback_voltar))

    async def voltar(self, interaction):
        view = PainelView(self.cog, self.owner, callback_voltar=self.callback_voltar)
        view.alvo = self.alvo if self.alvo.id != self.owner.id else None
        await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)


class VoltarPainelView(discord.ui.View):
    """Retorna à tela de perfil sem publicar uma nova mensagem."""
    def __init__(self, cog, owner, alvo=None, callback_voltar=None):
        super().__init__(timeout=900)
        self.cog, self.owner_id = cog, owner.id
        self.owner, self.alvo = owner, alvo
        self.callback_voltar = callback_voltar
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar", emoji="↩️")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Este painel pertence a outra pessoa.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Voltar ao painel", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PainelView(self.cog, self.owner, callback_voltar=self.callback_voltar)
        view.alvo = self.alvo
        await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)


class RankingView(discord.ui.View):
    def __init__(self, cog, tipo: str, owner=None, alvo=None, callback_voltar=None):
        super().__init__(timeout=900)
        from cogs.ranking import TIPOS
        self.cog = cog
        self.owner = owner
        self.alvo = alvo
        self.callback_voltar = callback_voltar
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
        view = PainelView(self.cog, owner, callback_voltar=self.callback_voltar)
        view.alvo = self.alvo
        await interaction.response.edit_message(content=None, embed=await view.embed(), view=view)


class PlatinaModal(discord.ui.Modal):
    """Dados da platina; avaliação e conferência acontecem em seguida."""

    def __init__(
        self, cog, plataforma_padrao: str | None = None,
        jogo_padrao: str | None = None, data_padrao: str | None = None,
        motivo_rejeicao: str | None = None,
    ):
        super().__init__(title="Corrigir platina rejeitada" if jogo_padrao else "Registrar platina")
        self.cog = cog
        self.jogo = discord.ui.TextInput(
            placeholder="Ex.: Elden Ring", max_length=100,
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
        self.prova = discord.ui.FileUpload(required=True, min_values=1, max_values=10)
        self.add_item(discord.ui.Label(text="Jogo", component=self.jogo))
        self.add_item(discord.ui.Label(text="Plataforma", component=self.plataforma))
        self.add_item(discord.ui.Label(text="Data da conquista", component=self.data))
        self.add_item(discord.ui.Label(text="Print da platina (comprovante)", component=self.prova))

    async def on_submit(self, interaction: discord.Interaction):
        if not self.prova.values or not self.plataforma.values:
            return await interaction.response.send_message("Preencha a plataforma e anexe pelo menos um comprovante.", ephemeral=True)
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
            await self.cog.registrar_platina(
                avaliacao_interaction, jogo, plataforma, data, capturas, nota, comentario, dificuldade
            )

        await interaction.response.send_message(
            "**Avaliação — 1/3: Nota do jogo**\nQuanto você gostou deste jogo? Escolha uma nota de 1 a 10." + aviso_titulo,
            view=NotaJogoView(
                concluir, "Na sua experiência, qual foi a dificuldade para conquistar esta platina?",
                contexto=(f"Jogo: **{discord.utils.escape_markdown(jogo)}**\n"
                          f"Plataforma: **{plataforma}** · Data: **{data}**\n"
                          f"Comprovantes: **{len(capturas)} arquivo(s)**"
                          + (f"\n**Motivo da rejeição anterior:** {discord.utils.escape_markdown(self.motivo_rejeicao)}" if self.motivo_rejeicao else "")),
            ), ephemeral=True,
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
