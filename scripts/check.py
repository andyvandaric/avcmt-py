#!/usr/bin/env python3
"""Run all pre-commit hooks on all files."""

import subprocess
import sys

from avcmt.utils import setup_logging

logger = setup_logging("log/precommit_check.log")  # atau langsung default log


def main():
    logger.info("🧪 Running pre-commit checks on all files...")
    try:
        subprocess.run(
            ["pre-commit", "run", "--all-files", "--show-diff-on-failure"], check=True
        )
        logger.info("✅ All pre-commit checks passed!")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Pre-commit check failed: {e}")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("❌ pre-commit not found. Make sure it's installed and on PATH.")
        sys.exit(2)


if __name__ == "__main__":
    main()
