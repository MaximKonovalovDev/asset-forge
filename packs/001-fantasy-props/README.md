# Pack #1 — Low-Poly Fantasy Props Vol. 1

The calibration pack. 30 hand-curated low-poly fantasy props for
stylized RPGs and adventure games.

## Status

Day 0. Brief authored, pipeline not yet implemented.

## Pieces

30 pieces across 6 categories: containers (5), furniture (6),
vessels (4), lighting (3), weapons (4), miscellaneous (8).

See `brief.yaml` for the full piece list, prompts, and style spec.

## Demo scenes

- **Tavern Corner** — tables, chairs, lantern, bottles
- **Blacksmith Yard** — anvil, axe, sword, shield, barrel
- **Campsite** — logs, mushrooms, rocks, torch

## Pricing strategy

- Launch: **$9.99** for 14 days
- Normal: **$19.99**
- Markets: Fab (primary), Itch.io, Gumroad

Unity Asset Store deferred to Pack #2 (we ship there only after our
first marketplace acceptance elsewhere — Unity's submission review
is slower and we want a track record first).

## Reference

`reference/hero.png` will hold the style reference image. Operator
provides this; AI generation uses it as the style anchor.

## Build command (when pipeline is ready)

```bash
asset-forge build packs/001-fantasy-props/brief.yaml
```

This produces `out/001-fantasy-props/` with every piece exported
for Unity / Unreal / Godot, plus marketplace manifests and the
showroom site.
