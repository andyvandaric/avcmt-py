#!/usr/bin/env python3
"""Show available CLI commands for project maintenance with color output."""

from rich.console import Console
from rich.table import Table

from avcmt.utils import setup_logging

logger = setup_logging("log/help_command.log")


def main():
    console = Console()
    # Heading pakai .rule() biar tebal, center, dan clean
    console.rule(
        "[bold blue]avcmt-py Maintenance Commands[/]", style="blue", align="center"
    )
    console.print("  \n")
    table = Table(show_header=False, box=None, pad_edge=False, collapse_padding=True)
    # Kolom kiri (command), lebar tetap, kanan (desc), lebar bebas
    table.add_column("", justify="right", no_wrap=True, width=10)
    table.add_column("", justify="left")
    table.add_row(
        "[red]preflight[/]",
        "Run full quality pipeline: setup → format → lintfix → check",
    )
    table.add_row(
        "[green]setup[/]", "Install dependencies, pre-commit, and clean cache files"
    )
    table.add_row(
        "[cyan]clean[/]", "Remove all __pycache__ folders and .pyc/.pyo files"
    )
    table.add_row("[magenta]format[/]", "Format codebase with Ruff Format and auto-fix")
    table.add_row("[yellow]lintfix[/]", "Run Ruff lint + auto-fix (import order, etc)")
    table.add_row("[cyan]check[/]", "Run all pre-commit hooks on all files")
    table.add_row("[white]helper[/]", "Show this list of available commands")

    console.print(table)
    console.print("\n[bold]Run with:[/]")
    console.print("  poetry run setup")
    console.print("  poetry run clean")
    console.print("  poetry run format")
    console.print("  poetry run lintfix")
    console.print("  poetry run check")
    console.print("  poetry run helper\n")
    logger.info("Displayed help commands.")
    console.print("  \n")


if __name__ == "__main__":
    main()
