import logging
import discord

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
