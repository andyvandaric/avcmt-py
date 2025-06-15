# File: avcmt/cli.py

import argparse
import os
import sys

from dotenv import load_dotenv

from .commit import run_commit_group_all
from .utils import get_log_file, setup_logging

# Locate the .env file in the project root directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)

if not os.getenv("POLLINATIONS_API_KEY"):
    print(
        "Error: POLLINATIONS_API_KEY is not set! Please create a .env file in the project root or set the environment variable."
    )
    sys.exit(1)


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

    args = parser.parse_args()

    logger = setup_logging(get_log_file())

    # ✅ Explicit argument passing (BUG FIXED + future-proof)
    run_commit_group_all(
        dry_run=args.dry_run, push=args.push, debug=args.debug, logger=logger
    )


if __name__ == "__main__":
    main()
