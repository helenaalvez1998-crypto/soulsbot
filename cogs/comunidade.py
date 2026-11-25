"""Contribuições, Arquivo de Mundos e camada social do NARA.

Este módulo centraliza publicação comunitária, interações, favoritos, acompanhamento,
threads e participação em desafios. A aprovação editorial continua sendo humana.
"""
from __future__ import annotations

import logging
import re

import discord
from discord.ext import commands

import config
from admin_config import GuildConfig
from utils import get_text_channel

log = logging.getLogger("nara.comunidade")

TIPOS = {
    "lore": ("📜 Lore", "Lore documentada ou narrativa do universo do jogo", 15),
    "theory": ("🔍 Teoria", "Hipótese e interpretação sustentada por evidências", 15),
    "discovery": ("🧩 Descoberta", "Segredo, conexão ou elemento encontrado no jogo", 20),
    "timeline": ("🕰️ Cronologia", "Organização temporal de acontecimentos", 20),
    "debate": ("💬 Debate", "Questão aberta para discussão comunitária", 5),
    "guide": ("📘 Guia", "Guia estruturado para ajudar outros jogadores", 25),
    "tutorial": ("🛠️ Tutorial", "Passo a passo prático e verificável", 25),
    "challenge": ("⚔️ Desafio", "Proposta de desafio individual ou coletivo", 15),
    "game_suggestion": ("🎮 Jogo para Runs", "Sugestão de jogo para a Central Soulslike", 10),
    "faq": ("❔ Pergunta para FAQ", "Pergunta e resposta sugeridas para a Central de Ajuda", 10),
    "item_suggestion": ("🪙 Item para Loja", "Sugestão de item, cosmético ou recompensa", 5),
    "correction": ("🧹 Correção", "Correção ou complemento de conteúdo existente", 5),
    "idea": ("💡 Ideia", "Sugestão de melhoria para o NARA ou a comunidade", 5),
}

CANAL_POR_TIPO = {
    "lore": "lore_channel", "theory": "lore_channel", "discovery": "lore_channel",
    "timeline": "lore_channel", "debate": "lore_channel",
    "guide": "guides_channel", "tutorial": "guides_channel",
    "challenge": "soulslike_channel", "game_suggestion": "soulslike_channel",
    "faq": "guides_channel", "item_suggestion": "community_channel",
    "correction": "community_channel", "idea": "community_channel",
}

REACTIONS = {
    "run": [
        ("gg", "👏", "GG"), ("fire", "🔥", "Insana"),
        ("build", "🧠", "Estratégia"), ("try", "⚔️", "Vou tentar"),
    ],
    "platina": [
        ("gg", "👏", "GG"), ("rare", "💎", "Raridade"),
        ("fire", "🔥", "Insano"), ("play", "🎮", "Quero jogar"),
    ],
    "zerado": [
        ("gg", "👏", "GG"), ("fire", "🔥", "Mandou bem"),
        ("grit", "💪", "Persistência"), ("play", "🎮", "Na minha lista"),
    ],
    "lore": [
        ("argument", "🧠", "Bem argumentada"), ("evidence", "🔎", "Boa evidência"),
        ("connection", "🧩", "Boa conexão"), ("interesting", "👀", "Interessante"),
    ],
    "theory": [
        ("argument", "🧠", "Bem argumentada"), ("evidence", "🔎", "Boa evidência"),
        ("connection", "🧩", "Boa conexão"), ("interesting", "👀", "Interessante"),
    ],
    "discovery": [
        ("discovery", "🔍", "Boa descoberta"), ("evidence", "📌", "Bem documentada"),
        ("connection", "🧩", "Boa conexão"), ("interesting", "✨", "Surpreendente"),
    ],
    "timeline": [
        ("clear", "🕰️", "Boa organização"), ("evidence", "🔎", "Bem fundamentada"),
        ("helpful", "📚", "Útil"), ("interesting", "✨", "Interessante"),
    ],
    "debate": [
        ("important", "💬", "Boa questão"), ("argument", "🧠", "Bom argumento"),
        ("different", "🧭", "Nova perspectiva"), ("interesting", "👀", "Quero discutir"),
    ],
    "guide": [
        ("useful", "✅", "Foi útil"), ("clear", "📘", "Bem explicado"),
        ("updated", "⚠️", "Precisa atualizar"), ("saved", "🔖", "Recomendado"),
    ],
    "tutorial": [
        ("useful", "✅", "Funcionou"), ("clear", "📘", "Bem explicado"),
        ("updated", "⚠️", "Precisa atualizar"), ("saved", "🔖", "Recomendado"),
    ],
    "challenge": [
        ("joined", "⚔️", "Quero participar"), ("fire", "🔥", "Bora"),
        ("hard", "💀", "Desafio brutal"), ("interesting", "👀", "Interessante"),
    ],
    "default": [
        ("useful", "✅", "Útil"), ("interesting", "💡", "Boa ideia"),
        ("support", "👏", "Apoio"), ("saved", "🔖", "Salvar"),
    ],
}

STATUS_PT = {
    "pending": "⏳ Aguardando análise", "changes_requested": "📝 Ajustes solicitados",
    "approved": "✅ Aprovada", "rejected": "❌ Rejeitada", "archived": "🗄️ Arquivada pela equipe",
}


def _tipo_social(target_type: str) -> str:
    if target_type.startswith("contrib_"):
        return target_type.removeprefix("contrib_")
    return target_type if target_type in REACTIONS else "default"


def _safe(text: str, limit: int = 1000) -> str:
    return discord.utils.escape_mentions(str(text or ""))[:limit]


def _parse_spoiler(raw: str) -> tuple[str, str]:
    spoiler = "none"
    match = re.search(r"\[SPOILER:\s*(nenhum|leve|avançado|final)\s*\]", raw or "", re.I)
    if match:
        spoiler = {"nenhum": "none", "leve": "light", "avançado": "advanced", "final": "final"}[match.group(1).lower()]
        raw = re.sub(r"\[SPOILER:.*?\]\s*", "", raw, count=1, flags=re.I).strip()
    return spoiler, raw


def _parse_challenge_mode(raw: str) -> tuple[str, int]:
    """Formato aceito: 'individual' ou 'coletivo: 15' (meta de conclusões)."""
    texto = str(raw or "").strip().lower()
    if not texto:
        return "individual", 0
    if "coletiv" not in texto:
        return "individual", 0
    match = re.search(r"(?:coletiv\w*\s*[:=-]?\s*|meta\s*[:=-]?\s*)(\d{1,3})", texto)
    if not match:
        return "collective", 0
    return "collective", max(0, min(int(match.group(1)), 500))


class ContributionModal(discord.ui.Modal):
    def __init__(self, cog: "Comunidade", kind: str, *, origin_sector: str = "community",
                 default_game: str = ""):
        label = TIPOS.get(kind, ("Contribuição", "", 0))[0]
        super().__init__(title=f"Enviar: {label}"[:45], timeout=300)
        self.cog, self.kind = cog, kind
        self.origin_sector = str(origin_sector or "community")[:40]
        self.default_game = str(default_game or "")[:80]
        game_label = (
            "Jogo (obrigatório para desafios)" if kind == "challenge" else
            "Plataforma ou contexto (opcional)" if kind == "game_suggestion" else
            "Jogo / universo (opcional)"
        )
        self.game = discord.ui.TextInput(
            label=game_label,
            placeholder="Ex.: Elden Ring", required=(kind == "challenge"), max_length=80,
            default=self.default_game or None,
        )
        title_label = ("Nome do jogo" if kind == "game_suggestion" else
                       "Nome do desafio" if kind == "challenge" else
                       "Pergunta" if kind == "faq" else "Título")
        self.title_input = discord.ui.TextInput(
            label=title_label, placeholder="Use um nome claro e identificável", required=True, max_length=90
        )
        summary_label = ("Por que incluir este jogo?" if kind == "game_suggestion" else
                         "Objetivo do desafio" if kind == "challenge" else
                         "Resposta curta" if kind == "faq" else "Resumo")
        self.summary = discord.ui.TextInput(
            label=summary_label, placeholder="Explique em poucas linhas o que está propondo", required=True,
            style=discord.TextStyle.paragraph, max_length=350
        )
        content_label = ("Regras do desafio" if kind == "challenge" else
                         "Resposta detalhada" if kind == "faq" else "Conteúdo / explicação")
        self.content = discord.ui.TextInput(
            label=content_label, placeholder="Desenvolva a ideia, passos, regras ou argumentos...",
            required=True, style=discord.TextStyle.paragraph, min_length=40, max_length=1500
        )
        self.sources = discord.ui.TextInput(
            label="Formato do desafio (opcional)" if kind == "challenge" else "Fontes, plataforma ou spoilers (opcional)",
            placeholder="Use 'individual' ou 'coletivo: 15' para meta de 15 conclusões" if kind == "challenge" else "Links/referências. Em lore, comece com [SPOILER: nenhum|leve|avançado|final]",
            required=False, style=discord.TextStyle.paragraph, max_length=700
        )
        for item in (self.game, self.title_input, self.summary, self.content, self.sources):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("Envie contribuições dentro do servidor NARA.", ephemeral=True)
        title = str(self.title_input.value).strip()
        content = str(self.content.value).strip()
        summary = str(self.summary.value).strip()
        game = str(self.game.value).strip()
        sources_raw = str(self.sources.value).strip()
        if len(title) < 4 or len(content) < 40:
            return await interaction.response.send_message("O título ou o conteúdo está curto demais. Revise e envie novamente.", ephemeral=True)
        challenge_mode, challenge_goal = _parse_challenge_mode(sources_raw) if self.kind == "challenge" else ("individual", 0)
        if self.kind == "challenge" and challenge_mode == "collective" and challenge_goal < 2:
            return await interaction.response.send_message(
                "Para um desafio coletivo, informe a meta no formato `coletivo: 15` (mínimo de 2 conclusões).",
                ephemeral=True,
            )
        if self.kind == "challenge":
            sources_raw = ""
            spoiler = "none"
        else:
            spoiler, sources_raw = _parse_spoiler(sources_raw)
        # Limita fila pessoal e frequência diária sem bloquear membros legítimos.
        pendentes = await self.cog.bot.db._one(
            "SELECT COUNT(*) AS n FROM community_contributions WHERE guild_id=? AND user_id=? AND status IN ('pending','changes_requested')",
            (interaction.guild_id, interaction.user.id),
        )
        if int(pendentes["n"] or 0) >= 5:
            return await interaction.response.send_message("Você já tem cinco propostas aguardando análise. Aguarde a equipe revisar alguma antes de enviar outra.", ephemeral=True)
        recentes = await self.cog.bot.db._one(
            "SELECT COUNT(*) AS n FROM community_contributions WHERE guild_id=? AND user_id=? AND created_at >= datetime('now','-1 day')",
            (interaction.guild_id, interaction.user.id),
        )
        if int(recentes["n"] or 0) >= 5:
            return await interaction.response.send_message("Você atingiu o limite de cinco contribuições por 24 horas. Isso protege a fila contra spam.", ephemeral=True)
        duplicada = await self.cog.bot.db._one(
            """SELECT id FROM community_contributions WHERE guild_id=? AND kind=? AND lower(title)=lower(?)
               AND lower(game_name)=lower(?) AND status IN ('pending','changes_requested','approved') LIMIT 1""",
            (interaction.guild_id, self.kind, title, game),
        )
        if duplicada:
            return await interaction.response.send_message(
                f"Já existe uma contribuição ativa com título e jogo semelhantes (`#{duplicada['id']}`). Use a opção de correção/complemento ou acrescente novas evidências.", ephemeral=True
            )
        await interaction.response.defer(ephemeral=True, thinking=True)
        contribution_id = await self.cog.bot.db.criar_contribuicao(
            guild_id=interaction.guild_id, user_id=interaction.user.id, kind=self.kind,
            game_name=game, title=title, summary=summary, content=content,
            sources=sources_raw, spoiler_level=spoiler,
            challenge_mode=challenge_mode, challenge_goal=challenge_goal,
            origin_sector=self.origin_sector, origin_channel_id=interaction.channel_id,
        )
        try:
            await self.cog.bot.db.log(interaction.user.id, "community_contribution_created", f"id={contribution_id} kind={self.kind}")
        except Exception:
            log.exception("Contribuição #%s salva, mas o log de auditoria falhou", contribution_id)
        try:
            mod_channel_id = await GuildConfig.get(self.cog.bot.db, interaction.guild_id, "mod_channel")
            mod_channel = await get_text_channel(self.cog.bot, mod_channel_id) if mod_channel_id else None
            if mod_channel:
                kind_label = TIPOS.get(self.kind, ("Contribuição", "", 0))[0]
                review_embed = discord.Embed(
                    title="📥 Nova contribuição aguardando aprovação",
                    description=(
                        f"**ID:** `#{contribution_id}`\n"
                        f"**Tipo:** {kind_label}\n"
                        f"**Título:** {discord.utils.escape_markdown(title)[:200]}\n"
                        f"**Jogo:** {discord.utils.escape_markdown(game)[:150] or 'Geral'}\n"
                        f"**Autor:** {interaction.user.mention} (`{interaction.user.id}`)"
                    ),
                    color=config.COR_OURO,
                )
                review_embed.set_footer(text="Abra a fila de contribuições da Comunidade para analisar.")
                await mod_channel.send(embed=review_embed, allowed_mentions=discord.AllowedMentions.none())
            else:
                log.error("Contribuição #%s salva, mas canal central de moderação não está configurado/acessível.", contribution_id)
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Contribuição #%s salva, mas falhou o aviso no canal central de moderação.", contribution_id)
        await interaction.followup.send(
            f"📨 Sua contribuição **#{contribution_id} — {discord.utils.escape_markdown(title)}** foi enviada para análise.\n"
            "Ela só será publicada e recompensada depois da aprovação da equipe. Você pode acompanhar o andamento abaixo, sem sair do assunto em que estava.",
            view=CommunitySubmissionReceiptView(
                self.cog, self.kind, self.origin_sector, self.default_game, interaction.user.id
            ),
            ephemeral=True,
        )


