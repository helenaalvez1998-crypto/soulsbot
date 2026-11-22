"""Coliseu de cartas: coleção, pacotes, forja, decks e duelos com apostas.

Todas as decisões de jogo e movimentações de moeda são validadas no servidor e
persistidas no SQLite. Nenhum resultado depende dos valores enviados pelo cliente.
"""
from __future__ import annotations

import asyncio
import io
import logging
import re
import time
from pathlib import Path

import discord
from discord.ext import commands, tasks

import config
from levels import PATENTES, nivel_por_xp
from sistemas.arte_cartas import (
    RARIDADES_MOLDURA,
    caminho_moldura_personalizada,
    listar_molduras_personalizadas,
    limpar_cache_molduras,
    remover_moldura_personalizada,
    render_carta,
    render_carta_bytes,
    render_deck_preview_bytes,
    render_pacote,
    render_previa_template,
    salvar_moldura_personalizada,
)
from sistemas import templates_cartas
from sistemas.atelie_coliseu import ArteInvalida, TAMANHO_MAXIMO_UPLOAD, gerar_prompt_carta, normalizar_imagem_carta
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
LIMITE_PACOTES_DIA = 3
COOLDOWN_DESAFIO_SEGUNDOS = 60
TEMPO_CONVITE_SEGUNDOS = 120
TEMPO_RODADA_SEGUNDOS = 40  # cinco escolhas simultâneas cabem em cerca de 2–4 minutos
DIFERENCA_MAXIMA_PODER_DECK = 4


def _formatar_carta(carta: dict) -> str:
    selo = " · **ÚNICA DO SERVIDOR**" if carta.get("raridade") == "Primordial" else ""
    return (
        f"{EMOJIS_TIPO.get(carta.get('tipo'), '✦')} **{carta.get('nome', 'Carta')}** "
        f"· {carta.get('raridade')} · Poder {carta.get('poder')} · Custo {carta.get('custo')}" + selo
    )


def _descricao_habilidade(carta: dict) -> str:
    from sistemas.cartas import HABILIDADES
    habilidade = HABILIDADES.get(str(carta.get("habilidade")), {})
    return f"**{habilidade.get('nome', 'Sem habilidade')}** — {habilidade.get('texto', '')}"


class BotaoDueloColiseu(discord.ui.DynamicItem[discord.ui.Button], template=r"coliseu_cartas:(?P<acao>aceitar|recusar|cancelar|jogar|revanche):(?P<duelo>[0-9]+)"):
    """Botões dinâmicos; continuam válidos após reiniciar o bot."""

    ROTULOS = {
        "aceitar": ("Aceitar duelo", "⚔️", discord.ButtonStyle.success),
        "recusar": ("Recusar", "✖️", discord.ButtonStyle.secondary),
        "cancelar": ("Cancelar convite", "🛑", discord.ButtonStyle.secondary),
        "jogar": ("Escolher carta", "🃏", discord.ButtonStyle.primary),
        "revanche": ("Desafiar novamente", "🔁", discord.ButtonStyle.success),
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


class FecharColiseuButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(label="Fechar painel", emoji="✖️", style=discord.ButtonStyle.secondary, row=4)
        self.user_id = int(user_id)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro membro.", ephemeral=True)
        await interaction.response.edit_message(
            content="Painel do Coliseu fechado. Use `/nara` para abrir novamente.",
            embed=None, attachments=[], view=None,
        )


class PainelColiseuView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", user_id: int, callback_voltar=None):
        super().__init__(timeout=600)
        self.user_id = int(user_id)
        self.callback_voltar = callback_voltar
        self.add_item(BotaoMenuCartas(cog, user_id, "colecao", "Minha coleção", "🃏", discord.ButtonStyle.primary, 0))
        self.add_item(BotaoMenuCartas(cog, user_id, "pacote", "Pacote Fogueira", "🔥", discord.ButtonStyle.success, 0))
        self.add_item(BotaoMenuCartas(cog, user_id, "deck", "Montar deck", "🛡️", discord.ButtonStyle.primary, 1))
        self.add_item(BotaoMenuCartas(cog, user_id, "forja", "Forja de Almas", "💎", discord.ButtonStyle.secondary, 1))
        self.add_item(BotaoMenuCartas(cog, user_id, "duelo", "Desafiar jogador", "⚔️", discord.ButtonStyle.danger, 2))
        self.add_item(BotaoMenuCartas(cog, user_id, "ranking", "Hall da Fama", "🏆", discord.ButtonStyle.secondary, 2))
        self.add_item(BotaoMenuCartas(cog, user_id, "missoes", "Missões semanais", "📜", discord.ButtonStyle.secondary, 3))
        if callback_voltar is not None:
            from painel_navegacao import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")
        self.add_item(FecharColiseuButton(user_id))

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
        callback_voltar = getattr(self.cog, "_retornos_nara", {}).get(self.user_id)
        await self.cog.abrir_painel(interaction, editar=True, callback_voltar=callback_voltar)


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
        selecionada = self.parent_view.cards_by_id.get(self.values[0])
        if selecionada is None:
            return await interaction.response.send_message("Não encontrei essa carta na sua coleção.", ephemeral=True)
        _, carta = selecionada
        await self.parent_view.cog.mostrar_detalhe_carta(
            interaction, carta, self.parent_view.user_id, collection_view=self.parent_view, editar=True,
        )


class VoltarColecaoButton(discord.ui.Button):
    def __init__(self, collection_view: "CollectionView"):
        # Fica ao lado de "Gerar prompt de arte" para nunca desaparecer em uma segunda linha.
        super().__init__(label="Voltar à coleção", emoji="⬅️", style=discord.ButtonStyle.secondary, row=0)
        self.collection_view = collection_view

    async def callback(self, interaction: discord.Interaction):
        view = self.collection_view
        if interaction.user.id != view.user_id:
            return await interaction.response.send_message("Esta coleção pertence a outro membro.", ephemeral=True)
        await interaction.response.edit_message(embed=view.embed(), attachments=[], view=view)


class PersonalizarCartaButton(discord.ui.Button):
    def __init__(self, cog: "ColiseuCartas", user_id: int, carta: dict, collection_view: "CollectionView"):
        super().__init__(label="Gerar prompt de arte", emoji="🎨", style=discord.ButtonStyle.primary, row=0)
        self.cog = cog
        self.user_id = int(user_id)
        self.carta = dict(carta)
        self.collection_view = collection_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Essa carta pertence à coleção de outro membro.", ephemeral=True)
        prompt = gerar_prompt_carta(self.carta)
        nome_base = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(self.carta.get("nome") or "carta"))
        nome_base = nome_base.strip("_-")[:48] or "carta"
        arquivo_prompt = discord.File(
            io.BytesIO(prompt.encode("utf-8")),
            filename=f"prompt_atelie_{nome_base}.txt",
        )
        embed = discord.Embed(
            title="🎨 Ateliê do Coliseu · Prompt pronto",
            description=(
                "O prompt completo foi enviado em um arquivo `.txt` na sua mensagem privada. "
                "Abra o arquivo, copie o conteúdo e cole no gerador de imagens de sua preferência.\n\n"
                "A arte deve conter somente a ilustração; moldura, nome e atributos oficiais são aplicados pelo SoulsBot."
            ),
            color=config.COR_OURO,
        )
        embed.add_field(
            name="Carta",
            value=f"**{self.carta.get('nome', 'Carta')}** · {self.carta.get('raridade', 'Raridade')} · {self.carta.get('tipo', 'Tipo')}",
            inline=False,
        )
        embed.set_footer(text="O prompt é anexado como TXT para evitar o limite de 4.096 caracteres dos embeds do Discord.")
        await interaction.response.edit_message(
            embed=embed, attachments=[],
            view=EnviarArteAtelieView(
                self.cog, self.user_id, self.carta, self.collection_view,
            ),
        )
        await interaction.followup.send(
            content="📄 **Prompt completo da sua carta:**",
            file=arquivo_prompt,
            ephemeral=True,
        )


class RemoverArtePersonalizadaButton(discord.ui.Button):
    def __init__(self, cog: "ColiseuCartas", user_id: int, carta: dict, collection_view: "CollectionView"):
        super().__init__(label="Usar arte original", emoji="↩️", style=discord.ButtonStyle.secondary, row=1)
        self.cog = cog
        self.user_id = int(user_id)
        self.carta = dict(carta)
        self.collection_view = collection_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Essa carta pertence à coleção de outro membro.", ephemeral=True)
        await self.cog.bot.db.coliseu_atelie_remover_arte_ativa(self.user_id, str(self.carta["id"]))
        await self.cog.mostrar_detalhe_carta(
            interaction, self.carta, self.user_id, collection_view=self.collection_view, editar=True,
            mensagem_status="Arte personalizada desativada. Sua carta voltou à ilustração original.",
        )


class VoltarCartaAtelieButton(discord.ui.Button):
    def __init__(self, cog: "ColiseuCartas", user_id: int, carta: dict, collection_view: "CollectionView"):
        super().__init__(label="Voltar à carta", emoji="⬅️", style=discord.ButtonStyle.secondary, row=0)
        self.cog = cog
        self.user_id = int(user_id)
        self.carta = dict(carta)
        self.collection_view = collection_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro membro.", ephemeral=True)
        await self.cog.mostrar_detalhe_carta(
            interaction, self.carta, self.user_id, collection_view=self.collection_view, editar=True,
        )


class DetalheCartaView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", user_id: int, carta: dict, possui_arte: bool,
                 collection_view: "CollectionView"):
        super().__init__(timeout=600)
        self.add_item(PersonalizarCartaButton(cog, user_id, carta, collection_view))
        if possui_arte:
            self.add_item(RemoverArtePersonalizadaButton(cog, user_id, carta, collection_view))
        self.add_item(VoltarColecaoButton(collection_view))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        owner_id = self.children[0].user_id if self.children else None
        if interaction.user.id != owner_id:
            await interaction.response.send_message("Esta carta pertence a outro membro.", ephemeral=True)
            return False
        return True


class EnviarArteAtelieButton(discord.ui.Button):
    def __init__(self, cog: "ColiseuCartas", user_id: int, carta: dict):
        super().__init__(label="Enviar minha arte", emoji="📤", style=discord.ButtonStyle.success, row=0)
        self.cog = cog
        self.user_id = int(user_id)
        self.carta = dict(carta)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este pedido de arte pertence a outro membro.", ephemeral=True)
        await self.cog.iniciar_upload_atelie(interaction, self.carta)


class EnviarArteAtelieView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", user_id: int, carta: dict,
                 collection_view: "CollectionView"):
        super().__init__(timeout=600)
        self.add_item(EnviarArteAtelieButton(cog, user_id, carta))
        self.add_item(VoltarCartaAtelieButton(cog, user_id, carta, collection_view))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.children and interaction.user.id != self.children[0].user_id:
            await interaction.response.send_message("Este Ateliê pertence a outro membro.", ephemeral=True)
            return False
        return True


