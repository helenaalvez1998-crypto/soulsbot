import asyncio
import io
import logging
import re
import time

import discord
from discord import app_commands
from discord.ext import commands

import config
from admin_config import GuildConfig
from utils import get_text_channel, upsert_panel
from cogs.comum import NotaJogoView, formatar_dificuldade

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
PENDING_UPLOAD_TTL = 10 * 60  # evita bloquear o usuário indefinidamente se ele não anexar comprovante


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

    async def _posicao(self, game_id, chal_id, seg, user_id) -> int:
        row = await self.bot.db._one(SQL_POSICAO, (game_id, chal_id, seg, user_id))
        return row["c"] + 1

    async def texto_ranking(self, game_id: int, chal_id: int) -> str:
        db = self.bot.db
        g = await db._one("SELECT * FROM sl_games WHERE id=?", (game_id,))
        c = await db._one("SELECT * FROM sl_challenges WHERE id=?", (chal_id,))
        if not g or not c:
            return "## ⚔️ Hall da Fama\n\nJogo ou desafio não encontrado. Atualize a central."
        if c["game_id"] is not None and int(c["game_id"]) != int(game_id):
            return "## ⚔️ Hall da Fama\n\nEste desafio pertence a outro jogo. Escolha um desafio compatível."
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
    async def enviar_para_moderacao(self, user, g, c, seg, build, dados, filename,
                                    nota: int | None = None, comentario: str = "",
                                    dificuldade: int | None = None):
        db = self.bot.db
        mod_ch_id = await GuildConfig.get(db, user.guild.id if hasattr(user, 'guild') and user.guild else 0, "mod_channel")
        canal = await get_text_channel(self.bot, mod_ch_id)
        if canal is None:
            return None
        if nota is not None and (type(nota) is not int or not 1 <= nota <= 10):
            return None
        if dificuldade is not None and (type(dificuldade) is not int or not 1 <= dificuldade <= 5):
            return None
        cur = await db.conn.execute(
            "INSERT INTO sl_runs(user_id, game_id, challenge_id, build, seconds, rating, difficulty, comment) VALUES (?,?,?,?,?,?,?,?)",
            (user.id, g["id"], c["id"], build, seg, nota, dificuldade, str(comentario or "")[:500]),
        )
        await db.conn.commit()
        run_id = cur.lastrowid

        try:
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
            if nota is not None:
                embed.add_field(name="Nota do jogo", value=f"⭐ {int(nota)}/10")
            if dificuldade is not None:
                embed.add_field(name="Dificuldade percebida", value=formatar_dificuldade(dificuldade))
            if str(comentario or "").strip():
                embed.add_field(name="Comentário", value=str(comentario).strip()[:500], inline=False)
            embed.add_field(name="Posição", value=ref)
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
                embed.set_image(url=f"attachment://{filename}")
            embed.set_footer(text=f"SL:{run_id}")
        except Exception:
            log.exception("Falha preparando card da run #%s; removendo registro incompleto", run_id)
            try:
                await db.conn.execute("DELETE FROM sl_runs WHERE id=? AND status='pending'", (run_id,))
                await db.conn.commit()
            except Exception:
                log.exception("Falha ao limpar run #%s após erro de preparação", run_id)
            return None
        try:
            msg = await canal.send(
                embed=embed,
                file=discord.File(io.BytesIO(dados), filename=filename),
                view=RevisaoRunView(self),
            )
        except Exception:
            log.exception("Falha ao enviar comprovante da run #%s à moderação", run_id)
            try:
                await db.conn.execute("DELETE FROM sl_runs WHERE id=? AND status='pending'", (run_id,))
                await db.conn.commit()
            except Exception:
                log.exception("Falha ao limpar run #%s após erro de envio", run_id)
            return None
        try:
            url = msg.embeds[0].image.url if msg.embeds and msg.embeds[0].image else ""
            cur = await db.conn.execute(
                "UPDATE sl_runs SET proof_msg_id=?, proof_url=? WHERE id=? AND status='pending'",
                (msg.id, url, run_id),
            )
            await db.conn.commit()
            if cur.rowcount != 1:
                raise RuntimeError("O registro de run deixou de existir durante o envio do comprovante.")
        except Exception:
            log.exception("Falha ao vincular comprovante à run #%s; removendo registro e mensagem", run_id)
            try:
                await msg.delete()
            except discord.HTTPException:
                log.exception("Falha ao apagar mensagem órfã da run #%s", run_id)
            try:
                await db.conn.execute("DELETE FROM sl_runs WHERE id=? AND status='pending'", (run_id,))
                await db.conn.commit()
            except Exception:
                log.exception("Falha ao limpar run incompleta #%s", run_id)
            return None
        try:
            await db.log(user.id, "run_registrada", f"id={run_id} {g['name']}/{c['name']} {fmt_tempo(seg)}")
        except Exception:
            log.exception("Run #%s registrada, mas falhou o log de auditoria", run_id)
        return run_id

    async def iniciar_upload_run(self, interaction: discord.Interaction, game_id: int,
                                 challenge_id: int, segundos: int, build: str,
                                 nota: int, comentario: str, dificuldade: int):
        """Salva a avaliação temporária e solicita o comprovante por DM."""
        if type(nota) is not int or not 1 <= nota <= 10:
            return await interaction.response.send_message("Escolha uma nota entre 1 e 10.", ephemeral=True)
        if type(dificuldade) is not int or not 1 <= dificuldade <= 5:
            return await interaction.response.send_message("Escolha uma dificuldade entre 1 e 5.", ephemeral=True)
        state = self.pending_uploads.get(interaction.user.id)
        if state and time.monotonic() - float(state.get("created_at", 0)) <= PENDING_UPLOAD_TTL:
            return await interaction.response.send_message(
                "Você já tem um registro aguardando comprovante. Conclua esse envio ou aguarde o prazo de 10 minutos antes de iniciar outro.",
                ephemeral=True,
            )
        g = await self.bot.db._one("SELECT * FROM sl_games WHERE id=?", (int(game_id),))
        c = await self.bot.db._one("SELECT * FROM sl_challenges WHERE id=?", (int(challenge_id),))
        if not g or not c:
            return await interaction.response.send_message(
                "O jogo ou desafio não está mais disponível. Reabra a Central Soulslike.", ephemeral=True
            )
        self.pending_uploads[interaction.user.id] = {
            'game_id': int(game_id), 'challenge_id': int(challenge_id), 'seconds': int(segundos),
            'build': str(build or 'Não informada')[:100], 'rating': int(nota),
            'difficulty': int(dificuldade), 'comment': str(comentario or '').strip()[:500],
            'created_at': time.monotonic(),
        }
        try:
            dm = await interaction.user.create_dm()
            await dm.send(
                f"**Ritual de entrada — etapa final**\nJogo: **{g['name']}**\nDesafio: **{c['name']}**\n"
                f"Tempo: **{fmt_tempo(segundos)}**\nNota do jogo: **{int(nota)}/10**\n"
                f"Dificuldade percebida: **{formatar_dificuldade(dificuldade)}**\n\n"
                f"Envie nesta conversa uma imagem ou vídeo como comprovante. "
                "O bot apresentará uma prévia para você confirmar antes de enviar à moderação. Limite: 20 MB."
            )
        except discord.Forbidden:
            self.pending_uploads.pop(interaction.user.id, None)
            return await interaction.response.send_message(
                "Não consigo enviar DM para você. Ative mensagens diretas deste servidor e tente novamente.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            "## ✅ Etapa final do registro\n\n"
            "Enviei uma mensagem direta para você. Anexe nela a imagem ou o vídeo de comprovante da run.\n\n"
            "_Esta tela foi atualizada; você não precisa abrir outro painel._",
            ephemeral=True,
            view=VoltarCentralView(self),
        )

    # -------------------------------------------------------- central Soulslike
    def texto_central(self) -> str:
        return (
            "# ⛧ SOULSLIKE · THE HALL OF THE FALLEN\n\n"
            "**A chama está acesa.** Registre suas runs, consulte recordes e acompanhe sua jornada. A arena não perdoa descuido, então confira as regras antes de enviar.\n\n"
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
                "Registre suas runs, consulte os recordes e acompanhe sua jornada. Confira as regras antes de entrar na arena.\n\n"
                "Escolha uma opção nos botões abaixo. Suas submissões são encaminhadas à moderação."
            ),
            color=config.COR_OURO,
        )
        e.add_field(name="⚔️ Registro de run", value="Jogo, desafio, tempo, build e comprovante.", inline=True)
        e.add_field(name="🏆 Hall da Fama", value="Melhores tempos por jogo e desafio.", inline=True)
        e.add_field(name="📜 Livro dos Desafios", value="Consulte regras e categorias disponíveis.", inline=True)
        e.add_field(name="🗡️ Meu perfil", value="Histórico, status e runs pendentes.", inline=True)
        e.set_footer(text="Cada run deixa uma marca. Só as aprovadas entram no ranking.")
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
        desafios = await self.bot.db._all(
            "SELECT c.*,g.name AS game_name FROM sl_challenges c LEFT JOIN sl_games g ON g.id=c.game_id ORDER BY g.name,c.name"
        )
        if not jogos or not desafios:
            motivo = "Ainda não existem jogos cadastrados." if not jogos else "Ainda não existem desafios cadastrados."
            return await substituir_ou_responder(
                interaction,
                content=f"## 📜 Livro dos Desafios\n\n{motivo} Use os botões abaixo para sugerir o que está faltando, sem sair desta tela.",
                view=VoltarCentralView(self),
            )
        lines = ["## 📜 Livro dos Desafios", ""]
        for c in desafios[:15]:
            regras = c['rules'] or 'Sem regras adicionais cadastradas.'
            escopo = c["game_name"] or "Global"
            lines.append(f"**{c['name']}** · _{escopo}_\n{regras[:220]}")
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
        if time.monotonic() - float(state.get("created_at", 0)) > PENDING_UPLOAD_TTL:
            self.pending_uploads.pop(message.author.id, None)
            return await message.channel.send(
                "Esse envio de comprovante expirou após 10 minutos. Abra a Central Soulslike e inicie uma nova run."
            )
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
            if state.get("rating") is not None:
                prev.append(f"**Nota do jogo:** ⭐ {int(state['rating'])}/10")
            if state.get("difficulty") is not None:
                prev.append(f"**Dificuldade percebida:** {formatar_dificuldade(state['difficulty'])}")
            if str(state.get("comment") or "").strip():
                prev.append(f"**Comentário:** {str(state['comment']).strip()[:500]}")
            if c['rules']:
                prev.extend(["", f"**Regras do desafio:** {c['rules'][:700]}"])
            prev.extend(["", "_Confirme para enviar o comprovante à moderação._"])
            view = ConfirmarView(
                self, message.author, g, c, seg, state['build'], data,
                attachment.filename[:100], state.get("rating"), state.get("comment", ""),
                state.get("difficulty"),
            )
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

    @sl_admin.command(name="recompensa_desafio", description="[MOD] Configura chance de Primordial e Singular de um desafio Soulslike.")
    @app_commands.describe(
        desafio_id="ID do desafio exibido no cadastro/registro",
        permitir_primordial="Habilita chance de 0,1% de drop Primordial nas runs aprovadas",
        singular="Carta Singular concedida ao aprovar uma run deste desafio",
    )
    @app_commands.choices(singular=[
        app_commands.Choice(name="Nenhuma Singular", value="none"),
        app_commands.Choice(name="O Primeiro Juramento", value="gwent_singular_primeiro"),
        app_commands.Choice(name="A Lâmina Intocada (No-hit)", value="gwent_singular_intocavel"),
        app_commands.Choice(name="A Vontade Inquebrável (Nível 1)", value="gwent_singular_nivel1"),
        app_commands.Choice(name="A Coroa dos Vencidos (Todos os chefes)", value="gwent_singular_cacador_chefes"),
    ])
    async def recompensa_desafio(
        self,
        interaction: discord.Interaction,
        desafio_id: int,
        permitir_primordial: bool,
        singular: app_commands.Choice[str],
    ):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas moderadores com Gerenciar servidor.", ephemeral=True)
        desafio = await self.bot.db._one("SELECT id,name FROM sl_challenges WHERE id=?", (int(desafio_id),))
        if not desafio:
            return await interaction.response.send_message("Desafio não encontrado.", ephemeral=True)
        singular_id = singular.value
        await self.bot.db.conn.execute(
            "UPDATE sl_challenges SET coliseu_primordial_drop=?,coliseu_singular_card_id=? WHERE id=?",
            (int(bool(permitir_primordial)), singular_id, int(desafio_id)),
        )
        await self.bot.db.conn.commit()
        await self.bot.db.log(
            interaction.user.id,
            "sl_recompensa_desafio_configurada",
            f"challenge={desafio_id};primordial={int(bool(permitir_primordial))};singular={singular_id or 'nenhuma'}",
        )
        resumo = "Primordial: chance de 0,1% habilitada" if permitir_primordial else "Primordial: desabilitada"
        resumo += f"\nSingular: {singular.name}"
        await interaction.response.send_message(
            f"Recompensas do desafio **{desafio['name']}** atualizadas.\n{resumo}", ephemeral=True
        )

    @sl_admin.command(name="recompensas_listar", description="[MOD] Lista IDs e recompensas configuradas dos desafios Soulslike.")
    async def recompensas_listar(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Apenas moderadores com Gerenciar servidor.", ephemeral=True)
        rows = await self.bot.db._all(
            "SELECT id,name,coliseu_primordial_drop,coliseu_singular_card_id FROM sl_challenges ORDER BY name LIMIT 80"
        )
        if not rows:
            return await interaction.response.send_message("Nenhum desafio cadastrado.", ephemeral=True)
        linhas = ["**ID · Desafio · Recompensas**"]
        for row in rows:
            cfg = int(row["coliseu_primordial_drop"] if row["coliseu_primordial_drop"] is not None else -1)
            primordial = "Primordial 0,1%" if cfg == 1 else "Primordial desativada" if cfg == 0 else "Primordial automática"
            singular = str(row["coliseu_singular_card_id"] or "")
            singular_label = singular.replace("gwent_singular_", "") if singular and singular != "none" else "nenhuma" if singular == "none" else "automática"
            linhas.append(f"`{row['id']}` · **{row['name']}** — {primordial}; Singular: {singular_label}")
        await interaction.response.send_message("\n".join(linhas)[:1900], ephemeral=True)

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
        try:
            await db.log(interaction.user.id, "run_invalidada", f"id={numero} motivo={motivo}")
        except Exception:
            log.exception("Run #%s invalidada, mas falhou o log de auditoria", numero)
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
        # Status, XP base e bônus de recorde são confirmados juntos. Isso impede que
        # uma falha entre UPDATE e add_reward gere aprovação sem recompensa (ou bônus duplicado).
        resultado = await db.aprovar_run_com_recompensa(run["id"], interaction.user.id)
        if resultado is None:
            return await interaction.response.send_message(
                "Esta run já foi processada por outro moderador.", ephemeral=True
            )
        # A consulta prévia contém os aliases de exibição (jogo/desafio); preserva-os
        # e mescla o estado transacional confirmado pelo banco.
        run = {**dict(run), **resultado["run"]}
        try:
            from cogs.comum import sincronizar_cartao
            await sincronizar_cartao(self.bot, interaction.guild_id, "runs", int(run["id"]), "approved", interaction.user.id)
        except Exception:
            log.exception("Falha ao sincronizar cartão original da run #%s", run["id"])
        try:
            await db.log(interaction.user.id, "run_aprovada", f"id={run['id']} user={run['user_id']}; xp={resultado['xp_awarded']}")
        except Exception:
            log.exception("Run #%s aprovada e recompensada, mas falhou o log de auditoria", run["id"])

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Resultado", value=f"✅ Aprovada por {interaction.user.mention}", inline=False)
        try:
            await interaction.response.edit_message(embed=embed, view=None)
        except discord.HTTPException:
            log.exception("Run #%s aprovada, mas a mensagem de revisão não pôde ser atualizada", run["id"])
            try:
                await interaction.followup.send(
                    f"A run `#{run['id']}` foi aprovada e a recompensa foi creditada, mas a mensagem antiga não pôde ser atualizada.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                pass

        progressao = self.bot.get_cog("ProgressaoXP")
        if progressao:
            try:
                await progressao.notificar_recompensa(
                    interaction.guild, run["user_id"], resultado["old_level"],
                    resultado["new_level"], resultado["xp_awarded"],
                    "run aprovada e novo recorde" if resultado["is_record"] else "run aprovada",
                )
            except Exception:
                log.exception("Run #%s aprovada; falha ao atualizar efeitos de patente", run["id"])

        melhorou = resultado["improved_personal"]
        tempo_no_ranking = run["seconds"] if melhorou else resultado["previous_personal_best"]
        try:
            pos = await self._posicao(run["game_id"], run["challenge_id"], tempo_no_ranking, run["user_id"])
        except Exception:
            log.exception("Run #%s aprovada; falha ao calcular posição atual no ranking", run["id"])
            pos = "—"
        vezes = resultado["approved_count_before"] + 1

        try:
            canal_id = await GuildConfig.get(db, interaction.guild_id, "soulslike_channel")
            canal = await get_text_channel(self.bot, canal_id) if canal_id else None
            if canal:
                if resultado["is_record"]:
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
                    f"**Recompensa:** +{resultado['xp_awarded']} XP",
                ]
                if resultado.get("card_outcome") == "carta":
                    linhas.append(f"🃏 **Drop:** {resultado.get('card_name')} · {resultado.get('card_rarity')}")
                elif resultado.get("card_outcome") == "almas":
                    linhas.append(f"✨ **Duplicata:** +{resultado.get('card_almas', 0)} Almas")
                elif resultado.get("card_outcome") == "fragmentos":
                    linhas.append(f"🧩 **Duplicata:** +{resultado.get('card_fragmentos', 0)} fragmentos")
                if (resultado.get("singular_drop") or {}).get("outcome") == "singular":
                    nome_singular = (resultado.get("singular_drop") or {}).get("card_name", "uma carta Singular")
                    linhas.append(f"🌟 **Feito extraordinário: {nome_singular} (Singular) conquistada!**")
                if run["rating"] is not None:
                    linhas.insert(4, f"**Nota do jogo:** ⭐ {int(run['rating'])}/10")
                if run["difficulty"] is not None:
                    pos_dificuldade = 5 if run["rating"] is not None else 4
                    linhas.insert(pos_dificuldade, f"**Dificuldade percebida:** {formatar_dificuldade(run['difficulty'])}")
                if str(run["comment"] or "").strip():
                    pos_comentario = 4 + int(run["rating"] is not None) + int(run["difficulty"] is not None)
                    linhas.insert(pos_comentario,
                                  f"**Comentário:** {str(run['comment']).strip()[:500]}")
                if run["proof_url"]:
                    linhas.append(f"[📸 Ver comprovante]({run['proof_url']})")
                if vezes > 1:
                    linhas.append(f"**Runs concluídas:** 🔁 {vezes}x")
                mensagem_publica = await canal.send("\n".join(linhas), allowed_mentions=discord.AllowedMentions.none())
                comunidade = self.bot.get_cog("Comunidade")
                if comunidade:
                    try:
                        await comunidade.registrar_publicacao_social(
                            interaction.guild, canal, mensagem_publica, "run", int(run["id"]), int(run["user_id"])
                        )
                    except Exception:
                        log.exception("Run #%s publicada, mas as interações sociais não foram anexadas", run["id"])
        except Exception:
            log.exception("Run #%s aprovada, mas falhou a publicação no canal Soulslike", run["id"])
        from utils import notificar_usuario
        await notificar_usuario(
            self.bot, interaction.guild_id, int(run["user_id"]), "approvals",
            f"✅ Sua run de **{run['jogo']} — {run['desafio']}** foi aprovada. "
            f"Tempo registrado: {fmt_tempo(run['seconds'])}. Recompensa: +{resultado['xp_awarded']} XP. "
            + (f"Drop: **{resultado.get('card_name')}** ({resultado.get('card_rarity')})."
               if resultado.get("card_outcome") == "carta" else
               "A duplicata virou recursos." if resultado.get("card_outcome") in ("almas", "fragmentos") else "")
            + (" Você também conquistou uma carta Singular!" if (resultado.get("singular_drop") or {}).get("outcome") == "singular" else "")
        )

    async def rejeitar(self, interaction: discord.Interaction):
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        run = await self.carregar_run(interaction)
        if run is None:
            return
        await interaction.response.send_modal(MotivoModal(self, run["id"]))


# ------------------------------------------------------------------ views
def _callback_nara_soulslike(cog, user_id: int | None):
    if user_id is None:
        return None
    return getattr(cog, "_retornos_nara", {}).get(int(user_id))


class VoltarCentralView(discord.ui.View):
    """Estado vazio do Soulslike: mantém o caminho de volta e oferece ações contextuais."""
    def __init__(self, cog, callback_voltar=None):
        super().__init__(timeout=600)
        self.cog = cog
        self.callback_voltar = callback_voltar
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar", emoji="↩️")
        from cogs.comunidade import adicionar_botao_contribuicao_contextual
        adicionar_botao_contribuicao_contextual(
            self, "game_suggestion", "runs", "Sugerir jogo ausente", "🎮", row=1,
            style=discord.ButtonStyle.success,
        )
        adicionar_botao_contribuicao_contextual(
            self, "challenge", "runs", "Propor desafio", "⚔️", row=1,
            style=discord.ButtonStyle.primary,
        )

    @discord.ui.button(label="Voltar à central", emoji="↩️", style=discord.ButtonStyle.secondary, row=0)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        callback = self.callback_voltar or _callback_nara_soulslike(self.cog, interaction.user.id)
        await interaction.response.edit_message(content=self.cog.texto_central(), embeds=[], view=CentralView(self.cog, callback_voltar=callback, user_id=interaction.user.id))


class VoltarCentralButton(discord.ui.Button):
    def __init__(self, cog, row=1, callback_voltar=None):
        self.cog = cog
        self.callback_voltar = callback_voltar
        super().__init__(label="Voltar à central", emoji="↩️", style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction):
        callback = self.callback_voltar or _callback_nara_soulslike(self.cog, interaction.user.id)
        await interaction.response.edit_message(content=self.cog.texto_central(), embeds=[], view=CentralView(self.cog, callback_voltar=callback, user_id=interaction.user.id))


class CentralView(discord.ui.View):
    """Central de runs; no fluxo privado mantém retorno à Nara sem alterar a versão pública persistente."""
    def __init__(self, cog, callback_voltar=None, user_id: int | None = None):
        super().__init__(timeout=None if callback_voltar is None else 600)
        self.cog = cog
        self.callback_voltar = callback_voltar
        if callback_voltar is not None and user_id is not None:
            if not hasattr(cog, "_retornos_nara"):
                cog._retornos_nara = {}
            cog._retornos_nara[int(user_id)] = callback_voltar
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar", emoji="↩️")
        from cogs.comunidade import adicionar_botao_contribuicao_contextual
        adicionar_botao_contribuicao_contextual(
            self, "game_suggestion", "runs", "Sugerir jogo ausente", "🎮", row=2,
            style=discord.ButtonStyle.success,
        )
        adicionar_botao_contribuicao_contextual(
            self, "challenge", "runs", "Propor desafio", "⚔️", row=2,
            style=discord.ButtonStyle.primary,
        )

    @discord.ui.button(label="Registrar run", style=discord.ButtonStyle.danger, emoji="⚔️", custom_id="central:register", row=0)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        jogos = await self.cog.bot.db._all("SELECT * FROM sl_games ORDER BY name")
        desafios = await self.cog.bot.db._all("SELECT * FROM sl_challenges ORDER BY name")
        if not jogos:
            return await substituir_ou_responder(
                interaction,
                content="## ⚔️ Ritual de entrada\n\nAinda não há jogos cadastrados. Você pode sugerir um jogo diretamente nesta tela; a equipe revisará a inclusão.",
                view=VoltarCentralView(self.cog, self.callback_voltar),
            )
        view = RegistrarView(self.cog, jogos, desafios, parent_interaction=interaction)
        orientacao = (
            "Ainda não há desafios cadastrados. Use **Sugerir desafio** nesta mesma tela para propor o primeiro."
            if not desafios else
            "Escolha o jogo e o desafio. Se não encontrar um desafio compatível, use **Sugerir desafio** aqui mesmo."
        )
        await substituir_ou_responder(
            interaction,
            content=("## ⚔️ Ritual de entrada\n\n" + orientacao +
                     " Depois, informe o tempo e a build; o comprovante será enviado por mensagem direta."),
            view=view,
        )

    @discord.ui.button(label="Hall da Fama", style=discord.ButtonStyle.primary, emoji="🏆", custom_id="central:ranking", row=0)
    async def ranking(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.cog.bot.db
        jogos = await db._all("SELECT * FROM sl_games ORDER BY name")
        desafios = await db._all("SELECT * FROM sl_challenges ORDER BY name")
        if not jogos or not desafios:
            motivo = "Ainda não há jogos cadastrados." if not jogos else "Ainda não há desafios cadastrados."
            return await substituir_ou_responder(
                interaction, content=f"## 🏆 Hall da Fama\n\n{motivo} Você pode sugerir o conteúdo que está faltando nesta mesma tela.",
                view=VoltarCentralView(self.cog, self.callback_voltar),
            )
        g = jogos[0]
        desafios_compativeis = [c for c in desafios if c["game_id"] is None or int(c["game_id"]) == int(g["id"])]
        if not desafios_compativeis:
            return await substituir_ou_responder(interaction, content="## 🏆 Hall da Fama\n\nEste jogo ainda não possui desafios compatíveis.", view=VoltarCentralView(self.cog, self.callback_voltar))
        c = desafios_compativeis[0]
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
        self.todos_desafios = desafios
        self.game_id = int(jogos[0]['id'])
        self.challenge_id = None
        self.game_page = 0
        self.challenge_page = 0
        self.desafios = []
        self.game_select = discord.ui.Select(placeholder="1. Escolha o jogo", min_values=1, max_values=1, row=0)
        self.challenge_select = discord.ui.Select(placeholder="2. Escolha o desafio compatível", min_values=1, max_values=1, row=1)
        self.game_select.callback = self._choose_game
        self.challenge_select.callback = self._choose_challenge
        self.add_item(self.game_select)
        self.add_item(self.challenge_select)
        self._filtrar_desafios()
        self._refresh_options()

    def _filtrar_desafios(self):
        self.desafios = [
            row for row in self.todos_desafios
            if row["game_id"] is None or int(row["game_id"]) == self.game_id
        ]
        ids = {int(row["id"]) for row in self.desafios}
        if self.challenge_id not in ids:
            self.challenge_id = int(self.desafios[0]["id"]) if self.desafios else None
        self.challenge_page = min(self.challenge_page, max(0, (len(self.desafios) - 1) // 25))

    def _refresh_options(self):
        self.game_select.options.clear()
        self.game_select.options.extend(
            discord.SelectOption(label=str(r['name'])[:100], value=str(r['id']), default=int(r['id']) == self.game_id)
            for r in self.jogos[self.game_page * 25:(self.game_page + 1) * 25]
        )
        self.challenge_select.options.clear()
        if self.desafios:
            self.challenge_select.options.extend(
                discord.SelectOption(label=str(r['name'])[:100], value=str(r['id']), default=int(r['id']) == self.challenge_id)
                for r in self.desafios[self.challenge_page * 25:(self.challenge_page + 1) * 25]
            )
            self.challenge_select.disabled = False
        else:
            self.challenge_select.options.append(discord.SelectOption(label="Nenhum desafio disponível para este jogo", value="0"))
            self.challenge_select.disabled = True
        from cogs.comunidade import CommunityContextContributionButton, adicionar_botao_contribuicao_contextual
        for item in list(self.children):
            if isinstance(item, (PageButton, VoltarCentralButton, CommunityContextContributionButton)):
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
        game_row = next((r for r in self.jogos if int(r["id"]) == self.game_id), None)
        game_name = str(game_row["name"]) if game_row else ""
        adicionar_botao_contribuicao_contextual(
            self, "challenge", "runs", "Sugerir desafio", "⚔️", row=4,
            default_game=game_name, style=discord.ButtonStyle.primary,
        )
        linha_voltar = next(linha for linha in (2, 3, 4) if linha not in linhas_usadas)
        self.add_item(VoltarCentralButton(self.cog, row=linha_voltar, callback_voltar=getattr(self.cog, "_retornos_nara", {}).get(getattr(self.parent_interaction, "user", None).id) if getattr(self.parent_interaction, "user", None) else None))

    async def _choose_game(self, interaction: discord.Interaction):
        self.game_id = int(self.game_select.values[0])
        self.challenge_page = 0
        self._filtrar_desafios()
        self._refresh_options()
        game_row = next((r for r in self.jogos if int(r["id"]) == self.game_id), None)
        game_name = str(game_row["name"]) if game_row else "este jogo"
        content = None if self.desafios else (
            f"Este jogo ainda não possui desafios compatíveis. Use **Sugerir desafio** nesta mesma tela para propor um novo para {game_name}."
        )
        await interaction.response.edit_message(content=content, view=self)

    async def _choose_challenge(self, interaction: discord.Interaction):
        if self.challenge_select.values[0] == "0":
            game_row = next((r for r in self.jogos if int(r["id"]) == self.game_id), None)
            game_name = str(game_row["name"]) if game_row else "este jogo"
            return await interaction.response.edit_message(
                content=(f"Este jogo ainda não possui desafios compatíveis. Use **Sugerir desafio** "
                         f"nesta mesma tela para propor um para {game_name}."),
                view=self,
            )
        self.challenge_id = int(self.challenge_select.values[0])
        g = await self.cog.bot.db._one("SELECT * FROM sl_games WHERE id=?", (self.game_id,))
        c = await self.cog.bot.db._one("SELECT * FROM sl_challenges WHERE id=?", (self.challenge_id,))
        if not g or not c or (c["game_id"] is not None and int(c["game_id"]) != self.game_id):
            return await interaction.response.edit_message(
                content="⚠️ Jogo ou desafio incompatível. Volte à central e tente novamente.",
                embeds=[], view=VoltarCentralView(self.cog, self.callback_voltar),
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

    def __init__(
        self, cog, game_id: int, challenge_id: int, parent_interaction=None,
        tempo_padrao: int | None = None, build_padrao: str | None = None,
        motivo_rejeicao: str | None = None, callback_voltar=None,
    ):
        super().__init__(timeout=300)
        self.cog = cog
        self.game_id = game_id
        self.challenge_id = challenge_id
        self.parent_interaction = parent_interaction
        user_obj = getattr(parent_interaction, "user", None)
        self.callback_voltar = callback_voltar or _callback_nara_soulslike(
            cog, getattr(user_obj, "id", None)
        )
        if tempo_padrao:
            self.tempo.default = fmt_tempo(int(tempo_padrao))
        if build_padrao is not None:
            self.build.default = str(build_padrao)[:100]
        self.motivo_rejeicao = str(motivo_rejeicao or "").strip()[:180]

    async def on_submit(self, interaction: discord.Interaction):
        seg = parse_tempo(str(self.tempo))
        if seg is None:
            return await interaction.response.send_message(AJUDA_TEMPO, ephemeral=True)
        g = await self.cog.bot.db._one("SELECT * FROM sl_games WHERE id=?", (self.game_id,))
        c = await self.cog.bot.db._one("SELECT * FROM sl_challenges WHERE id=?", (self.challenge_id,))
        if not g or not c:
            return await interaction.response.send_message("O jogo ou desafio não está mais disponível. Reabra a Central Soulslike.", ephemeral=True)
        state = self.cog.pending_uploads.get(interaction.user.id)
        if state and time.monotonic() - float(state.get("created_at", 0)) <= PENDING_UPLOAD_TTL:
            return await interaction.response.send_message(
                "Você já tem um registro aguardando comprovante. Conclua esse envio ou aguarde o prazo de 10 minutos antes de iniciar outro.",
                ephemeral=True,
            )
        if state:
            self.cog.pending_uploads.pop(interaction.user.id, None)
        build = (str(self.build).strip() or 'Não informada')[:100]

        async def concluir(avaliacao_interaction, nota, dificuldade, comentario):
            await self.cog.iniciar_upload_run(
                avaliacao_interaction, self.game_id, self.challenge_id, seg, build, nota, comentario, dificuldade
            )

        await interaction.response.send_message(
            "**Avaliação — 1/3: Nota da experiência**\nQuanto você gostou desta run? Escolha uma nota de 1 a 10.",
            view=NotaJogoView(
                concluir, "Na sua experiência, qual foi a dificuldade para concluir esta run/desafio?",
                contexto=(f"Jogo: **{discord.utils.escape_markdown(g['name'])}**\n"
                          f"Desafio: **{discord.utils.escape_markdown(c['name'])}** · Tempo: **{fmt_tempo(seg)}**\n"
                          f"Build: **{discord.utils.escape_markdown(build or 'Não informada')}**"
                          + (f"\n**Motivo da rejeição anterior:** {discord.utils.escape_markdown(self.motivo_rejeicao)}" if self.motivo_rejeicao else "")),
            ), ephemeral=True,
        )
        if self.parent_interaction is not None:
            try:
                await self.parent_interaction.edit_original_response(
                    content="Conclua a avaliação na tela privada aberta. Depois, enviarei as instruções do comprovante.",
                    embeds=[], view=VoltarCentralView(self.cog, self.callback_voltar),
                )
            except discord.HTTPException:
                log.debug("Não foi possível atualizar a tela anterior ao iniciar avaliação da run")


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
        try:
            mod_ch_id = await GuildConfig.get(db, interaction.guild_id, "mod_channel")
            canal = await get_text_channel(self.cog.bot, mod_ch_id)
            if canal and run and run['proof_msg_id']:
                msg = await canal.fetch_message(run['proof_msg_id'])
                if msg.embeds:
                    embed = msg.embeds[0]
                    embed.color = discord.Color.dark_grey()
                    embed.add_field(name="Resultado", value="Cancelada pelo autor", inline=False)
                    await msg.edit(embed=embed, view=None)
        except Exception:
            log.exception("Run #%s cancelada no banco, mas falhou a atualização da mensagem de moderação", self.run_id)
        try:
            await db.log(interaction.user.id, "run_cancelada", f"id={self.run_id}")
        except Exception:
            log.exception("Run #%s cancelada, mas falhou o log de auditoria", self.run_id)
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
    def __init__(self, cog, user, g, c, seg, build, dados, filename, nota=None, comentario="", dificuldade=None):
        super().__init__(timeout=180)
        self.cog, self.user, self.g, self.c = cog, user, g, c
        self.seg, self.build, self.dados, self.filename = seg, build, dados, filename
        self.nota, self.comentario = nota, str(comentario or "")[:500]
        self.dificuldade = dificuldade
        self._claimed = False
        self._claim_lock = asyncio.Lock()

    @discord.ui.button(label="Confirmar e enviar", style=discord.ButtonStyle.success, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Esse comprovante pertence a outro jogador.", ephemeral=True)
        async with self._claim_lock:
            if self._claimed:
                return await interaction.response.send_message("Este envio já está sendo processado.", ephemeral=True)
            self._claimed = True
        await interaction.response.edit_message(content="⏳ Enviando para a moderação...", embed=None, view=None)
        try:
            run_id = await self.cog.enviar_para_moderacao(
                self.user, self.g, self.c, self.seg, self.build, self.dados, self.filename,
                self.nota, self.comentario, self.dificuldade,
            )
        except Exception:
            log.exception("Falha inesperada ao enviar run para user=%s", self.user.id)
            run_id = None
        if run_id is None:
            return await interaction.edit_original_response(
                content="Não consegui enviar para a moderação. Nenhum registro incompleto foi mantido; confira o canal de aprovação e tente novamente."
            )
        await interaction.edit_original_response(
            content=f"✅ Run enviada para a moderação! Número `#{run_id}`. Acompanhe pelo botão **Meu perfil** na Central Soulslike."
        )
        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Esse comprovante pertence a outro jogador.", ephemeral=True)
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
        min_length=5,
        max_length=300,
        placeholder="Ex.: o print não mostra o tempo de jogo.",
    )

    def __init__(self, cog, run_id: int):
        super().__init__()
        self.cog, self.run_id = cog, run_id

    async def on_submit(self, interaction: discord.Interaction):
        # Revalida a permissão no submit; abrir o modal não é uma autorização permanente.
        if not isinstance(interaction.user, discord.Member) or not await eh_moderador(interaction.user, self.cog.bot.db):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        db = self.cog.bot.db
        run = await db._one("SELECT * FROM sl_runs WHERE id=?", (self.run_id,))
        if run is None or run["status"] != "pending":
            return await interaction.response.send_message("Este registro já foi processado.", ephemeral=True)
        if run["user_id"] == interaction.user.id and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Você não pode rejeitar a sua própria run.", ephemeral=True)
        cur = await db.conn.execute(
            "UPDATE sl_runs SET status='rejected', reviewer_id=?, reject_reason=? WHERE id=? AND status='pending'",
            (interaction.user.id, str(self.motivo), self.run_id),
        )
        await db.conn.commit()
        if cur.rowcount != 1:
            return await interaction.response.send_message("Esta run já foi processada por outro moderador.", ephemeral=True)
        from cogs.comum import sincronizar_cartao
        await sincronizar_cartao(self.cog.bot, interaction.guild_id, "runs", self.run_id, "rejected", interaction.user.id, str(self.motivo))
        try:
            await db.log(interaction.user.id, "run_rejeitada", f"id={self.run_id} motivo={self.motivo}")
        except Exception:
            log.exception("Run #%s rejeitada, mas falhou o log de auditoria", self.run_id)
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Resultado", value=f"❌ Rejeitada por {interaction.user.mention}\nMotivo: {self.motivo}", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        from utils import notificar_usuario
        await notificar_usuario(
            self.cog.bot, interaction.guild_id, int(run["user_id"]), "rejections",
            f"❌ Sua run `#{self.run_id}` foi rejeitada.\nMotivo: {self.motivo}\n"
            "Você pode corrigir os dados e enviar novamente pela Central Soulslike."
        )


class RankingView(discord.ui.View):
    def __init__(self, cog, jogos, desafios, game_id, chal_id):
        super().__init__(timeout=600)
        self.cog, self.game_id, self.chal_id = cog, int(game_id), int(chal_id)
        self.jogos, self.todos_desafios = jogos, desafios
        self.desafios = []
        self._filtrar_desafios()
        self.sel_jogo = discord.ui.Select(
            placeholder="Jogo",
            options=[discord.SelectOption(label=j["name"][:100], value=str(j["id"]), default=int(j["id"]) == self.game_id) for j in jogos[:25]],
        )
        self.sel_desafio = discord.ui.Select(placeholder="Desafio", min_values=1, max_values=1)
        self.sel_jogo.callback = self.trocar_jogo
        self.sel_desafio.callback = self.trocar_desafio
        self.add_item(self.sel_jogo)
        self.add_item(self.sel_desafio)
        self.add_item(VoltarCentralButton(cog, row=2))
        self._atualizar_opcoes_desafio()

    def _filtrar_desafios(self):
        self.desafios = [row for row in self.todos_desafios if row["game_id"] is None or int(row["game_id"]) == self.game_id]
        ids = {int(row["id"]) for row in self.desafios}
        if self.chal_id not in ids:
            self.chal_id = int(self.desafios[0]["id"]) if self.desafios else 0

    def _atualizar_opcoes_desafio(self):
        if self.desafios:
            self.sel_desafio.options = [
                discord.SelectOption(label=row["name"][:100], value=str(row["id"]), default=int(row["id"]) == self.chal_id)
                for row in self.desafios[:25]
            ]
            self.sel_desafio.disabled = False
        else:
            self.sel_desafio.options = [discord.SelectOption(label="Nenhum desafio disponível", value="0")]
            self.sel_desafio.disabled = True

    async def _atualizar(self, interaction: discord.Interaction):
        for option in self.sel_jogo.options:
            option.default = option.value == str(self.game_id)
        self._atualizar_opcoes_desafio()
        texto = (
            await self.cog.texto_ranking(self.game_id, self.chal_id) if self.chal_id
            else "## ⚔️ Hall da Fama\n\nEste jogo ainda não possui desafios compatíveis."
        )
        await interaction.response.edit_message(content=texto, embeds=[], view=self)

    async def trocar_jogo(self, interaction: discord.Interaction):
        self.game_id = int(self.sel_jogo.values[0])
        self._filtrar_desafios()
        await self._atualizar(interaction)

    async def trocar_desafio(self, interaction: discord.Interaction):
        self.chal_id = int(self.sel_desafio.values[0])
        await self._atualizar(interaction)


# Registrar run e ranking são botões da CentralView, não comandos slash.
# Autocomplete não se aplica a callbacks de botões.


async def setup(bot):
    await bot.add_cog(Soulslike(bot))
