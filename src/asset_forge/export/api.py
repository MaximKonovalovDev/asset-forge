"""Per-engine export public API.

The orchestrator calls export_pack once; each requested engine target
gets bundled. NEVER raises on per-engine failure; returns ExportResult
with success bool per engine.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths
from asset_forge.common.types import Brief
from asset_forge.snap_grid import canonical_piece_name

from .godot import build_godot_bundle
from .master_glb import build_master_glb_bundle
from .unity import build_unity_package
from .unreal import build_unreal_bundle

_log = get_logger("export")


class EngineTarget(StrEnum):
    UNITY = "unity"
    UNREAL = "unreal"
    GODOT = "godot"
    MASTER_GLB = "master_glb"


@dataclass(frozen=True, slots=True)
class EnginePackage:
    """One engine's bundled output."""

    target: EngineTarget
    bundle_path: Path  # the directory containing the bundle
    archive_path: Path  # the .zip/.unitypackage/etc. ready to upload
    file_count: int
    size_bytes: int
    canonical_names: tuple[str, ...] = ()
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class ExportResult:
    pack_id: str
    packages: tuple[EnginePackage, ...] = ()
    failures: tuple[tuple[EngineTarget, str], ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


def _resolve_source_glbs(
    paths: PackPaths,
    brief: Brief,
    pieces_succeeded: list[str],
) -> dict[str, Path]:
    """Walk the source-dir fallback chain to find the best GLB per piece.

    Prefers LOD output (smallest + LOD-bundled) and falls back through
    the pipeline output chain.
    """
    source_dirs = (
        paths.lods_dir,
        paths.final_dir,
        paths.materials_dir,
        paths.uv_dir,
        paths.retopo_dir,
        paths.raw_dir,
    )
    resolved: dict[str, Path] = {}
    for piece_id in pieces_succeeded:
        if brief.piece_by_id(piece_id) is None:
            continue
        for src in source_dirs:
            candidate = src / f"{piece_id}.glb"
            if candidate.exists():
                resolved[piece_id] = candidate
                break
    return resolved


def _build_canonical_name_map(
    brief: Brief, pieces: dict[str, Path]
) -> dict[str, str]:
    """Map piece_id -> canonical asset name (PACKPREFIX_category_piece_LOD0)."""
    name_map: dict[str, str] = {}
    for piece_id in pieces:
        piece = brief.piece_by_id(piece_id)
        if piece is None:
            continue
        name_map[piece_id] = canonical_piece_name(
            pack_id=brief.id,
            category=piece.category,
            piece_id=piece_id,
            lod=0,
        )
    return name_map


async def export_pack(
    paths: PackPaths,
    brief: Brief,
    *,
    pieces_succeeded: list[str],
    targets: tuple[EngineTarget, ...] | None = None,
) -> ExportResult:
    """Build per-engine bundles for every requested target.

    Reads GLBs from the best-available source dir; writes bundles to
    paths.exports_root/<engine>/. NEVER raises on per-engine failure.
    """
    if targets is None:
        targets = tuple(
            EngineTarget(t) for t in brief.exports if t in {e.value for e in EngineTarget}
        )
    if not targets:
        return ExportResult(pack_id=brief.id, failures=())

    paths.exports_root.mkdir(parents=True, exist_ok=True)

    source_glbs = _resolve_source_glbs(paths, brief, pieces_succeeded)
    if not source_glbs:
        return ExportResult(
            pack_id=brief.id,
            failures=tuple(
                (t, "no source GLBs found in any pipeline output dir") for t in targets
            ),
        )
    name_map = _build_canonical_name_map(brief, source_glbs)

    packages: list[EnginePackage] = []
    failures: list[tuple[EngineTarget, str]] = []

    for target in targets:
        _log.info("export.target_start", target=target.value, pieces=len(source_glbs))
        start = time.monotonic()
        try:
            if target is EngineTarget.UNITY:
                pkg = build_unity_package(
                    out_dir=paths.unity_export_dir,
                    brief=brief,
                    source_glbs=source_glbs,
                    name_map=name_map,
                )
            elif target is EngineTarget.UNREAL:
                pkg = build_unreal_bundle(
                    out_dir=paths.unreal_export_dir,
                    brief=brief,
                    source_glbs=source_glbs,
                    name_map=name_map,
                )
            elif target is EngineTarget.GODOT:
                pkg = build_godot_bundle(
                    out_dir=paths.godot_export_dir,
                    brief=brief,
                    source_glbs=source_glbs,
                    name_map=name_map,
                )
            elif target is EngineTarget.MASTER_GLB:
                pkg = build_master_glb_bundle(
                    out_dir=paths.master_export_dir,
                    brief=brief,
                    source_glbs=source_glbs,
                    name_map=name_map,
                )
            else:
                raise ValueError(f"unknown engine target: {target}")
        except Exception as e:
            _log.error("export.target_failed", target=target.value, error=str(e))
            failures.append((target, str(e)))
            continue

        duration = time.monotonic() - start
        packages.append(
            EnginePackage(
                target=target,
                bundle_path=pkg.bundle_path,
                archive_path=pkg.archive_path,
                file_count=pkg.file_count,
                size_bytes=pkg.size_bytes,
                canonical_names=tuple(name_map.values()),
                duration_seconds=duration,
            )
        )
        _log.info(
            "export.target_done",
            target=target.value,
            files=pkg.file_count,
            size_kb=pkg.size_bytes // 1024,
        )

    return ExportResult(
        pack_id=brief.id,
        packages=tuple(packages),
        failures=tuple(failures),
    )
