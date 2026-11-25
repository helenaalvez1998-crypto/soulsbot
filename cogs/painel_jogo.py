"""Painel de entrada do jogo Cartas do Coliseu.

O comando público /jogo é a entrada Discord do Coliseu. O Discord consulta
coleção, drops e recursos; Mercado, deckbuilding e partidas competitivas acontecem no site.
"""
from __future__ import annotations

import os

import discord
from discord import app_commands
from discord.ext import commands

from sistemas.cartas import CARTAS_POR_ID, carta_de_jogo_por_id


COR_COLISEU = 0x8E6A3A


def _nome_carta(card_id: str, game_name: str = "") -> str:
    carta = CARTAS_POR_ID.get(str(card_id))
    if carta:
        return carta.nome
    if str(card_id).startswith("jogo_") and game_name:
        try:
            return carta_de_jogo_por_id(str(card_id), game_name).nome
        except ValueError:
            pass
    return str(card_id).replace("_", " ").strip().title() or "Carta desconhecida"


class PainelJogoView(discord.ui.View):
    def __init__(self, bot: commands.Bot, user_id: int, callback_voltar=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = int(user_id)
        self.callback_voltar = callback_voltar
        base_url = str(os.getenv("SOULSBOT_PUBLIC_URL", "https://narabot.sbs") or "https://narabot.sbs").strip().rstrip("/")
        self.add_item(discord.ui.Button(
            label="Abrir Coliseu no site", emoji="🌐", style=discord.ButtonStyle.link,
            url=f"{base_url}/", row=1,
        ))
        if callback_voltar is not None:
            voltar = discord.ui.Button(label="Voltar aos Jogos", emoji="↩️", style=discord.ButtonStyle.secondary, row=1)
            voltar.callback = self._voltar
            self.add_item(voltar)

    async def _voltar(self, interaction: discord.Interaction):
        if self.callback_voltar is None:
            return await interaction.response.send_message("Abra `/nara` para voltar à central.", ephemeral=True)
        await self.callback_voltar(interaction)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Este painel pertence a outro jogador. Use `/jogo` para abrir o seu.",
                ephemeral=True,
            )
            return False
        return True

    async def _mostrar(self, interaction: discord.Interaction, titulo: str, descricao: str):
        embed = discord.Embed(title=titulo, description=descricao, color=COR_COLISEU)
        embed.set_footer(text="Cartas do Coliseu · NARA")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Minha coleção", emoji="🃏", style=discord.ButtonStyle.primary, row=0)
    async def colecao(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await self.bot.db.coliseu_listar_colecao(self.user_id)
        if not rows:
            texto = "Sua coleção ainda está vazia. Você pode receber cartas por drops de atividades ou comprar pacotes no Mercado do Coliseu pelo site."
        else:
            linhas = []
            for row in rows[:15]:
                nome = _nome_carta(row["card_id"], row["game_name"] if "game_name" in row.keys() else "")
                raridade = row["rarity"] or "Sem exemplar"
                poder = row["exemplar_power"]
                qtd = int(row["exemplares"] or 0)
                sufixo = f" · Poder {poder}" if poder is not None else ""
                linhas.append(f"• **{nome}** — {raridade}{sufixo} · {qtd} exemplar(es)")
            texto = "\n".join(linhas)
            if len(rows) > 15:
                texto += f"\n\n… e mais {len(rows) - 15} modelo(s)."
            texto = f"**Modelos na coleção:** {len(rows)}\n\n{texto}"
        await self._mostrar(interaction, "🃏 Sua coleção", texto)

    @discord.ui.button(label="Histórico de drops", emoji="🎁", style=discord.ButtonStyle.secondary, row=0)
    async def drops(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await self.bot.db.coliseu_historico_drops(self.user_id, 12)
        if not rows:
            texto = "Nenhum drop registrado ainda. Recompensas são vinculadas a eventos identificáveis para impedir duplicidade."
        else:
            linhas = []
            for row in rows:
                nome = _nome_carta(row["card_id"] or "", "") if row["card_id"] else "Recursos"
                resultado = str(row["outcome"] or "")
                if resultado == "carta":
                    detalhe = f"Carta: **{nome}** ({row['rarity'] or 'raridade não informada'})"
                elif resultado == "almas":
                    detalhe = f"**{int(row['almas_delta'] or 0)} Almas**"
                elif resultado == "fragmentos":
                    detalhe = f"**{int(row['fragmentos_delta'] or 0)} fragmentos**"
                else:
                    detalhe = resultado.replace("_", " ").title() or "Recompensa"
                linhas.append(f"• {detalhe} · origem: `{row['origin'] or 'não informada'}` · {row['created_at']}")
            texto = "\n".join(linhas)
        await self._mostrar(interaction, "🎁 Histórico de drops", texto)

    @discord.ui.button(label="Estatísticas", emoji="📊", style=discord.ButtonStyle.secondary, row=0)
    async def estatisticas(self, interaction: discord.Interaction, button: discord.ui.Button):
        estado = await self.bot.db.coliseu_estado_usuario(self.user_id)
        ranking = await self.bot.db._one(
            "SELECT mmr,wins,losses,draws FROM cartas_gwent_rankings WHERE user_id=?",
            (self.user_id,),
        )
        partidas = await self.bot.db._one(
            "SELECT COUNT(*) AS total FROM cartas_gwent_matches WHERE creator_id=? OR opponent_id=?",
            (self.user_id, self.user_id),
        )
        ranking = dict(ranking) if ranking else {"mmr": 1000, "wins": 0, "losses": 0, "draws": 0}
        texto = (
            f"**Coleção:** {estado['cartas']} cartas\n"
            f"**Almas:** {estado['almas']:,}\n"
            f"**Fragmentos:** {estado['fragmentos']:,}\n"
            f"**Gwent:** {int(partidas['total'] or 0)} partidas · {ranking['wins']} vitórias · {ranking['losses']} derrotas · {ranking['draws']} empates\n"
            f"**MMR:** {ranking['mmr']}"
        )
        await self._mostrar(interaction, "📊 Suas estatísticas", texto)

    @discord.ui.button(label="Atualizar painel", emoji="🔄", style=discord.ButtonStyle.secondary, row=1)
    async def atualizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        estado = await self.bot.db.coliseu_estado_usuario(self.user_id)
        ranking = await self.bot.db._one(
            "SELECT mmr,wins,losses,draws FROM cartas_gwent_rankings WHERE user_id=?",
            (self.user_id,),
        )
        partidas = await self.bot.db._one(
            "SELECT COUNT(*) AS total FROM cartas_gwent_matches WHERE creator_id=? OR opponent_id=?",
            (self.user_id, self.user_id),
        )
        ranking = dict(ranking) if ranking else {"mmr": 1000, "wins": 0, "losses": 0, "draws": 0}
        embed = discord.Embed(
            title="🏛️ Cartas do Coliseu",
            description=(
                "Sua central de coleção, drops e recursos. No site você também compra pacotes, monta decks e disputa partidas.\n\n"
                f"**Coleção:** {estado['cartas']} cartas\n"
                f"**Almas:** {estado['almas']:,} · **Fragmentos:** {estado['fragmentos']:,}\n"
                f"**Gwent:** {int(partidas['total'] or 0)} partidas · {ranking['wins']} vitórias · {ranking['losses']} derrotas\n"
                f"**MMR:** {ranking['mmr']}"
            ),
            color=COR_COLISEU,
        )
        embed.set_footer(text="Cartas do Coliseu · NARA")
        await interaction.response.edit_message(embed=embed, view=self)


class PainelJogo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def abrir_painel(self, interaction: discord.Interaction, callback_voltar=None):
        user_id = int(interaction.user.id)
        estado = await self.bot.db.coliseu_estado_usuario(user_id)
        ranking_row = await self.bot.db._one(
            "SELECT mmr,wins,losses,draws FROM cartas_gwent_rankings WHERE user_id=?",
            (user_id,),
        )
        partidas_row = await self.bot.db._one(
            "SELECT COUNT(*) AS total FROM cartas_gwent_matches WHERE creator_id=? OR opponent_id=?",
            (user_id, user_id),
        )
        ranking = dict(ranking_row) if ranking_row else {
            "mmr": 1000, "wins": 0, "losses": 0, "draws": 0,
        }
        total_partidas = int(partidas_row["total"] or 0) if partidas_row else 0
        embed = discord.Embed(
            title="🏛️ Cartas do Coliseu",
            description=(
                "Sua central de coleção, drops e recursos. No site você também compra pacotes, monta decks e disputa partidas.\n\n"
                f"**Coleção:** {estado['cartas']} cartas\n"
                f"**Almas:** {estado['almas']:,} · **Fragmentos:** {estado['fragmentos']:,}\n"
                f"**Gwent:** {total_partidas} partidas · {int(ranking['wins'])} vitórias · {int(ranking['losses'])} derrotas\n"
                f"**MMR:** {int(ranking['mmr'])}"
            ),
            color=COR_COLISEU,
        )
        embed.set_footer(text="Cartas do Coliseu · NARA")
        view = PainelJogoView(self.bot, interaction.user.id, callback_voltar=callback_voltar)
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view, content=None)
        else:
            await interaction.response.edit_message(embed=embed, view=view, content=None)

    @app_commands.command(name="jogo", description="Abre o painel de Cartas do Coliseu: coleção, drops e acesso ao jogo no site.")
    @app_commands.guild_only()
    async def jogo(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.abrir_painel(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(PainelJogo(bot))
