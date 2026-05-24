"""Resumable phase checkpointing.

Every phase boundary writes `.state.json` atomically. `asset-forge
resume <pack-id>` reads it and skips already-completed phases.

The state file is JSON for forensic readability — operators should
be able to open it in a text editor when something goes wrong.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from asset_forge.common.errors import AssetForgeError
from asset_forge.common.logging import get_logger
from asset_forge.common.types import Outcome, Phase


class PhaseState(BaseModel):
    """State for one phase."""

    model_config = ConfigDict(extra="forbid")

    phase: Phase
    outcome: Outcome = Outcome.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pieces_completed: list[str] = Field(default_factory=list)
    pieces_failed: list[str] = Field(default_factory=list)
    notes: str = ""


class PackState(BaseModel):
    """Full pack state. Persisted to <pack-root>/.state.json."""

    model_config = ConfigDict(extra="forbid")

    pack_id: str
    schema_version: int = 1
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    phases: dict[Phase, PhaseState] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    def phase_state(self, phase: Phase) -> PhaseState:
        if phase not in self.phases:
            self.phases[phase] = PhaseState(phase=phase)
        return self.phases[phase]

    def is_phase_complete(self, phase: Phase) -> bool:
        return self.phases.get(phase, PhaseState(phase=phase)).outcome is Outcome.SUCCESS

    def mark_phase_started(self, phase: Phase) -> None:
        ps = self.phase_state(phase)
        ps.outcome = Outcome.PENDING
        ps.started_at = datetime.now(UTC)
        self.last_updated = datetime.now(UTC)

    def mark_phase_complete(self, phase: Phase, notes: str = "") -> None:
        ps = self.phase_state(phase)
        ps.outcome = Outcome.SUCCESS
        ps.finished_at = datetime.now(UTC)
        if notes:
            ps.notes = notes
        self.last_updated = datetime.now(UTC)

    def mark_phase_failed(self, phase: Phase, notes: str) -> None:
        ps = self.phase_state(phase)
        ps.outcome = Outcome.FAILED
        ps.finished_at = datetime.now(UTC)
        ps.notes = notes
        self.last_updated = datetime.now(UTC)

    def add_cost(self, amount_usd: float) -> None:
        self.total_cost_usd = round(self.total_cost_usd + amount_usd, 4)
        self.last_updated = datetime.now(UTC)


def load_state(state_path: Path, pack_id: str) -> PackState:
    """Load existing state, or build a fresh PackState for the pack id."""
    if not state_path.exists():
        return PackState(pack_id=pack_id)
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise AssetForgeError(f"corrupt state file {state_path}: {e}") from e

    try:
        state = PackState.model_validate(raw)
    except Exception as e:
        raise AssetForgeError(f"state file schema mismatch in {state_path}: {e}") from e

    if state.pack_id != pack_id:
        raise AssetForgeError(
            f"state file pack_id mismatch: expected {pack_id}, got {state.pack_id}"
        )
    return state


def save_state(state: PackState, state_path: Path) -> None:
    """Atomic write to state_path."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state.last_updated = datetime.now(UTC)
    payload = state.model_dump_json(indent=2)

    # Atomic-ish: write to sibling tempfile, then rename.
    fd, tmp = tempfile.mkstemp(
        prefix=".state-", suffix=".tmp", dir=str(state_path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, state_path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def append_receipt(receipts_path: Path, receipt_json: str) -> None:
    """Append one NDJSON line to receipts.ndjson. Creates the file if needed."""
    receipts_path.parent.mkdir(parents=True, exist_ok=True)
    line = receipt_json.rstrip("\n") + "\n"
    # Open in append-binary so partial writes don't corrupt prior lines.
    with receipts_path.open("ab") as f:
        f.write(line.encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())


_log = get_logger("orchestrator.state")
