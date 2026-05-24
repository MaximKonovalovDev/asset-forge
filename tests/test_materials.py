"""Tests for materials module."""

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
from asset_forge.materials import (
    MATERIAL_LIBRARY,
    assign_pack_materials,
    assign_piece_material,
    find_materials_for_category,
)
from asset_forge.materials.api import (
    _color_distance,
    _hex_to_rgb,
    _palette_match_score,
    _pick_material,
)


def _brief(palette: tuple[str, ...] = ("#a04040", "#604030", "#80c0ff")) -> Brief:
    return Brief(
        id="test-mats",
        title="Mat Test",
        description="d",
        style=StyleSpec(
            palette=palette,
            reference_description="warm fantasy",
        ),
        grid=GridSpec(),
        pieces=(
            Piece(id="barrel", category="container", prompt="wooden barrel iron-bound"),
            Piece(id="sword", category="weapon", prompt="iron sword"),
        ),
        generation=GenerationConfig(),
        exports=("unity",),
        marketplaces=("fab",),
        demo_scenes=(DemoScene(name="s", description="d"),),
        pricing=PricingConfig(launch_usd=9.99, normal_usd=19.99),
        ai_disclosure=AiDisclosure(
            models_used=("TRELLIS",),
            human_review="reviewed",
            commercial_use_verified=True,
        ),
    )


def test_library_is_non_empty() -> None:
    assert len(MATERIAL_LIBRARY) >= 20
    # No duplicate ids
    ids = [m.id for m in MATERIAL_LIBRARY]
    assert len(ids) == len(set(ids))


def test_find_materials_for_category_container() -> None:
    mats = find_materials_for_category("container")
    assert len(mats) > 0
    for m in mats:
        assert "container" in m.category_tags


def test_find_materials_for_unknown_category_empty() -> None:
    assert find_materials_for_category("zzz_not_real") == ()


def test_hex_to_rgb() -> None:
    assert _hex_to_rgb("#000000") == (0, 0, 0)
    assert _hex_to_rgb("#ffffff") == (255, 255, 255)
    assert _hex_to_rgb("#a04040") == (160, 64, 64)


def test_color_distance_zero_for_identical() -> None:
    assert _color_distance("#a04040", "#a04040") == 0.0


def test_color_distance_max_black_white() -> None:
    d = _color_distance("#000000", "#ffffff")
    assert 440 < d < 442  # ~441.7


def test_palette_match_score_perfect() -> None:
    brown = _palette_match_score(
        MATERIAL_LIBRARY[0],  # wood_oak #604030
        ("#604030",),
    )
    assert brown == 1.0


def test_palette_match_score_falls_off() -> None:
    high = _palette_match_score(
        MATERIAL_LIBRARY[0],  # wood_oak
        ("#604030",),  # exact match
    )
    low = _palette_match_score(
        MATERIAL_LIBRARY[0],  # wood_oak
        ("#80c0ff",),  # very different (cyan/blue)
    )
    assert high > low


def test_pick_material_prefers_wood_for_wooden_barrel() -> None:
    brief = _brief()
    piece = brief.pieces[0]  # wooden barrel
    choice = _pick_material(piece, brief)
    # Wood-family or burlap should win for "wooden barrel" with warm palette
    wood_or_natural = {
        m.id for m in MATERIAL_LIBRARY if "wood" in m.id or "burlap" in m.id or "leather" in m.id
    }
    assert choice.material_id in wood_or_natural


def test_pick_material_prefers_iron_for_iron_sword() -> None:
    brief = _brief(palette=("#606060", "#a0a0a4"))  # grey palette pushes toward metal
    piece = Piece(id="sword", category="weapon", prompt="iron sword steel blade")
    choice = _pick_material(piece, brief)
    assert "iron" in choice.material_id or "steel" in choice.material_id


def test_pick_material_deterministic_across_runs() -> None:
    brief = _brief()
    piece = brief.pieces[0]
    a = _pick_material(piece, brief)
    b = _pick_material(piece, brief)
    assert a.material_id == b.material_id
    assert a.score == b.score


@pytest.mark.asyncio
async def test_assign_piece_material_missing_input(tmp_path: Path) -> None:
    brief = _brief()
    piece = brief.pieces[0]
    session = AsyncMock()

    result = await assign_piece_material(
        piece, brief,
        input_glb=tmp_path / "missing.glb",
        output_glb=tmp_path / "out.glb",
        session=session,
    )
    assert not result.success
    assert result.error_code == "input_missing"


@pytest.mark.asyncio
async def test_assign_piece_material_success(tmp_path: Path) -> None:
    brief = _brief()
    piece = brief.pieces[0]
    input_glb = tmp_path / "in.glb"
    input_glb.write_bytes(b"fake")
    output_glb = tmp_path / "out.glb"

    async def fake_call(tool: str, args: dict, **kw):
        Path(args["outputPath"]).write_bytes(b"fake out")
        return {"ok": True}

    session = AsyncMock()
    session.call = AsyncMock(side_effect=fake_call)

    result = await assign_piece_material(
        piece, brief, input_glb, output_glb, session=session
    )
    assert result.success
    assert result.choice is not None
    assert result.choice.material_id  # something was picked


@pytest.mark.asyncio
async def test_assign_piece_material_mcp_error_keeps_choice(tmp_path: Path) -> None:
    brief = _brief()
    piece = brief.pieces[0]
    input_glb = tmp_path / "in.glb"
    input_glb.write_bytes(b"fake")

    session = AsyncMock()
    session.call = AsyncMock(side_effect=RuntimeError("bridge down"))

    result = await assign_piece_material(
        piece, brief, input_glb, tmp_path / "out.glb", session=session
    )
    assert not result.success
    assert result.error_code == "mcp_error"
    # Choice is still populated even when MCP failed (operator can see what we WANTED to assign)
    assert result.choice is not None


@pytest.mark.asyncio
async def test_assign_pack_materials_full_loop(tmp_path: Path) -> None:
    brief = _brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    # Seed inputs in uv_dir
    (paths.uv_dir / "barrel.glb").write_bytes(b"fake")
    (paths.uv_dir / "sword.glb").write_bytes(b"fake")

    async def fake_call(tool: str, args: dict, **kw):
        Path(args["outputPath"]).write_bytes(b"fake out")
        return {"ok": True}

    session = AsyncMock()
    session.call = AsyncMock(side_effect=fake_call)

    results = await assign_pack_materials(
        paths, brief, pieces_succeeded=["barrel", "sword"], session=session
    )
    assert results["barrel"].success
    assert results["sword"].success
    assert (paths.materials_dir / "barrel.glb").exists()
    assert (paths.materials_dir / "sword.glb").exists()
