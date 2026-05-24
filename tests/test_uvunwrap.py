"""Tests for uvunwrap module. MCP calls mocked."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from asset_forge.uvunwrap import UvStrategy, unwrap_piece


@pytest.mark.asyncio
async def test_unwrap_piece_smart_project_happy(tmp_path: Path) -> None:
    output = tmp_path / "out.glb"
    output.write_bytes(b"fake glb")

    session = AsyncMock()
    session.call = AsyncMock(
        return_value={"uvIslandsCount": 12, "atlasWastePct": 8.3}
    )

    result = await unwrap_piece(
        piece_id="barrel",
        input_glb=tmp_path / "in.glb",
        output_glb=output,
        strategy=UvStrategy.SMART_PROJECT,
        session=session,
    )
    assert result.success
    assert result.strategy is UvStrategy.SMART_PROJECT
    assert result.uv_islands_count == 12
    assert result.atlas_waste_pct == pytest.approx(8.3)


@pytest.mark.asyncio
async def test_unwrap_piece_manual_seams_not_implemented(tmp_path: Path) -> None:
    session = AsyncMock()
    result = await unwrap_piece(
        piece_id="x",
        input_glb=tmp_path / "in.glb",
        output_glb=tmp_path / "out.glb",
        strategy=UvStrategy.MANUAL_SEAMS,
        session=session,
    )
    assert not result.success
    assert result.error_code == "strategy_not_implemented"
    # Session.call should NOT have been invoked
    session.call.assert_not_called()


@pytest.mark.asyncio
async def test_unwrap_piece_trim_sheet_falls_back_to_smart(tmp_path: Path) -> None:
    output = tmp_path / "out.glb"
    output.write_bytes(b"fake glb")

    session = AsyncMock()
    session.call = AsyncMock(return_value={})

    result = await unwrap_piece(
        piece_id="x",
        input_glb=tmp_path / "in.glb",
        output_glb=output,
        strategy=UvStrategy.TRIM_SHEET,
        session=session,
    )
    assert result.success
    assert result.strategy is UvStrategy.SMART_PROJECT  # fell back


@pytest.mark.asyncio
async def test_unwrap_piece_seam_hint_llm_falls_back_to_smart(tmp_path: Path) -> None:
    output = tmp_path / "out.glb"
    output.write_bytes(b"fake glb")

    session = AsyncMock()
    session.call = AsyncMock(return_value={})

    result = await unwrap_piece(
        piece_id="x",
        input_glb=tmp_path / "in.glb",
        output_glb=output,
        strategy=UvStrategy.SEAM_HINT_LLM,
        session=session,
    )
    assert result.success
    assert result.strategy is UvStrategy.SMART_PROJECT


@pytest.mark.asyncio
async def test_unwrap_piece_mcp_error_path(tmp_path: Path) -> None:
    session = AsyncMock()
    session.call = AsyncMock(side_effect=RuntimeError("flax-mcp down"))

    result = await unwrap_piece(
        piece_id="x",
        input_glb=tmp_path / "in.glb",
        output_glb=tmp_path / "out.glb",
        strategy=UvStrategy.SMART_PROJECT,
        session=session,
    )
    assert not result.success
    assert result.error_code == "mcp_error"


@pytest.mark.asyncio
async def test_unwrap_piece_missing_output(tmp_path: Path) -> None:
    session = AsyncMock()
    session.call = AsyncMock(return_value={})  # mcp says ok, but no file

    result = await unwrap_piece(
        piece_id="x",
        input_glb=tmp_path / "in.glb",
        output_glb=tmp_path / "out.glb",
        strategy=UvStrategy.SMART_PROJECT,
        session=session,
    )
    assert not result.success
    assert result.error_code == "output_missing"
