# COMPETITIVE_MOAT.md — exactly why asset-forge will be superior

The honest assessment of where the moat actually lives, vs where
it doesn't.

## The competitive landscape (verified 2026-05-24)

| Player | Position | Strength | Weakness |
|---|---|---|---|
| **Synty** | Premium catalog (130+ packs) | Style consistency, brand | Slow output, manual production, $$$$ |
| **KitBash3D** | AAA cinematic kits, subscription | Quality, brand, Cargo platform | $$$$, not for indies |
| **Quaternius / DevAssets / Kenney** | Free/CC0 + Patreon | Audience, trust, volume | Income ceiling per creator |
| **Meshy / Tripo / Rodin / 3D AI Studio** | AI-3D as SaaS | Speed, free tiers | Stop at "raw mesh", not asset |
| **CoplayDev / unity-mcp** | Unity MCP server (10k stars) | Tool count, contributors | Unity-only, agent-side not pack-side |
| **Monolith (UE5)** | 1,125-action Unreal MCP | Depth | Unreal-only, agent-side |
| **LL3M (Princeton)** | LLM agents writing Blender Python | Research-grade | Not productized, no pack output |
| **AssetFormer (ICLR 2026)** | Modular 3D from text | Research breakthrough | Code only, not pack output |
| **dmae97/gamedev-all-in-one-mcp** | Cross-engine MCP unifier | Multi-engine concept | AGPL, 2 stars, stale, 13-20 tools/engine |

## Where asset-forge wins

### Win #1: The "raw mesh → asset" gap is real and documented

Every AI-3D player STOPS at mesh generation. The gap to "marketplace-
ready asset pack" is:
- Auto-retopology (we wrap Instant Meshes / QuadriFlow / QuadRemesher)
- UV unwrapping with proper texel density (we ship LLM seam-hint)
- Material assignment with style consistency (we enforce via CLIP)
- LOD chains (already in flax-meshopt-bridge)
- Snap-grid normalization (nobody else does this for AI output)
- Per-engine export with demo scenes (manifest module)
- AI disclosure compliance (manifest module)

**Nobody else productizes this gap end-to-end.** Research papers do
fragments. Commercial AI-3D tools skip it entirely.

### Win #2: We already own the upstream MCP infrastructure

flax-mcp = 70+ asset-pipeline tools across 5 plugins. Already
shipped, tested, maintained. Our competitors building similar
pipelines have to write that from scratch.

**Time advantage: 6-12 months of head start that's already banked.**

### Win #3: Marketplace economics on Fab (88% cut)

Most asset-pack creators anchor to Unity Asset Store (70%). We
anchor to Fab (88%) and treat Unity as secondary. **26% revenue
uplift on identical work.** This is structural, not skill-based.

### Win #4: Style consistency via CLIP-pass + ControlNet

This is the #1 reason AI-generated packs get rejected by
marketplaces. We enforce style consistency at three points:
1. Generation-time (style prefix + seed lock)
2. Post-generation review (CLIP outlier detection)
3. Outlier regeneration (ControlNet-conditioned)

Nobody ships this. Skip this step = AI mush = rejected.

### Win #5: Modular snap-grid normalization

The unsexy module. Why Synty packs sell: pieces snap together.
Why most AI-generated packs don't sell: random pivots, random
scales. We normalize. Result: 30 props that build a village,
not 30 props that float.

### Win #6: Cross-engine from day 1

Every pack ships Unity + Unreal + Godot. Fab loves cross-engine.
Unity-only packs lose to cross-engine packs of equivalent quality.

### Win #7: Receipts + license sidecar from flax-asset-worker

Every piece in every pack has SHA-256 provenance + license sidecar
+ source attribution. When (not if) a marketplace asks "is this
your IP," we have an audit trail. Competitors will be scrambling;
we click a button and produce the receipt.

### Win #8: The showroom (owned distribution)

Marketplace listings rank for "buy fantasy pack." Our showroom
ranks for the long-tail (10,000 "low-poly X reference 3D model"
queries). Owned organic channel that compounds.

## Where asset-forge does NOT win (be honest)

### Loss #1: Art direction in year 1

Synty has 130 packs over 10 years. We can't match their style
breadth in year 1. **Mitigation**: pick narrow themes per pack,
nail the style on each one, build catalog over 12-24 months.

### Loss #2: Photoreal quality vs KitBash3D

KitBash3D's market is film + AAA. We're not competing for that.
**Mitigation**: explicitly position as "stylized + low-poly +
indie" niche. Different segment entirely.

### Loss #3: Free-tier audience growth vs Kenney

Kenney has years of free-asset audience. We can't out-free Kenney.
**Mitigation**: paid-first business model, smaller audience but
higher per-unit revenue. Different game.

### Loss #4: AAA pipeline integration vs commercial tools

Studios with Houdini + USD pipelines won't drop them for asset-
forge. **Mitigation**: target indies + small studios where pipeline
overhead is the bottleneck, not the quality.

## The moat-decay risks (what could erode our position)

### Risk 1: Meshy or Tripo adds auto-retopo + UV (12-18 months out)

Probability: medium-high. Both are venture-backed and aware of the
gap.
**Counter**: by then, we'll have the catalog + audience + showroom
SEO + brand. Compete on style and curation, not on raw pipeline.

### Risk 2: AssetFormer (ICLR 2026) becomes productized

Probability: low for first 18 months (academia → product is slow).
**Counter**: we use AssetFormer ourselves as a route when it
matures.

### Risk 3: Princeton releases Infinigen with full procedural packs

Probability: 6-12 months.
**Counter**: we wrap Infinigen as an additional generation route.
BSD-3 license = safe to integrate.

### Risk 4: Unity loosens its MCP gating, the moat-by-anger fades

Doesn't affect asset-forge. We're not in the MCP-server market;
we're in the asset-pack market. Different game.

### Risk 5: A major asset-pack maker (Synty?) adds AI to their
pipeline

Probability: medium. They'd be slow to ship (corporate inertia).
**Counter**: by the time they ship, we have catalog + brand. Our
moat is operational speed; theirs is incumbency.

## The honest summary

**asset-forge wins if we execute.** The market gap is real. The
infrastructure advantage from flax-mcp is real. The Fab economics
are real. The style-consistency moat is defensible.

**asset-forge loses if we don't ship.** Every month without a pack
in market is a month a competitor catches up. The 12-month plan
isn't padding; it's the minimum viable timeline.

**The single biggest risk is the operator (you) starting and not
finishing.** Documented elsewhere as the pattern. The covenant in
PLAN.md ("1-year commitment, no pivot, 6-12 packs minimum") is
the response to that risk.
