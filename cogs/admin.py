"""Painel administrativo completo da Nara.

Um único comando /adm abre o painel principal. Toda a configuração é feita
por cliques em botões, seletores nativos de canal/cargo e modais de texto.
As configurações são persistidas por servidor via KV store com fallback para
config.py quando não há valor personalizado.
"""

import logging
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

import config
from utils import adicionar_botao_voltar, restaurar_botao_voltar
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

class ModeracaoCategoriaSelect(discord.ui.Select):
    def __init__(self, view):
        self.painel = view
        super().__init__(
            placeholder="Filtrar solicitações por categoria...",
            min_values=1,
            max_values=1,
            row=0,
            options=[
                discord.SelectOption(label="Todas as categorias", value="all", description="Uma fila única por ordem de chegada", emoji="📥"),
                discord.SelectOption(label="Platinas", value="platinas", description="Conquistas enviadas para validação", emoji="🏆"),
                discord.SelectOption(label="Runs e desafios", value="runs", description="Tempos e resultados Soulslike", emoji="⚔️"),
                discord.SelectOption(label="Jogos zerados", value="zerados", description="Registros de jogos concluídos", emoji="🎮"),
                discord.SelectOption(label="Contribuições", value="contribuicoes", description="Lore, teorias, guias, desafios e ideias", emoji="📚"),
                discord.SelectOption(label="Sinalizações", value="denuncias", description="Publicações reportadas pela comunidade", emoji="🚩"),
                discord.SelectOption(label="Ports", value="ports", description="Ports enviados pela comunidade", emoji="🕹️"),
                discord.SelectOption(label="Mods", value="mods", description="Mods enviados pela comunidade", emoji="🧩"),
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        self.painel.categoria = self.values[0]
        self.painel.pagina = 0
        await self.painel.atualizar(interaction)


class ModeracaoSolicitacaoSelect(discord.ui.Select):
    def __init__(self, view, registros):
        self.painel = view
        opcoes = []
        for item in registros[:25]:
            titulo = f"{item['tipo_label']} · #{item['id']} · {item['titulo']}"
            descricao = f"{item['membro']} · {item['criado']}"
            opcoes.append(discord.SelectOption(
                label=titulo[:100], value=f"{item['tipo']}:{item['id']}",
                description=descricao[:100], emoji=item['emoji'],
            ))
        if not opcoes:
            opcoes = [discord.SelectOption(label="Nenhuma solicitação pendente", value="none", description="Novos envios aparecerão aqui.")]
        super().__init__(
            placeholder="Selecione uma solicitação para abrir o cartão original...",
            min_values=1, max_values=1, options=opcoes, row=1,
            disabled=not registros,
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message("Não há solicitações pendentes nesta categoria.", ephemeral=True)
        tipo, raw_id = self.values[0].split(":", 1)
        await self.painel.abrir_solicitacao(interaction, tipo, int(raw_id))


class ModeracaoPainelView(discord.ui.View):
    """Fila unificada que navega até o cartão original no canal de aprovação."""
    def __init__(self, bot, user_id: int, categoria: str = "all", guild_id: int | None = None):
        super().__init__(timeout=600)
        self.bot = bot
        self.user_id = user_id
        self.guild_id = int(guild_id) if guild_id else None
        self.categoria = categoria
        self.registros = []
        self.pagina = 0
        self.add_item(ModeracaoCategoriaSelect(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from cogs.platinas import eh_moderador
        if interaction.user.id != self.user_id and not await eh_moderador(interaction.user, self.bot.db):
            await interaction.response.send_message("Este painel foi aberto por outro moderador.", ephemeral=True)
            return False
        if not await eh_moderador(interaction.user, self.bot.db) and not await _eh_admin_painel(self.bot, interaction.user):
            await interaction.response.send_message("Apenas a equipe autorizada pode acessar a Central de Moderação.", ephemeral=True)
            return False
        return True

    async def _buscar(self):
        db = self.bot.db
        registros = []
        if self.categoria in ("all", "platinas"):
            rows = await db._all(
                "SELECT id, user_id, game AS titulo, created_at AS criado, proof_msg_id AS msg_id "
                "FROM platinas WHERE status='pending' ORDER BY created_at ASC, id ASC LIMIT 100"
            )
            registros.extend({**dict(r), "tipo":"platinas", "tipo_label":"Platina", "emoji":"🏆"} for r in rows)
        if self.categoria in ("all", "runs"):
            rows = await db._all(
                "SELECT r.id, r.user_id, g.name || ' · ' || c.name AS titulo, r.created_at AS criado, "
                "r.proof_msg_id AS msg_id FROM sl_runs r "
                "JOIN sl_games g ON g.id=r.game_id JOIN sl_challenges c ON c.id=r.challenge_id "
                "WHERE r.status='pending' ORDER BY r.created_at ASC, r.id ASC LIMIT 100"
            )
            registros.extend({**dict(r), "tipo":"runs", "tipo_label":"Run/Desafio", "emoji":"⚔️"} for r in rows)
        if self.categoria in ("all", "zerados"):
            rows = await db._all(
                "SELECT id, user_id, game AS titulo, created_at AS criado, proof_msg_id AS msg_id "
                "FROM zerados WHERE status='pending' ORDER BY created_at ASC, id ASC LIMIT 100"
            )
            registros.extend({**dict(r), "tipo":"zerados", "tipo_label":"Jogo zerado", "emoji":"🎮"} for r in rows)
        if self.categoria in ("all", "contribuicoes"):
            rows = await db._all(
                "SELECT id, user_id, title AS titulo, kind, game_name, status, published_message_id, created_at AS criado "
                "FROM community_contributions WHERE guild_id=? AND (status IN ('pending','changes_requested') "
                "OR (status='approved' AND published_message_id IS NULL)) "
                "ORDER BY CASE WHEN status='approved' THEN 1 ELSE 0 END, created_at ASC, id ASC LIMIT 100",
                (self.guild_id or 0,),
            )
            registros.extend({**dict(r), "tipo":"contribuicoes",
                              "tipo_label":("Publicação pendente" if r["status"] == "approved" else f"Contribuição · {r['kind']}"),
                              "emoji":"🔁" if r["status"] == "approved" else "📚"} for r in rows)
        if self.categoria in ("all", "ports", "mods"):
            try:
                from cogs import catalogo_integrado as catalogo
                with sqlite3.connect(catalogo.DB_PATH) as conn:
                    conn.row_factory = sqlite3.Row
                    if self.categoria in ("all", "ports"):
                        rows = conn.execute(
                            "SELECT id, nome AS titulo, autor_id AS user_id, plataforma, "
                            "COALESCE(NULLIF(criado_em, ''), datetime('now')) AS criado "
                            "FROM jogos WHERE status='pendente' ORDER BY criado ASC, id ASC LIMIT 100"
                        ).fetchall()
                        registros.extend({**dict(r), "tipo":"ports", "tipo_label":"Port", "emoji":"🕹️"} for r in rows)
                    if self.categoria in ("all", "mods"):
                        rows = conn.execute(
                            "SELECT id, mod_nome AS titulo, autor_id AS user_id, jogo_nome, "
                            "datetime('now') AS criado FROM mods WHERE status='pendente' ORDER BY id ASC LIMIT 100"
                        ).fetchall()
                        registros.extend({**dict(r), "tipo":"mods", "tipo_label":"Mod", "emoji":"🧩"} for r in rows)
            except Exception:
                log.exception("Falha ao consultar pendências do catálogo Ports & Mods na Central de Moderação.")
        if self.categoria in ("all", "denuncias"):
            rows = await db.listar_denuncias_comunitarias(self.guild_id or 0, "pending", 100)
            for report in rows:
                target = f"{report['target_type']} #{report['target_id']}"
                if str(report["target_type"]).startswith("contrib_"):
                    contribution = await db.get_contribuicao(int(report["target_id"]))
                    if contribution:
                        target = f"{contribution['title']} · {report['target_type'].removeprefix('contrib_')}"
                elif report["target_type"] == "platina":
                    item = await db._one("SELECT game FROM platinas WHERE id=?", (int(report["target_id"]),))
                    target = f"Platina · {item['game']}" if item else target
                elif report["target_type"] == "zerado":
                    item = await db._one("SELECT game FROM zerados WHERE id=?", (int(report["target_id"]),))
                    target = f"Jogo zerado · {item['game']}" if item else target
                elif report["target_type"] == "run":
                    item = await db._one(
                        "SELECT g.name AS game,c.name AS challenge FROM sl_runs r JOIN sl_games g ON g.id=r.game_id JOIN sl_challenges c ON c.id=r.challenge_id WHERE r.id=?",
                        (int(report["target_id"]),),
                    )
                    target = f"Run · {item['game']} · {item['challenge']}" if item else target
                registros.append({
                    **dict(report), "titulo": target, "criado": report["created_at"],
                    "membro": f"ID {report['reporter_id']}", "tipo": "denuncias",
                    "tipo_label": f"Sinalização · {report['reason']}", "emoji": "🚩",
                })
        registros.sort(key=lambda r: (str(r.get("criado") or ""), int(r["id"])))
        for item in registros:
            autor_id = item.get("user_id", item.get("reporter_id", 0))
            item["membro"] = f"ID {autor_id}"
            item["criado"] = str(item.get("criado") or "Data não informada")[:16]
        return registros

    async def embed_painel(self):
        self.registros = await self._buscar()
        self.pagina = min(self.pagina, max(0, (len(self.registros) - 1) // 25))
        inicio = self.pagina * 25
        pagina_registros = self.registros[inicio:inicio + 25]
        db = self.bot.db
        gid = getattr(self.bot, "guild_id", None)
        # O canal é configurado por servidor; a interação define o servidor atual.
        pendentes = len(self.registros)
        embed = discord.Embed(
            title="🛡️ Central de Moderação — NARA",
            description=(
                "A fila reúne as solicitações pendentes por categoria e ordem de chegada.\n\n"
                "**Como revisar:** abra a ficha privada, confira os comprovantes e só então use os botões de decisão. O sistema registra a decisão no fluxo original; evidência primeiro, espetáculo depois."
            ), color=COR_PAINEL,
        )
        embed.add_field(name="Na lista atual", value=f"**{pendentes}** solicitação(ões) exibida(s)", inline=True)
        embed.add_field(name="Categoria", value={"all":"Todas", "platinas":"Platinas", "runs":"Runs e desafios", "zerados":"Jogos zerados", "contribuicoes":"Contribuições", "denuncias":"Sinalizações", "ports":"Ports", "mods":"Mods"}.get(self.categoria, "Todas"), inline=True)
        embed.add_field(name="Página", value=f"{self.pagina + 1} · {max(1, (len(self.registros) + 24) // 25)}", inline=True)
        if pagina_registros:
            linhas = []
            for item in pagina_registros[:10]:
                linhas.append(f"{item['emoji']} **{item['tipo_label']} #{item['id']}** — {discord.utils.escape_markdown(str(item['titulo']))[:65]} · <@{item['user_id']}>")
            embed.add_field(name="Solicitações pendentes", value="\n".join(linhas), inline=False)
            if len(self.registros) > 10:
                embed.set_footer(text="A lista de seleção contém até 25 solicitações; use o filtro para localizar outras.")
        else:
            embed.add_field(name="Fila vazia", value="Não há solicitações pendentes nesta categoria. Novos envios aparecerão aqui automaticamente.", inline=False)
        return embed

    async def atualizar(self, interaction: discord.Interaction):
        embed = await self.embed_painel()
        self.clear_items()
        self.add_item(ModeracaoCategoriaSelect(self))
        self.add_item(ModeracaoSolicitacaoSelect(self, self.registros[self.pagina * 25:(self.pagina + 1) * 25]))
        if self.pagina > 0:
            self.add_item(ModeracaoPaginaButton(self, -1))
        if (self.pagina + 1) * 25 < len(self.registros):
            self.add_item(ModeracaoPaginaButton(self, 1))
        self.add_item(ModeracaoAtualizarButton(self))
        restaurar_botao_voltar(self)
        await interaction.response.edit_message(embed=embed, view=self)

    async def abrir_solicitacao(self, interaction: discord.Interaction, tipo: str, registro_id: int):
        if tipo in ("ports", "mods"):
            from cogs import catalogo_integrado as catalogo
            with sqlite3.connect(catalogo.DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                tabela = "jogos" if tipo == "ports" else "mods"
                row = conn.execute(f"SELECT * FROM {tabela} WHERE id=? AND status='pendente'", (registro_id,)).fetchone()
            if row is None:
                return await interaction.response.send_message(
                    "Esta solicitação já foi processada ou removida. Atualize a fila.", ephemeral=True
                )
            row = dict(row)
            if tipo == "ports":
                embed, arquivo = catalogo.jogo_embed(row)
                view = catalogo.PendenteView(row, {"mode": "pendentes", "plataforma": None, "query": None, "page": 0})
                kwargs = {"embed": embed, "view": view}
                if arquivo:
                    kwargs["file"] = arquivo
                return await interaction.response.send_message(**kwargs, ephemeral=True)
            detalhes = (
                f"**Port relacionado:** {row.get('jogo_nome') or 'Não informado'}\\n"
                f"**Descrição:** {row.get('descricao') or 'Sem descrição'}\\n"
                f"**Link:** {row.get('link') or 'Não informado'}\\n"
                f"**Autor:** <@{row.get('autor_id')}>"
            )
            embed = discord.Embed(title=f"🧩 {row.get('mod_nome')}", description=detalhes, color=discord.Color.orange())
            return await interaction.response.send_message(
                embed=embed, view=catalogo.ModDecisaoView(row), ephemeral=True
            )
        if tipo == "denuncias":
            report = await self.bot.db.get_denuncia_comunitaria(registro_id)
            if report is None or report["status"] != "pending" or int(report["guild_id"]) != int(self.guild_id or 0):
                return await interaction.response.send_message("Esta sinalização já foi processada ou pertence a outro servidor. Atualize a fila.", ephemeral=True)
            from cogs.comunidade import CommunityReportReviewView
            target_type, target_id = str(report["target_type"]), int(report["target_id"])
            post = await self.bot.db.get_post_comunitario(int(report["guild_id"]), target_type, target_id)
            details = f"**Tipo:** `{target_type}` · **Registro:** `#{target_id}`\n**Canal:** <#{post['channel_id']}>" if post else f"**Tipo:** `{target_type}` · **Registro:** `#{target_id}`"
            if target_type.startswith("contrib_"):
                content = await self.bot.db.get_contribuicao(target_id)
                if content:
                    details += f"\n**Título:** {discord.utils.escape_markdown(content['title'])}\n**Conteúdo:**\n{str(content['content'])[:1800]}"
            embed = discord.Embed(
                title=f"🚩 Sinalização comunitária #{registro_id}",
                description=(f"**Enviada por:** <@{report['reporter_id']}>\n**Motivo:** {discord.utils.escape_markdown(report['reason'])}\n"
                             f"**Detalhes:**\n{report['details']}\n\n{details}"),
                color=discord.Color.orange(),
            )
            embed.set_footer(text="Ocultar remove apenas a publicação; registros de runs/platinas e auditoria são preservados.")
            comunidade = self.bot.get_cog("Comunidade")
            if comunidade is None:
                return await interaction.response.send_message("O módulo de comunidade não está carregado.", ephemeral=True)
            return await interaction.response.send_message(embed=embed, view=CommunityReportReviewView(comunidade, registro_id), ephemeral=True)
        if tipo == "contribuicoes":
            row = await self.bot.db.get_contribuicao(registro_id)
            if row is None or (self.guild_id and int(row["guild_id"]) != self.guild_id):
                return await interaction.response.send_message("Esta contribuição foi removida ou pertence a outro servidor. Atualize a fila.", ephemeral=True)
            from cogs.comunidade import CommunityReviewView, CommunityPublishRetryView, TIPOS, STATUS_PT
            if row["status"] == "approved" and not row["published_message_id"]:
                embed = discord.Embed(
                    title=f"🔁 Republicação pendente · #{registro_id}",
                    description=(f"**Título:** {discord.utils.escape_markdown(row['title'])}\n"
                                 f"**Tipo:** {TIPOS.get(row['kind'], ('Contribuição','',''))[0]}\n"
                                 "A proposta já foi aprovada e o XP foi contabilizado. A publicação no canal não foi concluída; tente novamente após conferir as permissões."),
                    color=discord.Color.orange(),
                )
                return await interaction.response.send_message(embed=embed, view=CommunityPublishRetryView(self.bot.get_cog("Comunidade"), registro_id), ephemeral=True)
            if row["status"] not in ("pending", "changes_requested"):
                return await interaction.response.send_message("Esta contribuição já foi processada. Atualize a fila.", ephemeral=True)
            label = TIPOS.get(row["kind"], ("Contribuição", "", 0))[0]
            embed = discord.Embed(
                title=f"📚 Revisão de contribuição #{registro_id} · {label}",
                description=(
                    f"**Título:** {discord.utils.escape_markdown(row['title'])}\n"
                    f"**Autor:** <@{row['user_id']}>\n"
                    f"**Jogo/universo:** {discord.utils.escape_markdown(row['game_name'] or 'Não informado')}\n"
                    f"**Setor de origem:** {discord.utils.escape_markdown(row['origin_sector'] or 'Central de Contribuições')}\n"
                    + (f"**Canal de origem:** <#{row['origin_channel_id']}>\n" if row['origin_channel_id'] else "")
                    + f"**Status:** {STATUS_PT.get(row['status'], row['status'])}"
                ),
                color=COR_PAINEL,
            )
            if row["summary"]:
                embed.add_field(name="Resumo", value=str(row["summary"])[:1000], inline=False)
            texto = str(row["content"] or "")
            embed.description = (embed.description or "") + "\n\n**Conteúdo integral**\n" + texto[:2500]
            if row["sources"]:
                embed.add_field(name="Fontes e referências", value=str(row["sources"])[:1000], inline=False)
            embed.add_field(name="Spoilers", value=str(row["spoiler_level"]), inline=True)
            embed.add_field(name="XP previsto", value=str(TIPOS.get(row["kind"], ("", "", 10))[2]), inline=True)
            if row["kind"] == "challenge":
                modo = (f"Coletivo · meta de {int(row['challenge_goal'] or 0)} conclusões"
                        if row["challenge_mode"] == "collective" else "Individual")
                embed.add_field(name="Modalidade", value=modo, inline=True)
            if row["review_note"]:
                embed.add_field(name="Orientação anterior", value=str(row["review_note"])[:1000], inline=False)
            embed.set_footer(text="Aprovação publica no canal configurado e concede XP dentro do limite semanal.")
            comunidade = self.bot.get_cog("Comunidade")
            if comunidade is None:
                return await interaction.response.send_message("O módulo de contribuições não está carregado. Verifique os logs de inicialização.", ephemeral=True)
            return await interaction.response.send_message(embed=embed, view=CommunityReviewView(comunidade, registro_id), ephemeral=True)
        tabela = {"platinas": ("platinas", "🏆 Platina"), "runs": ("sl_runs", "⚔️ Run/Desafio"), "zerados": ("zerados", "🎮 Jogo zerado")}
        if tipo not in tabela:
            return await interaction.response.send_message("Categoria inválida.", ephemeral=True)
        tabela_sql, rotulo = tabela[tipo]
        row = await self.bot.db._one(f"SELECT * FROM {tabela_sql} WHERE id=? AND status='pending'", (registro_id,))
        if row is None:
            return await interaction.response.send_message("Esta solicitação já foi processada ou removida. Atualize a fila.", ephemeral=True)
        canal_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "mod_channel")
        canal = await interaction.guild.fetch_channel(int(canal_id)) if canal_id else None
        original = None
        if canal is not None and row["proof_msg_id"]:
            try:
                original = await canal.fetch_message(int(row["proof_msg_id"]))
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                original = None
        if original and original.embeds:
            embed = discord.Embed.from_dict(original.embeds[0].to_dict())
        else:
            embed = discord.Embed(title=f"{rotulo} #{registro_id}", description=f"**Membro:** <@{row['user_id']}>\n**Status:** Aguardando análise", color=discord.Color.gold())
            embed.add_field(name="Cartão original", value="Não foi possível carregar a mensagem original. A decisão ainda pode ser registrada no painel.", inline=False)
            if tipo == "platinas": embed.set_footer(text=f"ID:{registro_id}")
            elif tipo == "runs": embed.set_footer(text=f"SL:{registro_id}")
            else: embed.set_footer(text=f"ZeradoID:{registro_id}")
        # Reutiliza exatamente os fluxos de decisão existentes, incluindo transações,
        # recompensas, logs, notificações e validações anti-duplicidade.
        if tipo == "platinas":
            from cogs.platinas import RevisaoView
            view = RevisaoView(self.bot)
        elif tipo == "runs":
            cog = self.bot.get_cog("Soulslike")
            if cog is None:
                return await interaction.response.send_message("O sistema Soulslike não está carregado.", ephemeral=True)
            from cogs.soulslike import RevisaoRunView
            view = RevisaoRunView(cog)
        else:
            cog = self.bot.get_cog("Zerados")
            if cog is None:
                return await interaction.response.send_message("O sistema de jogos zerados não está carregado.", ephemeral=True)
            from cogs.zerados import ZeradoRevisaoView
            view = ZeradoRevisaoView(cog)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ModeracaoPaginaButton(discord.ui.Button):
    def __init__(self, painel, delta):
        self.painel, self.delta = painel, delta
        super().__init__(label="Anterior" if delta < 0 else "Próxima", emoji="◀️" if delta < 0 else "▶️", style=discord.ButtonStyle.secondary, row=2)

    async def callback(self, interaction: discord.Interaction):
        self.painel.pagina = max(0, self.painel.pagina + self.delta)
        await self.painel.atualizar(interaction)


class ModeracaoAtualizarButton(discord.ui.Button):
    def __init__(self, painel):
        super().__init__(label="Atualizar fila", emoji="🔄", style=discord.ButtonStyle.secondary, row=2)
        self.painel = painel

    async def callback(self, interaction: discord.Interaction):
        await self.painel.atualizar(interaction)



# ────────────────────────────────────────────────────────────────
# Dashboard operacional e auditoria
# ────────────────────────────────────────────────────────────────

async def _contagem_status(db, tabela: str, status: str):
    row = await db._one(f"SELECT COUNT(*) AS total FROM {tabela} WHERE status=?", (status,))
    return int(row["total"] or 0)


async def _contagem_decisoes_log(db, padrao: str):
    row = await db._one(
        "SELECT COUNT(*) AS total FROM logs WHERE lower(action) LIKE lower(?) "
        "AND datetime(created_at) >= datetime('now','-7 days')",
        (padrao,),
    )
    return int(row["total"] or 0)


async def _dados_dashboard(bot, guild_id: int):
    db = bot.db
    tabelas = ("platinas", "sl_runs", "zerados")
    pendentes = aprovados_7d = rejeitados_7d = 0
    mais_antiga = None
    por_tabela = {}
    padroes = {
        "platinas": ("%platina%aprov%", "%platina%rejeit%"),
        "sl_runs": ("%run%aprov%", "%run%rejeit%"),
        "zerados": ("%zerado%aprov%", "%zerado%rejeit%"),
    }
    for tabela in tabelas:
        pend = await _contagem_status(db, tabela, "pending")
        aprov = await _contagem_decisoes_log(db, padroes[tabela][0])
        rejeit = await _contagem_decisoes_log(db, padroes[tabela][1])
        por_tabela[tabela] = (pend, aprov, rejeit)
        pendentes += pend
        aprovados_7d += aprov
        rejeitados_7d += rejeit
        row = await db._one(
            f"SELECT created_at FROM {tabela} WHERE status='pending' ORDER BY datetime(created_at) ASC LIMIT 1"
        )
        if row and row["created_at"]:
            data = str(row["created_at"])
            if mais_antiga is None or data < mais_antiga:
                mais_antiga = data
    erros = await db._one(
        """SELECT COUNT(*) AS total FROM logs
           WHERE (lower(action) LIKE '%erro%' OR lower(action) LIKE '%falha%')
             AND datetime(created_at) >= datetime('now','-24 hours')"""
    )
    logs = await db._all(
        "SELECT actor_id, action, details, created_at FROM logs ORDER BY id DESC LIMIT 5"
    )
    return {
        "pending": pendentes, "approved7": aprovados_7d, "rejected7": rejeitados_7d,
        "oldest": mais_antiga, "errors24": int(erros["total"] or 0),
        "by_table": por_tabela, "logs": logs,
    }


class DashboardAtualizarButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Atualizar indicadores", emoji="🔄", style=discord.ButtonStyle.secondary, row=1)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        from cogs.platinas import eh_moderador
        autorizado = await eh_moderador(interaction.user, self.bot.db) or await _eh_admin_painel(self.bot, interaction.user)
        if not autorizado:
            return await interaction.response.send_message("Acesso restrito à equipe autorizada.", ephemeral=True)
        await interaction.response.edit_message(embed=await _embed_dashboard(self.bot, interaction.guild_id), view=self.view)


class DashboardHistoricoButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Abrir histórico de auditoria", emoji="📜", style=discord.ButtonStyle.primary, row=1)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        from cogs.platinas import eh_moderador
        autorizado = await eh_moderador(interaction.user, self.bot.db) or await _eh_admin_painel(self.bot, interaction.user)
        if not autorizado:
            return await interaction.response.send_message("Acesso restrito à equipe autorizada.", ephemeral=True)
        callback_voltar = getattr(self.view, "callback_voltar", None)
        view = HistoricoAuditoriaView(self.bot, interaction.user.id, callback_voltar=callback_voltar)
        await interaction.response.edit_message(embed=await view.embed(), view=view)


async def _embed_dashboard(bot, guild_id: int):
    dados = await _dados_dashboard(bot, guild_id)
    embed = discord.Embed(
        title="📊 Dashboard operacional — NARA",
        description="Indicadores calculados diretamente dos registros atuais do banco. Janela de desempenho: últimos 7 dias.",
        color=COR_PAINEL,
    )
    embed.add_field(name="Fila pendente", value=f"**{dados['pending']}** solicitações", inline=True)
    embed.add_field(name="Aprovações registradas · 7 dias", value=f"**{dados['approved7']}**", inline=True)
    embed.add_field(name="Rejeições registradas · 7 dias", value=f"**{dados['rejected7']}**", inline=True)
    embed.add_field(name="Eventos com erro/falha · 24h", value=f"**{dados['errors24']}**", inline=True)
    if dados["oldest"]:
        embed.add_field(name="Solicitação pendente mais antiga", value=f"`{dados['oldest']}`", inline=True)
    else:
        embed.add_field(name="Solicitação mais antiga", value="Fila sem pendências", inline=True)
    nomes = {"platinas": "Platinas", "sl_runs": "Runs/Desafios", "zerados": "Jogos zerados"}
    linhas = [
        f"**{nomes[t]}:** {v[0]} pendentes · {v[1]} aprovações · {v[2]} rejeições registradas (7d)"
        for t, v in dados["by_table"].items()
    ]
    embed.add_field(name="Detalhamento por sistema", value="\n".join(linhas), inline=False)
    if dados["logs"]:
        linhas_log = [
            f"`{str(r['created_at'])[:16]}` · <@{r['actor_id']}> · `{r['action']}`"
            for r in dados["logs"]
        ]
        embed.add_field(name="Atividade recente", value="\n".join(linhas_log)[:1024], inline=False)
    embed.set_footer(text="As métricas refletem os dados gravados; falhas não registradas em logs não são contabilizadas.")
    return embed


class DashboardOperacionalView(discord.ui.View):
    def __init__(self, bot, user_id: int, callback_voltar=None):
        super().__init__(timeout=600)
        self.bot = bot
        self.user_id = user_id
        self.callback_voltar = callback_voltar
        self.add_item(DashboardAtualizarButton(bot))
        self.add_item(DashboardHistoricoButton(bot))
        if callback_voltar:
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à categoria")
        self._admin_message = None

    async def on_timeout(self) -> None:
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
        if self._admin_message is None:
            return
        try:
            embeds = getattr(self._admin_message, "embeds", []) or []
            if embeds:
                embed = embeds[0].copy()
                embed.set_footer(text="NARA • Dashboard · Sessão encerrada; use /adm para reabrir")
                await self._admin_message.edit(embed=embed, view=self)
            else:
                await self._admin_message.edit(content="Dashboard encerrado. Use `/adm` para reabrir.", view=self)
        except (discord.HTTPException, AttributeError):
            log.debug("Não foi possível atualizar o dashboard expirado.", exc_info=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from cogs.platinas import eh_moderador
        autorizado = await eh_moderador(interaction.user, self.bot.db) or await _eh_admin_painel(self.bot, interaction.user)
        if interaction.user.id != self.user_id or not autorizado:
            await interaction.response.send_message("Este painel é restrito à pessoa que o abriu e à equipe autorizada.", ephemeral=True)
            return False
        return True


class HistoricoFiltroSelect(discord.ui.Select):
    def __init__(self, view):
        self.painel = view
        super().__init__(
            placeholder="Filtrar histórico...",
            min_values=1, max_values=1, row=0,
            options=[
                discord.SelectOption(label="Todas as atividades", value="all"),
                discord.SelectOption(label="Moderação", value="moderation"),
                discord.SelectOption(label="Administração", value="admin"),
                discord.SelectOption(label="Erros e falhas", value="errors"),
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        self.painel.filtro = self.values[0]
        self.painel.pagina = 0
        await self.painel.atualizar(interaction)


class HistoricoBuscaModal(discord.ui.Modal, title="Pesquisar auditoria"):
    termo = discord.ui.TextInput(label="Termo, ID do usuário ou ação", min_length=2, max_length=80)

    def __init__(self, view):
        super().__init__()
        self.painel = view

    async def on_submit(self, interaction: discord.Interaction):
        self.painel.termo = str(self.termo).strip()
        self.painel.pagina = 0
        await self.painel.atualizar(interaction, responder=True)


class HistoricoBuscaButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Pesquisar", emoji="🔎", style=discord.ButtonStyle.secondary, row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(HistoricoBuscaModal(self.view))


class HistoricoAtualizarButton(discord.ui.Button):
    """Atualiza a auditoria sem perder filtro, pesquisa ou página atual."""
    def __init__(self, view):
        super().__init__(label="Atualizar", emoji="🔄", style=discord.ButtonStyle.secondary, row=2)
        self.painel = view

    async def callback(self, interaction: discord.Interaction):
        await self.painel.atualizar(interaction)


class HistoricoPaginaButton(discord.ui.Button):
    def __init__(self, view, delta):
        super().__init__(label="Anterior" if delta < 0 else "Próxima",
                         style=discord.ButtonStyle.secondary, row=2)
        self.painel, self.delta = view, delta

    async def callback(self, interaction: discord.Interaction):
        self.painel.pagina = max(0, self.painel.pagina + self.delta)
        await self.painel.atualizar(interaction)


class HistoricoAuditoriaView(discord.ui.View):
    def __init__(self, bot, user_id: int, callback_voltar=None):
        super().__init__(timeout=600)
        self.bot, self.user_id = bot, user_id
        self.callback_voltar = callback_voltar
        self.filtro, self.termo, self.pagina = "all", "", 0
        self.add_item(HistoricoFiltroSelect(self))
        self.add_item(HistoricoBuscaButton())
        self.add_item(HistoricoAtualizarButton(self))
        if callback_voltar:
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à categoria")
        self._admin_message = None

    async def on_timeout(self) -> None:
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
        if self._admin_message is None:
            return
        try:
            embeds = getattr(self._admin_message, "embeds", []) or []
            if embeds:
                embed = embeds[0].copy()
                footer = embed.footer.text or "NARA • Auditoria"
                embed.set_footer(text=f"{footer} · Sessão encerrada; use /adm para reabrir"[:2048])
                await self._admin_message.edit(embed=embed, view=self)
            else:
                await self._admin_message.edit(content="Histórico encerrado. Use `/adm` para reabrir.", view=self)
        except (discord.HTTPException, AttributeError):
            log.debug("Não foi possível atualizar o histórico expirado.", exc_info=True)

    async def _buscar(self):
        where, args = [], []
        if self.filtro == "moderation":
            where.append("(lower(action) LIKE '%platina%' OR lower(action) LIKE '%run_%' OR lower(action) LIKE '%zerado%')")
        elif self.filtro == "admin":
            where.append("(lower(action) LIKE '%admin%' OR lower(action) LIKE '%config%' OR lower(action) LIKE '%canal%' OR lower(action) LIKE '%cargo%')")
        elif self.filtro == "errors":
            where.append("(lower(action) LIKE '%erro%' OR lower(action) LIKE '%falha%')")
        if self.termo:
            where.append("(CAST(actor_id AS TEXT) LIKE ? OR lower(action) LIKE lower(?) OR lower(COALESCE(details,'')) LIKE lower(?))")
            termo = f"%{self.termo}%"
            args.extend([termo, termo, termo])
        sql = "SELECT actor_id, action, details, created_at FROM logs"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT 200"
        return await self.bot.db._all(sql, tuple(args))

    async def embed(self):
        self.registros = await self._buscar()
        max_page = max(0, (len(self.registros) - 1) // 10)
        self.pagina = min(self.pagina, max_page)
        linhas = []
        for r in self.registros[self.pagina * 10:(self.pagina + 1) * 10]:
            detalhe = str(r["details"] or "").replace("\n", " ")
            linhas.append(
                f"**{str(r['action'])[:65]}** · <@{r['actor_id']}> · `{str(r['created_at'])[:16]}`"
                + (f"\n{discord.utils.escape_markdown(detalhe)[:140]}" if detalhe else "")
            )
        embed = discord.Embed(
            title="📜 Histórico de auditoria",
            description=("\n\n".join(linhas) if linhas else "Nenhum registro encontrado para este filtro/pesquisa."),
            color=COR_PAINEL,
        )
        embed.add_field(name="Resultados", value=f"{len(self.registros)} (máximo de 200)", inline=True)
        embed.add_field(name="Página", value=f"{self.pagina + 1}/{max(1, (len(self.registros) + 9) // 10)}", inline=True)
        if self.termo:
            embed.add_field(name="Pesquisa", value=discord.utils.escape_markdown(self.termo)[:100], inline=False)
        embed.set_footer(text="Auditoria baseada na tabela logs; registros antigos dependem do que já era gravado pelo bot.")
        return embed

    async def atualizar(self, interaction: discord.Interaction, responder: bool = False):
        embed = await self.embed()
        self.clear_items()
        self.add_item(HistoricoFiltroSelect(self))
        self.add_item(HistoricoBuscaButton())
        self.add_item(HistoricoAtualizarButton(self))
        if self.pagina > 0:
            self.add_item(HistoricoPaginaButton(self, -1))
        if (self.pagina + 1) * 10 < len(self.registros):
            self.add_item(HistoricoPaginaButton(self, 1))
        restaurar_botao_voltar(self)
        if responder:
            await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from cogs.platinas import eh_moderador
        autorizado = await eh_moderador(interaction.user, self.bot.db) or await _eh_admin_painel(self.bot, interaction.user)
        if interaction.user.id != self.user_id or not autorizado:
            await interaction.response.send_message("Este histórico é restrito à pessoa que o abriu e à equipe autorizada.", ephemeral=True)
            return False
        return True


class PublicarPaineisView(discord.ui.View):
    """Publica/atualiza os painéis persistentes existentes e fixa a mensagem no canal escolhido."""

    def __init__(self, bot, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.tipo = "principal"
        self.canal = None
        opcoes = [
            discord.SelectOption(label="Painel principal (Coliseu)", value="principal", emoji="🎮"),
            discord.SelectOption(label="Painel de Platinas", value="platinas", emoji="🏆"),
            discord.SelectOption(label="Painel de Jogos Zerados", value="zerados", emoji="✅"),
            discord.SelectOption(label="Central de Ajuda da NARA", value="ajuda", emoji="📚"),
            discord.SelectOption(label="Catálogo de Ports e Mods", value="catalogo", emoji="🕹️"),
            discord.SelectOption(label="Painel LuaTools", value="luatools", emoji="🧰"),
        ]
        seletor = discord.ui.Select(placeholder="1. Escolha o painel", options=opcoes)
        seletor.callback = self._selecionar_tipo
        self.add_item(seletor)
        canais = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="2. Escolha o canal de publicação",
            min_values=1, max_values=1,
        )
        canais.callback = self._selecionar_canal
        self.add_item(canais)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from cogs.platinas import eh_moderador
        autorizado = await eh_moderador(interaction.user, self.bot.db) or await _eh_admin_painel(self.bot, interaction.user)
        if interaction.user.id != self.user_id or not autorizado:
            await interaction.response.send_message("Acesso restrito à equipe autorizada.", ephemeral=True)
            return False
        return True

    async def _selecionar_tipo(self, interaction: discord.Interaction):
        self.tipo = interaction.data["values"][0]
        await interaction.response.send_message("Painel selecionado. Agora escolha o canal e clique em **Publicar e fixar**.", ephemeral=True)

    async def _selecionar_canal(self, interaction: discord.Interaction):
        # ChannelSelect pode entregar o snowflake como string dependendo da
        # versão/adapter do discord.py. Resolver sempre para um objeto de canal.
        valores = interaction.data.get("values", []) if interaction.data else []
        canal_id = valores[0] if valores else None
        try:
            canal_id = int(canal_id)
        except (TypeError, ValueError):
            canal_id = None

        canal = interaction.guild.get_channel(canal_id) if interaction.guild and canal_id else None
        if canal is None and canal_id:
            try:
                canal = await self.bot.fetch_channel(canal_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                canal = None

        if not isinstance(canal, discord.TextChannel):
            return await interaction.response.send_message(
                "Não consegui resolver o canal selecionado. Escolha um canal de texto deste servidor.",
                ephemeral=True,
            )

        self.canal = canal
        await interaction.response.send_message(
            f"Canal selecionado: {canal.mention}",
            ephemeral=True,
        )

    @discord.ui.button(label="Publicar e fixar", emoji="📌", style=discord.ButtonStyle.success, row=2)
    async def publicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.canal is None:
            return await interaction.response.send_message("Selecione primeiro um canal de texto.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        canal = self.canal
        try:
            if self.tipo == "luatools":
                from cogs.painel_membros import luatools_embed, LuaToolsLinksView
                key = f"panel:luatools:{canal.guild.id}:{canal.id}"
                marker = "nara:luatools"
                kwargs = {"embed": luatools_embed(), "view": LuaToolsLinksView()}
                message, _created = await upsert_panel(self.bot, canal, key, marker=marker, **kwargs)
            elif self.tipo == "catalogo":
                from cogs.catalogo_integrado import main_content, MainView, get_config, set_config
                cog = self.bot.get_cog("CatalogoIntegrado")
                if cog is None:
                    return await interaction.followup.send("O módulo de catálogo não está carregado.", ephemeral=True)
                key = f"catalogo_msg_{canal.id}"
                message = None
                old_id = get_config(key)
                if old_id:
                    try:
                        message = await canal.fetch_message(int(old_id))
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError):
                        message = None
                if message:
                    await message.edit(content=main_content(), embed=None, attachments=[], view=MainView())
                else:
                    message = await canal.send(content=main_content(), view=MainView())
                set_config(key, str(message.id))
            else:
                from utils import upsert_panel
                if self.tipo == "principal":
                    cog = self.bot.get_cog("Platinas")
                    from cogs.platinas import ColiseuView
                    view = ColiseuView(cog)
                    key, marker, content = f"panel:principal:{canal.guild.id}:{canal.id}", "nara:painel:principal*", view.texto()
                    kwargs = {"content": content, "embeds": [], "view": view}
                elif self.tipo == "platinas":
                    cog = self.bot.get_cog("Platinas")
                    from cogs.platinas import PainelPublicoView
                    view = PainelPublicoView(cog)
                    key, marker = f"panel:platinas:{canal.guild.id}:{canal.id}", "plat:painel"
                    kwargs = {"content": "🏆 **NARA — PLATINAS**\nRegistre suas conquistas e consulte suas platinas.\n\nClique no botão abaixo para abrir seu painel pessoal.", "view": view}
                elif self.tipo == "zerados":
                    cog = self.bot.get_cog("Zerados")
                    from cogs.zerados import ZeradosPublicoView
                    view = ZeradosPublicoView(cog)
                    key, marker = f"panel:zerados:{canal.guild.id}:{canal.id}", "zer:painel"
                    kwargs = {"content": "# ✅ Jogos Zerados\n\nRegistre seus jogos concluídos, consulte sua lista e acompanhe o ranking.", "embeds": [], "view": view}
                else:
                    from nara.ajuda import PainelAjudaPublicoView
                    embed = discord.Embed(
                        title="📚 Central de Ajuda da Nara",
                        description="Escolha uma opção para consultar orientações sobre os recursos da NARA.",
                        color=discord.Color.dark_teal(),
                    )
                    key, marker = f"panel:ajuda:{canal.guild.id}:{canal.id}", "nara:ajuda"
                    kwargs = {"embed": embed, "view": PainelAjudaPublicoView(self.bot)}
                message, _created = await upsert_panel(self.bot, canal, key, marker=marker, **kwargs)
                if self.tipo in ("platinas", "zerados"):
                    await self.bot.db.set_kv(f"rotating:channel:{self.tipo}:{canal.guild.id}", str(canal.id))
            try:
                if not message.pinned:
                    await message.pin(reason=f"Painel persistente publicado pelo /adm por {interaction.user}")
                status_pin = "e fixado"
            except discord.Forbidden:
                status_pin = "publicado, mas não foi possível fixar (permissão Gerenciar mensagens ausente)"
            except discord.HTTPException:
                status_pin = "publicado, mas o Discord recusou a fixação"
            await interaction.followup.send(f"✅ Painel **{self.tipo}** publicado/atualizado em {canal.mention} {status_pin}.", ephemeral=True)
        except Exception:
            log.exception("Falha ao publicar painel %s pelo /adm", self.tipo)
            await interaction.followup.send("Não foi possível publicar o painel. Confira as permissões do bot e os logs.", ephemeral=True)



# ---------------------------------------------------------------------------
# Botões de administração que substituem comandos antes digitados.
# Os comandos continuam nos cogs (só /nara e /adm são publicados no Discord);
# aqui o painel coleta os dados e chama o mesmo callback do comando.
# ---------------------------------------------------------------------------
class AcaoModalSimples(discord.ui.Modal):
    """Formulário genérico: coleta campos de texto e entrega os valores ao callback."""

    def __init__(self, titulo: str, campos: list, executar, callback_voltar=None):
        super().__init__(title=titulo[:45], timeout=300)
        self._executar = executar
        self.callback_voltar = callback_voltar
        self._campos = []
        for chave, rotulo, obrigatorio, longo, limite, padrao in campos:
            campo = discord.ui.TextInput(
                label=rotulo[:45], required=obrigatorio, max_length=limite, default=padrao,
                style=discord.TextStyle.paragraph if longo else discord.TextStyle.short,
            )
            self.add_item(campo)
            self._campos.append((chave, campo))

    async def on_submit(self, interaction: discord.Interaction):
        valores = {chave: (campo.value or "").strip() for chave, campo in self._campos}
        try:
            await self._executar(interaction, valores)
            if self.callback_voltar and interaction.response.is_done():
                from utils import view_so_com_voltar
                await interaction.followup.send(
                    "Ação processada. Você pode voltar à categoria administrativa.",
                    view=view_so_com_voltar(self.callback_voltar), ephemeral=True,
                )
        except Exception:
            log.exception("Falha ao executar ação administrativa via formulário")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Não foi possível concluir a ação. Confira os logs.", ephemeral=True
                )


async def _resolver_canal_texto(interaction: discord.Interaction, bot):
    """Resolve o canal escolhido em um ChannelSelect para um TextChannel do servidor."""
    valores = interaction.data.get("values", []) if interaction.data else []
    try:
        canal_id = int(valores[0]) if valores else None
    except (TypeError, ValueError):
        canal_id = None
    canal = interaction.guild.get_channel(canal_id) if interaction.guild and canal_id else None
    if canal is None and canal_id:
        try:
            canal = await bot.fetch_channel(canal_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            canal = None
    return canal if isinstance(canal, discord.TextChannel) else None


class _ViewDeModerador(discord.ui.View):
    """Base: só o moderador que abriu o painel (e a equipe autorizada) interage."""

    def __init__(self, bot, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from cogs.platinas import eh_moderador
        autorizado = await eh_moderador(interaction.user, self.bot.db) or await _eh_admin_painel(self.bot, interaction.user)
        if interaction.user.id != self.user_id or not autorizado:
            await interaction.response.send_message("Acesso restrito à equipe autorizada.", ephemeral=True)
            return False
        return True


class CentralRunsView(_ViewDeModerador):
    """Publica ou atualiza a central permanente de runs Soulslike no canal escolhido."""

    def __init__(self, bot, user_id: int):
        super().__init__(bot, user_id)
        self.canal = None
        seletor = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="Escolha o canal da central de runs",
            min_values=1, max_values=1,
        )
        seletor.callback = self._selecionar_canal
        self.add_item(seletor)
        self.add_item(AdminVoltarButton(bot))

    async def _selecionar_canal(self, interaction: discord.Interaction):
        canal = await _resolver_canal_texto(interaction, self.bot)
        if canal is None:
            return await interaction.response.send_message(
                "Não consegui resolver o canal. Escolha um canal de texto deste servidor.", ephemeral=True
            )
        self.canal = canal
        await interaction.response.send_message(f"Canal selecionado: {canal.mention}", ephemeral=True)

    @discord.ui.button(label="Publicar central", emoji="📌", style=discord.ButtonStyle.success, row=2)
    async def publicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.canal is None:
            return await interaction.response.send_message("Selecione primeiro um canal de texto.", ephemeral=True)
        cog = self.bot.get_cog("Soulslike")
        if cog is None:
            return await interaction.response.send_message("O módulo de runs Soulslike não está carregado.", ephemeral=True)
        await type(cog).publicar_central.callback(cog, interaction, self.canal)


class CentralRecompensasDesafioView(_ViewDeModerador):
    """Configura no painel /adm as recompensas especiais dos desafios Soulslike."""

    SINGULARES = [
        ("auto", "Automática pelo nome do desafio"),
        ("none", "Nenhuma Singular"),
        ("gwent_singular_primeiro", "O Primeiro Juramento"),
        ("gwent_singular_intocavel", "A Lâmina Intocada · No-hit"),
        ("gwent_singular_nivel1", "A Vontade Inquebrável · Nível 1"),
        ("gwent_singular_cacador_chefes", "A Coroa dos Vencidos · Todos os chefes"),
    ]

    def __init__(self, bot, user_id: int, desafios):
        super().__init__(bot, user_id)
        self.desafios = desafios[:25]
        self.challenge_id = int(self.desafios[0]["id"]) if self.desafios else 0
        self.primordial_value = int(self.desafios[0]["coliseu_primordial_drop"] if self.desafios and self.desafios[0]["coliseu_primordial_drop"] is not None else -1)
        singular_atual = str(self.desafios[0]["coliseu_singular_card_id"] or "") if self.desafios else ""
        self.singular_value = singular_atual or "auto"
        options = [discord.SelectOption(
            label=f"{int(row['id'])} · {str(row['name'])}"[:100],
            value=str(row["id"]), default=index == 0,
        ) for index, row in enumerate(self.desafios)]
        self.challenge_select = discord.ui.Select(
            placeholder="1. Escolha o desafio", min_values=1, max_values=1,
            options=options or [discord.SelectOption(label="Nenhum desafio cadastrado", value="0")],
            disabled=not options, row=0,
        )
        self.challenge_select.callback = self._choose_challenge
        self.add_item(self.challenge_select)
        self.primordial_select = discord.ui.Select(
            placeholder="2. Chance de drop Primordial",
            options=[
                discord.SelectOption(label="Automática pelo nome do desafio", value="-1", default=self.primordial_value == -1),
                discord.SelectOption(label="Desativada", value="0", default=self.primordial_value == 0),
                discord.SelectOption(label="Habilitar 0,1%", value="1", default=self.primordial_value == 1),
            ], min_values=1, max_values=1, row=1,
        )
        self.primordial_select.callback = self._choose_primordial
        self.add_item(self.primordial_select)
        self.singular_select = discord.ui.Select(
            placeholder="3. Singular concedida na aprovação",
            options=[discord.SelectOption(label=label, value=value, default=value == self.singular_value) for value, label in self.SINGULARES],
            min_values=1, max_values=1, row=2,
        )
        self.singular_select.callback = self._choose_singular
        self.add_item(self.singular_select)

    async def _choose_challenge(self, interaction: discord.Interaction):
        self.challenge_id = int(self.challenge_select.values[0])
        row = next((item for item in self.desafios if int(item["id"]) == self.challenge_id), None)
        if row:
            self.primordial_value = int(row["coliseu_primordial_drop"] if row["coliseu_primordial_drop"] is not None else -1)
            self.singular_value = str(row["coliseu_singular_card_id"] or "") or "auto"
            for option in self.primordial_select.options:
                option.default = option.value == str(self.primordial_value)
            for option in self.singular_select.options:
                option.default = option.value == self.singular_value
        await interaction.response.edit_message(view=self)

    async def _choose_primordial(self, interaction: discord.Interaction):
        self.primordial_value = int(self.primordial_select.values[0])
        await interaction.response.defer()

    async def _choose_singular(self, interaction: discord.Interaction):
        self.singular_value = self.singular_select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Salvar recompensas", emoji="💾", style=discord.ButtonStyle.success, row=3)
    async def salvar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.challenge_id:
            return await interaction.response.send_message("Nenhum desafio selecionado.", ephemeral=True)
        # Os valores iniciais dos selects são respeitados mesmo se o usuário não os alterar.
        primordial = self.primordial_value
        singular = self.singular_value
        if singular == "auto":
            singular = ""  # mantém detecção automática por nome até escolha explícita
        row = await self.bot.db._one("SELECT name FROM sl_challenges WHERE id=?", (self.challenge_id,))
        if not row:
            return await interaction.response.send_message("Esse desafio não existe mais. Atualize o painel.", ephemeral=True)
        await self.bot.db.conn.execute(
            "UPDATE sl_challenges SET coliseu_primordial_drop=?,coliseu_singular_card_id=? WHERE id=?",
            (primordial, singular, self.challenge_id),
        )
        await self.bot.db.conn.commit()
        await self.bot.db.log(
            interaction.user.id, "sl_recompensa_desafio_configurada",
            f"challenge={self.challenge_id};primordial={primordial};singular={singular or 'automatica'}",
        )
        primordial_label = "automática pelo nome" if primordial == -1 else "desativada" if primordial == 0 else "chance de 0,1%"
        singular_label = dict(self.SINGULARES).get(singular, "detecção automática pelo nome" if not singular else singular)
        await interaction.response.edit_message(
            content=f"## Recompensas atualizadas — {row['name']}\nPrimordial: **{primordial_label}**\nSingular: **{singular_label}**",
            embed=None, view=self,
        )


class CargoOpcoesView(_ViewDeModerador):
    """Adiciona, edita ou remove uma opção (botão) do painel de cargos."""

    ROTULOS = {"adicionar": "Adicionar", "editar": "Editar", "remover": "Remover"}

    def __init__(self, bot, user_id: int, callback_voltar=None):
        super().__init__(bot, user_id)
        self.callback_voltar = callback_voltar
        self.acao = "adicionar"
        seletor = discord.ui.Select(
            placeholder="1. O que deseja fazer?",
            options=[
                discord.SelectOption(label="Adicionar opção", value="adicionar", emoji="➕"),
                discord.SelectOption(label="Editar opção", value="editar", emoji="✏️"),
                discord.SelectOption(label="Remover opção", value="remover", emoji="🗑️"),
            ],
        )
        seletor.callback = self._selecionar_acao
        self.add_item(seletor)
        self.cargo_select = discord.ui.RoleSelect(placeholder="2. Escolha o cargo", min_values=1, max_values=1)
        self.cargo_select.callback = self._selecionar_cargo
        self.add_item(self.cargo_select)
        if callback_voltar:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à categoria")
        else:
            self.add_item(AdminVoltarButton(bot))

    async def _selecionar_acao(self, interaction: discord.Interaction):
        self.acao = interaction.data["values"][0]
        await interaction.response.defer()

    async def _selecionar_cargo(self, interaction: discord.Interaction):
        await interaction.response.defer()

    @discord.ui.button(label="Continuar", emoji="▶️", style=discord.ButtonStyle.success, row=2)
    async def continuar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cargo_select.values:
            return await interaction.response.send_message("Escolha um cargo primeiro.", ephemeral=True)
        cargo = self.cargo_select.values[0]
        cog = self.bot.get_cog("Cargos")
        if cog is None:
            return await interaction.response.send_message("O módulo de cargos não está carregado.", ephemeral=True)
        escolha = app_commands.Choice(name=self.ROTULOS[self.acao], value=self.acao)
        if self.acao == "remover":
            return await type(cog).cargo_painel.callback(cog, interaction, escolha, cargo)

        async def executar(inter: discord.Interaction, v: dict):
            await type(cog).cargo_painel.callback(cog, inter, escolha, cargo, v["nome"] or None, v["emoji"] or None)

        await interaction.response.send_modal(AcaoModalSimples(
            f"{self.ROTULOS[self.acao]} opção de cargo",
            [
                ("nome", "Texto do botão (sem emoji)", False, False, 80, None),
                ("emoji", "Emoji do botão", False, False, 40, None),
            ],
            executar,
            callback_voltar=self.callback_voltar,
        ))


ADMIN_CATEGORIAS = {
    "servidor": {
        "titulo": "⚙️ Servidor e acesso",
        "descricao": "Configure os canais e cargos do servidor, use o assistente inicial e gerencie os painéis de acesso.",
        "acoes": [
            ("channels", "Canais do servidor", "📺"),
            ("roles", "Cargos e permissões", "🎭"),
            ("auto_setup", "Assistente de configuração", "✨"),
            ("personalizacao", "Identidade visual", "🎨"),
            ("post_verificacao", "Publicar verificação", "🛡️"),
            ("post_cargos", "Publicar painel de cargos", "🎭"),
            ("cargos_texto", "Editar texto dos cargos", "✏️"),
            ("cargos_opcoes", "Opções dos cargos", "⚙️"),
            ("reset", "Restaurar padrões", "⚠️"),
        ],
    },
    "moderacao": {
        "titulo": "🛡️ Moderação e auditoria",
        "descricao": "Acompanhe solicitações, atualizações operacionais e o histórico de decisões. As ferramentas respeitam o nível de acesso da equipe.",
        "acoes": [
            ("moderacao", "Fila de aprovação", "📥"),
            ("dashboard", "Resumo operacional", "📈"),
            ("history", "Histórico de auditoria", "📜"),
        ],
    },
    "jogos": {
        "titulo": "🎮 Jogos, Coliseu e runs",
        "descricao": "Configure canais e recompensas de conquistas, santuários, catálogos de jogos e desafios Soulslike.",
        "acoes": [
            ("coliseu", "Configurações de conquistas", "⚔️"),
            ("galeria", "Canal de Santuários", "🏛️"),
            ("perfis", "Patentes e níveis de XP", "👤"),
            ("jogos", "Canais de jogos e promoções", "🎮"),
            ("colizeu_atualizar", "Atualizar rankings", "🔄"),
            ("sl_central", "Publicar central de runs", "📌"),
            ("sl_jogo", "Adicionar jogo Soulslike", "🎮"),
            ("sl_desafio", "Criar desafio Soulslike", "🏅"),
            ("sl_rewards", "Configurar drops especiais dos desafios", "🃏"),
            ("sl_invalidar", "Invalidar run", "🚫"),
        ],
    },
    "comunidade": {
        "titulo": "📚 Comunidade e contribuições",
        "descricao": "Configure os espaços de Lore, Guias e Arquivo de Mundos e publique os painéis comunitários.",
        "acoes": [
            ("community_config", "Canais e recompensas de contribuições", "⚙️"),
            ("community_publish", "Publicar Arquivo de Mundos", "📚"),
            ("community_guides_publish", "Publicar Guias e Tutoriais", "📘"),
        ],
    },
    "economia": {
        "titulo": "🪙 Economia e progressão",
        "descricao": "Consulte e ajuste XP, Denários, limites e recompensas. Os valores não personalizados continuam usando os padrões do bot.",
        "acoes": [
            ("economy", "Configurar economia", "🪙"),
            ("economy_adjust_member", "Ajustar XP / Denários de membro", "⚖️"),
        ],
    },
    "publicacoes": {
        "titulo": "📌 Publicações e integrações",
        "descricao": "Publique painéis no canal atual ou use o gerenciador para escolher outro canal. Configure também Radar, YouTube e ofertas.",
        "acoes": [
            ("publicar_paineis", "Gerenciador de painéis (escolher canal)", "📌"),
            ("post_coliseu", "Publicar painel principal neste canal", "⚔️"),
            ("post_ajuda", "Publicar Central de Ajuda neste canal", "📖"),
            ("post_loja", "Publicar painel da loja neste canal", "🪙"),
            ("post_santuario", "Publicar painel de Santuários neste canal", "🏛️"),
            ("radar_games", "Configurar Radar de Games", "📡"),
            ("youtube_status", "Status do YouTube", "📺"),
            ("youtube_test_video", "Testar aviso de vídeo", "🎬"),
            ("youtube_test_live", "Testar aviso de live", "🔴"),
            ("ofertas_status", "Status de ofertas", "🏷️"),
            ("ofertas_preview", "Prévia de oferta", "🛍️"),
            ("transmissao_video", "Vídeo tutorial de transmissões", "🎥"),
        ],
    },
    "catalogos": {
        "titulo": "🧩 Catálogos de Ports & Mods",
        "descricao": "Gerencie os ports, mods e envios da comunidade em seus catálogos próprios.",
        "acoes": [
            ("catalogo_jogos", "Gerenciar Ports", "🎮"),
            ("catalogo_mods", "Gerenciar Mods", "🧩"),
        ],
    },
    "diagnostico": {
        "titulo": "🤖 Diagnóstico e NARA IA",
        "descricao": "Verifique as configurações do servidor e o estado dos provedores e recursos de IA.",
        "acoes": [
            ("status", "Ver configuração completa", "📊"),
            ("ia_relatorio", "Relatório de uso da NARA", "📈"),
            ("ia_provedores", "Status dos provedores de IA", "🧠"),
        ],
    },
}


# ── Controle de acesso ──────────────────────────────────────────
# Moderadores (cargo de equipe) só enxergam/usam o que estiver fora destes conjuntos.
# Para liberar algo ao moderador, remova a categoria/ação daqui; para restringir, adicione.
CATEGORIAS_SO_ADMIN = {
    "servidor", "jogos", "comunidade", "economia", "publicacoes", "catalogos", "diagnostico",
}
ACOES_SO_ADMIN = {
    acao
    for cat in CATEGORIAS_SO_ADMIN
    for acao, *_ in ADMIN_CATEGORIAS[cat]["acoes"]
} | {"community_config", "community_publish", "community_guides_publish"}

MSG_SO_ADMIN = "🔒 Esta função é exclusiva do **administrador** do servidor."


def eh_administrador(user) -> bool:
    """Administrador de verdade: permissão Administrador ou dono do servidor."""
    guild = getattr(user, "guild", None)
    if guild is not None and guild.owner_id == user.id:
        return True
    perms = getattr(user, "guild_permissions", None)
    return bool(perms and perms.administrator)


def _retorno_categoria_admin(bot, categoria: str, user_id: int):
    async def voltar(interaction: discord.Interaction):
        if int(interaction.user.id) != int(user_id):
            return await interaction.response.send_message("Este painel pertence a outra sessão administrativa.", ephemeral=True)
        is_admin = await _eh_admin_painel(bot, interaction.user)
        if categoria in CATEGORIAS_SO_ADMIN and not is_admin:
            return await interaction.response.send_message(MSG_SO_ADMIN, ephemeral=True)
        dados = ADMIN_CATEGORIAS[categoria]
        embed = discord.Embed(
            title=dados["titulo"],
            description=dados["descricao"] + "\n\nEscolha uma ferramenta. A navegação de retorno preserva esta categoria.",
            color=COR_PAINEL,
        )
        acoes_visiveis = [a for a in dados["acoes"] if is_admin or a[0] not in ACOES_SO_ADMIN]
        embed.add_field(name="Ferramentas disponíveis", value=f"{len(acoes_visiveis)} opção(ões) nesta área", inline=True)
        embed.set_footer(text="NARA • Use ‘Voltar ao início’ para trocar de categoria")
        view = AdminCategoriaView(bot, categoria, user_id, is_admin)
        view._admin_message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)
    return voltar


async def _executar_acao_admin(interaction: discord.Interaction, bot, action: str, *, categoria: str | None = None, user_id: int | None = None):
    """Encaminha ações da navegação administrativa aos handlers já existentes."""
    if action in ACOES_SO_ADMIN and not await _eh_admin_painel(bot, interaction.user):
        return await interaction.response.send_message(MSG_SO_ADMIN, ephemeral=True)
    voltar = _retorno_categoria_admin(bot, categoria, user_id or interaction.user.id) if categoria in ADMIN_CATEGORIAS else None
    def com_voltar(view):
        return adicionar_botao_voltar(view, voltar)
    if action == "channels":
        return await _abrir_secao(interaction, bot, "channels", "📺 Canais configurados", callback_voltar=voltar)
    if action == "roles":
        return await _abrir_secao(interaction, bot, "roles", "🎭 Cargos configurados", callback_voltar=voltar)
    if action == "coliseu":
        return await _abrir_coliseu(interaction, bot, callback_voltar=voltar)
    if action == "moderacao":
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, bot.db) and not await _eh_admin_painel(bot, interaction.user):
            return await interaction.response.send_message("Seu cargo não tem permissão para moderar solicitações.", ephemeral=True)
        view = ModeracaoPainelView(bot, interaction.user.id)
        view.guild_id = int(interaction.guild_id) if interaction.guild_id else None
        embed = await view.embed_painel()
        # ModeracaoPainelView.__init__ já adiciona o filtro de categorias na linha 0.
        # Não adicionar uma segunda instância: dois Select ocupam 10 posições na mesma linha.
        view.add_item(ModeracaoSolicitacaoSelect(view, view.registros[:25]))
        if len(view.registros) > 25:
            view.add_item(ModeracaoPaginaButton(view, 1))
        view.add_item(ModeracaoAtualizarButton(view))
        com_voltar(view)
        return await interaction.response.edit_message(embed=embed, view=view)
    if action == "galeria":
        return await _abrir_galeria(interaction, bot, callback_voltar=voltar)
    if action == "perfis":
        return await _abrir_perfis(interaction, bot, callback_voltar=voltar)
    if action == "jogos":
        return await _abrir_jogos(interaction, bot, callback_voltar=voltar)
    if action == "economy":
        return await _abrir_economia(interaction, bot, callback_voltar=voltar)
    if action == "economy_adjust_member":
        if not await _eh_admin_painel(bot, interaction.user):
            return await interaction.response.send_message(MSG_SO_ADMIN, ephemeral=True)
        view = AdminEconomiaAjusteView(bot, interaction.user.id, callback_voltar=voltar)
        embed = discord.Embed(
            title="⚖️ Ajustar XP e Denários",
            description=(
                "Escolha um membro, selecione se deseja adicionar ou remover e informe "
                "as quantidades. A operação é registrada no histórico de auditoria.\n\n"
                "**Proteções:** saldos não ficam negativos; se a remoção superar o saldo, "
                "o recurso é reduzido somente até zero."
            ),
            color=COR_PAINEL,
        )
        return await interaction.response.edit_message(embed=embed, view=view)
    if action == "community_config":
        return await _abrir_secao(
            interaction, bot, "community", "📚 Configurações de contribuições e Arquivo de Mundos",
            callback_voltar=voltar,
        )
    if action == "community_publish":
        cog = bot.get_cog("Comunidade")
        if cog is None:
            return await interaction.response.send_message("O módulo de contribuições não está carregado.", ephemeral=True)
        return await cog.publicar_painel(interaction)
    if action == "community_guides_publish":
        cog = bot.get_cog("Comunidade")
        if cog is None:
            return await interaction.response.send_message("O módulo de contribuições não está carregado.", ephemeral=True)
        return await cog.publicar_painel_guias(interaction)
    if action == "personalizacao":
        return await _abrir_personalizacao(interaction, bot, callback_voltar=voltar)
    if action == "dashboard":
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, bot.db) and not await _eh_admin_painel(bot, interaction.user):
            return await interaction.response.send_message("Acesso restrito à moderação.", ephemeral=True)
        view = DashboardOperacionalView(bot, interaction.user.id, callback_voltar=voltar)
        view._admin_message = interaction.message
        return await interaction.response.edit_message(embed=await _embed_dashboard(bot, interaction.guild_id), view=view)
    if action == "history":
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, bot.db) and not await _eh_admin_painel(bot, interaction.user):
            return await interaction.response.send_message("Acesso restrito à moderação.", ephemeral=True)
        view = HistoricoAuditoriaView(bot, interaction.user.id, callback_voltar=voltar)
        view._admin_message = interaction.message
        return await interaction.response.edit_message(embed=await view.embed(), view=view)
    if action == "status":
        return await _abrir_status(interaction, bot, callback_voltar=voltar)
    if action == "publicar_paineis":
        from cogs.platinas import eh_moderador
        autorizado = await eh_moderador(interaction.user, bot.db) or await _eh_admin_painel(bot, interaction.user)
        if not autorizado:
            return await interaction.response.send_message("Acesso restrito à equipe autorizada.", ephemeral=True)
        view = PublicarPaineisView(bot, interaction.user.id)
        com_voltar(view)
        return await interaction.response.edit_message(
            content="## 📌 Publicar e fixar painéis\nEscolha o painel, selecione o canal e confirme. Se já existir, a mensagem será atualizada.",
            embed=None, attachments=[], view=view,
        )
    if action in ("catalogo_jogos", "catalogo_mods"):
        cog = bot.get_cog("CatalogoIntegrado")
        if cog is None:
            return await interaction.response.send_message("O módulo de catálogos não está carregado.", ephemeral=True)
        from cogs.catalogo_integrado import eh_admin, AdminView, ModAdminView
        if not eh_admin(interaction):
            return await interaction.response.send_message("Acesso restrito à equipe de gerenciamento.", ephemeral=True)
        if action == "catalogo_mods":
            return await interaction.response.edit_message(
                content="## 🧩 Administração do catálogo de mods\\nEscolha uma ação abaixo.",
                embed=None, attachments=[], view=com_voltar(ModAdminView()),
            )
        return await interaction.response.edit_message(
            content="## 🎮 Administração do catálogo de ports\\nEscolha uma ação no menu abaixo.",
            embed=None, attachments=[], view=com_voltar(AdminView()),
        )
    if action == "radar_games":
        cog = bot.get_cog("GameNewsCog")
        if cog is None:
            return await interaction.response.send_message("O Radar de Games não está carregado.", ephemeral=True)
        from cogs.game_news import NewsAdminView
        feeds = cog._feeds()
        channel_id = cog._get_config("channel_id")
        texto = (
            "## 📡 Radar de Games — NARA\\n"
            f"**Canal:** {f'<#{channel_id}>' if channel_id else 'não configurado'}\\n"
            f"**Feeds ativos:** {len(feeds)}\\n"
            f"**Verificação automática:** a cada 5 minutos\\n\\n"
            "Use o seletor para definir o canal, adicione fontes RSS, consulte os feeds ou envie uma mensagem de teste."
        )
        return await interaction.response.edit_message(content=texto, embed=None, attachments=[], view=com_voltar(NewsAdminView(cog)))
    # Ações administrativas existentes nos Cogs originais: o painel central
    # chama os mesmos callbacks para evitar duplicar regras de negócio.
    # Como a chamada interna não passa pelos checks do app command, repetimos
    # aqui a exigência de Gerenciar Servidor antes de executar essas operações.
    acoes_restritas = {
        "youtube_status", "youtube_test_video", "youtube_test_live",
        "ofertas_status", "ofertas_preview", "ia_relatorio", "ia_provedores",
        "post_ajuda", "post_verificacao", "post_cargos", "post_coliseu",
        "post_loja", "post_santuario",
        "sl_central", "sl_jogo", "sl_desafio", "sl_rewards", "sl_invalidar",
        "cargos_texto", "cargos_opcoes", "transmissao_video", "colizeu_atualizar",
    }
    if action in acoes_restritas and not await _eh_admin_painel(bot, interaction.user):
        return await interaction.response.send_message(
            "Esta ação exige a permissão **Gerenciar Servidor** (ou Administrador).",
            ephemeral=True,
        )
    if action in ("youtube_status", "youtube_test_video", "youtube_test_live"):
        cog = bot.get_cog("YouTube")
        if cog is None:
            return await interaction.response.send_message("O módulo do YouTube não está carregado.", ephemeral=True)
        metodo = {"youtube_status": "status_youtube", "youtube_test_video": "teste_video", "youtube_test_live": "teste_live"}[action]
        return await getattr(type(cog), metodo).callback(cog, interaction)
    if action in ("ofertas_status", "ofertas_preview"):
        cog = bot.get_cog("Ofertas")
        if cog is None:
            return await interaction.response.send_message("O monitor de ofertas não está carregado.", ephemeral=True)
        metodo = "status_ofertas" if action == "ofertas_status" else "previa_oferta"
        return await getattr(type(cog), metodo).callback(cog, interaction)
    if action in ("ia_relatorio", "ia_provedores", "post_ajuda"):
        cog = bot.get_cog("NaraIA")
        if cog is None:
            return await interaction.response.send_message("O módulo de IA não está carregado.", ephemeral=True)
        metodo = {"ia_relatorio": "nara_relatorio", "ia_provedores": "gemini_status_command", "post_ajuda": "painel_ajuda_nara_command"}[action]
        return await getattr(type(cog), metodo).callback(cog, interaction)
    if action in ("post_verificacao", "post_cargos"):
        cog = bot.get_cog("Cargos")
        if cog is None:
            return await interaction.response.send_message("O módulo de cargos não está carregado.", ephemeral=True)
        metodo = "painel_verificacao" if action == "post_verificacao" else "painel_cargos"
        return await getattr(type(cog), metodo).callback(cog, interaction)
    if action == "post_coliseu":
        cog = bot.get_cog("Colizeu")
        if cog is None:
            return await interaction.response.send_message("O módulo do Coliseu não está carregado.", ephemeral=True)
        return await type(cog).painel_colizeu.callback(cog, interaction)
    if action == "post_loja":
        cog = bot.get_cog("Loja")
        if cog is None:
            return await interaction.response.send_message("O módulo da loja não está carregado.", ephemeral=True)
        return await type(cog).painel_loja.callback(cog, interaction)
    if action == "post_santuario":
        cog = bot.get_cog("Santuario")
        if cog is None:
            return await interaction.response.send_message("O módulo de santuários não está carregado.", ephemeral=True)
        return await type(cog).painel_santuarios.callback(cog, interaction)
    if action in ("sl_central", "sl_jogo", "sl_desafio", "sl_rewards", "sl_invalidar"):
        cog = bot.get_cog("Soulslike")
        if cog is None:
            return await interaction.response.send_message("O módulo de runs Soulslike não está carregado.", ephemeral=True)
        if action == "sl_rewards":
            desafios = await bot.db._all(
                "SELECT id,name,coliseu_primordial_drop,coliseu_singular_card_id FROM sl_challenges ORDER BY name LIMIT 25"
            )
            return await interaction.response.edit_message(
                content="## 🃏 Recompensas especiais do Coliseu\nEscolha um desafio, defina a chance de Primordial e a Singular entregue quando uma run for aprovada.",
                embed=None, attachments=[], view=com_voltar(
                    CentralRecompensasDesafioView(bot, interaction.user.id, desafios)
                ),
            )
        if action == "sl_central":
            return await interaction.response.edit_message(
                content="## ⚔️ Central de runs Soulslike\nEscolha o canal e clique em **Publicar central**. Se já existir, a mensagem será atualizada.",
                embed=None, attachments=[], view=com_voltar(CentralRunsView(bot, interaction.user.id)),
            )
        if action == "sl_jogo":
            async def executar(inter, v):
                if not v["nome"]:
                    return await inter.response.send_message("Informe o nome do jogo.", ephemeral=True)
                await type(cog).jogo_adicionar.callback(cog, inter, v["nome"])
            campos = [("nome", "Nome do jogo", True, False, 80, None)]
            titulo = "Adicionar jogo às runs"
        elif action == "sl_desafio":
            async def executar(inter, v):
                if not v["nome"]:
                    return await inter.response.send_message("Informe o nome do desafio.", ephemeral=True)
                await type(cog).desafio_adicionar.callback(cog, inter, v["nome"], v["regras"])
            campos = [
                ("nome", "Nome do desafio", True, False, 80, None),
                ("regras", "Regras mostradas aos jogadores", False, True, 300, None),
            ]
            titulo = "Criar desafio"
        else:
            async def executar(inter, v):
                if not v["numero"].isdigit():
                    return await inter.response.send_message("Informe o número da run (somente dígitos).", ephemeral=True)
                await type(cog).invalidar.callback(cog, inter, int(v["numero"]), v["motivo"])
            campos = [
                ("numero", "Número da run", True, False, 12, None),
                ("motivo", "Motivo (fica no log)", False, True, 300, None),
            ]
            titulo = "Invalidar run aprovada"
        return await interaction.response.send_modal(AcaoModalSimples(titulo, campos, executar, callback_voltar=voltar))
    if action in ("cargos_texto", "cargos_opcoes"):
        cog = bot.get_cog("Cargos")
        if cog is None:
            return await interaction.response.send_message("O módulo de cargos não está carregado.", ephemeral=True)
        if action == "cargos_opcoes":
            return await interaction.response.edit_message(
                content="## 🎭 Opções do painel de cargos\nEscolha a ação e o cargo e clique em **Continuar**. Depois, publique ou atualize o painel pelo botão **Publicar painel de cargos**.",
                embed=None, attachments=[], view=com_voltar(CargoOpcoesView(bot, interaction.user.id, callback_voltar=voltar)),
            )
        atual = await cog._get_config(interaction.guild)

        async def executar(inter, v):
            if not v["titulo"] or not v["mensagem"]:
                return await inter.response.send_message("Preencha o título e a mensagem.", ephemeral=True)
            await type(cog).editar_painel_cargos.callback(cog, inter, v["titulo"], v["mensagem"])

        return await interaction.response.send_modal(AcaoModalSimples(
            "Texto do painel de cargos",
            [
                ("titulo", "Título do painel", True, False, 250, str(atual.get("title", ""))[:250]),
                ("mensagem", "Mensagem abaixo do título", True, True, 3500, str(atual.get("description", ""))[:3500]),
            ],
            executar,
            callback_voltar=voltar,
        ))
    if action == "transmissao_video":
        cog = bot.get_cog("Transmissoes")
        if cog is None:
            return await interaction.response.send_message("O módulo de transmissões não está carregado.", ephemeral=True)

        async def executar(inter, v):
            if not v["link"]:
                return await inter.response.send_message("Informe o link do vídeo.", ephemeral=True)
            await type(cog).configurar_video_transmissao.callback(cog, inter, v["link"])

        return await interaction.response.send_modal(AcaoModalSimples(
            "Vídeo tutorial de transmissões",
            [("link", "Link do vídeo no YouTube", True, False, 300, await cog.obter_video(interaction.guild_id))],
            executar,
            callback_voltar=voltar,
        ))
    if action == "colizeu_atualizar":
        cog = bot.get_cog("Colizeu")
        if cog is None:
            return await interaction.response.send_message("O módulo do Coliseu não está carregado.", ephemeral=True)
        return await type(cog).colizeu.callback(cog, interaction)
    if action == "auto_setup":
        return await _executar_configuracao_automatica(interaction, bot)
    if action == "reset":
        return await _confirmar_reset(interaction, bot, callback_voltar=voltar)
    return await interaction.response.send_message("Esta função ainda não está disponível no painel.", ephemeral=True)


class AdminAcaoButton(discord.ui.Button):
    def __init__(self, action: str, label: str, emoji: str, row: int, categoria: str, user_id: int):
        if action in {"reset", "sl_invalidar"}:
            estilo = discord.ButtonStyle.danger
        elif action in {"moderacao", "publicar_paineis", "community_publish", "community_guides_publish", "sl_central"}:
            estilo = discord.ButtonStyle.success
        else:
            estilo = discord.ButtonStyle.secondary
        super().__init__(
            label=label, emoji=emoji, style=estilo, row=row,
            custom_id=f"adm:cat:{int(user_id)}:{categoria}:{action}",
        )
        self.action = action
        self.categoria = categoria
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        await _executar_acao_admin(interaction, self.view.bot, self.action, categoria=self.categoria, user_id=self.user_id)


class AdminVoltarButton(discord.ui.Button):
    def __init__(self, bot, categoria: str | None = None, user_id: int | None = None):
        kwargs = {"row": 4}
        if categoria is not None and user_id is not None:
            kwargs["custom_id"] = f"adm:catback:{int(user_id)}:{categoria}"
        super().__init__(
            label="Voltar ao início", emoji="🏠", style=discord.ButtonStyle.secondary, **kwargs,
        )
        self.bot = bot
        self.categoria = categoria
        self.user_id = int(user_id) if user_id is not None else None

    async def callback(self, interaction: discord.Interaction):
        if self.user_id is not None and int(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(
                "Este painel pertence a outra sessão administrativa.", ephemeral=True
            )
        if self.categoria in CATEGORIAS_SO_ADMIN and not await _eh_admin_painel(self.bot, interaction.user):
            return await interaction.response.send_message(MSG_SO_ADMIN, ephemeral=True)
        await _mostrar_painel_principal(interaction, self.bot)


class AdminCategoriaView(discord.ui.View):
    def __init__(self, bot, categoria: str, user_id: int, is_admin: bool = True):
        # Esta é uma view privada de sessão, não uma view global persistente.
        # Prazo maior evita que uma sessão aberta fique inativa durante uma configuração longa.
        super().__init__(timeout=1800)
        self.bot = bot
        self.categoria = categoria
        self.user_id = user_id
        self._admin_message = None
        # Registra os botões no momento em que a categoria é criada.
        # Assim as ferramentas aparecem imediatamente ao abrir a categoria,
        # e não somente quando a View expira.
        dados = ADMIN_CATEGORIAS.get(categoria)
        if dados is None:
            raise ValueError(f"Categoria administrativa desconhecida: {categoria}")
        acoes = [acao for acao in dados["acoes"] if is_admin or acao[0] not in ACOES_SO_ADMIN]
        for index, (action, label, emoji) in enumerate(acoes):
            self.add_item(
                AdminAcaoButton(
                    action, label, emoji, row=index // 3,
                    categoria=categoria, user_id=user_id,
                )
            )
        self.add_item(AdminVoltarButton(bot, categoria, user_id))

    async def on_timeout(self) -> None:
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
        mensagem = self._admin_message
        if mensagem is None:
            return
        try:
            embeds = getattr(mensagem, "embeds", []) or []
            if embeds:
                embed = embeds[0].copy()
                footer = embed.footer.text or "NARA • Administração"
                embed.set_footer(text=f"{footer} · Sessão encerrada; use /adm para reabrir"[:2048])
                await mensagem.edit(embed=embed, view=self)
            else:
                await mensagem.edit(content="Esta sessão administrativa terminou. Use `/adm` para abrir uma nova.", view=self)
        except (discord.HTTPException, AttributeError):
            log.debug("Não foi possível atualizar a categoria administrativa expirada.", exc_info=True)
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from cogs.platinas import eh_moderador
        mesma_pessoa = interaction.user.id == self.user_id
        autorizado_admin = await _eh_admin_painel(self.bot, interaction.user)
        autorizado_moderacao = await eh_moderador(interaction.user, self.bot.db)
        acesso_categoria = autorizado_admin if self.categoria in CATEGORIAS_SO_ADMIN else (autorizado_admin or autorizado_moderacao)
        if not mesma_pessoa or not acesso_categoria:
            await interaction.response.send_message(
                "Este painel é restrito à pessoa que o abriu e à equipe autorizada. Use `/adm` para abrir sua própria central.",
                ephemeral=True,
            )
            return False
        return True


class AdminCategoriaButton(discord.ui.Button):
    def __init__(self, bot, categoria: str, label: str, emoji: str, row: int, user_id: int | None = None):
        super().__init__(
            label=label, emoji=emoji, style=discord.ButtonStyle.primary, row=row,
            custom_id=f"adm:categoria:{int(user_id) if user_id is not None else 'global'}:{categoria}",
        )
        self.bot = bot
        self.categoria = categoria
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if self.user_id is not None and int(interaction.user.id) != int(self.user_id):
            return await interaction.response.send_message(
                "Este painel pertence a outra sessão administrativa.", ephemeral=True
            )
        admin = await _eh_admin_painel(self.bot, interaction.user)
        if self.categoria in CATEGORIAS_SO_ADMIN and not admin:
            return await interaction.response.send_message(MSG_SO_ADMIN, ephemeral=True)
        dados = ADMIN_CATEGORIAS[self.categoria]
        embed = discord.Embed(
            title=dados["titulo"],
            description=dados["descricao"] + "\n\nEscolha uma ferramenta. A navegação de retorno preserva esta categoria.",
            color=COR_PAINEL,
        )
        acoes_visiveis = [a for a in dados["acoes"] if admin or a[0] not in ACOES_SO_ADMIN]
        embed.add_field(name="Ferramentas disponíveis", value=f"{len(acoes_visiveis)} opção(ões) nesta área", inline=True)
        embed.set_footer(text="NARA • Use ‘Voltar ao início’ para trocar de categoria")
        view = AdminCategoriaView(self.bot, self.categoria, self.user_id or interaction.user.id, admin)
        view._admin_message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)


async def _eh_dono_global_bot(bot, user) -> bool:
    """Valida o proprietário global do bot; cargos do servidor não concedem acesso."""
    owner_id = int(getattr(config, "BOT_OWNER_ID", 0) or 0)
    if owner_id and int(user.id) == owner_id:
        return True
    try:
        return bool(await bot.is_owner(user))
    except Exception:
        log.exception("Não foi possível validar o proprietário global do bot no painel ADM.")
        return False


async def _eh_admin_painel(bot, user) -> bool:
    """Permissão administrativa coerente com a entrada do /adm.

    Administrador do servidor, dono do servidor, quem possui Gerenciar Servidor
    ou proprietário global do bot pode usar as categorias administrativas.
    Cargos de moderador sem essa permissão continuam limitados à moderação.
    """
    if eh_administrador(user):
        return True
    perms = getattr(user, "guild_permissions", None)
    if perms and getattr(perms, "manage_guild", False):
        return True
    return await _eh_dono_global_bot(bot, user)


class RelacionamentoAdminUserSelectView(discord.ui.View):
    """Seletor efêmero para o proprietário escolher a pessoa monitorada pela NARA."""

    def __init__(self, bot, owner_id: int):
        super().__init__(timeout=180)
        self.bot = bot
        self.owner_id = int(owner_id)
        seletor = discord.ui.UserSelect(
            placeholder="Escolha o usuário do relacionamento", min_values=1, max_values=1, row=0
        )
        seletor.callback = self.selecionar_usuario
        self.add_item(seletor)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if int(interaction.user.id) != self.owner_id or not await _eh_dono_global_bot(self.bot, interaction.user):
            await interaction.response.send_message(
                "Somente o proprietário global do bot pode configurar o relacionamento da NARA.", ephemeral=True
            )
            return False
        return True

    async def selecionar_usuario(self, interaction: discord.Interaction):
        # discord.py expõe os objetos selecionados pelo componente em .values.
        seletor = next((item for item in self.children if isinstance(item, discord.ui.UserSelect)), None)
        usuario = seletor.values[0] if seletor and seletor.values else None
        if usuario is None:
            return await interaction.response.send_message("Não consegui identificar o usuário selecionado.", ephemeral=True)
        if getattr(usuario, "bot", False):
            return await interaction.response.send_message("Escolha uma pessoa, não outro bot.", ephemeral=True)
        cog = self.bot.get_cog("NaraIA")
        if cog is None:
            return await interaction.response.send_message(
                "O módulo de IA da NARA não está carregado. Verifique os logs do bot.", ephemeral=True
            )
        await cog.abrir_painel_relacionamento(interaction, usuario, editar=True)

    @discord.ui.button(label="Voltar ao ADM", emoji="↩️", style=discord.ButtonStyle.secondary, row=1)
    async def voltar_adm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _mostrar_painel_principal(interaction, self.bot)


class RelacionamentoAdminButton(discord.ui.Button):
    """Entrada do relacionamento no /adm; só é renderizada para o dono global."""

    def __init__(self, bot, user_id: int):
        super().__init__(
            label="Relacionamento da NARA", emoji="💠", style=discord.ButtonStyle.primary,
            custom_id="adm:nara:relacionamento", row=4,
        )
        self.bot = bot
        self.user_id = int(user_id)

    async def callback(self, interaction: discord.Interaction):
        if int(interaction.user.id) != self.user_id or not await _eh_dono_global_bot(self.bot, interaction.user):
            return await interaction.response.send_message(
                "Somente o proprietário global do bot pode acessar esta configuração.", ephemeral=True
            )
        view = RelacionamentoAdminUserSelectView(self.bot, self.user_id)
        embed = discord.Embed(
            title="💠 Relacionamento da NARA",
            description=(
                "Escolha abaixo o usuário cujo relacionamento será administrado. "
                "Somente você pode ver ou alterar afinidade, paciência e eventos."
            ),
            color=COR_PAINEL,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class AdminAtalhosSelect(discord.ui.Select):
    """Acesso rápido às tarefas administrativas mais frequentes."""

    def __init__(self, bot, user_id: int | None, is_admin: bool):
        self.bot = bot
        self.user_id = int(user_id) if user_id is not None else None
        self.rotas = {
            "moderacao": ("moderacao", "moderacao"),
            "dashboard": ("dashboard", "moderacao"),
            "history": ("history", "moderacao"),
        }
        opcoes = [
            discord.SelectOption(
                label="Abrir fila de aprovação", value="moderacao",
                description="Platinas, zerados, runs e contribuições", emoji="📥",
            ),
            discord.SelectOption(
                label="Resumo operacional", value="dashboard",
                description="Pendências, decisões recentes e alertas", emoji="📈",
            ),
            discord.SelectOption(
                label="Histórico de auditoria", value="history",
                description="Pesquisar ações e decisões registradas", emoji="📜",
            ),
        ]
        if is_admin:
            self.rotas.update({
                "channels": ("channels", "servidor"),
                "publish": ("publicar_paineis", "publicacoes"),
                "status": ("status", "diagnostico"),
            })
            opcoes.extend([
                discord.SelectOption(
                    label="Configurar canais", value="channels",
                    description="Ajustar destinos e canais do servidor", emoji="📺",
                ),
                discord.SelectOption(
                    label="Publicar ou atualizar painéis", value="publish",
                    description="Gerenciar painéis públicos do NARABOT", emoji="📌",
                ),
                discord.SelectOption(
                    label="Ver diagnóstico", value="status",
                    description="Identificar configurações ausentes ou padrão", emoji="🩺",
                ),
            ])
        super().__init__(
            placeholder="Acesso rápido — escolha uma tarefa frequente...",
            min_values=1, max_values=1, options=opcoes,
            custom_id="adm:atalhos", row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        rota = self.rotas.get(self.values[0])
        if not rota:
            return await interaction.response.send_message(
                "Essa ação rápida não está disponível. Abra uma categoria do painel.", ephemeral=True
            )
        action, categoria = rota
        await _executar_acao_admin(
            interaction, self.bot, action,
            categoria=categoria, user_id=self.user_id or interaction.user.id,
        )


class AdminMainView(discord.ui.View):
    """Painel administrativo organizado por categorias e atalhos frequentes."""

    def __init__(self, bot, user_id: int | None = None, is_admin: bool = True, is_bot_owner: bool = False):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        categorias = [
            ("servidor", "Servidor e acesso", "⚙️"),
            ("moderacao", "Moderação", "🛡️"),
            ("jogos", "Jogos e Coliseu", "🎮"),
            ("comunidade", "Comunidade", "📚"),
            ("economia", "Economia", "🪙"),
            ("publicacoes", "Publicações", "📌"),
            ("catalogos", "Ports & Mods", "🧩"),
            ("diagnostico", "Diagnóstico e IA", "🤖"),
        ]
        if not is_admin:  # moderador: esconde as categorias exclusivas do administrador
            categorias = [c for c in categorias if c[0] not in CATEGORIAS_SO_ADMIN]
        for index, (key, label, emoji) in enumerate(categorias):
            self.add_item(AdminCategoriaButton(bot, key, label, emoji, row=index // 4, user_id=user_id))
        # Sempre presente para que o custom_id também seja registrado na view
        # persistente criada durante cog_load(). As opções da sessão continuam
        # filtradas conforme o nível de acesso do usuário.
        self.add_item(AdminAtalhosSelect(bot, user_id, is_admin=is_admin))
        if is_bot_owner:
            self.add_item(RelacionamentoAdminButton(bot, int(user_id or 0)))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from cogs.platinas import eh_moderador
        mesma_pessoa = self.user_id is None or interaction.user.id == self.user_id
        autorizado = await eh_moderador(interaction.user, self.bot.db) or await _eh_admin_painel(self.bot, interaction.user)
        if not mesma_pessoa or not autorizado:
            await interaction.response.send_message("Você não tem autorização para utilizar este painel. Use `/adm` com uma conta autorizada.", ephemeral=True)
            return False
        return True


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

    def __init__(self, bot, callback_voltar=None):
        super().__init__(timeout=60)
        self.bot = bot
        self.callback_voltar = callback_voltar

    @discord.ui.button(label="Sim, restaurar tudo", emoji="⚠️", style=discord.ButtonStyle.danger, custom_id="adm:reset_yes")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        count = await GuildConfig.reset_all(self.bot.db, interaction.guild_id)
        embed = discord.Embed(
            title="✅ Configurações Restauradas",
            description=f"**{count}** configuração(ões) foram restauradas aos valores padrão de `config.py`.\n\nO bot continuará funcionando normalmente usando os valores globais.",
            color=discord.Color.green(),
        )
        if self.callback_voltar:
            from utils import view_so_com_voltar
            view = view_so_com_voltar(self.callback_voltar)
        else:
            view = VoltarInicioView(self.bot)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cancelar", emoji="↩️", style=discord.ButtonStyle.secondary, custom_id="adm:reset_no")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.callback_voltar:
            return await self.callback_voltar(interaction)
        await _mostrar_painel_principal(interaction, self.bot)


# ────────────────────────────────────────────────────────────────
# Seletor de canal persistente
# ────────────────────────────────────────────────────────────────

class ChannelSelectView(discord.ui.View):
    """Seletor nativo de canal que salva automaticamente."""

    def __init__(self, bot, key: str, label: str, callback_voltar=None):
        super().__init__(timeout=180)
        self.bot = bot
        self.key = key
        self.label = label
        self.callback_voltar = callback_voltar
        if callback_voltar:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à categoria")
        self.select = discord.ui.ChannelSelect(
            placeholder=f"Selecione o {label.lower()}",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
        )
        self.select.callback = self._salvar
        self.add_item(self.select)

    async def _salvar(self, interaction: discord.Interaction):
        escolhido = self.select.values[0]
        await GuildConfig.set(self.bot.db, interaction.guild_id, self.key, escolhido.id)
        # O ChannelSelect entrega um AppCommandChannel (só id/nome/menção). Para
        # alterar permissões é preciso o canal real do servidor.
        channel = interaction.guild.get_channel(escolhido.id) if interaction.guild else None
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(escolhido.id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                channel = None
        if self.key == "mod_channel" and channel is None:
            log.warning("Canal central salvo, mas não foi possível carregá-lo para ajustar permissões.")
        if self.key == "mod_channel" and channel is not None:
            role_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "mod_role")
            role = interaction.guild.get_role(role_id) if role_id else None
            if role:
                try:
                    await channel.set_permissions(
                        role, view_channel=True, send_messages=True,
                        read_message_history=True, attach_files=True, embed_links=True,
                        reason="Cargo de moderação vinculado à Central do NARA",
                    )
                except discord.Forbidden:
                    log.warning("Canal central alterado, mas o cargo de moderação não recebeu overwrite; verifique Gerenciar Canais.")
        log.info("Admin: %s configurado como %s na guild %s", self.key, escolhido.id, interaction.guild_id)
        embed = discord.Embed(
            title="✅ Canal Configurado",
            description=f"**{LABELS.get(self.key, self.key)}** definido como {escolhido.mention}.",
            color=discord.Color.green(),
        )
        if self.callback_voltar:
            from utils import view_so_com_voltar
            view = view_so_com_voltar(self.callback_voltar)
        else:
            view = VoltarInicioView(self.bot)
        await interaction.response.edit_message(embed=embed, view=view)


class RoleSelectView(discord.ui.View):
    """Seletor nativo de cargo que salva automaticamente."""

    def __init__(self, bot, key: str, label: str, callback_voltar=None):
        super().__init__(timeout=180)
        self.bot = bot
        self.key = key
        self.label = label
        self.callback_voltar = callback_voltar
        if callback_voltar:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à categoria")
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
        # Ao definir o cargo da equipe, concede acesso à Central privada criada
        # pelo assistente automático, sem tornar o canal público.
        aviso_permissao = False
        if self.key == "mod_role":
            mod_channel_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "mod_channel")
            mod_channel = interaction.guild.get_channel(mod_channel_id) if mod_channel_id else None
            if mod_channel is None and mod_channel_id:
                try:
                    mod_channel = await interaction.guild.fetch_channel(mod_channel_id)
                except discord.HTTPException:
                    mod_channel = None
            if isinstance(mod_channel, discord.TextChannel):
                try:
                    await mod_channel.set_permissions(
                        role,
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        attach_files=True,
                        embed_links=True,
                        reason="Cargo de moderação configurado pelo painel do NARA",
                    )
                except discord.Forbidden:
                    aviso_permissao = True
        log.info("Admin: %s configurado como %s na guild %s", self.key, role.id, interaction.guild_id)
        embed = discord.Embed(
            title="✅ Cargo Configurado",
            description=(
                f"**{LABELS.get(self.key, self.key)}** definido como {role.mention}."
                + ("\n\n⚠️ Não consegui atualizar as permissões da Central. Conceda **Gerenciar Canais** ao bot e tente novamente." if aviso_permissao else "")
            ),
            color=discord.Color.orange() if aviso_permissao else discord.Color.green(),
        )
        if self.callback_voltar:
            from utils import view_so_com_voltar
            view = view_so_com_voltar(self.callback_voltar)
        else:
            view = VoltarInicioView(self.bot)
        await interaction.response.edit_message(embed=embed, view=view)


# ────────────────────────────────────────────────────────────────
# Ajuste administrativo individual de XP e Denários
# ────────────────────────────────────────────────────────────────

class AdminEconomiaMembroSelect(discord.ui.UserSelect):
    def __init__(self, painel):
        self.painel = painel
        super().__init__(
            placeholder="Selecione o membro que receberá o ajuste...",
            min_values=1, max_values=1, row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        usuario = self.values[0] if self.values else None
        if usuario is None:
            return await interaction.response.send_message("Selecione um membro válido.", ephemeral=True)
        if getattr(usuario, "bot", False):
            return await interaction.response.send_message("Não é permitido ajustar o saldo de bots.", ephemeral=True)
        self.painel.membro_id = int(usuario.id)
        self.painel.membro_nome = str(getattr(usuario, "display_name", usuario.name))
        await self.painel.atualizar(interaction)


class AdminEconomiaOperacaoSelect(discord.ui.Select):
    def __init__(self, painel):
        self.painel = painel
        super().__init__(
            placeholder="Escolha a operação...",
            min_values=1, max_values=1, row=1,
            options=[
                discord.SelectOption(label="Adicionar", value="adicionar", emoji="➕", description="Creditar XP e/ou Denários"),
                discord.SelectOption(label="Remover", value="remover", emoji="➖", description="Debitar XP e/ou Denários"),
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        self.painel.operacao = self.values[0]
        await self.painel.atualizar(interaction)


class AdminEconomiaAjusteModal(discord.ui.Modal, title="Ajustar XP e Denários"):
    xp = discord.ui.TextInput(
        label="Quantidade de XP (opcional)", placeholder="Ex.: 500", required=False, max_length=10,
    )
    denarios = discord.ui.TextInput(
        label="Quantidade de Denários (opcional)", placeholder="Ex.: 100", required=False, max_length=10,
    )
    motivo = discord.ui.TextInput(
        label="Motivo obrigatório do ajuste", placeholder="Ex.: compensação de evento", max_length=200,
    )

    def __init__(self, bot, actor_id: int, target_id: int, operacao: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.actor_id = int(actor_id)
        self.target_id = int(target_id)
        self.operacao = operacao

    @staticmethod
    def _quantidade(valor: str, rotulo: str) -> int:
        texto = str(valor or "").strip()
        if not texto:
            return 0
        if not texto.isdecimal():
            raise ValueError(f"{rotulo}: informe somente um número inteiro positivo.")
        quantidade = int(texto)
        if not 1 <= quantidade <= 1_000_000_000:
            raise ValueError(f"{rotulo}: o valor precisa estar entre 1 e 1.000.000.000.")
        return quantidade

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if int(interaction.user.id) != self.actor_id or not await _eh_admin_painel(self.bot, interaction.user):
            return await interaction.followup.send(MSG_SO_ADMIN, ephemeral=True)
        if interaction.guild is None:
            return await interaction.followup.send("Esta ação só pode ser usada dentro de um servidor.", ephemeral=True)

        try:
            qtd_xp = self._quantidade(self.xp.value, "XP")
            qtd_denarios = self._quantidade(self.denarios.value, "Denários")
        except ValueError as exc:
            return await interaction.followup.send(str(exc), ephemeral=True)
        if qtd_xp == 0 and qtd_denarios == 0:
            return await interaction.followup.send(
                "Informe pelo menos uma quantidade: XP, Denários ou ambos.", ephemeral=True,
            )
        motivo = " ".join(str(self.motivo.value or "").split())
        if not motivo:
            return await interaction.followup.send("O motivo do ajuste é obrigatório.", ephemeral=True)

        membro = interaction.guild.get_member(self.target_id)
        if membro is None:
            try:
                membro = await interaction.guild.fetch_member(self.target_id)
            except discord.NotFound:
                return await interaction.followup.send(
                    "Esse membro não está mais no servidor. Nenhum saldo foi alterado.", ephemeral=True,
                )
            except discord.HTTPException:
                return await interaction.followup.send(
                    "Não consegui confirmar o membro no servidor. Tente novamente.", ephemeral=True,
                )
        if membro.bot:
            return await interaction.followup.send("Não é permitido ajustar o saldo de bots.", ephemeral=True)

        sinal = 1 if self.operacao == "adicionar" else -1
        try:
            resultado = await self.bot.db.ajustar_economia_por_admin(
                user_id=membro.id,
                actor_id=interaction.user.id,
                xp_delta=qtd_xp * sinal,
                denarios_delta=qtd_denarios * sinal,
                motivo=motivo,
                guild_id=interaction.guild.id,
            )
        except Exception:
            log.exception("Falha ao ajustar XP/Denários de user=%s por admin=%s", membro.id, interaction.user.id)
            return await interaction.followup.send(
                "Não consegui concluir o ajuste. Nenhum resultado foi confirmado; consulte os logs do bot.",
                ephemeral=True,
            )

        if resultado["xp_antes"] != resultado["xp_depois"]:
            try:
                from cogs.platinas import sincronizar_patente
                await sincronizar_patente(
                    interaction.guild, membro, resultado["nivel_depois"],
                )
            except Exception:
                log.exception("Saldo ajustado, mas falhou sincronização de patente para user=%s", membro.id)

        def fmt(numero: int) -> str:
            return f"{int(numero):,}".replace(",", ".")

        def linha(nome: str, delta: int, antes: int, depois: int) -> str:
            sinal_texto = "+" if delta > 0 else ""
            solicitado = qtd_xp if nome == "XP" else qtd_denarios
            aplicado = abs(int(delta))
            complemento = (
                f" _(solicitado: {fmt(solicitado)}; aplicado: {fmt(aplicado)} devido ao saldo disponível)_"
                if self.operacao == "remover" and aplicado < solicitado else ""
            )
            return f"**{nome}:** `{fmt(antes)}` → `{fmt(depois)}` · `{sinal_texto}{fmt(delta)}`{complemento}"

        embed = discord.Embed(
            title="✅ Ajuste administrativo concluído",
            description=(
                f"**Membro:** {membro.mention}\n"
                f"**Operação:** {'Adicionar' if self.operacao == 'adicionar' else 'Remover'}\n\n"
                f"{linha('XP', resultado['xp_delta'], resultado['xp_antes'], resultado['xp_depois'])}\n"
                f"{linha('Denários', resultado['denarios_delta'], resultado['denarios_antes'], resultado['denarios_depois'])}\n\n"
                f"**Nível:** {resultado['nivel_antes']} → {resultado['nivel_depois']}\n"
                f"**Motivo:** {discord.utils.escape_markdown(motivo)}"
            ),
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Responsável: {interaction.user} · Registro gravado na auditoria")
        await interaction.followup.send(embed=embed, ephemeral=True)


class AdminEconomiaAjusteContinuarButton(discord.ui.Button):
    def __init__(self, painel):
        super().__init__(
            label="Informar quantidades", emoji="⚖️", style=discord.ButtonStyle.primary,
            row=2, disabled=True,
        )
        self.painel = painel

    async def callback(self, interaction: discord.Interaction):
        if not self.painel.membro_id or self.painel.operacao not in {"adicionar", "remover"}:
            return await interaction.response.send_message(
                "Selecione um membro e uma operação antes de continuar.", ephemeral=True,
            )
        await interaction.response.send_modal(AdminEconomiaAjusteModal(
            self.painel.bot, self.painel.user_id, self.painel.membro_id, self.painel.operacao,
        ))


class AdminEconomiaAjusteView(discord.ui.View):
    """Fluxo privado do /adm para creditar/debitar XP e Denários de um membro."""

    def __init__(self, bot, user_id: int, callback_voltar=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = int(user_id)
        self.membro_id: int | None = None
        self.membro_nome: str | None = None
        self.operacao: str | None = None
        self.continuar_button = AdminEconomiaAjusteContinuarButton(self)
        self.add_item(AdminEconomiaMembroSelect(self))
        self.add_item(AdminEconomiaOperacaoSelect(self))
        self.add_item(self.continuar_button)
        if callback_voltar:
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Economia")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if int(interaction.user.id) != self.user_id or not await _eh_admin_painel(self.bot, interaction.user):
            await interaction.response.send_message(MSG_SO_ADMIN, ephemeral=True)
            return False
        return True

    async def atualizar(self, interaction: discord.Interaction):
        self.continuar_button.disabled = not (self.membro_id and self.operacao)
        membro = f"<@{self.membro_id}>" if self.membro_id else "_Não selecionado_"
        operacao = {"adicionar": "Adicionar", "remover": "Remover"}.get(self.operacao, "_Não selecionada_")
        embed = discord.Embed(
            title="⚖️ Ajustar XP e Denários",
            description=(
                f"**Membro:** {membro}\n**Operação:** {operacao}\n\n"
                "Selecione um membro e uma operação. Depois, informe XP e/ou Denários e o motivo."
            ),
            color=COR_PAINEL,
        )
        await interaction.response.edit_message(embed=embed, view=self)


# ────────────────────────────────────────────────────────────────
# Modal para valores numéricos (economia/recompensas)
# ────────────────────────────────────────────────────────────────

class NumberModal(discord.ui.Modal):
    """Modal genérico para configurar valores numéricos."""

    def __init__(self, bot, key: str, label: str, current_value: int | None, callback_voltar=None):
        super().__init__(title=f"Configurar: {label}")
        self.bot = bot
        self.key = key
        self.callback_voltar = callback_voltar
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
        if self.callback_voltar:
            from utils import view_so_com_voltar
            view = view_so_com_voltar(self.callback_voltar)
        else:
            view = VoltarInicioView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        log.exception("Erro no modal de configuração", exc_info=error)
        if not interaction.response.is_done():
            await interaction.response.send_message("Algo deu errado. Tente novamente.", ephemeral=True)


# ────────────────────────────────────────────────────────────────
# Botões de ação dentro das seções
# ────────────────────────────────────────────────────────────────

class SectionActionView(discord.ui.View):
    """Configurações em contexto: volta à categoria de origem, não reinicia o /adm."""

    def __init__(self, bot, keys: list[str], callback_voltar=None):
        super().__init__(timeout=600)
        self.bot = bot
        self.callback_voltar = callback_voltar
        if callback_voltar:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à categoria")
        else:
            self.add_item(AdminVoltarButton(bot))
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
                view = ChannelSelectView(self.bot, key, label, callback_voltar=self.callback_voltar)
                embed = discord.Embed(
                    title=f"⚙️ {label}",
                    description="Use o seletor abaixo para escolher o canal.",
                    color=COR_PAINEL,
                )
                await interaction.response.edit_message(embed=embed, view=view)
            elif tipo == "role":
                view = RoleSelectView(self.bot, key, label, callback_voltar=self.callback_voltar)
                embed = discord.Embed(
                    title=f"⚙️ {label}",
                    description="Use o seletor abaixo para escolher o cargo.",
                    color=COR_PAINEL,
                )
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                current = await GuildConfig.get(self.bot.db, interaction.guild_id, key)
                modal = NumberModal(self.bot, key, label, current, callback_voltar=self.callback_voltar)
                await interaction.response.send_modal(modal)
        return callback


# ────────────────────────────────────────────────────────────────
# Funções auxiliares para montar cada seção
# ────────────────────────────────────────────────────────────────

async def _mostrar_painel_principal(interaction: discord.Interaction, bot):
    """Renderiza o início do /adm com sinais de estado e ações frequentes."""
    db = bot.db
    gid = interaction.guild_id
    personalizados = usando_padrao = ausentes = 0
    for key in KEYS:
        valor = await GuildConfig.get(db, gid, key)
        custom = await GuildConfig.is_custom(db, gid, key)
        if custom:
            personalizados += 1
        elif valor not in (None, "", 0, "0"):
            usando_padrao += 1
        else:
            ausentes += 1

    pendentes = None
    try:
        dados_operacionais = await _dados_dashboard(bot, gid)
        pendentes = int(dados_operacionais.get("pending", 0))
    except Exception:
        # A indisponibilidade de um indicador nunca deve impedir a abertura do /adm.
        log.exception("Não foi possível carregar o resumo de pendências na tela inicial do /adm.")

    embed = discord.Embed(
        title="⚙️ Central administrativa",
        description=(
            "Gerencie o NARABOT por áreas. As ações mais usadas ficam no acesso rápido; "
            "as demais estão organizadas nas categorias abaixo.\n\n"
            "**Escolha uma categoria ou use o seletor de acesso rápido.**"
        ),
        color=COR_PAINEL,
    )
    embed.add_field(
        name="Configuração do servidor",
        value=(
            f"🟢 **{personalizados}** personalizadas\n"
            f"🟡 **{usando_padrao}** usando padrão\n"
            f"🔴 **{ausentes}** sem valor"
        ),
        inline=True,
    )
    embed.add_field(
        name="Fila de aprovação",
        value=(
            f"**{pendentes}** solicitações de platinas, zerados e runs pendentes"
            if pendentes is not None else "Indicador indisponível no momento; abra a fila para consultar."
        ),
        inline=True,
    )
    embed.add_field(
        name="Navegação",
        value="• Categorias para encontrar qualquer ferramenta\n• Acesso rápido para tarefas frequentes\n• Voltar à categoria após configurar",
        inline=False,
    )
    embed.set_footer(text="NARA • Painel privado • As alterações são salvas por servidor")
    is_bot_owner = await _eh_dono_global_bot(bot, interaction.user)
    is_admin_panel = await _eh_admin_painel(bot, interaction.user)
    view = AdminMainView(bot, interaction.user.id, is_admin_panel, is_bot_owner=is_bot_owner)
    if interaction.response.is_done():
        await interaction.edit_original_response(embed=embed, view=view)
    else:
        await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_secao(interaction: discord.Interaction, bot, section: str, titulo: str, callback_voltar=None):
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
    view = SectionActionView(bot, keys, callback_voltar=callback_voltar)
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_coliseu(interaction: discord.Interaction, bot, callback_voltar=None):
    """Seção Coliseu: combina canais de moderação/platinas com recompensas."""
    db = bot.db
    gid = interaction.guild_id

    mod_ch = await GuildConfig.get(db, gid, "mod_channel")
    plat_ch = await GuildConfig.get(db, gid, "platinas_channel")
    xp_plat = await GuildConfig.get(db, gid, "xp_platina")
    den_plat = await GuildConfig.get(db, gid, "denarios_platina")
    colizeu_ch = await GuildConfig.get(db, gid, "colizeu_channel")

    linhas = [
        f"📥 **Central de Aprovação (platinas, runs e zerados):** {_fmt_valor(mod_ch)}",
        f"🏆 **Canal público de Anúncio de Platinas:** {_fmt_valor(plat_ch)}",
        f"🏛️ **Canal do Painel do Colizeu:** {_fmt_valor(colizeu_ch)}",
        "",
        "_Todas as solicitações para análise da equipe chegam à Central de Aprovação. Os canais públicos só recebem registros depois da decisão._",
        "",
        f"⭐ **XP por Platina:** {xp_plat or 'Padrão'}",
        f"🪙 **Denários por Platina:** {den_plat or 'Padrão'}",
    ]
    embed = discord.Embed(title="⚔️ Configurações do Coliseu", description="\n".join(linhas), color=COR_PAINEL)
    keys = ["mod_channel", "platinas_channel", "colizeu_channel", "xp_platina", "denarios_platina"]
    view = SectionActionView(bot, keys, callback_voltar=callback_voltar)
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_galeria(interaction: discord.Interaction, bot, callback_voltar=None):
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
    view = SectionActionView(bot, ["perfis_channel"], callback_voltar=callback_voltar)
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_perfis(interaction: discord.Interaction, bot, callback_voltar=None):
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
    view = VoltarInicioView(bot) if callback_voltar is None else SectionActionView(bot, [], callback_voltar=callback_voltar)
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_jogos(interaction: discord.Interaction, bot, callback_voltar=None):
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
    view = SectionActionView(bot, ["games_channel", "promos_channel"], callback_voltar=callback_voltar)
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_economia(interaction: discord.Interaction, bot, callback_voltar=None):
    """Seção Economia: todas as recompensas e limites."""
    await _abrir_secao(interaction, bot, "economy", "💰 Economia e Recompensas", callback_voltar=callback_voltar)


async def _abrir_personalizacao(interaction: discord.Interaction, bot, callback_voltar=None):
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
    view = VoltarInicioView(bot) if callback_voltar is None else SectionActionView(bot, [], callback_voltar=callback_voltar)
    await interaction.response.edit_message(embed=embed, view=view)


async def _abrir_status(interaction: discord.Interaction, bot, callback_voltar=None):
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
    view = VoltarInicioView(bot) if callback_voltar is None else SectionActionView(bot, [], callback_voltar=callback_voltar)
    await interaction.response.edit_message(embed=embed, view=view)


async def _executar_configuracao_automatica(interaction: discord.Interaction, bot):
    """Cria a estrutura recomendada de canais e salva os destinos por servidor.

    Só cria canais após clique explícito do administrador. Não apaga nem renomeia
    canais existentes e mantém a central de aprovação privada para @everyone.
    """
    guild = interaction.guild
    if guild is None:
        return await interaction.response.send_message(
            "Este recurso só funciona dentro de um servidor Discord.", ephemeral=True
        )

    me = guild.me or guild.get_member(bot.user.id)
    if me is None or not me.guild_permissions.manage_channels:
        return await interaction.response.send_message(
            "Não consigo criar os canais porque falta a permissão **Gerenciar Canais**. "
            "Conceda essa permissão ao NARA e tente novamente.", ephemeral=True
        )

    await interaction.response.defer(ephemeral=True, thinking=True)
    category_name = "NARABOT • CANAIS OFICIAIS"
    category = discord.utils.get(guild.categories, name=category_name)
    criados = []
    reutilizados = []
    configurados = []

    if category is None:
        category = await guild.create_category(
            category_name,
            reason="Configuração automática do NARA",
        )
        criados.append(f"Categoria **{category.name}**")

    # A central é privada por padrão. Administradores mantêm acesso pelo bypass
    # de permissões do Discord; cargos de equipe podem ser adicionados em /adm.
    bot_member = me
    configured_mod_role_id = await GuildConfig.get(bot.db, guild.id, "mod_role")
    configured_mod_role = guild.get_role(configured_mod_role_id) if configured_mod_role_id else None
    specs = (
        ("mod_channel", "central-aprovacoes", "Solicitações privadas para análise da equipe", True),
        ("platinas_channel", "anuncios-platinas", "Platinas aprovadas", False),
        ("zerados_channel", "anuncios-zerados", "Jogos zerados aprovados", False),
        ("soulslike_channel", "runs-soulslike", "Runs e recordes Soulslike", False),
        ("perfis_channel", "santuario-perfis", "Santuários e perfis dos membros", False),
        ("video_channel", "youtube-videos", "Novos vídeos do canal conectado", False),
        ("live_channel", "youtube-lives", "Avisos de transmissões ao vivo", False),
        ("games_channel", "jogos-gratis", "Jogos gratuitos encontrados", False),
        ("promos_channel", "promocoes", "Promoções e descontos de jogos", False),
        ("colizeu_channel", "painel-colizeu", "Painel principal e rankings do Colizeu", False),
        ("nara_channel", "nara-conversa", "Converse com a Nara; pode mencionar a assistente ou usar este canal", False),
    )

    for key, channel_name, topic, privado in specs:
        channel = discord.utils.get(category.text_channels, name=channel_name)
        if channel is None:
            overwrites = {}
            if privado:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    bot_member: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, embed_links=True,
                        attach_files=True, read_message_history=True,
                    ),
                }
                if configured_mod_role is not None:
                    overwrites[configured_mod_role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, embed_links=True,
                        attach_files=True, read_message_history=True,
                    )
            channel = await guild.create_text_channel(
                channel_name,
                category=category,
                topic=topic,
                overwrites=overwrites,
                reason="Configuração automática do NARA",
            )
            criados.append(f"{channel.mention}")
        else:
            reutilizados.append(channel.mention)
        await GuildConfig.set(bot.db, guild.id, key, channel.id)
        configurados.append(key)

    embed = discord.Embed(
        title="✨ Estrutura do NARA configurada",
        description=(
            f"**{len(configurados)} destinos foram vinculados automaticamente** neste servidor.\n\n"
            "A estrutura foi criada sem apagar, mover ou renomear canais existentes. "
            "A Central de Aprovação foi criada privada para evitar exposição de comprovantes e solicitações."
        ),
        color=discord.Color.green(),
    )
    if criados:
        embed.add_field(name=f"Criados ({len(criados)})", value="\n".join(criados)[:1024], inline=False)
    if reutilizados:
        embed.add_field(name=f"Reutilizados ({len(reutilizados)})", value=" · ".join(reutilizados)[:1024], inline=False)
    embed.add_field(
        name="Próximos ajustes no painel /adm",
        value=(
            "1. Configure o **cargo de moderador** para a equipe acessar a Central de Aprovação.\n"
            "2. Escolha os cargos de aviso de vídeos e lives.\n"
            "3. Revise recompensas e permissões dos canais."
        ),
        inline=False,
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


async def _confirmar_reset(interaction: discord.Interaction, bot, callback_voltar=None):
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
    view = ResetConfirmView(bot, callback_voltar=callback_voltar)
    await interaction.response.edit_message(embed=embed, view=view)


# ────────────────────────────────────────────────────────────────
# Cog principal
# ────────────────────────────────────────────────────────────────

class Admin(commands.Cog):
    """Painel administrativo unificado da Nara."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # /adm cria um painel efêmero e vinculado ao usuário. Não registre uma
        # AdminMainView global com os mesmos custom_id da view de sessão: isso cria
        # uma rota de fallback que pode reapresentar o menu principal em vez da
        # categoria atualmente aberta.
        self.bot.add_view(VoltarInicioView(self.bot))
        # ResetConfirmView usa timeout=60 e é criada quando a confirmação é aberta;
        # não deve ser registrada como view persistente durante a inicialização.
        log.info("Cog Admin carregado com views persistentes registradas.")

    @app_commands.command(name="adm", description="Abra a central administrativa da NARA, com moderação e configurações por categoria.")
    @app_commands.guild_only()
    async def adm(self, interaction: discord.Interaction):
        """Comando único de entrada para todo o painel administrativo."""
        from cogs.platinas import eh_moderador
        if not await eh_moderador(interaction.user, self.bot.db) and not await _eh_admin_painel(self.bot, interaction.user):
            return await interaction.response.send_message(
                "Este painel é restrito à equipe autorizada.", ephemeral=True,
            )
        embed = discord.Embed(
            title="⚙️ Painel Administrativo — Nara",
            description="Carregando configurações...",
            color=COR_PAINEL,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await _mostrar_painel_principal(interaction, self.bot)


async def setup(bot):
    await bot.add_cog(Admin(bot))