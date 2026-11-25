"""Contrato comum de direção de arte para todos os prompts visuais do NARABOT.

A análise é apresentada em português; o prompt e o negative prompt são entregues
em inglês para uso direto em geradores de imagem. Este módulo não gera imagens.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

ASPECT_RATIO = "5:4"
ART_WIDTH = 1200
ART_HEIGHT = 960


def _text(value: Any, limit: int = 1000) -> str:
    value = re.sub(r"[\x00-\x1f\x7f]", " ", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _multiline(value: Any, limit: int = 24000) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text)
    return text.strip()[:limit]


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


FACTIONS = {
    "ordem aurea": "Ordem Áurea",
    "veu carmesim": "Véu Carmesim",
    "lua negra": "Lua Negra",
}


def normalizar_faccao(valor: Any) -> str:
    """Resolve somente os três valores oficiais do campo faccao; nunca infere pela lore."""
    return FACTIONS.get(_norm(_text(valor, 100)), "")


def direcao_faccao(valor: Any) -> str:
    """Direção visual compartilhada. A entrada deve vir exclusivamente de card['faccao']."""
    canonical = normalizar_faccao(valor)
    directions = {
        "Ordem Áurea": (
            "FACTION ART STANDARD — ORDEM ÁUREA (LIGHT, LAW AND FAITH): this is a NARABOT deck faction, not proof that the named subject is canonically a member of the Golden Order. "
            "Faction signature: majesty, order, nobility, spirituality and sacred authority. Use aged gold, solar yellow, warm ivory, muted bronze and neutral weathered stone as a controlled palette. "
            "Express the faction primarily through motivated golden or warm reflected light, environmental atmosphere, monumental but weathered stone, restrained sacred geometry and subtle background motifs. "
            "Leyndell, Altus Plateau, Erdtree-related architecture, temples or processional spaces may be selected only when the character's canonical identity or card lore supports that location. "
            "Do not automatically add angel wings, halos, a giant Erdtree, a paladin archetype or a full-frame gold filter. The faction must never recolor, replace or redesign canonical armor, garments, skin, hair, weapons or signature equipment."
        ),
        "Véu Carmesim": (
            "FACTION ART STANDARD — VÉU CARMESIM (BLOOD, SACRIFICE AND HERESY): this is a NARABOT deck faction, not a claim that every card subject is an official member of Mohg's blood dynasty. "
            "Faction signature: blood, violence, combat, mystery, lineage and dark elegance. Use deep crimson, blood red, claret, oxblood, blackened iron, tarnished silver and neutral ash-grey as controlled environmental and lighting accents. "
            "Express the faction through dramatic motivated red reflections, deep shadows, severe atmosphere, restrained heraldic or ritual context only when supported, and a fitting fortress, noble estate, battlefield, ruin or ceremonial environment selected from the card's actual story. "
            "Do not automatically make the subject a vampire, assassin, blood mage or demon; do not add horns, tridents, gore, bloodflame or blood magic without explicit card support. Never recolor or redesign canonical armor, garments, skin, hair, weapons or signature equipment."
        ),
        "Lua Negra": (
            "FACTION ART STANDARD — LUA NEGRA (MAGIC, COSMOS AND SECRETS): this is a NARABOT deck faction, not proof that the named subject canonically belongs to the Carian royal family or a lunar order. "
            "Faction signature: mystery, darkness, cold, lunar forces, melancholy and restrained supernatural atmosphere. Use deep blue, lunar blue, blue-grey, silver, cold white and blue-black as controlled environmental and lighting accents. "
            "Express the faction through motivated moonlight, cool reflections, mist, deep shadows and ancient ruins, night landscapes, observatories or Carian architecture only when supported by the card's actual identity and lore. "
            "Do not automatically turn the subject into a wizard, sorcerer or lunar entity; do not add a moon, starfield, glintstone spell, runes or magical aura without explicit support. Never recolor or redesign canonical armor, garments, skin, hair, weapons or signature equipment."
        ),
    }
    if canonical:
        return directions[canonical]
    raw = _text(valor, 100) or "blank"
    return (
        f"FACTION FIELD VALIDATION: the card's faccao field is '{raw}', which does not match one of the game's exactly three official factions: "
        "Ordem Áurea, Véu Carmesim or Lua Negra. Do not infer or assign a faction from the character name, lore, appearance, abilities, affinities or synergies. "
        "Do not create a fourth faction. Keep faction-specific heraldry, uniform, palette and allegiance neutral until the actual faccao field is corrected."
    )


# Referências explícitas para personagens/identidades recorrentes. A referência
# só é aplicada quando o nome ou a lore identifica o sujeito sem ambiguidade.
CANONICAL_REFERENCES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("ranni", "ranni the witch", "ranni bruxa"),
     "Ranni the Witch: preserve her canonical blue four-armed doll body, blue skin, long red hair, broad dark pointed witch hat and layered blue-white robes. Her four arms are a defining anatomical feature; do not humanize or alter her silhouette."),
    (("malenia", "blade of miquella", "lamina de miquella"),
     "Malenia, Blade of Miquella: preserve her copper-red hair, winged gold helm, ornate worn gold armor and canonical gold prosthetic limbs. Scarlet Rot traits may appear only when the card's story or ability calls for them; do not replace her with a generic valkyrie."),
    (("radahn", "starscourge radahn", "flagelo das estrelas"),
     "Starscourge Radahn: preserve his enormous red-haired demigod silhouette, battered lion-decorated armor, twin colossal curved greatswords and his small exhausted horse Leonard when depicting his canonical mounted appearance. Gravity effects require an explicit card-supported moment."),
    (("godfrey", "first elden lord", "primeiro lorde pristino"),
     "Godfrey, First Elden Lord: preserve his towering broad warrior build, long pale-gold hair, weathered face, heavy fur mantle, massive greataxe and Serosh as the spectral lion draped across his shoulders when that canonical aspect is depicted."),
    (("maliketh", "black blade", "lamina negra"),
     "Maliketh, the Black Blade: preserve his lean towering beast-clergyman anatomy, pale mane, dark layered armor and the distinctive Black Blade. Do not turn him into a human knight or an ordinary wolf."),
    (("messmer", "impaler", "empalador"),
     "Messmer the Impaler: preserve his pale red-haired demigod appearance, serpentine eye, ornate dark red and black armor, long spear and the great serpent when the canonical aspect is relevant. Do not replace this with a generic fire knight."),
    (("hoslow", "house hoslow", "casa hoslow"),
     "House Hoslow: use the recognizable fitted polished silver plate with fine floral/petal engraving, precise gauntlets, restrained dark red-brown cape and paired long flexible thorned whips when depicting a House Hoslow duelist. Do not substitute ordinary swords."),
    (("gurranq", "beast clergyman", "clerigo bestial"),
     "Gurranq, Beast Clergyman: preserve the hunched beastman anatomy, animalistic muzzle, clawed hands and austere dark layered cleric robes. Do not turn him into a human wizard."),
    (("black knife assassin", "assassino da faca negra", "assassina da faca negra"),
     "Black Knife Assassin: preserve the compact hooded silhouette, concealed face, close-fitting dark armor and characteristic curved Black Knife. Keep the face hidden; do not add unrelated blades."),
    (("blaidd", "half wolf", "meio lobo"),
     "Blaidd: preserve the recognizable wolf-headed warrior silhouette, grey fur, heavy dark armor and oversized greatsword. Do not humanize the head or replace his weapon with a generic sword."),
    (("mohg", "lord of blood", "senhor do sangue"),
     "Mohg, Lord of Blood: preserve his imposing horned Omen anatomy, ritual garments and characteristic trident when depicting the canonical character. Bloodflame is allowed only when the scene or card ability supports it; avoid gratuitous gore."),
    (("rykard", "lord of blasphemy", "senhor da blasfemia"),
     "Rykard, Lord of Blasphemy: preserve the colossal serpent-lord anatomy and the visual relationship between the blasphemous serpent and the embedded great blade. Do not depict an ordinary humanoid knight."),
)


def canonical_reference(card: dict[str, Any]) -> str:
    haystack = _norm(" ".join((_text(card.get("nome"), 200), _text(card.get("descricao") or card.get("lore"), 1200))))
    for aliases, reference in CANONICAL_REFERENCES:
        if any((" " + _norm(alias) + " ") in (" " + haystack + " ") for alias in aliases):
            return reference
    return (
        "CANONICAL IDENTITY CHECK: first determine whether the exact named character, creature, weapon, spell or place exists in Elden Ring. "
        "When it does, preserve its recognizable in-game model, silhouette, proportions, species, face, armor, clothing, equipment, signature weapon and canonical traits. "
        "Do not create an alternate version or substitute a generic role archetype. If the exact identity cannot be established from the supplied facts, do not invent canon; create only a restrained original subject fully consistent with the Lands Between and keep unknown physical details neutral."
    )


def gerar_analise_artistica(
    card: dict[str, Any],
    *,
    scene_reference: str = "",
    faction_direction: str = "",
    has_ability: bool | None = None,
    ability_name: str = "",
    ability_rule: str = "",
) -> str:
    """Cria a análise artística em português. A facção vem somente de card['faccao']."""
    name = _text(card.get("nome") or card.get("name") or "Carta sem nome", 160)
    category = _text(card.get("categoria") or card.get("category") or "não informada", 80)
    faction_raw = _text(card.get("faccao"), 80)
    faction = normalizar_faccao(faction_raw) or (faction_raw or "não informada")
    rarity = _text(card.get("raridade") or card.get("rarity") or "não informada", 60)
    card_type = _text(card.get("tipo") or card.get("type") or "não informado", 60)
    description = _text(card.get("descricao") or card.get("lore") or "", 1200)
    power = _text(card.get("poder") if card.get("poder") is not None else "não informado", 30)
    power_max = _text(card.get("poder_maximo") or card.get("max_power") or "não informado", 30)
    function = _text(card.get("funcao_tatica") or card.get("funcao") or card.get("papel_gwent") or "não informada", 100)
    row = _text(card.get("fileira") or "não informada", 40)
    archetype = _text(card.get("arquetipo") or card.get("epiteto") or "não informado", 140)
    affinities = card.get("afinidades") or card.get("afinidade_dominante") or "não informadas"
    if isinstance(affinities, (list, tuple, set)):
        affinities = ", ".join(_text(x, 80) for x in list(affinities)[:8]) or "não informadas"
    else:
        affinities = _text(affinities, 180)
    synergies = card.get("sinergias") or card.get("sinergia") or card.get("synergies") or []
    if isinstance(synergies, (list, tuple, set)):
        synergies = ", ".join(_text(x.get("nome") or x.get("name") or x, 100) if isinstance(x, dict) else _text(x, 100) for x in list(synergies)[:8]) or "não informadas"
    else:
        synergies = _text(synergies, 240)
    if has_ability is None:
        has_ability = bool(_text(ability_name, 100) or _text(ability_rule, 300))
    ability_summary = (
        f"Habilidade: {_text(ability_name, 100) or 'habilidade registrada'}. Interpretação: {_text(ability_rule, 300) or 'representar somente o efeito documentado'}."
        if has_ability else "Habilidade: nenhuma habilidade especial registrada; não adicionar magia, aura, runas ou poderes artificiais."
    )
    lore_line = f"Lore: {description}" if description else "Lore: sem descrição narrativa suficiente; não preencher lacunas com biografia inventada."
    return "\n".join((
        f"ANÁLISE ARTÍSTICA — {name} ({category}).",
        "Universo: Elden Ring / Terras Intermédias. Identificar primeiro o sujeito literal e preservar seu modelo canônico, quando reconhecível.",
        f"Facção identificada exclusivamente pelo campo FACÇÃO: {faction}.",
        f"Direção de facção: {direcao_faccao(faction_raw)}",
        f"Identidade e narrativa: {lore_line}",
        f"Classificação: raridade {rarity}; tipo {card_type}; arquétipo/função {archetype}; função tática {function}; fileira {row}.",
        f"Atributos de jogo: poder {power}/{power_max}; calibrar competência, sem transformar números em efeitos visuais.",
        ability_summary,
        f"Afinidades: {affinities}; são contexto secundário e não determinam a facção.",
        f"Sinergias: {synergies}; são contexto complementar, não exigem personagens adicionais.",
        "Hierarquia: universo Elden Ring → modelo original do personagem → facção → identidade individual da carta → lore → cenário e composição → complementos artísticos.",
        "Cena: " + (_text(scene_reference, 1000) if scene_reference else "criar um instante próprio a partir do nome e da lore, sem inventar fatos canônicos."),
        "Composição: ilustração horizontal em proporção exata 5:4; protagonista e equipamento integralmente dentro das margens seguras.",
    ))

def gerar_negative_prompt(card: dict[str, Any], *, has_ability: bool = True) -> str:
    """Negative prompt global + restrições específicas derivadas da carta."""
    base = [
        "generic medieval fantasy, generic fantasy knight, stock fantasy character, wrong Elden Ring character, alternate redesign of a canonical character, inaccurate face, inaccurate species, inaccurate silhouette, incorrect armor, incorrect clothing, incorrect signature weapon",
        "non-Elden-Ring universe, other game franchise, anime, manga, cartoon, cel shading, chibi, science fiction, futuristic armor, cyberpunk, modern clothing",
        "invented biography, unsupported rank, unsupported heraldry, unsupported faction membership, random castle, random cathedral, random dragon, random skulls, unrelated creatures, unrelated companions, extra characters not required by the card story",
        "random weapon, duplicate weapons, weapon incompatible with the named character, malformed weapon grip, impossible armor construction, floating equipment, broken anatomy, extra limbs, extra fingers, fused fingers, malformed hands, asymmetrical eyes, distorted face, incorrect proportions",
        "unmotivated magic, random runes, floating symbols, magical aura without lore support, excessive glow, neon, oversaturated color filter, excessive bloom, visual clutter, confusing silhouette, collage, split panels, multiple vignettes",
        "text, letters, typography, numbers, stats, title, logo, watermark, signature, card frame, card border, card edge, rarity gem, game UI, interface, mockup",
        "glossy CGI, plastic armor, waxy skin, airbrushed face, artificial microtexture, excessive pores, random scratches, film grain, digital noise, speckling, dithering, pixelation, compression artifacts, oversharpening, HDR halos, muddy detail",
    ]
    if not has_ability:
        base.append("spellcasting, magical attack, supernatural aura, energy beam, energy trail, floating glintstone, unexplained glow, invented elemental effect, artificial power")
    name = _norm(_text(card.get("nome") or card.get("name"), 180))
    faction = _norm(_text(card.get("faccao"), 80))
    if faction == _norm("Ordem Áurea"):
        base.append("generic angel, angel wings, excessive halo, full-frame gold filter, fantasy paladin stereotype")
    elif faction == _norm("Véu Carmesim"):
        base.append("automatic vampire traits, horns, trident, gratuitous gore, blood magic without explicit card support")
    elif faction == _norm("Lua Negra"):
        base.append("generic wizard robe, compulsory starfield, neon magic, science-fiction interface, cyberpunk elements")
    if "hoslow" in name:
        base.append("ordinary sword, greatsword, oversized plate armor, crown, horns, vampire design, blood splatter, gore, invented blood magic")
    if "ranni" in name:
        base.append("two arms, human skin, red-haired human woman without doll anatomy, missing canonical witch hat")
    if "malenia" in name:
        base.append("ordinary human limbs, missing prosthetic limbs, unrelated helmet, generic angel wings")
    return "; ".join(base)


def montar_prompt_mestre(
    *,
    card: dict[str, Any],
    detail_prompt: str,
    scene_reference: str = "",
    has_ability: bool = True,
    ability_name: str = "",
    ability_rule: str = "",
    faction_direction: str = "",
    negative_prompt: str = "",
) -> str:
    """Aplica o Prompt-Mestre V71 com precedência canônica e facção lida só do campo faccao."""
    name = _text(card.get("nome") or card.get("name") or "Unnamed card", 160)
    category = _text(card.get("categoria") or card.get("category") or "unspecified", 80)
    # IMPORTANTE: não consultar 'faction', lore, sinergias ou afinidades para decidir a facção.
    faction_raw = _text(card.get("faccao"), 80)
    faction = normalizar_faccao(faction_raw) or (faction_raw or "not specified")
    card_type = _text(card.get("tipo") or card.get("type") or "unspecified", 60)
    rarity = _text(card.get("raridade") or card.get("rarity") or "unspecified", 60)
    power = _text(card.get("poder") if card.get("poder") is not None else "not supplied", 30)
    power_max = _text(card.get("poder_maximo") or card.get("max_power") or "not supplied", 30)
    lore = _text(card.get("descricao") or card.get("lore") or "No card lore supplied; keep unknown facts neutral.", 1400)
    affinity = card.get("afinidades") or card.get("afinidade_dominante") or "not supplied"
    if isinstance(affinity, (list, tuple, set)):
        affinity = ", ".join(_text(item, 80) for item in list(affinity)[:8]) or "not supplied"
    else:
        affinity = _text(affinity, 180)
    ability_text = (
        f"{_text(ability_name, 100)} — {_text(ability_rule, 450)}" if has_ability else
        "No special ability. Do not invent spellcasting, magical attacks, aura, runes, energy trails or supernatural effects."
    )
    canonical = canonical_reference(card)
    scene = _text(scene_reference, 1800) or "No fixed catalogue scene. Derive one original moment strictly from the card name and lore; leave unsupported identity details neutral."
    faction_text = direcao_faccao(faction_raw)
    negative = negative_prompt or gerar_negative_prompt(card, has_ability=has_ability)
    detail = _multiline(detail_prompt, 30000)

    return f"""NARABOT — ELDEN RING CARD ART DIRECTOR / MASTER PROMPT

