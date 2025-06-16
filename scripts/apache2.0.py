import os
import re
import shutil
from datetime import datetime

import requests
import toml

from avcmt.utils import setup_logging

LICENSE_URL = "https://www.apache.org/licenses/LICENSE-2.0.txt"
LICENSE_OUTPUT_PATH = "LICENSE"
NOTICE_PATH = "NOTICE"
PYPROJECT_PATH = "pyproject.toml"
README_PATH = "README.md"
BACKUP_ROOT = "backup"
TARGET_DIR = "avcmt"

logger = setup_logging("log/license_migration.log")

APACHE_HEADER = """# Licensed under the Apache License, Version 2.0 (the \"License\");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an \"AS IS\" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""

LICENSE_BADGE_PATTERN = re.compile(
    r"\[!\[License.*MIT.*?\]\(.*?\)\]\(.*?\)", re.IGNORECASE
)
NEW_LICENSE_BADGE = (
    "[![License: Apache-2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg?style=for-the-badge)]"
    "(https://www.apache.org/licenses/LICENSE-2.0)"
)


def backup_file(file_path):
    rel_path = os.path.relpath(file_path)
    backup_path = os.path.join(BACKUP_ROOT, rel_path)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy(file_path, backup_path)
    return backup_path


def insert_apache_header(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
    if "Licensed under the Apache License" in content:
        return False
    backup = backup_file(file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(APACHE_HEADER + "\n\n" + content)
    logger.info(f"✅ Header inserted: {file_path} | Backup: {backup}")
    return True


def update_py_files():
    changed = 0
    for subdir, _, files in os.walk(TARGET_DIR):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(subdir, file)
                if insert_apache_header(path):
                    changed += 1
    logger.info(f"🔧 Total Python files updated: {changed}")


def write_license_and_notice(author):
    year = datetime.now().year

    # LICENSE file
    try:
        response = requests.get(LICENSE_URL)
        response.raise_for_status()
        content = response.text
    except requests.RequestException as e:
        logger.error(f"❌ Failed to download Apache LICENSE: {e}")
        return

    content = content.replace("[yyyy]", str(year)).replace(
        "[name of copyright owner]", author
    )
    with open(LICENSE_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"📄 LICENSE file written as Apache-2.0 ({year}, {author})")

    # NOTICE file
    if not os.path.exists(NOTICE_PATH):
        with open(NOTICE_PATH, "w", encoding="utf-8") as f:
            f.write(
                f"This product includes software developed by {author} as part of the avcmt-py project.\n"
                f"Licensed under the Apache License, Version 2.0.\n"
            )
        logger.info("📄 NOTICE file created.")


def update_pyproject_toml():
    data = toml.load(PYPROJECT_PATH)
    author_name = data["tool"]["poetry"]["authors"][0].split("<")[0].strip()
    backup = backup_file(PYPROJECT_PATH)
    data["tool"]["poetry"]["license"] = "Apache-2.0"
    with open(PYPROJECT_PATH, "w", encoding="utf-8") as f:
        toml.dump(data, f)
    logger.info(f"📝 pyproject.toml updated to Apache-2.0 | Backup: {backup}")
    return author_name


def update_readme_license_badge():
    if not os.path.exists(README_PATH):
        return
    with open(README_PATH, encoding="utf-8") as f:
        content = f.read()
    if "Apache" in content:
        return
    backup = backup_file(README_PATH)
    content = LICENSE_BADGE_PATTERN.sub(NEW_LICENSE_BADGE, content)
    content = re.sub(
        r"\[MIT\]\(LICENSE\)",
        "[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)",
        content,
    )
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"📝 README.md license badge updated | Backup: {backup}")


def main():
    author = update_pyproject_toml()
    update_readme_license_badge()
    write_license_and_notice(author)
    update_py_files()
    logger.info("✅ Apache-2.0 license migration complete.")


if __name__ == "__main__":
    main()
