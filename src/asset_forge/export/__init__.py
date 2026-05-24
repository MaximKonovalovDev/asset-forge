"""export \u2014 per-engine bundlers.

Public surface:
    export_pack(pack_paths, brief, pieces_succeeded) -> ExportResult

Per-engine bundlers:
    UnityExporter   .unitypackage tar bundle with .meta files
    UnrealExporter  .uasset references inside a .uplugin zip
    GodotExporter   project skeleton + .glb references in .zip
    MasterGlbExporter  raw GLB master (engine-agnostic)
"""

from __future__ import annotations

from .api import (
    EnginePackage,
    EngineTarget,
    ExportResult,
    export_pack,
)

__all__ = [
    "EnginePackage",
    "EngineTarget",
    "ExportResult",
    "export_pack",
]
