#!/usr/bin/env python3
"""Setup project environment: poetry install, pre-commit install, clean cache, with logging."""

import subprocess
import sys

from avcmt.utils import setup_logging

logger = setup_logging("log/setup_project.log")


def run_cmd(cmd, desc):
    logger.info(f"🔧 {desc}: {cmd}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed: {desc} ({e})")
        sys.exit(1)


def main():
    logger.info("🛠️ Setting up Python project environment...")
    run_cmd(["poetry", "install"], "Installing dependencies via Poetry")
    run_cmd(["poetry", "run", "pre-commit", "install"], "Installing pre-commit hooks")
    run_cmd(["poetry", "run", "clean"], "Cleaning Python cache files")
    logger.info("✅ Setup completed successfully!")


if __name__ == "__main__":
    main()
