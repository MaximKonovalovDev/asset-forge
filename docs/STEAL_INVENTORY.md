# STEAL_INVENTORY.md — every stealable thing, catalogued

Every open-source / public technique we plan to incorporate. Each
entry includes: what, source, license, integration plan, license
risk assessment.

**Rule: any STEAL must be either (a) wrapped via subprocess/CLI (no
code linkage), (b) MIT/BSD/Apache permissive, or (c) explicitly
re-implemented by us using only public ideas (not their code).**

## ALREADY OWNED (in flax-mcp, just consume via MCP)

### flax-asset-gen — AI 3D generation router (4 viable routes on 6 GB)
- Routes verified usable: TripoSR (MIT, primary), TRELLIS via HF
  Spaces (free, remote compute), Hunyuan3D-mini (with `--low-vram`),
  Rodin trial (verify T&Cs per pack)
- **Stable Fast 3D removed**: CC-BY-NC license, cannot be used in
  sellable packs. flax-asset-gen still exposes the route but
  asset-forge skips it.
- See `docs/HARDWARE_REALITY.md` for the 6 GB VRAM compatibility
  matrix.
- **How we use it**: mcp_client → `asset_gen/text_to_3d` and
  `asset_gen/image_to_3d`

### flax-asset-worker — 7-provider intake + SHA-256 + license sidecar
- Providers: PolyHaven, Kenney, Sketchfab, BlenderKit, Meshy Library,
  Open Heritage 3D, mat-vis
- License: per-provider; flax-asset-worker refuses CC-BY-ND
- **How we use it**: mcp_client → `asset_worker/install` for sourcing
  base meshes / textures / HDRIs to compose with AI-generated pieces

### flax-blender-bridge — 22 Blender tools (vendors ahujasid)
- Vendors: ahujasid/blender-mcp (MIT, 21.9k stars)
- License: MIT (vendored upstream)
- **How we use it**: mcp_client → all Blender automation (modeling,
  materials, rendering)

### flax-meshopt-bridge — gltfpack wrapper
- Upstream: zeux/meshoptimizer + gltfpack (MIT)
- License: MIT
- **How we use it**: mcp_client → `meshopt/lod_chain`,
  `meshopt/draco_compress`, `meshopt/profile_glb`

### flax-procedural — WFC / dungeon / scattering / terrain
- Includes: DeBroglie WFC, BSP dungeons, cellular caves, Poisson scatter,
  marching cubes, L-systems
- License: MIT
- **How we use it**: mcp_client → procedural pieces in packs (e.g.
  "scatter 50 rock variants across a 10×10 area for a nature pack")

## TO INTEGRATE (open-source, permissive)

### LL3M (Princeton/Threedle) — DISCONTINUED
- Source: github.com/threedle/ll3m (526 stars)
- **STATUS: server discontinued 2026.** Their hosted server required
  Claude Sonnet 3.7 which has been retired. Repo notice quote:
  "we have discontinued the LL3M server."
- **Decision**: we **DO NOT integrate LL3M.** Re-implement BlenderRAG
  ourselves from public Blender ScriptReference (free, MIT-friendly,
  no upstream dependency on a dead server).
- **Alternative live patterns** (MIT, active 2026):
  - **JustThreed** (Phanikondru/justthreed) — Blender + MCP + works
    with Claude/Cursor/Ollama. MIT. Reference pattern.
  - **saofund/LLM-Blender-Agent** — Blender + Function-Calling LLMs
    (Claude/DeepSeek/Zhipu/Moonshot). MIT. Reference pattern.
- **Risk**: zero, since we don't integrate the dead code at all.

### ProcFunc (Princeton) — function-oriented procedural Blender API
- Source: github.com/princeton-vl/procfunc
- License: BSD-3 ✅
- **Take**: the procfunc.ops API for procedural generators. WRAP IT,
  use directly. BSD-3 is permissive.
- **Risk**: low.

### AniGen (VAST-AI Research, SIGGRAPH 2026) — DEFERRED
- Source: github.com/VAST-AI-Research/AniGen (299 stars)
- License: NOASSERTION (MIT-style permissive on inspection)
- **STATUS: requires 12-16 GB VRAM.** Won't run on the operator's
  6 GB GPU. **Deferred** until GPU upgrade (a used RTX 3060 12 GB
  ~$200-300 makes this viable).
- **Take when viable**: S^3 fields pipeline for character auto-
  rigging. Subprocess CLI integration.
- **For now**: character packs are deferred to Pack #4+ (after we
  have first-pack revenue to upgrade GPU). Packs #1-#3 are
  prop/environment-only.
