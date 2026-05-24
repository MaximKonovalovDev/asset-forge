# orchestrator — the pack-production brain

The state machine that turns a `brief.yaml` into a shipped asset pack.

## Contract

```python
from asset_forge.orchestrator import build_pack
from pathlib import Path

result = await build_pack(brief_path=Path("packs/001-fantasy-props/brief.yaml"))
# result.status == "complete" | "failed" | "partial"
# result.artifact_paths == list of output files
# result.failures == list of (piece_id, reason) for partial/failed
```

## Pipeline phases (per pack)

1. **Brief parsing + expansion** — load brief.yaml, LLM-expand vague
   entries ("30 fantasy props" → enumerated list)
2. **Generation** — for each piece, call `flax-asset-gen/text_to_3d`
   or `image_to_3d` via mcp_client; fall back through the route list
3. **Auto-retopology** — pass each generated mesh through retopo
   backend; reject pieces that fail topology validation
4. **UV unwrap** — uvunwrap.unwrap_piece() on each
5. **Material assignment** — pick from curated PBR library matching
   pack style; vary within style bounds
6. **Style consistency pass** — style.enforce() reviews all pieces;
   regenerates outliers
7. **LOD generation** — flax-meshopt-bridge/lod via mcp_client; LOD0..LOD3
8. **Snap-grid normalization** — snap_grid.normalize_pivots()
9. **Per-engine export** — Unity .unitypackage, Unreal .uasset zip,
   Godot .glb bundle, raw GLB master
10. **Preview rendering** — Blender headless renders per piece + hero shots
11. **Manifest generation** — manifest.build_for(target_marketplace)
12. **Showroom build** — showroom.build_site() for the pack's landing page

## State persistence

Checkpoints at every phase boundary in `out/<pack-id>/.state.json`.
Resumable: `asset-forge resume <pack-id>` picks up where the pipeline
crashed or was stopped.

## What we steal

- **LL3M's BlenderRAG corpus** — retrieval-augmented Blender API
  knowledge base for the agent that drives the orchestrator
- **AssetFormer's modular token-stream pattern** — for representing
  pack composition as a sequence
- **flax-mcp's mutation/save_checkpoint + restore_checkpoint** — for
  rollback when a phase fails partway through

## What we DON'T do

- Don't push to marketplaces automatically (operator manually
  uploads for first 6 months)
- Don't skip the style consistency pass (skipping = AI mush =
  marketplace rejection)
- Don't decide pricing (operator's call per pack)
