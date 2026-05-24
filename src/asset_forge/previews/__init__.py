"""previews \u2014 Blender headless render of pack pieces + hero shots.

Public surface:
    preview_piece(piece_id, input_glb, dest_dir, settings, session) -> PreviewResult
    preview_pack(pack_paths, brief, pieces_succeeded, session) -> dict
"""

from __future__ import annotations

from .api import (
    PreviewResult,
    PreviewSettings,
    preview_pack,
    preview_piece,
)

__all__ = [
    "PreviewResult",
    "PreviewSettings",
    "preview_pack",
    "preview_piece",
]
