"""Utilitários compartilhados do NARA: canais/painéis, identidade visual, redes sociais,
notificações privadas e navegação entre painéis."""
from __future__ import annotations

import hashlib
import logging
import discord
import datetime as dt
import re
from urllib.parse import quote, urlparse
from collections.abc import Awaitable, Callable


# ======================================================================
# Canais e painéis persistentes
# ======================================================================

log = logging.getLogger("colizeu")


async def get_text_channel(bot, channel_id: int):
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            log.exception("Não foi possível acessar o canal Discord %s", channel_id)
            return None
    if not hasattr(channel, "send"):
        log.error("O ID %s não corresponde a um canal que aceita mensagens.", channel_id)
        return None
    return channel


async def erro_comando(interaction: discord.Interaction, error):
    from discord import app_commands
    if isinstance(error, app_commands.MissingPermissions):
        msg = "Você precisa da permissão **Gerenciar servidor** para usar esse comando."
    else:
        log.error("Erro em comando", exc_info=error)
        msg = "Ocorreu um erro. Confira os logs da FadeHost."
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


async def upsert_panel(bot, channel, key: str, *, marker: str | None = None, **message_kwargs):
    """Cria ou atualiza uma publicação persistente, evitando painéis duplicados.

    A chave é específica para canal/servidor. Se o ID salvo sumiu, procura uma publicação
    recente com o custom_id do painel antes de criar outra.
    """
    db = getattr(bot, "db", None)
    message_id = await db.get_kv(key) if db else None
    if message_id:
        try:
            message = await channel.fetch_message(int(message_id))
            await message.edit(**message_kwargs)
            return message, False
        except (discord.NotFound, ValueError):
            pass
        except discord.Forbidden:
            raise
        except discord.HTTPException:
            log.exception("Falha ao editar painel persistente %s", key)
            raise

    if marker and hasattr(channel, "history"):
        try:
            async for old in channel.history(limit=50):
                found = any(
                    (getattr(component, "custom_id", None) == marker or (marker.endswith("*") and str(getattr(component, "custom_id", "")).startswith(marker[:-1])))
                    for row in (getattr(old, "components", []) or [])
                    for component in getattr(row, "children", [])
                )
                if found:
                    await old.edit(**message_kwargs)
                    if db:
                        await db.set_kv(key, str(old.id))
                    return old, False
        except (discord.Forbidden, discord.HTTPException):
            log.debug("Não foi possível localizar painel anterior %s", key, exc_info=True)

    message = await channel.send(**message_kwargs)
    if db:
        await db.set_kv(key, str(message.id))
    return message, True


# ======================================================================
# Identidade visual do Colizeu: cores, símbolos e pequenos auxiliares compartilhados
# ======================================================================

# Cor de destaque por patente: quanto mais alta a patente, mais "nobre" o tom.
# Isso diferencia novatos, ativos e veteranos sem precisar de texto extra.
COR_PATENTE = {
    "Cinzas Novatas": 0x7A736B,
    "Guerreiro Caído": 0x8C6D4F,
    "Caçador de Almas": 0x5F7F8C,
    "Cavaleiro do Abismo": 0x3F6FA8,
    "Guardião das Cinzas": 0x5E5A8C,
    "Arauto da Ruína": 0x8B2E3C,
    "Executor Sombrio": 0x6D1F2B,
    "Senhor das Almas": 0xB8862B,
    "Lenda do Coliseu": 0xD4AF37,
    "Sentinela Imortal": 0xF1D77A,
}

LINHA = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
MARCA = "⚔️ Colizeu"


def rodape(secao: str | None = None) -> str:
    """Rodapé padrão: 'Colizeu · Seção'."""
    return f"{MARCA} · {secao}" if secao else MARCA


def barra(fracao: float, tamanho: int = 12) -> str:
    fracao = max(0.0, min(1.0, fracao))
    cheio = int(round(fracao * tamanho))
    return "▰" * cheio + "▱" * (tamanho - cheio)


def fmt_data(valor) -> str:
    try:
        return dt.date.fromisoformat(str(valor)).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(valor)


def fmt_tempo(seg: int) -> str:
    h, resto = divmod(int(seg), 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}"


# ======================================================================
# Validação dos links/@ das redes do santuário (sem depender do discord.py)
# ======================================================================

# chave: (nome, emoji, domínios aceitos, modelo de URL quando a pessoa digita só o @)
REDES = {
    # Plataformas de jogos: links de perfil quando a loja oferece URL pública.
    "steam":     ("Steam",             "🎮", ("steamcommunity.com",), "https://steamcommunity.com/id/{}"),
    "epic":      ("Epic Games",        "🟣", ("epicgames.com",), "https://store.epicgames.com/"),
    "gog":       ("GOG",               "🟠", ("gog.com",), "https://www.gog.com/"),
    "ea":        ("EA app",            "🔷", ("ea.com",), "https://www.ea.com/"),
    "ubisoft":   ("Ubisoft Connect",   "🔹", ("ubisoft.com",), "https://www.ubisoft.com/"),
    "battlenet": ("Battle.net",        "🔵", ("battle.net",), "https://battle.net/"),
    "itchio":    ("itch.io",           "🟥", ("itch.io",), "https://{}.itch.io"),
    "psn":       ("PlayStation",       "🔵", ("psnprofiles.com", "playstation.com", "exophase.com"), "https://psnprofiles.com/{}"),
    "xbox":      ("Xbox / Microsoft",  "🟢", ("xbox.com", "xboxgamertag.com", "trueachievements.com"), "https://www.xbox.com/play/user/{}"),
    "twitch":    ("Twitch",      "🟣", ("twitch.tv",), "https://twitch.tv/{}"),
    "youtube":   ("YouTube",     "🔴", ("youtube.com", "youtu.be"), "https://youtube.com/@{}"),
    "instagram": ("Instagram",   "📸", ("instagram.com",), "https://instagram.com/{}"),
    "tiktok":    ("TikTok",      "🎵", ("tiktok.com",), "https://tiktok.com/@{}"),
    "x":         ("X / Twitter", "🐦", ("x.com", "twitter.com"), "https://x.com/{}"),
}

