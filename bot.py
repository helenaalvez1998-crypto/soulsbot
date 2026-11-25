"""Entrypoint e ciclo de vida do NARA.

Start command recomendado (FadeHost): python bot.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import hmac
import hashlib
import json
import secrets
import time
from urllib.parse import quote, urlencode, urlsplit

import threading
import traceback
from io import BytesIO
from pathlib import Path
from typing import Any

import discord
import aiohttp
from aiohttp import web
from discord import app_commands
from discord.ext import commands

import config
from database import Database


LOG_LEVEL = getattr(logging, config.LOG_LEVEL, logging.INFO)
try:
    from zoneinfo import ZoneInfo
    FUSO_LOG = ZoneInfo("America/Sao_Paulo")  # horário de Brasília
except Exception:  # sem tzdata: Brasília é UTC-3 fixo (sem horário de verão desde 2019)
    from datetime import timedelta, timezone
    FUSO_LOG = timezone(timedelta(hours=-3), "BRT")


class _FormatterBrasilia(logging.Formatter):
    """Carimba os logs no horário de Brasília, independente do fuso do servidor."""

    def formatTime(self, record, datefmt=None):
        from datetime import datetime
        momento = datetime.fromtimestamp(record.created, FUSO_LOG)
        return momento.strftime(datefmt or "%Y-%m-%d %H:%M:%S")


_handler_log = logging.StreamHandler(sys.stdout)
_handler_log.setFormatter(_FormatterBrasilia(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
logging.basicConfig(level=LOG_LEVEL, handlers=[_handler_log])
logging.captureWarnings(True)
log = logging.getLogger("nara")

EXTENSOES = (
    "cogs.comunidade", "cogs.admin", "cogs.perfil", "cogs.platinas", "cogs.loja", "cogs.ranking",
    "cogs.colizeu", "cogs.cargos", "cogs.progressao", "cogs.youtube",
    "cogs.ofertas", "cogs.zerados", "cogs.santuario", "cogs.soulslike",
    "cogs.transmissoes", "cogs.nara_ia", "cogs.painel_rotativo",
    "cogs.painel_membros", "cogs.catalogo_integrado", "cogs.game_news", "cogs.painel_jogo", "cogs.portal_role_panel",
)

COMANDOS_PRINCIPAIS = frozenset({"nara", "jogo", "adm"})


def _manter_apenas_comandos_principais(tree) -> list[str]:
    """Remove da árvore local os comandos públicos fora da lista principal aprovada."""
    removidos = []
    for comando in list(tree.get_commands()):
        if comando.name not in COMANDOS_PRINCIPAIS:
            tree.remove_command(comando.name)
            removidos.append(comando.name)
    restantes = {comando.name for comando in tree.get_commands()}
    if restantes != COMANDOS_PRINCIPAIS:
        raise RuntimeError(
            "A árvore de comandos precisa conter exatamente /nara, /jogo e /adm; "
            f"encontrados: {sorted(restantes)}"
        )
    return removidos


def _install_process_exception_hooks() -> None:
    """Registra exceções não tratadas sem expor credenciais em logs."""
    def _sys_hook(exc_type: type[BaseException], exc: BaseException, traceback: Any) -> None:
        log.critical(
            "Exceção não tratada no processo.",
            exc_info=(exc_type, exc, traceback),
        )

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        log.critical(
            "Exceção não tratada na thread %s.",
            getattr(args.thread, "name", "desconhecida"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _sys_hook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _thread_hook


_install_process_exception_hooks()




class RelatorioErroModal(discord.ui.Modal, title="Reportar problema com o NARA"):
    descricao = discord.ui.TextInput(
        label="O que você estava tentando fazer?",
        placeholder="Descreva o que aconteceu e o que você esperava que acontecesse...",
        style=discord.TextStyle.paragraph,
        min_length=0,
        max_length=1000,
        required=False,
    )

    def __init__(self, contexto: dict[str, str]):
        super().__init__(timeout=300)
        self.contexto = contexto

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Usa a configuração por servidor do /adm; MOD_CHANNEL_ID fica apenas
        # como fallback para instalações que ainda não escolheram um canal.
        from admin_config import GuildConfig

        canal_id = await GuildConfig.get(
            interaction.client.db, interaction.guild_id, "mod_channel"
        ) if interaction.guild_id else getattr(config, "MOD_CHANNEL_ID", 0)
        canal_id = int(canal_id or 0)
        canal = interaction.client.get_channel(canal_id) if canal_id else None
        if canal is None and canal_id:
            try:
                canal = await interaction.client.fetch_channel(canal_id)
            except (discord.HTTPException, discord.Forbidden):
                canal = None

        if canal is None or not hasattr(canal, "send"):
            return await interaction.response.send_message(
                "Não foi possível encaminhar o relatório: o canal de moderação não está configurado ou está inacessível. Avise a equipe por outro meio.",
                ephemeral=True,
            )

        embed = discord.Embed(
            title="🐛 Novo relatório de erro",
            description=(str(self.descricao.value).strip() or "Nenhum comentário adicional informado.")[:1000],
            color=0xE67E22,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Usuário", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
        embed.add_field(name="Servidor", value=f"`{self.contexto.get('guild', 'DM')}`", inline=True)
        embed.add_field(name="Comando/ação", value=f"`{self.contexto.get('acao', 'não identificada')[:200]}`", inline=False)
        embed.add_field(name="Tipo de erro", value=f"`{self.contexto.get('erro', 'não identificado')[:200]}`", inline=True)
        embed.add_field(name="Mensagem técnica", value=f"```{self.contexto.get('mensagem_erro', 'não disponível')[:900]}```", inline=False)
        embed.add_field(name="Mensagem exibida no Discord", value=self.contexto.get("mensagem_usuario", "não disponível")[:1000], inline=False)
        embed.add_field(name="Canal", value=f"`{self.contexto.get('canal', 'não identificado')}`", inline=True)
        embed.add_field(name="ID da interação", value=f"`{self.contexto.get('interaction_id', 'não disponível')}`", inline=False)

        # O traceback completo vai em TXT para não estourar os limites dos embeds do Discord.
        diagnostico = (
            f"AÇÃO: {self.contexto.get('acao', 'não identificada')}\\n"
            f"TIPO: {self.contexto.get('erro', 'não identificado')}\\n"
            f"MENSAGEM TÉCNICA: {self.contexto.get('mensagem_erro', 'não disponível')}\\n"
            f"MENSAGEM EXIBIDA AO USUÁRIO: {self.contexto.get('mensagem_usuario', 'não disponível')}\\n"
            f"SERVIDOR: {self.contexto.get('guild', 'DM')}\\n"
            f"CANAL: {self.contexto.get('canal', 'não identificado')}\\n"
            f"INTERAÇÃO: {self.contexto.get('interaction_id', 'não disponível')}\\n\\n"
            f"TRACEBACK COMPLETO:\\n{self.contexto.get('traceback', 'Traceback não disponível')}"
        )
        arquivo = discord.File(BytesIO(diagnostico.encode("utf-8")[:900_000]), filename="diagnostico_nara.txt")
        try:
            await canal.send(embed=embed, file=arquivo, allowed_mentions=discord.AllowedMentions.none())
        except (discord.HTTPException, discord.Forbidden):
            return await interaction.response.send_message(
                "Não consegui enviar o relatório à moderação. Tente novamente mais tarde.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            "Relatório enviado à equipe de moderação. Obrigado por ajudar a melhorar o NARA.",
            ephemeral=True,
        )


class AtelieRevisaoView(discord.ui.View):
    """Ações de aprovação no canal privado do Ateliê."""
    def __init__(self, bot: "NaraBot", submission_id: int):
        super().__init__(timeout=7 * 24 * 60 * 60)
        self.bot = bot
        self.submission_id = int(submission_id)

    async def _decidir(self, interaction: discord.Interaction, aprovado: bool) -> None:
        if not self.bot._atelier_is_admin(interaction.user.id):
            await interaction.response.send_message("Você não tem autorização para revisar artes.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        result = await self.bot.db.coliseu_atelie_decidir_web(
            self.submission_id, interaction.user.id, aprovado,
            "" if aprovado else "Rejeitada pela equipe no Discord.",
        )
        if result.get("status") != "ok":
            await interaction.followup.send("Esta submissão já foi processada ou não existe.", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        embed = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else discord.Embed(title="Ateliê do Coliseu")
        embed.color = discord.Color.green() if aprovado else discord.Color.red()
        embed.add_field(name="Decisão", value=f"{'Aprovada' if aprovado else 'Rejeitada'} por {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.followup.send(f"Submissão #{self.submission_id} {'aprovada' if aprovado else 'rejeitada'}.", ephemeral=True)

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, emoji="✅")
    async def aprovar(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await self._decidir(interaction, True)

    @discord.ui.button(label="Rejeitar", style=discord.ButtonStyle.danger, emoji="✖️")
    async def rejeitar(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await self._decidir(interaction, False)


class RelatorioErroView(discord.ui.View):
    def __init__(self, contexto: dict[str, str]):
        super().__init__(timeout=300)
        self.contexto = contexto

    @discord.ui.button(
        label="Reportar erro aos administradores",
        emoji="🐛",
        style=discord.ButtonStyle.secondary,
    )
    async def reportar(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(RelatorioErroModal(self.contexto))


def _contexto_relatorio(
    interaction: discord.Interaction,
    acao: str,
    error: BaseException,
    mensagem_usuario: str = "",
) -> dict[str, str]:
    """Monta o contexto técnico que será anexado ao relatório voluntário."""
    traceback_text = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    return {
        "acao": acao,
        "erro": type(error).__name__,
        "mensagem_erro": str(error) or type(error).__name__,
        "mensagem_usuario": mensagem_usuario or "Nenhuma mensagem apresentada.",
        "traceback": traceback_text or "Traceback não disponível.",
        "guild": str(interaction.guild_id or "DM"),
        "canal": str(interaction.channel_id or "desconhecido"),
        "interaction_id": str(interaction.id),
    }


def _interacao_expirada(error: BaseException | None) -> bool:
    """True para 404/10062 (Unknown interaction): o Discord já descartou a interação
    (passou de 3s sem resposta, normalmente por lag do gateway). Não há mais o que responder."""
    while error is not None:
        if isinstance(error, discord.NotFound) and getattr(error, "code", None) == 10062:
            return True
        error = getattr(error, "original", None)
    return False


async def _responder_erro_interacao(
    interaction: discord.Interaction,
    mensagem: str,
    contexto: dict[str, str],
) -> None:
    view = RelatorioErroView(contexto)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(mensagem, ephemeral=True, view=view)
        else:
            await interaction.response.send_message(mensagem, ephemeral=True, view=view)
    except (discord.HTTPException, discord.InteractionResponded, RuntimeError):
        log.debug("Não foi possível apresentar a opção de relatório; a interação expirou.", exc_info=True)


async def _nara_view_on_error(
    view: discord.ui.View,
    interaction: discord.Interaction,
    error: Exception,
    item: discord.ui.Item[Any],
) -> None:
    """Tratamento padrão para falhas em botões/selects sem handler local."""
    acao = getattr(item, "label", None) or getattr(item, "custom_id", None) or type(item).__name__
    if _interacao_expirada(error):
        log.warning("Interação expirada em componente (%s); o clique chegou após o prazo de 3s.", acao)
        return
    log.error(
        "Falha em componente de interface (%s).",
        acao,
        exc_info=(type(error), error, error.__traceback__),
    )
    await _responder_erro_interacao(
        interaction,
        "Ocorreu um erro ao executar essa ação. Se quiser, envie um relatório para a equipe de moderação.",
        _contexto_relatorio(
            interaction,
            str(acao),
            error,
            "Ocorreu um erro ao executar essa ação. Se quiser, envie um relatório para a equipe de moderação.",
        ),
    )


# Views que não implementam on_error próprio passam a oferecer o fluxo de relatório.
discord.ui.View.on_error = _nara_view_on_error


# ---------------------------------------------------------------------------
# Rede de segurança contra "Interação expirada" (Unknown interaction 10062)
# ---------------------------------------------------------------------------
# O Discord exige uma primeira resposta em até 3s. Vários painéis consultam o banco
# e montam imagens ANTES de responder; basta o host estar lento para estourar o prazo.
# Se um clique em botão/select ainda não foi respondido após AUTO_DEFER_APOS segundos,
# o bot o "adia" (defer) sozinho. A resposta real do callback continua funcionando:
# edit_message/send_message/defer são redirecionados para edit_original_response/
# followup quando a interação já foi adiada por esta rede de segurança.
AUTO_DEFER_APOS = 2.0

_orig_send_message = discord.InteractionResponse.send_message
_orig_edit_message = discord.InteractionResponse.edit_message
_orig_defer = discord.InteractionResponse.defer


# discord.Interaction usa __slots__, então guardamos os IDs adiados aqui.
_INTERACOES_ADIADAS: set[int] = set()


def _adiada_automaticamente(response: discord.InteractionResponse) -> bool:
    return response._parent.id in _INTERACOES_ADIADAS and response.is_done()


async def _send_message_seguro(self: discord.InteractionResponse, *args: Any, **kwargs: Any):
    if _adiada_automaticamente(self):
        delete_after = kwargs.pop("delete_after", None)
        msg = await self._parent.followup.send(*args, wait=True, **kwargs)
        if delete_after:
            await msg.delete(delay=delete_after)
        return msg
    return await _orig_send_message(self, *args, **kwargs)


async def _edit_message_seguro(self: discord.InteractionResponse, *args: Any, **kwargs: Any):
    # Um componente só pode receber uma resposta inicial. Às vezes outro caminho já
    # reconheceu a interação (defer, auto-defer ou resposta concorrente) sem registrar
    # o ID em _INTERACOES_ADIADAS. Tentar _orig_edit_message nesse estado gera HTTP 40060.
    if _adiada_automaticamente(self) or self.is_done():
        delete_after = kwargs.pop("delete_after", None)
        kwargs.pop("suppress_embeds", None)
        id_ = self._parent.id
        if id_ in _VIEW_CARREGANDO:
            # A mensagem está com botões bloqueados ("Carregando…"). Se o callback não
            # informou uma view, reenvia a view real (já restaurada) para liberar os botões.
            kwargs.setdefault("view", _VIEW_CARREGANDO[id_])
            _CARREGANDO_EDITADO.add(id_)
        msg = await self._parent.edit_original_response(*args, **kwargs)
        if delete_after:
            await msg.delete(delay=delete_after)
        return msg
    return await _orig_edit_message(self, *args, **kwargs)


async def _defer_seguro(self: discord.InteractionResponse, *args: Any, **kwargs: Any):
    if _adiada_automaticamente(self) or self.is_done():
        return None  # já reconhecida por outro caminho; não tenta responder duas vezes
    return await _orig_defer(self, *args, **kwargs)


discord.InteractionResponse.send_message = _send_message_seguro  # type: ignore[method-assign]
discord.InteractionResponse.edit_message = _edit_message_seguro  # type: ignore[method-assign]
discord.InteractionResponse.defer = _defer_seguro  # type: ignore[method-assign]


async def _auto_defer(interaction: discord.Interaction) -> None:
    await asyncio.sleep(AUTO_DEFER_APOS)
    if interaction.response.is_done():
        return
    _INTERACOES_ADIADAS.add(interaction.id)
    asyncio.get_running_loop().call_later(1000, _INTERACOES_ADIADAS.discard, interaction.id)
    try:
        await _orig_defer(interaction.response)
        log.info("Clique adiado automaticamente (callback passou de %.1fs sem responder).", AUTO_DEFER_APOS)
    except (discord.HTTPException, discord.InteractionResponded):
        _INTERACOES_ADIADAS.discard(interaction.id)


# --- Indicador de "Carregando…" -------------------------------------------------
# Se o callback de um botão/select demora mais de CARREGANDO_APOS segundos, a mensagem
# é editada na hora: todos os botões ficam desativados e o botão clicado mostra
# "⏳ Carregando…". Assim ninguém clica várias vezes achando que travou. Quando o
# callback termina, a view volta ao normal (ou é substituída pela nova tela).
CARREGANDO_APOS = 0.8
_VIEW_CARREGANDO: dict[int, discord.ui.View] = {}
_CARREGANDO_EDITADO: set[int] = set()


async def _mostrar_carregando(view: discord.ui.View, item: Any, interaction: discord.Interaction) -> None:
    await asyncio.sleep(CARREGANDO_APOS)
    if interaction.response.is_done() or interaction.message is None:
        return
    estado = [(c, getattr(c, "disabled", None), getattr(c, "label", None), getattr(c, "emoji", None)) for c in view.children]
    try:
        for c in view.children:
            if hasattr(c, "disabled"):
                c.disabled = True
        if isinstance(item, discord.ui.Button):
            item.label = "⏳ Carregando…"
            item.emoji = None
        # Registra antes de enviar: se o callback responder durante o envio, o redirecionamento já funciona.
        _INTERACOES_ADIADAS.add(interaction.id)
        _VIEW_CARREGANDO[interaction.id] = view
        asyncio.get_running_loop().call_later(1000, _limpar_carregando, interaction.id)
        try:
            await _orig_edit_message(interaction.response, view=view)
        except (discord.HTTPException, discord.InteractionResponded):
            _INTERACOES_ADIADAS.discard(interaction.id)
            _VIEW_CARREGANDO.pop(interaction.id, None)
    finally:
        # O payload já foi serializado: devolve o estado real aos objetos da view.
        for c, disabled, label, emoji in estado:
            if disabled is not None:
                c.disabled = disabled
            if isinstance(c, discord.ui.Button):
                c.label, c.emoji = label, emoji


def _limpar_carregando(id_: int) -> None:
    _VIEW_CARREGANDO.pop(id_, None)
    _CARREGANDO_EDITADO.discard(id_)
    _INTERACOES_ADIADAS.discard(id_)


_orig_scheduled_task = discord.ui.View._scheduled_task


async def _scheduled_task_com_carregando(self: discord.ui.View, item: Any, interaction: discord.Interaction):
    aviso = asyncio.create_task(_mostrar_carregando(self, item, interaction))
    try:
        return await _orig_scheduled_task(self, item, interaction)
    finally:
        aviso.cancel()
        id_ = interaction.id
        if id_ in _VIEW_CARREGANDO and id_ not in _CARREGANDO_EDITADO and not self.is_finished():
            # O callback terminou sem trocar a tela (ex.: só mandou um aviso): libera os botões.
            try:
                await interaction.edit_original_response(view=self)
            except (discord.HTTPException, discord.InteractionResponded):
                log.debug("Não consegui restaurar os botões após o carregamento.", exc_info=True)
        _limpar_carregando(id_)


discord.ui.View._scheduled_task = _scheduled_task_com_carregando  # type: ignore[method-assign]


class NaraCommandTree(app_commands.CommandTree):
    """Tratamento central de erros de slash commands com resposta privada."""

    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        command = getattr(interaction, "command", None)
        command_name = getattr(command, "qualified_name", "comando desconhecido")
        original = error.original if isinstance(error, app_commands.CommandInvokeError) else error

        if _interacao_expirada(error):
            log.warning("Interação expirada em /%s; a resposta chegou após o prazo de 3s (lag do gateway).", command_name)
            return

        # Cogs e comandos já possuem handlers locais; não enviar uma segunda
        # mensagem ao usuário depois que esses handlers trataram a exceção.
        binding = getattr(command, "binding", None)
        has_local_handler = bool(getattr(command, "on_error", None)) or callable(
            getattr(binding, "cog_app_command_error", None)
        )
        if has_local_handler:
            log.error(
                "Erro em /%s encaminhado ao handler local (%s).",
                command_name, type(error).__name__,
                exc_info=(type(original), original, original.__traceback__),
            )
            return

        if isinstance(error, app_commands.CommandInvokeError):
            log.error(
                "Falha ao executar /%s.", command_name,
                exc_info=(type(original), original, original.__traceback__),
            )
            mensagem = (
                "Não consegui concluir essa ação. Nenhuma confirmação foi enviada. "
                "Tente novamente; se persistir, avise a moderação."
            )
        elif isinstance(error, app_commands.MissingPermissions):
            log.warning("Permissão insuficiente ao executar /%s: %s", command_name, error.missing_permissions)
            mensagem = "Você não tem permissão para usar esta função. Peça acesso à moderação do servidor."
        elif isinstance(error, app_commands.BotMissingPermissions):
            log.error("O bot não possui permissões para /%s: %s", command_name, error.missing_permissions)
            mensagem = "Não tenho as permissões necessárias para concluir. A moderação precisa ajustar minhas permissões ou minha posição na hierarquia de cargos."
        elif isinstance(error, app_commands.CommandOnCooldown):
            segundos = max(1, int(error.retry_after + 0.99))
            mensagem = f"Essa ação está em intervalo de segurança. Tente novamente em {segundos} segundo(s)."
        elif isinstance(error, app_commands.CheckFailure):
            log.info("Comando /%s bloqueado por uma verificação de acesso.", command_name)
            mensagem = "Essa função não está disponível para sua conta ou neste canal. Confira as regras e permissões do servidor."
        else:
            log.warning("Erro de interação em /%s: %s", command_name, type(error).__name__, exc_info=(type(error), error, error.__traceback__))
            mensagem = "Não foi possível concluir a solicitação. Tente novamente; se continuar, avise a moderação."

        await _responder_erro_interacao(
            interaction,
            mensagem,
            _contexto_relatorio(interaction, f"/{command_name}", original, mensagem),
        )



DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_ME_URL = "https://discord.com/api/users/@me"
OAUTH_STATE_COOKIE = "soulsbot_oauth_state"
OAUTH_NEXT_COOKIE = "soulsbot_oauth_next"
WEB_SESSION_COOKIE = "soulsbot_web_session"
WEB_SESSION_MAX_AGE = 60 * 60 * 24 * 7


def _web_session_secret() -> bytes:
    """Chave independente para assinar sessão e state; nunca usar o token do bot."""
    value = os.getenv("SOULSBOT_WEB_SESSION_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("SOULSBOT_WEB_SESSION_SECRET ausente ou muito curta (mínimo 32 caracteres).")
    return value.encode("utf-8")


def _assinar_payload(payload: str) -> str:
    assinatura = hmac.new(_web_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{assinatura}"


def _validar_payload_assinado(valor: str) -> str | None:
    try:
        payload, assinatura = valor.rsplit(".", 1)
        esperada = hmac.new(_web_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(assinatura, esperada):
            return None
        return payload
    except (ValueError, RuntimeError):
        return None


def _cookie_seguro(response: web.StreamResponse, nome: str, valor: str, *, max_age: int) -> None:
    response.set_cookie(
        nome, valor, max_age=max_age, httponly=True, secure=True,
        samesite="Lax", path="/",
    )


class NaraBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        intents.presences = True  # Necessário para listar membros Online/Ausente/Não perturbe no Coliseu.
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            tree_cls=NaraCommandTree,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.db = Database(config.DB_PATH)
        self.failed_extensions: list[str] = []
        self.sync_ok = False
        self._slash_sync_done = False
        self._tarefas_auto_defer: set[asyncio.Task] = set()
        self._tarefa_lag: asyncio.Task | None = None
        self._tarefa_anuncios: asyncio.Task | None = None
        self._web_runner: web.AppRunner | None = None
        self._web_presence: dict[int, float] = {}
        self._gwent_bootstrapped: set[int] = set()
        self._gwent_bootstrap_locks: dict[int, asyncio.Lock] = {}
        # Os PNGs são persistidos em disco e enviados por FileResponse; manter cópias
        # completas em bytes na RAM só duplicava memória sem acelerar cache frio.
        self._gwent_image_locks: dict[str, asyncio.Lock] = {}
        # FadeHost Free: 0,25 vCPU / 256 MB. Renderização Pillow é CPU/RAM-bound;
        # uma tarefa pesada por vez evita picos que atrasam também o Gateway Discord.
        try:
            render_workers = int(os.getenv("GWENT_RENDER_CONCURRENCY", "1"))
        except (TypeError, ValueError):
            render_workers = 1
        self._gwent_render_semaphore = asyncio.Semaphore(max(1, min(2, render_workers)))

    def _handle_asyncio_exception(self, loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        exception = context.get("exception")
        message = context.get("message", "Exceção não tratada no event loop")
        if exception is not None:
            log.error("%s", message, exc_info=(type(exception), exception, exception.__traceback__))
        else:
            log.error("%s | contexto=%s", message, {k: str(v)[:300] for k, v in context.items() if k != "task"})

    async def _avisar_vez_gwent(self, match_id: int, alvo_id: int, adversario_id: int) -> None:
        """DM discreta quando chega a vez do jogador (no máx. 1 a cada 5 min por partida)."""
        agora = time.time()
        ultimos = self.__dict__.setdefault("_avisos_vez_gwent", {})
        if agora - ultimos.get((match_id, alvo_id), 0) < 300:
            return
        ultimos[(match_id, alvo_id)] = agora
        if len(ultimos) > 500:
            for k in sorted(ultimos, key=ultimos.get)[:250]:
                ultimos.pop(k, None)
        try:
            guild = self.get_guild(config.GUILD_ID) if config.GUILD_ID else None
            alvo = (guild.get_member(alvo_id) if guild else None) or await self.fetch_user(alvo_id)
            rival = guild.get_member(adversario_id) if guild else None
            base_url = os.getenv("SOULSBOT_PUBLIC_URL", "https://narabot.sbs").rstrip("/")
            nome = rival.display_name if rival else "seu adversário"
            await alvo.send(f"🃏 **Sua vez no Gwent!** {nome} jogou. Continue a partida: {base_url}/?gwent={match_id}")
        except Exception:
            log.info("Não foi possível avisar a vez do Gwent #%s.", match_id)

    async def _loop_anuncios_drops(self) -> None:
        """Anuncia no canal do Coliseu quando um membro ganha carta por contribuir."""
        from admin_config import GuildConfig
        ROTULOS = {"zerado": "zerar um jogo", "platina": "conquistar uma platina", "run": "concluir uma run Soulslike",
                   "soulslike": "concluir uma run Soulslike", "port": "enviar um port", "mod": "enviar um mod",
                   "comunidade": "contribuir com a comunidade", "boas": "entrar na comunidade", "patente": "subir de patente"}
        CORES = {"comum": 0xB9A888, "rara": 0x6FB4EE, "epica": 0xB07AF0, "lendaria": 0xFFD36B,
                 "mitica": 0xFF6FB4, "primordial": 0xFFB84D, "singular": 0x6FF5E1}
        import unicodedata
        while True:
            try:
                await asyncio.sleep(6)
                fila = getattr(self.db, "fila_anuncios", None)
                if not fila:
                    continue
                itens, fila[:] = list(fila), []
                for it in itens:
                    for guild in self.guilds:
                        canal_id = await GuildConfig.get(self.db, guild.id, "colizeu_channel") or config.COLIZEU_CHANNEL_ID
                        canal = self.get_channel(int(canal_id)) if canal_id else None
                        membro = guild.get_member(it["user_id"])
                        if canal is None or membro is None:
                            continue
                        motivo = next((v for k, v in ROTULOS.items() if k in it["origem"]), "contribuir com a comunidade")
                        raridade = str(it["rarity"])
                        chave = unicodedata.normalize("NFD", raridade.lower()).encode("ascii", "ignore").decode()
                        emb = discord.Embed(
                            title="🃏 Nova carta no Coliseu!",
                            description=f"{membro.mention} ganhou **{it['card_name']}** ({raridade}) por {motivo}.\n"
                                        "Contribua também — zerados, platinas, mods e ports rendem cartas. Veja o Mercado do Gwent!",
                            color=CORES.get(chave, 0xD4AF37))
                        await canal.send(embed=emb, allowed_mentions=discord.AllowedMentions(users=[membro]))
                        break
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Falha ao anunciar drops.")

    async def setup_hook(self) -> None:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(self._handle_asyncio_exception)
        self._tarefa_lag = loop.create_task(self._monitorar_lag_loop())
        self._tarefa_anuncios = loop.create_task(self._loop_anuncios_drops())

        await self.db.connect()
        log.info("SQLite conectado: %s", config.DB_PATH)

        await self._iniciar_api_http()

        for extension in EXTENSOES:
            try:
                await self.load_extension(extension)
                log.info("Extensão carregada: %s", extension)
            except Exception:
                self.failed_extensions.append(extension)
                log.exception("Falha ao carregar a extensão %s; o restante do bot continuará iniciando.", extension)

        # A árvore local é reduzida antes de qualquer sincronização.
        # O motor antigo de cartas não é carregado; somente o Gwent permanece ativo.
        removidos = _manter_apenas_comandos_principais(self.tree)
        log.info(
            "Comandos slash locais filtrados: removidos=%s | permitidos=/nara,/jogo,/adm",
            len(removidos),
        )

        if self.failed_extensions:
            log.error("Inicialização parcial: %s extensão(ões) falharam: %s", len(self.failed_extensions), ", ".join(self.failed_extensions))

        # O canal de moderação agora é configurado por servidor no /adm.
        # Não validar apenas MOD_CHANNEL_ID aqui: o valor pode estar salvo no banco.
        if not config.GUILD_ID:
            log.warning("GUILD_ID vazio: /nara, /jogo e /adm serão sincronizados globalmente; a propagação do Discord pode levar algum tempo.")
        if not any((os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_BACKUP_API_KEY"), os.getenv("GEMINI_THIRD_API_KEY"))):
            log.warning("Nenhuma chave Gemini configurada: a Nara continuará com funções locais, mas sem geração de IA.")

    async def _iniciar_api_http(self) -> None:
        """Inicia endpoints públicos mínimos para health-check da hospedagem."""
        porta_raw = os.getenv("PORT", "8080")
        try:
            porta = int(porta_raw)
            if not 1 <= porta <= 65535:
                raise ValueError("porta fora do intervalo permitido")
        except (TypeError, ValueError):
            log.error("API HTTP não iniciada: valor inválido para PORT (%r).", porta_raw)
            return

        site_dir = Path(__file__).resolve().parent / "site"

        async def pagina_inicial(_request: web.Request) -> web.Response:
            index_file = site_dir / "index.html"
            if not index_file.is_file():
                return web.json_response({
                    "service": "NaraBot",
                    "status": "online",
                    "health": "/api/status",
                    "site": "frontend não instalado",
                })
            return web.FileResponse(index_file)

        async def estilo_site(_request: web.Request) -> web.Response:
            arquivo = site_dir / "style.css"
            if not arquivo.is_file():
                raise web.HTTPNotFound(text="CSS do site não encontrado.")
            return web.FileResponse(arquivo)

        async def script_site(_request: web.Request) -> web.Response:
            arquivo = site_dir / "app.js"
            if not arquivo.is_file():
                raise web.HTTPNotFound(text="JavaScript do site não encontrado.")
            return web.FileResponse(arquivo)

        async def elden_ui_css(_request: web.Request) -> web.Response:
            arquivo = site_dir / "elden-ui.css"
            if not arquivo.is_file():
                raise web.HTTPNotFound(text="Sistema visual V49 não encontrado.")
            return web.FileResponse(arquivo)

        async def narabot_visual_css(_request: web.Request) -> web.Response:
            """Entrega a camada visual do construtor de deck (V59)."""
            arquivo = site_dir / "narabot-visual-v59.css"
            if not arquivo.is_file():
                raise web.HTTPNotFound(text="Folha visual V59 não encontrada.")
            return web.FileResponse(arquivo)

        async def status_api(_request: web.Request) -> web.Response:
            return web.json_response({
                "service": "NaraBot-api",
                "status": "online",
                "discord_connected": self.is_ready(),
                "database": "connected",
            })

        app = web.Application(client_max_size=42 * 1024 * 1024)
        app.router.add_get("/", pagina_inicial)
        app.router.add_get("/style.css", estilo_site)
        app.router.add_get("/elden-ui.css", elden_ui_css)
        app.router.add_get("/narabot-visual-v59.css", narabot_visual_css)
        app.router.add_get("/app.js", script_site)
        assets_dir = site_dir / "assets"
        if assets_dir.is_dir():
            app.router.add_static("/assets/", str(assets_dir), show_index=False)
        app.router.add_get("/api/status", status_api)
        app.router.add_get("/auth/discord/login", self._oauth_login)
        app.router.add_get("/auth/discord/callback", self._oauth_callback)
        app.router.add_get("/api/me", self._api_me)
        app.router.add_get("/api/players", self._api_players)
        app.router.add_post("/api/presence/heartbeat", self._api_presence_heartbeat)
        app.router.add_get("/api/gwent/cards", self._api_gwent_cards)
        app.router.add_get("/api/gwent/exemplars", self._api_gwent_exemplars)
        app.router.add_get("/api/gwent/drops/history", self._api_gwent_drop_history)
        app.router.add_post("/api/gwent/evolve", self._api_gwent_evolve)
        app.router.add_post("/api/gwent/upgrade", self._api_gwent_upgrade)
        app.router.add_get("/api/gwent/cards/{card_id}/image", self._api_gwent_card_image)
        app.router.add_get("/api/gwent/atelier/prompt", self._api_gwent_atelier_prompt)
        app.router.add_post("/api/gwent/atelier/submit", self._api_gwent_atelier_submit)
        app.router.add_get("/api/gwent/atelier/history", self._api_gwent_atelier_history)
        app.router.add_get("/api/gwent/atelier/review", self._api_gwent_atelier_review_list)
        app.router.add_get("/api/gwent/atelier/submission/{submission_id}/image", self._api_gwent_atelier_submission_image)
        app.router.add_post("/api/gwent/atelier/review/{submission_id}", self._api_gwent_atelier_review_decide)
        app.router.add_get("/api/gwent/atelier/art/{card_id}", self._api_gwent_atelier_official_art)
        app.router.add_get("/api/gwent/atelier/official/{card_id}", self._api_gwent_atelier_official_metadata)
        app.router.add_post("/api/gwent/atelier/remove-all-art", self._api_gwent_atelier_remove_all_arts)
        app.router.add_get("/api/gwent/atelier/leaders", self._api_gwent_atelier_leaders_list)
        app.router.add_post("/api/gwent/atelier/leaders/{leader_id}/art", self._api_gwent_atelier_leader_art_upload)
        app.router.add_delete("/api/gwent/atelier/leaders/{leader_id}/art", self._api_gwent_atelier_leader_art_remove)
        app.router.add_get("/api/gwent/leaders/{leader_id}/art", self._api_gwent_leader_art)
        app.router.add_get("/api/gwent/store", self._api_gwent_store)
        app.router.add_post("/api/gwent/store/pack", self._api_gwent_store_pack)
        app.router.add_get("/api/gwent/deck", self._api_gwent_deck)
        app.router.add_post("/api/gwent/deck", self._api_gwent_deck_save)
        app.router.add_post("/api/gwent/deck/reset", self._api_gwent_deck_reset)
        app.router.add_get("/api/gwent/matches", self._api_gwent_matches)
        app.router.add_post("/api/gwent/matches", self._api_gwent_match_create)
        app.router.add_post("/api/gwent/matches/solo", self._api_gwent_match_create_solo)
        app.router.add_post("/api/gwent/matches/{match_id}/respond", self._api_gwent_match_respond)
        app.router.add_get("/api/gwent/matches/{match_id}", self._api_gwent_match_detail)
        app.router.add_post("/api/gwent/matches/{match_id}/action", self._api_gwent_match_action)
        app.router.add_post("/auth/logout", self._oauth_logout)
        from site_hub import registrar_rotas as _registrar_hub
        _registrar_hub(self, app)
        from site_portal import registrar_rotas as _registrar_portal
        _registrar_portal(self, app)
        runner = web.AppRunner(app, access_log=None)
        try:
            await runner.setup()
            site = web.TCPSite(runner, host="0.0.0.0", port=porta)
            await site.start()
            self._web_runner = runner
            log.info("API HTTP iniciada em 0.0.0.0:%s | health-check=/api/status", porta)
        except Exception:
            await runner.cleanup()
            log.exception("Não foi possível iniciar a API HTTP na porta %s; o bot Discord continuará iniciando.", porta)

    async def _oauth_login(self, request: web.Request) -> web.Response:
        client_id = os.getenv("DISCORD_OAUTH_CLIENT_ID", "").strip()
        redirect_uri = os.getenv("DISCORD_OAUTH_REDIRECT_URI", "").strip()
        if not client_id or not redirect_uri:
            raise web.HTTPServiceUnavailable(text="Login Discord não configurado.")
        try:
            _web_session_secret()
        except RuntimeError:
            raise web.HTTPServiceUnavailable(text="Chave de sessão do site não configurada.")
        state = secrets.token_urlsafe(32)
        next_path = request.query.get("next", "/")
        if not next_path.startswith("/") or next_path.startswith("//") or "\\" in next_path:
            next_path = "/"
        oauth_params = urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify",
            "state": state,
        })
        response = web.HTTPFound(f"{DISCORD_OAUTH_AUTHORIZE_URL}?{oauth_params}")
        _cookie_seguro(response, OAUTH_STATE_COOKIE, _assinar_payload(state), max_age=600)
        _cookie_seguro(response, OAUTH_NEXT_COOKIE, _assinar_payload(next_path), max_age=600)
        raise response

    async def _oauth_callback(self, request: web.Request) -> web.Response:
        error = request.query.get("error")
        if error:
            raise web.HTTPBadRequest(text="Login Discord cancelado ou recusado.")
        code_oauth = request.query.get("code", "")
        state = request.query.get("state", "")
        state_cookie = request.cookies.get(OAUTH_STATE_COOKIE, "")
        state_validado = _validar_payload_assinado(state_cookie)
        if not code_oauth or not state or not state_validado or not hmac.compare_digest(state, state_validado):
            raise web.HTTPBadRequest(text="Estado OAuth inválido. Inicie o login novamente.")

        client_id = os.getenv("DISCORD_OAUTH_CLIENT_ID", "").strip()
        client_secret = os.getenv("DISCORD_OAUTH_CLIENT_SECRET", "").strip()
        redirect_uri = os.getenv("DISCORD_OAUTH_REDIRECT_URI", "").strip()
        if not all((client_id, client_secret, redirect_uri)):
            raise web.HTTPServiceUnavailable(text="Credenciais OAuth Discord não configuradas.")
        try:
            _web_session_secret()
        except RuntimeError:
            raise web.HTTPServiceUnavailable(text="Chave de sessão do site não configurada.")

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                DISCORD_OAUTH_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "code": code_oauth,
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as token_response:
                if token_response.status != 200:
                    log.warning("Discord OAuth token exchange recusado: HTTP %s.", token_response.status)
                    raise web.HTTPUnauthorized(text="Não foi possível validar o login com Discord.")
                token_data = await token_response.json()

            access_token = token_data.get("access_token")
            if not access_token:
                raise web.HTTPUnauthorized(text="Discord não retornou um token de acesso válido.")

            async with session.get(
                DISCORD_API_ME_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            ) as user_response:
                if user_response.status != 200:
                    log.warning("Discord OAuth user lookup recusado: HTTP %s.", user_response.status)
                    raise web.HTTPUnauthorized(text="Não foi possível identificar sua conta Discord.")
                discord_user = await user_response.json()

        user_id = str(discord_user.get("id", ""))
        if not user_id.isdigit():
            raise web.HTTPUnauthorized(text="Identidade Discord inválida.")

        # A sessão contém apenas o ID autenticado e expiração; nenhum token OAuth é armazenado.
        expires_at = int(time.time()) + WEB_SESSION_MAX_AGE
        session_payload = f"{user_id}:{expires_at}"
        next_cookie = _validar_payload_assinado(request.cookies.get(OAUTH_NEXT_COOKIE, ""))
        next_path = next_cookie if next_cookie and next_cookie.startswith("/") and not next_cookie.startswith("//") else "/"
        response = web.HTTPFound(next_path)
        _cookie_seguro(response, WEB_SESSION_COOKIE, _assinar_payload(session_payload), max_age=WEB_SESSION_MAX_AGE)
        response.del_cookie(OAUTH_STATE_COOKIE, path="/")
        response.del_cookie(OAUTH_NEXT_COOKIE, path="/")
        return response

    def _api_user_id(self, request: web.Request) -> int | None:
        """Valida a sessão assinada do site e retorna o ID Discord autenticado."""
        payload = _validar_payload_assinado(request.cookies.get(WEB_SESSION_COOKIE, ""))
        if not payload:
            return None
        try:
            user_id, expires_raw = payload.split(":", 1)
            expires_at = int(expires_raw)
        except (ValueError, TypeError):
            return None
        if not user_id.isdigit() or expires_at < int(time.time()):
            return None
        return int(user_id)

    def _api_origin_ok(self, request: web.Request) -> bool:
        """Proteção CSRF para ações autenticadas do site; aceita somente origem do próprio host."""
        origin = str(request.headers.get("Origin", "") or "").strip()
        if not origin:
            origin = str(request.headers.get("Referer", "") or "").strip()
        if not origin:
            return False

        def authority(value: str, default_scheme: str) -> tuple[str, int] | None:
            try:
                parsed = urlsplit(value if "://" in value else f"{default_scheme}://{value}")
                if not parsed.hostname:
                    return None
                scheme = parsed.scheme.casefold()
                if scheme not in {"http", "https"}:
                    return None
                port = parsed.port or (443 if scheme == "https" else 80)
                return parsed.hostname.casefold(), port
            except (TypeError, ValueError):
                return None

        origin_key = authority(origin, request.scheme)
        if origin_key is None:
            return False
        # Em produção, o app pode estar atrás de um proxy HTTPS. O host
        # interno (ex.: 127.0.0.1:8080) não corresponde ao Origin do navegador.
        allowed = {authority(str(request.host), request.scheme)}
        forwarded_host = str(request.headers.get("X-Forwarded-Host", "") or "").split(",", 1)[0].strip()
        forwarded_proto = str(request.headers.get("X-Forwarded-Proto", "") or "").split(",", 1)[0].strip()
        if forwarded_host:
            allowed.add(authority(
                f"{forwarded_proto}://{forwarded_host}" if forwarded_proto else forwarded_host,
                request.scheme,
            ))
        public_url = str(os.getenv("SOULSBOT_PUBLIC_URL", "https://narabot.sbs") or "").strip()
        if public_url:
            allowed.add(authority(public_url, "https"))
        allowed.discard(None)
        return origin_key in allowed

    async def _api_presence_heartbeat(self, request: web.Request) -> web.Response:
        """Marca o jogador como online no site por até 75 segundos."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        self._web_presence[user_id] = time.time()
        return web.json_response({"ok": True, "expires_in": 75})

    async def _api_players(self, request: web.Request) -> web.Response:
        """Lista membros humanos do servidor configurado e combina presença Discord/site."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        try:
            guild_id = int(getattr(config, "GUILD_ID", 0) or 0)
        except (TypeError, ValueError):
            guild_id = 0
        guild = self.get_guild(guild_id) if guild_id else None
        if guild is None:
            return web.json_response({"error": "Servidor do NARABOT indisponível."}, status=503)
        now = time.time()
        # Heartbeats expirados não são tratados como usuários online no site.
        self._web_presence = {uid: stamp for uid, stamp in self._web_presence.items() if now - stamp <= 75}
        players = []
        for member in guild.members:
            if member.bot:
                continue
            status = str(member.status)
            players.append({
                "id": str(member.id), "name": member.display_name,
                "discord_presence": status,
                "web_online": member.id in self._web_presence,
                "is_self": member.id == user_id,
            })
        players.sort(key=lambda item: (not item["web_online"], item["discord_presence"] == "offline", item["name"].casefold()))
        return web.json_response({"players": players, "server": guild.name})

    async def _gwent_generated_card_payload(self, user_id: int, card_id: str, exemplar: dict):
        """Resolve uma carta procedural apenas para o proprietário autenticado."""
        import json
        row = await self.db._one(
            "SELECT definition_json,status,art_path FROM cartas_geradas WHERE owner_id=? AND card_id=?",
            (int(user_id), str(card_id)),
        )
        if not row or str(row["status"] or "") != "published":
            return None
        try:
            definition = json.loads(row["definition_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        from sistemas.gwent import preparar_carta_pessoal
        card = preparar_carta_pessoal(definition, exemplar, owner_id=int(user_id))
        if card is None:
            return None
        card["image_url"] = f"/api/gwent/atelier/art/{quote(card_id, safe='')}"
        return card

    async def _api_gwent_deck(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        await self._gwent_prepare_user(user_id)
        import json
        row = await self.db._one(
            "SELECT card_ids_json, exemplar_ids_json, faction, leader_id, relic_id FROM cartas_gwent_decks WHERE user_id=?",
            (user_id,),
        )
        ids = json.loads(row["card_ids_json"]) if row else []
        exemplar_ids = json.loads(row["exemplar_ids_json"] or "[]") if row and row["exemplar_ids_json"] else []
        exemplars = await self.db.coliseu_listar_exemplares(user_id)
        exemplar_by_id = {int(e["id"]): e for e in exemplars}
        owned = await self.db.coliseu_listar_colecao(user_id)
        game_by_id = {str(r["card_id"]): str(r["game_name"] or "") for r in owned}
        from sistemas.cartas import get_carta, carta_de_jogo_por_id, CUSTO_RARIDADE, faixa_poder_exemplar, VERSAO_ARTES
        from sistemas.gwent import preparar_carta, RARITY_EFFECT_BUDGET
        cards = []
        for index, card_id in enumerate(ids):
            exemplar_id = int(exemplar_ids[index]) if index < len(exemplar_ids) and exemplar_ids[index] else 0
            record = exemplar_by_id.get(exemplar_id) if exemplar_id else None
            # Compatibilidade com decks anteriores: selecionar o melhor exemplar disponível.
            if record is None or str(record["card_id"]) != str(card_id):
                candidates = [e for e in exemplars if str(e["card_id"]) == str(card_id)]
                order = {"Singular": 7, "Primordial": 6, "Mítica": 5, "Lendária": 4, "Épica": 3, "Rara": 2, "Comum": 1}
                record = max(candidates, key=lambda e: (order.get(str(e["rarity"]), 0), int(e["power"]), -int(e["id"]))) if candidates else None
            if not record:
                continue
            game_name = game_by_id.get(str(card_id), "")
            if record and str(card_id).startswith("transmutacao_"):
                personal = await self._gwent_generated_card_payload(user_id, str(card_id), record)
                if personal:
                    personal["potencia_raridade"] = int(RARITY_EFFECT_BUDGET.get(str(personal.get("raridade", "Comum")), 0))
                    cards.append(personal)
                continue
            card = get_carta(str(card_id))
            if card is None and str(card_id).startswith("jogo_") and game_name:
                try:
                    card = carta_de_jogo_por_id(str(card_id), game_name)
                except ValueError:
                    card = None
            if card:
                payload = card.para_dict()
                rarity = str(record["rarity"] or payload.get("raridade", "Comum"))
                payload["raridade"] = rarity
                payload["poder"] = int(record["power"] or payload.get("poder", 0))
                payload["custo"] = int(CUSTO_RARIDADE.get(rarity, payload.get("custo", 0)))
                item = preparar_carta(payload)
                item["card_id"] = str(card_id)
                item["exemplar_id"] = int(record["id"])
                item["id"] = f"{card_id}::{int(record['id'])}"
                item["max_power"] = faixa_poder_exemplar(card, rarity)[1]
                item["potencia_raridade"] = int(RARITY_EFFECT_BUDGET.get(rarity, 0))
                item["image_url"] = (
                    f"/api/gwent/cards/{quote(card_id, safe='')}/image"
                    f"?exemplar_id={int(record['id'])}&v={VERSAO_ARTES}"
                )
                cards.append(item)
        from sistemas.gwent import LEADERS, DEFAULT_LEADERS, FACTIONS, canonical_faction
        faction = canonical_faction(str(row["faction"] or "") if row else "") or ""
        if faction not in DEFAULT_LEADERS:
            counts = {"Força": 0, "Destreza": 0, "Magia": 0}
            for card in cards:
                if card.get("categoria", "").casefold() != "especial" and card.get("tipo") in counts:
                    counts[card["tipo"]] += 1
            inferred_type = max(counts, key=lambda kind: (counts[kind], kind))
            faction = FACTIONS[inferred_type]
        leader_id = str(row["leader_id"] or "") if row else ""
        if leader_id not in LEADERS or LEADERS[leader_id]["faction"] != faction:
            leader_id = DEFAULT_LEADERS[faction]
        leader_art_rows = await self.db.coliseu_gwent_lideres_artes_listar()
        leader_art_map = {str(item["leader_id"]): dict(item) for item in leader_art_rows}
        default_leader_assets = {
            "comandante_fornalha": "godfrey", "bastiao_ancestral": "morgott",
            "juiz_cerco": "radagon", "mestre_veu": "mohg",
            "sombra_caminhante": "rykard", "voz_caidos": "esgar",
            "arquimaga_eclipse": "rennala", "mestre_eclipse": "astel",
            "oraculo_tempestade": "loretta",
        }
        def leader_payload(key, value):
            art = leader_art_map.get(key)
            version = str(art.get("revision", "") if art else "")[:20]
            return {
                "id": key, "name": value["name"], "description": value["description"],
                "visual_only": True, "power": None, "cost": None, "rarity": "Lendária",
                "card_type": "Líder",
                "art_url": f"/api/gwent/leaders/{key}/art?v={version}" if art else "",
                "default_art_url": f"/assets/leaders/{default_leader_assets.get(key, 'godfrey')}.webp",
            }
        leaders = [leader_payload(key, value) for key, value in LEADERS.items() if value["faction"] == faction]
        return web.json_response({
            "deck": cards, "faction": faction, "leader_id": leader_id,
            "leaders": leaders,
            "leaders_by_faction": {
                name: [leader_payload(key, value)
                       for key, value in LEADERS.items() if value["faction"] == name]
                for name in DEFAULT_LEADERS},
            "factions": [{"name": name, "preferred_type": kind,
                          "description": {"Ordem Áurea": "Formação e resistência na linha de frente.",
                                          "Véu Carmesim": "Sangue, sacrifício e rituais de heresia.",
                                          "Lua Negra": "Magia lunar, cosmos e segredos arcanos."}[name]}
                         for kind, name in FACTIONS.items()],
            "relic_id": str(row["relic_id"] or "") if row else "",
            "rules": {"cards": 12, "opening_hand": 10, "reserve": 2, "unique": True, "relics_per_match": 1}})

    async def _api_gwent_deck_save(self, request: web.Request) -> web.Response:
        import json
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            body = await request.json()
            raw_cards = body.get("cards")
            if isinstance(raw_cards, list):
                entries = [(str(item.get("card_id", "")), int(item.get("exemplar_id", 0)))
                           for item in raw_cards if isinstance(item, dict)]
            else:
                # Compatibilidade com clientes antigos: usa o exemplar mais forte de cada modelo.
                entries = [(str(card_id), 0) for card_id in body.get("card_ids", [])]
            faction = str(body.get("faction", "Ordem Áurea"))
            leader_id = str(body.get("leader_id", "comandante_fornalha"))
            relic_id = str(body.get("relic_id", ""))
        except Exception:
            return web.json_response({"error": "JSON inválido ou exemplar inválido."}, status=400)
        ids = [entry[0] for entry in entries]
        if (len(entries) != 12 or any(not card_id or len(card_id) > 120 or exemplar_id < 0 for card_id, exemplar_id in entries)
                or len(set(ids)) != 12):
            return web.json_response({"error": "O deck Gwent exige exatamente 12 modelos diferentes."}, status=400)
        if relic_id and relic_id in ids:
            return web.json_response({"error": "A Relíquia equipada não pode ocupar também uma das 12 posições do deck."}, status=400)
        from sistemas.gwent import (DEFAULT_LEADERS, LEADERS, canonical_faction,
                                    validar_faccao_deck)
        faction = canonical_faction(faction) or "Ordem Áurea"
        if faction not in DEFAULT_LEADERS:
            return web.json_response({"error": "Facção inválida."}, status=400)
        if leader_id not in LEADERS or LEADERS[leader_id]["faction"] != faction:
            return web.json_response({"error": "O líder selecionado não pertence à facção escolhida."}, status=400)
        valid_relics = {"", "reliquia_grande_runa_godrick", "reliquia_runa_nao_nascidos", "reliquia_runa_morte", "reliquia_noite_chama", "reliquia_lamina_negra", "reliquia_algemas_margit"}
        if relic_id not in valid_relics:
            return web.json_response({"error": "Relíquia inválida."}, status=400)
        exemplars = await self.db.coliseu_listar_exemplares(user_id)
        by_exemplar = {int(e["id"]): e for e in exemplars}
        resolved = []
        for card_id, exemplar_id in entries:
            if not exemplar_id:
                candidates = [e for e in exemplars if str(e["card_id"]) == card_id]
                order = {"Singular": 7, "Primordial": 6, "Mítica": 5, "Lendária": 4, "Épica": 3, "Rara": 2, "Comum": 1}
                exemplar = max(candidates, key=lambda e: (order.get(str(e["rarity"]), 0), int(e["power"]), -int(e["id"]))) if candidates else None
            else:
                exemplar = by_exemplar.get(exemplar_id)
            if not exemplar or str(exemplar["card_id"]) != card_id:
                return web.json_response({"error": f"O exemplar selecionado não pertence à carta {card_id}."}, status=403)
            resolved.append(int(exemplar["id"]))
        from sistemas.cartas import get_carta, carta_de_jogo_por_id
        owned_rows = await self.db.coliseu_listar_colecao(user_id)
        game_by_id = {str(item["card_id"]): str(item["game_name"] or "") for item in owned_rows}
        unit_count = 0
        special_count = 0
        faction_units = []
        for card_id, exemplar_id in entries:
            card = get_carta(card_id)
            if card is None and card_id.startswith("transmutacao_"):
                generated = await self.db._one(
                    "SELECT definition_json,status FROM cartas_geradas WHERE owner_id=? AND card_id=?",
                    (int(user_id), card_id),
                )
                if not generated or str(generated["status"] or "") != "published":
                    return web.json_response({"error": f"Carta pessoal indisponível: {card_id}."}, status=403)
                try:
                    definition = json.loads(generated["definition_json"] or "{}")
                except (TypeError, ValueError, json.JSONDecodeError):
                    return web.json_response({"error": f"Definição inválida: {card_id}."}, status=409)
                if (definition.get("card_id") != card_id or definition.get("owner_scoped") is not True
                        or definition.get("origem_tipo") != "transmutacao"
                        or definition.get("is_sacrificable") is not False
                        or definition.get("categoria") != "Unidade"):
                    return web.json_response({"error": f"Carta pessoal inválida: {card_id}."}, status=409)
                unit_count += 1
                faction_units.append({"tipo": str(definition.get("tipo", "")), "categoria": "Unidade"})
            elif card is None and card_id.startswith("jogo_"):
                game_name = game_by_id.get(card_id, "")
                if not game_name:
                    return web.json_response({"error": f"Carta de jogo não pertence à sua coleção: {card_id}."}, status=403)
                try:
                    game_card = carta_de_jogo_por_id(card_id, game_name)
                except ValueError:
                    return web.json_response({"error": f"Carta de jogo inválida: {card_id}."}, status=409)
                unit_count += 1
                faction_units.append({"tipo": str(game_card.tipo), "categoria": str(game_card.categoria)})
            elif card is None:
                return web.json_response({"error": f"Carta inválida no deck: {card_id}."}, status=400)
            elif str(card.categoria).casefold() == "especial":
                special_count += 1
            else:
                unit_count += 1
                faction_units.append({"tipo": str(card.tipo), "categoria": str(card.categoria)})
        faction_ok, faction_counts = validar_faccao_deck(faction_units, faction)
        if not faction_ok:
            counts_text = " · ".join(f"{name}: {count}" for name, count in faction_counts.items())
            return web.json_response({
                "error": f"A facção escolhida precisa ser a predominante entre suas unidades. Distribuição atual: {counts_text}."
            }, status=400)
        if unit_count < 8 or special_count > 4:
            return web.json_response({"error": "O deck precisa ter pelo menos 8 unidades e no máximo 4 cartas especiais."}, status=400)
        import json
        async with self.db.transaction() as tx:
            await tx.conn.execute(
                """INSERT INTO cartas_gwent_decks(user_id,card_ids_json,exemplar_ids_json,faction,leader_id,relic_id)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET card_ids_json=excluded.card_ids_json,
                   exemplar_ids_json=excluded.exemplar_ids_json, faction=excluded.faction,
                   leader_id=excluded.leader_id, relic_id=excluded.relic_id, updated_at=CURRENT_TIMESTAMP""",
                (user_id, json.dumps(ids), json.dumps(resolved), faction, leader_id, relic_id))
        return web.json_response({"ok": True, "card_ids": ids, "exemplar_ids": resolved,
                                  "faction": faction, "leader_id": leader_id, "relic_id": relic_id})

    async def _api_gwent_deck_reset(self, request: web.Request) -> web.Response:
        """Zera somente o deck do jogador autenticado; coleção e exemplares são preservados."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        await self._gwent_prepare_user(user_id)
        from sistemas.gwent import DEFAULT_LEADERS
        faction = "Ordem Áurea"
        leader_id = DEFAULT_LEADERS[faction]
        result = await self.db.coliseu_gwent_zerar_deck(user_id, faction, leader_id)
        return web.json_response({
            **result, "message": "Deck zerado. Sua coleção permanece intacta.",
        })

    async def _gwent_deck_snapshots(self, user_id: int):
        import json
        from sistemas.cartas import get_carta, carta_de_jogo_por_id, CUSTO_RARIDADE
        from sistemas.gwent import preparar_carta
        row = await self.db._one(
            "SELECT card_ids_json, exemplar_ids_json FROM cartas_gwent_decks WHERE user_id=?", (user_id,))
        if not row:
            return None
        ids = json.loads(row["card_ids_json"])
        exemplar_ids = json.loads(row["exemplar_ids_json"] or "[]") if row["exemplar_ids_json"] else []
        exemplars = await self.db.coliseu_listar_exemplares(user_id)
        exemplar_by_id = {int(e["id"]): e for e in exemplars}
        owned_rows = await self.db.coliseu_listar_colecao(user_id)
        game_by_id = {str(r["card_id"]): str(r["game_name"] or "") for r in owned_rows}
        cards = []
        for index, card_id in enumerate(ids):
            exemplar_id = int(exemplar_ids[index]) if index < len(exemplar_ids) and exemplar_ids[index] else 0
            record = exemplar_by_id.get(exemplar_id) if exemplar_id else None
            if record is None or str(record["card_id"]) != str(card_id):
                candidates = [e for e in exemplars if str(e["card_id"]) == str(card_id)]
                order = {"Singular": 7, "Primordial": 6, "Mítica": 5, "Lendária": 4, "Épica": 3, "Rara": 2, "Comum": 1}
                record = max(candidates, key=lambda e: (order.get(str(e["rarity"]), 0), int(e["power"]), -int(e["id"]))) if candidates else None
            if record is None:
                return None
            if str(card_id).startswith("transmutacao_"):
                personal = await self._gwent_generated_card_payload(user_id, str(card_id), record)
                if not personal:
                    return None
                cards.append(personal)
                continue
            card = get_carta(card_id)
            if card is None and card_id.startswith("jogo_") and game_by_id.get(card_id):
                try:
                    card = carta_de_jogo_por_id(card_id, game_by_id[card_id])
                except ValueError:
                    card = None
            if card is None:
                return None
            payload = card.para_dict()
            rarity = str(record["rarity"] or payload.get("raridade", "Comum"))
            payload["raridade"] = rarity
            payload["poder"] = int(record["power"] or payload.get("poder", 0))
            payload["custo"] = int(CUSTO_RARIDADE.get(rarity, payload.get("custo", 0)))
            cards.append(preparar_carta(payload))
        return cards if len(cards) == 12 else None

    async def _api_gwent_matches(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None: return web.json_response({"error": "Autenticação necessária."}, status=401)
        rows = await self.db._all("SELECT id,creator_id,opponent_id,status,created_at FROM cartas_gwent_matches WHERE creator_id=? OR opponent_id=? ORDER BY id DESC LIMIT 30", (user_id,user_id))
        rank = await self.db._one("SELECT mmr,wins,losses,draws FROM cartas_gwent_rankings WHERE user_id=?", (user_id,))
        rank = dict(rank) if rank else {"mmr": 1000, "wins": 0, "losses": 0, "draws": 0}
        rank["tier"] = "Bronze" if rank["mmr"] < 1100 else "Prata" if rank["mmr"] < 1300 else "Ouro" if rank["mmr"] < 1550 else "Diamante"
        top_rows = await self.db._all("SELECT user_id,mmr,wins,losses,draws FROM cartas_gwent_rankings ORDER BY mmr DESC,wins DESC LIMIT 10")
        guild = self.get_guild(int(getattr(config, "GUILD_ID", 0) or 0))
        leaderboard = []
        for item in top_rows:
            member = guild.get_member(int(item["user_id"])) if guild else None
            leaderboard.append({"user_id": str(item["user_id"]), "name": member.display_name if member else f"Jogador {str(item['user_id'])[-4:]}",
                                "mmr": int(item["mmr"]), "wins": int(item["wins"])})
        return web.json_response({"ranking": rank, "leaderboard": leaderboard,
            "matches": [{"id": int(r["id"]), "creator_id": str(r["creator_id"]), "opponent_id": str(r["opponent_id"]), "is_ai_match": int(r["opponent_id"]) == -1, "status": r["status"], "created_at": r["created_at"]} for r in rows]})

    async def _api_gwent_match_create(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            body = await request.json()
            opponent_id = int(body.get("opponent_id", 0))
        except Exception:
            return web.json_response({"error": "Jogador inválido."}, status=400)
        if opponent_id <= 0 or opponent_id == user_id:
            return web.json_response({"error": "Escolha outro jogador."}, status=400)

        guild = self.get_guild(int(getattr(config, "GUILD_ID", 0) or 0))
        if not guild or not guild.get_member(user_id) or not guild.get_member(opponent_id):
            return web.json_response({"error": "Os dois jogadores precisam estar no servidor."}, status=404)

        deck_a = await self._gwent_deck_snapshots(user_id)
        deck_b = await self._gwent_deck_snapshots(opponent_id)
        if not deck_a or not deck_b:
            return web.json_response({"error": "Os dois jogadores precisam salvar um deck Gwent de 12 cartas."}, status=409)

        import json
        configs = {}
        for participant_id in (user_id, opponent_id):
            saved = await self.db._one(
                "SELECT faction,leader_id,relic_id FROM cartas_gwent_decks WHERE user_id=?",
                (participant_id,),
            )
            if saved:
                configs[str(participant_id)] = {
                    "faction": canonical_faction(str(saved["faction"] or "")) or "",
                    "leader_id": str(saved["leader_id"] or ""),
                    "relic_id": str(saved["relic_id"] or ""),
                }

        # A partida só começa depois da aceitação. O snapshot impede que alterações
        # posteriores nos decks modifiquem uma disputa já enviada.
        invitation = {
            "pending_invitation": True,
            "decks": {str(user_id): deck_a, str(opponent_id): deck_b},
            "configs": configs,
        }
        async with self.db.transaction() as tx:
            for participant_id in (user_id, opponent_id):
                active = await tx._one(
                    """SELECT COUNT(*) AS n FROM cartas_gwent_matches
                       WHERE status IN ('active','pending') AND (creator_id=? OR opponent_id=?)""",
                    (participant_id, participant_id),
                )
                if int(active["n"] or 0) >= 3:
                    return web.json_response(
                        {"error": "Um dos jogadores já possui três partidas ou convites em andamento."},
                        status=409,
                    )
            cur = await tx.conn.execute(
                "INSERT INTO cartas_gwent_matches(creator_id,opponent_id,status,state_json) VALUES (?,?, 'pending',?)",
                (user_id, opponent_id, json.dumps(invitation, ensure_ascii=False)),
            )
            match_id = int(cur.lastrowid)

        # Aviso por DM é auxiliar; o convite também aparece na lista do site.
        try:
            opponent = guild.get_member(opponent_id)
            base_url = os.getenv("SOULSBOT_PUBLIC_URL", "https://narabot.sbs").rstrip("/")
            await opponent.send(
                f"⚔️ Você recebeu um convite para uma partida Gwent no NARABOT. "
                f"Entre no site para aceitar ou recusar: {base_url}/?gwent={match_id}"
            )
        except Exception:
            log.info("Não foi possível enviar DM do convite Gwent #%s.", match_id)
        return web.json_response({"ok": True, "match_id": match_id, "status": "pending"}, status=201)

    async def _api_gwent_match_create_solo(self, request: web.Request) -> web.Response:
        """Cria uma partida de treino contra a NARA sem depender de outro membro."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)

        deck = await self._gwent_deck_snapshots(user_id)
        if not deck or len(deck) != 12:
            return web.json_response({"error": "Salve primeiro um deck Gwent válido com 12 cartas."}, status=409)

        import copy
        import json
        from sistemas.gwent import (AI_PLAYER_ID, DEFAULT_LEADERS, aplicar_jogada,
                                    novo_estado, canonical_faction, embaralhar_deck)

        saved = await self.db._one(
            "SELECT faction,leader_id,relic_id FROM cartas_gwent_decks WHERE user_id=?", (user_id,)
        )
        human_config = {
            "faction": canonical_faction(str(saved["faction"] or "")) if saved else "",
            "leader_id": str(saved["leader_id"] or "") if saved else "",
            "relic_id": str(saved["relic_id"] or "") if saved else "",
        }
        faction = human_config["faction"]
        ai_config = {
            "faction": faction,
            # O modo treino é espelhado: mesma facção e líder evitam vantagem
            # artificial de coleção; a IA recebe outra ordem de compra.
            "leader_id": human_config["leader_id"] or DEFAULT_LEADERS.get(faction, ""),
            "relic_id": human_config["relic_id"],
        }
        ai_deck = copy.deepcopy(deck)

        async with self.db.transaction() as tx:
            active = await tx._one(
                """SELECT COUNT(*) AS n FROM cartas_gwent_matches
                   WHERE status IN ('active','pending') AND (creator_id=? OR opponent_id=?)""",
                (user_id, user_id),
            )
            if int(active["n"] or 0) >= 3:
                return web.json_response(
                    {"error": "Você já possui três partidas ou convites em andamento."}, status=409
                )

            # Garante as duas referências exigidas pela FK da tabela de partidas.
            # O registro negativo é uma identidade técnica reservada: nunca recebe
            # ranking, XP, moeda ou recompensa competitiva.
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (AI_PLAYER_ID,))
            cursor = await tx.conn.execute(
                "INSERT INTO cartas_gwent_matches(creator_id,opponent_id,status,state_json) VALUES (?,?, 'active','{}')",
                (user_id, AI_PLAYER_ID),
            )
            match_id = int(cursor.lastrowid)

            decks = {
                str(user_id): embaralhar_deck(deck),
                str(AI_PLAYER_ID): embaralhar_deck(ai_deck),
            }
            configs = {str(user_id): human_config, str(AI_PLAYER_ID): ai_config}
            state = novo_estado(match_id, user_id, AI_PLAYER_ID, decks, configs)
            state["is_ai_match"] = True
            state["ai_difficulty"] = "normal"

            # A NARA conclui a preparação antes do usuário. A troca inicial humana
            # continua independente e a partida só entra em batalha após a escolha dele.
            setup = aplicar_jogada(state, AI_PLAYER_ID, action="keep")
            if "error" in setup:
                raise RuntimeError(f"Falha ao preparar a NARA: {setup['error']}")
            state = setup["state"]
            await tx.conn.execute(
                "UPDATE cartas_gwent_matches SET state_json=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (json.dumps(state, ensure_ascii=False), match_id),
            )

        return web.json_response({
            "ok": True, "match_id": match_id, "status": "active",
            "opponent": "NARA", "mode": "solo", "difficulty": "normal",
            "rewards": False,
        }, status=201)

    async def _api_gwent_match_respond(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            match_id = int(request.match_info["match_id"])
            body = await request.json()
            action = str(body.get("action", "")).casefold()
        except Exception:
            return web.json_response({"error": "Resposta ao convite inválida."}, status=400)
        if action not in {"accept", "decline", "cancel"}:
            return web.json_response({"error": "Ação de convite inválida."}, status=400)

        import json
        async with self.db.transaction() as tx:
            row = await tx._one("SELECT * FROM cartas_gwent_matches WHERE id=?", (match_id,))
            if not row:
                return web.json_response({"error": "Convite não encontrado."}, status=404)
            creator_id = int(row["creator_id"])
            opponent_id = int(row["opponent_id"])
            if action in {"accept", "decline"} and user_id != opponent_id:
                return web.json_response({"error": "Somente o adversário convidado pode responder."}, status=403)
            if action == "cancel" and user_id != creator_id:
                return web.json_response({"error": "Somente quem enviou o convite pode cancelá-lo."}, status=403)
            if row["status"] != "pending":
                return web.json_response({"error": "Este convite já foi respondido ou não está mais disponível."}, status=409)

            if action == "accept":
                invitation = json.loads(row["state_json"] or "{}")
                if not invitation.get("pending_invitation"):
                    return web.json_response({"error": "Dados do convite inválidos."}, status=409)
                from sistemas.gwent import novo_estado, embaralhar_deck
                match_decks = invitation.get("decks", {})
                # O embaralhamento acontece somente após a aceitação, usando CSPRNG.
                match_decks = {uid: embaralhar_deck(deck) for uid, deck in match_decks.items()}
                state = novo_estado(
                    match_id, creator_id, opponent_id,
                    match_decks, invitation.get("configs", {}),
                )
                cursor = await tx.conn.execute(
                    "UPDATE cartas_gwent_matches SET status='active',state_json=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'",
                    (json.dumps(state, ensure_ascii=False), match_id),
                )
                if cursor.rowcount != 1:
                    return web.json_response({"error": "O convite já foi respondido."}, status=409)
                result_status = "active"
            else:
                result_status = "declined" if action == "decline" else "cancelled"
                cursor = await tx.conn.execute(
                    "UPDATE cartas_gwent_matches SET status=?,state_json='{}',updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'",
                    (result_status, match_id),
                )
                if cursor.rowcount != 1:
                    return web.json_response({"error": "O convite já foi respondido."}, status=409)

        # A notificação não faz parte da transação: falha de DM não desfaz a resposta.
        try:
            guild = self.get_guild(int(getattr(config, "GUILD_ID", 0) or 0))
            notified_id = creator_id if action in {"accept", "decline"} else opponent_id
            notified = guild.get_member(notified_id) if guild else None
            if notified:
                base_url = os.getenv("SOULSBOT_PUBLIC_URL", "https://narabot.sbs").rstrip("/")
                if result_status == "active":
                    message = f"⚔️ Seu convite Gwent #{match_id} foi aceito. Entre na arena: {base_url}/?gwent={match_id}"
                elif result_status == "declined":
                    message = f"O convite Gwent #{match_id} foi recusado."
                else:
                    message = f"O convite Gwent #{match_id} foi cancelado."
                await notified.send(message)
        except Exception:
            log.info("Não foi possível enviar a notificação da resposta ao convite Gwent #%s.", match_id)

        return web.json_response({"ok": True, "match_id": match_id, "status": result_status})

    async def _api_gwent_match_detail(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None: return web.json_response({"error": "Autenticação necessária."}, status=401)
        try: match_id = int(request.match_info["match_id"])
        except ValueError: return web.json_response({"error": "Partida inválida."}, status=400)
        row = await self.db._one("SELECT * FROM cartas_gwent_matches WHERE id=?", (match_id,))
        if not row or user_id not in (int(row["creator_id"]), int(row["opponent_id"])): return web.json_response({"error": "Partida não encontrada."}, status=404)
        if row["status"] not in {"active", "finished"}:
            return web.json_response({"match_id": match_id, "status": str(row["status"])})
        import json
        from sistemas.gwent import placar
        state = json.loads(row["state_json"])
        reward_row = await self.db._one(
            """SELECT reward_denarios,reward_xp,mmr_delta,drop_event_key,milestone_drop_event_key
               FROM cartas_gwent_rewards WHERE match_id=? AND user_id=?""",
            (match_id, user_id),
        )
        reward_drops = []
        if reward_row:
            for event_key in (str(reward_row["drop_event_key"] or ""),
                              str(reward_row["milestone_drop_event_key"] or "")):
                if not event_key:
                    continue
                drop_row = await self.db._one(
                    """SELECT card_id,rarity,outcome,exemplar_id,power,origin,almas_delta,fragmentos_delta
                       FROM cartas_recompensas WHERE event_key=?""", (event_key,))
                if drop_row:
                    from sistemas.cartas import get_carta
                    model = get_carta(str(drop_row["card_id"] or ""))
                    reward_drops.append({
                        "card_id": str(drop_row["card_id"] or ""),
                        "card_name": model.nome if model else str(drop_row["card_id"] or "Carta"),
                        "rarity": str(drop_row["rarity"]),
                        "outcome": str(drop_row["outcome"]), "exemplar_id": drop_row["exemplar_id"],
                        "power": int(drop_row["power"] or 0), "origin": str(drop_row["origin"] or ""),
                        "almas_delta": int(drop_row["almas_delta"] or 0),
                        "fragmentos_delta": int(drop_row["fragmentos_delta"] or 0),
                    })
        own = state["players"][str(user_id)]
        opponent_id = next((uid for uid in state["players"] if uid != str(user_id)), "")
        opponent = state["players"].get(opponent_id, {})
        guild = self.get_guild(int(getattr(config, "GUILD_ID", 0) or 0))
        is_ai_match = bool(state.get("is_ai_match") or opponent_id == "-1")
        opponent_member = guild.get_member(int(opponent_id)) if guild and str(opponent_id).isdigit() and not is_ai_match else None
        opponent_name = "NARA · Adversária IA" if is_ai_match else (opponent_member.display_name if opponent_member else f"Jogador {opponent_id[-4:]}")
        from sistemas.gwent import LEADERS, opcoes_de_alvo, opcoes_de_reliquia
        leader_id = own.get("leader_id", "")
        # O histórico interno guarda score_a/score_b na ordem em que os jogadores
        # foram inseridos (criador, desafiante). Convertemos para a perspectiva
        # do usuário para a UI mostrar corretamente vitória/derrota/empate.
        player_order = list(state.get("players", {}).keys())
        round_history = []
        for item in state.get("rounds", []):
            score_by_player = {}
            if len(player_order) >= 2:
                score_by_player[player_order[0]] = int(item.get("score_a", 0))
                score_by_player[player_order[1]] = int(item.get("score_b", 0))
            round_winner = str(item.get("winner_id")) if item.get("winner_id") is not None else None
            round_history.append({
                "round": int(item.get("round", 0)),
                "your_score": score_by_player.get(str(user_id), 0),
                "opponent_score": score_by_player.get(opponent_id, 0),
                "winner_id": round_winner,
                "result": "draw" if round_winner is None else ("win" if round_winner == str(user_id) else "loss"),
            })
        public = {
            "match_id": match_id, "status": state["status"], "phase": state.get("phase", "battle"),
            "is_ai_match": is_ai_match, "ai_difficulty": state.get("ai_difficulty", ""),
            "round": state["round"], "turn": state["turn"], "crowns": state["crowns"],
            "winner_id": state["winner_id"], "last_event": state["last_event"],
            "score": placar(state), "hand": own["hand"], "leader_used": own["leader_used"],
            "alvos": opcoes_de_alvo(state, user_id),
            "relic_options": opcoes_de_reliquia(state, user_id),
            "equipped_relic_id": own.get("equipped_relic_id", ""),
            "relic_used": own.get("relic_used", False),
            "weather_used": own.get("weather_used", False), "weather": state.get("weather", {}),
            "is_your_turn": state["turn"] == str(user_id), "your_id": str(user_id),
            "rounds": round_history, "mulligan_done": own.get("mulligan_done", True),
            "discard_count": len(own.get("discard", [])), "draw_count": len(own.get("draw_pile", [])),
            "faction": own.get("faction", ""),
            "leader_id": leader_id,
            "leader_name": own.get("leader_name", "Líder"),
            "leader_description": LEADERS.get(leader_id, {}).get("description", ""),
            "opponent": {
                "id": opponent_id,
                "name": opponent_name,
                "faction": opponent.get("faction", ""),
                "leader_name": opponent.get("leader_name", "Líder"),
            },
            "event_log": state.get("event_log", [])[-12:],
            "reward": ({**dict(reward_row), "drops": reward_drops} if reward_row else None),
        }
        return web.json_response(public)

    async def _api_gwent_match_action(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            match_id = int(request.match_info["match_id"])
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Ação inválida."}, status=400)

        import json
        finished_participants: tuple[int, int] | None = None
        async with self.db.transaction() as tx:
            match_row = await tx._one("SELECT * FROM cartas_gwent_matches WHERE id=?", (match_id,))
            if not match_row or user_id not in (int(match_row["creator_id"]), int(match_row["opponent_id"])):
                return web.json_response({"error": "Partida não encontrada."}, status=404)
            state = json.loads(match_row["state_json"])
            from sistemas.gwent import AI_PLAYER_ID, aplicar_jogada, executar_turno_ia
            action = str(body.get("action", "play"))[:24]
            card_id = str(body.get("card_id", ""))[:120]
            target_row = str(body.get("row", ""))[:16]
            card_ids = body.get("card_ids") if isinstance(body.get("card_ids"), list) else None
            if card_ids is not None and (
                len(card_ids) > 2 or any(not isinstance(item, str) or len(item) > 120 for item in card_ids)
            ):
                return web.json_response({"error": "Seleção de troca inválida."}, status=400)

            turno_antes = str(state.get("turn") or "")
            target_id = str(body.get("target_id", ""))[:120] or None
            result = aplicar_jogada(state, user_id, card_id, action, target_row, card_ids, target_id)
            if "error" in result:
                return web.json_response({"error": result["error"]}, status=409)
            state = result["state"]
            # Em partidas solo, a NARA responde no servidor antes de persistir o
            # snapshot. O navegador nunca pode enviar ações em nome do jogador IA.
            if state.get("is_ai_match") and state["status"] == "active" and str(state.get("turn")) == str(AI_PLAYER_ID):
                try:
                    state = executar_turno_ia(state, AI_PLAYER_ID)
                except Exception:
                    log.exception("Falha na jogada da IA Gwent da partida #%s.", match_id)
                    fallback = aplicar_jogada(state, AI_PLAYER_ID, action="pass")
                    if "error" not in fallback:
                        state = fallback["state"]

            await tx.conn.execute(
                "UPDATE cartas_gwent_matches SET status=?,state_json=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (state["status"], json.dumps(state, ensure_ascii=False), match_id),
            )
            try:
                novo_turno = str(state.get("turn") or "")
                if (not state.get("is_ai_match") and state["status"] == "active" and novo_turno
                        and novo_turno != turno_antes and novo_turno != str(user_id)):
                    asyncio.get_running_loop().create_task(self._avisar_vez_gwent(match_id, int(novo_turno), user_id))
            except Exception:
                log.debug("Falha ao agendar aviso de vez Gwent.", exc_info=True)

            if state["status"] == "finished" and not state.get("is_ai_match"):
                winner = state.get("winner_id")
                participants = (int(match_row["creator_id"]), int(match_row["opponent_id"]))
                for participant in participants:
                    await tx.conn.execute(
                        "INSERT OR IGNORE INTO cartas_gwent_rankings(user_id) VALUES (?)", (participant,)
                    )
                    await tx.conn.execute(
                        "INSERT OR IGNORE INTO users(user_id) VALUES (?)", (participant,)
                    )

                ratings = {}
                for participant in participants:
                    rating_row = await tx._one(
                        "SELECT mmr FROM cartas_gwent_rankings WHERE user_id=?", (participant,)
                    )
                    ratings[participant] = int(rating_row["mmr"] if rating_row else 1000)

                from sistemas.gwent import calcular_delta_mmr, calcular_xp_partida
                if winner is None:
                    delta_a = 0
                else:
                    result_a = 1.0 if str(participants[0]) == str(winner) else 0.0
                    delta_a = calcular_delta_mmr(
                        ratings[participants[0]], ratings[participants[1]], result_a
                    )
                deltas = {participants[0]: delta_a, participants[1]: -delta_a}

                for participant in participants:
                    prior = await tx._one(
                        "SELECT 1 FROM cartas_gwent_rewards WHERE match_id=? AND user_id=?",
                        (match_id, participant),
                    )
                    if prior:
                        continue
                    won = winner is not None and str(participant) == str(winner)
                    lost = winner is not None and not won
                    reward_denarios = 25 if winner is None else (40 if won else 15)
                    recent_xp = await tx._one(
                        """SELECT COALESCE(SUM(reward_xp),0) AS total
                           FROM cartas_gwent_rewards
                           WHERE user_id=? AND created_at>=datetime('now','-1 day')""",
                        (participant,),
                    )
                    outcome = "draw" if winner is None else ("win" if won else "loss")
                    reward_xp = calcular_xp_partida(outcome, int(recent_xp["total"] or 0), 30)
                    delta = deltas[participant]

                    await tx.conn.execute(
                        """UPDATE cartas_gwent_rankings
                           SET mmr=MAX(0,mmr+?), wins=wins+?, losses=losses+?, draws=draws+?,
                               updated_at=CURRENT_TIMESTAMP
                           WHERE user_id=?""",
                        (delta, int(won), int(lost), int(winner is None), participant),
                    )
                    await tx.conn.execute(
                        "UPDATE users SET denarios=denarios+?, xp=xp+? WHERE user_id=?",
                        (reward_denarios, reward_xp, participant),
                    )
                    drop_event_key = ""
                    milestone_drop_event_key = ""
                    if won:
                        wins_row = await tx._one(
                            "SELECT wins FROM cartas_gwent_rankings WHERE user_id=?", (participant,)
                        )
                        total_wins = int(wins_row["wins"] or 0) if wins_row else 0
                        from sistemas.recompensas_gwent import conceder_drops_de_vitoria
                        drop_event_key, milestone_drop_event_key = await conceder_drops_de_vitoria(
                            tx, self.db, participant, match_id, total_wins
                        )

                    await tx.conn.execute(
                        """INSERT OR IGNORE INTO cartas_gwent_rewards
                           (match_id,user_id,reward_denarios,reward_xp,mmr_delta,drop_event_key,milestone_drop_event_key)
                           VALUES (?,?,?,?,?,?,?)""",
                        (match_id, participant, reward_denarios, reward_xp, delta,
                         drop_event_key, milestone_drop_event_key),
                    )
                finished_participants = participants

        # Sincroniza patentes liberadas pelo XP da partida depois de confirmar a transação.
        if finished_participants:
            for participant in finished_participants:
                try:
                    await self._gwent_sync_patents(participant)
                except Exception:
                    log.exception("Não foi possível sincronizar patentes Gwent do usuário %s.", participant)
        # O cliente consulta o snapshot persistido por polling; não há dependência de WebSocket.
        return web.json_response({"ok": True})

    async def _api_me(self, request: web.Request) -> web.Response:
        raw_session = request.cookies.get(WEB_SESSION_COOKIE, "")
        payload = _validar_payload_assinado(raw_session)
        if not payload:
            return web.json_response({"authenticated": False}, status=401)
        try:
            user_id, expires_raw = payload.split(":", 1)
            expires_at = int(expires_raw)
        except (ValueError, TypeError):
            return web.json_response({"authenticated": False}, status=401)
        if not user_id.isdigit() or expires_at < int(time.time()):
            return web.json_response({"authenticated": False}, status=401)
        return web.json_response({
            "authenticated": True,
            "user": {"id": user_id},
        })

    async def _gwent_sync_patents(self, user_id: int) -> None:
        from sistemas.cartas import CARTAS_PATENTE
        from levels import PATENTES, nivel_por_xp
        user = await self.db.get_user(int(user_id))
        level = nivel_por_xp(int(user["xp"] or 0)) if user else 1
        unlocked = [
            card.id for card, (minimum, _label) in zip(CARTAS_PATENTE, PATENTES)
            if level >= int(minimum)
        ]
        if unlocked:
            await self.db.coliseu_reivindicar_patentes(int(user_id), unlocked)

    async def _gwent_prepare_user(self, user_id: int) -> None:
        """Entrega drops globais de boas-vindas a contas novas e sincroniza marcos pendentes."""
        user_id = int(user_id)
        if user_id in self._gwent_bootstrapped:
            return
        lock = self._gwent_bootstrap_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            if user_id in self._gwent_bootstrapped:
                return
            await self.db.coliseu_entregar_drops_iniciais(user_id, quantidade=12)
            await self.db.coliseu_sincronizar_conquistas(user_id)
            await self._gwent_sync_patents(user_id)
            self._gwent_bootstrapped.add(user_id)

    async def _api_gwent_store(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        await self._gwent_prepare_user(user_id)
        state = await self.db.coliseu_estado_usuario(user_id)
        fragments = await self.db._one(
            "SELECT quantidade FROM cartas_fragmentos WHERE user_id=?", (int(user_id),)
        )
        packs = await self.db._one(
            "SELECT COUNT(*) AS n FROM cartas_transacoes WHERE user_id=? AND kind='pacote_fogueira' AND created_at>=datetime('now','-1 day')",
            (int(user_id),),
        )
        usados = int(packs["n"] or 0) if packs else 0
        return web.json_response({
            "summary": {"souls": int(state["almas"]), "denarios": int(state["denarios"]),
                        "pity": int(state["pity"]), "fragments": int(fragments["quantidade"] or 0) if fragments else 0},
            "pack": {"available": usados < 3, "price": 120, "cards": 3,
                     "daily_limit": 3, "remaining": max(0, 3-usados)},
        })

    async def _api_gwent_store_pack(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        result = await self.db.coliseu_abrir_pacote(user_id, preco=120, quantidade=3, limite_pacotes_dia=3)
        status = str(result.get("status", "erro"))
        if status == "sem_saldo":
            return web.json_response({"error": "Denários insuficientes.", **result}, status=402)
        if status == "limite_pacotes_dia":
            return web.json_response({"error": "Você já abriu o limite de três pacotes nas últimas 24 horas.", **result}, status=429)
        if status != "ok":
            return web.json_response({"error": "Não foi possível abrir o pacote.", **result}, status=400)
        state = await self.db.coliseu_estado_usuario(user_id)
        return web.json_response({"ok": True, **result,
                                  "summary": {"denarios": int(state["denarios"]),
                                              "souls": int(state["almas"]),
                                              "fragments": int(state["fragmentos"])}})

    async def _api_gwent_cards(self, request: web.Request) -> web.Response:
        """Retorna cada exemplar como opção independente para o construtor do Gwent."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"authenticated": False, "error": "Autenticação necessária."}, status=401)
        try:
            await self._gwent_prepare_user(user_id)
            await self._gwent_sync_patents(user_id)
            from sistemas.cartas import get_carta, carta_de_jogo_por_id, CUSTO_RARIDADE, faixa_poder_exemplar, VERSAO_ARTES
            from sistemas.gwent import preparar_carta, RARITY_EFFECT_BUDGET
            estado = await self.db.coliseu_estado_usuario(user_id)
            owned_rows = await self.db.coliseu_listar_colecao(user_id)
            game_by_id = {str(r["card_id"]): str(r["game_name"] or "") for r in owned_rows}
            exemplar_rows = await self.db.coliseu_listar_exemplares(user_id)
            cards = []
            for record in exemplar_rows:
                card_id = str(record["card_id"])
                if card_id.startswith("transmutacao_"):
                    personal = await self._gwent_generated_card_payload(user_id, card_id, record)
                    if personal:
                        personal["exemplares"] = 1
                        personal["source"] = str(record["source"] or "transmutacao")
                        personal["max_power"] = int(personal["poder"])
                        from sistemas.gwent import RARITY_EFFECT_BUDGET
                        personal["potencia_raridade"] = int(RARITY_EFFECT_BUDGET.get(str(personal.get("raridade", "Comum")), 0))
                        personal["image_url"] = (
                            f"/api/gwent/cards/{quote(card_id, safe='')}/image"
                            f"?exemplar_id={int(record['id'])}&v=transmutacao-v36"
                        )
                        cards.append(personal)
                    continue
                card = get_carta(card_id)
                if card is None and card_id.startswith("jogo_") and game_by_id.get(card_id):
                    try:
                        card = carta_de_jogo_por_id(card_id, game_by_id[card_id])
                    except ValueError:
                        card = None
                if card is None:
                    continue
                rarity = str(record["rarity"] or "Comum")
                payload = card.para_dict()
                payload["raridade"] = rarity
                payload["poder"] = int(record["power"] or payload.get("poder", 0))
                payload["custo"] = int(CUSTO_RARIDADE.get(rarity, payload.get("custo", 0)))
                item = preparar_carta(payload)
                item["card_id"] = card_id
                item["exemplar_id"] = int(record["id"])
                item["id"] = f"{card_id}::{int(record['id'])}"
                item["exemplares"] = 1
                item["source"] = str(record["source"] or "")
                item["max_power"] = faixa_poder_exemplar(card, rarity)[1]
                item["potencia_raridade"] = int(RARITY_EFFECT_BUDGET.get(rarity, 0))
                item["image_url"] = (
                    f"/api/gwent/cards/{quote(card_id, safe='')}/image"
                    f"?exemplar_id={int(record['id'])}&v={VERSAO_ARTES}"
                )
                cards.append(item)
            from levels import nivel_por_xp
            xp = int(estado["xp"])
            return web.json_response({
                "authenticated": True,
                "summary": {
                    "souls": int(estado["almas"]),
                    "fragments": int(estado["fragmentos"]),
                    "denarios": int(estado["denarios"]),
                    "xp": xp,
                    "level": nivel_por_xp(xp),
                },
                "cards": cards,
            })
        except Exception:
            log.exception("Falha ao carregar cartas Gwent do usuário %s.", user_id)
            raise web.HTTPInternalServerError(text="Não foi possível carregar as cartas do Gwent.")

    async def _api_gwent_upgrade(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            body = await request.json()
            exemplar_id = int(body.get("exemplar_id", 0))
        except (TypeError, ValueError, AttributeError):
            return web.json_response({"error": "Exemplar inválido."}, status=400)
        result = await self.db.coliseu_aprimorar_exemplar(user_id, exemplar_id)
        status = 200 if result.get("status") == "ok" else 409
        return web.json_response(result, status=status)

    async def _api_gwent_drop_history(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        from sistemas.cartas import CARTAS_POR_ID, carta_de_jogo_por_id
        rows = await self.db.coliseu_historico_drops(user_id, 20)
        movement_rows = await self.db.coliseu_historico_movimentacoes(user_id, 20)
        history = []
        movements = []
        for movement in movement_rows:
            item = dict(movement)
            card = CARTAS_POR_ID.get(str(item.get("card_id") or ""))
            item["card_name"] = card.nome if card else str(item.get("card_id") or "Carta")
            movements.append(item)
        for row in rows:
            item = dict(row)
            card = CARTAS_POR_ID.get(str(item["card_id"] or ""))
            if card is None and str(item["card_id"] or "").startswith("jogo_"):
                legacy = await self.db._one(
                    "SELECT game_name FROM cartas_colecao WHERE user_id=? AND card_id=?",
                    (int(user_id), str(item["card_id"])),
                )
                if legacy and legacy["game_name"]:
                    try: card = carta_de_jogo_por_id(str(item["card_id"]), str(legacy["game_name"]))
                    except ValueError: card = None
            item["card_name"] = card.nome if card else str(item["card_id"] or "Carta")
            history.append(item)
        return web.json_response({"history": history, "movements": movements})

    async def _api_gwent_exemplars(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        rows = await self.db.coliseu_listar_exemplares(user_id)
        return web.json_response({"exemplars": [dict(row) for row in rows]})

    async def _api_gwent_evolve(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            body = await request.json()
            exemplar_id = int(body.get("exemplar_id", 0))
        except (TypeError, ValueError, AttributeError):
            return web.json_response({"error": "Exemplar inválido."}, status=400)
        result = await self.db.coliseu_evoluir_exemplar(user_id, exemplar_id)
        status = 200 if result.get("status") == "ok" else 409
        return web.json_response(result, status=status)

    def _atelier_admin_ids(self) -> set[int]:
        # Criador do NARA: autorização explícita para administrar o Ateliê no site e Discord.
        ids = {1300117955236991046}
        if int(config.BOT_OWNER_ID or 0) > 0:
            ids.add(int(config.BOT_OWNER_ID))
        raw = os.getenv("COLISEUM_ART_REVIEWER_IDS", "")
        for value in raw.split(","):
            value = value.strip()
            if value.isdigit() and int(value) > 0:
                ids.add(int(value))
        return ids

    def _atelier_is_admin(self, user_id: int) -> bool:
        return int(user_id) in self._atelier_admin_ids()

    async def _api_gwent_atelier_prompt(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        card_id = str(request.query.get("card_id", "")).strip()[:120]
        if not card_id:
            return web.json_response({"error": "Selecione uma carta."}, status=400)
        try:
            owned = await self.db._one(
                "SELECT card_id,game_name FROM cartas_colecao WHERE user_id=? AND card_id=?",
                (user_id, card_id),
            )
            if not owned:
                return web.json_response({"error": "Você precisa possuir essa carta para enviar arte."}, status=403)
            from sistemas.cartas import get_carta, carta_de_jogo_por_id
            from sistemas.atelie_coliseu import gerar_prompt_carta_estruturado
            card = get_carta(card_id)
            if card is None and card_id.startswith("jogo_") and owned["game_name"]:
                card = carta_de_jogo_por_id(card_id, str(owned["game_name"]))
            if card is None:
                return web.json_response({"error": "Modelo de carta não encontrado no catálogo."}, status=404)
            payload = card.para_dict()
            package = gerar_prompt_carta_estruturado(payload)
            return web.json_response({
                "card_id": card_id,
                "name": payload.get("nome", card_id),
                "analysis": package["analysis"],
                "prompt": package["prompt"],
                "negative_prompt": package["negative_prompt"],
                "aspect_ratio": package["recommended_aspect_ratio"],
                "width": package["recommended_width"],
                "height": package["recommended_height"],
            })
        except Exception:
            log.exception("Falha ao gerar prompt do Ateliê para %s.", user_id)
            raise web.HTTPInternalServerError(text="Não foi possível gerar o prompt da carta.")

    async def _enviar_submissao_atelie_discord(
        self, submission_id: int, user_id: int, card_id: str, artist_name: str, image_data: bytes,
    ) -> bool:
        """Publica no canal privado do Ateliê a mesma submissão salva no banco compartilhado."""
        channel_id = int(getattr(config, "COLISEU_ART_CHANNEL_ID", 0) or 0)
        if not channel_id:
            log.error("COLISEU_ART_CHANNEL_ID não configurado; submissão #%s ficou salva sem aviso no Discord.", submission_id)
            return False
        channel = self.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                log.exception("Não foi possível acessar o canal do Ateliê (%s).", channel_id)
                return False
        embed = discord.Embed(
            title=f"Nova arte para revisão · #{submission_id}",
            description=f"**Carta:** `{card_id}`\n**Artista:** {artist_name[:100]}\n**Autor:** <@{user_id}>\n**Status:** Em análise",
            color=discord.Color.gold(),
        )
        embed.set_image(url="attachment://arte_atelie.jpg")
        embed.set_footer(text="Aprovar ou rejeitar atualiza a submissão no banco compartilhado com o site.")
        try:
            await channel.send(
                content=f"Nova submissão do Ateliê — <@{user_id}>",
                embed=embed,
                file=discord.File(BytesIO(image_data), filename="arte_atelie.jpg"),
                view=AtelieRevisaoView(self, submission_id),
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return True
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao publicar submissão #%s no canal do Ateliê.", submission_id)
            return False

    async def _api_gwent_atelier_submit(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        try:
            form = await request.post()
            card_id = str(form.get("card_id", "")).strip()[:120]
            prompt_text = str(form.get("prompt_text", ""))[:65000]
            if not prompt_text.strip():
                return web.json_response({"error": "Gere o prompt individual antes de enviar a ilustração."}, status=400)
            artist_name = "".join(ch for ch in str(form.get("artist_name", "")).strip() if ch.isprintable())[:80]
            if not artist_name:
                artist_name = f"Artista Discord {user_id}"
            upload = form.get("image")
            if not card_id or upload is None or not hasattr(upload, "file"):
                return web.json_response({"error": "Carta e arquivo de imagem são obrigatórios."}, status=400)
            raw = upload.file.read(8 * 1024 * 1024 + 1)
            from sistemas.atelie_coliseu import normalizar_imagem_carta, ArteInvalida
            try:
                normalized = normalizar_imagem_carta(raw)
            except ArteInvalida as exc:
                return web.json_response({"error": str(exc)}, status=400)
            result = await self.db.coliseu_atelie_criar_submissao_web(
                user_id, card_id, prompt_text, normalized.dados, "image/jpeg",
                artist_name,
            )
            statuses = {
                "not_owned": (403, "Você precisa possuir essa carta."),
                "pending_exists": (409, "Você já tem uma submissão pendente para esta carta."),
                "pending_limit": (429, "Limite de três submissões pendentes atingido."),
            }
            if result.get("status") in statuses:
                code, message = statuses[result["status"]]
                return web.json_response({"error": message, **result}, status=code)
            notified = await self._enviar_submissao_atelie_discord(
                int(result["submission_id"]), user_id, card_id, artist_name, normalized.dados,
            )
            return web.json_response({"ok": True, "discord_notified": notified, **result}, status=201)
        except web.HTTPException:
            raise
        except Exception:
            log.exception("Falha ao receber arte do Ateliê do usuário %s.", user_id)
            raise web.HTTPInternalServerError(text="Não foi possível registrar a arte enviada.")

    async def _api_gwent_atelier_history(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        history = await self.db.coliseu_atelie_historico_web(user_id)
        return web.json_response({"history": history})

    async def _api_gwent_atelier_review_list(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._atelier_is_admin(user_id):
            return web.json_response({"error": "Acesso restrito à equipe de revisão."}, status=403)
        rows = await self.db.coliseu_atelie_listar_pendentes_web()
        return web.json_response({"pending": rows})

    async def _api_gwent_atelier_submission_image(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            raise web.HTTPUnauthorized(text="Faça login com o Discord.")
        if not self._atelier_is_admin(user_id):
            raise web.HTTPForbidden(text="Acesso restrito à equipe de revisão.")
        try:
            submission_id = int(request.match_info.get("submission_id", 0))
        except (TypeError, ValueError):
            raise web.HTTPNotFound(text="Submissão não encontrada.")
        art = await self.db._one(
            "SELECT image_data,mime_type FROM cartas_atelie_submissoes WHERE id=? AND status='pending'",
            (submission_id,),
        )
        if not art:
            raise web.HTTPNotFound(text="Submissão não encontrada.")
        response = web.Response(body=bytes(art["image_data"]), content_type=str(art["mime_type"] or "image/jpeg"))
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    async def _api_gwent_atelier_review_decide(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        if not self._atelier_is_admin(user_id):
            return web.json_response({"error": "Acesso restrito à equipe de revisão."}, status=403)
        try:
            submission_id = int(request.match_info.get("submission_id", 0))
            body = await request.json()
            approve = bool(body.get("approve"))
            reason = str(body.get("reason", ""))[:500]
        except (TypeError, ValueError, AttributeError):
            return web.json_response({"error": "Decisão inválida."}, status=400)
        result = await self.db.coliseu_atelie_decidir_web(submission_id, user_id, approve, reason)
        if result.get("status") != "ok":
            return web.json_response({"error": "Submissão já processada ou inexistente."}, status=404)
        return web.json_response({"ok": True, "status": result["new_status"]})

    async def _api_gwent_atelier_remove_all_arts(self, request: web.Request) -> web.Response:
        """Arquiva todas as artes comunitárias aprovadas; restrito à equipe do Ateliê."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        if not self._atelier_is_admin(user_id):
            return web.json_response({"error": "Acesso restrito à administração do Ateliê."}, status=403)
        result = await self.db.coliseu_atelie_remover_todas_as_artes_ativas()
        return web.json_response({"ok": True, **result,
                                  "message": "As artes oficiais foram retiradas das cartas. O histórico foi preservado."})

    async def _api_gwent_atelier_leaders_list(self, request: web.Request) -> web.Response:
        """Lista os líderes e suas artes aplicadas; somente a administração pode acessar o painel."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._atelier_is_admin(user_id):
            return web.json_response({"error": "Acesso restrito à administração do Ateliê."}, status=403)

        from sistemas.gwent import LEADERS
        metadata = await self.db.coliseu_gwent_lideres_artes_listar()
        active = {str(row["leader_id"]): dict(row) for row in metadata}
        default_assets = {
            "comandante_fornalha": "godfrey", "bastiao_ancestral": "morgott",
            "juiz_cerco": "radagon", "mestre_veu": "mohg",
            "sombra_caminhante": "rykard", "voz_caidos": "esgar",
            "arquimaga_eclipse": "rennala", "mestre_eclipse": "astel",
            "oraculo_tempestade": "loretta",
        }
        leaders = []
        for leader_id, value in LEADERS.items():
            row = active.get(leader_id)
            version = str(row.get("revision", "") if row else "")[:20]
            leaders.append({
                "id": leader_id,
                "name": value["name"],
                "faction": value["faction"],
                "description": value["description"],
                "has_art": bool(row),
                "artist_name": str(row.get("artist_name", "") if row else ""),
                "updated_at": str(row.get("updated_at", "") if row else ""),
                "art_url": f"/api/gwent/leaders/{leader_id}/art?v={version}" if row else "",
                "default_art_url": f"/assets/leaders/{default_assets.get(leader_id, 'godfrey')}.webp",
            })
        return web.json_response({"leaders": leaders})

    async def _api_gwent_atelier_leader_art_upload(self, request: web.Request) -> web.Response:
        """Upload administrativo de arte oficial para uma carta de líder."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        if not self._atelier_is_admin(user_id):
            return web.json_response({"error": "Acesso restrito à administração do Ateliê."}, status=403)

        from sistemas.gwent import LEADERS
        from sistemas.atelie_coliseu import normalizar_imagem_carta, ArteInvalida, TAMANHO_MAXIMO_UPLOAD
        leader_id = str(request.match_info.get("leader_id", "")).strip()[:80]
        if leader_id not in LEADERS:
            return web.json_response({"error": "Líder não encontrado no catálogo."}, status=404)
        if request.content_length and request.content_length > TAMANHO_MAXIMO_UPLOAD + 1024 * 1024:
            return web.json_response({"error": "O envio ultrapassa o limite de 8 MB."}, status=413)

        image_data = b""
        artist_name = ""
        try:
            reader = await request.multipart()
            while True:
                field = await reader.next()
                if field is None:
                    break
                if field.name == "image":
                    chunks = []
                    total = 0
                    while True:
                        chunk = await field.read_chunk(size=256 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > TAMANHO_MAXIMO_UPLOAD:
                            return web.json_response({"error": "A imagem ultrapassa 8 MB."}, status=413)
                        chunks.append(chunk)
                    image_data = b"".join(chunks)
                elif field.name == "artist_name":
                    artist_name = (await field.text()).strip()[:100]
        except (ValueError, RuntimeError):
            return web.json_response({"error": "Formulário de envio inválido."}, status=400)

        if not image_data:
            return web.json_response({"error": "Selecione uma imagem para o líder."}, status=400)
        try:
            normalized = await asyncio.to_thread(normalizar_imagem_carta, image_data)
        except ArteInvalida as exc:
            return web.json_response({"error": str(exc)}, status=400)

        saved = await self.db.coliseu_gwent_lider_arte_salvar(
            leader_id, normalized.dados, "image/jpeg", artist_name, user_id
        )
        version = str(saved["revision"] or "")[:20]
        return web.json_response({
            "ok": True, "leader_id": leader_id, "leader_name": LEADERS[leader_id]["name"],
            "artist_name": str(saved["artist_name"] or ""),
            "width": normalized.largura, "height": normalized.altura,
            "art_url": f"/api/gwent/leaders/{leader_id}/art?v={version}",
            "message": "Arte do líder salva e aplicada ao construtor de deck.",
        })

    async def _api_gwent_atelier_leader_art_remove(self, request: web.Request) -> web.Response:
        """Remove a arte personalizada e restaura o retrato padrão do líder."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem não autorizada."}, status=403)
        if not self._atelier_is_admin(user_id):
            return web.json_response({"error": "Acesso restrito à administração do Ateliê."}, status=403)
        from sistemas.gwent import LEADERS
        leader_id = str(request.match_info.get("leader_id", "")).strip()[:80]
        if leader_id not in LEADERS:
            return web.json_response({"error": "Líder não encontrado no catálogo."}, status=404)
        removed = await self.db.coliseu_gwent_lider_arte_remover(leader_id)
        return web.json_response({"ok": True, "removed": removed,
                                  "message": "Retrato padrão do líder restaurado."})

    async def _api_gwent_leader_art(self, request: web.Request) -> web.Response:
        """Entrega a ilustração oficial do líder aos jogadores autenticados."""
        user_id = self._api_user_id(request)
        if user_id is None:
            raise web.HTTPUnauthorized(text="Faça login com o Discord.")
        from sistemas.gwent import LEADERS
        leader_id = str(request.match_info.get("leader_id", "")).strip()[:80]
        if leader_id not in LEADERS:
            raise web.HTTPNotFound(text="Líder não encontrado.")
        art = await self.db.coliseu_gwent_lider_arte_obter(leader_id)
        if not art:
            raise web.HTTPNotFound(text="Este líder utiliza o retrato padrão.")
        dados_arte = bytes(art["image_data"])
        from sistemas.arte_cartas import detectar_mime_imagem
        mime_real = await asyncio.to_thread(detectar_mime_imagem, dados_arte)
        if mime_real != "image/jpeg":
            raise web.HTTPUnprocessableEntity(text="A arte do líder armazenada está inválida.")
        version = str(art["revision"] or "")
        etag = hashlib.sha256(f"gwent-leader-art:{leader_id}:{version}".encode("utf-8")).hexdigest()
        headers = {
            "Cache-Control": "private, no-cache, must-revalidate",
            "ETag": f'"{etag}"',
            "X-Content-Type-Options": "nosniff",
            "Vary": "Cookie",
        }
        incoming = request.headers.get("If-None-Match", "")
        if any(token.strip() in ("*", headers["ETag"], f"W/{headers['ETag']}") for token in incoming.split(",")):
            return web.Response(status=304, headers=headers)
        return web.Response(body=dados_arte, content_type=mime_real, headers=headers)

    async def _api_gwent_atelier_official_metadata(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        card_id = str(request.match_info.get("card_id", "")).strip()[:120]
        art = await self.db.coliseu_atelie_obter_arte_oficial(card_id)
        if not art:
            return web.json_response({"official": False})
        return web.json_response({"official": True, "artist_name": str(art["artist_name"] or "Artista da comunidade"),
                                  "created_at": str(art["created_at"] or ""),
                                  "image_url": f"/api/gwent/atelier/art/{card_id}"})

    async def _api_gwent_atelier_official_art(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            raise web.HTTPUnauthorized(text="Faça login com o Discord.")
        card_id = str(request.match_info.get("card_id", "")).strip()[:120]
        art = await self.db.coliseu_atelie_obter_arte_oficial(card_id)
        if not art:
            raise web.HTTPNotFound(text="Esta carta ainda utiliza a arte-base.")
        from sistemas.arte_cartas import detectar_mime_imagem
        dados_arte = bytes(art["image_data"])
        mime_real = await asyncio.to_thread(detectar_mime_imagem, dados_arte)
        if mime_real is None:
            raise web.HTTPUnprocessableEntity(text="A arte oficial armazenada está inválida.")
        etag = hashlib.sha256(f"atelier-art:{art['id']}".encode("utf-8")).hexdigest()
        headers = {
            "Cache-Control": "private, no-cache, must-revalidate",
            "ETag": f'"{etag}"',
            "X-Content-Type-Options": "nosniff",
            "Vary": "Cookie",
        }
        incoming = request.headers.get("If-None-Match", "")
        if any(token.strip() in ("*", headers["ETag"], f"W/{headers['ETag']}") for token in incoming.split(",")):
            return web.Response(status=304, headers=headers)
        return web.Response(body=dados_arte, content_type=mime_real, headers=headers)

    async def _gwent_render_path_cached(self, key: str, renderer, cache_lookup=None):
        """Renderiza uma vez e devolve Path persistente, sem copiar o PNG para RAM.

        A vaga fica ocupada enquanto a thread real do Pillow trabalha, mesmo que o
        navegador cancele a requisição. Não há timeout curto que transforme fila em 503.
        """
        locks = self._gwent_image_locks
        if len(locks) > 512:
            for old_key, old_lock in list(locks.items()):
                if not old_lock.locked():
                    locks.pop(old_key, None)
                if len(locks) <= 384:
                    break
        lock = locks.setdefault(key, asyncio.Lock())

        async with lock:
            if cache_lookup is not None:
                cached_path = await asyncio.to_thread(cache_lookup)
                if cached_path is not None:
                    log.debug("Gwent image cache hit key=%s", key[:16])
                    return cached_path

            semaphore = self._gwent_render_semaphore
            # Limita a fila de espera: em CPU muito pequena, aceitar dezenas de
            # renderizações pendentes só acumula memória e piora a latência do bot.
            waiting = int(getattr(self, "_gwent_render_waiters", 0))
            if waiting >= 6:
                raise web.HTTPServiceUnavailable(
                    text="Renderizador ocupado. Tente novamente em alguns segundos.",
                    headers={"Retry-After": "3"},
                )
            self._gwent_render_waiters = waiting + 1
            try:
                await semaphore.acquire()
            finally:
                self._gwent_render_waiters = max(
                    0, int(getattr(self, "_gwent_render_waiters", 1)) - 1
                )
            loop = asyncio.get_running_loop()
            render_started = time.monotonic()
            future = loop.run_in_executor(None, renderer)
            release_in_callback = False

            def _release_after_cancel(done_future):
                try:
                    # Consumir exceção de thread desacoplada para não gerar warning.
                    done_future.exception()
                except (asyncio.CancelledError, Exception):
                    pass
                semaphore.release()

            try:
                path = await asyncio.shield(future)
                if not isinstance(path, Path) or not path.is_file():
                    raise ValueError("O renderizador não produziu um arquivo de cache válido.")
                elapsed_ms = (time.monotonic() - render_started) * 1000
                try:
                    size_bytes = path.stat().st_size
                except OSError:
                    size_bytes = -1
                log.info(
                    "Gwent image rendered key=%s elapsed_ms=%.1f size_bytes=%s waiters=%s",
                    key[:16], elapsed_ms, size_bytes,
                    int(getattr(self, "_gwent_render_waiters", 0)),
                )
                return path
            except asyncio.CancelledError:
                future.add_done_callback(_release_after_cancel)
                release_in_callback = True
                raise
            finally:
                if not release_in_callback:
                    semaphore.release()

    async def _api_gwent_card_image(self, request: web.Request) -> web.Response:
        """Entrega cache em arquivo; só consulta/renderiza a carta solicitada."""
        user_id = self._api_user_id(request)
        if user_id is None:
            raise web.HTTPUnauthorized(text="Faça login com o Discord.")
        card_id = str(request.match_info.get("card_id", "")).strip()
        if not card_id or len(card_id) > 120:
            raise web.HTTPNotFound(text="Carta não encontrada.")

        if card_id.startswith("transmutacao_"):
            generated = await self.db._one(
                "SELECT art_path,art_status,status FROM cartas_geradas WHERE card_id=?",
                (card_id,),
            )
            if not generated or generated["status"] != "published" or generated["art_status"] != "validated":
                raise web.HTTPNotFound(text="Carta pessoal não encontrada.")
            from config import get_data_dir
            art_path = Path(str(generated["art_path"] or "")).resolve()
            root = (Path(get_data_dir()) / "cartas_geradas").resolve()
            try:
                art_path.relative_to(root)
            except ValueError:
                raise web.HTTPNotFound(text="Arte pessoal indisponível.")
            if not art_path.is_file() or art_path.suffix.casefold() != ".png":
                raise web.HTTPNotFound(text="Arte pessoal indisponível.")
            digest = await asyncio.to_thread(lambda: hashlib.sha256(art_path.read_bytes()).hexdigest())
            expected = await self.db._one(
                "SELECT content_hash FROM cartas_geradas_artes WHERE generated_card_id=? AND status='validated'",
                (card_id,),
            )
            if not expected or not secrets.compare_digest(digest, str(expected["content_hash"] or "")):
                raise web.HTTPUnprocessableEntity(text="Integridade da arte pessoal inválida.")
            headers = {"Content-Disposition": "inline", "Cache-Control": "private, max-age=86400",
                       "ETag": f'"{digest}"', "X-Content-Type-Options": "nosniff", "Vary": "Cookie"}
            incoming = request.headers.get("If-None-Match", "")
            if any(token.strip() in ("*", headers["ETag"], f"W/{headers['ETag']}") for token in incoming.split(",")):
                return web.Response(status=304, headers=headers)
            return web.FileResponse(art_path, headers={**headers, "Content-Type": "image/png"})

        cache_control = "private, max-age=86400, stale-while-revalidate=604800"

        def _etag_corresponde(etag: str) -> bool:
            etag_header = f'"{etag}"'
            incoming = request.headers.get("If-None-Match", "")
            return any(token.strip() in ("*", etag_header, f"W/{etag_header}") for token in incoming.split(","))

        def _headers(etag: str) -> dict[str, str]:
            return {
                "Content-Disposition": "inline",
                "Cache-Control": cache_control,
                "ETag": f'"{etag}"',
                "X-Content-Type-Options": "nosniff",
                "Vary": "Cookie",
            }

        def _responder(body: bytes, mime: str, etag: str) -> web.Response:
            headers = _headers(etag)
            if _etag_corresponde(etag):
                return web.Response(status=304, headers=headers)
            return web.Response(body=body, content_type=mime, headers=headers)

        def _responder_arquivo(path: Path, mime: str, etag: str) -> web.Response:
            headers = _headers(etag)
            if _etag_corresponde(etag):
                return web.Response(status=304, headers=headers)
            # aiohttp envia o arquivo sem criar outra cópia bytes no heap do bot.
            headers["Content-Type"] = mime
            return web.FileResponse(path, headers=headers)

        try:
            from sistemas.cartas import get_carta, carta_de_jogo_por_id, CUSTO_RARIDADE
            from sistemas.gwent import preparar_carta
            from sistemas.arte_cartas import (
                render_carta,
                cache_carta_existente,
                render_carta_webp,
                cache_carta_webp_existente,
                webp_disponivel,
                cache_arte_oficial_por_id_existente,
                render_arte_oficial_cacheada_por_id,
                cache_arte_oficial_webp_existente,
                render_arte_oficial_webp_cacheada_por_id,
                detectar_mime_imagem,
                _fingerprint_templates,
                VERSAO_RENDERIZADOR,
            )

            exemplar_id_raw = request.query.get("exemplar_id", "").strip()
            exemplar_id = None
            if exemplar_id_raw:
                try:
                    exemplar_id = int(exemplar_id_raw)
                    if exemplar_id <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    raise web.HTTPNotFound(text="Exemplar não encontrado.")

            # SELECT indexado por user_id + card_id + exemplar_id. Antes, cada imagem
            # carregava a coleção inteira e depois fazia outra consulta de exemplares.
            owned_row = await self.db.coliseu_obter_dados_imagem(user_id, card_id, exemplar_id)
            if exemplar_id is not None and (owned_row is None or owned_row["exemplar_id"] is None):
                raise web.HTTPNotFound(text="Exemplar não encontrado na sua coleção.")

            # Só metadados nesta etapa. O BLOB de arte oficial é lido apenas no cache miss.
            official_meta = await self.db.coliseu_atelie_obter_arte_oficial_metadata(card_id)

            snapshot = None
            if owned_row is None:
                matches = await self.db._all(
                    """SELECT state_json FROM cartas_gwent_matches
                       WHERE creator_id=? OR opponent_id=? ORDER BY id DESC LIMIT 100""",
                    (user_id, user_id),
                )
                for match in matches:
                    try:
                        state = json.loads(match["state_json"] or "{}")
                    except (TypeError, ValueError):
                        continue
                    found = False
                    for player in (state.get("players") or {}).values():
                        zones = [player.get("hand", []), player.get("draw_pile", []),
                                 player.get("discard", []), player.get("board", [])]
                        for zone in zones:
                            snapshot = next((item for item in zone if str(item.get("id")) == card_id), None)
                            if snapshot:
                                found = True
                                break
                        if found:
                            break
                    if found:
                        break
                if snapshot is None:
                    if official_meta:
                        official_art = await self.db.coliseu_atelie_obter_arte_oficial(card_id)
                        if official_art:
                            raw_art = bytes(official_art["image_data"])
                            raw_mime = await asyncio.to_thread(detectar_mime_imagem, raw_art)
                            if raw_mime:
                                etag = hashlib.sha256(f"official-raw:{official_meta['id']}".encode()).hexdigest()
                                return _responder(raw_art, raw_mime, etag)
                    raise web.HTTPNotFound(text="Carta não encontrada na sua coleção ou nas suas partidas.")

            card = get_carta(card_id)
            if card is None and card_id.startswith("jogo_"):
                game_name = str((owned_row["game_name"] if owned_row is not None else "") or
                                (snapshot or {}).get("jogo_origem") or "")
                if game_name:
                    try:
                        card = carta_de_jogo_por_id(card_id, game_name)
                    except ValueError:
                        card = None
            if card is None and snapshot:
                card = snapshot
            if card is None:
                if official_meta:
                    official_art = await self.db.coliseu_atelie_obter_arte_oficial(card_id)
                    if official_art:
                        raw_art = bytes(official_art["image_data"])
                        raw_mime = await asyncio.to_thread(detectar_mime_imagem, raw_art)
                        if raw_mime:
                            etag = hashlib.sha256(f"official-raw:{official_meta['id']}".encode()).hexdigest()
                            return _responder(raw_art, raw_mime, etag)
                raise web.HTTPNotFound(text="Carta não encontrada no catálogo.")

            source = card.para_dict() if hasattr(card, "para_dict") else dict(card)
            if owned_row is not None and owned_row["rarity"]:
                source["raridade"] = str(owned_row["rarity"])
                source["poder"] = int(owned_row["exemplar_power"] or source.get("poder", 0))
                source["custo"] = int(CUSTO_RARIDADE.get(source["raridade"], source.get("custo", 0)))
            gwent = preparar_carta(source)
            source.update({
                "gwent_mode": True,
                "categoria": gwent["categoria"],
                "categoria_arte": source.get("categoria_arte", source.get("categoria_origem", "Unidade")),
                "faccao": gwent["faccao"],
                "fileira": gwent["row"],
                "row_label": gwent["row_label"],
                "papel_gwent": gwent["papel_gwent"],
                "habilidade_nome": gwent["habilidade_nome"],
                "habilidade_texto": gwent["habilidade_texto"],
            })

            # Três perfis independentes: grade leve, preview e modal HD.
            is_thumbnail = request.query.get("thumb") == "1"
            is_detail = request.query.get("detail") == "1"
            image_size = (210, 310) if is_thumbnail else ((840, 1240) if is_detail else (420, 620))
            image_quality = 82 if is_thumbnail else (90 if is_detail else 86)
            use_webp = webp_disponivel()
            image_format = "webp" if use_webp else "png"
            image_mime = "image/webp" if use_webp else "image/png"
            source_json = json.dumps(source, ensure_ascii=False, sort_keys=True, default=str)
            template_fingerprint = _fingerprint_templates({"card": source})
            size_token = f"{image_size[0]}x{image_size[1]}:{image_format}:q{image_quality}"

            if official_meta:
                official_id = int(official_meta["id"])
                etag = hashlib.sha256(
                    f"official:{official_id}:{size_token}:{VERSAO_RENDERIZADOR}:{template_fingerprint}:{source_json}".encode("utf-8")
                ).hexdigest()
                if _etag_corresponde(etag):
                    return web.Response(status=304, headers=_headers(etag))

                if use_webp:
                    official_lookup = lambda: cache_arte_oficial_webp_existente(
                        source, official_id, image_size, quality=image_quality
                    )
                    official_renderer = lambda raw: render_arte_oficial_webp_cacheada_por_id(
                        source, raw, official_id, image_size, quality=image_quality
                    )
                else:
                    official_lookup = lambda: cache_arte_oficial_por_id_existente(
                        source, official_id, image_size
                    )
                    official_renderer = lambda raw: render_arte_oficial_cacheada_por_id(
                        source, raw, official_id, image_size
                    )
                try:
                    official_path = await asyncio.to_thread(official_lookup)
                    if official_path is None:
                        # BLOB só sai do SQLite quando a composição ainda não existe.
                        official_art = await self.db.coliseu_atelie_obter_arte_oficial(card_id)
                        if not official_art or int(official_art["id"]) != official_id:
                            raise ValueError("A arte oficial mudou durante a renderização.")
                        raw_art = bytes(official_art["image_data"])
                        official_path = await self._gwent_render_path_cached(
                            f"official:{etag}",
                            lambda: official_renderer(raw_art),
                            cache_lookup=official_lookup,
                        )
                    return _responder_arquivo(official_path, image_mime, etag)
                except ValueError as exc:
                    log.warning("Arte oficial inválida para card=%s; usando arte-base: %s", card_id, exc)
                except web.HTTPException:
                    raise
                except Exception:
                    log.exception("Falha ao compor arte oficial na carta card=%s; usando arte-base.", card_id)

            etag = hashlib.sha256(
                f"base:{size_token}:{VERSAO_RENDERIZADOR}:{template_fingerprint}:{source_json}".encode("utf-8")
            ).hexdigest()
            if _etag_corresponde(etag):
                return web.Response(status=304, headers=_headers(etag))

            if use_webp:
                base_lookup = lambda: cache_carta_webp_existente(
                    source, tamanho=image_size, quality=image_quality
                )
                base_renderer = lambda: render_carta_webp(
                    source, tamanho=image_size, quality=image_quality
                )
            else:
                base_lookup = lambda: cache_carta_existente(source, tamanho=image_size)
                base_renderer = lambda: render_carta(source, tamanho=image_size)
            base_path = await asyncio.to_thread(base_lookup)
            if base_path is None:
                base_path = await self._gwent_render_path_cached(
                    f"base:{etag}", base_renderer, cache_lookup=base_lookup,
                )
            return _responder_arquivo(base_path, image_mime, etag)
        except web.HTTPException:
            raise
        except Exception:
            log.exception("Falha ao renderizar carta Gwent user=%s card=%s", user_id, card_id)
            raise web.HTTPInternalServerError(text="Não foi possível carregar a imagem da carta.")

    async def _oauth_logout(self, request: web.Request) -> web.Response:
        response = web.json_response({"ok": True})
        response.del_cookie(WEB_SESSION_COOKIE, path="/")
        response.del_cookie(OAUTH_STATE_COOKIE, path="/")
        return response

    async def on_interaction(self, interaction: discord.Interaction) -> None:
        # Só botões/selects: em slash commands o defer() decide se a resposta é efêmera,
        # então ali cada comando precisa responder por conta própria.
        if interaction.type is discord.InteractionType.component:
            task = asyncio.create_task(_auto_defer(interaction))
            self._tarefas_auto_defer.add(task)
            task.add_done_callback(self._tarefas_auto_defer.discard)

    async def _monitorar_lag_loop(self) -> None:
        """Avisa no log quando o event loop fica travado (código síncrono pesado)."""
        intervalo = 0.5
        while True:
            antes = asyncio.get_running_loop().time()
            await asyncio.sleep(intervalo)
            atraso = asyncio.get_running_loop().time() - antes - intervalo
            if atraso > 1.0:
                log.warning("Event loop travado por ~%.1fs (algo síncrono/pesado rodou no loop).", atraso)

    async def on_ready(self) -> None:
        if not self._slash_sync_done:
            self._slash_sync_done = True
            try:
                # Remove comandos antigos publicados diretamente em servidores.
                if config.GUILD_ID:
                    alvo = int(config.GUILD_ID)
                    guilds_para_limpar = list(self.guilds)
                    if all(g.id != alvo for g in guilds_para_limpar):
                        guilds_para_limpar.append(discord.Object(id=alvo))
                    for guild in guilds_para_limpar:
                        self.tree.clear_commands(guild=guild)
                        if guild.id == alvo:
                            self.tree.copy_global_to(guild=guild)
                        sincronizados = await self.tree.sync(guild=guild)
                        log.info(
                            "Sincronização forçada no servidor %s: %s comando(s): %s",
                            guild.id,
                            len(sincronizados),
                            ", ".join(sorted(c.name for c in sincronizados)) or "(nenhum)",
                        )
                    # /nara, /jogo e /adm ficam no escopo do servidor configurado,
                    # removendo também a versão global antiga.
                    self.tree.clear_commands(guild=None)
                    await self.tree.sync()
                    log.info("Comandos globais antigos removidos.")
                else:
                    # Sem GUILD_ID, publica somente os três comandos globalmente.
                    sincronizados = await self.tree.sync()
                    log.info(
                        "Sincronização global forçada: %s comando(s): %s",
                        len(sincronizados),
                        ", ".join(sorted(c.name for c in sincronizados)),
                    )
                    # Remove comandos antigos que tenham sido registrados por servidor.
                    for guild in list(self.guilds):
                        self.tree.clear_commands(guild=guild)
                        await self.tree.sync(guild=guild)
                        log.info("Comandos antigos removidos do servidor %s.", guild.id)
                self.sync_ok = True
            except Exception:
                self.sync_ok = False
                log.exception("Falha ao forçar a sincronização exclusiva de /nara, /jogo e /adm.")
        log.info(
            "NARA conectado como %s | guilds=%s | cogs=%s | comandos_sync=%s | extensoes_com_falha=%s",
            self.user, len(self.guilds), len(self.cogs), self.sync_ok, len(self.failed_extensions),
        )

    async def on_disconnect(self) -> None:
        log.warning("Conexão com o Gateway do Discord interrompida; tentando reconectar automaticamente.")

    async def on_resumed(self) -> None:
        log.info("Sessão do Discord retomada.")

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any) -> None:
        log.exception("Erro não tratado no evento Discord %s.", event_method)

    async def close(self) -> None:
        """Fecha extensões, cliente HTTP e SQLite no shutdown/redeploy."""
        try:
            await super().close()
        finally:
            if self._web_runner is not None:
                await self._web_runner.cleanup()
                self._web_runner = None
                log.info("Servidor HTTP encerrado.")
            await self.db.close()
            log.info("Conexão SQLite encerrada.")


def main() -> None:
    if not config.TOKEN:
        raise SystemExit("Configuração ausente: defina DISCORD_TOKEN nas variáveis de ambiente da hospedagem.")
    NaraBot().run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
