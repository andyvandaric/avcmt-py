# =================================================================
# File: avcmt/cli/commit.py (REVISED FOR SUB-COMMANDS)
#
# This file now defines a group of commands under `commit`.
# The main logic is moved to a 'run' subcommand.
# =================================================================

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

# File: avcmt/cli/commit.py
# Description: CLI sub-command group for all `commit` related actions.
# test1

from typing import Annotated

import typer

from avcmt.modules.commit_generator import run_commit_group_all
from avcmt.utils import (
    clear_dry_run_file,
    get_log_file,
    get_staged_files,
    read_dry_run_file,
    setup_logging,
)

# Import the business logic and new utility functions


# RE-INTRODUCED: A Typer app for the 'commit' command group.
app = typer.Typer(
    name="commit",
    help="Generate AI-powered commits and manage related utilities.",
    no_args_is_help=True,
)


@app.command("run")
def run_commit(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Preview commit messages without applying to git.",
        ),
    ] = False,
    push: Annotated[
        bool,
        typer.Option(
            "--push",
            help="Push commits to the remote repository after completion.",
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Enable debug mode to show prompts and raw AI responses.",
        ),
    ] = False,
    force_rebuild: Annotated[
        bool,
        typer.Option(
            "--force-rebuild",
            help="Ignore recent dry-run cache and force new AI suggestions.",
        ),
    ] = False,
) -> None:
    """Performs a commit operation with optional dry-run, push, debug, and rebuild settings, while configuring logging and invoking the commit process.
    Initializes logging, logs the provided options, and executes the commit process with the specified parameters.

    Args:
        dry_run (bool): If True, previews commit messages without applying to git. Defaults to False.
        push (bool): If True, pushes commits to the remote repository after completion. Defaults to False.
        debug (bool): If True, enables debug mode to show prompts and raw AI responses. Defaults to False.
        force_rebuild (bool): If True, ignores recent dry-run cache and forces new AI suggestions. Defaults to False.

    Returns:
        None
    """
    log_file = get_log_file()
    logger = setup_logging(log_file)
    logger.info(f"Log file for this run: {log_file}")
    logger.info("Invoking 'commit run' command with options:")
    logger.info(f"  dry_run: {dry_run}, push: {push}")
    logger.info(f"  debug: {debug}, force_rebuild: {force_rebuild}")

    run_commit_group_all(
        dry_run=dry_run,
        push=push,
        debug=debug,
        force_rebuild=force_rebuild,
        logger=logger,
    )


@app.command("clear-cache")
def clear_cache() -> None:
    """Deletes the dry-run cache file if it exists, providing user feedback on the operation's success or failure.

    Args:
        None

    Returns:
        None
    """
    if clear_dry_run_file():
        typer.secho(
            "✅ Dry-run cache file cleared successfully.", fg=typer.colors.GREEN
        )
    else:
        typer.secho("[i] No dry-run cache file found to clear.", fg=typer.colors.YELLOW)


@app.command("list-cached")
def list_cached() -> None:
    """Displays the content of the last dry-run cache, indicating whether a cache exists and printing its contents if available. This function reads the dry-run cache file and outputs its contents to the terminal with appropriate messaging based on cache presence.

    Args:
        None

    Returns:
        None
    """
    content = read_dry_run_file()
    if content:
        typer.secho("--- Last Cached Dry-Run Messages ---", fg=typer.colors.CYAN)
        typer.echo(content)
    else:
        typer.secho("[i] No dry-run cache file found.", fg=typer.colors.YELLOW)


@app.command("validate")
def validate() -> None:
    """Checks for staged files and provides user feedback accordingly, without returning any value.

    Args:
        None

    Returns:
        None
    """
    staged_files = get_staged_files()
    if staged_files:
        typer.secho(
            f"✅ Found {len(staged_files)} staged file(s):", fg=typer.colors.GREEN
        )
        for file in staged_files:
            typer.echo(f"- {file}")
    else:
        typer.secho(
            "❌ No staged files found. Use 'git add <files>' to stage changes.",
            fg=typer.colors.RED,
        )
