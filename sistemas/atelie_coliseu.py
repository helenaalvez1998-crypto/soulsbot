"""Regras do Ateliê de Cartas do Coliseu.

Gera prompts com direção artística híbrida: dark fantasy monumental e pictórico
com energia, silhuetas e efeitos de anime épico. A moldura oficial é aplicada
separadamente pelo renderizador do SoulsBot.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

ARTE_LARGURA = 1234
ARTE_ALTURA = 1000
TAMANHO_MAXIMO_UPLOAD = 8 * 1024 * 1024
PIXELS_MAXIMOS = 18_000_000

DIRECAO_ARTE = """
SOULSBOT COLISEUM — HYBRID MYTHIC DARK FANTASY / EPIC ANIME ART DIRECTION

CORE IDENTITY
Create premium collectible-card key art that combines the monumental, tragic,
ancient dark-fantasy atmosphere of modern mythic action RPG worlds with the
expressive energy and visual clarity of high-end epic anime illustration.
The result must feel like one coherent SoulsBot art universe: painterly and
material-rich environments, mythic scale, solemn atmosphere, but characters
with elegant readable silhouettes, expressive poses, decisive gesture lines,
and spectacular controlled supernatural effects. This is an original visual
identity, not a replica of any specific game's artwork, artist, anime, or IP.

PAINTING AND CHARACTER RENDERING
Use a deliberate 50/50 visual fusion of premium cinematic realism and mature
high-end anime illustration. Characters must have expressive anime-inspired
design language, striking readable eyes and faces, elegant shape design and
dynamic poses, while anatomy, proportions, skin, hair, armor, cloth, weapons,
stone, metal, glass and other materials receive realistic physically coherent
rendering. The environment should feel like a photorealistic dark-fantasy
film still, while the subject retains the visual impact and controlled
stylization of top-tier seinen / action-fantasy anime key art. Use finely
resolved micro-textures, crisp focal detail, nuanced gradients, natural
surface imperfections and believable material response. Target 4K-level
perceived detail and professional ultra-high-definition finish: clean edges,
well-defined forms, intricate but readable details, no pixelation, no blur,
no compression artifacts. Avoid flat cel shading, plastic CGI, chibi
proportions, generic mobile-game art, over-smoothed faces, waxy skin,
excessive outlines, muddy over-texturing and noisy detail. Stylized anatomy
must remain convincing and physically plausible.

WORLD, SCALE AND STORY
Build a layered mythic world: colossal ruined citadels, eroded temples,
cathedral arches, ancient bridges, petrified forests, vast battlefields,
forgotten thrones, shattered moons, underground sanctuaries, storm-wracked
cliffs or other environments chosen to fit the actual card concept. Add small
scale cues (distant towers, banners, birds, tiny figures, broken architecture)
when they reinforce scale. The image must communicate a specific event,
conflict, discovery or emotional beat—not merely a character standing in fog.
Use foreground, subject plane and distant background for cinematic depth.

CINEMATIC COMPOSITION
Landscape 5:4 illustration. One dominant focal subject or one clearly legible
story event. Use a deliberate camera angle (low-angle for imposing entities,
three-quarter action angle for combatants, intimate close framing for relics,
wide environmental composition for locations). Dynamic diagonals and flowing
cloth, hair, weapons, debris or energy may guide the eye toward the focal
point. Preserve clean negative space and safe margins around the main subject;
keep all important anatomy, weapon tips and magical forms inside the crop.
Readable at small card size. Avoid clutter, multiple competing focal points,
random floating objects and symmetrical poster poses unless the concept truly
calls for a ceremonial portrait.

LIGHT, COLOR AND ATMOSPHERE
Use dramatic motivated lighting: a clear key light, controlled rim light,
volumetric shafts, atmospheric perspective, selective bloom and deep but
readable shadows. Use a restrained base of charcoal, slate, weathered stone,
aged iron, muted bronze and antique gold. Introduce a deliberate accent palette
that supports the subject and card type; do not cover the entire image in one
monochrome filter. Magic and energy should illuminate nearby surfaces and
interact with smoke, rain, dust, snow, ash, water or debris. Particles must
support motion and scale, not become visual noise.

