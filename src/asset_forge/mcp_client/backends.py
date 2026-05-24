"""Generation backends: fal.ai, Kaggle, local-via-flax-mcp.

A Backend implements a single contract:

    async def generate(piece, brief, dest_dir) -> GenResult

The BackendRegistry routes piece → backend by route name. The
orchestrator chooses the route list (primary_routes / hero_routes /
fallback_routes from brief.yaml), then the registry maps each route
to a backend instance.

Day-0 implementation status:
- LocalMcpBackend: real, calls flax-mcp asset_gen/text_to_3d via session
- FalAiBackend: real, calls fal.run/ HTTP API
- KaggleBatchBackend: stub for now; spec'd in scripts/kaggle/README.md
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

from asset_forge.common.errors import GenerationError, RouteUnavailable
from asset_forge.common.logging import get_logger
from asset_forge.common.settings import get_settings
from asset_forge.common.types import Brief, GenResult, Piece

from .session import McpSession


class Backend(ABC):
    """Abstract base for generation backends."""

    name: str

    @abstractmethod
    async def health(self) -> bool:
        """Cheap reachability/credential check. False = route is unavailable."""

    @abstractmethod
    async def generate(self, piece: Piece, brief: Brief, dest_dir: Path) -> GenResult:
        """Run text-to-3D for one piece. Saves output GLB into dest_dir.

        Returns GenResult with success=True/False. NEVER raises on
        generation failure — caller chains fallback routes.
        """


# ---------------------------------------------------------------------------
# fal.ai backend
# ---------------------------------------------------------------------------

# Route name -> (fal model id, base cost USD, kind)
_FAL_ROUTES: dict[str, tuple[str, float, str]] = {
    "fal-trellis": ("fal-ai/trellis", 0.02, "image-to-3d"),
    "fal-triposr": ("fal-ai/triposr", 0.07, "image-to-3d"),
    "fal-hunyuan3d-21": ("fal-ai/hunyuan3d-v21", 0.30, "image-to-3d"),
    "fal-hunyuan3d-pro": ("fal-ai/hunyuan-3d/v3.1/pro/text-to-3d", 0.375, "text-to-3d"),
    "fal-tripo-text": ("tripo3d/p1/text-to-3d", 0.01, "text-to-3d"),
    "fal-rodin": ("fal-ai/hyper3d/rodin/v2", 0.40, "image-to-3d"),
}


class FalAiBackend(Backend):
    """fal.ai cloud generation. ~$0.02-$0.40 per generation. New accounts get $5 free."""

    def __init__(self, route: str) -> None:
        if route not in _FAL_ROUTES:
            raise ValueError(f"unknown fal route: {route}")
        self.name = route
        self._model_id, self._base_cost, self._kind = _FAL_ROUTES[route]
        self._log = get_logger("backend.fal")

    @property
    def base_cost_usd(self) -> float:
        return self._base_cost

    async def health(self) -> bool:
        s = get_settings()
        if not s.fal_api_key:
            return False
        # Don't burn a real generation on health check; just verify the key shape.
        return len(s.fal_api_key) > 16

    async def generate(self, piece: Piece, brief: Brief, dest_dir: Path) -> GenResult:
        s = get_settings()
        if not s.fal_api_key:
            raise RouteUnavailable(self.name, "ASSET_FORGE_FAL_API_KEY not set")

        dest_dir.mkdir(parents=True, exist_ok=True)
        out_path = dest_dir / f"{piece.id}.glb"

        prompt = self._compose_prompt(piece, brief)
        body: dict[str, Any] = self._build_request_body(prompt)

        url = f"https://fal.run/{self._model_id}"
        headers = {
            "Authorization": f"Key {s.fal_api_key}",
            "Content-Type": "application/json",
        }
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(url, headers=headers, json=body)
            duration = time.monotonic() - start

            if resp.status_code >= 400:
                return GenResult(
                    piece_id=piece.id,
                    route=self.name,
                    success=False,
                    duration_seconds=duration,
                    error_code=f"http_{resp.status_code}",
                    error_message=resp.text[:500],
                )

            data = resp.json()
            glb_url = self._extract_glb_url(data)
            if not glb_url:
                return GenResult(
                    piece_id=piece.id,
                    route=self.name,
                    success=False,
                    duration_seconds=duration,
                    error_code="no_glb_in_response",
                    error_message=str(data)[:500],
                )

            # Download the GLB
            async with httpx.AsyncClient(timeout=120.0) as client:
                glb_resp = await client.get(glb_url)
                glb_resp.raise_for_status()
                out_path.write_bytes(glb_resp.content)

            return GenResult(
                piece_id=piece.id,
                route=self.name,
                success=True,
                output_glb_path=out_path,
                cost_usd=self._base_cost,
                duration_seconds=time.monotonic() - start,
                metadata={"fal_model": self._model_id},
            )
        except httpx.HTTPError as e:
            return GenResult(
                piece_id=piece.id,
                route=self.name,
                success=False,
                duration_seconds=time.monotonic() - start,
                error_code="http_error",
                error_message=str(e),
            )

    def _compose_prompt(self, piece: Piece, brief: Brief) -> str:
        prefix = brief.generation.pre_prompt_style_prefix.strip()
        if prefix:
            return f"{prefix}\n\n{piece.prompt}"
        return piece.prompt

    def _build_request_body(self, prompt: str) -> dict[str, Any]:
        # fal.ai API shape varies slightly per model. The text-to-3D
        # variants take {"prompt": ...}; image-to-3D variants take
        # {"input_image_url": ...}. For initial implementation we
        # focus on text-to-3D where available.
        if self._kind == "text-to-3d":
            return {"prompt": prompt}
        # For image-to-3D models, the orchestrator must first generate
        # a reference image via Tripo/text-to-image and pass it. That
        # wiring lands in the orchestrator; for now we fail loudly.
        raise NotImplementedError(
            f"image-to-3D route {self.name} requires an upstream reference image; "
            "use a text-to-3D route or wire the image-gen pre-pass in orchestrator"
        )

    @staticmethod
    def _extract_glb_url(response: dict[str, Any]) -> str | None:
        """fal.ai responses vary; check known fields."""
        # Common shapes: {"model_mesh": {"url": ...}}, {"glb_url": ...},
        # {"output": {"url": ...}}, {"mesh": {"url": ...}}
        for key in ("model_mesh", "mesh", "output", "glb"):
            val = response.get(key)
            if isinstance(val, dict):
                url = val.get("url")
                if isinstance(url, str):
                    return url
        url = response.get("glb_url")
        if isinstance(url, str):
            return url
        return None


# ---------------------------------------------------------------------------
# Local-via-flax-mcp backend
# ---------------------------------------------------------------------------

# Map asset-forge route name to flax-asset-gen route name.
_LOCAL_ROUTE_MAP: dict[str, str] = {
    "triposr-local": "triposr",
    "trellis-hf": "trellis-hf",
    "hunyuan-mini-local": "hunyuan-mini",
    "rodin-trial": "rodin-trial",
}


class LocalMcpBackend(Backend):
    """Delegates to flax-mcp's asset_gen/text_to_3d tool.

    All five upstream routes run via flax-asset-gen (HF Spaces TRELLIS,
    Blender Rodin trial, Blender Hunyuan-mini, Blender StableFast3D
    SKIPPED, Blender TripoSR).
    """

    def __init__(self, route: str, session: McpSession) -> None:
        if route not in _LOCAL_ROUTE_MAP:
            raise ValueError(f"unknown local route: {route}")
        self.name = route
        self._upstream_route = _LOCAL_ROUTE_MAP[route]
        self._session = session
        self._log = get_logger("backend.local")

    async def health(self) -> bool:
        try:
            result = await self._session.call("asset_gen/list_routes")
            return bool(result)
        except Exception:
            return False

    async def generate(self, piece: Piece, brief: Brief, dest_dir: Path) -> GenResult:
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_path = dest_dir / f"{piece.id}.glb"
        prompt = self._compose_prompt(piece, brief)

        start = time.monotonic()
        try:
            result = await self._session.call(
                "asset_gen/text_to_3d",
                {
                    "prompt": prompt,
                    "route": self._upstream_route,
                    "outputPath": str(out_path),
                },
                intent=f"asset-forge pack={brief.id} piece={piece.id}",
            )
            duration = time.monotonic() - start

            if not out_path.exists():
                return GenResult(
                    piece_id=piece.id,
                    route=self.name,
                    success=False,
                    duration_seconds=duration,
                    error_code="output_missing",
                    error_message=f"flax-mcp returned success but {out_path} missing",
                )
            return GenResult(
                piece_id=piece.id,
                route=self.name,
                success=True,
                output_glb_path=out_path,
                cost_usd=0.0,
                duration_seconds=duration,
                metadata={"upstream_route": self._upstream_route, **result},
            )
        except Exception as e:
            return GenResult(
                piece_id=piece.id,
                route=self.name,
                success=False,
                duration_seconds=time.monotonic() - start,
                error_code="mcp_error",
                error_message=str(e),
            )

    def _compose_prompt(self, piece: Piece, brief: Brief) -> str:
        prefix = brief.generation.pre_prompt_style_prefix.strip()
        if prefix:
            return f"{prefix}\n\n{piece.prompt}"
        return piece.prompt


# ---------------------------------------------------------------------------
# Kaggle batch backend (stub on day 0; expands per scripts/kaggle/README.md)
# ---------------------------------------------------------------------------

_KAGGLE_ROUTE_TO_MODEL: dict[str, str] = {
    "kaggle-hunyuan3d-full": "hunyuan3d-full",
    "kaggle-trellis-local": "trellis-local",
    "kaggle-controlnet-style": "controlnet-style",
    "kaggle-anigen": "anigen",
}


class KaggleBatchBackend(Backend):
    """Submits batch jobs to Kaggle Notebooks. Free 30 GPU hrs/wk per account.

    Day-0 status: stub. Full implementation requires the kaggle CLI +
    notebook-version-push flow documented in scripts/kaggle/README.md.
    This stub fails health() cleanly so routing falls through to
    fal.ai or local until we land the real implementation.
    """

    def __init__(self, route: str, account: str = "primary") -> None:
        if route not in _KAGGLE_ROUTE_TO_MODEL:
            raise ValueError(f"unknown kaggle route: {route}")
        self.name = route
        self._model = _KAGGLE_ROUTE_TO_MODEL[route]
        self._account = account
        self._log = get_logger("backend.kaggle")

    async def health(self) -> bool:
        s = get_settings()
        if self._account == "primary":
            return bool(s.kaggle_username and s.kaggle_api_token)
        return bool(s.kaggle_username_secondary and s.kaggle_api_token_secondary)

    async def generate(self, piece: Piece, brief: Brief, dest_dir: Path) -> GenResult:
        # Batch backend: orchestrator should call submit_batch() with
        # multiple pieces, not one-at-a-time. The single-piece path is
        # supported for parity but submits a 1-piece batch.
        results = await self.submit_batch([piece], brief, dest_dir)
        return results[0]

    async def submit_batch(
        self, pieces: list[Piece], brief: Brief, dest_dir: Path
    ) -> list[GenResult]:
        """Day-0 stub. Returns 'route_unavailable' for each piece.

        Full implementation: uploads job_spec.json + reference images
        as a Kaggle Dataset, pushes a new version of the notebook,
        polls until completion, downloads outputs. See
        scripts/kaggle/README.md for the design.
        """
        await asyncio.sleep(0)  # silence "no await" lint
        return [
            GenResult(
                piece_id=p.id,
                route=self.name,
                success=False,
                error_code="not_implemented",
                error_message="KaggleBatchBackend.submit_batch is a day-0 stub; see scripts/kaggle/README.md",
            )
            for p in pieces
        ]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class BackendRegistry:
    """Resolves route name -> Backend instance.

    Built once per pipeline run. The orchestrator constructs it with a
    live McpSession; backends share it for any flax-mcp work.
    """

    def __init__(self, session: McpSession) -> None:
        self._session = session
        self._cache: dict[str, Backend] = {}

    @property
    def session(self) -> McpSession:
        """Expose the session for phase handlers that need it directly
        (retopo / uvunwrap / snap_grid / manifest)."""
        return self._session

    def get(self, route: str) -> Backend:
        if route in self._cache:
            return self._cache[route]
        backend = self._build(route)
        self._cache[route] = backend
        return backend

    def _build(self, route: str) -> Backend:
        if route in _FAL_ROUTES:
            return FalAiBackend(route)
        if route in _LOCAL_ROUTE_MAP:
            return LocalMcpBackend(route, self._session)
        if route in _KAGGLE_ROUTE_TO_MODEL:
            return KaggleBatchBackend(route)
        raise RouteUnavailable(route, "no backend registered for this route name")

    async def healthy_routes(self, candidate_routes: list[str]) -> list[str]:
        """Return only the routes whose backend health check passes."""
        out: list[str] = []
        for route in candidate_routes:
            try:
                backend = self.get(route)
            except RouteUnavailable:
                continue
            if await backend.health():
                out.append(route)
        return out


async def generate_with_fallback(
    registry: BackendRegistry,
    piece: Piece,
    brief: Brief,
    dest_dir: Path,
    route_list: list[str],
    max_retries_per_route: int = 1,
) -> GenResult:
    """Try each route in order; first success wins.

    NEVER raises. Returns a failed GenResult if every route fails.
    """
    log = get_logger("backend.fallback")
    last_result: GenResult | None = None

    for route in route_list:
        try:
            backend = registry.get(route)
        except RouteUnavailable as ru:
            log.warning("route.unavailable", route=route, reason=ru.reason)
            continue

        for attempt in range(1, max_retries_per_route + 1):
            log.info("generate.attempt", piece=piece.id, route=route, attempt=attempt)
            try:
                result = await backend.generate(piece, brief, dest_dir)
            except RouteUnavailable as ru:
                log.warning("route.unavailable_at_call", route=route, reason=ru.reason)
                break
            except Exception as e:
                log.error("generate.exception", piece=piece.id, route=route, error=str(e))
                result = GenResult(
                    piece_id=piece.id,
                    route=route,
                    success=False,
                    error_code="backend_exception",
                    error_message=str(e),
                )

            last_result = result
            if result.success:
                return result

    # Every route failed; raise so caller can decide per-pack policy
    if last_result is None:
        raise GenerationError(
            f"no routes attempted for piece {piece.id}",
            piece_id=piece.id,
            route="none",
        )
    return last_result
