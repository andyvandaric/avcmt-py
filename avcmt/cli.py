# File: avcmt/cli.py
# Description:
# Main entry point for the 'avcmt' command.
# Add --force-rebuild option
# Revision - Removed hardcoded API key check for flexibility.
# Status: Ready to use with the new CommitManager.

import argparse
import os

from dotenv import load_dotenv

from .commit import run_commit_group_all
from .utils import get_log_file, setup_logging

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dotenv_path = os.path.join(PROJECT_ROOT, ".env")

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# --- API KEY CHECK BLOCK REMOVED FROM HERE ---
# Specific 'POLLINATIONS_API_KEY' check removed.
# API key validation is now fully handled by the `ai.py` module
# dynamically based on the selected provider.


def main():
    parser = argparse.ArgumentParser(
        prog="avcmt",
        description="avcmt-py: AI-powered Semantic Release Commit Message Grouping & Automation",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show commit messages without committing to git",
    )
    parser.add_argument(
        "--push", action="store_true", help="Push all commits to remote after finishing"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug info (prompt & raw AI response)",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force new AI suggestions, ignoring recent dry-run cache.",
    )
    # You can add an argument to select a provider here in the future
    # Example: parser.add_argument("--provider", default="pollinations", help="AI provider to use.")

    args = parser.parse_args()

    log_file_path = get_log_file()
    logger = setup_logging(log_file_path)
    logger.info(f"Log file initialized at: {log_file_path}")

    run_commit_group_all(
        dry_run=args.dry_run,
        push=args.push,
        debug=args.debug,
        force_rebuild=args.force_rebuild,
        logger=logger,
        # provider=args.provider # <-- if you add the provider argument
    )


if __name__ == "__main__":
    main()
