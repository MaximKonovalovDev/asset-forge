"""Tests for the orchestrator state checkpoint."""

from __future__ import annotations

from pathlib import Path

import pytest

from asset_forge.common.errors import AssetForgeError
from asset_forge.common.types import Outcome, Phase
from asset_forge.orchestrator.state import (
    PackState,
    append_receipt,
    load_state,
    save_state,
)


def test_fresh_state_when_file_missing(tmp_path: Path) -> None:
    state = load_state(tmp_path / "nope.json", "p1")
    assert state.pack_id == "p1"
    assert state.phases == {}
    assert state.total_cost_usd == 0.0


def test_save_and_reload_roundtrip(tmp_path: Path) -> None:
    state = PackState(pack_id="p1")
    state.mark_phase_started(Phase.GENERATION)
    state.mark_phase_complete(Phase.GENERATION, notes="2/2 ok")
    state.add_cost(0.04)

    path = tmp_path / ".state.json"
    save_state(state, path)
    assert path.exists()

    reloaded = load_state(path, "p1")
    assert reloaded.pack_id == "p1"
    assert reloaded.is_phase_complete(Phase.GENERATION)
    assert reloaded.total_cost_usd == 0.04
    assert reloaded.phases[Phase.GENERATION].notes == "2/2 ok"


def test_mismatched_pack_id_raises(tmp_path: Path) -> None:
    state = PackState(pack_id="p1")
    path = tmp_path / ".state.json"
    save_state(state, path)
    with pytest.raises(AssetForgeError, match="pack_id mismatch"):
        load_state(path, "wrong-pack")


def test_corrupt_state_raises(tmp_path: Path) -> None:
    path = tmp_path / ".state.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(AssetForgeError, match="corrupt"):
        load_state(path, "p1")


def test_phase_failed_records_notes(tmp_path: Path) -> None:
    state = PackState(pack_id="p1")
    state.mark_phase_started(Phase.GENERATION)
    state.mark_phase_failed(Phase.GENERATION, notes="all routes failed")
    path = tmp_path / ".state.json"
    save_state(state, path)
    reloaded = load_state(path, "p1")
    ps = reloaded.phases[Phase.GENERATION]
    assert ps.outcome is Outcome.FAILED
    assert "all routes" in ps.notes


def test_receipt_append_creates_file(tmp_path: Path) -> None:
    receipts = tmp_path / "receipts.ndjson"
    append_receipt(receipts, '{"id": "r1", "x": 1}')
    append_receipt(receipts, '{"id": "r2", "x": 2}')
    lines = receipts.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert '"id": "r1"' in lines[0]
    assert '"id": "r2"' in lines[1]


def test_cost_accumulates(tmp_path: Path) -> None:
    state = PackState(pack_id="p1")
    state.add_cost(0.02)
    state.add_cost(0.30)
    state.add_cost(0.07)
    assert abs(state.total_cost_usd - 0.39) < 1e-9
