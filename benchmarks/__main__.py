"""Benchmark harness CLI for Alma TV."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from rich.console import Console
from rich.table import Table

console = Console()


def print_instructions() -> None:
    """Print benchmarking instructions."""
    console.print("\n[bold cyan]Alma TV Benchmark Harness[/bold cyan]\n")
    console.print("This harness runs performance benchmarks for Alma TV components.\n")

    console.print("[yellow]Available benchmarks:[/yellow]")
    console.print("  • scanner_bench    - Library scanner performance")
    console.print("  • scheduler_bench  - Scheduler performance (30-day simulation)")
    console.print("  • playback_gap     - Playback gap measurement\n")

    console.print("[yellow]Usage:[/yellow]")
    console.print("  pytest benchmarks/ --benchmark-only")
    console.print("  pytest benchmarks/scanner_bench.py --benchmark-only")
    console.print("  pytest benchmarks/ --benchmark-only --benchmark-json=results.json\n")

    console.print("[yellow]Dry run mode:[/yellow]")
    console.print("  python -m benchmarks --dry-run\n")

    console.print("[yellow]View results:[/yellow]")
    console.print("  python -m benchmarks --results\n")


def load_benchmark_results() -> Dict[str, Any]:
    """Load benchmark results from JSON files."""
    results_dir = Path(__file__).parent / "results"
    results: Dict[str, Any] = {}

    if not results_dir.exists():
        return results

    for result_file in results_dir.glob("*.json"):
        try:
            with open(result_file) as f:
                data = json.load(f)
                results[result_file.stem] = data
        except Exception as e:
            console.print(f"[red]Error loading {result_file}: {e}[/red]")

    return results


def display_results(results: Dict[str, Any]) -> None:
    """Display benchmark results in a table."""
    if not results:
        console.print("[yellow]No benchmark results found.[/yellow]")
        console.print("Run benchmarks with: pytest benchmarks/ --benchmark-only")
        return

    table = Table(title="Benchmark Results", show_header=True)
    table.add_column("Benchmark", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="white")

    for name, data in results.items():
        status = "✓" if data.get("success", False) else "✗"
        details = data.get("summary", "No details available")
        table.add_row(name, status, details)

    console.print(table)


def main() -> int:
    """Main entry point for benchmark harness."""
    parser = argparse.ArgumentParser(
        description="Alma TV Benchmark Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show benchmark instructions without running",
    )
    parser.add_argument(
        "--results",
        action="store_true",
        help="Display benchmark results",
    )

    args = parser.parse_args()

    if args.results:
        results = load_benchmark_results()
        display_results(results)
        return 0

    if args.dry_run:
        print_instructions()
        return 0

    # Default: print instructions
    print_instructions()
    return 0


if __name__ == "__main__":
    sys.exit(main())
