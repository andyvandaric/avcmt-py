# >> avcmt/cli/docs.py
# Copyright 2025 Andy Vandaric
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# File: avcmt/cli/docs.py
# FINAL REVISION: Orchestrates non-blocking execution via DocGenerator
# and handles CTRL+C gracefully using a context manager.

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from avcmt.modules.doc_generator import DocGenerator, DocGeneratorError
from avcmt.utils import (
    clear_docs_dry_run_file,
    graceful_shutdown_manager,
    read_docs_dry_run_file,
    setup_logging,
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
) -> None:
    """
    Main command to generate or update docstrings for Python files.
    """
    logger = setup_logging("docs.log")
    mode = "DRY RUN" if dry_run else "LIVE RUN"
    scope = "ALL FILES" if all_files else "CHANGED FILES"
    logger.info(f"Starting doc updater (Mode: {mode} | Scope: {scope})")

    # Use the graceful shutdown context manager
    with graceful_shutdown_manager() as shutdown_event:
        try:
            generator = DocGenerator(
                shutdown_event=shutdown_event,
                debug=debug,
            )
            generator.run(
                path=path,
                dry_run=dry_run,
                all_files=all_files,
                force_rebuild=force_rebuild,
            )

        except DocGeneratorError as e:
            typer.secho(f"❌ Error: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        except Exception as e:
            # Catch unexpected errors, especially useful during development
            if not shutdown_event.is_set():
                logger.critical(f"An unexpected error occurred: {e}", exc_info=debug)
                typer.secho(
                    f"❌ An unexpected error occurred: {e}",
                    fg=typer.colors.RED,
                    err=True,
                )
            raise typer.Exit(code=1)

    if shutdown_event.is_set():
        logger.warning("Process was aborted by user.")
    else:
        logger.info("Process finished successfully.")


@app.command("list-cached")
def list_cached() -> None:
    """Displays the content of the last docs dry-run cache."""
    content = read_docs_dry_run_file()
    if content:
        typer.secho("--- Last Cached Docs Dry-Run ---", fg=typer.colors.CYAN)
        typer.echo(content)
    else:
        typer.secho("[i] No docs dry-run cache file found.", fg=typer.colors.YELLOW)


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
