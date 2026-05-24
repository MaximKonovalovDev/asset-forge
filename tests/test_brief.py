"""Tests for the brief loader / validator."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from asset_forge.common.errors import BriefValidationError
from asset_forge.orchestrator.brief import load_brief


def _minimal_brief_dict() -> dict:
    return {
        "id": "test-001",
        "title": "Test Pack",
        "description": "A pack for testing.",
        "style": {
            "reference_description": "low-poly fantasy",
            "generation_seed": 42,
            "palette": ["#a04040", "#80c0ff"],
            "polygon_count_band": [800, 2500],
            "texel_density_px_per_unit": 512,
        },
        "grid": {
            "preset": "synty_polygon",
            "grid_unit_meters": 1.0,
        },
        "pieces": [
            {"id": "barrel", "category": "container", "prompt": "wooden barrel"},
            {"id": "crate", "category": "container", "prompt": "wooden crate"},
        ],
        "generation": {
            "primary_routes": ["fal-trellis"],
            "hero_routes": ["fal-hunyuan3d-21"],
            "fallback_routes": ["triposr-local"],
            "max_retries_per_piece": 3,
            "pre_prompt_style_prefix": "Low-poly stylized prop",
        },
        "exports": ["unity", "godot"],
        "marketplaces": ["fab", "itchio"],
        "pricing": {"launch_usd": 9.99, "normal_usd": 19.99, "launch_window_days": 14},
        "ai_disclosure": {
            "models_used": ["TRELLIS"],
            "human_review": "all 2 pieces reviewed",
            "commercial_use_verified": True,
        },
        "hero_piece_ids": ["barrel"],
    }


def _write_brief(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "brief.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_minimal_brief_loads(tmp_path: Path) -> None:
    path = _write_brief(tmp_path, _minimal_brief_dict())
    brief = load_brief(path)
    assert brief.id == "test-001"
    assert len(brief.pieces) == 2
    assert brief.is_hero("barrel")
    assert not brief.is_hero("crate")


def test_missing_brief_file_raises(tmp_path: Path) -> None:
    with pytest.raises(BriefValidationError, match="not found"):
        load_brief(tmp_path / "nope.yaml")


def test_bad_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("not: valid: yaml: : :", encoding="utf-8")
    with pytest.raises(BriefValidationError):
        load_brief(path)


def test_duplicate_piece_ids_rejected(tmp_path: Path) -> None:
    data = _minimal_brief_dict()
    data["pieces"].append({"id": "barrel", "category": "x", "prompt": "y"})
    path = _write_brief(tmp_path, data)
    with pytest.raises(BriefValidationError):
        load_brief(path)


def test_invalid_palette_rejected(tmp_path: Path) -> None:
    data = _minimal_brief_dict()
    data["style"]["palette"] = ["red"]  # not #RRGGBB
    path = _write_brief(tmp_path, data)
    with pytest.raises(BriefValidationError):
        load_brief(path)


def test_hero_piece_must_reference_real_piece(tmp_path: Path) -> None:
    data = _minimal_brief_dict()
    data["hero_piece_ids"] = ["nonexistent"]
    path = _write_brief(tmp_path, data)
    with pytest.raises(BriefValidationError, match="hero_piece_ids"):
        load_brief(path)


def test_launch_price_higher_than_normal_rejected(tmp_path: Path) -> None:
    data = _minimal_brief_dict()
    data["pricing"] = {"launch_usd": 29.99, "normal_usd": 19.99, "launch_window_days": 14}
    path = _write_brief(tmp_path, data)
    with pytest.raises(BriefValidationError, match="launch_usd"):
        load_brief(path)


def test_empty_exports_rejected(tmp_path: Path) -> None:
    data = _minimal_brief_dict()
    data["exports"] = []
    path = _write_brief(tmp_path, data)
    with pytest.raises(BriefValidationError, match="exports"):
        load_brief(path)


def test_pack_001_brief_loads() -> None:
    """The real Pack #1 brief must load cleanly."""
    repo_root = Path(__file__).resolve().parent.parent
    brief_path = repo_root / "packs" / "001-fantasy-props" / "brief.yaml"
    brief = load_brief(brief_path)
    assert brief.id == "001-fantasy-props"
    assert len(brief.pieces) == 30
    assert len(brief.hero_piece_ids) == 4
    for hero in brief.hero_piece_ids:
        assert brief.piece_by_id(hero) is not None
