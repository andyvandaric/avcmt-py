#!/usr/bin/env python3
"""Run Ruff lint checks and apply auto-fixes with logging."""

import subprocess
import sys

from avcmt.utils import setup_logging

logger = setup_logging("lintfix_codebase.log")


def run_lintfix():
    try:
        logger.info("🔍 Running Ruff Lint + Auto Fix...")
        subprocess.run(["ruff", "check", ".", "--fix"], check=True)
        subprocess.run(["ruff", "format", "."], check=True)
        logger.info("✅ Ruff linting and formatting completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error during Ruff lint fix: {e}")
        sys.exit(1)


def main():
    run_lintfix()


if __name__ == "__main__":
    main()
