"""Shared types, settings, paths, logging, errors. No IO at import time."""

from __future__ import annotations

from .errors import (
    AssetForgeError,
    BriefValidationError,
    GenerationError,
    McpCallError,
    PhaseFailed,
    RouteUnavailable,
    StyleOutlier,
)
from .logging import get_logger, setup_logging
from .paths import (
    PackPaths,
    pack_paths_for,
)
from .settings import Settings, get_settings
from .types import (
    Brief,
    GenResult,
    GridSpec,
    Outcome,
    Phase,
    Piece,
    Receipt,
    StyleSpec,
)

__all__ = [
    "AssetForgeError",
    "Brief",
    "BriefValidationError",
    "GenResult",
    "GenerationError",
    "GridSpec",
    "McpCallError",
    "Outcome",
    "PackPaths",
    "Phase",
    "PhaseFailed",
    "Piece",
    "Receipt",
    "RouteUnavailable",
    "Settings",
    "StyleOutlier",
    "StyleSpec",
    "get_logger",
    "get_settings",
    "pack_paths_for",
    "setup_logging",
]