1. CARD AND SUBJECT IDENTIFICATION
Card name: {name}. Category: {category}. Type: {card_type}. Rarity: {rarity}. Current power: {power}. Maximum power: {power_max}. Affinities: {affinity}. Ability: {ability_text}. These are production facts, not elements to render. Resolve the literal named subject. A category label must never replace the actual named person, creature, object, weapon, spell, place or event.

2. ELDEN RING UNIVERSE AND CANONICAL REFERENCE
Mandatory universe: Elden Ring — the Lands Between. Use the Realm of Shadow only when supported by the card. {canonical} Preserve canonical character, creature, weapon, spell, event or location design: model, silhouette, anatomy, face, proportions, armor, helmet, clothing, materials, signature equipment and canonical colors. Never create an unsupported alternate version, merge distinct identities or borrow another franchise's designs. When the exact identity is uncertain, do not invent canonical details; keep unknown features neutral and create only a restrained subject coherent with Elden Ring.

3. OFFICIAL NARABOT FACTION — SOURCE FIELD ONLY
The faction MUST be read exclusively from the card's FACÇÃO field (internal key: 'faccao'). The supplied value is: {faction}. The game has EXACTLY THREE factions: ORDEM ÁUREA, VÉU CARMESIM and LUA NEGRA. The three NARABOT factions are custom deck allegiances. Do not infer, guess, rename or assign a faction from the character's appearance, name, canon allegiance, lore, type, ability, affinity, synergy, ingredient or environment. Synergy and affinity are not faction fields. Do not create a fourth faction. If the 'faccao' field is missing or does not exactly identify one of the three official factions, leave faction styling neutral and explicitly do not infer it.

