"""Templates completos de carta (um por raridade) usados nas cartas com arte enviada.

Um template é um PNG 840 × 1240 *opaco*, com fundo, moldura e as placas vazias de cada
informação (nome, poder, tipo, custo, habilidade). Somente a janela da arte é
transparente. O bot cola a arte do membro por trás do template e escreve os textos nas
posições definidas pelo layout (`LAYOUT_PADRAO`, sobrescrevível por arquivos JSON).

Este módulo cuida de armazenar, validar, detectar a janela e carregar o layout. O desenho
das cartas continua em `arte_cartas.py`. As cartas sem arte enviada não usam templates.
"""
from __future__ import annotations

import io
import json
import threading
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFilter

from runtime_paths import get_data_dir

RARIDADES_TEMPLATE = {
    "Comum": "comum",
    "Rara": "rara",
    "Épica": "epica",
    "Lendária": "lendaria",
    "Primordial": "primordial",
}
TAMANHO_TEMPLATE = (840, 1240)
TAMANHO_MINIMO = (420, 620)
TAMANHO_MAXIMO_BYTES = 8 * 1024 * 1024
PIXELS_MAXIMOS = 20_000_000
# Geradores de imagem raramente entregam exatamente 420:620; até 6% é esticado com segurança.
TOLERANCIA_PROPORCAO = 0.06
FORMATOS_ACEITOS = {"PNG", "JPEG", "WEBP"}

# Coordenadas na grade de referência 840 × 1240.
LAYOUT_PADRAO: dict[str, Any] = {
    "raridade": [600, 44, 784, 96],
    "nome": [56, 100, 784, 236],
    "arte": [56, 256, 784, 846],
    "poder": {"centro": [144, 986], "raio": 78},
    "tipo": [254, 918, 780, 978],
    "custo": [254, 992, 780, 1052],
    "habilidade": [56, 1084, 784, 1176],
}
CAMPOS_RETANGULO = ("raridade", "nome", "arte", "tipo", "custo", "habilidade")

_CACHE: dict[str, tuple[int, int, Image.Image, dict[str, Any]]] = {}
_LOCK = threading.RLock()


class TemplateInvalido(ValueError):
    """Mensagem pensada para ser mostrada ao proprietário do bot."""


# ---------------------------------------------------------------- caminhos
def pasta_templates() -> Path:
    return get_data_dir() / "cartas_templates"


def caminho_template(raridade: str) -> Path:
    slug = RARIDADES_TEMPLATE.get(str(raridade))
    if not slug:
        raise ValueError(f"Raridade sem template configurável: {raridade}")
    return pasta_templates() / f"{slug}.png"


def caminho_layout_raridade(raridade: str) -> Path:
    return caminho_template(raridade).with_suffix(".json")


def listar_templates() -> dict[str, bool]:
    return {raridade: caminho_template(raridade).is_file() for raridade in RARIDADES_TEMPLATE}


def limpar_cache_templates(raridade: str | None = None) -> None:
    with _LOCK:
        if raridade is None:
            _CACHE.clear()
        else:
            _CACHE.pop(str(raridade), None)


# ---------------------------------------------------------------- layout
def _retangulo_valido(valor: Any) -> list[int] | None:
    try:
        x1, y1, x2, y2 = (int(round(float(n))) for n in valor)
    except (TypeError, ValueError):
        return None
    largura, altura = TAMANHO_TEMPLATE
    if not (0 <= x1 < x2 <= largura and 0 <= y1 < y2 <= altura):
        return None
    return [x1, y1, x2, y2]


def _ler_json(caminho: Path) -> dict[str, Any]:
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dados if isinstance(dados, dict) else {}


def _aplicar_override(layout: dict[str, Any], override: dict[str, Any]) -> None:
    for campo in CAMPOS_RETANGULO:
        retangulo = _retangulo_valido(override.get(campo))
        if retangulo:
            layout[campo] = retangulo
    poder = override.get("poder")
    if isinstance(poder, dict):
        try:
            cx, cy = (int(round(float(n))) for n in poder.get("centro", ()))
            raio = int(round(float(poder.get("raio", 0))))
        except (TypeError, ValueError):
            return
        if 20 <= raio <= 200 and 0 <= cx <= TAMANHO_TEMPLATE[0] and 0 <= cy <= TAMANHO_TEMPLATE[1]:
            layout["poder"] = {"centro": [cx, cy], "raio": raio}


def carregar_layout(raridade: str | None = None) -> dict[str, Any]:
    """Layout padrão + `layout.json` global + `<raridade>.json` (cada um opcional)."""
    layout = json.loads(json.dumps(LAYOUT_PADRAO))
    _aplicar_override(layout, _ler_json(pasta_templates() / "layout.json"))
    if raridade in RARIDADES_TEMPLATE:
        _aplicar_override(layout, _ler_json(caminho_layout_raridade(str(raridade))))
    return layout


