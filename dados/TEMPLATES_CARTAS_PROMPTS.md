# Prompts dos templates completos das cartas (5 raridades)

Como usar: anexe `guia_template_carta_limpo.png` na IA de imagem e cole **um** dos prompts abaixo. Cada prompt é completo (layout + estilo da raridade). Gere em retrato **840 × 1240 px**. O guia é vinculante: não desloque, redimensione ou redesenhe as placas em posições diferentes.

**Geometria obrigatória:** raridade `(600,44 → 784,96)`; nome `(56,100 → 784,236)`; janela da arte `(56,256 → 784,846)`; poder centro `(144,986)`, raio `78`; tipo `(254,918 → 780,978)`; custo `(254,992 → 780,1052)`; habilidade `(56,1084 → 784,1176)`. A janela deve ser uma abertura retangular limpa, sem ornamentos, e estar transparente ou em magenta chapado `#FF00FF`. O bot valida a janela com tolerância máxima de 3 px; não compense placas deslocadas com JSON.

Dicas: gere as cinco na mesma ferramenta e com o mesmo guia. Se aparecer qualquer letra, apague no editor antes de enviar em `/adm` → Jogos, Coliseu e runs → Templates completos das cartas. Se uma raridade baixa sair chamativa demais, repita o pedido acrescentando: "less glow, fewer ornaments, more muted".


## Comum

```
Using the attached layout guide image as the exact reference for where things go, create a COMPLETE vertical collectible card TEMPLATE, portrait exactly 840x1240 px. The card surface must be opaque everywhere EXCEPT for one single rectangular illustration window at x=56..784, y=256..846. That window must be true alpha transparency in the PNG (preferred) or perfectly flat pure magenta #FF00FF for chroma removal. Do not create any other transparent pixels, cut-out corners, or holes. The template is EMPTY: do NOT draw any text, letters, numbers, logos, watermarks or characters anywhere.

Layout (follow the guide, same positions on every card):
- Top right: a small empty badge plate for the rarity name.
- Below it: a wide empty name banner plate, room for two lines of text.
- Center: the exact ART WINDOW rectangle from the guide: x=56..784, y=256..846 (728 × 590 px), filled with FLAT PURE MAGENTA #FF00FF or true transparency. It must not be resized, moved, rounded or covered by ornaments.
- Lower left: an empty round medallion for a big power number.
- Lower right: two stacked, empty horizontal plates (type and cost).
- Bottom: a wide empty rectangular plate for ability text.

Readability rule for every rarity: the inside of every plate and medallion stays calm, dark and low-contrast so white text is readable. All the spectacle (glow, particles, light rays, ornaments, background effects) lives ONLY on the outer frame, the card margins and the background around the plates, never inside the plates or the art window. Dark-fantasy souls-like mood, symmetric and centered.

FLASHINESS LEVEL: 1 of 5 (the plainest card of the whole set).
RARITY STYLE (COMMON): a humble, worn, matte frame of dark iron and dull brown-gray steel, flat lighting, no glow at all, no gems, no particles. Thin plain border, four small rivets at the corners, simple beveled plates with light scratches and rust stains, flat dark charcoal background with a faint paper-like grain. Everything is muted and desaturated; the most saturated color on the card is a dull silver. Looks like cheap, old equipment.

Final check: no text anywhere; the only transparent area is the exact rectangular art window at x=56..784, y=256..846 (true alpha 0 preferred, otherwise clean flat #FF00FF); every pixel outside that window is opaque; all plates are empty and aligned to the guide; no ornament overlaps the art window or text surfaces; the spectacle matches the flashiness level stated above.
```


## Rara

