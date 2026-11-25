"""Molduras, emblemas e acabamento visual das cartas do Coliseu (V18).

Tudo é vetorial e desenhado com Pillow, em supersampling (3x) para bordas suaves.
Este módulo cuida somente da *aparência*: não conhece regras, custos ou persistência.

Camadas (de trás para frente):
    1. arte da carta (feita em ``arte_cartas``);
    2. ``aplicar_efeitos_arte``: vinheta, brilho de borda e foil conforme a raridade;
    3. ``construir_overlay``: moldura metálica, placas, medalhão, emblemas e gemas;
    4. textos (desenhados por ``arte_cartas`` na resolução final, para ficar nítidos).

Coordenadas sempre na grade base 420 x 620.
"""
from __future__ import annotations

import functools
import math
import random
import unicodedata
from typing import Callable

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

S = 3                       # fator de supersampling do overlay
BASE_W, BASE_H = 420, 620

# ---------------------------------------------------------------------------
# Posições compartilhadas com o desenho de textos
# ---------------------------------------------------------------------------
PLACA = (26, 26, 394, 86)            # placa do título
JANELA = (18, 90, 402, 470)          # janela da arte
PAINEL = (24, 474, 396, 602)         # painel de texto
CENTRO_PODER = (54, 126)             # medalhão de poder
CENTRO_FACCAO = (366, 126)           # emblema da facção
CENTRO_ELEMENTO = (366, 176)         # gema do elemento
CENTRO_FILEIRA = (54, 176)           # fileira (corpo a corpo / distância / cerco)
CENTRO_RARIDADE = (210, 474)         # placa de raridade, a cavalo no painel

# ---------------------------------------------------------------------------
# Paletas
# ---------------------------------------------------------------------------
# metal: sequência de tons (claro → escuro) varrida na diagonal.
# luz/cor: realce e cor de destaque; esc: base escura das placas.
ESTILOS: dict[str, dict] = {
    # Paletas inspiradas nos materiais e fenômenos de Elden Ring / Souls.
    # A raridade controla o metal; a facção aparece como esmalte e gravação secundária.
    "Comum": dict(
        metal=[(205, 207, 202), (112, 121, 124), (47, 54, 59), (151, 157, 154), (35, 40, 45)],
        luz=(225, 224, 211), cor=(135, 145, 145), esc=(17, 21, 25),
        esp=8, brilho=0, vinheta=0.34),
    "Rara": dict(
        metal=[(205, 231, 241), (70, 139, 177), (25, 57, 82), (105, 177, 204), (14, 35, 55)],
        luz=(218, 240, 246), cor=(79, 151, 188), esc=(8, 20, 32),
        esp=9, brilho=38, vinheta=0.36),
    "Épica": dict(
        metal=[(225, 213, 244), (132, 99, 174), (54, 37, 83), (164, 132, 201), (31, 22, 52)],
        luz=(239, 225, 250), cor=(145, 112, 190), esc=(20, 13, 34),
        esp=10, brilho=62, vinheta=0.38),
    "Lendária": dict(
        metal=[(246, 224, 158), (177, 126, 43), (83, 54, 22), (215, 169, 77), (48, 31, 15)],
        luz=(255, 239, 190), cor=(197, 151, 66), esc=(31, 22, 12),
        esp=12, brilho=82, vinheta=0.40),
    "Mítica": dict(
        metal=[(239, 174, 143), (153, 57, 48), (66, 22, 26), (190, 82, 58), (38, 13, 20)],
        luz=(255, 210, 177), cor=(177, 69, 57), esc=(29, 11, 16),
        esp=12, brilho=94, vinheta=0.41),
    "Primordial": dict(
        metal=[(250, 244, 218), (184, 169, 126), (82, 77, 59), (218, 207, 169), (45, 43, 35)],
        luz=(255, 250, 225), cor=(211, 194, 145), esc=(27, 26, 22),
        esp=13, brilho=108, vinheta=0.42),
    "Singular": dict(
        metal=[(205, 218, 220), (77, 112, 119), (24, 39, 51), (113, 155, 158), (12, 20, 31)],
        luz=(226, 241, 238), cor=(105, 150, 151), esc=(7, 13, 22),
        esp=14, brilho=122, vinheta=0.44),
}

FACCOES: dict[str, dict] = {
    # Esmaltes de facção: discretos o bastante para conviver com a raridade.
    "Ordem Áurea": dict(cor=(184, 143, 57), metal=(242, 218, 153), esc=(38, 29, 15)),
    "Véu Carmesim": dict(cor=(142, 42, 48), metal=(205, 139, 125), esc=(34, 12, 17)),
    "Lua Negra": dict(cor=(93, 111, 159), metal=(191, 202, 224), esc=(15, 20, 37)),
}

# Nomes antigos ainda podem existir em cartas salvas, decks e templates.
# Normalizamos antes de desenhar para nunca cair silenciosamente na Ordem Áurea.
_ALIASES_FACCAO = {
    "ordem aurea": "Ordem Áurea", "golden order": "Ordem Áurea",
    "veu carmesim": "Véu Carmesim", "dinastia mohgwyn": "Véu Carmesim",
    "mohgwyn": "Véu Carmesim", "blood dynasty": "Véu Carmesim",
    "lua negra": "Lua Negra", "lua sombria": "Lua Negra", "casa cariana": "Lua Negra",
    "cariana": "Lua Negra", "carian": "Lua Negra",
}

def normalizar_faccao(valor: str | None) -> str:
    """Converte nomes atuais/legados para uma das três facções oficiais."""
    bruto = str(valor or "").strip()
    chave = unicodedata.normalize("NFKD", bruto).encode("ascii", "ignore").decode("ascii").casefold()
    return _ALIASES_FACCAO.get(chave, bruto if bruto in FACCOES else "Ordem Áurea")
ELEMENTOS: dict[str, dict] = {
    "Força": dict(cor=(238, 112, 70), claro=(255, 186, 140), escuro=(110, 30, 18)),
    "Destreza": dict(cor=(70, 214, 170), claro=(170, 255, 226), escuro=(14, 80, 62)),
    "Magia": dict(cor=(160, 130, 255), claro=(214, 200, 255), escuro=(54, 34, 130)),
}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _mix(a, b, f):
    f = max(0.0, min(1.0, f))
    return tuple(int(round(a[i] * (1 - f) + b[i] * f)) for i in range(3))


def _tom(c, f):
    """Escurece (f<1) ou clareia (f>1) uma cor."""
    if f <= 1:
        return tuple(int(c[i] * f) for i in range(3))
    return _mix(c, (255, 255, 255), f - 1)


def _rampa(stops):
    luts = ([], [], [])
    m = len(stops) - 1
    for i in range(256):
        t = i / 255 * m
        k = min(int(t), m - 1)
        f = t - k
        for c in range(3):
            luts[c].append(int(round(stops[k][c] * (1 - f) + stops[k + 1][c] * f)))
    return luts


def _gradiente(size, stops, modo="v") -> Image.Image:
    w, h = max(1, size[0]), max(1, size[1])
    if len(stops) == 1:
        return Image.new("RGB", (w, h), stops[0])
    vert = Image.linear_gradient("L").resize((w, h), Image.Resampling.BILINEAR)
    if modo == "v":
        base = vert
    else:
        hor = Image.linear_gradient("L").transpose(Image.Transpose.ROTATE_90).resize(
            (w, h), Image.Resampling.BILINEAR)
        base = hor if modo == "h" else ImageChops.add(vert, hor, scale=2)
    luts = _rampa(stops)
    return Image.merge("RGB", [base.point(lut) for lut in luts])


