"""Arte local e determinística para as cartas do Coliseu.

As ilustrações são compostas com formas originais do Pillow. A categoria define a
composição, o tipo define a paleta secundária e a raridade altera moldura e ornamentos.
Nenhuma imagem, personagem ou marca de jogo de terceiros é incorporada.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import random
import threading
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from runtime_paths import get_data_dir
from .cartas import EMOJIS_TIPO, HABILIDADES, VERSAO_ARTES
from . import templates_cartas

# Cor principal da moldura por raridade: as categorias e os tipos continuam
# visualmente distintos dentro de cada faixa de raridade.
CORES_RARIDADE = {
    "Comum": ((35, 47, 59), (143, 163, 177)),
    "Rara": ((17, 56, 76), (72, 190, 218)),
    "Épica": ((54, 34, 83), (188, 119, 239)),
    "Lendária": ((83, 52, 18), (246, 194, 83)),
    "Primordial": ((35, 28, 12), (255, 238, 145)),
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
LARGURA_PADRAO = 420
ALTURA_PADRAO = 620


RARIDADES_MOLDURA = {
    "Comum": "comum",
    "Rara": "rara",
    "Épica": "epica",
    "Lendária": "lendaria",
    "Primordial": "primordial",
}
TAMANHO_MOLDURA = (420, 620)
TAMANHO_MAXIMO_MOLDURA = 8 * 1024 * 1024
PIXELS_MAXIMOS_MOLDURA = 20_000_000
_MOLDURAS_CACHE: dict[tuple[str, int, int], tuple[int, int, Image.Image]] = {}
_MOLDURAS_LOCK = threading.RLock()


def caminho_moldura_personalizada(raridade: str) -> Path:
    """Caminho persistente da moldura enviada pelo proprietário do bot."""
    slug = RARIDADES_MOLDURA.get(str(raridade))
    if not slug:
        raise ValueError(f"Raridade sem moldura configurável: {raridade}")
    return get_data_dir() / "cartas_molduras" / f"{slug}.png"


def listar_molduras_personalizadas() -> dict[str, bool]:
    """Informa quais raridades já possuem um PNG de moldura personalizado."""
    return {raridade: caminho_moldura_personalizada(raridade).is_file() for raridade in RARIDADES_MOLDURA}


def limpar_cache_molduras(raridade: str | None = None) -> None:
    """Invalida as versões em memória; usada após trocar/remover um arquivo."""
    with _MOLDURAS_LOCK:
        if raridade is None:
            _MOLDURAS_CACHE.clear()
            return
        for chave in list(_MOLDURAS_CACHE):
            if chave[0] == raridade:
                _MOLDURAS_CACHE.pop(chave, None)


def salvar_moldura_personalizada(raridade: str, dados: bytes) -> Path:
    """Valida e grava um overlay PNG transparente, sem aceitar uma carta completa."""
    destino = caminho_moldura_personalizada(raridade)
    if not dados or len(dados) > TAMANHO_MAXIMO_MOLDURA:
        raise ValueError("O arquivo precisa ter conteúdo e no máximo 8 MB.")
    try:
        with Image.open(io.BytesIO(dados)) as origem:
            if origem.format != "PNG":
                raise ValueError("A moldura precisa ser PNG com transparência real (canal alfa).")
            largura, altura = origem.size
            if largura * altura > PIXELS_MAXIMOS_MOLDURA:
                raise ValueError("A imagem excede o limite de 20 milhões de pixels. Exporte em 840 × 1240.")
            if largura < 420 or altura < 620:
                raise ValueError("A resolução mínima é 420 × 620 pixels; prefira 840 × 1240.")
            proporcao_esperada = TAMANHO_MOLDURA[0] / TAMANHO_MOLDURA[1]
            if abs((largura / altura) - proporcao_esperada) > 0.003:
                raise ValueError("A proporção precisa ser exatamente a da carta: 420:620 (840 × 1240 recomendado).")
            if origem.mode not in {"RGBA", "LA"} and "transparency" not in origem.info:
                raise ValueError("O PNG não contém transparência alfa. O centro precisa ser transparente.")
            imagem = origem.convert("RGBA")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Não consegui abrir o arquivo. Envie um PNG válido.") from exc

    alfa = imagem.getchannel("A")
    # A área central precisa permanecer praticamente vazia para não cobrir arte,
    # título, poder, custo ou habilidade que o bot desenha sob a moldura.
    x1, x2 = int(largura * 0.12), int(largura * 0.88)
    y1, y2 = int(altura * 0.10), int(altura * 0.90)
    hist_centro = alfa.crop((x1, y1, x2, y2)).histogram()
    total_centro = max(1, (x2 - x1) * (y2 - y1))
    transparentes = sum(hist_centro[:9])
    if transparentes / total_centro < 0.985:
        raise ValueError(
            "O centro do PNG não está suficientemente transparente. Envie somente a moldura, "
            "sem fundo, sem ilustração e sem preencher a área interna."
        )

    # Exige detalhe visível no perímetro para evitar salvar um PNG praticamente vazio.
    hist_total = alfa.histogram()
    visiveis = sum(hist_total[65:])
    if visiveis < max(1200, int(largura * altura * 0.003)):
        raise ValueError("A moldura parece vazia ou quase invisível. Reforce os detalhes nas bordas.")

    imagem = imagem.resize(TAMANHO_MOLDURA, Image.Resampling.LANCZOS)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".png.tmp")
    imagem.save(temporario, format="PNG", optimize=True)
    temporario.replace(destino)
    limpar_cache_molduras(raridade)
    return destino


def remover_moldura_personalizada(raridade: str) -> bool:
    """Remove a moldura enviada e volta a usar o acabamento vetorial padrão."""
    caminho = caminho_moldura_personalizada(raridade)
    existia = caminho.is_file()
    if existia:
        caminho.unlink(missing_ok=True)
    limpar_cache_molduras(raridade)
    return existia


def _assinatura_moldura(raridade: str) -> str:
    if raridade not in RARIDADES_MOLDURA:
        return "padrao"
    caminho = caminho_moldura_personalizada(raridade)
    try:
        info = caminho.stat()
        return f"{info.st_mtime_ns}:{info.st_size}"
    except OSError:
        return "padrao"


def _carregar_moldura(raridade: str, largura: int, altura: int) -> Image.Image | None:
    if raridade not in RARIDADES_MOLDURA:
        return None
    caminho = caminho_moldura_personalizada(raridade)
    try:
        info = caminho.stat()
    except OSError:
        limpar_cache_molduras(raridade)
        return None
    chave = (raridade, largura, altura)
    with _MOLDURAS_LOCK:
        existente = _MOLDURAS_CACHE.get(chave)
        if existente and existente[0] == info.st_mtime_ns and existente[1] == info.st_size:
            return existente[2].copy()
        try:
            with Image.open(caminho) as arquivo:
                moldura = arquivo.convert("RGBA")
            if moldura.size != (largura, altura):
                moldura = moldura.resize((largura, altura), Image.Resampling.LANCZOS)
            _MOLDURAS_CACHE[chave] = (info.st_mtime_ns, info.st_size, moldura.copy())
            return moldura
        except (OSError, ValueError):
            _MOLDURAS_CACHE.pop(chave, None)
            return None


def _font(size: int, bold: bool = False):
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root / "fonts" / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        root / "fonts" / "DejaVuSans.ttf",
    ]
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


def _draw_corner_ornament(draw: ImageDraw.ImageDraw, x: int, y: int, sx: int, sy: int, accent):
    p1 = (x, y)
    p2 = (x + sx * 29, y)
    p3 = (x, y + sy * 29)
    draw.line((p1, p2), fill=(*accent, 190), width=3)
    draw.line((p1, p3), fill=(*accent, 190), width=3)
    draw.polygon([(x + sx * 8, y + sy * 8), (x + sx * 16, y + sy * 8),
                  (x + sx * 8, y + sy * 16)], fill=(*accent, 210))


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
    else:  # Lendária e Primordial: moldura tripla; Primordial recebe acabamento dourado claro.
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
        # Pequena coroa no topo da moldura, sem invadir o título.
        cx = width // 2
        draw.polygon([(cx - 22, 17), (cx - 15, 7), (cx, 18), (cx + 15, 7),
                      (cx + 22, 17), (cx + 17, 27), (cx - 17, 27)],
                     fill=(*rarity_base, 250), outline=(255, 231, 165, 255))
        draw.ellipse((cx - 3, 14, cx + 3, 20), fill=(255, 245, 205, 255))


def _draw_card(card: dict[str, Any], width: int = LARGURA_PADRAO, height: int = ALTURA_PADRAO,
               illustration_bytes: bytes | None = None) -> Image.Image:
    # Carta com arte enviada pelo membro: usa o template completo da raridade, se houver.
    # Sem arte enviada (ou sem template configurado) segue o desenho por código abaixo.
    if illustration_bytes:
        com_template = _draw_card_com_template(card, illustration_bytes)
        if com_template is not None:
            return com_template
    rarity = str(card.get("raridade", "Comum"))
    category = str(card.get("categoria", "Carta"))
    card_type = str(card.get("tipo", "Magia"))
    rarity_base, rarity_accent = CORES_RARIDADE.get(rarity, CORES_RARIDADE["Comum"])
    type_accent = CORES_TIPO.get(card_type, (190, 190, 190))
    category_top, category_bottom = CORES_CATEGORIA.get(category, ((21, 29, 39), (44, 47, 61)))
    accent = _mix(rarity_accent, type_accent, 0.34)
    rng = random.Random(_seed(card))

    image = _gradient(width, height, _mix(category_top, rarity_base, .25), (7, 10, 16))
    draw = ImageDraw.Draw(image, "RGBA")

    # Textura de fundo determinística: poeira, brasas e riscos finos.
    for _ in range(190):
        x = rng.randint(12, width - 13)
        y = rng.randint(12, height - 13)
        radius = rng.choice((1, 1, 2, 3))
        alpha = rng.randint(16, 75)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*accent, alpha))
    for _ in range(18):
        x = rng.randint(25, width - 25)
        y = rng.randint(140, 390)
        draw.line((x, y, x + rng.randint(-16, 16), y - rng.randint(8, 26)),
                  fill=(*accent, rng.randint(18, 55)), width=1)

    # Luz difusa atrás da ilustração.
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((width * .17, height * .22, width * .83, height * .69),
                      fill=(*accent, 92))
    glow = glow.filter(ImageFilter.GaussianBlur(max(12, width // 18)))
    image = Image.alpha_composite(image.convert("RGBA"), glow)
    draw = ImageDraw.Draw(image, "RGBA")

    # Uma moldura PNG enviada pela administração substitui o acabamento vetorial.
    # Sem arquivo personalizado, o estilo original continua como fallback.
    moldura_fixa = _carregar_moldura(rarity, width, height)
    if moldura_fixa is None:
        _draw_rarity_frame(draw, width, height, rarity, rarity_base, rarity_accent)
        draw.rounded_rectangle((21, 21, width - 22, height - 22), radius=14,
                               outline=(238, 231, 211, 38), width=1)

    # Cabeçalho editorial.
    brand_font = _font(11, True)
    small_font = _font(13, True)
    title_font = _font(25, True)
    draw.text((31, 29), "SOULSBOT  /  COLISEU", font=brand_font, fill=(200, 203, 207, 190))
    rarity_label = rarity.upper()
    rarity_box = draw.textbbox((0, 0), rarity_label, font=small_font)
    pill_w = rarity_box[2] - rarity_box[0] + 22
    draw.rounded_rectangle((width - 31 - pill_w, 22, width - 31, 48), radius=9,
                           fill=(*rarity_base, 245), outline=(*rarity_accent, 230), width=1)
    draw.text((width - 31 - pill_w + 11, 27), rarity_label, font=small_font, fill=(255, 249, 231, 255))

    title = str(card.get("nome", "Carta"))
    title_lines = _wrap(draw, title, title_font, width - 62)[:2]
    title_y = 58
    for line in title_lines:
        draw.text((31, title_y), line, font=title_font, fill=(245, 241, 229, 255),
                  stroke_width=0)
        title_y += 30

    # Janela de ilustração: a composição depende da categoria, não só de um símbolo.
    art_box = (28, 128, width - 28, 423)
    x1, y1, x2, y2 = art_box
    draw.rounded_rectangle(art_box, radius=17, fill=(*category_top, 220), outline=(*accent, 185), width=2)
    # Delimita a arte com luz periférica.
    draw.arc((x1 + 12, y1 + 12, x2 - 12, y2 - 12), 190, 350, fill=(*accent, 100), width=2)
    if illustration_bytes:
        # A ilustração personalizada é aplicada somente na janela de arte. A moldura,
        # raridade, título, poder e habilidade continuam sendo renderizados pelo bot.
        try:
            with Image.open(io.BytesIO(illustration_bytes)) as custom_source:
                custom_art = ImageOps.fit(
                    custom_source.convert("RGB"),
                    (x2 - x1, y2 - y1),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.48),
                ).convert("RGBA")
            mask = Image.new("L", (x2 - x1, y2 - y1), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle((0, 0, x2 - x1 - 1, y2 - y1 - 1), radius=17, fill=255)
            image.paste(custom_art, (x1, y1), mask)
            draw = ImageDraw.Draw(image, "RGBA")
            draw.rounded_rectangle(art_box, radius=17, outline=(*accent, 205), width=2)
            # Overlay sutil integra a arte externa à paleta do Coliseu sem alterar a composição.
            shade = Image.new("RGBA", (x2 - x1, y2 - y1), (5, 8, 13, 22))
            image.alpha_composite(shade, (x1, y1))
            draw = ImageDraw.Draw(image, "RGBA")
        except (OSError, ValueError):
            # Se uma imagem antiga do Discord estiver corrompida, mantém a arte oficial.
            if category == "Chefe":
                _draw_boss(draw, art_box, accent, rng, card)
            elif category == "Arma":
                _draw_weapon(draw, art_box, accent, rng, card)
            elif category == "Magia":
                _draw_magic(draw, art_box, accent, rng, card)
            elif category == "Covenant":
                _draw_covenant(draw, art_box, accent, rng, card)
            elif category == "Jogo":
                _draw_game(draw, art_box, accent, rng)
            elif category == "Patente":
                _draw_patente(draw, art_box, accent, rng)
            else:
                _draw_magic(draw, art_box, accent, rng, card)
    elif category == "Chefe":
        _draw_boss(draw, art_box, accent, rng, card)
    elif category == "Arma":
        _draw_weapon(draw, art_box, accent, rng, card)
    elif category == "Magia":
        _draw_magic(draw, art_box, accent, rng, card)
    elif category == "Covenant":
        _draw_covenant(draw, art_box, accent, rng, card)
    elif category == "Jogo":
        _draw_game(draw, art_box, accent, rng)
    elif category == "Patente":
        _draw_patente(draw, art_box, accent, rng)
    else:
        _draw_magic(draw, art_box, accent, rng, card)

    # Pequena assinatura de tipo na base da ilustração.
    type_label = f"{card_type.upper()}  /  {category.upper()}"
    label_font = _font(12, True)
    draw.rounded_rectangle((x1 + 12, y2 - 31, x1 + 174, y2 - 9), radius=7,
                           fill=(5, 9, 15, 205), outline=(*accent, 140), width=1)
    draw.text((x1 + 21, y2 - 27), type_label[:22], font=label_font, fill=(*accent, 255))

    # Painel de atributos, com poder em selo visual destacado.
    draw.line((28, 438, width - 28, 438), fill=(*rarity_accent, 180), width=2)
    power = int(card.get("poder", 0) or 0)
    cost = int(card.get("custo", 0) or 0)
    badge_x, badge_y = 72, 493
    draw.ellipse((badge_x - 39, badge_y - 39, badge_x + 39, badge_y + 39),
                 fill=(*rarity_base, 255), outline=(*rarity_accent, 255), width=4)
    draw.ellipse((badge_x - 30, badge_y - 30, badge_x + 30, badge_y + 30),
                 outline=(255, 244, 211, 125), width=1)
    _text_center(draw, (badge_x, badge_y - 7), str(power), _font(31, True), (255, 248, 227, 255))
    _text_center(draw, (badge_x, badge_y + 23), "PODER", _font(9, True), (231, 221, 199, 235))

    # Tipo e custo em etiquetas independentes.
    draw.rounded_rectangle((127, 459, width - 30, 489), radius=9,
                           fill=(15, 22, 31, 235), outline=(*type_accent, 185), width=1)
    _draw_type_icon(draw, (145, 474), card_type, type_accent)
    draw.text((164, 465), card_type, font=_font(15, True), fill=(242, 240, 232, 255))
    draw.rounded_rectangle((127, 496, width - 30, 526), radius=9,
                           fill=(15, 22, 31, 235), outline=(*rarity_accent, 145), width=1)
    draw.text((140, 502), f"CUSTO DE DECK  ·  {cost}", font=_font(13, True), fill=(231, 226, 211, 255))

    # Habilidade em faixa própria, sempre legível na imagem individual e no pacote.
    ability = HABILIDADES.get(str(card.get("habilidade", "")), {})
    ability_name = str(ability.get("nome", "Habilidade"))
    ability_text = str(ability.get("texto", card.get("descricao", "")))
    draw.rounded_rectangle((28, 542, width - 28, 588), radius=10,
                           fill=(12, 17, 25, 245), outline=(*accent, 125), width=1)
    draw.text((40, 548), ability_name.upper()[:34], font=_font(11, True), fill=(*accent, 255))
    ability_lines = _wrap(draw, ability_text, _font(11), width - 90)[:2]
    for index, line in enumerate(ability_lines):
        draw.text((40, 563 + index * 12), line, font=_font(11), fill=(225, 226, 222, 245))

    # Os brilhos vetoriais antigos só aparecem no fallback. Com moldura fixa,
    # o PNG enviado é a única camada ornamental de raridade.
    if moldura_fixa is None:
        if rarity in {"Lendária", "Primordial"}:
            for i in range(5):
                px = 35 + i * 84
                py = 120 + (i % 2) * 8
                draw.polygon([(px, py - 4), (px + 4, py), (px, py + 4), (px - 4, py)],
                             fill=(255, 235, 164, 225))
        elif rarity == "Épica":
            for i in range(4):
                px = 50 + i * 105
                draw.ellipse((px - 2, 117, px + 2, 121), fill=(*rarity_accent, 220))
    else:
        image = Image.alpha_composite(image.convert("RGBA"), moldura_fixa)

    return image.convert("RGB")


# ---------------------------------------------------------------------------
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

    category = str(card.get("categoria", "Carta"))
    card_type = str(card.get("tipo", "Magia"))
    rarity_base, rarity_accent = CORES_RARIDADE.get(rarity, CORES_RARIDADE["Comum"])
    type_accent = CORES_TIPO.get(card_type, (190, 190, 190))
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
    _texto_no_slot(draw, (tx1 + 22 + lado + 6, ty1, tx2, ty2), card_type, maximo=34, minimo=18,
                   cor=creme, alinhamento="esquerda", margem=14, contorno=1)
    _texto_no_slot(draw, (tx1 + (tx2 - tx1) // 2, ty1, tx2, ty2), category.upper(), maximo=22, minimo=12,
                   cor=suave, alinhamento="direita", margem=22, negrito=True)

    # Custo: rótulo à esquerda, valor à direita.
    custo = str(int(card.get("custo", 0) or 0))
    cx1, cy1, cx2, cy2 = layout["custo"]
    _texto_no_slot(draw, (cx1, cy1, cx1 + (cx2 - cx1) * 3 // 4, cy2), "CUSTO DE DECK", maximo=26, minimo=14,
                   cor=suave, alinhamento="esquerda", margem=22)
    _texto_no_slot(draw, (cx2 - 130, cy1, cx2, cy2), custo, maximo=44, minimo=22, cor=creme,
                   alinhamento="direita", margem=22, contorno=2)

    # Habilidade: o guia reserva uma placa de 92 px. O título e até duas linhas
    # de descrição são dimensionados dentro da área segura, sem invadir o relevo.
    habilidade = HABILIDADES.get(str(card.get("habilidade", "")), {})
    nome_hab = str(habilidade.get("nome", "")).strip()
    texto_hab = str(habilidade.get("texto", "") or card.get("descricao", "")).strip()
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
             "tipo": (190, 120, 255), "custo": (255, 130, 90), "habilidade": (255, 90, 150)}
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


def _cache_path(payload: Any, suffix: str) -> Path:
    root = get_data_dir() / "cartas_cache"
    root.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(f"{VERSAO_ARTES}:{raw}".encode("utf-8")).hexdigest()[:24]
    return root / f"{digest}.{suffix}"


def render_carta(
    card: dict[str, Any],
    *,
    tamanho: tuple[int, int] = (LARGURA_PADRAO, ALTURA_PADRAO),
) -> Path:
    """Renderiza no tamanho de exibição e reutiliza o arquivo em cache."""
    largura, altura = max(120, int(tamanho[0])), max(180, int(tamanho[1]))
    raridade = str(card.get("raridade", "Comum"))
    payload = {
        "card": card,
        "frame": _assinatura_moldura(raridade),
        "size": [largura, altura],
    }
    path = _cache_path(payload, "png")
    if path.exists():
        return path
    imagem = _draw_card(card)
    if imagem.size != (largura, altura):
        imagem = imagem.resize((largura, altura), Image.Resampling.LANCZOS)
    temporario = path.with_suffix(".png.tmp")
    imagem.save(temporario, format="PNG", optimize=False)
    temporario.replace(path)
    return path


def render_pacote(cards: list[dict[str, Any]]) -> Path:
    payload = {
        "cards": cards,
        "layout": "pack-3-v3-fixed-frames",
        "frames": {raridade: _assinatura_moldura(raridade) for raridade in RARIDADES_MOLDURA},
    }
    path = _cache_path(payload, "png")
    if path.exists():
        return path
    card_w, card_h, gap = 294, 434, 16
    canvas = Image.new("RGB", (card_w * 3 + gap * 4, card_h + gap * 2), (7, 10, 16))
    canvas_draw = ImageDraw.Draw(canvas, "RGBA")
    for inset, alpha in ((0, 90), (5, 45)):
        canvas_draw.rounded_rectangle((inset, inset, canvas.width - inset - 1, canvas.height - inset - 1),
                                      radius=22, outline=(208, 166, 83, alpha), width=2)
    for index, card in enumerate(cards[:3]):
        art = _draw_card(card).resize((card_w, card_h), Image.Resampling.LANCZOS)
        canvas.paste(art, (gap + index * (card_w + gap), gap))
    canvas.save(path, format="PNG", optimize=False)
    return path


def render_carta_bytes(card: dict[str, Any], illustration_bytes: bytes) -> io.BytesIO:
    """Monta uma carta personalizada em memória, sem criar cópia local da arte do membro."""
    imagem = _draw_card(card, illustration_bytes=illustration_bytes)
    saida = io.BytesIO()
    imagem.save(saida, format="PNG", optimize=True)
    saida.seek(0)
    return saida

def render_deck_preview_bytes(
    cards: list[dict[str, Any]],
    illustrations: dict[str, bytes] | None = None,
) -> io.BytesIO:
    """Renderiza uma prévia do deck em memória, incluindo artes personalizadas disponíveis."""
    illustrations = illustrations or {}
    card_width, card_height = 210, 310
    gap = 18
    header_height = 66
    columns = 3
    rows = max(1, math.ceil(min(len(cards), 5) / columns))
    width = columns * card_width + (columns + 1) * gap
    height = header_height + rows * card_height + (rows + 1) * gap

    canvas = Image.new("RGB", (width, height), (7, 10, 16))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.text((gap + 2, 17), "DECK DO COLISEU", font=_font(24, True),
              fill=(238, 220, 180, 255))
    draw.text((gap + 3, 44), f"{min(len(cards), 5)} / 5 CARTAS", font=_font(10, True),
              fill=(150, 164, 177, 255))

    for index, card in enumerate(cards[:5]):
        column = index % columns
        row = index // columns
        x = gap + column * (card_width + gap)
        y = header_height + gap + row * (card_height + gap)
        illustration = illustrations.get(str(card.get("id", "")))
        artwork = _draw_card(card, illustration_bytes=illustration)
        artwork = artwork.resize((card_width, card_height), Image.Resampling.LANCZOS)
        canvas.paste(artwork, (x, y))

    output = io.BytesIO()
    canvas.save(output, format="PNG", optimize=False)
    output.seek(0)
    return output


def _painel_arena_base(width: int, height: int, subtitle: str = "") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Fundo gráfico compartilhado pelas telas da Arena; sem depender de emojis do Discord."""
    image = _gradient(width, height, (13, 20, 31), (5, 8, 14)).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    # Moldura externa e linhas de arena discretas.
    draw.rounded_rectangle((18, 18, width - 19, height - 19), radius=28,
                           outline=(193, 151, 78, 150), width=2)
    draw.rounded_rectangle((27, 27, width - 28, height - 28), radius=23,
                           outline=(222, 198, 150, 35), width=1)
    for x in range(60, width - 40, 100):
        draw.line((x, 40, x, height - 40), fill=(150, 173, 194, 13), width=1)
    draw.text((58, 42), "SOULSBOT  /  COLOSSEUM", font=_font(17, True), fill=(216, 182, 112, 255))
    if subtitle:
        draw.text((60, 67), subtitle.upper(), font=_font(10, True), fill=(133, 153, 174, 245))
    return image, draw


