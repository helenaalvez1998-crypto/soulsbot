# Prompts oficiais — molduras fixas das cartas do Coliseu

## Como usar

Gere **um arquivo separado por raridade**. Não peça ao gerador para criar a carta inteira. Cada imagem é somente uma camada de moldura (overlay) que o SoulsBot aplica sobre a carta já composta pelo Pillow.

**Especificação técnica obrigatória para todos os cinco arquivos**

- Canvas vertical exato: **840 × 1240 px**, proporção 420:620 (aproximadamente 0,6774:1).
- Formato final: **PNG RGBA com canal alfa verdadeiro**. Não simular transparência com quadriculado cinza/branco.
- Tudo que não for parte física da moldura deve ter alfa 0 (totalmente transparente).
- A moldura deve seguir o perímetro externo da carta: quatro lados contínuos, cantos alinhados, sem cortes e sem perspectiva.
- A faixa decorativa deve permanecer junto ao perímetro. Não avançar sobre a área de conteúdo; manter o centro livre e transparente.
- Não desenhar fundo, textura de papel, placa central, superfície, vinheta, sombra preenchida, cena, personagem ou ilustração.
- Não desenhar texto, letras, números, palavras, runas que pareçam escrita legível, nome da raridade, logotipo, marca-d'água ou assinatura.
- Não incluir a carta completa, caixas de atributos, espaços preenchidos para título, poder ou habilidade. O bot já desenha esses elementos.
- A moldura precisa ter leitura clara quando reduzida para 420 × 620 px. Priorizar silhueta limpa, contraste de materiais e acabamento nítido.
- Manter o interior da moldura realmente transparente. Como referência, a área central de aproximadamente 70% da largura por 70% da altura deve permanecer vazia.
- Sem elementos saindo do canvas. Sem mockup, sem mão segurando carta, sem mesa, sem fundo de apresentação.

**Regra de compatibilidade com a composição atual:** a marca do bot e a etiqueta da raridade ficam próximas do topo; título, janela da ilustração, atributos e habilidade ocupam o centro. Portanto, o trilho superior deve ser fino, os ornamentos dos cantos superiores devem ficar encostados ao extremo externo e as laterais não podem avançar sobre a área central. A moldura é uma camada transparente por cima da carta, não um novo layout.

---

## 1. COMUM — ferro gasto e construção utilitária

**Prompt (copiar integralmente):**

> Create a production-ready **transparent card-frame overlay**, not a complete card. Exact canvas **840 × 1240 pixels**, portrait ratio 420:620. Output a genuine **RGBA PNG with a real alpha channel**. The background and the entire inner opening must be fully transparent (alpha 0); do not simulate transparency with a checkerboard.
>
> Design a **COMMON rarity** frame for a premium dark-fantasy collectible card game. The frame represents a practical, mass-produced piece of old equipment: sober, durable, modest and slightly worn. Use dark gunmetal, cold iron, charcoal steel and restrained pewter highlights. The material should feel forged and functional, not precious. Show fine hammer marks, tiny nicks, shallow scratches, subtle oxidation, minute pits and a few restrained rivets. The wear must be controlled and elegant, never dirty, rusty-orange or damaged beyond use.
>
> Construct a continuous rectangular perimeter with softly chamfered corners and a narrow, consistent metal rail. Use a simple single outer bevel and one very fine inner hairline. The metal edge should have realistic thickness, a crisp machined highlight on one side and a deep graphite shadow on the opposite side. Add four small, identical corner fasteners; each fastener is a plain round-headed iron pin with a tiny recessed center. Add only short, straight corner engravings and restrained angular cuts. The four sides must feel manufactured from the same piece of metal and align perfectly.
>
> **Rarity hierarchy:** this is the lowest visual tier. Keep it deliberately understated. No gemstones, no crown, no wings, no flames, no magical aura, no glowing runes, no gold filigree and no elaborate ornaments. A viewer should immediately read it as a clean, dependable base frame, not as a damaged or low-quality image.
>
> **Placement and transparency:** keep every visible element in a thin perimeter band. The top rail must be especially slim and unobtrusive. Keep the upper-left and upper-right corner details tight to the outside corners so they do not overlap the card brand or rarity label. Keep the full inner opening transparent from edge to edge. No opaque pixels, color wash, grain, gradient or shadow in the center. The frame must not intrude into the illustration window or the lower text/attribute region.
>
> Front-facing orthographic view, perfectly flat card alignment, symmetrical left/right construction, precise 2D overlay geometry, premium hand-forged material rendering, restrained studio highlights painted onto the metal only. Sharp edges, high legibility at half size. No perspective, no card mockup, no environment, no background, no text, no logo, no watermark, no signature. Deliver only the isolated transparent frame overlay.

