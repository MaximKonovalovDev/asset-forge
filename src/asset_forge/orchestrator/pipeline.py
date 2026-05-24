"""Pipeline runner. Iterates phases; checkpoints between each.

Day-0 status: phases beyond GENERATION are stubs that mark themselves
SUCCESS so the state machine flows end-to-end. Real implementations
land per docs/PLAN.md phases.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from asset_forge.common.errors import PhaseFailed
from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths, pack_paths_for
from asset_forge.common.settings import get_settings
from asset_forge.common.types import (
    Brief,
    GenResult,
    Outcome,
    Phase,
    Receipt,
)
from asset_forge.lod import lod_pack
from asset_forge.manifest import Target, build_manifests
from asset_forge.mcp_client.backends import BackendRegistry, generate_with_fallback
from asset_forge.mcp_client.session import McpSession
from asset_forge.previews import preview_pack
from asset_forge.retopo import retopo_pack
from asset_forge.snap_grid import normalize_pack
from asset_forge.uvunwrap import unwrap_pack

from .brief import load_brief
from .state import PackState, append_receipt, load_state, save_state

_log = get_logger("orchestrator")


@dataclass(slots=True)
class PipelineResult:
    """End-of-run summary."""

    pack_id: str
    status: str  # "complete" | "failed" | "partial"
    state: PackState
    phases_run: list[Phase] = field(default_factory=list)
    phases_skipped: list[Phase] = field(default_factory=list)
    pieces_succeeded: list[str] = field(default_factory=list)
    pieces_failed: list[str] = field(default_factory=list)
    total_cost_usd: float = 0.0


_PHASE_ORDER: tuple[Phase, ...] = (
    Phase.BRIEF_PARSED,
    Phase.GENERATION,
    Phase.RETOPO,
    Phase.UVUNWRAP,
    Phase.MATERIALS,
    Phase.STYLE_REVIEW,
    Phase.LOD,
    Phase.SNAP_GRID,
    Phase.EXPORT,
    Phase.PREVIEWS,
    Phase.MANIFEST,
    Phase.SHOWROOM,
    Phase.COMPLETE,
)


async def build_pack(
    brief_path: Path,
    *,
    resume: bool = False,
    stop_after_phase: Phase | None = None,
) -> PipelineResult:
    """Run the full pipeline for a pack.

    Args:
        brief_path: path to a pack brief.yaml
        resume: if True, skip phases already marked SUCCESS
        stop_after_phase: optional stopping point (useful for dev / testing)

    Returns a PipelineResult. Does not raise on per-piece failure; phase-
    level failures raise PhaseFailed.
    """
    brief = load_brief(brief_path)
    paths = pack_paths_for(brief.id)
    paths.ensure()

    state = load_state(paths.state_file, brief.id) if resume else PackState(pack_id=brief.id)
    save_state(state, paths.state_file)

    result = PipelineResult(pack_id=brief.id, status="partial", state=state)

    # Brief parsed phase is implicit
    state.mark_phase_started(Phase.BRIEF_PARSED)
    state.mark_phase_complete(Phase.BRIEF_PARSED, notes=f"{len(brief.pieces)} pieces")
    save_state(state, paths.state_file)
    result.phases_run.append(Phase.BRIEF_PARSED)

    async with McpSession.connect() as mcp:
        registry = BackendRegistry(mcp)

        for phase in _PHASE_ORDER[1:]:
            if phase is Phase.COMPLETE:
                continue

            if state.is_phase_complete(phase):
                _log.info("phase.skip_resumed", phase=phase.value, pack=brief.id)
                result.phases_skipped.append(phase)
                continue

            _log.info("phase.start", phase=phase.value, pack=brief.id)
            state.mark_phase_started(phase)
            save_state(state, paths.state_file)

            try:
                handler = _PHASE_HANDLERS[phase]
                phase_outcome = await handler(brief, paths, registry, state)
            except Exception as e:
                state.mark_phase_failed(phase, notes=f"{type(e).__name__}: {e}")
                save_state(state, paths.state_file)
                result.status = "failed"
                _log.error("phase.failed", phase=phase.value, error=str(e))
                raise PhaseFailed(phase.value, str(e)) from e

            state.mark_phase_complete(phase, notes=phase_outcome)
            save_state(state, paths.state_file)
            result.phases_run.append(phase)
            _log.info("phase.complete", phase=phase.value, notes=phase_outcome)

            if stop_after_phase is not None and phase is stop_after_phase:
                _log.info("phase.stop_requested", at=phase.value)
                break

    # Aggregate piece-level success from the GENERATION phase state
    gen_state = state.phases.get(Phase.GENERATION)
    if gen_state:
        result.pieces_succeeded = list(gen_state.pieces_completed)
        result.pieces_failed = list(gen_state.pieces_failed)

    result.total_cost_usd = state.total_cost_usd
    if state.is_phase_complete(Phase.SHOWROOM):
        state.mark_phase_complete(Phase.COMPLETE)
        save_state(state, paths.state_file)
        result.status = "complete"
    return result


# ---------------------------------------------------------------------------
# Phase handlers. Day-0: GENERATION is real, others are stubs.
# ---------------------------------------------------------------------------


async def _phase_generation(
    brief: Brief,
    paths: PackPaths,
    registry: BackendRegistry,
    state: PackState,
) -> str:
    """Run text-to-3D for every piece with route fallback."""
    s = get_settings()
    route_list = s.gen_routes_list

    succeeded: list[str] = []
    failed: list[str] = []

    for piece in brief.pieces:
        # Hero pieces try hero_routes first; everyone else uses primary→fallback.
        if brief.is_hero(piece.id) and brief.generation.hero_routes:
            ordered = (
                list(brief.generation.hero_routes)
                + list(brief.generation.primary_routes)
                + list(brief.generation.fallback_routes)
            )
        else:
            ordered = (
                list(brief.generation.primary_routes)
                + list(brief.generation.fallback_routes)
            )

        # Intersect with the user's global route preference (env)
        ordered = [r for r in ordered if r in route_list] or ordered

        try:
            result: GenResult = await generate_with_fallback(
                registry, piece, brief, paths.raw_dir, ordered,
                max_retries_per_route=brief.generation.max_retries_per_piece,
            )
        except Exception as e:
            _log.error("generation.piece_exception", piece=piece.id, error=str(e))
            failed.append(piece.id)
            _write_receipt(
                paths.receipts_file,
                pack_id=brief.id,
                phase=Phase.GENERATION,
                piece_id=piece.id,
                tool="asset_gen/text_to_3d",
                intent=f"generate piece {piece.id}",
                outcome=Outcome.FAILED,
                error_code="exception",
                error_message=str(e),
            )
            continue

        if result.success:
            succeeded.append(piece.id)
            state.add_cost(result.cost_usd)
            _write_receipt(
                paths.receipts_file,
                pack_id=brief.id,
                phase=Phase.GENERATION,
                piece_id=piece.id,
                tool=f"backend:{result.route}",
                intent=f"generate piece {piece.id}",
                outcome=Outcome.SUCCESS,
                cost_usd=result.cost_usd,
                metadata={"route": result.route, "duration_s": result.duration_seconds},
            )
        else:
            failed.append(piece.id)
            _write_receipt(
                paths.receipts_file,
                pack_id=brief.id,
                phase=Phase.GENERATION,
                piece_id=piece.id,
                tool=f"backend:{result.route}",
                intent=f"generate piece {piece.id}",
                outcome=Outcome.FAILED,
                error_code=result.error_code,
                error_message=result.error_message,
            )

    gen_state = state.phase_state(Phase.GENERATION)
    gen_state.pieces_completed = succeeded
    gen_state.pieces_failed = failed

    if not succeeded:
        raise PhaseFailed(
            Phase.GENERATION.value,
            f"all {len(brief.pieces)} pieces failed to generate",
        )
    return f"{len(succeeded)}/{len(brief.pieces)} pieces generated"


# Type alias for a phase handler.
PhaseHandler = Callable[
    [Brief, PackPaths, BackendRegistry, PackState], Awaitable[str]
]


def _stub_for(name: str) -> PhaseHandler:
    """Build a no-op handler for a phase that isn't implemented yet."""

    async def handler(
        brief: Brief,
        paths: PackPaths,
        registry: BackendRegistry,
        state: PackState,
    ) -> str:
        del paths, registry, state
        _log.info("phase.stub", phase=name, pack=brief.id)
        return f"stub ({name}); real handler lands per PLAN.md"

    return handler


