"""Painel de entrada do jogo Cartas do Coliseu.

O comando público /jogo é a entrada Discord do Coliseu. O Discord consulta
coleção, drops e recursos; Mercado, deckbuilding e partidas competitivas acontecem no site.
"""
from __future__ import annotations

import os
import json

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

class ConfirmarConvergenciaView(discord.ui.View):
    def __init__(self, bot, user_id, exemplar_ids, resumo):
        super().__init__(timeout=120)
        self.bot, self.user_id = bot, int(user_id)
        self.exemplar_ids, self.resumo = list(exemplar_ids), resumo

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Este ritual pertence a outro jogador.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirmar sacrifício", emoji="🔥", style=discord.ButtonStyle.danger)
    async def confirmar(self, interaction, button):
        resultado = await self.bot.db.coliseu_convergir_exemplares(self.user_id, self.exemplar_ids)
        status = resultado.get("status")
        if status == "ok":
            embed = discord.Embed(
                title="🔥 Convergência concluída",
                description=(f"{self.resumo}\\n\\n**Novo exemplar:** #{resultado['exemplar_id']}"
                             f"\\n**Raridade:** {resultado['rarity']} · **Poder:** {resultado['power']}"
                             "\\n\\nMemória dos três sacrifícios registrada. Poder não foi transferido."),
                color=COR_COLISEU)
            return await interaction.response.edit_message(embed=embed, view=None)
        mensagens = {
            "exemplar_equipado": "Um dos exemplares está equipado no deck. Retire-o antes do ritual.",
            "ritual_especial_necessario": "Esta evolução exige um Ritual Ancestral.",
            "receita_incompativel": "Receita inválida. Use três exemplares do mesmo modelo e raridade.",
            "exemplar_nao_encontrado": "Um dos exemplares não está mais disponível.",
            "deck_indisponivel": "Não foi possível validar o deck. Nenhum exemplar foi consumido.",
        }
        await interaction.response.edit_message(content="⛔ " + mensagens.get(status, "Ritual não concluído."), embed=None, view=None)

    @discord.ui.button(label="Cancelar", emoji="↩️", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction, button):
        await interaction.response.edit_message(content="Ritual cancelado. Nenhum exemplar foi consumido.", embed=None, view=None)


class SelecaoConvergencia(discord.ui.Select):
    def __init__(self, bot, user_id, rows):
        self.bot, self.user_id = bot, int(user_id)
        self.rows_by_id = {int(r["id"]): dict(r) for r in rows}
        options = [discord.SelectOption(
            label=f"{_nome_carta(r['card_id'])} · {r['rarity']}"[:100],
            value=str(r["id"]),
            description=f"Exemplar #{r['id']} · Poder {r['power']}"[:100])
            for r in rows[:25]]
        super().__init__(placeholder="Selecione exatamente 3 exemplares", min_values=3, max_values=3, options=options)

    async def callback(self, interaction):
        escolhidos = [self.rows_by_id[int(x)] for x in self.values]
        if len({r["card_id"] for r in escolhidos}) != 1 or len({r["rarity"] for r in escolhidos}) != 1:
            return await interaction.response.send_message("Selecione três exemplares do mesmo modelo e raridade.", ephemeral=True)
        from sistemas.cartas import RARIDADES
        raridade = str(escolhidos[0]["rarity"])
        if raridade not in RARIDADES or RARIDADES.index(raridade)+1 >= len(RARIDADES):
            return await interaction.response.send_message("Esta raridade exige um Ritual Ancestral.", ephemeral=True)
        proxima = RARIDADES[RARIDADES.index(raridade)+1]
        if proxima in ("Primordial", "Singular"):
            return await interaction.response.send_message("A próxima raridade exige um Ritual Ancestral.", ephemeral=True)
        nome = _nome_carta(escolhidos[0]["card_id"])
        resumo = f"**{nome}** · {raridade} → {proxima}\\nSacrificar: " + ", ".join(
            f"#{r['id']} (Poder {r['power']})" for r in escolhidos)
        embed = discord.Embed(
            title="⚠️ Prévia do Ritual de Convergência",
            description=(resumo + "\\n\\n**Resultado:** 1 exemplar na raridade seguinte, com poder mínimo."
                         "\\n**Custo:** 3 exemplares. Operação irreversível."
                         "\\nPoder e lapidação dos sacrificados não são transferidos."),
            color=0xA33B32)
        await interaction.response.send_message(
            embed=embed, view=ConfirmarConvergenciaView(self.bot, self.user_id, [int(x) for x in self.values], resumo),
            ephemeral=True)


class ConvergenciaView(discord.ui.View):
    def __init__(self, bot, user_id, rows):
        super().__init__(timeout=180)
        self.add_item(SelecaoConvergencia(bot, user_id, rows))






