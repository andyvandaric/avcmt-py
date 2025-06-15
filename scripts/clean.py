#!/usr/bin/env python3
"""Clean Python cache files (__pycache__ directories and .pyc/.pyo files) with logging."""

import os
import shutil

from avcmt.utils import setup_logging

logger = setup_logging("log/clean_pycache.log")


def remove_pycache_and_pyc():
    removed_dirs = 0
    removed_files = 0
    for root, dirs, files in os.walk("."):
        # Hapus direktori __pycache__
        for dir_name in dirs:
            if dir_name == "__pycache__":
                dir_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(dir_path)
                    logger.info(f"Removed directory: {dir_path}")
                    removed_dirs += 1
                except Exception as e:
                    logger.warning(f"Failed to remove directory {dir_path}: {e}")

        # Hapus file .pyc / .pyo
        for file_name in files:
            if file_name.endswith((".pyc", ".pyo")):
                file_path = os.path.join(root, file_name)
                try:
                    os.remove(file_path)
                    logger.info(f"Removed file: {file_path}")
                    removed_files += 1
                except Exception as e:
                    logger.warning(f"Failed to remove file {file_path}: {e}")

    logger.info(
        f"✅ Done. Removed {removed_dirs} __pycache__ dirs and {removed_files} .pyc/.pyo files."
    )


def main():
    logger.info("🧹 Cleaning Python cache files...")
    remove_pycache_and_pyc()


if __name__ == "__main__":
    main()