---

## 2. RARA — aço frio e safira azul-petróleo

**Prompt (copiar integralmente):**

> Create a production-ready **transparent card-frame overlay**, not a complete card. Exact canvas **840 × 1240 pixels**, portrait ratio 420:620. Output a genuine **RGBA PNG with a real alpha channel**. The background and the entire inner opening must be fully transparent (alpha 0); do not simulate transparency with a checkerboard.
>
> Design a **RARE rarity** frame for the same premium dark-fantasy collectible card universe. It must look clearly superior to a common iron frame while remaining disciplined and readable. The primary material is finely forged blue-black steel with cold silver bevels. Add deep sapphire and blue-teal enamel inlays, small faceted blue gemstones and subtle cyan reflections. The dominant palette is midnight steel, desaturated silver, deep sapphire and restrained spectral teal; avoid electric-neon blue.
>
> Build a continuous, precision-machined perimeter with angular geometry: gently clipped or faceted corners, two nested metal rails, a narrow inner silver highlight and a recessed dark channel between the rails. Place four small sapphire lozenges or diamond-cut studs at the cardinal anchors (top, right, bottom, left), each seated inside a metal bezel. Add fine geometric linework that follows the perimeter and converges cleanly into each corner. Use short symmetrical notches and tiny engraved chevrons to create a sense of craftsmanship and controlled energy.
>
> Gemstones must be physically believable: crisp facets, dark blue cores, tiny pale-blue specular highlights and restrained internal depth. They must remain small and attached to the frame; do not create floating crystals or large objects in the center. Any cyan glow must be extremely local to the gemstone and must not spill into the transparent opening.
>
> **Rarity hierarchy:** clearly more refined and valuable than Common. It should communicate discovery, quality and a subtle magical charge, but not the grandiose luxury of Epic or Legendary. No crown, no large jewels, no gold, no wings, no flames, no full-frame energy aura and no bright neon tubing.
>
> **Placement and transparency:** all metal, gems, engravings and reflections stay in the narrow outer perimeter band. Keep the top center rail thin and keep upper corner ornaments tight to the outermost corners to protect the card brand, rarity capsule and title. The entire central opening must be transparent, including behind the illustration and all text/stat regions. No central plate, no background fill, no opaque inner panel, no color haze and no cast shadow inside the card.
>
> Front-facing orthographic view, perfectly aligned vertical rectangular overlay, symmetrical left/right construction, crisp layered metalwork, polished but believable finish, premium game collectible production asset. No perspective, no complete card, no scene, no mockup, no text, no letters, no numbers, no logo, no watermark, no signature. Deliver only the isolated transparent frame overlay.

---

## 3. ÉPICA — prata lunar, ametista e filigrana arcana

**Prompt (copiar integralmente):**