class AtelieReviewButton(discord.ui.DynamicItem[discord.ui.Button], template=r"coliseu_atelie:(?P<acao>aprovar|rejeitar):(?P<arte_id>[0-9]+)"):
    def __init__(self, acao: str, arte_id: int):
        aprovar = acao == "aprovar"
        super().__init__(discord.ui.Button(
            label="Aprovar arte" if aprovar else "Rejeitar arte",
            emoji="✅" if aprovar else "✖️",
            style=discord.ButtonStyle.success if aprovar else discord.ButtonStyle.danger,
            custom_id=f"coliseu_atelie:{acao}:{int(arte_id)}",
        ))
        self.acao = str(acao)
        self.arte_id = int(arte_id)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        return cls(match["acao"], int(match["arte_id"]))

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("ColiseuCartas")
        if cog is None:
            return await interaction.response.send_message("O Ateliê está temporariamente indisponível.", ephemeral=True)
        if not isinstance(interaction.user, discord.Member) or not cog._pode_revisar_arte(interaction.user):
            return await interaction.response.send_message("Somente a moderação pode avaliar artes do Coliseu.", ephemeral=True)
        if self.acao == "aprovar":
            return await cog.revisar_arte_atelie(interaction, self.arte_id, True)
        return await interaction.response.send_modal(RejeitarArteAtelieModal(cog, self.arte_id))


class AtelieReviewView(discord.ui.View):
    def __init__(self, arte_id: int):
        super().__init__(timeout=None)
        self.add_item(AtelieReviewButton("aprovar", arte_id))
        self.add_item(AtelieReviewButton("rejeitar", arte_id))


