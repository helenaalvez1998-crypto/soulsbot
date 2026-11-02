import asyncio
import datetime as dt
import json
import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

import config
from admin_config import GuildConfig
from cogs.platinas import eh_moderador
from levels import nivel_por_xp, patente_por_nivel, barra_progresso
from links_sociais import REDES, normalizar_link
from utils import upsert_panel

log = logging.getLogger("colizeu")

TEMAS = {
    "Ouro": config.COR_OURO,
    "Prata": config.COR_PRATA,
    "Sangue": 0x8B0000,
    "Safira": 0x1F4E9E,
    "Esmeralda": 0x1E8449,
    "Violeta": 0x6C3483,
}
LINHA = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
MAX_EMBEDS_CHARS = 5800  # o Discord aceita 6000 por mensagem


def fmt_tempo(seg: int) -> str:
    h, resto = divmod(seg, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}"


def fmt_data(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%d/%m/%Y")
    except ValueError:
        return iso


class Santuario(commands.Cog):
    """Cada membro tem um santuário: uma thread privada com o perfil, a galeria e as redes dele.
    Quem clica em "Visitar" é adicionado à thread e, ao usar "Sair do tópico", ela some da lista."""

    def __init__(self, bot):
        self.bot = bot
        self._lock_criar = asyncio.Lock()
        self._ultimo_refresh: dict[int, float] = {}

    async def cog_load(self):
        self.bot.add_view(SantuarioPublicoView(self))
        self.bot.add_view(CartaoView(self))

    # ------------------------------------------------------------ infraestrutura
    async def _thread(self, thread_id: int) -> discord.Thread | None:
        canal = self.bot.get_channel(thread_id)
        if canal is None:
            try:
                canal = await self.bot.fetch_channel(thread_id)
            except (discord.NotFound, discord.Forbidden):
                return None
            except discord.HTTPException:
                return None
        return canal if isinstance(canal, discord.Thread) else None

    async def _criar_thread(self, canal: discord.TextChannel, nome: str) -> discord.Thread:
        ultimo = None
        for duracao in (10080, 4320, 1440, 60):  # alguns servidores não aceitam as durações longas
            try:
                return await canal.create_thread(
                    name=f"🏛️ {nome}"[:100],
                    type=discord.ChannelType.private_thread,
                    invitable=False,
                    auto_archive_duration=duracao,
                    reason="Colizeu: santuário de membro",
                )
            except discord.HTTPException as e:
                ultimo = e
                if e.status == 403:
                    break
        raise ultimo

    async def _pessoa(self, guild: discord.Guild, user_id: int):
        m = guild.get_member(user_id)
        if m is None:
            try:
                m = await guild.fetch_member(user_id)
            except discord.HTTPException:
                m = None
        if m:
            return m.display_name, m.display_avatar.url, m.joined_at
        try:
            u = await self.bot.fetch_user(user_id)
            return u.display_name, u.display_avatar.url, None
        except discord.HTTPException:
            return f"Gladiador {user_id}", None, None

    async def _banner(self, user_id: int) -> str | None:
        try:
            u = await self.bot.fetch_user(user_id)
            return u.banner.url if u.banner else None
        except discord.HTTPException:
            return None

    async def _foto(self, guild: discord.Guild, p) -> str | None:
        """Links de imagem do Discord expiram: pega um novo na mensagem original da moderação."""
        mod_ch_id = await GuildConfig.get(self.bot.db, guild.id, "mod_channel")
        canal = guild.get_channel(mod_ch_id) if mod_ch_id else None
        if canal and p["proof_msg_id"]:
            try:
                msg = await canal.fetch_message(p["proof_msg_id"])
                if msg.embeds and msg.embeds[0].image:
                    return msg.embeds[0].image.url
                if msg.attachments:
                    return msg.attachments[0].url
            except discord.HTTPException:
                pass
        return None

    async def _runs(self, user_id: int):
        """Runs do módulo Soulslike (só aparece se as tabelas dele existirem neste banco)."""
        db = self.bot.db
        existe = await db._one("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sl_runs'")
        if not existe:
            return []
        return await db._all(
            """SELECT g.name AS jogo, c.name AS desafio, MIN(r.seconds) AS melhor, COUNT(*) AS vezes
               FROM sl_runs r JOIN sl_games g ON g.id=r.game_id JOIN sl_challenges c ON c.id=r.challenge_id
               WHERE r.user_id=? AND r.status='approved'
               GROUP BY r.game_id, r.challenge_id ORDER BY g.name, c.name LIMIT 8""",
            (user_id,),
        )

    # ------------------------------------------------------------ o cartão do santuário
    async def montar_embeds(self, guild: discord.Guild, thread: discord.Thread, user_id: int, perfil) -> list[discord.Embed]:
        db = self.bot.db
        cor = TEMAS.get(perfil["theme"], config.COR_OURO)
        nome, avatar, desde = await self._pessoa(guild, user_id)
        user = await db.get_user(user_id)
        nivel = nivel_por_xp(user["xp"])
        platinas = await db.platinas_do_usuario(user_id)
        qtd = len(platinas)

        # --- 1. o santuário em si
        tagline = f"*“{perfil['tagline']}”*\n" if perfil["tagline"] else "*Um gladiador em silêncio...*\n"
        sobre = perfil["bio"] or "Este gladiador ainda não escreveu a sua história."
        hero = discord.Embed(
            title=f"✦ SANTUÁRIO DE {nome.upper()} ✦"[:256],
            description=f"{tagline}{LINHA}\n**📜 Sobre**\n{sobre}",
            color=cor,
        )
        if avatar:
            hero.set_thumbnail(url=avatar)
        banner = await self._banner(user_id)
        if banner:
            hero.set_image(url=banner)
        hero.add_field(name="🎖️ Patente", value=patente_por_nivel(nivel))
        hero.add_field(name="⭐ Nível", value=str(nivel))
        hero.add_field(name="🏆 Platinas", value=str(qtd))
        hero.add_field(name="🪙 Denários", value=str(user["denarios"]))
        hero.add_field(name="📈 Rank XP", value=f"#{await db.posicao_xp(user['xp'])}")
        hero.add_field(name="🥇 Rank Platinas", value=f"#{await db.posicao_platinas(qtd)}")
        if perfil["fav_game"]:
            hero.add_field(name="💖 Jogo do coração", value=perfil["fav_game"], inline=False)
        hero.add_field(name="✨ Experiência", value=barra_progresso(user["xp"]), inline=False)
        rodape = "✦ Santuário • Colizeu"
        if desde:
            rodape += f" • No Colizeu desde {desde:%d/%m/%Y}"
        hero.set_footer(text=rodape)

        # --- 2. contas de jogos e redes sociais
        # Plataformas de jogos ficam visíveis nos santuários de todos.
        # Redes sociais pessoais aparecem apenas no santuário do proprietário do bot.
        links = json.loads(perfil["links"] or "{}")
        plataformas = {"steam", "epic", "gog", "ea", "ubisoft", "battlenet", "itchio", "psn", "xbox"}
        dono_bot_id = 1300117955236991046
        linhas_plataformas = [
            f"{REDES[k][1]} [{REDES[k][0]}]({url})"
            for k, url in links.items()
            if k in REDES and k in plataformas
        ]
        contas = discord.Embed(
            title="🎮 Plataformas de jogos",
            description="\n".join(linhas_plataformas) if linhas_plataformas else "*Nenhuma plataforma adicionada.*",
            color=cor,
        )
        embeds = [hero, contas]

        # YouTube, Twitch, Instagram, TikTok e X só aparecem no santuário do dono configurado.
        if int(user_id) == dono_bot_id:
            linhas_sociais = [
                f"{REDES[k][1]} [{REDES[k][0]}]({url})"
                for k, url in links.items()
                if k in REDES and k not in plataformas
            ]
            sociais = discord.Embed(
                title="🔗 Minhas redes sociais",
                description="\n".join(linhas_sociais) if linhas_sociais else "*Nenhuma rede social adicionada ainda.*",
                color=cor,
            )
            embeds.append(sociais)

        # --- 3. runs soulslike (se o módulo estiver ativo)
        runs = await self._runs(user_id)
        if runs:
            txt = "\n".join(
                f"⚔️ **{r['jogo']}** — {r['desafio']}: **{fmt_tempo(r['melhor'])}**"
                + (f" • 🔁 {r['vezes']}x" if r["vezes"] > 1 else "")
                for r in runs
            )
            embeds.append(discord.Embed(title="⚔️ Runs Soulslike (melhores tempos)", description=txt, color=cor))

        # --- 4. resumo da galeria no cartão público; os comprovantes ficam na galeria privada paginada
        if platinas:
            lista = "\n".join(
                f"🏆 **{p['game']}**\n└ {p['platform']} · {fmt_data(p['earned_at'])}"
                for p in platinas[:4]
            )
            restantes = len(platinas) - min(4, len(platinas))
            if restantes > 0:
                lista += f"\n\n*+ {restantes} outra{'s' if restantes != 1 else ''} conquista{'s' if restantes != 1 else ''}*"
            desc = f"**{len(platinas)} platina{'s' if len(platinas) != 1 else ''} conquistada{'s' if len(platinas) != 1 else ''}**\n\n{lista}\n\nUse **🏆 Ver galeria** abaixo para abrir os comprovantes em tamanho maior."
        else:
            desc = "*Nenhuma platina aprovada ainda. Use `/coliseu` para registrar a primeira!*"
        galeria = discord.Embed(title="🏆 Galeria de Platinas", description=desc, color=cor, url=thread.jump_url)
        galeria.set_footer(text="Coliseu pessoal · Comprovantes disponíveis em Ver galeria")
        embeds.append(galeria)

        # segurança: o Discord recusa mensagens com mais de 6000 caracteres nos embeds
        while sum(len(e) for e in embeds) > MAX_EMBEDS_CHARS and len(galeria.description) > 200:
            galeria.description = galeria.description.rsplit("\n", 1)[0]
        return embeds

    async def atualizar(self, user_id: int, force_new: bool = False) -> bool:
        """Redesenha o cartão; force_new publica um cartão novo e remove o anterior."""
        db = self.bot.db
        perfil = await db.get_perfil(user_id)
        if perfil is None:
            return False
        thread = await self._thread(perfil["thread_id"])
        if thread is None:
            return False
        if thread.archived:
            await thread.edit(archived=False)
        embeds = await self.montar_embeds(thread.guild, thread, user_id, perfil)
        view = CartaoView(self)
        mensagem_antiga = None
        if perfil["card_msg_id"]:
            try:
                mensagem_antiga = await thread.fetch_message(perfil["card_msg_id"])
            except discord.NotFound:
                mensagem_antiga = None
            if mensagem_antiga and not force_new:
                await mensagem_antiga.edit(embeds=embeds, view=view)
                return True
        msg = await thread.send(embeds=embeds, view=view)
        await db.atualizar_perfil(user_id, card_msg_id=msg.id)
        if force_new and mensagem_antiga:
            try:
                await mensagem_antiga.unpin()
            except discord.HTTPException:
                pass
            try:
                await mensagem_antiga.delete()
            except discord.HTTPException:
                log.warning("Novo cartão publicado, mas não foi possível apagar o cartão antigo do santuário %s", thread.id)
        try:
            await msg.pin()
        except discord.HTTPException:
            pass
        return True

    def _fonte_ephemeral(self, interaction: discord.Interaction) -> bool:
        return bool(interaction.message and getattr(interaction.message.flags, "ephemeral", False))

    def _view_voltar_painel(self, interaction: discord.Interaction, alvo=None):
        mensagem = interaction.message
        if not mensagem or not self._fonte_ephemeral(interaction):
            return None
        titulo = mensagem.embeds[0].title if mensagem.embeds else ""
        if titulo != "🏛️ Painel do Colizeu":
            return None
        platinas = self.bot.get_cog("Platinas")
        if not platinas:
            return None
        from cogs.platinas import VoltarPainelView
        return VoltarPainelView(platinas, interaction.user, alvo or interaction.user)

    async def _responder_fluxo(self, interaction: discord.Interaction, texto: str, *, privado_origem: bool,
                               view=None, antes_de_responder: bool = False):
        # Se ainda não respondemos, editar o painel privado original ou criar a primeira
        # resposta privada a partir de um painel público. Se já houve defer, finalizamos
        # o placeholder dessa mesma interação, sem abrir um follow-up adicional.
        if antes_de_responder and not interaction.response.is_done():
            if privado_origem:
                await interaction.response.edit_message(content=texto, embeds=[], view=view)
            else:
                await interaction.response.send_message(texto, ephemeral=True, view=view)
            return
        await interaction.edit_original_response(content=texto, embeds=[], view=view)

    # ------------------------------------------------------------ criar / abrir o próprio santuário
    async def abrir_meu(self, interaction: discord.Interaction):
        privado_origem = self._fonte_ephemeral(interaction)
        view_voltar = self._view_voltar_painel(interaction, interaction.user)
        perfis_ch_id = await GuildConfig.get(self.bot.db, interaction.guild_id, "perfis_channel")
        if not perfis_ch_id:
            return await self._responder_fluxo(
                interaction,
                "Os santuários ainda não foram configurados: falta o canal de perfis. Use /adm para configurar.",
                privado_origem=privado_origem, view=view_voltar, antes_de_responder=True,
            )
        canal = self.bot.get_channel(perfis_ch_id)
        if canal is None:
            try:
                canal = await self.bot.fetch_channel(perfis_ch_id)
            except discord.HTTPException:
                canal = None
        if not isinstance(canal, discord.TextChannel):
            log.error("perfis_channel=%s não é um canal de texto acessível pelo bot", perfis_ch_id)
            return await self._responder_fluxo(
                interaction, "O canal de santuários não foi encontrado. Configure pelo painel /adm.",
                privado_origem=privado_origem, view=view_voltar, antes_de_responder=True,
            )
        if privado_origem:
            await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
        db = self.bot.db
        criado = False
        async with self._lock_criar:
            perfil = await db.get_perfil(interaction.user.id)
            thread = await self._thread(perfil["thread_id"]) if perfil else None
            if perfil and thread is None:
                await db.apagar_perfil(interaction.user.id)
                perfil = None
            if perfil is None:
                try:
                    thread = await self._criar_thread(canal, interaction.user.display_name)
                except discord.HTTPException:
                    log.exception("Falha ao criar thread do santuário")
                    return await self._responder_fluxo(
                        interaction,
                        "Não consegui criar o santuário. Confira as permissões **Criar tópicos privados** e **Gerenciar tópicos**.",
                        privado_origem=privado_origem, view=view_voltar,
                    )
                await db.criar_perfil(interaction.user.id, thread.id)
                criado = True
        try:
            if thread.archived:
                await thread.edit(archived=False)
            await thread.add_user(interaction.user)
            await self.atualizar(interaction.user.id, force_new=True)
        except discord.HTTPException:
            log.exception("Falha ao preparar o santuário")
            return await self._responder_fluxo(
                interaction, "Algo deu errado ao preparar o santuário. Tente novamente.",
                privado_origem=privado_origem, view=view_voltar,
            )
        if criado:
            await db.log(interaction.user.id, "santuario_criado", f"thread={thread.id}")
        inicio = "✨ **Seu santuário foi criado!**" if criado else "🏛️ **Seu santuário está pronto.**"
        texto = f"{inicio}\n[Entrar no tópico do santuário]({thread.jump_url})\n\nLá dentro, use **Personalizar** e **Redes** para ajustar seu espaço."
        await self._responder_fluxo(
            interaction, texto, privado_origem=privado_origem, view=view_voltar,
        )

    # ------------------------------------------------------------ visitar
    async def visitar(self, interaction: discord.Interaction, alvo_id: int):
        privado_origem = self._fonte_ephemeral(interaction)
        alvo_membro = interaction.guild.get_member(alvo_id) if interaction.guild else None
        view_voltar = self._view_voltar_painel(interaction, alvo_membro or interaction.user)
        if privado_origem:
            await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
        if alvo_id == interaction.user.id:
            return await self._abrir_proprio_na_visita(interaction, privado_origem=privado_origem, view_voltar=view_voltar)
        perfil = await self.bot.db.get_perfil(alvo_id)
        thread = await self._thread(perfil["thread_id"]) if perfil else None
        if thread is None:
            return await self._responder_fluxo(
                interaction, f"<@{alvo_id}> ainda não tem santuário.", privado_origem=privado_origem,
                view=view_voltar,
            )
        try:
            if thread.archived:
                await thread.edit(archived=False)
            await thread.add_user(interaction.user)
        except discord.HTTPException:
            log.exception("Falha ao liberar visita")
            return await self._responder_fluxo(
                interaction, "Não consegui liberar a visita agora. Tente novamente.",
                privado_origem=privado_origem, view=view_voltar,
            )
        texto = (
            f"🚪 [Entrar no santuário de <@{alvo_id}>]({thread.jump_url})\n\n"
            "Quando terminar, use **Sair do tópico** no menu ⋯ para removê-lo da sua lista."
        )
        await self._responder_fluxo(
            interaction, texto, privado_origem=privado_origem, view=view_voltar,
        )

    async def _abrir_proprio_na_visita(self, interaction: discord.Interaction, *, privado_origem=False, view_voltar=None):
        perfil = await self.bot.db.get_perfil(interaction.user.id)
        thread = await self._thread(perfil["thread_id"]) if perfil else None
        if thread is None:
            return await self._responder_fluxo(
                interaction, "Você ainda não tem santuário. Use **Meu santuário** para criar.",
                privado_origem=privado_origem, view=view_voltar,
            )
        try:
            await thread.add_user(interaction.user)
        except discord.HTTPException:
            pass
        await self._responder_fluxo(
            interaction, f"🏛️ [Abrir seu santuário]({thread.jump_url})",
            privado_origem=privado_origem, view=view_voltar,
        )

    # ------------------------------------------------------------ dono do santuário
    async def exigir_dono(self, interaction: discord.Interaction):
        perfil = await self.bot.db.get_perfil_por_thread(interaction.channel_id)
        if perfil is None:
            await interaction.response.send_message("Não achei o dono deste santuário.", ephemeral=True)
            return None
        if perfil["user_id"] != interaction.user.id:
            await interaction.response.send_message("Só o dono deste santuário pode editá-lo. 🔒", ephemeral=True)
            return None
        return perfil

    async def refresh(self, interaction: discord.Interaction):
        perfil = await self.exigir_dono(interaction)
        if perfil is None:
            return
        agora = time.monotonic()
        if agora - self._ultimo_refresh.get(interaction.user.id, 0) < 30:
            return await interaction.response.send_message("Calma, gladiador! Espere uns segundos para atualizar de novo.", ephemeral=True)
        self._ultimo_refresh[interaction.user.id] = agora
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.atualizar(interaction.user.id)
        await interaction.edit_original_response(content="🔄 Santuário atualizado!")

    # ------------------------------------------------------------ comando de moderação
    @app_commands.command(name="painel_santuarios", description="[MOD] Publica neste canal o painel para criar ou visitar santuários pessoais.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def painel_santuarios(self, interaction: discord.Interaction):
        if not await eh_moderador(interaction.user, self.bot.db):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        texto = (
            "# 🏛️ Santuários do Coliseu\n\n"
            "Cada gladiador tem um espaço pessoal com suas platinas, comprovantes, runs e plataformas.\n\n"
            "✨ **Meu santuário** — crie ou abra o seu.\n"
            "🚪 **Visitar um santuário** — escolha um membro; ao terminar, saia do tópico para removê-lo da sua lista."
        )
        await upsert_panel(
            self.bot, interaction.channel,
            f"panel:santuarios:{interaction.guild_id}:{interaction.channel_id}",
            marker="sant:meu", content=texto, embeds=[], view=SantuarioPublicoView(self),
        )
        await interaction.response.send_message("✅ Painel de santuários atualizado neste canal.", ephemeral=True)


# ------------------------------------------------------------------ views
class SantuarioPublicoView(discord.ui.View):
    """Botões fixos do canal de perfis (continuam funcionando após reiniciar o bot)."""

    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Meu santuário", style=discord.ButtonStyle.success, emoji="✨", custom_id="sant:meu")
    async def meu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.abrir_meu(interaction)

    @discord.ui.button(label="Visitar um santuário", style=discord.ButtonStyle.primary, emoji="🚪", custom_id="sant:visitar")
    async def visitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "De quem você quer visitar o santuário?", view=EscolherVisitaView(self.cog), ephemeral=True
        )


class EscolherVisitaView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=120)
        self.cog = cog
        self.sel = discord.ui.UserSelect(placeholder="Escolha um membro")
        self.sel.callback = self.escolher
        self.add_item(self.sel)

    async def escolher(self, interaction: discord.Interaction):
        alvo = self.sel.values[0]
        if getattr(alvo, "bot", False):
            return await interaction.response.send_message("Bots não têm santuário.", ephemeral=True)
        await self.cog.visitar(interaction, alvo.id)


