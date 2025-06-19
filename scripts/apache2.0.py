"""
Script to migrate a project's license to Apache License 2.0.

This script ensures full compliance with Apache 2.0 guidelines by:
- Creating LICENSE and NOTICE files.
- Inserting a dynamically generated license header, including the copyright line,
  into all relevant source files.
- Correctly handling files with a shebang (#!/usr/bin/env python).
- Skipping files that already have a license header.
- Updating pyproject.toml with the correct license identifier.
- Updating README.md with a single, best-practice license badge linking
  to the local LICENSE file.
- Creating a timestamped backup before modifying any file.
"""

import logging
import os
import re
import shutil
import sys
from datetime import datetime

# Try to import third-party libraries, provide a message on failure.
try:
    import requests
    import toml
except ImportError as e:
    print(f"Error: Dependency not found -> {e}")
    print("Please install the required libraries: pip install requests toml")
    sys.exit(1)


# --- CONFIGURATION ---
# Directories where the main source code is located.
# 'scripts' directory is intentionally excluded to focus on core library code.
SOURCE_DIRS = ["avcmt", "tests"]
# File extensions to which the license header will be added
TARGET_EXTENSIONS = [".py", ".sh"]
# Standard file URLs and paths
LICENSE_URL = "https://www.apache.org/licenses/LICENSE-2.0.txt"
LICENSE_OUTPUT_PATH = "LICENSE"
NOTICE_PATH = "NOTICE"
PYPROJECT_PATH = "pyproject.toml"
README_PATH = "README.md"
# Main directory for storing backups
BACKUP_ROOT = "backup"
# Log file path
LOG_FILE_PATH = "log/license_migration.log"

# --- TEMPLATES AND PATTERNS ---
# Header template, now includes placeholders for copyright info.
# This matches the official Apache Foundation recommendation.
APACHE_HEADER_TEMPLATE = """# Copyright {year} {copyright_holder}
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
"""

# Pattern to find and replace the old MIT license badge in README
LICENSE_BADGE_PATTERN = re.compile(
    r"\[!\[License.*MIT.*?\]\(.*?\)\]\(.*?\)", re.IGNORECASE
)

# Best-practice single badge linking to the local LICENSE file.
NEW_LICENSE_BADGE = f"[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=for-the-badge)]({LICENSE_OUTPUT_PATH})"


def setup_logging(log_path: str) -> logging.Logger:
    """Sets up logging to output to both a file and the console."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger_instance = logging.getLogger("license_migration")
    logger_instance.setLevel(logging.INFO)

    if logger_instance.hasHandlers():
        logger_instance.handlers.clear()

    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger_instance.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger_instance.addHandler(console_handler)

    return logger_instance


# Initialize global logger
logger = setup_logging(LOG_FILE_PATH)


def create_timestamped_backup(file_path: str, backup_dir: str) -> str:
    """Creates a backup of a file into a timestamped backup directory."""
    if not os.path.exists(file_path):
        return ""
    try:
        rel_path = os.path.relpath(file_path)
        backup_path_full = os.path.join(backup_dir, rel_path)
        os.makedirs(os.path.dirname(backup_path_full), exist_ok=True)
        shutil.copy2(file_path, backup_path_full)
        return backup_path_full
    except Exception as e:
        logger.error(f"❌ Failed to create backup for {file_path}: {e}")
        return ""


def insert_apache_header(file_path: str, backup_dir: str, copyright_info: dict) -> bool:
    """
    Inserts the dynamically generated Apache 2.0 license header into a file.

    Args:
        file_path: Path to the file to be modified.
        backup_dir: The backup directory to use.
        copyright_info: A dict containing 'year' and 'copyright_holder'.

    Returns:
        True if the header was inserted, False if skipped.
    """
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        if not lines:
            logger.warning(f"⏩ Skipping empty file: {file_path}")
            return False

        if any("Licensed under the Apache License" in line for line in lines[:15]):
            logger.info(f"⏩ License already exists, skipping: {file_path}")
            return False

        backup = create_timestamped_backup(file_path, backup_dir)
        if not backup:
            return False

        shebang = ""
        encoding_line = ""
        content_start_index = 0
        if lines[0].startswith("#!"):
            shebang = lines[0]
            content_start_index = 1

        if len(lines) > content_start_index and "coding:" in lines[content_start_index]:
            encoding_line = lines[content_start_index]
            content_start_index += 1

        # Generate the full header text with copyright info
        header_text = APACHE_HEADER_TEMPLATE.format(**copyright_info)

        docstring_or_content = "".join(lines[content_start_index:])
        new_content = (
            shebang + encoding_line + header_text + "\n" + docstring_or_content
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        logger.info(f"✅ Header inserted: {file_path} | Backup: {backup}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to process file {file_path}: {e}")
        return False


def update_source_files(backup_dir: str, copyright_info: dict):
    """Walks through source directories and updates files with the license header."""
    logger.info("\n--- Updating Source Files with License Header ---")
    changed_count = 0
    total_files = 0
    for directory in SOURCE_DIRS:
        if not os.path.isdir(directory):
            logger.warning(f"Source directory '{directory}' not found.")
            continue
        for subdir, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in TARGET_EXTENSIONS):
                    total_files += 1
                    file_path = os.path.join(subdir, file)
                    if insert_apache_header(file_path, backup_dir, copyright_info):
                        changed_count += 1
    logger.info(
        f"🔧 Total source files updated: {changed_count} of {total_files} relevant files."
    )


def get_copyright_holder() -> str:
    """Gets the copyright holder's name from pyproject.toml."""
    try:
        data = toml.load(PYPROJECT_PATH)
        authors = data.get("tool", {}).get("poetry", {}).get("authors", [])
        if not authors:
            logger.warning(
                "⚠️ No 'authors' found in pyproject.toml. Using a placeholder."
            )
            return "[Copyright Holder Name]"
        author_full = authors[0]
        author_name = author_full.split("<")[0].strip()
        return author_name if author_name else "[Copyright Holder Name]"
    except (FileNotFoundError, toml.TomlDecodeError) as e:
        logger.error(f"❌ Failed to read pyproject.toml: {e}. Using a placeholder.")
        return "[Copyright Holder Name]"


