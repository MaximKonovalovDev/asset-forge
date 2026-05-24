"""manifest \u2014 marketplace submission bundle generation.

Public surface:
    build_manifests(pack_paths, brief, targets) -> ManifestResult
    ai_disclosure_text(brief) -> str
    pack_readme(brief) -> str
"""

from __future__ import annotations

from .api import ManifestResult, Target, build_manifests
from .templates import ai_disclosure_text, license_text, pack_readme

__all__ = [
    "ManifestResult",
    "Target",
    "ai_disclosure_text",
    "build_manifests",
    "license_text",
    "pack_readme",
]