async def _phase_retopo(
    brief: Brief,
    paths: PackPaths,
    registry: BackendRegistry,
    state: PackState,
) -> str:
    """Run retopology over every successfully-generated piece."""
    gen_state = state.phases.get(Phase.GENERATION)
    succeeded = list(gen_state.pieces_completed) if gen_state else []
    if not succeeded:
        return "skipped (no generation outputs)"

    results = await retopo_pack(
        paths,
        brief,
        pieces_succeeded=succeeded,
        session=registry.session,
    )
    ok = [pid for pid, r in results.items() if r.success]
    bad = [pid for pid, r in results.items() if not r.success]
    rs = state.phase_state(Phase.RETOPO)
    rs.pieces_completed = ok
    rs.pieces_failed = bad

    for pid, r in results.items():
        _write_receipt(
            paths.receipts_file,
            pack_id=brief.id,
            phase=Phase.RETOPO,
            piece_id=pid,
            tool=f"retopo:{r.backend}",
            intent=f"retopo piece {pid}",
            outcome=Outcome.SUCCESS if r.success else Outcome.FAILED,
            error_code=r.error_code,
            error_message=r.error_message,
            metadata={
                "duration_s": r.duration_seconds,
                "out_faces": r.output_face_count,
            },
        )

    if not ok:
        raise PhaseFailed(Phase.RETOPO.value, f"all {len(results)} pieces failed retopo")
    return f"{len(ok)}/{len(results)} retopo'd"


