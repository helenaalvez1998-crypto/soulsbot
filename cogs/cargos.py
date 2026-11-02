import json
import discord
from discord import app_commands
from discord.ext import commands
from utils import upsert_panel, erro_comando

DEFAULT_ROLES = [
    ("Avisos de Vídeo", "🔔"),
    ("Avisos de Live", "🔴"),
    ("Elden Ring", "⚔️"),
    ("Dark Souls", "💀"),
    ("Bloodborne", "🩸"),
    ("Sekiro", "🗡️"),
    ("Outros Soulslikes", "🌑"),
    ("Procurando Co-op", "🤝"),
]
MAX_ROLES = 25


class Verificacao(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verificar-me", emoji="✅", style=discord.ButtonStyle.success,
                       custom_id="verificar_membro")
    async def verificar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Use este botão dentro do servidor.", ephemeral=True)
            return
        cargo = discord.utils.get(interaction.guild.roles, name="✅ Membro")
        if cargo is None:
            await interaction.response.send_message("Cargo de membro não encontrado.", ephemeral=True)
            return
        if cargo in interaction.user.roles:
            await interaction.response.send_message("Você já está verificado(a)!", ephemeral=True)
            return
        try:
            await interaction.user.add_roles(cargo, reason="Verificação por botão")
            await interaction.response.send_message("Verificação concluída! Bem-vindo(a).", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Não consigo atribuir esse cargo. Confira Gerenciar Cargos e a hierarquia do bot.",
                ephemeral=True)


class CargosView(discord.ui.View):
    """View persistente: cada botão aponta para a posição salva na configuração do servidor."""
    def __init__(self, itens=None):
        super().__init__(timeout=None)
        # Sem configuração: registra todos os IDs possíveis para views antigas persistirem.
        # Com configuração: exibe apenas os botões realmente configurados.
        if itens is None:
            itens = [{"label": "Cargo", "emoji": None} for _ in range(MAX_ROLES)]
            disabled = True
        else:
            disabled = False
        for i, item in enumerate(itens[:MAX_ROLES]):
            button = discord.ui.Button(
                label=item.get("label", "Cargo")[:80],
                emoji=item.get("emoji") or None,
                style=discord.ButtonStyle.secondary,
                custom_id=f"cargo_escolha_{i}",
                disabled=disabled,
            )
            button.callback = self._callback(i)
            self.add_item(button)

    @staticmethod
    def _callback(index):
        async def callback(interaction: discord.Interaction):
            if interaction.guild is None or not isinstance(interaction.user, discord.Member):
                await interaction.response.send_message("Use este botão dentro do servidor.", ephemeral=True)
                return
            raw = await interaction.client.db.get_kv(f"roles_config:{interaction.guild_id}")
            config_data = json.loads(raw) if raw else {}
            itens = config_data.get("roles", [])
            if index >= len(itens):
                await interaction.response.send_message("Este botão não está configurado. Avise a moderação.", ephemeral=True)
                return
            item = itens[index]
            role_id = item.get("role_id")
            role = interaction.guild.get_role(int(role_id)) if role_id else None
            if role is None:
                await interaction.response.send_message(
                    f"O cargo configurado para **{item.get('label', 'este botão')}** não existe mais. Avise a moderação.",
                    ephemeral=True)
                return
            try:
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role, reason="Cargo removido pelo painel de cargos")
                    await interaction.response.send_message(f"Cargo **{role.name}** removido.", ephemeral=True)
                else:
                    await interaction.user.add_roles(role, reason="Cargo escolhido pelo painel")
                    await interaction.response.send_message(f"Cargo **{role.name}** adicionado.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message(
                    "Não consigo alterar esse cargo. Confira Gerenciar Cargos e a hierarquia do bot.",
                    ephemeral=True)
        return callback


