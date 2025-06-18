#!/usr/bin/env python3
# File: scripts/semrel.py
# Description: CLI Wrapper for ReleaseManager.
# Status: Correct and ready to use.

import argparse
import os
import sys

# Add the project path to sys.path to ensure avcmt can be imported
# This makes the script more reliable when run from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from avcmt.release import ReleaseFailedError, ReleaseManager
except ImportError:
    print(
        "Error: Could not import avcmt modules. "
        "Ensure you have run 'poetry install' and are in the project's virtual environment.",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="avcmt-py internal semantic release tool.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the release process without changing files or git state.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the release commit and tag to the remote repository.",
    )

    args = parser.parse_args()

    try:
        # 1. Create an instance of the manager, it will automatically load the configuration.
        releaser = ReleaseManager()

        # 2. Run the release process with arguments from the CLI.
        new_version = releaser.run(dry_run=args.dry_run, push=args.push)

        # If successful and there is a new version, print it to stdout
        if new_version:
            print(new_version)

    except ReleaseFailedError as e:
        # 3. Handle defined errors from the release process.
        print(f"\n❌ Release Failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # 4. Handle other unexpected errors for debugging.
        print(f"\n❌ An unexpected error occurred: {e}", file=sys.stderr)
        # For better debugging, you can print the traceback
        # import traceback
        # traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
