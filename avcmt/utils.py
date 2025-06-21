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
# Revision v3 - Added clean_ai_response, simplified extraction, and reusable Jinja2 environment setup.

import logging
import re
import subprocess
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader  # ADDED: Import Jinja2


def get_log_dir() -> Path:
    """Returns the Path object representing the log directory, creating the directory and any necessary parent directories if they do not already exist.

    Returns:
        Path: The Path object pointing to the log directory.
    """
    log_dir = Path(__file__).parent.parent / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file() -> Path:
    """Returns the full file path to the "commit_group_all.log" file located in the directory specified by get_log_dir(). This function constructs and returns a Path object by joining the directory path provided by get_log_dir() with the log file name. It may raise an exception if get_log_dir() encounters an error or returns an invalid path."""
    return get_log_dir() / "commit_group_all.log"


def get_dry_run_file() -> Path:
    """Retrieves the Path object for the 'commit_messages_dry_run.md' file within the log directory.

    This function constructs and returns a Path object pointing to the 'commit_messages_dry_run.md' file located inside the log directory. It relies on the existing get_log_dir() function to obtain the log directory path and appends the filename to it.

    Args:
        None

    Returns:
        Path: A Path object representing the full path to 'commit_messages_dry_run.md' in the log directory.
    """
    return get_log_dir() / "commit_messages_dry_run.md"


def is_recent_dry_run(file_path: Path | str, max_age_minutes=120) -> bool:
    """Checks whether the specified dry-run commit file is recent based on its modification time. Returns True if the file exists and has been modified within the given maximum age in minutes; otherwise, returns False.

    Args:
        file_path (Path or str): The path to the dry-run commit file.
        max_age_minutes (int, optional): The maximum age in minutes for the file to be considered recent. Defaults to 120.

    Returns:
        bool: True if the file exists and is recent within the specified time frame; False otherwise.
    """
    path = Path(file_path)
    if not path.exists():
        return False
    mtime = path.stat().st_mtime
    return (time.time() - mtime) <= max_age_minutes * 60


def clean_ai_response(raw_message: str) -> str:
    """Extracts and returns a relevant commit message block from a raw message string, stopping at the next commit header or sponsor indicator. If no valid commit block is found, returns an empty string.

    Args:
        raw_message (str): The original message string containing potential commit information.

    Returns:
        str: The cleaned commit message block, or an empty string if none is found.
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


# >> avcmt/utils.py


def clean_docstring_response(raw_text: str) -> str:
    """Performs cleaning of AI-generated raw text to ensure it's a valid and safe docstring content block, free of triple-quote artifacts and extraneous footers. The function extracts content from markdown code blocks, removes triple-quote characters and markdown syntax, and strips sponsorship or separator footers to produce ready-to-insert documentation. Args: raw_text (str): The raw string response from an AI that may contain code blocks, triple-quotes, or extraneous footer content. Returns: str: The cleaned, properly formatted docstring content free of triple-quotes and unnecessary footer sections."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        return ""

    # 1. Prefer content inside a python markdown block if it exists.
    # This handles cases where the AI wraps its response.
    code_block_match = re.search(r"```python\n(.*?)```", raw_text, re.DOTALL)
    text = code_block_match.group(1).strip() if code_block_match else raw_text

    # 2. CRITICAL FIX: Aggressively remove all triple-quote artifacts.
    # This is the key to preventing SyntaxError. It ensures that no matter
    # what the AI returns, the string we pass back to the generator
    # has no triple-quotes of its own to conflict with.
    # We also remove the markdown backticks just in case.
    text = text.replace('"""', "").replace("```", "")

    # 3. Remove common sponsorship footers or separators.
    lines = text.strip().split("\n")
    try:
        # Find the line index where a separator or sponsor text starts
        sponsor_index = next(
            i
            for i, line in enumerate(lines)
            if line.strip() in {"---", "***"} or "**Sponsor**" in line
        )
        # Keep only the lines before that index
        cleaned_text = "\n".join(lines[:sponsor_index]).strip()
    except StopIteration:
        # No sponsor section found, use the whole text
        cleaned_text = "\n".join(lines).strip()

    return cleaned_text


