#!/usr/bin/env python3
"""Run Ruff lint checks and apply auto-fixes."""

import subprocess
import sys

from rich import print


def main():
    print("[bold green]🔍 Running Ruff Lint Fix...[/]")
    try:
        subprocess.run(["ruff", "check", ".", "--fix"], check=True)
        subprocess.run(["ruff", "format", "."], check=True)
        print("[bold green]✅ Ruff linting and formatting complete![/]")
    except subprocess.CalledProcessError as e:
        print(f"[bold red]❌ Error during lint fix: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
