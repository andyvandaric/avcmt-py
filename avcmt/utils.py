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

import datetime
import logging
import re
import subprocess
import sys
import time
from pathlib import Path

# Platform-specific imports
try:
    import fcntl
except ImportError:
    # fcntl is not available on Windows
    fcntl = None

from jinja2 import Environment, FileSystemLoader
from rich.logging import RichHandler


def windows_safe_exit(exit_code: int = 0) -> None:
    """Performs Windows-safe exit with proper cleanup."""
    sys.exit(exit_code)


def get_log_dir() -> Path:
    """Returns the Path object for the log directory, creating it if needed."""
    log_dir = Path(__file__).parent.parent / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file(filename: str) -> Path:
    """
    Returns the full path to a specific log file inside the log directory.
    FIXED: Now correctly takes a filename instead of a hardcoded path.
    """
    return get_log_dir() / filename


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
    """Extracts Python function and class docstrings from a Markdown file with optimized parsing."""
    path = Path(filepath)
    if not path.exists():
        return {}

    try:
        # Use more efficient file reading with larger buffer
        with path.open(encoding="utf-8", buffering=8192) as f:
            content = f.read()
    except (OSError, UnicodeDecodeError) as e:
        logging.getLogger("avcmt").warning(f"Failed to read cache file {path}: {e}")
        return {}

    if not content.strip():
        return {}

    docstrings = {}
    # Optimized regex with compiled pattern for better performance
    pattern = re.compile(
        r"### `([^`]+)`.*?```python\n\"\"\"\n(.*?)\n\"\"\"\n```",
        re.DOTALL | re.MULTILINE,
    )

    try:
        matches = pattern.findall(content)
        for identifier, docstring_content in matches:
            # Validate identifier format to prevent invalid entries
            if "." in identifier and docstring_content.strip():
                docstrings[identifier] = docstring_content.strip()
    except re.error as e:
        logging.getLogger("avcmt").error(f"Regex error parsing cache: {e}")
        return {}

    return docstrings


def setup_logging(log_filename: str, rich_console: bool = False) -> logging.Logger:
    """Sets up a logger with file and console handlers."""
    logger = logging.getLogger("avcmt")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    log_path = get_log_file(log_filename)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # FIXED: Use 'a' (append) mode for file handler
    fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    fh.setFormatter(file_formatter)
    logger.addHandler(fh)

    # NEW: Use RichHandler for beautiful, non-conflicting console logs
    if rich_console:
        # The RichHandler will render logs above the progress bar
        rich_handler = RichHandler(
            show_path=False, markup=True, show_level=True, show_time=False
        )
        rich_handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
        logger.addHandler(rich_handler)
    else:
        sh = logging.StreamHandler()
        sh.setFormatter(file_formatter)
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


def write_docs_dry_run_file_atomic(cache_dict: dict) -> None:
    """Write cache to dry run file atomically to prevent race conditions."""
    if not cache_dict:
        return

    dry_run_file = get_docs_dry_run_file()
    dry_run_file.parent.mkdir(parents=True, exist_ok=True)

    temp_file = dry_run_file.with_suffix(".tmp")

    try:
        existing_content, existing_identifiers = _read_existing_cache(dry_run_file)
        write_header = not dry_run_file.exists() or dry_run_file.stat().st_size == 0

        _write_cache_content(
            temp_file, existing_content, cache_dict, existing_identifiers, write_header
        )
        _atomic_file_replace(temp_file, dry_run_file)

    except Exception as e:
        _cleanup_temp_file(temp_file)
        raise e


def _read_existing_cache(dry_run_file: Path) -> tuple[str, set[str]]:
    """Read existing cache content and extract identifiers."""
    if not dry_run_file.exists():
        return "", set()

    try:
        existing_content = dry_run_file.read_text(encoding="utf-8")
        existing_identifiers = set(re.findall(r"### `([^`]+)`", existing_content))
        return existing_content, existing_identifiers
    except Exception:
        return "", set()


def _write_cache_content(
    temp_file: Path,
    existing_content: str,
    cache_dict: dict,
    existing_identifiers: set[str],
    write_header: bool,
) -> None:
    """Write cache content to temporary file."""
    with temp_file.open("w", encoding="utf-8") as f:
        if existing_content and not write_header:
            f.write(existing_content)
        elif write_header:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"# AI-Generated Docstrings (Dry Run)\n_Generated on: {current_time}_\n\n"
            )

        # Write only NEW cache entries (not existing ones)
        for identifier, docstring in sorted(cache_dict.items()):
            if identifier not in existing_identifiers:
                f.write(f"### `{identifier}`\n")
                f.write(f'```python\n"""\n{docstring}\n"""\n```\n\n---\n\n')


def _atomic_file_replace(temp_file: Path, target_file: Path) -> None:
    """Atomically replace target file with temp file."""
    if sys.platform == "win32":
        # Windows requires explicit removal before rename
        if target_file.exists():
            target_file.unlink()
    temp_file.replace(target_file)


def _cleanup_temp_file(temp_file: Path) -> None:
    """Clean up temporary file on error."""
    if temp_file.exists():
        temp_file.unlink()


def write_docs_dry_run_file(cache_dict: dict) -> None:
    """Write cache to dry run file using proper append mode to preserve existing cache."""
    if not cache_dict:
        return

    dry_run_file = get_docs_dry_run_file()

    # Use file locking to prevent race conditions (Unix only)
    lock_file = dry_run_file.with_suffix(".lock")

    try:
        # Create lock file
        with lock_file.open("w") as lock:
            if fcntl is not None:
                # Use fcntl on Unix systems
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

            # Check if we need to write header (file doesn't exist or is empty)
            write_header = not dry_run_file.exists() or dry_run_file.stat().st_size == 0

            # Get existing identifiers to prevent duplicates
            existing_identifiers = set()
            if dry_run_file.exists():
                try:
                    content = dry_run_file.read_text(encoding="utf-8")
                    existing_identifiers = set(re.findall(r"### `([^`]+)`", content))
                except Exception:
                    pass

            # Use append mode to preserve existing cache
            with dry_run_file.open("a", encoding="utf-8") as f:
                if write_header:
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(
                        f"# AI-Generated Docstrings (Dry Run)\n_Generated on: {current_time}_\n\n"
                    )

                # Only write NEW cache entries (not existing ones)
                for identifier, docstring in sorted(cache_dict.items()):
                    if identifier not in existing_identifiers:
                        f.write(f"### `{identifier}`\n")
                        f.write(f'```python\n"""\n{docstring}\n"""\n```\n\n---\n\n')
                        f.flush()  # Ensure immediate write to disk

    finally:
        # Remove lock file
        if lock_file.exists():
            lock_file.unlink()


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


def clear_log_file(log_filename: str):
    """Clears the specified log file to ensure a fresh start for each run."""
    log_path = get_log_file(log_filename)
    if log_path.exists():
        log_path.write_text("", encoding="utf-8")


# NEW: Graceful shutdown context manager
# FINAL: This is the definitive, clean context manager.

__all__ = [
    "clean_ai_response",
    "clean_docstring_response",
    "clear_docs_dry_run_file",
    "clear_dry_run_file",
    "clear_log_file",  # ADDED to __all__
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
    "windows_safe_exit",  # ADDED to __all__
    "write_docs_dry_run_file",
    "write_docs_dry_run_file_atomic",  # ADDED to __all__
]
