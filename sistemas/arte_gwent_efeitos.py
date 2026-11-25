"""Efeitos visuais procedurais do Gwent.

- ``desenhar_aura_unidade``: camada que torna visível, na ilustração, a habilidade da unidade
  (escudo, vingança, ressurgir, devorar, sobrevivente, espólios).
- ``desenhar_emblema_especial``: um emblema próprio para cada carta especial, no lugar do losango
  genérico, para que o efeito seja reconhecível só de olhar.

Tudo é vetorial, determinístico (depende só da habilidade e da semente da carta) e não usa
arquivos externos. Habilidades sem desenho próprio devolvem ``False`` e a arte segue como antes.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

BRASA = (238, 98, 52)
OURO = (240, 203, 112)
ALMA = (190, 235, 255)
PEDRA = (92, 88, 96)
SANGUE = (206, 62, 66)


def _w(aw: int, valor: float) -> int:
    """Espessura de linha proporcional ao tamanho da arte (base 384 px)."""
    return max(1, int(round(valor * aw / 384)))


def _rng(habilidade: str, seed: int) -> random.Random:
    return random.Random(f"{habilidade}:{seed}")


def _brilho(d: ImageDraw.ImageDraw, cx: int, cy: int, raio: int, cor, alfa_max: int = 70) -> None:
    for i in range(6, 0, -1):
        r = int(raio * i / 6)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*cor, int(alfa_max * (7 - i) / 7)))


# --------------------------------------------------------------------------- unidades
def _camada(art: Image.Image):
    """Camada transparente própria: no Pillow, desenhar com alfa direto numa imagem RGBA
    *substitui* o pixel (vira buraco translúcido). Desenhando numa camada e compondo, o alfa mistura."""
    camada = Image.new("RGBA", art.size, (0, 0, 0, 0))
    return camada, ImageDraw.Draw(camada)


def desenhar_aura_unidade(art: Image.Image, habilidade: str, aw: int, ah: int, cx: int,
                          chao: int, accent, metal, seed: int) -> bool:
    """`chao` deve ser a linha de chão VISÍVEL (o painel do rodapé cobre o fim da arte)."""
    desenho = _AURAS.get(habilidade)
    if desenho is None:
        return False
    camada, d = _camada(art)
    desenho(d, aw, ah, cx, chao, accent, metal, _rng(habilidade, seed))
    art.alpha_composite(camada)
    return True


def _aura_escudo(d, aw, ah, cx, chao, accent, metal, rng):
    x1, y1, x2, y2 = cx - int(aw * .30), int(ah * .17), cx + int(aw * .30), chao + int(ah * .01)
    d.ellipse((x1, y1, x2, y2), fill=(*accent, 26), outline=(*metal, 175), width=_w(aw, 3))
    passo = max(14, int(aw * .075))
    for gy in range(y1 + passo, y2 - passo // 2, int(passo * .87)):
        desloc = passo // 2 if ((gy - y1) // int(passo * .87)) % 2 else 0
        for gx in range(x1 + passo + desloc, x2 - passo // 2, passo):
            nx, ny = (gx - (x1 + x2) / 2) / ((x2 - x1) / 2), (gy - (y1 + y2) / 2) / ((y2 - y1) / 2)
            if nx * nx + ny * ny < .80:
                pts = [(gx + math.cos(math.radians(60 * k + 30)) * passo * .46,
                        gy + math.sin(math.radians(60 * k + 30)) * passo * .46) for k in range(6)]
                d.polygon(pts, outline=(*metal, 70))
    d.arc((x1 + 6, y1 + 6, x2 - 6, y2 - 6), 200, 262, fill=(255, 255, 255, 215), width=_w(aw, 4))


def _aura_vinganca(d, aw, ah, cx, chao, accent, metal, rng):
    _brilho(d, cx, chao, int(aw * .30), BRASA, 60)
    for i in range(9):
        bx = cx + int((i - 4) * aw * .062)
        alt = int(ah * rng.uniform(.07, .17))
        d.polygon([(bx - _w(aw, 8), chao), (bx + rng.randint(-5, 5), chao - alt), (bx + _w(aw, 8), chao)],
                  fill=(*BRASA, rng.randint(115, 175)))
    for _ in range(34):
        px, py = cx + rng.randint(-int(aw * .27), int(aw * .27)), rng.randint(int(ah * .25), chao)
        r = rng.choice((1, 2, 2, 3))
        d.ellipse((px - r, py - r, px + r, py + r), fill=(255, rng.randint(120, 190), 70, rng.randint(110, 225)))
    for k in range(4):
        x0 = cx + (k - 2) * int(aw * .09)
        d.line((x0, chao, x0 + rng.randint(-14, 14), chao + int(ah * .035)), fill=(255, 150, 80, 190), width=_w(aw, 2))


def _aura_ressurgir(d, aw, ah, cx, chao, accent, metal, rng):
    _brilho(d, cx, chao, int(aw * .26), ALMA, 40)
    for k in range(6):
        x0 = cx + int((k - 2.5) * aw * .085)
        fase = rng.uniform(0, math.tau)
        pts = [(x0 + math.sin(fase + t * 7.5) * aw * .018 * (1 + t * 2), chao - int(t * ah * rng.uniform(.5, .72)))
               for t in [i / 22 for i in range(23)]]
        for i in range(len(pts) - 1):
            d.line((*pts[i], *pts[i + 1]), fill=(*ALMA, int(150 * (1 - i / 24))), width=_w(aw, 3))
    for _ in range(7):
        ox, oy = cx + rng.randint(-int(aw * .26), int(aw * .26)), rng.randint(int(ah * .18), int(ah * .72))
        r = rng.randint(max(3, int(aw * .012)), max(5, int(aw * .024)))
        _brilho(d, ox, oy, r * 3, ALMA, 85)
        d.ellipse((ox - r, oy - r, ox + r, oy + r), fill=(235, 250, 255, 230))


def _aura_devorar(d, aw, ah, cx, chao, accent, metal, rng):
    rx, ry = int(aw * .40), int(ah * .075)
    cy = chao - int(ah * .005)
    d.ellipse((cx - rx - 14, cy - ry - 10, cx + rx + 14, cy + ry + 10), fill=(*accent, 40))
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(5, 1, 9, 240), outline=(*accent, 255), width=_w(aw, 3))
    d.ellipse((cx - rx * .62, cy - ry * .6, cx + rx * .62, cy + ry * .6), fill=(120, 20, 60, 120))
    n = 22
    for k in range(n):
        ang = math.tau * k / n
        px, py = cx + math.cos(ang) * rx, cy + math.sin(ang) * ry
        ix, iy = cx + math.cos(ang) * rx * .66, cy + math.sin(ang) * ry * .40
        lado = math.tau / (n * 2.6)
        d.polygon([(cx + math.cos(ang - lado) * rx, cy + math.sin(ang - lado) * ry), (ix, iy),
                   (cx + math.cos(ang + lado) * rx, cy + math.sin(ang + lado) * ry)],
                  fill=(244, 238, 232, 250), outline=(*accent, 200))
    for lado in (-1, 1):
        for k in range(4):
            y0 = cy - int(ah * .014 * k)
            x0 = cx + lado * (rx - int(aw * .02 * k))
            d.line((x0, y0, x0 + lado * int(aw * (.05 + .02 * k)), y0 - int(ah * (.07 + .04 * k))),
                   fill=(70, 22, 84, 230), width=_w(aw, 4))


def _aura_sobrevivente(d, aw, ah, cx, chao, accent, metal, rng):
    topo = int(ah * .04)
    d.polygon([(cx - int(aw * .08), topo), (cx + int(aw * .08), topo),
               (cx + int(aw * .30), chao), (cx - int(aw * .30), chao)], fill=(*OURO, 30))
    for lado in (-1, 1):
        px = cx + lado * int(aw * .31)
        alt = int(ah * rng.uniform(.20, .30))
        l = _w(aw, 14)
        d.polygon([(px - l, chao), (px - l, chao - alt), (px + l * lado, chao - alt - int(ah * .04)), (px + l, chao - alt + int(ah * .03)), (px + l, chao)],
                  fill=(*PEDRA, 235), outline=(*metal, 150))
        for _ in range(3):
            rx = px + rng.randint(-int(aw * .06), int(aw * .06))
            d.polygon([(rx, chao), (rx + 8, chao - 9), (rx + 17, chao)], fill=(*PEDRA, 225))
    rx, ry = int(aw * .26), int(ah * .04)
    d.ellipse((cx - rx, chao - ry, cx + rx, chao + ry), outline=(*OURO, 205), width=_w(aw, 3))
    for k in range(8):
        ang = math.tau * k / 8
        d.line((cx + math.cos(ang) * rx * .72, chao + math.sin(ang) * ry * .72,
                cx + math.cos(ang) * rx * .95, chao + math.sin(ang) * ry * .95), fill=(*OURO, 220), width=_w(aw, 3))


def _aura_espolios(d, aw, ah, cx, chao, accent, metal, rng):
    _brilho(d, cx, chao - int(ah * .02), int(aw * .24), OURO, 38)
    bx, by, bw, bh = cx + int(aw * .17), chao - int(ah * .085), int(aw * .15), int(ah * .075)
    d.rectangle((bx, by, bx + bw, by + bh), fill=(86, 52, 30, 245), outline=(*OURO, 235), width=_w(aw, 2))
    d.pieslice((bx, by - bh // 2, bx + bw, by + bh // 2 + 2), 180, 360, fill=(104, 66, 38, 245), outline=(*OURO, 235))
    d.rectangle((bx + bw // 2 - 3, by - 2, bx + bw // 2 + 3, by + 9), fill=(*OURO, 255))
    for _ in range(15):
        px = cx + rng.randint(-int(aw * .27), int(aw * .24))
        py = chao - rng.randint(0, int(ah * .05))
        r = rng.randint(max(3, int(aw * .014)), max(5, int(aw * .022)))
        d.ellipse((px - r, py - r // 2, px + r, py + r // 2 + 1), fill=(*OURO, 245), outline=(150, 105, 40, 255))
        d.ellipse((px - r // 2, py - r // 4, px + r // 3, py + r // 6), fill=(255, 238, 170, 230))
    for _ in range(6):
        px, py = cx + rng.randint(-int(aw * .22), int(aw * .30)), rng.randint(int(ah * .5), chao - int(ah * .06))
        d.line((px - 4, py, px + 4, py), fill=(255, 245, 200, 200), width=1)
        d.line((px, py - 4, px, py + 4), fill=(255, 245, 200, 200), width=1)


_AURAS = {
    "escudo_ferro": _aura_escudo, "vinganca": _aura_vinganca, "ressurgir": _aura_ressurgir,
    "devorar": _aura_devorar, "sobrevivente": _aura_sobrevivente, "espolios": _aura_espolios,
}


# --------------------------------------------------------------------------- especiais
def desenhar_emblema_especial(art: Image.Image, habilidade: str, aw: int, ah: int,
                              accent, metal, seed: int) -> bool:
    desenho = _EMBLEMAS.get(habilidade)
    if desenho is None:
        return False
    camada, d = _camada(art)
    cx, cy = aw // 2, int(ah * .44)  # um pouco acima do centro: o rodapé cobre a base da arte
    R = int(min(aw, ah) * .29)
    _brilho(d, cx, cy, int(R * 1.5), accent, 60)
    desenho(d, cx, cy, R, aw, accent, metal, _rng(habilidade, seed))
    art.alpha_composite(camada)
    return True


def _em_nevoa(d, cx, cy, R, aw, accent, metal, rng):
    for i in range(5):
        y = cy - int(R * .85) + int(i * R * .42)
        for k in range(7):
            x = cx - int(R * 1.15) + int(k * R * .38) + (i % 2) * int(R * .19)
            rx, ry = int(R * .34), int(R * .17)
            d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=(*metal, 48 + (i % 3) * 14))
    d.ellipse((cx - R // 4, cy - R // 4, cx + R // 4, cy + R // 4), outline=(*metal, 160), width=_w(aw, 2))


def _em_geada(d, cx, cy, R, aw, accent, metal, rng):
    gelo = (196, 232, 255)
    for k in range(6):
        a = math.radians(60 * k - 90)
        ex, ey = cx + math.cos(a) * R, cy + math.sin(a) * R
        d.line((cx, cy, ex, ey), fill=(*gelo, 245), width=_w(aw, 5))
        for f in (.45, .72):
            bx, by = cx + math.cos(a) * R * f, cy + math.sin(a) * R * f
            for s in (-1, 1):
                b = a + s * math.radians(42)
                d.line((bx, by, bx + math.cos(b) * R * .28, by + math.sin(b) * R * .28), fill=(*gelo, 230), width=_w(aw, 3))
        d.ellipse((ex - 5, ey - 5, ex + 5, ey + 5), fill=(255, 255, 255, 240))
    d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=(255, 255, 255, 250), outline=(*gelo, 255))


def _em_chuva(d, cx, cy, R, aw, accent, metal, rng):
    nuvem = (96, 106, 134)
    for ox, oy, r in ((-.55, .02, .42), (0, -.18, .55), (.55, .02, .42), (-.2, .1, .4), (.3, .1, .4)):
        x, y, rr = cx + ox * R, cy - R * .52 + oy * R, r * R
        d.ellipse((x - rr, y - rr * .78, x + rr, y + rr * .78), fill=(*nuvem, 245), outline=(*metal, 150))
    for k in range(15):
        x = cx - R * .95 + k * R * .135 + rng.randint(-4, 4)
        y = cy + rng.randint(-int(R * .05), int(R * .30))
        d.line((x, y, x - R * .12, y + R * .42), fill=(150, 190, 240, rng.randint(170, 240)), width=_w(aw, 3))


def _em_chifre(d, cx, cy, R, aw, accent, metal, rng):
    cor, oc, banda = (216, 176, 96), (255, 232, 170), (150, 98, 40)
    p0, p1, p2 = (cx - R * .98, cy + R * .62), (cx + R * .20, cy + R * .86), (cx + R * .80, cy - R * .70)

    def ponto(t):
        return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])

    def tangente(t):
        tx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
        ty = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
        n = math.hypot(tx, ty) or 1
        return tx / n, ty / n

    lado_a, lado_b = [], []
    for k in range(41):
        t = k / 40
        x, y = ponto(t)
        tx, ty = tangente(t)
        larg = R * (.07 + .34 * t ** 1.9)
        lado_a.append((x - ty * larg, y + tx * larg))
        lado_b.append((x + ty * larg, y - tx * larg))
    d.polygon(lado_a + lado_b[::-1], fill=(*cor, 248), outline=(*oc, 255))
    for t in (.22, .5, .76):
        x, y = ponto(t)
        tx, ty = tangente(t)
        larg = R * (.07 + .34 * t ** 1.9) * 1.12
        d.line((x - ty * larg, y + tx * larg, x + ty * larg, y - tx * larg), fill=(*banda, 255), width=_w(aw, 6))
    bx, by = ponto(1.0)
    tx, ty = tangente(1.0)
    larg = R * .41
    d.ellipse((bx - larg * .55, by - larg * .55, bx + larg * .55, by + larg * .55), fill=(70, 42, 20, 255), outline=(*oc, 255), width=_w(aw, 3))
    bx0, by0 = ponto(0.0)
    d.ellipse((bx0 - R * .1, by0 - R * .1, bx0 + R * .1, by0 + R * .1), fill=(*banda, 255), outline=(*oc, 255), width=_w(aw, 2))
    ang = math.degrees(math.atan2(ty, tx))
    for k in range(1, 4):
        rr = R * (.34 + .24 * k)
        ox, oy = bx + tx * R * .05, by + ty * R * .05
        d.arc((ox - rr, oy - rr, ox + rr, oy + rr), ang - 38, ang + 38, fill=(*oc, 235 - k * 45), width=_w(aw, 4))


def _em_medico(d, cx, cy, R, aw, accent, metal, rng):
    verde = (120, 222, 150)
    a, b = int(R * .32), int(R * .95)
    d.rounded_rectangle((cx - a, cy - b, cx + a, cy + b), radius=a // 2, fill=(*verde, 235), outline=(*metal, 255), width=_w(aw, 3))
    d.rounded_rectangle((cx - b, cy - a, cx + b, cy + a), radius=a // 2, fill=(*verde, 235), outline=(*metal, 255), width=_w(aw, 3))
    d.rectangle((cx - a + 3, cy - a + 3, cx + a - 3, cy + a - 3), fill=(*verde, 235))
    for s in (-1, 1):
        d.polygon([(cx + s * b * .55, cy + b * .78), (cx + s * b * 1.05, cy + b * .5), (cx + s * b * .9, cy + b * .95)],
                  fill=(70, 160, 100, 225), outline=(*metal, 200))


def _em_queima(d, cx, cy, R, aw, accent, metal, rng):
    def chama(esc, cor, oc):
        pts = [(0, -1.05), (.22, -.62), (.42, -.78), (.58, -.2), (.82, -.34), (.78, .35), (.5, .8), (0, 1.0),
               (-.5, .8), (-.78, .35), (-.74, -.12), (-.5, -.02), (-.4, -.55), (-.18, -.5)]
        d.polygon([(cx + x * R * esc, cy + y * R * esc) for x, y in pts], fill=(*cor, 245), outline=(*oc, 255))
    chama(1.0, (222, 76, 38), (255, 170, 90))
    chama(.66, (250, 160, 52), (255, 220, 120))
    chama(.34, (255, 232, 140), (255, 250, 210))


def _em_purificar(d, cx, cy, R, aw, accent, metal, rng):
    for k in range(16):
        a = math.tau * k / 16
        r1, r2 = R * .5, R * (1.05 if k % 2 == 0 else .82)
        d.line((cx + math.cos(a) * r1, cy + math.sin(a) * r1, cx + math.cos(a) * r2, cy + math.sin(a) * r2),
               fill=(255, 238, 180, 235), width=_w(aw, 5 if k % 2 == 0 else 3))
    d.ellipse((cx - R * .46, cy - R * .46, cx + R * .46, cy + R * .46), fill=(255, 244, 205, 245), outline=(*metal, 255), width=_w(aw, 3))
    d.ellipse((cx - R * .28, cy - R * .28, cx + R * .28, cy + R * .28), outline=(240, 200, 120, 255), width=_w(aw, 2))


def _em_execucao(d, cx, cy, R, aw, accent, metal, rng):
    aco = (214, 220, 226)
    d.polygon([(cx - R * .12, cy - R * 1.05), (cx + R * .12, cy - R * 1.05), (cx + R * .09, cy + R * .45),
               (cx, cy + R * .62), (cx - R * .09, cy + R * .45)], fill=(*aco, 250), outline=(*metal, 255))
    d.line((cx, cy - R * .95, cx, cy + R * .45), fill=(150, 156, 164, 255), width=_w(aw, 2))
    d.rounded_rectangle((cx - R * .5, cy + R * .5, cx + R * .5, cy + R * .64), radius=4, fill=(*SANGUE, 255), outline=(*metal, 255))
    d.rectangle((cx - R * .06, cy + R * .64, cx + R * .06, cy + R * 1.05), fill=(90, 58, 40, 255), outline=(*metal, 200))
    d.line((cx - R * .85, cy - R * .62, cx + R * .85, cy + R * .15), fill=(*SANGUE, 235), width=_w(aw, 6))
    d.line((cx + R * .85, cy - R * .62, cx - R * .85, cy + R * .15), fill=(*SANGUE, 235), width=_w(aw, 6))


def _em_vinculo(d, cx, cy, R, aw, accent, metal, rng):
    for ox in (-.34, .34):
        x = cx + ox * R
        d.ellipse((x - R * .52, cy - R * .52, x + R * .52, cy + R * .52), outline=(*metal, 250), width=_w(aw, 9))
        d.ellipse((x - R * .52, cy - R * .52, x + R * .52, cy + R * .52), outline=(*accent, 255), width=_w(aw, 4))
    for oy in (-.95, .95):
        d.ellipse((cx - R * .14, cy + oy * R - R * .22, cx + R * .14, cy + oy * R + R * .22), outline=(*metal, 235), width=_w(aw, 5))


def _em_batedor(d, cx, cy, R, aw, accent, metal, rng):
    topo = [(cx + math.cos(math.radians(a)) * R * 1.05, cy - math.sin(math.radians(a)) * R * .52) for a in range(180, -1, -10)]
    base = [(cx + math.cos(math.radians(a)) * R * 1.05, cy + math.sin(math.radians(a)) * R * .52) for a in range(0, 181, 10)]
    d.polygon(topo + base, fill=(232, 238, 232, 245), outline=(*metal, 255))
    d.ellipse((cx - R * .36, cy - R * .36, cx + R * .36, cy + R * .36), fill=(*accent, 255), outline=(*metal, 255), width=_w(aw, 3))
    d.ellipse((cx - R * .15, cy - R * .15, cx + R * .15, cy + R * .15), fill=(8, 12, 14, 255))
    d.line((cx - R * 1.1, cy + R * .78, cx + R * 1.05, cy - R * .78), fill=(*metal, 255), width=_w(aw, 4))
    d.polygon([(cx + R * 1.12, cy - R * .84), (cx + R * .82, cy - R * .78), (cx + R * 1.02, cy - R * .52)], fill=(*metal, 255))


def _em_muralha(d, cx, cy, R, aw, accent, metal, rng):
    l, t, r, b = cx - R * .95, cy - R * .5, cx + R * .95, cy + R * .95
    d.rectangle((l, t, r, b), fill=(*PEDRA, 250), outline=(*metal, 255), width=_w(aw, 3))
    for k in range(5):
        x = l + k * (r - l) / 4.6
        d.rectangle((x, t - R * .3, x + (r - l) / 8, t), fill=(*PEDRA, 250), outline=(*metal, 255), width=_w(aw, 2))
    for fila in range(4):
        y = t + (fila + 1) * (b - t) / 5
        d.line((l, y, r, y), fill=(*metal, 120), width=1)
        for k in range(1 + fila % 2, 8, 2):
            x = l + k * (r - l) / 8
            d.line((x, y, x, y - (b - t) / 5), fill=(*metal, 110), width=1)
    d.pieslice((cx - R * .26, b - R * .72, cx + R * .26, b - R * .2), 180, 360, fill=(10, 12, 16, 255))
    d.rectangle((cx - R * .26, b - R * .46, cx + R * .26, b), fill=(10, 12, 16, 255))


def _em_egide(d, cx, cy, R, aw, accent, metal, rng):
    def escudo(esc):
        return [(cx - R * .9 * esc, cy - R * .85 * esc), (cx + R * .9 * esc, cy - R * .85 * esc), (cx + R * .86 * esc, cy + R * .1 * esc),
                (cx, cy + R * 1.1 * esc), (cx - R * .86 * esc, cy + R * .1 * esc)]
    d.polygon(escudo(1.0), fill=(*accent, 245), outline=(*OURO, 255), width=_w(aw, 5))
    d.polygon(escudo(.78), fill=(18, 24, 34, 245), outline=(*metal, 255), width=_w(aw, 2))
    d.line((cx, cy - R * .66, cx, cy + R * .84), fill=(*OURO, 255), width=_w(aw, 4))
    d.line((cx - R * .62, cy - R * .12, cx + R * .62, cy - R * .12), fill=(*OURO, 255), width=_w(aw, 4))
    d.ellipse((cx - R * .15, cy - R * .27, cx + R * .15, cy + R * .03), fill=(*OURO, 255))


def _em_requiem(d, cx, cy, R, aw, accent, metal, rng):
    l, r, b, t = cx - R * .55, cx + R * .55, cy + R * .95, cy - R * .25
    d.rectangle((l, t, r, b), fill=(*PEDRA, 250), outline=(*metal, 255), width=_w(aw, 3))
    d.pieslice((l, t - R * .55, r, t + R * .55), 180, 360, fill=(*PEDRA, 250), outline=(*metal, 255), width=_w(aw, 3))
    d.line((cx, cy - R * .22, cx, cy + R * .5), fill=(*ALMA, 255), width=_w(aw, 5))
    d.line((cx - R * .24, cy + R * .06, cx + R * .24, cy + R * .06), fill=(*ALMA, 255), width=_w(aw, 5))
    d.ellipse((cx - R * 1.0, b - R * .1, cx + R * 1.0, b + R * .14), fill=(20, 22, 30, 235))
    for ox, oy, rr in ((-.85, -.55, .15), (.82, -.78, .12), (.62, -.2, .09), (-.6, -.95, .09)):
        x, y = cx + ox * R, cy + oy * R
        _brilho(d, int(x), int(y), int(R * rr * 3), ALMA, 90)
        d.ellipse((x - R * rr, y - R * rr, x + R * rr, y + R * rr), fill=(235, 250, 255, 240))
        d.line((x, y + R * rr, x + R * .06, y + R * (rr + .3)), fill=(*ALMA, 150), width=_w(aw, 2))


def _em_passo(d, cx, cy, R, aw, accent, metal, rng):
    for k, dy in enumerate((-.8, 0, .8)):
        y = cy + dy * R
        d.line((cx - R * 1.05, y, cx + R * 1.05, y), fill=(*metal, 130 + k * 20), width=_w(aw, 4))
    pts = [(cx - R * .62 + R * 1.24 * t / 20 + math.sin(t / 20 * math.pi * 2) * R * .22,
            cy + R * .8 - R * 1.6 * t / 20) for t in range(21)]
    for i in range(len(pts) - 1):
        d.line((*pts[i], *pts[i + 1]), fill=(*accent, 255), width=_w(aw, 6))
    ex, ey = pts[-1]
    d.polygon([(ex, ey - R * .24), (ex - R * .2, ey + R * .08), (ex + R * .2, ey + R * .08)], fill=(*metal, 255), outline=(*accent, 255))
    for fx, fy in ((-.82, .98), (.78, .12)):
        x, y = cx + fx * R, cy + fy * R
        d.ellipse((x - R * .1, y - R * .17, x + R * .1, y + R * .17), fill=(*metal, 215))
        d.ellipse((x - R * .08, y + R * .2, x + R * .08, y + R * .31), fill=(*metal, 215))


_EMBLEMAS = {
    "gwent_nevoa": _em_nevoa, "gwent_geada": _em_geada, "gwent_chuva": _em_chuva, "gwent_chifre": _em_chifre,
    "gwent_medico": _em_medico, "gwent_queima": _em_queima, "gwent_purificar": _em_purificar,
    "gwent_execucao": _em_execucao, "gwent_vinculo": _em_vinculo, "gwent_batedor": _em_batedor,
    "gwent_muralha": _em_muralha, "gwent_egide": _em_egide, "gwent_requiem": _em_requiem, "gwent_passo": _em_passo,
}