4. FACTION ART DIRECTION — CONSISTENT COLLECTION SIGNATURE
{faction_text}
Across cards of the same faction, maintain a recognizable visual signature through atmosphere, lighting, environmental color, background materials and restrained complementary motifs. Do not make every card look like the same character or repeat the same composition. The faction is an art-direction layer, never a replacement for the named subject's canonical design, equipment, colors or actual Elden Ring allegiance.

VISUAL AUTHORITY HIERARCHY — apply in this exact order when any instructions appear to conflict: (1) Elden Ring universe and lore; (2) original canonical model of the named character, creature, object or place; (3) faction signature as a subordinate art-direction layer; (4) the individual card identity; (5) supplied lore and context; (6) scene, location and composition; (7) optional artistic complements. A lower-priority layer may never rewrite a higher-priority fact. In particular, faction colors must never recolor canonical armor, clothing, skin, hair, weapons or signature equipment.

5. PHYSICAL APPEARANCE AND ORIGINAL MODEL
Derive anatomy, species, age impression, face, hair, body proportions and silhouette from the canonical identity and supplied lore. Preserve all recognizable traits of existing Elden Ring characters. Do not change gender, species, age, body plan, skin, hair, face or physical condition. For an original NARABOT archetype, infer only details required to depict the stated role; leave all unsupported physical details restrained and neutral.

