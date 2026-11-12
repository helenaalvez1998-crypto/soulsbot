"""Sincronização dos cartões originais após decisões tomadas na Central /adm."""
import logging
import discord
from admin_config import GuildConfig
from utils import get_text_channel

log = logging.getLogger("moderacao")

async def sincronizar_cartao(bot, guild_id: int, tipo: str, registro_id: int, status: str,
                              reviewer_id: int, motivo: str | None = None):
    tabelas = {"platinas": "platinas", "runs": "sl_runs", "zerados": "zerados"}
    tabela = tabelas.get(tipo)
    if not tabela:
        return False
    try:
        row = await bot.db._one(f"SELECT proof_msg_id FROM {tabela} WHERE id=?", (registro_id,))
        if row is None or not row["proof_msg_id"]:
            return False
        canal_id = await GuildConfig.get(bot.db, guild_id, "mod_channel")
        canal = await get_text_channel(bot, canal_id) if canal_id else None
        if canal is None:
            return False
        mensagem = await canal.fetch_message(int(row["proof_msg_id"]))
        embed = discord.Embed.from_dict(mensagem.embeds[0].to_dict()) if mensagem.embeds else discord.Embed(title=f"Solicitação #{registro_id}")
        aprovado = status == "approved"
        embed.color = discord.Color.green() if aprovado else discord.Color.red()
        embed.add_field(
            name="Resultado",
            value=(f"{'✅ Aprovada' if aprovado else '❌ Rejeitada'} por <@{reviewer_id}>" + (f"\n**Motivo:** {motivo}" if motivo else "")),
            inline=False,
        )
        footer = embed.footer.text or ""
        if tipo == "platinas":
            embed.set_footer(text=f"ID:{registro_id} · {'APROVADA' if aprovado else 'REJEITADA'}")
        elif tipo == "runs":
            embed.set_footer(text=f"SL:{registro_id} · {'APROVADA' if aprovado else 'REJEITADA'}")
        else:
            embed.set_footer(text=f"ZeradoID:{registro_id} · {'APROVADO' if aprovado else 'REJEITADO'}")
        await mensagem.edit(embed=embed, view=None)
        return True
    except discord.NotFound:
        log.warning("Cartão original ausente para %s #%s", tipo, registro_id)
    except discord.HTTPException:
        log.exception("Falha ao sincronizar cartão %s #%s", tipo, registro_id)
    except Exception:
        log.exception("Erro inesperado ao sincronizar cartão %s #%s", tipo, registro_id)
    return False

class MotivoDecisaoModal(discord.ui.Modal, title="Motivo da rejeição"):
    motivo = discord.ui.TextInput(label="Motivo (obrigatório)", style=discord.TextStyle.paragraph,
                                  min_length=5, max_length=300,
                                  placeholder="Explique objetivamente o que precisa ser corrigido.")

    def __init__(self, bot, tipo: str, registro_id: int, callback):
        super().__init__()
        self.bot, self.tipo, self.registro_id, self.callback_decisao = bot, tipo, registro_id, callback

    async def on_submit(self, interaction: discord.Interaction):
        motivo = str(self.motivo).strip()
        if len(motivo) < 5:
            return await interaction.response.send_message("Informe um motivo com pelo menos 5 caracteres.", ephemeral=True)
        try:
            await self.bot.db.log(interaction.user.id, f"{self.tipo}_motivo_rejeicao", f"id={self.registro_id} motivo={motivo}")
        except Exception:
            log.exception("Falha ao registrar motivo da rejeição %s #%s", self.tipo, self.registro_id)
        await self.callback_decisao(interaction, motivo)
