"""Unity .unitypackage bundler.

The .unitypackage format is a gzipped tar with one entry per asset:

    <guid>/asset           binary asset data (the GLB)
    <guid>/asset.meta      Unity import settings as YAML
    <guid>/pathname        UTF-8 string: "Assets/Path/Inside/Project.glb"

Each asset has a deterministic GUID (we derive from canonical name +
pack id) so re-running export produces stable IDs.

Builds:
    <out_dir>/                          browseable bundle layout
      Assets/
        <PackTitle>/
          README.md
          license.txt
          ai_disclosure.txt
          Pieces/<canonical>.glb        per-piece GLB
          Pieces/<canonical>.glb.meta   per-piece import settings
    <out_dir>.unitypackage              gzipped tar ready to import
"""

from __future__ import annotations

import gzip
import hashlib
import io
import tarfile
from pathlib import Path

from asset_forge.common.types import Brief

from ._shared import BuilderOutput, copy_file, reset_dir, write_text

_GLB_META_TEMPLATE = """fileFormatVersion: 2
guid: {guid}
ModelImporter:
  serializedVersion: 21300
  internalIDToNameTable: []
  externalObjects: {{}}
  materials:
    materialImportMode: 2
    materialName: 0
    materialSearch: 1
    materialLocation: 1
  animations:
    legacyGenerateAnimations: 4
    bakeSimulation: 0
    resampleCurves: 1
    optimizeGameObjects: 0
    motionNodeName:
    rigImportErrors:
    rigImportWarnings:
    animationImportErrors:
    animationImportWarnings:
    animationRetargetingWarnings:
    animationDoRetargetingWarnings: 0
    importAnimatedCustomProperties: 0
    importConstraints: 0
    animationCompression: 1
    animationRotationError: 0.5
    animationPositionError: 0.5
    animationScaleError: 0.5
    animationWrapMode: 0
    extraExposedTransformPaths: []
    extraUserProperties: []
    clipAnimations: []
    isReadable: 0
  meshes:
    lODScreenPercentages: []
    globalScale: 1
    meshCompression: 0
    addColliders: 0
    useSRGBMaterialColor: 1
    sortHierarchyByName: 1
    importVisibility: 1
    importBlendShapes: 1
    importCameras: 0
    importLights: 0
    swapUVChannels: 0
    generateSecondaryUV: 1
    useFileUnits: 1
    keepQuads: 0
    weldVertices: 1
    bakeAxisConversion: 0
    preserveHierarchy: 0
    skinWeightsMode: 0
    maxBonesPerVertex: 4
    minBoneWeight: 0.001
    optimizeBones: 1
    meshOptimizationFlags: -1
    indexFormat: 0
    secondaryUVAngleDistortion: 8
    secondaryUVAreaDistortion: 15.000001
    secondaryUVHardAngle: 88
    secondaryUVMarginMethod: 1
    secondaryUVMinLightmapResolution: 40
    secondaryUVMinObjectScale: 1
    secondaryUVPackMargin: 4
    useFileScale: 1
"""

_FOLDER_META_TEMPLATE = """fileFormatVersion: 2
guid: {guid}
folderAsset: yes
DefaultImporter:
  externalObjects: {{}}
  userData:
  assetBundleName:
  assetBundleVariant:
"""

_TEXT_META_TEMPLATE = """fileFormatVersion: 2
guid: {guid}
TextScriptImporter:
  externalObjects: {{}}
  userData:
  assetBundleName:
  assetBundleVariant:
"""


def _deterministic_guid(pack_id: str, asset_path: str) -> str:
    """Generate a stable Unity-style GUID from (pack, asset_path).

    Unity GUIDs are 32 hex chars (128 bits). md5 fits perfectly and is
    fast; collision risk is negligible for per-pack scope.
    """
    h = hashlib.md5(f"{pack_id}::{asset_path}".encode())
    return h.hexdigest()


