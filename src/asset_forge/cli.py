"""asset-forge CLI. `asset-forge ...`

Day 0 scaffold: commands print "not implemented" with the phase
they'll be wired up in. Real implementations land per docs/PLAN.md.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="asset-forge — AI-driven game asset pack pipeline")
console = Console()


@app.command()
def status() -> None:
    """Smoke test: show config + verify flax-mcp reachable."""
    t = Table(title="asset-forge status", show_lines=True)
    t.add_column("check")
    t.add_column("result")
    t.add_row("config loaded", "[yellow]not implemented (Phase 0)[/yellow]")
    t.add_row("flax-mcp reachable", "[yellow]not implemented (Phase 0)[/yellow]")
    t.add_row("blender available", "[yellow]not implemented (Phase 0)[/yellow]")
    t.add_row("retopo backend", "[yellow]not implemented (Phase 0)[/yellow]")
    console.print(t)


@app.command()
def build(
    brief: Path = typer.Argument(..., help="Path to a pack brief.yaml"),
    resume: bool = typer.Option(False, "--resume", help="Resume from last checkpoint"),
    phase: str | None = typer.Option(None, "--phase", help="Run a single phase only"),
) -> None:
    """Build a pack end-to-end from a brief."""
    console.print(f"[cyan]Building from brief: {brief}[/cyan]")
    console.print(f"[yellow]asset-forge build: not implemented (Phase 1)[/yellow]")


@app.command()
def manifests(
    pack_dir: Path = typer.Argument(..., help="Output dir of a built pack"),
    targets: str = typer.Option("fab,unity,itchio,gumroad", help="Comma-separated targets"),
) -> None:
    """Generate marketplace submission manifests."""
    console.print(f"[yellow]asset-forge manifests: not implemented (Phase 2)[/yellow]")


@app.command()
def showroom(
    pack_dir: Path = typer.Argument(..., help="Output dir of a built pack"),
) -> None:
    """Build the static-site landing page for a pack."""
    console.print(f"[yellow]asset-forge showroom: not implemented (Phase 6)[/yellow]")


if __name__ == "__main__":
    app()
