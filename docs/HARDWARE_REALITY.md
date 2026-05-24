# HARDWARE_REALITY.md — what actually runs on 6 GB VRAM, all free

Your hardware: **6 GB VRAM** (single GPU). No paid SaaS. This doc
honestly answers "can we run this thing" for every item in
STEAL_INVENTORY.md and the BUILD list.

Verified 2026-05-24 against current upstream docs + release notes.

## Color codes

- ✅ **Works on 6 GB VRAM, free** — drop in
- ⚠️ **Marginal on 6 GB or has a catch** — use with care
- ❌ **Won't run on 6 GB or not free** — skip or replace
- 💻 **CPU-only, no VRAM concern** — works on anything

## AI 3D generation routes (the heaviest VRAM consumers)

| Route | VRAM | License | Cost | Verdict |
|---|---|---|---|---|
| **TripoSR** (Stability AI) | ~4 GB | MIT-ish | Free | ✅ Use this FIRST. Lightest. |
| **Hunyuan3D-mini** (Tencent) | ~6 GB | Permissive | Free | ⚠️ Tight on 6 GB; needs offload mode |
| **Stable Fast 3D (SF3D)** | ~6 GB | CC-BY-NC | Free | ⚠️ NON-COMMERCIAL license — DO NOT use for sellable packs |
| **TRELLIS** (Microsoft) | 6 GB minimum | MIT | Free (local) or HF Spaces (free remote) | ⚠️ HF Spaces version offloads compute to HuggingFace → free + zero VRAM cost. Local version is tight on 6 GB. |
| **Hyper3D / Rodin trial** | 0 GB local (API call) | Trial T&Cs | Free trial → paid | ⚠️ Trial limits; verify commercial-use clause |
| **AniGen** (VAST-AI) | **12-16 GB recommended** | NOASSERTION (MIT-ish) | Free | ❌ Does NOT run on 6 GB. Skip until you have a bigger GPU. |
| **AssetFormer** (ICLR 2026) | ~8-12 GB | research-leaning | Free | ❌ Research code, won't fit. Watch but don't integrate yet. |

### 🚨 SF3D license correction

**Stable Fast 3D is CC-BY-NC** — non-commercial use only. I missed
this in the prior steal inventory. **Cannot be used for sellable
asset packs.** Removing it from the route list.

### The actual viable generation stack on 6 GB

1. **TripoSR** — primary route. Fast, light, MIT, commercial-OK.
2. **TRELLIS via HuggingFace Spaces** — secondary route. Compute is
   on HF's servers, not your GPU. Free tier has rate limits but
   plenty for pack production (30 pieces/day is fine).
3. **Hunyuan3D-mini** with `--low-vram` / `--cpu-offload` — tertiary.
   Slower per piece, but works.
4. **Rodin trial via Blender** — quaternary. Free trial, verify
   commercial T&Cs before each pack ships.

Drop SF3D entirely. Drop AniGen until you upgrade GPU.

## Procedural / non-AI generation (no VRAM pressure)

| Tool | VRAM | License | Cost | Verdict |
|---|---|---|---|---|
| **ProcFunc** (Princeton) | 💻 CPU | BSD-3 | Free | ✅ Use. Pure Blender geometry-nodes wrapper. |
| **Infinigen** (Princeton) | 💻 mostly CPU | BSD-3 | Free | ✅ When their procedural generators ship publicly. Watch repo. |
| **flax-procedural** (already owned) | 💻 CPU | MIT | Free | ✅ 26 tools live. WFC, BSP, scatter, noise. |
| **Blender geometry nodes** | 💻 GPU-light | GPL via Blender | Free | ✅ Standard tool. |

## Retopology

| Tool | VRAM | License | Cost | Verdict |
|---|---|---|---|---|
| **Instant Meshes** | 💻 CPU | GPL ⚠️ | Free | ✅ Use as CLI subprocess. GPL boundary respected. |
| **QuadriFlow** | 💻 CPU | BSD ✅ | Free | ✅ Cleaner license than Instant Meshes; recommend FIRST |
| **Blender Voxel Remesh** | 💻 CPU | GPL via Blender | Free | ✅ Built into Blender. |
| **Blender Decimate** | 💻 CPU | GPL via Blender | Free | ✅ Built into Blender. |
| **QuadRemesher** | 💻 CPU | Commercial $109 one-time | Paid | ⚠️ Skip for now. Use only if budget allows after first pack sales. |
| **MutaMesh** | 💻 CPU | Commercial | Paid | ❌ Skip. |

