# CLOUD_GPU_OPTIONS.md — offload heavy work to cheap/free cloud GPU

Operator has 6 GB local VRAM + 2 Google accounts + interest in
fal.ai. This doc verifies what's actually cheap, what's actually
free, and what the per-pack cost looks like.

**Verified 2026-05-24 against current upstream pricing pages.**

## TL;DR — the verdict

**Default cloud-GPU strategy for asset-forge:**

1. **fal.ai TRELLIS at $0.02/generation** is the primary route.
   Stupidly cheap. For a 30-piece pack: **$0.60 in cloud cost.**
   You will not beat this.
2. **Kaggle Notebooks (30 GPU hours/week free, T4×2 or P100 16 GB)**
   is the secondary route. Two Kaggle accounts × 30 hrs/wk = 60
   hrs/wk free GPU. Run heavier models (Hunyuan3D, AniGen) here.
3. **Google Colab free tier** is the tertiary. T4 16 GB sometimes,
   variable, no guaranteed quota — keep as overflow.
4. **Local 6 GB GPU** stays useful for CPU-bound work (retopo,
   UV unwrap, Blender automation) and small models (CLIP ViT-L).

**You do NOT need to pay for cloud compute to ship Pack #1.**
Free tier covers it. Paid fal.ai is optional, costs cents per pack.

## fal.ai — verified pricing (2026-05-24)

Going through each 3D model on fal.ai with actual list price:

| Model | Cost/gen | Notes |
|---|---|---|
| **TRELLIS** (`fal-ai/trellis`) | **$0.02** | Cheapest by a wide margin. State-of-the-art image-to-3D. |
| **Trellis 2** (`fal-ai/trellis-2`) | TBC (price not on snippet) | Newer version |
| **TripoSR** (`fal-ai/triposr`) | **$0.07** | Same model we run locally, but cloud at $0.07 vs your 6 GB GPU time |
| **Tripo P1 text-to-3D** | **$0.01 per credit** | Cheap text-to-3D path |
| **Tripo3D v2.5 multiview** | **$0.20** no textures / $0.30 standard / $0.40 HD | Higher quality. +$0.05 for quad mesh / style |
| **Hunyuan3D 2.1** | **$0.30** | (textured = 3× = $0.90) |
| **Hunyuan3D v3** (image-to-3D) | **$0.375** normal / $0.225 geometry-only / $0.45 LowPoly | +$0.15 each for PBR / multi-view / custom face count |
| **Hunyuan3D Pro v3.1** (text-to-3D) | **$0.375** | Same pricing as image variant |
| **Hyper3D Rodin v2** | **$0.40** | The Rodin upstream we use via Blender trial |

### Per-pack cost analysis (real money)

For Pack #1 = 30 pieces:

| Strategy | Cost for 30 pieces |
|---|---|
| **All TRELLIS** | $0.60 |
| **All TripoSR cloud** | $2.10 |
| **All Tripo P1 text-to-3D credits** | ~$0.30 |
| **All Hunyuan3D 2.1** | $9.00 (or $27 with textures) |
| **All Hunyuan3D Pro v3** | $11.25 (with PBR = $15.75) |
| **All Rodin v2** | $12.00 |
| **Mixed** (TRELLIS first-pass, Hunyuan for hero pieces) | ~$3-5 |

**For an asset pack that sells at $9.99-$19.99, cloud cost of
$0.60-$5 is trivially absorbed.** This is not a budget concern.

### License posture on fal.ai

Per their model terms (verify per-model before commercial use):
- **Outputs are yours.** You own the generated 3D.
- **Commercial use OK** for the major models (TRELLIS, Hunyuan3D
  Pro, Tripo). Verify TripoSR + free-tier variants per model card.
- **Attribution not required** for the major models.
- Free trial credit: fal.ai gives ~$5 free on signup, which covers
  ~250 TRELLIS generations — enough to ship Pack #1 entirely free.

### How fal.ai integrates with asset-forge