_HANDLE = re.compile(r"[A-Za-z0-9_.\- ]{2,40}")


def normalizar_link(chave: str, texto: str) -> str | None:
    """'' = remover o link; None = inválido; senão devolve a URL https pronta."""
    if chave not in REDES:
        return None
    t = (texto or "").strip()
    if not t:
        return ""
    _, _, dominios, modelo = REDES[chave]
    if t.lower().startswith(("http://", "https://")):
        u = urlparse(t)
        host = (u.hostname or "").lower()
        if u.username or u.password or u.port:
            return None
        if not any(host == d or host.endswith("." + d) for d in dominios):
            return None
        url = f"https://{host}{u.path or ''}" + (f"?{u.query}" if u.query else "")
    else:
        h = t.lstrip("@").strip()
        if not _HANDLE.fullmatch(h):
            return None
        url = modelo.format(quote(h))
    url = url.replace("(", "%28").replace(")", "%29")
    return url if len(url) <= 200 else None


# ======================================================================
# Envio centralizado de notificações privadas, sempre respeitando opt-out
# ======================================================================



async def notificar_usuario(
    bot,
    guild_id: int | None,
    user_id: int,
    categoria: str,
    mensagem: str,
) -> bool:
    """Envia uma DM quando a categoria está ativa; falha de DM não interrompe o fluxo."""
    if guild_id is not None:
        try:
            preferencias = await bot.db.get_preferencias_notificacao(int(guild_id), int(user_id))
            if not preferencias.get(categoria, True):
                return False
        except Exception:
            # Se a leitura de preferências falhar, não bloquear uma decisão já concluída.
            log.exception("Não foi possível ler preferências de notificação de user=%s", user_id)
    try:
        usuario = bot.get_user(int(user_id))
        if usuario is None:
            usuario = await bot.fetch_user(int(user_id))
        await usuario.send(mensagem)
        return True
    except (discord.Forbidden, discord.HTTPException):
        # A DM pode estar bloqueada. Guarda o aviso no inbox do servidor para não perder
        # uma aprovação/rejeição; a chave evita duplicar a mesma notificação em retries.
        if guild_id is not None:
            try:
                chave = hashlib.sha256(
                    f"{int(guild_id)}:{int(user_id)}:{categoria}:{mensagem}".encode("utf-8")
                ).hexdigest()
                registrada = await bot.db.registrar_notificacao_pendente(
                    int(guild_id), int(user_id), categoria, mensagem, chave
                )
                if registrada:
                    log.info(
                        "DM indisponível para user=%s; notificação '%s' guardada no inbox",
                        user_id, categoria,
                    )
            except Exception:
                log.exception(
                    "DM indisponível e falha ao guardar notificação '%s' para user=%s",
                    categoria, user_id,
                )
        else:
            log.info("DM indisponível para user=%s; notificação '%s' não foi entregue", user_id, categoria)
        return False
    except Exception:
        log.exception("Falha inesperada enviando notificação '%s' para user=%s", categoria, user_id)
        return False


# ======================================================================
# Utilitários compartilhados para navegação entre painéis efêmeros do NARA
# ======================================================================

CallbackVoltar = Callable[[discord.Interaction], Awaitable[None]]


class VoltarPainelButton(discord.ui.Button):
    """Botão que restaura o painel imediatamente anterior na mesma mensagem."""

    def __init__(
        self,
        callback_voltar: CallbackVoltar,
        *,
        label: str = "Voltar ao painel anterior",
        emoji: str = "↩️",
        row: int | None = None,
    ):
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            row=row,
        )
        self.callback_voltar = callback_voltar

    async def callback(self, interaction: discord.Interaction):
        await self.callback_voltar(interaction)


def adicionar_botao_voltar(
    view: discord.ui.View | None,
    callback_voltar: CallbackVoltar | None,
    *,
    label: str = "Voltar ao painel anterior",
    emoji: str = "↩️",
) -> discord.ui.View | None:
    """Adiciona um botão de retorno uma única vez, sem alterar os outros itens."""
    if view is None or callback_voltar is None:
        return view
    # Guarda o callback para que telas dinâmicas possam reconstruir a View
    # depois de clear_items() sem perder a navegação.
    view._nara_callback_voltar = callback_voltar
    if any(isinstance(item, VoltarPainelButton) for item in view.children):
        view._nara_botao_voltar = True
        return view
    if len(view.children) >= 25:
        # Discord limita Views a 25 componentes. Não removemos controles funcionais
        # para encaixar o botão: o chamador pode exibir uma mensagem de fallback.
        return view
    view.add_item(VoltarPainelButton(callback_voltar, label=label, emoji=emoji))
    view._nara_botao_voltar = True
    return view


def restaurar_botao_voltar(view: discord.ui.View | None) -> discord.ui.View | None:
    """Reinsere o botão de retorno após uma View dinâmica reconstruir seus itens."""
    if view is None:
        return view
    callback = getattr(view, "_nara_callback_voltar", None)
    if callback is None:
        return view
    return adicionar_botao_voltar(view, callback)


def view_so_com_voltar(callback_voltar: CallbackVoltar) -> discord.ui.View:
    """Cria uma View curta para resultados que, de outro modo, seriam telas sem navegação."""
    view = discord.ui.View(timeout=600)
    adicionar_botao_voltar(view, callback_voltar)
    return view
