"""Tests for manifest templates + bundle generation."""

from __future__ import annotations

import zipfile
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
from asset_forge.manifest import ManifestResult, Target, build_manifests
from asset_forge.manifest.templates import (
    ai_disclosure_text,
    license_text,
    pack_readme,
)


def _build_brief() -> Brief:
    return Brief(
        id="test-001",
        title="Test Pack",
        description="A pack for testing manifests.",
        style=StyleSpec(palette=("#a04040",), reference_description="low-poly fantasy"),
        grid=GridSpec(),
        pieces=(
            Piece(id="barrel", category="container", prompt="wooden barrel"),
            Piece(id="crate", category="container", prompt="wooden crate"),
            Piece(id="sword", category="weapon", prompt="iron sword"),
        ),
        generation=GenerationConfig(
            primary_routes=("fal-trellis",),
            hero_routes=(),
            fallback_routes=(),
            pre_prompt_style_prefix="Low-poly",
        ),
        exports=("unity", "godot", "master_glb"),
        marketplaces=("fab", "itchio", "gumroad"),
        demo_scenes=(DemoScene(name="scene", description="d"),),
        pricing=PricingConfig(launch_usd=9.99, normal_usd=19.99, launch_window_days=14),
        ai_disclosure=AiDisclosure(
            models_used=("TRELLIS", "Hunyuan3D"),
            human_review="3 pieces reviewed",
            commercial_use_verified=True,
        ),
        hero_piece_ids=("sword",),
    )


def test_pack_readme_has_essentials() -> None:
    brief = _build_brief()
    md = pack_readme(brief)
    assert brief.title in md
    assert brief.description.strip() in md
    assert "3 pieces" in md  # piece count
    assert "container" in md  # category section
    assert "barrel" in md
    assert "ai_disclosure.txt" in md.lower() or "ai disclosure" in md.lower()


def test_license_text_has_required_clauses() -> None:
    brief = _build_brief()
    txt = license_text(brief)
    assert "Copyright" in txt
    assert "non-exclusive" in txt
    assert "PROHIBITED" in txt
    assert "NFT" in txt  # we explicitly ban NFT use
    assert "training" in txt.lower()  # ML training prohibition


def test_ai_disclosure_text_lists_models() -> None:
    brief = _build_brief()
    txt = ai_disclosure_text(brief)
    assert "TRELLIS" in txt
    assert "Hunyuan3D" in txt
    assert "commercial-use" in txt.lower() or "commercial use" in txt.lower()
    assert "3 pieces reviewed" in txt


@pytest.mark.asyncio
async def test_build_manifests_creates_bundles(tmp_path: Path) -> None:
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    result = await build_manifests(paths, brief)
    assert isinstance(result, ManifestResult)
    assert result.pack_id == brief.id
    assert not result.failures
    # 3 marketplaces requested -> 3 bundles
    assert len(result.bundles) == 3
    targets = {b.target for b in result.bundles}
    assert targets == {Target.FAB, Target.ITCHIO, Target.GUMROAD}


@pytest.mark.asyncio
async def test_bundle_contents_zipped(tmp_path: Path) -> None:
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    result = await build_manifests(paths, brief, targets=(Target.FAB,))
    assert len(result.bundles) == 1
    bundle = result.bundles[0]
    assert bundle.bundle_path.exists()
    assert bundle.bundle_path.suffix == ".zip"

    with zipfile.ZipFile(bundle.bundle_path) as zf:
        names = zf.namelist()
        assert any(n.endswith("README.md") for n in names)
        assert any(n.endswith("license.txt") for n in names)
        assert any(n.endswith("ai_disclosure.txt") for n in names)
        assert any("fab_description.md" in n for n in names)


@pytest.mark.asyncio
async def test_build_manifests_skips_unsupported_targets(tmp_path: Path) -> None:
    brief = _build_brief()
    # Brief advertises fab+itchio+gumroad; ask for UNITY which it doesn't
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    result = await build_manifests(paths, brief, targets=(Target.UNITY,))
    assert len(result.bundles) == 0
    assert not result.failures  # silently skipped, not failed
