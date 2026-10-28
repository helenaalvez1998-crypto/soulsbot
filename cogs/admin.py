"""Painel administrativo completo da Nara.

Um único comando /adm abre o painel principal. Toda a configuração é feita
por cliques em botões, seletores nativos de canal/cargo e modais de texto.
As configurações são persistidas por servidor via KV store com fallback para
config.py quando não há valor personalizado.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands

import config
from admin_config import GuildConfig, KEYS, LABELS, SECTIONS

log = logging.getLogger("admin")

COR_PAINEL = 0x2C3E50  # Azul escuro profissional


def _fmt_valor(valor, tipo: str = "channel") -> str:
    """Formata um valor para exibição no painel."""
    if valor is None or valor == 0:
        return "⚠️ Não configurado"
    if tipo == "channel":
        return f"<#{valor}>"
    if tipo == "role":
        return f"<@&{valor}>"
    return str(valor)


def _tipo_chave(key: str) -> str:
    if key in SECTIONS.get("channels", []):
        return "channel"
    if key in SECTIONS.get("roles", []):
        return "role"
    return "number"


# ────────────────────────────────────────────────────────────────
# Views persistentes (custom_id prefixo adm:)
# ────────────────────────────────────────────────────────────────

class AdminMainView(discord.ui.View):
    """Painel principal com botões de categoria."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Canais", emoji="📺", style=discord.ButtonStyle.primary, custom_id="adm:channels", row=0)
    async def canais(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _abrir_secao(interaction, self.bot, "channels", "📺 Canais Configurados")

    @discord.ui.button(label="Cargos", emoji="🎭", style=discord.ButtonStyle.primary, custom_id="adm:roles", row=0)
    async def cargos(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _abrir_secao(interaction, self.bot, "roles", "🎭 Cargos Configurados")

    @discord.ui.button(label="Coliseu", emoji="⚔️", style=discord.ButtonStyle.primary, custom_id="adm:coliseu", row=0)
    async def coliseu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _abrir_coliseu(interaction, self.bot)

    @discord.ui.button(label="Galeria", emoji="🏆", style=discord.ButtonStyle.secondary, custom_id="adm:galeria", row=1)
    async def galeria(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _abrir_galeria(interaction, self.bot)

    @discord.ui.button(label="Perfis", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="adm:perfis", row=1)
    async def perfis(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _abrir_perfis(interaction, self.bot)

    @discord.ui.button(label="Jogos", emoji="🎮", style=discord.ButtonStyle.secondary, custom_id="adm:jogos", row=1)
    async def jogos(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _abrir_jogos(interaction, self.bot)

    @discord.ui.button(label="Economia", emoji="💰", style=discord.ButtonStyle.success, custom_id="adm:economy", row=2)
    async def economia(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _abrir_economia(interaction, self.bot)

    @discord.ui.button(label="Personalização", emoji="🎨", style=discord.ButtonStyle.success, custom_id="adm:personalizacao", row=2)
    async def personalizacao(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _abrir_personalizacao(interaction, self.bot)

    @discord.ui.button(label="Status", emoji="📊", style=discord.ButtonStyle.success, custom_id="adm:status", row=2)
    async def status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _abrir_status(interaction, self.bot)

    @discord.ui.button(label="Restaurar Configurações", emoji="🔄", style=discord.ButtonStyle.danger, custom_id="adm:reset_confirm", row=3)
    async def restaurar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _confirmar_reset(interaction, self.bot)


class VoltarInicioView(discord.ui.View):
    """Botão para voltar ao painel principal."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Voltar ao Painel Principal", emoji="🏠", style=discord.ButtonStyle.secondary, custom_id="adm:home")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _mostrar_painel_principal(interaction, self.bot)


class ResetConfirmView(discord.ui.View):
    """Confirmação dupla antes de resetar todas as configurações."""

    def __init__(self, bot):
        super().__init__(timeout=60)
        self.bot = bot

    @discord.ui.button(label="Sim, restaurar tudo", emoji="⚠️", style=discord.ButtonStyle.danger, custom_id="adm:reset_yes")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        count = await GuildConfig.reset_all(self.bot.db, interaction.guild_id)
        embed = discord.Embed(
            title="✅ Configurações Restauradas",
            description=f"**{count}** configuração(ões) foram restauradas aos valores padrão de `config.py`.\n\nO bot continuará funcionando normalmente usando os valores globais.",
            color=discord.Color.green(),
        )
        view = VoltarInicioView(self.bot)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cancelar", emoji="↩️", style=discord.ButtonStyle.secondary, custom_id="adm:reset_no")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _mostrar_painel_principal(interaction, self.bot)


# ────────────────────────────────────────────────────────────────
# Seletor de canal persistente
# ────────────────────────────────────────────────────────────────

class ChannelSelectView(discord.ui.View):
    """Seletor nativo de canal que salva automaticamente."""

    def __init__(self, bot, key: str, label: str):
        super().__init__(timeout=120)
        self.bot = bot
        self.key = key
        self.label = label
        self.select = discord.ui.ChannelSelect(
            placeholder=f"Selecione o {label.lower()}",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
        )
        self.select.callback = self._salvar
        self.add_item(self.select)

    async def _salvar(self, interaction: discord.Interaction):
        channel = self.select.values[0]
        await GuildConfig.set(self.bot.db, interaction.guild_id, self.key, channel.id)
        log.info("Admin: %s configurado como %s na guild %s", self.key, channel.id, interaction.guild_id)
        embed = discord.Embed(
            title="✅ Canal Configurado",
            description=f"**{LABELS.get(self.key, self.key)}** definido como {channel.mention}.",
            color=discord.Color.green(),
        )
        view = VoltarInicioView(self.bot)
        await interaction.response.edit_message(embed=embed, view=view)


class RoleSelectView(discord.ui.View):
    """Seletor nativo de cargo que salva automaticamente."""

    def __init__(self, bot, key: str, label: str):
        super().__init__(timeout=120)
        self.bot = bot
        self.key = key
        self.label = label
        self.select = discord.ui.RoleSelect(
            placeholder=f"Selecione o {label.lower()}",
            min_values=1,
            max_values=1,
        )
        self.select.callback = self._salvar
        self.add_item(self.select)

    async def _salvar(self, interaction: discord.Interaction):
        role = self.select.values[0]
        await GuildConfig.set(self.bot.db, interaction.guild_id, self.key, role.id)
        log.info("Admin: %s configurado como %s na guild %s", self.key, role.id, interaction.guild_id)
        embed = discord.Embed(
            title="✅ Cargo Configurado",
            description=f"**{LABELS.get(self.key, self.key)}** definido como {role.mention}.",
            color=discord.Color.green(),
        )
        view = VoltarInicioView(self.bot)
        await interaction.response.edit_message(embed=embed, view=view)


# ────────────────────────────────────────────────────────────────
# Modal para valores numéricos (economia/recompensas)
# ────────────────────────────────────────────────────────────────

class NumberModal(discord.ui.Modal):
    """Modal genérico para configurar valores numéricos."""

    def __init__(self, bot, key: str, label: str, current_value: int | None):
        super().__init__(title=f"Configurar: {label}")
        self.bot = bot
        self.key = key
        self.valor_input = discord.ui.TextInput(
            label=label,
            placeholder=str(current_value) if current_value else "Ex.: 100",
            default=str(current_value) if current_value else None,
            max_length=10,
        )
        self.add_item(self.valor_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valor = int(self.valor_input.value.strip())
            if valor < 0:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message(
                "Valor inválido. Digite um número inteiro positivo.", ephemeral=True
            )
        await GuildConfig.set(self.bot.db, interaction.guild_id, self.key, valor)
        log.info("Admin: %s=%d na guild %s", self.key, valor, interaction.guild_id)
        embed = discord.Embed(
            title="✅ Valor Configurado",
            description=f"**{LABELS.get(self.key, self.key)}** definido como **{valor}**.",
            color=discord.Color.green(),
        )
        view = VoltarInicioView(self.bot)
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        log.exception("Erro no modal de configuração", exc_info=error)
        if not interaction.response.is_done():
            await interaction.response.send_message("Algo deu errado. Tente novamente.", ephemeral=True)


# ────────────────────────────────────────────────────────────────
# Botões de ação dentro das seções
# ────────────────────────────────────────────────────────────────

class SectionActionView(VoltarInicioView):
    """View com botões de 'Configurar X' para cada chave da seção + voltar."""

    def __init__(self, bot, keys: list[str]):
        super().__init__(bot)
        row = 0
        for i, key in enumerate(keys):
            label = LABELS.get(key, key)
            btn = discord.ui.Button(
                label=f"Configurar {label[:40]}",
                emoji="⚙️",
                style=discord.ButtonStyle.primary,
                custom_id=f"adm:set:{key}",
                row=row,
            )
            btn.callback = self._make_callback(key, label)
            self.add_item(btn)
            if (i + 1) % 4 == 0:
                row += 1

    def _make_callback(self, key: str, label: str):
        async def callback(interaction: discord.Interaction):
            tipo = _tipo_chave(key)
            if tipo == "channel":
                view = ChannelSelectView(self.bot, key, label)
                embed = discord.Embed(
                    title=f"⚙️ {label}",
                    description="Use o seletor abaixo para escolher o canal.",
                    color=COR_PAINEL,
                )
                await interaction.response.edit_message(embed=embed, view=view)
            elif tipo == "role":
                view = RoleSelectView(self.bot, key, label)
                embed = discord.Embed(
                    title=f"⚙️ {label}",
                    description="Use o seletor abaixo para escolher o cargo.",
                    color=COR_PAINEL,
                )
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                current = await GuildConfig.get(self.bot.db, interaction.guild_id, key)
                modal = NumberModal(self.bot, key, label, current)
                await interaction.response.send_modal(modal)
        return callback


# ────────────────────────────────────────────────────────────────
# Funções auxiliares para montar cada seção
# ────────────────────────────────────────────────────────────────

async def _mostrar_painel_principal(interaction: discord.Interaction, bot):
    """Renderiza o painel principal com resumo de status."""
    db = bot.db
    gid = interaction.guild_id
    total = len(KEYS)
    configurados = 0
    for k in KEYS:
        if await GuildConfig.is_custom(db, gid, k):
            configurados += 1
    pendentes = total - configurados

    embed = discord.Embed(
        title="⚙️ Painel Administrativo — Nara",
        description=(
            "Configure todos os sistemas do bot diretamente pelo Discord.\n\n"
            f"**Status:** {configurados}/{total} configurações personalizadas\n"
            + (f"⚠️ **{pendentes} item(ns)** ainda usam valores padrão." if pendentes else "✅ Tudo configurado!")
        ),
        color=COR_PAINEL,
    )
    embed.set_footer(text="Use os botões abaixo para navegar • Valores não configurados usam config.py")
    view = AdminMainView(bot)
    if interaction.response.is_done():
        await interaction.edit_original_response(embed=embed, view=view)
    else:
        await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_secao(interaction: discord.Interaction, bot, section: str, titulo: str):
    """Abre uma seção genérica (channels, roles, economy)."""
    keys = SECTIONS.get(section, [])
    db = bot.db
    gid = interaction.guild_id

    linhas = []
    for key in keys:
        valor = await GuildConfig.get(db, gid, key)
        tipo = _tipo_chave(key)
        custom = await GuildConfig.is_custom(db, gid, key)
        indicador = "🟢" if custom else ("🟡" if valor else "🔴")
        linhas.append(f"{indicador} **{LABELS.get(key, key)}:** {_fmt_valor(valor, tipo)}")

    embed = discord.Embed(title=titulo, description="\n".join(linhas), color=COR_PAINEL)
    embed.set_footer(text="🟢 Personalizado • 🟡 Padrão disponível • 🔴 Sem valor")
    view = SectionActionView(bot, keys)
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_coliseu(interaction: discord.Interaction, bot):
    """Seção Coliseu: combina canais de moderação/platinas com recompensas."""
    db = bot.db
    gid = interaction.guild_id

    mod_ch = await GuildConfig.get(db, gid, "mod_channel")
    plat_ch = await GuildConfig.get(db, gid, "platinas_channel")
    xp_plat = await GuildConfig.get(db, gid, "xp_platina")
    den_plat = await GuildConfig.get(db, gid, "denarios_platina")

    linhas = [
        f"📬 **Canal de Moderação:** {_fmt_valor(mod_ch)}",
        f"🏆 **Canal de Anúncio de Platinas:** {_fmt_valor(plat_ch)}",
        "",
        f"⭐ **XP por Platina:** {xp_plat or 'Padrão'}",
        f"🪙 **Denários por Platina:** {den_plat or 'Padrão'}",
    ]
    embed = discord.Embed(title="⚔️ Configurações do Coliseu", description="\n".join(linhas), color=COR_PAINEL)
    keys = ["mod_channel", "platinas_channel", "xp_platina", "denarios_platina"]
    view = SectionActionView(bot, keys)
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_galeria(interaction: discord.Interaction, bot):
    """Seção Galeria/Santuário: canal de perfis e informações sobre temas."""
    db = bot.db
    gid = interaction.guild_id
    perfis_ch = await GuildConfig.get(db, gid, "perfis_channel")

    linhas = [
        f"🏛️ **Canal de Santuários/Perfis:** {_fmt_valor(perfis_ch)}",
        "",
        "_Os santuários são criados automaticamente como threads privadas neste canal._",
        "_Temas disponíveis: Ouro, Prata, Sangue, Safira, Esmeralda, Violeta._",
    ]
    embed = discord.Embed(title="🏆 Galeria e Santuários", description="\n".join(linhas), color=COR_PAINEL)
    view = SectionActionView(bot, ["perfis_channel"])
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_perfis(interaction: discord.Interaction, bot):
    """Seção Perfis: informação read-only sobre patentes e níveis."""
    from levels import PATENTES, SIMBOLOS_PATENTES

    linhas = ["_As patentes são atribuídas automaticamente pelo sistema de XP._\n"]
    for nivel_min, nome in PATENTES:
        simbolo = SIMBOLOS_PATENTES.get(nome, "")
        linhas.append(f"{simbolo} **Nível {nivel_min}+** → {nome}")

    embed = discord.Embed(
        title="👤 Sistema de Patentes",
        description="\n".join(linhas),
        color=COR_PAINEL,
    )
    embed.set_footer(text="Patentes são automáticas e não precisam de configuração manual.")
    view = VoltarInicioView(bot)
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_jogos(interaction: discord.Interaction, bot):
    """Seção Jogos: canais de jogos grátis e promoções."""
    db = bot.db
    gid = interaction.guild_id
    games_ch = await GuildConfig.get(db, gid, "games_channel")
    promos_ch = await GuildConfig.get(db, gid, "promos_channel")

    linhas = [
        f"🎮 **Canal de Jogos Grátis:** {_fmt_valor(games_ch)}",
        f"🏷️ **Canal de Promoções:** {_fmt_valor(promos_ch)}",
        "",
        "_Ofertas são verificadas periodicamente via GamerPower e Steam Store._",
    ]
    embed = discord.Embed(title="🎮 Jogos e Promoções", description="\n".join(linhas), color=COR_PAINEL)
    view = SectionActionView(bot, ["games_channel", "promos_channel"])
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_economia(interaction: discord.Interaction, bot):
    """Seção Economia: todas as recompensas e limites."""
    await _abrir_secao(interaction, bot, "economy", "💰 Economia e Recompensas")


async def _abrir_personalizacao(interaction: discord.Interaction, bot):
    """Seção Personalização: cores e preferências visuais (expansível)."""
    embed = discord.Embed(
        title="🎨 Personalização",
        description=(
            "_Opções de personalização global serão adicionadas em futuras atualizações._\n\n"
            "**Atualmente disponível:**\n"
            "• Cores dos santuários (configurável pelo próprio membro)\n"
            "• Identidade visual do bot (definida em config.py)\n\n"
            "Para alterar cores globais ou prefixos, edite `config.py` diretamente."
        ),
        color=COR_PAINEL,
    )
    view = VoltarInicioView(bot)
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_status(interaction: discord.Interaction, bot):
    """Diagnóstico completo: lista cada configuração com seu estado."""
    db = bot.db
    gid = interaction.guild_id

    linhas_ok, linhas_warn, linhas_err = [], [], []
    for key in KEYS:
        valor = await GuildConfig.get(db, gid, key)
        custom = await GuildConfig.is_custom(db, gid, key)
        label = LABELS.get(key, key)
        tipo = _tipo_chave(key)
        if custom:
            linhas_ok.append(f"✅ {label}: {_fmt_valor(valor, tipo)}")
        elif valor:
            linhas_warn.append(f"🟡 {label}: {_fmt_valor(valor, tipo)} _(padrão)_")
        else:
            linhas_err.append(f"🔴 {label}: **não configurado**")

    desc_parts = []
    if linhas_ok:
        desc_parts.append("**Personalizados:**\n" + "\n".join(linhas_ok))
    if linhas_warn:
        desc_parts.append("**Usando padrão:**\n" + "\n".join(linhas_warn))
    if linhas_err:
        desc_parts.append("**Ausentes:**\n" + "\n".join(linhas_err))

    embed = discord.Embed(
        title="📊 Status das Configurações",
        description="\n\n".join(desc_parts) or "_Nenhuma configuração encontrada._",
        color=COR_PAINEL,
    )
    total = len(KEYS)
    ok = len(linhas_ok)
    embed.set_footer(text=f"{ok}/{total} personalizados • {len(linhas_warn)} padrão • {len(linhas_err)} ausentes")
    view = VoltarInicioView(bot)
    await interaction.response.edit_message(embed=embed, view=view)


async def _confirmar_reset(interaction: discord.Interaction, bot):
    """Tela de confirmação antes de resetar tudo."""
    count = 0
    for k in KEYS:
        if await GuildConfig.is_custom(bot.db, interaction.guild_id, k):
            count += 1
    embed = discord.Embed(
        title="⚠️ Restaurar Todas as Configurações?",
        description=(
            f"Você tem **{count}** configuração(ões) personalizada(s) neste servidor.\n\n"
            "Esta ação irá:\n"
            "• Remover todas as configurações personalizadas\n"
            "• Reverter para os valores padrão de `config.py`\n"
            "• **Não** apaga dados de usuários (XP, platinas, etc.)\n\n"
            "_Esta ação pode ser desfeita reconfigurando os valores novamente._"
        ),
        color=discord.Color.orange(),
    )
    view = ResetConfirmView(bot)
    await interaction.response.edit_message(embed=embed, view=view)


# ────────────────────────────────────────────────────────────────
# Cog principal
# ────────────────────────────────────────────────────────────────

class Admin(commands.Cog):
    """Painel administrativo unificado da Nara."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Registre apenas views persistentes: timeout=None e custom_id em todos os itens.
        self.bot.add_view(AdminMainView(self.bot))
        self.bot.add_view(VoltarInicioView(self.bot))
        # ResetConfirmView usa timeout=60 e é criada quando a confirmação é aberta;
        # não deve ser registrada como view persistente durante a inicialização.
        log.info("Cog Admin carregado com views persistentes registradas.")

    @app_commands.command(name="adm", description="Abre o painel administrativo completo do bot.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def adm(self, interaction: discord.Interaction):
        """Comando único de entrada para todo o painel administrativo."""
        embed = discord.Embed(
            title="⚙️ Painel Administrativo — Nara",
            description="Carregando configurações...",
            color=COR_PAINEL,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await _mostrar_painel_principal(interaction, self.bot)


async def setup(bot):
    await bot.add_cog(Admin(bot))