"""uvunwrap \u2014 UV unwrap automation via flax-blender-bridge.

Public surface:
    unwrap_piece(piece_id, input_glb, output_glb, strategy, ...)
    unwrap_pack(pack_paths, brief, ...)

Strategies:
    smart_project   Blender Smart UV Project (default for hard-surface)
    seam_hint_llm   LLM picks seam edges from topology; Blender unwraps along them
    box_project     Six-sided projection (crates, simple geo)
    trim_sheet      Aligns UVs to a shared trim sheet across the pack
    manual_seams    Operator-supplied seam paint (skipped in v1)
"""

from __future__ import annotations

from .api import UvResult, UvStrategy, unwrap_pack, unwrap_piece

__all__ = [
    "UvResult",
    "UvStrategy",
    "unwrap_pack",
    "unwrap_piece",
]
