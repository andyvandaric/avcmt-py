# >> avcmt/modules/doc_generator.py
# Copyright 2025 Andy Vandaric
# (lisensi lengkap di sini)

"""
Module for generating and formatting docstrings for Python files using AI.
FINAL REVISION: Fixes linter error PLR6301 by converting method to static.
"""

import ast
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import TextIO

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
    extract_docstrings_from_md,
    get_docs_dry_run_file,
    get_jinja_env,
    is_recent_dry_run,
    setup_logging,
)


class DocGeneratorError(Exception):
    """Custom exception indicating a failure during documentation generation.

    This exception is raised when the process of generating documentation encounters an error that prevents successful completion.
    """


class DocGenerator:
    """Performs analysis and updates of Python files by generating or reformatting docstrings using AI, with change tracking, backup creation, and support for dry run and live modes.

    This class manages the entire documentation generation process, including identifying changed files, backing up original files, interfacing with AI services to generate docstrings, applying updates to source code, and handling dry run versus live execution modes.

    Args:
        provider (str): The AI service provider to use (default is "pollinations").
        model (str): The specific AI model to utilize (default is "gemini").
        debug (bool): Enables debug logging for detailed tracebacks (default is False).

    Returns:
        None
    """

    BACKUP_ROOT = "backup"
    STATE_FILE = "log/docs_state.json"

    def __init__(
        self, provider: str = "pollinations", model: str = "gemini", debug: bool = False
    ):
        """Initializes the class with specified provider, model, and debug settings, and sets up logging, Jinja2 environment for documentation, a dry run file, and progress display columns for use during documentation generation.

        Args:
            provider (str, optional): The name of the service provider to use. Defaults to "pollinations".
            model (str, optional): The model to be utilized for documentation purposes. Defaults to "gemini".
            debug (bool, optional): Flag indicating whether to enable debug mode. Defaults to False.

        Returns:
            None
        """
        self.provider = provider
        self.model = model
        self.debug = debug
        self.logger = setup_logging("log/docs.log")
        self.doc_template_env = get_jinja_env("docs")
        self.dry_run_file = get_docs_dry_run_file()
        self.progress_columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeRemainingColumn(),
        ]

    # ... (Metode-metode lain seperti _load_state, _save_state, _get_changed_files, dll, tidak berubah) ...
    def _load_state(self) -> dict[str, float]:
        """Loads the saved state data from a JSON file specified by `self.STATE_FILE`. If the file does not exist or contains invalid JSON, returns an empty dictionary. The returned dictionary has string keys and float values representing the loaded state."""
        state_path = Path(self.STATE_FILE)
        if not state_path.exists():
            return {}
        try:
            with state_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def _save_state(self, state: dict[str, float]):
        """Saves the provided state dictionary to a JSON file, creating necessary directories if they do not exist.

        This method serializes the `state` dictionary, which contains string keys and float values, and writes it to the file specified by `self.STATE_FILE` in JSON format with indentation for readability.

        Args:
            state (dict[str, float]): A dictionary representing the current state, with string keys and float values.

        Returns:
            None
        """
        state_path = Path(self.STATE_FILE)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with state_path.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def _get_changed_files(self, all_files: list[Path]) -> list[Path]:
        """Performs detection of recently modified files from the provided list and returns the list of files that have changed.

        Args:
            all_files (list of Path): A list of Path objects representing the files to check for modifications.

        Returns:
            list of Path: A list containing the Path objects of files that have been changed since the last recorded state.
        """
        self.logger.info("Checking for recently modified files...")
        last_state = self._load_state()
        changed_files = []
        for file in all_files:
            file_key = str(file.resolve())
            current_mtime = file.stat().st_mtime
            if last_state.get(file_key) is None or current_mtime > last_state.get(
                file_key, 0
            ):
                changed_files.append(file)
                self.logger.info(f"  -> Detected change in: {file}")
        if not changed_files and all_files:
            self.logger.info("No file changes detected since last run.")
        return changed_files

    def _create_backup(self, file_path: Path, backup_dir: Path):
        """Creates a backup copy of the specified file in the designated backup directory. This method logs the backup process, ensures the backup directory exists, and handles potential exceptions during copying.

        Args:
            file_path (Path): The path to the original file to be backed up.
            backup_dir (Path): The directory where the backup copy will be stored.

        Returns:
            None

        Raises:
            Exceptions propagated from Path operations or shutil.copy2, if any occur during the backup process.
        """
        self.logger.info(f"Creating backup for {file_path}")
        if not file_path.exists():
            return
        try:
            relative_path = file_path.resolve().relative_to(Path.cwd().resolve())
            backup_path_full = backup_dir.resolve() / relative_path
            backup_path_full.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path_full)
        except Exception as e:
            self.logger.error(f"Failed to create backup for {file_path}: {e}")

    @staticmethod
    def _get_source_code(node: ast.AST, lines: list[str]) -> str:
        """Retrieves the source code snippet corresponding to a given AST node from the original source lines. This function extracts the source code associated with a specific Abstract Syntax Tree (AST) node based on line number information and source lines, facilitating analysis or transformation tasks that require the original code context.

        Args:
            node (ast.AST): The AST node for which to retrieve the source code.
            lines (list[str]): The list of source code lines read from the source file.

        Returns:
            str: A string containing the source code snippet corresponding to the provided AST node.
        """
        start_line = node.lineno - 1
        end_line = getattr(node, "end_lineno", start_line + 1)
        return "".join(lines[start_line:end_line])

    @staticmethod
    def _get_node_identifier(file_path: Path, node: ast.AST) -> str:
        """Generates a unique identifier for an AST node based on its file path and name.

        If the file is located within the current working directory, this function constructs a module-like path by relative to the current directory and appends the node's name, providing a fully qualified identifier. If the file path is outside the current working directory, it defaults to using the file name combined with the node's name.

        Args:
            file_path (Path): The path to the source file containing the node.
            node (ast.AST): The AST node for which the identifier is generated; expects the node to have a 'name' attribute.

        Returns:
            str: A string representing the node's unique identifier, either as a module path with the node name or as the file name with the node name.
        """
        try:
            module_path = ".".join(
                file_path.resolve().relative_to(Path.cwd()).with_suffix("").parts
            )
            return f"{module_path}.{node.name}"
        except ValueError:
            return f"{file_path.name}.{node.name}"

    def _generate_docstring_via_ai(self, identifier: str, node_source: str) -> str:
        """Generates a docstring for the given source code by querying an AI model.

        Constructs a prompt from the source code, sends it to an AI provider to generate an appropriate docstring, and returns the cleaned result. This method includes logging for debugging purposes and gracefully handles exceptions by returning an empty string if an error occurs.

        Args:
            identifier (str): A unique identifier for the source code block, used for logging purposes.
            node_source (str): The source code for which to generate the docstring.

        Returns:
            str: The generated and cleaned docstring, or an empty string if the generation process fails.
        """
        self.logger.info(f"Querying AI for: {identifier}")
        try:
            template = self.doc_template_env.get_template("docstring.j2")
            prompt = template.render(source_code=node_source)
            if self.debug:
                self.logger.info(f"--- PROMPT for {identifier} ---\n{prompt}")
            raw_response = generate_with_ai(
                prompt, provider=self.provider, model=self.model
            )
            if self.debug:
                self.logger.info(
                    f"--- RAW AI RESPONSE for {identifier} ---\n{raw_response}"
                )
            return clean_docstring_response(raw_response)
        except Exception as e:
            self.logger.error(
                f"Failed to generate docstring for {identifier}: {e}",
                exc_info=self.debug,
            )
            return ""

    # --- BUG FIX: LINTER ERROR PLR6301 ---
    @staticmethod
    def _update_docstring(
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

    def _process_single_file(
        self,
        file_path: Path,
        dry_run_writer: TextIO | None,
        backup_dir: Path | None,
        force_rebuild: bool,
        cached_docstrings: dict,
    ):
        """Performs processing of a single Python file to generate or update docstrings for functions and classes, with optional dry run and backup support.

        Args:
            file_path (Path): The path to the Python source file to process.
            dry_run_writer (TextIO or None): If provided, writes the proposed docstring changes to this writer instead of modifying the file.
            backup_dir (Path or None): Directory where backups will be saved if modifications are made.
            force_rebuild (bool): Whether to regenerate docstrings even if cached values are available.
            cached_docstrings (dict): Dictionary mapping node identifiers to their cached docstring content.

        Returns:
            None

        Raises:
            Exceptions may be raised during file reading, parsing, or writing operations, but are caught and logged within the method.
        """
        try:
            content_str = file_path.read_text(encoding="utf-8")
            content_lines = content_str.splitlines(keepends=True)
            tree = ast.parse(content_str)
            file_was_modified = False
            nodes_to_process = [
                n
                for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            ]

            for node in sorted(nodes_to_process, key=lambda n: n.lineno, reverse=True):
                identifier = self._get_node_identifier(file_path, node)
                if dry_run_writer and identifier in cached_docstrings:
                    continue

                new_docstring = cached_docstrings.get(identifier)
                if not new_docstring or (force_rebuild and not dry_run_writer):
                    source_code = self._get_source_code(node, content_lines)
                    new_docstring = self._generate_docstring_via_ai(
                        identifier, source_code
                    )

                # --- ADDED SAFETY CHECK ---
                # After cleaning, if the docstring is empty, skip to the next node.
                if not new_docstring:
                    self.logger.warning(
                        f"Skipping {identifier} due to empty docstring after generation/cleaning."
                    )
                    continue
                # --- END OF SAFETY CHECK ---

                if dry_run_writer:
                    dry_run_writer.write(
                        f'### `{identifier}`\n\n```python\n"""\n{new_docstring}\n"""\n```\n\n---\n\n'
                    )
                    dry_run_writer.flush()
                else:
                    content_lines = DocGenerator._update_docstring(
                        content_lines, node, new_docstring
                    )
                    file_was_modified = True

            if file_was_modified and backup_dir:
                final_content = "".join(content_lines)
                if final_content != content_str:
                    self._create_backup(file_path, backup_dir)
                    file_path.write_text(final_content, encoding="utf-8")
                    self.logger.info(f"Successfully wrote changes to {file_path}")
        except Exception as e:
            self.logger.error(
                f"Failed to process {file_path}: {e}", exc_info=self.debug
            )

    # ... (Metode run, _run_dry_mode, _run_live_mode tetap sama) ...
    def run(self, path: str, dry_run: bool, all_files: bool, force_rebuild: bool):
        """Performs documentation generation for specified Python files, supporting dry run and incremental update modes.

        This method processes files or directories to generate or update documentation, with options to simulate the process without making changes, process all files regardless of modification status, or force a rebuild of documentation even if up-to-date.

        Args:
            path (str): The file or directory path to process.
            dry_run (bool): If True, runs in dry mode without making changes.
            all_files (bool): If True, processes all Python files regardless of modification status.
            force_rebuild (bool): If True, forces regeneration of documentation even if up-to-date.

        Returns:
            None

        Raises:
            DocGeneratorError: If the provided path does not exist.
        """
        target_path = Path(path)
        if not target_path.exists():
            raise DocGeneratorError(f"Path does not exist: {target_path}")

        project_files = (
            list(target_path.rglob("*.py")) if target_path.is_dir() else [target_path]
        )

        # Logika pemilihan file tetap sama
        files_to_process = (
            self._get_changed_files(project_files) if not all_files else project_files
        )

        if not files_to_process:
            self.logger.info("No files require documentation updates. Exiting.")
            return

        if dry_run:
            self._run_dry_mode(files_to_process, force_rebuild)
        else:
            # --- START: BUG FIX SECTION ---
            cached_docstrings = {}

            # CHANGED LOGIC: Use cache if it's recent OR if --all-files is used.
            # This ensures that a full run uses the complete existing cache.
            use_cache = not force_rebuild and (
                is_recent_dry_run(self.dry_run_file) or all_files
            )

            if use_cache:
                self.logger.info(
                    f"Recent cache or --all-files flag found. Loading from {self.dry_run_file}"
                )
                cached_docstrings = extract_docstrings_from_md(self.dry_run_file)
                if not cached_docstrings:
                    self.logger.warning(
                        "Cache file was found but it is empty. AI will be queried."
                    )
            else:
                self.logger.warning(
                    "No recent cache, --all-files is off, or --force-rebuild is active. AI will be queried."
                )

            self._run_live_mode(files_to_process, force_rebuild, cached_docstrings)
            # --- END: BUG FIX SECTION ---

        if not dry_run and files_to_process:
            self.logger.info("Updating file modification state...")
            current_state = self._load_state()
            for fp in files_to_process:
                current_state[str(fp.resolve())] = fp.stat().st_mtime
            self._save_state(current_state)

    def _run_dry_mode(self, files_to_process: list[Path], force_rebuild: bool):
        """Performs a dry run to process a list of files, generating and caching docstring suggestions without making permanent changes. This method manages the dry run cache file by clearing it if `force_rebuild` is enabled, appends generated suggestions and timestamps, and provides real-time progress updates using a progress indicator. It leverages existing cache data if available and calls an internal method to process each individual file during the dry run."""
        self.logger.info(f"DRY RUN active. Caching to {self.dry_run_file}")
        if force_rebuild:
            self.logger.info("--force-rebuild active. Clearing existing cache.")
            self.dry_run_file.write_text("")
        existing_cache = extract_docstrings_from_md(self.dry_run_file)
        with Progress(*self.progress_columns, transient=False) as progress:
            task = progress.add_task(
                "[cyan]Generating suggestions...", total=len(files_to_process)
            )
            with self.dry_run_file.open("a", encoding="utf-8") as f:
                if not existing_cache:
                    ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S (%Z)")
                    f.write(
                        f"# AI-Generated Docstrings (Dry Run)\n_Last generated: {ts}_\n\n"
                    )
                for file_path in files_to_process:
                    progress.update(
                        task,
                        description=f"[cyan]Scanning [bold]{file_path.name}[/bold]",
                    )
                    self._process_single_file(
                        file_path, f, None, force_rebuild, existing_cache
                    )
                    progress.advance(task)

    def _run_live_mode(
        self, files_to_process: list[Path], force_rebuild: bool, cached_docstrings: dict
    ):
        """Performs live processing to update documentation across a list of files, handling backups and providing real-time progress updates. This method initializes backup directories based on the current timestamp, logs the start of the operation, and iterates through each file to process and update its documentation, displaying progress through a visual progress bar.

        Args:
            files_to_process (list[Path]): A list of Path objects representing the files to be processed.
            force_rebuild (bool): If True, forces a rebuild of the documentation, ignoring any cached data.
            cached_docstrings (dict): A dictionary containing cached docstrings for reuse during processing.
        """
        start_time = datetime.now()
        backup_dir = (
            Path(self.BACKUP_ROOT) / f"docs_{start_time.strftime('%Y%m%d_%H%M%S')}"
        )
        self.logger.info(f"LIVE RUN active. Backups will be saved to: {backup_dir}")
        with Progress(*self.progress_columns, transient=False) as progress:
            task = progress.add_task(
                "[green]Updating files...", total=len(files_to_process)
            )
            for file_path in files_to_process:
                progress.update(
                    task, description=f"[green]Updating [bold]{file_path.name}[/bold]"
                )
                self._process_single_file(
                    file_path, None, backup_dir, force_rebuild, cached_docstrings
                )
                progress.advance(task)