def _mascara(fn: Callable[[ImageDraw.ImageDraw], None]) -> Image.Image:
    m = Image.new("L", (BASE_W * S, BASE_H * S), 0)
    fn(ImageDraw.Draw(m))
    return m


def _p(pts):
    return [(x * S, y * S) for x, y in pts]


def _box(b):
    return [v * S for v in b]


def _erodir(m: Image.Image, largura: float) -> Image.Image:
    """Encolhe a máscara em ``largura`` px (base). Trabalha só na área útil, por velocidade."""
    bb = m.getbbox()
    if not bb:
        return m
    sigma = max(0.6, largura * S / 2.05)
    pad = int(sigma * 4) + 2
    box = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(m.width, bb[2] + pad), min(m.height, bb[3] + pad))
    miolo = m.crop(box).filter(ImageFilter.GaussianBlur(sigma)).point(lambda v: 255 if v >= 250 else 0)
    saida = Image.new("L", m.size, 0)
    saida.paste(miolo, box[:2])
    return saida


def _compor(ov, mascara, stops, modo="v", alpha=255):
    bb = mascara.getbbox()
    if not bb:
        return
    m = mascara.crop(bb)
    if alpha != 255:
        m = m.point(lambda v: v * alpha // 255)
    g = _gradiente(m.size, stops, modo).convert("RGBA")
    g.putalpha(m)
    ov.alpha_composite(g, (bb[0], bb[1]))


def _sombra(ov, mascara, desfoque=3.0, alpha=0.6, dy=1.6):
    bb = mascara.getbbox()
    if not bb:
        return
    pad = int(desfoque * S * 3)
    bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(mascara.width, bb[2] + pad), min(mascara.height, bb[3] + pad))
    m = mascara.crop(bb).filter(ImageFilter.GaussianBlur(desfoque * S)).point(lambda v: int(v * alpha))
    layer = Image.new("RGBA", m.size, (0, 0, 0, 0))
    layer.putalpha(m)
    destino = (bb[0], min(bb[1] + int(dy * S), mascara.height - m.height))
    ov.alpha_composite(layer, destino)


def _forma(ov, mascara, *, fundo, borda, borda_w=2.0, modo_fundo="v", modo_borda="diag",
           luz=(255, 255, 255), sombra=3.0):
    """Peça com fundo em degradê, aro metálico, brilho no topo e sombra projetada."""
    if sombra:
        _sombra(ov, mascara, sombra)
    _compor(ov, mascara, fundo, modo_fundo)
    interna = _erodir(mascara, borda_w)
    aro = ImageChops.subtract(mascara, interna)
    _compor(ov, aro, borda, modo_borda)
    # realce de bisel: borda superior-esquerda clara, inferior-direita escura
    d = max(1, int(S * 0.9))
    claro = ImageChops.subtract(aro, ImageChops.offset(aro, d, d))
    escuro = ImageChops.subtract(aro, ImageChops.offset(aro, -d, -d))
    _compor(ov, claro, [luz], alpha=190)
    _compor(ov, escuro, [(0, 0, 0)], alpha=110)
    # filete interno fino
    filete = ImageChops.subtract(interna, _erodir(interna, 0.8))
    _compor(ov, filete, [luz], alpha=48)


# ---------------------------------------------------------------------------
# Glifos (desenhados em máscara normalizada: x,y em [-1,1])
# ---------------------------------------------------------------------------
def _estrela4(md, R, cx, cy, r, v=255, fino=0.26):
    pts = []
    for i in range(8):
        a = -math.pi / 2 + i * math.pi / 4
        rr = r if i % 2 == 0 else r * fino
        pts.append((R + (cx + math.cos(a) * rr) * R, R + (cy + math.sin(a) * rr) * R))
    md.polygon(pts, fill=v)


def _T(R):
    return lambda x, y: (R + x * R, R + y * R)


def _g_erdtree(md, R, v=255):
    """Selo da Ordem Áurea: Térvore estilizada dentro do círculo do Elden."""
    T = _T(R)
    w = max(2, int(R * .095))
    # Círculo do Elden incompleto, para não competir com a árvore.
    md.arc([R*.12, R*.10, R*1.88, R*1.90], 205, 335, fill=v, width=max(2, int(R*.055)))
    # Tronco, raízes e copa ramificada.
    md.line([T(0, .76), T(0, -.42)], fill=v, width=w)
    md.line([T(0, .48), T(-.34, .82), T(-.58, .90)], fill=v, width=max(2, int(R*.07)))
    md.line([T(0, .48), T(.34, .82), T(.58, .90)], fill=v, width=max(2, int(R*.07)))
    for side in (-1, 1):
        md.line([T(0, -.22), T(side*.28, -.43), T(side*.57, -.48)], fill=v, width=w)
        md.line([T(side*.25, -.40), T(side*.20, -.69)], fill=v, width=max(2, int(R*.065)))
        md.line([T(side*.45, -.45), T(side*.61, -.72)], fill=v, width=max(2, int(R*.065)))
    md.ellipse([R*.43, R*.02, R*.57, R*.16], outline=v, width=max(2, int(R*.045)))
    _estrela4(md, R, 0, -.94, .12, v)

def _g_bigorna(md, R, v=255):
    T = _T(R)
    md.polygon([T(-.98, -.30), T(-.50, -.52), T(.74, -.52), T(.74, -.20), T(-.50, -.20)], fill=v)
    md.polygon([T(-.36, -.20), T(.50, -.20), T(.32, .22), T(-.22, .22)], fill=v)
    md.polygon([T(-.58, .22), T(.62, .22), T(.74, .58), T(-.70, .58)], fill=v)
    _estrela4(md, R, .50, -.86, .30, v)


def _g_lua(md, R, v=255):
    """Selo da Lua Negra: lua crescente, órbita e estrelas distantes."""
    # Crescente aberto à direita, com recorte limpo.
    md.ellipse([R*.12, R*.08, R*1.88, R*1.92], fill=v)
    md.ellipse([R*.55, R*.00, R*2.05, R*1.50], fill=0)
    # Órbita inclinada e três estrelas.
    md.arc([R*.02, R*.18, R*1.98, R*1.82], 205, 345, fill=v, width=max(2, int(R*.07)))
    _estrela4(md, R, -.40, -.55, .18, v)
    _estrela4(md, R, .58, .34, .22, v)
    _estrela4(md, R, -.28, .64, .11, v)

def _g_arcano(md, R, v=255):
    T = _T(R)
    w = max(2, int(R * .13))
    md.ellipse([R - .92 * R, R - .92 * R, R + .92 * R, R + .92 * R], outline=v, width=w)
    for k in (0, 1):
        pts = [T(math.cos(math.radians(-90 + k * 60 + i * 120)) * .66,
                 math.sin(math.radians(-90 + k * 60 + i * 120)) * .66) for i in range(3)]
        md.polygon(pts, outline=v, width=w)
    md.ellipse([R - .14 * R, R - .14 * R, R + .14 * R, R + .14 * R], fill=v)


