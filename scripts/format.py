#!/usr/bin/env python3
"""Format codebase using Ruff formatter and log results."""

import subprocess
import sys

from avcmt.utils import setup_logging

logger = setup_logging("format_codebase.log")


def run_formatter():
    try:
        logger.info("🎨 Running Ruff formatter...")
        subprocess.run(["ruff", "format", "."], check=True)
        logger.info("✅ Code formatted successfully with Ruff.")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ruff formatter failed: {e}")
        sys.exit(1)


def main():
    run_formatter()


if __name__ == "__main__":
    main()