```
Using the attached layout guide image as the exact reference for where things go, create a COMPLETE vertical collectible card TEMPLATE, portrait exactly 840x1240 px. The card surface must be opaque everywhere EXCEPT for one single rectangular illustration window at x=56..784, y=256..846. That window must be true alpha transparency in the PNG (preferred) or perfectly flat pure magenta #FF00FF for chroma removal. Do not create any other transparent pixels, cut-out corners, or holes. The template is EMPTY: do NOT draw any text, letters, numbers, logos, watermarks or characters anywhere.

Layout (follow the guide, same positions on every card):
- Top right: a small empty badge plate for the rarity name.
- Below it: a wide empty name banner plate, room for two lines of text.
- Center: the exact ART WINDOW rectangle from the guide: x=56..784, y=256..846 (728 × 590 px), filled with FLAT PURE MAGENTA #FF00FF or true transparency. It must not be resized, moved, rounded or covered by ornaments.
- Lower left: an empty round medallion for a big power number.
- Lower right: two stacked, empty horizontal plates (type and cost).
- Bottom: a wide empty rectangular plate for ability text.

Readability rule for every rarity: the inside of every plate and medallion stays calm, dark and low-contrast so white text is readable. All the spectacle (glow, particles, light rays, ornaments, background effects) lives ONLY on the outer frame, the card margins and the background around the plates, never inside the plates or the art window. Dark-fantasy souls-like mood, symmetric and centered.

FLASHINESS LEVEL: 2 of 5.
RARITY STYLE (RARE): a polished blue-steel frame with a clean metallic shine and crisp cyan and teal accents. Thin glowing cyan inlay lines run along the whole border, diamond-shaped studs sit at the middle of each side, the plates have delicate engraved geometric patterns with a faint cold-blue rim light, and the dark background has a subtle blue vignette. One single color family (cyan), a soft glow only on the border lines, no particles. Clearly nicer than common, still restrained.

Final check: no text anywhere; the only transparent area is the exact rectangular art window at x=56..784, y=256..846 (true alpha 0 preferred, otherwise clean flat #FF00FF); every pixel outside that window is opaque; all plates are empty and aligned to the guide; no ornament overlaps the art window or text surfaces; the spectacle matches the flashiness level stated above.
```


## Épica

```
Using the attached layout guide image as the exact reference for where things go, create a COMPLETE vertical collectible card TEMPLATE, portrait exactly 840x1240 px. The card surface must be opaque everywhere EXCEPT for one single rectangular illustration window at x=56..784, y=256..846. That window must be true alpha transparency in the PNG (preferred) or perfectly flat pure magenta #FF00FF for chroma removal. Do not create any other transparent pixels, cut-out corners, or holes. The template is EMPTY: do NOT draw any text, letters, numbers, logos, watermarks or characters anywhere.

Layout (follow the guide, same positions on every card):
- Top right: a small empty badge plate for the rarity name.
- Below it: a wide empty name banner plate, room for two lines of text.
- Center: the exact ART WINDOW rectangle from the guide: x=56..784, y=256..846 (728 × 590 px), filled with FLAT PURE MAGENTA #FF00FF or true transparency. It must not be resized, moved, rounded or covered by ornaments.
- Lower left: an empty round medallion for a big power number.
- Lower right: two stacked, empty horizontal plates (type and cost).
- Bottom: a wide empty rectangular plate for ability text.

Readability rule for every rarity: the inside of every plate and medallion stays calm, dark and low-contrast so white text is readable. All the spectacle (glow, particles, light rays, ornaments, background effects) lives ONLY on the outer frame, the card margins and the background around the plates, never inside the plates or the art window. Dark-fantasy souls-like mood, symmetric and centered.

FLASHINESS LEVEL: 3 of 5.
RARITY STYLE (EPIC): a dramatic dark obsidian frame with a sharp angular silhouette (chamfered, jagged corners that reach out into the card margins), deep violet and amethyst metal with bright magenta-purple edge lighting. Large glowing amethyst crystals set in the four corners and at the middle of the top edge, glowing arcane rune lines along the border (abstract shapes only, no readable letters), wisps of purple energy and mist curling around the outside of the frame, a purple aura glowing behind the plates, small floating violet sparks in the background. Two color families (violet plus a hot pink-white highlight). Bold and eye-catching.

Final check: no text anywhere; the only transparent area is the exact rectangular art window at x=56..784, y=256..846 (true alpha 0 preferred, otherwise clean flat #FF00FF); every pixel outside that window is opaque; all plates are empty and aligned to the guide; no ornament overlaps the art window or text surfaces; the spectacle matches the flashiness level stated above.
```


## Lendária

