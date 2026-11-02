"""Camada de abstração para configurações por servidor (guild).

Todas as configurações que antes eram hardcodadas em config.py agora podem ser
definidas por servidor via painel /adm. Os valores são persistidos no KV store
do banco de dados (chave: guild:{guild_id}:{key}). Quando não há valor salvo,
o sistema faz fallback transparente para config.py.
"""

import config


# Mapeamento: chave interna -> (atributo em config.py, tipo de cast)
# Adicione novas chaves aqui quando expandir o painel administrativo.
KEYS = {
    # ── Canais ────────────────────────────────────────────────────────
    "mod_channel":        ("MOD_CHANNEL_ID", int),
    "platinas_channel":   ("PLATINAS_CHANNEL_ID", int),
    "video_channel":      ("VIDEO_CHANNEL_ID", int),
    "live_channel":       ("LIVE_CHANNEL_ID", int),
    "zerados_channel":    ("ZERADOS_CHANNEL_ID", int),
    "perfis_channel":     ("PERFIS_CHANNEL_ID", int),
    "games_channel":      ("GAMES_CHANNEL_ID", int),
    "promos_channel":     ("PROMOS_CHANNEL_ID", int),

    # ── Cargos ────────────────────────────────────────────────────────
    "mod_role":           ("MOD_ROLE_ID", int),
    "role_video":         ("ROLE_VIDEO", int),
    "role_live":          ("ROLE_LIVE", int),

    # ── Economia / Recompensas ────────────────────────────────────────
    "xp_platina":         ("XP_PLATINA", int),
    "denarios_platina":   ("DENARIOS_PLATINA", int),
    "xp_zerado":          ("XP_ZERADO", int),
    "denarios_zerado":    ("DENARIOS_ZERADO", int),
    "zerados_xp_limite":  ("ZERADOS_XP_LIMITE_DIARIO", int),
}

# Rótulos legíveis para exibição no painel administrativo
LABELS = {
    "mod_channel":        "Canal de moderação",
    "platinas_channel":   "Canal de anúncio de platinas",
    "video_channel":      "Canal de vídeos do YouTube",
    "live_channel":       "Canal de lives do YouTube",
    "zerados_channel":    "Canal de anúncio de zerados",
    "perfis_channel":     "Canal de santuários/perfis",
    "games_channel":      "Canal de jogos grátis",
    "promos_channel":     "Canal de promoções",
    "mod_role":           "Cargo de moderador",
    "role_video":         "Cargo de aviso de vídeo",
    "role_live":          "Cargo de aviso de live",
    "xp_platina":         "XP por platina aprovada",
    "denarios_platina":   "Denários por platina aprovada",
    "xp_zerado":          "XP por jogo zerado",
    "denarios_zerado":    "Denários por jogo zerado",
    "zerados_xp_limite":  "Limite diário de XP por zerados",
}

# Agrupamento das chaves por seção do painel
SECTIONS = {
    "channels": ["mod_channel", "platinas_channel", "video_channel", "live_channel",
                 "zerados_channel", "perfis_channel", "games_channel", "promos_channel"],
    "roles":    ["mod_role", "role_video", "role_live"],
    "economy":  ["xp_platina", "denarios_platina", "xp_zerado", "denarios_zerado",
                 "zerados_xp_limite"],
}


class GuildConfig:
    """Acessa configurações do servidor com fallback para config.py."""

    @staticmethod
    async def get(db, guild_id: int, key: str):
        """Retorna o valor configurado para a guild, ou o fallback de config.py."""
        if key not in KEYS:
            return None
        raw = await db.get_kv(f"guild:{guild_id}:{key}")
        if raw is not None and raw != "":
            _, cast = KEYS[key]
            try:
                return cast(raw)
            except (ValueError, TypeError):
                pass
        attr, _ = KEYS[key]
        return getattr(config, attr, None)

    @staticmethod
    async def set(db, guild_id: int, key: str, value) -> None:
        """Salva um valor de configuração para a guild."""
        await db.set_kv(f"guild:{guild_id}:{key}", str(value))

    @staticmethod
    async def reset(db, guild_id: int, key: str) -> None:
        """Remove a configuração da guild, revertendo ao fallback de config.py."""
        await db.set_kv(f"guild:{guild_id}:{key}", "")

    @staticmethod
    async def get_all(db, guild_id: int) -> dict:
        """Retorna todas as configurações da guild com seus valores efetivos."""
        result = {}
        for key in KEYS:
            result[key] = await GuildConfig.get(db, guild_id, key)
        return result

    @staticmethod
    async def is_custom(db, guild_id: int, key: str) -> bool:
        """Verifica se a guild tem um valor personalizado (não usa fallback)."""
        raw = await db.get_kv(f"guild:{guild_id}:{key}")
        return raw is not None and raw != ""

    @staticmethod
    async def reset_all(db, guild_id: int) -> int:
        """Reseta todas as configurações da guild. Retorna quantas foram limpas."""
        count = 0
        for key in KEYS:
            if await GuildConfig.is_custom(db, guild_id, key):
                await GuildConfig.reset(db, guild_id, key)
                count += 1
        return count