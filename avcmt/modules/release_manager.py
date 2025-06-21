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

# File: avcmt/release.py -> avcmt/modules/release_manager.py
# Final Revision v7 - Fixed 'empty separator' bug in _update_changelog.

import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import toml

# Impor absolut dari dalam package Anda adalah best practice
from avcmt.utils import setup_logging

logger = setup_logging("log/semantic_release.log")


class ReleaseFailedError(Exception):
    """Custom exception indicating a failure during the release process.

    This exception is used to signal that the release process has encountered an unrecoverable error or an unexpected condition that prevents it from completing successfully. It inherits from the base Exception class without adding additional functionality, serving primarily as a specific indicator of release failures.

    Args:
        None

    Returns:
        None

    Raises:
        ReleaseFailedError: Always raised to indicate a release failure.
    """

    pass


class ReleaseManager:
    """Manages the entire semantic release process, including version bumping, changelog updates, git tagging, and optional publishing.

    This class orchestrates various static and instance methods to perform pre-release checks, determine version
    increments based on commit messages, generate formatted changelog sections, and coordinate pushing changes
    and publishing artifacts. It encapsulates the workflow needed for automated semantic releases.

    Args:
        config_path (str): Path to the configuration file (default is "pyproject.toml"). Specifies release settings such as version file location, branch, repository URL, and PyPI publish flag.

    Raises:
        ReleaseFailedError: If any step in the release process fails, such as configuration errors, git errors, or file I/O issues.
    """

    # NEW: Define section headers with emojis and desired formatting
    SECTION_HEADERS_WITH_EMOJIS: ClassVar[dict[str, str]] = {
        "feat": "### 🚀 Features",
        "fix": "### 🐛 Bug Fixes",
        "perf": "### ⚡ Performance Improvements",
        "refactor": "### 🛠️ Refactoring",
        "docs": "### 📚 Documentation",
        "style": "### 💅 Styles",
        "test": "### 🧪 Tests",
        "build": "### 🏗️ Build System",
        "ci": "### 🔄 Continuous Integration",
        "chore": "### 🧹 Chores",
        # Default for unrecognized types or 'other'
        "other": "### 📦 Others",
    }

    def __init__(self, config_path: str = "pyproject.toml"):
        """Initializes the manager by loading configuration data from the specified path and validating the version path format. This constructor reads the configuration file at the given `config_path` (defaulting to "pyproject.toml"), extracts the `version_path` value, and splits it into `version_file_path` and `version_key_path` based on the colon separator. If the format of `version_path` does not match the expected "file:key.path" pattern, it raises a `ReleaseFailedError`. Additionally, it initializes attributes to track the old and new version strings and a list to store commit information.

        Args:
            config_path (str): The path to the configuration file to load (default is "pyproject.toml").

        Raises:
            ReleaseFailedError: If the `version_path` in the configuration does not conform to the expected "file:key.path" format.
        """
        self.config = ReleaseManager._load_config(config_path)
        self.old_version: str | None = None
        self.new_version: str | None = None
        self.commits: list[dict[str, str]] = []

        # Validate and parse version_path once on initialization.
        try:
            self.version_file_path, self.version_key_path = self.config[
                "version_path"
            ].split(":", 1)
        except ValueError:
            raise ReleaseFailedError(
                f"Invalid 'version_path' format: '{self.config['version_path']}'. "
                "Expected format is 'file:key.path'."
            ) from None

    # --- Static Methods (Stateless Utilities) ---

    @staticmethod
    def _load_config(path: str) -> dict[str, Any]:
        """Loads release configuration details from the specified `pyproject.toml` file.

        This function reads the given file, extracts relevant release settings from the `[tool.avcmt.release]` section, and returns them as a dictionary containing parameters such as `version_path`, `changelog_file`, `branch`, `repo_url`, and `publish_to_pypi`.

        Args:
            path (str): The file system path to the `pyproject.toml` configuration file.

        Returns:
            dict[str, Any]: A dictionary with release configuration parameters, including `'version_path'`, `'changelog_file'`, `'branch'`, `'repo_url'`, and `'publish_to_pypi'`.

        Raises:
            ReleaseFailedError: If the configuration file is not found at the specified path or if an error occurs during parsing.
        """
        try:
            pyproject = toml.load(path)
            config = pyproject.get("tool", {}).get("avcmt", {}).get("release", {})
            return {
                "version_path": config.get(
                    "version_path", "pyproject.toml:tool.poetry.version"
                ),
                "changelog_file": config.get("changelog_file", "CHANGELOG.md"),
                "branch": config.get("branch", "main"),
                "repo_url": config.get("repo_url"),  # URL for commit links
                "publish_to_pypi": config.get("publish_to_pypi", False),
            }
        except FileNotFoundError:
            raise ReleaseFailedError(f"Configuration file not found at: {path}")
        except Exception as e:
            raise ReleaseFailedError(f"Failed to parse configuration: {e}") from e

    @staticmethod
    def _run_command(command: list[str], sensitive_output: bool = False):
        """Performs a command in a subprocess, captures its output, and raises a custom exception if the command fails. It executes the provided command list with optional suppression of output logging, returning the command's standard output as a string with whitespace trimmed; raises a ReleaseFailedError if the command execution fails.

        Args:
        - command (list of str): The command and its arguments to run.
        - sensitive_output (bool, optional): If True, suppresses debug logging of the command's output. Defaults to False.

        Returns:
        - str: The trimmed standard output from the command execution.

        Raises:
        - ReleaseFailedError: If the command fails to execute successfully.
        """
        try:
            process = subprocess.run(
                command, check=True, capture_output=True, text=True, encoding="utf-8"
            )
            if not sensitive_output:
                logger.debug(f"Command stdout: {process.stdout.strip()}")
            return process.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_message = f"Command '{' '.join(e.cmd)}' failed: {e.stderr.strip()}"
            logger.error(error_message)
            raise ReleaseFailedError(error_message) from e

    @staticmethod
    def _get_latest_tag() -> str:
        """Gets the latest Git tag, defaulting to "v0.0.0" if no tags are found. This method attempts to retrieve the most recent tag in the Git repository using the `git describe --tags --abbrev=0` command. If the command fails, it logs a warning and returns the default tag "v0.0.0".

        Args:
            None

        Returns:
            str: The latest Git tag as a string, or "v0.0.0" if no tags are available.
        """
        try:
            return ReleaseManager._run_command(
                ["git", "describe", "--tags", "--abbrev=0"]
            )
        except ReleaseFailedError:
            logger.warning("No tag found. Defaulting to v0.0.0.")
            return "v0.0.0"

    @staticmethod
    def _get_commits_since_tag(tag: str) -> list[dict[str, str]]:
        """Gets all commit hashes and subjects since a specified Git tag, returning a list of dictionaries containing the hash and subject of each commit.

        Args:
            tag (str): The Git tag from which to start retrieving commits.

        Returns:
            list[dict[str, str]]: A list of dictionaries, each with 'hash' and 'subject' keys representing individual commits.
        """
        # Use a delimiter that is unlikely to be in a commit message
        delimiter = "|||---|||"
        output = ReleaseManager._run_command(
            ["git", "log", f"{tag}..HEAD", f"--pretty=%h{delimiter}%s"]
        )
        if not output:
            return []

        commits = []
        for line in output.split("\n"):
            if delimiter in line:
                hash_val, subject = line.split(delimiter, 1)
                commits.append({"hash": hash_val.strip(), "subject": subject.strip()})
        return commits

    @staticmethod
    def _push_changes():
        """Pushes local commits and tags to the remote Git repository. This method executes the necessary Git commands to push any local commits and tags to the remote repository, ensuring that all changes are synchronized.

        Args: None

        Returns: None

        Raises: RuntimeError if the git push commands fail.
        """
        ReleaseManager._run_command(["git", "push"])
        ReleaseManager._run_command(["git", "push", "--tags"])
        logger.info("Successfully pushed commits and tags.")

    # --- Instance Methods (Stateful Workflow) ---

    def _pre_flight_checks(self):
        """Performs pre-flight validations to ensure the Git repository is in a clean state and on the correct release branch before proceeding with a release; verifies absence of uncommitted changes and correct branch alignment.

        Args:
        None

        Returns:
        None

        Raises:
        ReleaseFailedError: If uncommitted changes are detected or if the current branch does not match the specified release branch.
        """
        logger.info("Performing pre-flight checks...")

        # 1. Check for uncommitted changes
        status_output = self._run_command(["git", "status", "--porcelain"])
        if status_output:
            raise ReleaseFailedError(
                "Uncommitted changes found in the working directory. "
                "Please commit or stash them before releasing."
            )

        # 2. Check if on the correct release branch
        current_branch = self._run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if current_branch != self.config["branch"]:
            raise ReleaseFailedError(
                f"Not on the release branch '{self.config['branch']}'. "
                f"Currently on '{current_branch}'."
            )

        logger.info("Pre-flight checks passed successfully.")

    def _detect_bump(self) -> str | None:
        """Detects the type of version bump (major, minor, or patch) based on commit messages associated with the instance; analyzes commits to identify breaking changes, new features, or bug fixes to determine the appropriate Semantic Versioning (SemVer) bump type. Returns the bump type as a string ("major", "minor", "patch") or None if no relevant commits are found.

        Args:
            None

        Returns:
            str or None: The type of version bump ("major", "minor", "patch") or None if no relevant commit messages are detected.
        """
        bump_type: str | None = None
        for c in self.commits:
            subject = c["subject"]
            if "BREAKING CHANGE" in subject or re.search(r"\w+\(.*\)!:", subject):
                return "major"
            if subject.startswith("feat"):
                bump_type = "minor"
            elif subject.startswith("fix") and bump_type is None:
                bump_type = "patch"
        return bump_type

    def _bump_version(self, bump_type: str) -> str:
        """Bumps the version number based on the specified bump type and returns the updated version string.
        This method parses the current version from the instance, increments the major, minor, or patch component depending on the bump_type argument, and constructs a new version string in the format 'v<major>.<minor>.<patch>'.

        Args:
            bump_type (str): The type of version bump to perform. Valid values are "major", "minor", and "patch".

        Returns:
            str: The new version string following the format 'v<major>.<minor>.<patch>'.
        """
        major, minor, patch = map(int, self.old_version.strip("v").split("."))
        if bump_type == "major":
            major, minor, patch = major + 1, 0, 0
        elif bump_type == "minor":
            minor, patch = minor + 1, 0
        elif bump_type == "patch":
            patch += 1
        return f"v{major}.{minor}.{patch}"

    def _update_version_file(self):
        """Updates the version information in a specified file by traversing nested keys derived from the version key path, modifying the version value, and saving the changes back to the file. Raises a ReleaseFailedError if the operation fails due to file access issues, missing keys, or other errors during the update process.

        Args:
            None

        Returns:
            None

        Raises:
            ReleaseFailedError: If the version file cannot be read, the specified keys are missing, or an error occurs during file write operations.
        """
        keys = self.version_key_path.split(".")
        try:
            with Path(self.version_file_path).open("r+", encoding="utf-8") as f:
                data = toml.load(f)
                # Traverse to update the version
                temp_data = data
                for key in keys[:-1]:
                    temp_data = temp_data[key]
                temp_data[keys[-1]] = self.new_version.strip("v")

                # Write back to file
                f.seek(0)
                toml.dump(data, f)
                f.truncate()
            logger.info(
                f"Updated version in {self.version_file_path} to {self.new_version.strip('v')}"
            )
        except (FileNotFoundError, KeyError, Exception) as e:
            raise ReleaseFailedError(
                f"Failed to update version file {self.version_file_path}: {e}"
            ) from e

    @staticmethod
    def _parse_and_group_commits_for_changelog(
        commits: list[dict[str, str]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Parses a list of commit dictionaries following the Conventional Commits standard and groups them by type with extracted details for improved changelog formatting.

        Args:
            commits (list of dict): A list of commit dictionaries. Each dictionary should have at least the keys 'hash' and 'subject' representing the commit hash and subject line, respectively.

        Returns:
            dict: A dictionary where keys are commit types (e.g., 'feat', 'fix', 'other') and values are lists of dictionaries containing the commit 'hash' and parsed 'data' with details such as type, scope, breaking change indicator, and description.
        """
        grouped_commits = defaultdict(list)
        # Pattern to capture type, optional scope, breaking change, and description
        commit_pattern = re.compile(
            r"^(feat|fix|perf|refactor|docs|style|test|build|ci|chore)(?:\((.+?)\))?(!?): (.*)"
        )

        for commit in commits:
            subject = commit["subject"]
            match = commit_pattern.match(subject)
            if match:
                commit_type = match.group(1)
                scope = match.group(2)
                breaking = match.group(3) == "!"
                description = match.group(4)

                parsed_commit_data = {
                    "raw_subject": subject,
                    "type": commit_type,
                    "scope": scope,
                    "breaking": breaking,
                    "description": description,
                }
                grouped_commits[commit_type].append(
                    {"hash": commit["hash"], "data": parsed_commit_data}
                )
            else:
                # Fallback for non-conventional commits
                grouped_commits["other"].append(
                    {
                        "hash": commit["hash"],
                        "data": {
                            "raw_subject": subject,
                            "type": "other",
                            "scope": None,
                            "breaking": False,
                            "description": subject,
                        },
                    }
                )
        return grouped_commits

    def _generate_formatted_changelog_section(self) -> str:
        """Generates a formatted changelog section in Markdown format based on stored commit data.

        This method processes commit information to create a structured Markdown section suitable for appending to a changelog file. It groups commits by type, adds headers with emojis or titles, formats individual commit entries with optional links to specific commits in the repository, and includes the new version number along with the current date. The output provides a clear, organized summary of changes, enhancing changelog readability and consistency.

        Args:
            None

        Returns:
            str: A string containing the complete formatted changelog section, including headers, commit entries with optional links, and the version and date header.
        """
        grouped_commits = self._parse_and_group_commits_for_changelog(self.commits)
        repo_url = self.config.get("repo_url")

        new_section_parts = []
        dt = datetime.now().strftime("%Y-%m-%d")
        new_section_parts.append(f"## {self.new_version} ({dt})\n")

        # Iterate through ordered types to maintain consistent section order
        ordered_types = [
            "feat",
            "fix",
            "perf",
            "refactor",
            "docs",
            "style",
            "test",
            "build",
            "ci",
            "chore",
            "other",
        ]

        for type_key in ordered_types:
            if commits_list := grouped_commits.get(type_key):
                header = self.SECTION_HEADERS_WITH_EMOJIS.get(
                    type_key, f"### {type_key.capitalize()}"
                )
                new_section_parts.append(header)
                for c in commits_list:
                    commit_data = c["data"]
                    commit_link = ""
                    if repo_url:
                        commit_link = (
                            f" ([`{c['hash'][:7]}`]({repo_url}/commit/{c['hash']}))"
                        )

                    # Format subject: **type(scope):** description (link)
                    formatted_subject_prefix = f"**{commit_data['type']}"
                    if commit_data["scope"]:
                        formatted_subject_prefix += f"({commit_data['scope']})"
                    formatted_subject_prefix += ":**"

                    breaking_change_indicator = (
                        " **(BREAKING CHANGE)**" if commit_data["breaking"] else ""
                    )

                    new_section_parts.append(
                        f"- {formatted_subject_prefix}{breaking_change_indicator} {commit_data['description']}{commit_link}"
                    )
                new_section_parts.append(
                    ""
                )  # Add a blank line after each section for better readability

        return (
            "\n".join(part for part in new_section_parts if part is not None).strip()
            + "\n"
        )

    def _update_changelog(self):
        """Performs an update to the changelog file by inserting a new formatted release section at the appropriate position, handling legacy markers for backward compatibility, and creating the file if it does not exist. Raises a `ReleaseFailedError` if writing to the file fails.

        Args:
            None

        Returns:
            None
        """
        path = Path(self.config["changelog_file"])
        new_section = self._generate_formatted_changelog_section()

        new_marker = "<!-- avcmt-release-marker -->"
        legacy_marker = "<!-- version list -->"

        try:
            content = ""
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    content = f.read()

                # For backward compatibility, replace the old marker with the new one in memory.
                if legacy_marker in content:
                    logger.info(
                        f"Found legacy marker '{legacy_marker}'. Migrating to '{new_marker}'."
                    )
                    content = content.replace(legacy_marker, new_marker, 1)

            else:
                logger.info(f"Changelog file not found at {path}. Creating a new one.")
                # Create the file with a title and the new marker for future releases.
                content = f"# CHANGELOG\n\n{new_marker}\n"

            # Now, the logic only needs to deal with the new_marker.
            if new_marker in content:
                parts = content.split(new_marker, 1)
                final_content = (
                    f"{parts[0]}{new_marker}\n\n{new_section}{parts[1].lstrip()}"
                )
            else:
                # This case now only happens if the file exists but has NO marker at all.
                logger.warning(
                    f"No release marker found in {path}. Prepending content."
                )
                final_content = f"{new_section}\n{content}"

            with path.open("w", encoding="utf-8") as f:
                f.write(final_content)
            logger.info(f"Updated {path} with version {self.new_version}")
        except Exception as e:
            raise ReleaseFailedError(f"Failed to write to changelog {path}: {e}") from e

    def _commit_and_tag(self):
        """Performs staging, committing, and tagging of changes for a new version release using Git commands. It adds specified files, commits with a message including the new version, and creates a corresponding tag. This method may raise exceptions related to subprocess execution failures or Git errors."""
        files_to_add = [
            self.version_file_path,
            self.config["changelog_file"],
        ]
        self._run_command(["git", "add", *files_to_add])
        self._run_command(
            ["git", "commit", "-m", f"chore(release): {self.new_version}"]
        )
        self._run_command(["git", "tag", self.new_version])
        logger.info(f"Successfully committed and tagged {self.new_version}.")

    @staticmethod
    def _publish_to_pypi():
        """Builds and publishes the package to PyPI by executing build and publish commands; raises an exception if the PYPI_TOKEN environment variable is not set.

        Args:
            None

        Returns:
            None

        Raises:
            ReleaseFailedError: if the PYPI_TOKEN environment variable is missing.
        """
        logger.info("Starting PyPI publishing process...")
        pypi_token = os.getenv("PYPI_TOKEN")
        if not pypi_token:
            raise ReleaseFailedError("PYPI_TOKEN environment variable is not set.")

        logger.info("Building the package with 'poetry build'...")
        ReleaseManager._run_command(["poetry", "build"])

        logger.info("Publishing the package to PyPI...")
        ReleaseManager._run_command(
            ["poetry", "publish", "--username", "__token__", "--password", pypi_token],
            sensitive_output=True,
        )
        logger.info("Successfully published to PyPI.")

    def run(self, dry_run: bool = False, push: bool = False):
        """Performs the release process by bumping the version, updating the changelog, and optionally publishing or pushing changes.
        This method manages the full release workflow, including version detection, changelog generation, and deployment steps, with support for dry runs and conditional publishing.

        Args:
        - dry_run (bool): If True, simulate the release process without making any changes. Defaults to False.
        - push (bool): If True, push the commits and tags to the remote repository. Defaults to False.

        Returns:
        - str: The new version string if the release proceeds successfully; otherwise, None if there are no updates to release.
        """
        logger.info("--- ReleaseManager: Starting Release Process ---")

        if not dry_run:
            self._pre_flight_checks()

        self.old_version = self._get_latest_tag()
        self.commits = self._get_commits_since_tag(self.old_version)

        if not self.commits:
            logger.info("No new commits found. Nothing to release.")
            return

        bump_type = self._detect_bump()
        if not bump_type:
            logger.info("No relevant semantic commits found. Nothing to release.")
            return

        self.new_version = self._bump_version(bump_type)

        if dry_run:
            logger.info("--- [DRY RUN MODE] ---")
            logger.info(f"Next version would be: {self.new_version}")
            logger.info(f"Commits found: {len(self.commits)}")
            logger.info("Changelog section that would be generated:")
            print(self._generate_formatted_changelog_section())
            logger.info("No files will be changed.")
            return

        # Live Run
        self._update_version_file()
        self._update_changelog()
        self._commit_and_tag()

        if push:
            self._push_changes()

        if self.config.get("publish_to_pypi", False):
            ReleaseManager._publish_to_pypi()

        logger.info(f"🚀 Release {self.new_version} completed successfully!")

        return self.new_version