def _g_sangue(md, R, v=255):
    """Selo do Véu Carmesim: tridente ritual, gota e aro de espinhos."""
    T = _T(R)
    w = max(2, int(R*.105))
    # Haste central e três pontas evocam o rito sanguíneo de Mohgwyn.
    md.line([T(0, .88), T(0, -.42)], fill=v, width=w)
    md.line([T(0, -.12), T(-.48, -.72)], fill=v, width=w)
    md.line([T(0, -.12), T(.48, -.72)], fill=v, width=w)
    md.line([T(-.48, -.72), T(-.48, -.94)], fill=v, width=w)
    md.line([T(0, -.42), T(0, -.98)], fill=v, width=w)
    md.line([T(.48, -.72), T(.48, -.94)], fill=v, width=w)
    # Gota suspensa no centro e meia coroa de espinhos.
    md.polygon([T(0, -.02), T(-.23, .28), T(-.18, .55), T(0, .70), T(.18, .55), T(.23, .28)], fill=v)
    md.arc([R*.12, R*.35, R*1.88, R*1.92], 205, 335, fill=v, width=max(2, int(R*.06)))
    for ang in (220, 250, 280, 310, 340):
        a = math.radians(ang)
        x, y = .72*math.cos(a), .72*math.sin(a)
        md.polygon([T(x, y), T(x+.10*math.cos(a), y+.10*math.sin(a)),
                    T(x+.20*math.cos(a+1.0), y+.20*math.sin(a+1.0))], fill=v)

def _espada_rot(md, R, ang, v, dx=0.0, dy=0.0):
    """Espada de pé (ponta para cima) girada em torno do centro."""
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)

    def T(x, y):
        x, y = x + dx, y + dy
        return (R + (x * ca - y * sa) * R, R + (x * sa + y * ca) * R)

    md.polygon([T(0, -1.02), T(.15, -.74), T(.15, .26), T(-.15, .26), T(-.15, -.74)], fill=v)
    md.polygon([T(-.46, .26), T(.46, .26), T(.46, .42), T(-.46, .42)], fill=v)
    md.polygon([T(-.08, .42), T(.08, .42), T(.08, .78), T(-.08, .78)], fill=v)
    c = T(0, .88)
    md.ellipse([c[0] - .13 * R, c[1] - .13 * R, c[0] + .13 * R, c[1] + .13 * R], fill=v)


def _g_forca(md, R, v=255):
    _espada_rot(md, R, 38, v, 0, -.02)
    _espada_rot(md, R, -38, v, 0, -.02)


def _g_destreza(md, R, v=255):
    """Pena: leve, rápida, de ponta afiada."""
    T = _T(R)
    topo, base = [], []
    n = 24
    for k in range(n + 1):
        t = k / n
        ax, ay = -.78 + t * 1.58, .78 - t * 1.58           # eixo do canto inferior-esquerdo ao superior-direito
        larg = .44 * (math.sin(math.pi * min(1, t * 1.04)) ** .75) * (1 - .25 * t)
        topo.append(T(ax - larg * .707, ay - larg * .707))
        base.append(T(ax + larg * .707, ay + larg * .707))
    md.polygon(topo + base[::-1], fill=v)
    md.line([T(-.92, .92), T(.60, -.60)], fill=0, width=max(1, int(R * .07)))
    md.line([T(-.98, .98), T(-.62, .62)], fill=v, width=max(2, int(R * .11)))


def _g_magia(md, R, v=255):
    _estrela4(md, R, -.10, .06, .90, v, fino=.22)
    _estrela4(md, R, .62, -.62, .42, v, fino=.24)
    _estrela4(md, R, .56, .66, .22, v, fino=.26)


def _g_espada(md, R, v=255):
    T = _T(R)
    md.polygon([T(0, -.98), T(.17, -.62), T(.17, .34), T(-.17, .34), T(-.17, -.62)], fill=v)
    md.rectangle([T(-.52, .34), T(.52, .50)], fill=v)
    md.rectangle([T(-.10, .50), T(.10, .84)], fill=v)
    md.ellipse([T(-.18, .80), T(.18, 1.0)], fill=v)


def _g_arco(md, R, v=255):
    T = _T(R)
    md.arc([R - .98 * R, R - .92 * R, R + .34 * R, R + .92 * R], 280, 80, fill=v, width=max(2, int(R * .17)))
    md.line([T(-.34, -.86), T(-.34, .86)], fill=v, width=max(1, int(R * .07)))
    md.line([T(-.34, 0), T(.86, 0)], fill=v, width=max(2, int(R * .12)))
    md.polygon([T(.98, 0), T(.60, -.26), T(.60, .26)], fill=v)


def _g_torre(md, R, v=255):
    T = _T(R)
    md.rectangle([T(-.54, -.28), T(.54, .90)], fill=v)
    for x in (-.54, -.14, .26):
        md.rectangle([T(x, -.72), T(x + .28, -.28)], fill=v)
    md.pieslice([T(-.20, .20), T(.20, .98)], 180, 360, fill=0)
    md.rectangle([T(-.20, .58), T(.20, .90)], fill=0)


def _g_selo(md, R, v=255):
    T = _T(R)
    md.polygon([T(0, -.92), T(.70, 0), T(0, .92), T(-.70, 0)], fill=v)
    md.polygon([T(0, -.52), T(.38, 0), T(0, .52), T(-.38, 0)], fill=0)
    md.ellipse([R - .13 * R, R - .13 * R, R + .13 * R, R + .13 * R], fill=v)


def _carimbar(ov, glifo, cx, cy, raio, cores, *, sombra=True, modo="v"):
    """Aplica um glifo com degradê e uma sombra curta, sem depender de fontes."""
    R = int(raio * S)
    m = Image.new("L", (2 * R, 2 * R), 0)
    glifo(ImageDraw.Draw(m), R, 255)
    pos = (int(cx * S - R), int(cy * S - R))
    if sombra:
        sh = m.filter(ImageFilter.GaussianBlur(S * .8)).point(lambda v: int(v * .75))
        layer = Image.new("RGBA", m.size, (0, 0, 0, 0))
        layer.putalpha(sh)
        ov.alpha_composite(layer, (pos[0] + int(S * .8), pos[1] + int(S * 1.1)))
    g = _gradiente(m.size, cores, modo).convert("RGBA")
    g.putalpha(m)
    ov.alpha_composite(g, pos)


# ---------------------------------------------------------------------------
# Gemas e ornamentos pontuais
# ---------------------------------------------------------------------------
def _gema(ov, cx, cy, r, cor, forma="losango"):
    """Gema facetada: facetas claras no topo-esquerda, escuras na base-direita."""
    d = ImageDraw.Draw(ov)
    claro, medio, escuro = _tom(cor, 1.55), cor, _tom(cor, .42)
    if forma == "losango":
        a, b, c, e = (cx, cy - r), (cx + r * .78, cy), (cx, cy + r), (cx - r * .78, cy)
    else:  # hexágono
        a, b, c, e = (cx, cy - r), (cx + r * .86, cy), (cx, cy + r), (cx - r * .86, cy)
    ctr = (cx, cy)
    # contorno escuro
    k = 1.22
    d.polygon(_p([(cx, cy - r * k), (cx + (b[0] - cx) * k, cy), (cx, cy + r * k), (cx - (cx - e[0]) * k, cy)]),
              fill=(8, 8, 12, 235))
    d.polygon(_p([a, e, ctr]), fill=(*claro, 255))
    d.polygon(_p([a, b, ctr]), fill=(*medio, 255))
    d.polygon(_p([b, c, ctr]), fill=(*escuro, 255))
    d.polygon(_p([c, e, ctr]), fill=(*_mix(medio, escuro, .5), 255))
    d.ellipse(_box((cx - r * .22 - r * .18, cy - r * .5 - r * .12, cx - r * .22 + r * .02, cy - r * .5 + r * .1)),
              fill=(255, 255, 255, 230))


