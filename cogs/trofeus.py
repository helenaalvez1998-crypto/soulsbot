"""Caçador de Troféus — interface e importação de catálogos."""
import json
import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
import trofeus_service as svc
import catalogo_ia
from gemini_resilience import GeminiUnavailableError

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
        nome = " ".join(str(self.nome.value).split()).strip()
        plataforma = " ".join(str(self.plataforma.value or "").split()).strip()
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            permitido, _, _ = await self.cog.bot.db.reservar_pesquisa_catalogo(
                interaction.user.id, limite=3, janela_minutos=10
            )
            if not permitido:
                return await interaction.followup.send(
                    "Limite de pesquisa atingido: são permitidas até 3 identificações por 10 minutos para evitar abuso da API. Tente novamente mais tarde.",
                    ephemeral=True,
                )
            result = await catalogo_ia.identificar_jogo(nome)
            candidates = result["candidates"]
            if candidates:
                view = ConfirmacaoJogoView(
                    self.cog, interaction.user.id, nome, candidates,
                    result.get("sources", []), result.get("notes", "")
                )
                return await interaction.followup.send(
                    f"Plataforma informada: **{discord.utils.escape_markdown(plataforma or 'não especificada')}**. "
                    "Confirme o título oficial abaixo para iniciar a pesquisa do catálogo.",
                    embed=view.embed(), view=view, ephemeral=True,
                )
            raise ValueError(result.get("notes") or "Não foi encontrada uma correspondência confiável.")
        except Exception as exc:
            log.exception("Falha ao identificar jogo solicitado pelo painel")
            try:
                detalhe_erro = (
                    f"{exc.admin_message} Detalhe do provedor: {exc.technical_message}"
                    if isinstance(exc, GeminiUnavailableError) else str(exc)
                )
                await self.cog.bot.db.conn.execute(
                    """INSERT INTO catalog_import_jobs(requested_by,game_name,status,progress,details,updated_at)
                       VALUES (?,?, 'needs_review', 0, ?, CURRENT_TIMESTAMP)""",
                    (interaction.user.id, nome, f"Plataforma: {plataforma}. Erro/ambiguidade: {detalhe_erro[:800]}"),
                )
                await self.cog.bot.db.conn.commit()
            except Exception:
                log.exception("Falha ao salvar solicitação administrativa para %s", nome)
            reason = (exc.user_message if isinstance(exc, GeminiUnavailableError) else str(exc)).strip() or type(exc).__name__
            try:
                await interaction.followup.send(
                    f"**A identificação automática falhou.** Solicitação: **{discord.utils.escape_markdown(nome)}**\n"
                    f"Motivo: {discord.utils.escape_markdown(reason[:700])}\n"
                    "Nenhum nome canônico foi criado. O administrador pode consultar `/catalogo_fila` e `/gemini_status`.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                log.exception("Não foi possível notificar a falha de identificação")



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


class BotaoAlternarTrofeu(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="Marcar troféu conquistado", emoji="☑️",
                         style=discord.ButtonStyle.success, row=1)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        p = self.parent
        if interaction.user.id != p.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        done, total, reqs = await svc.progresso_trofeu(p.cog.bot.db, p.selected_trophy_id, p.user_id)
        await svc.definir_trofeu_concluido(p.cog.bot.db, p.user_id, p.selected_trophy_id, not bool(done))
        await p.rebuild()
        await interaction.response.edit_message(embed=await p.embed(), view=p)


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
                    if r["item_id"] is not None:
                        label = svc.nome_exibicao(r["name_pt"] or r["description_pt"], r["name_original"] or "")
                        lines.append(f"{'✅' if r['obtained'] else '⬜'} {label}")
                    elif r["description_pt"]:
                        lines.append(f"• Requisito manual: {r['description_pt']}")
                if not any(r["item_id"] is not None for r in reqs):
                    lines.append("Este troféu é acompanhado por confirmação manual.")
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
        if self.selected_trophy_id:
            self.add_item(BotaoAlternarTrofeu(self))
        self.add_item(BotaoVoltarJogo(self.cog, self.user_id, self.game))

    @discord.ui.button(label="Voltar", emoji="↩️", style=discord.ButtonStyle.secondary, row=2)
    async def voltar(self, interaction, button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro jogador.", ephemeral=True)
        view = PainelJogoView(self.cog, self.user_id, self.game)
        await interaction.response.edit_message(embed=await view.embed(), view=view)




class SeletorCandidato(discord.ui.Select):
    def __init__(self, parent):
        self.parent = parent
        opts = []
        for i, c in enumerate(parent.candidates[:5]):
            year = f" · {c['release_year']}" if c.get("release_year") else ""
            conf = f"Confiança {round(c['confidence']*100)}%"
            opts.append(discord.SelectOption(
                label=(c["canonical_title"] + year)[:100],
                value=str(i),
                description=(f"{c.get('developer') or 'Estúdio não confirmado'} · {conf}")[:100],
            ))
        super().__init__(placeholder="Selecione o jogo correto...", min_values=1, max_values=1, options=opts)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent.user_id:
            return await interaction.response.send_message("Esta pesquisa pertence a outro membro.", ephemeral=True)
        self.parent.selected = int(self.values[0])
        await interaction.response.edit_message(embed=self.parent.embed(), view=self.parent)


class ConfirmarPesquisaJogo(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="Confirmar jogo e pesquisar catálogo", emoji="🔎",
                         style=discord.ButtonStyle.success, row=1)
        self.parent = parent
        self.claimed = False

    async def callback(self, interaction: discord.Interaction):
        p = self.parent
        if interaction.user.id != p.user_id:
            return await interaction.response.send_message("Esta pesquisa pertence a outro membro.", ephemeral=True)
        if p.selected is None:
            return await interaction.response.send_message("Selecione primeiro o jogo correto.", ephemeral=True)
        if self.claimed:
            return await interaction.response.send_message("Esta pesquisa já foi iniciada.", ephemeral=True)

        # Claim antes do primeiro await: dois cliques quase simultâneos não iniciam duas pesquisas.
        self.claimed = True
        candidate = p.candidates[p.selected]
        for child in p.children:
            child.disabled = True
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await interaction.message.edit(view=p)
        except discord.HTTPException:
            log.warning("Não foi possível desabilitar os botões da confirmação de pesquisa")

        db = p.cog.bot.db
        job_id = None
        try:
            cur = await db.conn.execute(
                """INSERT INTO catalog_import_jobs(requested_by,game_name,status,progress,details,updated_at)
                   VALUES (?,?, 'researching', 5, ?, CURRENT_TIMESTAMP)""",
                (p.user_id, candidate["canonical_title"], json.dumps({
                    "input": p.query, "candidate": candidate, "identity_sources": p.sources
                }, ensure_ascii=False)),
            )
            await db.conn.commit()
            job_id = cur.lastrowid

            payload = await catalogo_ia.pesquisar_catalogo(candidate, incluir_dlc=True)
            year = candidate.get("release_year")
            payload["name"] = (f"{candidate['canonical_title']} ({year})" if year else candidate["canonical_title"])
            payload["name_original"] = candidate.get("original_title", "")
            payload["platforms"] = candidate.get("platforms", [])
            result = await svc.importar_catalogo(db, payload, publicar=False)
            # Não converta um nome genérico (ex.: "God of War") em alias de uma edição específica.
            aliases = [p.query, *candidate.get("aliases", [])]
            base_titles = {candidate["canonical_title"].casefold(),
                           str(candidate.get("original_title") or "").casefold()}
            aliases = [a for a in aliases if str(a).strip().casefold() not in base_titles]
            await svc.salvar_aliases(db, result["game_id"], aliases)
            details = {
                "game_id": result["game_id"], "slug": result["slug"],
                "coverage_notes": payload.get("coverage_notes", ""),
                "sources": payload.get("sources", []),
                "identity_sources": p.sources,
                "research_sources": payload.get("research_sources", 0),
                "items": result["items_received"], "trophies": result["trophies_received"],
            }
            await db.conn.execute(
                """UPDATE catalog_import_jobs SET status='review',progress=100,details=?,
                   updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (json.dumps(details, ensure_ascii=False), job_id),
            )
            await db.conn.commit()
            await interaction.followup.send(
                f"**Pesquisa concluída — catálogo em revisão**\n"
                f"Jogo identificado: **{candidate['canonical_title']}**\n"
                f"Slug: `{result['slug']}`\n"
                f"Itens coletados: **{result['items_received']}** · Troféus: **{result['trophies_received']}**\n"
                f"Fontes encontradas: **{details['research_sources']}**\n"
                f"Escopo: {discord.utils.escape_markdown(details['coverage_notes'] or 'Cobertura ainda não determinada.')}\n\n"
                "O catálogo NÃO foi publicado. Os dados começam como não verificados e precisam de revisão administrativa.",
                ephemeral=True,
            )
        except Exception as exc:
            log.exception("Falha na pesquisa automática do catálogo para %s", candidate.get("canonical_title", "desconhecido"))
            if job_id is not None:
                try:
                    await db.conn.execute(
                        "UPDATE catalog_import_jobs SET status='failed',details=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (str(exc)[:1500], job_id),
                    )
                    await db.conn.commit()
                except Exception:
                    log.exception("Não foi possível registrar a falha do job %s", job_id)
            try:
                await interaction.followup.send(
                    f"A pesquisa automática falhou: `{str(exc)[:500]}`. Nenhum catálogo foi publicado. "
                    "Confira a fila administrativa e os logs do bot.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                log.exception("Não foi possível notificar o usuário sobre a falha do catálogo")



class ConfirmacaoJogoView(discord.ui.View):
    def __init__(self, cog, user_id, query, candidates, sources, notes):
        super().__init__(timeout=240)
        self.cog, self.user_id, self.query = cog, user_id, query
        self.candidates, self.sources, self.notes = candidates, sources, notes
        self.selected = 0 if len(candidates) == 1 else None
        if len(candidates) > 1:
            self.add_item(SeletorCandidato(self))
        if len(candidates) == 1:
            self.add_item(ConfirmarPesquisaJogo(self))
        self.add_item(BotaoFechar())

    def embed(self):
        e = discord.Embed(
            title="Identificação do jogo",
            description=f"Entrada pesquisada: **{discord.utils.escape_markdown(self.query)}**\n"
                        "A entrada não será usada como nome oficial. Confirme a correspondência antes da pesquisa do catálogo.",
            color=config.COR_OURO,
        )
        for i, c in enumerate(self.candidates[:5]):
            selected = " ▶" if self.selected == i else ""
            e.add_field(
                name=f"{i+1}. {c['canonical_title']}{selected}",
                value=f"Original: {c.get('original_title') or '—'} · Ano: {c.get('release_year') or '—'}\n"
                      f"Estúdio: {c.get('developer') or '—'} · Confiança estimada: {round(c['confidence']*100)}%\n"
                      f"Escopo: {c.get('edition_scope') or 'Não determinado'}\n"
                      f"{c.get('identity_evidence') or ''}"[:900],
                inline=False,
            )
        if self.notes:
            e.add_field(name="Observações", value=self.notes[:900], inline=False)
        fontes = []
        for source in self.sources[:8]:
            if not isinstance(source, dict):
                continue
            url = str(source.get("url", "")).strip()
            if not url.startswith("https://"):
                continue
            titulo = discord.utils.escape_markdown(str(source.get("title") or url)[:100])
            fontes.append(f"• [{titulo}]({url})")
        if fontes:
            e.add_field(name="Fontes para conferência", value="\n".join(fontes)[:1024], inline=False)
        elif self.sources == []:
            e.add_field(name="Base da identificação", value="Correspondência local curada. A pesquisa do catálogo ainda fará sua própria busca com fontes.", inline=False)
        e.set_footer(text="A confiança é estimativa do modelo, não garantia factual. Confira as fontes antes de confirmar.")
        return e



class ConfirmarValidacaoCatalogo(discord.ui.View):
    def __init__(self, cog, game_id, game_name, user_id):
        super().__init__(timeout=120)
        self.cog, self.game_id, self.game_name, self.user_id = cog, game_id, game_name, user_id

    @discord.ui.button(label="Confirmo que revisei", style=discord.ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id or not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Somente o administrador que abriu esta confirmação pode validar.", ephemeral=True)
        try:
            result = await svc.validar_catalogo(self.cog.bot.db, self.game_id)
        except Exception as exc:
            log.exception("Falha ao validar catálogo %s", self.game_id)
            return await interaction.response.send_message(
                f"Não foi possível validar o catálogo: {discord.utils.escape_markdown(str(exc)[:400])}",
                ephemeral=True,
            )
        await interaction.response.edit_message(
            content=(f"Registros de **{self.game_name}** marcados como revisados "
                     f"({result['items']} itens e {result['trophies']} troféus). "
                     "Agora execute `/catalogo_auditar` e depois `/catalogo_publicar` se a auditoria estiver aprovada."),
            view=None,
        )

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Confirmação pertence a outro administrador.", ephemeral=True)
        await interaction.response.edit_message(content="Validação cancelada.", view=None)


class PainelAdminCacador(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=180)
        self.cog, self.user_id = cog, user_id

    @discord.ui.button(label="Ver fila de jogos", emoji="📥", style=discord.ButtonStyle.primary)
    async def fila(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id or not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas o administrador que abriu o painel pode consultar a fila.", ephemeral=True)
        rows = await self.cog.bot.db._all(
            "SELECT id,game_name,requested_by,status,details,created_at FROM catalog_import_jobs ORDER BY id DESC LIMIT 15"
        )
        if not rows:
            return await interaction.response.send_message("A fila está vazia.", ephemeral=True)
        lines = []
        for r in rows:
            detail = (r["details"] or "").strip()
            try:
                parsed = json.loads(detail)
                detail = parsed.get("error") or parsed.get("coverage_notes") or json.dumps(parsed, ensure_ascii=False)
            except Exception:
                pass
            lines.append(
                f"`#{r['id']}` **{discord.utils.escape_markdown(r['game_name'])}** · "
                f"<@{r['requested_by']}> · `{r['status']}`\n"
                f"↳ {discord.utils.escape_markdown(detail[:220] or 'Sem detalhes.')}"
            )
        e = discord.Embed(title="Fila do Caçador", description="\n\n".join(lines)[:4000], color=config.COR_OURO)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="Fechar", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro administrador.", ephemeral=True)
        await interaction.response.edit_message(content="Painel administrativo fechado.", embed=None, view=None)


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

    @app_commands.command(name="catalogo_admin", description="[ADMIN] Abre a administração do Caçador de Troféus.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def catalogo_admin(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Você precisa da permissão Gerenciar servidor.", ephemeral=True)
        e = discord.Embed(
            title="⚙️ Administração — Caçador de Troféus",
            description=(
                "**Fluxo de trabalho**\n"
                "1. `/catalogo_fila` ou botão abaixo: consulte solicitações e erros.\n"
                "2. `/jogo_buscar`: identifique o título oficial e gere o catálogo.\n"
                "3. `/catalogo_auditar slug`: confira fontes e cobertura.\n"
                "4. `/catalogo_validar slug`: confirme que a revisão humana foi feita.\n"
                "5. `/catalogo_publicar slug`: publique após passar na auditoria.\n\n"
                "Apenas membros com **Gerenciar servidor** podem administrar. A publicação não é automática."
            ),
            color=config.COR_OURO,
        )
        await interaction.response.send_message(embed=e, view=PainelAdminCacador(self, interaction.user.id), ephemeral=True)

    @app_commands.command(name="jogo_buscar", description="Identifica o título oficial do jogo e pesquisa fontes para o catálogo.")
    @app_commands.guild_only()
    @app_commands.describe(nome="Pode ser abreviação, nome traduzido ou conter erros de digitação.")
    async def jogo_buscar(self, interaction: discord.Interaction, nome: str):
        nome = " ".join(str(nome or "").split()).strip()[:120]
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            existing = await svc.buscar_jogo_por_nome_ou_alias(self.bot.db, nome)
            if existing:
                await svc.registrar_acesso(self.bot.db, interaction.user.id, int(existing["id"]))
                view = PainelJogoView(self, interaction.user.id, existing)
                return await interaction.followup.send(
                    f"Correspondência encontrada no catálogo: **{existing['name']}**.",
                    embed=await view.embed(), view=view, ephemeral=True)

            permitido, _, _ = await self.bot.db.reservar_pesquisa_catalogo(
                interaction.user.id, limite=3, janela_minutos=10
            )
            if not permitido:
                return await interaction.followup.send(
                    "Limite de pesquisa atingido: são permitidas até 3 identificações por 10 minutos para evitar abuso da API. Tente novamente mais tarde.",
                    ephemeral=True,
                )
            result = await catalogo_ia.identificar_jogo(nome)
        except Exception as exc:
            log.exception("Falha ao identificar ou consultar jogo %r", nome)
            # Mantém um rastro administrativo sem deixar uma falha de escrita mascarar a resposta.
            try:
                await self.bot.db.conn.execute(
                    """INSERT INTO catalog_import_jobs(requested_by,game_name,status,progress,details,updated_at)
                       VALUES (?,?, 'needs_review', 0, ?, CURRENT_TIMESTAMP)""",
                    (interaction.user.id, nome, f"Falha na identificação/consulta: {str(exc)[:1200]}"),
                )
                await self.bot.db.conn.commit()
            except Exception:
                log.exception("Não foi possível guardar a falha de pesquisa para %r", nome)
            return await interaction.followup.send(
                f"Não foi possível concluir a busca: `{discord.utils.escape_markdown(str(exc)[:450])}`. "
                "Nenhum catálogo foi publicado. A falha foi enviada à fila administrativa quando possível.",
                ephemeral=True,
            )

        candidates = result.get("candidates", [])
        if not candidates:
            return await interaction.followup.send(
                "Não encontrei uma correspondência confiável. Tente incluir o ano, estúdio ou plataforma. "
                "Nenhum nome foi cadastrado.",
                ephemeral=True,
            )
        view = ConfirmacaoJogoView(self, interaction.user.id, nome, candidates,
                                   result.get("sources", []), result.get("notes", ""))
        await interaction.followup.send(embed=view.embed(), view=view, ephemeral=True)


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
        try:
            audit = await svc.publicar_catalogo(self.bot.db, int(row["id"]))
        except ValueError as exc:
            return await interaction.response.send_message(
                f"Publicação bloqueada. {discord.utils.escape_markdown(str(exc)[:900])}\n"
                "Revise as fontes e os registros, use `/catalogo_validar` após a revisão humana e tente novamente.",
                ephemeral=True,
            )
        except Exception:
            log.exception("Falha ao publicar catálogo %s", slug)
            return await interaction.response.send_message(
                "Falha interna ao publicar. O status do catálogo não foi alterado; consulte os logs.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            f"✅ **{audit['name']}** está publicado no Caçador de Troféus.", ephemeral=True)


    @app_commands.command(name="catalogo_auditar", description="[MOD] Mostra cobertura, fontes e estado de validação de um catálogo.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def catalogo_auditar(self, interaction: discord.Interaction, slug: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas administradores.", ephemeral=True)
        row = await self.bot.db._one("SELECT * FROM games_catalog WHERE slug=? COLLATE NOCASE", (slug.strip(),))
        if not row:
            return await interaction.response.send_message("Slug não encontrado.", ephemeral=True)
        a = await svc.auditar_catalogo(self.bot.db, int(row["id"]))
        sources = "\n".join(f"• [{x.get('title') or x.get('url')}]({x.get('url')})" for x in a["sources"][:8]) or "Nenhuma fonte."
        e = discord.Embed(title=f"Auditoria — {row['name']}", description=(
            f"Status: `{row['status']}`\nItens: **{a['items']}** · Troféus: **{a['trophies']}**\n"
            f"Registros com fonte: **{a['sourced']}/{a['total']}**\n"
            f"Verificados manualmente: **{a['verified']}/{a['total']}**\n"
            f"Domínios independentes: **{len(a['domains'])}** ({', '.join(a['domains'][:8]) or 'nenhum'})\n"
            f"Pronto para publicar: **{'SIM' if a['ready'] else 'NÃO'}**"
        ), color=config.COR_OURO)
        e.add_field(name="Fontes de pesquisa", value=sources[:1024], inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="catalogo_validar", description="[MOD] Confirma revisão humana de todos os registros de um catálogo.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def catalogo_validar(self, interaction: discord.Interaction, slug: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas administradores.", ephemeral=True)
        row = await self.bot.db._one("SELECT * FROM games_catalog WHERE slug=? COLLATE NOCASE", (slug.strip(),))
        if not row:
            return await interaction.response.send_message("Slug não encontrado.", ephemeral=True)
        await interaction.response.send_message(
            f"Você confirma que revisou manualmente **todos** os itens, troféus, requisitos, localizações e fontes de **{row['name']}**?\n"
            "Responda `sim` no botão para marcar os registros como verificados. Isso não publica o catálogo.",
            view=ConfirmarValidacaoCatalogo(self, int(row["id"]), row["name"], interaction.user.id),
            ephemeral=True,
        )

    @app_commands.command(name="catalogo_fila", description="[MOD] Consulta solicitações de novos jogos.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def catalogo_fila(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas administradores podem consultar a fila.", ephemeral=True)
        # Reconcilia jobs abandonados por timeout/crash mesmo quando a pesquisa foi
        # interrompida há poucos minutos e escapou ao primeiro carregamento do cog.
        await self.bot.db.conn.execute(
            """UPDATE catalog_import_jobs SET status='interrupted',
               details=CASE WHEN details='' THEN 'Pesquisa interrompida ou expirada.' ELSE details || char(10) || 'Pesquisa interrompida ou expirada.' END,
               updated_at=CURRENT_TIMESTAMP
               WHERE status='researching' AND updated_at < datetime('now','-5 minutes')"""
        )
        await self.bot.db.conn.commit()
        rows = await self.bot.db._all(
            "SELECT id, game_name, requested_by, status, details, created_at FROM catalog_import_jobs ORDER BY id DESC LIMIT 15"
        )
        if not rows:
            return await interaction.response.send_message("A fila de solicitações está vazia.", ephemeral=True)
        lines = []
        for r in rows:
            detail = (r["details"] or "").strip()
            try:
                parsed = json.loads(detail)
                detail = parsed.get("error") or parsed.get("coverage_notes") or json.dumps(parsed, ensure_ascii=False)
            except Exception:
                pass
            detail = discord.utils.escape_markdown(detail[:220]) if detail else "Sem detalhes."
            lines.append(
                f"`#{r['id']}` **{discord.utils.escape_markdown(r['game_name'])}** · "
                f"<@{r['requested_by']}> · `{r['status']}` · {r['created_at']}\n"
                f"↳ {detail}"
            )
        embed = discord.Embed(title="📥 Solicitações de novos jogos", description="\n\n".join(lines)[:4000], color=config.COR_OURO)
        embed.set_footer(text="Erros técnicos e resultados da pesquisa são exibidos nesta fila.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def cog_load(self):
        # Executado uma vez no carregamento do cog. Jobs ainda marcados como "researching"
        # não sobreviveram a um reinício do processo: registra o estado interrompido.
        await self.bot.db.conn.execute(
            """UPDATE catalog_import_jobs SET status='interrupted',
               details=CASE WHEN details='' THEN 'Processo reiniciado durante a pesquisa.' ELSE details || char(10) || 'Processo reiniciado durante a pesquisa.' END,
               updated_at=CURRENT_TIMESTAMP
               WHERE status='researching' AND updated_at < datetime('now','-5 minutes')"""
        )
        await self.bot.db.conn.commit()
        log.info("Caçador de Troféus carregado; pesquisas órfãs marcadas como interrompidas.")


async def setup(bot):
    await bot.add_cog(CacadorTrofeus(bot))