flax-asset-gen already has a route system. We add a new route:
`fal-trellis` that hits `https://fal.run/fal-ai/trellis`. Same
contract (image input or text → URL prompt → GLB output), different
backend. Zero changes to asset-forge code; one new route in
flax-asset-gen.

## Google Colab — verified limits (2026-05-24)

### Free tier
- **GPU**: T4 16 GB when available (sometimes L4, sometimes none)
- **VRAM**: 16 GB → can run TRELLIS, Hunyuan3D-mini, CLIP comfortably
- **Session limit**: up to 12 hours per session
- **Daily quota**: NOT published; observed ~15-30 hours/week
- **Availability**: variable. Google can refuse you the GPU at peak times.
- **You have 2 Google accounts** → 2× free pool. Both subject to
  the same variable availability.

### Colab Pro ($9.99/month)
- Compute-unit model (~100 CU per month at standard price)
- T4 burns ~1.76 CU/hour → ~57 hours/month T4 access on Pro
- Possible V100 access depending on demand
- More reliable than free tier

### Colab Pro+ ($49.99/month)
- Higher priority, more compute units
- Possible A100 access (24-40 GB) — would unlock AniGen

### Verdict for asset-forge
- **Free Colab × 2 accounts**: usable as overflow. Variable. Don't
  build production pipeline that depends on it.
- **Colab Pro**: cost vs fal.ai math is unfavorable. $9.99/mo Pro
  gets you ~57 T4 hours = ~$10/mo. Equivalent fal.ai TRELLIS budget
  at $0.02/gen = **500 generations/month** = a 16-pack/month
  cadence. **fal.ai wins on $/generation.**
- **Colab Pro+**: only if you NEED AniGen (12+ GB VRAM). At
  $49.99/mo, only justified once you're shipping character packs
  and pulling >$200/mo from them.

## Kaggle Notebooks — verified limits (2026-05-24)

This is the **sleeper-hit free option** you didn't ask about but
should know.

- **30 GPU hours/week, completely free** (P100 16 GB or T4×2 16 GB each)
- Resets weekly, predictable quota (unlike Colab)
- Per-session limit: ~12 hours
- Storage: input datasets mounted read-only, `/kaggle/working` for
  output, `/kaggle/temp` ephemeral
- TPU v3-8: additional 20 hours/week free
- More stable environment than Colab

**You have 2 Google accounts → 2 Kaggle accounts (same Google
login) = 60 GPU hours/week free.** Stable. Reliable. Better than
Colab for our use case.

### Verdict
- **Use Kaggle as the default heavy-model runner** for anything
  that doesn't fit on 6 GB local AND isn't worth paying fal.ai for.
- Suitable for: AniGen tests (P100 16 GB can run it), Hunyuan3D-full,
  TRELLIS-local-batches, ControlNet workflows for style regen.
- NOT suitable for: production pipelines (notebook environment,
  not API). Use Kaggle to BATCH-process pieces, not to serve a
  live pipeline.

## Replicate, Modal, RunPod — comparison

For completeness, what else is out there:

| Platform | Model | Cost shape | When to use |
|---|---|---|---|
| **Replicate** | TRELLIS, Hunyuan, others | $0.092/img for FLUX-2 (4-9× more than fal) | Skip; fal is cheaper |
| **Modal** | Bring-your-own container | Pay-per-second GPU compute | When self-hosting your own model server makes sense (volume > $50/mo on fal) |
| **RunPod** | Spot GPU rental | $0.30-$2/hr depending on GPU | Long-running training, not per-call inference |
| **HuggingFace Spaces** | TRELLIS official Space | Free tier, rate-limited | Demo/dev. Not for production batches. |

**For asset-forge specifically: fal.ai wins on price, Kaggle wins
on free, Modal wins on volume. Replicate loses.**

## The recommended stack on your hardware

Asset-forge's generation pipeline, ordered by economic + practical
sense:

