# MARKET.md — what 15 research strikes actually found

Date: 2026-05-24. Sources: Unity Asset Store policy, Synty business
model, KitBash3D/Quixel models, Fab/Epic split, AssetFormer (ICLR
2026), AniGen (SIGGRAPH 2026), LL3M (524 stars), ProcFunc
(Princeton 2026), Infinigen, Material Maker, ArmorLab, OpenPBR,
Kenney/PolyHaven model, indie postmortems, CC0 economics.

## The big numbers

### Marketplace revenue splits (HUGE finding)

| Marketplace | Publisher cut | Take rate |
|---|---|---|
| **Fab (Epic, Unreal+general)** | **88%** | 12% |
| **Unity Asset Store** | **70%** | 30% |
| **Gumroad** | ~90% (after fees) | ~10% |
| **Itch.io** | up to 100% (variable) | 0-30% (you pick) |

**Implication: Fab is the optimal primary marketplace.** $100 sale =
$88 to you vs $70 on Unity. For asset-pack volume, this is a 26%
revenue uplift on identical work. **Don't anchor to Unity Asset
Store as the primary channel.**

### Pricing reality

- Synty POLYGON packs: $25-$150 per pack
- Top performers: catalog of 130+ packs (SyntyPass subscription)
- Editor tools on Unity Asset Store: $15-$80 sweet spot
- AI-generated asset packs: Unity explicitly allows (with disclosure
  + significant value-add); cannot use "handmade/painted" marketing
  language

### Asset categories that sell

In ranked order from research:
1. **Modular environment kits** (fantasy, sci-fi, post-apoc, urban)
2. **Character + environment bundles**
3. **Themed collections** (low-poly stylized > photoreal for indies)
4. **Modular building/dungeon kits**
5. **Weapons + armor packs**
6. **Vehicle packs**
7. **VFX packs** (this is in the next tier of demand)

What makes packs SELL (not just exist):
- **Modularity** — many usable pieces, snap-grid compatible
- **Style consistency** — cohesive art direction, not random AI mush
- **Use-case clarity** — "fantasy village kit," "sci-fi corridor"
- **Cross-engine** — Unity + Unreal + Godot all bundled

## The AI-3D production gap (verified, 2026)

Commercial AI-3D tools (Meshy, Tripo, Rodin, 3D AI Studio) generate
meshes well. They DO NOT solve:

- **Clean topology** — output meshes are dense / triangulated
- **Proper UV unwrapping** — UVs are auto-projected, not artist-quality
- **Auto-rigging** for animation
- **Consistent edge flow** for deformation
- **Collision geometry**
- **Engine-ready LODs**

**This is the gap.** AI generates meshes; nobody automates the
"make it an asset" pipeline. AniGen (SIGGRAPH 2026) does auto-rig
+ skinning. ProcFunc gives function-oriented procedural API. LL3M
proves LLM-as-Blender-coder works. **Nobody has bundled these into a
"prompt → asset-pack on disk" pipeline.**

You have most of the pieces already in flax-mcp:
- flax-asset-gen: 5 free text-to-3D routes
- flax-blender-bridge: 22 Blender tools (vendors ahujasid 21.9k-star
  upstream)
- flax-meshopt-bridge: gltfpack wrapper for LOD + Draco
- flax-procedural: 26 tools for procedural geometry (WFC, dungeon
  gen, noise, terrain, scattering)
- flax-asset-worker: SHA-256 provenance + license sidecar +
  7-provider intake

**What's missing for "asset-pack factory":**
- Auto-retopology (decimation + remesh + symmetry)
- UV unwrap automation (Blender Smart UV + manual seam hints)
- Auto-rigging (AniGen-style, or rigify for humanoids)
- Material assignment from PBR library (Material Maker / OpenPBR)
- LOD chain generation (partially: gltfpack)
- Modularity post-processing (snap-grid alignment, pivot
  standardization, naming conventions)