def _asset_safe(name: str) -> str:
    """Sanitize a pack title for Assets/<folder> path."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


def build_unity_package(
    out_dir: Path,
    brief: Brief,
    source_glbs: dict[str, Path],
    name_map: dict[str, str],
) -> BuilderOutput:
    """Build a Unity import bundle + the .unitypackage archive.

    out_dir layout (browseable):
        Assets/<PackFolder>/README.md
        Assets/<PackFolder>/license.txt
        Assets/<PackFolder>/ai_disclosure.txt
        Assets/<PackFolder>/Pieces/<canonical>.glb
        Assets/<PackFolder>/Pieces/<canonical>.glb.meta

    Then we serialize the .meta + .glb + pathname tuples into a
    gzipped tar at <out_dir>.unitypackage.
    """
    reset_dir(out_dir)
    pack_folder = _asset_safe(brief.title) or _asset_safe(brief.id)
    assets_root = out_dir / "Assets" / pack_folder
    pieces_dir = assets_root / "Pieces"
    pieces_dir.mkdir(parents=True, exist_ok=True)

    # 1. Text artifacts (manifest writes the canonical versions; here
    # we inline minimal placeholders so unitypackage stands alone).
    from asset_forge.manifest.templates import (
        ai_disclosure_text,
        license_text,
        pack_readme,
    )

    write_text(assets_root / "README.md", pack_readme(brief))
    write_text(assets_root / "license.txt", license_text(brief))
    write_text(assets_root / "ai_disclosure.txt", ai_disclosure_text(brief))

    # 2. Copy each GLB under canonical name + write its .meta
    total_size = 0
    file_count = 0
    glb_entries: list[tuple[str, Path, Path]] = []  # (project_path, glb, meta)

    for piece_id, source_glb in source_glbs.items():
        canonical = name_map.get(piece_id, piece_id)
        glb_target = pieces_dir / f"{canonical}.glb"
        total_size += copy_file(source_glb, glb_target)
        file_count += 1
        # Meta file
        project_path = f"Assets/{pack_folder}/Pieces/{canonical}.glb"
        guid = _deterministic_guid(brief.id, project_path)
        meta_target = pieces_dir / f"{canonical}.glb.meta"
        write_text(meta_target, _GLB_META_TEMPLATE.format(guid=guid))
        file_count += 1
        total_size += meta_target.stat().st_size
        glb_entries.append((project_path, glb_target, meta_target))

    # 3. Folder .meta files
    text_entries: list[tuple[str, Path, Path]] = []
    folder_entries: list[tuple[str, str]] = []  # (project_path, guid)

    for folder_path, _ in [
        (f"Assets/{pack_folder}", _FOLDER_META_TEMPLATE),
        (f"Assets/{pack_folder}/Pieces", _FOLDER_META_TEMPLATE),
    ]:
        guid = _deterministic_guid(brief.id, folder_path)
        folder_entries.append((folder_path, guid))

    # 4. README / license / ai_disclosure .meta files (text importer)
    for fname in ("README.md", "license.txt", "ai_disclosure.txt"):
        project_path = f"Assets/{pack_folder}/{fname}"
        guid = _deterministic_guid(brief.id, project_path)
        local_file = assets_root / fname
        meta_target = assets_root / f"{fname}.meta"
        write_text(meta_target, _TEXT_META_TEMPLATE.format(guid=guid))
        file_count += 2  # file + meta
        total_size += local_file.stat().st_size + meta_target.stat().st_size
        text_entries.append((project_path, local_file, meta_target))

    # 5. Build the .unitypackage tar.gz
    archive = out_dir.parent / f"{out_dir.name}.unitypackage"
    _serialize_unitypackage(
        archive=archive,
        pack_id=brief.id,
        glb_entries=glb_entries,
        text_entries=text_entries,
        folder_entries=folder_entries,
    )

    return BuilderOutput(
        bundle_path=out_dir,
        archive_path=archive,
        file_count=file_count,
        size_bytes=total_size,
    )


def _serialize_unitypackage(
    archive: Path,
    pack_id: str,
    glb_entries: list[tuple[str, Path, Path]],
    text_entries: list[tuple[str, Path, Path]],
    folder_entries: list[tuple[str, str]],
) -> None:
    """Write the .unitypackage gzipped-tar archive.

    Per-asset entries in the tar:
        <guid>/asset           binary
        <guid>/asset.meta      yaml
        <guid>/pathname        utf-8 string of Assets/... path
    For folder entries: same shape minus the binary 'asset'.
    """
    if archive.exists():
        archive.unlink()
    archive.parent.mkdir(parents=True, exist_ok=True)

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        # Files with binary content
        for project_path, file_path, meta_path in glb_entries + text_entries:
            guid = _deterministic_guid(pack_id, project_path)
            _add_asset_entry(
                tar=tar,
                guid=guid,
                project_path=project_path,
                asset_bytes=file_path.read_bytes(),
                meta_bytes=meta_path.read_bytes(),
            )
        # Folders (no 'asset' binary)
        for project_path, guid in folder_entries:
            meta_yaml = _FOLDER_META_TEMPLATE.format(guid=guid).encode("utf-8")
            _add_folder_entry(
                tar=tar, guid=guid, project_path=project_path, meta_bytes=meta_yaml
            )

    # Gzip the resulting tar
    with open(archive, "wb") as out:
        out.write(gzip.compress(buf.getvalue(), compresslevel=6))


def _add_asset_entry(
    tar: tarfile.TarFile,
    guid: str,
    project_path: str,
    asset_bytes: bytes,
    meta_bytes: bytes,
) -> None:
    _add_tar_file(tar, f"{guid}/asset", asset_bytes)
    _add_tar_file(tar, f"{guid}/asset.meta", meta_bytes)
    _add_tar_file(tar, f"{guid}/pathname", project_path.encode("utf-8"))


def _add_folder_entry(
    tar: tarfile.TarFile,
    guid: str,
    project_path: str,
    meta_bytes: bytes,
) -> None:
    _add_tar_file(tar, f"{guid}/asset.meta", meta_bytes)
    _add_tar_file(tar, f"{guid}/pathname", project_path.encode("utf-8"))


def _add_tar_file(tar: tarfile.TarFile, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(payload)
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(payload))
