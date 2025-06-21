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

# File: avcmt/modules/commit_generator.py
# FINAL REVISION: Smartly handles push even with no new file changes.

import logging
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from avcmt.ai import generate_with_ai
from avcmt.utils import (
    clean_ai_response,
    extract_commit_messages_from_md,
    get_jinja_env,
    is_recent_dry_run,
    setup_logging,
)


class CommitError(Exception):
    """Custom exception indicating an error occurred during the commit generation process.

    This exception should be raised when the commit creation fails due to reasons such as invalid input data, conflicts, or internal errors during the commit procedure.

    Args:
        message (str): A descriptive message explaining the reason for the exception.

    Raises:
        CommitError: Always raised when a commit generation error occurs.
    """


class CommitGenerator:
    """Manages the AI-powered commit generation process by identifying changed files, generating commit messages, staging, committing, and optionally pushing changes. Supports dry runs, caching, and configuration options for provider, model, and debugging.

    Args:
        dry_run (bool): If True, performs a dry run without making actual commits or pushes.
        push (bool): If True, pushes commits to the remote repository after committing.
        debug (bool): If True, enables debug-level logging and verbose output.
        force_rebuild (bool): If True, regenerates commit messages even if cached.
        provider (str): Name of the AI provider to use (default is "pollinations").
        model (str): Name of the AI model to use (default is "gemini").
        logger (Any or None): Logger instance for logging; defaults to internal setup if None.
        **kwargs: Additional keyword arguments passed to the AI generation function.

    Returns:
        None
    """

    def __init__(
        self,
        dry_run: bool = False,
        push: bool = False,
        debug: bool = False,
        force_rebuild: bool = False,
        provider: str = "pollinations",
        model: str = "gemini",
        logger: Any | None = None,
        **kwargs,
    ):
        """Initializes a class instance with configuration options for operation modes, provider, model, logging, and additional parameters.

        Args:
            dry_run (bool): If True, simulates operations without making changes.
            push (bool): If True, performs push operations after processing.
            debug (bool): If True, enables debug-level logging and output.
            force_rebuild (bool): If True, forces rebuilding of components.
            provider (str): Specifies the provider to use; defaults to "pollinations".
            model (str): Specifies the model to utilize; defaults to "gemini".
            logger (Any | None): Logger object for recording logs; if None, a default logger is set up.
            **kwargs: Additional keyword arguments for extended configuration.

        Returns:
            None
        """
        self.dry_run = dry_run
        self.push = push
        self.debug = debug
        self.force_rebuild = force_rebuild
        self.provider = provider
        self.model = model
        self.logger = logger or setup_logging("log/commit.log")
        self.kwargs = kwargs
        self.dry_run_file = Path("log") / "commit_messages_dry_run.md"
        self.commit_template_env = get_jinja_env("commit")

    # ... (Metode helper lain dari _run_git_command hingga _get_commit_message tetap sama) ...
    def _run_git_command(self, command: list[str], ignore_errors: bool = False) -> str:
        """Executes a git command and returns its standard output as a string; raises a CommitError if the command fails.

        Args:
            command (list[str]): The git command and its arguments to execute.
            ignore_errors (bool, optional): If True, suppresses exceptions on command failure. Defaults to False.

        Returns:
            str: The stripped standard output of the git command.

        Raises:
            CommitError: If the git command fails and ignore_errors is False.
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=not ignore_errors,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_message = (
                f"Git command '{' '.join(e.cmd)}' failed: {e.stderr.strip()}"
            )
            self.logger.error(error_message)
            raise CommitError(error_message) from e

    def _get_changed_files(self) -> list[str]:
        """Returns a list of file paths that have been deleted, modified, or are untracked in the current Git repository. The method executes a Git command to retrieve the list of such files and processes the output to return a clean list of file paths with whitespace trimmed.

        Args:
            None

        Returns:
            list[str]: A list of strings, each representing the path to a changed, deleted, or untracked file.
        """
        output = self._run_git_command(
            [
                "git",
                "ls-files",
                "--deleted",
                "--modified",
                "--others",
                "--exclude-standard",
            ]
        )
        return [line.strip() for line in output.split("\n") if line.strip()]

    @staticmethod
    def _group_files_by_directory(files: list[str]) -> dict[str, list[str]]:
        """Groups a list of file paths by their parent directories.

        This function takes a list of file path strings and organizes them into a dictionary where each key is the name of the parent directory, and the corresponding value is a list of files contained within that directory. Files located at the root level, with no parent directory, are grouped under the key "root".

        Args:
            files (list of str): A list of file path strings to be grouped.

        Returns:
            dict of str to list of str: A dictionary mapping directory names to lists of file paths.
        """
        grouped = defaultdict(list)
        for file_path in files:
            parent_dir = str(Path(file_path).parent)
            if parent_dir == ".":
                parent_dir = "root"
            grouped[parent_dir].append(file_path)
        return grouped

    def _get_diff_for_files(self, files: list[str]) -> str:
        """Generate a diff for the specified files staged in Git. This method runs a Git command to retrieve the differences between the staged version of the given files and their last committed state, returning the diff output as a string.

        Args:
            files (list[str]): A list of file paths for which the diff should be generated.

        Returns:
            str: The diff output as a string.
        """
        return self._run_git_command(
            ["git", "--no-pager", "diff", "--staged", "--", *files]
        )

    def _write_dry_run_header(self):
        """Writes the header information to the dry run file, including metadata and a timestamp. This method creates necessary directories and initializes the file with appropriate headers and timestamp information. It does not take any parameters and does not return a value, but may raise exceptions if directory creation or file writing encounters an error."""
        self.dry_run_file.parent.mkdir(parents=True, exist_ok=True)
        with self.dry_run_file.open("w", encoding="utf-8") as f:
            ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S (%Z)")
            f.write("# AI Semantic Release Commit Messages (Dry Run)\n")
            f.write(f"_Last generated: {ts}_\n\n")
            f.write("Automatically generated by `avcmt --dry-run`\n\n")

    def _write_dry_run_entry(self, group_name: str, commit_message: str):
        """Writes a dry run entry to a designated file by appending formatted group name and commit message. This method adds a markdown-formatted section containing the group name and commit message to the dry run log file for review purposes.

        Args:
            group_name (str): The name of the group associated with the commit.
            commit_message (str): The commit message to log in the dry run file.

        Returns:
            None
        """
        with self.dry_run_file.open("a", encoding="utf-8") as f:
            f.write(
                f"## Group: `{group_name}`\n\n```md\n{commit_message}\n```\n\n---\n\n"
            )

    def _stage_changes(self, files: list[str]):
        """Stages the specified list of files in the Git repository. If the list is empty, the method exits immediately without performing any operations. This method adds the provided files to the staging area and logs the operation.

        Args:
            files (list[str]): A list of file paths to be staged.

        Returns:
            None
        """
        if not files:
            return
        self.logger.info(f"Staging files for group: {files}")
        self._run_git_command(["git", "add", *files])

    def _commit_changes(self, message: str):
        """Commits staged changes to the git repository with a specified commit message.

        This method logs the commit action and executes the git command to create a commit containing the current staged changes, using the provided commit message.

        Args:
            message (str): The commit message to associate with the changes.

        Returns:
            None
        """
        self.logger.info(f"Committing with message:\n{message}")
        self._run_git_command(["git", "commit", "-m", message])

    def _push_changes(self):
        """Pushes all local commits to the currently active remote branch. This method logs the start of the push process, executes the `git push` command to update the remote repository with local changes, and logs a success message upon completion. It may raise a subprocess.CalledProcessError if the push command fails or an AttributeError if the required attributes are not properly initialized."""
        self.logger.info("Pushing all commits to the active remote branch...")
        self._run_git_command(["git", "push"])
        self.logger.info("✔️ All changes pushed successfully.")

    def _get_commit_message(
        self, group_name: str, diff: str, cached_messages: dict
    ) -> str:
        """Gets or generates a commit message for the specified group, utilizing caching and AI assistance. If caching is enabled and a message exists in cached_messages for the given group_name, the cached message is returned. Otherwise, a new message is generated by rendering a template with the provided diff and group name, then processed through an AI provider to produce a formatted commit message.

        Args:
            group_name (str): The name of the group for which the commit message is generated.
            diff (str): The diff text to be included in the commit message.
            cached_messages (dict): A dictionary containing cached commit messages, keyed by group name.

        Returns:
            str: The generated or cached commit message.
        """
        if not self.force_rebuild and group_name in cached_messages:
            self.logger.info(f"[CACHED] Using cached message for {group_name}.")
            return cached_messages[group_name]
        if self.force_rebuild and group_name in cached_messages:
            self.logger.info(f"[FORCED] Ignoring cache for {group_name}.")
        template = self.commit_template_env.get_template("commit_message.j2")
        prompt = template.render(group_name=group_name, diff_text=diff)
        raw_message = generate_with_ai(
            prompt,
            provider=self.provider,
            model=self.model,
            debug=self.debug,
            **self.kwargs,
        )
        return clean_ai_response(raw_message)

    # --- FUNGSI HELPER BARU ---
    def _is_local_ahead(self) -> bool:
        """Checks whether the local Git branch is ahead of its remote counterpart by one or more commits. This method fetches updates from the remote repository, compares commit counts between local and remote branches, and determines if there are local commits not present on the remote. If the branch has not been pushed before, it considers it ahead if there are local commits despite the absence of upstream tracking.

        Args:
            None

        Returns:
            bool: True if the local branch has commits that are not present on the remote, False otherwise.
        """
        try:
            # Pastikan remote-tracking branch ada
            self._run_git_command(["git", "fetch", "origin"])
            # Hitung jumlah commit yang ada di lokal tapi tidak di remote
            output = self._run_git_command(
                ["git", "rev-list", "--count", "@{u}..HEAD"], ignore_errors=True
            )
            if output and int(output) > 0:
                self.logger.info(
                    f"Local branch is ahead of remote by {output} commit(s)."
                )
                return True
        except CommitError as e:
            # Ini bisa terjadi jika branch belum pernah di-push (tidak ada upstream)
            self.logger.warning(
                f"Could not check remote status (branch may be new): {e}"
            )
            # Anggap saja 'ahead' jika ada commit lokal tapi upstream belum ada
            return bool(
                self._run_git_command(["git", "rev-parse", "HEAD"], ignore_errors=True)
            )
        return False

    def run(self):
        """Performs the main execution logic, including checking for file changes and branch status, and manages commit and push operations accordingly. Returns nothing. Raises exceptions related to underlying operations if any occur during file retrieval, grouping, caching, processing, or finalization."""
        initial_files = self._get_changed_files()
        local_is_ahead = self._is_local_ahead()

        # --- LOGIKA BARU: Keluar hanya jika tidak ada perubahan DAN tidak ada commit untuk di-push ---
        if not initial_files and not local_is_ahead:
            self.logger.info(
                "No changed files and local branch is up-to-date. Nothing to do."
            )
            return

        # Proses commit hanya jika ada perubahan file
        if initial_files:
            grouped_files = self._group_files_by_directory(initial_files)
            cached_messages = self._prepare_cache()
            _, failed_groups = self._process_groups(grouped_files, cached_messages)
        else:
            # Jika tidak ada file baru, tapi lokal lebih maju, lewati proses commit
            self.logger.info(
                "No new file changes to commit, but local branch is ahead. Proceeding to push."
            )
            failed_groups = []

        self._finalize_run(failed_groups)

    # ... (Metode _prepare_cache, _process_groups, _process_single_group tidak berubah dari patch sebelumnya) ...
    def _prepare_cache(self) -> dict[str, str]:
        """Returns a dictionary that maps strings to strings containing cached data. If dry_run mode is enabled, it writes a dry run header and returns an empty dictionary. If a recent dry run cache exists and force_rebuild is False, it logs an informational message indicating that the cache is being loaded from the dry run file and returns the extracted commit messages from the dry run file. Otherwise, it returns an empty dictionary."""
        if self.dry_run:
            self._write_dry_run_header()
            return {}
        if not self.force_rebuild and is_recent_dry_run(self.dry_run_file):
            self.logger.info(f"Recent cache found. Loading from {self.dry_run_file}")
            return extract_commit_messages_from_md(self.dry_run_file)
        return {}

    def _process_groups(
        self, grouped_files: dict, cached_messages: dict
    ) -> tuple[list, list]:
        """Performs processing of grouped files and categorizes groups into successful or failed based on the processing outcome.

        This method iterates through each group in the `grouped_files` dictionary, processes each group via the `_process_single_group` method, and segregates the groups into successful or failed lists accordingly.

        Args:
            grouped_files (dict): A dictionary where keys are group names (strings) and values are lists of filenames associated with each group.
            cached_messages (dict): A dictionary containing cached message data used during processing.

        Returns:
            tuple of (list, list): A tuple where the first list contains names of groups that were successfully processed, and the second list contains names of groups that failed processing.
        """
        successful_groups, failed_groups = [], []
        for group_name, files in grouped_files.items():
            was_successful = self._process_single_group(
                group_name, files, cached_messages
            )
            if was_successful:
                successful_groups.append(group_name)
            else:
                failed_groups.append(group_name)
        return successful_groups, failed_groups

    def _process_single_group(
        self, group_name: str, files: list, cached_messages: dict
    ) -> bool:
        """Performs processing on a single group of files, handling diff detection, commit message creation, and staging or resetting changes as needed.

        Args:
        - group_name (str): The name of the group being processed.
        - files (list): A list of file paths to be processed.
        - cached_messages (dict): A dictionary of cached messages used for commit message generation.

        Returns:
        - bool: True if the processing was successful and the changes were staged or reset; False if the commit message was empty and the group was skipped.
        """
        self._stage_changes(files)
        diff = self._get_diff_for_files(files)
        if not diff.strip():
            self.logger.info(f"[SKIP] No diff for group {group_name}. Unstaging.")
            self._run_git_command(["git", "reset", "HEAD", "--", *files])
            return True
        commit_message = self._get_commit_message(group_name, diff, cached_messages)
        if not commit_message:
            self.logger.error(f"Skipping group '{group_name}' due to empty message.")
            return False
        if self.dry_run:
            self._write_dry_run_entry(group_name, commit_message)
            self._run_git_command(["git", "reset", "HEAD", "--", *files])
        else:
            self._commit_changes(commit_message)
        return True

    def _finalize_run(self, failed_groups: list):
        """Performs finalization tasks after a commit operation, handling push actions and logging relevant information based on success or failure.

        Args:
            failed_groups (list): A list of group identifiers that failed during processing.

        Returns:
            None
        """
        if self.push and not self.dry_run:
            if not failed_groups:
                self._push_changes()
            else:
                self.logger.error(
                    "❌ Push aborted because one or more commit groups failed."
                )

        if self.dry_run:
            self.logger.info(
                f"✅ DRY RUN COMPLETED. Review suggestions in: {self.dry_run_file.resolve()}"
            )
        else:
            self.logger.info("✅ Commit process completed.")
            if failed_groups:
                self.logger.warning(
                    f"The following groups were skipped: {', '.join(failed_groups)}"
                )
                self.logger.warning(
                    "Please review the changes, commit them manually, and then push."
                )


def run_commit_group_all(**kwargs):
    """Performs initialization and execution of the CommitGenerator to process commit groups; handles exceptions during the process.

    Args:
        **kwargs:** Additional keyword arguments to pass to the CommitGenerator constructor. Type: dict.

    Returns:
        None.

    Raises:
        CommitError: If the commit process encounters a commit-related error during execution.
        Exception: If any other unexpected error occurs during the process.
    """
    logger = logging.getLogger("avcmt")
    try:
        generator = CommitGenerator(**kwargs)
        generator.run()
    except (CommitError, Exception) as e:
        logger.error(f"FATAL: The commit process failed: {e}", exc_info=True)


__all__ = ["run_commit_group_all"]
