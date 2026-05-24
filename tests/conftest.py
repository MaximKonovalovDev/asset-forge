"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Ensure each test gets a fresh Settings (env vars may differ)."""
    from asset_forge.common.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