async def _phase_uvunwrap(
    brief: Brief,
    paths: PackPaths,
    registry: BackendRegistry,
    state: PackState,
) -> str:
    """Unwrap UVs on every retopo'd piece."""
    retopo_state = state.phases.get(Phase.RETOPO)
    succeeded = list(retopo_state.pieces_completed) if retopo_state else []
    if not succeeded:
        return "skipped (no retopo outputs)"

    results = await unwrap_pack(
        paths,
        brief,
        pieces_succeeded=succeeded,
        session=registry.session,
    )
    ok = [pid for pid, r in results.items() if r.success]
    bad = [pid for pid, r in results.items() if not r.success]
    ps = state.phase_state(Phase.UVUNWRAP)
    ps.pieces_completed = ok
    ps.pieces_failed = bad

    for pid, r in results.items():
        _write_receipt(
            paths.receipts_file,
            pack_id=brief.id,
            phase=Phase.UVUNWRAP,
            piece_id=pid,
            tool=f"uv:{r.strategy.value}",
            intent=f"uvunwrap piece {pid}",
            outcome=Outcome.SUCCESS if r.success else Outcome.FAILED,
            error_code=r.error_code,
            error_message=r.error_message,
            metadata={
                "duration_s": r.duration_seconds,
                "islands": r.uv_islands_count,
                "atlas_waste_pct": r.atlas_waste_pct,
            },
        )

    if not ok:
        raise PhaseFailed(Phase.UVUNWRAP.value, f"all {len(results)} pieces failed uvunwrap")
    return f"{len(ok)}/{len(results)} unwrapped"