def extract_commit_messages_from_md(filepath: Path | str) -> dict[str, str]:
    """Extracts commit messages grouped by section from a Markdown file.
    Reads the file at the specified path, searches for sections labeled with "## Group: `group_name`" followed by a code block in Markdown format, and returns a dictionary mapping each group name to its corresponding commit message.

    Args:
        filepath (Path or str): Path to the Markdown file to be parsed.

    Returns:
        dict[str, str]: A dictionary where keys are group names and values are the associated commit messages.
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


def extract_docstrings_from_md(filepath: Path | str) -> dict[str, str]:
    """Extracts Python function and class docstrings from a Markdown file by parsing code blocks associated with specific identifiers.

    The function takes a file path as input, reads the content of the Markdown file, and uses a regex pattern to find code blocks containing docstrings linked to specific identifiers formatted as module paths. It returns a dictionary mapping each identifier to its corresponding docstring content as a string. If the file does not exist, it returns an empty dictionary.
    """
    path = Path(filepath)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        content = f.read()

    docstrings = {}
    # Unique identifier pattern: ### `module.submodule.function_name`
    pattern = re.compile(
        r"### `(.*?)`.*?```python\n\"\"\"\n(.*?)\n\"\"\"\n```", re.DOTALL
    )

    matches = pattern.findall(content)
    for identifier, docstring_content in matches:
        docstrings[identifier] = docstring_content.strip()

    return docstrings


def setup_logging(log_file: Path | str = "commit_group_all.log"):
    """Sets up and configures a logger named 'avcmt' with file and console handlers, ensuring that logs are written to a specified file and output to the console.

    Args:
        log_file (Path | str): The file path where logs will be written. Defaults to "commit_group_all.log".

    Returns:
        logging.Logger: The configured logger instance with attached handlers.
    """
    # Menggunakan logger dengan nama 'avcmt' sebagai root untuk seluruh aplikasi
    logger = logging.getLogger("avcmt")
    logger.setLevel(logging.INFO)

    # BUG FIX: Hapus handler yang ada untuk memastikan log selalu baru
    if logger.hasHandlers():
        logger.handlers.clear()

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Handler untuk menulis ke file (selalu menimpa dengan mode 'w')
    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Handler untuk menampilkan di konsol
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    return logger


def get_staged_files() -> list[str]:
    """Returns a list of filenames that are currently staged in Git. If the command fails, it returns an empty list.

    Args: None

    Returns:
        list[str]: A list containing the filenames of staged files in Git.
    """
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
    """Reads the content of the dry-run cache file if it exists; otherwise, returns None.

    Args:
        (None)

    Returns:
        str or None: The content of the dry-run cache file as a string if the file exists; otherwise, None.
    """
    filepath = get_dry_run_file()
    if not filepath.exists():
        return None
    with filepath.open(encoding="utf-8") as f:
        return f.read()


def clear_dry_run_file() -> bool:
    """Deletes the dry-run cache file if it exists. Checks for the presence of the dry-run cache file using get_dry_run_file(), deletes it if found, and returns True; returns False if the file does not exist.

    Args:
        None

    Returns:
        bool: True if the file was found and deleted, False otherwise.
    """
    filepath = get_dry_run_file()
    if filepath.exists():
        filepath.unlink()
        return True
    return False


# NEW FUNCTION: Reusable Jinja2 environment setup
def get_jinja_env(template_sub_dir: str | Path) -> Environment:
    """Returns a configured Jinja2 Environment that loads templates from a specified sub-directory within 'avcmt/prompt_templates', enabling rendering of prompt templates based on the given path.

    Args:
        template_sub_dir (str or Path): The sub-directory path within 'avcmt/prompt_templates' from which to load templates.

    Returns:
        Environment: A Jinja2 Environment instance configured to load templates from the specified directory.
    """
    # Root of all prompt templates
    root_template_dir = Path(__file__).parent / "prompt_templates"

    # Combined path to the specific sub-directory
    full_template_path = root_template_dir / template_sub_dir

    return Environment(loader=FileSystemLoader(full_template_path))


def get_docs_dry_run_file() -> Path:
    """Gets the Path object for the documentation dry-run file used to store or access the output.

    This function retrieves the file path for the 'docs_dry_run.md' file used in the dry-run process, which is stored in the log directory.

    Args:
        None

    Returns:
        Path: A Path object pointing to the 'docs_dry_run.md' file within the log directory.
    """
    return get_log_dir() / "docs_dry_run.md"


def read_docs_dry_run_file() -> str | None:
    """Reads and returns the content of the documentation dry-run cache file if it exists.

    This function checks for the presence of a cache file intended to store dry-run documentation data. If the cache file exists, it opens the file with UTF-8 encoding and returns its contents as a string. If the file does not exist, the function returns None.

    Args:
        None

    Returns:
        str or None: The content of the cache file as a string if the file exists; otherwise, None.
    """
    filepath = get_docs_dry_run_file()
    if not filepath.exists():
        return None
    with filepath.open(encoding="utf-8") as f:
        return f.read()


def clear_docs_dry_run_file() -> bool:
    """Deletes the documentation dry-run cache file if it exists. Checks for the presence of the cache file used during dry-run documentation generation, deletes it when found, and indicates whether deletion occurred.

    Args:
        None

    Returns:
        bool: True if the cache file was found and successfully deleted, False if the cache file did not exist.
    """
    filepath = get_docs_dry_run_file()
    if filepath.exists():
        filepath.unlink()
        return True
    return False


__all__ = [
    "clean_ai_response",
    "clean_docstring_response",
    "clear_docs_dry_run_file",
    "clear_dry_run_file",
    "extract_commit_messages_from_md",
    "extract_docstrings_from_md",
    "get_docs_dry_run_file",
    "get_dry_run_file",
    "get_jinja_env",  # ADDED to __all__
    "get_log_dir",
    "get_log_file",
    "get_staged_files",
    "is_recent_dry_run",
    "read_docs_dry_run_file",
    "read_dry_run_file",
    "setup_logging",
]
