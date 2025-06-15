# File: avcmt/utils.py

import logging
import os
import re
import time


def get_log_dir():
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "log")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def get_log_file():
    return os.path.join(get_log_dir(), "commit_group_all.log")


def get_dry_run_file():
    return os.path.join(get_log_dir(), "commit_messages_dry_run.md")


def is_recent_dry_run(file_path, max_age_minutes=10):
    """
    Cek apakah file dry-run commit masih dalam rentang waktu tertentu (default 10 menit).
    """
    if not os.path.exists(file_path):
        return False
    mtime = os.path.getmtime(file_path)
    return (time.time() - mtime) <= max_age_minutes * 60


def extract_commit_messages_from_md(filepath):
    """
    Extracts commit messages per group from a dry-run Markdown file,
    skipping any sponsor/injected AI ad blocks like Pollinations.

    Returns:
        dict: { group_name: commit_message }
    """
    # Step 1: Read the file content
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    messages = {}
    current_group = None
    current_message_lines = []
    in_code_block = False

    lines = content.splitlines()

    # Step 2: Walk through each line
    i = 0
    while i < len(lines):
        line = lines[i]

        # Step 3: Detect start of a new group
        group_match = re.match(r"^## Group: [`'](.+)[`']$", line)
        if group_match:
            # Save previous message if exists
            if current_group and current_message_lines:
                messages[current_group] = "\n".join(current_message_lines).strip()

            # Start new group
            current_group = group_match.group(1)
            current_message_lines = []
            in_code_block = False
            i += 1
            continue

        # Step 4: Detect start of code block for commit message
        if line.strip() == "```md":
            in_code_block = True
            current_message_lines = []
            i += 1
            continue

        # Step 5: Detect end of code block
        if line.strip() == "```" and in_code_block:
            in_code_block = False
            i += 1
            continue

        # Step 6: Skip sponsor block if detected
        if "**Sponsor**" in line or line.startswith("diff --git"):
            # Skip to the end of block or next group
            while i < len(lines) and not lines[i].startswith("## Group: "):
                i += 1
            current_group = None
            current_message_lines = []
            in_code_block = False
            continue

        # Step 7: Collect lines within code block
        if in_code_block:
            current_message_lines.append(line)

        i += 1

    # Step 8: Final group flush
    if current_group and current_message_lines:
        messages[current_group] = "\n".join(current_message_lines).strip()

    return messages


def setup_logging(log_file="commit_group_all.log"):
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers():
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

        fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)
    return logger
