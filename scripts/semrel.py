#!/usr/bin/env python3
"""Semantic Release Workflow Helper - Loads .env and runs semantic-release commands with correct environment, pretty CLI with color."""

import argparse
import os
import subprocess
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()  # auto-load .env into os.environ


def run_cmd(cmd, desc):
    console = Console()
    console.print(f"\n[bold green]$ {' '.join(cmd)}[/]  [dim]| {desc}[/]")
    result = subprocess.run(cmd, shell=False, check=False)
    if result.returncode != 0:
        console.print(f"[bold red]✖ Step failed: {desc}[/]")
        sys.exit(result.returncode)


def print_help():
    console = Console()
    console.rule(
        "[bold blue]avcmt-py Semantic Release Commands[/]", style="blue", align="center"
    )
    console.print("  ")

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column("", justify="right", no_wrap=False, min_width=28)
    table.add_column("", justify="left")
    table.add_row(
        "[cyan]semrel --next-version[/]",
        "Print the next semantic version (no write/tag)",
    )
    table.add_row("[cyan]semrel --next-tag[/]", "Print the next version tag")
    table.add_row(
        "[yellow]semrel --dry-run[/]",
        "Dry-run: Simulate full semantic-release publish (no changes pushed)",
    )
    table.add_row(
        "[green]semrel --changelog[/]", "Generate the changelog for next release"
    )
    table.add_row(
        "[red]semrel --release[/]",
        "Perform real release: version bump, changelog, tag, push to repo",
    )
    table.add_row("[white]semrel -h or [/] [white]--help[/]", "Show this help")
    console.print(table)
    console.print("\n[bold]Usage examples:[/]")
    console.print("  poetry run semrel --next-version")
    console.print("  poetry run semrel --next-tag")
    console.print("  poetry run semrel --dry-run")
    console.print("  poetry run semrel --changelog")
    console.print("  poetry run semrel --release")
    console.print("  poetry run semrel -h\n")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Semantic Release Workflow Helper: auto-load .env and run full semantic-release workflow.",
        add_help=False,
    )
    parser.add_argument(
        "--next-version", action="store_true", help="Print the next semantic version"
    )
    parser.add_argument(
        "--next-tag", action="store_true", help="Print the next version tag"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry-run: Simulate full publish workflow"
    )
    parser.add_argument(
        "--changelog", action="store_true", help="Generate changelog for next release"
    )
    parser.add_argument(
        "--release",
        action="store_true",
        help="Publish real release (tag, changelog, push)",
    )
    parser.add_argument("-h", "--help", action="store_true", help="Show help")

    args = parser.parse_args()
    console = Console()

    if args.help or not any(vars(args).values()):
        print_help()

    gh_token = os.getenv("GH_TOKEN")
    if not gh_token:
        console.print("[bold red]ERROR: GH_TOKEN is missing in .env or ENV![/]")
        sys.exit(1)
    else:
        console.print(f"[bold green]GH_TOKEN loaded: {gh_token[:8]}***[/]")

    if args.next_version:
        run_cmd(
            ["poetry", "run", "semantic-release", "version", "--print"],
            "Show next semantic version",
        )

    if args.next_tag:
        run_cmd(
            ["poetry", "run", "semantic-release", "version", "--print-tag"],
            "Show next tag",
        )

    if args.dry_run:
        run_cmd(
            ["poetry", "run", "semantic-release", "publish", "--dry-run"],
            "Dry-run publish (simulate, nothing pushed)",
        )

    if args.changelog:
        run_cmd(
            ["poetry", "run", "semantic-release", "changelog"],
            "Generate changelog for next release",
        )

    if args.release:
        console.print(
            "[yellow]You are about to run the REAL semantic-release publish![/]"
        )
        answer = input("Continue with actual release? (y/N): ").strip().lower()
        if answer == "y":
            run_cmd(
                ["poetry", "run", "semantic-release", "publish"],
                "Publish (real release)",
            )
        else:
            console.print("[bold red]Release aborted by user.[/]")
            sys.exit(0)


if __name__ == "__main__":
    main()
