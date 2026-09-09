# asset-forge

**AI-driven game asset pack creation pipeline.** You direct, AI produces.
Output: production-ready, marketplace-sellable, multi-engine asset packs.

> Origin: built inside `flax-game-studio` (admin mirror under my name).
> License: proprietary, flax-game-studio — see LICENSE. Not open source.

## Quick start

```powershell
pip install -e .
asset-forge --help
```

Pipeline: orchestrator → materials → retopo → LOD → previews → manifest → export → showroom. Talks to flax-mcp as an MCP client (same way Claude Code does); flax-mcp itself stays unchanged.

Born from: flax-mcp's existing 70-tool asset-pipeline surface
(flax-asset-gen + flax-asset-worker + flax-blender-bridge +
flax-meshopt-bridge + flax-procedural). asset-forge is the
**operator-facing product** that turns that existing infrastructure
into a sellable asset-pack factory.

## Repo boundary (important)

**asset-forge is a STANDALONE repo, not a flax-mcp plugin.**

- Lives in this repo (standalone checkout, any path)
- Does **not** modify `C:\flax\flax-mcp\` — flax-mcp is unchanged
- Talks to flax-mcp as an **MCP client over :8765** (same way
  Claude Code does)
- Has its own proprietary license (see LICENSE), its own CI, its own release cadence
- Can be open-sourced later without dragging flax-mcp along
- Sold as a commercial product without exposing flax-mcp internals

flax-mcp's 5 asset-related plugins (flax-asset-gen, flax-asset-worker,
flax-blender-bridge, flax-meshopt-bridge, flax-procedural) **stay
where they are**. They are the MCP-tool layer for AI agents working
in Flax projects. asset-forge is one such agent — a specialized one
focused on producing sellable packs end-to-end.

If at month 6+ we find genuinely engine-agnostic MCP-tool patterns
worth contributing back, those can graduate into flax-mcp as
patches. But day-1 architecture is: **asset-forge OUTSIDE,
flax-mcp UNCHANGED.**

## Project commitment

- **$100k Opus dev budget**, **1-year timeline**
- Built **on top of** flax-mcp (as a client), not a rewrite
- **Primary income path:** sell asset packs (Fab/Unity/Itch.io/Gumroad/own store)
- **Secondary income path:** sell the asset-forge tooling itself
  (open-core + hosted + premium tiers) — Synty-the-business shape,
  not Synty-the-art shape

## Status

Day 0 scaffold. See:
- `docs/PLAN.md` — 12-month roadmap, $100k budget, BUILD/BUY/STEAL split
- `docs/MARKET.md` — research from 15 strikes (Fab 88% cut, production gap, competitive landscape)
- `docs/STEAL_INVENTORY.md` — every stealable thing catalogued + license risk
- `docs/COMPETITIVE_MOAT.md` — 8 wins, 4 honest losses, 5 moat-decay risks
- `docs/HARDWARE_REALITY.md` — 6 GB VRAM compatibility per tool
- `docs/CLOUD_GPU_OPTIONS.md` — fal.ai / Kaggle / Colab pricing,
  Pack #1 ships for **~$2 cloud cost** ($0 with free credits)