**Retopology runs on CPU.** Your 6 GB VRAM is irrelevant for this.
Use QuadriFlow as default backend (BSD), Instant Meshes as
subprocess fallback, Blender's built-ins for fast/simple cases.

## UV unwrapping

| Tool | VRAM | License | Cost | Verdict |
|---|---|---|---|---|
| **Blender Smart UV Project** | 💻 CPU | GPL via Blender | Free | ✅ Default. |
| **Blender U-Net based unwrap** | 💻 CPU | GPL via Blender | Free | ✅ Built into 4.x. |
| **LLM seam-hint (our own)** | 0 GB local (API) | n/a | Free tier or cheap | ✅ Use Claude/GPT for seam hints; output is text, costs pennies per piece. Or run via Ollama free local. |

UV unwrap is CPU-bound + LLM-text-call. **Zero VRAM pressure.**

## Materials

| Tool | VRAM | License | Cost | Verdict |
|---|---|---|---|---|
| **Material Maker** | GPU-light (Godot-based shaders) | MIT | Free | ✅ Confirmed MIT, runs on modern GPUs incl. 6 GB. |
| **ArmorLab** | ~4-6 GB | Free for individuals | Free | ⚠️ AI texturing on GPU; tight on 6 GB. Optional, not critical. |
| **Blender Cycles/Eevee shader nodes** | 💻 fits 6 GB | GPL via Blender | Free | ✅ Default for procedural materials. |
| **Substance 3D Sampler** | needs more VRAM | Commercial $20/mo | Paid | ❌ Skip — costs money you said no to. |
| **OpenPBR** | n/a (spec) | Apache 2.0 | Free | ✅ Specification + reference; just use the standard. |

**Material Maker is the answer.** Open-source, MIT, runs on 6 GB,
node-based like Substance Designer. Build a curated library of 50
base PBR materials in Material Maker for the asset-forge starter
pack.

## Style consistency (CLIP + ControlNet)

| Tool | VRAM | License | Cost | Verdict |
|---|---|---|---|---|
| **OpenCLIP** (ViT-B/32) | ~2 GB | MIT | Free | ✅ Easy fit. |
| **OpenCLIP** (ViT-L/14) | ~4 GB | MIT | Free | ✅ Better quality, fits. |
| **OpenCLIP** (ViT-H/14) | ~8 GB | MIT | Free | ❌ Too big for 6 GB. |
| **ControlNet** (SD 1.5 base) | ~6 GB total stack | OpenRAIL | Free | ⚠️ Tight; use the small variants. |
| **ControlNet** (SDXL) | ~10 GB | OpenRAIL | Free | ❌ Won't fit. |

**Practical style pipeline on 6 GB:**
- OpenCLIP ViT-L/14 for outlier detection (4 GB, plenty of room)
- For regeneration, skip ControlNet locally; use HF Spaces
  (free tier) for ControlNet-conditioned re-generation. Free,
  rate-limited but workable.

## MCP infrastructure (already owned in flax-mcp)

All zero-VRAM, all free, all owned.

| Plugin | Status |
|---|---|
| flax-asset-gen | ✅ 6 tools live |
| flax-asset-worker | ✅ 9 tools live |
| flax-blender-bridge | ✅ 22 tools live (vendors ahujasid/blender-mcp 21.9k stars) |
| flax-meshopt-bridge | ✅ 6 tools live (gltfpack wrapper) |
| flax-procedural | ✅ 26 tools live |

## Asset sourcing (provider intake, no VRAM)

| Provider | License | Cost | Verdict |
|---|---|---|---|
| **PolyHaven** | CC0 | Free | ✅ Already wired in flax-asset-worker |
| **Kenney** | CC0 | Free | ✅ Already wired |
| **Open Heritage 3D** | Mostly CC0 / public domain | Free | ✅ Already wired |
| **Sketchfab** | Mixed (filter to CC-BY) | Free + paid tier | ⚠️ Auth-gated; license filter matters |
| **BlenderKit** | Mixed | Free + paid | ⚠️ Auth-gated |
| **Meshy Library** | Mixed | Free + paid | ⚠️ Verify per asset |
| **gltfpack** | MIT | Free | ✅ Already wrapped |

## LL3M / BlenderRAG — STATUS CHANGE

**Bad news:** LL3M's hosted server is **DISCONTINUED** as of
2026-05-24. Quote from their repo:

> "The model used in the paper, Claude Sonnet 3.7, has been
> retired. As a result, we have discontinued the LL3M server."

Their Blender addon requires login to their discontinued server.
**LL3M is DEAD as a direct integration.**

**What we do instead:**
1. Re-implement BlenderRAG ourselves. Public Blender ScriptReference
   is free to scrape. We build our own RAG corpus over Blender API
   docs. Costs nothing.
