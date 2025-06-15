#!/usr/bin/env python3
"""Format codebase using Ruff formatter."""

import subprocess
import sys

from rich import print


def main():
    print("[bold cyan]🎨 Running Ruff Formatter...[/]")
    try:
        subprocess.run(["ruff", "format", "."], check=True)
        print("[bold cyan]✅ Code formatted successfully with Ruff![/]")
    except subprocess.CalledProcessError as e:
        print(f"[bold red]❌ Formatter failed: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
