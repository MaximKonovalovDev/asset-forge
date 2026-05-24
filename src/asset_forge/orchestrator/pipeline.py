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
from asset_forge.mcp_client.backends import BackendRegistry, generate_with_fallback
from asset_forge.mcp_client.session import McpSession

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


_PHASE_HANDLERS: dict[Phase, PhaseHandler] = {
    Phase.GENERATION: _phase_generation,
    Phase.RETOPO: _stub_for("retopo"),
    Phase.UVUNWRAP: _stub_for("uvunwrap"),
    Phase.MATERIALS: _stub_for("materials"),
    Phase.STYLE_REVIEW: _stub_for("style_review"),
    Phase.LOD: _stub_for("lod"),
    Phase.SNAP_GRID: _stub_for("snap_grid"),
    Phase.EXPORT: _stub_for("export"),
    Phase.PREVIEWS: _stub_for("previews"),
    Phase.MANIFEST: _stub_for("manifest"),
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