class CartaoView(discord.ui.View):
    """Botões do cartão dentro do santuário. Só o dono consegue usar."""

    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Personalizar", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="sant:perfil")
    async def personalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        perfil = await self.cog.exigir_dono(interaction)
        if perfil:
            await interaction.response.send_modal(PersonalizarModal(self.cog, perfil))

    @discord.ui.button(label="Redes", style=discord.ButtonStyle.secondary, emoji="🔗", custom_id="sant:redes")
    async def redes(self, interaction: discord.Interaction, button: discord.ui.Button):
        perfil = await self.cog.exigir_dono(interaction)
        if perfil:
            await interaction.response.send_modal(RedeModal(self.cog))

    @discord.ui.button(label="Ver galeria", style=discord.ButtonStyle.success, emoji="🏆", custom_id="sant:galeria")
    async def ver_galeria(self, interaction: discord.Interaction, button: discord.ui.Button):
        perfil = await self.cog.bot.db.get_perfil_por_thread(interaction.channel_id)
        if perfil is None:
            return await interaction.response.send_message("Não achei este santuário.", ephemeral=True)
        guild = interaction.guild
        rows = await self.cog.bot.db.platinas_do_usuario(perfil["user_id"])
        if not rows:
            return await interaction.response.send_message(
                "Este santuário ainda não tem platinas aprovadas.", ephemeral=True
            )
        await interaction.response.defer(ephemeral=True, thinking=True)
        itens = []
        for p in rows:
            # O banco retorna sqlite3.Row, que permite p["campo"] mas não p.get(...).
            # Convertemos para dict para a galeria poder consultar os campos com .get().
            registro = dict(zip(p.keys(), p)) if hasattr(p, "keys") else dict(p)
            foto = await self.cog._foto(guild, registro)
            itens.append((registro, foto))
        view = GaleriaView(itens, TEMAS.get(perfil["theme"], config.COR_OURO))
        await interaction.edit_original_response(embeds=view.embeds_pagina(0), view=view)


