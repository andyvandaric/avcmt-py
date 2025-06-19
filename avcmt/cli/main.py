# =================================================================
# File: avcmt/cli/main.py (REVISED)
#
# We revert to using `add_typer` to register the entire command group.
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

# File: avcmt/cli/main.py
# Description: Main entry point for the unified Typer CLI application.

from pathlib import Path
from typing import Annotated

import toml
import typer

# --- Sub-command Imports ---
# CHANGE: We now import the module as an 'app' to be added.
from .commit import app as commit_app
from .release import app as release_app  # ADDED: Import the release Typer app

app = typer.Typer(
    name="avcmt",
    help="avcmt-py: AI-Powered Git Commit & Release Automation.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# ... (your existing _version_callback function remains here) ...


def _version_callback(value: bool) -> None:
    """Callback to display the application version and exit."""
    if value:
        try:
            pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
            pyproject_data = toml.load(pyproject_path)
            version = pyproject_data["tool"]["poetry"]["version"]
            typer.echo(f"avcmt-py version: {version}")
        except (FileNotFoundError, KeyError):
            typer.secho(
                "Error: Could not determine version. Is pyproject.toml missing or malformed?",
                fg=typer.colors.RED,
                err=True,
            )
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=_version_callback,
            is_eager=True,
            help="Show the application version and exit.",
        ),
    ] = None,
) -> None:
    """
    AI-Powered toolkit for development automation.
    Use `avcmt [COMMAND] --help` for more information on a specific command.
    """
    pass


# --- Register Sub-commands ---
# CHANGE: We now register the function as a command.
# The decorator automatically handles converting the function's parameters
# into CLI options like --dry-run, --push, etc.
app.add_typer(commit_app)
app.add_typer(release_app)  # ADDED: Register the release Typer app

if __name__ == "__main__":
    app()