class CommunitySubmissionReceiptView(discord.ui.View):
    """Pós-envio contextual: permite acompanhar o status ou enviar outra proposta semelhante."""

    def __init__(self, cog: "Comunidade", kind: str, origin_sector: str,
                 default_game: str, owner_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.kind = str(kind)
        self.origin_sector = str(origin_sector)
        self.default_game = str(default_game or "")
        self.owner_id = int(owner_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Este acompanhamento pertence a quem enviou a contribuição.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Acompanhar minha contribuição", emoji="🗂️", style=discord.ButtonStyle.primary, row=0)
    async def acompanhar(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await self.cog.bot.db.listar_contribuicoes(
            guild_id=interaction.guild_id, user_id=interaction.user.id, limit=10
        )
        embed = discord.Embed(title="🗂️ Minhas contribuições", color=config.COR_OURO)
        if rows:
            lines = []
            for row in rows:
                label = TIPOS.get(row["kind"], ("Contribuição", "", 0))[0]
                lines.append(
                    f"`#{row['id']}` **{discord.utils.escape_markdown(row['title'])}**\n"
                    f"{label} · {STATUS_PT.get(row['status'], row['status'])} · {str(row['created_at'])[:16]}"
                )
                if row["status"] == "changes_requested" and row["review_note"]:
                    lines.append(f"> Orientação: {discord.utils.escape_markdown(row['review_note'][:250])}")
            embed.description = "\n\n".join(lines)[:4000]
        else:
            embed.description = "Você ainda não enviou contribuições."
        embed.set_footer(text="O XP é creditado somente após aprovação. Use o seletor para responder a pedidos de ajuste.")
        await interaction.response.edit_message(embed=embed, content=None, view=CommunityMyContributionsView(self.cog, rows))

    @discord.ui.button(label="Enviar outra neste setor", emoji="➕", style=discord.ButtonStyle.success, row=0)
    async def enviar_outra(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            ContributionModal(
                self.cog, self.kind, origin_sector=self.origin_sector, default_game=self.default_game
            )
        )


class ContributionEditModal(discord.ui.Modal):
    def __init__(self, cog: "Comunidade", row):
        kind = str(row["kind"])
        super().__init__(title=f"Revisar contribuição #{row['id']}"[:45], timeout=300)
        self.cog, self.contribution_id, self.kind = cog, int(row["id"]), kind
        self.game = discord.ui.TextInput(
            label="Jogo / universo", default=str(row["game_name"] or "")[:80],
            required=(kind == "challenge"), max_length=80
        )
        title_label = "Nome do jogo" if kind == "game_suggestion" else "Nome do desafio" if kind == "challenge" else "Título"
        self.title_input = discord.ui.TextInput(label=title_label, default=str(row["title"])[:90], max_length=90)
        self.summary = discord.ui.TextInput(
            label="Resumo / justificativa", default=str(row["summary"] or "")[:350],
            style=discord.TextStyle.paragraph, max_length=350
        )
        self.content = discord.ui.TextInput(
            label="Conteúdo / regras", default=str(row["content"])[:1500],
            style=discord.TextStyle.paragraph, min_length=40, max_length=1500
        )
        default_sources = (
            f"coletivo: {int(row['challenge_goal'] or 0)}" if kind == "challenge" and row["challenge_mode"] == "collective"
            else "individual" if kind == "challenge" else str(row["sources"] or "")[:700]
        )
        self.sources = discord.ui.TextInput(
            label="Formato do desafio" if kind == "challenge" else "Fontes e spoilers (opcional)",
            default=default_sources[:700], style=discord.TextStyle.paragraph, required=False, max_length=700
        )
        for item in (self.game, self.title_input, self.summary, self.content, self.sources):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        raw_sources = str(self.sources.value).strip()
        challenge_mode, challenge_goal = _parse_challenge_mode(raw_sources) if self.kind == "challenge" else ("individual", 0)
        if self.kind == "challenge" and challenge_mode == "collective" and challenge_goal < 2:
            return await interaction.response.send_message("Informe a meta coletiva no formato `coletivo: 15` (mínimo de 2).", ephemeral=True)
        if self.kind == "challenge":
            spoiler, sources = "none", ""
        else:
            spoiler, sources = _parse_spoiler(raw_sources)
        updated = await self.cog.bot.db.editar_contribuicao(
            self.contribution_id, interaction.user.id, game_name=str(self.game.value).strip(),
            title=str(self.title_input.value).strip(), summary=str(self.summary.value).strip(),
            content=str(self.content.value).strip(), sources=sources, spoiler_level=spoiler,
            challenge_mode=challenge_mode, challenge_goal=challenge_goal,
        )
        if not updated:
            return await interaction.response.send_message(
                "Esta contribuição não está mais aguardando ajustes ou não pertence a você.", ephemeral=True
            )
        try:
            await self.cog.bot.db.log(interaction.user.id, "community_contribution_resubmitted", f"id={self.contribution_id}")
        except Exception:
            log.exception("Contribuição #%s reenviada, mas falhou o log de auditoria", self.contribution_id)
        await interaction.response.send_message(
            f"✅ Sua contribuição `#{self.contribution_id}` foi atualizada e voltou para a fila de aprovação.", ephemeral=True
        )


class CommunityContextContributionButton(discord.ui.Button):
    """Botão contextual: abre o formulário correto sem tirar o membro do setor atual."""

    def __init__(self, kind: str, origin_sector: str, label: str, emoji: str, *, row: int = 0,
                 default_game: str = "", style: discord.ButtonStyle = discord.ButtonStyle.secondary):
        custom_id = f"community:ctx:{origin_sector}:{kind}"[:100]
        super().__init__(label=label[:80], emoji=emoji, style=style, row=row, custom_id=custom_id)
        self.kind = str(kind)
        self.origin_sector = str(origin_sector)
        self.default_game = str(default_game or "")[:80]

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Comunidade")
        if cog is None:
            return await interaction.response.send_message(
                "O envio de contribuições está temporariamente indisponível. Tente novamente ou avise a equipe.",
                ephemeral=True,
            )
        await interaction.response.send_modal(
            ContributionModal(cog, self.kind, origin_sector=self.origin_sector, default_game=self.default_game)
        )


def adicionar_botao_contribuicao_contextual(
    view: discord.ui.View, kind: str, origin_sector: str, label: str, emoji: str, *,
    row: int = 0, default_game: str = "", style: discord.ButtonStyle = discord.ButtonStyle.secondary,
) -> CommunityContextContributionButton:
    """Anexa uma ação contextual a qualquer painel sem replicar lógica de submissão."""
    button = CommunityContextContributionButton(
        kind, origin_sector, label, emoji, row=row, default_game=default_game, style=style
    )
    view.add_item(button)
    return button


class ContributionCategoryView(discord.ui.View):
    def __init__(self, cog: "Comunidade", category: str, callback_voltar=None):
        super().__init__(timeout=180)
        self.cog, self.category = cog, category
        self.callback_voltar = callback_voltar
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")
        choices = {
            "lore": [("lore", "Lore", "📜"), ("theory", "Teoria", "🔍"), ("discovery", "Descoberta", "🧩"), ("timeline", "Cronologia", "🕰️"), ("debate", "Questão para debate", "💬")],
            "guide": [("guide", "Guia", "📘"), ("tutorial", "Tutorial", "🛠️"), ("faq", "Pergunta para FAQ", "❔")],
            "runs": [("challenge", "Propor desafio", "⚔️"), ("game_suggestion", "Sugerir jogo para Runs", "🎮")],
            "other": [("correction", "Correção / complemento", "🧹"), ("idea", "Ideia para o NARA", "💡"), ("item_suggestion", "Sugerir item para Loja", "🪙")],
        }
        for index, (kind, label, emoji) in enumerate(choices.get(category, choices["other"])):
            button = discord.ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.primary, row=index // 3)
            async def callback(interaction: discord.Interaction, selected=kind):
                await interaction.response.send_modal(ContributionModal(self.cog, selected))
            button.callback = callback
            self.add_item(button)


class ContributionTypeSelect(discord.ui.Select):
    def __init__(self, cog: "Comunidade", callback_voltar=None):
        self.cog = cog
        self.callback_voltar = callback_voltar
        options = [
            discord.SelectOption(label="Lore e teorias", value="lore", emoji="📜"),
            discord.SelectOption(label="Guias e tutoriais", value="guide", emoji="📘"),
            discord.SelectOption(label="Runs e desafios", value="runs", emoji="⚔️"),
            discord.SelectOption(label="Correções e ideias", value="other", emoji="💡"),
        ]
        super().__init__(placeholder="Escolha o tipo de contribuição", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        descriptions = {
            "lore": "O Arquivo de Mundos separa lore documentada, teorias, descobertas, cronologias e debates.",
            "guide": "Guias, tutoriais e sugestões para a Central de Ajuda devem ser claros, verificáveis e úteis.",
            "runs": "Sugira um desafio ou um jogo para a Central Soulslike. A equipe revisará regras e compatibilidade.",
            "other": "Envie correções para conteúdos existentes ou ideias de melhoria para a comunidade.",
        }
        await interaction.response.edit_message(
            embed=discord.Embed(title="✍️ Nova contribuição", description=descriptions[category], color=config.COR_OURO),
            view=ContributionCategoryView(self.cog, category, callback_voltar=self.callback_voltar),
        )


class CommunityGuidesView(discord.ui.View):
    """Painel persistente da Biblioteca de Guias e Tutoriais."""

    def __init__(self, cog: "Comunidade", *, persistent: bool = False):
        super().__init__(timeout=None if persistent else 300)
        self.cog = cog
        adicionar_botao_contribuicao_contextual(
            self, "guide", "guias", "Enviar guia", "📘", row=0, style=discord.ButtonStyle.primary
        )
        adicionar_botao_contribuicao_contextual(
            self, "tutorial", "guias", "Enviar tutorial", "🛠️", row=0, style=discord.ButtonStyle.primary
        )
        adicionar_botao_contribuicao_contextual(
            self, "faq", "guias", "Sugerir pergunta", "❔", row=0, style=discord.ButtonStyle.success
        )
        arquivo = discord.ui.Button(
            label="Consultar biblioteca", emoji="📚", style=discord.ButtonStyle.secondary,
            row=1, custom_id="community:guides:archive",
        )
        async def _arquivo(interaction: discord.Interaction):
            await self.cog.mostrar_arquivo(interaction, origin_sector="guias")
        arquivo.callback = _arquivo
        self.add_item(arquivo)
        minhas = discord.ui.Button(
            label="Minhas contribuições", emoji="🗂️", style=discord.ButtonStyle.secondary,
            row=1, custom_id="community:guides:mine",
        )
        async def _minhas(interaction: discord.Interaction):
            # Este painel é persistente e publicado em canal público; não possui
            # callback efêmero de retorno à Nara.
            await self.cog.mostrar_minhas(interaction)
        minhas.callback = _minhas
        self.add_item(minhas)


class CommunityHomeView(discord.ui.View):
    def __init__(self, cog: "Comunidade", *, persistent: bool = False, callback_voltar=None):
        super().__init__(timeout=None if persistent else 300)
        self.cog = cog
        self.persistent = persistent
        self.callback_voltar = callback_voltar
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")
        # Como este painel fica no canal de Lore, as ações mais usadas são diretas.
        for kind, label, emoji in (
            ("lore", "Publicar lore", "📜"), ("theory", "Publicar teoria", "🔍"),
            ("discovery", "Registrar descoberta", "🧩"),
            ("timeline", "Criar cronologia", "🕰️"), ("debate", "Abrir debate", "💬"),
        ):
            adicionar_botao_contribuicao_contextual(self, kind, "lore", label, emoji, row=2,
                                                     style=discord.ButtonStyle.primary)

    @discord.ui.button(label="Contribuir", emoji="✍️", style=discord.ButtonStyle.primary, custom_id="community:home:contribute", row=0)
    async def contribute(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💡 Contribuições da Comunidade",
            description="Escolha uma área. Suas propostas serão revisadas pela equipe antes de entrar nos canais e sistemas oficiais.",
            color=config.COR_OURO,
        )
        if self.callback_voltar is not None:
            await interaction.response.edit_message(embed=embed, view=ContributionCategoryLauncher(self.cog, self.callback_voltar))
        else:
            await interaction.response.send_message(embed=embed, view=ContributionCategoryLauncher(self.cog), ephemeral=True)

    @discord.ui.button(label="Explorar Arquivo", emoji="📚", style=discord.ButtonStyle.secondary, custom_id="community:home:archive", row=0)
    async def archive(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.mostrar_arquivo(interaction, callback_voltar=self.callback_voltar)

    @discord.ui.button(label="Minhas contribuições", emoji="🗂️", style=discord.ButtonStyle.secondary, custom_id="community:home:mine", row=0)
    async def mine(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.mostrar_minhas(interaction, callback_voltar=self.callback_voltar)

    @discord.ui.button(label="Favoritos", emoji="🔖", style=discord.ButtonStyle.secondary, custom_id="community:home:saved", row=1)
    async def saved(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.mostrar_favoritos(interaction, callback_voltar=self.callback_voltar)

    @discord.ui.button(label="Mural de atividades", emoji="📡", style=discord.ButtonStyle.secondary, custom_id="community:home:activity", row=1)
    async def activity(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.mostrar_atividades(interaction, callback_voltar=self.callback_voltar)

    @discord.ui.button(label="Notificações", emoji="🔔", style=discord.ButtonStyle.secondary, custom_id="community:home:preferences", row=1)
    async def preferences(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.mostrar_preferencias(interaction, callback_voltar=self.callback_voltar)


class ContributionCategoryLauncher(discord.ui.View):
    def __init__(self, cog: "Comunidade", callback_voltar=None):
        super().__init__(timeout=180)
        self.callback_voltar = callback_voltar
        self.add_item(ContributionTypeSelect(cog, callback_voltar=callback_voltar))
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")


class CommunityMyContributionsSelect(discord.ui.Select):
    def __init__(self, cog: "Comunidade", rows, callback_voltar=None):
        self.cog = cog
        self.callback_voltar = callback_voltar
        options = []
        for row in rows[:25]:
            label = discord.utils.escape_markdown(str(row["title"]))[:75]
            status = STATUS_PT.get(row["status"], row["status"])
            options.append(discord.SelectOption(
                label=f"#{row['id']} · {label}", value=str(row["id"]),
                description=f"{status} · {TIPOS.get(row['kind'], ('Contribuição','',''))[0]}"[:100],
            ))
        if not options:
            options = [discord.SelectOption(label="Nenhuma contribuição enviada", value="0")]
        super().__init__(placeholder="Selecione uma contribuição para ver opções",
                         min_values=1, max_values=1, options=options, disabled=not rows)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "0":
            return await interaction.response.send_message("Você ainda não tem contribuições.", ephemeral=True)
        row = await self.cog.bot.db.get_contribuicao(int(self.values[0]))
        if not row or int(row["user_id"]) != interaction.user.id or int(row["guild_id"]) != interaction.guild_id:
            return await interaction.response.send_message("Esta contribuição não pertence a você ou não está disponível.", ephemeral=True)
        if row["status"] == "changes_requested":
            return await interaction.response.send_modal(ContributionEditModal(self.cog, row))
        if row["status"] == "approved" and row["published_channel_id"] and row["published_message_id"]:
            url = f"https://discord.com/channels/{interaction.guild_id}/{row['published_channel_id']}/{row['published_message_id']}"
            texto = f"✅ Publicação aprovada: [abrir no Discord]({url})"
        else:
            texto = (
                f"Status atual: **{STATUS_PT.get(row['status'], row['status'])}**. "
                "Você receberá uma mensagem privada quando a equipe tomar uma decisão."
            )
        if self.callback_voltar is not None:
            await _responder_painel_membro(
                interaction, callback_voltar=self.callback_voltar, content=texto,
                view=CommunityMyContributionsView(self.cog, [row], self.callback_voltar),
            )
        else:
            await interaction.response.send_message(texto, ephemeral=True)


class CommunityMyContributionsView(discord.ui.View):
    def __init__(self, cog: "Comunidade", rows, callback_voltar=None):
        super().__init__(timeout=300)
        self.callback_voltar = callback_voltar
        self.add_item(CommunityMyContributionsSelect(cog, rows, callback_voltar))
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")


class CommunityArchiveSelect(discord.ui.Select):
    def __init__(self, cog: "Comunidade", rows):
        self.cog = cog
        options = []
        for row in rows[:25]:
            kind_label = TIPOS.get(row["kind"], ("Contribuição", "", 0))[0]
            options.append(discord.SelectOption(
                label=f"#{row['id']} · {str(row['title'])[:75]}",
                value=str(row["id"]),
                description=f"{kind_label} · {row['game_name'] or 'Comunidade'}"[:100],
            ))
        if not options:
            options = [discord.SelectOption(label="Nenhuma publicação encontrada", value="0")]
        super().__init__(placeholder="Selecione uma publicação para ler", min_values=1, max_values=1, options=options, disabled=not rows)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "0":
            return await interaction.response.edit_message(
                content="Ainda não há publicações aprovadas. Use as ações desta tela para enviar a primeira contribuição.",
                embed=None, view=self.view,
            )
        row = await self.cog.bot.db.get_contribuicao(int(self.values[0]))
        if not row or row["status"] != "approved":
            return await interaction.response.edit_message(
                content="Esta publicação não está mais disponível. Atualize o arquivo ou envie uma nova contribuição pelos botões abaixo.",
                embed=None, view=self.view,
            )
        await self.cog.mostrar_publicacao(interaction, row, callback_voltar=getattr(self.view, "callback_voltar", None))


class CommunityArchiveView(discord.ui.View):
    """Arquivo com ações de criação alinhadas ao assunto de origem."""
    def __init__(self, cog: "Comunidade", rows, origin_sector: str = "lore", callback_voltar=None):
        super().__init__(timeout=300)
        self.callback_voltar = callback_voltar
        self.add_item(CommunityArchiveSelect(cog, rows))
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")
        if origin_sector == "guias":
            for kind, label, emoji in (
                ("guide", "Enviar guia", "📘"), ("tutorial", "Enviar tutorial", "🛠️"),
                ("faq", "Sugerir pergunta", "❔"),
            ):
                adicionar_botao_contribuicao_contextual(
                    self, kind, "guias", label, emoji, row=1,
                    style=discord.ButtonStyle.success if kind == "faq" else discord.ButtonStyle.primary,
                )
        else:
            for kind, label, emoji in (
                ("lore", "Publicar lore", "📜"), ("theory", "Publicar teoria", "🔍"),
                ("discovery", "Registrar descoberta", "🧩"), ("timeline", "Criar cronologia", "🕰️"),
                ("debate", "Abrir debate", "💬"),
            ):
                adicionar_botao_contribuicao_contextual(
                    self, kind, "lore", label, emoji, row=1, style=discord.ButtonStyle.primary,
                )


class CommunityReviewView(discord.ui.View):
    def __init__(self, cog: "Comunidade", contribution_id: int):
        super().__init__(timeout=600)
        self.cog, self.contribution_id = cog, int(contribution_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, self.cog.bot.db):
            await interaction.response.send_message("Apenas a equipe autorizada pode decidir contribuições.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aprovar e publicar", emoji="✅", style=discord.ButtonStyle.success, row=0)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        row = await self.cog.bot.db.get_contribuicao(self.contribution_id)
        if row is None or row["status"] not in ("pending", "changes_requested"):
            return await interaction.response.send_message("Esta contribuição já foi processada.", ephemeral=True)
        await interaction.response.send_modal(ContributionApprovalModal(self.cog, self.contribution_id, row))

    @discord.ui.button(label="Solicitar ajustes", emoji="📝", style=discord.ButtonStyle.primary, row=0)
    async def changes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ContributionDecisionModal(self.cog, self.contribution_id, "changes_requested"))

    @discord.ui.button(label="Rejeitar", emoji="❌", style=discord.ButtonStyle.danger, row=0)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ContributionDecisionModal(self.cog, self.contribution_id, "rejected"))


class CommunityPublishRetryView(discord.ui.View):
    def __init__(self, cog: "Comunidade", contribution_id: int):
        super().__init__(timeout=600)
        self.cog, self.contribution_id = cog, int(contribution_id)

    @discord.ui.button(label="Tentar publicar novamente", emoji="🔁", style=discord.ButtonStyle.primary)
    async def retry(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.republicar(interaction, self.contribution_id)


class ContributionApprovalModal(discord.ui.Modal):
    def __init__(self, cog: "Comunidade", contribution_id: int, row):
        super().__init__(title=f"Aprovar contribuição #{contribution_id}"[:45], timeout=180)
        self.cog, self.contribution_id = cog, int(contribution_id)
        suggested = TIPOS.get(str(row["kind"]), ("", "", config.COMMUNITY_XP_DEFAULT))[2]
        self.xp = discord.ui.TextInput(
            label="XP desta aprovação (opcional)", placeholder=f"Padrão: {suggested}; informe 0 para não conceder XP",
            required=False, max_length=4
        )
        self.add_item(self.xp)

    async def on_submit(self, interaction: discord.Interaction):
        raw = str(self.xp.value).strip()
        override = None
        if raw:
            try:
                override = int(raw)
            except ValueError:
                return await interaction.response.send_message("Informe um número inteiro de XP ou deixe o campo vazio.", ephemeral=True)
            if override < 0 or override > 1000:
                return await interaction.response.send_message("O XP manual deve ficar entre 0 e 1000.", ephemeral=True)
        await self.cog.decidir(interaction, self.contribution_id, "approved", xp_override=override)


class ContributionDecisionModal(discord.ui.Modal):
    def __init__(self, cog: "Comunidade", contribution_id: int, status: str):
        super().__init__(title="Solicitar ajustes" if status == "changes_requested" else "Rejeitar contribuição", timeout=180)
        self.cog, self.contribution_id, self.status = cog, int(contribution_id), status
        self.note = discord.ui.TextInput(
            label="Orientação para o autor", style=discord.TextStyle.paragraph,
            min_length=5, max_length=700, required=True,
            placeholder="Explique o que precisa ser corrigido ou por que foi rejeitada.",
        )
        self.add_item(self.note)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.decidir(interaction, self.contribution_id, self.status, str(self.note.value))


class CommunityReactionButton(discord.ui.Button):
    def __init__(self, cog: "Comunidade", target_type: str, target_id: int,
                 reaction_key: str, emoji: str, label: str, count: int):
        custom_id = f"cm:r:{target_type}:{int(target_id)}:{reaction_key}"
        super().__init__(label=str(count), emoji=emoji, style=discord.ButtonStyle.secondary,
                         custom_id=custom_id[:100], row=0)
        self.cog, self.target_type, self.target_id = cog, target_type, int(target_id)
        self.reaction_key, self.reaction_label = reaction_key, label

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild_id is None:
            return await interaction.response.send_message("Esta interação só funciona no servidor.", ephemeral=True)
        owner_id = await self.cog.autor_alvo(self.target_type, self.target_id)
        if owner_id == interaction.user.id:
            return await interaction.response.send_message("Você não pode reagir à própria publicação.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=False)
        added = await self.cog.bot.db.alternar_interacao(
            interaction.guild_id, self.target_type, self.target_id, interaction.user.id, self.reaction_key
        )
        if interaction.message:
            await interaction.message.edit(view=await self.cog.criar_view_social(self.target_type, self.target_id))
        await interaction.followup.send(
            f"{self.emoji} {self.reaction_label}: {'registrado' if added else 'removido'}.", ephemeral=True
        )


class CommunityThreadButton(discord.ui.Button):
    def __init__(self, cog: "Comunidade", target_type: str, target_id: int):
        super().__init__(label="Discutir", emoji="💬", style=discord.ButtonStyle.primary,
                         custom_id=f"cm:t:{target_type}:{int(target_id)}"[:100], row=1)
        self.cog, self.target_type, self.target_id = cog, target_type, int(target_id)

    async def callback(self, interaction: discord.Interaction):
        if not interaction.message or not interaction.guild:
            return await interaction.response.send_message("Não consegui localizar a publicação original.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        post = await self.cog.bot.db.get_post_comunitario(interaction.guild_id, self.target_type, self.target_id)
        thread = None
        if post and post["thread_id"]:
            thread = interaction.guild.get_thread(int(post["thread_id"]))
            if thread is None:
                try:
                    thread = await interaction.guild.fetch_channel(int(post["thread_id"]))
                except discord.HTTPException:
                    thread = None
        if thread is None:
            thread = getattr(interaction.message, "thread", None)
        if thread is None:
            try:
                thread = await interaction.message.create_thread(
                    name=f"Discussão · {self.target_type} #{self.target_id}"[:100],
                    auto_archive_duration=10080,
                    reason="Discussão vinculada a publicação comunitária do NARA",
                )
                await self.cog.bot.db.definir_thread_comunitaria(
                    interaction.guild_id, self.target_type, self.target_id, thread.id
                )
                try:
                    await thread.send("💬 Discussão aberta. Mantenha o debate respeitoso e relacionado à publicação.")
                except discord.HTTPException:
                    pass
            except discord.Forbidden:
                return await interaction.followup.send("Não tenho permissão para criar threads neste canal. Peça à equipe para habilitar **Criar Threads Públicas**.", ephemeral=True)
            except discord.HTTPException:
                log.exception("Falha ao criar thread para %s #%s", self.target_type, self.target_id)
                return await interaction.followup.send("Não consegui abrir a discussão. Tente novamente mais tarde.", ephemeral=True)
        await interaction.followup.send(f"💬 Discussão disponível: {thread.mention}", ephemeral=True)


class CommunityBookmarkButton(discord.ui.Button):
    def __init__(self, cog: "Comunidade", target_type: str, target_id: int):
        super().__init__(label="Salvar", emoji="🔖", style=discord.ButtonStyle.secondary,
                         custom_id=f"cm:b:{target_type}:{int(target_id)}"[:100], row=1)
        self.cog, self.target_type, self.target_id = cog, target_type, int(target_id)

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild_id is None:
            return await interaction.response.send_message("Use esta função dentro do servidor.", ephemeral=True)
        saved = await self.cog.bot.db.alternar_favorito(
            interaction.guild_id, interaction.user.id, self.target_type, self.target_id
        )
        await interaction.response.send_message(
            "🔖 Conteúdo salvo nos seus favoritos." if saved else "O conteúdo foi removido dos seus favoritos.", ephemeral=True
        )


class CommunityFollowButton(discord.ui.Button):
    def __init__(self, cog: "Comunidade", owner_id: int):
        super().__init__(label="Acompanhar autor", emoji="⭐", style=discord.ButtonStyle.secondary,
                         custom_id=f"cm:f:{int(owner_id)}"[:100], row=1)
        self.cog, self.owner_id = cog, int(owner_id)

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild_id or interaction.user.id == self.owner_id:
            return await interaction.response.send_message("Não é possível acompanhar sua própria conta.", ephemeral=True)
        followed = await self.cog.bot.db.alternar_seguir(interaction.guild_id, interaction.user.id, self.owner_id)
        await interaction.response.send_message(
            f"{'⭐ Você agora acompanha' if followed else 'Você deixou de acompanhar'} <@{self.owner_id}>. "
            "As atualizações serão enviadas por mensagem direta quando possível.", ephemeral=True
        )


class CommunityHonorSelect(discord.ui.Select):
    def __init__(self, cog: "Comunidade", target_user_id: int):
        self.cog, self.target_user_id = cog, int(target_user_id)
        super().__init__(
            placeholder="Escolha uma honra para este gladiador",
            min_values=1, max_values=1,
            options=[
                discord.SelectOption(label="Respeito", value="respect", emoji="🛡️", description="Pela dedicação e postura"),
                discord.SelectOption(label="Determinação", value="determination", emoji="🔥", description="Pela persistência e esforço"),
                discord.SelectOption(label="Grandeza", value="greatness", emoji="👑", description="Por uma conquista marcante"),
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild_id or interaction.user.id == self.target_user_id:
            return await interaction.response.send_message("Você não pode conceder honra a si mesmo.", ephemeral=True)
        from datetime import datetime
        week_key = datetime.now(config.BRAZIL_TZ).strftime("%G-W%V")
        try:
            result = await self.cog.bot.db.registrar_honra(
                interaction.guild_id, interaction.user.id, self.target_user_id, self.values[0], week_key
            )
        except ValueError as exc:
            return await interaction.response.send_message(str(exc), ephemeral=True)
        labels = {"respect": "🛡️ Respeito", "determination": "🔥 Determinação", "greatness": "👑 Grandeza"}
        if result == "already":
            return await interaction.response.send_message("Você já concedeu essa honra nesta semana.", ephemeral=True)
        await interaction.response.send_message(
            f"{labels[self.values[0]]} {'concedido' if result == 'created' else 'atualizado'} para <@{self.target_user_id}>.", ephemeral=True
        )
        try:
            member = interaction.guild.get_member(self.target_user_id)
            user = member or self.cog.bot.get_user(self.target_user_id) or await self.cog.bot.fetch_user(self.target_user_id)
            await user.send(f"🏛️ Você recebeu **{labels[self.values[0]]}** de <@{interaction.user.id}> no Coliseu do NARA.")
        except (discord.Forbidden, discord.HTTPException):
            pass


class CommunityHonorButton(discord.ui.Button):
    def __init__(self, cog: "Comunidade", owner_id: int):
        super().__init__(label="Conceder honra", emoji="🏅", style=discord.ButtonStyle.secondary,
                         custom_id=f"cm:h:{int(owner_id)}"[:100], row=1)
        self.cog, self.owner_id = cog, int(owner_id)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.owner_id:
            return await interaction.response.send_message("Você não pode honrar a si mesmo.", ephemeral=True)
        view = discord.ui.View(timeout=180)
        view.add_item(CommunityHonorSelect(self.cog, self.owner_id))
        await interaction.response.send_message("🏅 Reconheça o percurso deste gladiador. Você pode conceder uma honra por semana; pode alterá-la até o fim da semana.", view=view, ephemeral=True)


class CommunityJoinChallengeButton(discord.ui.Button):
    def __init__(self, cog: "Comunidade", contribution_id: int, count: int):
        super().__init__(label=f"Participar · {count}", emoji="⚔️", style=discord.ButtonStyle.success,
                         custom_id=f"cm:j:{int(contribution_id)}"[:100], row=1)
        self.cog, self.contribution_id = cog, int(contribution_id)

    async def callback(self, interaction: discord.Interaction):
        row = await self.cog.bot.db.get_contribuicao(self.contribution_id)
        if not row or row["status"] != "approved" or row["kind"] != "challenge":
            return await interaction.response.send_message("Este desafio não está disponível.", ephemeral=True)
        try:
            joined = await self.cog.bot.db.alternar_participacao_desafio(
                interaction.guild_id, self.contribution_id, interaction.user.id
            )
        except ValueError as exc:
            return await interaction.response.send_message(str(exc), ephemeral=True)
        total = await self.cog.bot.db._one(
            "SELECT COUNT(*) AS n FROM community_challenge_participants WHERE guild_id=? AND contribution_id=?",
            (interaction.guild_id, self.contribution_id),
        )
        await interaction.response.send_message(
            f"{'⚔️ Inscrição confirmada' if joined else 'Inscrição cancelada'}. Participantes: {int(total['n'] or 0)}.", ephemeral=True
        )
        if interaction.message:
            await interaction.message.edit(view=await self.cog.criar_view_social(f"contrib_challenge", self.contribution_id))
        try:
            await self.cog.atualizar_resumo_desafio(interaction.guild_id, self.contribution_id)
        except Exception:
            log.exception("Não foi possível atualizar o resumo do desafio #%s após inscrição", self.contribution_id)
        desafio = await self.cog.bot.db.get_contribuicao(self.contribution_id)
        if joined and desafio and int(desafio["user_id"]) != interaction.user.id:
            from utils import notificar_usuario
            await notificar_usuario(
                self.cog.bot, interaction.guild_id, int(desafio["user_id"]), "challenges",
                f"⚔️ {interaction.user.display_name} entrou no seu desafio **{desafio['title']}**."
            )


class CommunityChallengeProgressModal(discord.ui.Modal):
    def __init__(self, cog: "Comunidade", contribution_id: int, status: str):
        super().__init__(title="Atualizar progresso" if status == "in_progress" else "Registrar conclusão", timeout=300)
        self.cog, self.contribution_id, self.status = cog, int(contribution_id), status
        self.progress = discord.ui.TextInput(
            label="Seu progresso", placeholder="Ex.: 4 de 7 chefes derrotados; falta apenas o último",
            style=discord.TextStyle.paragraph, min_length=8, max_length=700, required=True
        )
        self.evidence = discord.ui.TextInput(
            label="Comprovante ou link (opcional)", placeholder="Link de vídeo, imagem ou mensagem de prova",
            required=(status == "completed"), max_length=500
        )
        self.add_item(self.progress)
        self.add_item(self.evidence)

    async def on_submit(self, interaction: discord.Interaction):
        row = await self.cog.bot.db.get_contribuicao(self.contribution_id)
        if not row or row["status"] != "approved" or row["kind"] != "challenge":
            return await interaction.response.send_message("Este desafio não está disponível.", ephemeral=True)
        updated = await self.cog.bot.db.atualizar_progresso_desafio(
            interaction.guild_id, self.contribution_id, interaction.user.id, self.status,
            str(self.progress.value), str(self.evidence.value),
        )
        if not updated:
            return await interaction.response.send_message("Você precisa se inscrever no desafio antes de atualizar seu progresso.", ephemeral=True)
        await interaction.response.send_message(
            "🏁 Conclusão autodeclarada registrada com comprovante. A equipe pode verificar o resultado na discussão do desafio."
            if self.status == "completed" else "📈 Progresso atualizado. Continue sua jornada!", ephemeral=True
        )
        try:
            await self.cog.atualizar_resumo_desafio(interaction.guild_id, self.contribution_id)
        except Exception:
            log.exception("Não foi possível atualizar o resumo do desafio #%s após progresso", self.contribution_id)
        if int(row["user_id"]) != interaction.user.id:
            from utils import notificar_usuario
            evento = "concluiu" if self.status == "completed" else "atualizou o progresso de"
            await notificar_usuario(
                self.cog.bot, interaction.guild_id, int(row["user_id"]), "challenges",
                f"⚔️ {interaction.user.display_name} {evento} seu desafio **{row['title']}**."
            )


class CommunityChallengeProgressButton(discord.ui.Button):
    def __init__(self, cog: "Comunidade", contribution_id: int, status: str):
        label = "Marcar como concluído" if status == "completed" else "Atualizar progresso"
        emoji = "🏁" if status == "completed" else "📈"
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.primary if status == "completed" else discord.ButtonStyle.secondary,
                         custom_id=f"cm:jp:{int(contribution_id)}:{status}"[:100], row=3)
        self.cog, self.contribution_id, self.status = cog, int(contribution_id), status

    async def callback(self, interaction: discord.Interaction):
        row = await self.cog.bot.db._one(
            "SELECT status FROM community_challenge_participants WHERE guild_id=? AND contribution_id=? AND user_id=?",
            (interaction.guild_id, self.contribution_id, interaction.user.id),
        )
        if not row:
            return await interaction.response.send_message("Inscreva-se no desafio antes de atualizar seu progresso.", ephemeral=True)
        if row["status"] == "completed":
            return await interaction.response.send_message("Sua participação já está marcada como concluída.", ephemeral=True)
        await interaction.response.send_modal(CommunityChallengeProgressModal(self.cog, self.contribution_id, self.status))


class CommunityChallengeParticipantsButton(discord.ui.Button):
    def __init__(self, cog: "Comunidade", contribution_id: int):
        super().__init__(label="Participantes", emoji="👥", style=discord.ButtonStyle.secondary,
                         custom_id=f"cm:jlist:{int(contribution_id)}"[:100], row=2)
        self.cog, self.contribution_id = cog, int(contribution_id)

    async def callback(self, interaction: discord.Interaction):
        rows = await self.cog.bot.db.listar_participantes_desafio(
            interaction.guild_id, self.contribution_id, 25
        )
        if not rows:
            return await interaction.response.send_message("Ainda não há participantes inscritos neste desafio.", ephemeral=True)
        labels = {"joined": "Inscrito", "in_progress": "Em andamento", "completed": "Concluído"}
        lines = []
        for row in rows:
            note = discord.utils.escape_mentions(str(row["progress_note"] or ""))
            suffix = f" — {note[:110]}" if note else ""
            evidence = str(row["evidence"] or "").strip()
            if evidence:
                suffix += " · comprovante enviado"
            lines.append(f"• <@{int(row['user_id'])}> — **{labels.get(str(row['status']), 'Inscrito')}**{suffix}")
        embed = discord.Embed(
            title="👥 Participantes do desafio",
            description="\n".join(lines)[:4000],
            color=config.COR_OURO,
        )
        totals = await self.cog.bot.db.contar_participantes_desafio(interaction.guild_id, self.contribution_id)
        contribution = await self.cog.bot.db.get_contribuicao(self.contribution_id)
        total = sum(totals.values())
        completed = int(totals.get("completed", 0))
        if contribution and contribution["challenge_mode"] == "collective":
            goal = int(contribution["challenge_goal"] or 0)
            embed.add_field(name="Meta coletiva", value=f"**{completed}/{goal}** conclusões registradas", inline=False)
            embed.set_footer(text=f"{total} inscritos · progresso autodeclarado pelos participantes · mostrando até 25")
        else:
            embed.set_footer(text=f"{total} inscritos · {completed} concluídos (autodeclarados) · mostrando até 25")
        await interaction.response.send_message(embed=embed, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


class CommunityReportModal(discord.ui.Modal):
    def __init__(self, cog: "Comunidade", target_type: str, target_id: int):
        super().__init__(title="Sinalizar publicação", timeout=300)
        self.cog, self.target_type, self.target_id = cog, str(target_type), int(target_id)
        self.reason = discord.ui.TextInput(
            label="Motivo da sinalização", placeholder="Ex.: spam, assédio, conteúdo enganoso, spoiler sem aviso",
            required=True, max_length=90,
        )
        self.details = discord.ui.TextInput(
            label="Explique o problema", placeholder="Descreva o que a equipe deve verificar.",
            style=discord.TextStyle.paragraph, required=True, min_length=12, max_length=700,
        )
        self.add_item(self.reason)
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild_id is None:
            return await interaction.response.send_message("Sinalizações só podem ser enviadas dentro do servidor.", ephemeral=True)
        post = await self.cog.bot.db.get_post_comunitario(
            interaction.guild_id, self.target_type, self.target_id
        )
        if post is None or bool(post["is_hidden"]):
            return await interaction.response.send_message("Esta publicação não está mais disponível para sinalização.", ephemeral=True)
        owner_id = await self.cog.autor_alvo(self.target_type, self.target_id)
        if owner_id == interaction.user.id:
            return await interaction.response.send_message("Você não pode sinalizar sua própria publicação.", ephemeral=True)
        report_id = await self.cog.bot.db.criar_denuncia_comunitaria(
            interaction.guild_id, interaction.user.id, self.target_type, self.target_id,
            str(self.reason.value).strip(), str(self.details.value).strip(),
        )
        if report_id is None:
            return await interaction.response.send_message(
                "Você já tem uma sinalização pendente para esta publicação. A equipe poderá analisar a existente.", ephemeral=True
            )
        try:
            await self.cog.bot.db.log(
                interaction.user.id, "community_report_created",
                f"report={report_id} target={self.target_type}:{self.target_id}",
            )
        except Exception:
            log.exception("Denúncia #%s criada, mas o log de auditoria falhou", report_id)
        # Toda denúncia também precisa gerar um aviso no canal configurado em /adm.
        try:
            mod_channel_id = await GuildConfig.get(self.cog.bot.db, interaction.guild_id, "mod_channel")
            mod_channel = await get_text_channel(self.cog.bot, mod_channel_id) if mod_channel_id else None
            if mod_channel is None:
                log.error("Denúncia #%s salva, mas o canal central de moderação está ausente/inacessível.", report_id)
            else:
                report_embed = discord.Embed(
                    title="🚩 NOVA DENÚNCIA — aguardando análise",
                    description=(
                        f"**Denúncia:** `#{report_id}`\\n"
                        f"**Conteúdo:** `{self.target_type}:{self.target_id}`\\n"
                        f"**Motivo:** {discord.utils.escape_markdown(str(self.reason.value).strip())}\\n"
                        f"**Detalhes:** {discord.utils.escape_markdown(str(self.details.value).strip())}\\n"
                        "**Denunciante:** identidade privada — visível apenas nos controles de moderação."
                    ),
                    color=config.COR_PRATA,
                )
                report_embed.set_footer(text="Abra a Central de Moderação da NARA para analisar a denúncia.")
                await mod_channel.send(
                    embed=report_embed,
                    view=CommunityReportReviewView(self.cog, report_id),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
        except Exception:
            log.exception("Denúncia #%s salva, mas falhou o aviso no canal central.", report_id)
        await interaction.response.send_message(
            f"🚩 Sinalização registrada como `#{report_id}`. A equipe analisará o conteúdo; o autor não verá quem enviou.", ephemeral=True
        )


class CommunityReportButton(discord.ui.Button):
    def __init__(self, cog: "Comunidade", target_type: str, target_id: int):
        super().__init__(label="Sinalizar", emoji="🚩", style=discord.ButtonStyle.secondary,
                         custom_id=f"cm:report:{target_type}:{int(target_id)}"[:100], row=2)
        self.cog, self.target_type, self.target_id = cog, str(target_type), int(target_id)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == await self.cog.autor_alvo(self.target_type, self.target_id):
            return await interaction.response.send_message("Você não pode sinalizar sua própria publicação.", ephemeral=True)
        await interaction.response.send_modal(CommunityReportModal(self.cog, self.target_type, self.target_id))


class CommunityReportDecisionModal(discord.ui.Modal):
    def __init__(self, cog: "Comunidade", report_id: int, action: str):
        title = "Ocultar publicação" if action == "hidden" else "Arquivar sinalização"
        super().__init__(title=title, timeout=180)
        self.cog, self.report_id, self.action = cog, int(report_id), action
        self.note = discord.ui.TextInput(
            label="Justificativa da decisão", style=discord.TextStyle.paragraph,
            placeholder="Registre o que foi verificado e por que a equipe decidiu assim.",
            min_length=5, max_length=700, required=True,
        )
        self.add_item(self.note)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.decidir_denuncia(interaction, self.report_id, self.action, str(self.note.value))


class CommunityReportReviewView(discord.ui.View):
    def __init__(self, cog: "Comunidade", report_id: int):
        super().__init__(timeout=600)
        self.cog, self.report_id = cog, int(report_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, self.cog.bot.db):
            await interaction.response.send_message("Apenas a equipe pode revisar sinalizações.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Ocultar publicação", emoji="🚫", style=discord.ButtonStyle.danger, row=0)
    async def hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CommunityReportDecisionModal(self.cog, self.report_id, "hidden"))

    @discord.ui.button(label="Descartar sinalização", emoji="✅", style=discord.ButtonStyle.success, row=0)
    async def dismiss(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CommunityReportDecisionModal(self.cog, self.report_id, "dismissed"))


class CommunitySocialView(discord.ui.View):
    def __init__(self, cog: "Comunidade", target_type: str, target_id: int,
                 counts: dict[str, int], owner_id: int | None = None, participants: int = 0,
                 include_thread: bool = True):
        super().__init__(timeout=None if include_thread else 300)
        self.cog, self.target_type, self.target_id = cog, target_type, int(target_id)
        base = _tipo_social(target_type)
        for key, emoji, label in REACTIONS.get(base, REACTIONS["default"]):
            self.add_item(CommunityReactionButton(cog, target_type, target_id, key, emoji, label, counts.get(key, 0)))
        if include_thread:
            self.add_item(CommunityThreadButton(cog, target_type, target_id))
        self.add_item(CommunityBookmarkButton(cog, target_type, target_id))
        self.add_item(CommunityReportButton(cog, target_type, target_id))
        if base == "challenge":
            self.add_item(CommunityChallengeParticipantsButton(cog, target_id))
        if owner_id:
            self.add_item(CommunityFollowButton(cog, owner_id))
            self.add_item(CommunityHonorButton(cog, owner_id))
        if base == "challenge":
            self.add_item(CommunityJoinChallengeButton(cog, target_id, participants))
            self.add_item(CommunityChallengeProgressButton(cog, target_id, "in_progress"))
            self.add_item(CommunityChallengeProgressButton(cog, target_id, "completed"))


class CommunityPreferenceButton(discord.ui.Button):
    LABELS = {
        "platinas": ("Platinas", "🏆"), "zerados": ("Jogos zerados", "✅"),
        "runs": ("Runs", "⚔️"), "lore": ("Lore e teorias", "📜"),
        "guides": ("Guias e tutoriais", "📘"), "challenges": ("Desafios", "🔥"),
    }

    def __init__(self, cog: "Comunidade", user_id: int, key: str, enabled: bool, row: int):
        label, emoji = self.LABELS[key]
        super().__init__(label=f"{label}: {'ON' if enabled else 'OFF'}", emoji=emoji,
                         style=discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary, row=row)
        self.cog, self.user_id, self.key = cog, int(user_id), key

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Estas preferências pertencem a outro membro.", ephemeral=True)
        prefs = await self.cog.bot.db.get_preferencias_atividade(interaction.guild_id, self.user_id)
        await self.cog.bot.db.definir_preferencias_atividade(interaction.guild_id, self.user_id, **{self.key: not prefs[self.key]})
        await interaction.response.edit_message(
            content="Escolha quais novidades de quem você acompanha deseja receber por mensagem direta. As opções desligadas continuam disponíveis no Mural de Atividades.",
            view=await CommunityPreferencesView.criar(
                self.cog, self.user_id, interaction.guild_id,
                callback_voltar=getattr(self.view, "callback_voltar", None),
            ),
        )


class CommunityPreferencesView(discord.ui.View):
    def __init__(self, cog: "Comunidade", user_id: int, prefs: dict, callback_voltar=None):
        super().__init__(timeout=300)
        self.cog, self.user_id = cog, int(user_id)
        self.callback_voltar = callback_voltar
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")
        keys = list(CommunityPreferenceButton.LABELS)
        for i, key in enumerate(keys):
            self.add_item(CommunityPreferenceButton(cog, user_id, key, bool(prefs.get(key, True)), row=i // 3))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Estas preferências pertencem a outro membro.", ephemeral=True)
            return False
        return True

    @classmethod
    async def criar(cls, cog: "Comunidade", user_id: int, guild_id: int, callback_voltar=None):
        prefs = await cog.bot.db.get_preferencias_atividade(guild_id, user_id)
        return cls(cog, user_id, prefs, callback_voltar=callback_voltar)




async def _responder_painel_membro(interaction: discord.Interaction, *, callback_voltar=None, content=None, embed=None, view=None):
    """Edita a mensagem de origem quando veio da Nara; evita empilhar respostas efêmeras."""
    if callback_voltar is not None:
        from utils import adicionar_botao_voltar
        if view is None:
            view = discord.ui.View(timeout=600)
        adicionar_botao_voltar(view, callback_voltar, label="Voltar à Nara", emoji="🏠")
        if interaction.response.is_done():
            return await interaction.edit_original_response(content=content, embed=embed, view=view, attachments=[])
        return await interaction.response.edit_message(content=content, embed=embed, view=view, attachments=[])
    return await interaction.response.send_message(content=content, embed=embed, view=view, ephemeral=True)


class Comunidade(commands.Cog):
    """Módulo de contribuições da comunidade, Arquivo de Mundos e interações sociais."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(CommunityHomeView(self, persistent=True))
        self.bot.add_view(CommunityGuidesView(self, persistent=True))
        # Recupera os botões persistentes das publicações após reinicialização.
        try:
            posts = await self.bot.db.listar_posts_comunitarios(1500)
            restored = 0
            for post in posts:
                owner = await self.autor_alvo(str(post["target_type"]), int(post["target_id"]))
                view = await self.criar_view_social(str(post["target_type"]), int(post["target_id"]), owner_id=owner)
                try:
                    self.bot.add_view(view, message_id=int(post["message_id"]))
                    restored += 1
                except (ValueError, discord.HTTPException):
                    log.exception("Falha ao restaurar view social da mensagem %s", post["message_id"])
            log.info("Views sociais persistentes restauradas: %s", restored)
        except Exception:
            log.exception("Falha ao restaurar views sociais da comunidade")

    async def _channel(self, guild_id: int, key: str):
        channel_id = await GuildConfig.get(self.bot.db, guild_id, key)
        return await get_text_channel(self.bot, channel_id) if channel_id else None

    async def destino_contribuicao(self, guild_id: int, kind: str, origin_sector: str = ""):
        # O setor de origem orienta a fila/publicação quando o tipo é transversal (ex.: correção).
        sector_channels = {
            "runs": "soulslike_channel", "platinas": "platinas_channel",
            "zerados": "zerados_channel", "coliseu": "colizeu_channel",
            "lore": "lore_channel", "guias": "guides_channel",
            "ajuda": "guides_channel", "loja": "community_channel",
            "catalogo": "community_channel", "santuario": "community_channel",
        }
        key = sector_channels.get(str(origin_sector), CANAL_POR_TIPO.get(kind, "community_channel"))
        # Tipos com destino fixo (jogo/desafio Soulslike, lore, guia) preservam o canal correto.
        if kind not in {"correction", "idea", "item_suggestion"}:
            key = CANAL_POR_TIPO.get(kind, key)
        channel = await self._channel(guild_id, key)
        if channel is None and key != "community_channel":
            channel = await self._channel(guild_id, "community_channel")
        return channel

    async def autor_alvo(self, target_type: str, target_id: int) -> int | None:
        mapping = {
            "platina": ("platinas", "user_id"), "run": ("sl_runs", "user_id"),
            "zerado": ("zerados", "user_id"),
        }
        if target_type.startswith("contrib_"):
            row = await self.bot.db._one("SELECT user_id FROM community_contributions WHERE id=?", (int(target_id),))
        elif target_type in mapping:
            table, column = mapping[target_type]
            row = await self.bot.db._one(f"SELECT {column} FROM {table} WHERE id=?", (int(target_id),))
        else:
            row = None
        return int(row["user_id"]) if row else None

    async def atualizar_resumo_desafio(self, guild_id: int, contribution_id: int):
        """Atualiza no cartão público inscritos, andamento e conclusões autodeclaradas."""
        post = await self.bot.db.get_post_comunitario(guild_id, "contrib_challenge", contribution_id)
        if not post:
            return
        channel = self.bot.get_channel(int(post["channel_id"]))
        if channel is None:
            channel = await self.bot.fetch_channel(int(post["channel_id"]))
        message = await channel.fetch_message(int(post["message_id"]))
        if not message.embeds:
            return
        counts = await self.bot.db.contar_participantes_desafio(guild_id, contribution_id)
        total = sum(counts.values())
        andamento = int(counts.get("in_progress", 0))
        concluidos = int(counts.get("completed", 0))
        contribution = await self.bot.db.get_contribuicao(contribution_id)
        resumo = f"👥 {total} inscritos · 📈 {andamento} em andamento · 🏁 {concluidos} concluídos (autodeclarados)"
        if contribution and contribution["challenge_mode"] == "collective":
            meta = int(contribution["challenge_goal"] or 0)
            resumo += f"\n**Meta coletiva:** {concluidos}/{meta} conclusões"
        embed = message.embeds[0]
        idx = next((i for i, field in enumerate(embed.fields) if field.name == "Participação atual"), None)
        if idx is None:
            embed.add_field(name="Participação atual", value=resumo[:1024], inline=False)
        else:
            embed.set_field_at(idx, name="Participação atual", value=resumo[:1024], inline=False)
        await message.edit(embed=embed)

    async def criar_view_social(self, target_type: str, target_id: int, owner_id: int | None = None,
                                include_thread: bool = True):
        counts = await self.bot.db.contar_interacoes(
            (await self._guild_id_para_alvo(target_type, target_id)) or 0, target_type, target_id
        )
        guild_id = await self._guild_id_para_alvo(target_type, target_id)
        participants = 0
        if target_type == "contrib_challenge" and guild_id:
            totals = await self.bot.db.contar_participantes_desafio(guild_id, int(target_id))
            participants = sum(totals.values())
        if owner_id is None:
            owner_id = await self.autor_alvo(target_type, target_id)
        return CommunitySocialView(self, target_type, target_id, counts, owner_id, participants, include_thread)

    async def _guild_id_para_alvo(self, target_type: str, target_id: int) -> int | None:
        post = await self.bot.db._one(
            "SELECT guild_id FROM community_posts WHERE target_type=? AND target_id=? ORDER BY id DESC LIMIT 1",
            (str(target_type), int(target_id)),
        )
        if post:
            return int(post["guild_id"])
        if target_type.startswith("contrib_"):
            row = await self.bot.db._one("SELECT guild_id FROM community_contributions WHERE id=?", (int(target_id),))
        elif target_type == "platina":
            row = await self.bot.db._one("SELECT 1 AS ok FROM platinas WHERE id=?", (int(target_id),))
            return int(config.GUILD_ID) if row and config.GUILD_ID else None
        elif target_type == "run":
            row = await self.bot.db._one("SELECT 1 AS ok FROM sl_runs WHERE id=?", (int(target_id),))
            return int(config.GUILD_ID) if row and config.GUILD_ID else None
        elif target_type == "zerado":
            row = await self.bot.db._one("SELECT 1 AS ok FROM zerados WHERE id=?", (int(target_id),))
            return int(config.GUILD_ID) if row and config.GUILD_ID else None
        else:
            row = None
        return int(row["guild_id"]) if row else None

    async def registrar_publicacao_social(self, guild: discord.Guild, channel, message: discord.Message,
                                          target_type: str, target_id: int, owner_id: int | None = None):
        await self.bot.db.registrar_post_comunitario(
            guild.id, target_type, int(target_id), channel.id, message.id
        )
        view = await self.criar_view_social(target_type, target_id, owner_id=owner_id)
        try:
            await message.edit(view=view)
            self.bot.add_view(view, message_id=message.id)
        except (discord.HTTPException, ValueError):
            log.exception("Falha anexando interações à publicação %s #%s", target_type, target_id)
        if owner_id:
            await self.notificar_seguidores(guild.id, owner_id, target_type, target_id, message.jump_url)

    async def notificar_seguidores(self, guild_id: int, owner_id: int,
                                   target_type: str, target_id: int, jump_url: str):
        rows = await self.bot.db._all(
            "SELECT follower_id FROM community_follows WHERE guild_id=? AND followed_id=? LIMIT 30",
            (int(guild_id), int(owner_id)),
        )
        kind_label = {"platina": "uma nova platina", "zerado": "um jogo zerado", "run": "uma nova run"}.get(target_type, "uma nova publicação")
        preference_key = (
            "platinas" if target_type == "platina" else "zerados" if target_type == "zerado" else
            "runs" if target_type == "run" else "guides" if target_type in {"contrib_guide", "contrib_tutorial", "contrib_faq"} else
            "challenges" if target_type == "contrib_challenge" else "lore"
        )
        for row in rows:
            preferences = await self.bot.db.get_preferencias_atividade(guild_id, int(row["follower_id"]))
            if not preferences.get(preference_key, True):
                continue
            user = self.bot.get_user(int(row["follower_id"]))
            if user is None:
                try:
                    user = await self.bot.fetch_user(int(row["follower_id"]))
                except discord.HTTPException:
                    continue
            try:
                await user.send(f"⭐ Uma pessoa que você acompanha publicou {kind_label} no NARA.\n{jump_url}")
            except (discord.Forbidden, discord.HTTPException):
                continue

    async def decidir(self, interaction: discord.Interaction, contribution_id: int,
                      status: str, note: str = "", xp_override: int | None = None):
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores podem decidir contribuições.", ephemeral=True)
        row = await self.bot.db.get_contribuicao(contribution_id)
        if not row or row["status"] not in ("pending", "changes_requested"):
            return await interaction.response.send_message("Esta contribuição já foi processada. Atualize a fila.", ephemeral=True)
        target_channel = None
        if status == "approved":
            if row["kind"] == "game_suggestion":
                existing = await self.bot.db._one("SELECT id FROM sl_games WHERE name=? COLLATE NOCASE", (str(row["title"]).strip(),))
                if existing:
                    return await interaction.response.send_message("Este jogo já está cadastrado na Central Soulslike. Solicite ao autor uma complementação ou rejeite como duplicado.", ephemeral=True)
            if row["kind"] == "challenge":
                game_name = str(row["game_name"] or "").strip()
                game = await self.bot.db._one("SELECT id FROM sl_games WHERE name=? COLLATE NOCASE", (game_name,)) if game_name else None
                if game is None:
                    return await interaction.response.send_message("O jogo desta proposta ainda não está no catálogo de Runs. Aprove primeiro a sugestão do jogo ou cadastre-o em `/adm` → Runs.", ephemeral=True)
                duplicate = await self.bot.db._one("SELECT id FROM sl_challenges WHERE name=? COLLATE NOCASE", (str(row["title"]).strip(),))
                if duplicate:
                    return await interaction.response.send_message("Já existe um desafio com esse nome no Livro dos Desafios. Solicite outro nome ou rejeite como duplicado.", ephemeral=True)
            target_channel = await self.destino_contribuicao(
                int(row["guild_id"]), str(row["kind"]), str(row["origin_sector"] or "")
            )
            if target_channel is None:
                return await interaction.response.send_message(
                    "Não aprovei a publicação porque o canal de destino não está configurado ou está inacessível. Configure `/adm` → Comunidade e tente novamente.", ephemeral=True
                )
        xp_default = await GuildConfig.get(self.bot.db, int(row["guild_id"]), "community_xp_default")
        xp_cap = await GuildConfig.get(self.bot.db, int(row["guild_id"]), "community_xp_weekly_cap")
        xp_default = config.COMMUNITY_XP_DEFAULT if xp_default is None else int(xp_default)
        xp_cap = config.COMMUNITY_XP_WEEKLY_CAP if xp_cap is None else int(xp_cap)
        xp_base = int(TIPOS.get(str(row["kind"]), ("", "", xp_default))[2])
        if xp_override is not None:
            xp_base = int(xp_override)
        elif xp_base <= 0:
            xp_base = int(xp_default or 0)
        result = await self.bot.db.decidir_contribuicao(
            contribution_id, interaction.user.id, status, note, xp_base, xp_cap
        )
        if result is None:
            return await interaction.response.send_message("Outro moderador já processou esta contribuição.", ephemeral=True)
        try:
            await self.bot.db.log(interaction.user.id, f"community_{status}", f"id={contribution_id} author={row['user_id']} xp={result['xp_awarded']} note={note[:160]}")
        except Exception:
            log.exception("Contribuição #%s decidida, mas falhou auditoria", contribution_id)
        await interaction.response.send_message(
            f"✅ Decisão registrada para a contribuição `#{contribution_id}`. Status: **{STATUS_PT[status]}**.", ephemeral=True
        )
        if status == "approved" and target_channel is not None:
            try:
                await self.publicar_contribuicao(target_channel, result["contribution"])
            except Exception:
                log.exception("Contribuição #%s aprovada, mas publicação falhou", contribution_id)
                try:
                    await interaction.followup.send(
                        "A aprovação e o XP foram registrados, mas a publicação no canal falhou. A equipe deve verificar as permissões do canal e republicar pelo painel de administração.", ephemeral=True
                    )
                except discord.HTTPException:
                    pass
        row_atual = await self.bot.db.get_contribuicao(contribution_id) or result["contribution"]
        await self.notificar_autor(row_atual, status, note, result["xp_awarded"], result)
        if interaction.message:
            try:
                embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed(title=f"Contribuição #{contribution_id}")
                embed.color = discord.Color.green() if status == "approved" else discord.Color.orange() if status == "changes_requested" else discord.Color.red()
                embed.add_field(name="Decisão", value=f"{STATUS_PT[status]} por {interaction.user.mention}\n{note or 'Sem observações.'}", inline=False)
                await interaction.message.edit(embed=embed, view=None)
            except discord.HTTPException:
                log.exception("Não foi possível atualizar cartão de moderação da contribuição #%s", contribution_id)

    async def decidir_denuncia(self, interaction: discord.Interaction, report_id: int,
                               action: str, note: str = ""):
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores podem decidir sinalizações.", ephemeral=True)
        report = await self.bot.db.get_denuncia_comunitaria(report_id)
        if not report or report["status"] != "pending" or int(report["guild_id"]) != int(interaction.guild_id or 0):
            return await interaction.response.send_message("Esta sinalização já foi processada ou não pertence a este servidor.", ephemeral=True)
        if action == "hidden":
            post = await self.bot.db.get_post_comunitario(
                int(report["guild_id"]), str(report["target_type"]), int(report["target_id"])
            )
            if post and not bool(post["is_hidden"]):
                try:
                    channel = self.bot.get_channel(int(post["channel_id"]))
                    if channel is None:
                        channel = await self.bot.fetch_channel(int(post["channel_id"]))
                    message = await channel.fetch_message(int(post["message_id"]))
                    await message.delete(reason=f"Publicação ocultada por revisão comunitária #{report_id}: {note[:300]}")
                except discord.NotFound:
                    pass  # Já removida manualmente; registra a decisão e oculta do arquivo.
                except (discord.Forbidden, discord.HTTPException):
                    return await interaction.response.send_message(
                        "Não consegui ocultar a mensagem. Confira se o bot tem **Gerenciar mensagens** no canal original; a denúncia continua pendente.", ephemeral=True
                    )
        result = await self.bot.db.decidir_denuncia_comunitaria(report_id, interaction.user.id, action, note)
        if result is None:
            return await interaction.response.send_message("Outro moderador já decidiu esta sinalização.", ephemeral=True)
        try:
            await self.bot.db.log(
                interaction.user.id, f"community_report_{action}",
                f"report={report_id} target={report['target_type']}:{report['target_id']} note={note[:180]}",
            )
        except Exception:
            log.exception("Sinalização #%s decidida, mas o log de auditoria falhou", report_id)
        if action == "hidden":
            response = "🚫 Publicação ocultada. O registro original e os dados competitivos continuam preservados; conteúdo comunitário foi retirado do Arquivo."
        else:
            response = "✅ Sinalização arquivada sem ocultar a publicação."
        await interaction.response.send_message(response, ephemeral=True)
        try:
            reporter = self.bot.get_user(int(report["reporter_id"])) or await self.bot.fetch_user(int(report["reporter_id"]))
            await reporter.send(f"📬 A equipe concluiu a análise da sua sinalização `#{report_id}`: **{'publicação ocultada' if action == 'hidden' else 'sinalização descartada'}**.")
        except (discord.Forbidden, discord.HTTPException):
            pass
        if interaction.message:
            try:
                await interaction.message.edit(view=None)
            except discord.HTTPException:
                pass

    async def republicar(self, interaction: discord.Interaction, contribution_id: int):
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas a equipe pode republicar contribuições.", ephemeral=True)
        row = await self.bot.db.get_contribuicao(contribution_id)
        if not row or row["status"] != "approved":
            return await interaction.response.send_message("Somente contribuições aprovadas podem ser republicadas.", ephemeral=True)
        channel = await self.destino_contribuicao(
            int(row["guild_id"]), str(row["kind"]), str(row["origin_sector"] or "")
        )
        if channel is None:
            return await interaction.response.send_message("O canal de destino continua indisponível. Revise as configurações em `/adm` → Comunidade.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.publicar_contribuicao(channel, row)
        except Exception:
            log.exception("Falha ao republicar contribuição #%s", contribution_id)
            return await interaction.followup.send("A republicação falhou. Verifique permissões e registros; a proposta continua aprovada e pode ser tentada novamente.", ephemeral=True)
        await interaction.followup.send(f"✅ Contribuição `#{contribution_id}` publicada ou publicação existente recuperada.", ephemeral=True)

    async def publicar_contribuicao(self, channel, row):
        kind = str(row["kind"])
        target_type = f"contrib_{kind}"
        guild_id, contribution_id = int(row["guild_id"]), int(row["id"])

        async def recuperar_mensagem(channel_id: int, message_id: int, thread_id: int | None = None):
            post_channel = self.bot.get_channel(int(channel_id))
            if post_channel is None:
                post_channel = await self.bot.fetch_channel(int(channel_id))
            existing_message = await post_channel.fetch_message(int(message_id))
            await self.bot.db.registrar_post_comunitario(
                guild_id, target_type, contribution_id, int(post_channel.id), existing_message.id, thread_id
            )
            await self.bot.db.marcar_publicacao_contribuicao(
                contribution_id, int(post_channel.id), existing_message.id, thread_id
            )
            view = await self.criar_view_social(target_type, contribution_id, owner_id=int(row["user_id"]))
            await existing_message.edit(view=view)
            self.bot.add_view(view, message_id=existing_message.id)
            return existing_message

        # A coluna da submissão é a segunda fonte de idempotência, inclusive se a
        # publicação foi salva antes de o registro auxiliar community_posts concluir.
        if row["published_message_id"] and row["published_channel_id"]:
            try:
                return await recuperar_mensagem(
                    int(row["published_channel_id"]), int(row["published_message_id"]), row["published_thread_id"]
                )
            except (discord.NotFound, discord.Forbidden, discord.HTTPException, AttributeError):
                raise RuntimeError(
                    f"A contribuição #{contribution_id} já possui ID de publicação registrado, mas a mensagem não foi localizada. "
                    "Verifique o canal original e faça a recuperação administrativa antes de criar outro anúncio."
                )

        # Recupera uma publicação existente antes de enviar outra mensagem: o retry é idempotente.
        existing_post = await self.bot.db.get_post_comunitario(guild_id, target_type, contribution_id)
        if existing_post:
            # Usa o canal salvo no registro, não o canal atualmente configurado.
            try:
                return await recuperar_mensagem(
                    int(existing_post["channel_id"]), int(existing_post["message_id"]), existing_post["thread_id"]
                )
            except (discord.NotFound, discord.Forbidden, discord.HTTPException, AttributeError):
                log.warning("Publicação registrada para contribuição #%s não foi localizada; será necessário reparar o vínculo.", contribution_id)
                # Não envia outra mensagem silenciosamente: evita duplicação visível.
                raise RuntimeError(
                    f"A contribuição #{contribution_id} já possui uma publicação registrada, mas a mensagem não foi localizada. "
                    "Verifique o canal original e repare o registro antes de publicar novamente."
                )
        catalog_effect = None
        if kind in {"game_suggestion", "challenge"}:
            catalog_effect = await self.bot.db.aplicar_contribuicao_soulslike(int(row["id"]))
        if kind == "faq":
            await self.bot.db.ativar_faq_comunitaria(int(row["id"]))
        title = discord.utils.escape_markdown(str(row["title"]))[:250]
        label = TIPOS.get(kind, ("Contribuição", "", 0))[0]
        spoilers = {"none": "Sem spoilers", "light": "Spoilers leves", "advanced": "Spoilers avançados", "final": "Spoilers de final/DLC"}.get(row["spoiler_level"], "Classificação não informada")
        description = _safe(row["content"], 3900)
        embed = discord.Embed(title=f"{label} · {title}", description=description, color=config.COR_OURO)
        embed.add_field(name="Jogo / universo", value=_safe(row["game_name"] or "Não especificado", 200), inline=True)
        embed.add_field(name="Classificação", value=spoilers, inline=True)
        if kind == "challenge":
            mode = str(row["challenge_mode"] or "individual")
            mode_label = (
                f"Coletivo · meta de {int(row['challenge_goal'] or 0)} conclusões"
                if mode == "collective" else "Individual"
            )
            embed.add_field(name="Modalidade", value=mode_label, inline=True)
            embed.add_field(
                name="Participação atual",
                value="👥 0 inscritos · 📈 0 em andamento · 🏁 0 concluídos (autodeclarados)"
                      + (f"\n**Meta coletiva:** 0/{int(row['challenge_goal'] or 0)} conclusões" if mode == "collective" else ""),
                inline=False,
            )
        if row["summary"]:
            embed.add_field(name="Resumo", value=_safe(row["summary"], 1000), inline=False)
        if row["sources"]:
            embed.add_field(name="Fontes e referências", value=_safe(row["sources"], 1000), inline=False)
        embed.set_footer(text=f"Arquivo da Comunidade · #{row['id']} · Autor: {row['user_id']} · Revisado pela equipe")
        owner = int(row["user_id"])
        embed.add_field(name="Contribuição de", value=f"<@{owner}>", inline=True)
        if row["origin_sector"]:
            embed.add_field(name="Setor de origem", value=_safe(str(row["origin_sector"]), 80), inline=True)
        if catalog_effect:
            embed.add_field(
                name="Cadastro Soulslike",
                value=("Jogo adicionado às opções de Runs." if catalog_effect["type"] == "sl_game" else "Desafio adicionado ao Livro dos Desafios para o jogo informado."),
                inline=False,
            )
        view = await self.criar_view_social(target_type, int(row["id"]), owner_id=owner)
        message = await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())
        await self.bot.db.marcar_publicacao_contribuicao(int(row["id"]), channel.id, message.id)
        await self.registrar_publicacao_social(channel.guild, channel, message, target_type, int(row["id"]), owner)
        # Threads são iniciadas automaticamente quando o canal suporta; o botão continua como fallback.
        try:
            thread = await message.create_thread(name=f"Discussão · {str(row['title'])[:85]}", auto_archive_duration=10080)
            await self.bot.db.definir_thread_comunitaria(channel.guild.id, target_type, int(row["id"]), thread.id)
            await self.bot.db.marcar_publicacao_contribuicao(int(row["id"]), channel.id, message.id, thread.id)
            try:
                await thread.send("💬 Debate aberto. Diferencie evidências de interpretação e mantenha respeito entre os participantes.")
            except discord.HTTPException:
                pass
        except (discord.Forbidden, discord.HTTPException):
            log.info("Thread automática indisponível para contribuição #%s; o botão de discussão permanece ativo.", row["id"])

    async def notificar_autor(self, row, status: str, note: str, xp: int, resultado=None):
        if status == "approved":
            if row["published_message_id"] and row["published_channel_id"]:
                link = f"https://discord.com/channels/{row['guild_id']}/{row['published_channel_id']}/{row['published_message_id']}"
                msg = f"✅ Sua contribuição **#{row['id']} — {row['title']}** foi aprovada e publicada.\\n{link}"
            else:
                msg = f"✅ Sua contribuição **#{row['id']} — {row['title']}** foi aprovada. A publicação ainda está pendente de conclusão pela equipe."
            drop = resultado or {}
            if drop.get("card_outcome") == "carta":
                msg += f"\\n🃏 Drop recebido: **{drop.get('card_name')}** ({drop.get('card_rarity', 'Comum')})."
            elif drop.get("card_outcome") == "almas":
                msg += f"\\n✨ Duplicata convertida em **{drop.get('card_almas', 0)} Almas**."
            elif drop.get("card_outcome") == "fragmentos":
                msg += f"\\n🧩 Duplicata convertida em **{drop.get('card_fragmentos', 0)} fragmentos**."
            if xp:
                msg += f" Você recebeu **+{xp} XP**."
            else:
                msg += " O limite semanal de XP comunitário já foi atingido; não houve crédito adicional."
            categoria = "approvals"
        elif status == "changes_requested":
            msg = f"📝 A equipe solicitou ajustes na contribuição **#{row['id']} — {row['title']}**.\\nOrientação: {note}"
            categoria = "replies"
        else:
            msg = f"❌ Sua contribuição **#{row['id']} — {row['title']}** foi rejeitada.\\nMotivo: {note}"
            categoria = "rejections"
        from utils import notificar_usuario
        await notificar_usuario(self.bot, row["guild_id"], int(row["user_id"]), categoria, msg)

    async def mostrar_minhas(self, interaction: discord.Interaction, callback_voltar=None):
        rows = await self.bot.db.listar_contribuicoes(guild_id=interaction.guild_id, user_id=interaction.user.id, limit=10)
        embed = discord.Embed(title="🗂️ Minhas contribuições", color=config.COR_OURO)
        if not rows:
            embed.description = "Você ainda não enviou contribuições. Use **Contribuir** para começar."
        else:
            lines = []
            for row in rows:
                label = TIPOS.get(row["kind"], ("Contribuição", "", 0))[0]
                lines.append(f"`#{row['id']}` **{discord.utils.escape_markdown(row['title'])}**\n{label} · {STATUS_PT.get(row['status'], row['status'])} · {row['created_at'][:16]}")
                if row["status"] == "changes_requested" and row["review_note"]:
                    lines.append(f"> Orientação: {discord.utils.escape_markdown(row['review_note'][:250])}")
        embed.description = "\n\n".join(lines)[:4000] if rows else embed.description
        embed.set_footer(text="Mostrando até 10 propostas recentes. O XP é creditado somente após aprovação. Use o seletor para responder a pedidos de ajuste.")
        await _responder_painel_membro(interaction, callback_voltar=callback_voltar, embed=embed, view=CommunityMyContributionsView(self, rows, callback_voltar))

    async def mostrar_favoritos(self, interaction: discord.Interaction, callback_voltar=None):
        rows = await self.bot.db.listar_favoritos(interaction.guild_id, interaction.user.id, 20)
        embed = discord.Embed(title="🔖 Meus favoritos", color=config.COR_OURO)
        if not rows:
            embed.description = "Você ainda não salvou publicações. Use o botão **Salvar** nos cartões do Coliseu e do Arquivo de Mundos."
        else:
            lines = []
            for row in rows:
                label = {"platina": "🏆 Platina", "run": "⚔️ Run", "zerado": "✅ Jogo zerado"}.get(row["target_type"], "📚 Publicação")
                description = f"{label} · registro `#{row['target_id']}`"
                if row["target_type"].startswith("contrib_"):
                    contrib = await self.bot.db.get_contribuicao(int(row["target_id"]))
                    if contrib:
                        description = f"{label} · **{discord.utils.escape_markdown(contrib['title'])}** · `#{row['target_id']}`"
                post = await self.bot.db.get_post_comunitario(interaction.guild_id, row["target_type"], int(row["target_id"]))
                if post and post["is_hidden"]:
                    description += " · publicação ocultada pela moderação"
                elif post:
                    description += f" · [Abrir](https://discord.com/channels/{interaction.guild_id}/{post['channel_id']}/{post['message_id']})"
                lines.append(description)
            embed.description = "\n".join(lines)[:4000]
        await _responder_painel_membro(interaction, callback_voltar=callback_voltar, embed=embed) 

    async def mostrar_arquivo(self, interaction: discord.Interaction, origin_sector: str = "lore", callback_voltar=None):
        rows = await self.bot.db.listar_contribuicoes(guild_id=interaction.guild_id, status="approved", limit=25)
        embed = discord.Embed(
            title="📚 Arquivo de Mundos e Biblioteca da Comunidade",
            description="Publicações aprovadas pela equipe. Teorias são interpretações da comunidade; lore confirmada deve estar sustentada por fontes do jogo ou oficiais.",
            color=config.COR_OURO,
        )
        if not rows:
            embed.add_field(name="Arquivo em formação", value="Ainda não há publicações aprovadas. Seja um dos primeiros colaboradores.", inline=False)
        else:
            lines = []
            for row in rows[:10]:
                label = TIPOS.get(row["kind"], ("Contribuição", "", 0))[0]
                lines.append(f"`#{row['id']}` **{discord.utils.escape_markdown(row['title'])}** · {label} · {row['game_name'] or 'Geral'}")
            embed.add_field(name="Publicações recentes", value="\n".join(lines)[:1024], inline=False)
        view = CommunityArchiveView(self, rows, origin_sector=origin_sector, callback_voltar=callback_voltar)
        await _responder_painel_membro(interaction, callback_voltar=callback_voltar, embed=embed, view=view)

    async def mostrar_publicacao(self, interaction: discord.Interaction, row, callback_voltar=None):
        label = TIPOS.get(row["kind"], ("Contribuição", "", 0))[0]
        spoilers = {"none": "Sem spoilers", "light": "Spoilers leves", "advanced": "Spoilers avançados", "final": "Spoilers de final/DLC"}.get(row["spoiler_level"], "Não classificado")
        embed = discord.Embed(title=f"{label} · {row['title']}", description=_safe(row["content"], 3900), color=config.COR_OURO)
        embed.add_field(name="Jogo", value=_safe(row["game_name"] or "Não especificado", 200), inline=True)
        embed.add_field(name="Spoilers", value=spoilers, inline=True)
        if row["summary"]:
            embed.add_field(name="Resumo", value=_safe(row["summary"], 1000), inline=False)
        if row["sources"]:
            embed.add_field(name="Fontes", value=_safe(row["sources"], 1000), inline=False)
        embed.set_footer(text=f"Publicação #{row['id']} · Autor <@{row['user_id']}> · Revisão humana")
        view = await self.criar_view_social(f"contrib_{row['kind']}", int(row["id"]), owner_id=int(row["user_id"]), include_thread=False)
        await _responder_painel_membro(interaction, callback_voltar=callback_voltar, embed=embed, view=view)

    async def mostrar_atividades(self, interaction: discord.Interaction, callback_voltar=None):
        rows = await self.bot.db._all(
            "SELECT * FROM community_posts WHERE guild_id=? AND is_hidden=0 ORDER BY created_at DESC,id DESC LIMIT 15",
            (interaction.guild_id,),
        )
        embed = discord.Embed(title="📡 Mural de atividades", description="Publicações recentes dos sistemas sociais do NARA.", color=config.COR_OURO)
        if not rows:
            embed.add_field(name="Sem atividades recentes", value="Novas runs, platinas, jogos zerados e contribuições aprovadas aparecerão aqui quando os módulos forem integrados.", inline=False)
        else:
            labels = {"run": "⚔️ Run", "platina": "🏆 Platina", "zerado": "✅ Zerado"}
            lines = []
            for row in rows:
                target_type = str(row["target_type"])
                label = labels.get(target_type, "📚 Comunidade")
                if target_type.startswith("contrib_"):
                    contrib = await self.bot.db.get_contribuicao(int(row["target_id"]))
                    if contrib:
                        label = f"📖 {contrib['title']}"
                lines.append(f"{label} · `#{row['target_id']}` · <#{row['channel_id']}> · [Abrir](https://discord.com/channels/{row['guild_id']}/{row['channel_id']}/{row['message_id']})")
            embed.add_field(name="Últimas publicações", value="\n".join(lines)[:4000], inline=False)
        await _responder_painel_membro(interaction, callback_voltar=callback_voltar, embed=embed)

    async def mostrar_preferencias(self, interaction: discord.Interaction, callback_voltar=None):
        if interaction.guild_id is None:
            return await interaction.response.send_message("Abra estas preferências dentro do servidor.", ephemeral=True)
        view = await CommunityPreferencesView.criar(self, interaction.user.id, interaction.guild_id, callback_voltar=callback_voltar)
        await _responder_painel_membro(
            interaction, callback_voltar=callback_voltar,
            content="🔔 **Notificações de quem você acompanha**\nAtive ou desative cada tipo. O Mural de Atividades continua disponível mesmo quando as mensagens diretas estão desligadas.",
            view=view,
        )

    async def publicar_painel_guias(self, interaction: discord.Interaction):
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas a equipe pode publicar este painel.", ephemeral=True)
        channel = await self._channel(interaction.guild_id, "guides_channel")
        if channel is None:
            return await interaction.response.send_message(
                "Configure primeiro o canal de Guias e Tutoriais em `/adm` → Comunidade.", ephemeral=True
            )
        embed = discord.Embed(
            title="📘 BIBLIOTECA DA COMUNIDADE — NARA",
            description=(
                "**Guias · Tutoriais · Soluções · Perguntas frequentes**\n\n"
                "Encontre orientações preparadas por jogadores, compartilhe um passo a passo e ajude a manter os conteúdos atualizados.\n\n"
                "Todas as contribuições passam pela revisão da equipe. Informe jogo, plataforma e versão quando isso fizer diferença."
            ), color=config.COR_OURO,
        )
        embed.set_footer(text="NARA • Biblioteca da Comunidade • Conteúdo revisado pela equipe")
        msg_id = await self.bot.db.get_kv(f"community_guides_panel:{interaction.guild_id}")
        msg = None
        if msg_id:
            try:
                msg = await channel.fetch_message(int(msg_id))
            except (discord.NotFound, ValueError, TypeError):
                msg = None
        if msg:
            await msg.edit(embed=embed, view=CommunityGuidesView(self, persistent=True))
        else:
            msg = await channel.send(embed=embed, view=CommunityGuidesView(self, persistent=True))
        await self.bot.db.set_kv(f"community_guides_panel:{interaction.guild_id}", str(msg.id))
        await interaction.response.send_message(
            f"✅ Painel da Biblioteca de Guias publicado/atualizado em {channel.mention}.", ephemeral=True
        )

    async def publicar_painel(self, interaction: discord.Interaction):
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas a equipe pode publicar este painel.", ephemeral=True)
        channel = await self._channel(interaction.guild_id, "lore_channel")
        if channel is None:
            return await interaction.response.send_message("Configure primeiro o canal de Lore e Teorias em `/adm` → Comunidade.", ephemeral=True)
        embed = discord.Embed(
            title="📚 ARQUIVO DE MUNDOS — NARA",
            description=(
                "**Lore · Teorias · Mistérios · Descobertas**\n\n"
                "Um arquivo colaborativo dos universos dos jogos. Publique teorias com argumentos, documente descobertas, organize cronologias e participe dos debates.\n\n"
                "**Como funciona:** todos podem contribuir; a equipe revisa antes da publicação. Lore confirmada, teoria e debate são classificados separadamente. Spoilers precisam ser identificados.\n\n"
                "Use os botões abaixo para enviar conteúdo, explorar o arquivo ou acompanhar suas propostas."
            ), color=config.COR_OURO,
        )
        embed.set_footer(text="NARA • Arquivo de Mundos • Conhecimento construído pela comunidade")
        msg_id = await self.bot.db.get_kv(f"community_panel:{interaction.guild_id}")
        msg = None
        if msg_id:
            try:
                msg = await channel.fetch_message(int(msg_id))
            except (discord.NotFound, ValueError, TypeError):
                msg = None
        if msg:
            await msg.edit(embed=embed, view=CommunityHomeView(self, persistent=True))
        else:
            msg = await channel.send(embed=embed, view=CommunityHomeView(self, persistent=True))
        await self.bot.db.set_kv(f"community_panel:{interaction.guild_id}", str(msg.id))
        await interaction.response.send_message(f"✅ Painel do Arquivo de Mundos publicado/atualizado em {channel.mention}.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Comunidade(bot))
