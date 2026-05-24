"""asset-forge — AI-driven game asset pack creation pipeline.

Proprietary, flax-game-studio. See LICENSE.

Architecture:
    asset-forge is an MCP CLIENT of flax-mcp. It sends MCP tool calls
    to the flax-mcp server running on :8765 (default) and orchestrates
    them into end-to-end asset-pack production.

Subsystems:
    orchestrator   the pack-production brain (state machine)
    mcp_client     talks to flax-mcp over MCP
    retopo         auto-retopology wrappers (QuadRemesher / Instant Meshes / QuadriFlow)
    uvunwrap       UV unwrap automation (Smart UV + seam hints + LLM refine)
    style          style-consistency enforcer (seed + CLIP-guidance + color match)
    snap_grid      pivot normalizer for modular assembly
    manifest       marketplace manifest generation (Fab / Unity / Itch / Gumroad)
    showroom       static-site generator for pack landing pages
    common         shared types, settings, telemetry

The rule: subsystems never call flax-mcp directly. Everything goes
through mcp_client.* so we can swap backends later (hosted MCP,
bundled equivalents, etc.) without rewriting subsystems.
"""

__version__ = "0.0.1"
