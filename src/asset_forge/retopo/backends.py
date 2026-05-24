"""Retopology backends. Each implements RetopoBackend.retopo()."""

from __future__ import annotations

import asyncio
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from asset_forge.common.logging import get_logger
from asset_forge.mcp_client.session import McpSession

# RetopoResult / TopologyTarget live HERE (not in api.py) to break the
# circular import. api.py re-exports them for the public surface.


@dataclass(frozen=True, slots=True)
class TopologyTarget:
    target_face_count: int = 2000
    quads_preferred: bool = True
    preserve_uvs: bool = False
    symmetric_axis: Literal["x", "y", "z", None] = None


@dataclass(frozen=True, slots=True)
class RetopoResult:
    piece_id: str
    backend: str
    success: bool
    output_glb: Path | None = None
    input_face_count: int | None = None
    output_face_count: int | None = None
    is_quad_dominant: bool = False
    duration_seconds: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class RetopoBackend(ABC):
    """Abstract base for retopo backends."""

    name: str

    @abstractmethod
    async def retopo(
        self,
        piece_id: str,
        input_glb: Path,
        output_glb: Path,
        target: TopologyTarget,
    ) -> RetopoResult:
        """Run retopology. NEVER raises; returns RetopoResult with success bool."""


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------


async def _run_cli(
    cmd: list[str],
    *,
    timeout_seconds: float = 180.0,
    log_name: str = "subprocess",
) -> tuple[int, str, str]:
    """Run a subprocess to completion. Returns (returncode, stdout, stderr)."""
    log = get_logger(f"retopo.{log_name}")
    log.debug("subprocess.start", cmd=cmd[0], argc=len(cmd))
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_seconds
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return 124, "", f"subprocess timed out after {timeout_seconds}s"
    except FileNotFoundError as e:
        return 127, "", f"binary not found: {e}"
    except OSError as e:
        return 1, "", f"subprocess error: {e}"

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    rc = proc.returncode if proc.returncode is not None else 1
    log.debug("subprocess.done", rc=rc, stdout_len=len(stdout), stderr_len=len(stderr))
    return rc, stdout, stderr


# ---------------------------------------------------------------------------
# QuadriFlow (BSD, CPU-only, subprocess)
# ---------------------------------------------------------------------------


class QuadriFlowBackend(RetopoBackend):
    """QuadriFlow CLI wrapper. BSD-licensed; preferred default."""

    name = "quadriflow"

    def __init__(self, binary_path: str | None = None) -> None:
        self._binary = binary_path or shutil.which("quadriflow") or "quadriflow"

    async def retopo(
        self,
        piece_id: str,
        input_glb: Path,
        output_glb: Path,
        target: TopologyTarget,
    ) -> RetopoResult:
        start = time.monotonic()
        cmd = [
            self._binary,
            "-i",
            str(input_glb),
            "-o",
            str(output_glb),
            "-f",
            str(target.target_face_count),
        ]
        if target.quads_preferred:
            cmd.append("-sharp")

        rc, stdout, stderr = await _run_cli(cmd, log_name=self.name, timeout_seconds=180)
        duration = time.monotonic() - start

        if rc == 127:
            return RetopoResult(
                piece_id=piece_id,
                backend=self.name,
                success=False,
                duration_seconds=duration,
                error_code="binary_not_found",
                error_message=f"{self._binary} not on PATH or ASSET_FORGE_QUADRIFLOW_PATH",
            )
        if rc != 0 or not output_glb.exists():
            return RetopoResult(
                piece_id=piece_id,
                backend=self.name,
                success=False,
                duration_seconds=duration,
                error_code=f"exit_{rc}",
                error_message=(stderr or stdout)[:500],
            )

        return RetopoResult(
            piece_id=piece_id,
            backend=self.name,
            success=True,
            output_glb=output_glb,
            output_face_count=target.target_face_count,
            is_quad_dominant=target.quads_preferred,
            duration_seconds=duration,
        )


# ---------------------------------------------------------------------------
# Instant Meshes (GPL, CPU-only, subprocess)
# ---------------------------------------------------------------------------


class InstantMeshesBackend(RetopoBackend):
    """Instant Meshes CLI wrapper. GPL; invoked as subprocess."""

    name = "instant-meshes"

    def __init__(self, binary_path: str | None = None) -> None:
        self._binary = (
            binary_path
            or shutil.which("Instant Meshes")
            or shutil.which("instant-meshes")
        )

    async def retopo(
        self,
        piece_id: str,
        input_glb: Path,
        output_glb: Path,
        target: TopologyTarget,
    ) -> RetopoResult:
        start = time.monotonic()

        if not self._binary:
            return RetopoResult(
                piece_id=piece_id,
                backend=self.name,
                success=False,
                error_code="binary_not_found",
                error_message=(
                    "Instant Meshes binary not on PATH or "
                    "ASSET_FORGE_INSTANT_MESHES_PATH"
                ),
            )

        cmd = [
            self._binary,
            str(input_glb),
            str(output_glb),
            "--faces",
            str(target.target_face_count),
        ]
        if target.quads_preferred:
            cmd.extend(["--quad"])

        rc, stdout, stderr = await _run_cli(cmd, log_name=self.name, timeout_seconds=180)
        duration = time.monotonic() - start

        if rc != 0 or not output_glb.exists():
            return RetopoResult(
                piece_id=piece_id,
                backend=self.name,
                success=False,
                duration_seconds=duration,
                error_code=f"exit_{rc}",
                error_message=(stderr or stdout)[:500],
            )

        return RetopoResult(
            piece_id=piece_id,
            backend=self.name,
            success=True,
            output_glb=output_glb,
            output_face_count=target.target_face_count,
            is_quad_dominant=target.quads_preferred,
            duration_seconds=duration,
        )


