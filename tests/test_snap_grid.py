"""Tests for snap_grid module."""

from __future__ import annotations

from asset_forge.snap_grid import canonical_piece_name
from asset_forge.snap_grid.api import _pack_prefix


def test_pack_prefix_fantasy_props() -> None:
    assert _pack_prefix("001-fantasy-props") == "FNTPRP"


def test_pack_prefix_scifi_crates() -> None:
    assert _pack_prefix("002-scifi-crates") == "SCFCRT"


def test_pack_prefix_no_numeric_id() -> None:
    # No leading digit prefix; still works. Consonants: medieval -> mdv,
    # village -> vll. Concatenated, uppercased, truncated to 7.
    assert _pack_prefix("medieval-village") == "MDVVLL"


def test_pack_prefix_handles_empty_word() -> None:
    # Empty word edge case shouldn't crash.
    prefix = _pack_prefix("003-fantasy")
    assert prefix.startswith("FNT")


def test_canonical_name_basic() -> None:
    name = canonical_piece_name(
        pack_id="001-fantasy-props",
        category="container",
        piece_id="barrel_wooden",
        lod=0,
    )
    assert name == "FNTPRP_container_barrel_wooden_LOD0"


def test_canonical_name_lod_chain() -> None:
    name3 = canonical_piece_name(
        pack_id="001-fantasy-props",
        category="vessel",
        piece_id="jug_clay",
        lod=3,
    )
    assert name3.endswith("_LOD3")
    assert "vessel" in name3


def test_canonical_name_sanitizes_special_chars() -> None:
    name = canonical_piece_name(
        pack_id="001-fantasy-props",
        category="weapons & armor",
        piece_id="sword.short",
        lod=0,
    )
    assert " " not in name
    assert "&" not in name
    assert "." not in name
