# >> avcmt/modules/doc_generator.py
# Copyright 2025 Andy Vandaric
# ... (lisensi) ...

# FINAL REVISION: Fixed AttributeError by calling static methods via the
# class name (DocGenerator._) instead of the instance (self._).

import ast
import multiprocessing
import random
import subprocess
import threading
import time
from pathlib import Path

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
    setup_logging,
)


# ... (_doc_generation_worker dan DocGeneratorError tetap sama) ...
def _doc_generation_worker(args: dict) -> dict:
    """A single unit of work for a child process."""
    identifier, node_source, provider, model, debug = (
        args["identifier"],
        args["node_source"],
        args["provider"],
        args["model"],
        args["debug"],
    )
    delay = random.uniform(1.0, 3.0)
    time.sleep(delay)
    try:
        template_env = get_jinja_env("docs")
        template = template_env.get_template("docstring.j2")
        prompt = template.render(source_code=node_source)
        raw_response = generate_with_ai(
            prompt, provider=provider, model=model, debug=debug
        )
        cleaned = clean_docstring_response(raw_response)
        if cleaned:
            return {identifier: cleaned}
    except Exception as e:
        print(f"\nError in worker for '{identifier}': {e}")
    return {}


class DocGeneratorError(Exception):
    """Custom exception for doc generation failures."""


class DocGenerator:
    MAX_WORKERS = 4

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
        self.logger = setup_logging("docs.log")
        self._shutdown_event = shutdown_event

    def _get_git_changed_files(self, project_path: Path) -> list[Path]:
        """Gets a list of modified and untracked Python files using Git."""
        self.logger.info("Detecting changes using 'git ls-files'...")
        try:
            command = [
                "git",
                "ls-files",
                "--modified",
                "--others",
                "--exclude-standard",
            ]
            output = subprocess.run(
                command, capture_output=True, text=True, check=True, encoding="utf-8"
            ).stdout.strip()
            if not output:
                return []
            changed_paths = [Path(p) for p in output.splitlines() if p.endswith(".py")]
            absolute_project_path = project_path.resolve()
            filtered_files = [
                p
                for p in changed_paths
                if absolute_project_path == p.resolve()
                or absolute_project_path in p.resolve().parents
            ]
            if filtered_files:
                self.logger.info("Found changed files to process:")
                for file in filtered_files:
                    self.logger.info(f"  -> {file}")
            return filtered_files
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {e.stderr.strip()}")
            return []

    @staticmethod
    def _get_node_identifier(file_path: Path, node: ast.AST) -> str:
        """Generates a unique identifier for an AST node."""
        try:
            module_path = ".".join(
                file_path.resolve().relative_to(Path.cwd()).with_suffix("").parts
            )
            return f"{module_path}.{node.name}"
        except ValueError:
            return f"{file_path.name}.{node.name}"

    @staticmethod
    def _get_source_code(node: ast.AST, lines: list[str]) -> str:
        """Retrieves the source code snippet for a given AST node."""
        start_line = node.lineno - 1
        end_line = getattr(node, "end_lineno", start_line + 1)
        return "".join(lines[start_line:end_line])

    def _prepare_tasks(
        self, files_to_process: list[Path], force_rebuild: bool, preserved_cache: dict
    ) -> list[dict]:
        """Parses files and creates a list of task arguments for workers."""
        tasks = []
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
                    # FIXED: Call static methods via Class name 'DocGenerator'
                    identifier = DocGenerator._get_node_identifier(file_path, node)
                    if not force_rebuild and identifier in preserved_cache:
                        continue

                    # FIXED: Call static methods via Class name 'DocGenerator'
                    source_code = DocGenerator._get_source_code(
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
                    f"Failed to parse or prepare tasks for {file_path}: {e}",
                    exc_info=self.debug,
                )
        return tasks

    def _monitor_pool_progress(
        self, async_results, pool, progress, task_id, total_tasks
    ):
        """Waits for the pool to finish, updating progress and checking for shutdown."""
        while not async_results.ready():
            if self._shutdown_event.is_set():
                self.logger.warning(
                    "Shutdown signal received, terminating worker pool..."
                )
                pool.terminate()
                pool.join()
                return

            completed_count = total_tasks - async_results._number_left
            progress.update(
                task_id,
                completed=completed_count,
                description=f"Processing item {completed_count + 1}",
            )
            time.sleep(0.2)

        progress.update(
            task_id, completed=total_tasks, description="[green]All tasks complete!"
        )

    def _collect_pool_results(self, async_results) -> dict:
        """Safely collects results from the async_results object after completion."""
        if self._shutdown_event.is_set():
            self.logger.info("Result collection skipped due to user shutdown.")
            return {}

        try:
            suggestions = {}
            for res_dict in async_results.get():
                if res_dict:
                    suggestions.update(res_dict)
            return suggestions
        except Exception as e:
            self.logger.error(
                f"Error collecting results from pool: {e}", exc_info=self.debug
            )
            return {}

    def _run_worker_pool_with_progress(self, tasks: list[dict]) -> dict:
        """Initializes and monitors a multiprocessing pool with a Rich progress bar."""
        progress_columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed} of {task.total})"),
            TimeRemainingColumn(),
        ]

        with Progress(*progress_columns) as progress:
            task_id = progress.add_task(
                "[cyan]Generating docstrings...", total=len(tasks)
            )
            with multiprocessing.Pool(processes=self.MAX_WORKERS) as pool:
                async_results = pool.map_async(_doc_generation_worker, tasks)
                self._monitor_pool_progress(
                    async_results, pool, progress, task_id, len(tasks)
                )
                return self._collect_pool_results(async_results)

    def _execute_parallel_processing(
        self, files_to_process: list[Path], force_rebuild: bool, preserved_cache: dict
    ) -> dict[str, str]:
        """Prepares tasks and runs them in a managed worker pool."""
        tasks = self._prepare_tasks(files_to_process, force_rebuild, preserved_cache)
        if not tasks:
            self.logger.info("No new documentation tasks to run.")
            return {}
        return self._run_worker_pool_with_progress(tasks)

    def run(self, path: str, dry_run: bool, all_files: bool, force_rebuild: bool):
        """Main method to execute the documentation generation workflow."""
        if self._shutdown_event.is_set():
            return

        target_path = Path(path)
        if not target_path.exists():
            raise DocGeneratorError(f"Path does not exist: {target_path}")

        files_to_process = (
            (list(target_path.rglob("*.py")) if target_path.is_dir() else [target_path])
            if all_files
            else self._get_git_changed_files(target_path)
        )

        if not files_to_process:
            self.logger.info(
                "No relevant files require documentation updates. Exiting."
            )
            return

        if dry_run:
            self.logger.info("DRY RUN active.")
            preserved_cache = {}
            if not force_rebuild:
                preserved_cache = extract_docstrings_from_md(get_docs_dry_run_file())
                if preserved_cache:
                    self.logger.info(f"Loaded {len(preserved_cache)} items from cache.")

            all_new_suggestions = self._execute_parallel_processing(
                files_to_process, force_rebuild, preserved_cache
            )

            final_cache = {**preserved_cache, **all_new_suggestions}
            if final_cache:
                self.logger.info(
                    f"Writing {len(final_cache)} total items to dry-run file..."
                )
                # TODO: Implement _write_dry_run_file(final_cache)

            if self._shutdown_event.is_set():
                self.logger.warning("Dry run was aborted by user.")
            else:
                self.logger.info("\n✅ Dry run complete.")
        else:
            self.logger.warning("Live run mode needs to be implemented.")
