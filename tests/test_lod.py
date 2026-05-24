"""Tests for the lod module. MCP calls mocked."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from asset_forge.lod import LodLevels, lod_piece


def test_lod_levels_default_chain() -> None:
    lvls = LodLevels()
    assert lvls.as_list() == [1.0, 0.5, 0.25, 0.125]


def test_lod_levels_custom_chain() -> None:
    lvls = LodLevels(lod0=1.0, lod1=0.7, lod2=0.4, lod3=0.2)
    assert lvls.as_list() == [1.0, 0.7, 0.4, 0.2]


@pytest.mark.asyncio
async def test_lod_piece_missing_input(tmp_path: Path) -> None:
    session = AsyncMock()
    result = await lod_piece(
        piece_id="x",
        input_glb=tmp_path / "missing.glb",
        output_glb=tmp_path / "out.glb",
        session=session,
    )
    assert not result.success
    assert result.error_code == "input_missing"
    session.call.assert_not_called()


@pytest.mark.asyncio
async def test_lod_piece_mcp_error(tmp_path: Path) -> None:
    input_glb = tmp_path / "in.glb"
    input_glb.write_bytes(b"fake")

    session = AsyncMock()
    session.call = AsyncMock(side_effect=RuntimeError("meshopt unreachable"))

    result = await lod_piece(
        piece_id="x",
        input_glb=input_glb,
        output_glb=tmp_path / "out.glb",
        session=session,
    )
    assert not result.success
    assert result.error_code == "mcp_error"


@pytest.mark.asyncio
async def test_lod_piece_success(tmp_path: Path) -> None:
    input_glb = tmp_path / "in.glb"
    input_glb.write_bytes(b"fake glb")
    output_glb = tmp_path / "out.glb"
    output_glb.write_bytes(b"fake lod output")

    session = AsyncMock()
    session.call = AsyncMock(
        return_value={
            "levelsProduced": 4,
            "faceCounts": [2000, 1000, 500, 250],
            "sizeBytes": 15_000,
        }
    )

    result = await lod_piece(
        piece_id="barrel",
        input_glb=input_glb,
        output_glb=output_glb,
        session=session,
    )
    assert result.success
    assert result.levels_produced == 4
    assert result.face_counts == (2000, 1000, 500, 250)
    assert result.size_bytes == 15_000


@pytest.mark.asyncio
async def test_lod_piece_missing_output_after_success(tmp_path: Path) -> None:
    """MCP returned success but no file was written."""
    input_glb = tmp_path / "in.glb"
    input_glb.write_bytes(b"fake")

    session = AsyncMock()
    session.call = AsyncMock(return_value={"levelsProduced": 4})

    result = await lod_piece(
        piece_id="x",
        input_glb=input_glb,
        output_glb=tmp_path / "out.glb",
        session=session,
    )
    assert not result.success
    assert result.error_code == "output_missing"


@pytest.mark.asyncio
async def test_lod_piece_filesize_fallback_to_stat(tmp_path: Path) -> None:
    """If meshopt doesn't report sizeBytes, we stat the file ourselves."""
    input_glb = tmp_path / "in.glb"
    input_glb.write_bytes(b"fake")
    output_glb = tmp_path / "out.glb"
    output_glb.write_bytes(b"some output content")

    session = AsyncMock()
    session.call = AsyncMock(return_value={"faceCounts": [1000]})

    result = await lod_piece(
        piece_id="x",
        input_glb=input_glb,
        output_glb=output_glb,
        session=session,
    )
    assert result.success
    assert result.size_bytes == len(b"some output content")
    assert result.levels_produced == 1  # inferred from face_counts