class Cargos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(Verificacao())
        # Registra os custom_ids persistentes para os painéis existentes após reinicialização.
        self.bot.add_view(CargosView())

    async def _get_config(self, guild: discord.Guild):
        key = f"roles_config:{guild.id}"
        raw = await self.bot.db.get_kv(key)
        if raw:
            try:
                data = json.loads(raw)
                data.setdefault("title", "🎭 Escolha seus cargos")
                data.setdefault("description", "Clique em um cargo para adicioná-lo ou removê-lo. Clique novamente para tirar.")
                data.setdefault("roles", [])
                return data
            except (ValueError, TypeError):
                pass
        roles = []
        for name, emoji in DEFAULT_ROLES:
            role = discord.utils.get(guild.roles, name=name) or discord.utils.get(guild.roles, name=f"{emoji} {name}")
            if role:
                roles.append({"role_id": role.id, "label": name, "emoji": emoji})
        data = {
            "title": "🎭 Escolha seus cargos",
            "description": "Clique em um cargo para adicioná-lo ou removê-lo. Clique novamente para tirar.",
            "roles": roles,
        }
        await self._save_config(guild.id, data)
        return data

    async def _save_config(self, guild_id, data):
        await self.bot.db.set_kv(f"roles_config:{guild_id}", json.dumps(data, ensure_ascii=False))

    async def _update_panel(self, interaction, data):
        if interaction.guild is None or interaction.channel is None:
            raise ValueError("Use este comando dentro de um servidor e canal de texto.")
        content = f"# {data['title']}\n\n{data['description']}"
        await upsert_panel(
            self.bot, interaction.channel,
            f"panel:roles:{interaction.guild_id}:{interaction.channel_id}",
            marker="cargo_escolha_*", content=content, embeds=[],
            view=CargosView(data.get("roles", [])),
        )

    @app_commands.command(name="painel_verificacao", description="[MOD] Publica ou atualiza o painel de verificação.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def painel_verificacao(self, interaction: discord.Interaction):
        texto = "# ✅ Verificação do servidor\n\nPara liberar o acesso aos canais, clique em **Verificar-me** abaixo.\n\n_Se o botão não funcionar, avise a moderação._"
        await upsert_panel(self.bot, interaction.channel,
            f"panel:verification:{interaction.guild_id}:{interaction.channel_id}",
            marker="verificar_membro", content=texto, embeds=[], view=Verificacao())
        await interaction.response.send_message("Painel de verificação atualizado neste canal.", ephemeral=True)

    @app_commands.command(name="painel_cargos", description="[MOD] Publica ou atualiza o painel configurado de cargos.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def painel_cargos(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        data = await self._get_config(interaction.guild)
        await self._update_panel(interaction, data)
        await interaction.response.send_message("Painel de cargos publicado/atualizado neste canal.", ephemeral=True)

    @app_commands.command(name="editar_painel_cargos", description="[MOD] Edita o título e a mensagem do painel de cargos.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(titulo="Título exibido no painel", mensagem="Texto abaixo do título")
    async def editar_painel_cargos(self, interaction: discord.Interaction, titulo: str, mensagem: str):
        if interaction.guild is None:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        data = await self._get_config(interaction.guild)
        data["title"] = titulo[:250]
        data["description"] = mensagem[:3500]
        await self._save_config(interaction.guild_id, data)
        await self._update_panel(interaction, data)
        await interaction.response.send_message("Texto salvo e painel atualizado neste canal.", ephemeral=True)

    @app_commands.command(name="cargo_painel", description="[MOD] Adiciona, edita ou remove uma opção do painel de cargos.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(acao="O que deseja fazer", cargo="Cargo do servidor", nome="Texto do botão (sem emoji)", emoji="Emoji do botão")
    @app_commands.choices(acao=[
        app_commands.Choice(name="Adicionar", value="adicionar"),
        app_commands.Choice(name="Editar", value="editar"),
        app_commands.Choice(name="Remover", value="remover"),
    ])
    async def cargo_painel(self, interaction: discord.Interaction, acao: app_commands.Choice[str],
                           cargo: discord.Role, nome: str = None, emoji: str = None):
        if interaction.guild is None:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        data = await self._get_config(interaction.guild)
        itens = data["roles"]
        found = next((i for i, item in enumerate(itens) if int(item.get("role_id", 0)) == cargo.id), None)
        if acao.value == "adicionar":
            if found is not None:
                await interaction.response.send_message("Esse cargo já está no painel. Use **Editar** para alterar o botão.", ephemeral=True)
                return
            if len(itens) >= MAX_ROLES:
                await interaction.response.send_message("O Discord permite no máximo 25 botões nesta view.", ephemeral=True)
                return
            itens.append({"role_id": cargo.id, "label": (nome or cargo.name)[:80], "emoji": emoji or None})
        elif acao.value == "editar":
            if found is None:
                await interaction.response.send_message("Esse cargo não está no painel. Use **Adicionar** primeiro.", ephemeral=True)
                return
            if nome is not None:
                itens[found]["label"] = nome[:80]
            if emoji is not None:
                itens[found]["emoji"] = emoji or None
        else:
            if found is None:
                await interaction.response.send_message("Esse cargo não está no painel.", ephemeral=True)
                return
            itens.pop(found)
        await self._save_config(interaction.guild_id, data)
        await self._update_panel(interaction, data)
        await interaction.response.send_message(f"Configuração de cargos atualizada: **{acao.name}**.", ephemeral=True)

    async def cog_app_command_error(self, interaction, error):
        await erro_comando(interaction, error)


async def setup(bot):
    await bot.add_cog(Cargos(bot))