VISUAL QUALITY BAR
Ultra-premium 4K-quality game cinematic key art fused with mature anime
illustration and photorealistic dark-fantasy rendering. Film-grade composition,
exceptional character design, realistic anatomy and materials, intricate
micro-detail, sharp focal plane, controlled depth of field, nuanced HDR-like
lighting, rich but disciplined color grading, physically believable shadows,
volumetric atmosphere and polished professional finish. The image must look
like a high-budget anime feature film rendered with the material fidelity of
a realistic AAA game cinematic. Preserve clean readability at small card
size. Every card must have a distinct visual hook that can be described in
one sentence. Quality target describes detail and finish; do not add borders
or UI to simulate resolution.

CARD ART ONLY — STRICT OUTPUT RULES
Create only the illustration, not a finished card. Do NOT draw any border,
frame, card edge, title, lettering, numbers, stats, icons, rarity gem, UI,
logo, watermark, signature or text of any kind. Do not reserve a fake frame
inside the image. The SoulsBot renderer adds the official fixed rarity frame,
name, stats and ability separately. Keep important content away from the outer
edges so the official frame never covers it.
""".strip()

DIRETRIZES_CATEGORIA = {
    "chefe": (
        "SUBJECT DIRECTION — BOSS: depict one unforgettable boss entity or antagonist. "
        "Give it a unique silhouette, readable anatomy, a signature weapon/body feature, "
        "and a clear action or threatening gesture. Establish scale using architecture, "
        "terrain or a tiny environmental scale cue. Show what makes this foe dangerous; "
        "do not default to a generic armored knight."
    ),
    "arma": (
        "SUBJECT DIRECTION — WEAPON / RELIC: make one complete, unmistakable weapon or relic "
        "the protagonist. Show a strong three-quarter view and distinctive construction, "
        "wear, engravings, balance, material and history. Give it a small environmental "
        "story (embedded in stone, held by a spectral hand, resting on an altar, etc.). "
        "Energy effects must explain its power and must not obscure its silhouette."
    ),
    "magia": (
        "SUBJECT DIRECTION — SPELL / MAGIC: depict a specific supernatural event with a "
        "visible source, direction of movement and physical consequence in the environment. "
        "Use elegant anime-like energy trails and painterly light interaction. Avoid generic "
        "glowing orb, random runes or floating symbols as the entire subject."
    ),
    "covenant": (
        "SUBJECT DIRECTION — COVENANT / ORDER: tell the story of an oath, secret order or "
        "ancient faction through a ritual, confrontation, procession, shrine or group silhouette. "
        "Use one dominant emblematic object or figure and environmental clues to communicate "
        "the faction's values. Do not make it look like a flat logo or UI badge."
    ),
    "jogo": (
        "SUBJECT DIRECTION — GAME MILESTONE: depict a memorable original scene that expresses "
        "the emotional identity of the source game's journey. Choose a concrete visual moment: "
        "a final ascent, a quiet aftermath, a dangerous crossing, a discovery, a victory with "
        "a cost, or a world-changing event. Avoid a generic hero portrait."
    ),
    "patente": (
        "SUBJECT DIRECTION — RANK / ACHIEVEMENT: create a physical ceremonial relic, insignia, "
        "weapon, mantle or symbolic scene that communicates earned mastery. It must feel like "
        "an object from the SoulsBot world, not a digital badge, trophy icon or interface element."
    ),
    "reliquia": (
        "SUBJECT DIRECTION — PRIMORDIAL RELIC: portray an ancient object or entity that seems "
        "to predate the known world. Make its impossible age and power legible through scale, "
        "material, environmental reaction and restrained cosmic phenomena. Avoid generic galaxy "
        "backgrounds or a simple glowing crystal."
    ),
}

CORES_TIPO = {
    "Destreza": "cool spectral teal, moonlit silver and restrained cyan edge-light; agile flowing motion",
    "Força": "ember red, oxidized copper, furnace orange and heavy kinetic impact",
    "Magia": "muted violet, deep indigo, pale arcane white and elegant supernatural trails",
}

DIRETRIZES_RARIDADE = {
    "Comum": "RARITY INTENSITY — COMMON: grounded and intimate scale; one strong visual idea, restrained supernatural effects, believable worn materials and focused composition. Keep the same premium rendering quality; do not make it look unfinished or low-resolution.",
    "Rara": "RARITY INTENSITY — RARE: add a distinctive supernatural accent, unusual environmental detail or more dynamic action beat. The image should feel exceptional but still grounded in the world.",
    "Épica": "RARITY INTENSITY — EPIC: allow a more ambitious camera angle, layered magic, dramatic environmental reaction and a larger sense of scale. Keep one clear focal point and avoid visual clutter.",
    "Lendária": "RARITY INTENSITY — LEGENDARY: create a monumental, iconic moment with highly distinctive silhouette, elaborate environment, powerful controlled effects and memorable cinematic lighting. The subject should feel historically significant.",
    "Primordial": "RARITY INTENSITY — PRIMORDIAL: depict mythic, world-altering scale and an uncanny sense of ancient divinity. Use impossible architecture or cosmic/environmental distortion sparingly but powerfully. Preserve a readable central subject; grandeur must not become chaos.",
}

HABILIDADE_VISUAL = {
    "primeira_luz": "Visual motif for Primeira Luz: a decisive first ray of dawn cutting through darkness, illuminating the subject's leading edge.",
    "retaliacao": "Visual motif for Retaliação: a counterattack at the instant of reversal, with a sharp returning arc and displaced debris.",
    "impeto": "Visual motif for Ímpeto: forward momentum, streaming cloth and energy, with the environment pushed back by the charge.",
    "ultimo_folego": "Visual motif for Último Fôlego: a wounded but unbroken subject releasing one final concentrated burst of force; avoid gore.",
    "contragolpe": "Visual motif for Contragolpe: a precise strike slipping through a larger opponent's guard, emphasizing timing and agility.",
    "encadeamento": "Visual motif for Encadeamento: successive linked arcs or repeated motion echoes that form one elegant continuous attack path.",
    "adaptacao": "Visual motif for Adaptação: a transformation between two combat approaches, shown through contrasting motion or materials without splitting the image into panels.",
    "sangue_frio": "Visual motif for Sangue-frio: absolute composure amid chaos, with suspended particles and a calm, precise focal pose.",
    "instinto": "Visual motif for Instinto: a near-instinctive evasive or predatory movement, with a sharp gaze and subtle motion cues.",
    "precisao": "Visual motif for Precisão: one exact impact point, clean trajectory and carefully controlled energy; no random explosions.",
    "drenagem": "Visual motif for Drenagem: energy being drawn away through tendrils, fading light or flowing particles; keep the effect elegant and legible.",
    "cacador_arcano": "Visual motif for Caçador Arcano: a focused hunter confronting supernatural energy, with a precise countermeasure or ward.",
    "quebra_ritmo": "Visual motif for Quebra-ritmo: a sudden interruption of an opponent's motion, expressed by a broken energy trail or shattered rhythm in the environment.",
    "lei_primeva": "Visual motif for Lei Primeva: the first law of creation manifesting as ancient geometric light and primordial force.",
    "decreto_soberano": "Visual motif for Decreto Soberano: an imposing royal gesture or relic imposing order over a hostile force; regal, not ornamental UI.",
    "olho_tempestade": "Visual motif for Olho da Tempestade: a calm focal center surrounded by a vast spiraling storm, with controlled directional energy.",
    "fome_abismo": "Visual motif for Fome do Abismo: a deep void-like force pulling light and debris inward, with the subject still clearly visible.",
    "paradoxo_eterno": "Visual motif for Paradoxo Eterno: a visual contradiction of time, such as suspended fragments, repeated silhouettes or a fractured light path; no clocks or text.",
}

class ArteInvalida(ValueError):
    """Imagem não atende aos requisitos do Ateliê."""


@dataclass(frozen=True)
class ImagemNormalizada:
    dados: bytes
    largura: int
    altura: int
    formato: str = "JPEG"


def _valor_prompt(valor: Any, limite: int) -> str:
    texto = " ".join(str(valor or "").split())
    texto = "".join(ch for ch in texto if ch.isprintable())
    return texto.replace("<", "(").replace(">", ")").replace("`", "'")[:limite]


def gerar_prompt_carta(carta: dict[str, Any]) -> str:
    """Monta uma direção de arte específica para jogo, categoria, raridade e habilidade."""
    nome = _valor_prompt(carta.get("nome") or "Carta do Coliseu", 100)
    categoria_raw = _valor_prompt(carta.get("categoria") or "Carta", 60)
    categoria = categoria_raw.casefold()
    habilidade = _valor_prompt(carta.get("habilidade") or "", 60).casefold()
    raridade = _valor_prompt(carta.get("raridade") or "Rara", 30)
    tipo = _valor_prompt(carta.get("tipo") or "", 30)
    jogo = _valor_prompt(carta.get("jogo_origem") or carta.get("game_name") or "", 100)
    descricao = _valor_prompt(carta.get("descricao") or "", 500)

    diretriz = next(
        (texto for chave, texto in DIRETRIZES_CATEGORIA.items() if chave in categoria),
        "SUBJECT DIRECTION: depict one specific, memorable physical subject or story event derived from the card concept. Avoid generic fantasy hero imagery.",
    )
    cor = CORES_TIPO.get(tipo, "charcoal, antique silver and restrained arcane light")
    raridade_prompt = DIRETRIZES_RARIDADE.get(raridade, DIRETRIZES_RARIDADE["Rara"])
    habilidade_prompt = HABILIDADE_VISUAL.get(habilidade, "")

    if jogo:
        origem = (
            f'SOURCE GAME: "{jogo}". Use this title as a thematic and worldbuilding reference. '
            "Identify its broad genre, emotional tone, environmental motifs, architecture, climate, "
            "materials and symbolic themes. Translate those broad qualities into the SoulsBot hybrid "
            "dark-fantasy / epic-anime art direction. Create an original scene and original design. "
            "Do not reproduce official key art, screenshots, logos, exact locations, named copyrighted "
            "characters, signature costumes or a recognizable composition."
        )
    else:
        origem = (
            "SOURCE GAME: none. Invent a distinctive original mythic dark-fantasy subject that belongs "
            "to the SoulsBot Coliseum universe. Give it a specific story hook, not a generic fantasy trope."
        )

    contexto = f'CARD CONCEPT: "{nome}".\nCATEGORY: {categoria_raw}.\nTYPE: {tipo or "unassigned"}.\nRARITY: {raridade}.'
    if descricao:
        contexto += f'\nLORE / CONTEXT: "{descricao}".'

    extras: list[str] = []
    card_id = _valor_prompt(carta.get("id") or "", 120).casefold()
    if "jogo" in categoria and (card_id.endswith("_platina") or "eco da platina" in nome.casefold()):
        extras.append(
            "MILESTONE STORY: communicate complete mastery after overcoming the world's hardest trials. "
            "Show a solemn earned aftermath, a transformed landmark or a meaningful relic; never draw a trophy icon or completion UI."
        )
    elif "jogo" in categoria and (card_id.endswith("_zerado") or "alma desperta" in nome.casefold()):
        extras.append(
            "MILESTONE STORY: communicate the emotional end of a difficult journey. Show the protagonist's "
            "silhouette facing the consequence of victory, a final threshold, or a quiet world after the battle; avoid generic victory poses."
        )

    blocos = [DIRECAO_ARTE, origem, contexto, diretriz, raridade_prompt]
    if habilidade_prompt:
        blocos.append(f"ABILITY VISUAL STORYTELLING: {habilidade_prompt} This is a visual metaphor only; do not add text or symbols that resemble UI.")
    blocos.extend(extras)
    blocos.append(
        f"TYPE COLOR / MOTION LANGUAGE: {cor}. Use this as a controlled accent, not a full-image filter. "
        "Let the accent interact with the lighting, materials and atmosphere."
    )
    blocos.append(
        "FINAL ART DIRECTION CHECK: the image must have one specific visual hook, a readable silhouette, "
        "a deliberate cinematic camera angle, foreground/midground/background depth, motivated lighting, "
        "and a story beat that is unique to this card. Landscape 5:4. Artwork only. No frame, border, text, "
        "logo, watermark, stats or UI. The fixed official rarity frame is added by the SoulsBot renderer."
    )
    return "\n\n".join(blocos)


def normalizar_imagem_carta(dados: bytes) -> ImagemNormalizada:
    """Valida, remove metadados e padroniza a imagem em memória para o Discord."""
    if not dados:
        raise ArteInvalida("O arquivo está vazio. Envie uma imagem PNG, JPG ou WEBP.")
    if len(dados) > TAMANHO_MAXIMO_UPLOAD:
        raise ArteInvalida("A imagem ultrapassa 8 MB. Exporte uma versão menor e envie novamente.")

    try:
        with Image.open(io.BytesIO(dados)) as original:
            if getattr(original, "n_frames", 1) > 1:
                raise ArteInvalida("Envie uma imagem estática; GIFs e animações não são aceitos.")
            if original.format not in {"PNG", "JPEG", "WEBP"}:
                raise ArteInvalida("Formato não aceito. Utilize PNG, JPG ou WEBP.")
            largura, altura = original.size
            if largura < 512 or altura < 512:
                raise ArteInvalida("A imagem precisa ter pelo menos 512 × 512 pixels para manter a qualidade.")
            if largura > 6000 or altura > 6000 or largura * altura > PIXELS_MAXIMOS:
                raise ArteInvalida("A resolução é excessiva. Reduza a imagem para no máximo 18 megapixels.")

            orientada = ImageOps.exif_transpose(original)
            if orientada.mode in {"RGBA", "LA"} or "transparency" in orientada.info:
                camada = orientada.convert("RGBA")
                fundo = Image.new("RGBA", camada.size, (16, 19, 25, 255))
                fundo.alpha_composite(camada)
                imagem = fundo.convert("RGB")
            else:
                imagem = orientada.convert("RGB")
            imagem = ImageOps.fit(
                imagem,
                (ARTE_LARGURA, ARTE_ALTURA),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.48),
            )
            saida = io.BytesIO()
            imagem.save(saida, format="JPEG", quality=91, optimize=True, progressive=True)
            normalizada = saida.getvalue()
            if len(normalizada) > TAMANHO_MAXIMO_UPLOAD:
                saida = io.BytesIO()
                imagem.save(saida, format="JPEG", quality=84, optimize=True, progressive=True)
                normalizada = saida.getvalue()
            if len(normalizada) > TAMANHO_MAXIMO_UPLOAD:
                raise ArteInvalida("Não consegui reduzir a imagem o suficiente. Envie uma versão com menos detalhes ou resolução menor.")
            return ImagemNormalizada(normalizada, ARTE_LARGURA, ARTE_ALTURA)
    except ArteInvalida:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, SyntaxError, OverflowError) as exc:
        raise ArteInvalida("Não consegui abrir essa imagem. Envie um PNG, JPG ou WEBP válido.") from exc
