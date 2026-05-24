"""Domain types. Strict, immutable, no IO.

The whole pipeline speaks these. brief.yaml deserializes into Brief
which contains Piece objects; every other phase consumes/produces
GenResult, StyleSpec, Receipt, etc.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Phase(StrEnum):
    """Pipeline phases. Stored in state.json; orchestrator resumes from here."""

    BRIEF_PARSED = "brief_parsed"
    GENERATION = "generation"
    RETOPO = "retopo"
    UVUNWRAP = "uvunwrap"
    MATERIALS = "materials"
    STYLE_REVIEW = "style_review"
    LOD = "lod"
    SNAP_GRID = "snap_grid"
    EXPORT = "export"
    PREVIEWS = "previews"
    MANIFEST = "manifest"
    SHOWROOM = "showroom"
    COMPLETE = "complete"


class Outcome(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


class StyleSpec(BaseModel):
    """Style anchor for a pack. Drives consistency enforcement."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_image: str | None = None
    reference_description: str = ""
    generation_seed: int = 42
    palette: tuple[str, ...] = Field(default_factory=tuple)
    polygon_count_band: tuple[int, int] = (800, 2500)
    texel_density_px_per_unit: int = 512
    material_complexity: Literal["low_poly_flat", "stylized_pbr", "photoreal"] = "low_poly_flat"
    shading: Literal["faceted", "smooth", "mixed"] = "faceted"
    uv_strategy: Literal[
        "smart_project", "seam_hint_llm", "box_project", "trim_sheet", "manual_seams"
    ] = "smart_project"

    @field_validator("palette")
    @classmethod
    def palette_is_hex_colors(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        for color in v:
            if not (color.startswith("#") and len(color) == 7):
                raise ValueError(f"palette entry must be #RRGGBB, got {color!r}")
        return v


class GridSpec(BaseModel):
    """Snap-grid spec for modular assembly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    preset: Literal["synty_polygon", "dungeon_tile", "voxel_micro", "archviz", "custom"] = (
        "synty_polygon"
    )
    grid_unit_meters: float = 1.0
    snap_pivot_to: Literal["base_center", "bbox_min", "mass_center"] = "base_center"
    snap_rotation_to_axes: bool = True
    normalize_scale: bool = True
    target_unit_height_meters: float | None = None


class Piece(BaseModel):
    """One asset piece in a pack."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    category: str
    prompt: str

    @field_validator("id")
    @classmethod
    def id_is_slug(cls, v: str) -> str:
        if not v or " " in v or not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"piece id must be a snake_case slug (a-z0-9_-), got {v!r}"
            )
        return v


class GenerationConfig(BaseModel):
    """Generation routing for a pack."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    primary_routes: tuple[str, ...] = ("fal-trellis", "fal-triposr")
    hero_routes: tuple[str, ...] = ("fal-hunyuan3d-21",)
    fallback_routes: tuple[str, ...] = ("triposr-local", "trellis-hf")
    max_retries_per_piece: int = 3
    estimated_cloud_cost_usd: float | None = None
    pre_prompt_style_prefix: str = ""


class PricingConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    launch_usd: float
    normal_usd: float
    launch_window_days: int = 14


class AiDisclosure(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    models_used: tuple[str, ...]
    human_review: str
    commercial_use_verified: bool


class DemoScene(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    description: str


class Brief(BaseModel):
    """A pack brief loaded from brief.yaml."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    description: str
    style: StyleSpec
    grid: GridSpec
    pieces: tuple[Piece, ...]
    generation: GenerationConfig
    exports: tuple[str, ...]
    marketplaces: tuple[str, ...]
    demo_scenes: tuple[DemoScene, ...] = ()
    pricing: PricingConfig
    ai_disclosure: AiDisclosure
    hero_piece_ids: tuple[str, ...] = ()

    @field_validator("pieces")
    @classmethod
    def pieces_have_unique_ids(cls, v: tuple[Piece, ...]) -> tuple[Piece, ...]:
        seen: set[str] = set()
        for p in v:
            if p.id in seen:
                raise ValueError(f"duplicate piece id: {p.id}")
            seen.add(p.id)
        if not v:
            raise ValueError("pieces must be non-empty")
        return v

    def piece_by_id(self, piece_id: str) -> Piece | None:
        for p in self.pieces:
            if p.id == piece_id:
                return p
        return None

    def is_hero(self, piece_id: str) -> bool:
        return piece_id in self.hero_piece_ids


class GenResult(BaseModel):
    """Result of a 3D-generation call. Returned by every route backend."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    piece_id: str
    route: str
    success: bool
    output_glb_path: Path | None = None
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Receipt(BaseModel):
    """Audit record. One per non-Safe operation. Persisted to receipts.ndjson."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    pack_id: str
    phase: Phase
    piece_id: str | None = None
    tool: str
    intent: str
    outcome: Outcome
    cost_usd: float = 0.0
    error_code: str | None = None
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
