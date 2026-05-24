"""asset-forge CLI.

Phase-0 commands work:
    asset-forge status      verify config + flax-mcp reachability
    asset-forge validate    parse + validate a brief.yaml
    asset-forge build       run the pipeline (resumable)
    asset-forge doctor      run all health checks

Other commands print "Phase N stub" until their subsystem lands.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from asset_forge.common.logging import setup_logging
from asset_forge.common.settings import get_settings
from asset_forge.orchestrator import build_pack, load_brief
from asset_forge.orchestrator.state import load_state

app = typer.Typer(help="asset-forge — AI-driven game asset pack pipeline")
console = Console()


@app.callback()
def _configure(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Configure logging before any command runs."""
    setup_logging(level="DEBUG" if verbose else "INFO")


@app.command()
def status() -> None:
    """Show current configuration."""
    s = get_settings()
    t = Table(title="asset-forge settings", show_lines=True)
    t.add_column("key")
    t.add_column("value")
    t.add_row("mcp_url", s.mcp_url)
    t.add_row("output_root", str(s.output_root))
    t.add_row("gen_routes", ", ".join(s.gen_routes_list))
    t.add_row("fal_api_key", _mask(s.fal_api_key))
    t.add_row("kaggle_primary", "set" if s.kaggle_api_token else "unset")
    t.add_row("kaggle_secondary", "set" if s.kaggle_api_token_secondary else "unset")
    t.add_row("blender_path", s.blender_path or "(not set)")
    t.add_row("retopo_backend", s.retopo_backend)
    console.print(t)


@app.command()
def doctor() -> None:
    """Run all health checks: config, flax-mcp, fal.ai, kaggle, blender, retopo."""
    asyncio.run(_doctor_async())


async def _doctor_async() -> None:
    from asset_forge.mcp_client.backends import BackendRegistry
    from asset_forge.mcp_client.session import McpSession

    s = get_settings()
    t = Table(title="asset-forge doctor", show_lines=True)
    t.add_column("check")
    t.add_column("status")
    t.add_column("detail")

    # flax-mcp reachability
    try:
        async with McpSession.connect() as mcp:
            ok = await mcp.health()
            t.add_row("flax-mcp", "[green]ok[/green]" if ok else "[red]down[/red]", s.mcp_url)
            registry = BackendRegistry(mcp)
            for route in s.gen_routes_list:
                try:
                    backend = registry.get(route)
                    healthy = await backend.health()
                    t.add_row(
                        f"route: {route}",
                        "[green]ok[/green]" if healthy else "[yellow]unavailable[/yellow]",
                        "",
                    )
                except Exception as e:
                    t.add_row(f"route: {route}", "[red]error[/red]", str(e)[:80])
    except Exception as e:
        t.add_row("flax-mcp", "[red]unreachable[/red]", str(e)[:80])

    # Blender path
    if s.blender_path:
        p = Path(s.blender_path)
        t.add_row("blender", "[green]ok[/green]" if p.exists() else "[red]missing[/red]", str(p))
    else:
        t.add_row("blender", "[yellow]unset[/yellow]", "set ASSET_FORGE_BLENDER_PATH")

    console.print(t)


@app.command()
def validate(brief_path: Path = typer.Argument(..., help="Path to a brief.yaml")) -> None:
    """Parse + validate a brief.yaml without running anything."""
    try:
        brief = load_brief(brief_path)
    except Exception as e:
        console.print(f"[red]Validation failed:[/red] {e}")
        raise typer.Exit(code=1) from e

    t = Table(title=f"brief: {brief.title}", show_lines=False)
    t.add_column("field")
    t.add_column("value")
    t.add_row("id", brief.id)
    t.add_row("pieces", str(len(brief.pieces)))
    t.add_row("hero_pieces", str(len(brief.hero_piece_ids)))
    t.add_row("exports", ", ".join(brief.exports))
    t.add_row("marketplaces", ", ".join(brief.marketplaces))
    t.add_row("primary_routes", ", ".join(brief.generation.primary_routes))
    t.add_row("hero_routes", ", ".join(brief.generation.hero_routes))
    t.add_row("est. cost", f"${brief.generation.estimated_cloud_cost_usd or 0:.2f}")
    t.add_row("pricing", f"${brief.pricing.launch_usd}/launch / ${brief.pricing.normal_usd}/normal")
    console.print(t)
    console.print("[green]Brief is valid.[/green]")


@app.command()
def build(
    brief_path: Path = typer.Argument(..., help="Path to a brief.yaml"),
    resume: bool = typer.Option(False, "--resume", help="Skip phases already completed"),
    stop_after: str | None = typer.Option(
        None, "--stop-after", help="Stop after this phase (e.g. generation)"
    ),
) -> None:
    """Build a pack end-to-end from a brief."""
    from asset_forge.common.types import Phase

    stop_phase = None
    if stop_after:
        try:
            stop_phase = Phase(stop_after)
        except ValueError:
            console.print(
                f"[red]Unknown phase: {stop_after}. Valid: "
                f"{', '.join(p.value for p in Phase)}[/red]"
            )
            raise typer.Exit(code=1) from None

    try:
        result = asyncio.run(
            build_pack(brief_path, resume=resume, stop_after_phase=stop_phase)
        )
    except Exception as e:
        console.print(f"[red]Build failed:[/red] {e}")
        raise typer.Exit(code=1) from e

    t = Table(title=f"build result: {result.pack_id}", show_lines=False)
    t.add_column("field")
    t.add_column("value")
    t.add_row("status", result.status)
    t.add_row("phases_run", ", ".join(p.value for p in result.phases_run))
    t.add_row("phases_skipped", ", ".join(p.value for p in result.phases_skipped))
    t.add_row("pieces_succeeded", str(len(result.pieces_succeeded)))
    t.add_row("pieces_failed", str(len(result.pieces_failed)))
    t.add_row("total_cost_usd", f"${result.total_cost_usd:.4f}")
    console.print(t)
    if result.pieces_failed:
        console.print(
            f"[yellow]Failed pieces:[/yellow] {', '.join(result.pieces_failed)}"
        )


@app.command()
def show_state(pack_id: str = typer.Argument(...)) -> None:
    """Print the state.json for a pack."""
    from asset_forge.common.paths import pack_paths_for

    paths = pack_paths_for(pack_id)
    if not paths.state_file.exists():
        console.print(f"[red]No state file for {pack_id} at {paths.state_file}[/red]")
        raise typer.Exit(code=1)

    state = load_state(paths.state_file, pack_id)
    t = Table(title=f"state: {pack_id}", show_lines=False)
    t.add_column("phase")
    t.add_column("outcome")
    t.add_column("notes")
    for phase, ps in state.phases.items():
        t.add_row(phase.value, ps.outcome.value, ps.notes[:60])
    console.print(t)
    console.print(f"Total cost so far: [cyan]${state.total_cost_usd:.4f}[/cyan]")


@app.command()
def manifests(
    pack_dir: Path = typer.Argument(...),
    targets: str = typer.Option("fab,unity,itchio,gumroad"),
) -> None:
    """Generate marketplace submission manifests. Phase 2 stub."""
    console.print("[yellow]manifests: phase 2 stub[/yellow]")


@app.command()
def showroom(pack_dir: Path = typer.Argument(...)) -> None:
    """Build the static-site landing page. Phase 6 stub."""
    console.print("[yellow]showroom: phase 6 stub[/yellow]")


def _mask(value: str) -> str:
    if not value or len(value) < 12:
        return value if value else "(not set)"
    return f"{value[:6]}...{value[-4:]}"


if __name__ == "__main__":
    app()
