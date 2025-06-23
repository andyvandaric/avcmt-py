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

# File: avcmt/modules/doc_generator.py
# FINAL REVISION: Fixed subprocess handling for graceful shutdown and proper force-rebuild cache clearing

import ast
import contextlib
import logging
import multiprocessing
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

from jinja2 import Template
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

from avcmt.ai import generate_with_ai
from avcmt.utils import (
    clean_docstring_response,
    clear_docs_dry_run_file,
    extract_docstrings_from_md,
    get_docs_dry_run_file,
    get_jinja_env,
    windows_safe_exit,
    write_docs_dry_run_file_atomic,
)

# Global variable to track completed tasks across processes
completed_tasks = multiprocessing.Value("i", 0)

# Global variable for total workers count
total_workers = multiprocessing.Value("i", 0)

# Constants for docstring processing
MIN_COMPLETE_DOCSTRING_PARTS = 3  # Minimum parts for complete inline docstring
MIN_QUOTE_COUNT_FOR_INLINE = 2  # Minimum quote count for inline docstring detection
BACKUP_ROOT = "backup"  # Backup directory root

# Project root for robust path resolution
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Module-level template cache
_template_cache: Template | None = None

# Regex for stripping triple quotes
_TRIPLE_QUOTE_RX = re.compile(r'^([ \t]*)[\'"]{3}|[\'"]{3}[ \t]*$')


def _strip_quotes(doc: str) -> str:
    """Remove leading/trailing triple quotes and surrounding blank lines."""
    # Remove opening/closing """ lines
    doc = _TRIPLE_QUOTE_RX.sub("", doc.strip())
    # Remove one "accidental" indent level from template
    return textwrap.dedent(doc).strip("\n")


def _get_template() -> Template:
    """Get cached Jinja template for docstring generation."""
    # Use module-level cache instead of global statement
    if _template_cache is None:
        # This will be initialized once per worker process
        template = get_jinja_env("docs").get_template("docstring.j2")
        globals()["_template_cache"] = template
    return _template_cache


class WorkerContext:
    """Shared context for worker processes to avoid global statements."""

    def __init__(self, shared_progress_dict, shared_cache_dict):
        self.worker_progress = shared_progress_dict
        self.cache = shared_cache_dict


class WorkerContextManager:
    """Manages the worker context for multiprocessing without using global variables."""

    def __init__(self):
        self.worker_context = None

    def initialize(self, shared_progress_dict, shared_cache_dict):
        """Initialize the worker context with the shared dictionaries."""
        self.worker_context = WorkerContext(shared_progress_dict, shared_cache_dict)

    def get_context(self):
        """Retrieve the worker context."""
        return self.worker_context


# Create a module-level instance of WorkerContextManager
worker_context_manager = WorkerContextManager()


def _init_worker(shared_progress_dict, shared_cache_dict):
    """Initialize worker context for multiprocessing."""
    worker_context_manager.initialize(shared_progress_dict, shared_cache_dict)


def _generate_with_retry(prompt, provider, model, debug, max_retries=3):
    """Generate AI response with retry mechanism and exponential backoff."""
    for attempt in range(max_retries):
        try:
            return generate_with_ai(prompt, provider=provider, model=model, debug=debug)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            # Exponential backoff with jitter
            wait_time = (2**attempt) + random.uniform(0, 1)
            time.sleep(wait_time)
    return None


def _doc_generation_worker(args: dict) -> tuple:
    """
    A single unit of work for a child process.
    Returns a tuple: (identifier, result_dictionary, error_message_string).
    """

    worker_id = os.getpid()
    identifier = args["identifier"]

    def _update_status(**kwargs):
        """Utility to synchronize worker status updates across processes."""
        try:
            progress_dict = worker_context_manager.get_context().worker_progress
            base = progress_dict.get(worker_id, {})
            base.update(kwargs)
            progress_dict[worker_id] = base  # Re-assign to trigger proxy sync
        except Exception:
            pass  # Ignore status update errors to prevent worker failures

    try:
        # Access shared progress and cache through worker context
        cache = worker_context_manager.get_context().cache

        # Initialize worker progress with proper sync
        _update_status(
            current_task=identifier, status="processing", start_time=time.time()
        )

        # Add random delay between 1-3 seconds to avoid overwhelming AI service
        delay = random.uniform(1.0, 3.0)
        time.sleep(delay)

        # Use cached template for efficiency
        template = _get_template()
        prompt = template.render(source_code=args["node_source"])

        _update_status(status="generating_ai_response")
        # Use retry mechanism for AI generation
        raw_response = _generate_with_retry(
            prompt, provider=args["provider"], model=args["model"], debug=args["debug"]
        )

        _update_status(status="cleaning_response")
        cleaned = clean_docstring_response(raw_response)
        cleaned = _strip_quotes(cleaned)  # ⭐️ Strip quotes to get plain text

        # Mark as completed
        _update_status(status="completed", end_time=time.time())

        with completed_tasks.get_lock():  # Thread-safe increment
            completed_tasks.value += 1

        if cleaned:
            # Update both caches in real-time
            cache[identifier] = cleaned
            # Use atomic write to prevent race conditions
            try:
                write_docs_dry_run_file_atomic({identifier: cleaned})
            except Exception as e:
                # Log error but don't fail the worker
                logging.getLogger("avcmt").error(
                    f"Failed to write cache atomically: {e}"
                )
            return (identifier, {identifier: cleaned}, None)
        return (identifier, None, "Cleaned response was empty.")

    except Exception as e:
        # Mark as failed with proper cleanup
        try:
            _update_status(status="failed", error=str(e), end_time=time.time())

            with completed_tasks.get_lock():  # Thread-safe increment
                completed_tasks.value += 1
        except Exception:
            pass  # Avoid cascading failures

        return (identifier, None, f"An exception occurred: {e}")