def _rebite(ov, cx, cy, r, luz):
    d = ImageDraw.Draw(ov)
    d.ellipse(_box((cx - r, cy - r, cx + r, cy + r)), fill=(10, 10, 14, 220))
    d.ellipse(_box((cx - r * .78, cy - r * .78, cx + r * .78, cy + r * .78)), fill=(*_tom(luz, .62), 255))
    d.ellipse(_box((cx - r * .5, cy - r * .55, cx + r * .1, cy + r * .05)), fill=(*luz, 255))


def _estrela_gema(ov, cx, cy, r, cor, luz, pontas=8):
    d = ImageDraw.Draw(ov)
    pts = []
    for i in range(pontas * 2):
        a = -math.pi / 2 + i * math.pi / pontas
        rr = r if i % 2 == 0 else r * .40
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    d.polygon(_p(pts), fill=(*cor, 255), outline=(*luz, 255), width=S)
    d.ellipse(_box((cx - r * .22, cy - r * .22, cx + r * .22, cy + r * .22)), fill=(255, 255, 255, 240))


# ---------------------------------------------------------------------------
# Moldura por raridade
# ---------------------------------------------------------------------------
def _pontos_arquitetura_faccao(faccao: str, inset: float = 0) -> list[tuple[float, float]]:
    """Retângulo vertical de cantos retos; a facção muda a heráldica, não o formato da carta.

    O contorno externo permanece sempre 90° e com proporção de carta colecionável.
    A identidade de cada facção é desenhada como gravação metálica dentro do aro.
    """
    normalizar_faccao(faccao)  # valida aliases legados sem alterar a geometria
    x1, y1, x2, y2 = 3 + inset, 3 + inset, BASE_W - 3 - inset, BASE_H - 3 - inset
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def _forma_moldura(rar: str, est: dict, faccao: str = "Ordem Áurea") -> Image.Image:
    """Aro retangular vertical de cantos a 90°, com espessura uniforme.

    Facção e raridade não deformam a silhueta: elas são comunicadas pelo metal,
    pelos filetes e pelos ornamentos gravados na superfície do aro.
    """
    t = est["esp"]
    x1, y1, x2, y2 = 3, 3, BASE_W - 3, BASE_H - 3
    def fn(d):
        d.rectangle(_box((x1, y1, x2, y2)), fill=255)
        d.rectangle(_box((x1 + t, y1 + t, x2 - t, y2 - t)), fill=0)
    return _mascara(fn)


def _bisel_moldura(ov, mascara, est):
    """Metal envelhecido: bisel, pátina e microtextura de forja."""
    # Contorno escuro profundo, como metal oxidado sob a luz.
    contorno = mascara.filter(ImageFilter.MaxFilter(5))
    _compor(ov, contorno, [(4, 5, 8)], alpha=245)
    _compor(ov, mascara, est["metal"], "diag")

    # Microtextura determinística de metal martelado. A máscara impede que
    # qualquer grão escape para a ilustração ou para fora da carta.
    ruido = Image.effect_noise(mascara.size, 19).convert("L")
    alpha_ruido = ruido.point(lambda v: max(0, min(24, int((v - 72) * .16))))
    alpha_ruido = ImageChops.multiply(alpha_ruido, mascara)
    textura = Image.new("RGBA", mascara.size, (*_mix(est["metal"][1], est["luz"], .38), 0))
    textura.putalpha(alpha_ruido)
    ov.alpha_composite(textura)

    d = max(1, int(S * 1.1))
    claro = ImageChops.subtract(mascara, ImageChops.offset(mascara, d, d))
    escuro = ImageChops.subtract(mascara, ImageChops.offset(mascara, -d, -d))
    _compor(ov, claro, [est["luz"]], alpha=225)
    _compor(ov, escuro, [(0, 0, 0)], alpha=155)

    # Duplo filete: um bisel claro externo e uma gravação escura interna.
    interna = _erodir(mascara, 2.0)
    miolo = ImageChops.subtract(interna, _erodir(interna, 0.9))
    _compor(ov, miolo, [est["luz"]], alpha=58)
    grava = ImageChops.subtract(_erodir(mascara, 4.1), _erodir(mascara, 4.8))
    _compor(ov, grava, [est["cor"]], alpha=42)


def _decoracoes_moldura(ov, rar, est):
    """Gemas, rebites e filetes que ficam *por cima* do metal."""
    W, H = BASE_W, BASE_H
    cx = W / 2
    luz, cor = est["luz"], est["cor"]
    d = ImageDraw.Draw(ov)
    t = est["esp"]
    if rar == "Comum":
        for x, y in ((3 + t / 2, 3 + t / 2), (W - 3 - t / 2, 3 + t / 2), (3 + t / 2, H - 3 - t / 2),
                     (W - 3 - t / 2, H - 3 - t / 2), (cx, 3 + t / 2), (cx, H - 3 - t / 2)):
            _rebite(ov, x, y, 2.3, luz)
    elif rar == "Rara":
        _gema(ov, cx, 12, 8, cor)
        _gema(ov, cx, H - 12, 8, cor)
        for x in (3 + t / 2, W - 3 - t / 2):
            _gema(ov, x, H / 2, 6, cor)
        for x, y in ((14, 14), (W - 14, 14), (14, H - 14), (W - 14, H - 14)):
            d.ellipse(_box((x - 2.4, y - 2.4, x + 2.4, y + 2.4)), fill=(255, 255, 255, 235))
    elif rar == "Épica":
        for y0 in (14, H - 14):
            _gema(ov, cx, y0, 8.5, cor)
        for x, y in ((14, 14), (W - 14, 14), (14, H - 14), (W - 14, H - 14)):
            _gema(ov, x, y, 5, _mix(cor, (255, 255, 255), .25))
    elif rar == "Lendária":
        _gema(ov, cx, 10, 7.5, (255, 60, 80), "hex")
        for x, y in ((16, 16), (W - 16, 16), (16, H - 16), (W - 16, H - 16)):
            _gema(ov, x, y, 5.6, cor)
        _gema(ov, cx, H - 11, 6.5, cor, "hex")
        for sx in (3 + t / 2, W - 3 - t / 2):
            for y in (190, 300, 410):
                d.ellipse(_box((sx - 2.2, y - 2.2, sx + 2.2, y + 2.2)), fill=(255, 250, 215, 240))
    elif rar == "Mítica":
        for x, y in ((cx, 14), (cx, H - 14)):
            _estrela_gema(ov, x, y, 11, cor, luz, 6)
        for x in (14, W - 14):
            _estrela_gema(ov, x, H / 2, 7.5, (150, 210, 255), luz, 6)
        for x, y in ((18, 18), (W - 18, 18), (18, H - 18), (W - 18, H - 18)):
            d.ellipse(_box((x - 3, y - 3, x + 3, y + 3)), fill=(255, 255, 255, 245))
    elif rar == "Primordial":
        for y in (11, H - 11):
            d.ellipse(_box((cx - 13, y - 13, cx + 13, y + 13)), fill=(30, 22, 6, 255), outline=(*luz, 255), width=int(S * 1.4))
            for k in range(12):
                a = k * math.pi / 6
                d.line(_p([(cx + math.cos(a) * 5.5, y + math.sin(a) * 5.5), (cx + math.cos(a) * 11.5, y + math.sin(a) * 11.5)]),
                       fill=(*luz, 255), width=int(S * 1.2))
            d.ellipse(_box((cx - 4.5, y - 4.5, cx + 4.5, y + 4.5)), fill=(255, 250, 205, 255))
        for sx in (3 + t / 2 + 1, W - 3 - t / 2 - 1):
            for y in range(120, H - 100, 62):
                d.polygon(_p([(sx, y - 5), (sx + 3.4, y), (sx, y + 5), (sx - 3.4, y)]), fill=(255, 250, 205, 255))
    elif rar == "Singular":
        _gema(ov, 112, 12, 7.5, cor)
        for y in (210, 262, 314):
            d.ellipse(_box((W - 15.5, y - 3.5, W - 8.5, y + 3.5)), fill=(*cor, 255))
            d.ellipse(_box((W - 14, y - 2, W - 10, y + 2)), fill=(255, 255, 255, 240))
        d.line(_p([(W - 12, 212), (W - 12, 312)]), fill=(*luz, 150), width=S)
        _gema(ov, W - 112, H - 12, 7.5, cor)


