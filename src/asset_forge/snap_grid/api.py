"""snap_grid public API."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths
from asset_forge.common.types import Brief, GridSpec
from asset_forge.mcp_client.session import McpSession

_log = get_logger("snap_grid")

# Pack-id -> uppercase prefix for canonical naming.
# "001-fantasy-props" -> "FNTPRP"
_VOWELS = frozenset("aeiou")


@dataclass(frozen=True, slots=True)
class SnapResult:
    piece_id: str
    success: bool
    output_glb: Path | None = None
    canonical_name: str | None = None
    duration_seconds: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def _pack_prefix(pack_id: str) -> str:
    """Build a 5-7 char uppercase pack prefix from the id.

    Strips digits + dashes, takes consonants from each word, truncates.
    "001-fantasy-props" -> "FNTPRP"
    "002-scifi-crates"  -> "SCFCRT"
    """
    # Drop leading numeric id segment if present
    words = re.sub(r"^\d+-", "", pack_id).split("-")
    chunks: list[str] = []
    for word in words:
        consonants = [c for c in word.lower() if c.isalpha() and c not in _VOWELS]
        if not consonants:
            consonants = list(word.lower())
        chunks.append("".join(consonants[:3]).upper())
    prefix = "".join(chunks)[:7] or "PACK"
    return prefix


def canonical_piece_name(
    pack_id: str, category: str, piece_id: str, lod: int = 0
) -> str:
    """Build the canonical asset name a marketplace expects.

    Pattern: <PACK_PREFIX>_<category>_<piece_id>_LOD<N>
    e.g. FNTPRP_container_barrel_wooden_LOD0
    """
    prefix = _pack_prefix(pack_id)
    safe_category = re.sub(r"[^a-zA-Z0-9_]", "_", category.lower())
    safe_piece = re.sub(r"[^a-zA-Z0-9_]", "_", piece_id.lower())
    return f"{prefix}_{safe_category}_{safe_piece}_LOD{lod}"


async def normalize_piece(
    piece_id: str,
    input_glb: Path,
    output_glb: Path,
    *,
    canonical_name: str,
    spec: GridSpec,
    session: McpSession,
) -> SnapResult:
    """Normalize one piece: pivot, scale, rotation, naming.

    Delegates to flax-blender-bridge which runs a Blender script that:
      1. Move pivot per spec.snap_pivot_to (base_center | bbox_min | mass_center)
      2. Snap rotation to axes if spec.snap_rotation_to_axes
      3. Normalize scale to spec.grid_unit_meters if spec.normalize_scale
      4. Rename the root node to canonical_name
      5. Export back to output_glb

    NEVER raises; returns SnapResult.
    """
    start = time.monotonic()

    try:
        await session.call(
            "blender_bridge/snap_normalize",
            {
                "inputPath": str(input_glb),
                "outputPath": str(output_glb),
                "canonicalName": canonical_name,
                "snapPivotTo": spec.snap_pivot_to,
                "snapRotationToAxes": spec.snap_rotation_to_axes,
                "normalizeScale": spec.normalize_scale,
                "gridUnitMeters": spec.grid_unit_meters,
                "targetUnitHeightMeters": spec.target_unit_height_meters,
            },
            intent=f"asset-forge snap_grid piece={piece_id}",
        )
    except Exception as e:
        return SnapResult(
            piece_id=piece_id,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="mcp_error",
            error_message=str(e),
        )

    if not output_glb.exists():
        return SnapResult(
            piece_id=piece_id,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="output_missing",
            error_message=f"Blender bridge returned success but {output_glb} missing",
        )

    return SnapResult(
        piece_id=piece_id,
        success=True,
        output_glb=output_glb,
        canonical_name=canonical_name,
        duration_seconds=time.monotonic() - start,
    )


async def normalize_pack(
    paths: PackPaths,
    brief: Brief,
    *,
    pieces_succeeded: list[str],
    session: McpSession,
) -> dict[str, SnapResult]:
    """Normalize every piece. Reads from uv_dir (or materials_dir if
    materials phase has run), writes to final_dir."""
    paths.final_dir.mkdir(parents=True, exist_ok=True)

    # Prefer materials_dir output if it exists (materials phase ran);
    # else fall back to uv_dir (materials hasn't been wired yet).
    results: dict[str, SnapResult] = {}
    for piece_id in pieces_succeeded:
        piece = brief.piece_by_id(piece_id)
        if piece is None:
            continue

        source_candidates = [
            paths.materials_dir / f"{piece_id}.glb",
            paths.uv_dir / f"{piece_id}.glb",
            paths.retopo_dir / f"{piece_id}.glb",
        ]
        input_glb = next((p for p in source_candidates if p.exists()), None)
        if input_glb is None:
            results[piece_id] = SnapResult(
                piece_id=piece_id,
                success=False,
                error_code="input_missing",
                error_message=f"no upstream GLB for piece {piece_id}",
            )
            continue

        output_glb = paths.final_dir / f"{piece_id}.glb"
        canonical = canonical_piece_name(
            pack_id=brief.id,
            category=piece.category,
            piece_id=piece_id,
            lod=0,
        )

        results[piece_id] = await normalize_piece(
            piece_id=piece_id,
            input_glb=input_glb,
            output_glb=output_glb,
            canonical_name=canonical,
            spec=brief.grid,
            session=session,
        )

    return results
