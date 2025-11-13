"""Command-line interface for Alma TV."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from alma_tv.config import get_settings
from alma_tv.logging import configure_logging

app = typer.Typer(
    name="alma",
    help="Alma TV - Raspberry Pi automation suite for children's programming",
    add_completion=False,
)

console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
) -> None:
    """Alma TV CLI."""
    settings = get_settings()
    if debug or settings.debug:
        configure_logging(log_level="DEBUG", log_file=settings.log_file)
    else:
        configure_logging(log_level=settings.log_level, log_file=settings.log_file)


# Config commands
config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show current configuration."""
    settings = get_settings()

    if json_output:
        # Convert to dict, handling Path objects
        config_dict = {}
        for field_name, field_info in settings.model_fields.items():
            value = getattr(settings, field_name)
            if isinstance(value, Path):
                config_dict[field_name] = str(value)
            else:
                config_dict[field_name] = value
        rprint(json.dumps(config_dict, indent=2))
    else:
        table = Table(title="Alma TV Configuration", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        for field_name, field_info in settings.model_fields.items():
            value = getattr(settings, field_name)
            # Don't show sensitive values in full
            if field_name == "database_url" and "://" in str(value):
                display_value = str(value).split("://")[0] + "://..."
            else:
                display_value = str(value)
            table.add_row(field_name, display_value)

        console.print(table)


# Library commands (stubs for now)
library_app = typer.Typer(help="Media library management")
app.add_typer(library_app, name="library")


@library_app.command("list")
def library_list() -> None:
    """List series in the library."""
    rprint("[yellow]Library listing not yet implemented[/yellow]")


@library_app.command("scan")
def library_scan(
    path: Optional[str] = typer.Argument(None, help="Path to scan"),
) -> None:
    """Scan media library for new content."""
    settings = get_settings()
    scan_path = path or str(settings.media_root)
    rprint(f"[yellow]Scanning {scan_path} (not yet implemented)[/yellow]")


# Schedule commands (stubs for now)
schedule_app = typer.Typer(help="Schedule management")
app.add_typer(schedule_app, name="schedule")


@schedule_app.command("today")
def schedule_today() -> None:
    """Show today's schedule."""
    rprint("[yellow]Schedule generation not yet implemented[/yellow]")


@schedule_app.command("show")
def schedule_show(
    date: Optional[str] = typer.Option(None, "--date", help="Date (YYYY-MM-DD)"),
    preview: bool = typer.Option(False, "--preview", help="Preview mode"),
) -> None:
    """Show schedule for a specific date."""
    rprint(f"[yellow]Schedule for {date or 'today'} (not yet implemented)[/yellow]")


# Playback commands (stubs for now)
playback_app = typer.Typer(help="Playback control")
app.add_typer(playback_app, name="playback")


@playback_app.command("run")
def playback_run() -> None:
    """Run playback orchestrator daemon."""
    rprint("[yellow]Playback orchestrator not yet implemented[/yellow]")


# Clock commands (stubs for now)
clock_app = typer.Typer(help="Clock display")
app.add_typer(clock_app, name="clock")


@clock_app.command("run")
def clock_run() -> None:
    """Run clock display service."""
    rprint("[yellow]Clock service not yet implemented[/yellow]")


if __name__ == "__main__":
    app()
