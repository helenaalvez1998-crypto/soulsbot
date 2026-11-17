"""Entrypoint e ciclo de vida do NARA.

Start command recomendado (FadeHost): python bot.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import traceback
from io import BytesIO
from typing import Any

import discord
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
)

COMANDOS_PRINCIPAIS = frozenset({"nara", "adm", "nara_relacionamento"})


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
