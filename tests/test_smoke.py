"""Smoke tests. Just verify the package imports cleanly on day 0."""

from __future__ import annotations


def test_package_imports() -> None:
    import asset_forge

    assert asset_forge.__version__ == "0.0.1"


def test_subsystems_import() -> None:
    from asset_forge import common, mcp_client, orchestrator
    from asset_forge import retopo, uvunwrap, style, snap_grid
    from asset_forge import manifest, showroom

    # All present, no import errors.
    assert all(m is not None for m in [
        common, mcp_client, orchestrator,
        retopo, uvunwrap, style, snap_grid,
        manifest, showroom,
    ])


def test_cli_imports() -> None:
    from asset_forge import cli

    assert cli.app is not None