- Marketplace manifest generation (preview renders, README,
  license file, demo scene per engine)

## Business models that work for asset creators

Three proven shapes from the research:

### 1. Synty model — "premium catalog publisher"

- Distinct, recognizable art style (POLYGON low-poly faceted look)
- 130+ packs in one consistent visual system
- Cross-engine (Unity, Unreal, Godot)
- $25-150 per pack + SyntyPass subscription
- Strategy: front-load production cost, long-tail revenue
- **Realistic income at scale:** $20k-$200k+ MRR
- **Time to mature:** 2-3 years

### 2. Kenney/PolyHaven model — "free + Patreon + commercial bundles"

- All assets CC0 / free for everyone
- Patreon for early access, source files, premium variants
- Commercial bundles for studios that want time-saving curated packs
- Kenney has thousands of Patreon supporters; PolyHaven generates
  6-figure annual revenue
- **Realistic income at scale:** $5k-$30k MRR via Patreon
- **Time to mature:** 1-2 years (audience-building required)

### 3. KitBash3D model — "subscription library"

- Curated production-ready kits, $99-$499 per pack
- Cargo subscription: $25-$60/mo for full library access
- Targets pros (film + AAA games) not indies
- **Realistic income at scale:** millions/year
- **Time to mature:** 3-5 years, needs serious art quality

## What sells AI-generated specifically

Unity Asset Store explicitly allows AI-generated assets with:
- AI tool disclosure (which models, what was generated, what you
  modified)
- "Significant value and usability"
- No "handmade/painted" marketing language
- No copyrighted-character resemblance
- License-compatible source tools (commercial-use rights confirmed)

**The Fab/Epic stance is currently MORE permissive** than Unity.

So: AI-pipeline asset packs are sellable. The bar is "significant
value-add" — i.e. you can't just dump raw Meshy output. You have to
fix topology, UVs, rigs, materials, LODs, snap-grids, demo scenes.

**Which is exactly the gap our pipeline fills.**

## Three live competitive threats

### Threat 1: ProcFunc (Princeton, 2026)
- Function-oriented procedural Blender API
- Coming with pre-made generators as part of Infinigen
- BSD-3 license
- **Means:** Princeton ships a free open-source procedural generator
  pack within 6-12 months. Anyone who waits for it gets free
  competition.
- **Counter:** Use ProcFunc directly. It's BSD-3, you can wrap it.

### Threat 2: LL3M (524 stars, 2025-2026)
- LLM agents writing Python in Blender to generate assets
- Client-server, requires account
- **Means:** AI-pipeline-as-a-service exists already
- **Counter:** LL3M is research, not productized. They don't do
  asset packs; they do one-off objects. Different shape.

### Threat 3: AssetFormer (ICLR 2026)
- Autoregressive transformer for modular 3D assets specifically
- 33 stars currently, research code
- **Means:** Modular asset generation from text is now a paper, not
  a moat
- **Counter:** Research code != productized. Production-ready
  modular kits with collision/rigs/LODs/UVs is still ~12-18 months
  out for academia. Window exists.

## The honest assessment

Asset-pack creation is **the right space.** Reasons:

1. You have 70% of the pipeline already built (flax-mcp's 5 plugins)
2. Marketplace economics are real ($88 per $100 on Fab)
3. AI-generated packs are explicitly allowed by marketplaces
4. The AI-3D production gap is documented and real
5. Multiple proven business models exist (Synty, Kenney, KitBash)
6. Your 1-year timeline + $100k Opus budget is realistic for v1

But:

- Asset packs are an art product, not just code. Quality matters
  beyond just "AI generated it." Plan for at minimum: human review,
  curation, style consistency enforcement, demo scenes.
- Marketplaces have curation hurdles. First submission rejection is
  common. Plan for 2-3 submission rounds per pack initially.
- This is a 12-24 month business, not a 30-day MVP. The compound
  arrives in year 2.
