"""Public API for retopology.

RetopoResult / TopologyTarget live in backends.py to avoid a circular
import. We re-export them here as the public surface.
"""

from __future__ import annotations

from pathlib import Path

from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths
from asset_forge.common.settings import Settings, get_settings
from asset_forge.common.types import Brief
from asset_forge.mcp_client.session import McpSession

from .backends import (
    BlenderDecimateBackend,
    BlenderVoxelRemeshBackend,
    InstantMeshesBackend,
    QuadRemesherBackend,
    QuadriFlowBackend,
    RetopoBackend,
    RetopoResult,
    TopologyTarget,
)

__all__ = ["RetopoBackend", "RetopoResult", "TopologyTarget", "retopo_pack", "retopo_piece"]

_log = get_logger("retopo")


def _build_backend(
    name: str,
    session: McpSession | None,
    settings: Settings,
) -> RetopoBackend:
    """Construct a backend by name. Raises ValueError on unknown."""
    if name == "quadriflow":
        return QuadriFlowBackend()
    if name == "instant-meshes":
        return InstantMeshesBackend(binary_path=settings.instant_meshes_path or None)
    if name == "voxel-remesh":
        if session is None:
            raise ValueError("voxel-remesh backend requires an McpSession")
        return BlenderVoxelRemeshBackend(session)
    if name == "decimate":
        if session is None:
            raise ValueError("decimate backend requires an McpSession")
        return BlenderDecimateBackend(session)
    if name == "quadremesher":
        return QuadRemesherBackend()
    raise ValueError(f"unknown retopo backend: {name}")


async def retopo_piece(
    piece_id: str,
    input_glb: Path,
    output_glb: Path,
    target: TopologyTarget,
    *,
    backend_name: str | None = None,
    session: McpSession | None = None,
    settings: Settings | None = None,
) -> RetopoResult:
    """Retopologise one GLB into another.

    Returns a RetopoResult with success=True/False. NEVER raises on
    backend failure; caller falls back to a different backend if needed.
    """
    s = settings or get_settings()
    name = backend_name or s.retopo_backend
    try:
        backend = _build_backend(name, session, s)
    except ValueError as e:
        return RetopoResult(
            piece_id=piece_id,
            backend=name,
            success=False,
            error_code="unknown_backend",
            error_message=str(e),
        )

    _log.info("retopo.start", piece=piece_id, backend=name)
    return await backend.retopo(piece_id, input_glb, output_glb, target)


async def retopo_pack(
    paths: PackPaths,
    brief: Brief,
    *,
    pieces_succeeded: list[str],
    session: McpSession | None = None,
    settings: Settings | None = None,
) -> dict[str, RetopoResult]:
    """Retopologise every successfully-generated piece in a pack.

    Reads from paths.raw_dir, writes to paths.retopo_dir. Skips pieces
    that don't have a raw input (i.e. failed generation).
    """
    s = settings or get_settings()
    paths.retopo_dir.mkdir(parents=True, exist_ok=True)

    # Target topology derived from the brief's polygon band midpoint.
    lo, hi = brief.style.polygon_count_band
    target = TopologyTarget(
        target_face_count=(lo + hi) // 2,
        quads_preferred=True,
        preserve_uvs=False,
    )

    results: dict[str, RetopoResult] = {}
    for piece_id in pieces_succeeded:
        piece = brief.piece_by_id(piece_id)
        if piece is None:
            continue
        input_glb = paths.raw_dir / f"{piece_id}.glb"
        output_glb = paths.retopo_dir / f"{piece_id}.glb"
        if not input_glb.exists():
            results[piece_id] = RetopoResult(
                piece_id=piece_id,
                backend=s.retopo_backend,
                success=False,
                error_code="input_missing",
                error_message=f"raw GLB not found: {input_glb}",
            )
            continue

        result = await retopo_piece(
            piece_id=piece_id,
            input_glb=input_glb,
            output_glb=output_glb,
            target=target,
            session=session,
            settings=s,
        )
        results[piece_id] = result
        _log.info(
            "retopo.piece_done",
            piece=piece_id,
            success=result.success,
            faces=result.output_face_count,
        )

    return results