> Create a production-ready **transparent card-frame overlay**, not a complete card. Exact canvas **840 × 1240 pixels**, portrait ratio 420:620. Output a genuine **RGBA PNG with a real alpha channel**. The background and the entire inner opening must be fully transparent (alpha 0); do not simulate transparency with a checkerboard.
>
> Design an **EPIC rarity** frame for a coherent premium dark-fantasy collectible card game. This frame should feel like an ancient relic made for a high-ranking sorcerer: refined, arcane, intricate and powerful, but still restrained enough to keep card content readable. Use aged moon-silver, dark violet steel, muted lavender enamel and deep amethyst. The silver is cool and slightly tarnished in recesses; its raised edges catch pale lilac highlights. Amethyst accents should be rich and dark, with crisp facets and a controlled internal glow.
>
> Create a continuous multi-layer perimeter: an outer dark-violet structural rail, a raised silver bevel, a thin luminous lavender fillet and an inner fine silver line. Use elegant pointed corner caps with interlocking metal segments. Add delicate filigree inspired by abstract orbital paths, crescent arcs, small starburst cuts and symmetrical knotwork. Work the ornament into the four corners and the midpoint anchors without creating a bulky frame. Include four small amethyst cabochons or faceted stones held in narrow silver claws. Add a few tiny engraved arcane marks that are purely decorative geometry, not readable alphabetic characters or words.
>
> The design language should imply hidden knowledge and disciplined sorcery: interlocking arcs, measured radial symmetry, subtle celestial geometry and fine etched lines. The decoration must be physically attached to the metal. The glow is a small reflected highlight on metal and gemstones only; no fog, particles or magical cloud may extend into the center.
>
> **Rarity hierarchy:** substantially more elaborate than Rare, clearly violet and arcane, but below the opulence of Legendary and the cosmic authority of Primordial. Do not use a crown, royal gold plating, giant central jewel, wings, fire, lightning bolts or a full-frame neon aura. No large symbols in the top center.
>
> **Placement and transparency:** keep filigree, stones, bevels and all ornament inside the outer perimeter band. Leave the top-center rail narrow. Keep both upper corner ornaments close to the external corners and away from the card's brand and rarity label. The complete inner opening must remain transparent so the bot's illustration, title, power, cost and ability remain visible. No filled panel, no texture, no gradient, no colored wash and no drop shadow in the center.
>
> Perfectly flat front-facing orthographic overlay, exact vertical card alignment, balanced bilateral symmetry, meticulous engraved metal detail, high-end fantasy prop craftsmanship, crisp edges at 420 × 620 output size. No perspective, no card mockup, no environment, no background, no text, no readable runes, no logo, no watermark, no signature. Deliver only the isolated transparent frame overlay.

---

## 4. LENDÁRIA — ouro antigo, filigrana régia e brasões solares

**Prompt (copiar integralmente):**

> Create a production-ready **transparent card-frame overlay**, not a complete card. Exact canvas **840 × 1240 pixels**, portrait ratio 420:620. Output a genuine **RGBA PNG with a real alpha channel**. The background and the entire inner opening must be fully transparent (alpha 0); do not simulate transparency with a checkerboard.
>
> Design a **LEGENDARY rarity** frame for a premium dark-fantasy collectible card game. It must feel like a royal relic forged for a champion whose name is remembered for centuries. Use antique high-karat gold, warm champagne gold, aged bronze in the recesses and precise pale-gold edge highlights. The metal should look heavy, expertly engraved and historically old, but meticulously maintained. Avoid flat yellow, orange plastic, cheap glitter and mirror-like chrome.
>
> Construct a richly layered perimeter with three distinct metal levels: a dark bronze foundation rail, a raised antique-gold structural band and a fine pale-gold inner bevel. The rail should be continuous and mechanically coherent. Use deep chased relief, tiny repeating leaf motifs, restrained sun-ray geometry, heraldic scrollwork and symmetrical acanthus-inspired curls. Design four substantial but compact corner plates with engraved radial patterns. Add four small inset gemstones in dark garnet or warm amber, each held by a precise gold bezel. Add a discreet laurel or wing-like motif that follows the outer edge; it must never become a large object projecting into the center.
>
> Give the top and bottom center a distinct ceremonial accent: a small symmetrical sunburst medallion or abstract heraldic crest integrated into the perimeter rail. It must remain shallow and narrow, not a large central crown or plaque. Use delicate micro-engraving along the gold band, with alternating polished and satin surfaces. Highlights should trace the raised relief and reveal depth; recesses remain dark bronze for contrast.
>
> **Rarity hierarchy:** this is unmistakably more prestigious and ornate than Epic. It should communicate authority, achievement and exceptional craftsmanship. It may use royal motifs and rich gold, but it must stay below Primordial in cosmic scale and visual rarity. No giant jewels, no large central emblem, no fire effects, no floating sparks crossing the opening, no excessive yellow glow and no text.
>
> **Placement and transparency:** the luxurious ornament is confined to the outer border band. Keep the top horizontal rail especially controlled and keep the top-left and top-right crest details close to the extreme corners so the card's brand, rarity capsule and title remain unobstructed. Keep the complete center transparent. The illustration, attribute panel, cost and ability are supplied by the bot and must remain visible over the transparent opening. No central gold plate, no background texture, no opaque inner fill, no vignette and no internal shadow.
>
> Orthographic front view, straight-on flat overlay, perfect vertical alignment, mirrored corner construction, physically believable engraved gold, crisp micro-detail, premium collectible relic finish, readable after reduction to 420 × 620. No perspective, no full card, no table, no mockup, no environment, no background, no letters, no numbers, no words, no logo, no watermark, no signature. Deliver only the isolated transparent frame overlay.

