"""Coliseu de cartas: coleção, pacotes, forja, decks e duelos com apostas.

Todas as decisões de jogo e movimentações de moeda são validadas no servidor e
persistidas no SQLite. Nenhum resultado depende dos valores enviados pelo cliente.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import discord
from discord.ext import commands, tasks

import config
from levels import PATENTES, nivel_por_xp
from sistemas.arte_cartas import render_carta, render_pacote
from sistemas.cartas import (
    ALMAS_DUPLICATA,
    CARTAS_PACOTE,
    CARTAS_PACOTE_POR_RARIDADE,
    CARTAS_PATENTE,
    CUSTO_FORJA,
    EMOJIS_TIPO,
    PITY_CARTAS,
    PRECO_PACOTE_FOGUEIRA,
    bonus_habilidade,
    carta_de_jogo_por_id,
    carta_jogo,
    cards_em_deck_validos,
    get_carta,
    narrar_rodada,
    poder_total_deck,
    resolver_rodada,
)

log = logging.getLogger("cogs.cartas_coliseu")

# Limites conservadores de lançamento; configuráveis no código em uma futura tela admin.
NIVEL_MINIMO_DUELO = 5
APOSTA_MINIMA = 10
APOSTA_MAXIMA = 500
LIMITE_DUELOS_DIA = 5
LIMITE_DUELOS_PAR_DIA = 2
LIMITE_APOSTA_DIA = 1500  # soma das apostas individuais iniciadas pelo mesmo membro
COOLDOWN_DESAFIO_SEGUNDOS = 60
TEMPO_CONVITE_SEGUNDOS = 120
TEMPO_RODADA_SEGUNDOS = 180
DIFERENCA_MAXIMA_PODER_DECK = 4


def _formatar_carta(carta: dict) -> str:
    return (
        f"{EMOJIS_TIPO.get(carta.get('tipo'), '✦')} **{carta.get('nome', 'Carta')}** "
        f"· {carta.get('raridade')} · Poder {carta.get('poder')} · Custo {carta.get('custo')}"
    )


def _descricao_habilidade(carta: dict) -> str:
    from sistemas.cartas import HABILIDADES
    habilidade = HABILIDADES.get(str(carta.get("habilidade")), {})
    return f"**{habilidade.get('nome', 'Sem habilidade')}** — {habilidade.get('texto', '')}"


class BotaoDueloColiseu(discord.ui.DynamicItem[discord.ui.Button], template=r"coliseu_cartas:(?P<acao>aceitar|recusar|cancelar|jogar):(?P<duelo>[0-9]+)"):
    """Botões dinâmicos; continuam válidos após reiniciar o bot."""

    ROTULOS = {
        "aceitar": ("Aceitar duelo", "⚔️", discord.ButtonStyle.success),
        "recusar": ("Recusar", "✖️", discord.ButtonStyle.secondary),
        "cancelar": ("Cancelar convite", "🛑", discord.ButtonStyle.secondary),
        "jogar": ("Escolher carta", "🃏", discord.ButtonStyle.primary),
    }

    def __init__(self, acao: str, duelo_id: int):
        label, emoji, style = self.ROTULOS[acao]
        super().__init__(discord.ui.Button(
            label=label, emoji=emoji, style=style,
            custom_id=f"coliseu_cartas:{acao}:{int(duelo_id)}",
        ))
        self.acao = acao
        self.duelo_id = int(duelo_id)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        return cls(match["acao"], int(match["duelo"]))

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("ColiseuCartas")
        if cog is None:
            return await interaction.response.send_message("O Coliseu está temporariamente indisponível.", ephemeral=True)
        await cog.processar_botao_duelo(interaction, self.acao, self.duelo_id)


class BotaoMenuCartas(discord.ui.Button):
    def __init__(self, cog: "ColiseuCartas", user_id: int, acao: str, label: str, emoji: str,
                 style: discord.ButtonStyle = discord.ButtonStyle.secondary, row: int = 0):
        super().__init__(label=label, emoji=emoji, style=style, row=row)
        self.cog = cog
        self.user_id = int(user_id)
        self.acao = acao

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro membro. Abra o seu pelo `/nara`.", ephemeral=True)
        await self.cog.executar_acao_menu(interaction, self.acao)


class PainelColiseuView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", user_id: int):
        super().__init__(timeout=600)
        self.user_id = int(user_id)
        self.add_item(BotaoMenuCartas(cog, user_id, "colecao", "Minha coleção", "🃏", discord.ButtonStyle.primary, 0))
        self.add_item(BotaoMenuCartas(cog, user_id, "pacote", "Pacote Fogueira", "🔥", discord.ButtonStyle.success, 0))
        self.add_item(BotaoMenuCartas(cog, user_id, "deck", "Montar deck", "🛡️", discord.ButtonStyle.primary, 1))
        self.add_item(BotaoMenuCartas(cog, user_id, "forja", "Forja de Almas", "💎", discord.ButtonStyle.secondary, 1))
        self.add_item(BotaoMenuCartas(cog, user_id, "duelo", "Desafiar jogador", "⚔️", discord.ButtonStyle.danger, 2))
        self.add_item(BotaoMenuCartas(cog, user_id, "ranking", "Hall da Fama", "🏆", discord.ButtonStyle.secondary, 2))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Este painel é privado. Abra `/nara` para acessar o seu.", ephemeral=True)
            return False
        return True


class VoltarColiseuButton(discord.ui.Button):
    def __init__(self, cog: "ColiseuCartas", user_id: int):
        super().__init__(label="Voltar ao Coliseu", emoji="↩️", style=discord.ButtonStyle.secondary, row=4)
        self.cog = cog
        self.user_id = int(user_id)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro membro.", ephemeral=True)
        await self.cog.abrir_painel(interaction, editar=True)


class CollectionSelect(discord.ui.Select):
    def __init__(self, view: "CollectionView"):
        self.parent_view = view
        start = view.page * view.page_size
        page_items = view.cards[start:start + view.page_size]
        options = []
        for row, carta in page_items:
            options.append(discord.SelectOption(
                label=str(carta["nome"])[:100],
                value=str(carta["id"]),
                description=f"{carta['raridade']} · {carta['tipo']} · Poder {carta['poder']} · Custo {carta['custo']}"[:100],
                emoji=EMOJIS_TIPO.get(carta.get("tipo"), "🃏"),
            ))
        super().__init__(placeholder="Selecione uma carta para ver os detalhes...", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        carta = self.parent_view.cards_by_id.get(self.values[0])
        if carta is None:
            return await interaction.response.send_message("Não encontrei essa carta na sua coleção.", ephemeral=True)
        await self.parent_view.cog.mostrar_detalhe_carta(interaction, carta)


class CollectionPageButton(discord.ui.Button):
    def __init__(self, parent_view: "CollectionView", direcao: int):
        self.parent_view = parent_view
        self.direcao = int(direcao)
        super().__init__(label="Anterior" if direcao < 0 else "Próxima", emoji="◀️" if direcao < 0 else "▶️",
                         style=discord.ButtonStyle.secondary, row=1,
                         disabled=(parent_view.page == 0 if direcao < 0 else (parent_view.page + 1 >= parent_view.pages)))

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.page = max(0, min(self.parent_view.pages - 1, self.parent_view.page + self.direcao))
        self.parent_view.rebuild()
        await interaction.response.edit_message(embed=self.parent_view.embed(), view=self.parent_view)


class CollectionView(discord.ui.View):
    page_size = 20

    def __init__(self, cog: "ColiseuCartas", user_id: int, cards: list[tuple[dict, dict]]):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = int(user_id)
        self.cards = cards
        self.cards_by_id = {carta["id"]: carta for _, carta in cards}
        self.page = 0
        self.pages = max(1, (len(cards) + self.page_size - 1) // self.page_size)
        self.rebuild()

    def rebuild(self):
        self.clear_items()
        if self.cards:
            self.add_item(CollectionSelect(self))
        self.add_item(CollectionPageButton(self, -1))
        self.add_item(CollectionPageButton(self, 1))
        self.add_item(VoltarColiseuButton(self.cog, self.user_id))

    def embed(self) -> discord.Embed:
        embed = discord.Embed(title="🃏 Minha coleção", color=config.COR_OURO)
        if not self.cards:
            embed.description = "Sua coleção ainda está vazia. Abra um Pacote Fogueira ou conquiste cartas registrando jogos e platinas aprovados."
        else:
            start = self.page * self.page_size
            lines = []
            for _, carta in self.cards[start:start + self.page_size]:
                lines.append(
                    f"{EMOJIS_TIPO.get(carta['tipo'], '🃏')} **{carta['nome']}** · {carta['raridade']} · "
                    f"Poder {carta['poder']} · Custo {carta['custo']}"
                )
            embed.description = "\n".join(lines)
            embed.set_footer(text=f"Página {self.page + 1}/{self.pages} · Selecione uma carta para ver sua arte e habilidade")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Esta coleção é privada.", ephemeral=True)
            return False
        return True


class ConfirmarPacoteButton(discord.ui.Button):
    def __init__(self, view: "ConfirmarPacoteView"):
        super().__init__(label=f"Abrir por {PRECO_PACOTE_FOGUEIRA} Denários", emoji="🔥", style=discord.ButtonStyle.success)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        view = self.parent_view
        if interaction.user.id != view.user_id:
            return await interaction.response.send_message("Este pacote pertence a outro membro.", ephemeral=True)
        if view.aberto:
            return await interaction.response.send_message("Este pacote já está sendo processado.", ephemeral=True)
        view.aberto = True
        self.disabled = True
        await interaction.response.defer(ephemeral=True, thinking=True)
        resultado = await view.cog.bot.db.coliseu_abrir_pacote(
            view.user_id,
            {r: [c.para_dict() for c in cards] for r, cards in CARTAS_PACOTE_POR_RARIDADE.items()},
            ALMAS_DUPLICATA,
            PRECO_PACOTE_FOGUEIRA,
            3,
        )
        if resultado["status"] == "sem_saldo":
            return await interaction.followup.send(
                f"Você tem {resultado['saldo']} Denários; o pacote custa {PRECO_PACOTE_FOGUEIRA}.", ephemeral=True
            )
        if resultado["status"] != "ok":
            return await interaction.followup.send("Não consegui abrir o pacote. Nenhum Denário foi descontado.", ephemeral=True)
        cards = [x["carta"] for x in resultado["cards"]]
        linhas = []
        for item in resultado["cards"]:
            carta = item["carta"]
            linha = _formatar_carta(carta)
            if item["duplicata"]:
                linha += f"\n↳ Repetida: convertida em **{item['almas']} Almas**."
            linhas.append(linha)
        caminho = render_pacote(cards)
        arquivo = discord.File(str(caminho), filename="pacote_fogueira.png")
        embed = discord.Embed(
            title="🔥 Pacote Fogueira aberto",
            description="\n\n".join(linhas),
            color=config.COR_OURO,
        )
        embed.set_image(url="attachment://pacote_fogueira.png")
        embed.add_field(name="Almas recebidas", value=f"+{resultado['almas_ganhas']}", inline=True)
        embed.add_field(name="Saldo restante", value=f"{resultado['saldo']} Denários", inline=True)
        embed.add_field(name="Proteção contra azar", value=f"{resultado['pity']}/10 cartas Comuns consecutivas", inline=False)
        await interaction.followup.send(embed=embed, file=arquivo, ephemeral=True)


class ConfirmarPacoteView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", user_id: int):
        super().__init__(timeout=90)
        self.cog = cog
        self.user_id = int(user_id)
        self.aberto = False
        self.add_item(ConfirmarPacoteButton(self))
        self.add_item(VoltarColiseuButton(cog, user_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Este painel é privado.", ephemeral=True)
            return False
        return True


class ForjaSelect(discord.ui.Select):
    def __init__(self, view: "ForjaView"):
        self.parent_view = view
        opcoes = []
        for carta in view.disponiveis[:25]:
            custo = CUSTO_FORJA[carta["raridade"]]
            opcoes.append(discord.SelectOption(
                label=carta["nome"][:100], value=carta["id"],
                description=f"{carta['raridade']} · {custo} Almas · Poder {carta['poder']}"[:100],
                emoji=EMOJIS_TIPO.get(carta["tipo"], "💎"),
            ))
        super().__init__(placeholder="Escolha a carta que deseja forjar...", min_values=1, max_values=1,
                         options=opcoes or [discord.SelectOption(label="Todas as cartas disponíveis já foram coletadas", value="none")],
                         disabled=not opcoes, row=0)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message("Não há cartas disponíveis para forjar.", ephemeral=True)
        self.parent_view.selecionada = self.parent_view.carta_por_id[self.values[0]]
        self.parent_view.rebuild()
        await interaction.response.edit_message(embed=self.parent_view.embed(), view=self.parent_view)


class ForjaConfirmButton(discord.ui.Button):
    def __init__(self, view: "ForjaView"):
        super().__init__(label="Forjar carta", emoji="💎", style=discord.ButtonStyle.success, row=1, disabled=view.selecionada is None)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        view = self.parent_view
        if view.selecionada is None:
            return await interaction.response.send_message("Selecione uma carta primeiro.", ephemeral=True)
        custo = CUSTO_FORJA[view.selecionada["raridade"]]
        resultado = await view.cog.bot.db.coliseu_forjar_carta(view.user_id, view.selecionada, custo)
        if resultado == "ok":
            await interaction.response.edit_message(
                embed=discord.Embed(title="💎 Carta forjada", description=f"{_formatar_carta(view.selecionada)}\n\n{custo} Almas foram utilizadas.", color=config.COR_OURO),
                view=discord.ui.View(timeout=120).add_item(VoltarColiseuButton(view.cog, view.user_id)),
            )
        elif resultado == "sem_almas":
            await interaction.response.send_message(f"Você precisa de {custo} Almas para forjar essa carta.", ephemeral=True)
        elif resultado == "ja_tem":
            await interaction.response.send_message("Você já possui essa carta. Escolha outra para não desperdiçar Almas.", ephemeral=True)
        else:
            await interaction.response.send_message("Não consegui concluir a forja.", ephemeral=True)


class ForjaView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", user_id: int, disponiveis: list[dict], almas: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = int(user_id)
        self.disponiveis = disponiveis
        self.carta_por_id = {c["id"]: c for c in disponiveis}
        self.almas = int(almas)
        self.selecionada: dict | None = None
        self.rebuild()

    def rebuild(self):
        self.clear_items()
        self.add_item(ForjaSelect(self))
        self.add_item(ForjaConfirmButton(self))
        self.add_item(VoltarColiseuButton(self.cog, self.user_id))

    def embed(self):
        embed = discord.Embed(title="💎 Forja de Almas", color=config.COR_OURO)
        embed.description = f"**Seu saldo:** {self.almas} Almas\nDuplicatas viram Almas automaticamente. Cada raridade tem um custo fixo de criação."
        embed.add_field(
            name="Custos",
            value="Comum: 40 · Rara: 120 · Épica: 320 · Lendária: 800 Almas",
            inline=False,
        )
        embed.add_field(
            name="Cartas exclusivas",
            value="Cartas de jogos e patentes são conquistas especiais e não podem ser fabricadas. Elas continuam exclusivas de quem alcançou o marco correspondente.",
            inline=False,
        )
        if self.selecionada:
            carta = self.selecionada
            embed.add_field(name="Carta selecionada", value=f"{_formatar_carta(carta)}\nCusto: **{CUSTO_FORJA[carta['raridade']]} Almas**", inline=False)
        else:
            embed.set_footer(text="Escolha uma carta e confirme a criação antes de gastar suas Almas.")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Esta forja é privada.", ephemeral=True)
            return False
        return True


class DeckCardSelect(discord.ui.Select):
    def __init__(self, view: "DeckBuilderView"):
        self.parent_view = view
        start = view.page * view.page_size
        disponiveis = view.cartas_disponiveis
        page_cards = disponiveis[start:start + view.page_size]
        options = [discord.SelectOption(
            label=c["nome"][:100], value=c["id"],
            description=f"{c['raridade']} · {c['tipo']} · Poder {c['poder']} · Custo {c['custo']}"[:100],
            emoji=EMOJIS_TIPO.get(c["tipo"], "🃏"),
        ) for c in page_cards]
        super().__init__(placeholder="Adicione uma carta ao deck...", min_values=1, max_values=1,
                         options=options or [discord.SelectOption(label="Não há cartas nesta página", value="none")],
                         disabled=(not options or len(view.selecionadas) >= 5), row=0)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message("Não há mais cartas para selecionar nesta página.", ephemeral=True)
        view = self.parent_view
        carta = view.cards_by_id.get(self.values[0])
        if carta and len(view.selecionadas) < 5:
            view.selecionadas.append(carta)
        view.rebuild()
        await interaction.response.edit_message(embed=view.embed(), view=view)


class DeckPageButton(discord.ui.Button):
    def __init__(self, view: "DeckBuilderView", direction: int):
        self.parent_view = view
        self.direction = int(direction)
        pages = view.pages
        super().__init__(label="Anterior" if direction < 0 else "Próxima", emoji="◀️" if direction < 0 else "▶️",
                         style=discord.ButtonStyle.secondary, row=1,
                         disabled=(view.page <= 0 if direction < 0 else view.page + 1 >= pages))

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.page = max(0, min(self.parent_view.pages - 1, self.parent_view.page + self.direction))
        self.parent_view.rebuild()
        await interaction.response.edit_message(embed=self.parent_view.embed(), view=self.parent_view)


class DeckActionButton(discord.ui.Button):
    def __init__(self, view: "DeckBuilderView", action: str):
        self.parent_view = view
        self.action = action
        if action == "undo":
            label, emoji, style, disabled = "Desfazer última", "↩️", discord.ButtonStyle.secondary, not view.selecionadas
        elif action == "save":
            label, emoji, style = "Salvar deck", "💾", discord.ButtonStyle.success
            valido, _ = cards_em_deck_validos(view.selecionadas)
            disabled = not valido
        else:
            label, emoji, style, disabled = "Voltar", "🏠", discord.ButtonStyle.secondary, False
        super().__init__(label=label, emoji=emoji, style=style, row=2, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        view = self.parent_view
        if self.action == "undo":
            if view.selecionadas:
                view.selecionadas.pop()
            view.rebuild()
            return await interaction.response.edit_message(embed=view.embed(), view=view)
        if self.action == "save":
            valido, motivo = cards_em_deck_validos(view.selecionadas)
            if not valido:
                return await interaction.response.send_message(motivo, ephemeral=True)
            resultado = await view.cog.bot.db.coliseu_salvar_deck(view.user_id, view.selecionadas)
            if resultado["status"] == "ok":
                embed = discord.Embed(title="🛡️ Deck salvo", description="Seu deck de cinco cartas está pronto para duelos com apostas.", color=config.COR_OURO)
                embed.add_field(name="Custo total", value=f"{resultado['custo']}/12", inline=True)
                embed.add_field(name="Poder total", value=str(poder_total_deck(view.selecionadas)), inline=True)
                embed.add_field(name="Cartas", value="\n".join(f"• {c['nome']}" for c in view.selecionadas), inline=False)
                return await interaction.response.edit_message(embed=embed, view=discord.ui.View(timeout=120).add_item(VoltarColiseuButton(view.cog, view.user_id)))
            return await interaction.response.send_message("Não foi possível salvar: uma das cartas não pertence à sua coleção.", ephemeral=True)
        await view.cog.abrir_painel(interaction, editar=True)


class DeckBuilderView(discord.ui.View):
    page_size = 25

    def __init__(self, cog: "ColiseuCartas", user_id: int, cards: list[dict]):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = int(user_id)
        self.cards = cards
        self.cards_by_id = {c["id"]: c for c in cards}
        self.selecionadas: list[dict] = []
        self.page = 0
        self.pages = max(1, (len(cards) + self.page_size - 1) // self.page_size)
        self.rebuild()

    @property
    def cartas_disponiveis(self) -> list[dict]:
        usados = {str(c["id"]) for c in self.selecionadas}
        return [c for c in self.cards if str(c["id"]) not in usados]

    def rebuild(self):
        self.pages = max(1, (len(self.cartas_disponiveis) + self.page_size - 1) // self.page_size)
        self.page = max(0, min(self.page, self.pages - 1))
        self.clear_items()
        self.add_item(DeckCardSelect(self))
        self.add_item(DeckPageButton(self, -1))
        self.add_item(DeckPageButton(self, 1))
        self.add_item(DeckActionButton(self, "undo"))
        self.add_item(DeckActionButton(self, "save"))
        self.add_item(DeckActionButton(self, "back"))

    def embed(self):
        embed = discord.Embed(title="🛡️ Montagem do deck", color=config.COR_OURO)
        if self.selecionadas:
            lines = [f"**{i}.** {_formatar_carta(c)}" for i, c in enumerate(self.selecionadas, 1)]
            custo = sum(int(c["custo"]) for c in self.selecionadas)
            lendarias = sum(c["raridade"] == "Lendária" for c in self.selecionadas)
            poder = poder_total_deck(self.selecionadas)
            embed.description = "\n".join(lines) + f"\n\n**Custo:** {custo}/12 · **Poder total:** {poder} · **Lendárias:** {lendarias}/1"
        else:
            embed.description = (
                "Escolha cinco cartas, uma por vez. O deck aceita até 12 pontos de custo e no máximo uma Lendária.\n"
                f"Para duelar com apostas, os dois decks precisam ter poder total com diferença máxima de {DIFERENCA_MAXIMA_PODER_DECK}."
            )
        embed.set_footer(text=f"{len(self.selecionadas)}/5 cartas · Página {self.page + 1}/{self.pages}")
        if len(self.selecionadas) == 5:
            valido, motivo = cards_em_deck_validos(self.selecionadas)
            embed.add_field(name="Validação", value=motivo, inline=False)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Este deck pertence a outro membro.", ephemeral=True)
            return False
        return True


class SelecaoCartaJogo(discord.ui.Select):
    def __init__(self, cog: "ColiseuCartas", duel_id: int, user_id: int, cards: list[dict]):
        self.cog = cog
        self.duel_id = int(duel_id)
        self.user_id = int(user_id)
        options = [discord.SelectOption(
            label=c["nome"][:100], value=c["id"],
            description=f"{c['tipo']} · Poder {c['poder']} · {c['raridade']}"[:100],
            emoji=EMOJIS_TIPO.get(c["tipo"], "🃏"),
        ) for c in cards[:5]]
        super().__init__(placeholder="Sua escolha é secreta. Selecione uma carta...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Esta escolha pertence a outro duelista.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        resultado = await self.cog.bot.db.coliseu_registrar_jogada(self.duel_id, self.user_id, self.values[0])
        if resultado["status"] == "aguardando":
            await interaction.followup.send(
                "Sua carta foi registrada em segredo. A arena só revela as escolhas quando os dois duelistas confirmarem.",
                ephemeral=True,
            )
            return
        if resultado["status"] == "pronto":
            resolucao = await self.cog.resolver_rodada(resultado)
            await self.cog.atualizar_mensagem_duelo(self.duel_id, interaction.guild)
            await interaction.followup.send(resolucao, ephemeral=True)
            return
        mensagens = {
            "inativo": "Este duelo não está mais ativo.",
            "nao_autorizado": "Você não participa deste duelo.",
            "ja_escolheu": "Sua carta desta rodada já foi registrada. Não é possível trocá-la.",
            "carta_invalida": "Essa carta não pertence ao deck travado para este duelo.",
            "carta_usada": "Cada carta só pode ser utilizada uma vez por duelo.",
            "snapshot_invalido": "Não consegui validar o deck desta partida.",
        }
        await interaction.followup.send(mensagens.get(resultado["status"], "Não consegui registrar sua jogada."), ephemeral=True)


class SelecaoCartaView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", duel_id: int, user_id: int, cards: list[dict]):
        super().__init__(timeout=120)
        self.add_item(SelecaoCartaJogo(cog, duel_id, user_id, cards))


class DesafioColiseuModal(discord.ui.Modal, title="Desafiar um gladiador"):
    def __init__(self, cog: "ColiseuCartas", creator_id: int):
        super().__init__(timeout=180)
        self.cog = cog
        self.creator_id = int(creator_id)
        self.alvo = discord.ui.TextInput(
            label="Membro que você quer desafiar",
            placeholder="Mencione o membro ou informe o ID do Discord",
            min_length=1, max_length=32,
        )
        self.aposta = discord.ui.TextInput(
            label=f"Aposta por pessoa ({APOSTA_MINIMA}–{APOSTA_MAXIMA} Denários)",
            placeholder="Ex.: 50", min_length=1, max_length=4, default=str(APOSTA_MINIMA),
        )
        self.add_item(self.alvo)
        self.add_item(self.aposta)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None or interaction.channel is None:
            return await interaction.response.send_message("Os duelos só podem ser criados dentro de um servidor.", ephemeral=True)
        match = re.search(r"\d{15,22}", str(self.alvo.value))
        if not match:
            return await interaction.response.send_message("Mencione o membro ou informe um ID válido do Discord.", ephemeral=True)
        try:
            aposta = int(str(self.aposta.value).strip())
        except ValueError:
            return await interaction.response.send_message("Informe a aposta usando apenas números.", ephemeral=True)
        if not APOSTA_MINIMA <= aposta <= APOSTA_MAXIMA:
            return await interaction.response.send_message(f"A aposta precisa ficar entre {APOSTA_MINIMA} e {APOSTA_MAXIMA} Denários.", ephemeral=True)
        alvo_id = int(match.group(0))
        if alvo_id == self.creator_id:
            return await interaction.response.send_message("Você não pode desafiar a si mesmo.", ephemeral=True)
        alvo = interaction.guild.get_member(alvo_id)
        if alvo is None:
            try:
                alvo = await interaction.guild.fetch_member(alvo_id)
            except discord.HTTPException:
                alvo = None
        if alvo is None or alvo.bot:
            return await interaction.response.send_message("Não encontrei esse membro ativo neste servidor.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        resultado = await self.cog.bot.db.coliseu_criar_convite(
            interaction.guild.id, interaction.channel.id, self.creator_id, alvo.id, aposta,
            nivel_minimo=NIVEL_MINIMO_DUELO,
            limite_diario=LIMITE_DUELOS_DIA,
            limite_par=LIMITE_DUELOS_PAR_DIA,
            max_aposta_dia=LIMITE_APOSTA_DIA,
            cooldown_segundos=COOLDOWN_DESAFIO_SEGUNDOS,
            diferenca_maxima_poder=DIFERENCA_MAXIMA_PODER_DECK,
        )
        if resultado["status"] != "ok":
            await interaction.followup.send(self.cog.mensagem_erro_convite(resultado), ephemeral=True)
            return
        duel_id = resultado["duel_id"]
        embed = discord.Embed(
            title="⚔️ Convite para o Coliseu",
            description=(
                f"{interaction.user.mention} desafiou {alvo.mention} para um duelo de cinco rodadas.\n\n"
                f"**Aposta por jogador:** {aposta} Denários\n"
                f"**Pote total:** {aposta * 2} Denários\n"
                f"**Poder dos decks:** {resultado['deck_power'][self.creator_id]} × {resultado['deck_power'][alvo.id]} "
                f"(diferença {resultado['power_gap']}/{DIFERENCA_MAXIMA_PODER_DECK})\n"
                "As duas apostas só serão travadas quando o convite for aceito.\n"
                "O convite expira em dois minutos."
            ),
            color=config.COR_OURO,
        )
        embed.set_footer(text=f"Coliseu de Cartas • Duelo #{duel_id} • Nível mínimo 5")
        try:
            message = await interaction.channel.send(
                content=alvo.mention,
                embed=embed,
                view=ConviteDueloView(duel_id),
                allowed_mentions=discord.AllowedMentions(users=[alvo], roles=False, everyone=False),
            )
            await self.cog.bot.db.coliseu_definir_mensagem_convite(duel_id, message.id)
        except discord.HTTPException:
            await self.cog.bot.db.coliseu_decidir_convite(duel_id, self.creator_id, False)
            log.exception("Não foi possível publicar convite do duelo #%s", duel_id)
            await interaction.followup.send("Não consegui publicar o convite no canal; nenhum Denário foi descontado.", ephemeral=True)
            return
        await interaction.followup.send(
            f"Convite publicado para {alvo.mention}. A aposta só será descontada se ele aceitar: {message.jump_url}",
            ephemeral=True,
        )


class ConviteDueloView(discord.ui.View):
    def __init__(self, duel_id: int):
        super().__init__(timeout=None)
        self.add_item(BotaoDueloColiseu("aceitar", duel_id))
        self.add_item(BotaoDueloColiseu("recusar", duel_id))
        self.add_item(BotaoDueloColiseu("cancelar", duel_id))


class BatalhaDueloView(discord.ui.View):
    def __init__(self, duel_id: int):
        super().__init__(timeout=None)
        self.add_item(BotaoDueloColiseu("jogar", duel_id))


class HallFamaView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", user_id: int):
        super().__init__(timeout=300)
        self.add_item(VoltarColiseuButton(cog, user_id))


class ColiseuCartas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_dynamic_items(BotaoDueloColiseu)
        self.monitorar_prazos.start()

    async def cog_unload(self):
        self.bot.remove_dynamic_items(BotaoDueloColiseu)
        self.monitorar_prazos.cancel()

    @tasks.loop(seconds=20)
    async def monitorar_prazos(self):
        try:
            expirados = await self.bot.db.coliseu_expirar_prazos()
            for item in expirados:
                await self._editar_mensagem_expirada(item)
        except Exception:
            log.exception("Falha ao verificar prazos dos duelos do Coliseu")

    @monitorar_prazos.before_loop
    async def _antes_monitorar(self):
        await self.bot.wait_until_ready()

    async def abrir_painel(self, interaction: discord.Interaction, editar: bool = False):
        user = await self.bot.db.get_user(interaction.user.id)
        level = nivel_por_xp(int(user["xp"] or 0))
        # Recupera cartas de conquistas antigas e entrega uma carta de cada patente já atingida.
        await self.bot.db.coliseu_entregar_kit_inicial(
            interaction.user.id,
            ["chefe_cervo_sombrio", "arma_lamina_peregrino", "magia_brasa_errante", "arma_agulha_astro", "covenant_sentinelas"],
        )
        await self.bot.db.coliseu_sincronizar_conquistas(interaction.user.id)
        patentes_liberadas = [c.id for c, (nivel_min, _) in zip(CARTAS_PATENTE, PATENTES) if level >= nivel_min]
        await self.bot.db.coliseu_reivindicar_patentes(interaction.user.id, patentes_liberadas)
        state = await self.bot.db.coliseu_estado_usuario(interaction.user.id)
        faltam = max(0, PITY_CARTAS - state["pity"])
        embed = discord.Embed(
            title="⚔️ Cartas do Coliseu",
            description=(
                "Transforme suas conquistas em coleção, monte seu deck e dispute Denários na arena.\n\n"
                f"**Nível:** {level} · **Denários:** {state['denarios']}\n"
                f"**Cartas:** {state['cartas']} · **Almas:** {state['almas']}\n"
                f"**Proteção contra azar:** {state['pity']}/10 cartas Comuns consecutivas "
                f"({'próxima carta garantida Rara+' if faltam == 0 else f'faltam {faltam} cartas Comuns'})\n"
                f"**Deck:** {state['deck']}/5 cartas\n\n"
                "**Pacote Fogueira:** 3 cartas por 120 Denários. Chances por carta: "
                "70% Comum · 22% Rara · 7% Épica · 1% Lendária.\n"
                "Duplicatas viram Almas; a Forja permite criar cartas específicas.\n\n"
                "**Duelos:** apostas de 10 a 500 Denários por jogador. Exigem nível 5 e um deck válido.\n"
                f"**Pareamento:** os decks precisam ter diferença máxima de {DIFERENCA_MAXIMA_PODER_DECK} pontos de poder total."
            ),
            color=config.COR_OURO,
        )
        embed.set_footer(text="As cartas são arte original gerada localmente. A coleção fica salva no SQLite.")
        view = PainelColiseuView(self, interaction.user.id)
        if editar:
            await interaction.response.edit_message(content=None, embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def executar_acao_menu(self, interaction: discord.Interaction, acao: str):
        user_id = interaction.user.id
        db = self.bot.db
        if acao == "colecao":
            rows = await db.coliseu_listar_colecao(user_id)
            cards = []
            for row in rows:
                carta = self._carta_da_linha(row)
                if carta:
                    cards.append((dict(row), carta))
            view = CollectionView(self, user_id, cards)
            return await interaction.response.edit_message(embed=view.embed(), view=view)
        if acao == "pacote":
            embed = discord.Embed(
                title="🔥 Pacote Fogueira",
                description=(
                    f"O pacote contém **3 cartas** e custa **{PRECO_PACOTE_FOGUEIRA} Denários**.\n\n"
                    "**Probabilidades por carta:**\n70% Comum · 22% Rara · 7% Épica · 1% Lendária\n\n"
                    "Após 10 cartas Comuns consecutivas, a próxima carta será garantidamente Rara ou melhor. "
                    "Duplicatas são convertidas automaticamente em Almas.\n\n"
                    "O desconto só acontece ao confirmar a abertura."
                ),
                color=config.COR_OURO,
            )
            view = ConfirmarPacoteView(self, user_id)
            return await interaction.response.edit_message(embed=embed, view=view)
        if acao == "deck":
            rows = await db.coliseu_listar_colecao(user_id)
            cards = [self._carta_da_linha(row) for row in rows]
            cards = [c for c in cards if c]
            if len(cards) < 5:
                return await interaction.response.edit_message(
                    embed=discord.Embed(title="🛡️ Monte sua coleção primeiro", description=f"Você possui {len(cards)} carta(s); precisa de pelo menos cinco diferentes para montar um deck. Abra pacotes ou registre conquistas aprovadas.", color=config.COR_OURO),
                    view=discord.ui.View(timeout=180).add_item(VoltarColiseuButton(self, user_id)),
                )
            antigo = await db.coliseu_obter_deck(user_id)
            view = DeckBuilderView(self, user_id, cards)
            if antigo:
                view.selecionadas = antigo[:5]
                view.rebuild()
            return await interaction.response.edit_message(embed=view.embed(), view=view)
        if acao == "forja":
            rows = await db.coliseu_listar_colecao(user_id)
            owned = {str(row["card_id"]) for row in rows}
            disponiveis = [c.para_dict() for c in CARTAS_PACOTE if c.id not in owned]
            state = await db.coliseu_estado_usuario(user_id)
            view = ForjaView(self, user_id, disponiveis, state["almas"])
            return await interaction.response.edit_message(embed=view.embed(), view=view)
        if acao == "duelo":
            modal = DesafioColiseuModal(self, user_id)
            return await interaction.response.send_modal(modal)
        if acao == "ranking":
            rows = await db.coliseu_ranking_duelos(10)
            embed = discord.Embed(title="🏆 Hall da Fama do Coliseu", color=config.COR_OURO)
            if not rows:
                embed.description = "Ainda não há duelos concluídos. O Hall da Fama aguarda seus primeiros gladiadores."
            else:
                linhas = []
                for pos, row in enumerate(rows, 1):
                    linhas.append(
                        f"`{pos:02}.` <@{row['user_id']}> — **{row['wins']} vitórias** / "
                        f"{row['duels']} duelos · {row['lucro']:+,} Denários"
                    )
                embed.description = "\n".join(linhas)
            embed.set_footer(text="Somente duelos concluídos entram no ranking. Empates e partidas canceladas não contam como vitória.")
            return await interaction.response.edit_message(embed=embed, view=HallFamaView(self, user_id))

    def _carta_da_linha(self, row) -> dict | None:
        card_id = str(row["card_id"])
        carta = get_carta(card_id)
        if carta:
            return carta.para_dict()
        if card_id.startswith("jogo_") and row["game_name"]:
            try:
                return carta_de_jogo_por_id(card_id, str(row["game_name"])).para_dict()
            except ValueError:
                return None
        return None

    async def mostrar_detalhe_carta(self, interaction: discord.Interaction, carta: dict):
        path = render_carta(carta)
        arquivo = discord.File(str(path), filename="carta.png")
        embed = discord.Embed(title=carta["nome"], color=config.COR_OURO)
        embed.set_image(url="attachment://carta.png")
        embed.add_field(name="Categoria", value=carta["categoria"], inline=True)
        embed.add_field(name="Raridade", value=carta["raridade"], inline=True)
        embed.add_field(name="Tipo", value=f"{EMOJIS_TIPO.get(carta['tipo'], '✦')} {carta['tipo']}", inline=True)
        embed.add_field(name="Poder", value=str(carta["poder"]), inline=True)
        embed.add_field(name="Custo de deck", value=str(carta["custo"]), inline=True)
        embed.add_field(name="Habilidade", value=_descricao_habilidade(carta), inline=False)
        if carta.get("descricao"):
            embed.add_field(name="Origem", value=carta["descricao"][:500], inline=False)
        await interaction.response.send_message(embed=embed, file=arquivo, ephemeral=True)

    def mensagem_erro_convite(self, resultado: dict) -> str:
        status = resultado.get("status")
        if status == "nivel":
            return f"Os dois duelistas precisam ter nível {NIVEL_MINIMO_DUELO} ou superior. O membro <@{resultado.get('user_id')}> ainda não cumpre o requisito."
        if status == "saldo":
            return f"O membro <@{resultado.get('user_id')}> não tem Denários suficientes para cobrir a aposta."
        if status == "sem_deck":
            return f"O membro <@{resultado.get('user_id')}> precisa montar e salvar um deck com cinco cartas antes de duelar."
        if status == "deck_invalido":
            return f"Não consegui validar o poder do deck de <@{resultado.get('user_id')}>. Peça para salvar o deck novamente."
        if status == "desbalanceado":
            return (
                f"Os decks estão muito distantes em poder ({resultado.get('poder_a')} × {resultado.get('poder_b')}). "
                f"A diferença máxima permitida é {resultado.get('limite', DIFERENCA_MAXIMA_PODER_DECK)}. "
                "Ajustem os decks antes de apostar."
            )
        if status == "ocupado":
            return "Um dos jogadores já tem um convite pendente ou um duelo em andamento."
        if status == "limite_diario":
            return f"O limite de {LIMITE_DUELOS_DIA} duelos por dia foi atingido por um dos jogadores."
        if status == "limite_par":
            return f"Vocês já disputaram {LIMITE_DUELOS_PAR_DIA} duelos nas últimas 24 horas."
        if status == "cooldown":
            return f"Aguarde {COOLDOWN_DESAFIO_SEGUNDOS} segundos antes de iniciar outro desafio."
        if status == "limite_aposta_dia":
            return f"O limite diário de apostas de {LIMITE_APOSTA_DIA} Denários foi atingido."
        if status == "aposta_invalida":
            return f"A aposta precisa ficar entre {resultado.get('minimo', APOSTA_MINIMA)} e {resultado.get('maximo', APOSTA_MAXIMA)} Denários."
        if status == "self":
            return "Você não pode desafiar a si mesmo."
        return "Não foi possível criar o convite. Confira deck, nível, saldo e limites do Coliseu."

    async def processar_botao_duelo(self, interaction: discord.Interaction, acao: str, duel_id: int):
        duel = await self.bot.db.coliseu_obter_duelo(duel_id)
        if duel is None:
            return await interaction.response.send_message("Este duelo não existe mais.", ephemeral=True)
        uid = interaction.user.id
        creator_id, opponent_id = int(duel["creator_id"]), int(duel["opponent_id"])
        if acao == "aceitar":
            if uid != opponent_id:
                return await interaction.response.send_message("Somente o membro convidado pode aceitar este duelo.", ephemeral=True)
            resultado = await self.bot.db.coliseu_decidir_convite(
                duel_id, uid, True, diferenca_maxima_poder=DIFERENCA_MAXIMA_PODER_DECK
            )
            if resultado["status"] != "ok":
                mensagens = {
                    "expired": "O convite expirou. Nenhum Denário foi descontado.",
                    "saldo": f"O membro <@{resultado.get('user_id')}> já não tem Denários suficientes. O duelo não começou.",
                    "sem_deck": f"O membro <@{resultado.get('user_id')}> já não tem um deck válido.",
                    "deck_invalido": f"Não consegui validar o deck de <@{resultado.get('user_id')}>. Nenhuma aposta foi travada.",
                    "desbalanceado": (
                        f"Os decks agora têm poder {resultado.get('poder_a')} × {resultado.get('poder_b')}, "
                        f"acima da diferença máxima de {resultado.get('limite', DIFERENCA_MAXIMA_PODER_DECK)}. "
                        "Nenhuma aposta foi travada. Salvem decks mais equilibrados e criem outro convite."
                    ),
                    "limite_diario": "O limite diário foi atingido antes do início. Nenhuma aposta foi travada.",
                    "limite_par": "Vocês já atingiram o limite de duelos entre si nas últimas 24 horas.",
                    "limite_aposta_dia": "Um dos jogadores atingiu o limite de apostas do dia. Nenhum Denário foi travado.",
                }
                return await interaction.response.send_message(mensagens.get(resultado["status"], "Este convite não pode mais ser aceito."), ephemeral=True)
            embed = await self.embed_duelo(duel_id, interaction.guild)
            try:
                await interaction.response.edit_message(embed=embed, view=BatalhaDueloView(duel_id))
            except discord.HTTPException:
                # A trava financeira já foi confirmada; tenta recuperar a mensagem original.
                log.exception("Duelos #%s iniciou, mas a interação não atualizou o convite; tentando reparar mensagem", duel_id)
                await self.atualizar_mensagem_duelo(duel_id, interaction.guild)
                if not interaction.response.is_done():
                    await interaction.response.send_message("O duelo foi iniciado e as apostas estão travadas. A mensagem pública foi reparada; use o botão Escolher carta.", ephemeral=True)
                else:
                    await interaction.followup.send("O duelo foi iniciado e as apostas estão travadas. A mensagem pública foi reparada; use o botão Escolher carta.", ephemeral=True)
                return
            await interaction.followup.send(
                f"Duelo #{duel_id} iniciado. As duas apostas de {int(duel['aposta'])} Denários foram travadas. "
                "Use **Escolher carta** para registrar sua primeira jogada em segredo.",
                ephemeral=True,
            )
            return
        if acao in {"recusar", "cancelar"}:
            if acao == "recusar" and uid != opponent_id:
                return await interaction.response.send_message("Somente o membro convidado pode recusar.", ephemeral=True)
            if acao == "cancelar" and uid != creator_id:
                return await interaction.response.send_message("Somente quem criou o convite pode cancelá-lo.", ephemeral=True)
            resultado = await self.bot.db.coliseu_decidir_convite(duel_id, uid, False)
            if resultado["status"] != "cancelled":
                return await interaction.response.send_message("Este convite já foi processado.", ephemeral=True)
            embed = discord.Embed(title="Convite encerrado", description="O convite foi recusado ou cancelado. Nenhum Denário foi movimentado.", color=discord.Color.dark_grey())
            return await interaction.response.edit_message(embed=embed, view=None)
        if acao == "jogar":
            if uid not in {creator_id, opponent_id}:
                return await interaction.response.send_message("Você não participa desta batalha.", ephemeral=True)
            if duel["status"] != "active":
                return await interaction.response.send_message("Este duelo não está mais ativo.", ephemeral=True)
            cards = await self.bot.db.coliseu_cartas_disponiveis(duel_id, uid)
            if not cards:
                return await interaction.response.send_message("Você já utilizou suas cinco cartas ou não há escolhas disponíveis.", ephemeral=True)
            embed = discord.Embed(
                title=f"🃏 Escolha secreta · Rodada {duel['current_round']}/5",
                description="Sua escolha não será revelada até o adversário registrar a dele. Cada carta só pode ser usada uma vez.",
                color=config.COR_OURO,
            )
            return await interaction.response.send_message(embed=embed, view=SelecaoCartaView(self, duel_id, uid, cards), ephemeral=True)

    async def resolver_rodada(self, payload: dict) -> str:
        duel = payload["duel"]
        a, b = int(duel["creator_id"]), int(duel["opponent_id"])
        card_a, card_b = payload["cards"][a], payload["cards"][b]
        historico = await self.bot.db.coliseu_historico_rodadas(int(duel["id"]))
        previous_a = previous_b = None
        if historico:
            winner = str(historico[-1]["winner_side"])
            if winner == "a":
                previous_a, previous_b = "venceu", "perdeu"
            elif winner == "b":
                previous_a, previous_b = "perdeu", "venceu"
        result = resolver_rodada(card_a, card_b, int(payload["round_no"]), previous_a, previous_b)
        narration = narrar_rodada(int(payload["round_no"]), card_a, card_b, result)
        result.update({"card_a": card_a, "card_b": card_b, "narration": narration})
        final = await self.bot.db.coliseu_resolver_rodada(int(duel["id"]), int(payload["round_no"]), result)
        if final["status"] == "round_ok":
            return f"Rodada {payload['round_no']} resolvida. A próxima escolha já está disponível no painel público."
        if final["status"] == "vitoria":
            return f"Duelo encerrado. Vencedor: <@{final['winner_id']}> · prêmio: {final['payout']} Denários · {final['burned']} Denários foram removidos do jogo."
        if final["status"] == "empate":
            return "O duelo terminou empatado. As duas apostas foram devolvidas integralmente."
        return "A rodada foi processada. Consulte o painel público para ver o estado atualizado."

    async def embed_duelo(self, duel_id: int, guild: discord.Guild | None = None) -> discord.Embed:
        duel = await self.bot.db.coliseu_obter_duelo(duel_id)
        if not duel:
            return discord.Embed(title="Duelo indisponível", color=discord.Color.dark_grey())
        a, b = int(duel["creator_id"]), int(duel["opponent_id"])
        nome_a = self._nome_membro(guild, a)
        nome_b = self._nome_membro(guild, b)
        rounds = await self.bot.db.coliseu_historico_rodadas(duel_id)
        deck_a = await self.bot.db.coliseu_deck_da_partida(duel_id, a)
        deck_b = await self.bot.db.coliseu_deck_da_partida(duel_id, b)
        poder_a = poder_total_deck(deck_a)
        poder_b = poder_total_deck(deck_b)
        wins_a = sum(r["winner_side"] == "a" for r in rounds)
        wins_b = sum(r["winner_side"] == "b" for r in rounds)
        embed = discord.Embed(
            title=f"⚔️ Coliseu · Duelo #{duel_id}",
            description=(
                f"**{nome_a}** × **{nome_b}**\n"
                f"Aposta travada: **{int(duel['aposta'])} Denários por jogador** · Pote: **{int(duel['aposta']) * 2}**\n"
                f"Poder base dos decks: **{poder_a} × {poder_b}** · Diferença: **{abs(poder_a - poder_b)}**\n"
                f"Placar: **{wins_a} × {wins_b}** · Rodada {min(int(duel['current_round']), 5)}/5"
            ),
            color=config.COR_OURO,
        )
        for row in rounds:
            if row["winner_side"] == "a":
                vencedor = nome_a
            elif row["winner_side"] == "b":
                vencedor = nome_b
            else:
                vencedor = "Empate"
            extra_a = []
            extra_b = []
            if int(row["type_bonus_a"]):
                extra_a.append(f"tipo +{row['type_bonus_a']}")
            if int(row["skill_bonus_a"]):
                extra_a.append(f"habilidade +{row['skill_bonus_a']}")
            if int(row["type_bonus_b"]):
                extra_b.append(f"tipo +{row['type_bonus_b']}")
            if int(row["skill_bonus_b"]):
                extra_b.append(f"habilidade +{row['skill_bonus_b']}")
            embed.add_field(
                name=f"Rodada {row['round_no']} · {vencedor}",
                value=(
                    f"**{row['card_a_name']}** — {row['power_a']} ({', '.join(extra_a) or 'sem bônus'})\n"
                    f"**{row['card_b_name']}** — {row['power_b']} ({', '.join(extra_b) or 'sem bônus'})\n"
                    f"_{row['narration']}_"
                )[:1024],
                inline=False,
            )
        if duel["status"] == "active":
            embed.add_field(
                name="Próxima ação",
                value="Os dois duelistas devem escolher uma carta em segredo. A revelação acontece quando ambas forem registradas.",
                inline=False,
            )
            embed.set_footer(text="Prazo de inatividade: 3 minutos. Se a rodada expirar, as duas apostas são devolvidas.")
        elif duel["status"] == "finished":
            if duel["winner_id"]:
                embed.add_field(name="Resultado", value=f"🏆 Vencedor: <@{duel['winner_id']}>\nPrêmio: **{duel['payout']} Denários**\nRemovidos do jogo: **{duel['burned']} Denários**", inline=False)
            else:
                embed.add_field(name="Resultado", value="Empate. As duas apostas foram devolvidas.", inline=False)
        elif duel["status"] == "cancelled":
            embed.add_field(name="Resultado", value="A partida expirou por inatividade. As duas apostas foram devolvidas integralmente.", inline=False)
        else:
            embed.add_field(name="Estado", value=f"{duel['status']}: {duel['end_reason']}", inline=False)
        embed.set_footer(text="Cartas do Coliseu · cálculo validado pelo servidor")
        return embed

    @staticmethod
    def _nome_membro(guild: discord.Guild | None, user_id: int) -> str:
        if guild:
            membro = guild.get_member(user_id)
            if membro:
                return discord.utils.escape_markdown(membro.display_name)
        return f"Jogador {user_id}"

    async def atualizar_mensagem_duelo(self, duel_id: int, guild: discord.Guild | None = None):
        duel = await self.bot.db.coliseu_obter_duelo(duel_id)
        if not duel or not duel["message_id"]:
            return
        channel = self.bot.get_channel(int(duel["channel_id"]))
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(int(duel["channel_id"]))
            except discord.HTTPException:
                return
        try:
            message = await channel.fetch_message(int(duel["message_id"]))
            embed = await self.embed_duelo(duel_id, guild or getattr(channel, "guild", None))
            view = BatalhaDueloView(duel_id) if duel["status"] == "active" else None
            await message.edit(embed=embed, view=view)
        except discord.HTTPException:
            log.warning("Não consegui atualizar a mensagem pública do duelo #%s", duel_id)

    async def _editar_mensagem_expirada(self, item: dict):
        channel = self.bot.get_channel(int(item["channel_id"]))
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(int(item["channel_id"]))
            except discord.HTTPException:
                return
        if not item.get("message_id"):
            return
        try:
            message = await channel.fetch_message(int(item["message_id"]))
            duel_id = int(item["id"])
            if item["status"] == "expired":
                embed = discord.Embed(title=f"Convite #{duel_id} expirado", description="O convite não foi aceito em dois minutos. Nenhum Denário foi descontado.", color=discord.Color.dark_grey())
            else:
                embed = await self.embed_duelo(duel_id, getattr(channel, "guild", None))
            await message.edit(embed=embed, view=None)
        except discord.HTTPException:
            pass

    async def cog_command_error(self, ctx, error):
        log.exception("Erro no módulo Cartas do Coliseu", exc_info=error)


async def setup(bot: commands.Bot):
    await bot.add_cog(ColiseuCartas(bot))
