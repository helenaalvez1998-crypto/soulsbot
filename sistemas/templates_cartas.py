"""Templates completos de carta (um por raridade) usados nas cartas com arte enviada.

Cada template é um PNG RGBA 840 × 1240: fundo e placas opacos, com somente a janela
exata da ilustração transparente. Os cinco templates padrão são distribuídos em
`assets/cartas_templates`; uploads administrativos em DATA_DIR/cartas_templates os
substituem sem alterar os arquivos do projeto.

O layout dos textos é compartilhado e fixo. A janela transparente precisa coincidir
com `LAYOUT_PADRAO["arte"]`, pois os demais campos não devem mudar por raridade.
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
# Imagens enviadas podem ter poucos pixels de diferença no canvas, mas a janela deve
# coincidir com o guia para que os textos e os elementos da carta não se desloquem.
TOLERANCIA_PROPORCAO = 0.005
TOLERANCIA_JANELA_PX = 3
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

_CACHE: dict[str, tuple[str, int, int, Image.Image, dict[str, Any]]] = {}
_LOCK = threading.RLock()


class TemplateInvalido(ValueError):
    """Mensagem pensada para ser mostrada ao proprietário do bot."""


# ---------------------------------------------------------------- caminhos
def pasta_templates() -> Path:
    return get_data_dir() / "cartas_templates"


def caminho_template_persistente(raridade: str) -> Path:
    """Caminho de um template enviado pelo proprietário (volume persistente)."""
    slug = RARIDADES_TEMPLATE.get(str(raridade))
    if not slug:
        raise ValueError(f"Raridade sem template configurável: {raridade}")
    return pasta_templates() / f"{slug}.png"


def caminho_template_embutido(raridade: str) -> Path:
    """Template padrão distribuído junto com o código do SoulsBot."""
    slug = RARIDADES_TEMPLATE.get(str(raridade))
    if not slug:
        raise ValueError(f"Raridade sem template configurável: {raridade}")
    return Path(__file__).resolve().parents[1] / "assets" / "cartas_templates" / f"{slug}.png"


def caminho_template(raridade: str) -> Path:
    """Retorna o upload válido ou o template padrão incluído no projeto."""
    persistente = caminho_template_persistente(raridade)
    if persistente.is_file():
        try:
            processar_template(persistente.read_bytes())
            return persistente
        except (OSError, TemplateInvalido):
            pass
    return caminho_template_embutido(raridade)


def caminho_layout_raridade(raridade: str) -> Path:
    # Overrides de coordenadas são sempre persistentes e nunca modificam os assets inclusos.
    return caminho_template_persistente(raridade).with_suffix(".json")


def listar_templates() -> dict[str, bool]:
    return {raridade: carregar_template(raridade) is not None for raridade in RARIDADES_TEMPLATE}


def origem_template(raridade: str) -> str | None:
    """Origem efetiva; uploads antigos inválidos não substituem o padrão do projeto."""
    persistente = caminho_template_persistente(raridade)
    embutido = caminho_template_embutido(raridade)
    if persistente.is_file():
        try:
            processar_template(persistente.read_bytes())
            return "personalizado"
        except (OSError, TemplateInvalido):
            return "padrão (upload inválido ignorado)" if embutido.is_file() else "inválido"
    if embutido.is_file():
        return "padrão"
    return None


def limpar_cache_templates(raridade: str | None = None) -> None:
    with _LOCK:
        if raridade is None:
            _CACHE.clear()
        else:
            _CACHE.pop(str(raridade), None)


# ---------------------------------------------------------------- layout
def carregar_layout(raridade: str | None = None) -> dict[str, Any]:
    """Retorna uma cópia do guia oficial; coordenadas antigas em JSON são ignoradas.

    A geometria é única para as cinco raridades. Ajustar slots por raridade faria os
    dados escritos pelo renderizador divergirem do guia e não é mais permitido.
    """
    return json.loads(json.dumps(LAYOUT_PADRAO))


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
    esperado = LAYOUT_PADRAO["arte"]
    diferencas = [abs(atual - padrao) for atual, padrao in zip((x1, y1, x2, y2), esperado)]
    if any(delta > TOLERANCIA_JANELA_PX for delta in diferencas):
        raise TemplateInvalido(
            "A janela transparente não coincide com o guia oficial: use exatamente "
            "56,256 → 784,846 (728 × 590 px). As placas e textos dependem dessas coordenadas."
        )
    recorte = alfa.crop((x1, y1, x2, y2)).histogram()
    transparentes = sum(recorte[:limite])
    if transparentes / max(1, janela_w * janela_h) < 0.90:
        raise TemplateInvalido(
            "A janela da arte não é um retângulo limpo. Há pedaços da moldura ou do fundo dentro dela, ou "
            "o magenta não ficou chapado."
        )
    return [x1, y1, x2, y2]


def _validar_opacidade(imagem: Image.Image, janela: list[int]) -> None:
    """Exige uma janela limpa e superfícies sólidas fora dela.

    Pequenas franjas de alpha dentro da janela ou transparência fora dela podem criar
    halos e vazamentos na composição. Os templates são cartas completas, não overlays.
    """
    alfa = imagem.getchannel("A")
    largura, altura = imagem.size
    x1, y1, x2, y2 = janela
    hist_total = alfa.histogram()
    hist_janela = alfa.crop((x1, y1, x2, y2)).histogram()
    total_janela = (x2 - x1) * (y2 - y1)
    total_fora = largura * altura - total_janela

    transparentes_janela = sum(hist_janela[:16])
    if transparentes_janela / max(1, total_janela) < 0.995:
        raise TemplateInvalido(
            "A janela da arte precisa estar totalmente limpa: pelo menos 99,5% dos pixels com alpha 0. "
            "Não deixe textura, reflexos ou partes da moldura dentro da área transparente."
        )

    opacos_fora = hist_total[255] - hist_janela[255]
    if opacos_fora / max(1, total_fora) < 0.995:
        raise TemplateInvalido(
            "Fora da janela da arte o template precisa ser opaco (alpha 255): fundo, placas e moldura "
            "devem formar uma carta completa. Não envie uma borda isolada nem cantos transparentes."
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
    destino = caminho_template_persistente(raridade)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".png.tmp")
    imagem.save(temporario, format="PNG", optimize=True)
    temporario.replace(destino)
    limpar_cache_templates(raridade)
    return destino, janela


def remover_template(raridade: str) -> bool:
    """Remove o upload personalizado e restaura o template padrão incluso no projeto."""
    caminho = caminho_template_persistente(raridade)
    existia = caminho.is_file()
    if existia:
        caminho.unlink(missing_ok=True)
    limpar_cache_templates(raridade)
    return existia


def carregar_template(raridade: str) -> tuple[Image.Image, dict[str, Any]] | None:
    """Carrega um template validado; se um upload antigo estiver inválido, usa o padrão.

    A janela é detectada e validada contra o guia oficial. Nenhum JSON legado pode
    deslocar os textos ou a ilustração para compensar uma placa fora de posição.
    """
    if raridade not in RARIDADES_TEMPLATE:
        return None

    candidatos = [caminho_template_persistente(raridade), caminho_template_embutido(raridade)]
    vistos: set[str] = set()
    with _LOCK:
        for caminho in candidatos:
            try:
                if not caminho.is_file():
                    continue
                origem_path = str(caminho.resolve())
                if origem_path in vistos:
                    continue
                vistos.add(origem_path)
                info = caminho.stat()
            except OSError:
                continue

            existente = _CACHE.get(raridade)
            if (existente and existente[0] == origem_path
                    and existente[1] == info.st_mtime_ns and existente[2] == info.st_size):
                return existente[3].copy(), json.loads(json.dumps(existente[4]))

            try:
                imagem, janela = processar_template(caminho.read_bytes())
                layout = carregar_layout(raridade)
                layout["arte"] = janela
            except (OSError, TemplateInvalido, ValueError):
                # Um upload persistente inválido não deve inutilizar a raridade:
                # tenta o template oficial incluído no próprio pacote.
                _CACHE.pop(raridade, None)
                continue

            _CACHE[raridade] = (
                origem_path, info.st_mtime_ns, info.st_size, imagem.copy(),
                json.loads(json.dumps(layout)),
            )
            return imagem, layout

    limpar_cache_templates(raridade)
    return None

