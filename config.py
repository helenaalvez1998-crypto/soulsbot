"""Configuração central do NARA: variáveis de ambiente, constantes e caminhos persistentes."""
from __future__ import annotations

import os
from pathlib import Path
import logging
import shutil
import re as _re
from datetime import timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dotenv import load_dotenv


# ======================================================================
# Resolução única dos caminhos persistentes do NARA
# ======================================================================

def get_data_dir() -> Path:
    """Retorna o diretório de dados configurado sem depender do diretório atual."""
    configured = os.getenv("DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    persistent_volume = Path("/data")
    if persistent_volume.is_dir():
        return persistent_volume
    return Path(__file__).resolve().parent / "data"


def get_state_path(env_name: str, default_filename: str) -> Path:
    """Retorna caminho override por variável de ambiente ou arquivo dentro de DATA_DIR."""
    configured = os.getenv(env_name, "").strip()
    if configured:
        return Path(configured).expanduser()
    return get_data_dir() / default_filename


# ======================================================================
# Variáveis de ambiente e constantes
# ======================================================================

load_dotenv()

_log = logging.getLogger("nara.config")

def _env_int(nome: str, padrao: int, *, minimo: int | None = None, maximo: int | None = None) -> int:
    """Lê inteiros sem derrubar o processo por placeholder/valor inválido no .env."""
    raw = os.getenv(nome)
    if raw is None or not raw.strip():
        return padrao
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        _log.warning("Valor inválido para %s; usando padrão %s.", nome, padrao)
        return padrao
    if minimo is not None and value < minimo:
        _log.warning("%s abaixo do mínimo; usando padrão %s.", nome, padrao)
        return padrao
    if maximo is not None and value > maximo:
        _log.warning("%s acima do máximo; usando padrão %s.", nome, padrao)
        return padrao
    return value

# Identidade visual (preto, dourado, prata)
COR_OURO = 0xD4AF37
COR_PRATA = 0xC0C0C0
COR_PRETO = 0x0D0D0D

# Configuração principal do Discord e da economia. IDs vazios/ inválidos usam 0.
GUILD_ID = _env_int("GUILD_ID", 0) or None
MOD_CHANNEL_ID = _env_int("MOD_CHANNEL_ID", 0)
SOULSLIKE_CHANNEL_ID = _env_int("SOULSLIKE_CHANNEL_ID", 0)
COLIZEU_CHANNEL_ID = _env_int("COLIZEU_CHANNEL_ID", 0)
# Canal privado único para a biblioteca de artes e a fila de aprovação do Ateliê.
COLISEU_ART_CHANNEL_ID = _env_int("COLISEU_ART_CHANNEL_ID", 0)
NARA_CHANNEL_ID = _env_int("NARA_CHANNEL_ID", 0)
PLATINAS_CHANNEL_ID = _env_int("PLATINAS_CHANNEL_ID", 0)
MOD_ROLE_ID = _env_int("MOD_ROLE_ID", 0)
PERFIS_CHANNEL_ID = _env_int("PERFIS_CHANNEL_ID", 0)
ZERADOS_CHANNEL_ID = _env_int("ZERADOS_CHANNEL_ID", 0)
LORE_CHANNEL_ID = _env_int("LORE_CHANNEL_ID", 0)
GUIDES_CHANNEL_ID = _env_int("GUIDES_CHANNEL_ID", 0)
COMMUNITY_CHANNEL_ID = _env_int("COMMUNITY_CHANNEL_ID", 0)
DATA_DIR = get_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _migrar_dados_legados_para_volume_persistente() -> None:
    """Migra cache/templates do diretório do deploy para o volume /data.

    Na FadeHost, /data/app é recriado a cada deploy, enquanto /data persiste.
    Versões anteriores podiam deixar arquivos em /data/app/data; copiar apenas
    arquivos ausentes preserva o conteúdo já existente no volume persistente.
    """
    origem = Path(__file__).resolve().parent / "data"
    try:
        if not origem.is_dir() or origem.resolve() == DATA_DIR.resolve():
            return
    except OSError:
        return

    copiados = 0
    falhas = 0
    # Somente dados de cartas: não copiar bancos ou outros estados por acidente.
    for nome in ("cartas_cache", "cartas_templates"):
        pasta_origem = origem / nome
        if not pasta_origem.is_dir():
            continue
        for arquivo in pasta_origem.rglob("*"):
            if not arquivo.is_file():
                continue
            try:
                relativo = arquivo.relative_to(origem)
                destino = DATA_DIR / relativo
                if destino.exists():
                    continue
                destino.parent.mkdir(parents=True, exist_ok=True)
                # Escrita temporária + replace evita deixar cópia parcial.
                temporario = destino.with_name(destino.name + ".migrating")
                shutil.copy2(arquivo, temporario)
                temporario.replace(destino)
                copiados += 1
            except OSError:
                falhas += 1

    if copiados or falhas:
        _log.info(
            "Migração de dados de cartas concluída: %s arquivo(s) copiado(s), %s falha(s); destino=%s",
            copiados, falhas, DATA_DIR,
        )
    else:
        _log.info("Volume persistente de cartas verificado: destino=%s; nenhum arquivo legado pendente", DATA_DIR)


_migrar_dados_legados_para_volume_persistente()
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "colizeu.db")).strip() or str(DATA_DIR / "colizeu.db")

