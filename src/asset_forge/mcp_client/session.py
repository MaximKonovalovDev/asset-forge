"""MCP session — the ONLY module that opens a connection to flax-mcp.

Every subsystem calls McpSession.call() instead of opening its own
client. This is the seam that lets us swap backends later (hosted
MCP, bundled equivalents, etc).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Self

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from asset_forge.common.errors import McpCallError
from asset_forge.common.logging import get_logger
from asset_forge.common.settings import get_settings


class McpSession:
    """Async client for flax-mcp over HTTP.

    Use as `async with McpSession.connect() as mcp: ...` or construct
    directly for testing.
    """

    def __init__(self, base_url: str, timeout: float, session_id: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session_id = session_id or f"asset-forge-{uuid.uuid4().hex[:12]}"
        self._client: httpx.AsyncClient | None = None
        self._log = get_logger("mcp_client")

    @classmethod
    @asynccontextmanager
    async def connect(cls) -> AsyncIterator[Self]:
        """Construct from settings and open the underlying HTTP client."""
        s = get_settings()
        session = cls(base_url=s.mcp_url, timeout=s.mcp_timeout_seconds)
        await session.__aenter__()
        try:
            yield session
        finally:
            await session.__aexit__(None, None, None)

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def session_id(self) -> str:
        return self._session_id

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    async def call(
        self,
        tool: str,
        arguments: dict[str, Any] | None = None,
        *,
        intent: str | None = None,
        dry_run_id: str | None = None,
    ) -> dict[str, Any]:
        """Call an MCP tool. Returns the result dict; raises McpCallError on error.

        Auto-supplies intent/dryRunId when provided. Receipts are written
        on the flax-mcp side; asset-forge mirrors them locally if needed.
        """
        if self._client is None:
            raise McpCallError("McpSession.call() outside an async with block", tool=tool)

        args = dict(arguments or {})
        if intent is not None:
            args["intent"] = intent
        if dry_run_id is not None:
            args["dryRunId"] = dry_run_id

        payload = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": args,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-Asset-Forge-Session": self._session_id,
        }

        self._log.debug("mcp.call", tool=tool, args_keys=list(args.keys()))

        try:
            resp = await self._client.post(
                f"{self._base_url}/mcp",
                headers=headers,
                content=json.dumps(payload),
            )
        except httpx.HTTPError as e:
            raise McpCallError(f"transport error calling {tool}: {e}", tool=tool) from e

        if resp.status_code >= 500:
            raise McpCallError(f"server error {resp.status_code} on {tool}", tool=tool)
        if resp.status_code >= 400:
            raise McpCallError(
                f"client error {resp.status_code} on {tool}: {resp.text[:200]}",
                tool=tool,
                code="invalid_arguments",
            )

        body = resp.json()
        if "error" in body:
            err = body["error"]
            raise McpCallError(
                err.get("message", "unknown error"),
                tool=tool,
                code=err.get("code"),
            )
        result = body.get("result", {})
        if isinstance(result, dict) and result.get("isError"):
            raise McpCallError(
                result.get("errorMessage", "tool reported isError=true"),
                tool=tool,
                code=result.get("errorCode"),
            )
        return result if isinstance(result, dict) else {"data": result}

    async def health(self) -> bool:
        """Cheap reachability check. Returns True if flax-mcp responds to tool/health."""
        try:
            await self.call("tool/health")
            return True
        except McpCallError:
            return False
