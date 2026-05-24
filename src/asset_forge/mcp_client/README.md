# mcp_client — talks to flax-mcp over MCP

The ONLY module in asset-forge that touches flax-mcp directly. Every
subsystem calls functions here instead of opening their own MCP
sockets. This is the seam that lets us swap backends later (hosted
MCP, bundled equivalents, different engine MCPs).

## Contract

```python
from asset_forge.mcp_client import McpSession

async with McpSession.connect() as mcp:
    result = await mcp.call("asset_gen/text_to_3d", {
        "prompt": "low-poly fantasy barrel, wooden, vibrant",
        "intent": "pack-001 piece-007",
    })
    # result.is_error: bool
    # result.data: dict | None
    # result.error_code: str | None
```

## What it wraps

Available flax-mcp surfaces (already shipped):

- **flax-asset-gen** (6 atomic + 1 mega) — text/image-to-3D routing
- **flax-asset-worker** (9 atomic + 1 mega) — 7-provider intake +
  SHA-256 provenance + license sidecar
- **flax-blender-bridge** (22 atomic + 1 mega) — Blender automation
  (vendors ahujasid/blender-mcp, 21.9k stars)
- **flax-meshopt-bridge** (6 atomic + 1 mega) — gltfpack wrapper
  (LOD chains + Draco compression + GLB profiling)
- **flax-procedural** (26 atomic + 3 mega) — WFC, dungeon gen,
  scattering, terrain, noise

That's **70 atomic tools + 7 mega-tools** asset-forge can drive.

## Connection

Default: stdio launcher to `flax-mcp.exe` running on local machine.
Optional: HTTP/SSE to a remote flax-mcp instance.

The session:
- Auto-reconnects on connection drop (5 retries with backoff)
- Persists session-id across reconnects so receipts stay attributed
- Surfaces flax-mcp receipts (audit trail) to asset-forge's own log

## Mutation safety

Every call that flax-mcp tags as Mutating or Destructive gets:
- Auto-supplied `intent` arg: `"asset-forge <pack-id> phase=<phase>"`
- For Destructive: auto-dry_run + dryRunId capture
- All receipts logged to `out/<pack-id>/receipts.ndjson`

asset-forge never bypasses flax-mcp's safety contract. Production
code, not toy code.

## What we steal

- **flax-mcp's MCP client patterns** — session management, receipts,
  dry-run flow
- **CoplayDev's stdio-to-HTTP proxy keepalive** — for surviving
  editor restarts (relevant once we hook into Unity/Unreal MCPs too,
  not just flax-mcp)