class DocGeneratorError(Exception):
    """Custom exception for doc generation failures."""


def _create_backup(file_path: Path, backup_dir: Path, logger: logging.Logger) -> None:
    """Copy *file_path* → *backup_dir* and log the operation; swallow errors."""
    try:
        rel = file_path.resolve().relative_to(Path.cwd().resolve())
        dest = backup_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest)
        logger.info("📋 Backup created → %s", dest)
    except Exception as exc:
        logger.error("Backup failed for %s: %s", file_path, exc)


def _legacy_update_docstring(
    file_content: list[str], node: ast.stmt, new_docstring: str
) -> list[str]:
    """Updates the docstring of a specified function node within source code by inserting or replacing the existing docstring with a new one, properly formatted and indented."""
    if not node.body:
        # Cannot insert a docstring into an empty body (e.g., protocol stubs)
        return file_content

    # Determine indentation from the first statement of the function's body
    first_body_stmt = node.body[0]
    indent_str = " " * first_body_stmt.col_offset

    # Format the new docstring with the correct indentation
    docstring_lines = new_docstring.split("\n")
    indented_lines = [f"{indent_str}{line}".rstrip() for line in docstring_lines]
    formatted_docstring = f'{indent_str}"""{indented_lines[0].lstrip()}'
    if len(indented_lines) > 1:
        formatted_docstring += "\n" + "\n".join(indented_lines[1:])
    formatted_docstring += f'\n{indent_str}"""\n'

    # Check if a docstring already exists
    has_existing_doc = isinstance(first_body_stmt, ast.Expr) and isinstance(
        first_body_stmt.value, (ast.Constant, ast.Str)
    )

    if has_existing_doc:
        # Replace the old docstring lines with the new one
        start_line_idx = first_body_stmt.lineno - 1
        end_line_idx = first_body_stmt.end_lineno
        file_content[start_line_idx:end_line_idx] = [formatted_docstring]
    else:
        # Insert the new docstring before the first body statement
        insertion_point_idx = first_body_stmt.lineno - 1
        file_content.insert(insertion_point_idx, formatted_docstring)

    return file_content


