"""UV unwrap public API."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths
from asset_forge.common.types import Brief
from asset_forge.mcp_client.session import McpSession

_log = get_logger("uvunwrap")


class UvStrategy(StrEnum):
    SMART_PROJECT = "smart_project"
    SEAM_HINT_LLM = "seam_hint_llm"
    BOX_PROJECT = "box_project"
    TRIM_SHEET = "trim_sheet"
    MANUAL_SEAMS = "manual_seams"


@dataclass(frozen=True, slots=True)
class UvResult:
    """Outcome of one UV unwrap invocation."""

    piece_id: str
    strategy: UvStrategy
    success: bool
    output_glb: Path | None = None
    uv_islands_count: int | None = None
    atlas_waste_pct: float | None = None
    duration_seconds: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


async def unwrap_piece(
    piece_id: str,
    input_glb: Path,
    output_glb: Path,
    *,
    strategy: UvStrategy = UvStrategy.SMART_PROJECT,
    texel_density_px_per_unit: int = 512,
    target_atlas_resolution: int = 2048,
    session: McpSession,
) -> UvResult:
    """Unwrap one piece. NEVER raises; returns UvResult."""
    start = time.monotonic()

    # MANUAL_SEAMS skipped in v1 (requires operator interaction).
    if strategy is UvStrategy.MANUAL_SEAMS:
        return UvResult(
            piece_id=piece_id,
            strategy=strategy,
            success=False,
            error_code="strategy_not_implemented",
            error_message="MANUAL_SEAMS requires operator seam paint; not implemented in v1",
        )

    # TRIM_SHEET requires a pack-level shared sheet; for v1 we fall back to
    # SMART_PROJECT and log a note. Real trim-sheet support lands in Phase 4.
    effective_strategy = strategy
    if strategy is UvStrategy.TRIM_SHEET:
        _log.warning("uvunwrap.trim_sheet_fallback", piece=piece_id)
        effective_strategy = UvStrategy.SMART_PROJECT

    # SEAM_HINT_LLM is a two-step: LLM picks seams -> Blender unwraps along them.
    # The LLM call adds complexity; for v1 we fall back to SMART_PROJECT and
    # land the LLM step in Phase 5. The strategy is honored where the bridge
    # supports it.
    if effective_strategy is UvStrategy.SEAM_HINT_LLM:
        _log.info("uvunwrap.seam_hint_llm_v1_smart_fallback", piece=piece_id)
        effective_strategy = UvStrategy.SMART_PROJECT

    try:
        result = await session.call(
            "blender_bridge/uv_unwrap",
            {
                "inputPath": str(input_glb),
                "outputPath": str(output_glb),
                "strategy": effective_strategy.value,
                "texelDensityPxPerUnit": texel_density_px_per_unit,
                "atlasResolution": target_atlas_resolution,
            },
            intent=f"asset-forge uvunwrap piece={piece_id}",
        )
    except Exception as e:
        return UvResult(
            piece_id=piece_id,
            strategy=effective_strategy,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="mcp_error",
            error_message=str(e),
        )

    if not output_glb.exists():
        return UvResult(
            piece_id=piece_id,
            strategy=effective_strategy,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="output_missing",
            error_message=f"Blender bridge returned success but {output_glb} missing",
        )

    meta: dict[str, object] = result if isinstance(result, dict) else {}
    islands_raw = meta.get("uvIslandsCount")
    islands = islands_raw if isinstance(islands_raw, int) else None
    waste_raw = meta.get("atlasWastePct")
    waste = float(waste_raw) if isinstance(waste_raw, (int, float)) else None

    return UvResult(
        piece_id=piece_id,
        strategy=effective_strategy,
        success=True,
        output_glb=output_glb,
        uv_islands_count=islands,
        atlas_waste_pct=waste,
        duration_seconds=time.monotonic() - start,
        metadata=meta,
    )


async def unwrap_pack(
    paths: PackPaths,
    brief: Brief,
    *,
    pieces_succeeded: list[str],
    session: McpSession,
) -> dict[str, UvResult]:
    """Unwrap every retopo'd piece in a pack. Reads from retopo_dir,
    writes to uv_dir."""
    paths.uv_dir.mkdir(parents=True, exist_ok=True)

    try:
        strategy = UvStrategy(brief.style.uv_strategy)
    except ValueError:
        strategy = UvStrategy.SMART_PROJECT

    results: dict[str, UvResult] = {}
    for piece_id in pieces_succeeded:
        input_glb = paths.retopo_dir / f"{piece_id}.glb"
        output_glb = paths.uv_dir / f"{piece_id}.glb"
        if not input_glb.exists():
            results[piece_id] = UvResult(
                piece_id=piece_id,
                strategy=strategy,
                success=False,
                error_code="input_missing",
                error_message=f"retopo output not found: {input_glb}",
            )
            continue

        results[piece_id] = await unwrap_piece(
            piece_id=piece_id,
            input_glb=input_glb,
            output_glb=output_glb,
            strategy=strategy,
            texel_density_px_per_unit=brief.style.texel_density_px_per_unit,
            session=session,
        )

    return results