async def _phase_snap_grid(
    brief: Brief,
    paths: PackPaths,
    registry: BackendRegistry,
    state: PackState,
) -> str:
    """Pivot/scale/naming normalization. Reads from uv_dir (or materials_dir
    if materials has run), writes to final_dir."""
    upstream_state = (
        state.phases.get(Phase.UVUNWRAP) or state.phases.get(Phase.RETOPO)
    )
    succeeded = list(upstream_state.pieces_completed) if upstream_state else []
    if not succeeded:
        return "skipped (no upstream outputs)"

    results = await normalize_pack(
        paths,
        brief,
        pieces_succeeded=succeeded,
        session=registry.session,
    )
    ok = [pid for pid, r in results.items() if r.success]
    bad = [pid for pid, r in results.items() if not r.success]
    ps = state.phase_state(Phase.SNAP_GRID)
    ps.pieces_completed = ok
    ps.pieces_failed = bad

    for pid, r in results.items():
        _write_receipt(
            paths.receipts_file,
            pack_id=brief.id,
            phase=Phase.SNAP_GRID,
            piece_id=pid,
            tool="snap_grid",
            intent=f"normalize piece {pid}",
            outcome=Outcome.SUCCESS if r.success else Outcome.FAILED,
            error_code=r.error_code,
            error_message=r.error_message,
            metadata={
                "canonical_name": r.canonical_name,
                "duration_s": r.duration_seconds,
            },
        )

    if not ok:
        raise PhaseFailed(Phase.SNAP_GRID.value, f"all {len(results)} pieces failed snap_grid")
    return f"{len(ok)}/{len(results)} normalized"


async def _phase_manifest(
    brief: Brief,
    paths: PackPaths,
    registry: BackendRegistry,
    state: PackState,
) -> str:
    """Generate per-marketplace submission bundles."""
    del registry, state  # manifest is pure-IO; doesn't need session or registry

    requested = tuple(
        Target(m) for m in brief.marketplaces if m in {t.value for t in Target}
    )
    if not requested:
        return "skipped (no supported marketplaces in brief)"

    result = await build_manifests(paths, brief, targets=requested)

    for bundle in result.bundles:
        _write_receipt(
            paths.receipts_file,
            pack_id=brief.id,
            phase=Phase.MANIFEST,
            tool=f"manifest:{bundle.target.value}",
            intent=f"build manifest bundle for {bundle.target.value}",
            outcome=Outcome.SUCCESS,
            metadata={
                "bundle_path": str(bundle.bundle_path),
                "files": bundle.files_included,
                "size_bytes": bundle.size_bytes,
            },
        )

    for target, msg in result.failures:
        _write_receipt(
            paths.receipts_file,
            pack_id=brief.id,
            phase=Phase.MANIFEST,
            tool=f"manifest:{target.value}",
            intent=f"build manifest bundle for {target.value}",
            outcome=Outcome.FAILED,
            error_code="manifest_failed",
            error_message=msg,
        )

    if not result.bundles:
        raise PhaseFailed(
            Phase.MANIFEST.value,
            f"all {len(requested)} marketplace manifests failed",
        )
    return f"{len(result.bundles)}/{len(requested)} bundles built"


async def _phase_lod(
    brief: Brief,
    paths: PackPaths,
    registry: BackendRegistry,
    state: PackState,
) -> str:
    """Generate LOD chains via flax-meshopt-bridge."""
    upstream = (
        state.phases.get(Phase.SNAP_GRID)
        or state.phases.get(Phase.UVUNWRAP)
        or state.phases.get(Phase.RETOPO)
    )
    succeeded = list(upstream.pieces_completed) if upstream else []
    if not succeeded:
        return "skipped (no upstream outputs)"

    results = await lod_pack(
        paths,
        brief,
        pieces_succeeded=succeeded,
        session=registry.session,
    )
    ok = [pid for pid, r in results.items() if r.success]
    bad = [pid for pid, r in results.items() if not r.success]
    ps = state.phase_state(Phase.LOD)
    ps.pieces_completed = ok
    ps.pieces_failed = bad

    for pid, r in results.items():
        _write_receipt(
            paths.receipts_file,
            pack_id=brief.id,
            phase=Phase.LOD,
            piece_id=pid,
            tool="meshopt/lod_chain",
            intent=f"lod chain piece {pid}",
            outcome=Outcome.SUCCESS if r.success else Outcome.FAILED,
            error_code=r.error_code,
            error_message=r.error_message,
            metadata={
                "duration_s": r.duration_seconds,
                "levels": r.levels_produced,
                "face_counts": list(r.face_counts),
                "size_bytes": r.size_bytes,
            },
        )

    if not ok:
        raise PhaseFailed(Phase.LOD.value, f"all {len(results)} pieces failed LOD")
    return f"{len(ok)}/{len(results)} LOD chains built"