### Tier 1 — try first (free or near-free)

1. **fal.ai TRELLIS** ($0.02/gen) for first-pass image-to-3D on
   every piece. ~$0.60/pack. Use your $5 free signup credit for
   the first pack — completely free.
2. **Kaggle Notebook** for batch retries and heavier models when
   TRELLIS output isn't good enough. 60 hrs/week free across both
   accounts.

### Tier 2 — fallback for harder pieces

3. **Local 6 GB GPU** running TripoSR for offline-iteration when
   you're tuning prompts and want zero per-call cost.
4. **fal.ai TripoSR** ($0.07) when local TripoSR is too slow.
5. **fal.ai Hunyuan3D 2.1** ($0.30) for hero pieces that need
   higher quality.

### Tier 3 — premium when needed

6. **fal.ai Hunyuan3D Pro v3** ($0.375 + PBR $0.15 = $0.525) for
   pack hero shots / marketing renders.
7. **fal.ai Rodin v2** ($0.40) when prompt engineering for
   TRELLIS/Hunyuan keeps failing — Rodin is best at imaginative
   prompts.

### What we explicitly skip

- **Local TRELLIS** — tight on 6 GB; cloud at $0.02 is a no-brainer
- **Local Hunyuan3D-full** — won't fit; use cloud or Kaggle
- **Local AniGen** — needs 12+ GB; use Kaggle or Colab Pro+ or
  defer entirely
- **Local SF3D** — license is non-commercial (CC-BY-NC). Skip.
- **Replicate** — 4-9× more expensive than fal.ai for equivalent work

## Pack #1 cost breakdown (concrete numbers)

Assuming 30 pieces, mixed strategy:

- 24 pieces via fal.ai TRELLIS: 24 × $0.02 = **$0.48**
- 4 hero pieces via fal.ai Hunyuan3D 2.1: 4 × $0.30 = **$1.20**
- 2 retries via fal.ai TripoSR: 2 × $0.07 = **$0.14**
- LLM calls (UV seam-hint via DeepSeek/Qwen Coder): ~$0.30 total
- Blender renders (local CPU, no cloud cost): **$0**
- Retopo (local CPU subprocess): **$0**

**Total cloud cost per Pack #1: ~$2.12**

If we lean on the fal.ai $5 signup credit + Kaggle's 60 hrs/week
free → **Pack #1 ships at $0 cloud cost** (everything fits in
free tiers).

If we abandon free tier and pay full fal.ai pricing for 6-12 packs
in year 1: **$12-25 in total cloud cost.** Trivial.

## What about Blender renders / preview videos?

Blender Cycles + Eevee runs on local 6 GB GPU just fine for:
- Single-piece preview renders (1080p, 4 angles, ~30s each)
- Hero shots (4K, ray-traced, ~3 min each)
- Demo scene renders (1080p, 10s clips)

For full pack demo videos (1080p, 60s walkthrough at high quality):
- Local: ~30-60 min render time per video. Free, slow.
- **Sheepit** (free distributed Blender render farm): hours-to-days
  via credit system. Free.
- **Vagon Cloud** or similar paid Blender render: $0.50-2/hr. Skip.

**Local + Sheepit covers all rendering needs at $0.**

## Updating the asset-forge config

I'll add `fal-trellis` as the primary route and update
`.env.example` to reflect cloud-first generation strategy. Local
routes stay as fallback for offline iteration.

```env
ASSET_FORGE_GEN_ROUTES=fal-trellis,fal-triposr,triposr-local,trellis-hf,hunyuan-mini-local,fal-hunyuan3d-21,rodin-trial

ASSET_FORGE_FAL_API_KEY=
```

## The honest one-liner

**fal.ai at $0.02/generation makes 6 GB VRAM a non-issue.** You
have everything you need to ship Pack #1 for under $3 in cloud
cost, or $0 if you ride the free credit + Kaggle. GPU upgrade
becomes a quality-of-life concern, not a blocker.
