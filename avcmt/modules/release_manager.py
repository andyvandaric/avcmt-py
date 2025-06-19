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
    """Custom exception for failures during the release process."""

    pass


class ReleaseManager:
    """
    Manages the entire semantic release process by orchestrating stateless git
    utilities and stateful versioning logic.
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
        """Initializes the manager by loading configuration."""
        self.config = ReleaseManager._load_config(config_path)
        self.old_version: str | None = None
        self.new_version: str | None = None
        self.commits: list[dict[str, str]] = []

    # --- Static Methods (Stateless Utilities) ---

    @staticmethod
    def _load_config(path: str) -> dict[str, Any]:
        """Loads release configuration from pyproject.toml."""
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
        """Helper to run any command and handle errors."""
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
        """Gets the latest git tag, defaulting to v0.0.0 if none exists."""
        try:
            return ReleaseManager._run_command(
                ["git", "describe", "--tags", "--abbrev=0"]
            )
        except ReleaseFailedError:
            logger.warning("No tag found. Defaulting to v0.0.0.")
            return "v0.0.0"

    @staticmethod
    def _get_commits_since_tag(tag: str) -> list[dict[str, str]]:
        """Gets all commit hashes and subjects since a given tag."""
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
        """Pushes commits and tags to the remote repository."""
        ReleaseManager._run_command(["git", "push"])
        ReleaseManager._run_command(["git", "push", "--tags"])
        logger.info("Successfully pushed commits and tags.")

    # --- Instance Methods (Stateful Workflow) ---

    def _pre_flight_checks(self):
        """Performs checks to ensure the repository is in a clean state for release."""
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
        """Detects version bump type based on instance's commit messages."""
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
        """Bumps the version based on the old version stored in the instance."""
        major, minor, patch = map(int, self.old_version.strip("v").split("."))
        if bump_type == "major":
            major, minor, patch = major + 1, 0, 0
        elif bump_type == "minor":
            minor, patch = minor + 1, 0
        elif bump_type == "patch":
            patch += 1
        return f"v{major}.{minor}.{patch}"

    def _update_version_file(self):
        """Updates the version in the file specified in the instance's config."""
        path, key_path = self.config["version_path"].split(":", 1)
        keys = key_path.split(".")
        try:
            with Path(path).open("r+", encoding="utf-8") as f:
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
            logger.info(f"Updated version in {path} to {self.new_version.strip('v')}")
        except (FileNotFoundError, KeyError, Exception) as e:
            raise ReleaseFailedError(
                f"Failed to update version file {path}: {e}"
            ) from e

    @staticmethod
    def _parse_and_group_commits_for_changelog(
        commits: list[dict[str, str]],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Parses conventional commits and groups them by type,
        extracting type, scope, and description for better formatting.
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
        """
        Parses conventional commits and generates a formatted changelog section with commit links.
        This version applies improved formatting.
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
        """
        Updates the changelog file by inserting the new formatted section
        at the correct position using a precise split method.
        """
        path = Path(self.config["changelog_file"])
        new_section = self._generate_formatted_changelog_section()
        # FIX: The marker was incorrectly set to an empty string.
        # It should be the '' comment from CHANGELOG.md.
        marker = ""

        try:
            content = ""
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    content = f.read()
            else:
                logger.info(f"Changelog file not found at {path}. Creating a new one.")
                content = f"# CHANGELOG\n\n{marker}\n"

            if marker in content:
                parts = content.split(marker, 1)
                final_content = (
                    f"{parts[0]}{marker}\n\n{new_section}{parts[1].lstrip()}"
                )
            else:
                logger.warning(
                    f"Marker '{marker}' not found in {path}. Prepending content."
                )
                final_content = f"{new_section}\n{content}"

            with path.open("w", encoding="utf-8") as f:
                f.write(final_content)
            logger.info(f"Updated {path} with version {self.new_version}")
        except Exception as e:
            raise ReleaseFailedError(f"Failed to write to changelog {path}: {e}") from e

    def _commit_and_tag(self):
        """Commits and tags the new version."""
        files_to_add = [
            self.config["version_path"].split(":")[0],
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
        """Builds and publishes the package to PyPI."""
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
        """Main method to execute the entire release workflow."""
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
