"""Showroom static-site generator.

Builds a per-pack landing page + per-piece pages with three.js GLB
viewer. No backend dependencies; the output is plain HTML/CSS/JS that
can deploy to Cloudflare Pages, Vercel, GitHub Pages, or any static
host.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths
from asset_forge.common.types import Brief
from asset_forge.snap_grid import canonical_piece_name

_log = get_logger("showroom")

_TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True, slots=True)
class SiteConfig:
    output_dir: Path | None = None  # defaults to <pack_root>/showroom/
    marketplace_links: dict[str, str] = field(default_factory=dict)
    include_glb_in_site: bool = True  # copy GLBs into showroom for the viewer


@dataclass(frozen=True, slots=True)
class ShowroomResult:
    pack_id: str
    success: bool
    site_root: Path | None = None
    pages_generated: int = 0
    assets_total_mb: float = 0.0
    duration_seconds: float = 0.0
    error_code: str | None = None
    error_message: str | None = None


def _resolve_source_glb(paths: PackPaths, piece_id: str) -> Path | None:
    for src in (
        paths.lods_dir,
        paths.final_dir,
        paths.materials_dir,
        paths.uv_dir,
        paths.retopo_dir,
        paths.raw_dir,
    ):
        candidate = src / f"{piece_id}.glb"
        if candidate.exists():
            return candidate
    return None


def _resolve_preview_image(paths: PackPaths, piece_id: str, kind: str = "hero") -> Path | None:
    """Find a piece's preview image. kind = 'hero' or 'thumb_<angle>'."""
    candidate = paths.previews_dir / piece_id / f"{kind}.png"
    return candidate if candidate.exists() else None


def _list_thumbnails(paths: PackPaths, piece_id: str) -> list[Path]:
    piece_dir = paths.previews_dir / piece_id
    if not piece_dir.exists():
        return []
    return sorted(p for p in piece_dir.glob("thumb_*.png"))


async def build_site(
    paths: PackPaths,
    brief: Brief,
    *,
    pieces_succeeded: list[str],
    config: SiteConfig | None = None,
) -> ShowroomResult:
    """Build the static site. NEVER raises; returns ShowroomResult."""
    cfg = config or SiteConfig()
    start = time.monotonic()
    site_root = cfg.output_dir or (paths.root / "showroom")

    try:
        if site_root.exists():
            shutil.rmtree(site_root)
        site_root.mkdir(parents=True, exist_ok=True)
        (site_root / "assets").mkdir(exist_ok=True)
        (site_root / "pieces").mkdir(exist_ok=True)
        (site_root / "glbs").mkdir(exist_ok=True)
        (site_root / "previews").mkdir(exist_ok=True)
    except OSError as e:
        return ShowroomResult(
            pack_id=brief.id,
            success=False,
            duration_seconds=time.monotonic() - start,
            error_code="output_dir_error",
            error_message=str(e),
        )

    # Copy CSS
    shutil.copy2(_TEMPLATE_DIR / "style.css", site_root / "assets" / "style.css")

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        keep_trailing_newline=True,
    )

    # Collect per-piece data
    pieces_view: list[dict[str, object]] = []
    pieces_by_category: dict[str, list[dict[str, object]]] = {}
    total_bytes = 0
    pages = 0

    cover_relative: str | None = None
    cover_src = paths.previews_dir / "cover.png"
    if cover_src.exists():
        cover_dst = site_root / "previews" / "cover.png"
        shutil.copy2(cover_src, cover_dst)
        cover_relative = "previews/cover.png"
        total_bytes += cover_dst.stat().st_size

    for piece_id in pieces_succeeded:
        piece = brief.piece_by_id(piece_id)
        if piece is None:
            continue

        canonical = canonical_piece_name(
            pack_id=brief.id, category=piece.category, piece_id=piece_id, lod=0
        )

        # Copy hero image if present
        hero_src = _resolve_preview_image(paths, piece_id, "hero")
        hero_relative: str | None = None
        if hero_src is not None:
            hero_dst = site_root / "previews" / piece_id / "hero.png"
            hero_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(hero_src, hero_dst)
            hero_relative = f"previews/{piece_id}/hero.png"
            total_bytes += hero_dst.stat().st_size

        # Copy thumbnails
        thumbs_relative: list[str] = []
        for thumb in _list_thumbnails(paths, piece_id):
            thumb_dst = site_root / "previews" / piece_id / thumb.name
            thumb_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(thumb, thumb_dst)
            thumbs_relative.append(f"previews/{piece_id}/{thumb.name}")
            total_bytes += thumb_dst.stat().st_size

        # Copy the GLB for the viewer
        glb_relative: str | None = None
        if cfg.include_glb_in_site:
            source_glb = _resolve_source_glb(paths, piece_id)
            if source_glb is not None:
                glb_dst = site_root / "glbs" / f"{piece_id}.glb"
                shutil.copy2(source_glb, glb_dst)
                glb_relative = f"glbs/{piece_id}.glb"
                total_bytes += glb_dst.stat().st_size

        view: dict[str, object] = {
            "id": piece_id,
            "category": piece.category,
            "prompt": piece.prompt,
            "hero_image": hero_relative,
            "thumbnails": thumbs_relative,
            "canonical_name": canonical,
            "glb_relative_path": glb_relative,
        }
        pieces_view.append(view)
        pieces_by_category.setdefault(piece.category, []).append(view)

        # Per-piece page
        if glb_relative:  # only render piece page if we have a GLB to show
            piece_template = env.get_template("piece.html.j2")
            piece_html = piece_template.render(
                brief=brief,
                piece=piece,
                canonical_name=canonical,
                glb_relative_path=glb_relative,
                thumbnail_images=thumbs_relative,
            )
            (site_root / "pieces" / f"{piece_id}.html").write_text(
                piece_html, encoding="utf-8"
            )
            pages += 1

    # Index page
    index_template = env.get_template("index.html.j2")
    index_html = index_template.render(
        brief=brief,
        pieces=pieces_view,
        pieces_by_category=pieces_by_category,
        categories=list(pieces_by_category.keys()),
        cover_image=cover_relative,
        marketplace_links=cfg.marketplace_links,
    )
    (site_root / "index.html").write_text(index_html, encoding="utf-8")
    pages += 1
    total_bytes += (site_root / "index.html").stat().st_size

    _log.info(
        "showroom.built", pack=brief.id, pages=pages, size_mb=total_bytes // (1024 * 1024)
    )

    return ShowroomResult(
        pack_id=brief.id,
        success=True,
        site_root=site_root,
        pages_generated=pages,
        assets_total_mb=round(total_bytes / (1024 * 1024), 2),
        duration_seconds=time.monotonic() - start,
    )
