"""Central interativa de acesso às funções dos membros da NARA."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import config
from levels import nivel_por_xp, patente_por_nivel, barra_progresso
from painel_navegacao import adicionar_botao_voltar, view_so_com_voltar


class RemoverZeradoModal(discord.ui.Modal, title="Remover registro de jogo zerado"):
    def __init__(self, cog, callback_voltar=None):
        super().__init__(timeout=180)
        self.cog = cog
        self.callback_voltar = callback_voltar
        self.registro = discord.ui.TextInput(
            label="Número do registro",
            placeholder="Somente o número do registro (ex.: 12)",
            min_length=1,
            max_length=10,
        )
        self.add_item(self.registro)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            registro = int(self.registro.value.strip())
            if registro < 1:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("Digite somente o número positivo do registro (ex.: 12). Você encontra esse número na lista de jogos zerados.", ephemeral=True)
        await type(self.cog).remover_zerado.callback(self.cog, interaction, registro)


GUIA_MEMBROS = {
    "jogos": ("🎮 Minha biblioteca", "**Platinas:** consulte suas conquistas e registros aprovados.\n**Zerados:** registre e consulte seus jogos concluídos.\n**Runs e desafios:** acesse seus registros, tempos e recordes."),
    "progresso": ("🛡️ Nível e recompensas", "**Meu nível e XP:** consulte sua patente, experiência acumulada e progresso.\n**Ranking de XP:** compare a experiência dos membros.\n**Loja de recompensas:** consulte itens disponíveis e use seus Denários nas opções oferecidas."),
    "ajuda": ("🧠 Preferências e suporte", "**Minha memória na Nara:** acesse as opções de memória pessoal da assistente.\n**Ajuda e tutoriais:** encontre instruções para os recursos da comunidade.\n**Dica:** os botões abrem respostas privadas; você pode voltar ao painel para escolher outra função."),
    "perfil": ("👤 Meu perfil", "**Meu perfil:** consulte sua patente, nível, XP, Denários, quantidade de platinas e jogos zerados, além das posições nos rankings."),
    "santuario": ("🏛️ Meu Santuário", "**Meu Santuário:** crie ou abra seu espaço pessoal, personalize sua apresentação, configure redes e consulte sua galeria de platinas."),
}


class GuiaMembrosSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Não sabe por onde começar? Escolha um guia...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Jogos zerados", value="jogos", description="Registrar, consultar e excluir registros", emoji="🎮"),
                discord.SelectOption(label="Nível, XP e loja", value="progresso", description="Progresso, ranking e recompensas", emoji="🛡️"),
                discord.SelectOption(label="Memória e ajuda", value="ajuda", description="Preferências pessoais e tutoriais", emoji="🧠"),
                discord.SelectOption(label="Meu perfil", value="perfil", description="Nível, Denários, platinas e rankings", emoji="👤"),
                discord.SelectOption(label="Meu Santuário", value="santuario", description="Seu espaço pessoal e galeria", emoji="🏛️"),
            ],
            row=3,
        )

    async def callback(self, interaction: discord.Interaction):
        titulo, descricao = GUIA_MEMBROS[self.values[0]]
        embed = discord.Embed(title=titulo, description=descricao, color=config.COR_OURO)
        embed.set_footer(text="Volte ao painel anterior para executar a função desejada.")
        await interaction.response.send_message(embed=embed, ephemeral=True)



MEMBROS_CATEGORIAS = {
    "jogos": {
        "titulo": "🎮 Ports & Mods",
        "descricao": "Explore ports de jogos organizados por plataforma e mods relacionados. Pesquise títulos ou envie sugestões para análise da equipe.",
        "acoes": [
            ("catalogos", "Abrir Ports & Mods", "🎮", discord.ButtonStyle.primary),
        ],
    },
    "biblioteca": {
        "titulo": "📚 Minha biblioteca",
        "descricao": "Acesse suas platinas, jogos zerados e runs e desafios, ou corrija um registro de zerado.",
        "acoes": [
            ("biblioteca_platinas", "Platinas", "🏆", discord.ButtonStyle.primary),
            ("zerados", "Zerados", "✅", discord.ButtonStyle.success),
            ("biblioteca_runs", "Runs e desafios", "⚔️", discord.ButtonStyle.danger),
            ("remover_zerado", "Remover zerado", "🗑️", discord.ButtonStyle.secondary),
        ],
    },
    "progresso": {
        "titulo": "🏆 Meu progresso e recompensas",
        "descricao": "Consulte seu nível, compare seu XP e utilize seus Denários.",
        "acoes": [
            ("nivel", "Meu nível e XP", "🛡️", discord.ButtonStyle.primary),
            ("ranking_xp", "Ranking de XP", "🏆", discord.ButtonStyle.secondary),
            ("loja", "Loja de recompensas", "🪙", discord.ButtonStyle.success),
        ],
    },
    "preferencias": {
        "titulo": "🧠 Minhas preferências",
        "descricao": "Acesse as opções pessoais da Nara.",
        "acoes": [
            ("memoria", "Memória da Nara", "🧠", discord.ButtonStyle.secondary),
        ],
    },
    "ajuda": {
        "titulo": "❔ Ajuda e suporte",
        "descricao": "Encontre orientações para usar os recursos da comunidade.",
        "acoes": [
            ("ajuda", "Abrir central de ajuda", "📖", discord.ButtonStyle.primary),
        ],
    },
    "comunidade": {
        "titulo": "📡 Comunidade e contribuições",
        "descricao": "Participe da comunidade, publique Lore e Teorias, envie guias e acompanhe suas contribuições. Tudo passa por revisão humana antes da publicação.",
        "acoes": [
            ("community_home", "Central de Contribuições", "💡", discord.ButtonStyle.primary),
            ("community_archive", "Arquivo de Mundos", "📚", discord.ButtonStyle.secondary),
            ("community_mine", "Minhas contribuições", "🗂️", discord.ButtonStyle.secondary),
            ("ajuda", "Central de ajuda", "📖", discord.ButtonStyle.secondary),
            ("perfil", "Meu perfil e atividade", "👤", discord.ButtonStyle.secondary),
            ("santuario", "Meu Santuário", "🏛️", discord.ButtonStyle.success),
        ],
    },
}


def _embed_categoria_membro(categoria: str) -> discord.Embed:
    dados = MEMBROS_CATEGORIAS[categoria]
    embed = discord.Embed(
        title=dados["titulo"],
        description=dados["descricao"] + "\n\nEscolha uma ação. O resultado será privado; eu cuido da navegação para você não precisar caçar botão.",
        color=config.COR_OURO,
    )
    embed.set_footer(text="NARA • Use 'Voltar à central' para escolher outra categoria")
    return embed


def _retorno_categoria_membro(bot: commands.Bot, user_id: int, categoria: str):
    async def voltar(interaction: discord.Interaction):
        if categoria == "__inicio__":
            embed = discord.Embed(
                title="🌙 NARA — CENTRAL DO MEMBRO",
                description=(
                    "**Bem-vindo à sua central NARA.**\n\n"
                    "Escolha uma categoria. Eu organizo os caminhos; você fica com a parte interessante.\n"
                    "🎮 **Ports & Mods** · 📚 **Minha biblioteca** · 🏆 **Meu progresso**\n"
                    "🧠 **Preferências** · 📡 **Comunidade** · ❔ **Ajuda e suporte**\n\n"
                    "🔒 Esta central é privada e só pode ser utilizada por você."
                ),
                color=config.COR_OURO,
            )
            embed.set_footer(text="NARA • Central de acesso dos membros")
            await interaction.response.edit_message(embed=embed, view=PainelMembrosView(bot, user_id))
            return
        await interaction.response.edit_message(
            embed=_embed_categoria_membro(categoria),
            view=MembrosCategoriaView(bot, user_id, categoria),
        )
    return voltar


async def _executar_acao_membro(
    interaction: discord.Interaction,
    bot: commands.Bot,
    action: str,
    *,
    categoria: str | None = None,
    user_id: int | None = None,
):
    """Encaminha a ação do painel para o módulo original, sem duplicar regras de negócio."""
    voltar = (
        _retorno_categoria_membro(bot, user_id or interaction.user.id, categoria)
        if categoria in MEMBROS_CATEGORIAS else None
    )

    def com_voltar(view):
        return adicionar_botao_voltar(view, voltar)

    if action == "coliseu":
        cog = bot.get_cog("Platinas")
        if cog is None:
            return await interaction.response.send_message("O Coliseu está indisponível no momento. Tente novamente mais tarde.", ephemeral=True)
        from cogs.platinas import ColiseuView
        view = ColiseuView(cog, interaction.user, back_callback=voltar)
        return await interaction.response.edit_message(content=view.texto(), embed=None, view=view)

    if action == "biblioteca_platinas":
        cog = bot.get_cog("Platinas")
        if cog is None:
            return await interaction.response.send_message("O painel de platinas está indisponível no momento.", ephemeral=True)
        from cogs.platinas import PainelView
        view = PainelView(cog, interaction.user)
        return await interaction.response.edit_message(content=None, embed=await view.embed(), view=com_voltar(view))

    if action == "biblioteca_runs":
        cog = bot.get_cog("Soulslike")
        if cog is None:
            return await interaction.response.send_message("O painel de runs e desafios está indisponível no momento.", ephemeral=True)
        from cogs.soulslike import CentralView
        view = CentralView(cog)
        return await interaction.response.edit_message(content=cog.texto_central(), embeds=[], view=com_voltar(view))

    if action == "zerados":
        cog = bot.get_cog("Zerados")
        if cog is None:
            return await interaction.response.send_message("O painel de jogos zerados está indisponível no momento.", ephemeral=True)
        view = cog.painel_view(interaction.user)
        return await interaction.response.edit_message(content=None, embed=await view.embed(), view=com_voltar(view))

    if action == "remover_zerado":
        cog = bot.get_cog("Zerados")
        if cog is None:
            return await interaction.response.send_message("O gerenciamento de jogos zerados está indisponível no momento.", ephemeral=True)
        return await interaction.response.send_modal(RemoverZeradoModal(cog, callback_voltar=voltar))

    if action == "loja":
        cog = bot.get_cog("Loja")
        if cog is None:
            return await interaction.response.send_message("A loja está indisponível no momento.", ephemeral=True)
        from cogs.loja import LojaView
        view = LojaView(cog, interaction.user)
        await view.carregar()
        return await interaction.response.edit_message(content=None, embed=view.embed(), view=view)

    if action == "nivel":
        cog = bot.get_cog("ProgressaoXP")
        if cog is None:
            return await interaction.response.send_message("O sistema de níveis está indisponível no momento.", ephemeral=True)
        user = await bot.db.get_user(interaction.user.id)
        xp = int(user["xp"])
        nivel_atual = nivel_por_xp(xp)
        embed = discord.Embed(title=f"🛡️ NARA — {interaction.user.display_name}", color=config.COR_OURO)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Patente", value=patente_por_nivel(nivel_atual), inline=True)
        embed.add_field(name="Nível", value=str(nivel_atual), inline=True)
        embed.add_field(name="XP total", value=f"{xp:,}", inline=True)
        embed.add_field(name="Progresso", value=barra_progresso(xp), inline=False)
        return await interaction.response.edit_message(embed=embed, content=None, view=view_so_com_voltar(voltar))

    if action == "ranking_xp":
        cog = bot.get_cog("ProgressaoXP")
        if cog is None:
            return await interaction.response.send_message("O ranking de XP está indisponível no momento.", ephemeral=True)
        rows = await bot.db.ranking_xp(10)
        if not rows:
            return await interaction.response.edit_message(content="Ainda não há XP registrado para montar o ranking.", embed=None, view=view_so_com_voltar(voltar))
        linhas = []
        for i, row in enumerate(rows, 1):
            nivel_atual = nivel_por_xp(int(row["valor"]))
            linhas.append(
                f"`{i:>2}.` <@{row['user_id']}> — **Nível {nivel_atual}** · "
                f"{patente_por_nivel(nivel_atual)} · {row['valor']} XP"
            )
        return await interaction.response.edit_message(
            content="## 🏆 Ranking de XP da NARA\n\n" + "\n".join(linhas),
            embed=None,
            view=view_so_com_voltar(voltar),
        )

    if action == "memoria":
        cog = bot.get_cog("NaraIA")
        if cog is None:
            return await interaction.response.send_message("As preferências de memória estão indisponíveis no momento.", ephemeral=True)
        return await type(cog).nara_memoria.callback(cog, interaction)

    if action == "ajuda":
        cog = bot.get_cog("NaraIA")
        if cog is None:
            return await interaction.response.send_message("A Central de Ajuda está indisponível no momento.", ephemeral=True)
        return await type(cog).central_ajuda_command.callback(cog, interaction)

    if action == "perfil":
        cog = bot.get_cog("Perfil")
        if cog is None:
            return await interaction.response.send_message("Seu perfil está indisponível no momento.", ephemeral=True)
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Não consegui identificar seu perfil neste servidor.", ephemeral=True)
        embed = await cog.embed_perfil(interaction.user)
        embed.set_footer(text="NARA • Seu perfil pessoal")
        return await interaction.response.edit_message(embed=embed, content=None, view=view_so_com_voltar(voltar))

    if action == "santuario":
        cog = bot.get_cog("Santuario")
        if cog is None:
            return await interaction.response.send_message("Seu Santuário está indisponível no momento.", ephemeral=True)
        return await cog.abrir_meu(interaction)

    if action == "catalogos":
        cog = bot.get_cog("CatalogoIntegrado")
        if cog is None:
            return await interaction.response.send_message("O catálogo Ports & Mods ainda não está disponível.", ephemeral=True)
        return await cog.abrir_membros(interaction)

    if action in ("community_home", "community_archive", "community_mine"):
        cog = bot.get_cog("Comunidade")
        if cog is None:
            return await interaction.response.send_message("O sistema de contribuições está indisponível no momento.", ephemeral=True)
        if action == "community_archive":
            return await cog.mostrar_arquivo(interaction)
        if action == "community_mine":
            return await cog.mostrar_minhas(interaction)
        from cogs.comunidade import CommunityHomeView
        embed = discord.Embed(
            title="💡 Contribuições da Comunidade",
            description="Publique lore, teorias, descobertas, guias, tutoriais e propostas para o NARA. Todos os envios passam por aprovação humana antes de aparecerem nos canais oficiais.",
            color=config.COR_OURO,
        )
        return await interaction.response.edit_message(content=None, embed=embed, view=CommunityHomeView(cog))

    return await interaction.response.send_message("Esta opção ainda não está disponível. Volte à central e escolha outra categoria.", ephemeral=True)


class MembrosAcaoButton(discord.ui.Button):
    def __init__(self, painel, action: str, label: str, emoji: str, style: discord.ButtonStyle, row: int):
        super().__init__(label=label, emoji=emoji, style=style, row=row)
        self.painel = painel
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        await _executar_acao_membro(interaction, self.painel.bot, self.action, categoria=self.painel.categoria, user_id=self.painel.user_id)


class MembrosVoltarButton(discord.ui.Button):
    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(label="Voltar à central", emoji="🏠", style=discord.ButtonStyle.secondary, row=1)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌙 NARA — CENTRAL DO MEMBRO",
            description=(
                "**Bem-vindo à sua central de recursos.**\n\n"
                "Escolha uma categoria para encontrar a função desejada:\n"
                "🎮 **Ports & Mods:** explore ports de jogos e mods da comunidade.\n"
                "📚 **Minha biblioteca:** Platinas, Zerados e Runs e desafios.\n"
                "🏆 **Meu progresso:** nível, XP, ranking e Loja.\n"
                "👤 **Meu perfil:** estatísticas, patente e rankings pessoais.\n"
                "🏛️ **Meu Santuário:** espaço pessoal e galeria de platinas.\n"
                "🧠 **Preferências:** opções pessoais da Nara.\n"
                "❔ **Ajuda e suporte:** tutoriais e orientações.\n\n"
                "🔒 Esta central é privada e só pode ser utilizada por você."
            ),
            color=config.COR_OURO,
        )
        embed.set_footer(text="NARA • Central de acesso dos membros")
        await interaction.response.edit_message(embed=embed, view=PainelMembrosView(self.bot, self.user_id))


class MembrosCategoriaView(discord.ui.View):
    def __init__(self, bot: commands.Bot, user_id: int, categoria: str):
        super().__init__(timeout=600)
        self.bot = bot
        self.user_id = user_id
        self.categoria = categoria
        dados = MEMBROS_CATEGORIAS[categoria]
        for index, (action, label, emoji, style) in enumerate(dados["acoes"]):
            self.add_item(MembrosAcaoButton(self, action, label, emoji, style, row=0 if index < 3 else 1))
        self.add_item(MembrosVoltarButton(bot, user_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Este painel pertence a outro membro. Use `/nara` para abrir o seu.", ephemeral=True)
            return False
        return True


class MembrosAcessoDiretoButton(discord.ui.Button):
    def __init__(self, painel, action: str, label: str, emoji: str, style: discord.ButtonStyle, row: int = 2):
        super().__init__(label=label, emoji=emoji, style=style, row=row)
        self.painel = painel
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        await _executar_acao_membro(interaction, self.painel.bot, self.action, categoria="__inicio__", user_id=self.painel.user_id)


class MembrosCategoriaButton(discord.ui.Button):
    def __init__(self, painel, categoria: str, label: str, emoji: str, row: int):
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.primary, row=row)
        self.painel = painel
        self.categoria = categoria

    async def callback(self, interaction: discord.Interaction):
        dados = MEMBROS_CATEGORIAS[self.categoria]
        embed = discord.Embed(
            title=dados["titulo"],
            description=dados["descricao"] + "\n\nEscolha uma ação. O resultado será privado; eu cuido da navegação para você não precisar caçar botão.",
            color=config.COR_OURO,
        )
        embed.set_footer(text="NARA • Use 'Voltar à central' para escolher outra categoria")
        await interaction.response.edit_message(
            embed=embed,
            view=MembrosCategoriaView(self.painel.bot, self.painel.user_id, self.categoria),
        )


class PainelMembrosView(discord.ui.View):
    """Central de membros organizada por categorias, com submenus privados."""

    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(timeout=600)
        self.bot = bot
        self.user_id = user_id
        categorias = [
            ("jogos", "Ports & Mods", "🎮"),
            ("biblioteca", "Minha biblioteca", "📚"),
            ("progresso", "Meu progresso", "🏆"),
            ("preferencias", "Preferências", "🧠"),
            ("ajuda", "Ajuda e suporte", "❔"),
            ("comunidade", "Comunidade", "📡"),
        ]
        for index, (key, label, emoji) in enumerate(categorias):
            self.add_item(MembrosCategoriaButton(self, key, label, emoji, row=index // 3))
        self.add_item(MembrosAcessoDiretoButton(self, "perfil", "Meu perfil", "👤", discord.ButtonStyle.secondary))
        self.add_item(MembrosAcessoDiretoButton(self, "santuario", "Meu Santuário", "🏛️", discord.ButtonStyle.success))
        self.add_item(GuiaMembrosSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Este painel pertence a outro membro. Use `/nara` para abrir o seu.",
                ephemeral=True,
            )
            return False
        return True


class PainelMembros(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="nara", description="Abra sua central de Ports & Mods, biblioteca, progresso, recompensas e suporte.")
    @app_commands.guild_only()
    async def nara(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌙 NARA — CENTRAL DO MEMBRO",
            description=(
                "**Bem-vindo à sua central NARA.**\n\n"
                "🎮 **Ports & Mods:** explore ports de jogos e mods da comunidade, pesquise e envie sugestões.\n"
                "📚 **Minha biblioteca:** acesse Platinas, Zerados e Runs e desafios.\n"
                "🏆 **Meu progresso:** acompanhe nível, XP, ranking e Loja.\n"
                "👤 **Meu perfil:** veja suas estatísticas e posições nos rankings.\n"
                "🏛️ **Meu Santuário:** personalize seu espaço e galeria de platinas.\n"
                "🧠 **Preferências:** acesse suas opções pessoais da Nara.\n"
                "📡 **Comunidade:** acompanhe novidades, contribua com Lore, Teorias e Guias no Arquivo de Mundos.\n"
                "❔ **Ajuda e suporte:** encontre tutoriais e orientações.\n\n"
                "**Como usar:** escolha uma categoria para abrir as ações relacionadas. "
                "Cada submenu explica o que você pode fazer. Não precisa decorar tudo de uma vez.\n\n"
                "🔒 Este painel é privado: somente você pode utilizá-lo."
            ),
            color=config.COR_OURO,
        )
        embed.set_footer(text="NARA • Central de acesso dos membros")
        await interaction.response.send_message(
            embed=embed,
            view=PainelMembrosView(self.bot, interaction.user.id),
            ephemeral=True,
        )

    async def cog_load(self):
        # Os comandos continuam implementados nos módulos originais e são acessados
        # pelos botões. Removê-los da árvore reduz a lista pública do Discord sem
        # duplicar a lógica nem quebrar os fluxos internos.
        comandos_membros = (
            "coliseu", "zerados", "remover_zerado",
            "loja", "nivel", "ranking-xp", "nara_memoria", "central_ajuda", "comandos",
        )
        for nome in comandos_membros:
            self.bot.tree.remove_command(nome)


async def setup(bot: commands.Bot):
    await bot.add_cog(PainelMembros(bot))
