"""Tests for the generation backends.

Network calls are mocked. Real fal.ai / Kaggle calls are NOT made
in the test suite.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from asset_forge.common.errors import RouteUnavailable
from asset_forge.common.types import (
    AiDisclosure,
    Brief,
    DemoScene,
    GenerationConfig,
    GridSpec,
    Piece,
    PricingConfig,
    StyleSpec,
)
from asset_forge.mcp_client.backends import (
    BackendRegistry,
    FalAiBackend,
    KaggleBatchBackend,
    generate_with_fallback,
)


def _build_test_brief() -> Brief:
    return Brief(
        id="test-001",
        title="Test",
        description="d",
        style=StyleSpec(palette=("#a04040",)),
        grid=GridSpec(),
        pieces=(Piece(id="barrel", category="container", prompt="wooden barrel"),),
        generation=GenerationConfig(
            primary_routes=("fal-trellis",),
            hero_routes=(),
            fallback_routes=("triposr-local",),
            pre_prompt_style_prefix="Low-poly",
        ),
        exports=("unity",),
        marketplaces=("fab",),
        demo_scenes=(DemoScene(name="s", description="d"),),
        pricing=PricingConfig(launch_usd=9.99, normal_usd=19.99),
        ai_disclosure=AiDisclosure(
            models_used=("TRELLIS",),
            human_review="reviewed",
            commercial_use_verified=True,
        ),
    )


def test_fal_backend_unhealthy_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSET_FORGE_FAL_API_KEY", raising=False)

    from asset_forge.common.settings import get_settings

    get_settings.cache_clear()

    backend = FalAiBackend("fal-trellis")
    assert backend.name == "fal-trellis"
    assert backend.base_cost_usd == 0.02

    import asyncio

    assert asyncio.run(backend.health()) is False


def test_fal_backend_unknown_route_rejected() -> None:
    with pytest.raises(ValueError, match="unknown fal route"):
        FalAiBackend("fal-nonexistent")


def test_kaggle_backend_unhealthy_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSET_FORGE_KAGGLE_API_TOKEN", raising=False)
    monkeypatch.delenv("ASSET_FORGE_KAGGLE_USERNAME", raising=False)

    from asset_forge.common.settings import get_settings

    get_settings.cache_clear()

    backend = KaggleBatchBackend("kaggle-hunyuan3d-full")
    import asyncio

    assert asyncio.run(backend.health()) is False


def test_kaggle_backend_unknown_route_rejected() -> None:
    with pytest.raises(ValueError, match="unknown kaggle route"):
        KaggleBatchBackend("kaggle-nonexistent")


def test_registry_unknown_route_raises_route_unavailable() -> None:
    # Construct registry with a stub session (None is fine; we never call it)
    registry = BackendRegistry(session=None)  # type: ignore[arg-type]
    with pytest.raises(RouteUnavailable):
        registry.get("totally-not-a-route")


def test_registry_caches_backend_instances() -> None:
    registry = BackendRegistry(session=None)  # type: ignore[arg-type]
    a = registry.get("fal-trellis")
    b = registry.get("fal-trellis")
    assert a is b


async def test_fallback_returns_first_success(tmp_path: Path) -> None:
    """generate_with_fallback should stop on first success."""
    brief = _build_test_brief()
    piece = brief.pieces[0]

    from asset_forge.common.types import GenResult

    mock_backend = AsyncMock()
    mock_backend.generate = AsyncMock(
        return_value=GenResult(
            piece_id=piece.id, route="fal-trellis", success=True,
            output_glb_path=tmp_path / "barrel.glb", cost_usd=0.02,
        )
    )

    registry = BackendRegistry(session=None)  # type: ignore[arg-type]
    with patch.object(registry, "get", return_value=mock_backend):
        result = await generate_with_fallback(
            registry, piece, brief, tmp_path, ["fal-trellis", "triposr-local"],
        )
    assert result.success
    assert mock_backend.generate.await_count == 1


async def test_fallback_tries_second_route_on_failure(tmp_path: Path) -> None:
    brief = _build_test_brief()
    piece = brief.pieces[0]

    from asset_forge.common.types import GenResult

    fail_then_succeed = [
        GenResult(piece_id=piece.id, route="fal-trellis", success=False, error_code="x"),
        GenResult(
            piece_id=piece.id, route="triposr-local", success=True,
            output_glb_path=tmp_path / "barrel.glb",
        ),
    ]
    backends = [AsyncMock(), AsyncMock()]
    backends[0].generate = AsyncMock(return_value=fail_then_succeed[0])
    backends[1].generate = AsyncMock(return_value=fail_then_succeed[1])

    registry = BackendRegistry(session=None)  # type: ignore[arg-type]
    with patch.object(registry, "get", side_effect=backends):
        result = await generate_with_fallback(
            registry, piece, brief, tmp_path, ["fal-trellis", "triposr-local"],
        )
    assert result.success
    assert result.route == "triposr-local"
    assert backends[0].generate.await_count == 1
    assert backends[1].generate.await_count == 1


async def test_fallback_returns_last_failure_when_all_fail(tmp_path: Path) -> None:
    brief = _build_test_brief()
    piece = brief.pieces[0]

    from asset_forge.common.types import GenResult

    failures = [
        GenResult(piece_id=piece.id, route="fal-trellis", success=False, error_code="a"),
        GenResult(piece_id=piece.id, route="triposr-local", success=False, error_code="b"),
    ]
    backends = [AsyncMock(), AsyncMock()]
    backends[0].generate = AsyncMock(return_value=failures[0])
    backends[1].generate = AsyncMock(return_value=failures[1])

    registry = BackendRegistry(session=None)  # type: ignore[arg-type]
    with patch.object(registry, "get", side_effect=backends):
        result = await generate_with_fallback(
            registry, piece, brief, tmp_path, ["fal-trellis", "triposr-local"],
        )
    assert not result.success
    assert result.route == "triposr-local"  # last attempted