class GaleriaView(discord.ui.View):
    """Coleção compacta: seleciona uma platina e abre seu comprovante sob demanda."""

    def __init__(self, itens, cor):
        super().__init__(timeout=300)
        self.itens = itens
        self.cor = cor
        self.pagina = 0
        self.selecionado = 0
        self.modo_comprovante = False
        self.tamanho_pagina = 10
        self.total_paginas = max(1, (len(itens) + self.tamanho_pagina - 1) // self.tamanho_pagina)
        self._montar_componentes()

    def _montar_componentes(self):
        self.clear_items()
        inicio = self.pagina * self.tamanho_pagina
        lote = self.itens[inicio:inicio + self.tamanho_pagina]
        opcoes = []
        for indice, (p, _foto) in enumerate(lote, start=inicio):
            nome = str(p.get('game') or 'Jogo sem nome')
            if len(nome) > 95:
                nome = nome[:92] + '...'
            opcoes.append(discord.SelectOption(
                label=nome,
                description=f"{p.get('platform', 'Plataforma não informada')} · {fmt_data(p.get('earned_at'))}"[:100],
                value=str(indice),
                default=indice == self.selecionado,
            ))
        if opcoes and not self.modo_comprovante:
            seletor = discord.ui.Select(
                placeholder="Escolha uma platina para ver o comprovante",
                min_values=1, max_values=1, options=opcoes, row=0,
            )
            seletor.callback = self.selecionar
            self.add_item(seletor)
            self.ver_comprovante.disabled = False
            self.add_item(self.ver_comprovante)
            self.anterior.disabled = self.pagina == 0
            self.proxima.disabled = self.pagina >= self.total_paginas - 1
            self.add_item(self.anterior)
            self.add_item(self.proxima)
        else:
            self.add_item(self.voltar)

    def embeds_pagina(self, pagina=None):
        if pagina is None:
            pagina = self.pagina
        inicio = pagina * self.tamanho_pagina
        lote = self.itens[inicio:inicio + self.tamanho_pagina]
        linhas = []
        for indice, (p, _foto) in enumerate(lote, start=inicio):
            marcador = ' **← selecionada**' if indice == self.selecionado else ''
            linhas.append(
                f"🏆 **{p.get('game', 'Jogo sem nome')}**\n"
                f"　`{p.get('platform', 'N/D')}` · {fmt_data(p.get('earned_at'))}{marcador}"
            )
        e = discord.Embed(
            title="🏆 Arsenal de Platinas",
            description=(f"**{len(self.itens)} conquistas** · Página **{pagina + 1}/{self.total_paginas}**\n\n"
                         + "\n\n".join(linhas)
                         + "\n\n*Selecione um jogo e clique em **Ver comprovante** para ampliar a captura.*"),
            color=self.cor,
        )
        e.set_footer(text="Coliseu pessoal · Comprovantes sob demanda")
        return [e]

    def embed_comprovante(self):
        p, foto = self.itens[self.selecionado]
        e = discord.Embed(
            title=f"🏆 {p.get('game', 'Jogo sem nome')}"[:256],
            description=f"**Plataforma:** {p.get('platform', 'N/D')}\n**Conquistada em:** {fmt_data(p.get('earned_at'))}",
            color=self.cor,
        )
        if foto:
            e.set_image(url=foto)
        else:
            e.add_field(name="Comprovante indisponível", value="A captura não está mais acessível na mensagem de moderação.", inline=False)
        e.set_footer(text=f"Platina {self.selecionado + 1} de {len(self.itens)}")
        return [e]

    async def selecionar(self, interaction: discord.Interaction):
        self.selecionado = int(interaction.data['values'][0])
        self._montar_componentes()
        await interaction.response.edit_message(embeds=self.embeds_pagina(), view=self)

    async def mudar(self, interaction, delta):
        self.pagina = max(0, min(self.total_paginas - 1, self.pagina + delta))
        inicio = self.pagina * self.tamanho_pagina
        if not (inicio <= self.selecionado < min(inicio + self.tamanho_pagina, len(self.itens))):
            self.selecionado = inicio
        self._montar_componentes()
        await interaction.response.edit_message(embeds=self.embeds_pagina(), view=self)

    @discord.ui.button(label="Ver comprovante", style=discord.ButtonStyle.success, emoji="🔎", row=1)
    async def ver_comprovante(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.modo_comprovante = True
        self._montar_componentes()
        await interaction.response.edit_message(embeds=self.embed_comprovante(), view=self)

    @discord.ui.button(label="Voltar à coleção", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.modo_comprovante = False
        self._montar_componentes()
        await interaction.response.edit_message(embeds=self.embeds_pagina(), view=self)

    @discord.ui.button(label="Anterior", style=discord.ButtonStyle.secondary, emoji="◀️", row=2)
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.mudar(interaction, -1)

    @discord.ui.button(label="Próxima", style=discord.ButtonStyle.primary, emoji="▶️", row=2)
    async def proxima(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.mudar(interaction, 1)


class PersonalizarModal(discord.ui.Modal):
    def __init__(self, cog, perfil):
        super().__init__(title="Personalizar santuário")
        self.cog = cog
        self.tagline = discord.ui.TextInput(
            placeholder="Uma frase que te define", required=False, max_length=100, default=perfil["tagline"] or None
        )
        self.bio = discord.ui.TextInput(
            style=discord.TextStyle.paragraph, placeholder="Conte sua história de jogador",
            required=False, max_length=500, default=perfil["bio"] or None,
        )
        self.fav = discord.ui.TextInput(
            placeholder="Ex.: Bloodborne", required=False, max_length=60, default=perfil["fav_game"] or None
        )
        self.tema = discord.ui.Select(
            options=[discord.SelectOption(label=n, value=n, default=n == perfil["theme"]) for n in TEMAS]
        )
        self.add_item(discord.ui.Label(text="Frase do santuário", component=self.tagline))
        self.add_item(discord.ui.Label(text="Sobre você", component=self.bio))
        self.add_item(discord.ui.Label(text="Jogo do coração", component=self.fav))
        self.add_item(discord.ui.Label(text="Cor do santuário", component=self.tema))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        tema = self.tema.values[0] if self.tema.values else "Ouro"
        await self.cog.bot.db.atualizar_perfil(
            interaction.user.id,
            tagline=self.tagline.value.strip(), bio=self.bio.value.strip(),
            fav_game=self.fav.value.strip(), theme=tema if tema in TEMAS else "Ouro",
        )
        await self.cog.atualizar(interaction.user.id)
        await interaction.edit_original_response(content="✅ Santuário personalizado!")

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        log.exception("Erro ao personalizar santuário", exc_info=error)
        if not interaction.response.is_done():
            await interaction.response.send_message("Algo deu errado. Tente de novo.", ephemeral=True)
        else:
            await interaction.edit_original_response(content="Algo deu errado. Tente de novo.")


class RedeModal(discord.ui.Modal):
    def __init__(self, cog):
        super().__init__(title="Adicionar rede ou conta")
        self.cog = cog
        self.rede = discord.ui.Select(
            options=[discord.SelectOption(label=nome, value=k, emoji=emoji) for k, (nome, emoji, _, _) in REDES.items()]
        )
        self.texto = discord.ui.TextInput(
            placeholder="Cole o link do perfil ou digite o @ (vazio = remover)", required=False, max_length=200
        )
        self.add_item(discord.ui.Label(text="Qual rede?", component=self.rede))
        self.add_item(discord.ui.Label(text="Link ou @", component=self.texto))

    async def on_submit(self, interaction: discord.Interaction):
        chave = self.rede.values[0] if self.rede.values else None
        resultado = normalizar_link(chave, self.texto.value) if chave else None
        if resultado is None:
            nome = REDES[chave][0] if chave else "essa rede"
            return await interaction.response.send_message(
                f"Não consegui usar isso como link de **{nome}**. Cole o link do seu perfil nessa rede "
                "(ex.: `https://twitch.tv/seunome`) ou digite só o `@`.",
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True, thinking=True)
        db = self.cog.bot.db
        perfil = await db.get_perfil(interaction.user.id)
        links = json.loads(perfil["links"] or "{}")
        if resultado == "":
            links.pop(chave, None)
            msg = f"🗑️ **{REDES[chave][0]}** removido."
        else:
            links[chave] = resultado
            msg = f"✅ **{REDES[chave][0]}** adicionado."
        await db.atualizar_perfil(interaction.user.id, links=json.dumps(links))
        await self.cog.atualizar(interaction.user.id)
        await interaction.edit_original_response(content=msg)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        log.exception("Erro ao salvar rede", exc_info=error)
        if not interaction.response.is_done():
            await interaction.response.send_message("Algo deu errado. Tente de novo.", ephemeral=True)
        else:
            await interaction.edit_original_response(content="Algo deu errado. Tente de novo.")


async def setup(bot):
    await bot.add_cog(Santuario(bot))
