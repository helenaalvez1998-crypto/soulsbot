"""Validação dos links/@ das redes do santuário (sem depender do discord.py)."""
import re
from urllib.parse import quote, urlparse

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
