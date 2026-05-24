"""brief.yaml parser + validator. Pydantic does the heavy lifting."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from asset_forge.common.errors import BriefValidationError
from asset_forge.common.types import Brief


def load_brief(path: Path) -> Brief:
    """Load and validate a brief.yaml. Raises BriefValidationError on bad input."""
    if not path.exists():
        raise BriefValidationError(f"brief file not found: {path}")
    if not path.is_file():
        raise BriefValidationError(f"brief path is not a file: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise BriefValidationError(f"yaml parse error in {path}: {e}") from e

    if not isinstance(raw, dict):
        raise BriefValidationError(
            f"brief root must be a mapping, got {type(raw).__name__}"
        )

    try:
        brief = Brief.model_validate(raw)
    except ValidationError as ve:
        raise BriefValidationError(f"schema validation failed: {ve}") from ve

    validate_brief(brief)
    return brief


def validate_brief(brief: Brief) -> None:
    """Semantic validation beyond the schema. Raises BriefValidationError."""

    # Hero piece ids must reference actual pieces
    piece_ids = {p.id for p in brief.pieces}
    bad_hero = [h for h in brief.hero_piece_ids if h not in piece_ids]
    if bad_hero:
        raise BriefValidationError(
            f"hero_piece_ids reference unknown pieces: {bad_hero}"
        )

    # Polygon band must be sane
    lo, hi = brief.style.polygon_count_band
    if lo <= 0 or hi <= lo:
        raise BriefValidationError(
            f"style.polygon_count_band must be (lo, hi) with 0 < lo < hi; got {(lo, hi)}"
        )

    # Pricing must be sane
    if brief.pricing.launch_usd <= 0 or brief.pricing.normal_usd <= 0:
        raise BriefValidationError("pricing values must be positive")
    if brief.pricing.launch_usd > brief.pricing.normal_usd:
        raise BriefValidationError(
            f"pricing.launch_usd ({brief.pricing.launch_usd}) > normal_usd "
            f"({brief.pricing.normal_usd}); launch should be a discount"
        )

    # At least one export target
    if not brief.exports:
        raise BriefValidationError("brief.exports must list at least one target")

    # At least one marketplace
    if not brief.marketplaces:
        raise BriefValidationError("brief.marketplaces must list at least one target")
