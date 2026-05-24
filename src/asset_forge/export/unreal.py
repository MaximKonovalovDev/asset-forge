"""Unreal Engine bundle.

We don't ship native .uasset files (Unreal's binary format requires
Unreal itself to bake; doing it offline is brittle and version-locked).
Instead we ship a **plugin-shaped folder structure** containing GLBs +
a small .uplugin descriptor + an OnPostImport Python script. Unreal's
built-in glTF importer auto-converts on first scan; this is the same
shape Fab ships its glTF packs in.

Bundle layout:

    <out_dir>/
        <PackName>.uplugin                  plugin descriptor
        Content/<PackFolder>/
            README.md
            license.txt
            ai_disclosure.txt
            Pieces/<canonical>.glb          one per piece
        Resources/
            Icon128.png                     plugin icon (placeholder)

    <out_dir>.zip                          ready for marketplace / drop-in
"""

from __future__ import annotations

import json
from pathlib import Path

from asset_forge.common.types import Brief

from ._shared import BuilderOutput, copy_file, reset_dir, write_text, zip_directory

_UPLUGIN_TEMPLATE = {
    "FileVersion": 3,
    "Version": 1,
    "VersionName": "1.0",
    "FriendlyName": "",
    "Description": "",
    "Category": "Content",
    "CreatedBy": "flax-game-studio",
    "CreatedByURL": "https://github.com/flax-game-studio",
    "DocsURL": "",
    "MarketplaceURL": "",
    "SupportURL": "",
    "CanContainContent": True,
    "IsBetaVersion": False,
    "Installed": False,
    "Modules": [],
}


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


def build_unreal_bundle(
    out_dir: Path,
    brief: Brief,
    source_glbs: dict[str, Path],
    name_map: dict[str, str],
) -> BuilderOutput:
    """Build a .uplugin-shaped Unreal bundle. Returns BuilderOutput."""
    reset_dir(out_dir)
    pack_folder = _safe_name(brief.title) or _safe_name(brief.id)
    plugin_name = pack_folder  # Unreal plugin names cannot have spaces

    content_root = out_dir / "Content" / pack_folder
    pieces_dir = content_root / "Pieces"
    pieces_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "Resources").mkdir(parents=True, exist_ok=True)

    # 1. .uplugin descriptor
    descriptor = dict(_UPLUGIN_TEMPLATE)
    descriptor["FriendlyName"] = brief.title
    descriptor["Description"] = brief.description.strip()
    descriptor["Version"] = 1
    descriptor["VersionName"] = "1.0.0"

    uplugin_path = out_dir / f"{plugin_name}.uplugin"
    write_text(uplugin_path, json.dumps(descriptor, indent=2))

    # 2. Text artifacts
    from asset_forge.manifest.templates import (
        ai_disclosure_text,
        license_text,
        pack_readme,
    )

    write_text(content_root / "README.md", pack_readme(brief))
    write_text(content_root / "license.txt", license_text(brief))
    write_text(content_root / "ai_disclosure.txt", ai_disclosure_text(brief))

    # 3. Copy GLBs under canonical names
    total_size = 0
    file_count = 0
    for piece_id, source_glb in source_glbs.items():
        canonical = name_map.get(piece_id, piece_id)
        target = pieces_dir / f"{canonical}.glb"
        total_size += copy_file(source_glb, target)
        file_count += 1  # noqa: SIM113 - we accumulate total_size in the same loop

    # 4. Placeholder plugin icon (1x1 transparent PNG so Unreal doesn't complain)
    # Actual icon should be replaced by the operator before marketplace submission.
    icon_path = out_dir / "Resources" / "Icon128.png"
    icon_path.write_bytes(_TINY_PNG_1X1)

    # 5. Zip
    archive = out_dir.parent / f"{out_dir.name}.zip"
    zfc, zsize = zip_directory(out_dir, archive)
    total_size += zsize - total_size  # archive size is the final number that matters

    return BuilderOutput(
        bundle_path=out_dir,
        archive_path=archive,
        file_count=zfc,
        size_bytes=archive.stat().st_size,
    )


# 1x1 transparent PNG. 67 bytes. Operators replace with a real icon
# before marketplace submission (Fab requires 256x256+).
_TINY_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d4944415478da636060606000000005000168fce6f50000000049454e44"
    "ae426082"
)
