import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0")) or None
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL_ID", "0"))
SOULSLIKE_CHANNEL_ID = int(os.getenv("SOULSLIKE_CHANNEL_ID", "0"))  # canal de anúncios de runs
COLIZEU_CHANNEL_ID = int(os.getenv("COLIZEU_CHANNEL_ID", "0"))
PLATINAS_CHANNEL_ID = int(os.getenv("PLATINAS_CHANNEL_ID", "0"))
MOD_ROLE_ID = int(os.getenv("MOD_ROLE_ID", "0"))
PERFIS_CHANNEL_ID = int(os.getenv("PERFIS_CHANNEL_ID", "0"))  # canal onde nascem os santuários (threads privadas)
DB_PATH = os.getenv("DB_PATH", "/data/colizeu.db" if os.path.isdir("/data") else "data/colizeu.db")

# Recompensas por platina aprovada
XP_PLATINA = 200
DENARIOS_PLATINA = 50

# Jogos zerados (versão leve das platinas, sem comprovante obrigatório)
ZERADOS_CHANNEL_ID = int(os.getenv("ZERADOS_CHANNEL_ID", "0"))  # canal de anúncios (0 = não anuncia)
XP_ZERADO = int(os.getenv("XP_ZERADO", "50"))
DENARIOS_ZERADO = int(os.getenv("DENARIOS_ZERADO", "10"))
# Quantos zerados por 24h rendem XP/Denários (evita farm). 0 = sem limite.
ZERADOS_XP_LIMITE_DIARIO = int(os.getenv("ZERADOS_XP_LIMITE_DIARIO", "3"))

# Identidade visual (preto, dourado, prata)
COR_OURO = 0xD4AF37
COR_PRATA = 0xC0C0C0
COR_PRETO = 0x0D0D0D


# =====================================================================
# Configurações herdadas da instalação anterior (YouTube, ofertas, cargos)
# Os nomes das variáveis de ambiente são os mesmos de antes.
# =====================================================================
import asyncio  # noqa: E402,F401
from datetime import timedelta, timezone  # noqa: E402
from pathlib import Path  # noqa: E402
from urllib.parse import quote  # noqa: E402
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # noqa: E402

def _env_bool(nome: str, padrao: bool) -> bool:
    return os.getenv(nome, str(padrao)).strip().lower() in ("1", "true", "sim", "yes")


TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
YOUTUBE_CHANNEL_ID = os.getenv(
    "YOUTUBE_CHANNEL_ID", "UCBuR1KPa9g9yYilBiy_7iqw"
).strip()

# Canais do Discord
VIDEO_CHANNEL_ID = int(os.getenv("CREATOR_VIDEO_CHANNEL_ID", "1563040916074405979"))
LIVE_CHANNEL_ID = int(os.getenv("CREATOR_LIVE_CHANNEL_ID", "1563040917298872340"))
GAMES_CHANNEL_ID = int(os.getenv("GAMES_CHANNEL_ID", "1563071436724248627"))
PROMOS_CHANNEL_ID = int(os.getenv("PROMOS_CHANNEL_ID", "1563103272494039092"))

# Cargos mencionados nos avisos (criados pelo script do servidor)
ROLE_VIDEO = os.getenv("ROLE_VIDEO_NAME", "🔔 Avisos de Vídeo")
ROLE_LIVE = os.getenv("ROLE_LIVE_NAME", "🔴 Avisos de Live")

# Vídeos novos: RSS (leve, sem custo de cota).
# Lives: search.list da YouTube Data API (100 unidades por consulta).
# A cota padrão é 10.000/dia: a cada 10 min por 5 h = 30 consultas = 3.000 unidades.
YOUTUBE_VIDEO_CHECK_SECONDS = max(60, int(os.getenv("YOUTUBE_VIDEO_CHECK_SECONDS", "120")))
YOUTUBE_LIVE_CHECK_MINUTES = max(5, int(os.getenv("YOUTUBE_LIVE_CHECK_MINUTES", "10")))
LIVE_START_HOUR = int(os.getenv("LIVE_START_HOUR", "19"))
LIVE_END_HOUR = int(os.getenv("LIVE_END_HOUR", "24"))  # exclusivo: 19:00 até 23:59

OFFERS_CHECK_MINUTES = max(10, int(os.getenv("OFFERS_CHECK_MINUTES", "30")))
MAX_OFFERS_PER_CHECK = max(1, int(os.getenv("MAX_OFFERS_PER_CHECK", "8")))
# Só avisa promoções da Steam com pelo menos esse desconto (0 = todas)
MIN_PROMO_DISCOUNT = max(0, int(os.getenv("MIN_PROMO_DISCOUNT", "50")))
# Chave opcional da API do GG.deals (comparação de preços em região brasileira).
GG_DEALS_API_KEY = os.getenv("GG_DEALS_API_KEY", "").strip()
# Na primeira execução, registra as ofertas que já existem sem postar (evita inundar o canal)
SEED_OFFERS_ON_FIRST_RUN = _env_bool("SEED_OFFERS_ON_FIRST_RUN", True)

DATA_DIR = Path(os.getenv("DATA_DIR", "/data" if Path("/data").is_dir() else "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
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