def _janela_arte(ov, est):
    """Aro fino de metal ao redor da janela da arte, com sombra interna."""
    x1, y1, x2, y2 = JANELA
    m = _mascara(lambda d: d.rounded_rectangle(_box((x1 - 2.5, y1 - 2.5, x2 + 2.5, y2 + 2.5)),
                                                radius=5 * S, fill=255))
    nucleo = _mascara(lambda d: d.rounded_rectangle(_box((x1, y1, x2, y2)), radius=3 * S, fill=255))
    aro = ImageChops.subtract(m, nucleo)
    _compor(ov, aro, est["metal"], "diag")
    d = max(1, int(S * .9))
    _compor(ov, ImageChops.subtract(aro, ImageChops.offset(aro, d, d)), [est["luz"]], alpha=150)
    _compor(ov, ImageChops.subtract(aro, ImageChops.offset(aro, -d, -d)), [(0, 0, 0)], alpha=150)


# ---------------------------------------------------------------------------
# Placas, medalhões e emblemas
# ---------------------------------------------------------------------------
def _placa_titulo(ov, est):
    x1, y1, x2, y2 = PLACA
    c = 9
    pts = [(x1 + c, y1), (x2 - c, y1), (x2, y1 + c), (x2, y2 - c), (x2 - c, y2), (x1 + c, y2), (x1, y2 - c), (x1, y1 + c)]
    m = _mascara(lambda d: d.polygon(_p(pts), fill=255))
    base = est["esc"]
    _forma(ov, m, fundo=[_tom(base, 1.5), _tom(base, .75), (7, 8, 11)], borda=est["metal"], borda_w=2.2,
           luz=est["luz"], sombra=2.5)
    d = ImageDraw.Draw(ov)
    # losangos laterais
    for x in (x1 + 8, x2 - 8):
        d.polygon(_p([(x, (y1 + y2) / 2 - 5), (x + 4, (y1 + y2) / 2), (x, (y1 + y2) / 2 + 5), (x - 4, (y1 + y2) / 2)]),
                  fill=(*est["luz"], 235))


def _painel_texto(ov, est, faccao):
    x1, y1, x2, y2 = PAINEL
    c = 9
    pts = [(x1 + c, y1), (x2 - c, y1), (x2, y1 + c), (x2, y2 - 6), (x2 - 6, y2), (x1 + 6, y2), (x1, y2 - 6), (x1, y1 + c)]
    m = _mascara(lambda d: d.polygon(_p(pts), fill=255))
    base = _mix(est["esc"], FACCOES.get(faccao, FACCOES["Ordem Áurea"])["esc"], .72)
    _forma(ov, m, fundo=[_tom(base, 1.25), _tom(base, .62), (7, 8, 10)], borda=est["metal"], borda_w=2.4,
           luz=est["luz"], sombra=3.5)
    # divisória sob a linha de facção/fileira
    d = ImageDraw.Draw(ov)
    yy = 502
    for i in range(0, 100):
        t = i / 99
        a = int(210 * math.sin(math.pi * t) ** .7)
        xa = x1 + 12 + (x2 - x1 - 24) * t
        d.line(_p([(xa, yy), (xa + (x2 - x1 - 24) / 99 + .3, yy)]), fill=(*est["cor"], a), width=int(S * 1.4))
    d.polygon(_p([(x1 + 12, yy), (x1 + 17, yy - 3), (x1 + 22, yy), (x1 + 17, yy + 3)]), fill=(*est["luz"], 255))
    d.polygon(_p([(x2 - 12, yy), (x2 - 17, yy - 3), (x2 - 22, yy), (x2 - 17, yy + 3)]), fill=(*est["luz"], 255))


def _placa_raridade(ov, est, largura):
    cx, cy = CENTRO_RARIDADE
    hw, hh = largura / 2, 11.5
    pts = [(cx - hw - 9, cy), (cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw + 9, cy), (cx + hw, cy + hh), (cx - hw, cy + hh)]
    m = _mascara(lambda d: d.polygon(_p(pts), fill=255))
    cor = est["cor"]
    _forma(ov, m, fundo=[_tom(cor, .95), _tom(cor, .52), _tom(cor, .30)], borda=est["metal"], borda_w=1.9,
           luz=est["luz"], sombra=2.6)
    d = ImageDraw.Draw(ov)
    for sx in (-1, 1):
        x = cx + sx * (hw + 14)
        _gema(ov, x, cy, 4.8, cor)


def _medalhao_poder(ov, est, especial):
    cx, cy = CENTRO_PODER
    r = 29
    hexa = lambda rr: [(cx + math.cos(math.radians(-90 + i * 60)) * rr, cy + math.sin(math.radians(-90 + i * 60)) * rr)
                       for i in range(6)]
    m = _mascara(lambda d: d.polygon(_p(hexa(r)), fill=255))
    _forma(ov, m, fundo=[_tom(est["cor"], .80), _tom(est["cor"], .42), _tom(est["esc"], .7)],
           borda=est["metal"], borda_w=3.2, luz=est["luz"], sombra=3.2)
    miolo = _mascara(lambda d: d.polygon(_p(hexa(r - 6.5)), fill=255))
    _compor(ov, ImageChops.subtract(miolo, _erodir(miolo, .8)), [est["luz"]], alpha=70)
    if especial:
        _carimbar(ov, _g_selo, cx, cy, 15, [(255, 252, 235), est["luz"]])


