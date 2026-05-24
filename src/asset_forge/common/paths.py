"""Output path conventions per pack.

The canonical layout:

    out/<pack-id>/
        .state.json
        raw/                 text-to-3D outputs
        retopo/              after retopology
        uv/                  after UV unwrap
        materials/           after material assignment
        final/               after style + snap_grid normalization
        lods/                with LOD chains
        exports/
            unity/
            unreal/
            godot/
            master/
        previews/            Blender renders
        manifests/
            fab/
            unity/
            itchio/
            gumroad/
        receipts.ndjson
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .settings import get_settings


@dataclass(frozen=True, slots=True)
class PackPaths:
    """All paths a pack uses, derived from pack_id + output root."""

    pack_id: str
    root: Path

    @property
    def state_file(self) -> Path:
        return self.root / ".state.json"

    @property
    def receipts_file(self) -> Path:
        return self.root / "receipts.ndjson"

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def retopo_dir(self) -> Path:
        return self.root / "retopo"

    @property
    def uv_dir(self) -> Path:
        return self.root / "uv"

    @property
    def materials_dir(self) -> Path:
        return self.root / "materials"

    @property
    def final_dir(self) -> Path:
        return self.root / "final"

    @property
    def lods_dir(self) -> Path:
        return self.root / "lods"

    @property
    def exports_root(self) -> Path:
        return self.root / "exports"

    @property
    def unity_export_dir(self) -> Path:
        return self.exports_root / "unity"

    @property
    def unreal_export_dir(self) -> Path:
        return self.exports_root / "unreal"

    @property
    def godot_export_dir(self) -> Path:
        return self.exports_root / "godot"

    @property
    def master_export_dir(self) -> Path:
        return self.exports_root / "master"

    @property
    def previews_dir(self) -> Path:
        return self.root / "previews"

    @property
    def manifests_root(self) -> Path:
        return self.root / "manifests"

    def manifest_dir(self, target: str) -> Path:
        return self.manifests_root / target

    def ensure(self) -> None:
        """Create all directories. Idempotent."""
        for d in (
            self.root,
            self.raw_dir,
            self.retopo_dir,
            self.uv_dir,
            self.materials_dir,
            self.final_dir,
            self.lods_dir,
            self.exports_root,
            self.unity_export_dir,
            self.unreal_export_dir,
            self.godot_export_dir,
            self.master_export_dir,
            self.previews_dir,
            self.manifests_root,
        ):
            d.mkdir(parents=True, exist_ok=True)


def pack_paths_for(pack_id: str, output_root: Path | None = None) -> PackPaths:
    """Build PackPaths for a pack id under the configured output root."""
    root = (output_root or get_settings().output_root) / pack_id
    return PackPaths(pack_id=pack_id, root=root)
