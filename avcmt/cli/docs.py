# Copyright 2025 Andy Vandaric
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# File: avcmt/cli/docs.py
# FINAL REVISION: Orchestrates non-blocking execution via DocGenerator
# and handles CTRL+C gracefully using a context manager.

import logging
import sys
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from avcmt.modules.doc_generator import DocGenerator, DocGeneratorError
from avcmt.system.context_managers import GracefulShutdownManager
from avcmt.utils import (
    clear_docs_dry_run_file,
    clear_log_file,
    get_docs_dry_run_file,
    get_log_file,
    setup_logging,
    windows_safe_exit,
)

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
dotenv_path = PROJECT_ROOT / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# Setup Typer app
app = typer.Typer(
    name="docs",
    help="🤖 Intelligently generate and format docstrings with AI.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _run_with_process_isolation():
    """Run the main CLI with process isolation to prevent Windows batch job prompt."""
    # DISABLED: Process isolation is causing CTRL+C to not work
    # We'll use a simpler approach with better signal handling instead

    # Remove --isolated flag if present (legacy cleanup)
    if "--isolated" in sys.argv:
        sys.argv.remove("--isolated")


def _setup_logging_and_validation(debug: bool) -> logging.Logger:
    """Setup logging and return logger instance."""
    logger = setup_logging("docs.log", rich_console=True)
    clear_log_file("docs.log")
    return logger


def _log_run_info(logger: logging.Logger, dry_run: bool, all_files: bool) -> None:
    """Log the run information with mode and scope."""
    mode = "DRY RUN" if dry_run else "LIVE RUN"
    scope = "ALL FILES" if all_files else "CHANGED FILES"
    logger.info(
        f"Starting doc updater (Mode: [bold cyan]{mode}[/bold cyan] | Scope: [bold cyan]{scope}[/bold cyan])"
    )


def _execute_doc_generation(
    shutdown_event,
    path: str,
    dry_run: bool,
    all_files: bool,
    force_rebuild: bool,
    debug: bool,
) -> int:
    """Execute the documentation generation process and return exit code."""
    try:
        generator = DocGenerator(shutdown_event=shutdown_event, debug=debug)
        generator.run(
            path=path,
            dry_run=dry_run,
            all_files=all_files,
            force_rebuild=force_rebuild,
        )

        # Check if process was aborted by user
        return 130 if shutdown_event.is_set() else 0

    except DocGeneratorError as e:
        typer.secho(f"❌ Error: {e}", fg=typer.colors.RED, err=True)
        return 1
    except Exception as e:
        if not shutdown_event.is_set():
            logger = logging.getLogger("avcmt")
            logger.critical(f"An unexpected error occurred: {e}", exc_info=debug)
            typer.secho(
                f"❌ An unexpected error occurred: {e}",
                fg=typer.colors.RED,
                err=True,
            )
        return 1


def _show_summary_panel(shutdown_event) -> None:
    """Display the summary panel with file paths."""
    try:
        summary_text = Text()
        if shutdown_event.is_set():
            summary_text.append("PROCESS ABORTED BY USER.", style="bold yellow")
        else:
            summary_text.append("PROCESS COMPLETED.", style="bold green")

        dry_run_path = get_docs_dry_run_file()
        log_path = get_log_file("docs.log")

        # Always show file paths if they exist
        if dry_run_path.exists():
            summary_text.append(f"\n📄 Dry run results: {dry_run_path.as_uri()}")
        if log_path.exists():
            summary_text.append(f"\n📜 Full log file:   {log_path.as_uri()}")

        # Render summary panel
        panel = Panel(
            summary_text, title="[bold]Summary[/bold]", border_style="dim", expand=False
        )
        console = Console()
        console.print(panel)

    except Exception:
        # Fallback: Always show basic file paths even if styling fails
        _show_fallback_summary(shutdown_event)


def _show_fallback_summary(shutdown_event) -> None:
    """Show fallback summary in plain text if Rich styling fails."""
    try:
        print("\n=== SUMMARY ===")
        if shutdown_event.is_set():
            print("PROCESS ABORTED BY USER.")
        else:
            print("PROCESS COMPLETED.")

        dry_run_path = get_docs_dry_run_file()
        log_path = get_log_file("docs.log")

        if dry_run_path.exists():
            print(f"📄 Dry run results: {dry_run_path}")
        if log_path.exists():
            print(f"📜 Full log file:   {log_path}")
        print("================\n")
    except Exception:
        # Final fallback - silently ignore
        pass


@app.command("run")
def run_doc_updater(
    path: Annotated[
        str, typer.Argument(help="The project directory or file to scan.")
    ] = "avcmt",
    all_files: Annotated[
        bool,
        typer.Option("--all-files", help="Process all files, ignoring git changes."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-d", help="Preview changes without modifying files."
        ),
    ] = False,
    force_rebuild: Annotated[
        bool,
        typer.Option("--force-rebuild", help="Ignore cache and force regeneration."),
    ] = False,
    debug: Annotated[
        bool, typer.Option("--debug", help="Enable verbose debug logging.")
    ] = False,
    isolated: Annotated[
        bool,
        typer.Option(
            "--isolated", help="Internal flag for process isolation.", hidden=True
        ),
    ] = False,
) -> None:
    """Main command to generate or update docstrings for Python files."""
    # Setup logging
    logger = _setup_logging_and_validation(debug)
    _log_run_info(logger, dry_run, all_files)

    # ENHANCED: Show mode warning for live runs
    if not dry_run:
        typer.secho(
            "⚠️  LIVE RUN MODE: Files will be modified directly!",
            fg=typer.colors.RED,
            bold=True,
        )
        if not typer.confirm("Continue with live run?"):
            typer.echo("Operation cancelled.")
            return

    # Execute with graceful shutdown handling
    with GracefulShutdownManager() as shutdown_event:
        exit_code = _execute_doc_generation(
            shutdown_event, path, dry_run, all_files, force_rebuild, debug
        )

    # Always show summary panel regardless of termination method
    _show_summary_panel(shutdown_event)

    # Enhanced: Platform-specific clean exit using utility function
    windows_safe_exit(exit_code)


@app.command("list-cached")
def list_cached() -> None:
    """Displays the content of the last docs dry-run cache."""
    dry_run_path = get_docs_dry_run_file()

    if not dry_run_path.exists():
        typer.secho("[i] No docs dry-run cache file found.", fg=typer.colors.YELLOW)
        return

    try:
        content = dry_run_path.read_text(encoding="utf-8")
        if content.strip():
            typer.echo("📄 Docs dry-run cache contents:")
            typer.echo(content)
        else:
            typer.secho("[i] Docs dry-run cache file is empty.", fg=typer.colors.YELLOW)
    except Exception as e:
        typer.secho(f"❌ Error reading cache file: {e}", fg=typer.colors.RED, err=True)


@app.command("clear-cache")
def clear_cache() -> None:
    """Clears the docs dry-run cache file."""
    if clear_docs_dry_run_file():
        typer.secho(
            "✅ Docs dry-run cache file cleared successfully.", fg=typer.colors.GREEN
        )
    else:
        typer.secho(
            "[i] No docs dry-run cache file found to clear.", fg=typer.colors.YELLOW
        )