6. ARMOR, CLOTHING AND EQUIPMENT
Use the subject's canonical armor, clothing, helmet and equipment whenever established. Otherwise use only garments and materials supported by the card's lore or scene. Respect the actual construction language of Elden Ring: functional articulated armor, attached straps, worn leather, woven cloth, oxidized steel, aged brass, carved stone and weathered materials. Preserve original colors and motifs. Never recolor, replace or redesign canonical armor, garments or equipment merely to match a faction.

7. WEAPONS AND COMBAT POSTURE
Use the recognizable canonical weapon or equipment explicitly supported by the card. Match stance and gesture to the named subject and actual combat function. Tactical type or row may guide movement and distance but cannot invent a weapon, profession or class. Use a readable pose with correct grip, balance, scale and weapon construction. Do not add duplicate or unrelated weapons.

8. EXPRESSION AND PERSONALITY
Translate documented personality and emotional tone into gaze, expression, shoulder tension, hand placement and bearing. Avoid default frontal posing. Do not invent emotion, injury, relationship, rank or dramatic gesture that contradicts the canonical character or supplied lore.

9. SCENE AND CARD-SPECIFIC NARRATIVE
Card lore: "{lore}". Depict one distinct, concrete moment that communicates this specific card's story through action, expression, gesture, objects and consequence. Use the scene reference only where it is compatible with the actual card identity: {scene}. Synergies are context only; do not add associated characters unless the card lore explicitly depicts them. Ability effects must correspond only to the exact documented ability: {ability_text}