# ---------------------------------------------------------------- janela
def _parece_magenta(pixel: tuple[int, ...]) -> bool:
    r, g, b = pixel[:3]
    return r >= 190 and b >= 190 and g <= 110


def _aplicar_chroma_magenta(imagem: Image.Image) -> Image.Image:
    """Troca o magenta (#FF00FF) por transparência, inclusive as bordas suavizadas."""
    r, g, b, a = imagem.split()
    forte = ImageChops.multiply(
        ImageChops.multiply(r.point(lambda v: 255 if v >= 195 else 0), b.point(lambda v: 255 if v >= 195 else 0)),
        g.point(lambda v: 255 if v <= 95 else 0),
    )
    # Franja: pixels rosados vizinhos da área removida (anti-aliasing do gerador).
    vizinhanca = forte.filter(ImageFilter.MaxFilter(7))
    rosado = ImageChops.multiply(
        ImageChops.subtract(r, g).point(lambda v: 255 if v >= 55 else 0),
        ImageChops.subtract(b, g).point(lambda v: 255 if v >= 55 else 0),
    )
    franja = ImageChops.multiply(vizinhanca, rosado)
    remover = ImageChops.lighter(forte, franja)
    novo_alfa = ImageChops.subtract(a, remover)
    imagem = imagem.copy()
    imagem.putalpha(novo_alfa)
    return imagem


def detectar_janela(imagem: Image.Image) -> list[int]:
    """Retângulo transparente da arte, a partir do centro do slot de arte padrão."""
    largura, altura = imagem.size
    alfa = imagem.getchannel("A")
    ax1, ay1, ax2, ay2 = LAYOUT_PADRAO["arte"]
    sx = int((ax1 + ax2) / 2 * largura / TAMANHO_TEMPLATE[0])
    sy = int((ay1 + ay2) / 2 * altura / TAMANHO_TEMPLATE[1])
    pixels = alfa.load()
    limite = 16
    if pixels[sx, sy] >= limite:
        raise TemplateInvalido(
            "A janela da arte não está transparente no centro da carta. Deixe a área da arte vazia "
            "(transparente ou preenchida com magenta chapado #FF00FF)."
        )
    esquerda = direita = sx
    while esquerda > 0 and pixels[esquerda - 1, sy] < limite:
        esquerda -= 1
    while direita < largura - 1 and pixels[direita + 1, sy] < limite:
        direita += 1
    topo = base = sy
    while topo > 0 and pixels[sx, topo - 1] < limite:
        topo -= 1
    while base < altura - 1 and pixels[sx, base + 1] < limite:
        base += 1
    x1, y1, x2, y2 = esquerda, topo, direita + 1, base + 1
    janela_w, janela_h = x2 - x1, y2 - y1

    if x1 <= int(largura * 0.02) or x2 >= int(largura * 0.98) or y1 <= int(altura * 0.02) or y2 >= int(altura * 0.98):
        raise TemplateInvalido(
            "A área transparente encosta nas bordas da imagem. A moldura precisa envolver a janela da arte."
        )
    if not (0.40 <= janela_w / largura <= 0.96 and 0.20 <= janela_h / altura <= 0.72):
        raise TemplateInvalido(
            "A janela da arte tem um tamanho fora do esperado (use a do guia: cerca de 87% da largura e 48% da altura)."
        )
    if not (0.85 <= janela_w / janela_h <= 1.9):
        raise TemplateInvalido("A janela da arte precisa ter formato horizontal próximo de 5:4.")
    recorte = alfa.crop((x1, y1, x2, y2)).histogram()
    transparentes = sum(recorte[:limite])
    if transparentes / max(1, janela_w * janela_h) < 0.90:
        raise TemplateInvalido(
            "A janela da arte não é um retângulo limpo. Há pedaços da moldura ou do fundo dentro dela, ou "
            "o magenta não ficou chapado."
        )
    return [x1, y1, x2, y2]


def _validar_opacidade(imagem: Image.Image, janela: list[int]) -> None:
    alfa = imagem.getchannel("A")
    largura, altura = imagem.size
    x1, y1, x2, y2 = janela
    total_fora = largura * altura - (x2 - x1) * (y2 - y1)
    opacos_total = sum(alfa.histogram()[200:])
    opacos_janela = sum(alfa.crop((x1, y1, x2, y2)).histogram()[200:])
    if (opacos_total - opacos_janela) / max(1, total_fora) < 0.90:
        raise TemplateInvalido(
            "Fora da janela da arte o template precisa ser opaco (carta completa, com fundo e moldura). "
            "Para enviar só uma borda, use o painel de Molduras fixas."
        )


