"""LOD chain generation. Wraps flax-meshopt-bridge's gltfpack tools.

The output is a single GLB carrying LOD0..LOD3 as scene nodes (the
gltfpack convention every game engine consumes). We delegate to
flax-meshopt-bridge for the actual gltfpack invocation; this module
just orchestrates per-piece calls and aggregates results.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths
from asset_forge.common.types import Brief
from asset_forge.mcp_client.session import McpSession

_log = get_logger("lod")


@dataclass(frozen=True, slots=True)
class LodLevels:
    """Polygon-fraction targets per LOD level.

    LOD0 = 100% (original). LOD1..3 are fractions of LOD0 face count.
    Defaults are the conservative "Synty-grade" chain that holds visual
    quality at typical viewing distances. Operator can override per pack
    via brief.style metadata if needed (Phase 4+).
    """

    lod0: float = 1.0
    lod1: float = 0.5
    lod2: float = 0.25
    lod3: float = 0.125

    def as_list(self) -> list[float]:
        return [self.lod0, self.lod1, self.lod2, self.lod3]


@dataclass(frozen=True, slots=True)
class LodResult:
    piece_id: str
    success: bool
    output_glb: Path | None = None
    levels_produced: int = 0
    face_counts: tuple[int, ...] = ()
    size_bytes: int | None = None
    duration_seconds: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


async def lod_piece(
    piece_id: str,
    input_glb: Path,
    output_glb: Path,
    *,
    levels: LodLevels | None = None,
    session: McpSession,
) -> LodResult:
    """Generate a LOD chain for one piece. NEVER raises; returns LodResult."""
    start = time.monotonic()
    lvls = levels or LodLevels()

    if not input_glb.exists():
        return LodResult(
            piece_id=piece_id,
            success=False,
            error_code="input_missing",
            error_message=f"{input_glb} not found",
        )

    try:
        result = await session.call(
            "meshopt/lod_chain",
            {
                "inputPath": str(input_glb),
                "outputPath": str(output_glb),
                "ratios": lvls.as_list(),
                "drachoCompress": True,
                "optimizeVertexCache": True,
                "optimizeVertexFetch": True,
            },
            intent=f"asset-forge lod piece={piece_id}",
        )
    except Exception as e:
        return LodResult(
            piece_id=piece_id,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="mcp_error",
            error_message=str(e),
        )

    if not output_glb.exists():
        return LodResult(
            piece_id=piece_id,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="output_missing",
            error_message=f"meshopt returned success but {output_glb} missing",
        )

    meta: dict[str, object] = result if isinstance(result, dict) else {}
    face_counts_raw = meta.get("faceCounts")
    face_counts: tuple[int, ...] = ()
    if isinstance(face_counts_raw, (list, tuple)):
        face_counts = tuple(int(x) for x in face_counts_raw if isinstance(x, (int, float)))
    levels_raw = meta.get("levelsProduced")
    levels_produced = int(levels_raw) if isinstance(levels_raw, int) else len(face_counts)
    size_raw = meta.get("sizeBytes")
    size_bytes = int(size_raw) if isinstance(size_raw, int) else None
    if size_bytes is None:
        try:
            size_bytes = output_glb.stat().st_size
        except OSError:
            size_bytes = None

    return LodResult(
        piece_id=piece_id,
        success=True,
        output_glb=output_glb,
        levels_produced=levels_produced,
        face_counts=face_counts,
        size_bytes=size_bytes,
        duration_seconds=time.monotonic() - start,
        metadata=meta,
    )


async def lod_pack(
    paths: PackPaths,
    brief: Brief,
    *,
    pieces_succeeded: list[str],
    session: McpSession,
) -> dict[str, LodResult]:
    """Generate LOD chains for every snap-normalized piece.

    Reads from paths.final_dir (snap_grid output), writes to paths.lods_dir.
    Falls back to materials_dir or uv_dir or retopo_dir if final_dir is empty
    (i.e. some upstream phase was skipped). This makes LOD usable even when
    we're testing in isolation.
    """
    paths.lods_dir.mkdir(parents=True, exist_ok=True)

    source_dirs = (paths.final_dir, paths.materials_dir, paths.uv_dir, paths.retopo_dir)

    results: dict[str, LodResult] = {}
    for piece_id in pieces_succeeded:
        if brief.piece_by_id(piece_id) is None:
            continue
        input_glb: Path | None = None
        for src in source_dirs:
            candidate = src / f"{piece_id}.glb"
            if candidate.exists():
                input_glb = candidate
                break
        if input_glb is None:
            results[piece_id] = LodResult(
                piece_id=piece_id,
                success=False,
                error_code="input_missing",
                error_message=f"no upstream GLB for piece {piece_id}",
            )
            continue

        output_glb = paths.lods_dir / f"{piece_id}.glb"
        results[piece_id] = await lod_piece(
            piece_id=piece_id,
            input_glb=input_glb,
            output_glb=output_glb,
            session=session,
        )
        _log.info(
            "lod.piece_done",
            piece=piece_id,
            success=results[piece_id].success,
            levels=results[piece_id].levels_produced,
        )

    return results
