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
    # A raridade define o metal principal da moldura; a facção permanece como
    # cor secundária nos emblemas, filetes e no painel de habilidade.
    "Comum": dict(
        metal=[(238, 242, 245), (160, 174, 186), (91, 104, 118), (190, 201, 210), (76, 88, 102)],
        luz=(246, 249, 250), cor=(166, 181, 194), esc=(23, 29, 37),
        esp=8, brilho=0, vinheta=0.34),
    "Rara": dict(
        metal=[(218, 245, 255), (76, 174, 220), (24, 83, 133), (104, 204, 239), (18, 62, 108)],
        luz=(222, 248, 255), cor=(77, 180, 226), esc=(9, 29, 48),
        esp=10, brilho=42, vinheta=0.36),
    "Épica": dict(
        metal=[(248, 229, 255), (178, 119, 235), (91, 48, 151), (204, 150, 250), (65, 31, 112)],
        luz=(247, 230, 255), cor=(183, 126, 239), esc=(28, 15, 50),
        esp=11, brilho=72, vinheta=0.38),
    "Lendária": dict(
        metal=[(255, 248, 211), (239, 185, 75), (145, 87, 24), (255, 218, 112), (112, 65, 18)],
        luz=(255, 247, 205), cor=(239, 185, 75), esc=(39, 25, 10),
        esp=13, brilho=92, vinheta=0.40),
    "Mítica": dict(
        metal=[(255, 225, 220), (202, 58, 68), (91, 18, 30), (239, 105, 104), (58, 12, 24)],
        luz=(255, 226, 215), cor=(205, 61, 75), esc=(38, 10, 18),
        esp=13, brilho=100, vinheta=0.41),
    "Primordial": dict(
        metal=[(255, 255, 248), (232, 224, 190), (139, 131, 103), (255, 248, 218), (105, 100, 82)],
        luz=(255, 255, 245), cor=(239, 224, 174), esc=(34, 32, 25),
        esp=14, brilho=112, vinheta=0.42),
    "Singular": dict(
        metal=[(238, 236, 255), (130, 117, 170), (34, 37, 62), (112, 206, 203), (17, 21, 38)],
        luz=(248, 244, 255), cor=(151, 143, 206), esc=(9, 12, 24),
        esp=14, brilho=125, vinheta=0.43),
}

FACCOES: dict[str, dict] = {
    "Ordem Áurea": dict(cor=(229, 187, 83), metal=(250, 235, 181), esc=(46, 36, 16)),
    "Véu Carmesim": dict(cor=(190, 54, 68), metal=(246, 187, 184), esc=(43, 13, 18)),
    "Lua Sombria": dict(cor=(139, 112, 214), metal=(224, 215, 255), esc=(18, 15, 39)),
}

