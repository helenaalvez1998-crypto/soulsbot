"""Renderizador local de cartas: arte geométrica original, sem assets de terceiros."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from runtime_paths import get_data_dir
from .cartas import EMOJIS_TIPO, VERSAO_ARTES

CORES_RARIDADE = {
    "Comum": ((32, 37, 45), (116, 130, 146)),
    "Rara": ((20, 46, 69), (70, 157, 205)),
    "Épica": ((48, 27, 72), (166, 100, 220)),
    "Lendária": ((70, 43, 15), (231, 183, 67)),
}
SIMBOLOS = {"Destreza": "✥", "Força": "⚔", "Magia": "✧"}


def _font(size: int, bold: bool = False):
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root / "fonts" / "DejaVuSans-Bold.ttf" if bold else root / "fonts" / "DejaVuSans.ttf",
        root / "fonts" / "DejaVuSans.ttf",
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = str(text).split()
    lines: list[str] = []
    atual = ""
    for word in words:
        tentativa = f"{atual} {word}".strip()
        if draw.textbbox((0, 0), tentativa, font=font)[2] <= max_width:
            atual = tentativa
        else:
            if atual:
                lines.append(atual)
            atual = word
    if atual:
        lines.append(atual)
    return lines or [""]


def _draw_card(card: dict[str, Any], width: int = 360, height: int = 500) -> Image.Image:
    rarity = str(card.get("raridade", "Comum"))
    base, accent = CORES_RARIDADE.get(rarity, CORES_RARIDADE["Comum"])
    image = Image.new("RGB", (width, height), (10, 12, 16))
    px = image.load()
    for y in range(height):
        frac = y / max(height - 1, 1)
        color = tuple(int(base[i] * (1 - frac) + (8, 10, 15)[i] * frac) for i in range(3))
        for x in range(width):
            px[x, y] = color
    draw = ImageDraw.Draw(image, "RGBA")
    # Moldura e ornamentos em camadas.
    draw.rounded_rectangle((7, 7, width - 8, height - 8), radius=22, outline=(*accent, 230), width=6)
    draw.rounded_rectangle((18, 18, width - 19, height - 19), radius=17, outline=(255, 255, 255, 55), width=2)
    for inset in range(0, 4):
        margin = 45 + inset * 15
        draw.arc((margin, 90 + margin // 3, width - margin, 380 - margin // 3), 190, 350, fill=(*accent, 55), width=2)
    cx, cy = width // 2, 235
    for radius, alpha, stroke in ((112, 28, 5), (86, 34, 3), (60, 55, 2)):
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(*accent, alpha), width=stroke)
    symbol = SIMBOLOS.get(str(card.get("tipo")), "✦")
    symbol_font = _font(118, True)
    bbox = draw.textbbox((0, 0), symbol, font=symbol_font)
    draw.text((cx - (bbox[2] - bbox[0]) / 2, cy - (bbox[3] - bbox[1]) / 2 - 4), symbol,
              font=symbol_font, fill=(*accent, 230), stroke_width=1, stroke_fill=(255, 255, 255, 80))

    title_font = _font(25, True)
    small = _font(16)
    body = _font(17)
    title = str(card.get("nome", "Carta"))
    lines = _wrap(draw, title, title_font, width - 46)[:2]
    y = 345
    for line in lines:
        box = draw.textbbox((0, 0), line, font=title_font)
        draw.text(((width - (box[2] - box[0])) / 2, y), line, font=title_font, fill=(245, 240, 225, 255))
        y += 31
    draw.text((25, 420), f"{rarity.upper()}  ·  {card.get('categoria', 'Carta').upper()}", font=small, fill=(*accent, 255))
    draw.text((25, 447), f"{EMOJIS_TIPO.get(card.get('tipo'), '✦')} {card.get('tipo')}  ·  Poder {card.get('poder')}  ·  Custo {card.get('custo')}",
              font=body, fill=(238, 238, 238, 255))
    draw.line((24, 412, width - 24, 412), fill=(*accent, 130), width=2)
    return image


def _cache_path(payload: Any, suffix: str) -> Path:
    root = get_data_dir() / "cartas_cache"
    root.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{VERSAO_ARTES}:{raw}".encode("utf-8")).hexdigest()[:24]
    return root / f"{digest}.{suffix}"


def render_carta(card: dict[str, Any]) -> Path:
    path = _cache_path(card, "png")
    if not path.exists():
        _draw_card(card).save(path, format="PNG", optimize=True)
    return path


def render_pacote(cards: list[dict[str, Any]]) -> Path:
    payload = {"cards": cards, "layout": "pack-3"}
    path = _cache_path(payload, "png")
    if path.exists():
        return path
    card_w, card_h, gap = 330, 458, 18
    canvas = Image.new("RGB", (card_w * 3 + gap * 4, card_h + gap * 2), (10, 12, 16))
    for index, card in enumerate(cards[:3]):
        art = _draw_card(card, card_w, card_h)
        canvas.paste(art, (gap + index * (card_w + gap), gap))
    canvas.save(path, format="PNG", optimize=True)
    return path
