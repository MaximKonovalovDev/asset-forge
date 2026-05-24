"""Master GLB export. Engine-agnostic, raw GLB files + manifest.

Most engines (Three.js, Babylon.js, Blender, Houdini, Maya, Stride,
Flax) consume glTF directly. The master bundle is just the GLB files
under canonical names + a JSON manifest listing them.

Bundle layout:

    <out_dir>/
        README.md
        license.txt
        ai_disclosure.txt
        manifest.json               JSON listing of all pieces
        pieces/<canonical>.glb      per-piece GLB

    <out_dir>.zip                  drop-in ready
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from asset_forge.common.types import Brief

from ._shared import BuilderOutput, copy_file, reset_dir, write_text, zip_directory


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_master_glb_bundle(
    out_dir: Path,
    brief: Brief,
    source_glbs: dict[str, Path],
    name_map: dict[str, str],
) -> BuilderOutput:
    """Build the engine-agnostic master GLB bundle + .zip."""
    reset_dir(out_dir)
    pieces_dir = out_dir / "pieces"
    pieces_dir.mkdir(parents=True, exist_ok=True)

    # 1. Text artifacts
    from asset_forge.manifest.templates import (
        ai_disclosure_text,
        license_text,
        pack_readme,
    )

    write_text(out_dir / "README.md", pack_readme(brief))
    write_text(out_dir / "license.txt", license_text(brief))
    write_text(out_dir / "ai_disclosure.txt", ai_disclosure_text(brief))

    # 2. Copy GLBs under canonical names + collect manifest entries
    total_size = 0
    file_count = 0
    pieces_manifest: list[dict[str, object]] = []

    for piece_id, source_glb in source_glbs.items():
        canonical = name_map.get(piece_id, piece_id)
        target = pieces_dir / f"{canonical}.glb"
        size = copy_file(source_glb, target)
        total_size += size
        file_count += 1

        piece = brief.piece_by_id(piece_id)
        pieces_manifest.append(
            {
                "id": piece_id,
                "canonical_name": canonical,
                "filename": f"pieces/{canonical}.glb",
                "category": piece.category if piece else "uncategorized",
                "prompt": piece.prompt if piece else "",
                "size_bytes": size,
                "sha256": _sha256(target),
            }
        )

    # 3. JSON manifest
    manifest_payload = {
        "pack_id": brief.id,
        "title": brief.title,
        "description": brief.description.strip(),
        "piece_count": len(pieces_manifest),
        "pieces": pieces_manifest,
        "style": {
            "shading": brief.style.shading,
            "material_complexity": brief.style.material_complexity,
            "polygon_count_band": list(brief.style.polygon_count_band),
            "texel_density_px_per_unit": brief.style.texel_density_px_per_unit,
            "palette": list(brief.style.palette),
        },
        "ai_disclosure": {
            "models_used": list(brief.ai_disclosure.models_used),
            "commercial_use_verified": brief.ai_disclosure.commercial_use_verified,
        },
    }
    write_text(
        out_dir / "manifest.json",
        json.dumps(manifest_payload, indent=2, sort_keys=True),
    )
    file_count += 1
    total_size += (out_dir / "manifest.json").stat().st_size

    # 4. Zip
    archive = out_dir.parent / f"{out_dir.name}.zip"
    zfc, _zsize = zip_directory(out_dir, archive)

    return BuilderOutput(
        bundle_path=out_dir,
        archive_path=archive,
        file_count=zfc,
        size_bytes=archive.stat().st_size,
    )
