"""Cartão de perfil em imagem (Pillow). Função pura: recebe números, devolve bytes PNG.

Sem discord.py e sem rede, então dá para testar e gerar prévias localmente.
Emojis NÃO são desenhados na imagem (as fontes comuns não têm); só texto, formas e cores.
"""
import io
import unicodedata

from PIL import Image, ImageDraw, ImageFont, ImageOps

LARGURA, ALTURA = 920, 440
OURO = (212, 175, 55)
FUNDO_TOPO, FUNDO_BASE = (24, 24, 27), (10, 10, 12)
TEXTO, TEXTO_SUAVE, TEXTO_FRACO = (245, 241, 226), (185, 188, 194), (130, 134, 142)
COR_RARIDADE = {
    "comum": (150, 152, 160),
    "rara": (86, 148, 226),
    "epica": (168, 108, 214),
    "lendaria": (212, 175, 55),
}

_CAMINHOS = {
    "bold": ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    "regular": ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    "italic": ("DejaVuSans-Oblique.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
}


def _fonte(estilo: str, tamanho: int):
    for caminho in _CAMINHOS[estilo]:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            continue
    try:  # Pillow >= 10.1 consegue escalar a fonte embutida; versões antigas só têm a miniatura
        return ImageFont.load_default(size=tamanho)
    except TypeError:
        return ImageFont.load_default()


def limpar_texto(texto: str) -> str:
    """Tira emojis e símbolos que a fonte não desenha (viram quadradinhos)."""
    saida = []
    for ch in str(texto):
        if ord(ch) > 0xFFFF or unicodedata.category(ch) in ("So", "Cs", "Cf", "Co", "Cn"):
            continue
        saida.append(ch)
    return " ".join("".join(saida).split())


def _caber(draw, texto, fonte, largura):
    """Corta o texto com reticências para caber na largura."""
    if draw.textlength(texto, font=fonte) <= largura:
        return texto
    while texto and draw.textlength(texto + "…", font=fonte) > largura:
        texto = texto[:-1]
    return texto.rstrip() + "…"


def _cor(valor) -> tuple[int, int, int]:
    return ((valor >> 16) & 255, (valor >> 8) & 255, valor & 255)


def _misturar(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _fundo():
    img = Image.new("RGB", (LARGURA, ALTURA), FUNDO_BASE)
    d = ImageDraw.Draw(img)
    for y in range(ALTURA):
        d.line([(0, y), (LARGURA, y)], fill=_misturar(FUNDO_TOPO, FUNDO_BASE, y / ALTURA))
    return img


def _avatar(dados_bytes, tamanho, cor, inicial):
    anel = 5
    total = tamanho + anel * 2
    saida = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    d = ImageDraw.Draw(saida)
    d.ellipse((0, 0, total - 1, total - 1), fill=cor)
    foto = None
    if dados_bytes:
        try:
            foto = ImageOps.fit(Image.open(io.BytesIO(dados_bytes)).convert("RGB"), (tamanho, tamanho),
                                method=Image.Resampling.LANCZOS)
        except Exception:
            foto = None
    if foto is None:  # sem avatar: círculo escuro com a inicial
        foto = Image.new("RGB", (tamanho, tamanho), (38, 38, 44))
        fd = ImageDraw.Draw(foto)
        f = _fonte("bold", tamanho // 2)
        w = fd.textlength(inicial, font=f)
        fd.text(((tamanho - w) / 2, tamanho * 0.22), inicial, font=f, fill=cor)
    mascara = Image.new("L", (tamanho, tamanho), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, tamanho - 1, tamanho - 1), fill=255)
    saida.paste(foto, (anel, anel), mascara)
    return saida


def render_cartao(dados: dict, avatar: bytes | None = None) -> bytes:
    """dados: nome, patente, nivel, xp_nivel, xp_necessario, fracao, cor (0xRRGGBB), tagline,
    platinas, zerados, runs, denarios, pos_xp, pos_platinas, conquistas [(nome, raridade)], desde, proxima."""
    cor = _cor(dados.get("cor", 0xD4AF37))
    img = _fundo()
    d = ImageDraw.Draw(img)

    # moldura: faixa lateral na cor da patente + borda dourada discreta
    d.rectangle((0, 0, 9, ALTURA), fill=cor)
    d.rectangle((1, 1, LARGURA - 2, ALTURA - 2), outline=_misturar(OURO, FUNDO_BASE, 0.55), width=1)

    nome = limpar_texto(dados.get("nome", "")) or "Gladiador"
    av = _avatar(avatar, 150, cor, nome[:1].upper())
    img.paste(av, (42, 36), av)

    x0 = 232
    largura_util = LARGURA - x0 - 40
    f_nome, f_pat, f_peq = _fonte("bold", 38), _fonte("bold", 18), _fonte("regular", 14)
    titulo = limpar_texto(dados.get("titulo", ""))
    if titulo:
        f_tit = _fonte("bold", 12)
        d.text((x0, 14), _caber(d, titulo.upper(), f_tit, largura_util), font=f_tit, fill=OURO)
    d.text((x0, 34), _caber(d, nome, f_nome, largura_util), font=f_nome, fill=TEXTO)
    d.text((x0, 86), f"{limpar_texto(dados.get('patente', '')).upper()}  ·  NÍVEL {dados.get('nivel', 1)}",
           font=f_pat, fill=cor)

    tagline = limpar_texto(dados.get("tagline", ""))
    if tagline:
        f_tag = _fonte("italic", 16)
        d.text((x0, 118), _caber(d, f"“{tagline}”", f_tag, largura_util), font=f_tag, fill=TEXTO_SUAVE)

    # barra de XP
    by, bh = 156, 20
    d.rounded_rectangle((x0, by, x0 + largura_util, by + bh), radius=10, fill=(40, 40, 46))
    fracao = max(0.0, min(1.0, dados.get("fracao", 0.0)))
    if fracao > 0:
        d.rounded_rectangle((x0, by, x0 + max(bh, int(largura_util * fracao)), by + bh), radius=10, fill=cor)
    xp_txt = f"{dados.get('xp_nivel', 0):,} / {dados.get('xp_necessario', 0):,} XP".replace(",", ".")
    d.text((x0, by + bh + 6), xp_txt, font=f_peq, fill=TEXTO_SUAVE)
    prox = dados.get("proxima")
    if prox:
        t = limpar_texto(prox)
        w = d.textlength(t, font=f_peq)
        d.text((x0 + largura_util - w, by + bh + 6), t, font=f_peq, fill=TEXTO_FRACO)

    # números
    caixas = [
        ("PLATINAS", str(dados.get("platinas", 0))),
        ("ZERADOS", str(dados.get("zerados", 0))),
        ("RUNS", str(dados.get("runs", 0))),
        ("DENÁRIOS", f"{dados.get('denarios', 0):,}".replace(",", ".")),
        ("RANK XP", f"#{dados['pos_xp']}" if dados.get("pos_xp") else "—"),
        ("RANK PLAT.", f"#{dados['pos_platinas']}" if dados.get("pos_platinas") else "—"),
    ]
    gap, y = 10, 232
    larg = (LARGURA - 42 - 38 - gap * (len(caixas) - 1)) // len(caixas)
    f_val, f_lab = _fonte("bold", 28), _fonte("bold", 11)
    for i, (rotulo, valor) in enumerate(caixas):
        x = 42 + i * (larg + gap)
        d.rounded_rectangle((x, y, x + larg, y + 78), radius=10, fill=(30, 30, 35), outline=(52, 52, 60))
        d.text((x + 14, y + 12), rotulo, font=f_lab, fill=TEXTO_FRACO)
        d.text((x + 14, y + 32), _caber(d, valor, f_val, larg - 24), font=f_val, fill=TEXTO)

    # conquistas
    d.text((42, 332), "CONQUISTAS", font=f_lab, fill=TEXTO_FRACO)
    conquistas = dados.get("conquistas") or []
    f_chip = _fonte("bold", 13)
    cx, cy = 42, 354
    if not conquistas:
        d.text((cx, cy + 6), "Nenhuma conquista ainda — registre uma platina, um zerado ou uma run.",
               font=f_peq, fill=TEXTO_FRACO)
    else:
        mostradas = 0
        for nome_c, raridade in conquistas:
            rot = limpar_texto(nome_c)
            w = int(d.textlength(rot, font=f_chip)) + 28
            if cx + w > LARGURA - 40 - 60 and mostradas < len(conquistas):
                break
            c = COR_RARIDADE.get(raridade, COR_RARIDADE["comum"])
            d.rounded_rectangle((cx, cy, cx + w, cy + 30), radius=15, fill=_misturar(FUNDO_BASE, c, 0.18), outline=c)
            d.ellipse((cx + 10, cy + 12, cx + 17, cy + 19), fill=c)
            d.text((cx + 22, cy + 7), rot, font=f_chip, fill=TEXTO)
            cx += w + 8
            mostradas += 1
        resto = len(conquistas) - mostradas
        if resto > 0:
            d.text((cx + 4, cy + 7), f"+{resto}", font=f_chip, fill=TEXTO_SUAVE)

    # rodapé
    rod = f"No Colizeu desde {dados['desde']}" if dados.get("desde") else ""
    d.text((42, ALTURA - 32), rod, font=f_peq, fill=TEXTO_FRACO)
    marca = "C O L I Z E U"
    d.text((LARGURA - 40 - d.textlength(marca, font=f_peq), ALTURA - 32), marca, font=f_peq, fill=OURO)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