def _emblema_faccao(ov, est, faccao):
    faccao = normalizar_faccao(faccao)
    f = FACCOES[faccao]
    cx, cy = CENTRO_FACCAO
    r = 28
    m = _mascara(lambda d: d.ellipse(_box((cx - r, cy - r, cx + r, cy + r)), fill=255))
    _forma(ov, m, fundo=[_tom(f["cor"], .55), _tom(f["esc"], .85), (6, 8, 10)], modo_fundo="v",
           borda=[_tom(f["metal"], 1.1), f["cor"], _tom(f["cor"], .4), f["cor"], _tom(f["cor"], .5)], borda_w=3.2,
           luz=f["metal"], sombra=3.2)
    anel = _mascara(lambda d: d.ellipse(_box((cx - r + 6, cy - r + 6, cx + r - 6, cy + r - 6)), fill=255))
    _compor(ov, ImageChops.subtract(anel, _erodir(anel, .7)), [f["cor"]], alpha=95)
    glifo = {"Ordem Áurea": _g_erdtree, "Lua Negra": _g_lua, "Véu Carmesim": _g_sangue}.get(faccao, _g_arcano)
    _carimbar(ov, glifo, cx, cy + (1.2 if faccao == "Ordem Áurea" else 0), 15.5, [_tom(f["metal"], 1.25), f["cor"]])


def _gema_elemento(ov, est, tipo):
    e = ELEMENTOS.get(tipo, ELEMENTOS["Magia"])
    cx, cy = CENTRO_ELEMENTO
    r = 18
    octo = lambda rr: [(cx + math.cos(math.radians(-67.5 + i * 45)) * rr, cy + math.sin(math.radians(-67.5 + i * 45)) * rr)
                       for i in range(8)]
    m = _mascara(lambda d: d.polygon(_p(octo(r)), fill=255))
    _forma(ov, m, fundo=[e["claro"], e["cor"], e["escuro"]], modo_fundo="diag",
           borda=[(236, 240, 244), (140, 150, 162), (60, 68, 80), (160, 170, 182)], borda_w=2.4,
           luz=(255, 255, 255), sombra=2.8)
    # reflexo de gema
    d = ImageDraw.Draw(ov)
    d.polygon(_p([(cx - 9, cy - 8), (cx + 2, cy - 12), (cx - 2, cy - 6), (cx - 8, cy - 2)]), fill=(255, 255, 255, 70))
    glifo = {"Força": _g_forca, "Destreza": _g_destreza}.get(tipo, _g_magia)
    _carimbar(ov, glifo, cx, cy + .3, 10.6, [(255, 255, 255), _tom(e["claro"], 1.2)])


def _chip_fileira(ov, est, fileira):
    cx, cy = CENTRO_FILEIRA
    r = 17
    m = _mascara(lambda d: d.ellipse(_box((cx - r, cy - r, cx + r, cy + r)), fill=255))
    _forma(ov, m, fundo=[_tom(est["esc"], 1.6), _tom(est["esc"], .6), (6, 7, 9)],
           borda=est["metal"], borda_w=2.3, luz=est["luz"], sombra=2.8)
    glifo = {"melee": _g_espada, "ranged": _g_arco}.get(fileira, _g_torre)
    _carimbar(ov, glifo, cx, cy, 9.4, [(255, 255, 255), _tom(est["luz"], .95)])




