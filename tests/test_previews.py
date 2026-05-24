"""Tests for previews module. MCP calls mocked."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from asset_forge.common.paths import PackPaths
from asset_forge.common.types import (
    AiDisclosure,
    Brief,
    DemoScene,
    GenerationConfig,
    GridSpec,
    Piece,
    PricingConfig,
    StyleSpec,
)
from asset_forge.previews import PreviewSettings, preview_pack, preview_piece


def _build_brief() -> Brief:
    return Brief(
        id="test-prev",
        title="Preview Test",
        description="d",
        style=StyleSpec(palette=("#a04040",)),
        grid=GridSpec(),
        pieces=(
            Piece(id="barrel", category="container", prompt="x"),
            Piece(id="crate", category="container", prompt="y"),
        ),
        generation=GenerationConfig(
            primary_routes=("fal-trellis",),
            hero_routes=(),
            fallback_routes=(),
        ),
        exports=("unity",),
        marketplaces=("fab",),
        demo_scenes=(DemoScene(name="s", description="d"),),
        pricing=PricingConfig(launch_usd=9.99, normal_usd=19.99),
        ai_disclosure=AiDisclosure(
            models_used=("TRELLIS",),
            human_review="reviewed",
            commercial_use_verified=True,
        ),
        hero_piece_ids=("barrel",),
    )


def test_preview_settings_defaults() -> None:
    s = PreviewSettings()
    assert s.thumbnail_size == 512
    assert s.hero_size == 1024
    assert "front" in s.thumbnail_angles
    assert s.use_eevee is True


@pytest.mark.asyncio
async def test_preview_piece_missing_input(tmp_path: Path) -> None:
    session = AsyncMock()
    result = await preview_piece(
        piece_id="x",
        input_glb=tmp_path / "missing.glb",
        dest_dir=tmp_path / "out",
        session=session,
    )
    assert not result.success
    assert result.error_code == "input_missing"
    session.call.assert_not_called()


@pytest.mark.asyncio
async def test_preview_piece_success(tmp_path: Path) -> None:
    """Bridge writes a hero.png + thumb files; we detect them on disk."""
    input_glb = tmp_path / "in.glb"
    input_glb.write_bytes(b"fake")

    dest = tmp_path / "previews"
    piece_dir = dest / "barrel"

    async def fake_call(tool: str, args: dict, **kw):
        piece_dir.mkdir(parents=True, exist_ok=True)
        (piece_dir / "hero.png").write_bytes(b"\x89PNG")
        (piece_dir / "thumb_front.png").write_bytes(b"\x89PNG")
        (piece_dir / "thumb_back.png").write_bytes(b"\x89PNG")
        (piece_dir / "thumb_three_quarter.png").write_bytes(b"\x89PNG")
        (piece_dir / "thumb_top.png").write_bytes(b"\x89PNG")
        return {"ok": True}

    session = AsyncMock()
    session.call = AsyncMock(side_effect=fake_call)

    result = await preview_piece(
        piece_id="barrel",
        input_glb=input_glb,
        dest_dir=dest,
        session=session,
    )
    assert result.success
    assert result.hero_image is not None
    assert result.hero_image.name == "hero.png"
    assert len(result.thumbnail_images) == 4


@pytest.mark.asyncio
async def test_preview_piece_hero_missing_after_call(tmp_path: Path) -> None:
    input_glb = tmp_path / "in.glb"
    input_glb.write_bytes(b"fake")

    session = AsyncMock()
    session.call = AsyncMock(return_value={"ok": True})  # but no files written

    result = await preview_piece(
        piece_id="x",
        input_glb=input_glb,
        dest_dir=tmp_path / "previews",
        session=session,
    )
    assert not result.success
    assert result.error_code == "hero_missing"


@pytest.mark.asyncio
async def test_preview_piece_mcp_error(tmp_path: Path) -> None:
    input_glb = tmp_path / "in.glb"
    input_glb.write_bytes(b"fake")

    session = AsyncMock()
    session.call = AsyncMock(side_effect=RuntimeError("blender bridge down"))

    result = await preview_piece(
        piece_id="x",
        input_glb=input_glb,
        dest_dir=tmp_path / "previews",
        session=session,
    )
    assert not result.success
    assert result.error_code == "mcp_error"


@pytest.mark.asyncio
async def test_preview_pack_falls_back_through_source_dirs(tmp_path: Path) -> None:
    """preview_pack checks LOD -> final -> materials -> uv -> retopo
    and uses whichever has the GLB."""
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    # Put barrel.glb in retopo_dir only (worst case fallback)
    (paths.retopo_dir / "barrel.glb").write_bytes(b"fake")

    call_count = {"n": 0}

    async def fake_call(tool: str, args: dict, **kw):
        call_count["n"] += 1
        if tool == "blender_bridge/render_piece":
            piece_dir = Path(args["outputDir"])
            piece_dir.mkdir(parents=True, exist_ok=True)
            (piece_dir / "hero.png").write_bytes(b"\x89PNG")
        elif tool == "blender_bridge/render_cover":
            cover = Path(args["outputPath"])
            cover.parent.mkdir(parents=True, exist_ok=True)
            cover.write_bytes(b"\x89PNG")
        return {"ok": True}

    session = AsyncMock()
    session.call = AsyncMock(side_effect=fake_call)

    results = await preview_pack(
        paths,
        brief,
        pieces_succeeded=["barrel", "crate"],
        session=session,
    )

    # barrel exists in retopo_dir; crate doesn't exist anywhere
    assert results["barrel"].success
    assert not results["crate"].success
    assert results["crate"].error_code == "input_missing"
    # Cover attempted (hero_piece_ids = ("barrel",))
    assert "__cover__" in results


@pytest.mark.asyncio
async def test_preview_pack_no_hero_pieces_cover_fails_cleanly(tmp_path: Path) -> None:
    brief_data = _build_brief().model_dump()
    brief_data["hero_piece_ids"] = ()
    brief = type(_build_brief())(**brief_data)

    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()
    (paths.retopo_dir / "barrel.glb").write_bytes(b"fake")
    (paths.retopo_dir / "crate.glb").write_bytes(b"fake")

    async def fake_call(tool: str, args: dict, **kw):
        if tool == "blender_bridge/render_piece":
            piece_dir = Path(args["outputDir"])
            piece_dir.mkdir(parents=True, exist_ok=True)
            (piece_dir / "hero.png").write_bytes(b"\x89PNG")
        return {"ok": True}

    session = AsyncMock()
    session.call = AsyncMock(side_effect=fake_call)

    results = await preview_pack(
        paths,
        brief,
        pieces_succeeded=["barrel", "crate"],
        session=session,
    )

    assert results["barrel"].success
    assert results["crate"].success
    # Cover should fail with no_hero_pieces
    cover = results["__cover__"]
    assert not cover.success
    assert cover.error_code == "no_hero_pieces"