def write_license_and_notice(author: str, year: int):
    """Downloads and writes the LICENSE and NOTICE files."""
    logger.info("\n--- Creating LICENSE and NOTICE files ---")
    try:
        response = requests.get(LICENSE_URL, timeout=10)
        response.raise_for_status()
        license_template = response.text

        # **FIX:** Replace placeholders in the downloaded LICENSE file content.
        license_content = license_template.replace("[yyyy]", str(year)).replace(
            "[name of copyright owner]", author
        )

        with open(LICENSE_OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(license_content)
        logger.info(f"📄 LICENSE file successfully created for {author} ({year}).")
    except requests.RequestException as e:
        logger.error(f"❌ Failed to download LICENSE file from Apache.org: {e}")

    if not os.path.exists(NOTICE_PATH):
        notice_content = (
            f"Copyright {year} {author}\n\n"
            "This product is licensed under the Apache License, Version 2.0."
        ) + "\n"
        with open(NOTICE_PATH, "w", encoding="utf-8") as f:
            f.write(notice_content)
        logger.info("📄 NOTICE file successfully created.")
    else:
        logger.info("⏩ NOTICE file already exists, no changes made.")


def update_pyproject_toml(backup_dir: str):
    """Updates the 'license' field in pyproject.toml."""
    logger.info("\n--- Updating pyproject.toml ---")
    try:
        backup = create_timestamped_backup(PYPROJECT_PATH, backup_dir)
        if not backup:
            return

        data = toml.load(PYPROJECT_PATH)
        data["tool"]["poetry"]["license"] = "Apache-2.0"
        with open(PYPROJECT_PATH, "w", encoding="utf-8") as f:
            toml.dump(data, f)
        logger.info(
            f"📝 pyproject.toml changed to 'license = \"Apache-2.0\"' | Backup: {backup}"
        )
    except (FileNotFoundError, KeyError, toml.TomlDecodeError) as e:
        logger.error(f"❌ Failed to update pyproject.toml: {e}")


def update_readme_license_badge(backup_dir: str):
    """Replaces the old license badge with a single, correct Apache 2.0 badge."""
    logger.info("\n--- Updating README.md ---")
    if not os.path.exists(README_PATH):
        logger.warning(f"File {README_PATH} not found, skipping this step.")
        return
    try:
        with open(README_PATH, encoding="utf-8") as f:
            content = f.read()

        if f"({LICENSE_OUTPUT_PATH})" in content and "Apache_2.0" in content:
            logger.info("⏩ Correct Apache 2.0 license badge already exists. Skipping.")
            return

        backup = create_timestamped_backup(README_PATH, backup_dir)
        if not backup:
            return

        # Replace the old badge with the new one
        new_content, count = LICENSE_BADGE_PATTERN.subn(NEW_LICENSE_BADGE, content)
        if count == 0:  # If pattern didn't match, maybe there's no badge? Add it.
            # This is a basic attempt to add it at the top.
            # A more robust solution might require a placeholder comment in the README.
            new_content = NEW_LICENSE_BADGE + "\n\n" + content
            logger.info("No MIT badge found. Added new Apache 2.0 badge at the top.")
        else:
            logger.info("📝 License badge in README.md successfully updated.")

        # Optional: remove other textual links to old license if any
        new_content = re.sub(
            r"\[MIT\]\(.*?LICENSE.*?\)",
            "[Apache 2.0](LICENSE)",
            new_content,
            flags=re.IGNORECASE,
        )

        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        logger.error(f"❌ Failed to update README.md: {e}")


def main():
    """Main function to run all migration steps."""
    start_time = datetime.now()
    backup_timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    current_backup_dir = os.path.join(BACKUP_ROOT, backup_timestamp)

    logger.info("=" * 53)
    logger.info("🚀 Starting License Migration to Apache 2.0")
    logger.info(f"🕒 Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📦 Backups will be saved to: {current_backup_dir}")
    logger.info("=" * 53)

    copyright_holder = get_copyright_holder()
    current_year = datetime.now().year
    copyright_info = {"year": current_year, "copyright_holder": copyright_holder}

    update_pyproject_toml(current_backup_dir)
    update_readme_license_badge(current_backup_dir)
    write_license_and_notice(copyright_holder, current_year)
    update_source_files(current_backup_dir, copyright_info)

    end_time = datetime.now()
    duration = end_time - start_time
    logger.info("\n" + "=" * 53)
    logger.info("✅ License Migration Complete!")
    logger.info(f"🕒 End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏱️ Duration: {duration.total_seconds():.2f} seconds")
    logger.info("=" * 53)


if __name__ == "__main__":
    main()
