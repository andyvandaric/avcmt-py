# =================================================================
# File: avcmt/cli/commit.py (REVISED)
#
# We will simplify this file. It no longer needs its own Typer app.
# It will just be a regular function that we import into main.py.
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
# Description: CLI command logic for `avcmt commit`.

from typing import Annotated

import typer

from avcmt.modules.commit_generator import run_commit_group_all
from avcmt.utils import get_log_file, setup_logging

# Import the business logic from the modules layer


# NOTE: The `app = typer.Typer(...)` instance is REMOVED from this file.


# This is now a regular function, not a Typer callback.
def commit(
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
    """
    Generates semantic commit messages for staged changes by grouping them
    and using an AI provider.
    """
    log_file = get_log_file()
    logger = setup_logging(log_file)
    logger.info(f"Log file for this run: {log_file}")
    logger.info("Invoking 'commit' command with options:")
    logger.info(f"  dry_run: {dry_run}, push: {push}")
    logger.info(f"  debug: {debug}, force_rebuild: {force_rebuild}")

    # This is the bridge: call the business logic from the `modules` layer
    # and pass all the CLI options to it.
    run_commit_group_all(
        dry_run=dry_run,
        push=push,
        debug=debug,
        force_rebuild=force_rebuild,
        logger=logger,
    )
