"""Smoke tests. Just verify the package imports cleanly."""

from __future__ import annotations


def test_package_imports() -> None:
    import asset_forge

    assert asset_forge.__version__ == "0.0.1"


def test_subsystems_import() -> None:
    from asset_forge import (
        common,
        manifest,
        mcp_client,
        orchestrator,
        retopo,
        showroom,
        snap_grid,
        style,
        uvunwrap,
    )

    assert all(
        m is not None
        for m in [
            common,
            mcp_client,
            orchestrator,
            retopo,
            uvunwrap,
            style,
            snap_grid,
            manifest,
            showroom,
        ]
    )


def test_cli_imports() -> None:
    from asset_forge import cli

    assert cli.app is not None


def test_common_types_import() -> None:
    from asset_forge.common import (
        Brief,
        GenResult,
        GridSpec,
        Phase,
        Piece,
        Receipt,
        StyleSpec,
    )

    assert all(
        t is not None
        for t in [Brief, GenResult, Phase, Piece, Receipt, StyleSpec, GridSpec]
    )
