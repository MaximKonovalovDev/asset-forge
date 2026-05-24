"""structlog setup. Rich console for dev; JSON for prod."""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.typing import Processor


def setup_logging(level: str = "INFO", json: bool = False) -> None:
    """Configure structlog. Call once at process startup."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
    )
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    if json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
