"""mcp_client — talks to flax-mcp + multi-backend generation routing."""

from __future__ import annotations

from .backends import (
    Backend,
    BackendRegistry,
    FalAiBackend,
    KaggleBatchBackend,
    LocalMcpBackend,
)
from .session import McpSession

__all__ = [
    "Backend",
    "BackendRegistry",
    "FalAiBackend",
    "KaggleBatchBackend",
    "LocalMcpBackend",
    "McpSession",
]
