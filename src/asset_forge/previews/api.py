"""Preview render orchestration.

Drives Blender (headless, via flax-blender-bridge) to render:
  - per-piece thumbnails: 4 angles at 512x512 each (front/back/3-4/top)
  - per-piece hero shot:  1 nice angle at 1024x1024
  - pack cover image:     hero render combining the hero pieces

The actual Cycles/Eevee work happens inside Blender via the bridge.
This module just orchestrates per-piece calls + aggregates results.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths
from asset_forge.common.types import Brief
from asset_forge.mcp_client.session import McpSession

_log = get_logger("previews")


@dataclass(frozen=True, slots=True)
class PreviewSettings:
    """Per-pack render settings."""

    thumbnail_size: int = 512
    thumbnail_angles: tuple[str, ...] = ("front", "back", "three_quarter", "top")
    hero_size: int = 1024
    cover_width: int = 1920
    cover_height: int = 1080
    samples: int = 64  # Cycles samples; 64 is a sane preview default
    use_eevee: bool = True  # faster default; operator can override per pack


@dataclass(frozen=True, slots=True)
class PreviewResult:
    piece_id: str
    success: bool
    hero_image: Path | None = None
    thumbnail_images: tuple[Path, ...] = ()
    duration_seconds: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PackCoverResult:
    success: bool
    cover_image: Path | None = None
    duration_seconds: float = 0.0
    error_code: str | None = None
    error_message: str | None = None


async def preview_piece(
    piece_id: str,
    input_glb: Path,
    dest_dir: Path,
    *,
    settings: PreviewSettings | None = None,
    session: McpSession,
) -> PreviewResult:
    """Render thumbnails + hero shot for one piece. NEVER raises."""
    start = time.monotonic()
    cfg = settings or PreviewSettings()
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not input_glb.exists():
        return PreviewResult(
            piece_id=piece_id,
            success=False,
            error_code="input_missing",
            error_message=f"{input_glb} not found",
        )

    piece_dir = dest_dir / piece_id
    piece_dir.mkdir(parents=True, exist_ok=True)
    hero_path = piece_dir / "hero.png"
    thumb_paths: list[Path] = []

    try:
        result = await session.call(
            "blender_bridge/render_piece",
            {
                "inputPath": str(input_glb),
                "outputDir": str(piece_dir),
                "thumbnailSize": cfg.thumbnail_size,
                "thumbnailAngles": list(cfg.thumbnail_angles),
                "heroSize": cfg.hero_size,
                "samples": cfg.samples,
                "useEevee": cfg.use_eevee,
            },
            intent=f"asset-forge preview piece={piece_id}",
        )
    except Exception as e:
        return PreviewResult(
            piece_id=piece_id,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="mcp_error",
            error_message=str(e),
        )

    # Bridge writes files; we trust filesystem for the canonical list.
    if hero_path.exists():
        pass  # ok
    else:
        return PreviewResult(
            piece_id=piece_id,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="hero_missing",
            error_message=f"Blender bridge returned success but {hero_path} missing",
        )

    for angle in cfg.thumbnail_angles:
        path = piece_dir / f"thumb_{angle}.png"
        if path.exists():
            thumb_paths.append(path)

    return PreviewResult(
        piece_id=piece_id,
        success=True,
        hero_image=hero_path,
        thumbnail_images=tuple(thumb_paths),
        duration_seconds=time.monotonic() - start,
        metadata=result if isinstance(result, dict) else {},
    )


async def _build_cover_image(
    paths: PackPaths,
    brief: Brief,
    *,
    settings: PreviewSettings,
    session: McpSession,
) -> PackCoverResult:
    """Compose a pack cover from the hero pieces."""
    start = time.monotonic()
    if not brief.hero_piece_ids:
        return PackCoverResult(
            success=False,
            error_code="no_hero_pieces",
            error_message="brief.hero_piece_ids is empty; can't build cover",
        )

    hero_glbs: list[Path] = []
    for hero_id in brief.hero_piece_ids:
        # Prefer LOD output (smaller); fall back to final_dir.
        candidates = (paths.lods_dir / f"{hero_id}.glb", paths.final_dir / f"{hero_id}.glb")
        for c in candidates:
            if c.exists():
                hero_glbs.append(c)
                break

    if not hero_glbs:
        return PackCoverResult(
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="hero_glbs_missing",
            error_message="No hero piece GLBs available for cover composition",
        )

    cover_path = paths.previews_dir / "cover.png"
    paths.previews_dir.mkdir(parents=True, exist_ok=True)

    try:
        await session.call(
            "blender_bridge/render_cover",
            {
                "heroGlbs": [str(p) for p in hero_glbs],
                "outputPath": str(cover_path),
                "width": settings.cover_width,
                "height": settings.cover_height,
                "samples": settings.samples,
                "useEevee": settings.use_eevee,
                "packTitle": brief.title,
            },
            intent=f"asset-forge preview cover pack={brief.id}",
        )
    except Exception as e:
        return PackCoverResult(
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="mcp_error",
            error_message=str(e),
        )

    if not cover_path.exists():
        return PackCoverResult(
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="cover_missing",
            error_message=f"Blender bridge returned success but {cover_path} missing",
        )

    return PackCoverResult(
        success=True,
        cover_image=cover_path,
        duration_seconds=time.monotonic() - start,
    )


async def preview_pack(
    paths: PackPaths,
    brief: Brief,
    *,
    pieces_succeeded: list[str],
    settings: PreviewSettings | None = None,
    session: McpSession,
) -> dict[str, PreviewResult]:
    """Render all pieces + the cover image. Returns dict of per-piece results.

    The cover-image result is folded into the metadata under key '__cover__'.
    """
    cfg = settings or PreviewSettings()
    paths.previews_dir.mkdir(parents=True, exist_ok=True)

    # Prefer LODs (smaller, faster to render). Fall back through the chain.
    source_dirs = (
        paths.lods_dir,
        paths.final_dir,
        paths.materials_dir,
        paths.uv_dir,
        paths.retopo_dir,
    )

    results: dict[str, PreviewResult] = {}
    for piece_id in pieces_succeeded:
        if brief.piece_by_id(piece_id) is None:
            continue

        input_glb: Path | None = None
        for src in source_dirs:
            candidate = src / f"{piece_id}.glb"
            if candidate.exists():
                input_glb = candidate
                break

        if input_glb is None:
            results[piece_id] = PreviewResult(
                piece_id=piece_id,
                success=False,
                error_code="input_missing",
                error_message=f"no upstream GLB for piece {piece_id}",
            )
            continue

        results[piece_id] = await preview_piece(
            piece_id=piece_id,
            input_glb=input_glb,
            dest_dir=paths.previews_dir,
            settings=cfg,
            session=session,
        )

    # Build the pack cover (separate concern; failures don't fail the phase)
    cover = await _build_cover_image(paths, brief, settings=cfg, session=session)
    results["__cover__"] = PreviewResult(
        piece_id="__cover__",
        success=cover.success,
        hero_image=cover.cover_image,
        duration_seconds=cover.duration_seconds,
        error_code=cover.error_code,
        error_message=cover.error_message,
    )

    return results
