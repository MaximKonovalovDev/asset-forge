"""Style review: scores each piece's hero image against the pack reference
or against the centroid of all hero images. Flags outliers below threshold.

This is the gate that prevents shipping AI-mush packs. Pieces below
threshold are returned as outliers; the orchestrator can re-queue them
through GENERATION (Phase 5 feature; v1 just reports).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths
from asset_forge.common.types import Brief

from .scorers import HistogramScorer, StyleScorer

_log = get_logger("style")


@dataclass(frozen=True, slots=True)
class StyleReviewConfig:
    """How strict to be about style consistency."""

    threshold: float = 0.70  # 0..1; below this is an outlier
    use_clip: bool = False  # use OpenCLIP if available (heavier)
    reference_strategy: str = "centroid"  # "centroid" | "hero" | "operator_image"


@dataclass(frozen=True, slots=True)
class PieceScore:
    piece_id: str
    score: float
    is_outlier: bool


@dataclass(frozen=True, slots=True)
class StyleReviewResult:
    pack_id: str
    success: bool
    scores: tuple[PieceScore, ...] = ()
    outliers: tuple[str, ...] = ()
    mean_score: float = 0.0
    threshold: float = 0.0
    backend: str = ""
    duration_seconds: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def _centroid(embeddings: list[tuple[float, ...]]) -> tuple[float, ...]:
    """Mean vector. Empty input -> empty tuple."""
    if not embeddings:
        return ()
    valid = [e for e in embeddings if e]
    if not valid:
        return ()
    length = len(valid[0])
    if not all(len(e) == length for e in valid):
        return ()
    return tuple(sum(e[i] for e in valid) / len(valid) for i in range(length))


def _resolve_hero_image(paths: PackPaths, piece_id: str) -> Path | None:
    candidate = paths.previews_dir / piece_id / "hero.png"
    return candidate if candidate.exists() else None


def _resolve_reference_image(paths: PackPaths, brief: Brief) -> Path | None:
    """Find an operator-supplied reference image if it exists."""
    if not brief.style.reference_image:
        return None
    # The brief lists 'reference/hero.png'; resolve relative to packs/<id>/
    packs_root = paths.root.parent.parent / "packs" / brief.id
    candidate = packs_root / brief.style.reference_image
    if candidate.exists():
        return candidate
    return None


async def review_pack_style(
    paths: PackPaths,
    brief: Brief,
    *,
    pieces_succeeded: list[str],
    config: StyleReviewConfig | None = None,
) -> StyleReviewResult:
    """Score every piece's hero image. Return outliers below threshold.

    NEVER raises; returns StyleReviewResult.
    """
    cfg = config or StyleReviewConfig()
    start = time.monotonic()

    # Pick scorer
    scorer: StyleScorer
    if cfg.use_clip:
        try:
            from .scorers import ClipScorer

            scorer = ClipScorer()
        except Exception:
            scorer = HistogramScorer()
    else:
        scorer = HistogramScorer()

    # Embed every piece's hero
    embeddings: dict[str, tuple[float, ...]] = {}
    missing: list[str] = []
    for piece_id in pieces_succeeded:
        if brief.piece_by_id(piece_id) is None:
            continue
        hero = _resolve_hero_image(paths, piece_id)
        if hero is None:
            missing.append(piece_id)
            continue
        emb = scorer.embed(hero)
        if emb:
            embeddings[piece_id] = emb
        else:
            missing.append(piece_id)

    if not embeddings:
        return StyleReviewResult(
            pack_id=brief.id,
            success=False,
            duration_seconds=time.monotonic() - start,
            backend=scorer.name,
            error_code="no_hero_images",
            error_message=(
                f"No hero images found for any piece (checked {len(pieces_succeeded)} pieces). "
                "Run PREVIEWS phase first."
            ),
        )

    # Build reference embedding per strategy
    reference_emb: tuple[float, ...] = ()
    used_strategy = cfg.reference_strategy
    if cfg.reference_strategy == "operator_image":
        ref_path = _resolve_reference_image(paths, brief)
        if ref_path is not None:
            reference_emb = scorer.embed(ref_path)
        if not reference_emb:
            used_strategy = "centroid"  # fall back

    if used_strategy == "centroid":
        reference_emb = _centroid(list(embeddings.values()))
    elif used_strategy == "hero":
        # Use the first hero piece's embedding as reference
        for hid in brief.hero_piece_ids:
            if hid in embeddings:
                reference_emb = embeddings[hid]
                break
        if not reference_emb:
            reference_emb = _centroid(list(embeddings.values()))
            used_strategy = "centroid"

    if not reference_emb:
        return StyleReviewResult(
            pack_id=brief.id,
            success=False,
            duration_seconds=time.monotonic() - start,
            backend=scorer.name,
            error_code="no_reference",
            error_message="Could not build a reference embedding",
        )

    # Score every piece
    scores: list[PieceScore] = []
    for piece_id, emb in embeddings.items():
        sim = StyleScorer.cosine_similarity(emb, reference_emb)
        scores.append(
            PieceScore(piece_id=piece_id, score=sim, is_outlier=sim < cfg.threshold)
        )

    scores.sort(key=lambda s: s.score)
    outliers = tuple(s.piece_id for s in scores if s.is_outlier)
    mean = sum(s.score for s in scores) / max(len(scores), 1)

    _log.info(
        "style.reviewed",
        pack=brief.id,
        backend=scorer.name,
        scored=len(scores),
        outliers=len(outliers),
        mean=round(mean, 3),
    )

    return StyleReviewResult(
        pack_id=brief.id,
        success=True,
        scores=tuple(scores),
        outliers=outliers,
        mean_score=round(mean, 4),
        threshold=cfg.threshold,
        backend=scorer.name,
        duration_seconds=time.monotonic() - start,
        metadata={
            "reference_strategy_used": used_strategy,
            "pieces_missing_heros": missing,
        },
    )