class RejeitarArteAtelieModal(discord.ui.Modal, title="Rejeitar arte personalizada"):
    motivo = discord.ui.TextInput(
        label="Motivo da rejeição",
        placeholder="Explique o que precisa ser corrigido.",
        min_length=5,
        max_length=500,
        required=True,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, cog: "ColiseuCartas", arte_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.arte_id = int(arte_id)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.revisar_arte_atelie(interaction, self.arte_id, False, str(self.motivo.value))


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
        self.cards_by_id = {carta["id"]: (row, carta) for row, carta in cards}
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


class RevelarProximaCartaButton(discord.ui.Button):
    def __init__(self, parent_view: "RevelacaoPacoteView"):
        self.parent_view = parent_view
        super().__init__(label="Revelar próxima", emoji="✨", style=discord.ButtonStyle.primary,
                         disabled=parent_view.indice >= len(parent_view.cards) - 1, row=0)

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.revelar_proxima(interaction)


class RevelarTodasCartasButton(discord.ui.Button):
    def __init__(self, parent_view: "RevelacaoPacoteView"):
        self.parent_view = parent_view
        label = "Ver resumo do pacote" if parent_view.indice >= len(parent_view.cards) - 1 else "Revelar todas"
        super().__init__(label=label, emoji="⚡", style=discord.ButtonStyle.success, row=0)

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.revelar_todas(interaction)


class RevelacaoPacoteView(discord.ui.View):
    """Revela as três cartas em sequência, mas permite pular a animação."""

    def __init__(self, cog: "ColiseuCartas", user_id: int, resultado: dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = int(user_id)
        self.itens = list(resultado["cards"])
        self.cards = [item["carta"] for item in self.itens]
        self.resultado = dict(resultado)
        self.indice = 0
        self.todas_reveladas = False
        self._reveal_lock = asyncio.Lock()
        self.rebuild()

    def rebuild(self):
        self.clear_items()
        if not self.todas_reveladas:
            if self.indice < len(self.cards) - 1:
                self.add_item(RevelarProximaCartaButton(self))
                self.add_item(RevelarTodasCartasButton(self))
            else:
                self.add_item(RevelarTodasCartasButton(self))
        self.add_item(VoltarColiseuButton(self.cog, self.user_id))

    def embed_carta_atual(self) -> discord.Embed:
        item = self.itens[self.indice]
        carta = item["carta"]
        extra = (
            f"\n\n↳ Repetida: convertida em **{item['almas']} Almas**."
            if item["duplicata"] else (
                "\n\n✦ **PRIMORDIAL RESGATADA!** Esta carta é única em todo o servidor e não pode ser transferida ou consumida."
                if item.get("primordial") else "\n\n✨ Nova carta adicionada à coleção!"
            )
        )
        embed = discord.Embed(
            title=f"🔥 Pacote Fogueira · Carta {self.indice + 1}/{len(self.cards)}",
            description=f"{_formatar_carta(carta)}\n\n{_descricao_habilidade(carta)}{extra}",
            color=config.COR_OURO,
        )
        embed.set_image(url="attachment://carta.png")
        embed.add_field(name="Almas neste pacote", value=f"+{self.resultado['almas_ganhas']}", inline=True)
        embed.add_field(name="Saldo restante", value=f"{self.resultado['saldo']} Denários", inline=True)
        embed.add_field(name="Pity", value=f"{self.resultado['pity']}/10", inline=True)
        if self.indice == len(self.cards) - 1:
            embed.set_footer(text="Última carta revelada · Você pode ver o pacote completo ou voltar ao Coliseu.")
        else:
            embed.set_footer(text="Revele a próxima carta ou veja as três de uma vez. A compra já foi concluída com segurança.")
        return embed

    def embed_todas(self) -> discord.Embed:
        linhas = []
        for i, item in enumerate(self.itens, 1):
            carta = item["carta"]
            linha = f"**{i}.** {_formatar_carta(carta)}"
            if item["duplicata"]:
                linha += f" · repetida: +{item['almas']} Almas"
            else:
                linha += " · nova"
            linhas.append(linha)
        embed = discord.Embed(
            title="🔥 Pacote Fogueira · Todas as cartas",
            description="\n\n".join(linhas),
            color=config.COR_OURO,
        )
        embed.set_image(url="attachment://pacote_completo.png")
        embed.add_field(name="Almas recebidas", value=f"+{self.resultado['almas_ganhas']}", inline=True)
        embed.add_field(name="Saldo restante", value=f"{self.resultado['saldo']} Denários", inline=True)
        embed.add_field(name="Pacotes restantes hoje", value=str(self.resultado.get("pacotes_restantes", 0)), inline=True)
        embed.set_footer(text="As três cartas já estão salvas na sua coleção.")
        return embed

    async def revelar_proxima(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Esta abertura pertence a outro membro.", ephemeral=True)
        async with self._reveal_lock:
            if self.todas_reveladas or self.indice >= len(self.cards) - 1:
                return await interaction.response.send_message("As três cartas já foram reveladas.", ephemeral=True)
            self.indice += 1
            self.rebuild()
            path = render_carta(self.cards[self.indice])
            arquivo = discord.File(str(path), filename="carta.png")
            await interaction.response.edit_message(
                embed=self.embed_carta_atual(), attachments=[arquivo], view=self,
            )

    async def revelar_todas(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Esta abertura pertence a outro membro.", ephemeral=True)
        async with self._reveal_lock:
            if self.todas_reveladas:
                return await interaction.response.send_message("O resumo deste pacote já está aberto.", ephemeral=True)
            self.todas_reveladas = True
            self.rebuild()
            path = render_pacote(self.cards)
            arquivo = discord.File(str(path), filename="pacote_completo.png")
            await interaction.response.edit_message(
                embed=self.embed_todas(), attachments=[arquivo], view=self,
            )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Esta abertura é privada.", ephemeral=True)
            return False
        return True


class AtualizarMissoesButton(discord.ui.Button):
    def __init__(self, parent_view: "MissaoSemanalView"):
        self.parent_view = parent_view
        super().__init__(label="Atualizar progresso", emoji="🔄", style=discord.ButtonStyle.primary, row=0)

    async def callback(self, interaction: discord.Interaction):
        view = self.parent_view
        if interaction.user.id != view.user_id:
            return await interaction.response.send_message("Estas missões pertencem a outro membro.", ephemeral=True)
        view.dados = await view.cog.bot.db.coliseu_missoes_semanais(view.user_id)
        await interaction.response.edit_message(embed=view.embed(), view=view)


class MissaoSemanalView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", user_id: int, dados: dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = int(user_id)
        self.dados = dados
        self.add_item(AtualizarMissoesButton(self))
        self.add_item(VoltarColiseuButton(cog, user_id))

    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📜 Missões semanais do Coliseu",
            description=(
                "Objetivos opcionais, sem sequência diária e sem punição por ficar ausente. "
                "As Almas são creditadas automaticamente quando a meta é concluída.\n\n"
                f"**Semana:** {self.dados['week_key']}"
            ),
            color=config.COR_OURO,
        )
        for item in self.dados["missions"]:
            progresso = int(item["progress"])
            meta = int(item["goal"])
            preenchido = "■" * progresso + "□" * max(0, meta - progresso)
            estado = "Recompensa recebida" if item["claimed"] else "Em andamento"
            if progresso >= meta:
                estado = "Concluída" if item["claimed"] else "Meta alcançada"
            embed.add_field(
                name=f"{item['title']} · {preenchido}",
                value=(
                    f"{item['description']}\n"
                    f"Progresso: **{progresso}/{meta}** · Recompensa: **{item['reward_almas']} Almas**\n"
                    f"_{estado}_"
                ),
                inline=False,
            )
        embed.set_footer(text="As missões reiniciam na semana seguinte. Nenhuma atividade é obrigatória.")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Estas missões são privadas. Abra seu próprio Coliseu pela Nara.", ephemeral=True)
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
            LIMITE_PACOTES_DIA,
        )
        if resultado["status"] == "sem_saldo":
            return await interaction.followup.send(
                f"Você tem {resultado['saldo']} Denários; o pacote custa {PRECO_PACOTE_FOGUEIRA}.", ephemeral=True
            )
        if resultado["status"] == "limite_pacotes_dia":
            return await interaction.followup.send(
                f"Você já abriu {LIMITE_PACOTES_DIA} pacotes nas últimas 24 horas. "
                "O limite protege seus Denários; você poderá abrir outro quando uma abertura sair da janela de 24 horas.",
                ephemeral=True,
            )
        if resultado["status"] != "ok":
            return await interaction.followup.send("Não consegui abrir o pacote. Nenhum Denário foi descontado.", ephemeral=True)
        view_revelacao = RevelacaoPacoteView(view.cog, view.user_id, resultado)
        primeira_carta = render_carta(view_revelacao.cards[0])
        arquivo = discord.File(str(primeira_carta), filename="carta.png")
        await interaction.followup.send(
            embed=view_revelacao.embed_carta_atual(), file=arquivo,
            view=view_revelacao, ephemeral=True,
        )


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
                "Escolha cinco cartas, uma por vez. O deck aceita até 12 pontos de custo e no máximo uma Lendária. Cartas Primordiais são únicas e não podem ser transferidas ou consumidas.\n"
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
            "expirado": "O prazo de escolha terminou. A partida será encerrada e as duas apostas serão devolvidas.",
        }
        await interaction.followup.send(mensagens.get(resultado["status"], "Não consegui registrar sua jogada."), ephemeral=True)


class SelecaoCartaView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", duel_id: int, user_id: int, cards: list[dict]):
        super().__init__(timeout=TEMPO_RODADA_SEGUNDOS)
        self.add_item(SelecaoCartaJogo(cog, duel_id, user_id, cards))


class MembrosOnlineSelect(discord.ui.Select):
    """Lista paginada de membros conectados e aptos a receber um desafio."""

    def __init__(self, parent_view: "DesafioColiseuView"):
        self.parent_view = parent_view
        start = parent_view.page * parent_view.page_size
        page_members = parent_view.members[start:start + parent_view.page_size]
        options = []
        for item in page_members:
            member = item["member"]
            status_label = item["status_label"]
            options.append(discord.SelectOption(
                label=member.display_name[:100],
                value=str(member.id),
                description=f"{status_label} · Nível {item['nivel']} · Deck {item['poder']} de poder"[:100],
                emoji=item["status_emoji"],
            ))
        super().__init__(
            placeholder="Escolha um membro conectado...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.parent_view
        if interaction.user.id != view.user_id:
            return await interaction.response.send_message("Esta lista pertence a outro membro.", ephemeral=True)
        target_id = int(self.values[0])
        guild = interaction.guild
        target = guild.get_member(target_id) if guild else None
        if target is None or target.bot or target.status not in (discord.Status.online, discord.Status.idle, discord.Status.dnd):
            return await interaction.response.send_message(
                "Esse membro não está mais conectado. Atualize a lista e escolha outra pessoa.", ephemeral=True
            )
        await interaction.response.send_modal(DesafioColiseuModal(view.cog, view.user_id, target.id))


class PaginaDesafioButton(discord.ui.Button):
    def __init__(self, parent_view: "DesafioColiseuView", direcao: int):
        self.parent_view = parent_view
        self.direcao = int(direcao)
        super().__init__(
            label="Anterior" if direcao < 0 else "Próxima",
            emoji="◀️" if direcao < 0 else "▶️",
            style=discord.ButtonStyle.secondary,
            row=1,
            disabled=(parent_view.page == 0 if direcao < 0 else parent_view.page + 1 >= parent_view.pages),
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.parent_view
        if interaction.user.id != view.user_id:
            return await interaction.response.send_message("Esta lista pertence a outro membro.", ephemeral=True)
        view.page = max(0, min(view.pages - 1, view.page + self.direcao))
        view.rebuild()
        await interaction.response.edit_message(embed=view.embed(), view=view)


class AtualizarMembrosOnlineButton(discord.ui.Button):
    def __init__(self, parent_view: "DesafioColiseuView"):
        self.parent_view = parent_view
        super().__init__(label="Atualizar lista", emoji="🔄", style=discord.ButtonStyle.primary, row=1)

    async def callback(self, interaction: discord.Interaction):
        view = self.parent_view
        if interaction.user.id != view.user_id:
            return await interaction.response.send_message("Esta lista pertence a outro membro.", ephemeral=True)
        await view.cog.abrir_selecao_desafio(interaction, view.user_id)


class DesafioColiseuView(discord.ui.View):
    page_size = 25

    def __init__(self, cog: "ColiseuCartas", user_id: int, members: list[dict], total_conectados: int):
        super().__init__(timeout=180)
        self.cog = cog
        self.user_id = int(user_id)
        self.members = list(members)
        self.total_conectados = int(total_conectados)
        self.page = 0
        self.pages = max(1, (len(self.members) + self.page_size - 1) // self.page_size)
        self.rebuild()

    def rebuild(self):
        self.clear_items()
        if self.members:
            self.add_item(MembrosOnlineSelect(self))
        if self.pages > 1:
            self.add_item(PaginaDesafioButton(self, -1))
            self.add_item(PaginaDesafioButton(self, 1))
        self.add_item(AtualizarMembrosOnlineButton(self))
        self.add_item(VoltarColiseuButton(self.cog, self.user_id))

    def embed(self) -> discord.Embed:
        embed = discord.Embed(title="⚔️ Desafiar jogador", color=config.COR_OURO)
        if not self.members:
            if self.total_conectados:
                embed.description = (
                    f"Há **{self.total_conectados}** membro(s) conectado(s), mas nenhum está disponível para duelo agora.\n\n"
                    "Nesta fase, basta ter uma conta no Coliseu, um deck válido de cinco cartas e não estar em outro duelo. "
                    "Não exigimos nível mínimo, saldo mínimo nem equilíbrio de poder entre os decks."
                )
            else:
                embed.description = (
                    "Não encontrei membros conectados neste momento. Quando alguém estiver online, "
                    "aparecerá nesta lista. Você pode atualizá-la sem sair do painel."
                )
        else:
            embed.description = (
                f"**{len(self.members)}** membro(s) conectado(s) e apto(s) para duelo.\n\n"
                 "Escolha quem deseja desafiar. A aposta é opcional: use 0 para um duelo amistoso. "
                "A lista inclui membros Online, Ausentes e em Não perturbe."
            )
            if self.pages > 1:
                embed.set_footer(text=f"Página {self.page + 1}/{self.pages} · A lista mostra até 25 membros por página")
            else:
                embed.set_footer(text="Modo inicial: sem nível mínimo ou diferença máxima de poder; deck válido continua necessário.")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Esta lista é privada. Abra seu painel pelo `/nara`.", ephemeral=True)
            return False
        return True


class DesafioColiseuModal(discord.ui.Modal, title="Definir aposta do duelo"):
    def __init__(self, cog: "ColiseuCartas", creator_id: int, target_id: int):
        super().__init__(timeout=180)
        self.cog = cog
        self.creator_id = int(creator_id)
        self.target_id = int(target_id)
        self.aposta = discord.ui.TextInput(
            label="Aposta opcional por pessoa (0 = amistoso)",
            placeholder="0 para jogar sem apostar", min_length=1, max_length=4, default="0",
        )
        self.add_item(self.aposta)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None or interaction.channel is None:
            return await interaction.response.send_message("Os duelos só podem ser criados dentro de um servidor.", ephemeral=True)
        alvo = interaction.guild.get_member(self.target_id)
        if alvo is None:
            try:
                alvo = await interaction.guild.fetch_member(self.target_id)
            except discord.HTTPException:
                alvo = None
        if alvo is None or alvo.bot:
            return await interaction.response.send_message("O membro escolhido não está mais disponível no servidor.", ephemeral=True)
        if alvo.id == self.creator_id:
            return await interaction.response.send_message("Você não pode desafiar a si mesmo.", ephemeral=True)
        try:
            aposta = int(str(self.aposta.value).strip())
        except ValueError:
            return await interaction.response.send_message("Informe a aposta usando apenas números.", ephemeral=True)
        if not 0 <= aposta <= APOSTA_MAXIMA:
            return await interaction.response.send_message(f"A aposta precisa ficar entre 0 e {APOSTA_MAXIMA} Denários.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        resultado = await self.cog.bot.db.coliseu_criar_convite(
            interaction.guild.id, interaction.channel.id, self.creator_id, alvo.id, aposta,
            nivel_minimo=0,
            limite_diario=LIMITE_DUELOS_DIA,
            limite_par=LIMITE_DUELOS_PAR_DIA,
            max_aposta_dia=LIMITE_APOSTA_DIA,
            cooldown_segundos=COOLDOWN_DESAFIO_SEGUNDOS,
            diferenca_maxima_poder=999999,
        )
        if resultado["status"] != "ok":
            await interaction.followup.send(self.cog.mensagem_erro_convite(resultado), ephemeral=True)
            return
        duel_id = resultado["duel_id"]
        embed = discord.Embed(
            title="⚔️ Convite para o Coliseu",
            description=(
                f"{interaction.user.mention} desafiou {alvo.mention} para um duelo de cinco rodadas.\n\n"
                + (
                    "**Duelo amistoso:** sem aposta e sem perda de Denários.\n"
                    if aposta == 0 else
                    f"**Aposta por jogador:** {aposta} Denários · **Pote:** {aposta * 2} Denários.\n"
                )
                + "Não há exigência de nível nem limite de diferença de poder entre decks.\n"
                + f"Cada rodada tem {TEMPO_RODADA_SEGUNDOS} segundos para escolha; o duelo costuma levar 2–4 minutos com respostas rápidas.\n"
                + "O convite expira em dois minutos."
            ),
            color=config.COR_OURO,
        )
        embed.set_footer(text=f"Coliseu de Cartas • Duelo #{duel_id} • Modo inicial simplificado")
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


class ResultadoDueloView(discord.ui.View):
    def __init__(self, duel_id: int):
        super().__init__(timeout=None)
        self.add_item(BotaoDueloColiseu("revanche", duel_id))


class HallFamaView(discord.ui.View):
    def __init__(self, cog: "ColiseuCartas", user_id: int):
        super().__init__(timeout=300)
        self.add_item(VoltarColiseuButton(cog, user_id))


class MolduraUploadButton(discord.ui.Button):
    def __init__(self, cog: "ColiseuCartas", raridade: str, row: int):
        super().__init__(
            label=f"Enviar {raridade}", emoji="🖼️",
            style=discord.ButtonStyle.primary, row=row,
        )
        self.cog = cog
        self.raridade = raridade

    async def callback(self, interaction: discord.Interaction):
        await self.cog.solicitar_upload_moldura(interaction, self.raridade)


class MolduraRemoverSelect(discord.ui.Select):
    def __init__(self, view: "MoldurasCartasAdminView"):
        self.painel = view
        super().__init__(
            placeholder="Restaurar uma moldura original do bot...",
            min_values=1, max_values=1, row=2,
            options=[
                discord.SelectOption(label=raridade, value=raridade, description=f"Remover o PNG personalizado de {raridade}")
                for raridade in RARIDADES_MOLDURA
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        raridade = self.values[0]
        removida = remover_moldura_personalizada(raridade)
        embed = await self.painel.cog.embed_painel_molduras()
        await interaction.response.edit_message(embed=embed, view=self.painel)
        mensagem = (
            f"A moldura fixa de **{raridade}** foi removida. A partir da próxima renderização, o bot usará o acabamento original."
            if removida else f"**{raridade}** já estava usando a moldura original do bot."
        )
        await interaction.followup.send(mensagem, ephemeral=True)


class MoldurasAtualizarButton(discord.ui.Button):
    def __init__(self, painel: "MoldurasCartasAdminView"):
        super().__init__(label="Atualizar status", emoji="🔄", style=discord.ButtonStyle.secondary, row=3)
        self.painel = painel

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=await self.painel.cog.embed_painel_molduras(), view=self.painel
        )


class MoldurasVoltarButton(discord.ui.Button):
    def __init__(self, callback):
        super().__init__(label="Voltar à categoria", emoji="↩️", style=discord.ButtonStyle.secondary, row=4)
        self.callback_voltar = callback

    async def callback(self, interaction: discord.Interaction):
        if self.callback_voltar:
            await self.callback_voltar(interaction)
        else:
            await interaction.response.edit_message(
                content="Use `/adm` para voltar à central administrativa.", embed=None, view=None
            )


class MoldurasCartasAdminView(discord.ui.View):
    """Painel efêmero para substituir as molduras PNG fixas do Coliseu."""

    def __init__(self, cog: "ColiseuCartas", user_id: int, callback_voltar=None):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = int(user_id)
        self.callback_voltar = callback_voltar
        raridades = list(RARIDADES_MOLDURA)
        for indice, raridade in enumerate(raridades):
            self.add_item(MolduraUploadButton(cog, raridade, row=indice // 3))
        self.add_item(MolduraRemoverSelect(self))
        self.add_item(MoldurasAtualizarButton(self))
        self.add_item(MoldurasVoltarButton(callback_voltar))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if int(interaction.user.id) != self.user_id:
            await interaction.response.send_message("Este painel pertence a outra sessão administrativa.", ephemeral=True)
            return False
        if not await self.cog.eh_proprietario_bot(interaction.user):
            await interaction.response.send_message(
                "Somente o proprietário global do bot pode alterar molduras que afetam todas as cartas.", ephemeral=True
            )
            return False
        return True


class TemplateUploadButton(discord.ui.Button):
    def __init__(self, cog: "ColiseuCartas", raridade: str, row: int):
        super().__init__(
            label=f"Enviar {raridade}", emoji="🃏",
            style=discord.ButtonStyle.primary, row=row,
        )
        self.cog = cog
        self.raridade = raridade

    async def callback(self, interaction: discord.Interaction):
        await self.cog.solicitar_upload_template(interaction, self.raridade)


class TemplateRemoverSelect(discord.ui.Select):
    def __init__(self, view: "TemplatesCartasAdminView"):
        self.painel = view
        super().__init__(
            placeholder="Restaurar o template padrão do projeto...",
            min_values=1, max_values=1, row=2,
            options=[
                discord.SelectOption(label=raridade, value=raridade, description=f"Restaurar o template padrão de {raridade}")
                for raridade in templates_cartas.RARIDADES_TEMPLATE
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        raridade = self.values[0]
        removido = templates_cartas.remover_template(raridade)
        embed = await self.painel.cog.embed_painel_templates()
        await interaction.response.edit_message(embed=embed, view=self.painel)
        mensagem = (
            f"A substituição personalizada de **{raridade}** foi removida. O template padrão incluso no projeto voltou a ser usado."
            if removido else f"**{raridade}** já está usando o template padrão do projeto."
        )
        await interaction.followup.send(mensagem, ephemeral=True)


class TemplatesAtualizarButton(discord.ui.Button):
    def __init__(self, painel: "TemplatesCartasAdminView"):
        super().__init__(label="Atualizar status", emoji="🔄", style=discord.ButtonStyle.secondary, row=3)
        self.painel = painel

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=await self.painel.cog.embed_painel_templates(), view=self.painel
        )


class TemplatesCartasAdminView(discord.ui.View):
    """Painel efêmero para enviar os templates completos (um por raridade) das cartas."""

    def __init__(self, cog: "ColiseuCartas", user_id: int, callback_voltar=None):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = int(user_id)
        self.callback_voltar = callback_voltar
        for indice, raridade in enumerate(templates_cartas.RARIDADES_TEMPLATE):
            self.add_item(TemplateUploadButton(cog, raridade, row=indice // 3))
        self.add_item(TemplateRemoverSelect(self))
        self.add_item(TemplatesAtualizarButton(self))
        self.add_item(MoldurasVoltarButton(callback_voltar))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if int(interaction.user.id) != self.user_id:
            await interaction.response.send_message("Este painel pertence a outra sessão administrativa.", ephemeral=True)
            return False
        if not await self.cog.eh_proprietario_bot(interaction.user):
            await interaction.response.send_message(
                "Somente o proprietário global do bot pode alterar templates que afetam todas as cartas.", ephemeral=True
            )
            return False
        return True


class ColiseuCartas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._retornos_nara: dict[int, object] = {}
        # Sessões curtas de upload de moldura; os arquivos finais ficam no DATA_DIR persistente.
        self._pending_moldura_uploads: dict[int, dict] = {}
        # Sessões curtas de upload de template completo (cartas com arte enviada pelo membro).
        self._pending_template_uploads: dict[int, dict] = {}

    async def cog_load(self):
        self.bot.add_dynamic_items(BotaoDueloColiseu, AtelieReviewButton)
        self.monitorar_prazos.start()

    async def cog_unload(self):
        self.bot.remove_dynamic_items(BotaoDueloColiseu, AtelieReviewButton)
        self.monitorar_prazos.cancel()

    @tasks.loop(seconds=5)
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

    async def eh_proprietario_bot(self, user) -> bool:
        """Molduras são globais: só o proprietário do bot pode alterá-las."""
        owner_id = int(getattr(config, "BOT_OWNER_ID", 0) or 0)
        souls_id = int(getattr(config, "SOULS_USER_ID", 0) or 0)
        if int(user.id) in {value for value in (owner_id, souls_id) if value}:
            return True
        try:
            return bool(await self.bot.is_owner(user))
        except Exception:
            log.exception("Não foi possível confirmar o proprietário global ao configurar molduras.")
            return False

    async def embed_painel_molduras(self) -> discord.Embed:
        status = listar_molduras_personalizadas()
        linhas = []
        for raridade, configurada in status.items():
            estado = "🟢 PNG personalizado ativo" if configurada else "⚪ Moldura original do bot"
            linhas.append(f"**{raridade}:** {estado}")
        embed = discord.Embed(
            title="🖼️ Molduras fixas das cartas",
            description=(
                "Envie um PNG transparente para substituir a borda vetorial daquela raridade nas cartas **sem arte enviada** "
                "(as com arte usam os templates completos). "
                "A arte, o nome, o poder, o custo e a habilidade continuam sendo montados pelo bot.\n\n"
                + "\n".join(linhas)
                + "\n\n**Arquivo aceito:** PNG com canal alfa, proporção 420:620, mínimo 420 × 620 "
                "e até 8 MB. Recomendado: **840 × 1240 px**.\n"
                "O centro precisa ficar transparente; somente a moldura deve ter pixels visíveis."
            ),
            color=config.COR_OURO,
        )
        embed.set_footer(text="Configuração global · somente o proprietário do bot · alterações aplicadas às próximas renderizações")
        return embed

    async def abrir_painel_molduras(self, interaction: discord.Interaction, callback_voltar=None):
        if not await self.eh_proprietario_bot(interaction.user):
            return await interaction.response.send_message(
                "A configuração de molduras é global e só pode ser alterada pelo proprietário do bot.",
                ephemeral=True,
            )
        view = MoldurasCartasAdminView(self, interaction.user.id, callback_voltar)
        return await interaction.response.edit_message(
            content=None, embed=await self.embed_painel_molduras(), view=view
        )

    async def solicitar_upload_moldura(self, interaction: discord.Interaction, raridade: str):
        if not await self.eh_proprietario_bot(interaction.user):
            return await interaction.response.send_message(
                "Somente o proprietário global do bot pode substituir as molduras oficiais.", ephemeral=True
            )
        try:
            dm = await interaction.user.create_dm()
            self._pending_moldura_uploads[int(interaction.user.id)] = {
                "raridade": raridade,
                "channel_id": int(dm.id),
                "expires_at": time.monotonic() + 600,
            }
            await dm.send(
                f"🖼️ **Upload da moldura fixa — {raridade}**\n\n"
                "Anexe **um único arquivo PNG com transparência real** nesta conversa.\n"
                "• Tamanho recomendado: **840 × 1240 px** (mínimo 420 × 620).\n"
                "• Proporção exata: **420:620**.\n"
                "• Limite: **8 MB**.\n"
                "• O centro precisa ser transparente; envie somente a moldura, sem fundo e sem a carta inteira.\n"
                "• A sessão expira em 10 minutos.\n\n"
                "Depois de validar, vou salvar o arquivo e enviar uma prévia de uma carta com a nova moldura."
            )
        except discord.Forbidden:
            self._pending_moldura_uploads.pop(int(interaction.user.id), None)
            return await interaction.response.send_message(
                "Não consegui enviar a solicitação por DM. Ative mensagens diretas do servidor e tente novamente.",
                ephemeral=True,
            )
        except discord.HTTPException:
            self._pending_moldura_uploads.pop(int(interaction.user.id), None)
            return await interaction.response.send_message(
                "O Discord não permitiu abrir a conversa privada. Tente novamente.", ephemeral=True
            )
        await interaction.response.send_message(
            f"Enviei uma solicitação privada para enviar a moldura **{raridade}**. Anexe o PNG na DM da Nara.",
            ephemeral=True,
        )

    async def _receber_upload_moldura(self, message: discord.Message, sessao: dict) -> None:
        raridade = str(sessao["raridade"])
        if not await self.eh_proprietario_bot(message.author):
            self._pending_moldura_uploads.pop(int(message.author.id), None)
            await message.reply("Este upload não está autorizado para esta conta.")
            return
        if time.monotonic() > float(sessao.get("expires_at", 0)):
            self._pending_moldura_uploads.pop(int(message.author.id), None)
            await message.reply("A sessão de envio da moldura expirou. Abra `/adm` → Jogos → Molduras fixas e tente novamente.")
            return
        if len(message.attachments) != 1:
            await message.reply("Envie exatamente um arquivo PNG como anexo. A sessão continua aberta.")
            return
        anexo = message.attachments[0]
        if int(getattr(anexo, "size", 0) or 0) > 8 * 1024 * 1024:
            await message.reply("O arquivo ultrapassa 8 MB. Envie um PNG menor; a sessão continua aberta.")
            return
        try:
            bruto = await anexo.read(use_cached=True)
            caminho = await asyncio.to_thread(salvar_moldura_personalizada, raridade, bruto)
        except ValueError as exc:
            await message.reply(f"❌ **Não aceitei a moldura:** {exc}\nA sessão continua aberta; envie outro PNG dentro do prazo.")
            return
        except (discord.HTTPException, OSError) as exc:
            await message.reply("Não consegui baixar ou salvar o arquivo. Tente enviar novamente.")
            log.warning("Falha no upload de moldura %s: %s", raridade, exc)
            return

        self._pending_moldura_uploads.pop(int(message.author.id), None)
        limpar_cache_molduras(raridade)
        resposta = f"✅ **Moldura {raridade} salva e ativada.**\nArquivo persistente: `{caminho.name}`. As próximas renderizações usarão este PNG."
        try:
            exemplo = {
                "id": f"preview_moldura_{RARIDADES_MOLDURA[raridade]}",
                "nome": f"Prévia — {raridade}",
                "categoria": "Chefe",
                "raridade": raridade,
                "tipo": "Magia",
                "poder": 88,
                "custo": 3,
                "habilidade": "",
                "descricao": "Prévia da moldura fixa enviada.",
            }
            preview = await asyncio.to_thread(render_carta_bytes, exemplo, b"")
            await message.reply(
                resposta + "\nConfira a prévia abaixo:",
                file=discord.File(preview, filename=f"previa_moldura_{RARIDADES_MOLDURA[raridade]}.png"),
            )
        except Exception:
            log.exception("Moldura %s foi salva, mas não consegui gerar a prévia.", raridade)
            await message.reply(resposta)

    async def embed_painel_templates(self) -> discord.Embed:
        status = templates_cartas.listar_templates()
        linhas = []
        for raridade, configurado in status.items():
            origem = templates_cartas.origem_template(raridade)
            if origem == "personalizado":
                estado = "🟢 Template personalizado"
            elif origem == "padrão":
                estado = "🔷 Template padrão do projeto"
            elif origem and origem.startswith("padrão ("):
                estado = "🟡 Template padrão ativo (upload antigo inválido ignorado)"
            elif origem == "inválido":
                estado = "🔴 Template inválido e sem padrão disponível"
            else:
                estado = "⚪ Sem template (layout antigo)"
            linhas.append(f"**{raridade}:** {estado}")
        embed = discord.Embed(
            title="🃏 Templates completos das cartas",
            description=(
                "Os cinco templates oficiais já vêm incluídos no projeto e são usados **somente nas cartas com arte enviada pelo membro**. "
                "A arte entra por trás do template, pela janela transparente, e o bot escreve os dados nos slots do guia.\n"
                "Cartas sem arte enviada continuam sendo desenhadas pelo bot. Você pode enviar um PNG para substituir temporariamente o padrão.\n\n"
                + "\n".join(linhas)
                + "\n\n**Arquivo aceito:** PNG RGBA de carta completa, 840 × 1240 px, sem textos. "
                "A janela transparente deve coincidir com o guia oficial (56,256 → 784,846)."
            ),
            color=config.COR_OURO,
        )
        embed.set_footer(text="Configuração global · somente o proprietário do bot · vale para as próximas renderizações")
        return embed

    async def abrir_painel_templates(self, interaction: discord.Interaction, callback_voltar=None):
        if not await self.eh_proprietario_bot(interaction.user):
            return await interaction.response.send_message(
                "A configuração de templates é global e só pode ser alterada pelo proprietário do bot.",
                ephemeral=True,
            )
        view = TemplatesCartasAdminView(self, interaction.user.id, callback_voltar)
        return await interaction.response.edit_message(
            content=None, embed=await self.embed_painel_templates(), view=view
        )

    async def solicitar_upload_template(self, interaction: discord.Interaction, raridade: str):
        if not await self.eh_proprietario_bot(interaction.user):
            return await interaction.response.send_message(
                "Somente o proprietário global do bot pode substituir os templates oficiais.", ephemeral=True
            )
        try:
            dm = await interaction.user.create_dm()
            self._pending_template_uploads[int(interaction.user.id)] = {
                "raridade": raridade,
                "channel_id": int(dm.id),
                "expires_at": time.monotonic() + 600,
            }
            await dm.send(
                f"🃏 **Upload do template completo — {raridade}**\n\n"
                "Anexe **um único arquivo** (PNG recomendado; JPG/WEBP só com magenta chapado) nesta conversa.\n"
                "• Canvas: **840 × 1240 px**, retrato, PNG RGBA.\n"
                "• Carta completa, com fundo e placas vazias, **sem nenhum texto**.\n"
                "• A única janela transparente deve coincidir com `(56,256) → (784,846)` (**728 × 590 px**). "
                "Fora dela, o template deve ser opaco. Se usar magenta, ele deve ocupar exatamente essa janela.\n"
                "• Limite: **8 MB**. A sessão expira em 10 minutos.\n\n"
                "Depois de validar, salvo o template e envio duas prévias: a carta de exemplo e outra com os "
                "slots contornados, para conferir se os textos caíram nas placas."
            )
        except discord.Forbidden:
            self._pending_template_uploads.pop(int(interaction.user.id), None)
            return await interaction.response.send_message(
                "Não consegui enviar a solicitação por DM. Ative mensagens diretas do servidor e tente novamente.",
                ephemeral=True,
            )
        except discord.HTTPException:
            self._pending_template_uploads.pop(int(interaction.user.id), None)
            return await interaction.response.send_message(
                "O Discord não permitiu abrir a conversa privada. Tente novamente.", ephemeral=True
            )
        await interaction.response.send_message(
            f"Enviei uma solicitação privada para enviar o template **{raridade}**. Anexe o arquivo na DM da Nara.",
            ephemeral=True,
        )

    async def _receber_upload_template(self, message: discord.Message, sessao: dict) -> None:
        raridade = str(sessao["raridade"])
        if not await self.eh_proprietario_bot(message.author):
            self._pending_template_uploads.pop(int(message.author.id), None)
            await message.reply("Este upload não está autorizado para esta conta.")
            return
        if time.monotonic() > float(sessao.get("expires_at", 0)):
            self._pending_template_uploads.pop(int(message.author.id), None)
            await message.reply("A sessão de envio do template expirou. Abra `/adm` → Jogos → Templates das cartas e tente novamente.")
            return
        if len(message.attachments) != 1:
            await message.reply("Envie exatamente um arquivo como anexo. A sessão continua aberta.")
            return
        anexo = message.attachments[0]
        if int(getattr(anexo, "size", 0) or 0) > templates_cartas.TAMANHO_MAXIMO_BYTES:
            await message.reply("O arquivo ultrapassa 8 MB. Envie uma versão menor; a sessão continua aberta.")
            return
        try:
            bruto = await anexo.read(use_cached=True)
            caminho, janela = await asyncio.to_thread(templates_cartas.salvar_template, raridade, bruto)
        except ValueError as exc:  # inclui TemplateInvalido
            await message.reply(f"❌ **Não aceitei o template:** {exc}\nA sessão continua aberta; envie outro arquivo dentro do prazo.")
            return
        except (discord.HTTPException, OSError) as exc:
            await message.reply("Não consegui baixar ou salvar o arquivo. Tente enviar novamente.")
            log.warning("Falha no upload de template %s: %s", raridade, exc)
            return

        self._pending_template_uploads.pop(int(message.author.id), None)
        x1, y1, x2, y2 = janela
        resposta = (
            f"✅ **Template {raridade} salvo e ativado.**\n"
            f"Janela da arte detectada: `{x1},{y1} → {x2},{y2}` ({x2 - x1} × {y2 - y1}). "
            "Vale para as próximas cartas com arte enviada."
        )
        try:
            previa = await asyncio.to_thread(render_previa_template, raridade)
            calibracao = await asyncio.to_thread(render_previa_template, raridade, calibracao=True)
            arquivos = []
            slug = templates_cartas.RARIDADES_TEMPLATE[raridade]
            if previa:
                arquivos.append(discord.File(previa, filename=f"previa_template_{slug}.png"))
            if calibracao:
                arquivos.append(discord.File(calibracao, filename=f"calibracao_template_{slug}.png"))
            await message.reply(
                resposta + "\nA primeira imagem é a carta de exemplo; a segunda contorna os slots de texto.",
                files=arquivos,
            )
        except Exception:
            log.exception("Template %s foi salvo, mas não consegui gerar as prévias.", raridade)
            await message.reply(resposta)

    async def preparar_deck_inicial(self, user_id: int) -> list[dict]:
        """Entrega o kit gratuito, sincroniza conquistas e deixa um primeiro deck pronto."""
        user_id = int(user_id)
        await self.bot.db.coliseu_entregar_kit_inicial(
            user_id,
            ["chefe_cervo_sombrio", "arma_lamina_peregrino", "magia_brasa_errante", "arma_agulha_astro", "covenant_sentinelas"],
        )
        await self.bot.db.coliseu_sincronizar_conquistas(user_id)
        user = await self.bot.db.get_user(user_id)
        level = nivel_por_xp(int(user["xp"] or 0))
        patentes_liberadas = [c.id for c, (nivel_min, _) in zip(CARTAS_PATENTE, PATENTES) if level >= nivel_min]
        await self.bot.db.coliseu_reivindicar_patentes(user_id, patentes_liberadas)

        deck = await self.bot.db.coliseu_obter_deck(user_id)
        valido, _ = cards_em_deck_validos(deck)
        if not valido:
            rows = await self.bot.db.coliseu_listar_colecao(user_id)
            por_id = {str(row["card_id"]): self._carta_da_linha(row) for row in rows}
            preferidas = [
                "chefe_cervo_sombrio", "arma_lamina_peregrino", "magia_brasa_errante",
                "arma_agulha_astro", "covenant_sentinelas",
            ]
            selecionadas = [por_id[card_id] for card_id in preferidas if por_id.get(card_id)]
            if len(selecionadas) < 5:
                raridade_ordem = {"Comum": 0, "Rara": 1, "Épica": 2, "Lendária": 3, "Primordial": 4}
                restantes = [c for c in por_id.values() if c and str(c["id"]) not in {str(x["id"]) for x in selecionadas}]
                restantes.sort(key=lambda c: (raridade_ordem.get(str(c.get("raridade")), 9), int(c.get("custo", 99)), str(c.get("nome", ""))))
                for carta in restantes:
                    if len(selecionadas) >= 5:
                        break
                    tentativa = selecionadas + [carta]
                    if sum(int(c["custo"]) for c in tentativa) <= 12 and (
                        carta.get("raridade") != "Lendária" or not any(c.get("raridade") == "Lendária" for c in selecionadas)
                    ):
                        selecionadas.append(carta)
            valido, _ = cards_em_deck_validos(selecionadas)
            if valido:
                resultado = await self.bot.db.coliseu_salvar_deck(user_id, selecionadas)
                if resultado.get("status") == "ok":
                    deck = await self.bot.db.coliseu_obter_deck(user_id)
        return deck if cards_em_deck_validos(deck)[0] else []

    async def _preview_deck(self, user_id: int, deck: list[dict]):
        # Consultas/leituras independentes podem avançar juntas; a renderização
        # Pillow roda fora do event loop para não atrasar os demais botões.
        cartas = deck[:5]
        artes_encontradas = await asyncio.gather(*(
            self._obter_arte_personalizada(user_id, str(carta["id"]))
            for carta in cartas
        ))
        artes = {
            str(carta["id"]): imagem
            for carta, imagem in zip(cartas, artes_encontradas)
            if imagem
        }
        return await asyncio.to_thread(render_deck_preview_bytes, deck, artes)

    async def abrir_painel(
        self, interaction: discord.Interaction, editar: bool = False, callback_voltar=None,
    ):
        user_id = int(interaction.user.id)
        if editar:
            # O callback pode precisar preparar o deck e carregar artes do Discord.
            # Confirma o clique antes dessas operações de banco/rede.
            await interaction.response.defer()
        if not editar:
            self._retornos_nara.pop(user_id, None)
        if callback_voltar is not None:
            self._retornos_nara[user_id] = callback_voltar
        elif editar:
            callback_voltar = self._retornos_nara.get(user_id)

        deck = await self.preparar_deck_inicial(user_id)
        state = await self.bot.db.coliseu_estado_usuario(user_id)
        level = nivel_por_xp(int(state["xp"] or 0))
        faltam = max(0, PITY_CARTAS - state["pity"])
        embed = discord.Embed(
            title="⚔️ Seu Coliseu",
            description=(
                "Sua coleção e seu deck ficam aqui. O deck inicial já está preparado; você pode editar quando quiser.\n\n"
                f"**Nível:** {level} · **Denários:** {state['denarios']} · **Almas:** {state['almas']}\n"
                f"**Coleção:** {state['cartas']} cartas · **Proteção contra azar:** {state['pity']}/10"
                f" ({'próxima Rara+' if faltam == 0 else f'faltam {faltam} cartas Comuns'})\n"
                f"**Deck:** {len(deck)}/5 cartas · custo {sum(int(c['custo']) for c in deck) if deck else 0}/12 · "
                f"poder-base {poder_total_deck(deck) if deck else 0}\n\n"
                f"**Pacote Fogueira:** 3 cartas por {PRECO_PACOTE_FOGUEIRA} Denários · 70% Comum, 22% Rara, 7% Épica e 1% Lendária por carta.\n"
                f"**Duelos:** apostas de {APOSTA_MINIMA} a {APOSTA_MAXIMA} Denários por jogador, cinco rodadas e até {TEMPO_RODADA_SEGUNDOS}s por escolha."
            ),
            color=config.COR_OURO,
        )
        if deck:
            embed.add_field(
                name="🛡️ Seu deck atual",
                value="\n".join(f"{i}. **{c['nome']}** · {c['raridade']} · {c['tipo']}" for i, c in enumerate(deck, 1)),
                inline=False,
            )
            deck_image = discord.File(await self._preview_deck(user_id, deck), filename="meu_deck.png")
            embed.set_image(url="attachment://meu_deck.png")
        else:
            deck_image = None
            embed.add_field(
                name="Seu primeiro deck",
                value="Ainda não há cinco cartas diferentes na coleção. Abra um Pacote Fogueira ou registre uma conquista aprovada para completar seu deck.",
                inline=False,
            )
        embed.set_footer(text="Você pode editar o deck a qualquer momento. A coleção e as conquistas não são apagadas ao trocar cartas.")
        view = PainelColiseuView(self, user_id, callback_voltar=callback_voltar)
        if editar:
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                attachments=[deck_image] if deck_image else [],
                view=view,
            )
        elif deck_image:
            await interaction.response.send_message(
                content=None, embed=embed, view=view, file=deck_image, ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                content=None, embed=embed, view=view, ephemeral=True,
            )

    async def abrir_selecao_desafio(self, interaction: discord.Interaction, user_id: int):
        """Lista membros conectados; no início, duelos amistosos têm requisitos mínimos."""
        guild = interaction.guild
        if guild is None:
            return await interaction.response.edit_message(
                embed=discord.Embed(title="⚔️ Desafio indisponível", description="Abra o Coliseu dentro de um servidor.", color=config.COR_OURO),
                view=discord.ui.View(timeout=60).add_item(VoltarColiseuButton(self, user_id)),
            )

        if not interaction.response.is_done():
            await interaction.response.defer()

        if not guild.chunked:
            try:
                await guild.chunk(cache=True)
            except (discord.Forbidden, discord.HTTPException):
                log.warning("Não foi possível completar o cache de membros do servidor %s", guild.id)

        conectados = [
            member for member in guild.members
            if member.id != int(user_id)
            and not member.bot
            and member.status in (discord.Status.online, discord.Status.idle, discord.Status.dnd)
        ]
        prioridade_status = {discord.Status.online: 0, discord.Status.idle: 1, discord.Status.dnd: 2}
        rotulos_status = {
            discord.Status.online: ("Online", "🟢"),
            discord.Status.idle: ("Ausente", "🟡"),
            discord.Status.dnd: ("Não perturbe", "🔴"),
        }
        conectados.sort(key=lambda m: (prioridade_status.get(m.status, 9), m.display_name.casefold()))

        db = self.bot.db
        candidatos: list[dict] = []
        for member in conectados:
            dados = await db._one("SELECT xp FROM users WHERE user_id=?", (int(member.id),))
            if not dados:
                continue
            deck = await db.coliseu_obter_deck(int(member.id))
            valido, _ = cards_em_deck_validos(deck)
            if not valido:
                continue
            ocupado = await db._one(
                "SELECT id FROM cartas_duelos WHERE status IN ('invited','active') "
                "AND (creator_id=? OR opponent_id=? OR creator_id=? OR opponent_id=?) LIMIT 1",
                (int(member.id), int(member.id), int(member.id), int(member.id)),
            )
            if ocupado:
                continue
            status_label, status_emoji = rotulos_status.get(member.status, ("Conectado", "🟢"))
            candidatos.append({
                "member": member,
                "status_label": status_label,
                "status_emoji": status_emoji,
                "nivel": nivel_por_xp(int(dados["xp"] or 0)),
                "poder": poder_total_deck(deck),
            })

        view = DesafioColiseuView(self, int(user_id), candidatos, len(conectados))
        await interaction.edit_original_response(embed=view.embed(), view=view)

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
                    "Duplicatas são convertidas automaticamente em Almas.\n"
                    f"Limite de uso: até {LIMITE_PACOTES_DIA} pacotes a cada 24 horas.\n\n"
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
            return await self.abrir_selecao_desafio(interaction, user_id)
        if acao == "missoes":
            dados = await db.coliseu_missoes_semanais(user_id)
            view = MissaoSemanalView(self, user_id, dados)
            return await interaction.response.edit_message(embed=view.embed(), view=view)
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

    async def _obter_arte_personalizada(self, user_id: int, card_id: str) -> bytes | None:
        registro = await self.bot.db.coliseu_atelie_arte_ativa(user_id, card_id)
        if not registro or not registro["channel_id"] or not registro["message_id"]:
            return None
        try:
            canal = self.bot.get_channel(int(registro["channel_id"]))
            if canal is None:
                canal = await self.bot.fetch_channel(int(registro["channel_id"]))
            mensagem = await canal.fetch_message(int(registro["message_id"]))
            anexo = next((a for a in mensagem.attachments if int(a.id) == int(registro["attachment_id"])), None)
            if anexo is None:
                return None
            return await anexo.read(use_cached=True)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException, AttributeError):
            log.warning("Arte personalizada indisponível para user=%s card=%s", user_id, card_id)
            return None

    async def mostrar_detalhe_carta(
        self, interaction: discord.Interaction, carta: dict, user_id: int,
        *, collection_view: CollectionView | None = None, editar: bool = False,
        mensagem_status: str | None = None,
    ):
        # O detalhe substitui a lista na mesma mensagem efêmera. Assim o membro
        # sempre tem um caminho de volta e não acumula respostas privadas separadas.
        if collection_view is None:
            collection_view = CollectionView(self, user_id, [])
        arte_bytes = await self._obter_arte_personalizada(user_id, str(carta["id"]))
        possui_arte = arte_bytes is not None
        if arte_bytes:
            buffer = render_carta_bytes(carta, arte_bytes)
            arquivo = discord.File(buffer, filename="carta.png")
        else:
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
        if carta.get("jogo_origem"):
            embed.add_field(name="Jogo de origem", value=str(carta["jogo_origem"])[:200], inline=False)
        elif carta.get("descricao"):
            embed.add_field(name="Origem", value=str(carta["descricao"])[:500], inline=False)
        if mensagem_status:
            embed.add_field(name="Atualização", value=mensagem_status, inline=False)
        embed.set_footer(text=("Arte personalizada ativa. Os atributos oficiais permanecem iguais." if possui_arte
                               else "Personalização opcional. Gere um prompt ou volte à coleção."))
        view = DetalheCartaView(self, user_id, carta, possui_arte, collection_view)
        if editar and interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, attachments=[arquivo], view=view)
        elif editar:
            await interaction.response.edit_message(embed=embed, attachments=[arquivo], view=view)
        else:
            await interaction.response.send_message(embed=embed, file=arquivo, view=view, ephemeral=True)

    def _pode_revisar_arte(self, member: discord.Member) -> bool:
        perms = member.guild_permissions
        if perms.administrator or perms.manage_guild or perms.manage_messages:
            return True
        role_id = int(getattr(config, "MOD_ROLE_ID", 0) or 0)
        return bool(role_id and any(int(role.id) == role_id for role in member.roles))

    async def iniciar_upload_atelie(self, interaction: discord.Interaction, carta: dict):
        if interaction.guild is None:
            return await interaction.response.send_message("Abra a carta dentro do servidor para iniciar a personalização.", ephemeral=True)
        canal_id = int(getattr(config, "COLISEU_ART_CHANNEL_ID", 0) or 0)
        if not canal_id:
            return await interaction.response.send_message(
                "O Ateliê ainda não foi configurado pela administração. A geração do prompt funciona, mas o envio de artes será liberado quando o canal privado `#biblioteca-coliseu` estiver configurado.",
                ephemeral=True,
            )
        canal = self.bot.get_channel(canal_id)
        if canal is None:
            try:
                canal = await self.bot.fetch_channel(canal_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                canal = None
        if not isinstance(canal, discord.TextChannel) or canal.guild.id != interaction.guild.id:
            return await interaction.response.send_message(
                "Configure `COLISEU_ART_CHANNEL_ID` com o ID de um canal de texto deste servidor.",
                ephemeral=True,
            )
        try:
            permissoes_bot = canal.permissions_for(interaction.guild.me)
            permissoes_publicas = canal.permissions_for(interaction.guild.default_role)
            if permissoes_publicas.view_channel:
                return await interaction.response.send_message(
                    "A `#biblioteca-coliseu` precisa ser privada. Oculte o canal do cargo @everyone e libere acesso somente ao bot e à moderação.",
                    ephemeral=True,
                )
            if not (permissoes_bot.view_channel and permissoes_bot.send_messages and permissoes_bot.attach_files
                    and permissoes_bot.embed_links and permissoes_bot.read_message_history):
                return await interaction.response.send_message(
                    "Não tenho permissão para ver o canal, enviar imagens, publicar embeds ou ler o histórico da `#biblioteca-coliseu`. Peça à moderação para ajustar minhas permissões.",
                    ephemeral=True,
                )
        except AttributeError:
            return await interaction.response.send_message(
                "Não consegui verificar as permissões da biblioteca. Confira o canal e tente novamente.",
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True, thinking=True)
        resultado = await self.bot.db.coliseu_atelie_criar_sessao(
            interaction.user.id, interaction.guild.id, str(carta["id"]),
            str(carta.get("jogo_origem") or carta.get("game_name") or ""),
        )
        if resultado["status"] == "not_owned":
            return await interaction.followup.send("Você precisa possuir essa carta para personalizá-la.", ephemeral=True)
        if resultado["status"] == "pending":
            return await interaction.followup.send(
                "Você já tem uma arte dessa carta aguardando avaliação. Aguarde a decisão da moderação antes de enviar outra.",
                ephemeral=True,
            )
        if resultado["status"] == "pending_limit":
            return await interaction.followup.send(
                "Você já tem três artes aguardando avaliação. Assim que a moderação analisar uma delas, poderá enviar outra.",
                ephemeral=True,
            )
        try:
            await interaction.user.send(
                f"🎨 **Ateliê do Coliseu — {carta['nome']}**\n"
                "Envie nesta conversa uma imagem PNG, JPG ou WEBP.\n"
                "Use uma arte horizontal próxima de 5:4, com pelo menos 512 × 512 pixels e até 8 MB. "
                "Vou ajustá-la à janela oficial da carta, sem alterar moldura, raridade ou atributos.\n"
                "A sessão fica aberta por 30 minutos. Envie apenas uma imagem."
            )
        except discord.Forbidden:
            await self.bot.db.coliseu_atelie_encerrar_sessao(interaction.user.id)
            return await interaction.followup.send(
                "Não consegui abrir sua DM. Ative temporariamente as mensagens diretas deste servidor e tente novamente.",
                ephemeral=True,
            )
        await interaction.followup.send(
            "Enviei as instruções por mensagem direta. Basta responder à Nara anexando sua imagem; ela será encaminhada para aprovação.",
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Recebe uploads privados do Ateliê e da configuração global de molduras."""
        if message.guild is not None or message.author.bot:
            return
        template_pendente = self._pending_template_uploads.get(int(message.author.id))
        if template_pendente and int(message.channel.id) == int(template_pendente.get("channel_id", 0)):
            await self._receber_upload_template(message, template_pendente)
            return
        moldura_pendente = self._pending_moldura_uploads.get(int(message.author.id))
        if moldura_pendente and int(message.channel.id) == int(moldura_pendente.get("channel_id", 0)):
            await self._receber_upload_moldura(message, moldura_pendente)
            return
        sessao = await self.bot.db.coliseu_atelie_obter_sessao(message.author.id)
        if not sessao:
            return
        if len(message.attachments) != 1:
            await message.reply("Envie uma única imagem PNG, JPG ou WEBP nesta conversa. Sua sessão continua aberta.")
            return
        anexo = message.attachments[0]
        if int(getattr(anexo, "size", 0) or 0) > TAMANHO_MAXIMO_UPLOAD:
            await message.reply("A imagem ultrapassa 8 MB. Envie uma versão menor; sua sessão continua aberta.")
            return
        try:
            raw = await anexo.read(use_cached=True)
            imagem = normalizar_imagem_carta(raw)
        except ArteInvalida as exc:
            await message.reply(f"Não consegui aceitar essa imagem: {exc}\nSua sessão continua aberta; envie outra imagem dentro de 30 minutos.")
            return
        except (discord.HTTPException, OSError):
            await message.reply("Não consegui baixar o anexo. Tente enviar a imagem novamente.")
            return
        reservado = await self.bot.db.coliseu_atelie_reservar_sessao(message.author.id)
        if not reservado:
            await message.reply("Sua sessão do Ateliê expirou. Abra a carta novamente e clique em **Enviar minha arte**.")
            return
        canal_id = int(getattr(config, "COLISEU_ART_CHANNEL_ID", 0) or 0)
        canal = self.bot.get_channel(canal_id) if canal_id else None
        if canal is None and canal_id:
            try:
                canal = await self.bot.fetch_channel(canal_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                canal = None
        guild = self.bot.get_guild(int(reservado["guild_id"]))
        if not isinstance(canal, discord.TextChannel) or guild is None or canal.guild.id != guild.id:
            await self.bot.db.coliseu_atelie_reabrir_sessao(message.author.id)
            await message.reply("A biblioteca de artes está temporariamente indisponível. Sua sessão continua aberta; avise a moderação.")
            return
        perms_bot = canal.permissions_for(guild.me)
        perms_publicas = canal.permissions_for(guild.default_role)
        if perms_publicas.view_channel or not (perms_bot.view_channel and perms_bot.send_messages and perms_bot.attach_files and perms_bot.read_message_history):
            await self.bot.db.coliseu_atelie_reabrir_sessao(message.author.id)
            await message.reply("A biblioteca precisa ser privada e permitir que a Nara envie imagens, publique embeds e leia o histórico. Avise a moderação; sua sessão continua aberta.")
            return

        pedido = await self.bot.db.coliseu_atelie_criar_pedido(
            message.author.id, int(reservado["guild_id"]), str(reservado["card_id"]), str(reservado["game_name"] or "")
        )
        if pedido["status"] == "not_owned":
            await self.bot.db.coliseu_atelie_encerrar_sessao(message.author.id)
            return await message.reply("Essa carta não está mais na sua coleção. Reabra a coleção para iniciar outro pedido.")
        if pedido["status"] == "pending":
            await self.bot.db.coliseu_atelie_encerrar_sessao(message.author.id)
            return await message.reply("Já existe uma arte dessa carta aguardando avaliação. Não precisa enviar novamente.")
        if pedido["status"] == "pending_limit":
            await self.bot.db.coliseu_atelie_encerrar_sessao(message.author.id)
            return await message.reply("Você já tem três artes aguardando avaliação. Aguarde a moderação analisar uma delas antes de enviar outra.")

        card = get_carta(str(reservado["card_id"]))
        card_dict = card.para_dict() if card else {
            "id": str(reservado["card_id"]), "nome": str(reservado["game_name"] or "Carta de jogo"),
            "categoria": "Jogo", "raridade": "Conquista", "tipo": "Magia", "poder": 0, "custo": 0,
            "habilidade": "", "jogo_origem": str(reservado["game_name"] or ""),
        }
        if str(reservado["card_id"]).startswith("jogo_") and reservado["game_name"]:
            try:
                card_dict = carta_de_jogo_por_id(str(reservado["card_id"]), str(reservado["game_name"])).para_dict()
            except ValueError:
                pass
        embed = discord.Embed(
            title="🎨 Nova arte para avaliação",
            description=(
                f"**Carta:** {card_dict.get('nome', 'Carta')}\n"
                f"**Jogador:** <@{message.author.id}> (`{message.author.id}`)\n"
                f"**Jogo de origem:** {reservado['game_name'] or 'Universo original do Coliseu'}\n"
                f"**Categoria:** {card_dict.get('categoria', 'Carta')} · **Raridade:** {card_dict.get('raridade', '—')}\n\n"
                "A arte foi normalizada para a janela oficial 5:4. Aprovar ativa a imagem somente na coleção deste jogador."
            ),
            color=config.COR_OURO,
        )
        embed.set_footer(text=f"Ateliê do Coliseu · Pedido #{pedido['art_id']} · Aguardando avaliação")
        arquivo = discord.File(io.BytesIO(imagem.dados), filename=f"coliseu_arte_{pedido['art_id']}.jpg")
        revisao = None
        try:
            revisao = await canal.send(embed=embed, file=arquivo)
            if not revisao.attachments:
                raise RuntimeError("O Discord não retornou o anexo enviado à biblioteca.")
            attachment_id = revisao.attachments[0].id
            publicado = await self.bot.db.coliseu_atelie_publicar_pedido(
                pedido["art_id"], canal.id, revisao.id, attachment_id
            )
            if not publicado:
                raise RuntimeError("Não foi possível persistir a referência da imagem enviada.")
        except Exception:
            if revisao is not None:
                try:
                    await revisao.delete()
                except (discord.Forbidden, discord.HTTPException):
                    pass
            await self.bot.db.coliseu_atelie_cancelar_pedido(pedido["art_id"])
            await self.bot.db.coliseu_atelie_reabrir_sessao(message.author.id)
            log.exception("Falha ao publicar ou registrar arte do Coliseu no canal configurado")
            return await message.reply("Não consegui enviar sua arte à biblioteca. Sua sessão continua aberta; tente novamente ou avise a moderação.")

        try:
            await revisao.edit(view=AtelieReviewView(pedido["art_id"]))
        except discord.HTTPException:
            # Mantém a imagem original no arquivo e tenta disponibilizar os botões em uma segunda mensagem.
            log.exception("Falha ao anexar os botões de moderação na imagem do Ateliê")
            try:
                await canal.send(
                    f"Ações de moderação para o pedido #{pedido['art_id']}:",
                    view=AtelieReviewView(pedido["art_id"]),
                )
            except discord.HTTPException:
                log.exception("Não foi possível publicar a mensagem alternativa de moderação do pedido #%s", pedido["art_id"])
        await self.bot.db.coliseu_atelie_encerrar_sessao(message.author.id)
        await message.reply(
            f"✅ Recebi sua arte para **{card_dict.get('nome', 'sua carta')}**! Ela foi enviada para avaliação. "
            "Vou avisar por aqui quando a moderação decidir."
        )

    async def revisar_arte_atelie(self, interaction: discord.Interaction, arte_id: int, aprovado: bool, motivo: str = ""):
        if not isinstance(interaction.user, discord.Member) or not self._pode_revisar_arte(interaction.user):
            return await interaction.response.send_message("Somente a moderação pode avaliar artes do Coliseu.", ephemeral=True)
        resultado = await self.bot.db.coliseu_atelie_decidir_pedido(
            arte_id, interaction.user.id, aprovado, motivo,
        )
        if resultado["status"] != "ok":
            return await interaction.response.send_message("Este pedido já foi avaliado ou não está mais disponível.", ephemeral=True)
        pedido = resultado["pedido"]
        carta_revisada = self._carta_da_linha(pedido) or {"nome": pedido["card_id"]}
        nome_carta = str(carta_revisada.get("nome") or pedido["card_id"])
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green() if aprovado else discord.Color.red()
            status_text = "✅ Arte aprovada e ativada na coleção do jogador." if aprovado else f"❌ Arte rejeitada. Motivo: {motivo[:400]}"
            embed.add_field(name="Avaliação", value=status_text, inline=False)
            embed.set_footer(text=f"Avaliado por {interaction.user} · Pedido #{arte_id}")
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message("Avaliação registrada.", ephemeral=True)
        try:
            membro = self.bot.get_user(int(pedido["user_id"])) or await self.bot.fetch_user(int(pedido["user_id"]))
            if aprovado:
                await membro.send(
                    f"✅ Sua arte de **{nome_carta}** foi aprovada e já está ativa na sua coleção do Coliseu. "
                    "Abra a carta pela Nara para conferir."
                )
            else:
                await membro.send(
                    f"A arte enviada para **{nome_carta}** não foi aprovada.\n"
                    f"**Motivo:** {motivo}\nVocê pode gerar outra imagem e enviar novamente pela própria carta."
                )
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não foi possível avisar por DM o proprietário da arte #%s", arte_id)

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
        if acao == "revanche":
            if uid not in {creator_id, opponent_id}:
                return await interaction.response.send_message("Somente os duelistas originais podem pedir uma revanche.", ephemeral=True)
            if duel["status"] != "finished":
                return await interaction.response.send_message("A revanche fica disponível após um duelo concluído.", ephemeral=True)
            if interaction.guild is None:
                return await interaction.response.send_message("A revanche precisa ser criada dentro do servidor.", ephemeral=True)
            alvo_id = opponent_id if uid == creator_id else creator_id
            alvo = interaction.guild.get_member(alvo_id)
            if alvo is None or alvo.bot or alvo.status not in (discord.Status.online, discord.Status.idle, discord.Status.dnd):
                return await interaction.response.send_message(
                    "Seu adversário não está conectado agora. A revanche ficará disponível quando ele voltar.", ephemeral=True
                )
            channel = interaction.channel
            if channel is None or not hasattr(channel, "send"):
                channel = self.bot.get_channel(int(duel["channel_id"]))
            if channel is None:
                return await interaction.response.send_message("Não encontrei o canal para publicar a revanche.", ephemeral=True)
            await interaction.response.defer(ephemeral=True, thinking=True)
            resultado = await self.bot.db.coliseu_criar_convite(
                interaction.guild.id, channel.id, uid, alvo.id, int(duel["aposta"]),
                nivel_minimo=NIVEL_MINIMO_DUELO,
                limite_diario=LIMITE_DUELOS_DIA,
                limite_par=LIMITE_DUELOS_PAR_DIA,
                max_aposta_dia=LIMITE_APOSTA_DIA,
                cooldown_segundos=0,  # revanche direta não precisa esperar o cooldown normal
                diferenca_maxima_poder=DIFERENCA_MAXIMA_PODER_DECK,
            )
            if resultado["status"] != "ok":
                return await interaction.followup.send(self.mensagem_erro_convite(resultado), ephemeral=True)
            novo_id = resultado["duel_id"]
            embed = discord.Embed(
                title="🔁 Pedido de revanche",
                description=(
                    f"{interaction.user.mention} pediu uma revanche contra {alvo.mention}.\n\n"
                    f"**Aposta por jogador:** {int(duel['aposta'])} Denários\n"
                    f"**Pote total:** {int(duel['aposta']) * 2} Denários\n"
                    f"**Poder dos decks:** {resultado['deck_power'][uid]} × {resultado['deck_power'][alvo.id]}\n"
                    "As apostas só serão travadas se o convite for aceito.\n"
                    f"Cada rodada tem {TEMPO_RODADA_SEGUNDOS} segundos para escolha.\n"
                    "O deck atual de cada jogador será usado; confira suas cartas antes de aceitar."
                ),
                color=config.COR_OURO,
            )
            embed.set_footer(text=f"Coliseu · Revanche do duelo #{duel_id} · Convite expira em 2 minutos")
            try:
                message = await channel.send(
                    content=alvo.mention, embed=embed, view=ConviteDueloView(novo_id),
                    allowed_mentions=discord.AllowedMentions(users=[alvo], roles=False, everyone=False),
                )
                await self.bot.db.coliseu_definir_mensagem_convite(novo_id, message.id)
            except discord.HTTPException:
                await self.bot.db.coliseu_decidir_convite(novo_id, uid, False)
                log.exception("Não foi possível publicar a revanche do duelo #%s", duel_id)
                return await interaction.followup.send("Não consegui publicar o convite. Nenhum Denário foi descontado.", ephemeral=True)
            return await interaction.followup.send(
                f"Revanche enviada para {alvo.mention}. O valor da aposta anterior foi mantido: {message.jump_url}",
                ephemeral=True,
            )

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
                description=(f"Sua escolha é secreta e só será revelada quando o adversário escolher. "
                             f"Você tem {TEMPO_RODADA_SEGUNDOS} segundos. Cada carta só pode ser usada uma vez."),
                color=config.COR_OURO,
            )
            return await interaction.response.send_message(embed=embed, view=SelecaoCartaView(self, duel_id, uid, cards), ephemeral=True)

    async def _notificar_niveis_por_duelo(self, duel: dict, recompensas: dict):
        """Sincroniza patentes após XP já creditado; falhas de notificação não desfazem o duelo."""
        progressao = self.bot.get_cog("ProgressaoXP")
        guild = self.bot.get_guild(int(duel.get("guild_id", 0)))
        if progressao is None or guild is None:
            return
        for user_id, item in (recompensas or {}).items():
            xp = int(item.get("xp", 0) or 0)
            nivel_antigo = int(item.get("old_level", 0) or 0)
            nivel_novo = int(item.get("new_level", 0) or 0)
            if xp <= 0 or nivel_novo <= nivel_antigo:
                continue
            try:
                await progressao.notificar_recompensa(
                    guild, int(user_id), nivel_antigo, nivel_novo, xp, "participação no Coliseu"
                )
            except Exception:
                log.exception("Falha ao notificar nível do membro %s após duelo #%s", user_id, duel.get("id"))

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
            elif winner == "empate":
                previous_a = previous_b = "empatou"
        tipo_anterior_a = tipo_anterior_b = None
        if historico:
            deck_a = await self.bot.db.coliseu_deck_da_partida(int(duel["id"]), a)
            deck_b = await self.bot.db.coliseu_deck_da_partida(int(duel["id"]), b)
            mapa_a = {str(c["id"]): c for c in deck_a}
            mapa_b = {str(c["id"]): c for c in deck_b}
            carta_anterior_a = mapa_a.get(str(historico[-1]["card_a_id"]))
            carta_anterior_b = mapa_b.get(str(historico[-1]["card_b_id"]))
            tipo_anterior_a = carta_anterior_a.get("tipo") if carta_anterior_a else None
            tipo_anterior_b = carta_anterior_b.get("tipo") if carta_anterior_b else None
        result = resolver_rodada(
            card_a, card_b, int(payload["round_no"]), previous_a, previous_b,
            tipo_anterior_a, tipo_anterior_b,
        )
        narration = narrar_rodada(int(payload["round_no"]), card_a, card_b, result)
        result.update({"card_a": card_a, "card_b": card_b, "narration": narration})
        final = await self.bot.db.coliseu_resolver_rodada(int(duel["id"]), int(payload["round_no"]), result)
        if final["status"] == "round_ok":
            return f"Rodada {payload['round_no']} resolvida. A próxima escolha já está disponível no painel público."
        if final["status"] == "vitoria":
            base = f"Duelo encerrado. Vencedor: <@{final['winner_id']}> · prêmio: {final['payout']} Denários · {final['burned']} Denários foram removidos do jogo."
        elif final["status"] == "empate":
            base = "O duelo terminou empatado. As duas apostas foram devolvidas integralmente."
        else:
            return "A rodada foi processada. Consulte o painel público para ver o estado atualizado."
        await self._notificar_niveis_por_duelo(duel, final.get("recompensas") or {})
        linhas_recompensa = []
        for user_id, item in (final.get("recompensas") or {}).items():
            partes = []
            if item.get("xp"):
                partes.append(f"+{item['xp']} XP")
            if item.get("almas"):
                partes.append(f"+{item['almas']} Almas de missões")
            if partes:
                linhas_recompensa.append(f"<@{user_id}>: {', '.join(partes)}")
        if linhas_recompensa:
            base += "\n\n**Progressão:**\n" + "\n".join(linhas_recompensa)
        else:
            base += "\n\nA participação foi registrada. O limite de XP diário pode já ter sido alcançado."
        return base

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
            embed.set_footer(text=f"Prazo por rodada: {TEMPO_RODADA_SEGUNDOS}s. Se expirar, as duas apostas são devolvidas.")
        elif duel["status"] == "finished":
            if duel["winner_id"]:
                embed.add_field(name="Resultado", value=f"🏆 Vencedor: <@{duel['winner_id']}>\nPrêmio: **{duel['payout']} Denários**\nRemovidos do jogo: **{duel['burned']} Denários**", inline=False)
            else:
                embed.add_field(name="Resultado", value="Empate. As duas apostas foram devolvidas.", inline=False)
            rivalidade = await self.bot.db.coliseu_rivalidade(a, b, limite=5)
            embed.add_field(
                name="Rivalidade histórica",
                value=(
                    f"**{nome_a}:** {rivalidade['wins']} vitória(s) · "
                    f"**{nome_b}:** {rivalidade['losses']} vitória(s) · "
                    f"**Empates:** {rivalidade['draws']} · **Confrontos:** {rivalidade['duels']}"
                ),
                inline=False,
            )
            recentes = []
            for registro in rivalidade["recent"]:
                if registro["winner_id"] is None:
                    recentes.append(f"Duelo #{registro['id']}: empate")
                elif int(registro["winner_id"]) == a:
                    recentes.append(f"Duelo #{registro['id']}: {nome_a} venceu")
                else:
                    recentes.append(f"Duelo #{registro['id']}: {nome_b} venceu")
            if recentes:
                embed.add_field(name="Últimos confrontos", value="\n".join(recentes), inline=False)
            recompensas = await self.bot.db.coliseu_recompensas_duelo(duel_id)
            linhas = []
            for item in recompensas:
                partes = []
                if int(item["xp_awarded"] or 0):
                    partes.append(f"+{int(item['xp_awarded'])} XP")
                if int(item["almas_awarded"] or 0):
                    partes.append(f"+{int(item['almas_awarded'])} Almas")
                if partes:
                    linhas.append(f"<@{item['user_id']}>: {', '.join(partes)}")
            if linhas:
                embed.add_field(name="Progresso recebido", value="\n".join(linhas), inline=False)
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
            if duel["status"] == "active":
                view = BatalhaDueloView(duel_id)
            elif duel["status"] == "finished":
                view = ResultadoDueloView(duel_id)
            else:
                view = None
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
