"""Arte local e determinística para as cartas do Coliseu.

As ilustrações são compostas com formas originais do Pillow. A categoria define a
composição, o tipo define a paleta secundária e a raridade altera moldura e ornamentos.
Nenhuma imagem, personagem ou marca de jogo de terceiros é incorporada.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import random
import tempfile
import threading
from pathlib import Path
from typing import Any

import PIL
from PIL import Image, ImageDraw, ImageFont, ImageOps
from config import get_data_dir

from .cartas import HABILIDADES, VERSAO_ARTES
from .arte_gwent_efeitos import desenhar_aura_unidade, desenhar_emblema_especial
from . import molduras_cartas, templates_cartas


def _dados_habilidade_visual(card: dict[str, Any]) -> tuple[str, str]:
    """Retorna o texto mecânico efetivo, priorizando habilidades exclusivas do motor."""
    try:
        # Usa exatamente o mesmo texto preparado para a partida, inclusive os ajustes de raridade.
        from .gwent import preparar_carta
        prepared = preparar_carta(card)
        return str(prepared.get("habilidade_nome") or "Habilidade"), str(prepared.get("habilidade_texto") or "Sem habilidade especial.")
    except Exception:
        ability = HABILIDADES.get(str(card.get("habilidade", "")), {})
        return str(ability.get("nome") or "Tática"), str(ability.get("texto") or "Sem habilidade especial.")


def _fingerprint_renderizador() -> str:
    """Hash automático do código/recursos visuais que realmente compõem as cartas."""
    root = Path(__file__).resolve().parents[1]
    componentes = [
        Path(__file__).resolve(),
        root / "sistemas" / "cartas.py",
        root / "sistemas" / "molduras_cartas.py",
        root / "sistemas" / "arte_gwent_efeitos.py",
        root / "sistemas" / "templates_cartas.py",
        root / "fonts" / "DejaVuSans.ttf",
        root / "fonts" / "DejaVuSans-Bold.ttf",
        root / "fonts" / "DejaVuSerif.ttf",
        root / "fonts" / "DejaVuSerif-Bold.ttf",
    ]
    digest = hashlib.sha256()
    digest.update(f"Pillow:{PIL.__version__}".encode("utf-8"))
    for componente in componentes:
        digest.update(componente.name.encode("utf-8"))
        try:
            digest.update(componente.read_bytes())
        except OSError:
            digest.update(b"missing")
    return digest.hexdigest()[:16]


# A versão explícita documenta releases; a impressão digital também invalida
# automaticamente o cache quando o código/overlay/fonte muda sem bump manual.
VERSAO_RENDERIZADOR = f"{VERSAO_ARTES}-V12-ACABAMENTO-SOULS-ELDEN-{_fingerprint_renderizador()}"

# Cor principal da moldura por raridade: as categorias e os tipos continuam
# visualmente distintos dentro de cada faixa de raridade.
CORES_RARIDADE = {
    "Comum": ((23, 29, 37), (166, 181, 194)),
    "Rara": ((9, 29, 48), (77, 180, 226)),
    "Épica": ((28, 15, 50), (183, 126, 239)),
    "Lendária": ((39, 25, 10), (239, 185, 75)),
    "Mítica": ((38, 10, 18), (205, 61, 75)),
    "Primordial": ((34, 32, 25), (239, 224, 174)),
    "Singular": ((9, 12, 24), (151, 143, 206)),
}
CORES_TIPO = {
    "Destreza": (75, 211, 177),
    "Força": (237, 117, 75),
    "Magia": (157, 132, 255),
}
CORES_CATEGORIA = {
    "Chefe": ((18, 27, 39), (100, 47, 49)),
    "Arma": ((19, 31, 40), (79, 75, 55)),
    "Magia": ((22, 22, 48), (70, 48, 105)),
    "Covenant": ((16, 39, 37), (43, 83, 76)),
    "Jogo": ((17, 31, 48), (37, 72, 91)),
    "Patente": ((45, 31, 17), (104, 76, 31)),
}
SIMBOLOS = {"Destreza": "✥", "Força": "⚔", "Magia": "✧"}
CORES_FACCAO = {
    "Ordem Áurea": ((38, 31, 17), (230, 190, 91)),
    "Lua Negra": ((24, 18, 51), (139, 112, 214)),
    "Véu Carmesim": ((47, 13, 20), (190, 54, 68)),
}
ROTULOS_FILEIRA = {"melee": "CORPO A CORPO", "ranged": "LONGA DISTÂNCIA", "siege": "CERCO"}
LARGURA_PADRAO = 420
ALTURA_PADRAO = 620

log = logging.getLogger("nara.cartas")
_CACHE_LOCK_GUARD = threading.Lock()
_CACHE_LOCKS: dict[str, threading.Lock] = {}
_CACHE_VALIDATED: dict[str, tuple[int, int]] = {}


def _cache_lock_for(path: Path) -> threading.Lock:
    """Serializa renderizações concorrentes do mesmo arquivo entre threads."""
    key = str(path)
    with _CACHE_LOCK_GUARD:
        lock = _CACHE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _CACHE_LOCKS[key] = lock
        if len(_CACHE_LOCKS) > 512:
            for old_key, old_lock in list(_CACHE_LOCKS.items()):
                if old_key != key and not old_lock.locked():
                    _CACHE_LOCKS.pop(old_key, None)
                if len(_CACHE_LOCKS) <= 384:
                    break
        return lock


def _cache_png_valido(path: Path) -> bool:
    """Verifica PNG uma vez por versão física do arquivo e invalida cache truncado."""
    try:
        stat = path.stat()
        assinatura = (int(stat.st_size), int(stat.st_mtime_ns))
        if stat.st_size < 64:
            return False
        chave = str(path)
        with _CACHE_LOCK_GUARD:
            if _CACHE_VALIDATED.get(chave) == assinatura:
                return True
        with Image.open(path) as imagem:
            if imagem.format != "PNG" or imagem.width < 1 or imagem.height < 1:
                return False
            imagem.verify()
        with _CACHE_LOCK_GUARD:
            _CACHE_VALIDATED[chave] = assinatura
            if len(_CACHE_VALIDATED) > 2048:
                for antiga in list(_CACHE_VALIDATED)[:512]:
                    _CACHE_VALIDATED.pop(antiga, None)
        return True
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return False


def webp_disponivel() -> bool:
    """Indica se o Pillow atual possui encoder/decoder WebP."""
    try:
        return Image.registered_extensions().get(".webp") == "WEBP"
    except Exception:
        return False


def _cache_webp_valido(path: Path, tamanho: tuple[int, int]) -> bool:
    """Valida miniatura WebP e aproveita a assinatura física para cachear a checagem."""
    try:
        stat = path.stat()
        assinatura = (int(stat.st_size), int(stat.st_mtime_ns))
        if stat.st_size < 64:
            return False
        chave = str(path)
        with _CACHE_LOCK_GUARD:
            if _CACHE_VALIDATED.get(chave) == assinatura:
                return True
        with Image.open(path) as imagem:
            if imagem.format != "WEBP" or imagem.size != tamanho:
                return False
            imagem.verify()
        with _CACHE_LOCK_GUARD:
            _CACHE_VALIDATED[chave] = assinatura
            if len(_CACHE_VALIDATED) > 2048:
                for antiga in list(_CACHE_VALIDATED)[:512]:
                    _CACHE_VALIDATED.pop(antiga, None)
        return True
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return False


def _salvar_webp_atomico(
    imagem: Image.Image, path: Path, *, quality: int = 82, method: int = 4,
) -> None:
    """Grava WebP temporário e publica por rename atômico."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporario: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f"{path.stem}.", suffix=".webp.tmp", dir=path.parent, delete=False
        ) as arquivo:
            temporario = Path(arquivo.name)
        imagem.save(temporario, format="WEBP", quality=max(50, min(95, int(quality))),
                    method=max(0, min(6, int(method))))
        temporario.replace(path)
        stat = path.stat()
        with _CACHE_LOCK_GUARD:
            _CACHE_VALIDATED[str(path)] = (int(stat.st_size), int(stat.st_mtime_ns))
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def _salvar_png_atomico(imagem: Image.Image, path: Path, *, optimize: bool = False) -> None:
    """Publica PNG completo por rename atômico; nunca deixa arquivo parcial no cache."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporario: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f"{path.stem}.", suffix=".png.tmp", dir=path.parent, delete=False
        ) as arquivo:
            temporario = Path(arquivo.name)
        imagem.save(temporario, format="PNG", optimize=optimize)
        temporario.replace(path)
        stat = path.stat()
        with _CACHE_LOCK_GUARD:
            _CACHE_VALIDATED[str(path)] = (int(stat.st_size), int(stat.st_mtime_ns))
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def detectar_mime_imagem(dados: bytes, *, limite_bytes: int = 20 * 1024 * 1024,
                         limite_pixels: int = 40_000_000) -> str | None:
    """Detecta formato real pelo decoder; não confia no MIME informado no upload."""
    if not dados or len(dados) > limite_bytes:
        return None
    formatos = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "GIF": "image/gif"}
    try:
        with Image.open(io.BytesIO(dados)) as imagem:
            if imagem.width < 32 or imagem.height < 32:
                return None
            if imagem.width * imagem.height > limite_pixels:
                return None
            mime = formatos.get(str(imagem.format or "").upper())
            if mime is None:
                return None
            imagem.verify()
        return mime
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return None


def validar_imagem_bytes(dados: bytes, *, limite_bytes: int = 20 * 1024 * 1024,
                         limite_pixels: int = 40_000_000) -> bool:
    """Valida arte enviada/armazenada sem confiar no MIME informado pelo cliente."""
    return detectar_mime_imagem(
        dados, limite_bytes=limite_bytes, limite_pixels=limite_pixels
    ) is not None


def _font(size: int, bold: bool = False, serif: bool = False):
    """Fonte da carta. Prefere as famílias embutidas em ``fonts/`` e cai para as do sistema."""
    root = Path(__file__).resolve().parents[1]
    nomes = []
    if serif:
        nomes += ["DejaVuSerif-Bold.ttf"] if bold else ["DejaVuSerif.ttf"]
    nomes += ["DejaVuSans-Bold.ttf"] if bold else []
    nomes += ["DejaVuSans.ttf"]
    candidates = [root / "fonts" / n for n in nomes]
    candidates += [Path("/usr/share/fonts/truetype/dejavu") / n for n in nomes]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], factor: float):
    factor = max(0.0, min(1.0, factor))
    return tuple(round(a[i] * (1 - factor) + b[i] * factor) for i in range(3))


def _text_center(draw: ImageDraw.ImageDraw, xy, text: str, font, fill):
    x, y = xy
    box = draw.textbbox((0, 0), str(text), font=font)
    draw.text((x - (box[2] - box[0]) / 2, y - (box[3] - box[1]) / 2 - box[1]),
              str(text), font=font, fill=fill)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = str(text or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            # Evita linha vazia se uma palavra isolada for maior que a área.
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _largura_rastreada(draw: ImageDraw.ImageDraw, texto: str, font, tracking: float) -> float:
    """Largura de um texto com espaçamento extra entre letras (versaletes elegantes)."""
    return sum(draw.textlength(ch, font=font) for ch in texto) + tracking * max(0, len(texto) - 1)


def _texto_rastreado(draw: ImageDraw.ImageDraw, xy, texto: str, font, fill, tracking: float, *, centro: bool = False):
    x, y = xy
    if centro:
        x -= _largura_rastreada(draw, texto, font, tracking) / 2
    for ch in texto:
        draw.text((x, y), ch, font=font, fill=fill, anchor="lm")
        x += draw.textlength(ch, font=font) + tracking


def _seed(card: dict[str, Any]) -> int:
    raw = json.dumps(card, ensure_ascii=False, sort_keys=True, default=str)
    return int.from_bytes(hashlib.sha256(raw.encode("utf-8")).digest()[:8], "big")


def _gradient(width: int, height: int, top, bottom) -> Image.Image:
    image = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        color = _mix(top, bottom, y / max(1, height - 1))
        draw.line((0, y, width, y), fill=color)
    return image


def _draw_ruins(draw: ImageDraw.ImageDraw, box, accent, rng: random.Random):
    x1, y1, x2, y2 = box
    width, height = x2 - x1, y2 - y1
    horizon = y1 + int(height * 0.72)
    draw.rectangle((x1, horizon, x2, y2), fill=(9, 13, 20, 180))
    # Silhuetas de ruínas variam de carta para carta.
    for i in range(7):
        px = x1 + int((i + 0.25) * width / 7)
        ph = rng.randint(int(height * 0.25), int(height * 0.62))
        pw = rng.randint(13, 30)
        color = _mix((9, 14, 21), accent, 0.13)
        draw.rectangle((px, horizon - ph, px + pw, horizon + 4), fill=(*color, 230))
        draw.polygon([(px - 5, horizon - ph), (px + pw // 2, horizon - ph - 10),
                      (px + pw + 5, horizon - ph)], fill=(*color, 230))
    draw.polygon([(x1, y2), (x1 + width * .18, horizon), (x1 + width * .42, y2)], fill=(13, 18, 25, 230))
    draw.polygon([(x2, y2), (x2 - width * .22, horizon), (x2 - width * .48, y2)], fill=(11, 16, 24, 230))



def _draw_unique_scene(art: Image.Image, card: dict[str, Any], rng: random.Random,
                       accent: tuple[int, int, int], metal: tuple[int, int, int],
                       top: tuple[int, int, int]) -> None:
    """Acrescenta cenário e assinatura visual determinísticos por carta.

    A diversidade vem de eixos independentes (bioma, arquitetura, clima,
    enquadramento e objeto de cena), não só de trocar a paleta.
    """
    w, h = art.size
    d = ImageDraw.Draw(art, "RGBA")
    seed = _seed(card)
    local = random.Random(seed ^ 0x4E415241)
    identity = " ".join((str(card.get("id", "")), str(card.get("nome", "")),
                         str(card.get("descricao", "")))).casefold()
    biome = seed % 12
    horizon = int(h * (0.68 + (seed % 7) * 0.012))
    ground = _mix(top, (5, 7, 12), .72)
    d.rectangle((0, horizon, w, h), fill=(*ground, 190))

    # Doze famílias de cenário com silhuetas distintas.
    if biome in (0, 1):  # floresta antiga / bosque morto
        for x in range(-10, w + 20, max(25, w // 7)):
            trunk = local.randint(max(5, w // 35), max(9, w // 18))
            base = local.randint(int(h*.52), int(h*.78))
            d.polygon([(x, base), (x+trunk, base), (x+trunk//2, int(h*.18))],
                      fill=(8, 15, 16, 210), outline=(*accent, 65))
            for j in range(3):
                yy = int(h*.22) + j*int(h*.11) + local.randint(-8, 8)
                d.ellipse((x-w*.12, yy-w*.08, x+w*.12, yy+w*.08), fill=(8, 24, 22, 125))
    elif biome in (2, 3):  # muralha / catedral
        for x in (int(w*.08), int(w*.78)):
            tower_h = local.randint(int(h*.28), int(h*.48))
            d.rectangle((x, horizon-tower_h, x+int(w*.14), horizon), fill=(8, 12, 19, 225), outline=(*metal, 90), width=2)
            d.polygon([(x-5, horizon-tower_h), (x+int(w*.07), horizon-tower_h-int(h*.08),),
                       (x+int(w*.14)+5, horizon-tower_h)], fill=(9, 13, 20, 230))
            for wy in range(horizon-tower_h+18, horizon-12, 28):
                d.arc((x+int(w*.045), wy, x+int(w*.10), wy+34), 180, 360, fill=(*accent, 100), width=2)
    elif biome in (4, 5):  # costa / ruínas inundadas
        for yy in range(horizon, h, max(9, h//24)):
            d.line((0, yy, w, yy+local.randint(-5, 5)), fill=(*accent, local.randint(18, 48)), width=1)
        for x in range(int(w*.12), w, int(w*.24)):
            d.line((x, horizon, x+local.randint(-12, 12), horizon-local.randint(20, 65)), fill=(9, 15, 20, 210), width=5)
    elif biome in (6, 7):  # vulcão / forja
        for _ in range(9):
            x = local.randint(0, w); y = local.randint(int(h*.25), horizon)
            r = local.randint(3, max(5, w//22))
            d.ellipse((x-r, y-r, x+r, y+r), fill=(255, 105, 38, local.randint(18, 65)))
        d.polygon([(0,horizon),(int(w*.2),horizon-int(h*.25)),(int(w*.36),horizon),
                   (int(w*.62),horizon-int(h*.18)),(w,horizon)], fill=(18, 12, 14, 225))
    elif biome in (8, 9):  # necrópole / pântano
        for x in range(int(w*.08), w, int(w*.19)):
            yy = local.randint(int(h*.43), horizon)
            d.line((x, yy, x, horizon), fill=(7, 12, 17, 220), width=max(2, w//65))
            d.line((x-int(w*.035), yy+int(h*.06), x+int(w*.035), yy+int(h*.06)), fill=(*metal, 115), width=3)
        for _ in range(7):
            x=local.randint(0,w); y=local.randint(int(h*.55),h)
            d.ellipse((x-10,y-5,x+10,y+5), fill=(*accent, 35))
    else:  # geleira / planície de guerra
        for _ in range(8):
            x=local.randint(-20,w); y=local.randint(int(h*.45),horizon)
            d.polygon([(x,y+25),(x+local.randint(12,35),y-local.randint(10,40)),(x+55,y+25)],
                      fill=(9, 15, 23, 190), outline=(*metal, 55))

    # Clima independente: névoa, chuva, cinzas, neve ou faíscas.
    weather = (seed >> 9) % 5
    for _ in range(34):
        x=local.randint(2,w-3); y=local.randint(2,h-3)
        if weather == 0:
            d.ellipse((x-2,y-2,x+2,y+2), fill=(205,220,226,local.randint(12,45)))
        elif weather == 1:
            d.line((x,y,x-4,y+local.randint(8,18)), fill=(*metal,local.randint(25,85)), width=1)
        elif weather == 2:
            d.ellipse((x-2,y-2,x+2,y+2), fill=(255,116,54,local.randint(30,110)))
        elif weather == 3:
            d.line((x,y,x+local.randint(-4,4),y+local.randint(4,12)), fill=(220,235,245,local.randint(25,90)), width=2)
        else:
            d.arc((x-8,y-5,x+8,y+5), 10, 170, fill=(*accent,local.randint(20,65)), width=1)

    # Um objeto narrativo em posição assimétrica, com forma escolhida por carta.
    prop = (seed >> 17) % 10
    px = int(w * (.18 + ((seed >> 24) % 60) / 100))
    py = int(h * (.70 + ((seed >> 31) % 12) / 100))
    scale = max(10, w//14)
    ink = (*metal, 205)
    if prop == 0:  # monólito
        d.polygon([(px-scale,py),(px-scale//2,py-scale*3),(px+scale//2,py-scale*3),(px+scale,py)], fill=(12,17,23,230), outline=ink)
        d.line((px,py-scale*2,px,py-scale), fill=(*accent,210), width=3)
    elif prop == 1:  # árvore caída
        d.line((px-scale*2,py-scale,px+scale*2,py), fill=(18,16,14,240), width=max(5,scale//2))
        for side in (-1,1): d.line((px+side*scale,py-scale//2,px+side*scale*2,py-scale*2), fill=ink, width=3)
    elif prop == 2:  # altar
        d.rectangle((px-scale,py-scale,px+scale,py), fill=(15,19,25,235), outline=ink, width=2)
        d.ellipse((px-scale//2,py-scale*2,px+scale//2,py-scale), outline=(*accent,220), width=3)
    elif prop == 3:  # estandarte
        d.line((px,py-scale*3,px,py), fill=ink, width=4)
        d.polygon([(px,py-scale*3),(px+scale*2,py-scale*2),(px+scale,py-scale),(px,py-scale)], fill=(*accent,135), outline=ink)
    elif prop == 4:  # crânio/relíquia
        d.ellipse((px-scale,py-scale*2,px+scale,py), fill=(28,27,25,230), outline=ink, width=2)
        d.ellipse((px-scale//2,py-scale,px-scale//5,py-scale//2), fill=(*accent,190))
        d.ellipse((px+scale//5,py-scale,px+scale//2,py-scale//2), fill=(*accent,190))
    elif prop == 5:  # portal pequeno
        d.ellipse((px-scale,py-scale*3,px+scale,py), outline=(*accent,180), width=4)
        d.ellipse((px-scale//2,py-scale*2,px+scale//2,py-scale), outline=ink, width=2)
    elif prop == 6:  # coluna partida
        d.rectangle((px-scale//2,py-scale*3,px+scale//2,py), fill=(18,21,27,225), outline=ink)
        d.polygon([(px-scale,py-scale*3),(px,py-scale*4),(px+scale,py-scale*3)], fill=(20,24,29,230), outline=ink)
    elif prop == 7:  # rocha/cristal
        d.polygon([(px,py-scale*3),(px+scale,py-scale),(px+scale//2,py),(px-scale,py-scale)], fill=(*accent,85), outline=ink)
    elif prop == 8:  # roda/engrenagem
        d.ellipse((px-scale,py-scale*2,px+scale,py), outline=ink, width=4)
        d.ellipse((px-scale//3,py-scale*4//3,px+scale//3,py-scale*2//3), outline=(*accent,190), width=3)
    else:  # fogueira
        d.polygon([(px,py-scale*3),(px+scale,py-scale),(px,py-scale*2),(px-scale,py-scale)], fill=(255,120,45,110), outline=(*accent,220))
        d.line((px-scale,py,px+scale,py-scale//2), fill=ink, width=4)


def _draw_boss(draw: ImageDraw.ImageDraw, box, accent, rng: random.Random, card: dict[str, Any]):
    x1, y1, x2, y2 = box
    cx = (x1 + x2) // 2
    cy = y1 + int((y2 - y1) * .53)
    h = y2 - y1
    _draw_ruins(draw, box, accent, rng)
    boss_name = f"{card.get('id', '')} {card.get('nome', '')}".casefold()
    if "cervo" in boss_name or "cacador" in boss_name or "caçador" in boss_name:
        variant = 1
    elif "dama" in boss_name or "aparicao" in boss_name or "aparição" in boss_name:
        variant = 2
    elif "oraculo" in boss_name or "oráculo" in boss_name or "rei_afogado" in boss_name:
        variant = 3
    else:
        variant = rng.randrange(4)
    draw.ellipse((cx - 112, y1 + 5, cx + 112, y1 + 220), outline=(*accent, 80), width=3)
    draw.ellipse((cx - 88, y1 + 27, cx + 88, y1 + 194), outline=(*accent, 42), width=2)

    if variant == 0:  # cavaleiro/carrasco com armadura e elmo.
        cape = [(cx - 35, cy - 22), (cx - 108, cy + 50), (cx - 94, y2 - 8),
                (cx, y2 - 48), (cx + 96, y2 - 8), (cx + 108, cy + 50), (cx + 35, cy - 22)]
        draw.polygon(cape, fill=(10, 15, 23, 250), outline=(*accent, 210))
        draw.polygon([(cx - 30, cy - 28), (cx - 105, cy - 10), (cx - 78, cy + 48),
                      (cx - 22, cy + 39), (cx, cy + 8), (cx + 22, cy + 39),
                      (cx + 78, cy + 48), (cx + 105, cy - 10), (cx + 30, cy - 28)],
                     fill=(24, 30, 40, 255), outline=(*accent, 240))
        draw.polygon([(cx - 36, cy - 13), (cx + 36, cy - 13), (cx + 28, cy + 100),
                      (cx, cy + 126), (cx - 28, cy + 100)], fill=(18, 24, 34, 255), outline=(*accent, 160))
        draw.polygon([(cx - 49, cy - 61), (cx - 82, cy - 120), (cx - 34, cy - 95),
                      (cx, cy - 139), (cx + 31, cy - 95), (cx + 82, cy - 120),
                      (cx + 49, cy - 61)], fill=(29, 35, 46, 255), outline=(*accent, 250))
        draw.polygon([(cx - 43, cy - 58), (cx, cy - 88), (cx + 43, cy - 58),
                      (cx + 35, cy + 4), (cx, cy + 34), (cx - 35, cy + 4)],
                     fill=(42, 47, 58, 255), outline=(210, 207, 197, 170))
        draw.line((cx - 25, cy - 22, cx - 7, cy - 26), fill=(*accent, 255), width=5)
        draw.line((cx + 7, cy - 26, cx + 25, cy - 22), fill=(*accent, 255), width=5)
    elif variant == 1:  # fera/alfa, com focinho, presas e chifres.
        body = [(cx - 116, cy + 21), (cx - 76, cy - 37), (cx - 9, cy - 53),
                (cx + 78, cy - 28), (cx + 116, cy + 36), (cx + 75, cy + 93),
                (cx - 70, cy + 93)]
        draw.polygon(body, fill=(18, 24, 32, 255), outline=(*accent, 230), width=4)
        draw.polygon([(cx - 65, cy - 33), (cx - 42, cy - 104), (cx - 14, cy - 53),
                      (cx + 35, cy - 104), (cx + 67, cy - 27), (cx + 32, cy + 21),
                      (cx - 26, cy + 20)], fill=(31, 38, 48, 255), outline=(*accent, 255))
        draw.polygon([(cx - 52, cy - 60), (cx - 105, cy - 130), (cx - 74, cy - 28)],
                     fill=(31, 37, 46, 255), outline=(*accent, 240))
        draw.polygon([(cx + 48, cy - 60), (cx + 108, cy - 131), (cx + 72, cy - 24)],
                     fill=(31, 37, 46, 255), outline=(*accent, 240))
        draw.polygon([(cx - 25, cy - 6), (cx + 25, cy - 6), (cx, cy + 48)],
                     fill=(7, 10, 16, 255), outline=(224, 218, 205, 155))
        draw.ellipse((cx - 43, cy - 38, cx - 23, cy - 18), fill=(*accent, 255))
        draw.ellipse((cx + 23, cy - 38, cx + 43, cy - 18), fill=(*accent, 255))
        for side in (-1, 1):
            draw.line((cx + side * 58, cy + 45, cx + side * 93, y2 - 12), fill=(26, 29, 36, 255), width=17)
    elif variant == 2:  # espectro encapuzado, com manto alongado.
        draw.polygon([(cx, y1 + 25), (cx + 75, y1 + 84), (cx + 64, cy + 54),
                      (cx + 98, y2 - 5), (cx, y2 - 51), (cx - 98, y2 - 5),
                      (cx - 64, cy + 54), (cx - 75, y1 + 84)],
                     fill=(13, 20, 31, 245), outline=(*accent, 225), width=4)
        draw.ellipse((cx - 48, y1 + 55, cx + 48, y1 + 153), fill=(7, 12, 21, 255), outline=(*accent, 235), width=4)
        draw.polygon([(cx - 55, y1 + 82), (cx - 33, y1 + 24), (cx, y1 + 7),
                      (cx + 33, y1 + 24), (cx + 55, y1 + 82)], fill=(27, 33, 47, 255), outline=(*accent, 255))
        draw.ellipse((cx - 25, y1 + 100, cx - 8, y1 + 114), fill=(*accent, 255))
        draw.ellipse((cx + 8, y1 + 100, cx + 25, y1 + 114), fill=(*accent, 255))
        for side in (-1, 1):
            draw.arc((cx + side * 55 - 25, y1 + 35, cx + side * 55 + 25, y1 + 95),
                     190 if side < 0 else 0, 340 if side < 0 else 150, fill=(*accent, 180), width=4)
    else:  # colosso esquelético, com costelas expostas.
        draw.ellipse((cx - 57, y1 + 33, cx + 57, y1 + 150), fill=(37, 40, 45, 255), outline=(*accent, 245), width=4)
        draw.polygon([(cx - 44, y1 + 90), (cx - 22, y1 + 65), (cx, y1 + 83),
                      (cx + 22, y1 + 65), (cx + 44, y1 + 90), (cx + 32, y1 + 156),
                      (cx, y1 + 178), (cx - 32, y1 + 156)], fill=(27, 31, 39, 255), outline=(*accent, 210))
        draw.line((cx - 30, y1 + 111, cx + 30, y1 + 111), fill=(218, 205, 179, 220), width=5)
        draw.line((cx - 26, y1 + 132, cx + 26, y1 + 132), fill=(218, 205, 179, 200), width=5)
        draw.line((cx - 18, y1 + 151, cx + 18, y1 + 151), fill=(218, 205, 179, 180), width=5)
        draw.polygon([(cx - 37, y1 + 72), (cx - 78, y1 + 9), (cx - 66, y1 + 94)],
                     fill=(47, 49, 54, 255), outline=(*accent, 225))
        draw.polygon([(cx + 37, y1 + 72), (cx + 78, y1 + 9), (cx + 66, y1 + 94)],
                     fill=(47, 49, 54, 255), outline=(*accent, 225))
        draw.polygon([(cx - 14, y1 + 119), (cx + 14, y1 + 119), (cx, y1 + 146)], fill=(7, 9, 14, 255))
        draw.line((cx - 70, cy + 5, cx - 117, y2 - 22), fill=(45, 43, 42, 255), width=16)
        draw.line((cx + 70, cy + 5, cx + 117, y2 - 22), fill=(45, 43, 42, 255), width=16)


def _draw_weapon(draw: ImageDraw.ImageDraw, box, accent, rng: random.Random, card: dict[str, Any]):
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    # Raios de fundo e runas discretas.
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    for i in range(12):
        angle = math.radians(i * 30 + rng.randint(-6, 6))
        ex = cx + math.cos(angle) * w * .56
        ey = cy + math.sin(angle) * h * .62
        draw.line((cx, cy, ex, ey), fill=(*accent, rng.randint(22, 58)), width=rng.randint(1, 3))
    weapon_name = f"{card.get('id', '')} {card.get('nome', '')}".casefold()
    if "martelo" in weapon_name:
        variant = 2
    elif any(token in weapon_name for token in ("cajado", "agulha")):
        variant = 3
    elif "arco" in weapon_name:
        variant = 4
    elif "sino" in weapon_name:
        variant = 5
    elif "duas_luas" in weapon_name or "duas luas" in weapon_name:
        variant = 6
    elif "lanca" in weapon_name or "lança" in weapon_name:
        variant = 1
    else:
        variant = rng.randrange(2)
    angle_shift = rng.randint(-22, 22)
    if variant in (0, 1):  # lâmina longa / lança
        a = (cx - 35 + angle_shift, y2 - 26)
        b = (cx + 48 + angle_shift, y1 + 24)
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy / length, dx / length
        width = 18 if variant == 0 else 12
        blade = [(a[0] + nx * width, a[1] + ny * width),
                 (b[0] + nx * 5, b[1] + ny * 5),
                 (b[0] + dx * .13, b[1] + dy * .13),
                 (b[0] - nx * 5, b[1] - ny * 5),
                 (a[0] - nx * width, a[1] - ny * width)]
        draw.polygon(blade, fill=(171, 196, 202, 255), outline=(*accent, 255))
        draw.line((a[0], a[1], b[0], b[1]), fill=(255, 255, 234, 230), width=3)
        draw.line((a[0] - nx * 34, a[1] - ny * 34, a[0] + nx * 34, a[1] + ny * 34), fill=(190, 150, 99, 255), width=9)
        draw.line((a[0] - dx * .07, a[1] - dy * .07, a[0] + dx * .11, a[1] + dy * .11), fill=(112, 70, 43, 255), width=9)
        draw.ellipse((a[0] - 12, a[1] - 12, a[0] + 12, a[1] + 12), fill=(*accent, 255), outline=(240, 222, 178, 255), width=3)
    elif variant == 2:  # martelo
        draw.line((cx - 55, y2 - 23, cx + 40, y1 + 55), fill=(103, 72, 52, 255), width=20)
        draw.line((cx - 55, y2 - 23, cx + 40, y1 + 55), fill=(190, 145, 93, 255), width=5)
        draw.polygon([(cx + 4, y1 + 39), (cx + 35, y1 + 6), (cx + 105, y1 + 48),
                      (cx + 92, y1 + 103), (cx + 24, y1 + 91)],
                     fill=(68, 80, 92, 255), outline=(*accent, 255))
        draw.line((cx + 21, y1 + 46, cx + 90, y1 + 83), fill=(220, 224, 205, 210), width=4)
    elif variant == 3:  # cajado ou agulha astral
        draw.line((cx - 54, y2 - 19, cx + 45, y1 + 23), fill=(109, 77, 55, 255), width=14)
        draw.line((cx - 54, y2 - 19, cx + 45, y1 + 23), fill=(210, 159, 99, 255), width=3)
        orb = (cx + 47, y1 + 28)
        draw.ellipse((orb[0] - 39, orb[1] - 39, orb[0] + 39, orb[1] + 39), fill=(*accent, 55), outline=(*accent, 255), width=4)
        draw.ellipse((orb[0] - 20, orb[1] - 20, orb[0] + 20, orb[1] + 20), fill=(226, 232, 237, 245), outline=(255, 255, 255, 255), width=3)
    elif variant == 4:  # arco recurvo e flecha
        draw.arc((cx - 110, y1 + 25, cx + 100, y2 - 7), 255, 105, fill=(181, 125, 75, 255), width=16)
        draw.line((cx + 48, y1 + 28, cx + 48, y2 - 22), fill=(231, 223, 200, 230), width=2)
        draw.line((cx - 90, cy, cx + 91, cy - 62), fill=(188, 207, 214, 255), width=7)
        draw.polygon([(cx + 91, cy - 62), (cx + 64, cy - 72), (cx + 76, cy - 46)], fill=(226, 233, 226, 255))
    elif variant == 5:  # sino de guerra, corrente e badalo
        draw.line((cx - 50, y1 + 36, cx + 50, y1 + 36), fill=(196, 158, 90, 255), width=10)
        draw.polygon([(cx - 42, y1 + 48), (cx + 42, y1 + 48), (cx + 61, y1 + 181),
                      (cx + 36, y1 + 210), (cx - 36, y1 + 210), (cx - 61, y1 + 181)],
                     fill=(80, 91, 94, 255), outline=(*accent, 255), width=4)
        draw.arc((cx - 53, y1 + 87, cx + 53, y1 + 177), 5, 175, fill=(235, 213, 158, 230), width=5)
        draw.line((cx, y1 + 210, cx, y1 + 251), fill=(177, 133, 78, 255), width=7)
        draw.ellipse((cx - 12, y1 + 239, cx + 12, y1 + 263), fill=(208, 171, 105, 255), outline=(*accent, 220), width=2)
    else:  # duas lâminas cruzadas
        draw.line((cx - 92, y2 - 30, cx + 70, y1 + 43), fill=(183, 207, 215, 255), width=15)
        draw.line((cx + 92, y2 - 30, cx - 70, y1 + 43), fill=(142, 174, 190, 255), width=15)
        draw.line((cx - 12, y1 + 126, cx + 12, y1 + 166), fill=(206, 167, 104, 255), width=8)
        draw.line((cx + 12, y1 + 126, cx - 12, y1 + 166), fill=(206, 167, 104, 255), width=8)


def _draw_magic(draw: ImageDraw.ImageDraw, box, accent, rng: random.Random, card: dict[str, Any]):
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    magic_name = f"{card.get('id', '')} {card.get('nome', '')}".casefold()
    if any(token in magic_name for token in ("brasa", "fagulha", "chama")):
        variant = 4  # chama viva
    elif "trovao" in magic_name or "trovão" in magic_name:
        variant = 5  # raio
    elif "nevoa" in magic_name or "névoa" in magic_name:
        variant = 6  # espiral de névoa
    elif "sol_negro" in magic_name or "sol negro" in magic_name:
        variant = 7  # eclipse
    else:
        variant = rng.randrange(4)
    for radius, alpha, width in ((112, 65, 2), (88, 100, 3), (60, 135, 2)):
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(*accent, alpha), width=width)
    for i in range(8):
        angle = math.radians(i * 45 + rng.randint(-8, 8))
        rx, ry = math.cos(angle), math.sin(angle)
        r1, r2 = 72, 122
        p1 = (cx + rx * r1, cy + ry * r1)
        p2 = (cx + rx * r2, cy + ry * r2)
        draw.line((p1, p2), fill=(*accent, 135), width=2)
        size = rng.randint(5, 9)
        draw.polygon([(p2[0], p2[1] - size), (p2[0] + size, p2[1]),
                      (p2[0], p2[1] + size), (p2[0] - size, p2[1])], fill=(*accent, 220))
    if variant == 4:
        flame = [(cx, cy - 91), (cx + 29, cy - 39), (cx + 19, cy - 12),
                 (cx + 57, cy - 21), (cx + 42, cy + 43), (cx, cy + 83),
                 (cx - 48, cy + 40), (cx - 36, cy - 10), (cx - 13, cy + 17)]
        draw.polygon(flame, fill=(*accent, 135), outline=(255, 236, 206, 245), width=4)
        draw.polygon([(cx, cy - 40), (cx + 21, cy + 5), (cx, cy + 53), (cx - 18, cy + 8)],
                     fill=(255, 228, 164, 230))
    elif variant == 5:
        lightning = [(cx + 13, cy - 94), (cx - 39, cy - 8), (cx - 3, cy - 8),
                     (cx - 22, cy + 92), (cx + 52, cy - 20), (cx + 13, cy - 20)]
        draw.polygon(lightning, fill=(*accent, 175), outline=(245, 241, 255, 255), width=3)
    elif variant == 6:
        for i in range(5):
            inset = i * 13
            draw.arc((cx - 83 + inset, cy - 63 + inset, cx + 83 - inset, cy + 63 - inset),
                     35 + i * 18, 305 + i * 18, fill=(*accent, 220 - i * 22), width=8 - i)
        draw.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=(238, 239, 255, 235))
    elif variant == 7:
        draw.ellipse((cx - 75, cy - 75, cx + 75, cy + 75), fill=(11, 9, 24, 255), outline=(*accent, 255), width=6)
        draw.ellipse((cx - 54, cy - 54, cx + 54, cy + 54), fill=(*accent, 115), outline=(255, 225, 178, 230), width=3)
        draw.ellipse((cx - 31, cy - 67, cx + 66, cy + 31), fill=(11, 9, 24, 255))
    elif variant == 0:
        draw.ellipse((cx - 44, cy - 44, cx + 44, cy + 44), fill=(*accent, 70), outline=(241, 231, 255, 240), width=3)
        draw.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), fill=(231, 235, 255, 245), outline=(*accent, 255), width=4)
    elif variant == 1:
        draw.polygon([(cx, cy - 74), (cx + 62, cy), (cx, cy + 74), (cx - 62, cy)],
                     fill=(*accent, 60), outline=(241, 231, 255, 245), width=4)
        draw.polygon([(cx, cy - 36), (cx + 31, cy), (cx, cy + 36), (cx - 31, cy)],
                     fill=(229, 224, 255, 235), outline=(*accent, 255), width=3)
    elif variant == 2:
        draw.arc((cx - 68, cy - 68, cx + 68, cy + 68), 25, 300, fill=(248, 232, 255, 245), width=8)
        draw.arc((cx - 48, cy - 48, cx + 88, cy + 88), 190, 470, fill=(*accent, 250), width=5)
        draw.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=(250, 244, 255, 250))
    else:
        points = []
        for i in range(12):
            angle = math.radians(i * 30 - 90)
            radius = 76 if i % 2 == 0 else 35
            points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        draw.polygon(points, fill=(*accent, 75), outline=(239, 228, 255, 250))
        draw.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=(250, 245, 255, 255))


def _draw_covenant(draw: ImageDraw.ImageDraw, box, accent, rng: random.Random, card: dict[str, Any]):
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    # Bandeirolas e escudo principal.
    draw.polygon([(x1 + 28, y1 + 35), (x1 + 105, y1 + 54), (x1 + 91, y2 - 12),
                  (x1 + 46, y2 - 40)], fill=(16, 31, 31, 220), outline=(*accent, 170))
    draw.polygon([(x2 - 28, y1 + 35), (x2 - 105, y1 + 54), (x2 - 91, y2 - 12),
                  (x2 - 46, y2 - 40)], fill=(16, 31, 31, 220), outline=(*accent, 170))
    shield = [(cx, y1 + 20), (cx + 105, y1 + 62), (cx + 85, cy + 60),
              (cx, y2 - 8), (cx - 85, cy + 60), (cx - 105, y1 + 62)]
    draw.polygon(shield, fill=(23, 42, 41, 255), outline=(*accent, 255), width=5)
    inner = [(cx, y1 + 43), (cx + 78, y1 + 75), (cx + 64, cy + 47),
             (cx, y2 - 34), (cx - 64, cy + 47), (cx - 78, y1 + 75)]
    draw.polygon(inner, fill=(9, 20, 24, 255), outline=(218, 204, 165, 190), width=2)
    covenant_name = f"{card.get('id', '')} {card.get('nome', '')}".casefold()
    if "lua" in covenant_name:
        variant = 0
    elif "lobo" in covenant_name or "lobos" in covenant_name or "cervo" in covenant_name:
        variant = 1
    elif "brasa" in covenant_name or "filhos" in covenant_name:
        variant = 2
    elif "coroa" in covenant_name:
        variant = 3
    else:
        variant = rng.randrange(4)
    if variant == 0:  # lua
        draw.arc((cx - 48, cy - 61, cx + 52, cy + 39), 60, 300, fill=(*accent, 255), width=14)
        draw.ellipse((cx + 4, cy - 43, cx + 29, cy - 18), fill=(244, 230, 190, 255))
    elif variant == 1:  # lobo abstrato
        draw.polygon([(cx - 48, cy + 17), (cx - 36, cy - 50), (cx - 5, cy - 24),
                      (cx + 11, cy - 56), (cx + 48, cy + 17), (cx, cy + 47)],
                     fill=(*accent, 190), outline=(245, 235, 215, 240))
        draw.ellipse((cx - 18, cy - 7, cx - 8, cy + 3), fill=(9, 15, 18, 255))
        draw.ellipse((cx + 8, cy - 7, cx + 18, cy + 3), fill=(9, 15, 18, 255))
    elif variant == 2:  # chama
        draw.polygon([(cx, cy - 64), (cx + 27, cy - 15), (cx + 14, cy + 5),
                      (cx + 37, cy - 1), (cx + 26, cy + 39), (cx, cy + 55),
                      (cx - 29, cy + 30), (cx - 22, cy - 9), (cx - 9, cy + 8)],
                     fill=(*accent, 225), outline=(247, 225, 188, 235))
    else:  # estrela
        points = []
        for i in range(10):
            angle = math.radians(-90 + i * 36)
            radius = 58 if i % 2 == 0 else 25
            points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        draw.polygon(points, fill=(*accent, 220), outline=(247, 232, 197, 240))


def _draw_game(draw: ImageDraw.ImageDraw, box, accent, rng: random.Random):
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    cx = (x1 + x2) // 2
    horizon = y1 + int(h * .72)
    variant = rng.randrange(4)
    # Cada título recebe uma cena abstrata diferente: portal, fortaleza, árvore ou mar.
    if variant == 0:
        moon_x = x1 + int(w * (.28 + rng.random() * .44))
        moon_y = y1 + rng.randint(55, 105)
        moon_r = rng.randint(28, 47)
        draw.ellipse((moon_x - moon_r, moon_y - moon_r, moon_x + moon_r, moon_y + moon_r),
                     fill=(*accent, 45), outline=(*accent, 220), width=3)
        draw.ellipse((moon_x - moon_r // 2, moon_y - moon_r // 2, moon_x + moon_r // 2, moon_y + moon_r // 2),
                     fill=(234, 232, 220, 225))
        portal = (cx - 84, y1 + 37, cx + 84, horizon + 28)
        draw.ellipse(portal, outline=(*accent, 130), width=12)
        draw.ellipse((portal[0] + 11, portal[1] + 11, portal[2] - 11, portal[3] - 11),
                     outline=(236, 226, 200, 175), width=3)
        draw.polygon([(x1, y2), (x1 + 72, horizon - 24), (cx - 26, y2),
                      (cx + 38, horizon - 52), (x2, y2)], fill=(10, 17, 26, 240))
        for i in range(5):
            px = x1 + 25 + i * int(w / 5)
            ph = rng.randint(30, 83)
            draw.polygon([(px - 10, horizon), (px, horizon - ph), (px + 10, horizon)],
                         fill=(13, 23, 33, 255), outline=(*accent, 65))
    elif variant == 1:
        # Fortaleza vertical recortada pelo céu.
        draw.ellipse((cx - 72, y1 + 24, cx + 72, y1 + 168), outline=(*accent, 150), width=5)
        draw.polygon([(cx - 91, y2), (cx - 69, y1 + 113), (cx - 47, y1 + 136),
                      (cx - 31, y1 + 60), (cx, y1 + 92), (cx + 31, y1 + 60),
                      (cx + 47, y1 + 136), (cx + 69, y1 + 113), (cx + 91, y2)],
                     fill=(13, 20, 31, 255), outline=(*accent, 190), width=3)
        for side in (-1, 1):
            sx = cx + side * 117
            draw.rectangle((sx - 18, y1 + 95, sx + 18, y2 - 9), fill=(9, 16, 26, 255), outline=(*accent, 110), width=2)
            draw.polygon([(sx - 25, y1 + 96), (sx, y1 + 52), (sx + 25, y1 + 96)],
                         fill=(20, 27, 39, 255), outline=(*accent, 150))
        draw.line((x1 + 20, y2 - 34, x2 - 20, y2 - 34), fill=(*accent, 145), width=3)
    elif variant == 2:
        # Árvore ancestral e raízes luminosas.
        trunk = [(cx - 17, y1 + 105), (cx - 35, y2 - 12), (cx + 34, y2 - 12), (cx + 15, y1 + 105)]
        draw.polygon(trunk, fill=(34, 27, 24, 255), outline=(*accent, 190), width=3)
        for branch in range(6):
            angle = math.radians(205 + branch * 26)
            ex = cx + math.cos(angle) * rng.randint(74, 142)
            ey = y1 + rng.randint(30, 132)
            draw.line((cx, y1 + 165, ex, ey), fill=(69, 54, 43, 255), width=rng.randint(7, 13))
            draw.ellipse((ex - 10, ey - 10, ex + 10, ey + 10), fill=(*accent, 115), outline=(*accent, 240), width=2)
        for root in (-1, 1):
            draw.line((cx, y2 - 16, cx + root * 86, y2 - 4), fill=(91, 65, 45, 255), width=7)
    else:
        # Mar escuro, pilares e lua refletida.
        moon_x, moon_y = cx + rng.randint(-80, 80), y1 + 72
        draw.ellipse((moon_x - 38, moon_y - 38, moon_x + 38, moon_y + 38),
                     fill=(230, 226, 206, 220), outline=(*accent, 220), width=3)
        draw.polygon([(x1, horizon), (x1 + 70, horizon - 42), (x1 + 125, horizon + 8),
                      (cx, horizon - 20), (x2 - 90, horizon + 6), (x2, horizon - 35),
                      (x2, y2), (x1, y2)], fill=(8, 17, 28, 255), outline=(*accent, 90))
        for i in range(5):
            y = horizon + 17 + i * 18
            draw.arc((cx - 110 + i * 12, y - 8, cx + 110 - i * 12, y + 22), 0, 180,
                     fill=(*accent, 95 - i * 10), width=3)
        for px in (x1 + 57, x2 - 57):
            draw.rectangle((px - 12, y1 + 90, px + 12, horizon + 20), fill=(19, 25, 34, 255), outline=(*accent, 120), width=2)
            draw.polygon([(px - 23, y1 + 90), (px, y1 + 55), (px + 23, y1 + 90)], fill=(25, 32, 42, 255))
    # Filetes e pontos de luz, com composição ligada ao identificador da carta.
    for i in range(14):
        px = rng.randint(x1 + 13, x2 - 13)
        py = rng.randint(y1 + 14, y2 - 22)
        r = rng.randint(1, 3)
        draw.ellipse((px - r, py - r, px + r, py + r), fill=(*accent, rng.randint(90, 210)))


def _draw_patente(draw: ImageDraw.ImageDraw, box, accent, rng: random.Random):
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    for i in range(12):
        angle = math.radians(i * 30)
        draw.line((cx, cy, cx + math.cos(angle) * 145, cy + math.sin(angle) * 128),
                  fill=(*accent, 55), width=2)
    # Medalhão e fitas.
    draw.polygon([(cx - 55, cy + 58), (cx - 42, y2 - 7), (cx, y2 - 42),
                  (cx + 42, y2 - 7), (cx + 55, cy + 58)],
                 fill=(85, 35, 34, 235), outline=(*accent, 235))
    draw.ellipse((cx - 105, cy - 105, cx + 105, cy + 105), fill=(32, 28, 24, 255), outline=(*accent, 255), width=8)
    draw.ellipse((cx - 83, cy - 83, cx + 83, cy + 83), fill=(54, 42, 29, 255), outline=(244, 224, 171, 180), width=3)
    variant = rng.randrange(3)
    if variant == 0:
        draw.polygon([(cx - 57, cy - 9), (cx - 48, cy - 58), (cx - 15, cy - 30),
                      (cx, cy - 75), (cx + 15, cy - 30), (cx + 48, cy - 58),
                      (cx + 57, cy - 9), (cx + 36, cy + 40), (cx - 36, cy + 40)],
                     fill=(*accent, 230), outline=(255, 240, 190, 255))
    elif variant == 1:
        draw.polygon([(cx, cy - 65), (cx + 59, cy), (cx, cy + 65), (cx - 59, cy)],
                     fill=(*accent, 205), outline=(255, 240, 190, 255))
        draw.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=(30, 26, 21, 255))
    else:
        draw.text((cx - 47, cy - 57), "S", font=_font(108, True), fill=(*accent, 255), stroke_width=2,
                  stroke_fill=(255, 239, 188, 210))


def _draw_type_icon(draw: ImageDraw.ImageDraw, center: tuple[int, int], card_type: str, accent):
    """Ícone vetorial próprio; não depende de glifos emoji instalados no servidor."""
    cx, cy = center
    pale = (245, 239, 219, 245)
    if card_type == "Destreza":
        draw.arc((cx - 9, cy - 9, cx + 9, cy + 9), 35, 325, fill=(*accent, 255), width=3)
        draw.arc((cx - 5, cy - 5, cx + 13, cy + 13), 205, 495, fill=pale, width=2)
        draw.polygon([(cx + 10, cy - 9), (cx + 15, cy - 10), (cx + 12, cy - 4)], fill=(*accent, 255))
    elif card_type == "Força":
        draw.line((cx - 9, cy + 10, cx + 9, cy - 10), fill=pale, width=3)
        draw.line((cx - 9, cy - 10, cx + 9, cy + 10), fill=(*accent, 255), width=3)
        draw.line((cx - 12, cy + 5, cx - 5, cy + 12), fill=(*accent, 255), width=3)
        draw.line((cx + 5, cy + 12, cx + 12, cy + 5), fill=pale, width=3)
    else:
        points = []
        for i in range(8):
            angle = math.radians(-90 + i * 45)
            radius = 12 if i % 2 == 0 else 5
            points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        draw.polygon(points, fill=(*accent, 200), outline=pale)
        draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(255, 255, 255, 255))


def _draw_rarity_frame(draw: ImageDraw.ImageDraw, width: int, height: int, rarity: str,
                       rarity_base, rarity_accent):
    """Cada raridade recebe uma geometria de moldura própria, não só outra cor."""
    if rarity == "Comum":
        draw.rounded_rectangle((5, 5, width - 6, height - 6), radius=18,
                               fill=(6, 9, 14, 255), outline=(*rarity_accent, 245), width=5)
        draw.rounded_rectangle((14, 14, width - 15, height - 15), radius=14,
                               outline=(220, 225, 226, 90), width=1)
        for x, y, sx, sy in ((23, 23, 1, 1), (width - 23, 23, -1, 1),
                             (23, height - 23, 1, -1), (width - 23, height - 23, -1, -1)):
            draw.line((x, y, x + sx * 18, y), fill=(*rarity_accent, 180), width=2)
            draw.line((x, y, x, y + sy * 18), fill=(*rarity_accent, 180), width=2)
    elif rarity == "Rara":
        draw.rounded_rectangle((5, 5, width - 6, height - 6), radius=22,
                               fill=(6, 9, 14, 255), outline=(*rarity_accent, 255), width=6)
        draw.rounded_rectangle((14, 14, width - 15, height - 15), radius=16,
                               outline=(*rarity_accent, 145), width=2)
        points = [(width // 2, 16), (width - 18, 42), (width - 18, height - 42),
                  (width // 2, height - 16), (18, height - 42), (18, 42), (width // 2, 16)]
        draw.line(points, fill=(230, 246, 245, 115), width=1)
        for cx, cy in ((width // 2, 19), (width - 19, height // 2),
                       (width // 2, height - 19), (19, height // 2)):
            draw.polygon([(cx, cy - 6), (cx + 6, cy), (cx, cy + 6), (cx - 6, cy)],
                         fill=(*rarity_accent, 220))
    elif rarity == "Épica":
        draw.rounded_rectangle((5, 5, width - 6, height - 6), radius=18,
                               fill=(6, 9, 14, 255), outline=(*rarity_accent, 255), width=6)
        points = [(width // 2, 13), (width - 13, 34), (width - 13, height - 34),
                  (width // 2, height - 13), (13, height - 34), (13, 34), (width // 2, 13)]
        draw.line(points, fill=(*rarity_accent, 225), width=3)
        draw.line([(width // 2, 22), (width - 22, 48), (width - 22, height - 48),
                   (width // 2, height - 22), (22, height - 48), (22, 48), (width // 2, 22)],
                  fill=(243, 224, 255, 105), width=1)
        for cx, cy in ((30, 30), (width - 30, 30), (30, height - 30), (width - 30, height - 30)):
            draw.polygon([(cx, cy - 9), (cx + 9, cy), (cx, cy + 9), (cx - 9, cy)],
                         fill=(*rarity_accent, 230), outline=(255, 244, 255, 220))
    elif rarity == "Lendária":
        draw.rounded_rectangle((4, 4, width - 5, height - 5), radius=24,
                               fill=(8, 8, 12, 255), outline=(*rarity_accent, 255), width=7)
        draw.rounded_rectangle((13, 13, width - 14, height - 14), radius=19,
                               outline=(255, 235, 171, 210), width=2)
        draw.rounded_rectangle((21, 21, width - 22, height - 22), radius=15,
                               outline=(*rarity_accent, 105), width=1)
        for side in (1, -1):
            x = 27 if side == 1 else width - 27
            for i in range(4):
                y = 165 + i * 62
                draw.arc((x - 14, y - 17, x + 14, y + 17), 205 if side == 1 else -25,
                         335 if side == 1 else 105, fill=(*rarity_accent, 165), width=2)
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 230, 164, 220))
        cx = width // 2
        draw.polygon([(cx - 22, 17), (cx - 15, 7), (cx, 18), (cx + 15, 7),
                      (cx + 22, 17), (cx + 17, 27), (cx - 17, 27)],
                     fill=(*rarity_base, 250), outline=(255, 231, 165, 255))
        draw.ellipse((cx - 3, 14, cx + 3, 20), fill=(255, 245, 205, 255))
    elif rarity == "Mítica":
        # Moldura estrelada: raios e gemas orbitais, distinta da coroa lendária.
        draw.rounded_rectangle((4, 4, width - 5, height - 5), radius=18,
                               fill=(10, 7, 16, 255), outline=(*rarity_accent, 255), width=7)
        draw.rounded_rectangle((15, 15, width - 16, height - 16), radius=13,
                               outline=(255, 190, 235, 190), width=2)
        cx = width // 2
        for x, y, r in ((cx, 18, 12), (cx, height - 18, 12), (20, height // 2, 8),
                        (width - 20, height // 2, 8), (24, 24, 6), (width - 24, 24, 6),
                        (24, height - 24, 6), (width - 24, height - 24, 6)):
            pts = []
            for i in range(10):
                angle = -math.pi / 2 + i * math.pi / 5
                radius = r if i % 2 == 0 else r * .38
                pts.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
            draw.polygon(pts, fill=(*rarity_base, 245), outline=(*rarity_accent, 255))
        for y in range(92, height - 92, 86):
            for x in (18, width - 18):
                draw.line((x, y - 12, x, y + 12), fill=(*rarity_accent, 185), width=2)
                draw.line((x - 7, y, x + 7, y), fill=(*rarity_accent, 185), width=2)
    elif rarity == "Primordial":
        # Moldura de relíquia ancestral: octógonos, discos solares e runas laterais.
        draw.rectangle((4, 4, width - 5, height - 5), fill=(11, 9, 5, 255),
                       outline=(*rarity_accent, 255), width=7)
        octagon = [(width // 2, 9), (width - 9, 34), (width - 9, height - 34),
                   (width // 2, height - 9), (9, height - 34), (9, 34), (width // 2, 9)]
        draw.line(octagon, fill=(255, 244, 190, 220), width=3)
        cx = width // 2
        for cy in (28, height - 28):
            draw.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), outline=(*rarity_accent, 255), width=3)
            draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(255, 245, 190, 245))
            for i in range(8):
                angle = math.pi * i / 4
                x1, y1 = cx + math.cos(angle) * 19, cy + math.sin(angle) * 19
                x2, y2 = cx + math.cos(angle) * 27, cy + math.sin(angle) * 27
                draw.line((x1, y1, x2, y2), fill=(*rarity_accent, 220), width=2)
        for side in (1, -1):
            x = 24 if side == 1 else width - 24
            for i in range(5):
                y = 150 + i * 72
                draw.polygon([(x, y - 9), (x + side * 7, y), (x, y + 9), (x - side * 7, y)],
                             outline=(255, 244, 190, 220), fill=(*rarity_base, 170))
    elif rarity == "Singular":
        # Moldura assimétrica: uma assinatura única, sem coroa ou simetria de conjunto.
        draw.rounded_rectangle((4, 4, width - 5, height - 5), radius=30,
                               fill=(5, 13, 15, 255), outline=(*rarity_accent, 255), width=7)
        draw.line([(15, 70), (15, 15), (width - 15, 15), (width - 15, height - 15),
                   (65, height - 15), (15, height - 65)], fill=(190, 255, 245, 210), width=2)
        draw.arc((width // 2 - 24, 4, width // 2 + 24, 52), 195, 345,
                 fill=(*rarity_accent, 255), width=4)
        draw.polygon([(width // 2, 8), (width // 2 + 10, 25), (width // 2, 42),
                      (width // 2 - 10, 25)], fill=(*rarity_base, 250), outline=(215, 255, 249, 255))
        for i in range(4):
            y = 170 + i * 80
            draw.arc((8, y - 18, 44, y + 18), 270, 90, fill=(*rarity_accent, 220), width=3)
            draw.arc((width - 44, y - 18, width - 8, y + 18), 90, 270, fill=(*rarity_accent, 220), width=3)
        draw.line((25, height - 90, 25, height - 35, 80, height - 35),
                  fill=(*rarity_accent, 220), width=3)
    else:
        draw.rectangle((5, 5, width - 6, height - 6), outline=(*rarity_accent, 255), width=5)


def _draw_gwent_unit(draw: ImageDraw.ImageDraw, box, faction: str, row: str, accent, rng: random.Random):
    """Ilustração procedural original orientada por facção e fileira do Gwent."""
    x1, y1, x2, y2 = box
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2 + 12
    h = y2 - y1
    # Arcos e runas de fundo variam pela fileira, não por categorias do jogo anterior.
    for radius in (int(h*.22), int(h*.31), int(h*.40)):
        draw.arc((cx-radius, cy-radius, cx+radius, cy+radius), 195, 345,
                 fill=(*accent, 105), width=2)
    for side in (-1, 1):
        sx = cx + side * int((x2-x1)*.29)
        draw.line((sx, y1+35, sx+side*12, y2-35), fill=(*accent, 85), width=2)
    head_r = max(16, int(h*.075))
    head_y = cy - int(h*.22)
    draw.ellipse((cx-head_r, head_y-head_r, cx+head_r, head_y+head_r),
                 fill=(18, 24, 31, 245), outline=(*accent, 235), width=4)
    shoulder = int(h*.16)
    torso_top = head_y + head_r
    torso_bottom = cy + int(h*.23)
    draw.polygon([(cx-shoulder, torso_top+8), (cx+shoulder, torso_top+8),
                  (cx+shoulder//2, torso_bottom), (cx-shoulder//2, torso_bottom)],
                 fill=(20, 29, 38, 245), outline=(*accent, 235))
    # Brasão da facção.
    shield_w = int(h*.14)
    shield_y = cy + int(h*.02)
    draw.polygon([(cx, shield_y), (cx+shield_w, shield_y+18),
                  (cx+shield_w//2, shield_y+int(h*.19)), (cx, shield_y+int(h*.22)),
                  (cx-shield_w//2, shield_y+int(h*.19)), (cx-shield_w, shield_y+18)],
                 fill=(11, 18, 25, 245), outline=(*accent, 230), width=3)
    # Arma/artefato comunica o papel tático.
    if row == "melee":
        draw.line((cx+shoulder//2, cy, cx+int(h*.24), cy-int(h*.24)), fill=(218, 222, 220, 255), width=7)
        draw.line((cx+int(h*.24)-12, cy-int(h*.24)+18, cx+int(h*.24)+12, cy-int(h*.24)-18), fill=(*accent, 255), width=5)
    elif row == "ranged":
        bx = cx + int(h*.23)
        draw.arc((bx-int(h*.10), cy-int(h*.18), bx+int(h*.10), cy+int(h*.18)), 270, 90, fill=(*accent, 255), width=5)
        draw.line((bx, cy-int(h*.18), bx, cy+int(h*.18)), fill=(220, 226, 221, 230), width=2)
    else:
        draw.line((cx+shoulder//2, cy+int(h*.12), cx+int(h*.22), cy-int(h*.29)), fill=(214, 207, 239, 255), width=6)
        draw.ellipse((cx+int(h*.22)-10, cy-int(h*.29)-10, cx+int(h*.22)+10, cy-int(h*.29)+10), fill=(*accent, 255))
    # Partículas controladas, sem símbolos ou lettering herdados.
    for _ in range(22):
        px = rng.randint(x1+18, x2-18)
        py = rng.randint(y1+18, y2-18)
        r = rng.choice((1, 2, 3))
        draw.ellipse((px-r, py-r, px+r, py+r), fill=(*accent, rng.randint(70, 170)))



def _draw_card(card: dict[str, Any], width: int = LARGURA_PADRAO, height: int = ALTURA_PADRAO,
               illustration_bytes: bytes | None = None) -> Image.Image:
    """Carta narrativa V11: arte ampla, moldura heráldica e leitura tática clara."""
    rarity = str(card.get("raridade", "Comum"))
    category = "Especial" if str(card.get("categoria", "Unidade")).casefold() == "especial" else "Unidade"
    ctype = str(card.get("tipo", "Magia"))
    faction = molduras_cartas.normalizar_faccao(card.get("faccao") or {"Força":"Ordem Áurea","Destreza":"Véu Carmesim","Magia":"Lua Negra"}.get(ctype,"Ordem Áurea"))
    row = str(card.get("fileira") or {"Força":"melee","Destreza":"ranged","Magia":"siege"}.get(ctype,"melee"))
    seed = _seed(card); rng = random.Random(seed)
    palettes = {
        "Ordem Áurea": ((39,31,17),(91,69,31),(224,183,82),(245,230,180)),
        "Véu Carmesim": ((43,13,18),(83,23,31),(177,49,62),(238,178,177)),
        "Lua Negra": ((18,15,39),(39,29,76),(139,112,214),(224,215,255)),
    }
    top, mid, accent, metal = palettes.get(faction, palettes["Ordem Áurea"])
    rarity_colors = {
        "Comum": ((23, 29, 37), (166, 181, 194)),
        "Rara": ((9, 29, 48), (77, 180, 226)),
        "Épica": ((28, 15, 50), (183, 126, 239)),
        "Lendária": ((39, 25, 10), (239, 185, 75)),
        "Mítica": ((38, 10, 18), (205, 61, 75)),
        "Primordial": ((34, 32, 25), (239, 224, 174)),
        "Singular": ((9, 12, 24), (151, 143, 206)),
    }
    rdark, rlight = rarity_colors.get(rarity, rarity_colors["Comum"])
    sx, sy = width/420, height/620
    X=lambda v:int(v*sx); Y=lambda v:int(v*sy)
    B=lambda a,b,c,d:(X(a),Y(b),X(c),Y(d))
    im=Image.new("RGBA",(width,height),(7,8,10,255))
    d=ImageDraw.Draw(im,"RGBA")

    # Pintura procedural com atmosfera, ruínas e profundidade em camadas.
    aw,ah=X(384),Y(430)
    art=Image.new("RGBA",(aw,ah),(*top,255)); a=ImageDraw.Draw(art,"RGBA")
    for yy in range(ah):
        t=yy/max(1,ah-1); col=_mix(top,mid,t*.82)
        a.line((0,yy,aw,yy),fill=(*col,255))
    sx0=rng.randint(int(aw*.28),int(aw*.72)); sy0=rng.randint(int(ah*.16),int(ah*.37))
    rad=rng.randint(int(ah*.10),int(ah*.18))
    for mul,alpha in ((2.1,12),(1.5,24),(1,76)):
        rr=int(rad*mul); a.ellipse((sx0-rr,sy0-rr,sx0+rr,sy0+rr),fill=(*accent,alpha))
    # Silhuetas de serras e muralhas.
    for layer in range(3):
        pts=[(0,ah)]; base_y=int(ah*(.51+layer*.105))
        for xx in range(-20,aw+45,max(26,aw//8)):
            peak=base_y-rng.randint(int(ah*.04),int(ah*.19))
            pts.extend([(xx,peak),(xx+max(18,aw//13),base_y+rng.randint(-8,9))])
        pts.append((aw,ah))
        shade=_mix(top,(7,10,13),.28+layer*.18)
        a.polygon(pts,fill=(*shade,250))
    # Torres, paliçadas, bandeiras e fumaça.
    for i in range(5):
        bx=rng.randint(-8,max(0,aw-24)); by=rng.randint(int(ah*.55),int(ah*.75))
        bw=rng.randint(max(12,aw//20),max(20,aw//9)); bh=rng.randint(int(ah*.10),int(ah*.27))
        stone=_mix(mid,(7,10,12),.52)
        a.rectangle((bx,by-bh,bx+bw,by),fill=(*stone,235))
        a.polygon([(bx-4,by-bh),(bx+bw//2,by-bh-8),(bx+bw+4,by-bh)],fill=(*stone,235))
        for wx in range(bx+5,bx+bw-3,10):
            a.rectangle((wx,by-bh+8,wx+3,by-bh+16),fill=(*accent,65))
    for side in (-1,1):
        pole=int(aw*(.13 if side<0 else .86)); py=int(ah*rng.uniform(.29,.47))
        a.line((pole,py,pole,int(ah*.82)),fill=(*metal,165),width=max(2,X(3)))
        fw=int(aw*.12); fh=int(ah*.12)
        a.polygon([(pole,py),(pole+side*fw,py+Y(7)),(pole+side*fw*.82,py+fh),(pole,py+fh-Y(5))],
                  fill=(*accent,115),outline=(*metal,150))
    for i in range(8):
        yy=rng.randint(int(ah*.63),int(ah*.96))
        a.line((0,yy,aw,yy+rng.randint(-8,8)),fill=(*metal,rng.randint(12,34)),width=max(1,Y(5)))

    # Camada de cenário exclusiva fica atrás do personagem/motivo principal.
    _draw_unique_scene(art, card, rng, accent, metal, top)

    # Motivo narrativo individual: o ID define a família visual e o nome/descrição
    # refinam o tema. Tudo é vetorial, determinístico e não depende de assets externos.
    card_id = str(card.get("id", "")).casefold()
    identity = " ".join((card_id, str(card.get("nome", "")), str(card.get("descricao", "")))).casefold()
    motif = ImageDraw.Draw(art, "RGBA")
    mx, my = aw // 2, int(ah * .39)
    glow = (*accent, 38)
    if card_id.startswith("chefe_") or any(k in identity for k in ("chefe", "guardiao", "guardião", "cervo", "dama", "rei afogado", "sem rosto")):
        # Arco de ameaça e chifres/coroa variáveis para chefes.
        motif.ellipse((mx-int(aw*.27), my-int(ah*.26), mx+int(aw*.27), my+int(ah*.20)), outline=(*accent,105), width=max(2,X(4)))
        points=[]
        for j in range(12):
            ang=-math.pi/2+j*math.pi/6
            rad=int(aw*(.19 if j%2==0 else .145))
            points.append((mx+int(math.cos(ang)*rad), my-int(ah*.06)+int(math.sin(ang)*rad)))
        motif.line(points+[points[0]], fill=(*metal,150), width=max(2,X(3)), joint="curve")
        for side in (-1,1):
            motif.line((mx+side*int(aw*.12),my-int(ah*.12),mx+side*int(aw*.22),my-int(ah*.31),mx+side*int(aw*.18),my-int(ah*.12)), fill=(*accent,185), width=max(3,X(6)))
    elif card_id.startswith("arma_") or any(k in identity for k in ("lâmina", "lamina", "martelo", "cajado", "arco", "sino", "lança", "lanca", "agulha")):
        # Silhueta de equipamento grande ao fundo, com forma conforme o nome.
        if any(k in identity for k in ("arco", "batedor")):
            motif.arc((mx-int(aw*.30),my-int(ah*.27),mx+int(aw*.30),my+int(ah*.28)),260,100,fill=(*metal,190),width=max(4,X(8)))
            motif.line((mx,my-int(ah*.27),mx,my+int(ah*.28)),fill=(*accent,180),width=max(2,X(3)))
        elif any(k in identity for k in ("martelo", "sino")):
            motif.line((mx-int(aw*.18),my+int(ah*.28),mx+int(aw*.18),my-int(ah*.25)),fill=(*metal,175),width=max(7,X(12)))
            motif.polygon([(mx+int(aw*.08),my-int(ah*.29)),(mx+int(aw*.29),my-int(ah*.25)),(mx+int(aw*.27),my-int(ah*.08)),(mx+int(aw*.06),my-int(ah*.12))],fill=(*accent,100),outline=(*metal,220))
        else:
            motif.polygon([(mx,my-int(ah*.34)),(mx+int(aw*.045),my-int(ah*.02)),(mx+int(aw*.018),my+int(ah*.24)),(mx,my+int(ah*.31)),(mx-int(aw*.018),my+int(ah*.24)),(mx-int(aw*.045),my-int(ah*.02))],fill=(*metal,115),outline=(*accent,210))
            motif.line((mx-int(aw*.12),my+int(ah*.14),mx+int(aw*.12),my+int(ah*.14)),fill=(*accent,220),width=max(3,X(6)))
    elif card_id.startswith("magia_") or any(k in identity for k in ("orbe", "oráculo", "oraculo", "brasa", "trovão", "trovao", "névoa", "nevoa", "sol negro", "fagulha", "chama")):
        # Portal arcano com órbitas e partículas em posições exclusivas.
        for j in range(4):
            rr=int(aw*(.12+j*.055))
            motif.ellipse((mx-rr,my-int(rr*.82),mx+rr,my+int(rr*.82)),outline=(*accent,max(48,160-j*24)),width=max(2,X(3)))
        for j in range(9):
            ang=math.radians(j*40+seed%31)
            ex=mx+int(math.cos(ang)*aw*.29); ey=my+int(math.sin(ang)*ah*.24)
            motif.line((mx,my,ex,ey),fill=(*metal,95),width=max(1,X(2)))
            motif.ellipse((ex-X(3),ey-Y(3),ex+X(3),ey+Y(3)),fill=(*accent,210))
    elif card_id.startswith("covenant_") or any(k in identity for k in ("covenant", "pacto", "irmandade", "lobos", "lua velada", "sentinelas", "abismo")):
        # Estandarte e brasão da ordem, com variação heráldica por carta.
        pole=int(aw*.19); motif.line((pole,int(ah*.13),pole,int(ah*.79)),fill=(*metal,190),width=max(3,X(5)))
        motif.polygon([(pole,my-int(ah*.17)),(pole+int(aw*.25),my-int(ah*.10)),(pole+int(aw*.21),my+int(ah*.12)),(pole,my+int(ah*.16))],fill=(*accent,105),outline=(*metal,220))
        motif.ellipse((mx-int(aw*.10),my-int(aw*.10),mx+int(aw*.10),my+int(aw*.10)),outline=(*metal,220),width=max(3,X(4)))
        motif.line((mx-int(aw*.08),my,mx+int(aw*.08),my),fill=(*accent,230),width=max(3,X(4)))
    else:
        # Brasão singular para cartas geradas de jogos/patentes e demais famílias.
        sides=5+(seed%4); radius=int(aw*(.13+(seed%5)*.012))
        pts=[(mx+int(math.cos(-math.pi/2+j*2*math.pi/sides)*radius),my+int(math.sin(-math.pi/2+j*2*math.pi/sides)*radius)) for j in range(sides)]
        motif.polygon(pts,fill=glow,outline=(*metal,175))
        motif.ellipse((mx-X(8),my-Y(8),mx+X(8),my+Y(8)),fill=(*accent,210))

    # Arte enviada pelo jogador ocupa a janela toda, mas recebe a moldura nova.
    custom=False
    if illustration_bytes:
        try:
            with Image.open(io.BytesIO(illustration_bytes)) as src:
                art=ImageOps.fit(src.convert("RGB"),(aw,ah),method=Image.Resampling.LANCZOS,
                                 centering=(.5,.46)).convert("RGBA")
            tint=Image.new("RGBA",art.size,(*top,18)); art=Image.alpha_composite(art,tint); custom=True
        except (OSError,ValueError):
            custom=False
    if not custom and category=="Unidade":
        a=ImageDraw.Draw(art,"RGBA")
        cx=int(aw*rng.uniform(.44,.57)); ground=int(ah*.94)
        archetype=seed%8
        # Arquétipos narrativos dirigidos pelo conteúdo da carta, não apenas pelo acaso.
        # O seed ainda varia pose, proporções, ornamentos e cenário dentro de cada família.
        if card_id.startswith("chefe_"):
            if any(k in identity for k in ("cervo", "lobo", "fera")): archetype=3
            elif any(k in identity for k in ("dama", "aparição", "aparicao", "oráculo", "oraculo")): archetype=2
            elif any(k in identity for k in ("afogado", "abismo", "esqueleto")): archetype=4
            elif any(k in identity for k in ("caçador", "cacador", "sem rosto")): archetype=5
            else: archetype=0
        elif card_id.startswith("magia_"):
            archetype=6 if any(k in identity for k in ("brasa", "chama", "fagulha", "fogo")) else 2
        elif card_id.startswith("arma_"):
            if any(k in identity for k in ("duelista", "dançarina", "dancarino", "batedor")): archetype=5
            elif any(k in identity for k in ("oráculo", "oraculo", "tecela", "tecelã")): archetype=2
            else: archetype=0
        elif card_id.startswith("covenant_"):
            if any(k in identity for k in ("lobo", "lobos")): archetype=3
            elif any(k in identity for k in ("lua", "véu", "veu")): archetype=2
            elif any(k in identity for k in ("abismo", "coroa")): archetype=4
            else: archetype=0
        body=_mix((12,16,20),accent,.22); cloth=_mix(top,metal,.18)
        # capa, com pontas e dobras ao vento
        cape=cx+rng.choice((-1,1))*int(aw*.27)
        a.polygon([(cx-X(20),int(ah*.38)),(cx+X(20),int(ah*.38)),(cape,ground),
                   (cx+X(9),int(ah*.82)),(cx-X(18),ground-Y(8))],
                  fill=(*_mix(top,(4,6,9),.25),245),outline=(*accent,175))
        head_y=int(ah*(.30 if archetype!=3 else .38)); hr=int(ah*(.064 if archetype!=3 else .105))
        if archetype==3: # fera / criatura
            a.ellipse((cx-hr,head_y-hr,cx+hr,head_y+hr),fill=(*body,255),outline=(*metal,235),width=max(2,X(3)))
            a.polygon([(cx-hr+4,head_y-hr+8),(cx-hr-X(24),head_y-hr-Y(38)),(cx-hr//3,head_y-hr+3)],
                      fill=(*body,255),outline=(*accent,245))
            a.polygon([(cx+hr-4,head_y-hr+8),(cx+hr+X(24),head_y-hr-Y(38)),(cx+hr//3,head_y-hr+3)],
                      fill=(*body,255),outline=(*accent,245))
            a.ellipse((cx-hr//2,head_y-2,cx-hr//2+X(7),head_y+Y(6)),fill=(*accent,255))
            a.ellipse((cx+hr//2-X(7),head_y-2,cx+hr//2,head_y+Y(6)),fill=(*accent,255))
            a.polygon([(cx-hr,head_y+hr//2),(cx+hr,head_y+hr//2),(cx+int(aw*.21),ground),
                       (cx-int(aw*.21),ground)],fill=(*body,255),outline=(*metal,180))
        else:
            # elmo/rosto e pescoço
            a.ellipse((cx-hr,head_y-hr,cx+hr,head_y+hr),fill=(151,119,96,255),outline=(*metal,220),width=max(1,X(2)))
            a.pieslice((cx-hr-X(5),head_y-hr-Y(10),cx+hr+X(5),head_y+hr),180,360,
                       fill=(*body,255),outline=(*metal,210))
            if archetype in (1,7):
                a.polygon([(cx,head_y-hr-Y(20)),(cx-hr-X(17),head_y-hr+Y(5)),
                           (cx+hr+X(17),head_y-hr+Y(5))],fill=(*_mix(body,accent,.15),255),outline=(*accent,220))
            shoulder=int(aw*(.17 if archetype not in (2,5) else .14))
            torso_top=head_y+hr; torso_bottom=int(ah*(.75 if archetype!=2 else .84))
            waist=int(shoulder*.58)
            if archetype==2: # arcanista de manto
                shape=[(cx-shoulder,torso_top),(cx+shoulder,torso_top),(cx+int(aw*.22),ground),
                       (cx-int(aw*.22),ground)]
            elif archetype==5: # assassino leve
                shape=[(cx-int(shoulder*.8),torso_top),(cx+int(shoulder*.8),torso_top),
                       (cx+waist,torso_bottom),(cx-waist,torso_bottom)]
            else:
                shape=[(cx-shoulder,torso_top+8),(cx-int(shoulder*.7),torso_top-2),
                       (cx+int(shoulder*.7),torso_top-2),(cx+shoulder,torso_top+8),
                       (cx+waist,torso_bottom),(cx-waist,torso_bottom)]
            a.polygon(shape,fill=(*body,255),outline=(*metal,235),width=max(2,X(3)))
            a.polygon([(cx-int(shoulder*.64),torso_top+8),(cx+int(shoulder*.64),torso_top+8),
                       (cx+int(shoulder*.42),torso_top+int(ah*.19)),(cx,torso_bottom-Y(10)),
                       (cx-int(shoulder*.42),torso_top+int(ah*.19))],
                      fill=(*cloth,255),outline=(*accent,245),width=max(1,X(2)))
            # placas de ombro, rebites, brasão e cintura
            for side in (-1,1):
                qx=cx+side*int(shoulder*.82)
                a.polygon([(qx-side*X(13),torso_top+5),(qx+side*X(16),torso_top+8),
                           (qx+side*X(22),torso_top+Y(31)),(qx,torso_top+Y(39)),
                           (qx-side*X(17),torso_top+Y(24))],fill=(*_mix(body,metal,.22),255),
                          outline=(*metal,230))
                a.ellipse((qx-X(3),torso_top+Y(18),qx+X(3),torso_top+Y(24)),fill=(*accent,255))
            a.polygon([(cx,torso_top+Y(15)),(cx+X(15),torso_top+Y(31)),
                       (cx,torso_top+Y(48)),(cx-X(15),torso_top+Y(31))],
                      fill=(*accent,245),outline=(*metal,255))
            a.line((cx-int(shoulder*.5),torso_top+int(ah*.24),cx+int(shoulder*.5),torso_top+int(ah*.24)),
                   fill=(*metal,185),width=max(2,X(3)))
            # braços em pose assimétrica e pernas em passada
            arm_l=(cx-int(shoulder*.84),torso_top+Y(12)); elbow_l=(cx-int(shoulder*1.16),int(ah*.57))
            hand_l=(cx-int(shoulder*.72),int(ah*.66)); arm_r=(cx+int(shoulder*.82),torso_top+Y(10))
            elbow_r=(cx+int(shoulder*1.12),int(ah*.48)); hand_r=(cx+int(aw*.19),int(ah*.58))
            for aa,bb,cc in ((arm_l,elbow_l,hand_l),(arm_r,elbow_r,hand_r)):
                a.line((aa[0],aa[1],bb[0],bb[1]),fill=(*body,255),width=max(8,X(17)))
                a.line((bb[0],bb[1],cc[0],cc[1]),fill=(*body,255),width=max(7,X(14)))
                a.ellipse((bb[0]-X(9),bb[1]-Y(9),bb[0]+X(9),bb[1]+Y(9)),
                          fill=(*_mix(body,metal,.3),255),outline=(*metal,235),width=max(1,X(2)))
            hip=int(ah*.74)
            for side in (-1,1):
                hx=cx+side*int(waist*.55); kx=cx+side*int(aw*.07); ky=int(ah*(.80 if side<0 else .77))
                bx=cx+side*int(aw*(.12 if side<0 else .085))
                a.line((hx,hip,kx,ky),fill=(*body,255),width=max(10,X(19)))
                a.line((kx,ky,bx,ground),fill=(*body,255),width=max(9,X(16)))
                a.polygon([(kx-X(12),ky-Y(10)),(kx+X(12),ky-Y(10)),
                           (kx+X(14),ky+Y(12)),(kx-X(14),ky+Y(12))],
                          fill=(*_mix(body,metal,.25),255),outline=(*metal,230))
                a.line((bx-X(9),ground-Y(3),bx+X(14),ground-Y(3)),fill=(*metal,225),width=max(2,X(4)))
            # armas e adereços distintos por fileira
            hx,hy=hand_r
            if row=="melee":
                a.line((hx,hy,cx+int(aw*.28),int(ah*.16)),fill=(211,215,210,255),width=max(4,X(7)))
                a.line((hx-X(13),hy-Y(12),hx+X(13),hy+Y(10)),fill=(*accent,255),width=max(3,X(5)))
            elif row=="ranged":
                bx=cx+int(aw*.23)
                a.arc((bx-int(aw*.10),int(ah*.27),bx+int(aw*.10),int(ah*.69)),270,90,fill=(*accent,255),width=max(4,X(6)))
                a.line((bx,int(ah*.28),bx,int(ah*.70)),fill=(*metal,255),width=max(2,X(2)))
            else:
                ox=cx+int(aw*.24); oy=int(ah*.17)
                a.line((hx,hy,ox,oy),fill=(*metal,255),width=max(5,X(8)))
                rr=int(aw*.06); a.ellipse((ox-rr,oy-rr,ox+rr,oy+rr),fill=(*accent,215),outline=(*metal,255),width=max(2,X(3)))
            # aura visual da habilidade (escudo, vingança, ressurgir, devorar, sobrevivente, espólios)
            desenhar_aura_unidade(art, str(card.get("habilidade", "")), aw, ah, cx, int(ah * .85), accent, metal, seed)
            # partículas, runas e luz de recorte
            for _ in range(42):
                qx=rng.randint(4,aw-4); qy=rng.randint(int(ah*.18),ah-4); rr=rng.choice((1,2,3))
                a.ellipse((qx-rr,qy-rr,qx+rr,qy+rr),fill=(*accent,rng.randint(35,125)))
    elif not custom:
        # Especiais: tempestade, selo, fogo ou ruptura arcana.
        a=ImageDraw.Draw(art,"RGBA"); cx,cy=aw//2,int(ah*.5); motif=seed%6
        for i in range(6):
            rr=int(min(aw,ah)*(.11+i*.065))
            a.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),outline=(*accent,max(28,135-i*17)),width=max(1,X(2)))
        for ang in range(0,360,30 if motif%2==0 else 45):
            rad=math.radians(ang+rng.randint(-5,5))
            ex=cx+int(math.cos(rad)*aw*.46); ey=cy+int(math.sin(rad)*ah*.43)
            a.line((cx,cy,ex,ey),fill=(*metal,105),width=max(1,X(2)))
        if not desenhar_emblema_especial(art, str(card.get("habilidade", "")), aw, ah, accent, metal, seed):
            a.polygon([(cx,cy-int(ah*.28)),(cx+int(aw*.18),cy),
                       (cx,cy+int(ah*.28)),(cx-int(aw*.18),cy)],
                      fill=(*accent,75),outline=(*metal,235),width=max(2,X(3)))
            rr=int(aw*.07); a.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),fill=(*accent,180),outline=(*metal,255),width=max(2,X(3)))
    im.alpha_composite(art,(X(18),Y(90)))
    # Acabamento: vinheta, brilho de borda e foil conforme a raridade.
    im=molduras_cartas.aplicar_efeitos_arte(im,rarity,seed,X,Y)
    especial=category=="Especial"
    est=molduras_cartas.ESTILOS.get(rarity,molduras_cartas.ESTILOS["Comum"])
    fac=molduras_cartas.FACCOES.get(faction,molduras_cartas.FACCOES["Ordem Áurea"])
    d=ImageDraw.Draw(im,"RGBA")

    # Largura da placa de raridade depende do texto (medida em unidades da grade 420).
    f_rar=_font(max(8,X(10)),True)
    rar_txt=rarity.upper()
    larg_rar=_largura_rastreada(d,rar_txt,f_rar,X(1.6))/max(sx,.01)+12
    ov=molduras_cartas.overlay_pronto(rarity,faction,ctype,row,especial,int(math.ceil(larg_rar/4)*4),width,height)
    im=Image.alpha_composite(im,ov)
    d=ImageDraw.Draw(im,"RGBA")

    creme=(249,243,228,255); sombra=(0,0,0,205)
    def txt(xy,texto,font,fill,anchor="mm",sombra_px=1):
        if sombra_px:
            d.text((xy[0],xy[1]+max(1,X(sombra_px))),texto,font=font,fill=sombra,anchor=anchor)
        d.text(xy,texto,font=font,fill=fill,anchor=anchor)

    # Título centralizado na placa; uma linha ganha legenda da coleção, duas linhas ocupam a placa.
    px1,py1,px2,py2=molduras_cartas.PLACA
    pcx=X((px1+px2)/2); pcy=Y((py1+py2)/2); maxw=X(296)
    title=str(card.get("nome","Carta")); linhas=None
    for tam in (22,20,18,17):
        ft=_font(max(10,X(tam)),True,serif=True)
        if d.textlength(title,font=ft)<=maxw:
            linhas=[title]; break
    if linhas is None:
        for tam in (17,16,15,14):
            ft=_font(max(9,X(tam)),True,serif=True); linhas=_wrap(d,title,ft,maxw)
            if len(linhas)<=2: break
        linhas=linhas[:2]
    if len(linhas)==1:
        _texto_rastreado(d,(pcx,Y(37)),"COLISEU  ·  CRÔNICAS DE GUERRA",_font(max(7,X(8)),True),
                         (*est["cor"],235),X(1.4),centro=True)
        txt((pcx,Y(61)),linhas[0],ft,creme)
    else:
        txt((pcx,Y(46)),linhas[0],ft,creme); txt((pcx,Y(67)),linhas[1],ft,creme)

    # Poder (ou selo de carta especial, já desenhado na moldura).
    if not especial:
        poder=int(card.get("poder",0) or 0)
        f_pod=_font(max(14,X(30 if poder<10 else 24)),True,serif=True)
        qx,qy=molduras_cartas.CENTRO_PODER
        d.text((X(qx),Y(qy)+max(1,X(1))),str(poder),font=f_pod,fill=(0,0,0,255),anchor="mm",
               stroke_width=max(2,X(2)),stroke_fill=(0,0,0,255))
        d.text((X(qx),Y(qy)),str(poder),font=f_pod,fill=(255,250,232,255),anchor="mm")

    # Placa de raridade.
    rx,ry=molduras_cartas.CENTRO_RARIDADE
    _texto_rastreado(d,(X(rx),Y(ry)+max(1,X(1))),rar_txt,f_rar,(0,0,0,210),X(1.6),centro=True)
    _texto_rastreado(d,(X(rx),Y(ry)),rar_txt,f_rar,(255,250,236,255),X(1.6),centro=True)

    # Painel: facção + fileira, habilidade e texto de efeito.
    f_lbl=_font(max(8,X(9.5)),True)
    row_label={"melee":"CORPO A CORPO","ranged":"LONGA DISTÂNCIA","siege":"CERCO"}.get(row,"TÁTICA") if not especial else "CARTA ESPECIAL"
    _texto_rastreado(d,(X(38),Y(491)),faction.upper(),f_lbl,(*fac["cor"],255),X(1.0))
    larg=_largura_rastreada(d,row_label,f_lbl,X(1.0))
    _texto_rastreado(d,(X(386)-larg,Y(491)),row_label,f_lbl,(*fac["metal"],225),X(1.0))
    aname, atext = _dados_habilidade_visual(card)
    f_hab=_font(max(10,X(13.5)),True,serif=True)
    txt((X(38),Y(518)),aname,f_hab,(*est["luz"],255),anchor="lm")
    # O texto usa o maior tamanho que couber em 3 linhas (12 → 9); só no mínimo aceita 4 linhas.
    for tam in (12, 11, 10, 9):
        fonte_txt=_font(max(8,X(tam))); linhas_txt=_wrap(d,atext,fonte_txt,X(342))
        if len(linhas_txt)<=3: break
    passo=tam+3.4 if len(linhas_txt)<=3 else 12.6
    for i,line in enumerate(linhas_txt[:4]):
        d.text((X(38),Y(538+i*passo)),line,font=fonte_txt,fill=(228,224,212,255),anchor="lm")

    # O sistema atual não usa custo de carta/deck: o espaço inferior é reservado
    # integralmente para o texto da habilidade.
    return im.convert("RGB")


# Cartas com template completo (somente quando o membro enviou uma arte)
# ---------------------------------------------------------------------------
def _ajustar_texto(draw: ImageDraw.ImageDraw, texto: str, largura: int, altura: int, *,
                   maximo: int, minimo: int, negrito: bool = False, max_linhas: int = 1,
                   espaco: float = 1.18):
    """Maior fonte em que o texto cabe na caixa; devolve (fonte, linhas, altura_da_linha)."""
    texto = str(texto or "").strip()
    for tamanho in range(maximo, minimo - 1, -1):
        fonte = _font(tamanho, negrito)
        linhas = _wrap(draw, texto, fonte, largura)
        altura_linha = int(tamanho * espaco)
        if len(linhas) <= max_linhas and len(linhas) * altura_linha <= altura \
                and all(draw.textbbox((0, 0), linha, font=fonte)[2] <= largura for linha in linhas):
            return fonte, linhas, altura_linha
    fonte = _font(minimo, negrito)
    altura_linha = int(minimo * espaco)
    linhas = _wrap(draw, texto, fonte, largura)[:max(1, min(max_linhas, altura // max(1, altura_linha)))]
    if linhas and len(linhas) == max_linhas and len(_wrap(draw, texto, fonte, largura)) > len(linhas):
        while linhas[-1] and draw.textbbox((0, 0), linhas[-1] + "…", font=fonte)[2] > largura:
            linhas[-1] = linhas[-1][:-1]
        linhas[-1] = linhas[-1].rstrip() + "…"
    return fonte, linhas, altura_linha


def _texto_no_slot(draw: ImageDraw.ImageDraw, retangulo, texto: str, *, maximo: int, minimo: int,
                   cor, negrito: bool = True, max_linhas: int = 1, margem: int = 20,
                   alinhamento: str = "centro", contorno: int = 0, cor_contorno=(8, 10, 16, 255)):
    x1, y1, x2, y2 = retangulo
    fonte, linhas, altura_linha = _ajustar_texto(
        draw, texto, (x2 - x1) - margem * 2, (y2 - y1) - 8,
        maximo=maximo, minimo=minimo, negrito=negrito, max_linhas=max_linhas,
    )
    topo = y1 + ((y2 - y1) - altura_linha * len(linhas)) / 2
    for indice, linha in enumerate(linhas):
        largura_linha = draw.textbbox((0, 0), linha, font=fonte)[2]
        if alinhamento == "esquerda":
            x = x1 + margem
        elif alinhamento == "direita":
            x = x2 - margem - largura_linha
        else:
            x = (x1 + x2) / 2 - largura_linha / 2
        caixa = draw.textbbox((0, 0), linha, font=fonte)
        y = topo + indice * altura_linha + (altura_linha - (caixa[3] - caixa[1])) / 2 - caixa[1]
        draw.text((x, y), linha, font=fonte, fill=cor, stroke_width=contorno, stroke_fill=cor_contorno)


def _draw_card_com_template(card: dict[str, Any], illustration_bytes: bytes) -> Image.Image | None:
    """Monta: arte do membro (atrás) → template da raridade (frente) → textos nos slots.

    Devolve `None` quando a raridade não tem template ou a arte não pode ser lida; o chamador
    então usa o desenho tradicional por código.
    """
    rarity = str(card.get("raridade", "Comum"))
    carregado = templates_cartas.carregar_template(rarity)
    if carregado is None:
        return None
    template, layout = carregado
    largura, altura = template.size
    try:
        with Image.open(io.BytesIO(illustration_bytes)) as origem:
            # Arte de origem é reduzida antes da composição; 2x a janela final é suficiente.
            origem.thumbnail((1680, 1360), Image.Resampling.LANCZOS)
            origem_rgb = origem.convert("RGB")
    except (OSError, ValueError):
        return None

    ax1, ay1, ax2, ay2 = layout["arte"]
    # A arte avança alguns pixels por baixo da moldura: nenhuma fresta aparece na borda.
    sangria = max(4, largura // 140)
    bx1, by1 = max(0, ax1 - sangria), max(0, ay1 - sangria)
    bx2, by2 = min(largura, ax2 + sangria), min(altura, ay2 + sangria)
    arte = ImageOps.fit(origem_rgb, (bx2 - bx1, by2 - by1), method=Image.Resampling.LANCZOS,
                        centering=(0.5, 0.48)).convert("RGBA")
    base = Image.new("RGBA", (largura, altura), (8, 10, 15, 255))
    base.paste(arte, (bx1, by1))
    imagem = Image.alpha_composite(base, template)
    draw = ImageDraw.Draw(imagem, "RGBA")

    category = str(card.get("categoria", "Unidade"))
    card_type = str(card.get("tipo", "Magia"))
    faction = molduras_cartas.normalizar_faccao(card.get("faccao") or {"Força": "Ordem Áurea", "Destreza": "Véu Carmesim", "Magia": "Lua Negra"}.get(card_type, "Ordem Áurea"))
    row = str(card.get("fileira") or {"Força": "melee", "Destreza": "ranged", "Magia": "siege"}.get(card_type, "melee"))
    rarity_base, rarity_accent = CORES_RARIDADE.get(rarity, CORES_RARIDADE["Comum"])
    type_accent = CORES_FACCAO.get(faction, ((21, 29, 39), (44, 47, 61)))[1]
    accent = _mix(rarity_accent, type_accent, 0.34)
    creme = (245, 241, 229, 255)
    suave = (205, 208, 212, 235)

    # Selo de raridade e nome.
    _texto_no_slot(draw, layout["raridade"], rarity.upper(), maximo=30, minimo=16, cor=creme,
                   margem=12, contorno=2)
    _texto_no_slot(draw, layout["nome"], str(card.get("nome", "Carta")), maximo=58, minimo=26,
                   cor=creme, max_linhas=2, margem=28, contorno=3)

    # Poder no medalhão.
    cx, cy = layout["poder"]["centro"]
    raio = layout["poder"]["raio"]
    poder = str(int(card.get("poder", 0) or 0))
    fonte_poder, _, _ = _ajustar_texto(draw, poder, int(raio * 1.45), int(raio * 1.1),
                                        maximo=int(raio * 1.0), minimo=24, negrito=True)
    draw.text((cx, cy - raio * 0.12), poder, font=fonte_poder, fill=creme, anchor="mm",
              stroke_width=3, stroke_fill=(8, 10, 16, 255))
    draw.text((cx, cy + raio * 0.58), "PODER", font=_font(max(14, int(raio * 0.24)), True),
              fill=suave, anchor="mm", stroke_width=1, stroke_fill=(8, 10, 16, 255))

    # Tipo (com ícone) e categoria.
    tx1, ty1, tx2, ty2 = layout["tipo"]
    altura_tipo = ty2 - ty1
    icone = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    _draw_type_icon(ImageDraw.Draw(icone, "RGBA"), (20, 20), card_type, type_accent)
    lado = max(32, int(altura_tipo * 0.62))
    icone = icone.resize((lado, lado), Image.Resampling.LANCZOS)
    imagem.alpha_composite(icone, (tx1 + 22, ty1 + (altura_tipo - lado) // 2))
    draw = ImageDraw.Draw(imagem, "RGBA")
    _texto_no_slot(draw, (tx1 + 22 + lado + 6, ty1, tx2, ty2), faction, maximo=34, minimo=15,
                   cor=creme, alinhamento="esquerda", margem=14, contorno=1)
    _texto_no_slot(draw, (tx1 + (tx2 - tx1) // 2, ty1, tx2, ty2),
                   ROTULOS_FILEIRA.get(row, "UNIDADE"), maximo=22, minimo=12,
                   cor=suave, alinhamento="direita", margem=22, negrito=True)

    # Habilidade: o guia reserva uma placa de 92 px. O título e até duas linhas
    # de descrição são dimensionados dentro da área segura, sem invadir o relevo.
    nome_hab, texto_hab = _dados_habilidade_visual(card)
    nome_hab = nome_hab.strip()
    texto_hab = texto_hab.strip()
    hx1, hy1, hx2, hy2 = layout["habilidade"]
    margem_x, margem_y = 24, 9
    y_texto = hy1 + margem_y
    largura_util = (hx2 - hx1) - margem_x * 2
    if nome_hab:
        fonte_nome, linhas_nome, altura_nome = _ajustar_texto(
            draw, nome_hab.upper(), largura_util, 27,
            maximo=23, minimo=15, negrito=True, max_linhas=1, espaco=1.0,
        )
        titulo = linhas_nome[0] if linhas_nome else nome_hab.upper()[:36]
        draw.text((hx1 + margem_x, y_texto), titulo, font=fonte_nome,
                  fill=(*accent, 255), stroke_width=1, stroke_fill=(8, 10, 16, 255))
        y_texto += max(25, altura_nome) + 1
    if texto_hab and y_texto < hy2 - margem_y:
        altura_disponivel = hy2 - margem_y - y_texto
        fonte, linhas, altura_linha = _ajustar_texto(
            draw, texto_hab, largura_util, altura_disponivel,
            maximo=19, minimo=13, max_linhas=2, espaco=1.08,
        )
        for indice, linha in enumerate(linhas[:2]):
            draw.text((hx1 + margem_x, y_texto + indice * altura_linha), linha, font=fonte,
                      fill=(230, 231, 227, 255), stroke_width=1, stroke_fill=(8, 10, 16, 255))
    return imagem.convert("RGB")


def desenhar_calibracao(imagem: Image.Image, raridade: str) -> Image.Image:
    """Contorna os slots do guia oficial sobre uma carta montada para verificar alinhamento."""
    layout = templates_cartas.carregar_layout(raridade)
    carregado = templates_cartas.carregar_template(raridade)
    if carregado:
        layout = carregado[1]
    saida = imagem.convert("RGBA")
    draw = ImageDraw.Draw(saida, "RGBA")
    cores = {"raridade": (240, 180, 60), "nome": (80, 160, 255), "arte": (60, 220, 120),
             "tipo": (190, 120, 255), "habilidade": (255, 90, 150)}
    for campo, cor in cores.items():
        x1, y1, x2, y2 = layout[campo]
        draw.rectangle((x1, y1, x2, y2), outline=(*cor, 255), width=3)
        draw.text((x1 + 6, y1 + 4), f"{campo} {x1},{y1}→{x2},{y2}", font=_font(15, True), fill=(*cor, 255),
                  stroke_width=2, stroke_fill=(0, 0, 0, 255))
    cx, cy = layout["poder"]["centro"]
    raio = layout["poder"]["raio"]
    draw.ellipse((cx - raio, cy - raio, cx + raio, cy + raio), outline=(255, 210, 60, 255), width=3)
    return saida.convert("RGB")


def _arte_de_exemplo(card: dict[str, Any]) -> bytes:
    """Ilustração procedural limpa, usada só nas prévias administrativas dos templates.

    O renderizador tradicional inclui uma etiqueta de tipo/categoria sobre sua própria arte.
    Como os templates já desenham essas informações nas placas inferiores, removemos essa
    etiqueta apenas da imagem de demonstração para não simular uma duplicação na carta final.
    """
    base = _draw_card(dict(card))
    demo = base.convert("RGBA")
    demo_draw = ImageDraw.Draw(demo, "RGBA")
    demo_draw.rounded_rectangle((38, 391, 205, 416), radius=8, fill=(9, 13, 20, 255))
    x1, y1, x2, y2 = 32, 132, LARGURA_PADRAO - 32, 419
    recorte = demo.crop((x1, y1, x2, y2)).resize((1092, 861), Image.Resampling.LANCZOS)
    saida = io.BytesIO()
    recorte.save(saida, format="PNG")
    return saida.getvalue()


def render_previa_template(raridade: str, *, calibracao: bool = False) -> io.BytesIO | None:
    """Carta de exemplo usando o template salvo da raridade (ou `None` se não houver)."""
    if templates_cartas.carregar_template(raridade) is None:
        return None
    exemplo = {
        "id": f"preview_template_{templates_cartas.RARIDADES_TEMPLATE.get(raridade, 'x')}",
        "nome": f"Prévia — {raridade}",
        "categoria": "Chefe",
        "raridade": raridade,
        "tipo": "Magia",
        "poder": 88,
        "custo": 3,
        "habilidade": next(iter(HABILIDADES), ""),
        "descricao": "Prévia do template completo enviado.",
    }
    imagem = _draw_card_com_template(exemplo, _arte_de_exemplo(exemplo))
    if imagem is None:
        return None
    if calibracao:
        imagem = desenhar_calibracao(imagem, raridade)
    saida = io.BytesIO()
    imagem.save(saida, format="PNG", optimize=False)
    saida.seek(0)
    return saida


def _fingerprint_templates(payload: Any) -> str:
    """Inclui a versão dos templates dinâmicos do Ateliê na chave do PNG.

    Os templates são atualizados em DATA_DIR sem alterar o código. mtime_ns + tamanho
    do PNG e o conteúdo dos metadados Discord invalidam o cache assim que um template
    é substituído, removido ou cadastrado.
    """
    if isinstance(payload, dict) and isinstance(payload.get("card"), dict):
        cards = [payload["card"]]
    elif isinstance(payload, dict) and isinstance(payload.get("cards"), list):
        cards = [card for card in payload["cards"] if isinstance(card, dict)]
    elif isinstance(payload, dict):
        cards = [payload]
    else:
        cards = []

    raridades = sorted({str(card.get("raridade", "Comum")) for card in cards})
    digest = hashlib.sha256()
    for raridade in raridades:
        digest.update(raridade.encode("utf-8"))
        try:
            caminhos = (
                templates_cartas.caminho_cache_template(raridade),
                templates_cartas.caminho_metadados_template(raridade),
            )
        except ValueError:
            continue
        for caminho in caminhos:
            try:
                info = caminho.stat()
                digest.update(
                    f"{caminho.name}:{info.st_size}:{info.st_mtime_ns}".encode("utf-8")
                )
                # Os metadados são pequenos; seu conteúdo detecta uma nova referência
                # Discord mesmo quando o tamanho do JSON não muda.
                if caminho.suffix == ".json":
                    digest.update(caminho.read_bytes())
            except OSError:
                digest.update(f"{caminho.name}:missing".encode("utf-8"))
    return digest.hexdigest()[:16]


def _cache_path(payload: Any, suffix: str) -> Path:
    root = get_data_dir() / "cartas_cache"
    root.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    versao_cache = f"{VERSAO_RENDERIZADOR}:{_fingerprint_templates(payload)}"
    digest = hashlib.sha256(f"{versao_cache}:{raw}".encode("utf-8")).hexdigest()[:24]
    return root / f"{digest}.{suffix}"


def cache_carta_existente(
    card: dict[str, Any],
    *,
    tamanho: tuple[int, int] = (LARGURA_PADRAO, ALTURA_PADRAO),
) -> Path | None:
    """Retorna o PNG persistente validado sem iniciar uma renderização."""
    largura, altura = max(120, int(tamanho[0])), max(180, int(tamanho[1]))
    path = _cache_path({"card": card, "size": [largura, altura]}, "png")
    with _cache_lock_for(path):
        if _cache_png_valido(path):
            return path
    return None


def cache_arte_oficial_existente(
    card: dict[str, Any], illustration_bytes: bytes,
) -> Path | None:
    """Retorna a composição persistente da arte oficial, identificada pelo hash da imagem."""
    illustration_hash = hashlib.sha256(illustration_bytes).hexdigest()
    payload = {
        "card": card,
        "kind": "official-illustration",
        "illustration_sha256": illustration_hash,
        "size": [LARGURA_PADRAO, ALTURA_PADRAO],
    }
    path = _cache_path(payload, "png")
    with _cache_lock_for(path):
        if _cache_png_valido(path):
            return path
    return None


def _cache_path_arte_oficial_id(
    card: dict[str, Any], official_art_id: int | str,
    tamanho: tuple[int, int] = (LARGURA_PADRAO, ALTURA_PADRAO),
    *, suffix: str = "png",
) -> Path:
    largura, altura = max(120, int(tamanho[0])), max(180, int(tamanho[1]))
    payload = {
        "card": card,
        "kind": "official-illustration",
        # A submissão aprovada é imutável: nova arte recebe outro ID. Isso permite
        # consultar o cache sem carregar o BLOB inteiro do SQLite em cache hit.
        "official_art_id": str(official_art_id),
        "size": [largura, altura],
    }
    return _cache_path(payload, suffix)


def cache_arte_oficial_por_id_existente(
    card: dict[str, Any], official_art_id: int | str,
    tamanho: tuple[int, int] = (LARGURA_PADRAO, ALTURA_PADRAO),
) -> Path | None:
    """Localiza composição oficial persistente usando apenas o ID da submissão."""
    path = _cache_path_arte_oficial_id(card, official_art_id, tamanho)
    with _cache_lock_for(path):
        if _cache_png_valido(path):
            return path
    return None


def render_arte_oficial_cacheada_por_id(
    card: dict[str, Any], illustration_bytes: bytes, official_art_id: int | str,
    tamanho: tuple[int, int] = (LARGURA_PADRAO, ALTURA_PADRAO),
) -> Path:
    """Gera composição oficial uma vez por ID, versão visual e dimensões."""
    largura, altura = max(120, int(tamanho[0])), max(180, int(tamanho[1]))
    path = _cache_path_arte_oficial_id(card, official_art_id, (largura, altura))
    with _cache_lock_for(path):
        if _cache_png_valido(path):
            return path
        if path.exists():
            path.unlink(missing_ok=True)
            with _CACHE_LOCK_GUARD:
                _CACHE_VALIDATED.pop(str(path), None)
        if not validar_imagem_bytes(illustration_bytes):
            raise ValueError("A imagem oficial armazenada não é válida ou excede os limites permitidos.")
        imagem = _draw_card(card, width=largura, height=altura, illustration_bytes=illustration_bytes)
        _salvar_png_atomico(imagem, path, optimize=False)
    return path


def cache_carta_webp_existente(
    card: dict[str, Any], *, tamanho: tuple[int, int] = (210, 310), quality: int = 82,
) -> Path | None:
    largura, altura = max(120, int(tamanho[0])), max(180, int(tamanho[1]))
    quality = max(50, min(95, int(quality)))
    payload = {"card": card, "size": [largura, altura], "format": "webp", "quality": quality}
    path = _cache_path(payload, "webp")
    with _cache_lock_for(path):
        if _cache_webp_valido(path, (largura, altura)):
            return path
    return None


def render_carta_webp(
    card: dict[str, Any], *, tamanho: tuple[int, int] = (210, 310), quality: int = 82,
) -> Path:
    """Miniatura WebP persistente; desenha diretamente na resolução de destino."""
    largura, altura = max(120, int(tamanho[0])), max(180, int(tamanho[1]))
    quality = max(50, min(95, int(quality)))
    payload = {"card": card, "size": [largura, altura], "format": "webp", "quality": quality}
    path = _cache_path(payload, "webp")
    with _cache_lock_for(path):
        if _cache_webp_valido(path, (largura, altura)):
            return path
        if path.exists():
            path.unlink(missing_ok=True)
            with _CACHE_LOCK_GUARD:
                _CACHE_VALIDATED.pop(str(path), None)
        imagem = _draw_card(card, width=largura, height=altura)
        _salvar_webp_atomico(imagem, path, quality=quality, method=4)
    return path


def cache_arte_oficial_webp_existente(
    card: dict[str, Any], official_art_id: int | str,
    tamanho: tuple[int, int] = (210, 310), quality: int = 82,
) -> Path | None:
    largura, altura = max(120, int(tamanho[0])), max(180, int(tamanho[1]))
    payload = {
        "card": card, "kind": "official-illustration", "official_art_id": str(official_art_id),
        "size": [largura, altura], "format": "webp", "quality": int(quality),
    }
    path = _cache_path(payload, "webp")
    with _cache_lock_for(path):
        if _cache_webp_valido(path, (largura, altura)):
            return path
    return None


def render_arte_oficial_webp_cacheada_por_id(
    card: dict[str, Any], illustration_bytes: bytes, official_art_id: int | str,
    tamanho: tuple[int, int] = (210, 310), quality: int = 82,
) -> Path:
    largura, altura = max(120, int(tamanho[0])), max(180, int(tamanho[1]))
    quality = max(50, min(95, int(quality)))
    payload = {
        "card": card, "kind": "official-illustration", "official_art_id": str(official_art_id),
        "size": [largura, altura], "format": "webp", "quality": quality,
    }
    path = _cache_path(payload, "webp")
    with _cache_lock_for(path):
        if _cache_webp_valido(path, (largura, altura)):
            return path
        if path.exists():
            path.unlink(missing_ok=True)
            with _CACHE_LOCK_GUARD:
                _CACHE_VALIDATED.pop(str(path), None)
        if not validar_imagem_bytes(illustration_bytes):
            raise ValueError("A imagem oficial armazenada não é válida ou excede os limites permitidos.")
        imagem = _draw_card(card, width=largura, height=altura, illustration_bytes=illustration_bytes)
        _salvar_webp_atomico(imagem, path, quality=quality, method=4)
    return path


def render_carta_bytes_cacheada(card: dict[str, Any], illustration_bytes: bytes) -> Path:
    """Compõe arte oficial uma única vez e persiste o PNG validado para próximos acessos."""
    payload = {
        "card": card,
        "kind": "official-illustration",
        "illustration_sha256": hashlib.sha256(illustration_bytes).hexdigest(),
        "size": [LARGURA_PADRAO, ALTURA_PADRAO],
    }
    path = _cache_path(payload, "png")
    with _cache_lock_for(path):
        if _cache_png_valido(path):
            return path
        if path.exists():
            path.unlink(missing_ok=True)
            with _CACHE_LOCK_GUARD:
                _CACHE_VALIDATED.pop(str(path), None)
        if not validar_imagem_bytes(illustration_bytes):
            raise ValueError("A imagem oficial armazenada não é válida ou excede os limites permitidos.")
        imagem = _draw_card(card, illustration_bytes=illustration_bytes)
        _salvar_png_atomico(imagem, path, optimize=False)
    return path


def render_carta(
    card: dict[str, Any],
    *,
    tamanho: tuple[int, int] = (LARGURA_PADRAO, ALTURA_PADRAO),
) -> Path:
    """Renderiza no tamanho de exibição e reutiliza cache persistente validado."""
    largura, altura = max(120, int(tamanho[0])), max(180, int(tamanho[1]))
    payload = {"card": card, "size": [largura, altura]}
    path = _cache_path(payload, "png")
    with _cache_lock_for(path):
        if _cache_png_valido(path):
            return path
        if path.exists():
            log.warning("PNG inválido no cache de cartas; regenerando: %s", path.name)
            path.unlink(missing_ok=True)
            with _CACHE_LOCK_GUARD:
                _CACHE_VALIDATED.pop(str(path), None)
        # O renderer é proporcional; desenhar no tamanho final evita criar um RGBA
        # 420x620 apenas para reduzi-lo em miniaturas de catálogo.
        imagem = _draw_card(card, width=largura, height=altura)
        _salvar_png_atomico(imagem, path, optimize=False)
    return path


def render_pacote(cards: list[dict[str, Any]]) -> Path:
    payload = {"cards": cards, "layout": "pack-3-v4-vector-rarity-frames"}
    path = _cache_path(payload, "png")
    with _cache_lock_for(path):
        if _cache_png_valido(path):
            return path
        if path.exists():
            log.warning("PNG inválido no cache de pacote; regenerando: %s", path.name)
            path.unlink(missing_ok=True)
            with _CACHE_LOCK_GUARD:
                _CACHE_VALIDATED.pop(str(path), None)
        card_w, card_h, gap = 294, 434, 16
        canvas = Image.new("RGB", (card_w * 3 + gap * 4, card_h + gap * 2), (7, 10, 16))
        canvas_draw = ImageDraw.Draw(canvas, "RGBA")
        for inset, alpha in ((0, 90), (5, 45)):
            canvas_draw.rounded_rectangle((inset, inset, canvas.width - inset - 1, canvas.height - inset - 1),
                                          radius=22, outline=(208, 166, 83, alpha), width=2)
        for index, card in enumerate(cards[:3]):
            art = _draw_card(card).resize((card_w, card_h), Image.Resampling.LANCZOS)
            canvas.paste(art, (gap + index * (card_w + gap), gap))
        _salvar_png_atomico(canvas, path, optimize=False)
    return path


def render_carta_bytes(card: dict[str, Any], illustration_bytes: bytes) -> io.BytesIO:
    """Monta uma carta personalizada; rejeita arte inválida em vez de mostrá-la como oficial."""
    if not validar_imagem_bytes(illustration_bytes):
        raise ValueError("A imagem oficial armazenada não é válida ou excede os limites permitidos.")
    imagem = _draw_card(card, illustration_bytes=illustration_bytes)
    saida = io.BytesIO()
    imagem.save(saida, format="PNG", optimize=True)
    saida.seek(0)
    return saida