2. Use a free local LLM via **Ollama** (Qwen 2.5 Coder 7B fits in
   6 GB; Mistral Small fits; Llama 3.2 fits). Free, local, no API
   key.
3. Or use Anthropic/OpenAI free trial credits for the first weeks.

This adds maybe 1-2 days of work but removes a dead dependency.

## Alternative LL3M-like projects (verified live)

- **JustThreed** (MIT, MIT, 2026-04) — Blender + MCP + works with
  Claude/Cursor/Ollama/local models. Active maintenance. Use this
  pattern as reference for our orchestrator if needed.
- **saofund/LLM-Blender-Agent** (MIT, 20 stars) — Blender +
  Function-Calling LLMs (Claude / DeepSeek / Zhipu / Moonshot).
  Wraps BlenderMCP plugin.

Both prove the pattern. Both are MIT. Both are stealable for ideas.

## BUILD-side items (asset-forge subsystems)

| Subsystem | Runs on | VRAM | Cost | Verdict |
|---|---|---|---|---|
| **orchestrator** | Python on CPU | 0 GB | Free | ✅ |
| **mcp_client** | Python on CPU | 0 GB | Free | ✅ |
| **retopo** wrapper | CPU subprocess | 0 GB | Free | ✅ |
| **uvunwrap** wrapper | CPU + Blender + tiny LLM call | <1 GB | Free | ✅ |
| **style** enforcer | OpenCLIP ViT-L/14 | ~4 GB | Free | ✅ |
| **snap_grid** normalizer | CPU + Blender | 0 GB | Free | ✅ |
| **manifest** generator | Python on CPU | 0 GB | Free | ✅ |
| **showroom** generator | Python on CPU + Jinja | 0 GB | Free | ✅ |

**Every BUILD subsystem fits on 6 GB.** The only VRAM-consuming
parts are the AI-3D generation and CLIP style scoring, both of
which we've sized down to fit.

## The honest "what's free, what runs" verdict

| Originally promised | Reality on 6 GB / free | Action |
|---|---|---|
| TRELLIS local | ⚠️ Tight on 6 GB | Use HF Spaces instead — free remote |
| Hunyuan3D-mini local | ⚠️ Works with `--low-vram` | OK, slower |
| SF3D | ❌ CC-BY-NC, cannot sell | **DROP** |
| TripoSR | ✅ Lightest, fits easily | **Primary route** |
| Rodin trial | ⚠️ Trial T&Cs | Verify per use |
| AniGen | ❌ Needs 12+ GB | **DROP for now** (add later when GPU upgraded) |
| LL3M BlenderRAG | ❌ Server discontinued | **Re-implement free** from public Blender docs |
| ProcFunc | ✅ CPU-only, BSD-3 | Use directly |
| Infinigen | ✅ Watch for full release | Add when public |
| Material Maker | ✅ MIT, fits on 6 GB | Use directly |
| Instant Meshes | ✅ CPU-only, GPL via subprocess | Use directly |
| QuadriFlow | ✅ CPU-only, BSD | Use directly (preferred over Instant Meshes) |
| QuadRemesher | ❌ Costs $109 | Skip until first revenue |
| Substance Sampler | ❌ Paid $20/mo | Skip (Material Maker replaces) |
| ahujasid/blender-mcp | ✅ Already owned | — |
| gltfpack | ✅ Already owned | — |
| Three.js | ✅ MIT, browser-only | — |
| OpenPBR | ✅ Apache 2.0, spec only | — |
| OpenCLIP ViT-L/14 | ✅ Fits in 4 GB | Use for style scoring |
| Cloudflare Pages | ✅ Free tier | Showroom hosting |

## Net: revised generation route priority for asset-forge

In `.env.example`, the route order should be:

```env
ASSET_FORGE_GEN_ROUTES=triposr,trellis-hf,hunyuan-mini,rodin-trial
```

(SF3D removed entirely; AniGen removed entirely.)

## One unavoidable truth

**6 GB VRAM is the bottleneck.** Everything fits, but barely. The
real long-term answer is GPU upgrade. A used **RTX 3060 12 GB**
costs ~$200-300 on the second-hand market and would:
- Make AniGen viable (= character/creature packs)
- Make TRELLIS comfortable locally
- Make ControlNet local (= faster style-consistency regen)
- Make Hunyuan3D-mini comfortable

**Not required for v1.** First pack ships on 6 GB. After Pack #1
sells some copies, the GPU upgrade pays for itself.

For now: **6 GB + free + HF Spaces fallback = everything we need.**
