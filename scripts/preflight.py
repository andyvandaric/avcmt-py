#!/usr/bin/env python3
"""Run full code quality pipeline: setup, format, lintfix, check."""

import subprocess
import sys

from avcmt.utils import setup_logging

logger = setup_logging("preflight_pipeline.log")

STEPS = [
    ("🔧 Environment setup", "poetry run setup"),
    ("🎨 Formatting codebase", "poetry run format"),
    ("🛠️ Lint & autofix issues", "poetry run lintfix"),
    ("🧪 Run pre-commit checks", "poetry run check"),
]


def main():
    logger.info("🚀 Starting preflight quality pipeline...")
    for step_name, cmd in STEPS:
        logger.info(f"👉 {step_name}...")
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Step failed: {step_name}. Error: {e}")
            sys.exit(1)
    logger.info("✅ Preflight quality pipeline completed successfully!")


if __name__ == "__main__":
    main()