10. ENVIRONMENT AND LOCATION
Choose one Elden Ring region, structure or landscape supported by the named identity or card lore. Select architecture, terrain, climate and materials appropriate to that place. If no precise location is established, use a restrained Lands Between environment. Never insert famous landmarks randomly, combine unrelated regions or let faction alone force a canonical location.

11. LIGHTING AND ATMOSPHERE
Use cinematic but physically motivated lighting with one coherent source: overcast daylight, dawn, torchlight, firelight, moonlight, storm light, reflected snow light or a supernatural source only when the card supports it. The faction may guide the secondary color of light and atmosphere, but cannot alter canonical character colors or obscure the subject. Preserve Elden Ring's ancient, solemn, melancholic dark-fantasy mood.

12. COLOR PALETTE
Priority: canonical character and equipment colors first; the faction's palette second, applied mainly to lighting, atmosphere, background, environmental materials and restrained complementary accents; individual affinities only as subtle accents supported by the lore. Do not recolor canonical armor, clothing, skin, hair, weapons or signature equipment. Do not apply a full-image faction filter.

13. CINEMATIC COMPOSITION
Create one dominant subject and one focal story beat. Use landscape composition with clear foreground, subject plane and background; choose eye-level intimacy, three-quarter action, low-angle threat or environmental scale according to this card. Maintain strong silhouette, natural perspective, depth and clear focal hierarchy. Keep face, hands, weapon and defining equipment fully inside safe margins. Avoid static catalogue pose unless the identity calls for it. The image must remain readable at card-thumbnail size.

