#!/usr/bin/env python3
"""Run all pre-commit hooks on all files."""

import subprocess
import sys

from rich import print


def main():
    print("[bold yellow]🧪 Running pre-commit checks on all files...[/]")
    try:
        subprocess.run(["pre-commit", "run", "--all-files", "--show-diff-on-failure"], check=True)
        print("[bold green]✅ All pre-commit checks passed![/]")
    except subprocess.CalledProcessError as e:
        print(f"[bold red]❌ Pre-commit check failed: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
