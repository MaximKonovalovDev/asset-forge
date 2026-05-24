"""Tests for style review."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

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
from asset_forge.style import (
    HistogramScorer,
    StyleReviewConfig,
    StyleScorer,
    review_pack_style,
)


def _brief() -> Brief:
    return Brief(
        id="test-style",
        title="Style Test",
        description="d",
        style=StyleSpec(
            palette=("#a04040",),
            reference_description="warm fantasy",
        ),
        grid=GridSpec(),
        pieces=(
            Piece(id="barrel", category="container", prompt="wooden barrel"),
            Piece(id="crate", category="container", prompt="wooden crate"),
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
        hero_piece_ids=("barrel",),
    )


def _write_image(path: Path, rgb: tuple[int, int, int], size: int = 64) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (size, size), rgb)
    img.save(path)


def test_histogram_scorer_identical_images_high_similarity(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    _write_image(a, (160, 64, 64))
    _write_image(b, (160, 64, 64))

    scorer = HistogramScorer()
    ea = scorer.embed(a)
    eb = scorer.embed(b)
    sim = StyleScorer.cosine_similarity(ea, eb)
    assert sim > 0.95


def test_histogram_scorer_different_colors_lower_similarity(tmp_path: Path) -> None:
    red = tmp_path / "red.png"
    blue = tmp_path / "blue.png"
    _write_image(red, (200, 30, 30))
    _write_image(blue, (30, 30, 200))

    scorer = HistogramScorer()
    er = scorer.embed(red)
    eb = scorer.embed(blue)
    sim_same = StyleScorer.cosine_similarity(er, er)
    sim_cross = StyleScorer.cosine_similarity(er, eb)
    assert sim_same > sim_cross


def test_histogram_embed_missing_file_returns_empty(tmp_path: Path) -> None:
    scorer = HistogramScorer()
    assert scorer.embed(tmp_path / "nope.png") == ()


def test_cosine_similarity_empty_tuples_returns_zero() -> None:
    assert StyleScorer.cosine_similarity((), ()) == 0.0
    assert StyleScorer.cosine_similarity((1.0,), ()) == 0.0


def test_cosine_similarity_orthogonal_returns_half() -> None:
    """Orthogonal vectors -> cos=0 -> remapped to 0.5."""
    a = (1.0, 0.0)
    b = (0.0, 1.0)
    sim = StyleScorer.cosine_similarity(a, b)
    assert abs(sim - 0.5) < 0.01


@pytest.mark.asyncio
async def test_review_pack_style_no_heros_fails_gracefully(tmp_path: Path) -> None:
    brief = _brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    result = await review_pack_style(
        paths, brief, pieces_succeeded=["barrel", "crate", "sword"]
    )
    assert not result.success
    assert result.error_code == "no_hero_images"


@pytest.mark.asyncio
async def test_review_pack_style_all_consistent(tmp_path: Path) -> None:
    """When all pieces have similar hero images, no outliers."""
    brief = _brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    for pid in ["barrel", "crate", "sword"]:
        _write_image(paths.previews_dir / pid / "hero.png", (160, 80, 50))

    result = await review_pack_style(
        paths, brief, pieces_succeeded=["barrel", "crate", "sword"],
        config=StyleReviewConfig(threshold=0.70),
    )
    assert result.success
    assert len(result.scores) == 3
    assert len(result.outliers) == 0
    assert result.mean_score > 0.8


@pytest.mark.asyncio
async def test_review_pack_style_flags_outlier(tmp_path: Path) -> None:
    """One piece with wildly different color should be flagged."""
    brief = _brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    # Two warm; one cold (outlier)
    _write_image(paths.previews_dir / "barrel" / "hero.png", (180, 60, 40))
    _write_image(paths.previews_dir / "crate" / "hero.png", (170, 70, 50))
    _write_image(paths.previews_dir / "sword" / "hero.png", (30, 50, 200))

    result = await review_pack_style(
        paths, brief, pieces_succeeded=["barrel", "crate", "sword"],
        config=StyleReviewConfig(threshold=0.85),
    )
    assert result.success
    # sword should be the outlier with high threshold
    assert "sword" in result.outliers


@pytest.mark.asyncio
async def test_review_pack_style_centroid_strategy(tmp_path: Path) -> None:
    brief = _brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    for pid, color in [
        ("barrel", (160, 80, 50)),
        ("crate", (180, 70, 40)),
        ("sword", (140, 90, 60)),
    ]:
        _write_image(paths.previews_dir / pid / "hero.png", color)

    result = await review_pack_style(
        paths, brief, pieces_succeeded=["barrel", "crate", "sword"],
        config=StyleReviewConfig(reference_strategy="centroid"),
    )
    assert result.success
    assert result.metadata["reference_strategy_used"] == "centroid"


@pytest.mark.asyncio
async def test_review_pack_style_hero_strategy(tmp_path: Path) -> None:
    brief = _brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    for pid in ["barrel", "crate", "sword"]:
        _write_image(paths.previews_dir / pid / "hero.png", (160, 80, 50))

    result = await review_pack_style(
        paths, brief, pieces_succeeded=["barrel", "crate", "sword"],
        config=StyleReviewConfig(reference_strategy="hero"),
    )
    assert result.success
    # Barrel is the only hero piece in the brief
    barrel_score = next(s for s in result.scores if s.piece_id == "barrel")
    assert barrel_score.score > 0.95  # compared to itself