```
Using the attached layout guide image as the exact reference for where things go, create a COMPLETE vertical collectible card TEMPLATE, portrait exactly 840x1240 px. The card surface must be opaque everywhere EXCEPT for one single rectangular illustration window at x=56..784, y=256..846. That window must be true alpha transparency in the PNG (preferred) or perfectly flat pure magenta #FF00FF for chroma removal. Do not create any other transparent pixels, cut-out corners, or holes. The template is EMPTY: do NOT draw any text, letters, numbers, logos, watermarks or characters anywhere.

Layout (follow the guide, same positions on every card):
- Top right: a small empty badge plate for the rarity name.
- Below it: a wide empty name banner plate, room for two lines of text.
- Center: the exact ART WINDOW rectangle from the guide: x=56..784, y=256..846 (728 × 590 px), filled with FLAT PURE MAGENTA #FF00FF or true transparency. It must not be resized, moved, rounded or covered by ornaments.
- Lower left: an empty round medallion for a big power number.
- Lower right: two stacked, empty horizontal plates (type and cost).
- Bottom: a wide empty rectangular plate for ability text.

Readability rule for every rarity: the inside of every plate and medallion stays calm, dark and low-contrast so white text is readable. All the spectacle (glow, particles, light rays, ornaments, background effects) lives ONLY on the outer frame, the card margins and the background around the plates, never inside the plates or the art window. Dark-fantasy souls-like mood, symmetric and centered.

FLASHINESS LEVEL: 4 of 5.
RARITY STYLE (LEGENDARY): a lavish, blazing frame of gleaming polished gold and burnished bronze with intense orange and amber fire-glow, triple layered border with heavy filigree scrollwork, large ornate wing-like and flame-like gold flourishes extending outward from both sides, a big golden crown with red jewels at the top center, a huge jeweled gold medallion for the power number, gold engraved plates with a bright warm rim light, radiant sunburst rays and drifting golden embers and sparkles across the background behind the frame, a rich warm red-and-orange glow around the whole card edge. High contrast, glittering, saturated and luxurious; it must look obviously far more valuable than the epic card.

Final check: no text anywhere; the only transparent area is the exact rectangular art window at x=56..784, y=256..846 (true alpha 0 preferred, otherwise clean flat #FF00FF); every pixel outside that window is opaque; all plates are empty and aligned to the guide; no ornament overlaps the art window or text surfaces; the spectacle matches the flashiness level stated above.
```


## Primordial

```
Using the attached layout guide image as the exact reference for where things go, create a COMPLETE vertical collectible card TEMPLATE, portrait exactly 840x1240 px. The card surface must be opaque everywhere EXCEPT for one single rectangular illustration window at x=56..784, y=256..846. That window must be true alpha transparency in the PNG (preferred) or perfectly flat pure magenta #FF00FF for chroma removal. Do not create any other transparent pixels, cut-out corners, or holes. The template is EMPTY: do NOT draw any text, letters, numbers, logos, watermarks or characters anywhere.

Layout (follow the guide, same positions on every card):
- Top right: a small empty badge plate for the rarity name.
- Below it: a wide empty name banner plate, room for two lines of text.
- Center: the exact ART WINDOW rectangle from the guide: x=56..784, y=256..846 (728 × 590 px), filled with FLAT PURE MAGENTA #FF00FF or true transparency. It must not be resized, moved, rounded or covered by ornaments.
- Lower left: an empty round medallion for a big power number.
- Lower right: two stacked, empty horizontal plates (type and cost).
- Bottom: a wide empty rectangular plate for ability text.

Readability rule for every rarity: the inside of every plate and medallion stays calm, dark and low-contrast so white text is readable. All the spectacle (glow, particles, light rays, ornaments, background effects) lives ONLY on the outer frame, the card margins and the background around the plates, never inside the plates or the art window. Dark-fantasy souls-like mood, symmetric and centered.

FLASHINESS LEVEL: 5 of 5 (the most spectacular card of the whole set, it must outshine all the others at a glance).
RARITY STYLE (PRIMORDIAL): a divine, cosmic, holographic frame of radiant white-gold with a prismatic rainbow iridescent sheen sweeping across the metal like a holographic foil, blinding light. A huge crown-and-halo with a circle of light rays at the top, enormous feathered celestial wings of light and gold unfolding from both sides of the frame into the margins, a nebula and starfield background in deep blue, magenta and gold, bright lens flares and star-shaped glints at the corners, swirling streams of golden light and floating luminous particles all around, carved cosmic symbols (abstract shapes only, no readable letters), pearlescent plates with a glowing luminous edge, a powerful white-gold aura radiating from behind the whole card. Maximum detail, maximum glow, maximum color, awe-inspiring and mythic; the most extravagant ornamentation possible while the plates and the art window stay clean.

Final check: no text anywhere; the only transparent area is the exact rectangular art window at x=56..784, y=256..846 (true alpha 0 preferred, otherwise clean flat #FF00FF); every pixel outside that window is opaque; all plates are empty and aligned to the guide; no ornament overlaps the art window or text surfaces; the spectacle matches the flashiness level stated above.
```