# Nomes antigos ainda podem existir em cartas salvas, decks e templates.
# Normalizamos antes de desenhar para nunca cair silenciosamente na Ordem Áurea.
_ALIASES_FACCAO = {
    "ordem aurea": "Ordem Áurea", "golden order": "Ordem Áurea",
    "veu carmesim": "Véu Carmesim", "dinastia mohgwyn": "Véu Carmesim",
    "mohgwyn": "Véu Carmesim", "blood dynasty": "Véu Carmesim",
    "lua sombria": "Lua Sombria", "casa cariana": "Lua Sombria",
    "cariana": "Lua Sombria", "carian": "Lua Sombria",
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
    """Selo da Lua Sombria: lua crescente, órbita e estrelas distantes."""
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
    """Silhueta externa própria de cada facção; o miolo da carta permanece intacto."""
    f = normalizar_faccao(faccao)
    # Os três perfis mudam a arquitetura do aro, não a janela da ilustração.
    if f == "Ordem Áurea":
        pts = [(3, 22), (22, 3), (174, 3), (210, 13), (246, 3), (398, 3),
               (417, 22), (417, 598), (398, 617), (246, 617), (210, 607),
               (174, 617), (22, 617), (3, 598)]
    elif f == "Véu Carmesim":
        pts = [(3, 12), (25, 3), (395, 3), (417, 12), (417, 150), (405, 170),
               (417, 190), (417, 286), (402, 310), (417, 334), (417, 430),
               (405, 450), (417, 470), (417, 608), (395, 617), (25, 617),
               (3, 608), (3, 470), (15, 450), (3, 430), (3, 334), (18, 310),
               (3, 286), (3, 190), (15, 170), (3, 150)]
    else:  # Lua Sombria: arcos ogivais e perfil de observatório astral.
        pts = [(3, 28), (24, 3), (158, 3), (184, 18), (210, 3), (236, 18),
               (262, 3), (396, 3), (417, 28), (417, 592), (396, 617),
               (262, 617), (236, 602), (210, 617), (184, 602), (158, 617),
               (24, 617), (3, 592)]
    # Escala em torno do centro para gerar o recorte interno com espessura uniforme.
    fator = 1.0 - (inset / 420.0)
    return [(210 + (x - 210) * fator, 310 + (y - 310) * fator) for x, y in pts]


def _forma_moldura(rar: str, est: dict, faccao: str = "Ordem Áurea") -> Image.Image:
    """Máscara (255 = metal) do aro externo + ornamentos próprios de cada raridade."""
    t = est["esp"]
    W, H = BASE_W, BASE_H
    cx = W / 2

    def fn(d):
        # ---------- aro base: arquitetura determinada pela facção ----------
        # O mesmo perfil é usado nas sete raridades; cada raridade acrescenta
        # seus próprios metais, gemas e ornamentos sem apagar a identidade da facção.
        d.polygon(_p(_pontos_arquitetura_faccao(faccao, 0)), fill=255)
        d.polygon(_p(_pontos_arquitetura_faccao(faccao, t)), fill=0)

        # ---------- ornamentos ----------
        if rar == "Rara":
            # aba superior/inferior com gema + cantoneiras em losango
            for y0, s in ((3, 1), (H - 3, -1)):
                d.polygon(_p([(cx - 30, y0), (cx + 30, y0), (cx + 22, y0 + s * 18),
                              (cx, y0 + s * 26), (cx - 22, y0 + s * 18)]), fill=255)
            for x, y in ((14, 14), (W - 14, 14), (14, H - 14), (W - 14, H - 14)):
                d.polygon(_p([(x, y - 11), (x + 11, y), (x, y + 11), (x - 11, y)]), fill=255)
            for x in (3 + t / 2, W - 3 - t / 2):
                d.polygon(_p([(x, H / 2 - 24), (x + (7 if x < cx else -7), H / 2), (x, H / 2 + 24),
                              (x - (7 if x < cx else -7), H / 2)]), fill=255)
        elif rar == "Épica":
            # estilhaços de cristal nos quatro cantos
            for (px, py, sx, sy) in ((3, 3, 1, 1), (W - 3, 3, -1, 1), (3, H - 3, 1, -1), (W - 3, H - 3, -1, -1)):
                for ang, comp in ((14, 46), (45, 34), (76, 46)):
                    a = math.radians(ang)
                    ux, uy = math.cos(a) * sx, math.sin(a) * sy
                    nx, ny = -uy, ux
                    bx, by = px + ux * 4, py + uy * 4
                    d.polygon(_p([(bx + nx * 4.4, by + ny * 4.4), (bx - nx * 4.4, by - ny * 4.4),
                                  (px + ux * comp, py + uy * comp)]), fill=255)
            # espinhos centrais
            for y0, s in ((3, 1), (H - 3, -1)):
                d.polygon(_p([(cx - 26, y0), (cx + 26, y0), (cx + 8, y0 + s * 20), (cx, y0 + s * 34),
                              (cx - 8, y0 + s * 20)]), fill=255)
        elif rar == "Lendária":
            # coroa no topo, pétalas nos cantos, volutas nas laterais
            d.polygon(_p([(cx - 40, 3), (cx + 40, 3), (cx + 34, 22), (cx - 34, 22)]), fill=255)
            d.polygon(_p([(cx - 40, 18), (cx - 34, 2), (cx - 18, 14), (cx, 0), (cx + 18, 14), (cx + 34, 2),
                          (cx + 40, 18)]), fill=255)
            for x, y in ((16, 16), (W - 16, 16), (16, H - 16), (W - 16, H - 16)):
                d.ellipse(_box((x - 13, y - 13, x + 13, y + 13)), fill=255)
                for k in range(8):
                    a = k * math.pi / 4
                    d.ellipse(_box((x + math.cos(a) * 14 - 4, y + math.sin(a) * 14 - 4,
                                    x + math.cos(a) * 14 + 4, y + math.sin(a) * 14 + 4)), fill=255)
            for sx in (1, -1):
                bx = 3 + t / 2 if sx == 1 else W - 3 - t / 2
                for y in (190, 300, 410):
                    pts = []
                    for k in range(-8, 9):
                        u = k / 8
                        pts.append((bx + 8.5 * (1 - u * u), y + u * 21))
                    pts += [(bx - 8.5 * (1 - (k / 8) ** 2), y + (k / 8) * 21) for k in range(8, -9, -1)]
                    d.polygon(_p(pts), fill=255)
            for y0, s in ((H - 3, -1),):
                d.polygon(_p([(cx - 44, y0), (cx + 44, y0), (cx + 32, y0 + s * 18), (cx - 32, y0 + s * 18)]), fill=255)
        elif rar == "Mítica":
            # órbita estelar: arco interno com contas, estrelas nos cantos
            for x, y, rr in ((cx, 14, 15), (cx, H - 14, 15), (14, H / 2, 10), (W - 14, H / 2, 10)):
                d.ellipse(_box((x - rr, y - rr, x + rr, y + rr)), fill=255)
            for sx in (3 + t / 2, W - 3 - t / 2):
                for y in range(100, H - 90, 54):
                    if abs(y - H / 2) < 28:
                        continue
                    d.ellipse(_box((sx - 4, y - 4, sx + 4, y + 4)), fill=255)
            for x, y in ((18, 18), (W - 18, 18), (18, H - 18), (W - 18, H - 18)):
                d.polygon(_p([(x, y - 17), (x + 5, y - 5), (x + 17, y), (x + 5, y + 5), (x, y + 17),
                              (x - 5, y + 5), (x - 17, y), (x - 5, y - 5)]), fill=255)
        elif rar == "Primordial":
            # discos solares no eixo, runas em losango nas laterais
            for y in (11, H - 11):
                d.ellipse(_box((cx - 21, y - 21, cx + 21, y + 21)), fill=255)
            for sx in (3 + t / 2 + 1, W - 3 - t / 2 - 1):
                for y in range(120, H - 100, 62):
                    d.polygon(_p([(sx, y - 10), (sx + 7, y), (sx, y + 10), (sx - 7, y)]), fill=255)
            for x, y in ((9, 9), (W - 9, 9), (9, H - 9), (W - 9, H - 9)):
                d.ellipse(_box((x - 9, y - 9, x + 9, y + 9)), fill=255)
        elif rar == "Singular":
            # assinatura assimétrica: cunha superior-esquerda, circuito à direita
            d.polygon(_p([(3, 3), (150, 3), (126, 22), (22, 22), (22, 130), (3, 154)]), fill=255)
            d.polygon(_p([(W - 3, H - 3), (W - 150, H - 3), (W - 126, H - 22), (W - 22, H - 22),
                          (W - 22, H - 130), (W - 3, H - 154)]), fill=255)
            d.polygon(_p([(W - 3, 170), (W - 22, 186), (W - 22, 330), (W - 3, 346)]), fill=255)
            for y in (210, 262, 314):
                d.ellipse(_box((W - 15, y - 4, W - 7, y + 4)), fill=0)
        elif rar == "Comum":
            pass

    return _mascara(fn)


def _bisel_moldura(ov, mascara, est):
    """Pinta o metal da moldura com bisel (luz no topo-esquerda, sombra na base-direita)."""
    # contorno escuro para destacar do fundo
    contorno = mascara.filter(ImageFilter.MaxFilter(5))
    _compor(ov, contorno, [(6, 7, 10)], alpha=235)
    _compor(ov, mascara, est["metal"], "diag")
    d = max(1, int(S * 1.1))
    claro = ImageChops.subtract(mascara, ImageChops.offset(mascara, d, d))
    escuro = ImageChops.subtract(mascara, ImageChops.offset(mascara, -d, -d))
    _compor(ov, claro, [est["luz"]], alpha=215)
    _compor(ov, escuro, [(0, 0, 0)], alpha=140)
    # brilho interno suave: um segundo anel mais fino dentro do metal
    interna = _erodir(mascara, 2.0)
    miolo = ImageChops.subtract(interna, _erodir(interna, 0.9))
    _compor(ov, miolo, [est["luz"]], alpha=40)


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
    glifo = {"Ordem Áurea": _g_erdtree, "Lua Sombria": _g_lua, "Véu Carmesim": _g_sangue}.get(faccao, _g_arcano)
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
    """Heráldica temática discreta: a facção aparece também nos cantos e filetes."""
    faccao = normalizar_faccao(faccao)
    d = ImageDraw.Draw(ov)
    cor = FACCOES[faccao]["cor"]
    metal = FACCOES[faccao]["metal"]
    # Desenho em coordenadas-base, ampliadas pelo supersampling.
    def line(points, fill, width=1.0):
        d.line(_p(points), fill=(*fill[:3], fill[3] if len(fill) > 3 else 150), width=max(1, int(width*S)), joint="curve")
    def gem(x, y, r=2.2):
        d.polygon(_p([(x,y-r*1.8),(x+r,y),(x,y+r*1.8),(x-r,y)]), fill=(*metal,185))
    if faccao == "Ordem Áurea":
        # Ramos dourados e pequenas folhas: iconografia da Térvore e do voto áureo.
        for side in (-1, 1):
            x = 13 if side < 0 else BASE_W-13
            pts = [(x, 205), (x+side*5, 224), (x, 244), (x+side*5, 264), (x, 284),
                   (x+side*5, 304), (x, 324), (x+side*5, 344), (x, 364)]
            line(pts, (*cor,115), 1.1)
            for yy in (230, 270, 310, 350):
                d.ellipse(_box((x-3, yy-5, x+3, yy+1)), outline=(*metal,170), width=max(1,S))
            gem(x, 185, 2.0)
    elif faccao == "Véu Carmesim":
        # Espinhos e gotas rituais, como um selo de sangue gravado no metal.
        for side in (-1, 1):
            x = 13 if side < 0 else BASE_W-13
            for yy in (205, 250, 295, 340, 385):
                line([(x,yy-15),(x+side*5,yy-5),(x,yy+4),(x+side*6,yy+13)], (*cor,135), 1.25)
                line([(x+side*3,yy-5),(x+side*10,yy-12)], (*metal,135), .8)
                d.polygon(_p([(x,yy+7),(x-2.2,yy+12),(x,yy+16),(x+2.2,yy+12)]), fill=(*cor,175))
    elif faccao == "Lua Sombria":
        # Órbitas lunares e estrelas de quatro pontas.
        for side in (-1, 1):
            x = 14 if side < 0 else BASE_W-14
            d.arc(_box((x-9, 205, x+9, 250)), 65 if side < 0 else 115, 295 if side < 0 else 245,
                  fill=(*cor,145), width=max(1,S))
            d.arc(_box((x-7, 278, x+7, 330)), 235, 55, fill=(*metal,110), width=max(1,S))
            for yy in (220, 285, 350):
                d.polygon(_p([(x, yy-5), (x+1.8, yy-1.8), (x+5, yy),
                              (x+1.8, yy+1.8), (x, yy+5), (x-1.8, yy+1.8),
                              (x-5, yy), (x-1.8, yy-1.8)]), fill=(*metal,185))




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
