"""Painel persistente de cargos selecionáveis administrado pelo portal NARA."""
from __future__ import annotations

import json
import logging
import discord
from discord.ext import commands

log = logging.getLogger("cogs.portal_role_panel")


class SelfRoleSelect(discord.ui.Select):
    def __init__(self, bot, roles=None):
        self.bot = bot
        options = [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in (roles or [])[:25]]
        if not options:
            options = [discord.SelectOption(label="Carregando opções", value="none")]
        super().__init__(
            placeholder="Escolha seus cargos de interesse...",
            min_values=0,
            max_values=len(options),
            custom_id="nara:self_roles:select",
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("Use este painel dentro do servidor.", ephemeral=True)
        raw = await self.bot.db.get_kv(f"portal:self_roles:{interaction.guild.id}")
        try:
            configured = json.loads(raw or "[]")
        except (TypeError, ValueError):
            configured = []
        allowed = {int(x) for x in configured if str(x).isdigit()}
        selected = {int(x) for x in self.values if str(x).isdigit()}
        if not selected.issubset(allowed):
            return await interaction.response.send_message("A configuração deste painel mudou. Peça à equipe para republicá-lo.", ephemeral=True)
        member = interaction.user
        bot_member = interaction.guild.me
        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            return await interaction.response.send_message("O bot precisa da permissão Gerenciar Cargos.", ephemeral=True)
        role_map = {r.id: r for r in interaction.guild.roles}
        managed = {rid: role_map[rid] for rid in allowed if rid in role_map and not role_map[rid].managed and role_map[rid] < bot_member.top_role}
        if not selected.issubset(managed):
            return await interaction.response.send_message("Um ou mais cargos não estão mais disponíveis.", ephemeral=True)
        current = {r.id for r in member.roles}
        add_ids = selected - current
        remove_ids = (allowed & current) - selected
        try:
            if add_ids:
                await member.add_roles(*(managed[x] for x in add_ids), reason="Preferências de cargos pelo painel NARA")
            if remove_ids:
                await member.remove_roles(*(managed[x] for x in remove_ids if x in managed), reason="Preferências de cargos pelo painel NARA")
        except discord.Forbidden:
            return await interaction.response.send_message("Não tenho hierarquia/permissão para alterar esses cargos.", ephemeral=True)
        except discord.HTTPException:
            log.exception("Falha ao atualizar cargos selecionáveis")
            return await interaction.response.send_message("Falha do Discord ao atualizar seus cargos. Tente novamente.", ephemeral=True)
        mentions = [role_map[x].mention for x in sorted(selected) if x in role_map]
        await interaction.response.send_message(
            "Preferências atualizadas. " + ("Cargos ativos: " + ", ".join(mentions) if mentions else "Nenhum cargo selecionável ativo."),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class SelfRolePanelView(discord.ui.View):
    def __init__(self, bot, roles=None):
        super().__init__(timeout=None)
        self.add_item(SelfRoleSelect(bot, roles))


class PortalRolePanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(SelfRolePanelView(bot))


async def setup(bot):
    await bot.add_cog(PortalRolePanel(bot))
