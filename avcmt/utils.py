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

# File: avcmt/utils.py
# Revision v2 - Added clean_ai_response and simplified extraction logic.

import logging
import re
import subprocess
import time
from pathlib import Path


def get_log_dir() -> Path:
    log_dir = Path(__file__).parent.parent / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file() -> Path:
    return get_log_dir() / "commit_group_all.log"


def get_dry_run_file() -> Path:
    return get_log_dir() / "commit_messages_dry_run.md"


def is_recent_dry_run(file_path: Path | str, max_age_minutes=10) -> bool:
    """
    Cek apakah file dry-run commit masih dalam rentang waktu tertentu (default 10 menit).
    """
    path = Path(file_path)
    if not path.exists():
        return False
    mtime = path.stat().st_mtime
    return (time.time() - mtime) <= max_age_minutes * 60


def clean_ai_response(raw_message: str) -> str:
    """
    Membersihkan output mentah dari AI, mengekstrak blok Conventional Commit
    pertama yang valid dan membuang teks lain, termasuk sponsor.
    """
    lines = raw_message.strip().split("\n")
    commit_lines = []
    in_commit_block = False

    # Pola untuk menemukan awal dari header commit yang valid.
    commit_start_pattern = re.compile(
        r"^(feat|fix|chore|refactor|docs|style|test|build|ci)(\(.*\))?!?: .*"
    )

    for line in lines:
        if in_commit_block:
            # Kondisi berhenti: jika menemukan awal commit baru atau penanda sponsor.
            if commit_start_pattern.match(line.strip()) or "**Sponsor**" in line:
                break
            commit_lines.append(line)
        elif commit_start_pattern.match(line.strip()):
            # Jika menemukan awal blok commit, mulai kumpulkan.
            in_commit_block = True
            commit_lines.append(line)

    if not commit_lines:
        return ""  # Kembalikan string kosong jika tidak ada blok yang valid ditemukan.

    return "\n".join(commit_lines).strip()


def extract_commit_messages_from_md(filepath: Path | str) -> dict[str, str]:
    """
    Mengekstrak pesan commit per grup dari file Markdown dry-run.
    Versi ini lebih sederhana karena diasumsikan file sudah bersih.
    """
    path = Path(filepath)
    if not path.exists():
        return {}

    with path.open(encoding="utf-8") as f:
        content = f.read()

    messages = {}
    # Pola untuk menemukan semua grup dan blok kodenya
    pattern = re.compile(r"## Group: `(.*?)`\s*```md\n(.*?)\n```", re.DOTALL)

    matches = pattern.findall(content)
    for group_name, commit_message in matches:
        messages[group_name] = commit_message.strip()

    return messages


def setup_logging(log_file: Path | str = "commit_group_all.log"):
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers():
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

        fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)
    return logger


def get_staged_files() -> list[str]:
    """Returns a list of staged files."""
    try:
        output = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return [line for line in output.splitlines() if line]
    except subprocess.CalledProcessError:
        return []


def read_dry_run_file() -> str | None:
    """Reads the content of the dry-run cache file."""
    filepath = get_dry_run_file()
    if not filepath.exists():
        return None
    with filepath.open(encoding="utf-8") as f:
        return f.read()


def clear_dry_run_file() -> bool:
    """Deletes the dry-run cache file."""
    filepath = get_dry_run_file()
    if filepath.exists():
        filepath.unlink()
        return True
    return False
