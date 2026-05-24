"""snap_grid \u2014 pivot/scale/naming normalization for modular assembly.

Public surface:
    normalize_piece(piece_id, input_glb, output_glb, spec, session) -> SnapResult
    normalize_pack(pack_paths, brief, session) -> dict[piece_id, SnapResult]
    canonical_piece_name(pack_id, category, piece_id, lod) -> str
"""

from __future__ import annotations

from .api import (
    SnapResult,
    canonical_piece_name,
    normalize_pack,
    normalize_piece,
)

__all__ = [
    "SnapResult",
    "canonical_piece_name",
    "normalize_pack",
    "normalize_piece",
]
