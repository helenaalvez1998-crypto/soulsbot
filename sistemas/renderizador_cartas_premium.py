"""Composição premium por camadas para cartas do Narabot.

O módulo é leve: Pillow já é dependência do renderizador existente. Templates são
assets estáticos locais; nenhuma IA, rede ou banco é acionado durante a partida.
A primeira skin finalizada é Ordem Áurea. Facções sem template continuam usando
com segurança o renderizador legado até receberem seus próprios assets.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

TEMPLATE_POR_FACCAO = {
    "Ordem Áurea": "template_ordem_aurea_overlay.png",
}
ASSET_RARIDADE = {
    "Comum": "comum.webp", "Rara": "rara.webp", "Épica": "epica.webp",
    "Lendária": "lendaria.webp", "Mítica": "mitica.webp",
    "Primordial": "primordial.webp", "Singular": "singular.webp",
}
JANELA_ARTE = (185, 190, 1007, 844)  # coordenadas no master 1024x1536


def _fonte(tamanho: int, negrito: bool = False, italico: bool = False):
    candidatos = []
    base = Path(__file__).resolve().parents[1] / "fonts"
    if italico:
        candidatos.append(base / "DejaVuSerif-Italic.ttf")
    elif negrito:
        candidatos.append(base / "DejaVuSerif-Bold.ttf")
    else:
        candidatos.append(base / "DejaVuSerif.ttf")
    for caminho in candidatos:
        if caminho.exists():
            return ImageFont.truetype(str(caminho), max(8, int(tamanho)))
    return ImageFont.load_default()


def _texto_ajustado(draw, texto: str, max_largura: int, tamanho: int, minimo: int = 10,
                    negrito: bool = False):
    for tam in range(int(tamanho), int(minimo)-1, -1):
        f = _fonte(tam, negrito=negrito)
        if draw.textbbox((0, 0), texto, font=f)[2] <= max_largura:
            return f
    return _fonte(minimo, negrito=negrito)


def _quebrar(draw, texto: str, fonte, largura: int, max_linhas: int = 3):
    palavras = str(texto or "").split()
    linhas, atual = [], ""
    for palavra in palavras:
        teste = f"{atual} {palavra}".strip()
        if draw.textbbox((0,0), teste, font=fonte)[2] <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        while linhas[-1] and draw.textbbox((0,0), linhas[-1] + "…", font=fonte)[2] > largura:
            linhas[-1] = linhas[-1][:-1]
        linhas[-1] = linhas[-1].rstrip() + "…"
    return linhas


def _recolorir_medalhao(imagem: Image.Image, raridade: str):
    """Adapta o esmalte do medalhão preservando metal, relevo e geometria do asset."""
    paletas = {
        "Comum": ((130,145,157),(205,214,220)),
        "Rara": ((16,76,130),(76,185,245)),
        "Épica": ((70,30,120),(194,125,255)),
        "Lendária": ((105,56,10),(255,194,65)),
        "Mítica": ((24,45,130),(105,180,255)),
        "Primordial": ((90,35,20),(255,120,65)),
        "Singular": ((42,20,85),(235,210,255)),
    }
    base, luz = paletas.get(raridade, paletas["Comum"])
    # Apenas o interior da gema/medalhão é tingido; ouro da estrutura permanece.
    badge = imagem.crop((830, 0, 1024, 245)).convert("RGB")
    px = badge.load()
    for y in range(badge.height):
        for x in range(badge.width):
            r,g,b = px[x,y]
            # O interior original é violeta escuro. Pixels dourados/prateados do aro ficam intactos.
            if b > r * 1.12 and b > g * 1.02 and r < 145 and g < 130:
                brilho = min(1.0, max(0.0, (r+g+b)/420))
                cor = tuple(int(base[i]*(1-brilho)+luz[i]*brilho) for i in range(3))
                px[x,y] = cor
    imagem.paste(badge, (830,0))


def compor_carta_premium(card: dict[str, Any], base_card: Image.Image,
                         largura: int, altura: int, illustration_bytes: bytes | None = None) -> Image.Image | None:
    """Usa a arte já produzida pelo motor e aplica o template premium se disponível."""
    faccao = str(card.get("faccao") or "")
    arquivo = TEMPLATE_POR_FACCAO.get(faccao)
    if not arquivo:
        return None
    caminho = Path(__file__).resolve().parents[1] / "assets" / "cartas" / "premium" / arquivo
    if not caminho.is_file():
        return None
    master = Image.open(caminho).convert("RGBA")
    if illustration_bytes:
        import io
        with Image.open(io.BytesIO(illustration_bytes)) as src:
            arte_origem = src.convert("RGB")
    else:
        # Recorte central evita copiar os antigos medalhões laterais do renderer legado.
        arte_origem = base_card.convert("RGB").crop((118, 92, 354, 468))
    ax1,ay1,ax2,ay2 = JANELA_ARTE
    arte = ImageOps.fit(arte_origem, (ax2-ax1, ay2-ay1), method=Image.Resampling.LANCZOS,
                        centering=(0.5,0.43)).convert("RGBA")
    fundo = Image.new("RGBA", master.size, (8,8,10,255))
    fundo.alpha_composite(arte, (ax1,ay1))
    master = Image.alpha_composite(fundo, master)
    if master.size != (largura,altura):
        master=master.resize((largura,altura),Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(master, "RGBA")
    sx, sy = largura/1024, altura/1536
    def pt(x,y): return (int(x*sx),int(y*sy))
    def font_px(master_px, minimum=8): return max(minimum,int(master_px*min(sx,sy)))
    creme=(248,239,218,255); dourado=(244,202,112,255)
    suave=(225,216,198,255); sombra=(5,5,6,240)

    # Medalhão: cada raridade usa uma arte própria, não apenas uma troca de cor.
    raridade=str(card.get("raridade") or "Comum")
    rar=raridade.upper()
    badge_name=ASSET_RARIDADE.get(raridade,ASSET_RARIDADE["Comum"])
    badge_path=Path(__file__).resolve().parents[1] / "assets" / "cartas" / "premium" / "raridades" / badge_name
    if badge_path.is_file():
        with Image.open(badge_path) as badge_src:
            badge=ImageOps.fit(badge_src.convert("RGB"),(int(190*sx),int(235*sy)),
                               method=Image.Resampling.LANCZOS,centering=(0.5,0.5))
        master.paste(badge,(int(830*sx),0))
        draw=ImageDraw.Draw(master,"RGBA")

    def text_center(texto, x, y, fonte, fill=creme, stroke=1):
        draw.text(pt(x,y),texto,font=fonte,fill=fill,anchor="mm",stroke_width=stroke,stroke_fill=sombra)

    # Cabeçalho e nome, com texto sempre derivado do catálogo.
    text_center("NARABOT  •  CRÔNICAS DO ENTRE-TERRAS  •",512,43,_fonte(font_px(23)),creme)
    nome=str(card.get("nome") or "Carta")
    f_nome=_texto_ajustado(draw,nome,int(largura*.64),font_px(48),font_px(34),True)
    text_center(nome,512,123,f_nome,creme,2)
    # Poder e tipo de combate na coluna esquerda, como na referência.
    if str(card.get("categoria", "Unidade")).casefold() != "especial":
        text_center(str(int(card.get("poder",0) or 0)),147,354,_fonte(font_px(94),True),creme,2)
    try:
        from .arte_cartas import _draw_type_icon
        from .molduras_cartas import ELEMENTOS
        icone=Image.new("RGBA",(80,80),(0,0,0,0))
        # A faixa e o escudo representam a fileira de combate; não o atributo da carta.
        tipo_icone = {"melee":"Força", "ranged":"Destreza", "siege":"Magia"}.get(str(card.get("fileira") or "melee"),"Força")
        cor=ELEMENTOS.get(tipo_icone,ELEMENTOS["Força"])["claro"]
        _draw_type_icon(ImageDraw.Draw(icone,"RGBA"),(40,40),tipo_icone,cor)
        icone=icone.resize((int(74*sx),int(74*sy)),Image.Resampling.LANCZOS)
        master.alpha_composite(icone,(int(120*sx),int(440*sy)))
        draw=ImageDraw.Draw(master,"RGBA")
    except Exception:
        pass
    row=str(card.get("fileira") or "melee")
    rotulos={"melee":"CORPO A CORPO","ranged":"LONGA DISTÂNCIA","siege":"CERCO"}
    tipo_fileira=rotulos.get(row,"TÁTICA")
    faction_name=faccao.upper()
    text_center(faction_name,250,907,_texto_ajustado(draw,faction_name,int(largura*.30),font_px(35),font_px(22),True),dourado,1)
    text_center(tipo_fileira,782,907,_texto_ajustado(draw,tipo_fileira,int(largura*.32),font_px(34),font_px(17),True),creme,1)

    # Mecânica e lore são obtidos em campos separados; nenhum texto de regra é inventado.
    try:
        from .gwent import preparar_carta
        preparada=preparar_carta(card)
        nome_hab=str(preparada.get("habilidade_nome") or "Habilidade")
        texto_hab=str(preparada.get("habilidade_texto") or "")
        texto_rar=str(preparada.get("raridade_texto") or "")
        raridade_ativa=bool(preparada.get("potencia_raridade_ativa"))
    except Exception:
        nome_hab=str(card.get("habilidade_nome") or "Habilidade")
        texto_hab=str(card.get("habilidade_texto") or "")
        texto_rar=""; raridade_ativa=False
    lore=str(card.get("descricao") or "")
    left=int(185*sx); max_width=int(790*sx)
    y=int(1010*sy)
    f_titulo=_texto_ajustado(draw,nome_hab,max_width,font_px(49),font_px(22),True)
    draw.text((left,y),nome_hab,font=f_titulo,fill=creme,stroke_width=1,stroke_fill=sombra)
    y+=int(48*sy)
    f_efeito=_fonte(font_px(34))
    linhas=_quebrar(draw,texto_hab,f_efeito,max_width,3)
    for linha in linhas:
        draw.text((left,y),linha,font=f_efeito,fill=suave,stroke_width=1,stroke_fill=sombra)
        y+=int(34*sy)
    if texto_rar and raridade_ativa:
        y+=int(5*sy)
        draw.line((int(145*sx),y,int(950*sx),y),fill=(196,151,74,220),width=max(1,int(2*sx)))
        y+=int(29*sy)
        titulo=f"BÔNUS DA RARIDADE ({rar.upper()})"
        draw.text((left,y),titulo,font=_fonte(font_px(25),True),fill=dourado,stroke_width=1,stroke_fill=sombra)
        y+=int(29*sy)
        texto_rar=texto_rar.replace(f"Raridade {raridade}: ", "").replace(f"Raridade {raridade}: ", "")
        for linha in _quebrar(draw,texto_rar,_fonte(font_px(25)),max_width,2):
            draw.text((left,y),linha,font=_fonte(font_px(25)),fill=creme,stroke_width=1,stroke_fill=sombra)
            y+=int(25*sy)
    if lore and y < int(1240*sy):
        lore_linhas=_quebrar(draw,lore,_fonte(font_px(22),italico=True),int(820*sx),2)
        y_lore=int(1245*sy)
        lore_linhas=_quebrar(draw,lore,_fonte(font_px(20),italico=True),int(820*sx),1)
        for i,linha in enumerate(lore_linhas):
            draw.text((largura//2,y_lore+i*int(22*sy)),linha,font=_fonte(font_px(22),italico=True),
                      fill=suave,anchor="mm",stroke_width=1,stroke_fill=sombra)
    return master.convert("RGB")
