"""Material assignment.

Per-piece pipeline:
  1. Look up library entries matching the piece's category.
  2. Score each candidate by palette proximity (base_color vs pack
     palette) and prompt-keyword match (brief.style + piece.prompt).
  3. Pick the highest-scoring candidate. Tie-break by stable hash so
     re-runs give the same answer.
  4. Apply the chosen material via flax-blender-bridge's
     `blender_bridge/assign_material` tool: takes inputPath GLB +
     material spec + outputPath. NEVER raises; returns MaterialResult.

We don't synthesize new materials at runtime \u2014 we pick from a curated
library. That's the simple, predictable, debug-able move.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path

from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths
from asset_forge.common.types import Brief, Piece
from asset_forge.mcp_client.session import McpSession

from .library import (
    MATERIAL_LIBRARY,
    MaterialEntry,
    find_materials_for_category,
)

_log = get_logger("materials")


@dataclass(frozen=True, slots=True)
class MaterialChoice:
    """Why we picked this material for this piece."""

    piece_id: str
    material_id: str
    material_name: str
    score: float
    reason: str


@dataclass(frozen=True, slots=True)
class MaterialResult:
    piece_id: str
    success: bool
    output_glb: Path | None = None
    choice: MaterialChoice | None = None
    duration_seconds: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _color_distance(a_hex: str, b_hex: str) -> float:
    """Euclidean distance in sRGB. Lower = more similar."""
    ar, ag, ab = _hex_to_rgb(a_hex)
    br, bg, bb = _hex_to_rgb(b_hex)
    return float(((ar - br) ** 2 + (ag - bg) ** 2 + (ab - bb) ** 2) ** 0.5)


def _palette_match_score(material: MaterialEntry, palette: tuple[str, ...]) -> float:
    """0..1; higher = closer to some palette color."""
    if not palette:
        return 0.5  # neutral when no palette is defined
    best_distance = min(_color_distance(material.base_color, p) for p in palette)
    # Max possible euclidean distance in sRGB ~ 441.7 (black to white).
    normalized = 1.0 - min(best_distance / 441.7, 1.0)
    return normalized


def _keyword_match_score(material: MaterialEntry, piece: Piece, brief: Brief) -> float:
    """0..1; based on keyword overlap with the piece's prompt + brief style."""
    text = f"{piece.prompt} {brief.style.reference_description}".lower()
    matches = 0
    total = 0
    for tag in material.style_tags:
        total += 1
        if tag.lower() in text:
            matches += 1
    # Also reward direct name hits ("iron" in prompt matches iron material)
    if material.name.lower() in text or material.id.lower().replace("_", " ") in text:
        matches += 2
    total += 2
    if total == 0:
        return 0.5
    return min(matches / total, 1.0)


def _stable_tiebreak(material_id: str, piece_id: str) -> float:
    """Deterministic tie-break in [0, 0.001) based on hash. Keeps re-runs stable."""
    h = hashlib.md5(f"{material_id}::{piece_id}".encode()).hexdigest()
    return int(h[:8], 16) / (16**8) * 0.001


def _pick_material(
    piece: Piece, brief: Brief
) -> MaterialChoice:
    """Choose the best library material for this piece. Always returns a choice
    (falls back to generic_grey if nothing matches)."""
    candidates = find_materials_for_category(piece.category)
    if not candidates:
        candidates = MATERIAL_LIBRARY  # nothing category-matched; consider all

    scored: list[tuple[float, MaterialEntry, str]] = []
    palette = brief.style.palette

    for mat in candidates:
        palette_score = _palette_match_score(mat, palette)
        keyword_score = _keyword_match_score(mat, piece, brief)
        # 70% palette, 30% keyword. Palette consistency is the moat.
        score = (palette_score * 0.7) + (keyword_score * 0.3)
        score += _stable_tiebreak(mat.id, piece.id)
        reason = (
            f"palette={palette_score:.2f} keyword={keyword_score:.2f}"
        )
        scored.append((score, mat, reason))

    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best_mat, best_reason = scored[0]
    return MaterialChoice(
        piece_id=piece.id,
        material_id=best_mat.id,
        material_name=best_mat.name,
        score=round(best_score, 4),
        reason=best_reason,
    )


async def assign_piece_material(
    piece: Piece,
    brief: Brief,
    input_glb: Path,
    output_glb: Path,
    *,
    session: McpSession,
) -> MaterialResult:
    """Choose + assign a material for one piece. NEVER raises."""
    start = time.monotonic()

    if not input_glb.exists():
        return MaterialResult(
            piece_id=piece.id,
            success=False,
            error_code="input_missing",
            error_message=f"{input_glb} not found",
        )

    choice = _pick_material(piece, brief)
    material = next((m for m in MATERIAL_LIBRARY if m.id == choice.material_id), None)
    if material is None:
        return MaterialResult(
            piece_id=piece.id,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="material_not_found",
            error_message=f"material {choice.material_id} missing from library",
        )

    try:
        await session.call(
            "blender_bridge/assign_material",
            {
                "inputPath": str(input_glb),
                "outputPath": str(output_glb),
                "materialName": material.name,
                "baseColor": material.base_color,
                "roughness": material.roughness,
                "metallic": material.metallic,
                "extraParams": material.extra_params,
            },
            intent=f"asset-forge material piece={piece.id} material={material.id}",
        )
    except Exception as e:
        return MaterialResult(
            piece_id=piece.id,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="mcp_error",
            error_message=str(e),
            choice=choice,
        )

    if not output_glb.exists():
        return MaterialResult(
            piece_id=piece.id,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="output_missing",
            error_message="Blender bridge returned success but output missing",
            choice=choice,
        )

    return MaterialResult(
        piece_id=piece.id,
        success=True,
        output_glb=output_glb,
        choice=choice,
        duration_seconds=time.monotonic() - start,
    )


async def assign_pack_materials(
    paths: PackPaths,
    brief: Brief,
    *,
    pieces_succeeded: list[str],
    session: McpSession,
) -> dict[str, MaterialResult]:
    """Assign materials to every UV-unwrapped piece. Writes to materials_dir."""
    paths.materials_dir.mkdir(parents=True, exist_ok=True)

    source_dirs = (paths.uv_dir, paths.retopo_dir, paths.raw_dir)

    results: dict[str, MaterialResult] = {}
    for piece_id in pieces_succeeded:
        piece = brief.piece_by_id(piece_id)
        if piece is None:
            continue

        input_glb: Path | None = None
        for src in source_dirs:
            candidate = src / f"{piece_id}.glb"
            if candidate.exists():
                input_glb = candidate
                break

        if input_glb is None:
            results[piece_id] = MaterialResult(
                piece_id=piece_id,
                success=False,
                error_code="input_missing",
                error_message=f"no upstream GLB for {piece_id}",
            )
            continue

        output_glb = paths.materials_dir / f"{piece_id}.glb"
        results[piece_id] = await assign_piece_material(
            piece, brief, input_glb, output_glb, session=session
        )
        choice = results[piece_id].choice
        if choice is not None:
            _log.info(
                "material.assigned",
                piece=piece_id,
                material=choice.material_id,
                score=choice.score,
            )

    return results
