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

# File: avcmt/cli.py
# Description:
# Main entry point for the 'avcmt' command.
# Add --force-rebuild option
# Revision - Removed hardcoded API key check for flexibility.
# Status: Ready to use with the new CommitManager.

import argparse
from pathlib import Path

from dotenv import load_dotenv

from .commit import run_commit_group_all
from .utils import get_log_file, setup_logging

PROJECT_ROOT = Path(__file__).resolve().parent.parent
dotenv_path = PROJECT_ROOT / ".env"

if dotenv_path.exists():
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