class DocGenerator:
    """Manages documentation generation for Python files using AI-powered docstring creation."""

    MAX_WORKERS = 4
    MAX_LOG_FILES_DISPLAY = 10  # Maximum number of files to display in logs

    def __init__(
        self,
        shutdown_event: threading.Event,
        provider: str = "pollinations",
        model: str = "gemini",
        debug: bool = False,
    ):
        self.provider = provider
        self.model = model
        self.debug = debug
        self.logger = logging.getLogger("avcmt")
        self._shutdown_event = shutdown_event
        self.last_backup_dir: Path | None = None

    def _validate_and_get_files(self, path: str, all_files: bool) -> list[Path]:
        """Validates the target path and returns list of files to process."""
        target_path = Path(path)
        if not target_path.exists():
            msg = f"Path does not exist: {target_path}"
            raise DocGeneratorError(msg)

        if all_files:
            return [p for p in target_path.rglob("*.py") if "venv" not in p.parts]
        return self._get_git_changed_files(target_path)

    def _setup_cache(self, force_rebuild: bool) -> dict:
        """Sets up the cache based on force_rebuild flag with proper preservation logic."""
        if force_rebuild:
            self.logger.info(
                "[bold yellow]--force-rebuild active. Clearing existing cache.[/bold yellow]"
            )
            # Clear cache file but preserve directory structure
            clear_docs_dry_run_file()
            self.logger.info("Cache cleared. All items will be processed.")
            return {}

        # Preserve existing cache
        preserved_cache = extract_docstrings_from_md(get_docs_dry_run_file())
        if preserved_cache:
            self.logger.info(f"Loaded {len(preserved_cache)} items from cache.")
        else:
            self.logger.info("No existing cache found. Starting fresh.")
        return preserved_cache

    @staticmethod
    def _validate_syntax(lines: list[str]) -> bool:
        """Validate that the given lines form syntactically correct Python code."""
        try:
            ast.parse("".join(lines))
            return True
        except SyntaxError:
            return False

    def _update_docstring_with_fallback(
        self, lines: list[str], node: ast.AST, docstring: str
    ) -> tuple[bool, list[str]]:
        """Update docstring with fallback to legacy method and syntax validation."""
        original_lines = lines.copy()  # Keep original for fallback

        # Try new insertion method first
        success = self._insert_docstring(lines, node, docstring)

        if not success:
            # Fallback to legacy algorithm - create a fresh copy
            lines[:] = _legacy_update_docstring(original_lines.copy(), node, docstring)
            success = lines != original_lines

        # Compile check - ensure resulting file is valid python
        if success and not self._validate_syntax(lines):
            # Try legacy method if new method failed validation
            legacy_lines = _legacy_update_docstring(
                original_lines.copy(), node, docstring
            )
            if self._validate_syntax(legacy_lines):
                lines[:] = legacy_lines
                success = True
            else:
                # If both methods fail validation, revert to original
                lines[:] = original_lines
                success = False

        return success, lines

    def _update_file_docstrings(
        self, file_path: Path, suggestions: dict, backup_dir: Path | None = None
    ) -> bool:
        """Update docstrings in a Python file based on suggestions."""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)

            # Parse AST to find nodes
            tree = ast.parse(content)
            nodes = [
                n
                for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            ]

            modified = False

            # Process nodes in reverse order to maintain line numbers
            for node in reversed(nodes):
                identifier = self._get_node_identifier(file_path, node)
                if identifier not in suggestions:
                    continue

                docstring = suggestions[identifier]
                success, lines = self._update_docstring_with_fallback(
                    lines, node, docstring
                )

                if success:
                    modified = True

            if modified:
                # Create backup before modifying
                if backup_dir:
                    _create_backup(file_path, backup_dir, self.logger)

                # Write updated content atomically
                temp_file = file_path.with_suffix(".tmp")
                temp_file.write_text("".join(lines), encoding="utf-8")
                temp_file.replace(file_path)
                return True

        except Exception as e:
            self.logger.error(f"Error updating docstrings in {file_path}: {e}")

        return False

    def _apply_docstrings(
        self,
        files_to_process: list[Path],
        docstrings: dict[str, str],
        backup_dir: Path | None = None,
    ) -> int:
        """Write docstrings into each file in files_to_process.

        Args:
            files_to_process: List of Python files to process.
            docstrings: Dictionary mapping identifiers to docstring content.
            backup_dir: Directory for backup files (None for dry run).

        Returns:
            Number of files that were modified on disk.
        """
        files_updated = 0
        for file_path in files_to_process:
            try:
                if self._update_file_docstrings(file_path, docstrings, backup_dir):
                    files_updated += 1
                    self.logger.info(
                        "Updated docstrings in: [green]%s[/green]", file_path
                    )
            except Exception as exc:
                self.logger.error("Failed to update %s: %s", file_path, exc)
        return files_updated

    def _process_dry_run(
        self, files_to_process: list[Path], force_rebuild: bool
    ) -> None:
        """Handles the complete dry run process using append mode."""
        self.logger.info("[bold cyan]DRY RUN active.[/bold cyan]")

        if force_rebuild:
            self.logger.info("--force-rebuild active. Clearing existing cache.")
            clear_docs_dry_run_file()
            existing_cache = {}
        else:
            existing_cache = extract_docstrings_from_md(get_docs_dry_run_file())
            if existing_cache:
                self.logger.info("Loaded %d items from cache.", len(existing_cache))

        tasks = self._prepare_tasks(files_to_process, force_rebuild, existing_cache)

        if not tasks:
            if not existing_cache:
                write_docs_dry_run_file_atomic({})

            dry_run_path = get_docs_dry_run_file()
            self.logger.info(
                "[bold green]All documentation is up-to-date![/bold green]"
            )
            self.logger.info(f"Cache file: [cyan]{dry_run_path}[/cyan]")
            return

        # Process new tasks and merge cache for resume functionality
        all_new_suggestions, new_cache = self._run_worker_pool_with_progress(tasks)
        existing_cache.update(new_cache)  # Update in-memory cache for next run

        if all_new_suggestions and not self._shutdown_event.is_set():
            dry_run_path = get_docs_dry_run_file()
            self.logger.info("[bold green]Dry run completed successfully![/bold green]")
            self.logger.info(f"Results saved to: [cyan]{dry_run_path}[/cyan]")
        elif self._shutdown_event.is_set():
            self.logger.warning("[yellow]Dry run was aborted by user.[/yellow]")

    def _process_live_run(
        self, files_to_process: list[Path], force_rebuild: bool
    ) -> None:
        """Handles the live run process that actually updates files."""
        self.logger.info(
            "[bold red]LIVE RUN active. Files will be modified![/bold red]"
        )

        start_ts = time.strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(BACKUP_ROOT) / f"docs_{start_ts}"
        self.last_backup_dir = backup_dir
        self.logger.info("🗂  Backups will be stored in: %s", backup_dir)

        # Load existing cache first
        existing_cache = (
            extract_docstrings_from_md(get_docs_dry_run_file())
            if not force_rebuild
            else {}
        )

        tasks = self._prepare_tasks(files_to_process, force_rebuild, existing_cache)

        # Always build a write set from existing cache
        write_set: dict[str, str] = existing_cache.copy()

        if not tasks:
            # No new AI calls needed - apply cached docstrings
            self.logger.info("No new AI calls -- applying cached docstrings.")
            modified = self._apply_docstrings(files_to_process, write_set, backup_dir)
            self.logger.info("%d files updated from cache.", modified)

            # Persist cache after live run to update timestamp
            if modified:
                write_docs_dry_run_file_atomic({})  # Bump mtime
            return

        # Generate new docstrings and merge with existing cache
        suggestions, new_cache = self._run_worker_pool_with_progress(tasks)

        if not suggestions or self._shutdown_event.is_set():
            if self._shutdown_event.is_set():
                self.logger.warning("[yellow]Live run was aborted by user.[/yellow]")
            return

        # Update write set and cache
        write_set.update(suggestions)
        existing_cache.update(new_cache)  # Update in-memory cache for next run

        # Apply all docstrings to files
        files_updated = self._apply_docstrings(files_to_process, write_set, backup_dir)

        self.logger.info("🟢 Live run done. Backups saved in: %s", self.last_backup_dir)
        self.logger.info(
            "[bold green]Live run completed! Updated %d files.[/bold green]",
            files_updated,
        )

    @staticmethod
    def _find_colon_line(node: ast.AST, source_lines: list[str]) -> int:
        """
        Return index of line containing ':' at end of definition.
        For multi-line headers, search backwards from body start to definition start.
        """
        start = node.lineno - 1  # Definition start line

        # Use first body element line as upper bound for search (more accurate)
        if hasattr(node, "body") and node.body:
            stop = getattr(node.body[0], "lineno", start + 1) - 2
        else:
            # Fallback: search reasonable range for colon
            stop = min(start + 50, len(source_lines) - 1)

        # Search backwards from body start to definition start
        for i in range(stop, start - 1, -1):
            if (
                i >= 0
                and i < len(source_lines)
                and ":" in source_lines[i]
                and source_lines[i].rstrip().endswith(":")
            ):
                return i

        return start  # Fallback to definition start

    @staticmethod
    def _has_inline_docstring(lines: list[str], colon_idx: int) -> bool:
        """Check if there's an inline docstring on the colon line."""
        if colon_idx >= len(lines):
            return False
        line = lines[colon_idx]
        return '"""' in line or "'''" in line

    @staticmethod
    def _extract_inline_docstring(line: str) -> tuple[str, str]:
        """Extract existing inline docstring and return (prefix, suffix)."""
        # Handle both """ and ''' quotes
        for quote in ['"""', "'''"]:
            if quote in line:
                parts = line.split(quote)
                if len(parts) >= MIN_COMPLETE_DOCSTRING_PARTS:
                    prefix = parts[0]
                    # Note: suffix not used in current implementation
                    return prefix, ""
        return line, ""

    @staticmethod
    def _get_consistent_indent(lines: list[str], colon_line: int) -> str:
        """Calculate consistent indentation for docstring."""
        if colon_line >= len(lines):
            return "    "

        # Get base indentation from the definition line
        base_indent = re.match(r"\s*", lines[colon_line]).group(0)
        return base_indent + "    "

    @staticmethod
    def _format_docstring_lines(docstring: str, indent: str) -> list[str]:
        """Wrap plain-text docstring into indented triple-quote block."""
        # ASSUMPTION: docstring already has no """ quotes
        lines = []
        lines.append(f'{indent}"""\n')

        # Wrap text to reasonable width (88 chars - indent length for ruff compliance)
        max_width = max(60, 88 - len(indent))

        for paragraph in docstring.split("\n\n"):
            if paragraph.strip():
                wrapped = textwrap.fill(
                    paragraph.strip(), width=max_width, subsequent_indent=indent
                )
                # Use extend for better performance
                lines.extend(f"{indent}{line}\n" for line in wrapped.split("\n"))
                lines.append(f"{indent}\n")  # Blank line between paragraphs

        # Remove last blank line if present
        if lines and lines[-1].strip() == indent.strip():
            lines.pop()

        lines.append(f'{indent}"""\n')
        return lines

    def _insert_docstring(
        self, lines: list[str], node: ast.AST, docstring: str
    ) -> bool:
        """Insert docstring into the appropriate location in the source code."""
        try:
            # Use improved colon detection with source lines
            colon_line = self._find_colon_line(node, lines)

            if colon_line >= len(lines):
                return False

            # Calculate consistent indentation
            indent = self._get_consistent_indent(lines, colon_line)

            # Handle inline docstrings
            if self._has_inline_docstring(lines, colon_line):
                prefix_raw, _ = self._extract_inline_docstring(lines[colon_line])
                # Extract header before the LAST colon to handle type hints properly
                # Use rsplit to avoid cutting off at type annotation colons
                header = prefix_raw.rsplit(":", 1)[0].rstrip() + ":"
                lines[colon_line] = header + "\n"
                new_docstring_lines = self._format_docstring_lines(docstring, indent)
                lines[colon_line + 1 : colon_line + 1] = new_docstring_lines
                return True

            # Check for existing multi-line docstring using AST
            next_line = colon_line + 1
            if next_line < len(lines):
                # Bonus fix: Use AST to detect existing docstring more reliably
                try:
                    # Parse just the function/class to get its docstring
                    node_source = self._get_source_code(node, lines)
                    temp_tree = ast.parse(node_source)
                    temp_node = temp_tree.body[0] if temp_tree.body else None

                    if temp_node and ast.get_docstring(temp_node):
                        # Find docstring boundaries more accurately
                        end_line = self._find_docstring_end_robust(
                            lines, next_line, node
                        )
                        new_docstring_lines = self._format_docstring_lines(
                            docstring, indent
                        )
                        lines[next_line : end_line + 1] = new_docstring_lines
                        return True
                except (SyntaxError, IndexError):
                    # Fallback to old method if AST parsing fails
                    stripped = lines[next_line].strip()
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        quote_char = '"""' if stripped.startswith('"""') else "'''"
                        end_line = self._find_docstring_end(
                            lines, next_line, quote_char, stripped
                        )
                        new_docstring_lines = self._format_docstring_lines(
                            docstring, indent
                        )
                        lines[next_line : end_line + 1] = new_docstring_lines
                        return True

            # Insert new docstring
            new_docstring_lines = self._format_docstring_lines(docstring, indent)
            lines[colon_line + 1 : colon_line + 1] = new_docstring_lines
            return True

        except Exception as e:
            self.logger.error(f"Error inserting docstring for {node.name}: {e}")
            return False

    @staticmethod
    def _find_docstring_end_robust(
        lines: list[str], start_line: int, node: ast.AST
    ) -> int:
        """Find docstring end using AST information when possible."""
        try:
            # Try to use AST end_lineno if available
            if hasattr(node, "body") and node.body:
                first_stmt = node.body[0]
                if isinstance(first_stmt, ast.Expr) and isinstance(
                    first_stmt.value, ast.Constant
                ):
                    # This is likely the docstring statement
                    return getattr(first_stmt, "end_lineno", start_line) - 1
        except Exception:
            pass

        # Fallback to searching for quote patterns
        line_content = lines[start_line].strip()
        if line_content.startswith('"""'):
            quote_char = '"""'
        elif line_content.startswith("'''"):
            quote_char = "'''"
        else:
            return start_line

        # Search for closing quotes
        for i in range(start_line + 1, min(len(lines), start_line + 50)):
            if quote_char in lines[i]:
                return i
        return start_line

    @staticmethod
    def _find_docstring_end(
        lines: list[str],
        start_line: int,
        quote_char: str,
        first_line: str,
    ) -> int:
        """Fallback: scan downwards for the matching closing quotes."""
        # If the opening and closing quotes are on the same line
        if first_line.count(quote_char) >= MIN_QUOTE_COUNT_FOR_INLINE:
            return start_line
        for i in range(start_line + 1, min(len(lines), start_line + 50)):
            if quote_char in lines[i]:
                return i
        return start_line

    def _prepare_tasks(
        self,
        files_to_process: list[Path],
        force_rebuild: bool,
        preserved_cache: dict[str, str],
    ) -> list[dict[str, str]]:
        """Parses files and creates a list of tasks, respecting the force_rebuild flag."""
        if not files_to_process:
            self.logger.info("No candidate files -- skipping task preparation.")
            return []

        tasks = []
        skipped_count = 0
        self.logger.info("Preparing tasks for parallel processing...")

        for file_path in files_to_process:
            try:
                content_str = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content_str)
                nodes = [
                    n
                    for n in ast.walk(tree)
                    if isinstance(
                        n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    )
                ]
                for node in nodes:
                    identifier = self._get_node_identifier(file_path, node)

                    should_process = force_rebuild or identifier not in preserved_cache

                    if not should_process:
                        self.logger.debug(
                            "Skipping cached item: [cyan]%s[/cyan]", identifier
                        )
                        skipped_count += 1
                    else:
                        source_code = self._get_source_code(
                            node, content_str.splitlines(keepends=True)
                        )
                        tasks.append(
                            {
                                "identifier": identifier,
                                "node_source": source_code,
                                "provider": self.provider,
                                "model": self.model,
                                "debug": self.debug,
                            }
                        )
            except Exception as e:
                self.logger.error(
                    f"Failed to parse or prepare tasks for [bold red]{file_path}[/bold red]: {e}",
                    exc_info=self.debug,
                )

        self.logger.info(
            "Skipped %d cached items, generated %d new tasks for processing.",
            skipped_count,
            len(tasks),
        )

        if not tasks:
            self.logger.info(
                "[bold green]All documentation is up-to-date based on cache. No processing needed.[/bold green]"
            )

        return tasks

    def _collect_pool_results(self, async_results) -> dict[str, str]:
        """Safely collects results, logging the status of each individual worker."""
        suggestions: dict[str, str] = {}
        if self._shutdown_event.is_set():
            self.logger.info(
                "[yellow]Result collection skipped due to user shutdown.[/yellow]"
            )
            return {}
        try:
            # The .get() will wait for all results to be ready.
            for identifier, result_dict, error_msg in async_results.get():
                if error_msg:
                    self.logger.error(
                        f"Worker for [bold magenta]{identifier}[/bold magenta] failed: {error_msg}"
                    )
                elif result_dict:
                    self.logger.info(
                        f"Successfully generated docstring for [bold green]{identifier}[/bold green]"
                    )
                    suggestions.update(result_dict)
        except (KeyboardInterrupt, SystemExit):
            self.logger.warning("[yellow]Result collection interrupted.[/yellow]")
        except Exception as e:
            self.logger.error(
                f"Critical error collecting results from pool: {e}", exc_info=self.debug
            )
        return suggestions

    @staticmethod
    def _update_worker_task_description(worker_id: int, worker_info: dict) -> str:
        """Generate task description based on worker status."""
        status = worker_info.get("status", "idle")
        current_task = worker_info.get("current_task", "unknown")

        if status == "processing":
            return f"[yellow]Worker {worker_id}[/yellow]: Processing {current_task}"
        elif status == "generating_ai_response":
            return f"[blue]Worker {worker_id}[/blue]: AI generation for {current_task}"
        elif status == "cleaning_response":
            return (
                f"[cyan]Worker {worker_id}[/cyan]: Cleaning response for {current_task}"
            )
        elif status == "completed":
            return f"[green]Worker {worker_id}[/green]: Completed {current_task}"
        elif status == "failed":
            error = worker_info.get("error", "Unknown error")
            return f"[red]Worker {worker_id}[/red]: Failed {current_task} - {error}"
        return f"[dim]Worker {worker_id}[/dim]: {status}"

    @staticmethod
    def _get_worker_progress_value(status: str) -> float:
        """Get progress value based on worker status."""
        status_progress = {
            "processing": 0.25,
            "generating_ai_response": 0.50,
            "cleaning_response": 0.75,
            "completed": 1.00,
            "failed": 1.00,
        }
        return status_progress.get(status, 0.0)

    @staticmethod
    def _update_worker_progress_bars(
        progress, worker_tasks: dict, shared_progress_dict: dict
    ) -> None:
        """Update individual worker progress bars with thread safety."""
        try:
            # FIX: Use the passed dictionary, not self.worker_progress
            current_workers = dict(shared_progress_dict)

            for worker_id, worker_info in current_workers.items():
                if worker_id not in worker_tasks:
                    # Create new task for this worker
                    worker_tasks[worker_id] = progress.add_task(
                        f"[dim]Worker {worker_id}[/dim]", total=1, visible=True
                    )

                # Update worker task description and progress
                desc = DocGenerator._update_worker_task_description(
                    worker_id, worker_info
                )
                progress_value = DocGenerator._get_worker_progress_value(
                    worker_info.get("status", "idle")
                )

                progress.update(
                    worker_tasks[worker_id], completed=progress_value, description=desc
                )
        except Exception:
            # Ignore progress update errors to prevent crashes
            pass

    @staticmethod
    def _kill_background_processes():
        """Kill background Python processes in a cross-platform way."""
        try:
            if sys.platform == "win32":
                # Windows: Use taskkill
                with contextlib.suppress(Exception):
                    subprocess.run(
                        ["taskkill", "/F", "/IM", "python.exe", "/T"],
                        capture_output=True,
                        timeout=2,
                        check=False,
                    )
            elif sys.platform == "darwin":
                # macOS: Use pkill
                with contextlib.suppress(Exception):
                    subprocess.run(
                        ["pkill", "-f", "python"],
                        capture_output=True,
                        timeout=2,
                        check=False,
                    )
            else:
                # Linux and other Unix-like: Use pkill
                with contextlib.suppress(Exception):
                    subprocess.run(
                        ["pkill", "-f", "python"],
                        capture_output=True,
                        timeout=2,
                        check=False,
                    )
        except Exception:
            pass  # Ignore errors in cleanup

    def _handle_shutdown_cleanup(self, pool, progress, main_task_id, worker_tasks):
        """Handle immediate and aggressive cleanup sequence during shutdown."""
        self.logger.warning(
            "[yellow]Shutdown signal confirmed. Terminating worker pool...[/yellow]"
        )

        try:
            # AGGRESSIVE: Immediate termination without graceful shutdown
            with contextlib.suppress(Exception):
                pool.terminate()  # Force kill all workers immediately

            # Cross-platform background process cleanup
            self._kill_background_processes()

            # Hide progress bars immediately
            for task_id in list(worker_tasks.values()):
                with contextlib.suppress(Exception):
                    progress.update(task_id, visible=False)
            worker_tasks.clear()

            with contextlib.suppress(Exception):
                progress.update(main_task_id, visible=False)
                progress.stop()

        except Exception:
            pass  # Ignore all cleanup errors

        # Cross-platform safe exit
        windows_safe_exit(130)

    def _update_progress_tracking(
        self,
        progress,
        main_task_id,
        worker_tasks,
        last_completed,
        current_sleep,
        base_sleep,
        max_sleep,
        shared_progress_dict,  # Added parameter
    ):
        """Update progress tracking and return updated values."""
        # Update main progress
        current_completed = completed_tasks.value
        if current_completed != last_completed:
            progress.update(main_task_id, completed=current_completed)
            last_completed = current_completed
            # Reset sleep time on activity
            current_sleep = base_sleep
        else:
            # Increase sleep time when no activity (adaptive)
            current_sleep = min(current_sleep * 1.2, max_sleep)

        # Update per-worker progress bars
        self._update_worker_progress_bars(progress, worker_tasks, shared_progress_dict)
        return last_completed, current_sleep

    @staticmethod
    def _finalize_progress(progress, main_task_id, worker_tasks, total_tasks):
        """Finalize progress bars when monitoring is complete."""
        try:
            progress.update(
                main_task_id,
                completed=total_tasks,
                description="[green]All tasks complete![/green]",
            )

            # Hide individual worker progress bars when done
            for task_id in worker_tasks.values():
                with contextlib.suppress(Exception):
                    progress.update(task_id, visible=False)
        except Exception:
            pass  # Ignore final update errors

    def _monitor_pool_progress(
        self,
        async_results,
        pool,
        progress,
        main_task_id,
        total_tasks,
        shared_progress_dict,
    ):
        """Waits for the pool to finish, updating progress per worker with adaptive timing."""
        # Reset counters
        completed_tasks.value = 0
        last_completed = 0
        worker_tasks = {}

        # Adaptive timing - FIX: Reduce CPU waste
        base_sleep = 0.5  # Start with 500ms
        max_sleep = 2.0  # Max 2 seconds
        current_sleep = base_sleep

        # RPM monitoring (optional debug feature)
        rpm_start_time = time.time()
        rpm_last_log = rpm_start_time
        rpm_interval = 30.0  # Log every 30 seconds

        try:
            while not async_results.ready():
                if self._shutdown_event.is_set():
                    self._handle_shutdown_cleanup(
                        pool, progress, main_task_id, worker_tasks
                    )
                    return

                last_completed, current_sleep = self._update_progress_tracking(
                    progress,
                    main_task_id,
                    worker_tasks,
                    last_completed,
                    current_sleep,
                    base_sleep,
                    max_sleep,
                    shared_progress_dict,
                )

                # Optional RPM logging for rate limiting awareness
                current_time = time.time()
                if current_time - rpm_last_log >= rpm_interval:
                    elapsed = current_time - rpm_start_time
                    if elapsed > 0 and last_completed > 0:
                        rpm = (last_completed * 60) / elapsed
                        self.logger.debug(f"Processing rate: {rpm:.1f} requests/minute")
                    rpm_last_log = current_time

                time.sleep(current_sleep)

        except (KeyboardInterrupt, SystemExit):
            # Handle any remaining interrupts during monitoring
            self.logger.warning("[yellow]Progress monitoring interrupted[/yellow]")
            return
        except Exception as e:
            self.logger.error(f"Progress monitoring error: {e}")
            return

        # Final update - mark all as complete
        self._finalize_progress(progress, main_task_id, worker_tasks, total_tasks)

    def _run_worker_pool_with_progress(
        self, tasks: list[dict[str, str]]
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Initializes and monitors a multiprocessing pool with Rich progress bars for each worker."""
        if not tasks:
            return {}, {}

        # MEMORY: Better resource management - Force garbage collection before starting
        import gc  # noqa: PLC0415

        gc.collect()

        # Use context manager for proper cleanup - FIX: Memory leak prevention
        with multiprocessing.Manager() as manager:
            # Create shared dictionaries for this run
            shared_progress_dict = manager.dict()
            shared_cache = manager.dict()

            progress_columns = [
                SpinnerColumn(),
                TextColumn("{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed} of {task.total})"),
                TimeRemainingColumn(),
            ]

            with Progress(*progress_columns, transient=False) as progress:
                # Main progress task
                main_task_id = progress.add_task(
                    "[bold cyan]Overall Progress[/bold cyan]",
                    total=len(tasks),
                )

                worker_count = min(self.MAX_WORKERS, len(tasks))
                total_workers.value = worker_count

                self.logger.info(f"Starting {worker_count} worker processes...")

                with multiprocessing.Pool(
                    processes=worker_count,
                    initializer=_pool_initializer,
                    initargs=(shared_progress_dict, shared_cache),
                ) as pool:
                    async_results = pool.map_async(_doc_generation_worker, tasks)
                    self._monitor_pool_progress(
                        async_results,
                        pool,
                        progress,
                        main_task_id,
                        len(tasks),
                        shared_progress_dict,
                    )
                    result = self._collect_pool_results(async_results)

                    # Merge shared cache into preserved_cache for resume functionality
                    cache_result: dict[str, str] = dict(shared_cache) if result else {}

                    # MEMORY: Force cleanup
                    pool.close()
                    pool.join()
                    gc.collect()

                    return result, cache_result

    def run(self, path: str, dry_run: bool, all_files: bool, force_rebuild: bool):
        """Main entry point for documentation generation."""
        try:
            if self._shutdown_event.is_set():
                return

            files_to_process = self._validate_and_get_files(path, all_files)

            if not files_to_process:
                self.logger.info(
                    "No relevant files require documentation updates. Exiting."
                )
                return

            if dry_run:
                self._process_dry_run(files_to_process, force_rebuild)
            else:
                # IMPLEMENTED: Live run mode
                self._process_live_run(files_to_process, force_rebuild)

        except (KeyboardInterrupt, SystemExit):
            # CRITICAL: Force Windows-safe exit for any interruption
            self.logger.info("[yellow]Process interrupted by user.[/yellow]")
            windows_safe_exit(130)  # Standard SIGINT exit code
        except Exception as e:
            # CRITICAL: Force Windows-safe exit for any error
            self.logger.error(f"DocGenerator error: {e}")
            windows_safe_exit(1)

    def _get_git_changed_files(self, project_path: Path) -> list[Path]:
        """Get list of changed Python files using git with proper error handling."""
        self.logger.info("Detecting changes using 'git ls-files'...")

        timeout = 10

        try:
            command = [
                "git",
                "ls-files",
                "--modified",
                "--others",
                "--exclude-standard",
                "*.py",
            ]

            base_kwargs = {
                "capture_output": True,
                "text": True,
                "encoding": "utf-8",
                "timeout": timeout,
                "cwd": project_path,
            }

            if sys.platform == "win32":
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = subprocess.SW_HIDE

                result = subprocess.run(
                    command,
                    check=False,
                    startupinfo=startup_info,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    **base_kwargs,
                )
            else:
                result = subprocess.run(command, check=False, **base_kwargs)

            if result.returncode != 0:
                self.logger.error(f"Git command failed: {result.stderr.strip()}")
                return []

            output = result.stdout.strip()
            if not output:
                return []

            changed_paths = [
                project_path / p
                for p in output.splitlines()
                if p.endswith(".py") and (project_path / p).exists()
            ]

            if changed_paths:
                self.logger.info("Found changed files to process:")
                for file in changed_paths[: self.MAX_LOG_FILES_DISPLAY]:
                    self.logger.info(f"  -> {file}")
                if len(changed_paths) > self.MAX_LOG_FILES_DISPLAY:
                    self.logger.info(
                        f"  ... and {len(changed_paths) - self.MAX_LOG_FILES_DISPLAY} more files"
                    )

            return changed_paths

        except subprocess.TimeoutExpired:
            self.logger.error(f"Git command timed out after {timeout}s")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error running git command: {e}")
            return []

    @staticmethod
    def _get_node_identifier(file_path: Path, node: ast.AST) -> str:
        """Generate unique identifier for AST node with robust path resolution."""
        try:
            # Try relative to project root first
            try:
                relative_path = file_path.resolve().relative_to(PROJECT_ROOT)
                module_parts = relative_path.with_suffix("").parts
            except ValueError:
                # Fallback: try relative to current working directory
                try:
                    relative_path = file_path.resolve().relative_to(Path.cwd())
                    module_parts = relative_path.with_suffix("").parts
                except ValueError:
                    # Final fallback: just use the filename
                    module_parts = (file_path.stem,)

            module_path = ".".join(module_parts)
            return f"{module_path}.{node.name}"
        except Exception:
            # Ultimate fallback
            return f"{file_path.stem}.{node.name}"

    @staticmethod
    def _get_source_code(node: ast.AST, lines: list[str]) -> str:
        """Extract source code for given AST node."""
        start_line = node.lineno - 1
        end_line = getattr(node, "end_lineno", start_line + 1)
        return "".join(lines[start_line:end_line])


def _pool_initializer(shared_progress_dict, shared_cache_dict):
    """Initializer for worker processes to set up shared state and signal handling."""
    # CRITICAL: Ignore ALL signals in worker processes to prevent broken pipe errors
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

    # Windows-specific: Also ignore SIGBREAK
    if sys.platform == "win32":
        with contextlib.suppress(AttributeError):
            signal.signal(signal.SIGBREAK, signal.SIG_IGN)

    # Set up worker context
    _init_worker(shared_progress_dict, shared_cache_dict)
