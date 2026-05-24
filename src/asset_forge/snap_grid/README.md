# snap_grid — pivot normalizer for modular assembly

The unsexy module that makes packs ACTUALLY USABLE.

Synty packs sell because pieces snap together. Generated pieces have
random pivots, random scales, random origins — useless for modular
assembly. This module normalizes all of that.

## Contract

```python
from asset_forge.snap_grid import normalize_pack, GridSpec

result = await normalize_pack(
    pack_root=Path("out/001-fantasy-props/"),
    spec=GridSpec(
        grid_unit_meters=1.0,        # 1m = 1 grid cell, Unity default
        snap_pivot_to="base_center", # base_center | bbox_min | mass_center
        snap_rotation_to_axes=True,
        normalize_scale=True,
        target_unit_height_meters=None,  # None = auto-fit per piece
    ),
)
# result.pieces_normalized, result.failures
```

## What "normalized" means

For every piece:
- Pivot moved to base center (object sits ON the grid, not floats)
- Rotation snapped to nearest axis (no random 7.3° rotations)
- Scale normalized (1m grid = 1 Blender unit = 1 Unity unit = 1
  Unreal unit / 100 = 1 Godot unit)
- Bounding box reported in metadata
- Optional: pieces tagged with "snap_to_corner", "snap_to_edge",
  "snap_to_face" hints for engine-side snap tools

## Grid presets

| Preset | Grid unit | Use case |
|---|---|---|
| `synty_polygon` | 1.0 m | Stylized modular kits |
| `dungeon_tile` | 4.0 m | Dungeon tile-based |
| `voxel_micro` | 0.25 m | Voxel-style detailed |
| `archviz` | 0.5 m | Architectural / interiors |
| `custom` | user-defined | Pack-specific |

## Naming conventions enforced

After normalization, every piece is renamed to a canonical pattern:
```
<pack-prefix>_<category>_<descriptor>_<variant>_LOD<N>
```
e.g. `FNTPRP_barrel_wooden_a_LOD0`. This is required by Unity Asset
Store guidelines and dramatically improves discoverability.

## What we steal

- **Synty's naming conventions** (publicly visible in their packs)
- **Unity Asset Store naming best practices** (from their submission
  guidelines)
- **Unreal Marketplace naming conventions** (Fab guidelines)
- **gltfpack's pivot+transform metadata** (already wrapped in
  flax-meshopt-bridge)

## Why this matters

This module looks boring. It's the difference between "a pack of
30 disconnected props" and "a pack of 30 props that build a village
in 5 minutes." Buyers don't articulate this in reviews; they FEEL
it. Packs with snap-grid alignment get 5-star reviews; packs
without get 3-star "looks great but hard to use" reviews.