---

## 5. PRIMORDIAL — ouro branco, platina celestial e geometria anterior ao tempo

**Prompt (copiar integralmente):**

> Create a production-ready **transparent card-frame overlay**, not a complete card. Exact canvas **840 × 1240 pixels**, portrait ratio 420:620. Output a genuine **RGBA PNG with a real alpha channel**. The background and the entire inner opening must be fully transparent (alpha 0); do not simulate transparency with a checkerboard.
>
> Design the **PRIMORDIAL rarity** frame: the highest and most singular tier in a premium dark-fantasy collectible card universe. It must feel older than kingdoms, beyond ordinary divinity and almost impossible to forge. The design should be unmistakably more important than Legendary without becoming noisy or unreadable. Use a sophisticated combination of luminous pale gold, white gold, ancient platinum, ivory-metal highlights and very deep midnight-gold recesses. Introduce tiny opalescent reflections and restrained celestial-blue or pale-violet spectral glints only as secondary accents. Never use flat bright yellow or saturated neon.
>
> Build a monumental but narrow perimeter from multiple interlocked materials: an outer platinum structural rim, a raised white-gold rail, a fine pale-gold inner line and small sections of translucent-looking mineral inlay that remain opaque only where they physically form part of the border. The metal must feel impossibly precise and ancient at once: hairline engravings, micro-cut facets, interlocking geometric joints and subtle signs of age. Use a unique four-corner architecture with nested diamond geometry, tiny star-like nodes and radial cuts. The corners should look like fragments of an ancient celestial mechanism, not ordinary royal decoration.
>
> Along the sides, incorporate extremely fine orbital arcs, broken halo segments, star-map geometry and delicate concentric lines. All patterns must remain attached to the frame and follow its perimeter. At the top and bottom center, add a small, narrow, symmetrical primordial sigil made from abstract geometry: a central diamond, two mirrored arcs and three tiny points of light. It must be ornamental, not readable writing, and must not resemble a known religious, commercial or copyrighted symbol. Add minute prismatic facets along selected bevels to imply that the material catches light from impossible angles.
>
> The luminosity must be controlled and physically integrated: crisp white-gold edge glints, a few tiny star-like reflections embedded in the metal, and very subtle iridescence on selected facets. No broad aura, no fog, no particles, no rays extending into the interior and no starfield background. The center is not space; it is fully transparent. Make the border feel sacred, ancient, absolute and singular through craftsmanship and silhouette rather than through a filled cosmic effect.
>
> **Rarity hierarchy:** the most prestigious and visually distinctive frame in the entire system. It must surpass Legendary in material refinement, complexity and symbolic weight. It should not simply be a brighter gold version of Legendary: its identity is platinum-white gold, celestial geometry, broken halos and primordial precision. No ordinary crown, no laurel wreath, no large gemstone, no bulky wings, no flames, no lightning, no purple full-frame glow and no giant medallion.
>
> **Placement and transparency:** keep every visible detail within the narrow external perimeter. Upper ornaments must be extremely compact and placed at the extreme corners; the top-center rail must remain thin so the card identity and rarity capsule are never covered. Keep the whole inner opening transparent from top to bottom. No opaque plate, no inner color, no gradient, no card art, no background, no vignette and no shadow inside the card. The bot will render all text, illustration and statistics underneath this overlay.
>
> Perfectly flat front-facing orthographic overlay, exact 840 × 1240 vertical alignment, flawless left/right balance, precise interlocking construction, exquisite micro-engraving, white-gold and platinum material realism, high visual authority without clutter, exceptionally crisp at 420 × 620. No perspective, no card mockup, no environment, no background, no readable glyphs, no text, no letters, no numbers, no logo, no watermark, no signature. Deliver only the isolated transparent frame overlay.

---

## Checklist antes de enviar ao bot

- [ ] O arquivo é PNG RGBA e a transparência é real, não um quadriculado desenhado.
- [ ] O canvas é 840 × 1240 px (ou 420 × 620 px no mínimo).
- [ ] A imagem contém somente a moldura externa; não há arte, fundo ou cartão preenchido.
- [ ] O centro é transparente e não cobre texto, ilustração, poder, custo ou habilidade.
- [ ] As quatro bordas estão completas, alinhadas e não foram cortadas.
- [ ] A identidade visual corresponde à raridade correta.
- [ ] O resultado continua legível quando reduzido para 420 × 620 px.
