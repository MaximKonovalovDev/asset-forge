"""Typed exception hierarchy.

Rule: every exception that crosses a phase boundary derives from
AssetForgeError. Subsystem-local exceptions can be plain.
"""

from __future__ import annotations


class AssetForgeError(Exception):
    """Base for all asset-forge errors. Carries an optional code for receipt logging."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code or self.__class__.__name__


class BriefValidationError(AssetForgeError):
    """brief.yaml failed schema or semantic validation."""


class McpCallError(AssetForgeError):
    """flax-mcp tool call returned an error or the bridge was unreachable."""

    def __init__(self, message: str, *, tool: str | None = None, code: str | None = None) -> None:
        super().__init__(message, code=code)
        self.tool = tool


class GenerationError(AssetForgeError):
    """A 3D-generation route failed for a specific piece."""

    def __init__(self, message: str, *, piece_id: str, route: str) -> None:
        super().__init__(message, code="generation_failed")
        self.piece_id = piece_id
        self.route = route


class RouteUnavailable(AssetForgeError):
    """A generation route is configured but not reachable (no API key, no GPU, etc)."""

    def __init__(self, route: str, reason: str) -> None:
        super().__init__(f"route {route} unavailable: {reason}", code="route_unavailable")
        self.route = route
        self.reason = reason


class PhaseFailed(AssetForgeError):
    """A pipeline phase failed; the orchestrator caught it and checkpointed."""

    def __init__(self, phase: str, message: str) -> None:
        super().__init__(f"phase {phase} failed: {message}", code="phase_failed")
        self.phase = phase


class StyleOutlier(AssetForgeError):
    """A piece failed the style-consistency gate and is queued for regen."""

    def __init__(self, piece_id: str, score: float, threshold: float) -> None:
        super().__init__(
            f"piece {piece_id} style score {score:.3f} below threshold {threshold:.3f}",
            code="style_outlier",
        )
        self.piece_id = piece_id
        self.score = score
        self.threshold = threshold