class SelecaoForja(discord.ui.Select):
    def __init__(self, view, rows):
        self.parent_view = view
        self.rows_by_id = {int(r["id"]): dict(r) for r in rows}
        options = []
        for r in rows:
            nome = _nome_carta(r["card_id"])
            options.append(discord.SelectOption(
                label=f"{nome} · {r['rarity']}"[:100],
                value=str(r["id"]),
                description=f"Exemplar #{r['id']} · Poder {r['power']}"[:100],
            ))
        super().__init__(placeholder="Escolha um exemplar para aprimorar", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction):
        row = self.rows_by_id[int(self.values[0])]
        self.parent_view.selected = row
        from sistemas.cartas import CUSTO_APRIMORAMENTO_ALMAS, BONUS_EVOLUCAO_FRAGMENTOS, get_carta, faixa_poder_exemplar
        card = get_carta(str(row["card_id"]))
        if card is None or str(card.categoria).casefold() == "especial":
            return await interaction.response.send_message("Esta carta não pode ser aprimorada na Forja.", ephemeral=True)
        rarity, power = str(row["rarity"]), int(row["power"] or 0)
        _, maximum = faixa_poder_exemplar(card, rarity)
        lap_cost = CUSTO_APRIMORAMENTO_ALMAS.get(rarity)
        evo_cost = BONUS_EVOLUCAO_FRAGMENTOS.get(rarity)
        from sistemas.cartas import RARIDADES
        next_rarity = RARIDADES[RARIDADES.index(rarity)+1] if rarity in RARIDADES and RARIDADES.index(rarity)+1 < len(RARIDADES) else None
        if next_rarity in ("Primordial", "Singular"):
            next_rarity = None
        embed = discord.Embed(
            title=f"⚒️ Forja · {_nome_carta(row['card_id'])}",
            description=(f"**Exemplar:** #{row['id']}\n**Raridade:** {rarity}"
                         f"\n**Poder:** {power}/{maximum}"
                         f"\n\n**Lapidação:** {('+' + str(1) + ' poder por ' + str(lap_cost) + ' Almas') if lap_cost is not None and power < maximum else 'Indisponível (limite atingido)'}"
                         f"\n**Ascensão:** {(rarity + ' → ' + next_rarity + ' por ' + str(evo_cost) + ' Fragmentos') if next_rarity and evo_cost is not None else 'Indisponível nesta raridade'}"
                         "\n\nCada operação afeta somente este exemplar."),
            color=COR_COLISEU)
        self.parent_view.lapidar.disabled = lap_cost is None or power >= maximum
        self.parent_view.ascender.disabled = evo_cost is None or next_rarity is None
        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class ForjaView(discord.ui.View):
    def __init__(self, bot, user_id, rows):
        super().__init__(timeout=180)
        self.bot, self.user_id = bot, int(user_id)
        self.rows = [dict(r) for r in rows]
        self.page = 0
        self.page_size = 25
        self.selected = None
        self.selector = SelecaoForja(self, self.rows[:self.page_size])
        self.add_item(self.selector)
        self.anterior.disabled = True
        self.proxima.disabled = len(self.rows) <= self.page_size

    async def _change_page(self, interaction, delta):
        total_pages = max(1, (len(self.rows) + self.page_size - 1) // self.page_size)
        self.page = max(0, min(total_pages - 1, self.page + delta))
        self.selected = None
        self.lapidar.disabled = True
        self.ascender.disabled = True
        if self.selector is not None:
            self.remove_item(self.selector)
        start = self.page * self.page_size
        self.selector = SelecaoForja(self, self.rows[start:start + self.page_size])
        self.add_item(self.selector)
        self.anterior.disabled = self.page == 0
        self.proxima.disabled = self.page >= total_pages - 1
        await interaction.response.edit_message(
            content=f"Página **{self.page + 1}/{total_pages}** · {len(self.rows)} exemplares",
            view=self)

    @discord.ui.button(label="Anterior", emoji="◀️", style=discord.ButtonStyle.secondary, row=0)
    async def anterior(self, interaction, button):
        await self._change_page(interaction, -1)

    @discord.ui.button(label="Próxima", emoji="▶️", style=discord.ButtonStyle.secondary, row=0)
    async def proxima(self, interaction, button):
        await self._change_page(interaction, 1)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Esta Forja pertence a outro jogador.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Lapidar +1", emoji="✦", style=discord.ButtonStyle.primary, row=2, disabled=True)
    async def lapidar(self, interaction, button):
        if not self.selected:
            return await interaction.response.send_message("Selecione um exemplar primeiro.", ephemeral=True)
        result = await self.bot.db.coliseu_aprimorar_exemplar(self.user_id, int(self.selected["id"]))
        if result.get("status") == "ok":
            await interaction.response.edit_message(content=(f"✦ Lapidação concluída no exemplar **#{result['exemplar_id']}**. "
                f"Poder: **{result['power']}/{result['max_power']}** · Almas gastas: **{result['almas_gastas']}**."), embed=None, view=None)
        else:
            messages = {"almas_insuficientes": f"Almas insuficientes: precisa de {result.get('necessarias', '?')}; saldo {result.get('saldo', 0)}.",
                        "limite_poder_modelo": "Este exemplar já atingiu o poder máximo.",
                        "carta_especial_nao_aprimora": "Cartas especiais não podem ser lapidadas.",
                        "nao_encontrado": "Exemplar não encontrado na sua coleção."}
            await interaction.response.edit_message(content="⛔ " + messages.get(result.get("status"), "Não foi possível lapidar o exemplar."), embed=None, view=None)

    @discord.ui.button(label="Ascender", emoji="⬆️", style=discord.ButtonStyle.success, row=2, disabled=True)
    async def ascender(self, interaction, button):
        if not self.selected:
            return await interaction.response.send_message("Selecione um exemplar primeiro.", ephemeral=True)
        result = await self.bot.db.coliseu_evoluir_exemplar(self.user_id, int(self.selected["id"]))
        if result.get("status") == "ok":
            await interaction.response.edit_message(content=(f"⬆️ Ascensão concluída no exemplar **#{result['exemplar_id']}**. "
                f"Nova raridade: **{result['rarity']}** · Poder: **{result['power']}** · "
                f"Fragmentos gastos: **{result['fragmentos_gastos']}**."), embed=None, view=None)
        else:
            messages = {"fragmentos_insuficientes": f"Fragmentos insuficientes: precisa de {result.get('necessarios', '?')}; saldo {result.get('saldo', 0)}.",
                        "limite_raridade": "Este exemplar não pode ascender por esta trilha.",
                        "carta_especial_nao_evolui": "Cartas especiais não podem ascender.",
                        "nao_encontrado": "Exemplar não encontrado na sua coleção."}
            await interaction.response.edit_message(content="⛔ " + messages.get(result.get("status"), "Não foi possível ascender o exemplar."), embed=None, view=None)


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
        self.add_item(discord.ui.Button(
            label="Forja no site", emoji="⚒️", style=discord.ButtonStyle.link,
            url=f"{base_url}/forja", row=1,
        ))
        self.add_item(discord.ui.Button(
            label="Receitas de Linhagem", emoji="🜂", style=discord.ButtonStyle.link,
            url=f"{base_url}/linhagens", row=1,
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

    @discord.ui.button(label="Forja", emoji="⚒️", style=discord.ButtonStyle.primary, row=2)
    async def forja(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await self.bot.db.coliseu_listar_exemplares(self.user_id)
        from sistemas.cartas import get_carta
        elegiveis = [r for r in rows if (get_carta(str(r["card_id"])) is not None
                    and str(get_carta(str(r["card_id"])).categoria).casefold() != "especial")]
        if not elegiveis:
            return await interaction.response.send_message("Você ainda não possui unidades elegíveis para a Forja.", ephemeral=True)
        embed = discord.Embed(
            title="⚒️ Forja das Terras Intermédias",
            description=("Selecione um exemplar para consultar os custos e limites. "
                         "Lapidação consome Almas e concede +1 poder; Ascensão consome Fragmentos e eleva a raridade. "
                         "As operações são individuais e não transferem progresso entre duplicatas."),
            color=COR_COLISEU)
        paginas = max(1, (len(elegiveis) + 24) // 25)
        embed.set_footer(text=f"{len(elegiveis)} exemplares elegíveis · {paginas} página(s)")
        await interaction.response.send_message(
            content=f"Página **1/{paginas}** · {len(elegiveis)} exemplares",
            embed=embed, view=ForjaView(self.bot, self.user_id, elegiveis), ephemeral=True)

    @discord.ui.button(label="Ritual de Convergência", emoji="🔥", style=discord.ButtonStyle.success, row=2)
    async def convergencia(self, interaction, button):
        rows = await self.bot.db.coliseu_listar_exemplares(self.user_id)
        from collections import Counter
        from sistemas.cartas import get_carta
        grupos = Counter((str(r["card_id"]), str(r["rarity"])) for r in rows)
        elegiveis = []
        for r in rows:
            modelo = get_carta(str(r["card_id"]))
            if modelo is not None and str(modelo.categoria).casefold() != "especial" and grupos[(str(r["card_id"]), str(r["rarity"]))] >= 3:
                elegiveis.append(r)
        if not elegiveis:
            return await interaction.response.send_message(
                "Você ainda não possui três exemplares do mesmo modelo e raridade elegíveis.", ephemeral=True)
        embed = discord.Embed(
            title="🔥 Forja · Ritual de Convergência",
            description=("Selecione três exemplares do mesmo modelo e raridade. "
                         "Você verá o resultado antes da confirmação. Exemplares equipados no deck serão bloqueados."),
            color=COR_COLISEU)
        await interaction.response.send_message(
            embed=embed, view=ConvergenciaView(self.bot, self.user_id, elegiveis[:25]), ephemeral=True)

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