# ---------------------------------------------------------------- salvar / carregar
def processar_template(dados: bytes) -> tuple[Image.Image, list[int]]:
    """Valida o arquivo e devolve o template normalizado (840 × 1240) e a janela detectada."""
    if not dados or len(dados) > TAMANHO_MAXIMO_BYTES:
        raise TemplateInvalido("O arquivo precisa ter conteúdo e no máximo 8 MB.")
    try:
        with Image.open(io.BytesIO(dados)) as origem:
            formato = origem.format
            if formato not in FORMATOS_ACEITOS:
                raise TemplateInvalido("Envie o template em PNG (ou JPG/WEBP, se o magenta estiver chapado).")
            largura, altura = origem.size
            if largura * altura > PIXELS_MAXIMOS:
                raise TemplateInvalido("A imagem excede 20 milhões de pixels. Exporte em 840 × 1240.")
            if largura < TAMANHO_MINIMO[0] or altura < TAMANHO_MINIMO[1]:
                raise TemplateInvalido("A resolução mínima é 420 × 620 pixels; prefira 840 × 1240.")
            alvo = TAMANHO_TEMPLATE[0] / TAMANHO_TEMPLATE[1]
            desvio = abs((largura / altura) - alvo) / alvo
            if desvio > TOLERANCIA_PROPORCAO:
                raise TemplateInvalido(
                    f"A proporção da imagem ({largura} × {altura}) está longe da carta (420:620). "
                    "Recorte ou gere em retrato 840 × 1240."
                )
            imagem = origem.convert("RGBA")
    except TemplateInvalido:
        raise
    except Exception as exc:
        raise TemplateInvalido("Não consegui abrir o arquivo. Envie uma imagem PNG válida.") from exc

    if imagem.size != TAMANHO_TEMPLATE:
        imagem = imagem.resize(TAMANHO_TEMPLATE, Image.Resampling.LANCZOS)
    cx = int((LAYOUT_PADRAO["arte"][0] + LAYOUT_PADRAO["arte"][2]) / 2)
    cy = int((LAYOUT_PADRAO["arte"][1] + LAYOUT_PADRAO["arte"][3]) / 2)
    pixel = imagem.getpixel((cx, cy))
    if pixel[3] >= 16 and _parece_magenta(pixel):
        imagem = _aplicar_chroma_magenta(imagem)
    janela = detectar_janela(imagem)
    _validar_opacidade(imagem, janela)
    return imagem, janela


def salvar_template(raridade: str, dados: bytes) -> tuple[Path, list[int]]:
    imagem, janela = processar_template(dados)
    destino = caminho_template(raridade)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".png.tmp")
    imagem.save(temporario, format="PNG", optimize=True)
    temporario.replace(destino)
    limpar_cache_templates(raridade)
    return destino, janela


def remover_template(raridade: str) -> bool:
    caminho = caminho_template(raridade)
    existia = caminho.is_file()
    if existia:
        caminho.unlink(missing_ok=True)
    limpar_cache_templates(raridade)
    return existia


def carregar_template(raridade: str) -> tuple[Image.Image, dict[str, Any]] | None:
    """Template RGBA 840 × 1240 + layout efetivo, ou `None` se a raridade não tem template.

    A janela da arte vem da detecção no próprio PNG (a menos que um JSON a sobrescreva), de modo
    que o encaixe segue sempre a imagem aprovada, mesmo que o gerador tenha errado alguns pixels.
    """
    if raridade not in RARIDADES_TEMPLATE:
        return None
    caminho = caminho_template(raridade)
    try:
        info = caminho.stat()
    except OSError:
        limpar_cache_templates(raridade)
        return None
    with _LOCK:
        existente = _CACHE.get(raridade)
        if existente and existente[0] == info.st_mtime_ns and existente[1] == info.st_size:
            return existente[2].copy(), json.loads(json.dumps(existente[3]))
        try:
            with Image.open(caminho) as arquivo:
                imagem = arquivo.convert("RGBA")
            if imagem.size != TAMANHO_TEMPLATE:
                imagem = imagem.resize(TAMANHO_TEMPLATE, Image.Resampling.LANCZOS)
            layout = carregar_layout(raridade)
            override_arte = _retangulo_valido(_ler_json(caminho_layout_raridade(raridade)).get("arte"))
            if not override_arte:
                try:
                    layout["arte"] = detectar_janela(imagem)
                except TemplateInvalido:
                    pass  # mantém a janela do layout padrão
        except (OSError, ValueError):
            _CACHE.pop(raridade, None)
            return None
        _CACHE[raridade] = (info.st_mtime_ns, info.st_size, imagem.copy(), json.loads(json.dumps(layout)))
        return imagem, layout