- **Risk**: zero, since we don't integrate it on this hardware.

### Instant Meshes — auto quad remesher
- Source: github.com/wjakob/instant-meshes
- License: GPL ⚠️
- **Take**: invoke as CLI subprocess. GPL boundary is the
  subprocess boundary (per FSF guidance). We ship Instant Meshes
  binary alongside ours with its own GPL license file.
- **Risk**: medium. Legal review of "subprocess invocation of GPL CLI
  while shipping our proprietary code" before commercial release.

### QuadriFlow — research quad remesher
- Source: github.com/hjwdzh/QuadriFlow
- License: BSD ✅
- **Take**: same as Instant Meshes but cleaner license. Subprocess
  CLI wrapper.
- **Risk**: low.

### Material Maker — open-source procedural material authoring
- Source: github.com/RodZill4/material-maker
- License: MIT ✅
- **Take**: a curated library of 50 base PBR materials produced in
  Material Maker, included as the asset-forge material starter pack.
  Procedural means we can vary per pack within style bounds.
- **Risk**: low. Verify that MM-produced .mat files are not
  copyleft-tainted.

### gltfpack — mesh optimizer CLI
- Already in flax-meshopt-bridge. MIT. Subprocess.
- **Risk**: zero.

### Three.js — GLB viewer for showroom
- Source: github.com/mrdoob/three.js
- License: MIT ✅
- **Take**: embed the GLB loader + orbit controls in every showroom
  page. Static-site, MIT, perfect fit.
- **Risk**: zero.

### OpenUSD (NVIDIA + AOUSD)
- Source: github.com/PixarAnimationStudios/OpenUSD
- License: Modified Apache 2.0 ✅
- **Take**: optional USD export per piece (for studios that want
  USD pipeline). Use OpenUSD Exchange SDK patterns.
- **Risk**: zero. Apache 2.0 is permissive.

### CLIP / OpenCLIP — style consistency embeddings
- Source: github.com/mlfoundations/open_clip
- License: MIT ✅
- **Take**: CLIP image embeddings for the style.enforce_pack_style
  outlier-detection pass.
- **Risk**: zero.

### Infinigen (Princeton, when public)
- Source: github.com/princeton-vl/infinigen
- License: BSD-3 ✅
- **Take**: procedural generators when they release them
- **Risk**: zero. Watch the repo.

## TO WATCH (research code, not yet integrable)

### AssetFormer (ICLR 2026)
- Modular 3D asset generation via autoregressive transformer
- License: unclear in current pre-release
- **Status**: monitor. Could become a primary route in 12-18 months.

### Graph-CAD (ICLR 2026)
- Text-to-CAD via hierarchical graph decomposition
- License: unclear
- **Status**: monitor.

### Hyper3D / Rodin (commercial via Blender bundle)
- Already accessible via flax-asset-gen's Blender-Rodin-trial route
- **Status**: keep using; if they shut down free trial we lose a
  route but have 4 fallbacks

## DO NOT TOUCH (license-incompatible or risk)

### Synty's actual asset files
- Even though their style is public, their meshes/textures are
  proprietary. **Generate "Synty-style" via prompt prefix, never
  copy their files.**

### Quixel Megascans
- Bound to Epic ecosystem terms; commercial use complicated.
- Skip.

### Any AGPL-licensed Blender addon
- AGPL is viral. **Hard veto.** Even if it's the best at its job.

### CoplayDev's Unity MCP code
- MIT, but it's their commercial product's loss-leader. Don't fork.
  We talk to flax-mcp, not their stuff.

### dmae97/gamedev-all-in-one-mcp
- AGPL-3. **Hard veto** for direct integration. We can read it for
  ideas but cannot reuse code.

## License compliance gate

Before pack #1 ships:

- [ ] Every direct dependency (in pyproject.toml) is MIT/BSD/Apache
- [ ] Every CLI subprocess we invoke has its license file shipped
      alongside our binary (Instant Meshes, gltfpack, etc.)
- [ ] AI-generation routes verified for commercial-use rights:
  - [ ] TRELLIS — Microsoft, check terms
  - [ ] Hunyuan3D — Tencent, check terms (last verified: permissive)
  - [ ] StableFast3D — Stability AI, check terms
  - [ ] TripoSR — Stability AI, check terms
  - [ ] Rodin trial — Hyper3D, commercial-use OK on paid tier
- [ ] No GPL contamination in our shipped Python code
- [ ] All vendored sources have NOTICE / attribution files in `vendor/`

This list is mandatory pre-launch reading. **Treat it as a CI gate**
before any pack-1 sales transaction.
