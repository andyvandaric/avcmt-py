# File: avcmt/cli.py

import argparse
import os
import sys
from .commit import run_commit_group_all
from .utils import setup_logging

if not os.getenv("POLLINATIONS_API_KEY"):
    print("Error: POLLINATIONS_API_KEY is not set! Please create a .env file or set the environment variable.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="avcmt-py: AI-powered Semantic Commit Grouping & Automation"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only show commit messages without committing to git"
    )
    parser.add_argument(
        "--push", action="store_true", help="Push all commits to remote after finishing"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Show debug info (prompt & raw AI response)"
    )
    args = parser.parse_args()
    logger = setup_logging()
    run_commit_group_all(args, logger)

if __name__ == "__main__":
    main()