14. MANDATORY FORMAT — EXACT 5:4
Mandatory 5:4 aspect ratio, horizontal composition. Exact landscape ratio 5:4 only. Compose natively for 5:4 from the beginning. Never use portrait, square, 3:4, 2:3, 16:9 or any other aspect ratio. Do not rely on later cropping; keep all important parts of the subject and signature equipment inside safe margins.

15. QUALITY AND MATERIAL FINISH
Premium realistic Elden Ring dark-fantasy collectible-card illustration. Believable anatomy, natural facial proportions, correct hands, physically plausible materials and reflections, credible weight, accurate perspective, grounded contact shadows, coherent light direction and atmospheric depth. Controlled painterly finish, deliberate brushwork and restrained detail; no glossy CGI. Maintain professional quality regardless of rarity. Rarity influences narrative scale and refinement only; power influences credible competence only. Neither grants new powers or changes canonical design.

16. NEGATIVE PROMPT — CARD-SPECIFIC EXCLUSIONS
{negative}

DETAILED CARD-SPECIFIC PRODUCTION BRIEF
The following source brief adds card-specific visual facts. It is subordinate to Elden Ring canonical identity, the FACÇÃO-field rule, the hierarchy above, exact 5:4 and every explicit prohibition:
{detail}

FINAL OUTPUT: one standalone illustration only, set in Elden Ring, exact horizontal 5:4. No card frame, border, title, text, numbers, stats, icon, logo, watermark, signature, rarity gem, user interface, collage or mockup. The requested output is artwork only."""

def pacote_prompt_arte(
    *,
    card_id: str,
    card: dict[str, Any],
    prompt: str,
    scene_reference: str = "",
    faction_direction: str = "",
    has_ability: bool = True,
    ability_name: str = "",
    ability_rule: str = "",
) -> dict[str, Any]:
    negative = gerar_negative_prompt(card, has_ability=has_ability)
    return {
        "card_id": str(card_id),
        "analysis": gerar_analise_artistica(
            card,
            scene_reference=scene_reference,
            faction_direction=faction_direction,
            has_ability=has_ability,
            ability_name=ability_name,
            ability_rule=ability_rule,
        ),
        "prompt": montar_prompt_mestre(
            card=card,
            detail_prompt=prompt,
            scene_reference=scene_reference,
            has_ability=has_ability,
            ability_name=ability_name,
            ability_rule=ability_rule,
            faction_direction=faction_direction,
            negative_prompt=negative,
        ),
        "negative_prompt": negative,
        "language": "en",
        "recommended_aspect_ratio": ASPECT_RATIO,
        "recommended_width": ART_WIDTH,
        "recommended_height": ART_HEIGHT,
    }
