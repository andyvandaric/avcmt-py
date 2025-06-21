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

# File: avcmt/cli/release.py
# Description: Typer sub-command for managing avcmt-py releases.


import typer

# Import absolute from within the package
from avcmt.modules.release_manager import ReleaseFailedError, ReleaseManager
from avcmt.utils import setup_logging

# Initialize logger for this module
logger = setup_logging("log/release_cli.log")

# Create Typer instance for the 'release' sub-command
app = typer.Typer(
    name="release",
    help="📦 Manage project releases (Semantic Release style).",
    no_args_is_help=True,  # Ensure that 'avcmt release' without subcommand shows help
    rich_markup_mode="markdown",
)


# The main release logic is now a sub-command 'run'
@app.command("run")
def run_release_command(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Simulate the release process without changing files or git state.",
    ),
    push: bool = typer.Option(
        False,
        "--push",
        "-p",
        help="Push the release commit and tag to the remote repository.",
    ),
) -> None:
    """Executes the semantic release process, handling version bumping, changelog generation, and optional pushing; manages release failures and unexpected errors gracefully.

    Args:
        dry_run (bool): If True, simulates the release without modifying files or pushing changes. Defaults to False.
        push (bool): If True, pushes the release commit and tags to the remote repository after a successful release. Defaults to False.

    Returns:
        None.
    """
    logger.info("Initiating release process via CLI (run subcommand)...")
    try:
        # 1. Create an instance of the manager, it will automatically load the configuration.
        releaser = ReleaseManager()

        # 2. Run the release process with arguments from the CLI.
        new_version = releaser.run(dry_run=dry_run, push=push)

        # Perubahan: Hanya cetak nomor versi ke stdout untuk penangkapan CI/CD.
        # Pesan deskriptif lain harus ke logger.info atau typer.echo(..., err=True)
        if new_version:
            typer.echo(new_version)  # HANYA mencetak versi, tanpa teks tambahan
            logger.info(f"Release process finished. New version: {new_version}")
        else:
            # Jika tidak ada versi baru, output pesan deskriptif ke stderr atau log
            typer.secho(
                "No new version released (e.g., no semantic commits or dry-run).",
                err=True,
            )
            logger.info("Release process finished. No new version released.")

    except ReleaseFailedError as e:
        # Handle defined errors from the release process.
        typer.secho(f"\n❌ Release Failed: {e}", fg=typer.colors.RED, err=True)
        logger.error(f"Release process failed: {e}", exc_info=True)
        raise typer.Exit(code=1)
    except Exception as e:
        # Handle other unexpected errors for debugging.
        typer.secho(
            f"\n❌ An unexpected error occurred during release: {e}",
            fg=typer.colors.RED,
            err=True,
        )
        logger.critical(f"Unexpected error during release: {e}", exc_info=True)
        raise typer.Exit(code=1)


# If you want to add other sub-commands under 'release' in the future,
# you can add them here using @app.command()
# Example:
# @app.command()
# def status():
#     """Show current release status."""
#     typer.echo("Checking release status...")
