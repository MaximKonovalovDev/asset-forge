"""Tests for retopo module. Subprocess + MCP calls are mocked."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from asset_forge.retopo import TopologyTarget, retopo_piece
from asset_forge.retopo.backends import (
    BlenderVoxelRemeshBackend,
    InstantMeshesBackend,
    QuadRemesherBackend,
    QuadriFlowBackend,
)


def test_topology_target_defaults() -> None:
    t = TopologyTarget()
    assert t.target_face_count == 2000
    assert t.quads_preferred is True


def test_quadremesher_returns_unlicensed() -> None:
    import asyncio

    backend = QuadRemesherBackend()
    result = asyncio.run(
        backend.retopo(
            piece_id="x", input_glb=Path("a"), output_glb=Path("b"), target=TopologyTarget()
        )
    )
    assert not result.success
    assert result.error_code == "commercial_not_licensed"


def test_instant_meshes_no_binary() -> None:
    import asyncio

    backend = InstantMeshesBackend(binary_path=None)
    # Force the binary to None by constructing with explicit empty
    backend._binary = None  # type: ignore[attr-defined]
    result = asyncio.run(
        backend.retopo(
            piece_id="x", input_glb=Path("a"), output_glb=Path("b"), target=TopologyTarget()
        )
    )
    assert not result.success
    assert result.error_code == "binary_not_found"


@pytest.mark.asyncio
async def test_quadriflow_subprocess_failure_path(tmp_path: Path) -> None:
    backend = QuadriFlowBackend(binary_path="/nonexistent/quadriflow_xyzzy")
    result = await backend.retopo(
        piece_id="x",
        input_glb=tmp_path / "in.glb",
        output_glb=tmp_path / "out.glb",
        target=TopologyTarget(),
    )
    # Either binary_not_found (rc=127) or exit_<rc>; both are valid failures.
    assert not result.success
    assert result.error_code in {"binary_not_found", "exit_127", "exit_1"}


@pytest.mark.asyncio
async def test_retopo_piece_unknown_backend(tmp_path: Path) -> None:
    result = await retopo_piece(
        piece_id="x",
        input_glb=tmp_path / "in.glb",
        output_glb=tmp_path / "out.glb",
        target=TopologyTarget(),
        backend_name="totally-not-a-backend",
    )
    assert not result.success
    assert result.error_code == "unknown_backend"


@pytest.mark.asyncio
async def test_blender_voxel_backend_mcp_error_path(tmp_path: Path) -> None:
    """The MCP call fails; backend returns a clean failure result."""
    session = AsyncMock()
    session.call = AsyncMock(side_effect=RuntimeError("flax-mcp down"))

    backend = BlenderVoxelRemeshBackend(session)
    result = await backend.retopo(
        piece_id="x",
        input_glb=tmp_path / "in.glb",
        output_glb=tmp_path / "out.glb",
        target=TopologyTarget(),
    )
    assert not result.success
    assert result.error_code == "mcp_error"
    assert "flax-mcp down" in (result.error_message or "")


@pytest.mark.asyncio
async def test_blender_voxel_backend_success(tmp_path: Path) -> None:
    """Happy path: MCP returns, output file present -> success."""
    output = tmp_path / "out.glb"
    output.write_bytes(b"fake glb")  # simulate Blender writing the file

    session = AsyncMock()
    session.call = AsyncMock(return_value={"outputFaceCount": 1800})

    backend = BlenderVoxelRemeshBackend(session)
    result = await backend.retopo(
        piece_id="x",
        input_glb=tmp_path / "in.glb",
        output_glb=output,
        target=TopologyTarget(target_face_count=2000),
    )
    assert result.success
    assert result.output_face_count == 1800
    assert result.is_quad_dominant is False  # voxel = triangles


@pytest.mark.asyncio
async def test_blender_voxel_backend_missing_output(tmp_path: Path) -> None:
    """MCP returns success but no file -> failure."""
    session = AsyncMock()
    session.call = AsyncMock(return_value={})

    backend = BlenderVoxelRemeshBackend(session)
    result = await backend.retopo(
        piece_id="x",
        input_glb=tmp_path / "in.glb",
        output_glb=tmp_path / "out.glb",
        target=TopologyTarget(),
    )
    assert not result.success
    assert result.error_code == "output_missing"
