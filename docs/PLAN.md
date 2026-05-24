# PLAN.md — asset-forge 12-month roadmap

$100k Opus budget. 1-year calendar. End-state: a working asset-pack
factory + 6-12 shipped commercial packs + recurring income.

## The product, defined

**asset-forge = the operator-facing factory** that takes a brief
("modular fantasy village, 80 props, low-poly, Unity+Unreal+Godot
compatible") and produces a marketplace-ready asset pack:

- 80 modular pieces with consistent style
- Clean topology (auto-retopo via QuadRemesher / instant meshes)
- Proper UV unwrap (Blender Smart UV + seam hints)
- PBR materials from a curated library (Material Maker / OpenPBR)
- LOD0..LOD3 per piece via gltfpack
- Snap-grid pivots, standardized naming
- Demo scene per target engine (Unity .unitypackage, Unreal
  .uasset zip, Godot .glb-bundled)
- README, license file, preview renders, video walkthrough
- Marketplace manifest (Fab + Unity + Itch.io + Gumroad)

The HUMAN OPERATOR (you) directs style, reviews output, makes
curation calls. AI does the grunt work.

## What we BUILD vs BUY vs STEAL

### BUILD (code we write)

1. **The orchestrator** — `asset-forge-cli`, the brain that takes a
   pack-brief and runs the pipeline end-to-end via flax-mcp tools.
2. **Auto-retopology wrapper** — wraps Blender's QuadRemesher or
   Instant Meshes; normalizes outputs.
3. **UV-unwrap automation** — Smart UV + seam-hint heuristics + LLM
   refine pass for edge cases.
4. **Style-consistency enforcer** — given a reference image / seed,
   force all pieces in the pack to match (control via prompt
   conditioning + post-process color/lighting match).
5. **Snap-grid pivot normalizer** — every piece's pivot rationalized
   for modular assembly.
6. **Marketplace manifest generator** — produces submission-ready
   bundles per target marketplace.
7. **The web showroom** — static-site generator that builds a
   sales page per pack (renders, demo videos, asset list).

### BUY (services / paid software, budgeted line items)

- **QuadRemesher Blender plugin** ($109 perpetual) — auto-retopology
  industry standard
- **Substance 3D Sampler subscription** ($20/mo) — AI-assisted
  texture authoring; ArmorLab is the cheaper alt
- **Marketplace seller fees** — Fab/Unity/Itch are free to list;
  Gumroad $10/mo for Pro
- **Render farm** for demo videos — $200-500/mo budgeted for
  cloud Blender rendering (e.g. Sheepit free + paid backup)
- **Domain + landing page hosting** — $20/yr + $10/mo Vercel/
  Cloudflare
- **Audio for demo videos** — $20/mo Epidemic Sound or one-time
  music packs

### STEAL (open-source we incorporate)

- **ProcFunc** (Princeton, BSD-3) — function-oriented procedural
  API for Blender geometry nodes. WRAP IT for procedural pieces.
- **AniGen** (SIGGRAPH 2026, MIT-ish) — auto-rig + skin from single
  image. Wire into the pipeline for character packs.
- **LL3M Blender RAG knowledge base** — their Blender API doc
  retrieval system is high-value; extract the RAG corpus.
- **gltfpack** (already wrapped in flax-meshopt-bridge)
- **TRELLIS / Hunyuan3D / SF3D / TripoSR** (already wrapped in
  flax-asset-gen)
- **Material Maker** — open-source procedural material authoring;
  bundle a curated material library
- **Infinigen** (Princeton, BSD-3) when it ships its procedural
  generators publicly
- **ahujasid/blender-mcp** (already vendored in flax-blender-bridge,
  21.9k stars)

## 12-month phasing

### Month 1 — Pack #1 manual end-to-end (the calibration pack)

**Goal:** ship ONE asset pack manually end-to-end. No automation.
Just to learn the real shape of the work.

- [ ] Pick a small, well-scoped pack: "low-poly fantasy props x 30"
- [ ] Generate 30 pieces via flax-asset-gen (TRELLIS/Hunyuan)
- [ ] Manual retopo on the 10 most important; auto-retopo the rest
- [ ] UV unwrap, material assignment, LOD generation
- [ ] Demo scene in Unity + Unreal + Godot
- [ ] Render previews, write README, license file
- [ ] Submit to **Fab** (88% cut, easier policy than Unity)
- [ ] Submit to **Itch.io** (you keep the rate you want)
- [ ] Submit to **Gumroad** (90% after fees)
- **Price point:** $9.99 launch / $19.99 normal

This pack probably won't make significant money. **It teaches us
the actual pipeline shape, including which automations matter most
and which marketplace rules bite.**

### Month 2-3 — Build asset-forge v1 from Pack #1's lessons

**Goal:** automate the pipeline based on what we learned, ship
Pack #2 with 50% less manual effort.

- [ ] `asset-forge-cli generate --brief brief.yaml` skeleton
- [ ] Wire flax-asset-gen as the generation router
- [ ] Wire flax-blender-bridge for Blender automation
- [ ] Wire flax-meshopt-bridge for LOD chain
- [ ] Wire flax-procedural for procedural pieces (props that
      benefit from scattering / WFC)
- [ ] Add auto-retopo (QuadRemesher CLI or Instant Meshes)
- [ ] Add UV-unwrap automation (Blender Smart UV + heuristics)
- [ ] Add manifest generator for Fab + Unity + Itch
- [ ] Add preview-render pipeline (Blender + Eevee/Cycles)
- [ ] Ship Pack #2 (another low-poly themed pack, ~50 pieces)
- [ ] Submit and learn from rejection cycles

### Month 4-5 — Style consistency + character pipeline

**Goal:** packs that look like Synty, not random AI mush. Plus add
character assets.

- [ ] Style-consistency enforcer (seed image → all pieces match)
- [ ] Material library curation (50 base PBR materials grouped
      by theme)
- [ ] Integrate AniGen for character auto-rig (skip if upstream
      isn't production-ready)
- [ ] Rigify-based fallback for humanoid characters
- [ ] Ship Pack #3 (character + environment bundle, ~$24.99)
- [ ] Ship Pack #4 (modular dungeon kit, ~$19.99)

### Month 6-7 — Marketing engine

**Goal:** stop hoping for marketplace algorithm; build owned channel.

- [ ] Landing page for asset-forge (Vercel / Cloudflare Pages)
- [ ] YouTube channel: "AI-built asset pack of the week" demos
- [ ] r/Unity3D, r/UnrealEngine, r/godot launch posts per pack
- [ ] Twitter/X presence (build-in-public approach)
- [ ] Discord for buyers + WIP previews
- [ ] Newsletter for pack-launch announcements
- [ ] Ship Pack #5 + #6

### Month 8-9 — Subscription / bundle layer

**Goal:** move from one-off sales to recurring revenue.

- [ ] "Asset-Forge Pass" — $19/mo for all packs + early access to
      WIP
- [ ] Or: "Asset-Forge Studio Tier" — $99/mo for commercial-pack
      licensing
- [ ] Ship Pack #7-#9
- [ ] First $1k-$5k MRR realistic by month 9

### Month 10-12 — Open-core the tooling

**Goal:** asset-forge-cli itself becomes a second product.

- [ ] Open-source asset-forge-cli on GitHub, MIT
- [ ] Paid tier: hosted asset-forge cloud (we run the GPU + serve
      packs)
- [ ] Paid premium-pipeline tier (style-consistency, premium
      materials)
- [ ] Ship Pack #10-#12
- [ ] Aim for $5k-$15k MRR by end of year 1

## Income targets (honest)

| Month | Packs shipped | Pack revenue | Tooling MRR | Total |
|---|---|---|---|---|
| 1 | 1 | $50-200 | — | small |
| 3 | 2 | $300-800 | — | small |
| 6 | 6 | $1k-3k | — | building |
| 9 | 9 | $2k-6k/mo | $500-2k | $2.5-8k/mo |
| 12 | 12 | $4k-10k/mo | $1k-5k | $5k-15k/mo |

Year-2 the catalog compounds. Year-3 the tooling can match or
exceed pack revenue if open-core works.

## The non-negotiables (covenant)

1. **Quality bar before automation.** Pack #1 is hand-crafted. We
   automate from observed pain points, not speculation.
2. **Marketplace-policy compliance.** AI disclosure on every pack.
   No "handmade" marketing. No copyrighted-character resemblance.
3. **Cross-engine from day 1.** Every pack ships Unity + Unreal +
   Godot compatible. Fab loves this; Unity-only loses to Fab's
   88% split.
4. **CC0 or paid, never AGPL/GPL contamination.** All upstream
   we steal from must be MIT/BSD/Apache/CC0 compatible.
5. **Build in public.** Twitter/YouTube/Discord from month 2.
   Marketing is part of the build, not a phase 2 afterthought.
6. **Receipts on every commercial release.** Asset provenance,
   license sidecar, SHA-256 from flax-asset-worker. Audit trail
   for marketplace disputes.

## What this plan does NOT do

- ❌ Compete with Synty on art direction in year 1 (their head start
  is real; we compete on AI-pipeline speed + pricing)
- ❌ Compete with KitBash3D on photoreal quality (their market is
  film + AAA; ours is indies)
- ❌ Try to build a marketplace ourselves (Fab/Itch already exist)
- ❌ Skip the human-curation step (AI-mush packs get rejected and
  destroy reputation)
- ❌ Pivot at month 3 because Pack #1 didn't sell well (we already
  decided 1-year commitment; honor it)
