"""Shared helpers for engine builders."""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BuilderOutput:
    """What every per-engine builder returns to api.export_pack()."""

    bundle_path: Path  # directory containing the bundle (browseable)
    archive_path: Path  # the .zip/.unitypackage/etc. ready to upload
    file_count: int
    size_bytes: int


def reset_dir(d: Path) -> None:
    """Wipe + recreate a directory."""
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_file(src: Path, dst: Path) -> int:
    """Copy src to dst, creating parents. Returns bytes copied."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst.stat().st_size


def zip_directory(src_dir: Path, archive: Path) -> tuple[int, int]:
    """Zip src_dir into archive. Returns (file_count, total_bytes)."""
    if archive.exists():
        archive.unlink()
    archive.parent.mkdir(parents=True, exist_ok=True)
    files = 0
    total = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in src_dir.rglob("*"):
            if path.is_file():
                arcname = path.relative_to(src_dir.parent)
                zf.write(path, arcname=arcname)
                files += 1
                total += path.stat().st_size
    return files, total
