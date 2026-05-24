"""manifest public API. Builds per-marketplace submission bundles."""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from asset_forge.common.logging import get_logger
from asset_forge.common.paths import PackPaths
from asset_forge.common.types import Brief

from .templates import ai_disclosure_text, license_text, pack_readme

_log = get_logger("manifest")


class Target(StrEnum):
    FAB = "fab"
    UNITY = "unity"
    ITCHIO = "itchio"
    GUMROAD = "gumroad"


@dataclass(frozen=True, slots=True)
class ManifestBundle:
    target: Target
    bundle_path: Path
    files_included: int
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ManifestResult:
    pack_id: str
    bundles: tuple[ManifestBundle, ...] = ()
    failures: tuple[tuple[Target, str], ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


def _supports_target(brief: Brief, target: Target) -> bool:
    return target.value in brief.marketplaces


async def build_manifests(
    paths: PackPaths,
    brief: Brief,
    *,
    targets: tuple[Target, ...] | None = None,
) -> ManifestResult:
    """Build per-marketplace submission bundles.

    For day-2 the bundle is a directory tree + a zip alongside it. The
    directory is what the operator browses; the zip is what they upload.
    """
    if targets is None:
        targets = tuple(Target(t) for t in brief.marketplaces if t in Target.__members__.values() or t in {m.value for m in Target})

    paths.manifests_root.mkdir(parents=True, exist_ok=True)

    bundles: list[ManifestBundle] = []
    failures: list[tuple[Target, str]] = []

    readme = pack_readme(brief)
    license_blob = license_text(brief)
    ai_disclosure = ai_disclosure_text(brief)

    for target in targets:
        if not _supports_target(brief, target):
            _log.info("manifest.skip_target", target=target.value, pack=brief.id)
            continue
        target_dir = paths.manifest_dir(target.value)
        try:
            bundle = _build_one_bundle(
                target=target,
                target_dir=target_dir,
                paths=paths,
                brief=brief,
                readme=readme,
                license_blob=license_blob,
                ai_disclosure=ai_disclosure,
            )
            bundles.append(bundle)
        except Exception as e:
            _log.error("manifest.failed", target=target.value, error=str(e))
            failures.append((target, str(e)))

    return ManifestResult(
        pack_id=brief.id,
        bundles=tuple(bundles),
        failures=tuple(failures),
    )


def _build_one_bundle(
    target: Target,
    target_dir: Path,
    paths: PackPaths,
    brief: Brief,
    readme: str,
    license_blob: str,
    ai_disclosure: str,
) -> ManifestBundle:
    """Build a single marketplace bundle. Synchronous; per-target IO."""
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write text artifacts
    (target_dir / "README.md").write_text(readme, encoding="utf-8")
    (target_dir / "license.txt").write_text(license_blob, encoding="utf-8")
    (target_dir / "ai_disclosure.txt").write_text(ai_disclosure, encoding="utf-8")

    # 2. Copy engine-specific export directories that exist
    assets_dir = target_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    engine_export_map = {
        "unity": paths.unity_export_dir,
        "unreal": paths.unreal_export_dir,
        "godot": paths.godot_export_dir,
        "master_glb": paths.master_export_dir,
    }
    for engine in brief.exports:
        src = engine_export_map.get(engine)
        if src is None or not src.exists() or not any(src.iterdir()):
            # Day-2: export phase may not have run yet; skip silently
            continue
        dst = assets_dir / engine
        shutil.copytree(src, dst, dirs_exist_ok=True)

    # 3. Copy previews if available
    if paths.previews_dir.exists() and any(paths.previews_dir.iterdir()):
        shutil.copytree(paths.previews_dir, target_dir / "previews", dirs_exist_ok=True)

    # 4. Per-target description file (markdown for upload form)
    description = _per_target_description(target, brief)
    (target_dir / f"{target.value}_description.md").write_text(description, encoding="utf-8")

    # 5. Zip everything for easy upload
    zip_path = target_dir.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    files_count = 0
    total_bytes = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in target_dir.rglob("*"):
            if path.is_file():
                arcname = path.relative_to(target_dir.parent)
                zf.write(path, arcname=arcname)
                files_count += 1
                total_bytes += path.stat().st_size

    return ManifestBundle(
        target=target,
        bundle_path=zip_path,
        files_included=files_count,
        size_bytes=total_bytes,
    )


def _per_target_description(target: Target, brief: Brief) -> str:
    """Marketplace-specific description text (operator pastes into upload form)."""
    if target is Target.FAB:
        return (
            f"# {brief.title}\n\n"
            f"{brief.description.strip()}\n\n"
            f"- {len(brief.pieces)} pieces\n"
            f"- Engine support: {', '.join(brief.exports)}\n"
            f"- Style: {brief.style.reference_description}\n\n"
            "AI-assisted creation; see `ai_disclosure.txt` in the package.\n"
        )
    if target is Target.UNITY:
        # Unity Asset Store requires explicit AI declaration in the description.
        return (
            f"# {brief.title}\n\n"
            f"{brief.description.strip()}\n\n"
            "**AI disclosure:** This pack contains assets created with AI assistance. "
            f"Models used: {', '.join(brief.ai_disclosure.models_used)}. "
            "All pieces reviewed and curated by a human; topology, UVs, "
            "and materials hand-validated.\n\n"
            f"- {len(brief.pieces)} pieces\n"
            f"- Polygon band: {brief.style.polygon_count_band[0]}-{brief.style.polygon_count_band[1]}\n"
            f"- Texel density: {brief.style.texel_density_px_per_unit} px/unit\n"
        )
    if target is Target.ITCHIO:
        return (
            f"# {brief.title}\n\n"
            f"{brief.description.strip()}\n\n"
            "Drop-in modular pack for indie game devs. Cross-engine "
            "(Unity/Unreal/Godot). AI-assisted, human-curated.\n\n"
            f"**Launch price:** ${brief.pricing.launch_usd} for "
            f"{brief.pricing.launch_window_days} days\n"
            f"**Normal price:** ${brief.pricing.normal_usd}\n"
        )
    if target is Target.GUMROAD:
        return (
            f"# {brief.title}\n\n"
            f"{brief.description.strip()}\n\n"
            "Buy once, use forever. Multi-engine support included.\n\n"
            f"Includes: {len(brief.pieces)} pieces, demo scenes per engine, "
            "license + AI disclosure.\n"
        )
    return f"# {brief.title}\n\n{brief.description}\n"
