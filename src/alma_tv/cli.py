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


# Library commands
library_app = typer.Typer(help="Media library management")
app.add_typer(library_app, name="library")


@library_app.command("list")
def library_list(
    series: Optional[str] = typer.Option(None, "--series", "-s", help="Filter by series"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List series or episodes in the library."""
    from alma_tv.database import init_db
    from alma_tv.library import LibraryService

    init_db()
    service = LibraryService()

    if series:
        # List episodes for specific series
        episodes = service.list_episodes(series=series)
        if json_output:
            rprint(
                json.dumps(
                    [
                        {
                            "id": ep.id,
                            "series": ep.series,
                            "season": ep.season,
                            "episode_code": ep.episode_code,
                            "title": ep.title,
                            "duration_seconds": ep.duration_seconds,
                        }
                        for ep in episodes
                    ],
                    indent=2,
                )
            )
        else:
            table = Table(title=f"{series} Episodes", show_header=True)
            table.add_column("ID", style="cyan")
            table.add_column("Episode", style="green")
            table.add_column("Title", style="white")
            table.add_column("Duration", style="yellow")

            for ep in episodes:
                table.add_row(
                    str(ep.id),
                    ep.episode_code,
                    ep.title or "",
                    f"{ep.duration_seconds // 60}m {ep.duration_seconds % 60}s",
                )

            console.print(table)
    else:
        # List all series
        series_list = service.list_series()
        if json_output:
            rprint(json.dumps(series_list, indent=2))
        else:
            table = Table(title="Media Library", show_header=True)
            table.add_column("Series", style="cyan")
            table.add_column("Episodes", style="green")
            table.add_column("Total Duration", style="yellow")

            for s in series_list:
                total_mins = s["total_duration_seconds"] // 60
                table.add_row(str(s["series"]), str(s["episode_count"]), f"{total_mins}m")

            console.print(table)


@library_app.command("scan")
def library_scan(
    path: Optional[str] = typer.Argument(None, help="Path to scan"),
) -> None:
    """Scan media library for new content."""
    from alma_tv.database import init_db
    from alma_tv.library import Scanner

    settings = get_settings()
    scan_path = Path(path) if path else settings.media_root

    rprint(f"[cyan]Scanning media library:[/cyan] {scan_path}")

    init_db()
    scanner = Scanner(media_root=scan_path)

    with console.status("[bold green]Scanning...", spinner="dots"):
        summary = scanner.scan_directory()

    rprint(f"\n[green]Scan complete![/green]")
    rprint(f"  • Scanned: {summary['scanned']} files")
    rprint(f"  • Added: {summary['added']} videos")
    rprint(f"  • Updated: {summary.get('updated', 0)} videos")
    rprint(f"  • Failed: {summary['failed']} files")


# Schedule commands
schedule_app = typer.Typer(help="Schedule management")
app.add_typer(schedule_app, name="schedule")


@schedule_app.command("today")
def schedule_today(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    generate: bool = typer.Option(False, "--generate", help="Generate if not exists"),
) -> None:
    """Show today's schedule."""
    from datetime import date

    from alma_tv.database import init_db
    from alma_tv.scheduler import LineupGenerator

    init_db()
    today = date.today()

    _show_schedule(today, json_output, generate)


@schedule_app.command("show")
def schedule_show(
    target_date: Optional[str] = typer.Argument(None, help="Date (YYYY-MM-DD)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    generate: bool = typer.Option(False, "--generate", "-g", help="Generate if not exists"),
) -> None:
    """Show schedule for a specific date."""
    from datetime import date, datetime

    from alma_tv.database import init_db

    init_db()

    if target_date:
        try:
            show_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            rprint(f"[red]Invalid date format: {target_date}. Use YYYY-MM-DD[/red]")
            raise typer.Exit(1)
    else:
        show_date = date.today()

    _show_schedule(show_date, json_output, generate)


@schedule_app.command("generate")
def schedule_generate(
    target_date: Optional[str] = typer.Argument(None, help="Date (YYYY-MM-DD)"),
    duration: Optional[int] = typer.Option(None, "--duration", help="Target duration in minutes"),
) -> None:
    """Generate lineup for a specific date."""
    from datetime import date, datetime

    from alma_tv.database import init_db
    from alma_tv.scheduler import LineupGenerator

    init_db()

    if target_date:
        try:
            show_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            rprint(f"[red]Invalid date format: {target_date}. Use YYYY-MM-DD[/red]")
            raise typer.Exit(1)
    else:
        show_date = date.today()

    rprint(f"[cyan]Generating lineup for {show_date}...[/cyan]")

    generator = LineupGenerator()

    with console.status("[bold green]Generating...", spinner="dots"):
        session_id = generator.generate_lineup(
            target_date=show_date, target_duration_minutes=duration
        )

    if session_id:
        rprint(f"[green]✓ Lineup generated![/green] Session ID: {session_id}")
        _show_schedule(show_date, json_output=False, generate=False)
    else:
        rprint("[red]Failed to generate lineup[/red]")
        raise typer.Exit(1)


def _show_schedule(show_date: date, json_output: bool, generate: bool) -> None:
    """Helper to show schedule details."""
    from datetime import datetime

    from alma_tv.database import Session, get_db
    from alma_tv.scheduler import LineupGenerator

    with get_db() as db:
        session = (
            db.query(Session)
            .filter(Session.show_date == datetime.combine(show_date, datetime.min.time()))
            .first()
        )

        if not session and generate:
            rprint(f"[yellow]No lineup exists for {show_date}, generating...[/yellow]")
            generator = LineupGenerator()
            session_id = generator.generate_lineup(target_date=show_date)
            session = db.query(Session).filter(Session.id == session_id).first()

        if not session:
            rprint(f"[yellow]No lineup exists for {show_date}[/yellow]")
            rprint("Use --generate to create one")
            return

        if json_output:
            schedule_data = {
                "date": show_date.isoformat(),
                "status": session.status.value,
                "total_duration_seconds": session.total_duration_seconds,
                "episodes": [
                    {
                        "slot": ph.slot_order,
                        "series": ph.video.series,
                        "episode_code": ph.video.episode_code,
                        "title": ph.video.title,
                        "duration_seconds": ph.video.duration_seconds,
                        "completed": ph.completed,
                    }
                    for ph in session.play_history
                ],
            }
            rprint(json.dumps(schedule_data, indent=2))
        else:
            # Pretty table output
            table = Table(title=f"Schedule for {show_date}", show_header=True)
            table.add_column("#", style="cyan", width=3)
            table.add_column("Series", style="green")
            table.add_column("Episode", style="yellow")
            table.add_column("Title", style="white")
            table.add_column("Duration", style="magenta")
            table.add_column("Status", style="blue")

            for ph in sorted(session.play_history, key=lambda x: x.slot_order):
                status = "✓" if ph.completed else "○"
                table.add_row(
                    str(ph.slot_order),
                    ph.video.series,
                    ph.video.episode_code,
                    ph.video.title or "",
                    f"{ph.video.duration_seconds // 60}m {ph.video.duration_seconds % 60}s",
                    status,
                )

            console.print(table)

            # Summary
            total_mins = session.total_duration_seconds // 60
            rprint(f"\n[cyan]Status:[/cyan] {session.status.value}")
            rprint(f"[cyan]Total Duration:[/cyan] {total_mins}m {session.total_duration_seconds % 60}s")
            rprint(f"[cyan]Episodes:[/cyan] {len(session.play_history)}")


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