def _painel_cartao(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
                    fill=(16, 25, 38, 238), outline=(170, 139, 89, 120), radius: int = 18):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def _texto_ajustado(draw: ImageDraw.ImageDraw, text: str, max_width: int,
                    font_size: int = 18, bold: bool = True, max_chars: int = 42) -> str:
    value = str(text or "—").replace("\n", " ").strip()
    font = _font(font_size, bold)
    while value and (len(value) > max_chars or draw.textbbox((0, 0), value, font=font)[2] > max_width):
        value = value[:-2].rstrip() + "…"
        if len(value) <= 2:
            break
    return value or "—"


def _card_back(size: tuple[int, int], number: int, accent=(198, 157, 85)) -> Image.Image:
    width, height = size
    image = _gradient(width, height, (25, 34, 49), (8, 12, 20)).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((3, 3, width - 4, height - 4), radius=max(8, width // 14),
                           outline=(*accent, 230), width=max(2, width // 75))
    draw.rounded_rectangle((width * .12, height * .12, width * .88, height * .88),
                           radius=max(6, width // 18), outline=(*accent, 105), width=2)
    cx, cy = width // 2, height // 2
    r = min(width, height) * .23
    draw.polygon([(cx, cy-r), (cx+r*.68, cy), (cx, cy+r), (cx-r*.68, cy)],
                 outline=(*accent, 210), fill=(48, 39, 29, 130))
    _text_center(draw, (cx, cy - 7), f"{number}", _font(max(15, width // 5), True), (245, 228, 190, 255))
    _text_center(draw, (cx, cy + r + 16), "SOULS", _font(max(7, width // 18), True), (183, 164, 131, 220))
    return image


def render_duel_hand_bytes(cards: list[dict[str, Any]], duel_id: int, round_no: int) -> io.BytesIO:
    """Mão de escolha visual: cinco cartas em linha, numeradas para os botões de seleção rápida."""
    count = min(5, len(cards))
    card_width, card_height, gap = 250, 369, 18
    margin = 34
    header_height = 88
    width = margin * 2 + count * card_width + max(0, count - 1) * gap
    width = max(760, width)
    height = header_height + card_height + 54
    canvas = _gradient(width, height, (17, 26, 41), (5, 8, 15)).convert("RGB")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle((12, 12, width - 13, height - 13), radius=24,
                           outline=(203, 164, 96, 185), width=2)
    draw.text((margin, 24), f"RODADA {int(round_no)}  /  05", font=_font(25, True),
              fill=(247, 230, 194, 255))
    draw.text((margin, 58), f"DUELO #{int(duel_id)}  ·  ESCOLHA UMA CARTA", font=_font(12, True),
              fill=(153, 171, 190, 255))
    start_x = (width - (count * card_width + max(0, count - 1) * gap)) // 2
    for index, card in enumerate(cards[:5]):
        x = start_x + index * (card_width + gap)
        art = _draw_card(card).resize((card_width, card_height), Image.Resampling.LANCZOS).convert("RGBA")
        # Sombra externa e índice fixo que corresponde ao botão sob a imagem.
        shadow = Image.new("RGBA", (card_width + 16, card_height + 16), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((5, 5, card_width + 10, card_height + 10),
                                                  radius=17, fill=(0, 0, 0, 125))
        canvas.paste(shadow, (x - 8, header_height - 3), shadow)
        canvas.paste(art, (x, header_height), art)
        draw = ImageDraw.Draw(canvas, "RGBA")
        rarity = str(card.get("raridade", "Comum"))
        base, accent = CORES_RARIDADE.get(rarity, CORES_RARIDADE["Comum"])
        bx, by = x + 31, header_height + 31
        draw.ellipse((bx - 23, by - 23, bx + 23, by + 23), fill=(*base, 250), outline=(*accent, 255), width=3)
        _text_center(draw, (bx, by - 1), str(index + 1), _font(23, True), (255, 247, 222, 255))
    draw.text((margin, height - 36), "TOQUE NO BOTÃO COM O MESMO NÚMERO DA CARTA", font=_font(12, True),
              fill=(214, 194, 157, 245))
    output = io.BytesIO()
    canvas.save(output, format="PNG", optimize=False)
    output.seek(0)
    return output


def render_duel_board_bytes(
    duel: dict[str, Any],
    rounds: list[dict[str, Any]],
    deck_a: list[dict[str, Any]],
    deck_b: list[dict[str, Any]],
    nome_a: str,
    nome_b: str,
    picks_count: int = 0,
    tempo_rodada: int = 30,
) -> io.BytesIO:
    """Tabuleiro completo de uma partida: confronto, trilha, cartas reveladas e resultado."""
    width, height = 1600, 1080
    duel_id = int(duel.get("id", 0) or 0)
    status = str(duel.get("status", "active"))
    current_round = max(1, min(5, int(duel.get("current_round", 1) or 1)))
    rounds_by_no = {int(row.get("round_no", 0)): row for row in rounds}
    map_a = {str(c.get("id")): c for c in deck_a}
    map_b = {str(c.get("id")): c for c in deck_b}
    power_a = sum(int(c.get("poder", 0) or 0) for c in deck_a)
    power_b = sum(int(c.get("poder", 0) or 0) for c in deck_b)
    wins_a = sum(str(r.get("winner_side")) == "a" for r in rounds)
    wins_b = sum(str(r.get("winner_side")) == "b" for r in rounds)
    draws = sum(str(r.get("winner_side")) == "empate" for r in rounds)
    aposta = int(duel.get("aposta", 0) or 0)
    pote = aposta * 2

    image, draw = _painel_arena_base(width, height, f"DUEL #{duel_id:04d}  ·  MATCH BOARD")
    status_labels = {
        "invited": ("CONVITE PENDENTE", (205, 160, 79)),
        "active": ("EM ANDAMENTO", (75, 183, 148)),
        "finished": ("PARTIDA CONCLUÍDA", (214, 177, 99)),
        "cancelled": ("PARTIDA ENCERRADA", (133, 148, 164)),
        "expired": ("CONVITE EXPIRADO", (133, 148, 164)),
    }
    status_label, status_color = status_labels.get(status, (status.upper(), (133, 148, 164)))
    pill_w = draw.textbbox((0, 0), status_label, font=_font(13, True))[2] + 34
    draw.rounded_rectangle((width - 70 - pill_w, 38, width - 70, 72), radius=16,
                           fill=(*status_color, 45), outline=(*status_color, 210), width=2)
    draw.text((width - 53 - pill_w, 48), status_label, font=_font(13, True), fill=(*status_color, 255))

    # Painéis de duelistas e placar central.
    panel_y, panel_h = 126, 205
    _painel_cartao(draw, (58, panel_y, 615, panel_y + panel_h), fill=(15, 27, 42, 245), outline=(70, 154, 132, 180))
    _painel_cartao(draw, (985, panel_y, 1542, panel_y + panel_h), fill=(35, 22, 29, 245), outline=(179, 91, 91, 180))
    winner_id = duel.get("winner_id")
    winner_side = None
    if status == "finished" and winner_id is not None:
        winner_side = "a" if int(winner_id) == int(duel.get("creator_id", 0)) else "b"
    if winner_side == "a":
        draw.rounded_rectangle((420, panel_y + 18, 590, panel_y + 49), radius=12,
                               fill=(83, 190, 141, 43), outline=(111, 222, 169, 210), width=2)
        _text_center(draw, (505, panel_y + 33), "CAMPEÃO", _font(11, True), (137, 232, 181, 255))
    elif winner_side == "b":
        draw.rounded_rectangle((1347, panel_y + 18, 1517, panel_y + 49), radius=12,
                               fill=(202, 102, 93, 43), outline=(235, 145, 133, 210), width=2)
        _text_center(draw, (1432, panel_y + 33), "CAMPEÃO", _font(11, True), (245, 164, 151, 255))
    draw.text((88, panel_y + 26), "DUELISTA A", font=_font(13, True), fill=(106, 215, 177, 255))
    draw.text((88, panel_y + 57), _texto_ajustado(draw, nome_a, 420, 30, True, 26), font=_font(30, True), fill=(246, 242, 232, 255))
    draw.text((88, panel_y + 112), f"PODER DO DECK  {power_a}", font=_font(16, True), fill=(158, 185, 196, 255))
    draw.text((1015, panel_y + 26), "DUELISTA B", font=_font(13, True), fill=(231, 133, 126, 255))
    draw.text((1015, panel_y + 57), _texto_ajustado(draw, nome_b, 420, 30, True, 26), font=_font(30, True), fill=(246, 242, 232, 255))
    draw.text((1015, panel_y + 112), f"PODER DO DECK  {power_b}", font=_font(16, True), fill=(196, 160, 164, 255))
    # Ícones circulares para dar identidade a cada lado.
    draw.ellipse((520, panel_y + 52, 584, panel_y + 116), fill=(27, 79, 68, 255), outline=(111, 218, 176, 230), width=3)
    _text_center(draw, (552, panel_y + 83), "A", _font(30, True), (238, 255, 247, 255))
    draw.ellipse((1446, panel_y + 52, 1510, panel_y + 116), fill=(91, 42, 48, 255), outline=(235, 142, 135, 230), width=3)
    _text_center(draw, (1478, panel_y + 83), "B", _font(30, True), (255, 240, 237, 255))

    _painel_cartao(draw, (650, panel_y + 7, 950, panel_y + panel_h - 7), fill=(20, 26, 37, 250), outline=(193, 151, 78, 170))
    _text_center(draw, (800, panel_y + 39), "PLACAR", _font(12, True), (182, 164, 132, 255))
    _text_center(draw, (800, panel_y + 99), f"{wins_a}  :  {wins_b}", _font(43, True), (248, 233, 199, 255))
    _text_center(draw, (800, panel_y + 141), f"{draws} EMPATE(S)", _font(11, True), (159, 169, 181, 255))
    _text_center(draw, (800, panel_y + 171), f"POTE  {pote:,} DENÁRIOS", _font(12, True), (221, 184, 107, 255))

    # Trilha das cinco rodadas.
    track_y = 365
    draw.text((66, track_y - 26), "TRILHA DA PARTIDA", font=_font(15, True), fill=(221, 198, 153, 255))
    track_x, track_w, track_h, track_gap = 66, 1468, 64, 14
    seg_w = (track_w - 4 * track_gap) // 5
    for index in range(5):
        number = index + 1
        row = rounds_by_no.get(number)
        x = track_x + index * (seg_w + track_gap)
        if row:
            winner = str(row.get("winner_side", "empate"))
            accent = (77, 190, 146) if winner == "a" else (215, 111, 105) if winner == "b" else (174, 177, 185)
            label = "VITÓRIA A" if winner == "a" else "VITÓRIA B" if winner == "b" else "EMPATE"
        elif status == "active" and number == current_round:
            accent = (224, 181, 91)
            label = f"{int(picks_count)}/2 ESCOLHAS"
        elif status == "invited":
            accent = (128, 142, 160)
            label = "AGUARDANDO"
        else:
            accent = (78, 91, 108)
            label = "NÃO JOGADA"
        draw.rounded_rectangle((x, track_y, x + seg_w, track_y + track_h), radius=14,
                               fill=(*accent, 27), outline=(*accent, 180), width=2)
        draw.text((x + 15, track_y + 10), f"RODADA {number}", font=_font(11, True), fill=(211, 218, 223, 255))
        draw.text((x + 15, track_y + 31), label, font=_font(12, True), fill=(*accent, 255))

    # Cinco vitrines de rodada com miniaturas reais das cartas usadas.
    start_y = 470
    slot_gap = 14
    slot_w = (width - 2 * 58 - 4 * slot_gap) // 5
    slot_h = 482
    for index in range(5):
        number = index + 1
        row = rounds_by_no.get(number)
        x = 58 + index * (slot_w + slot_gap)
        _painel_cartao(draw, (x, start_y, x + slot_w, start_y + slot_h),
                       fill=(12, 19, 29, 242), outline=(104, 119, 136, 100), radius=16)
        draw.text((x + 16, start_y + 15), f"RODADA {number:02d}", font=_font(13, True), fill=(222, 197, 150, 255))
        if row:
            card_a = map_a.get(str(row.get("card_a_id", ""))) or {
                "id": row.get("card_a_id", f"a{number}"), "nome": row.get("card_a_name", "Carta A"),
                "categoria": "Magia", "raridade": "Comum", "tipo": "Magia", "poder": row.get("power_a", 0), "custo": 0,
            }
            card_b = map_b.get(str(row.get("card_b_id", ""))) or {
                "id": row.get("card_b_id", f"b{number}"), "nome": row.get("card_b_name", "Carta B"),
                "categoria": "Magia", "raridade": "Comum", "tipo": "Magia", "poder": row.get("power_b", 0), "custo": 0,
            }
            mini_w, mini_h = 112, 166
            mini_y = start_y + 51
            xa, xb = x + 15, x + slot_w - 15 - mini_w
            art_a = _draw_card(card_a).resize((mini_w, mini_h), Image.Resampling.LANCZOS)
            art_b = _draw_card(card_b).resize((mini_w, mini_h), Image.Resampling.LANCZOS)
            image.paste(art_a, (xa, mini_y))
            image.paste(art_b, (xb, mini_y))
            draw = ImageDraw.Draw(image, "RGBA")
            _text_center(draw, (x + slot_w // 2, mini_y + 78), "VS", _font(15, True), (235, 216, 172, 255))
            # Nomes e poderes dos dois lados.
            draw.text((x + 12, mini_y + mini_h + 12), _texto_ajustado(draw, row.get("card_a_name", card_a.get("nome")), slot_w // 2 - 17, 11, True, 18),
                      font=_font(11, True), fill=(139, 218, 185, 255))
            draw.text((x + 12, mini_y + mini_h + 31), f"PODER {int(row.get('power_a', 0) or 0)}", font=_font(10, True), fill=(181, 193, 202, 255))
            draw.text((x + slot_w // 2 + 4, mini_y + mini_h + 12), _texto_ajustado(draw, row.get("card_b_name", card_b.get("nome")), slot_w // 2 - 17, 11, True, 18),
                      font=_font(11, True), fill=(231, 154, 149, 255))
            draw.text((x + slot_w // 2 + 4, mini_y + mini_h + 31), f"PODER {int(row.get('power_b', 0) or 0)}", font=_font(10, True), fill=(181, 193, 202, 255))
            winner = str(row.get("winner_side", "empate"))
            result_label = "EMPATE" if winner == "empate" else "PONTO PARA A" if winner == "a" else "PONTO PARA B"
            result_color = (177, 180, 188) if winner == "empate" else (87, 202, 153) if winner == "a" else (222, 122, 116)
            draw.rounded_rectangle((x + 13, start_y + 330, x + slot_w - 13, start_y + 370), radius=10,
                                   fill=(*result_color, 31), outline=(*result_color, 150), width=1)
            _text_center(draw, (x + slot_w // 2, start_y + 350), result_label, _font(11, True), (*result_color, 255))
            narration = str(row.get("narration", ""))
            for line_no, line in enumerate(_wrap(draw, narration, _font(10), slot_w - 30)[:3]):
                _text_center(draw, (x + slot_w // 2, start_y + 405 + line_no * 16), line, _font(10), (165, 176, 188, 240))
        else:
            accent = (217, 178, 104) if status == "active" and number == current_round else (84, 102, 121)
            mini_w, mini_h = 104, 154
            mini_y = start_y + 81
            backs = [_card_back((mini_w, mini_h), number, accent), _card_back((mini_w, mini_h), number, accent)]
            image.paste(backs[0], (x + 18, mini_y), backs[0])
            image.paste(backs[1], (x + slot_w - 18 - mini_w, mini_y), backs[1])
            draw = ImageDraw.Draw(image, "RGBA")
            _text_center(draw, (x + slot_w // 2, mini_y + 76), "VS", _font(14, True), (216, 196, 156, 245))
            if status == "active" and number == current_round:
                label = f"{int(picks_count)}/2 ESCOLHAS TRAVADAS"
            elif status == "invited":
                label = "AGUARDANDO ACEITE"
            else:
                label = "AGUARDANDO RODADA"
            for line_no, line in enumerate(_wrap(draw, label, _font(12, True), slot_w - 26)[:2]):
                _text_center(draw, (x + slot_w // 2, start_y + 304 + line_no * 19), line, _font(12, True), (*accent, 255))
            _text_center(draw, (x + slot_w // 2, start_y + 382), "CARTAS OCULTAS", _font(10, True), (127, 145, 163, 230))

    # Faixa de desfecho: o resultado de cada duelo fica explícito e não se mistura ao histórico.
    footer_y = height - 69
    if status == "finished":
        winner_id = duel.get("winner_id")
        if winner_id is None:
            outcome = f"EMPATE  ·  {nome_a} {wins_a} × {wins_b} {nome_b}  ·  APOSTAS DEVOLVIDAS"
            outcome_color = (177, 182, 191)
        elif int(winner_id) == int(duel.get("creator_id", 0)):
            lucro = int(duel.get("payout", 0) or 0) - aposta
            outcome = (
                f"VENCEDOR: {nome_a}  ·  PRÊMIO {int(duel.get('payout', 0) or 0):,}  ·  "
                f"LUCRO +{lucro:,}  ·  {int(duel.get('burned', 0) or 0):,} REMOVIDOS"
            )
            outcome_color = (102, 218, 164)
        else:
            lucro = int(duel.get("payout", 0) or 0) - aposta
            outcome = (
                f"VENCEDOR: {nome_b}  ·  PRÊMIO {int(duel.get('payout', 0) or 0):,}  ·  "
                f"LUCRO +{lucro:,}  ·  {int(duel.get('burned', 0) or 0):,} REMOVIDOS"
            )
            outcome_color = (237, 153, 130)
    elif status == "active":
        outcome = f"RODADA {current_round}/5  ·  {int(picks_count)}/2 ESCOLHAS RECEBIDAS  ·  {int(tempo_rodada)} SEGUNDOS POR ESCOLHA"
        outcome_color = (222, 184, 108)
    elif status == "invited":
        outcome = f"CONVITE ABERTO  ·  {aposta:,} DENÁRIOS POR JOGADOR  ·  POTE {pote:,}"
        outcome_color = (222, 184, 108)
    elif status == "expired":
        outcome = "CONVITE EXPIRADO  ·  NENHUMA APOSTA FOI DEBITADA"
        outcome_color = (158, 168, 181)
    else:
        outcome = "PARTIDA ENCERRADA  ·  CONFIRA O HISTÓRICO DESTA FICHA"
        outcome_color = (158, 168, 181)
    _text_center(draw, (width // 2, footer_y), outcome, _font(16, True), (*outcome_color, 255))

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=False)
    output.seek(0)
    return output


def render_arena_dashboard_bytes(display_name: str, stats: dict[str, Any], resumos: list[dict[str, Any]]) -> io.BytesIO:
    """Painel gráfico pessoal com estatísticas, partidas em andamento e resultados individuais."""
    width, height = 1500, 940
    image, draw = _painel_arena_base(width, height, "PERSONAL DUEL DASHBOARD")
    draw.text((60, 111), _texto_ajustado(draw, display_name, 650, 32, True, 32),
              font=_font(32, True), fill=(245, 239, 224, 255))
    draw.text((62, 153), "SEU DESEMPENHO NO COLISEU", font=_font(13, True), fill=(149, 166, 184, 255))

    total = int(stats.get("partidas", 0) or 0)
    wins = int(stats.get("vitorias", 0) or 0)
    losses = int(stats.get("derrotas", 0) or 0)
    draws = int(stats.get("empates", 0) or 0)
    balance = int(stats.get("saldo_liquido", 0) or 0)
    win_rate = (wins / total * 100) if total else 0
    metrics = [
        ("VITÓRIAS", wins, (91, 202, 152)),
        ("DERROTAS", losses, (220, 119, 112)),
        ("EMPATES", draws, (171, 178, 190)),
        ("PARTIDAS", total, (214, 182, 117)),
        ("APROVEITAMENTO", f"{win_rate:.0f}%", (117, 174, 219)),
    ]
    metric_y, metric_h, metric_gap = 205, 112, 14
    metric_w = (width - 120 - 4 * metric_gap) // 5
    for index, (label, value, accent) in enumerate(metrics):
        x = 60 + index * (metric_w + metric_gap)
        _painel_cartao(draw, (x, metric_y, x + metric_w, metric_y + metric_h),
                       fill=(17, 26, 39, 245), outline=(*accent, 130), radius=16)
        draw.text((x + 20, metric_y + 17), label, font=_font(11, True), fill=(161, 174, 188, 255))
        draw.text((x + 20, metric_y + 45), str(value), font=_font(31, True), fill=(*accent, 255))

    _painel_cartao(draw, (60, 345, width - 60, 480), fill=(17, 25, 38, 245), outline=(204, 166, 96, 125))
    draw.text((86, 365), "SALDO LÍQUIDO DAS PARTIDAS", font=_font(13, True), fill=(174, 184, 193, 255))
    balance_color = (100, 218, 161) if balance >= 0 else (232, 123, 116)
    draw.text((86, 397), f"{balance:+,} DENÁRIOS", font=_font(33, True), fill=(*balance_color, 255))
    draw.text((790, 404), "O resultado financeiro é calculado por partida e permanece salvo no histórico.",
              font=_font(14), fill=(162, 175, 188, 255))

    ativos = [x for x in resumos if x.get("duel", {}).get("status") in {"invited", "active"}]
    concluidos = [x for x in resumos if x.get("duel", {}).get("status") in {"finished", "cancelled", "expired"}]
    section_y = 520
    draw.text((65, section_y), "PARTIDAS ATIVAS", font=_font(17, True), fill=(221, 196, 147, 255))
    draw.text((width - 90, section_y + 4), f"{len(ativos)} EM ABERTO", font=_font(11, True), fill=(140, 161, 178, 255), anchor="ra")
    row_y = section_y + 39
    if not ativos:
        _painel_cartao(draw, (60, row_y, width - 60, row_y + 64), fill=(12, 20, 30, 220), outline=(88, 107, 127, 95), radius=12)
        draw.text((84, row_y + 21), "Nenhum confronto em andamento. Inicie um novo desafio para entrar na arena.",
                  font=_font(14), fill=(153, 168, 182, 255))
        row_y += 78
    else:
        for resumo in ativos[:3]:
            d = resumo.get("duel", {})
            _painel_cartao(draw, (60, row_y, width - 60, row_y + 61), fill=(12, 20, 31, 238), outline=(87, 139, 132, 115), radius=12)
            rival = str(resumo.get("label", "Confronto")).split("·", 1)[-1].strip()
            title = f"#{int(d.get('id', 0)):04d}   VS   {rival}"
            description = str(resumo.get("active_line", "Partida ativa")).replace("**", "").replace("`", "").replace("*", "")
            draw.text((83, row_y + 9), _texto_ajustado(draw, title, 950, 14, True, 70), font=_font(14, True), fill=(230, 235, 232, 255))
            draw.text((83, row_y + 34), _texto_ajustado(draw, description, 1200, 11, False, 145), font=_font(11), fill=(150, 173, 184, 255))
            row_y += 69

    recent_y = max(row_y + 9, 785)
    draw.text((65, recent_y), "RESULTADOS RECENTES", font=_font(17, True), fill=(221, 196, 147, 255))
    recent_y += 36
    if not concluidos:
        draw.text((83, recent_y + 8), "As fichas individuais aparecerão aqui após a conclusão dos duelos.",
                  font=_font(13), fill=(153, 168, 182, 255))
    else:
        recent = concluidos[:3]
        col_gap = 13
        col_w = (width - 120 - 2 * col_gap) // 3
        for index, resumo in enumerate(recent):
            x = 60 + index * (col_w + col_gap)
            _painel_cartao(draw, (x, recent_y, x + col_w, recent_y + 82), fill=(14, 22, 33, 245), outline=(133, 116, 87, 110), radius=12)
            result = str(resumo.get("result_line", "Partida concluída")).replace("**", "").replace("`", "").replace("*", "")
            draw.text((x + 16, recent_y + 13), _texto_ajustado(draw, result, col_w - 32, 12, True, 56),
                      font=_font(12, True), fill=(229, 224, 210, 255))
            draw.text((x + 16, recent_y + 47), str(resumo.get("description", "Ficha individual"))[:64],
                      font=_font(10), fill=(157, 171, 184, 255))

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=False)
    output.seek(0)
    return output


def render_duel_locked_card_bytes(card: dict[str, Any], duel_id: int, round_no: int) -> io.BytesIO:
    """Confirma visualmente a carta travada sem revelar a escolha ao adversário."""
    card_image = _draw_card(card).convert("RGBA")
    width, height = card_image.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    # Faixa opaca e selo de bloqueio: mantém a arte reconhecível apenas para o dono.
    draw.rectangle((0, int(height * .39), width, int(height * .61)), fill=(6, 11, 18, 225))
    draw.line((0, int(height * .39), width, int(height * .39)), fill=(224, 184, 107, 230), width=3)
    draw.line((0, int(height * .61), width, int(height * .61)), fill=(224, 184, 107, 230), width=3)
    _text_center(draw, (width // 2, int(height * .455)), "CARTA TRAVADA", _font(29, True), (249, 226, 180, 255))
    _text_center(draw, (width // 2, int(height * .52)), f"DUELO #{int(duel_id)}  ·  RODADA {int(round_no)}/5",
                 _font(14, True), (189, 204, 219, 255))
    card_image.alpha_composite(overlay)
    output = io.BytesIO()
    card_image.convert("RGB").save(output, format="PNG", optimize=False)
    output.seek(0)
    return output
