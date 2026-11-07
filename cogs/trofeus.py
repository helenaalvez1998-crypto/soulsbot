"""Caçador de Troféus — interface e importação de catálogos."""
import json
import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
import trofeus_service as svc

log = logging.getLogger("nara.trofeus")


def _barra(atual: int, total: int, tamanho: int = 12) -> str:
    if total <= 0:
        return "▱" * tamanho
    cheios = round(max(0, min(1, atual / total)) * tamanho)
    return "▰" * cheios + "▱" * (tamanho - cheios)


def _nome(item):
    return svc.nome_exibicao(item["name_pt"], item["name_original"])


class SeletorJogo(discord.ui.Select):
    def __init__(self, cog, user_id, jogos):
        self.cog, self.user_id = cog, user_id
        options = [
            discord.SelectOption(label=g["name"][:100], value=str(g["id"]),
                                 description=("Catálogo pronto para uso")[:100])
            for g in jogos[:25]
        ]
        super().__init__(placeholder="Escolha um jogo...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        game = await svc.buscar_jogo(self.cog.bot.db, int(self.values[0]))
        if not game or game["status"] != "ready":
            return await interaction.response.send_message("Esse catálogo não está disponível no momento.", ephemeral=True)
        await svc.registrar_acesso(self.cog.bot.db, self.user_id, int(game["id"]))
        view = PainelJogoView(self.cog, self.user_id, game)
        await interaction.response.edit_message(embed=await view.embed(), view=view)


class PainelCacadorView(discord.ui.View):
    def __init__(self, cog, user):
        super().__init__(timeout=300)
        self.cog, self.user_id = cog, user.id

    async def embed(self):
        jogos = await svc.listar_jogos(self.cog.bot.db)
        ultimo = await svc.ultimo_jogo(self.cog.bot.db, self.user_id)
        e = discord.Embed(
            title="📜 NARA — CAÇADOR DE TROFÉUS",
            description="Acompanhe troféus e colecionáveis em um único progresso.\n"
                        "Escolha um jogo para começar ou retome sua última jornada.",
            color=config.COR_OURO,
        )
        if ultimo:
            feitos, total = await svc.progresso_jogo(self.cog.bot.db, ultimo["id"], self.user_id)
            e.add_field(
                name="▶️ Continuar jornada",
                value=f"**{ultimo['name']}**\n{feitos}/{total} itens · {_barra(feitos,total)}",
                inline=False,
            )
        if jogos:
            e.add_field(name="🎮 Jogos disponíveis", value="\n".join(f"• {g['name']}" for g in jogos[:10]), inline=False)
            if len(jogos) > 10:
                e.add_field(name="Catálogo", value=f"+ {len(jogos)-10} jogos disponíveis", inline=False)
        else:
            e.add_field(
                name="Catálogo em preparação",
                value="Ainda não há jogos publicados. Os catálogos precisam ser importados e validados antes de aparecerem para os jogadores.",
                inline=False,
            )
        e.set_footer(text="Seu progresso é individual e fica salvo no banco da Nara.")
        return e

    async def montar(self):
        self.clear_items()
        jogos = await svc.listar_jogos(self.cog.bot.db)
        if jogos:
            self.add_item(SeletorJogo(self.cog, self.user_id, jogos))
        ultimo = await svc.ultimo_jogo(self.cog.bot.db, self.user_id)
        if ultimo:
            self.add_item(BotaoRetomar(self.cog, self.user_id, int(ultimo["id"])))
        self.add_item(BotaoSolicitarJogo(self.cog))
        self.add_item(BotaoFechar())


class BotaoRetomar(discord.ui.Button):
    def __init__(self, cog, user_id, game_id):
        super().__init__(label="Continuar última jornada", emoji="▶️", style=discord.ButtonStyle.success, row=1)
        self.cog, self.user_id, self.game_id = cog, user_id, game_id

    async def callback(self, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        game = await svc.buscar_jogo(self.cog.bot.db, self.game_id)
        if not game:
            return await interaction.response.send_message("Jogo não encontrado.", ephemeral=True)
        view = PainelJogoView(self.cog, self.user_id, game)
        await interaction.response.edit_message(embed=await view.embed(), view=view)


class SolicitarJogoModal(discord.ui.Modal, title="Solicitar cadastro de jogo"):
    nome = discord.ui.TextInput(
        label="Nome do jogo",
        placeholder="Ex.: Lies of P",
        max_length=100,
        required=True,
    )
    plataforma = discord.ui.TextInput(
        label="Plataforma (opcional)",
        placeholder="PC, PlayStation, Xbox...",
        max_length=80,
        required=False,
    )

    def __init__(self, cog):
        super().__init__(timeout=180)
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        nome = str(self.nome.value).strip()
        plataforma = str(self.plataforma.value or "").strip()
        await self.cog.bot.db.conn.execute(
            """INSERT INTO catalog_import_jobs(requested_by,game_name,status,progress,details,updated_at)
               VALUES (?,?, 'queued', 0, ?, CURRENT_TIMESTAMP)""",
            (interaction.user.id, nome, plataforma),
        )
        await self.cog.bot.db.conn.commit()
        await interaction.response.send_message(
            f"📥 Solicitação de **{discord.utils.escape_markdown(nome)}** registrada. "
            "Ela entrou na fila de novos catálogos. A pesquisa automática por fontes externas ainda será ativada "
            "na próxima etapa; por enquanto, a solicitação fica registrada para processamento administrativo.",
            ephemeral=True,
        )


class BotaoSolicitarJogo(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(label="Não encontrou seu jogo? Solicitar cadastro", emoji="🔎",
                         style=discord.ButtonStyle.secondary, row=1)
        self.cog = cog

    async def callback(self, interaction):
        await interaction.response.send_modal(SolicitarJogoModal(self.cog))


class BotaoFechar(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Fechar", emoji="✖️", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction):
        await interaction.response.edit_message(content="Painel fechado.", embed=None, view=None)


class PainelJogoView(discord.ui.View):
    def __init__(self, cog, user_id, game):
        super().__init__(timeout=300)
        self.cog, self.user_id, self.game = cog, user_id, game

    async def embed(self):
        feitos, total = await svc.progresso_jogo(self.cog.bot.db, self.game["id"], self.user_id)
        cats = await svc.categorias_do_jogo(self.cog.bot.db, self.game["id"])
        trophies = await svc.listar_trofeus(self.cog.bot.db, self.game["id"])
        e = discord.Embed(
            title=f"🎮 {self.game['name']}",
            description=f"**Progresso das coleções:** {feitos}/{total} itens\n"
                        f"`{_barra(feitos,total)}` {round(feitos/total*100) if total else 0}%",
            color=config.COR_OURO,
        )
        if cats:
            e.add_field(
                name="📦 Coleções",
                value="\n".join(f"• **{c['category']}** — {c['total']} itens" for c in cats[:12]),
                inline=False,
            )
        if trophies:
            e.add_field(name="🏆 Troféus cadastrados", value=str(len(trophies)), inline=True)
        e.set_footer(text="Marque cada item uma vez; o progresso é compartilhado com os troféus relacionados.")
        return e

    @discord.ui.button(label="Coleções", emoji="📦", style=discord.ButtonStyle.primary, row=0)
    async def colecoes(self, interaction, button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        cats = await svc.categorias_do_jogo(self.cog.bot.db, self.game["id"])
        if not cats:
            return await interaction.response.send_message("Ainda não existem coleções cadastradas para este jogo.", ephemeral=True)
        view = CategoriasView(self.cog, self.user_id, self.game, cats)
        await interaction.response.edit_message(embed=await view.embed(), view=view)

    @discord.ui.button(label="Troféus", emoji="🏆", style=discord.ButtonStyle.success, row=0)
    async def trofeus(self, interaction, button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        view = TrofeusView(self.cog, self.user_id, self.game)
        await view.rebuild()
        await interaction.response.edit_message(embed=await view.embed(), view=view)

    @discord.ui.button(label="Voltar", emoji="↩️", style=discord.ButtonStyle.secondary, row=1)
    async def voltar(self, interaction, button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        view = PainelCacadorView(self.cog, interaction.user)
        await view.montar()
        await interaction.response.edit_message(embed=await view.embed(), view=view)


class SeletorCategoria(discord.ui.Select):
    def __init__(self, view, categories):
        self.parent = view
        options = [
            discord.SelectOption(label=f"{c['category']} ({c['total']})"[:100], value=c["category"])
            for c in categories[:25]
        ]
        super().__init__(placeholder="Escolha uma coleção...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.parent.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        view = ListaItensView(self.parent.cog, self.parent.user_id, self.parent.game, self.values[0])
        await view.rebuild()
        await interaction.response.edit_message(embed=await view.embed(), view=view)


class CategoriasView(discord.ui.View):
    def __init__(self, cog, user_id, game, categories):
        super().__init__(timeout=300)
        self.cog, self.user_id, self.game = cog, user_id, game
        self.add_item(SeletorCategoria(self, categories))
        self.add_item(BotaoVoltarJogo(cog, user_id, game))

    async def embed(self):
        e = discord.Embed(title=f"📦 Coleções — {self.game['name']}",
                          description="Escolha uma categoria para ver os itens, pesquisar e marcar o que já conseguiu.",
                          color=config.COR_OURO)
        for c in await svc.categorias_do_jogo(self.cog.bot.db, self.game["id"]):
            got, total = await svc.progresso_categoria(self.cog.bot.db, self.game["id"], c["category"], self.user_id)
            e.add_field(name=c["category"], value=f"{got}/{total} · {_barra(got,total)}", inline=True)
        return e


class SeletorItem(discord.ui.Select):
    def __init__(self, parent, items):
        self.parent = parent
        options = []
        for item in items:
            label = _nome(item)
            status = "Obtido" if item["obtained"] else "Faltando"
            options.append(discord.SelectOption(
                label=label[:100], value=str(item["id"]),
                description=f"{status} · {item['category']}"[:100],
                default=(parent.selected_item_id == item["id"]),
            ))
        super().__init__(placeholder="Selecione um item para ver detalhes...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.parent.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        self.parent.selected_item_id = int(self.values[0])
        await interaction.response.edit_message(embed=await self.parent.embed(), view=self.parent)


class ListaItensView(discord.ui.View):
    PAGE_SIZE = 20

    def __init__(self, cog, user_id, game, category, page=0, selected_item_id=None):
        super().__init__(timeout=300)
        self.cog, self.user_id, self.game, self.category = cog, user_id, game, category
        self.page, self.selected_item_id = page, selected_item_id

    async def _items(self):
        return await svc.listar_itens(self.cog.bot.db, self.game["id"], self.category,
                                      self.user_id, self.PAGE_SIZE, self.page * self.PAGE_SIZE)

    async def embed(self):
        items = await self._items()
        got, total = await svc.progresso_categoria(self.cog.bot.db, self.game["id"], self.category, self.user_id)
        e = discord.Embed(
            title=f"📦 {self.category} — {self.game['name']}",
            description=f"**{got}/{total} obtidos** · {_barra(got,total)}\n"
                        f"Página {self.page+1} · Selecione um item para marcar ou consultar detalhes.",
            color=config.COR_OURO,
        )
        for it in items[:10]:
            e.add_field(name=_nome(it), value="✅ Obtido" if it["obtained"] else "⬜ Faltando", inline=True)
        if self.selected_item_id:
            selected = next((x for x in items if x["id"] == self.selected_item_id), None)
            if selected:
                details = []
                if selected["location_pt"]:
                    details.append(f"**Localização:** {selected['location_pt']}")
                if selected["acquisition_pt"]:
                    details.append(f"**Como obter:** {selected['acquisition_pt']}")
                if selected["dlc"]:
                    details.append(f"**Conteúdo:** {selected['dlc']}")
                if selected["ng_cycle"]:
                    details.append(f"**Ciclo:** {selected['ng_cycle']}")
                if selected["missable"]:
                    details.append("⚠️ **Perdível:** pode exigir atenção a uma condição ou progresso específico.")
                if selected["description_pt"]:
                    details.append(selected["description_pt"])
                if selected["source_url"]:
                    details.append(f"[Fonte consultada]({selected['source_url']})")
                e.add_field(name=f"Detalhes — {_nome(selected)}", value=("\n".join(details) or "Sem detalhes cadastrados.")[:1024], inline=False)
        return e

    async def rebuild(self):
        self.clear_items()
        items = await self._items()
        if items:
            self.add_item(SeletorItem(self, items))
        self.add_item(BotaoMarcarItem(self, True))
        self.add_item(BotaoMarcarItem(self, False))
        total = await svc.contar_itens(self.cog.bot.db, self.game["id"], self.category)
        if self.page > 0:
            self.add_item(BotaoPagina(self, -1, "Anterior"))
        if (self.page + 1) * self.PAGE_SIZE < total:
            self.add_item(BotaoPagina(self, 1, "Próxima"))
        self.add_item(BotaoVoltarCategorias(self))

    async def _marcar(self, interaction, obtido):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        if not self.selected_item_id:
            return await interaction.response.send_message("Selecione um item primeiro.", ephemeral=True)
        await svc.definir_item_obtido(self.cog.bot.db, self.user_id, self.selected_item_id, obtido)
        await self.rebuild()
        await interaction.response.edit_message(embed=await self.embed(), view=self)

    @discord.ui.button(label="Preparando...", disabled=True, row=2)
    async def placeholder(self, interaction, button):
        pass


class BotaoMarcarItem(discord.ui.Button):
    def __init__(self, parent, obtido):
        super().__init__(label="Marcar obtido" if obtido else "Desmarcar",
                         emoji="✅" if obtido else "↩️",
                         style=discord.ButtonStyle.success if obtido else discord.ButtonStyle.secondary,
                         row=1)
        self.parent, self.obtido = parent, obtido

    async def callback(self, interaction):
        await self.parent._marcar(interaction, self.obtido)


class BotaoPagina(discord.ui.Button):
    def __init__(self, parent, delta, label):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=2)
        self.parent, self.delta = parent, delta

    async def callback(self, interaction):
        if interaction.user.id != self.parent.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        self.parent.page += self.delta
        self.parent.selected_item_id = None
        await self.parent.rebuild()
        await interaction.response.edit_message(embed=await self.parent.embed(), view=self.parent)


class BotaoVoltarCategorias(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="Categorias", emoji="↩️", style=discord.ButtonStyle.secondary, row=2)
        self.parent = parent

    async def callback(self, interaction):
        if interaction.user.id != self.parent.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        cats = await svc.categorias_do_jogo(self.parent.cog.bot.db, self.parent.game["id"])
        view = CategoriasView(self.parent.cog, self.parent.user_id, self.parent.game, cats)
        await interaction.response.edit_message(embed=await view.embed(), view=view)


class BotaoVoltarJogo(discord.ui.Button):
    def __init__(self, cog, user_id, game):
        super().__init__(label="Voltar ao jogo", emoji="↩️", style=discord.ButtonStyle.secondary, row=1)
        self.cog, self.user_id, self.game = cog, user_id, game

    async def callback(self, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        view = PainelJogoView(self.cog, self.user_id, self.game)
        await interaction.response.edit_message(embed=await view.embed(), view=view)


class SeletorTrofeu(discord.ui.Select):
    def __init__(self, parent, trophies):
        self.parent = parent
        options = [
            discord.SelectOption(label=svc.nome_exibicao(t["name_pt"], t["name_original"])[:100],
                                 value=str(t["id"]), description=(t["description_pt"] or t["grade"] or "Ver requisitos")[:100])
            for t in trophies[:25]
        ]
        super().__init__(placeholder="Escolha um troféu...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.parent.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        self.parent.selected_trophy_id = int(self.values[0])
        await interaction.response.edit_message(embed=await self.parent.embed(), view=self.parent)


class TrofeusView(discord.ui.View):
    def __init__(self, cog, user_id, game):
        super().__init__(timeout=300)
        self.cog, self.user_id, self.game = cog, user_id, game
        self.selected_trophy_id = None

    async def embed(self):
        trophies = await svc.listar_trofeus(self.cog.bot.db, self.game["id"])
        e = discord.Embed(title=f"🏆 Troféus — {self.game['name']}",
                          description="Selecione um troféu para consultar descrição, requisitos e progresso.",
                          color=config.COR_OURO)
        if not trophies:
            e.description = "Ainda não há troféus cadastrados neste catálogo."
        for t in trophies[:8]:
            e.add_field(name=svc.nome_exibicao(t["name_pt"], t["name_original"]),
                        value=(t["description_pt"] or t["grade"] or "Sem descrição cadastrada.")[:250],
                        inline=False)
        if self.selected_trophy_id:
            t = next((x for x in trophies if x["id"] == self.selected_trophy_id), None)
            if t:
                done, total, reqs = await svc.progresso_trofeu(self.cog.bot.db, t["id"], self.user_id)
                lines = [f"**Progresso:** {done}/{total} · {_barra(done,total)}"]
                for r in reqs[:12]:
                    label = svc.nome_exibicao(r["name_pt"] or r["description_pt"], r["name_original"] or "")
                    lines.append(f"{'✅' if r['obtained'] else '⬜'} {label}")
                if t["source_url"]:
                    lines.append(f"[Fonte]({t['source_url']})")
                e.add_field(name=f"Detalhes — {svc.nome_exibicao(t['name_pt'], t['name_original'])}",
                            value="\n".join(lines)[:1024], inline=False)
        return e

    async def rebuild(self):
        self.clear_items()
        trophies = await svc.listar_trofeus(self.cog.bot.db, self.game["id"])
        if trophies:
            self.add_item(SeletorTrofeu(self, trophies))
        self.add_item(BotaoVoltarJogo(self.cog, self.user_id, self.game))

    @discord.ui.button(label="Voltar", emoji="↩️", style=discord.ButtonStyle.secondary, row=2)
    async def voltar(self, interaction, button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        view = PainelJogoView(self.cog, self.user_id, self.game)
        await interaction.response.edit_message(embed=await view.embed(), view=view)


class CacadorTrofeus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def abrir(self, interaction: discord.Interaction, editar: bool = False):
        view = PainelCacadorView(self, interaction.user)
        await view.montar()
        embed = await view.embed()
        if editar:
            await interaction.response.edit_message(content=None, embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="cacador", description="Abre seu painel de troféus e colecionáveis.")
    @app_commands.guild_only()
    async def cacador(self, interaction: discord.Interaction):
        await self.abrir(interaction)

    @app_commands.command(name="catalogo_importar", description="[MOD] Importa um catálogo de jogo em JSON para revisão.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def catalogo_importar(self, interaction: discord.Interaction, arquivo: discord.Attachment):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas administradores podem importar catálogos.", ephemeral=True)
        if not arquivo.filename.lower().endswith(".json") or arquivo.size > 8 * 1024 * 1024:
            return await interaction.response.send_message("Envie um arquivo .json de até 8 MB.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            raw = await arquivo.read()
            payload = json.loads(raw.decode("utf-8-sig"))
            result = await svc.importar_catalogo(self.bot.db, payload, publicar=False)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return await interaction.followup.send(f"Não foi possível importar: {str(exc)[:500]}", ephemeral=True)
        except Exception:
            log.exception("Falha ao importar catálogo JSON")
            return await interaction.followup.send("Falha interna ao importar o catálogo. Consulte os logs.", ephemeral=True)
        await interaction.followup.send(
            f"📥 **{result['name']}** importado para revisão.\n"
            f"• Itens recebidos: {result['items_received']}\n"
            f"• Troféus recebidos: {result['trophies_received']}\n"
            "O jogo ainda não aparece para os jogadores. A publicação será habilitada após validação.",
            ephemeral=True,
        )

    @app_commands.command(name="catalogo_publicar", description="[MOD] Publica um catálogo já importado e validado.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def catalogo_publicar(self, interaction: discord.Interaction, slug: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas administradores podem publicar catálogos.", ephemeral=True)
        row = await self.bot.db._one("SELECT * FROM games_catalog WHERE slug=? COLLATE NOCASE", (slug.strip(),))
        if not row:
            return await interaction.response.send_message("Não encontrei esse catálogo. Confira o slug.", ephemeral=True)
        items = await self.bot.db._one("SELECT COUNT(*) AS n FROM game_items WHERE game_id=?", (row["id"],))
        trophies = await self.bot.db._one("SELECT COUNT(*) AS n FROM game_trophies WHERE game_id=?", (row["id"],))
        if not items["n"] or not trophies["n"]:
            return await interaction.response.send_message(
                f"Publicação bloqueada: encontrei {items['n']} itens e {trophies['n']} troféus. "
                "O catálogo precisa ter as duas áreas preenchidas.", ephemeral=True)
        await self.bot.db.conn.execute(
            "UPDATE games_catalog SET status='ready', updated_at=CURRENT_TIMESTAMP WHERE id=?", (row["id"],)
        )
        await self.bot.db.conn.commit()
        await interaction.response.send_message(
            f"✅ **{row['name']}** está publicado no Caçador de Troféus.", ephemeral=True)

    @app_commands.command(name="catalogo_fila", description="[MOD] Consulta solicitações de novos jogos.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def catalogo_fila(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas administradores podem consultar a fila.", ephemeral=True)
        rows = await self.bot.db._all(
            "SELECT id, game_name, requested_by, status, created_at FROM catalog_import_jobs ORDER BY id DESC LIMIT 15"
        )
        if not rows:
            return await interaction.response.send_message("A fila de solicitações está vazia.", ephemeral=True)
        lines = [
            f"`#{r['id']}` **{discord.utils.escape_markdown(r['game_name'])}** · "
            f"<@{r['requested_by']}> · `{r['status']}` · {r['created_at']}"
            for r in rows
        ]
        embed = discord.Embed(title="📥 Solicitações de novos jogos", description="\n".join(lines), color=config.COR_OURO)
        embed.set_footer(text="A pesquisa automática e o processamento da fila serão implementados na próxima etapa.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def cog_load(self):
        log.info("Caçador de Troféus carregado.")


async def setup(bot):
    await bot.add_cog(CacadorTrofeus(bot))
