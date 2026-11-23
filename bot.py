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
from urllib.parse import urlencode

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
    "cogs.painel_membros", "cogs.catalogo_integrado", "cogs.game_news",
    "cogs.cartas_coliseu",
)

COMANDOS_PRINCIPAIS = frozenset({"nara", "adm"})


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
            "A árvore de comandos precisa conter exatamente os comandos principais aprovados; "
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
        canal_id = int(getattr(config, "MOD_CHANNEL_ID", 0) or 0)
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
        self._web_runner: web.AppRunner | None = None
        self._web_presence: dict[int, float] = {}
        self._web_sockets: dict[int, set[web.WebSocketResponse]] = {}

    def _handle_asyncio_exception(self, loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        exception = context.get("exception")
        message = context.get("message", "Exceção não tratada no event loop")
        if exception is not None:
            log.error("%s", message, exc_info=(type(exception), exception, exception.__traceback__))
        else:
            log.error("%s | contexto=%s", message, {k: str(v)[:300] for k, v in context.items() if k != "task"})

    async def setup_hook(self) -> None:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(self._handle_asyncio_exception)
        self._tarefa_lag = loop.create_task(self._monitorar_lag_loop())

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
        # Os Cogs antigos continuam carregados para uso interno pelos painéis,
        # mas seus comandos individuais não serão publicados no Discord.
        removidos = _manter_apenas_comandos_principais(self.tree)
        log.info(
            "Comandos slash locais filtrados: removidos=%s | permitidos=/nara,/adm",
            len(removidos),
        )

        if self.failed_extensions:
            log.error("Inicialização parcial: %s extensão(ões) falharam: %s", len(self.failed_extensions), ", ".join(self.failed_extensions))

        if not config.MOD_CHANNEL_ID:
            log.warning("MOD_CHANNEL_ID não configurado: os fluxos de aprovação que dependem da central ficarão indisponíveis.")
        if not config.GUILD_ID:
            log.warning("GUILD_ID vazio: /nara e /adm serão sincronizados globalmente; a propagação do Discord pode levar algum tempo.")
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
                    "service": "soulsbot",
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

        async def status_api(_request: web.Request) -> web.Response:
            return web.json_response({
                "service": "soulsbot-api",
                "status": "online",
                "discord_connected": self.is_ready(),
                "database": "connected",
            })

        app = web.Application()
        app.router.add_get("/", pagina_inicial)
        app.router.add_get("/style.css", estilo_site)
        app.router.add_get("/app.js", script_site)
        app.router.add_get("/api/status", status_api)
        app.router.add_get("/auth/discord/login", self._oauth_login)
        app.router.add_get("/auth/discord/callback", self._oauth_callback)
        app.router.add_get("/api/me", self._api_me)
        app.router.add_get("/api/collection", self._api_collection)
        app.router.add_get("/api/deck", self._api_deck)
        app.router.add_post("/api/deck", self._api_deck_save)
        app.router.add_get("/api/players", self._api_players)
        app.router.add_post("/api/presence/heartbeat", self._api_presence_heartbeat)
        app.router.add_post("/api/duels", self._api_duel_create)
        app.router.add_get("/api/duels", self._api_duels)
        app.router.add_get("/api/duels/{duel_id}", self._api_duel_detail)
        app.router.add_post("/api/duels/{duel_id}/accept", self._api_duel_accept)
        app.router.add_post("/api/duels/{duel_id}/moves", self._api_duel_move)
        app.router.add_get("/ws/duels/{duel_id}", self._ws_duel_room)
        app.router.add_get("/api/cards/{card_id}/image", self._api_card_image)
        app.router.add_post("/auth/logout", self._oauth_logout)
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
            return web.json_response({"error": "Servidor do SoulsBot indisponível."}, status=503)
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

    async def _broadcast_duel_event(self, duel_id: int, event: str = "duel_updated") -> None:
        """Notifica em tempo real apenas os sockets autenticados da sala correspondente."""
        sockets = self._web_sockets.get(int(duel_id), set()).copy()
        if not sockets:
            return
        payload = json.dumps({"type": event, "duel_id": int(duel_id)})
        stale = []
        for socket in sockets:
            try:
                await socket.send_str(payload)
            except Exception:
                stale.append(socket)
        for socket in stale:
            self._web_sockets.get(int(duel_id), set()).discard(socket)

    async def _ws_duel_room(self, request: web.Request) -> web.StreamResponse:
        """Canal de eventos da sala; a autorização continua baseada na sessão e participação."""
        user_id = self._api_user_id(request)
        if user_id is None:
            raise web.HTTPUnauthorized(text="Faça login com Discord.")
        try:
            duel_id = int(request.match_info["duel_id"])
        except (TypeError, ValueError):
            raise web.HTTPBadRequest(text="Duelo inválido.")
        duel = await self.db.coliseu_obter_duelo(duel_id)
        if not duel or user_id not in (int(duel["creator_id"]), int(duel["opponent_id"])):
            raise web.HTTPNotFound(text="Duelo não encontrado.")
        ws = web.WebSocketResponse(heartbeat=25, max_msg_size=1024)
        await ws.prepare(request)
        room = self._web_sockets.setdefault(duel_id, set())
        room.add(ws)
        await ws.send_json({"type": "connected", "duel_id": duel_id})
        try:
            async for message in ws:
                if message.type == web.WSMsgType.ERROR:
                    break
        finally:
            room.discard(ws)
            if not room:
                self._web_sockets.pop(duel_id, None)
        return ws

    async def _api_presence_heartbeat(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        self._web_presence[user_id] = time.time()
        return web.json_response({"ok": True, "web_online": True})

    def _api_origin_ok(self, request: web.Request) -> bool:
        """Aceita apenas POSTs originados na mesma origem do painel, quando Origin existe."""
        origin = request.headers.get("Origin")
        if not origin:
            return True
        from urllib.parse import urlsplit
        parsed = urlsplit(origin)
        return parsed.scheme == "https" and parsed.netloc.lower() == request.host.lower()

    async def _api_duel_create(self, request: web.Request) -> web.Response:
        """Cria convite pelo site e publica no canal Discord configurado."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem da solicitação não autorizada."}, status=403)
        try:
            body = await request.json()
            opponent_id = int(body.get("opponent_id", 0))
            aposta = int(body.get("aposta", 0))
        except (TypeError, ValueError):
            return web.json_response({"error": "Informe jogador e aposta válidos."}, status=400)
        if opponent_id <= 0 or opponent_id == user_id or aposta < 0 or aposta > 500:
            return web.json_response({"error": "Jogador ou aposta inválidos. A aposta máxima é 500 Denários."}, status=400)
        try:
            guild_id = int(getattr(config, "GUILD_ID", 0) or 0)
            channel_id = int(os.getenv("SOULSBOT_DUELOS_CHANNEL_ID", "0") or 0)
        except (TypeError, ValueError):
            guild_id, channel_id = 0, 0
        guild = self.get_guild(guild_id) if guild_id else None
        channel = guild.get_channel(channel_id) if guild and channel_id else None
        if guild is None or channel is None or not hasattr(channel, "send"):
            return web.json_response({"error": "Configure SOULSBOT_DUELOS_CHANNEL_ID com o ID do canal de convites no Discord."}, status=503)
        creator = guild.get_member(user_id)
        opponent = guild.get_member(opponent_id)
        if creator is None or opponent is None or creator.bot or opponent.bot:
            return web.json_response({"error": "Os dois jogadores precisam ser membros humanos do servidor SoulsBot."}, status=404)
        cog = self.get_cog("ColiseuCartas")
        if cog is None:
            return web.json_response({"error": "Motor do Coliseu indisponível."}, status=503)
        from cogs.cartas_coliseu import ConviteDueloView, DIFERENCA_MAXIMA_PODER_DECK, TEMPO_RODADA_SEGUNDOS
        result = await self.db.coliseu_criar_convite(
            guild.id, channel.id, user_id, opponent_id, aposta,
            nivel_minimo=5, limite_diario=5, limite_par=2, max_aposta_dia=1500,
            cooldown_segundos=60, diferenca_maxima_poder=DIFERENCA_MAXIMA_PODER_DECK,
        )
        if result.get("status") != "ok":
            return web.json_response({"error": str(result.get("status", "falha")), "details": result}, status=409)
        duel_id = int(result["duel_id"])
        embed = discord.Embed(
            title="⚔️ Convite para o Coliseu",
            description=(f"{creator.mention} desafiou {opponent.mention} para um duelo de cinco rodadas.\n\n"
                         f"**Aposta por jogador:** {aposta} Denários\n**Pote total:** {aposta * 2} Denários\n"
                         f"**Poder dos decks:** {result['deck_power'][user_id]} × {result['deck_power'][opponent_id]}\n"
                         "As apostas só serão travadas quando o convite for aceito.\n"
                         f"Cada rodada tem {TEMPO_RODADA_SEGUNDOS} segundos. O convite expira em dois minutos."),
            color=config.COR_OURO,
        )
        embed.set_footer(text=f"Coliseu de Cartas • Duelo #{duel_id} • criado pelo site")
        try:
            embed, attachment = await cog.preparar_ficha_visual_duelo(duel_id, guild)
            kwargs = {"content": opponent.mention, "embed": embed, "view": ConviteDueloView(duel_id),
                      "allowed_mentions": discord.AllowedMentions(users=[opponent], roles=False, everyone=False)}
            if attachment is not None:
                kwargs["file"] = attachment
            message = await channel.send(**kwargs)
            await self.db.coliseu_definir_mensagem_convite(duel_id, message.id)
        except Exception:
            log.exception("Falha ao publicar convite web do duelo #%s", duel_id)
            await self.db.coliseu_decidir_convite(duel_id, user_id, False)
            return web.json_response({"error": "Não foi possível publicar o convite no Discord; o convite foi cancelado."}, status=502)
        base_url = os.getenv("SOULSBOT_PUBLIC_URL", "https://narabot.sbs").rstrip("/")
        await self._broadcast_duel_event(duel_id, "duel_created")
        return web.json_response({"ok": True, "duel_id": duel_id, "discord_message": message.jump_url,
                                  "match_url": f"{base_url}/?duel={duel_id}"}, status=201)

    async def _api_duels(self, request: web.Request) -> web.Response:
        """Lista apenas duelos dos quais a conta autenticada participa."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        try:
            rows = await self.db.coliseu_listar_duelos_usuario(user_id, limite=30)
            duels = []
            for row in rows:
                duel = dict(row)
                duels.append({
                    "id": int(duel["id"]), "status": str(duel["status"]),
                    "creator_id": str(duel["creator_id"]), "opponent_id": str(duel["opponent_id"]),
                    "aposta": int(duel["aposta"] or 0), "current_round": int(duel["current_round"] or 0),
                    "created_at": duel.get("created_at"), "expires_at": duel.get("expires_at"),
                    "round_deadline": duel.get("round_deadline"),
                    "is_creator": user_id == int(duel["creator_id"]),
                })
            return web.json_response({"duels": duels})
        except Exception:
            log.exception("Falha ao listar duelos no site para user_id=%s", user_id)
            return web.json_response({"error": "Não foi possível carregar seus duelos."}, status=500)

    async def _api_duel_detail(self, request: web.Request) -> web.Response:
        """Entrega estado e mão privada somente ao participante autenticado."""
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        try:
            duel_id = int(request.match_info["duel_id"])
        except (TypeError, ValueError):
            return web.json_response({"error": "Duelo inválido."}, status=400)
        duel = await self.db.coliseu_obter_duelo(duel_id)
        if not duel or user_id not in (int(duel["creator_id"]), int(duel["opponent_id"])):
            return web.json_response({"error": "Duelo não encontrado."}, status=404)
        rounds = [dict(row) for row in await self.db.coliseu_historico_rodadas(duel_id)]
        picks = await self.db.coliseu_contagem_jogadas_rodada(duel_id) if duel["status"] == "active" else 0
        available = await self.db.coliseu_cartas_disponiveis(duel_id, user_id) if duel["status"] == "active" else []
        # Nunca revelar a escolha secreta do adversário antes da resolução da rodada.
        own_pick = await self.db._one(
            "SELECT 1 FROM cartas_duelo_jogadas WHERE duel_id=? AND round_no=? AND user_id=?",
            (duel_id, int(duel["current_round"] or 0), user_id),
        ) if duel["status"] == "active" else None
        return web.json_response({
            "duel": {
                "id": duel_id, "status": str(duel["status"]),
                "creator_id": str(duel["creator_id"]), "opponent_id": str(duel["opponent_id"]),
                "aposta": int(duel["aposta"] or 0), "current_round": int(duel["current_round"] or 0),
                "round_deadline": duel.get("round_deadline"), "winner_id": str(duel["winner_id"]) if duel.get("winner_id") else None,
                "payout": int(duel.get("payout") or 0), "burned": int(duel.get("burned") or 0),
                "is_creator": user_id == int(duel["creator_id"]),
            },
            "score": {
                "creator": sum(1 for row in rounds if row["winner_side"] == "a"),
                "opponent": sum(1 for row in rounds if row["winner_side"] == "b"),
                "rounds_played": len(rounds), "choices_received": picks,
                "own_choice_submitted": bool(own_pick),
            },
            "available_cards": available,
            "rounds": rounds,
        })

    async def _api_duel_accept(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem da solicitação não autorizada."}, status=403)
        try:
            duel_id = int(request.match_info["duel_id"])
        except (TypeError, ValueError):
            return web.json_response({"error": "Duelo inválido."}, status=400)
        duel = await self.db.coliseu_obter_duelo(duel_id)
        if not duel or int(duel["opponent_id"]) != user_id:
            return web.json_response({"error": "Somente o jogador convidado pode aceitar."}, status=403)
        resultado = await self.db.coliseu_decidir_convite(duel_id, user_id, True)
        if resultado.get("status") != "ok":
            return web.json_response({"error": str(resultado.get("status", "indisponivel")), "details": resultado}, status=409)
        cog = self.get_cog("ColiseuCartas")
        if cog:
            try:
                await cog.atualizar_mensagem_duelo(duel_id)
            except Exception:
                log.exception("Falha ao sincronizar mensagem Discord após aceitar duelo #%s pelo site", duel_id)
        await self._broadcast_duel_event(duel_id, "duel_accepted")
        base_url = os.getenv("SOULSBOT_PUBLIC_URL", "https://narabot.sbs").rstrip("/")
        return web.json_response({"ok": True, "duel_id": duel_id, "match_url": f"{base_url}/?duel={duel_id}"})

    async def _api_duel_move(self, request: web.Request) -> web.Response:
        user_id = self._api_user_id(request)
        if user_id is None:
            return web.json_response({"error": "Autenticação necessária."}, status=401)
        if not self._api_origin_ok(request):
            return web.json_response({"error": "Origem da solicitação não autorizada."}, status=403)
        try:
            duel_id = int(request.match_info["duel_id"])
            body = await request.json()
            card_id = str(body.get("card_id", "")).strip()
        except (TypeError, ValueError):
            return web.json_response({"error": "Dados da jogada inválidos."}, status=400)
        if not card_id or len(card_id) > 100:
            return web.json_response({"error": "Carta inválida."}, status=400)
        duel = await self.db.coliseu_obter_duelo(duel_id)
        if not duel or user_id not in (int(duel["creator_id"]), int(duel["opponent_id"])):
            return web.json_response({"error": "Duelo não encontrado."}, status=404)
        resultado = await self.db.coliseu_registrar_jogada(duel_id, user_id, card_id)
        if resultado.get("status") == "pronto":
            cog = self.get_cog("ColiseuCartas")
            if cog is None:
                return web.json_response({"error": "Motor do Coliseu indisponível."}, status=503)
            try:
                await cog.resolver_rodada(resultado)
                await cog.atualizar_mensagem_duelo(duel_id, revelar_ultima_rodada=True)
            except Exception:
                log.exception("Falha ao resolver rodada %s do duelo #%s via site", resultado.get("round_no"), duel_id)
                return web.json_response({"error": "A jogada foi registrada, mas houve falha ao resolver a rodada. Atualize a partida."}, status=500)
            await self._broadcast_duel_event(duel_id, "round_resolved")
            return web.json_response({"ok": True, "status": "round_resolved"})
        if resultado.get("status") == "aguardando":
            cog = self.get_cog("ColiseuCartas")
            if cog:
                try:
                    await cog.atualizar_mensagem_duelo(duel_id)
                except Exception:
                    log.exception("Falha ao atualizar painel Discord do duelo #%s", duel_id)
            await self._broadcast_duel_event(duel_id, "move_received")
            return web.json_response({"ok": True, "status": "waiting_opponent"})
        status_http = 409 if resultado.get("status") in {"ja_escolheu", "carta_usada", "carta_invalida", "expirado", "inativo"} else 403
        return web.json_response({"error": str(resultado.get("status", "falha"))}, status=status_http)

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

    async def _api_collection(self, request: web.Request) -> web.Response:
        """Retorna somente a coleção do usuário autenticado, usando o banco atual do bot."""
        raw_session = request.cookies.get(WEB_SESSION_COOKIE, "")
        payload = _validar_payload_assinado(raw_session)
        if not payload:
            return web.json_response({"authenticated": False}, status=401)

        try:
            user_id_raw, expires_raw = payload.split(":", 1)
            expires_at = int(expires_raw)
        except (ValueError, TypeError):
            return web.json_response({"authenticated": False}, status=401)

        if not user_id_raw.isdigit() or expires_at < int(time.time()):
            return web.json_response({"authenticated": False}, status=401)

        user_id = int(user_id_raw)
        try:
            from sistemas.cartas import get_carta, carta_de_jogo_por_id

            estado = await self.db.coliseu_estado_usuario(user_id)
            rows = await self.db.coliseu_listar_colecao(user_id)
            cartas = []

            for row in rows:
                card_id = str(row["card_id"])
                carta = get_carta(card_id)
                if carta is None and card_id.startswith("jogo_") and row["game_name"]:
                    try:
                        carta = carta_de_jogo_por_id(card_id, str(row["game_name"]))
                    except ValueError:
                        carta = None
                if carta is None:
                    log.warning(
                        "Carta da coleção não encontrada no catálogo: user_id=%s card_id=%s",
                        user_id, card_id,
                    )
                    continue

                item = carta.para_dict()
                item["quantidade"] = int(row["quantidade"] or 1)
                item["source"] = str(row["source"] or "")
                item["obtained_at"] = str(row["obtained_at"] or "")
                item["image_url"] = f"/api/cards/{card_id}/image"
                cartas.append(item)

            return web.json_response({
                "authenticated": True,
                "summary": {
                    "cards": int(estado["cartas"]),
                    "souls": int(estado["almas"]),
                    "denarios": int(estado["denarios"]),
                    "deck_cards": int(estado["deck"]),
                },
                "collection": cartas,
            })
        except Exception:
            log.exception("Falha ao consultar coleção web do usuário %s.", user_id)
            raise web.HTTPInternalServerError(text="Não foi possível carregar sua coleção.")

    async def _api_deck(self, request: web.Request) -> web.Response:
        """Retorna o deck salvo do jogador autenticado, compartilhado com os duelos do Discord."""
        raw_session = request.cookies.get(WEB_SESSION_COOKIE, "")
        payload = _validar_payload_assinado(raw_session)
        if not payload:
            raise web.HTTPUnauthorized(text="Faça login com o Discord.")
        try:
            user_id_raw, expires_raw = payload.split(":", 1)
            expires_at = int(expires_raw)
        except (ValueError, TypeError):
            raise web.HTTPUnauthorized(text="Sessão inválida.")
        if not user_id_raw.isdigit() or expires_at < int(time.time()):
            raise web.HTTPUnauthorized(text="Sessão expirada.")

        user_id = int(user_id_raw)
        try:
            deck = await self.db.coliseu_obter_deck(user_id)
            return web.json_response({
                "authenticated": True,
                "deck": [{**carta, "image_url": f"/api/cards/{carta['id']}/image"} for carta in deck],
                "rules": {"cards": 5, "max_cost": 12, "max_legendary": 1, "unique_cards": True},
            })
        except Exception:
            log.exception("Falha ao consultar deck web do usuário %s.", user_id)
            raise web.HTTPInternalServerError(text="Não foi possível carregar seu deck.")

    async def _api_deck_save(self, request: web.Request) -> web.Response:
        """Salva somente IDs de cartas; o banco valida posse e reconstrói atributos canônicos."""
        raw_session = request.cookies.get(WEB_SESSION_COOKIE, "")
        payload = _validar_payload_assinado(raw_session)
        if not payload:
            raise web.HTTPUnauthorized(text="Faça login com o Discord.")
        try:
            user_id_raw, expires_raw = payload.split(":", 1)
            expires_at = int(expires_raw)
        except (ValueError, TypeError):
            raise web.HTTPUnauthorized(text="Sessão inválida.")
        if not user_id_raw.isdigit() or expires_at < int(time.time()):
            raise web.HTTPUnauthorized(text="Sessão expirada.")

        # Bloqueia submissões cross-site. O site e a API são servidos na mesma origem.
        origin = request.headers.get("Origin")
        if origin:
            from urllib.parse import urlsplit
            origem = urlsplit(origin)
            if origem.scheme != "https" or origem.netloc.lower() != request.host.lower():
                raise web.HTTPForbidden(text="Origem da solicitação não autorizada.")
        if request.content_type != "application/json":
            raise web.HTTPUnsupportedMediaType(text="Envie os dados em JSON.")
        try:
            body = await request.json()
        except (ValueError, TypeError):
            raise web.HTTPBadRequest(text="JSON inválido.")
        card_ids = body.get("card_ids") if isinstance(body, dict) else None
        if not isinstance(card_ids, list) or len(card_ids) != 5 or any(not isinstance(x, str) or not x or len(x) > 120 for x in card_ids):
            raise web.HTTPBadRequest(text="Envie exatamente cinco IDs de cartas.")
        if len(set(card_ids)) != 5:
            raise web.HTTPBadRequest(text="Não é permitido repetir uma carta no deck.")

        try:
            resultado = await self.db.coliseu_salvar_deck(
                int(user_id_raw), [{"id": card_id} for card_id in card_ids]
            )
            status = resultado.get("status")
            if status == "ok":
                deck = await self.db.coliseu_obter_deck(int(user_id_raw))
                return web.json_response({"ok": True, "deck": deck, "custo": resultado.get("custo", 0)})
            if status == "invalido":
                return web.json_response({"ok": False, "error": resultado.get("motivo", "Deck inválido.")}, status=400)
            if status == "nao_possui":
                return web.json_response({"ok": False, "error": "Uma das cartas não pertence à sua coleção."}, status=403)
            if status == "carta_indisponivel":
                return web.json_response({"ok": False, "error": "Uma das cartas não está disponível no catálogo."}, status=400)
            raise web.HTTPInternalServerError(text="Não foi possível salvar o deck.")
        except web.HTTPException:
            raise
        except Exception:
            log.exception("Falha ao salvar deck web do usuário %s.", user_id_raw)
            raise web.HTTPInternalServerError(text="Não foi possível salvar seu deck.")

    async def _api_card_image(self, request: web.Request) -> web.Response:
        """Entrega o PNG da carta somente ao dono autenticado da carta."""
        raw_session = request.cookies.get(WEB_SESSION_COOKIE, "")
        payload = _validar_payload_assinado(raw_session)
        if not payload:
            raise web.HTTPUnauthorized(text="Faça login com o Discord.")

        try:
            user_id_raw, expires_raw = payload.split(":", 1)
            expires_at = int(expires_raw)
        except (ValueError, TypeError):
            raise web.HTTPUnauthorized(text="Sessão inválida.")

        if not user_id_raw.isdigit() or expires_at < int(time.time()):
            raise web.HTTPUnauthorized(text="Sessão expirada.")

        user_id = int(user_id_raw)
        card_id = str(request.match_info.get("card_id", "")).strip()
        if not card_id or len(card_id) > 120:
            raise web.HTTPNotFound(text="Carta não encontrada.")

        try:
            rows = await self.db.coliseu_listar_colecao(user_id)
            row = next((item for item in rows if str(item["card_id"]) == card_id), None)
            if row is None:
                # Não revela se a carta existe na coleção de outra pessoa.
                raise web.HTTPNotFound(text="Carta não encontrada.")

            cog = self.get_cog("ColiseuCartas")
            if cog is None:
                raise web.HTTPServiceUnavailable(text="Sistema de cartas indisponível.")

            carta = cog._carta_da_linha(row)
            if carta is None:
                raise web.HTTPNotFound(text="Carta não encontrada no catálogo.")

            arte_personalizada = await cog._obter_arte_personalizada(user_id, card_id)
            if arte_personalizada:
                from sistemas.arte_cartas import render_carta_bytes
                imagem = render_carta_bytes(carta, arte_personalizada)
                png = imagem.getvalue()
            else:
                from sistemas.arte_cartas import render_carta
                caminho = render_carta(carta)
                png = caminho.read_bytes()

            return web.Response(
                body=png,
                content_type="image/png",
                headers={
                    "Content-Disposition": "inline",
                    "Cache-Control": "private, no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )
        except web.HTTPException:
            raise
        except Exception:
            log.exception(
                "Falha ao renderizar imagem da carta para usuário %s (card_id=%s).",
                user_id, card_id,
            )
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
                    # /nara e /adm ficam no escopo do servidor configurado,
                    # removendo também a versão global antiga.
                    self.tree.clear_commands(guild=None)
                    await self.tree.sync()
                    log.info("Comandos globais antigos removidos.")
                else:
                    # Sem GUILD_ID, publica somente os dois comandos globalmente.
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
                log.exception("Falha ao forçar a sincronização exclusiva de /nara e /adm.")
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