def _decoracoes_faccao(ov, faccao, est):
    """Gravuras heráldicas finas nas faixas do aro; nunca altera a silhueta.

    O desenho externo, a janela da arte e as placas permanecem fixos.
    A facção é reconhecida pela linguagem ornamental, não por trocar apenas a cor.
    """
    faccao = normalizar_faccao(faccao)
    d = ImageDraw.Draw(ov)
    f = FACCOES[faccao]
    cor, metal = f["cor"], f["metal"]
    brilho = _mix(metal, (255, 250, 225), .28)
    sombra = _mix(f["esc"], (5, 7, 12), .25)

    def line(points, color=metal, width=.8, alpha=225):
        d.line(_p(points), fill=(*color, alpha), width=max(1, int(width*S)), joint="curve")

    def ellipse(box, outline=metal, width=.7, alpha=220, fill=None):
        x1,y1,x2,y2=box
        d.ellipse(_box((min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2))),
                  fill=((*fill,alpha) if fill else None),
                  outline=(*outline,alpha), width=max(1,int(width*S)))

    def diamond(x,y,rx=1.5,ry=3.0,color=brilho,alpha=235):
        d.polygon(_p([(x,y-ry),(x+rx,y),(x,y+ry),(x-rx,y)]),fill=(*color,alpha))

    def star(x,y,r=2.0,color=brilho,alpha=235):
        pts=[]
        for i in range(8):
            a=-math.pi/2+i*math.pi/4
            rr=r if i%2==0 else r*.18
            pts.append((x+math.cos(a)*rr,y+math.sin(a)*rr))
        d.polygon(_p(pts),fill=(*color,alpha))

    # As gravações ocupam somente o metal entre a borda externa e a janela.
    # Quatro cartuchos de canto criam uma leitura heráldica sem arredondar os cantos.
    for sx in (-1,1):
        for sy in (-1,1):
            x0 = 10.5 if sx < 0 else BASE_W-10.5
            y0 = 14 if sy < 0 else BASE_H-14
            if faccao == "Ordem Áurea":
                # Pequenos frontões e colunas de catedral, como os relevos de Leyndell.
                line([(x0-sx*5,y0+sy*7),(x0-sx*5,y0-sy*1),
                      (x0,y0-sy*7),(x0+sx*5,y0-sy*1),(x0+sx*5,y0+sy*7)],metal,1.0,240)
                line([(x0-sx*2.5,y0+sy*6),(x0-sx*2.5,y0-sy*1),
                      (x0,y0-sy*4),(x0+sx*2.5,y0-sy*1),(x0+sx*2.5,y0+sy*6)],cor,.7,230)
                diamond(x0,y0+sy*1.5,1.4,2.6,brilho,245)
            elif faccao == "Véu Carmesim":
                # Pontas de tridente e espinhos, remetendo aos ritos de Mohgwyn.
                line([(x0-sx*5,y0+sy*7),(x0-sx*5,y0-sy*1),
                      (x0,y0-sy*7),(x0+sx*5,y0-sy*1),(x0+sx*5,y0+sy*7)],metal,1.0,240)
                line([(x0,y0-sy*6),(x0,y0+sy*4)],cor,1.0,240)
                line([(x0,y0-sy*2),(x0-sx*3,y0-sy*5)],cor,.8,235)
                line([(x0,y0-sy*2),(x0+sx*3,y0-sy*5)],cor,.8,235)
                d.polygon(_p([(x0,y0+sy*1),(x0-sx*2,y0+sy*5),
                              (x0,y0+sy*8),(x0+sx*2,y0+sy*5)]),fill=(*cor,245))
            else:
                # Astrolábio compacto: anéis, eixo e estrela polar.
                ellipse((x0-6,y0-7,x0+6,y0+7),metal,.8,235)
                ellipse((x0-3.7,y0-4.5,x0+3.7,y0+4.5),cor,.55,220)
                line([(x0-sx*7,y0+sy*6),(x0+sx*7,y0-sy*6)],metal,.65,215)
                star(x0,y0,2.2,brilho,250)

    # Trilhos laterais: cada facção tem um ritmo visual próprio e medalhões distintos.
    for side in (-1,1):
        x=10.5 if side<0 else BASE_W-10.5
        if faccao == "Ordem Áurea":
            # Haste de ouro vivo com pares de folhas, brotos e sementes.
            line([(x,188),(x,218),(x+side*.8,248),(x,278),(x,308),
                  (x+side*.8,338),(x,368),(x,397)],metal,1.15,235)
            line([(x+side*1.8,190),(x+side*1.8,397)],cor,.55,135)
            for yy, direction in ((204,-1),(224,1),(246,-1),(268,1),(290,-1),
                                  (312,1),(334,-1),(356,1),(380,-1)):
                ex=x+side*4.0
                ey=yy+direction*3.0
                line([(x,yy),(ex,ey)],metal,.7,220)
                ellipse((ex-1.3,ey-2.4,ex+1.3,ey+2.4),metal,.45,230,cor)
                line([(ex,ey+1),(ex,ey+3)],brilho,.45,210)
            for yy in (230,300,370):
                ellipse((x-4.5,yy-8,x+4.5,yy+8),metal,.75,235)
                line([(x,yy+5),(x,yy-5),(x-side*2.5,yy-7)],brilho,.8,245)
                line([(x,yy-1),(x+side*2.7,yy-4)],brilho,.7,235)
                diamond(x,yy,1.1,2.0,cor,245)

        elif faccao == "Véu Carmesim":
            # Coluna de espinhos com elos e gotas alongadas de sangue coagulado.
            line([(x,188),(x,210),(x+side*2.7,228),(x-side*2.4,248),
                  (x,270),(x,292),(x+side*2.7,310),(x-side*2.4,332),
                  (x,354),(x,397)],cor,1.25,245)
            line([(x-side*1.7,190),(x-side*1.7,397)],metal,.55,150)
            for yy, direction in ((211,-1),(245,1),(291,-1),(329,1),(370,-1)):
                line([(x,yy),(x+side*4.8,yy+direction*5.5),
                      (x+side*3.0,yy+direction*1.3)],metal,.85,235)
                d.polygon(_p([(x,yy+4),(x-side*1.6,yy+8),
                              (x,yy+14),(x+side*1.6,yy+8)]),fill=(*cor,245))
            for yy in (230,305,378):
                ellipse((x-4.6,yy-8.5,x+4.6,yy+8.5),metal,.75,235)
                ellipse((x-2.7,yy-5.7,x+2.7,yy+5.7),cor,.55,230)
                d.polygon(_p([(x,yy-5),(x-2.2,yy+1),(x-1.5,yy+5),
                              (x,yy+7),(x+1.5,yy+5),(x+2.2,yy+1)]),
                          fill=(*brilho,235))
                diamond(x,yy-7,1.0,1.8,cor,245)

        else:
            # Mapa celeste vertical: órbitas elípticas, nós estelares e crescentes.
            nodes=[(x,198),(x+side*2.7,224),(x-side*2.5,250),
                   (x,278),(x+side*2.7,306),(x-side*2.5,334),(x,362),(x,394)]
            line(nodes,metal,.7,220)
            line([(x-side*2.1,198),(x-side*2.1,394)],cor,.5,130)
            for idx,(nx,ny) in enumerate(nodes):
                if idx%2==0:
                    star(nx,ny,2.2 if idx in (0,6) else 1.8,brilho,245)
                else:
                    ellipse((nx-1.35,ny-1.35,nx+1.35,ny+1.35),cor,.55,230,sombra)
            for yy,direction in ((216,-1),(270,1),(324,-1),(380,1)):
                ellipse((x-4.2,yy-6.0,x+4.2,yy+6.0),metal,.65,220)
                # Crescente obtido por dois arcos deslocados.
                ellipse((x-2.0,yy-4.5,x+3.2,yy+4.5),cor,.55,225)
                d.ellipse(_box((x-.2,yy-4.2,x+4.6,yy+4.2)),fill=(*sombra,255))
                star(x-side*1.2,yy,1.6,brilho,245)

    # Fecho heráldico central no rodapé: sol, gota ou estrela polar.
    if faccao == "Ordem Áurea":
        ellipse((198,605,222,619),metal,.75,205)
        for a in range(12):
            ang=a*math.pi/6
            line([(210+math.cos(ang)*4,612+math.sin(ang)*2.2),
                  (210+math.cos(ang)*9,612+math.sin(ang)*5.2)],brilho,.65,220)
        diamond(210,612,1.5,3.0,cor,245)
    elif faccao == "Véu Carmesim":
        ellipse((198,605,222,619),metal,.7,190)
        for cx in (201,207,213,219):
            ellipse((cx-2.3,607,cx+2.3,616),metal,.55,185)
        d.polygon(_p([(210,605),(205,611),(207,616),(210,619),
                      (213,616),(215,611)]),fill=(*cor,245),outline=(*brilho,230))
    else:
        ellipse((198,605,222,619),metal,.7,195)
        ellipse((202,607,218,617),cor,.55,220)
        star(210,612,3.1,brilho,250)
        line([(210,603),(210,606)],metal,.7,210)
        line([(210,618),(210,621)],metal,.7,210)

    # Acabamento de ourivesaria: dois filetes internos e pequenas marcas de punção.
    # Eles reforçam a leitura de metal trabalhado sem mudar o contorno nem invadir a arte.
    for side in (-1, 1):
        x_outer = 5.4 if side < 0 else BASE_W-5.4
        x_inner = 16.1 if side < 0 else BASE_W-16.1
        line([(x_outer, 34),(x_outer, 586)],metal,.65,115)
        line([(x_inner, 188),(x_inner, 398)],cor,.55,145)
        for yy in (178, 414, 454):
            diamond(x_inner, yy, .9, 1.8, brilho, 185)

    # Medalhões laterais mais legíveis em miniatura: cada facção usa um selo próprio.
    for side in (-1, 1):
        x = 10.5 if side < 0 else BASE_W-10.5
        for yy in (230, 305, 380):
            if faccao == "Ordem Áurea":
                ellipse((x-5.0,yy-9.5,x+5.0,yy+9.5),metal,.9,245,sombra)
                ellipse((x-3.6,yy-7.8,x+3.6,yy+7.8),cor,.55,230)
                line([(x,yy+6),(x,yy-5),(x-side*2.0,yy-7)],brilho,.85,245)
                line([(x,yy-1),(x+side*2.3,yy-4)],brilho,.75,240)
                diamond(x,yy+1,1.0,2.0,metal,245)
            elif faccao == "Véu Carmesim":
                ellipse((x-5.0,yy-9.5,x+5.0,yy+9.5),metal,.9,245,sombra)
                ellipse((x-3.6,yy-7.8,x+3.6,yy+7.8),cor,.55,235)
                d.polygon(_p([(x,yy-6),(x-2.7,yy+1),(x-1.7,yy+5),
                              (x,yy+7),(x+1.7,yy+5),(x+2.7,yy+1)]),
                          fill=(*brilho,245))
                line([(x,yy-7),(x,yy-9)],metal,.7,235)
            else:
                ellipse((x-5.0,yy-9.5,x+5.0,yy+9.5),metal,.9,245,sombra)
                ellipse((x-3.6,yy-7.8,x+3.6,yy+7.8),cor,.55,230)
                ellipse((x-2.1,yy-5.2,x+2.1,yy+5.2),metal,.5,220)
                star(x,yy,2.0,brilho,250)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def construir_overlay(*, raridade: str, faccao: str, tipo: str, fileira: str, especial: bool,
                      largura_raridade: float = 100) -> Image.Image:
    """Camada RGBA (BASE × S) com moldura, placas, medalhão e emblemas."""
    est = ESTILOS.get(raridade, ESTILOS["Comum"])
    faccao = normalizar_faccao(faccao)
    ov = Image.new("RGBA", (BASE_W * S, BASE_H * S), (0, 0, 0, 0))
    # 1) peças que ficam *atrás* do conteúdo
    _janela_arte(ov, est)
    _painel_texto(ov, est, faccao)
    _placa_titulo(ov, est)
    # 2) moldura externa (por último dos blocos grandes, para cobrir as bordas das placas)
    masc = _forma_moldura(raridade if raridade in ESTILOS else "Comum", est, faccao)
    _bisel_moldura(ov, masc, est)
    # Filete interno colorido: reforça a facção sem competir com o metal da raridade.
    f_est = FACCOES[faccao]
    aro_interno = ImageChops.subtract(_erodir(masc, 2.2), _erodir(masc, 3.35))
    _compor(ov, aro_interno, [f_est["cor"]], alpha=145)
    _decoracoes_moldura(ov, raridade if raridade in ESTILOS else "Comum", est)
    _decoracoes_faccao(ov, faccao, est)
    # 3) HUD
    _medalhao_poder(ov, est, especial)
    _emblema_faccao(ov, est, faccao)
    _gema_elemento(ov, est, tipo)
    if not especial:
        _chip_fileira(ov, est, fileira)
    _placa_raridade(ov, est, largura_raridade)
    return ov


