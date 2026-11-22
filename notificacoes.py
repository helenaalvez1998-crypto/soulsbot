"""Envio centralizado de notificações privadas, sempre respeitando opt-out."""
from __future__ import annotations

import logging

import discord

log = logging.getLogger("nara.notificacoes")


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
