"""lod \u2014 LOD chain generation via flax-meshopt-bridge.

Public surface:
    lod_piece(piece_id, input_glb, output_glb, levels, session) -> LodResult
    lod_pack(pack_paths, brief, pieces_succeeded, session) -> dict
"""

from __future__ import annotations

from .api import LodLevels, LodResult, lod_pack, lod_piece

__all__ = ["LodLevels", "LodResult", "lod_pack", "lod_piece"]
