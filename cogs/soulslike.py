import io
import logging
import re

import discord
from discord import app_commands
from discord.ext import commands

import config
from admin_config import GuildConfig
from utils import get_text_channel

log = logging.getLogger("soulslike")

JOGOS_PADRAO = ["Elden Ring", "Dark Souls", "Dark Souls II", "Dark Souls III", "Bloodborne", "Sekiro", "Lies of P"]
DESAFIOS_PADRAO = [
    ("Any%", "Zerar o jogo o mais rápido possível, sem restrições extras."),
    ("Nível 1", "Zerar o jogo sem subir de nível."),
    ("Sem tomar dano", "Zerar o jogo sem levar nenhum golpe (no-hit)."),
    ("Todos os chefes", "Derrotar todos os chefes do jogo."),
]
MIN_SEGUNDOS = 30
MAX_SEGUNDOS = 1000 * 3600


async def eh_moderador(member: discord.Member, db=None) -> bool:
    if member.guild_permissions.manage_guild:
        return True
    if db and member.guild:
        mod_role_id = await GuildConfig.get(db, member.guild.id, "mod_role")
        if mod_role_id and any(r.id == mod_role_id for r in member.roles):
            return True
    return bool(config.MOD_ROLE_ID) and any(r.id == config.MOD_ROLE_ID for r in member.roles)


MEDALHAS = ["🥇", "🥈", "🥉"]


# ------------------------------------------------------------------ tempo
def parse_tempo(txt: str) -> int | None:
    """Aceita 1:30:45, 90:15, 1h30m45s, 1h30, 45m12s. Devolve segundos ou None."""
    t = txt.strip().lower().replace(" ", "")
    if not t:
        return None
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)(?:min|m))?(?:(\d+)s)?", t)
    if m and any(m.groups()):
        h, mi, s = (int(x or 0) for x in m.groups())
    elif (m := re.fullmatch(r"(\d+)h(\d{1,2})", t)):
        h, mi, s = int(m[1]), int(m[2]), 0
    elif re.fullmatch(r"\d+(:\d{1,2}){1,2}", t):
        p = [int(x) for x in t.split(":")]
        if len(p) == 2:
            h, mi, s = 0, p[0], p[1]
        else:
            h, mi, s = p
            if mi > 59:
                return None
        if s > 59:
            return None
    else:
        return None
    total = h * 3600 + mi * 60 + s
    return total if MIN_SEGUNDOS <= total <= MAX_SEGUNDOS else None


async def substituir_ou_responder(interaction: discord.Interaction, *, content: str | None = None,
                                  embed: discord.Embed | None = None, view: discord.ui.View | None = None):
    """Edita a tela privada já aberta; para painéis públicos, cria a primeira resposta efêmera."""
    mensagem_privada = bool(
        interaction.message and getattr(interaction.message.flags, "ephemeral", False)
    )
    if mensagem_privada:
        if embed is not None:
            await interaction.response.edit_message(content=None, embed=embed, view=view)
        else:
            await interaction.response.edit_message(content=content, embeds=[], view=view)
    elif embed is not None:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction.response.send_message(content=content, view=view, ephemeral=True)


def fmt_tempo(seg: int) -> str:
    h, resto = divmod(seg, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}"


AJUDA_TEMPO = (
    "Não entendi o tempo. Use um destes formatos: `1:30:45`, `90:15` (minutos:segundos), "
    "`1h30m45s`, `1h30` ou `45m12s`. O mínimo é 30 segundos."
)

# ------------------------------------------------------------------ consultas
SQL_RANKING = """
SELECT r.id, r.user_id, r.seconds, r.build,
       (SELECT COUNT(*) FROM sl_runs r3 WHERE r3.user_id=r.user_id AND r3.game_id=r.game_id
          AND r3.challenge_id=r.challenge_id AND r3.status='approved') AS vezes
FROM sl_runs r
WHERE r.status='approved' AND r.game_id=? AND r.challenge_id=?
  AND r.id = (SELECT r2.id FROM sl_runs r2
              WHERE r2.user_id=r.user_id AND r2.game_id=r.game_id
                AND r2.challenge_id=r.challenge_id AND r2.status='approved'
              ORDER BY r2.seconds ASC, r2.id ASC LIMIT 1)
ORDER BY r.seconds ASC, r.id ASC LIMIT ?
"""

SQL_POSICAO = """
SELECT COUNT(DISTINCT user_id) AS c FROM sl_runs
WHERE status='approved' AND game_id=? AND challenge_id=? AND seconds < ? AND user_id != ?
"""

SQL_RUN_COMPLETA = """
SELECT r.*, g.name AS jogo, c.name AS desafio, c.rules AS regras
FROM sl_runs r JOIN sl_games g ON g.id=r.game_id JOIN sl_challenges c ON c.id=r.challenge_id
WHERE r.id=?
"""


