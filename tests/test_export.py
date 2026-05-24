"""Tests for export module. Pure-IO, no MCP, no network."""

from __future__ import annotations

import gzip
import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from asset_forge.common.paths import PackPaths
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
from asset_forge.export import EngineTarget, export_pack
from asset_forge.export.godot import build_godot_bundle
from asset_forge.export.master_glb import build_master_glb_bundle
from asset_forge.export.unity import (
    _deterministic_guid,
    build_unity_package,
)
from asset_forge.export.unreal import build_unreal_bundle


def _build_brief() -> Brief:
    return Brief(
        id="test-export",
        title="Export Test Pack",
        description="A pack for testing exports.",
        style=StyleSpec(
            palette=("#a04040",),
            reference_description="low-poly fantasy",
            shading="faceted",
        ),
        grid=GridSpec(),
        pieces=(
            Piece(id="barrel", category="container", prompt="wooden barrel"),
            Piece(id="crate", category="container", prompt="wooden crate"),
            Piece(id="sword", category="weapon", prompt="iron sword"),
        ),
        generation=GenerationConfig(
            primary_routes=("fal-trellis",),
            hero_routes=(),
            fallback_routes=(),
        ),
        exports=("unity", "unreal", "godot", "master_glb"),
        marketplaces=("fab",),
        demo_scenes=(DemoScene(name="s", description="d"),),
        pricing=PricingConfig(launch_usd=9.99, normal_usd=19.99, launch_window_days=14),
        ai_disclosure=AiDisclosure(
            models_used=("TRELLIS",),
            human_review="3 pieces reviewed",
            commercial_use_verified=True,
        ),
        hero_piece_ids=("sword",),
    )


def _make_fake_glbs(tmp_path: Path, ids: list[str]) -> dict[str, Path]:
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    glbs: dict[str, Path] = {}
    for pid in ids:
        p = src_dir / f"{pid}.glb"
        # Tiny fake GLB header (glTF binary magic)
        p.write_bytes(b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 64)
        glbs[pid] = p
    return glbs


def test_deterministic_guid_stable() -> None:
    g1 = _deterministic_guid("pack-1", "Assets/Foo/Bar.glb")
    g2 = _deterministic_guid("pack-1", "Assets/Foo/Bar.glb")
    assert g1 == g2
    assert len(g1) == 32  # md5 hex = 32 chars
    # Different inputs differ
    assert g1 != _deterministic_guid("pack-2", "Assets/Foo/Bar.glb")
    assert g1 != _deterministic_guid("pack-1", "Assets/Foo/Baz.glb")


def test_unity_package_layout(tmp_path: Path) -> None:
    brief = _build_brief()
    glbs = _make_fake_glbs(tmp_path, ["barrel", "crate"])
    name_map = {"barrel": "EXPRTC_container_barrel_LOD0", "crate": "EXPRTC_container_crate_LOD0"}
    out_dir = tmp_path / "unity"

    pkg = build_unity_package(
        out_dir=out_dir, brief=brief, source_glbs=glbs, name_map=name_map
    )

    assert pkg.bundle_path.exists()
    assert pkg.archive_path.exists()
    assert pkg.archive_path.suffix == ".unitypackage"
    # Browseable layout: Assets/<pack>/Pieces/<canonical>.glb
    pieces_dir = out_dir / "Assets" / "Export_Test_Pack" / "Pieces"
    assert pieces_dir.exists()
    assert (pieces_dir / "EXPRTC_container_barrel_LOD0.glb").exists()
    assert (pieces_dir / "EXPRTC_container_barrel_LOD0.glb.meta").exists()


def test_unitypackage_archive_is_valid_gzipped_tar(tmp_path: Path) -> None:
    brief = _build_brief()
    glbs = _make_fake_glbs(tmp_path, ["barrel"])
    name_map = {"barrel": "EXPRTC_container_barrel_LOD0"}
    out_dir = tmp_path / "unity"

    pkg = build_unity_package(out_dir, brief, glbs, name_map)

    # Decompress + inspect tar contents
    payload = gzip.decompress(pkg.archive_path.read_bytes())
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r") as tar:
        names = tar.getnames()

    # Every asset has /asset + /asset.meta + /pathname tuple
    asset_names = [n for n in names if n.endswith("/asset")]
    meta_names = [n for n in names if n.endswith("/asset.meta")]
    pathname_names = [n for n in names if n.endswith("/pathname")]
    # We have: 1 GLB + 3 text files + (no asset for folders, but they still have .meta and pathname)
    # asset entries = 1 glb + 3 text = 4
    assert len(asset_names) >= 4
    # meta entries = 4 files + 2 folders = 6
    assert len(meta_names) >= 6
    # pathname mirrors
    assert len(pathname_names) == len(meta_names)