XP_PLATINA = _env_int("XP_PLATINA", 200, minimo=0)
DENARIOS_PLATINA = _env_int("DENARIOS_PLATINA", 50, minimo=0)
XP_ZERADO = _env_int("XP_ZERADO", 50, minimo=0)
DENARIOS_ZERADO = _env_int("DENARIOS_ZERADO", 10, minimo=0)
ZERADOS_XP_LIMITE_DIARIO = _env_int("ZERADOS_XP_LIMITE_DIARIO", 3, minimo=0)
COMMUNITY_XP_DEFAULT = _env_int("COMMUNITY_XP_DEFAULT", 10, minimo=0)
COMMUNITY_XP_WEEKLY_CAP = _env_int("COMMUNITY_XP_WEEKLY_CAP", 50, minimo=0)


# =====================================================================
# Configurações herdadas da instalação anterior (YouTube, ofertas, cargos)
# Os nomes das variáveis de ambiente são os mesmos de antes.
# =====================================================================

def _env_bool(nome: str, padrao: bool) -> bool:
    return os.getenv(nome, str(padrao)).strip().lower() in ("1", "true", "sim", "yes")

# Evita apagar comandos globais por acidente ao sincronizar comandos em um servidor.
CLEAR_GLOBAL_COMMANDS_ON_GUILD_SYNC = _env_bool("CLEAR_GLOBAL_COMMANDS_ON_GUILD_SYNC", False)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
if LOG_LEVEL not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
    LOG_LEVEL = "INFO"


TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
BOT_OWNER_ID = _env_int("BOT_OWNER_ID", 0)
# Conta do criador no Discord; o apelido público pode mudar, a identidade não.
SOULS_USER_ID = 1300117955236991046
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "").strip()

# Canais do Discord
VIDEO_CHANNEL_ID = _env_int("CREATOR_VIDEO_CHANNEL_ID", 0)
LIVE_CHANNEL_ID = _env_int("CREATOR_LIVE_CHANNEL_ID", 0)
GAMES_CHANNEL_ID = _env_int("GAMES_CHANNEL_ID", 0)
PROMOS_CHANNEL_ID = _env_int("PROMOS_CHANNEL_ID", 0)

# Cargos mencionados nos avisos (criados pelo script do servidor)
ROLE_VIDEO = os.getenv("ROLE_VIDEO_NAME", "🔔 Avisos de Vídeo")
ROLE_LIVE = os.getenv("ROLE_LIVE_NAME", "🔴 Avisos de Live")

# Vídeos novos: RSS (leve, sem custo de cota).
# Lives: search.list da YouTube Data API (100 unidades por consulta).
# A cota padrão é 10.000/dia: a cada 10 min por 5 h = 30 consultas = 3.000 unidades.
YOUTUBE_VIDEO_CHECK_SECONDS = max(60, _env_int("YOUTUBE_VIDEO_CHECK_SECONDS", 120))
YOUTUBE_LIVE_CHECK_MINUTES = max(5, _env_int("YOUTUBE_LIVE_CHECK_MINUTES", 10))
LIVE_START_HOUR = _env_int("LIVE_START_HOUR", 19, minimo=0, maximo=23)
LIVE_END_HOUR = _env_int("LIVE_END_HOUR", 24, minimo=1, maximo=24)  # exclusivo: 19:00 até 23:59

OFFERS_CHECK_MINUTES = max(10, _env_int("OFFERS_CHECK_MINUTES", 15))
MAX_OFFERS_PER_CHECK = max(1, _env_int("MAX_OFFERS_PER_CHECK", 15))
# Só avisa promoções da Steam com pelo menos esse desconto (0 = todas)
MIN_PROMO_DISCOUNT = max(0, _env_int("MIN_PROMO_DISCOUNT", 50))
# Chave da API GG.deals (fonte prioritária de comparação de preços em região brasileira).
GG_DEALS_API_KEY = os.getenv("GG_DEALS_API_KEY", "").strip()

# IsThereAnyDeal (https://isthereanydeal.com/apps/my/ — chave gratuita). Opcional:
# habilita promoções da Nuuvem e outras lojas em reais, mais giveaways.
ITAD_API_KEY = os.getenv("ITAD_API_KEY", "").strip()
# IDs de lojas da ITAD separados por vírgula. Padrão: 50 = Nuuvem.
# Steam, Epic e GOG já são consultadas diretamente, então não precisam entrar aqui.
ITAD_SHOPS = [int(x) for x in _re.findall(r"\d+", os.getenv("ITAD_SHOPS", "50"))] or [50]
# GOG (catálogo público, preços em BRL, sem chave). Desligue com OFFERS_GOG_ENABLED=false.
OFFERS_GOG_ENABLED = os.getenv("OFFERS_GOG_ENABLED", "true").strip().lower() in ("1", "true", "sim", "yes")
# Cartões limpos não mostram descrição. Ligue para exibir um resumo curto (traduzido, se houver Gemini).
OFFERS_SHOW_DESCRIPTION = os.getenv("OFFERS_SHOW_DESCRIPTION", "false").strip().lower() in ("1", "true", "sim", "yes")
# Na primeira execução, registra as ofertas que já existem sem postar (evita inundar o canal)
SEED_OFFERS_ON_FIRST_RUN = _env_bool("SEED_OFFERS_ON_FIRST_RUN", True)

SENT_DB_PATH = DATA_DIR / "sent_offers.sqlite3"

try:
    BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    BRAZIL_TZ = timezone(timedelta(hours=-3))  # Brasília não tem horário de verão atualmente

ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"
YOUTUBE_FEED_URL = (
    "https://www.youtube.com/feeds/videos.xml?channel_id="
    + quote(YOUTUBE_CHANNEL_ID)
)
