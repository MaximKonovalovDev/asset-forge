"""Godot 4 bundle.

Godot 4 imports GLBs natively via its built-in glTF importer. On first
project scan Godot generates .import sidecar files. We ship a project-
shaped folder that drops into an existing Godot project's `addons/` or
`assets/` directory.

Bundle layout:

    <out_dir>/
        addons/<pack_safe_name>/
            plugin.cfg                  Godot plugin descriptor
            README.md
            license.txt
            ai_disclosure.txt
            pieces/<canonical>.glb      per-piece GLB

    <out_dir>.zip                      drop-in ready
"""

from __future__ import annotations

from pathlib import Path

from asset_forge.common.types import Brief

from ._shared import BuilderOutput, copy_file, reset_dir, write_text, zip_directory

_PLUGIN_CFG_TEMPLATE = """[plugin]

name="{name}"
description="{description}"
author="flax-game-studio"
version="1.0.0"
script="plugin.gd"
"""

_PLUGIN_GD = """@tool
extends EditorPlugin

func _enter_tree() -> void:
\tpass

func _exit_tree() -> void:
\tpass
"""


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name).lower()


def build_godot_bundle(
    out_dir: Path,
    brief: Brief,
    source_glbs: dict[str, Path],
    name_map: dict[str, str],
) -> BuilderOutput:
    """Build a Godot 4 addon bundle + .zip."""
    reset_dir(out_dir)
    addon_name = _safe_name(brief.title) or _safe_name(brief.id)
    addon_root = out_dir / "addons" / addon_name
    pieces_dir = addon_root / "pieces"
    pieces_dir.mkdir(parents=True, exist_ok=True)

    # 1. Plugin descriptor + stub script
    write_text(
        addon_root / "plugin.cfg",
        _PLUGIN_CFG_TEMPLATE.format(
            name=brief.title,
            description=brief.description.strip().replace('"', "'"),
        ),
    )
    write_text(addon_root / "plugin.gd", _PLUGIN_GD)

    # 2. Text artifacts
    from asset_forge.manifest.templates import (
        ai_disclosure_text,
        license_text,
        pack_readme,
    )

    write_text(addon_root / "README.md", pack_readme(brief))
    write_text(addon_root / "license.txt", license_text(brief))
    write_text(addon_root / "ai_disclosure.txt", ai_disclosure_text(brief))

    # 3. Copy GLBs
    total_size = 0
    file_count = 0
    for piece_id, source_glb in source_glbs.items():
        canonical = name_map.get(piece_id, piece_id)
        target = pieces_dir / f"{canonical}.glb"
        total_size += copy_file(source_glb, target)
        file_count += 1  # noqa: SIM113 - we accumulate total_size in the same loop

    # 4. Zip
    archive = out_dir.parent / f"{out_dir.name}.zip"
    zfc, _zsize = zip_directory(out_dir, archive)

    return BuilderOutput(
        bundle_path=out_dir,
        archive_path=archive,
        file_count=zfc,
        size_bytes=archive.stat().st_size,
    )