# ---------------------------------------------------------------------------
# Blender voxel remesh (built-in; via flax-blender-bridge MCP)
# ---------------------------------------------------------------------------


class BlenderVoxelRemeshBackend(RetopoBackend):
    """Blender Voxel Remesh modifier. Built into Blender; driven via MCP."""

    name = "voxel-remesh"

    def __init__(self, session: McpSession) -> None:
        self._session = session

    async def retopo(
        self,
        piece_id: str,
        input_glb: Path,
        output_glb: Path,
        target: TopologyTarget,
    ) -> RetopoResult:
        start = time.monotonic()
        try:
            result = await self._session.call(
                "blender_bridge/voxel_remesh",
                {
                    "inputPath": str(input_glb),
                    "outputPath": str(output_glb),
                    "targetFaceCount": target.target_face_count,
                    "symmetricAxis": target.symmetric_axis,
                },
                intent=f"asset-forge retopo piece={piece_id}",
            )
        except Exception as e:
            return RetopoResult(
                piece_id=piece_id,
                backend=self.name,
                success=False,
                duration_seconds=time.monotonic() - start,
                error_code="mcp_error",
                error_message=str(e),
            )

        if not output_glb.exists():
            return RetopoResult(
                piece_id=piece_id,
                backend=self.name,
                success=False,
                duration_seconds=time.monotonic() - start,
                error_code="output_missing",
                error_message=f"Blender bridge returned success but {output_glb} missing",
            )

        out_faces_raw = result.get("outputFaceCount") if isinstance(result, dict) else None
        out_faces = out_faces_raw if isinstance(out_faces_raw, int) else None
        return RetopoResult(
            piece_id=piece_id,
            backend=self.name,
            success=True,
            output_glb=output_glb,
            output_face_count=out_faces,
            is_quad_dominant=False,
            duration_seconds=time.monotonic() - start,
            metadata={"upstream": result if isinstance(result, dict) else {}},
        )


# ---------------------------------------------------------------------------
# Blender decimate (built-in; via flax-blender-bridge MCP)
# ---------------------------------------------------------------------------


class BlenderDecimateBackend(RetopoBackend):
    """Blender Decimate modifier. Fast, triangle output. Good for hard-surface."""

    name = "decimate"

    def __init__(self, session: McpSession) -> None:
        self._session = session

    async def retopo(
        self,
        piece_id: str,
        input_glb: Path,
        output_glb: Path,
        target: TopologyTarget,
    ) -> RetopoResult:
        start = time.monotonic()
        try:
            result = await self._session.call(
                "blender_bridge/decimate",
                {
                    "inputPath": str(input_glb),
                    "outputPath": str(output_glb),
                    "targetFaceCount": target.target_face_count,
                },
                intent=f"asset-forge retopo piece={piece_id}",
            )
        except Exception as e:
            return RetopoResult(
                piece_id=piece_id,
                backend=self.name,
                success=False,
                duration_seconds=time.monotonic() - start,
                error_code="mcp_error",
                error_message=str(e),
            )

        if not output_glb.exists():
            return RetopoResult(
                piece_id=piece_id,
                backend=self.name,
                success=False,
                duration_seconds=time.monotonic() - start,
                error_code="output_missing",
                error_message="Blender bridge produced no file",
            )

        out_faces_raw = result.get("outputFaceCount") if isinstance(result, dict) else None
        out_faces = out_faces_raw if isinstance(out_faces_raw, int) else None
        return RetopoResult(
            piece_id=piece_id,
            backend=self.name,
            success=True,
            output_glb=output_glb,
            output_face_count=out_faces,
            is_quad_dominant=False,
            duration_seconds=time.monotonic() - start,
        )


# ---------------------------------------------------------------------------
# QuadRemesher (commercial; skipped by default)
# ---------------------------------------------------------------------------


class QuadRemesherBackend(RetopoBackend):
    """Commercial Blender plugin. $109 one-time. Skipped by default."""

    name = "quadremesher"

    async def retopo(
        self,
        piece_id: str,
        input_glb: Path,
        output_glb: Path,
        target: TopologyTarget,
    ) -> RetopoResult:
        del input_glb, output_glb, target
        return RetopoResult(
            piece_id=piece_id,
            backend=self.name,
            success=False,
            error_code="commercial_not_licensed",
            error_message=(
                "QuadRemesher costs $109. Skipped until purchased + "
                "ASSET_FORGE_QUADREMESHER_PATH is set. Use quadriflow or "
                "voxel-remesh instead."
            ),
        )
