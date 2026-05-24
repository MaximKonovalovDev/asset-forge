# style — style-consistency enforcer

The single most important quality module. The difference between
"AI mush" (rejected by marketplaces) and "Synty-grade pack" (sells)
is style consistency. This module enforces it.

## Contract

```python
from asset_forge.style import enforce_pack_style, StyleSpec

result = await enforce_pack_style(
    pack_root=Path("out/001-fantasy-props/"),
    spec=StyleSpec(
        reference_image=Path("packs/001-fantasy-props/reference/hero.png"),
        style_seed=42,
        palette=["#a04040", "#80c0ff", "#f0e090"],
        polygon_count_band=(800, 2500),
        material_complexity="low_poly_flat",
    ),
)
# result.outlier_pieces: list[str]  # pieces that need regen
# result.style_score: float         # CLIP similarity to reference, 0-1
```

## How it works

1. **Generation-time consistency** — every piece's text-to-3D call
   prepends the pack's "style prefix" (e.g. "low-poly fantasy,
   faceted shading, vibrant palette, consistent Synty style"). All
   pieces use the same seed for the generation model.

2. **Post-generation review** — after retopology + UV + materials,
   each piece is rendered from 4 angles. CLIP embedding compared to
   the reference image. Pieces below threshold flagged as outliers.

3. **Outlier regeneration** — flagged pieces re-generated with
   stronger prompt guidance + ControlNet conditioning on a similar
   piece that passed.

4. **Palette enforcement** — material assignment restricted to the
   pack's palette. Procedural materials parametrized to fall within
   palette HSL bounds.

5. **Polygon count band** — pieces outside the band auto-retopo
   harder or auto-subdiv to match.

## What we steal

- **CLIP embeddings via OpenCLIP** (MIT) — for similarity scoring
- **ControlNet patterns for asset consistency** (research papers
  2025-2026)
- **Synty's style guide** as a reference (not the assets, the
  style philosophy)
- **AniGen's S^3 fields pattern** for consistency across
  geometry+rigging (when we do characters)

## Why this is the moat

Every AI-3D pipeline can generate meshes. Almost nobody enforces
style across a pack of 30-100 pieces. This is the #1 reason packs
get rejected from Unity Asset Store and Fab. Doing this well = the
moat.
