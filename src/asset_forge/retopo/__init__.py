"""retopo \u2014 auto-retopology with backend selection.

Public surface:
    retopo_piece(input_glb, target, backend) -> RetopoResult
    retopo_pack(pack_paths, brief, settings) -> dict[piece_id, RetopoResult]

Backends (selected per settings.retopo_backend):
    quadriflow      BSD; CLI subprocess; preferred default
    instant-meshes  GPL; CLI subprocess; broader shape support
    voxel-remesh    Blender built-in; via flax-blender-bridge MCP
    decimate        Blender built-in; via flax-blender-bridge MCP
    quadremesher    Commercial $109; Blender plugin; skipped by default
"""

from __future__ import annotations

from .api import RetopoResult, TopologyTarget, retopo_pack, retopo_piece
from .backends import RetopoBackend

__all__ = [
    "RetopoBackend",
    "RetopoResult",
    "TopologyTarget",
    "retopo_pack",
    "retopo_piece",
]
