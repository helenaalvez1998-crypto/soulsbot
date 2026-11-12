"""Entrypoint e ciclo de vida do NARA.

Start command recomendado (FadeHost): python bot.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

import config
from database import Database


LOG_LEVEL = getattr(logging, config.LOG_LEVEL, logging.INFO)
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logging.captureWarnings(True)
log = logging.getLogger("nara")

EXTENSOES = (
    "cogs.admin", "cogs.perfil", "cogs.platinas", "cogs.loja", "cogs.ranking",
    "cogs.colizeu", "cogs.cargos", "cogs.progressao", "cogs.youtube",
    "cogs.ofertas", "cogs.zerados", "cogs.santuario", "cogs.soulslike",
    "cogs.transmissoes", "cogs.nara_ia", "cogs.painel_rotativo",
    "cogs.painel_membros", "cogs.catalogo_integrado", "cogs.game_news",
)

COMANDOS_PRINCIPAIS = frozenset({"nara", "adm"})


def _manter_apenas_comandos_principais(tree) -> list[str]:
    """Remove da árvore local todos os slash commands exceto /nara e /adm."""
    removidos = []
    for comando in list(tree.get_commands()):
        if comando.name not in COMANDOS_PRINCIPAIS:
            tree.remove_command(comando.name)
            removidos.append(comando.name)
    restantes = {comando.name for comando in tree.get_commands()}
    if restantes != COMANDOS_PRINCIPAIS:
        raise RuntimeError(
            "A árvore de comandos precisa conter exatamente /nara e /adm; "
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


class NaraCommandTree(app_commands.CommandTree):
    """Tratamento central de erros de slash commands com resposta privada."""

    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        command = getattr(interaction, "command", None)
        command_name = getattr(command, "qualified_name", "comando desconhecido")
        original = error.original if isinstance(error, app_commands.CommandInvokeError) else error

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

        try:
            if interaction.response.is_done():
                await interaction.followup.send(mensagem, ephemeral=True)
            else:
                await interaction.response.send_message(mensagem, ephemeral=True)
        except (discord.HTTPException, discord.InteractionResponded, RuntimeError):
            log.debug("A interação de /%s expirou antes da resposta amigável.", command_name, exc_info=True)


class NaraBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
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

        await self.db.connect()
        log.info("SQLite conectado: %s", config.DB_PATH)

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
            await self.db.close()
            log.info("Conexão SQLite encerrada.")


def main() -> None:
    if not config.TOKEN:
        raise SystemExit("Configuração ausente: defina DISCORD_TOKEN nas variáveis de ambiente da hospedagem.")
    NaraBot().run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