def test_unreal_bundle_layout_and_uplugin(tmp_path: Path) -> None:
    brief = _build_brief()
    glbs = _make_fake_glbs(tmp_path, ["barrel", "sword"])
    name_map = {
        "barrel": "EXPRTC_container_barrel_LOD0",
        "sword": "EXPRTC_weapon_sword_LOD0",
    }
    out_dir = tmp_path / "unreal"

    pkg = build_unreal_bundle(out_dir, brief, glbs, name_map)

    assert pkg.bundle_path.exists()
    assert pkg.archive_path.exists()
    assert pkg.archive_path.suffix == ".zip"

    # uplugin descriptor exists and parses as JSON
    uplugin = next(out_dir.glob("*.uplugin"))
    descriptor = json.loads(uplugin.read_text(encoding="utf-8"))
    assert descriptor["FriendlyName"] == brief.title
    assert descriptor["CanContainContent"] is True

    # Content folder has both pieces
    pieces_dir = out_dir / "Content" / "Export_Test_Pack" / "Pieces"
    assert (pieces_dir / "EXPRTC_container_barrel_LOD0.glb").exists()
    assert (pieces_dir / "EXPRTC_weapon_sword_LOD0.glb").exists()


def test_unreal_archive_contains_uplugin_and_glb(tmp_path: Path) -> None:
    brief = _build_brief()
    glbs = _make_fake_glbs(tmp_path, ["barrel"])
    name_map = {"barrel": "EXPRTC_container_barrel_LOD0"}
    out_dir = tmp_path / "unreal"

    pkg = build_unreal_bundle(out_dir, brief, glbs, name_map)

    with zipfile.ZipFile(pkg.archive_path) as zf:
        names = zf.namelist()
    assert any(n.endswith(".uplugin") for n in names)
    assert any(n.endswith("EXPRTC_container_barrel_LOD0.glb") for n in names)
    assert any(n.endswith("README.md") for n in names)
    assert any(n.endswith("license.txt") for n in names)


def test_godot_bundle_layout(tmp_path: Path) -> None:
    brief = _build_brief()
    glbs = _make_fake_glbs(tmp_path, ["barrel"])
    name_map = {"barrel": "EXPRTC_container_barrel_LOD0"}
    out_dir = tmp_path / "godot"

    pkg = build_godot_bundle(out_dir, brief, glbs, name_map)

    assert pkg.archive_path.suffix == ".zip"
    # addons/<lowercase pack name>/...
    addons_root = out_dir / "addons"
    assert addons_root.exists()
    addon_dir = next(addons_root.iterdir())
    assert (addon_dir / "plugin.cfg").exists()
    assert (addon_dir / "plugin.gd").exists()
    assert (addon_dir / "pieces" / "EXPRTC_container_barrel_LOD0.glb").exists()

    cfg = (addon_dir / "plugin.cfg").read_text(encoding="utf-8")
    assert brief.title in cfg
    assert "flax-game-studio" in cfg


def test_master_glb_bundle_includes_manifest(tmp_path: Path) -> None:
    brief = _build_brief()
    glbs = _make_fake_glbs(tmp_path, ["barrel", "crate", "sword"])
    name_map = {
        "barrel": "EXPRTC_container_barrel_LOD0",
        "crate": "EXPRTC_container_crate_LOD0",
        "sword": "EXPRTC_weapon_sword_LOD0",
    }
    out_dir = tmp_path / "master"

    build_master_glb_bundle(out_dir, brief, glbs, name_map)

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["pack_id"] == brief.id
    assert manifest["piece_count"] == 3
    piece_ids = {p["id"] for p in manifest["pieces"]}
    assert piece_ids == {"barrel", "crate", "sword"}
    # Every entry has sha256
    for p in manifest["pieces"]:
        assert len(p["sha256"]) == 64  # hex
        assert p["size_bytes"] > 0
        assert p["canonical_name"].startswith("EXPRTC_")


@pytest.mark.asyncio
async def test_export_pack_builds_all_targets(tmp_path: Path) -> None:
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()

    # Drop fake GLBs into lods_dir (the preferred source)
    for pid in ["barrel", "crate", "sword"]:
        (paths.lods_dir / f"{pid}.glb").write_bytes(b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 64)

    result = await export_pack(
        paths, brief, pieces_succeeded=["barrel", "crate", "sword"]
    )

    assert result.pack_id == brief.id
    targets = {pkg.target for pkg in result.packages}
    assert targets == {
        EngineTarget.UNITY,
        EngineTarget.UNREAL,
        EngineTarget.GODOT,
        EngineTarget.MASTER_GLB,
    }
    assert not result.failures

    # Every bundle archive exists
    for pkg in result.packages:
        assert pkg.archive_path.exists()
        assert pkg.file_count > 0
        assert pkg.size_bytes > 0


@pytest.mark.asyncio
async def test_export_pack_skips_when_no_source_glbs(tmp_path: Path) -> None:
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()
    # No GLBs anywhere

    result = await export_pack(
        paths, brief, pieces_succeeded=["barrel"]
    )

    assert not result.packages
    assert len(result.failures) == 4  # one per requested target


@pytest.mark.asyncio
async def test_export_pack_respects_targets_arg(tmp_path: Path) -> None:
    brief = _build_brief()
    paths = PackPaths(pack_id=brief.id, root=tmp_path)
    paths.ensure()
    (paths.lods_dir / "barrel.glb").write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 64)

    result = await export_pack(
        paths,
        brief,
        pieces_succeeded=["barrel"],
        targets=(EngineTarget.MASTER_GLB,),
    )

    assert len(result.packages) == 1
    assert result.packages[0].target is EngineTarget.MASTER_GLB
