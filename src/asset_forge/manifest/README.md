# manifest — marketplace manifest generation

Produces submission-ready bundles for every target marketplace from
the same pack source. Operator uploads manually for the first 6
months (build trust + avoid API risk), then automation when warranted.

## Contract

```python
from asset_forge.manifest import build_manifests, Target

result = await build_manifests(
    pack_root=Path("out/001-fantasy-props/"),
    targets=[Target.FAB, Target.UNITY, Target.ITCHIO, Target.GUMROAD],
)
# result.bundles: dict[Target, Path]  # path to per-marketplace submission folder
```

## Per-target output

### Fab (Epic, 88% publisher cut — PRIMARY)
- `.unitypackage` (since Fab accepts Unity packages)
- `.uasset` Unreal plugin folder
- README.md (Fab format)
- license.txt (per-pack EULA template)
- preview images (hero + per-piece thumbnails)
- demo scene per engine
- **AI disclosure document** (required by Fab policy)

### Unity Asset Store (70% cut)
- `.unitypackage` with full directory structure
- Documentation following Unity's template
- preview images (square + landscape)
- demo scene as .unitypackage subfolder
- **AI disclosure metadata** in the asset's description field
  (Unity requires explicit AI declaration since 2024)
- Naming compliance check (Unity's strict pattern enforcement)

### Itch.io (you set the cut, 0-30%)
- Standalone .zip with all engine variants
- README.md
- license.txt
- preview images
- itch.io project description (markdown)
- itch.io tags suggestions

### Gumroad (~10% fee)
- Same .zip as Itch.io
- Gumroad product description (markdown)
- preview image gallery

## License compliance gate

Before bundling, manifest validates:
- No GPL/LGPL contamination (would force open-source)
- No CC-BY-ND assets (cannot derive)
- All upstream models/textures have commercial-use clearance
- Provenance receipts from flax-asset-worker present for every
  source asset

If any check fails, the bundle is rejected and operator is told
which piece needs sourcing fix.

## AI disclosure language

Auto-generated per pack with:
- Which AI models were used (TRELLIS, Hunyuan3D, etc.)
- What was generated vs hand-modified
- Operator review attestation
- Commercial-use rights confirmation per tool

Fab and Unity both require this. Boilerplate maintained in
`templates/ai_disclosure_*.md`.

## What we steal

- **Unity Asset Store submission guidelines** (publicly documented)
- **Fab publisher guidelines** (publicly documented)
- **Itch.io project metadata schema** (open)
- **Gumroad product API schema** (open)

## What we DON'T do (for the first 6 months)

- ❌ Auto-submit to any marketplace (operator uploads manually)
- ❌ Auto-update pricing (operator decides per pack)
- ❌ Auto-respond to reviews (relationship building is manual)

Automation comes when we have a track record of accepted packs.