class Soulslike(commands.Cog):
    sl_admin = app_commands.Group(
        name="sl_admin",
        description="Administração do Soulslike",
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        db = self.bot.db
        for nome in JOGOS_PADRAO:
            await db.conn.execute("INSERT OR IGNORE INTO sl_games(name) VALUES (?)", (nome,))
        for nome, regras in DESAFIOS_PADRAO:
            await db.conn.execute("INSERT OR IGNORE INTO sl_challenges(name, rules) VALUES (?,?)", (nome, regras))
        await db.conn.commit()
        self.bot.add_view(RevisaoRunView(self))
        self.bot.add_view(CentralView(self))
        self.pending_uploads = {}

    # -------------------------------------------------------- auxiliares
    async def _jogo(self, nome: str):
        return await self.bot.db._one("SELECT * FROM sl_games WHERE name=?", (nome.strip(),))

    async def _desafio(self, nome: str):
        return await self.bot.db._one("SELECT * FROM sl_challenges WHERE name=?", (nome.strip(),))

    async def _posicao(self, game_id, chal_id, seg, user_id) -> int:
        row = await self.bot.db._one(SQL_POSICAO, (game_id, chal_id, seg, user_id))
        return row["c"] + 1

    async def ac_jogo(self, interaction: discord.Interaction, atual: str):
        rows = await self.bot.db._all("SELECT name FROM sl_games ORDER BY name")
        return [app_commands.Choice(name=r["name"], value=r["name"]) for r in rows if atual.lower() in r["name"].lower()][:25]

    async def ac_desafio(self, interaction: discord.Interaction, atual: str):
        rows = await self.bot.db._all("SELECT name FROM sl_challenges ORDER BY name")
        return [app_commands.Choice(name=r["name"], value=r["name"]) for r in rows if atual.lower() in r["name"].lower()][:25]

    async def texto_ranking(self, game_id: int, chal_id: int) -> str:
        db = self.bot.db
        g = await db._one("SELECT * FROM sl_games WHERE id=?", (game_id,))
        c = await db._one("SELECT * FROM sl_challenges WHERE id=?", (chal_id,))
        if not g or not c:
            return "## ⚔️ Hall da Fama\n\nJogo ou desafio não encontrado. Atualize a central."
        rows = await db._all(SQL_RANKING, (game_id, chal_id, 10))
        partes = [f"## ⚔️ {g['name']} — {c['name']}"]
        if c["rules"]:
            partes.extend(["", f"**Regras:** {c['rules'][:700]}"])
        partes.append("")
        if not rows:
            partes.append("Ainda não há registros nesta categoria. Seja o primeiro a enviar uma run aprovada!")
        else:
            for i, row in enumerate(rows):
                pos = MEDALHAS[i] if i < 3 else f"`{i + 1:>2}.`"
                build = f" · {row['build']}" if row['build'] and row['build'] != "Não informada" else ""
                vezes = f" · 🔁 {row['vezes']}x" if row['vezes'] > 1 else ""
                partes.append(f"{pos} <@{row['user_id']}> — **{fmt_tempo(row['seconds'])}**{build}{vezes}")
        partes.extend(["", "_O ranking usa o melhor tempo de cada jogador; 🔁 indica quantas vezes concluiu o desafio._"])
        return "\n".join(partes)[:1990]

    async def embed_ranking(self, game_id: int, chal_id: int) -> discord.Embed:
        db = self.bot.db
        g = await db._one("SELECT * FROM sl_games WHERE id=?", (game_id,))
        c = await db._one("SELECT * FROM sl_challenges WHERE id=?", (chal_id,))
        rows = await db._all(SQL_RANKING, (game_id, chal_id, 10))
        e = discord.Embed(title=f"⚔️ {g['name']} — {c['name']}", color=config.COR_OURO)
        if c["rules"]:
            e.add_field(name="Regras do desafio", value=c["rules"], inline=False)
        if not rows:
            e.description = "Ninguém registrou essa categoria ainda. Seja o primeiro pela Central Soulslike!"
        else:
            linhas = []
            for i, r in enumerate(rows):
                pos = MEDALHAS[i] if i < 3 else f"`{i + 1}.`"
                build = f" • {r['build']}" if r["build"] and r["build"] != "Não informada" else ""
                vezes = f" • 🔁 {r['vezes']}x" if r["vezes"] > 1 else ""
                linhas.append(f"{pos} <@{r['user_id']}> — **{fmt_tempo(r['seconds'])}**{build}{vezes}")
            e.description = "\n".join(linhas)
        e.set_footer(text="O ranking usa o melhor tempo de cada jogador. 🔁 mostra quantas vezes ele zerou.")
        return e

    # -------------------------------------------------------- submissão de runs (usada pela Central)
    async def enviar_para_moderacao(self, user, g, c, seg, build, dados, filename):
        db = self.bot.db
        mod_ch_id = await GuildConfig.get(db, user.guild.id if hasattr(user, 'guild') and user.guild else 0, "mod_channel") or config.MOD_CHANNEL_ID
        canal = await get_text_channel(self.bot, mod_ch_id)
        if canal is None:
            return None
        cur = await db.conn.execute(
            "INSERT INTO sl_runs(user_id, game_id, challenge_id, build, seconds) VALUES (?,?,?,?,?)",
            (user.id, g["id"], c["id"], build, seg),
        )
        await db.conn.commit()
        run_id = cur.lastrowid

        record = await db._one(
            "SELECT MIN(seconds) AS m FROM sl_runs WHERE status='approved' AND game_id=? AND challenge_id=?",
            (g["id"], c["id"]),
        )
        pb = await db._one(
            "SELECT MIN(seconds) AS m FROM sl_runs WHERE status='approved' AND user_id=? AND game_id=? AND challenge_id=?",
            (user.id, g["id"], c["id"]),
        )
        pos = await self._posicao(g["id"], c["id"], seg, user.id)
        if pb and pb["m"] is not None and seg >= pb["m"]:
            ref = f"não melhora o melhor tempo dele ({fmt_tempo(pb['m'])}); conta como **mais uma zerada**"
        elif record and record["m"] is not None:
            dif = seg - record["m"]
            ref = "seria um **novo recorde**" if dif < 0 else f"seria o {pos}º, {fmt_tempo(dif)} mais lento que o recorde"
        else:
            ref = "seria o **primeiro registro** da categoria"

        embed = discord.Embed(title="⚔️ Run Soulslike aguardando aprovação", color=config.COR_PRATA)
        embed.add_field(name="Membro", value=user.mention)
        embed.add_field(name="Jogo", value=g["name"])
        embed.add_field(name="Desafio", value=c["name"])
        embed.add_field(name="Tempo", value=fmt_tempo(seg))
        embed.add_field(name="Build", value=build or "Não informada")
        embed.add_field(name="Posição", value=ref)
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
            embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=f"SL:{run_id}")
        try:
            msg = await canal.send(
                embed=embed,
                file=discord.File(io.BytesIO(dados), filename=filename),
                view=RevisaoRunView(self),
            )
        except discord.HTTPException:
            await db.conn.execute("DELETE FROM sl_runs WHERE id=?", (run_id,))
            await db.conn.commit()
            return None
        url = msg.embeds[0].image.url if msg.embeds and msg.embeds[0].image else ""
        await db.conn.execute("UPDATE sl_runs SET proof_msg_id=?, proof_url=? WHERE id=?", (msg.id, url, run_id))
        await db.conn.commit()
        await db.log(user.id, "run_registrada", f"id={run_id} {g['name']}/{c['name']} {fmt_tempo(seg)}")
        return run_id

    # -------------------------------------------------------- central Soulslike
    def texto_central(self) -> str:
        return (
            "# ⛧ SOULSLIKE · THE HALL OF THE FALLEN\n\n"
            "**A chama está acesa.** Registre suas runs, consulte recordes e acompanhe sua jornada.\n\n"
            "⚔️ **Registrar run** — jogo, desafio, tempo, build e comprovante.\n"
            "🏆 **Hall da Fama** — melhores tempos por jogo e desafio.\n"
            "📜 **Livro dos Desafios** — categorias e regras.\n"
            "🗡️ **Meu perfil** — histórico e status dos registros.\n\n"
            "_Apenas runs aprovadas entram no ranking. Use os botões abaixo para continuar._"
        )

    def embed_central(self) -> discord.Embed:
        e = discord.Embed(
            title="⛧ SOULSLIKE | THE HALL OF THE FALLEN",
            description=(
                "**A chama está acesa.**\n"
                "Registre suas runs, consulte os recordes e acompanhe sua jornada.\n\n"
                "Escolha uma opção nos botões abaixo. Suas submissões são encaminhadas à moderação."
            ),
            color=config.COR_OURO,
        )
        e.add_field(name="⚔️ Registro de run", value="Jogo, desafio, tempo, build e comprovante.", inline=True)
        e.add_field(name="🏆 Hall da Fama", value="Melhores tempos por jogo e desafio.", inline=True)
        e.add_field(name="📜 Livro dos Desafios", value="Consulte regras e categorias disponíveis.", inline=True)
        e.add_field(name="🗡️ Meu perfil", value="Histórico, status e runs pendentes.", inline=True)
        e.set_footer(text="Cada run deixa uma marca. Apenas runs aprovadas entram no ranking.")
        return e

    async def mostrar_perfil(self, interaction: discord.Interaction):
        rows = await self.bot.db._all(
            """SELECT r.*, g.name AS jogo, c.name AS desafio FROM sl_runs r
               JOIN sl_games g ON g.id=r.game_id JOIN sl_challenges c ON c.id=r.challenge_id
               WHERE r.user_id=? ORDER BY r.id DESC LIMIT 10""",
            (interaction.user.id,),
        )
        if not rows:
            return await substituir_ou_responder(
                interaction, content="## 🗡️ Crônicas do jogador\n\nVocê ainda não registrou nenhuma run.",
                view=VoltarCentralView(self),
            )
        status = {"pending": "⏳ Pendente", "approved": "✓ Aprovada", "rejected": "✕ Rejeitada",
                  "cancelled": "— Cancelada", "invalidated": "⚠ Invalidada"}
        lines = []
        for r in rows:
            line = f"`#{r['id']}` **{r['jogo']}** · {r['desafio']} · `{fmt_tempo(r['seconds'])}` · {status.get(r['status'], r['status'])}"
            if r['status'] == 'rejected' and r['reject_reason']:
                line += f"\n> Motivo: {r['reject_reason'][:250]}"
            lines.append(line)
        e = discord.Embed(title="🗡️ Crônicas do jogador", description="\n\n".join(lines), color=config.COR_PRATA)
        e.set_footer(text="Mostrando seus 10 registros mais recentes.")
        view = PerfilView(self, rows)
        view.add_item(VoltarCentralButton(self, row=1))
        await substituir_ou_responder(interaction, embed=e, view=view)

    async def mostrar_desafios(self, interaction: discord.Interaction):
        jogos = await self.bot.db._all("SELECT * FROM sl_games ORDER BY name")
        desafios = await self.bot.db._all("SELECT * FROM sl_challenges ORDER BY name")
        if not jogos or not desafios:
            return await substituir_ou_responder(
                interaction, content="## 📜 Livro dos Desafios\n\nAinda não existem jogos ou desafios cadastrados.",
                view=VoltarCentralView(self),
            )
        lines = ["## 📜 Livro dos Desafios", ""]
        for c in desafios[:15]:
            regras = c['rules'] or 'Sem regras adicionais cadastradas.'
            lines.append(f"**{c['name']}**\n{regras[:250]}")
        lines.extend(["", "### 🎮 Jogos disponíveis"])
        lines.extend(f"• {g['name']}" for g in jogos[:25])
        if len(desafios) > 15 or len(jogos) > 25:
            lines.extend(["", "_A lista foi limitada para caber na mensagem do Discord._"])
        await substituir_ou_responder(
            interaction, content="\n".join(lines)[:2000], view=VoltarCentralView(self)
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is not None:
            return
        state = self.pending_uploads.get(message.author.id)
        if not state:
            return
        if not message.attachments:
            return
        attachment = message.attachments[0]
        ctype = (attachment.content_type or "").lower()
        is_image = ctype.startswith("image/") or attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
        is_video = ctype.startswith("video/") or attachment.filename.lower().endswith((".mp4", ".mov", ".webm", ".mkv"))
        if not (is_image or is_video):
            await message.channel.send("O arquivo precisa ser uma imagem ou vídeo. Envie o comprovante como anexo.")
            return
        if attachment.size > 20 * 1024 * 1024:
            await message.channel.send("O arquivo excede o limite de 20 MB desta central. Envie uma versão menor.")
            return
        try:
            data = await attachment.read()
            g = await self.bot.db._one("SELECT * FROM sl_games WHERE id=?", (state['game_id'],))
            c = await self.bot.db._one("SELECT * FROM sl_challenges WHERE id=?", (state['challenge_id'],))
            if not g or not c:
                self.pending_uploads.pop(message.author.id, None)
                return await message.channel.send("O jogo ou desafio não está mais disponível. Abra a Central Soulslike e tente novamente.")
            seg = state['seconds']
            prev = [
                "## ⚔️ Confira sua run antes de enviar",
                f"**Jogo:** {g['name']}",
                f"**Desafio:** {c['name']}",
                f"**Tempo:** `{fmt_tempo(seg)}`",
                f"**Build:** {state['build'] or 'Não informada'}",
            ]
            if c['rules']:
                prev.extend(["", f"**Regras do desafio:** {c['rules'][:700]}"])
            prev.extend(["", "_Confirme para enviar o comprovante à moderação._"])
            view = ConfirmarView(self, message.author, g, c, seg, state['build'], data, attachment.filename[:100])
            await message.channel.send(content="\n".join(prev), view=view)
            self.pending_uploads.pop(message.author.id, None)
        except (discord.HTTPException, OSError) as exc:
            log.exception("Falha ao processar comprovante enviado por DM: %s", exc)
            await message.channel.send("Não consegui processar esse arquivo. Tente enviar novamente pela Central Soulslike.")

    # -------------------------------------------------------- admin
    @sl_admin.command(name="publicar_central", description="[MOD] Publica a central permanente para registrar runs e consultar desafios.")
    @app_commands.describe(canal="Canal onde a central ficará disponível")
    async def publicar_central(self, interaction: discord.Interaction, canal: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Você precisa da permissão Gerenciar servidor.", ephemeral=True)
        try:
            await upsert_panel(
                self.bot, canal, f"panel:soulslike:{interaction.guild_id}:{canal.id}",
                marker="central:register", content=self.texto_central(), embeds=[], view=CentralView(self),
            )
        except discord.Forbidden:
            return await interaction.response.send_message("Não tenho permissão para enviar mensagens neste canal.", ephemeral=True)
        await self.bot.db.log(interaction.user.id, "central_publicada", f"channel={canal.id}")
        await interaction.response.send_message(f"✅ Central Soulslike atualizada em {canal.mention}.", ephemeral=True)

    @sl_admin.command(name="jogo_adicionar", description="[MOD] Adiciona um jogo às opções de registro de runs.")
    async def jogo_adicionar(self, interaction: discord.Interaction, nome: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        nome = nome.strip()[:80]
        cur = await self.bot.db.conn.execute("INSERT OR IGNORE INTO sl_games(name) VALUES (?)", (nome,))
        await self.bot.db.conn.commit()
        msg = f"Jogo **{nome}** adicionado." if cur.rowcount else f"**{nome}** já existe."
        await self.bot.db.log(interaction.user.id, "sl_jogo_adicionar", nome)
        await interaction.response.send_message(msg, ephemeral=True)

    @sl_admin.command(name="desafio_adicionar", description="[MOD] Cria uma categoria de desafio e define as regras exibidas aos jogadores.")
    @app_commands.describe(nome="Nome do desafio", regras="Regras que aparecem para quem registra")
    async def desafio_adicionar(self, interaction: discord.Interaction, nome: str, regras: str = ""):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        nome = nome.strip()[:80]
        cur = await self.bot.db.conn.execute(
            "INSERT OR IGNORE INTO sl_challenges(name, rules) VALUES (?,?)", (nome, regras.strip()[:300])
        )
        await self.bot.db.conn.commit()
        msg = f"Desafio **{nome}** adicionado." if cur.rowcount else f"**{nome}** já existe."
        await self.bot.db.log(interaction.user.id, "sl_desafio_adicionar", nome)
        await interaction.response.send_message(msg, ephemeral=True)

    @sl_admin.command(name="invalidar", description="[MOD] Retira do ranking uma run aprovada e registra o motivo no log.")
    @app_commands.describe(numero="Número da run", motivo="Motivo (fica no log)")
    async def invalidar(self, interaction: discord.Interaction, numero: int, motivo: str = ""):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        db = self.bot.db
        run = await db._one("SELECT * FROM sl_runs WHERE id=?", (numero,))
        if run is None or run["status"] != "approved":
            return await interaction.response.send_message("Só dá para invalidar uma run aprovada.", ephemeral=True)
        cur = await db.conn.execute(
            "UPDATE sl_runs SET status='invalidated', reviewer_id=?, reject_reason=? WHERE id=? AND status='approved'",
            (interaction.user.id, motivo[:300], numero),
        )
        await db.conn.commit()
        if cur.rowcount != 1:
            return await interaction.response.send_message("A run deixou de estar aprovada antes da operação.", ephemeral=True)
        await db.log(interaction.user.id, "run_invalidada", f"id={numero} motivo={motivo}")
        await interaction.response.send_message(f"Run `#{numero}` invalidada e fora do ranking.", ephemeral=True)

    # -------------------------------------------------------- decisões da moderação
    async def carregar_run(self, interaction: discord.Interaction):
        """Lê o número da run no rodapé do card. Já responde ao usuário se algo estiver errado."""
        try:
            run_id = int(interaction.message.embeds[0].footer.text.split(":")[1])
        except (IndexError, ValueError, AttributeError):
            await interaction.response.send_message("Não consegui identificar essa run.", ephemeral=True)
            return None
        run = await self.bot.db._one(SQL_RUN_COMPLETA, (run_id,))
        if run is None or run["status"] != "pending":
            await interaction.response.send_message("Este registro já foi processado.", ephemeral=True)
            return None
        return run

    async def aprovar(self, interaction: discord.Interaction):
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        run = await self.carregar_run(interaction)
        if run is None:
            return
        if run["user_id"] == interaction.user.id and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Você não pode aprovar a sua própria run.", ephemeral=True)

        db = self.bot.db
        antes = await db._one(
            "SELECT MIN(seconds) AS m FROM sl_runs WHERE status='approved' AND game_id=? AND challenge_id=?",
            (run["game_id"], run["challenge_id"]),
        )
        pb_antes = await db._one(
            "SELECT MIN(seconds) AS m FROM sl_runs WHERE status='approved' AND user_id=? AND game_id=? AND challenge_id=?",
            (run["user_id"], run["game_id"], run["challenge_id"]),
        )
        ja_tinha = await db._one(
            "SELECT COUNT(*) AS c FROM sl_runs WHERE status='approved' AND user_id=? AND game_id=? AND challenge_id=?",
            (run["user_id"], run["game_id"], run["challenge_id"]),
        )
        cur = await db.conn.execute(
            "UPDATE sl_runs SET status='approved', reviewer_id=? WHERE id=? AND status='pending'",
            (interaction.user.id, run["id"]),
        )
        await db.conn.commit()
        if cur.rowcount != 1:
            return await interaction.response.send_message("Esta run já foi processada por outro moderador.", ephemeral=True)
        await db.log(interaction.user.id, "run_aprovada", f"id={run['id']} user={run['user_id']}")
        progressao = self.bot.get_cog("ProgressaoXP")
        if progressao:
            await progressao.conceder_xp(interaction.guild, run["user_id"], 100, "run aprovada")

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Resultado", value=f"✅ Aprovada por {interaction.user.mention}", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)

        novo_recorde = antes is None or antes["m"] is None or run["seconds"] < antes["m"]
        melhorou = pb_antes is None or pb_antes["m"] is None or run["seconds"] < pb_antes["m"]
        if novo_recorde and progressao:
            await progressao.conceder_xp(interaction.guild, run["user_id"], 100, "novo recorde")
        tempo_no_ranking = run["seconds"] if melhorou else pb_antes["m"]
        pos = await self._posicao(run["game_id"], run["challenge_id"], tempo_no_ranking, run["user_id"])
        vezes = ja_tinha["c"] + 1

        canal = await get_text_channel(self.bot, config.SOULSLIKE_CHANNEL_ID) if config.SOULSLIKE_CHANNEL_ID else None
        if canal:
            if novo_recorde:
                titulo = "👑 NOVO RECORDE!"
            elif melhorou:
                titulo = "⚔️ NOVA RUN SOULSLIKE!"
            else:
                titulo = "🔁 ZEROU DE NOVO!"
            linhas = [
                f"## {titulo}",
                f"<@{run['user_id']}> terminou **{run['jogo']}** no desafio **{run['desafio']}** em **{fmt_tempo(run['seconds'])}**.",
                f"**Build:** {run['build'] or 'Não informada'}",
                f"**Posição no ranking:** {pos}º" + ("" if melhorou else " _(melhor tempo pessoal)_"),
            ]
            if run["proof_url"]:
                linhas.append(f"[📸 Ver comprovante]({run['proof_url']})")
            if vezes > 1:
                linhas.append(f"**Runs concluídas:** 🔁 {vezes}x")
            await canal.send("\n".join(linhas))

    async def rejeitar(self, interaction: discord.Interaction):
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        run = await self.carregar_run(interaction)
        if run is None:
            return
        await interaction.response.send_modal(MotivoModal(self, run["id"]))


# ------------------------------------------------------------------ views
class VoltarCentralView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=600)
        self.cog = cog

    @discord.ui.button(label="Voltar à central", emoji="↩️", style=discord.ButtonStyle.secondary)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=self.cog.texto_central(), embeds=[], view=CentralView(self.cog))


class VoltarCentralButton(discord.ui.Button):
    def __init__(self, cog, row=1):
        self.cog = cog
        super().__init__(label="Voltar à central", emoji="↩️", style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=self.cog.texto_central(), embeds=[], view=CentralView(self.cog))


class CentralView(discord.ui.View):
    """View persistente: custom_id estável e timeout=None permitem reutilizar a mensagem após reinício."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Registrar run", style=discord.ButtonStyle.danger, emoji="⚔️", custom_id="central:register", row=0)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        jogos = await self.cog.bot.db._all("SELECT * FROM sl_games ORDER BY name")
        desafios = await self.cog.bot.db._all("SELECT * FROM sl_challenges ORDER BY name")
        if not jogos or not desafios:
            return await substituir_ou_responder(
                interaction, content="## ⚔️ Ritual de entrada\n\nAinda não há jogos e desafios cadastrados.",
                view=VoltarCentralView(self.cog),
            )
        view = RegistrarView(self.cog, jogos, desafios, parent_interaction=interaction)
        await substituir_ou_responder(
            interaction,
            content="## ⚔️ Ritual de entrada\n\nEscolha o jogo e o desafio. Depois, informe o tempo e a build; o comprovante será enviado por mensagem direta.",
            view=view,
        )

    @discord.ui.button(label="Hall da Fama", style=discord.ButtonStyle.primary, emoji="🏆", custom_id="central:ranking", row=0)
    async def ranking(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.cog.bot.db
        jogos = await db._all("SELECT * FROM sl_games ORDER BY name")
        desafios = await db._all("SELECT * FROM sl_challenges ORDER BY name")
        if not jogos or not desafios:
            return await substituir_ou_responder(
                interaction, content="## 🏆 Hall da Fama\n\nAinda não há jogos ou desafios cadastrados.",
                view=VoltarCentralView(self.cog),
            )
        g, c = jogos[0], desafios[0]
        await substituir_ou_responder(
            interaction, content=await self.cog.texto_ranking(g['id'], c['id']),
            view=RankingView(self.cog, jogos, desafios, g['id'], c['id']),
        )

    @discord.ui.button(label="Desafios", style=discord.ButtonStyle.secondary, emoji="📜", custom_id="central:challenges", row=1)
    async def desafios(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.mostrar_desafios(interaction)

    @discord.ui.button(label="Meu perfil", style=discord.ButtonStyle.secondary, emoji="🗡️", custom_id="central:profile", row=1)
    async def perfil(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.mostrar_perfil(interaction)


class RegistrarView(discord.ui.View):
    def __init__(self, cog, jogos, desafios, parent_interaction=None):
        super().__init__(timeout=300)
        self.cog = cog
        self.parent_interaction = parent_interaction
        self.jogos = jogos
        self.desafios = desafios
        self.game_id = jogos[0]['id']
        self.challenge_id = desafios[0]['id']
        self.game_page = 0
        self.challenge_page = 0
        self.game_select = discord.ui.Select(placeholder="1. Escolha o jogo", min_values=1, max_values=1, row=0)
        self.challenge_select = discord.ui.Select(placeholder="2. Escolha o desafio", min_values=1, max_values=1, row=1)
        self.game_select.callback = self._choose_game
        self.challenge_select.callback = self._choose_challenge
        self.add_item(self.game_select)
        self.add_item(self.challenge_select)
        self._refresh_options()

    def _refresh_options(self):
        self.game_select.options.clear()
        self.game_select.options.extend(
            discord.SelectOption(label=str(r['name'])[:100], value=str(r['id']), default=r['id'] == self.game_id)
            for r in self.jogos[self.game_page * 25:(self.game_page + 1) * 25]
        )
        self.challenge_select.options.clear()
        self.challenge_select.options.extend(
            discord.SelectOption(label=str(r['name'])[:100], value=str(r['id']), default=r['id'] == self.challenge_id)
            for r in self.desafios[self.challenge_page * 25:(self.challenge_page + 1) * 25]
        )
        # Paginação dos menus, respeitando o limite de 25 opções por select.
        for item in list(self.children):
            if isinstance(item, PageButton) or isinstance(item, VoltarCentralButton):
                self.remove_item(item)
        linhas_usadas = set()
        if len(self.jogos) > 25:
            self.add_item(PageButton(self, 'game', -1, row=2))
            self.add_item(PageButton(self, 'game', 1, row=2))
            linhas_usadas.add(2)
        if len(self.desafios) > 25:
            self.add_item(PageButton(self, 'challenge', -1, row=3))
            self.add_item(PageButton(self, 'challenge', 1, row=3))
            linhas_usadas.add(3)
        linha_voltar = next(linha for linha in (2, 3, 4) if linha not in linhas_usadas)
        self.add_item(VoltarCentralButton(self.cog, row=linha_voltar))

    async def _choose_game(self, interaction: discord.Interaction):
        self.game_id = int(self.game_select.values[0])
        self._refresh_options()
        await interaction.response.edit_message(view=self)

    async def _choose_challenge(self, interaction: discord.Interaction):
        self.challenge_id = int(self.challenge_select.values[0])
        g = await self.cog.bot.db._one("SELECT * FROM sl_games WHERE id=?", (self.game_id,))
        c = await self.cog.bot.db._one("SELECT * FROM sl_challenges WHERE id=?", (self.challenge_id,))
        if not g or not c:
            return await interaction.response.edit_message(
                content="⚠️ Jogo ou desafio não encontrado. Volte à central e tente novamente.",
                embeds=[], view=VoltarCentralView(self.cog),
            )
        await interaction.response.send_modal(RunDadosModal(self.cog, g['id'], c['id'], parent_interaction=self.parent_interaction or interaction))


class PageButton(discord.ui.Button):
    def __init__(self, parent, kind, delta, row):
        self.parent_view = parent
        self.kind = kind
        self.delta = delta
        label = "Anterior" if delta < 0 else "Próxima"
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row,
                         custom_id=f"central:page:{kind}:{delta}:{id(parent)}")

    async def callback(self, interaction: discord.Interaction):
        rows = self.parent_view.jogos if self.kind == 'game' else self.parent_view.desafios
        page_attr = 'game_page' if self.kind == 'game' else 'challenge_page'
        new_page = getattr(self.parent_view, page_attr) + self.delta
        max_page = (len(rows) - 1) // 25
        setattr(self.parent_view, page_attr, max(0, min(max_page, new_page)))
        self.parent_view._refresh_options()
        await interaction.response.edit_message(view=self.parent_view)


class RunDadosModal(discord.ui.Modal, title="Registrar run Soulslike"):
    tempo = discord.ui.TextInput(label="Tempo da run", placeholder="Ex.: 1:30:45 ou 1h30m", max_length=30)
    build = discord.ui.TextInput(label="Build / classe / arma (opcional)", required=False, default="Não informada", max_length=100)

    def __init__(self, cog, game_id: int, challenge_id: int, parent_interaction=None):
        super().__init__(timeout=300)
        self.cog = cog
        self.game_id = game_id
        self.challenge_id = challenge_id
        self.parent_interaction = parent_interaction

    async def on_submit(self, interaction: discord.Interaction):
        seg = parse_tempo(str(self.tempo))
        if seg is None:
            return await interaction.response.send_message(AJUDA_TEMPO, ephemeral=True)
        g = await self.cog.bot.db._one("SELECT * FROM sl_games WHERE id=?", (self.game_id,))
        c = await self.cog.bot.db._one("SELECT * FROM sl_challenges WHERE id=?", (self.challenge_id,))
        if not g or not c:
            return await interaction.response.send_message("O jogo ou desafio não está mais disponível. Reabra a Central Soulslike.", ephemeral=True)
        if interaction.user.id in self.cog.pending_uploads:
            return await interaction.response.send_message(
                "Você já tem um registro aguardando comprovante. Conclua ou reinicie esse envio antes de abrir outro.",
                ephemeral=True,
            )
        self.cog.pending_uploads[interaction.user.id] = {
            'game_id': self.game_id, 'challenge_id': self.challenge_id, 'seconds': seg,
            'build': (str(self.build).strip() or 'Não informada')[:100],
        }
        try:
            dm = await interaction.user.create_dm()
            await dm.send(
                f"**Ritual de entrada — etapa final**\nJogo: **{g['name']}**\nDesafio: **{c['name']}**\n"
                f"Tempo: **{fmt_tempo(seg)}**\n\nEnvie nesta conversa uma imagem ou vídeo como comprovante. "
                "O bot apresentará uma prévia para você confirmar antes de enviar à moderação. Limite: 20 MB."
            )
        except discord.Forbidden:
            self.cog.pending_uploads.pop(interaction.user.id, None)
            return await interaction.response.send_message(
                "Não consigo enviar DM para você. Ative mensagens diretas deste servidor e tente novamente.", ephemeral=True
            )
        aviso = (
            "## ✅ Etapa final do registro\n\n"
            "Enviei uma mensagem direta para você. Anexe nela a imagem ou o vídeo de comprovante da run.\n\n"
            "_Esta tela foi atualizada; você não precisa abrir outro painel._"
        )
        if self.parent_interaction is not None:
            await interaction.response.defer(ephemeral=True, thinking=True)
            try:
                await self.parent_interaction.edit_original_response(
                    content=aviso, embeds=[], view=VoltarCentralView(self.cog),
                )
            except discord.HTTPException:
                # Se o token anterior expirou, preserva a confirmação no fluxo atual.
                await interaction.edit_original_response(content=aviso, embeds=[], view=VoltarCentralView(self.cog))
            else:
                try:
                    await interaction.delete_original_response()
                except discord.HTTPException:
                    pass  # A tela principal já foi atualizada; não duplica a confirmação.
        else:
            await interaction.response.send_message(aviso, ephemeral=True)


class PerfilView(discord.ui.View):
    def __init__(self, cog, rows):
        super().__init__(timeout=300)
        self.cog = cog
        pendentes = [r for r in rows if r['status'] == 'pending']
        if pendentes:
            self.add_item(CancelarRunButton(cog, pendentes[0]['id']))


class CancelarRunButton(discord.ui.Button):
    def __init__(self, cog, run_id):
        self.cog = cog
        self.run_id = run_id
        super().__init__(label=f"Cancelar run #{run_id}", style=discord.ButtonStyle.danger, emoji="✕")

    async def callback(self, interaction: discord.Interaction):
        db = self.cog.bot.db
        cur = await db.conn.execute(
            "UPDATE sl_runs SET status='cancelled' WHERE id=? AND user_id=? AND status='pending'",
            (self.run_id, interaction.user.id),
        )
        await db.conn.commit()
        if cur.rowcount != 1:
            return await interaction.response.send_message("A run não está mais pendente ou não pertence a você.", ephemeral=True)
        run = await db._one("SELECT proof_msg_id FROM sl_runs WHERE id=?", (self.run_id,))
        mod_ch_id = await GuildConfig.get(db, interaction.guild_id, "mod_channel") or config.MOD_CHANNEL_ID
        canal = await get_text_channel(self.cog.bot, mod_ch_id)
        if canal and run and run['proof_msg_id']:
            try:
                msg = await canal.fetch_message(run['proof_msg_id'])
                if msg.embeds:
                    embed = msg.embeds[0]
                    embed.color = discord.Color.dark_grey()
                    embed.add_field(name="Resultado", value="Cancelada pelo autor", inline=False)
                    await msg.edit(embed=embed, view=None)
            except discord.HTTPException:
                pass
        await db.log(interaction.user.id, "run_cancelada", f"id={self.run_id}")
        embed_atual = interaction.message.embeds[0] if interaction.message.embeds else None
        if embed_atual is not None and embed_atual.description:
            blocos = embed_atual.description.split("\n\n")
            for indice, bloco in enumerate(blocos):
                if f"`#{self.run_id}`" in bloco:
                    blocos[indice] = bloco.replace("⏳ Pendente", "— Cancelada")
                    break
            embed_atual.description = "\n\n".join(blocos)
        if self.view is not None:
            self.view.remove_item(self)
        if embed_atual is not None:
            await interaction.response.edit_message(embed=embed_atual, view=self.view)
        else:
            await interaction.response.edit_message(content=f"✅ Run `#{self.run_id}` cancelada.", view=self.view)


class ConfirmarView(discord.ui.View):
    def __init__(self, cog, user, g, c, seg, build, dados, filename):
        super().__init__(timeout=180)
        self.cog, self.user, self.g, self.c = cog, user, g, c
        self.seg, self.build, self.dados, self.filename = seg, build, dados, filename

    @discord.ui.button(label="Confirmar e enviar", style=discord.ButtonStyle.success, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="⏳ Enviando para a moderação...", embed=None, view=None)
        run_id = await self.cog.enviar_para_moderacao(self.user, self.g, self.c, self.seg, self.build, self.dados, self.filename)
        if run_id is None:
            return await interaction.edit_original_response(
                content="Não consegui enviar para a moderação. Avise um administrador (canal de aprovação não configurado ou sem permissão)."
            )
        await interaction.edit_original_response(
            content=f"✅ Run enviada para a moderação! Número `#{run_id}`. Acompanhe pelo botão **Meu perfil** na Central Soulslike."
        )
        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Registro cancelado. Nada foi enviado.", embed=None, view=None)
        self.stop()


class RevisaoRunView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, custom_id="sl:approve")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.aprovar(interaction)

    @discord.ui.button(label="Rejeitar", style=discord.ButtonStyle.danger, custom_id="sl:reject")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.rejeitar(interaction)


class MotivoModal(discord.ui.Modal, title="Rejeitar run"):
    motivo = discord.ui.TextInput(
        label="Motivo (a pessoa vai receber isso)",
        style=discord.TextStyle.paragraph,
        max_length=300,
        placeholder="Ex.: o print não mostra o tempo de jogo.",
    )

    def __init__(self, cog, run_id: int):
        super().__init__()
        self.cog, self.run_id = cog, run_id

    async def on_submit(self, interaction: discord.Interaction):
        db = self.cog.bot.db
        run = await db._one("SELECT * FROM sl_runs WHERE id=?", (self.run_id,))
        if run is None or run["status"] != "pending":
            return await interaction.response.send_message("Este registro já foi processado.", ephemeral=True)
        cur = await db.conn.execute(
            "UPDATE sl_runs SET status='rejected', reviewer_id=?, reject_reason=? WHERE id=? AND status='pending'",
            (interaction.user.id, str(self.motivo), self.run_id),
        )
        await db.conn.commit()
        if cur.rowcount != 1:
            return await interaction.response.send_message("Esta run já foi processada por outro moderador.", ephemeral=True)
        await db.log(interaction.user.id, "run_rejeitada", f"id={self.run_id} motivo={self.motivo}")
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Resultado", value=f"❌ Rejeitada por {interaction.user.mention}\nMotivo: {self.motivo}", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        try:
            user = self.cog.bot.get_user(run["user_id"]) or await self.cog.bot.fetch_user(run["user_id"])
            await user.send(f"Sua run `#{self.run_id}` foi rejeitada.\nMotivo: {self.motivo}\nVocê pode enviar novamente pela Central Soulslike no servidor.")
        except discord.HTTPException:
            pass


class RankingView(discord.ui.View):
    def __init__(self, cog, jogos, desafios, game_id, chal_id):
        super().__init__(timeout=600)
        self.cog, self.game_id, self.chal_id = cog, game_id, chal_id
        self.sel_jogo = discord.ui.Select(
            placeholder="Jogo",
            options=[discord.SelectOption(label=j["name"], value=str(j["id"]), default=j["id"] == game_id) for j in jogos[:25]],
        )
        self.sel_desafio = discord.ui.Select(
            placeholder="Desafio",
            options=[discord.SelectOption(label=c["name"], value=str(c["id"]), default=c["id"] == chal_id) for c in desafios[:25]],
        )
        self.sel_jogo.callback = self.trocar_jogo
        self.sel_desafio.callback = self.trocar_desafio
        self.add_item(self.sel_jogo)
        self.add_item(self.sel_desafio)
        self.add_item(VoltarCentralButton(cog, row=2))

    async def _atualizar(self, interaction: discord.Interaction):
        for o in self.sel_jogo.options:
            o.default = o.value == str(self.game_id)
        for o in self.sel_desafio.options:
            o.default = o.value == str(self.chal_id)
        await interaction.response.edit_message(content=await self.cog.texto_ranking(self.game_id, self.chal_id), embeds=[], view=self)

    async def trocar_jogo(self, interaction: discord.Interaction):
        self.game_id = int(self.sel_jogo.values[0])
        await self._atualizar(interaction)

    async def trocar_desafio(self, interaction: discord.Interaction):
        self.chal_id = int(self.sel_desafio.values[0])
        await self._atualizar(interaction)


# Registrar run e ranking são botões da CentralView, não comandos slash.
# Autocomplete não se aplica a callbacks de botões.


async def setup(bot):
    await bot.add_cog(Soulslike(bot))
