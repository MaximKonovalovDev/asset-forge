# uvunwrap — UV unwrap automation

Auto-UV is the second-biggest gap in commercial AI-3D tools after
retopology. This module produces artist-quality UVs without manual
seam marking.

## Contract

```python
from asset_forge.uvunwrap import unwrap_piece, UvStrategy

result = await unwrap_piece(
    input_glb=Path("out/retopo/barrel.glb"),
    strategy=UvStrategy.SMART_PROJECT,
    texel_density_px_per_unit=512,
    target_atlas_resolution=2048,
)
# result.output_glb (with UVs), result.uv_islands_count,
# result.atlas_waste_pct
```

## Strategies

| Strategy | Method | Best for |
|---|---|---|
| `SMART_PROJECT` | Blender Smart UV Project | Hard-surface props (default) |
| `SEAM_HINT_LLM` | LLM picks seam edges from topology hints | Organic / complex shapes |
| `BOX_PROJECT` | Six-sided box projection | Box-like crates, simple geo |
| `TRIM_SHEET` | Aligned to a shared trim sheet | Modular kits sharing material |
| `MANUAL_SEAMS` | Operator-supplied seam paint | Hero assets where AI fails |

The LLM seam-hint strategy is novel: we feed the piece's topology
(edge graph + curvature analysis) to a Claude/GPT call, ask it to
identify ideal seam paths, then Blender unwraps along those seams.
Far better than Smart Project on humanoids and creatures.

## Texel density

Pack-level setting from `brief.yaml`:
```yaml
texel_density_px_per_unit: 512   # Synty-style
# or
texel_density_px_per_unit: 1024  # mid-density
# or
texel_density_px_per_unit: 2048  # photoreal
```

Every piece in the pack is unwrapped to that density. Consistent
texel density across a pack is the #1 difference between "looks
amateur" and "looks Synty-grade."

## What we steal

- **Blender's Smart UV Project** (via flax-blender-bridge)
- **Trim-sheet workflow patterns** from TrimSheetFast / 80.lv
  tutorials
- **MutaMesh's seam-from-curvature heuristic**

## Why this is hard

Auto-UV looks easy in tutorials and falls apart on:
- Closed organic shapes (where do seams go?)
- Stretchy UVs around joints
- Wasted atlas space on irregular shapes

The LLM seam-hint pass is the key differentiator. Nobody else
ships this.
