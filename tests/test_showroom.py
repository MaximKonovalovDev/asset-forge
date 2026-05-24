"""Tests for showroom static-site generator."""

from __future__ import annotations

from pathlib import Path

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
from asset_forge.showroom import SiteConfig, build_site


def _build_brief() -> Brief:
    return Brief(
        id="test-showroom",
        title="Showroom Test",
        description="A pack for testing the showroom generator.",
        style=StyleSpec(
            palette=("#a04040", "#80c0ff"),
            reference_description="low-poly fantasy",
            shading="faceted",
        ),
        grid=GridSpec(),
        pieces=(
            Piece(id="barrel", category="container", prompt="wooden barrel"),
            Piece(id="sword", category="weapon", prompt="iron sword"),
        ),
        generation=GenerationConfig(),
        exports=("unity", "godot"),
        marketplaces=("fab",),
        demo_scenes=(DemoScene(name="s", description="d"),),
        pricing=PricingConfig(launch_usd=9.99, normal_usd=19.99),
        ai_disclosure=AiDisclosure(
            models_used=("TRELLIS",),
            human_review="reviewed",
            commercial_use_verified=True,
        ),
        hero_piece_ids=("sword",),
    )


def _seed_pipeline_outputs(paths: PackPaths, pieces: list[str], with_previews: bool = True) -> None:
    """Seed fake pipeline outputs that the showroom should pick up."""
    for pid in pieces:
        (paths.lods_dir / f"{pid}.glb").write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 64)
        if with_previews:
            piece_prev = paths.previews_dir / pid
            piece_prev.mkdir(parents=True, exist_ok=True)
            (piece_prev / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
            (piece_prev / "thumb_front.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
            (piece_prev / "thumb_back.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    if with_previews:
        (paths.previews_dir / "cover.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)


@pytest.mark.asyncio
async def test_build_site_basic_layout(tmp_path: Path) -> None:
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()
    _seed_pipeline_outputs(paths, ["barrel", "sword"])

    result = await build_site(paths, brief, pieces_succeeded=["barrel", "sword"])

    assert result.success
    assert result.site_root is not None
    assert (result.site_root / "index.html").exists()
    assert (result.site_root / "assets" / "style.css").exists()
    assert (result.site_root / "pieces" / "barrel.html").exists()
    assert (result.site_root / "pieces" / "sword.html").exists()
    # GLBs copied for viewer
    assert (result.site_root / "glbs" / "barrel.glb").exists()
    # Previews copied
    assert (result.site_root / "previews" / "barrel" / "hero.png").exists()
    assert (result.site_root / "previews" / "cover.png").exists()


@pytest.mark.asyncio
async def test_index_html_contains_pack_metadata(tmp_path: Path) -> None:
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()
    _seed_pipeline_outputs(paths, ["barrel", "sword"])

    result = await build_site(paths, brief, pieces_succeeded=["barrel", "sword"])
    assert result.success
    assert result.site_root is not None
    index = (result.site_root / "index.html").read_text(encoding="utf-8")

    assert brief.title in index
    assert brief.description in index
    assert "TRELLIS" in index  # AI disclosure section
    assert "$9.99" in index  # launch price
    assert "container" in index.lower() or "Container" in index
    assert "weapon" in index.lower() or "Weapon" in index
    # Color swatches rendered
    assert "#a04040" in index


@pytest.mark.asyncio
async def test_piece_page_has_three_js_viewer(tmp_path: Path) -> None:
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()
    _seed_pipeline_outputs(paths, ["barrel"])

    result = await build_site(paths, brief, pieces_succeeded=["barrel"])
    assert result.success
    assert result.site_root is not None

    piece_html = (result.site_root / "pieces" / "barrel.html").read_text(encoding="utf-8")
    assert 'id="viewer"' in piece_html
    assert "three" in piece_html.lower()
    assert "GLTFLoader" in piece_html
    assert "OrbitControls" in piece_html
    # Glb path threaded through
    assert "../glbs/barrel.glb" in piece_html


@pytest.mark.asyncio
async def test_marketplace_links_rendered_when_supplied(tmp_path: Path) -> None:
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()
    _seed_pipeline_outputs(paths, ["barrel"])

    config = SiteConfig(
        marketplace_links={
            "fab": "https://fab.com/example",
            "itchio": "https://example.itch.io/pack",
        }
    )
    result = await build_site(paths, brief, pieces_succeeded=["barrel"], config=config)
    assert result.success
    assert result.site_root is not None

    index = (result.site_root / "index.html").read_text(encoding="utf-8")
    assert "https://fab.com/example" in index
    assert "https://example.itch.io/pack" in index


@pytest.mark.asyncio
async def test_build_site_works_without_previews(tmp_path: Path) -> None:
    """If no preview renders exist, the site still builds (just without images)."""
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()
    _seed_pipeline_outputs(paths, ["barrel"], with_previews=False)

    result = await build_site(paths, brief, pieces_succeeded=["barrel"])
    assert result.success
    assert result.site_root is not None
    # Cover image absent in HTML
    index = (result.site_root / "index.html").read_text(encoding="utf-8")
    assert 'class="cover"' not in index
    # Piece page still rendered (we have GLB)
    assert (result.site_root / "pieces" / "barrel.html").exists()


@pytest.mark.asyncio
async def test_build_site_skips_piece_page_when_no_glb(tmp_path: Path) -> None:
    """Pieces without a GLB don't get a viewer page (no point)."""
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()
    # Only barrel has a GLB
    (paths.lods_dir / "barrel.glb").write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 64)

    result = await build_site(paths, brief, pieces_succeeded=["barrel", "sword"])
    assert result.success
    assert result.site_root is not None
    assert (result.site_root / "pieces" / "barrel.html").exists()
    assert not (result.site_root / "pieces" / "sword.html").exists()


@pytest.mark.asyncio
async def test_pages_count_in_result(tmp_path: Path) -> None:
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()
    _seed_pipeline_outputs(paths, ["barrel", "sword"])

    result = await build_site(paths, brief, pieces_succeeded=["barrel", "sword"])
    assert result.success
    # 1 index + 2 piece pages
    assert result.pages_generated == 3