@functools.lru_cache(maxsize=64)
def overlay_pronto(raridade: str, faccao: str, tipo: str, fileira: str, especial: bool,
                   largura_raridade: int, largura: int, altura: int) -> Image.Image:
    """Overlay já redimensionado e em cache: ele não depende do conteúdo da carta, só da
    combinação raridade/facção/elemento/fileira. Tratar o retorno como somente-leitura."""
    ov = construir_overlay(raridade=raridade, faccao=faccao, tipo=tipo, fileira=fileira,
                           especial=especial, largura_raridade=largura_raridade)
    if ov.size != (largura, altura):
        ov = ov.resize((largura, altura), Image.Resampling.LANCZOS)
    return ov


def aplicar_efeitos_arte(im: Image.Image, raridade: str, seed: int, X, Y) -> Image.Image:
    """Vinheta, brilho de borda, esmaecimento inferior e foil por raridade na janela da arte."""
    est = ESTILOS.get(raridade, ESTILOS["Comum"])
    W, H = im.size
    x1, y1, x2, y2 = X(JANELA[0]), Y(JANELA[1]), X(JANELA[2]), Y(JANELA[3])
    win = Image.new("L", (W, H), 0)
    ImageDraw.Draw(win).rectangle((x1, y1, x2, y2), fill=255)

    # vinheta escura + brilho da raridade nas bordas
    borda = win.filter(ImageFilter.GaussianBlur(max(6, X(18)))).point(lambda v: max(0, min(255, (255 - v) * 2)))
    borda = ImageChops.multiply(borda, win)
    esc = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    esc.putalpha(borda.point(lambda v: int(v * est["vinheta"])))
    im = Image.alpha_composite(im, esc)
    if est["brilho"]:
        glow = Image.new("RGBA", (W, H), (*est["cor"], 0))
        glow.putalpha(borda.point(lambda v: int(v * est["brilho"] / 255 * .75)))
        im = Image.alpha_composite(im, glow)

    # esmaecimento inferior: a arte "afunda" no painel de texto
    fade = Image.new("L", (W, H), 0)
    altura = max(1, Y(96))
    fade.paste(Image.linear_gradient("L").resize((x2 - x1, altura), Image.Resampling.BILINEAR), (x1, y2 - altura))
    fade = ImageChops.multiply(fade, win)
    sombra = Image.new("RGBA", (W, H), (4, 5, 8, 0))
    sombra.putalpha(fade.point(lambda v: int(v * .84)))
    im = Image.alpha_composite(im, sombra)

    rng = random.Random(seed ^ 0x5EED)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(camada)

    def faixa(cx0, larg, alpha, cor=(255, 255, 255)):
        pts = [(cx0, y1), (cx0 + larg, y1), (cx0 + larg - X(150), y2), (cx0 - X(150), y2)]
        cd.polygon(pts, fill=(*cor, alpha))

    if raridade in ("Rara", "Épica", "Lendária"):
        base = {"Rara": 22, "Épica": 34, "Lendária": 46}[raridade]
        faixa(x1 + X(210), X(34), base, _mix(est["luz"], (255, 255, 255), .5))
        faixa(x1 + X(270), X(12), base // 2, (255, 255, 255))
    elif raridade == "Mítica":
        arco = _gradiente((x2 - x1, y2 - y1), [(255, 110, 200), (170, 110, 255), (100, 210, 255), (255, 150, 220)], "diag")
        banda = Image.new("L", (W, H), 0)
        ImageDraw.Draw(banda).polygon([(x1 + X(120), y1), (x1 + X(300), y1), (x1 + X(140), y2), (x1 - X(40), y2)], fill=255)
        banda = banda.filter(ImageFilter.GaussianBlur(X(20))).point(lambda v: int(v * .24))
        cam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cam.paste(arco.convert("RGBA"), (x1, y1))
        cam.putalpha(ImageChops.multiply(banda, win))
        im = Image.alpha_composite(im, cam)
    elif raridade == "Primordial":
        ox, oy = (x1 + x2) // 2, y1 - Y(10)
        for k in range(-5, 6):
            a0 = math.radians(90 + k * 11 - 3)
            a1 = math.radians(90 + k * 11 + 3)
            r = Y(560)
            cd.polygon([(ox, oy), (ox + math.cos(a0) * r, oy + math.sin(a0) * r),
                        (ox + math.cos(a1) * r, oy + math.sin(a1) * r)], fill=(255, 236, 160, 24 if k % 2 else 14))
    elif raridade == "Singular":
        for yy in range(y1, y2, max(3, Y(4))):
            cd.line((x1, yy, x2, yy), fill=(120, 255, 238, 15), width=1)
        faixa(x1 + X(200), X(30), 40, (190, 255, 248))
        faixa(x1 + X(260), X(10), 24, (255, 255, 255))

    # brilhos (estrelas de 4 pontas) em posições estáveis para cada carta
    n = {"Rara": 0, "Épica": 3, "Lendária": 5, "Mítica": 8, "Primordial": 6, "Singular": 5}.get(raridade, 0)
    brilhos = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(brilhos)
    for _ in range(n):
        sx = rng.randint(x1 + X(24), x2 - X(24))
        sy = rng.randint(y1 + Y(20), y2 - Y(130))
        r = rng.choice((X(5), X(7), X(9)))
        pts = []
        for i in range(8):
            a = -math.pi / 2 + i * math.pi / 4
            rr = r if i % 2 == 0 else r * .2
            pts.append((sx + math.cos(a) * rr, sy + math.sin(a) * rr))
        bd.polygon(pts, fill=(255, 255, 255, 235))
        bd.ellipse((sx - 1, sy - 1, sx + 1, sy + 1), fill=(255, 255, 255, 255))
    halo = brilhos.filter(ImageFilter.GaussianBlur(max(2, X(4))))
    tinta = Image.new("RGBA", (W, H), (*est["luz"], 0))
    tinta.putalpha(halo.getchannel("A").point(lambda v: int(v * .7)))

    cam_alpha = ImageChops.multiply(camada.getchannel("A"), win)
    camada.putalpha(cam_alpha)
    im = Image.alpha_composite(im, camada)
    if n:
        im = Image.alpha_composite(im, tinta)
        ba = ImageChops.multiply(brilhos.getchannel("A"), win)
        brilhos.putalpha(ba)
        im = Image.alpha_composite(im, brilhos)
    return im