async def _phase_previews(
    brief: Brief,
    paths: PackPaths,
    registry: BackendRegistry,
    state: PackState,
) -> str:
    """Render thumbnails + hero shots + pack cover."""
    upstream = (
        state.phases.get(Phase.LOD)
        or state.phases.get(Phase.SNAP_GRID)
        or state.phases.get(Phase.UVUNWRAP)
        or state.phases.get(Phase.RETOPO)
    )
    succeeded = list(upstream.pieces_completed) if upstream else []
    if not succeeded:
        return "skipped (no upstream outputs)"

    results = await preview_pack(
        paths,
        brief,
        pieces_succeeded=succeeded,
        session=registry.session,
    )
    ok = [pid for pid, r in results.items() if r.success and pid != "__cover__"]
    bad = [pid for pid, r in results.items() if not r.success and pid != "__cover__"]
    ps = state.phase_state(Phase.PREVIEWS)
    ps.pieces_completed = ok
    ps.pieces_failed = bad

    for pid, r in results.items():
        if pid == "__cover__":
            _write_receipt(
                paths.receipts_file,
                pack_id=brief.id,
                phase=Phase.PREVIEWS,
                tool="blender_bridge/render_cover",
                intent="render pack cover",
                outcome=Outcome.SUCCESS if r.success else Outcome.FAILED,
                error_code=r.error_code,
                error_message=r.error_message,
                metadata={
                    "duration_s": r.duration_seconds,
                    "cover_path": str(r.hero_image) if r.hero_image else None,
                },
            )
            continue

        _write_receipt(
            paths.receipts_file,
            pack_id=brief.id,
            phase=Phase.PREVIEWS,
            piece_id=pid,
            tool="blender_bridge/render_piece",
            intent=f"render previews for {pid}",
            outcome=Outcome.SUCCESS if r.success else Outcome.FAILED,
            error_code=r.error_code,
            error_message=r.error_message,
            metadata={
                "duration_s": r.duration_seconds,
                "hero": str(r.hero_image) if r.hero_image else None,
                "thumb_count": len(r.thumbnail_images),
            },
        )

    if not ok:
        raise PhaseFailed(Phase.PREVIEWS.value, f"all {len(results) - 1} preview pieces failed")
    cover_result = results.get("__cover__")
    cover_note = " + cover" if cover_result is not None and cover_result.success else ""
    return f"{len(ok)}/{len(results) - 1} previews rendered{cover_note}"


_PHASE_HANDLERS: dict[Phase, PhaseHandler] = {
    Phase.GENERATION: _phase_generation,
    Phase.RETOPO: _phase_retopo,
    Phase.UVUNWRAP: _phase_uvunwrap,
    Phase.MATERIALS: _stub_for("materials"),
    Phase.STYLE_REVIEW: _stub_for("style_review"),
    Phase.LOD: _phase_lod,
    Phase.SNAP_GRID: _phase_snap_grid,
    Phase.EXPORT: _stub_for("export"),
    Phase.PREVIEWS: _phase_previews,
    Phase.MANIFEST: _phase_manifest,
    Phase.SHOWROOM: _stub_for("showroom"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_receipt(
    receipts_path: Path,
    *,
    pack_id: str,
    phase: Phase,
    tool: str,
    intent: str,
    outcome: Outcome,
    piece_id: str | None = None,
    cost_usd: float = 0.0,
    error_code: str | None = None,
    error_message: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    receipt = Receipt(
        id=f"rcpt_{phase.value}_{piece_id or 'pack'}_{int(time.time() * 1000)}",
        pack_id=pack_id,
        phase=phase,
        piece_id=piece_id,
        tool=tool,
        intent=intent,
        outcome=outcome,
        cost_usd=cost_usd,
        error_code=error_code,
        metadata={**(metadata or {}), **({"error_message": error_message} if error_message else {})},
    )
    append_receipt(receipts_path, receipt.model_dump_json())
