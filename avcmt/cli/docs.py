# >> avcmt/cli/docs.py
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
# FINAL REVISION: Unified into a single 'run' command with intelligent tracking.

from typing import Annotated

import typer

from avcmt.modules.doc_generator import DocGenerator, DocGeneratorError
from avcmt.utils import (
    clear_docs_dry_run_file,
    get_docs_dry_run_file,
    read_docs_dry_run_file,
)

app = typer.Typer(
    name="docs",
    help="🤖 Intelligently generate and format docstrings with AI.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@app.command("run")
def run_doc_updater(
    path: Annotated[
        str, typer.Argument(help="The project directory to scan.")
    ] = "avcmt",
    all_files: Annotated[
        bool,
        typer.Option(
            "--all-files",
            help="Process all files, ignoring modification times.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Preview changes in a log file without modifying source code.",
        ),
    ] = False,
    force_rebuild: Annotated[
        bool,
        typer.Option(
            "--force-rebuild",
            help="Ignore recent dry-run cache and force new AI suggestions.",
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug", help="Enable debug mode for prompts and raw AI responses."
        ),
    ] = False,
) -> None:
    """Performs the documentation update process for project files, supporting dry run mode, full file processing, debugging, and error handling.
    Raises a `typer.Exit` exception with code 1 if an error occurs, including specific handling for `DocGeneratorError`.
    Args:
        path (str): The directory of the project to scan for documentation updates. Defaults to "avcmt".
        all_files (bool): If True, processes all files regardless of modification time. Defaults to False.
        dry_run (bool): If True, performs a preview of changes without modifying files, outputting suggestions to a log. Defaults to False.
        force_rebuild (bool): If True, ignores cache and forces new AI suggestions for all files. Defaults to False.
        debug (bool): If True, enables debug mode to show prompts and raw AI responses. Defaults to False.
    Returns: None.
    """
    mode = "DRY RUN" if dry_run else "LIVE RUN"
    scope = "ALL FILES" if all_files else "CHANGED FILES ONLY"
    typer.secho(
        f"Starting docstring updater ({mode} | SCOPE: {scope})...", fg=typer.colors.CYAN
    )

    try:
        generator = DocGenerator(debug=debug)
        generator.run(
            path=path, dry_run=dry_run, all_files=all_files, force_rebuild=force_rebuild
        )

        if dry_run:
            typer.secho(
                f"\n✅ Dry run complete. Check the suggestions in {get_docs_dry_run_file()}",
                fg=typer.colors.GREEN,
            )
        else:
            typer.secho(
                "\n✅ Docstring update process complete.", fg=typer.colors.GREEN
            )

    except DocGeneratorError as e:
        typer.secho(f"❌ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(
            f"❌ An unexpected error occurred: {e}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)


@app.command("list-cached")
def list_cached() -> None:
    """Displays the content of the last documentation dry-run cache, showing cached output if available. This function reads the cache file and outputs its contents to the console with styled messages. It does not take any arguments and does not return a value.

    Args:
        None
    Returns:
        None
    """
    content = read_docs_dry_run_file()
    if content:
        typer.secho("--- Last Cached Docs Dry-Run ---", fg=typer.colors.CYAN)
        typer.echo(content)
    else:
        typer.secho("[i] No docs dry-run cache file found.", fg=typer.colors.YELLOW)


@app.command("clear-cache")
def clear_cache() -> None:
    """Deletes the docs dry-run cache file if it exists and provides user feedback. This function attempts to remove the cache file used for dry-run documentation generation. If the cache file is successfully deleted, it displays a success message; if no cache file is found, it informs the user accordingly.

    Args:
        None

    Returns:
        None

    Raises:
        Exceptions that may be raised by `clear_docs_dry_run_file()` or `typer.secho()`, such as I/O errors or other unforeseen issues during file removal or message display.
    """
    if clear_docs_dry_run_file():
        typer.secho(
            "✅ Docs dry-run cache file cleared successfully.", fg=typer.colors.GREEN
        )
    else:
        typer.secho(
            "[i] No docs dry-run cache file found to clear.", fg=typer.colors.YELLOW
        )
